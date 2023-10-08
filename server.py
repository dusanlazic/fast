from gevent import monkey
monkey.patch_all()
import re
import os
import sys
import json
import yaml
import time
import uuid
import logging
import functools
from itertools import chain
from base64 import b64decode
from importlib import import_module, reload
from datetime import datetime, timedelta
from flask import Flask, request, send_from_directory
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from models import Flag, Webhook
from secrets import token_hex
from dsl import parse_query, build_query
from peewee import fn, IntegrityError, PostgresqlDatabase, DoesNotExist
from database import db
from playhouse.shortcuts import model_to_dict
from util.log import logger
from util.styler import TextStyler as st
from util.helpers import truncate, deep_update, flag_model_to_dict
from util.validation import validate_data, validate_delay, validate_interval, server_yaml_schema
from pyparsing.exceptions import ParseException

app = Flask(__name__, static_url_path='')
auth = HTTPBasicAuth()
socketio = SocketIO(app, cors_allowed_origins="*")

tick_number = -1
tick_start = None
game_start = None

config = {
    'game': {},
    'submitter': {
        'module': 'submitter'
    },
    'server': {
        'host': '0.0.0.0',
        'port': 2023
    },
    'database': {
        'name': 'fast',
        'user': 'admin',
        'password': 'admin',
        'host': 'localhost',
        'port': 5432
    }
}

RECOVERY_CONFIG_PATH = os.path.join('.fast', 'recover.json')


def main():
    banner()
    create_dot_dir()
    configure_flask()
    load_config()
    setup_database()

    game, submitter, server = config['game'], config['submitter'], config['server']

    # Schedule tick clock

    update_tick_clock()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=tick_clock,
        trigger='interval',
        seconds=game['tick_duration'],
        id='clock',
        next_run_time=tick_start
    )

    # Schedule flag submitting

    if submitter.get('delay'):
        delay = timedelta(seconds=submitter['delay'])
        interval = game['tick_duration']
        first_run = tick_start + delay
    elif submitter.get('interval'):
        interval = submitter['interval']
        now = datetime.now()
        elapsed = (now - tick_start).total_seconds()
        first_run = now + timedelta(seconds=elapsed //
                                    interval * interval + interval - elapsed)

    # Enable submitter importing
    sys.path.append(os.getcwd())

    scheduler.add_job(
        func=submitter_wrapper,
        trigger='interval',
        seconds=interval,
        id='submitter',
        next_run_time=first_run
    )

    # Run scheduler and Gevent server

    scheduler.start()

    socketio.run(
        app,
        host=server['host'],
        port=server['port']
    )


@auth.verify_password
def authenticate(username, password):
    return password == config['server']['password']


@auth.error_handler
def unauthorized():
    return {"error": "Unauthorized access"}, 401


def basic(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'password' in config['server']:
            return auth.login_required(func)(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper


@socketio.on('connect')
def authenticate_websocket():
    if 'password' not in config['server']:
        return True

    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False

    basic, credentials = auth_header.split(' ')
    if basic.lower() != 'basic':
        return False

    username, password = b64decode(credentials).decode('utf-8').split(':')

    return authenticate(username, password)


@app.route('/enqueue', methods=['POST'])
@basic
def enqueue():
    flags = request.json['flags']
    exploit = request.json['exploit']
    target = request.json['target']
    player = request.json['player']

    with db.connection_context():
        duplicate_flags = [flag.value for flag in
                           Flag.select(Flag.value)
                           .where(Flag.value.in_(flags))]

        flags_to_insert = [{'value': flag_value, 'exploit': exploit, 'target': target,
                            'tick': tick_number, 'player': player, 'status': 'queued'}
                           for flag_value in flags if flag_value not in duplicate_flags]

        Flag.insert_many(flags_to_insert).on_conflict_ignore().execute()

    new_flags = [flag['value'] for flag in flags_to_insert]

    if new_flags:
        logger.success(f"{st.bold(player)} retrieved " +
                       (f"{st.bold(1)} flag " if len(new_flags) == 1 else f"{st.bold(len(new_flags))} flags ") +
                       f"from {st.bold(target)} using {st.bold(exploit)}. 🚩  — {st.faint(truncate(' '.join(new_flags), 50))}")

    socketio.emit('enqueue', {
        'new': len(new_flags),
        'dup': len(duplicate_flags),
        'player': player,
        'target': target,
        'exploit': exploit
    })

    return {
        'duplicates': duplicate_flags,
        'new': new_flags
    }


@app.route('/enqueue-fallback', methods=['POST'])
@basic
def enqueue_fallback():
    flags = request.get_json()

    new_flags = []
    duplicate_flags = []

    for flag in flags:
        flag_value = flag['flag']
        exploit = flag['exploit']
        target = flag['target']
        player = flag['player']
        timestamp = flag.get('timestamp', None)
        tick = int((datetime.fromtimestamp(timestamp) - game_start).total_seconds() //
                   config['game']['tick_duration']) if timestamp else tick_number

        try:
            with db.connection_context():
                Flag.create(value=flag_value, exploit=exploit, target=target,
                            tick=tick, player=player, status='queued')
            new_flags.append(flag_value)
        except IntegrityError:
            duplicate_flags.append(flag_value)

    if new_flags:
        logger.success(f"{st.bold(player)} sent " +
                       (f"{st.bold(1)} flag " if len(new_flags) == 1 else f"{st.bold(len(new_flags))} flags from fallback flagstore. 🚩"))

    socketio.emit('enqueue_fallback', {
        'new': len(new_flags),
        'dup': len(duplicate_flags)
    })

    return {
        'duplicates': duplicate_flags,
        'new': new_flags
    }


@app.route('/enqueue-manual', methods=['POST'])
@basic
def enqueue_manual():
    flags = request.json['flags']
    player = request.json.get('player') or 'anon'
    action = request.json.get('action') or 'submit'

    if action == 'enqueue':
        new_flags = []
        duplicate_flags = []

        for flag_value in flags:
            try:
                with db.connection_context():
                    new_flag = Flag.create(value=flag_value, tick=tick_number, player=player,
                                           exploit='manual', target='unknown', status='queued')
                new_flags.append(new_flag)
            except IntegrityError:
                duplicate_flags.append(flag_value)

        return [
            {
                'status': flag.status,
                'value': flag.value,
                'persisted': flag._pk is not None
            } for flag in new_flags
        ] + [
            {
                'status': 'duplicate',
                'value': value,
                'persisted': False
            } for value in duplicate_flags
        ]
    elif action == 'submit':
        accepted, rejected = submit_func(flags)
        accepted_flags = []
        rejected_flags = []

        for value, response in accepted.items():
            try:
                with db.connection_context():
                    flag = Flag.create(value=value, tick=tick_number, player=player,
                                       exploit='manual', target='unknown', status='accepted', response=response)
                accepted_flags.append(flag)
            except IntegrityError:
                accepted_flags.append(
                    Flag(value=value, status='accepted', response=response))

        for value, response in rejected.items():
            try:
                with db.connection_context():
                    flag = Flag.create(value=value, tick=tick_number, player=player,
                                       exploit='manual', target='unknown', status='rejected', response=response)
                rejected_flags.append(flag)
            except IntegrityError:
                rejected_flags.append(
                    Flag(value=value, status='rejected', response=response))

        return [
            {
                'status': flag.status,
                'value': flag.value,
                'response': flag.response,
                'persisted': flag._pk is not None
            } for flag in chain(accepted_flags, rejected_flags)
        ]
    else:
        return {
            'message': 'Unknown action.'
        }, 400


@app.route('/vuln-report', methods=['POST'])
@basic
def vulnerability_report():
    exploit = request.json['exploit']
    target = request.json['target']
    player = request.json['player']

    socketio.emit('vulnerabilityReported', {
        'player': player,
        'target': target,
        'exploit': exploit
    })

    logger.warning(f"{st.bold(player)} retrieved " +
                   f"{st.bold('own')} flag from {st.bold(target)} using {st.bold(exploit)}! Patch the service ASAP.")

    return {
        'message': 'Vulnerability reported.'
    }


@app.route('/sync')
@basic
def sync():
    now: datetime = datetime.now()

    duration = config['game']['tick_duration']
    elapsed = (now - tick_start).total_seconds()
    if elapsed > 0:
        remaining = duration - elapsed
    else:
        remaining = -elapsed

    delay = config['submitter'].get('delay')
    interval = config['submitter'].get('interval')

    if delay is not None:
        next_submit: datetime = tick_start + \
            timedelta(seconds=delay + (duration if elapsed > delay else 0))
    elif interval:
        next_submit: datetime = now + \
            timedelta(seconds=elapsed // interval *
                      interval + interval - elapsed)

    next_submit_remaining = (next_submit - now).total_seconds()

    return {
        'submitter': {
            'elapsed': (interval or delay) - next_submit_remaining,
            'remaining': next_submit_remaining,
            'interval': interval or delay
        },
        'tick': {
            'current': tick_number,
            'duration': duration,
            'elapsed': elapsed,
            'remaining': remaining,
        }
    }


@app.route('/flagstore-stats')
@basic
def get_flagstore_stats():
    with db.connection_context():
        queued_count = Flag.select().where(Flag.status == 'queued').count()
        accepted_count = Flag.select().where(Flag.status == 'accepted').count()
        rejected_count = Flag.select().where(Flag.status == 'rejected').count()

        accepted_delta = Flag.select().where(Flag.status == 'accepted',
                                             Flag.tick == tick_number).count()
        rejected_delta = Flag.select().where(Flag.status == 'rejected',
                                             Flag.tick == tick_number).count()

    return {
        'queued': queued_count,
        'accepted': accepted_count,
        'rejected': rejected_count,
        'delta': {
            'accepted': accepted_delta,
            'rejected': rejected_delta
        }
    }


@app.route('/exploit-analytics')
@basic
def get_exploit_analytics():
    return generate_exploit_analytics()


@app.route('/search', methods=['POST'])
@basic
def search():
    request_json = request.json

    # Build search query
    try:
        parsed_query = parse_query(request_json['query'])
        peewee_query = build_query(parsed_query)
    except KeyError:
        return {
            'error': 'Missing query.'
        }, 400
    except ParseException:
        return {
            'error': 'Invalid query.'
        }, 400
    except AttributeError as e:
        return {
            'error': f'Unknown field {e.args[0].split()[-1]}.'
        }, 400
    except Exception as e:
        return {
            'error': f'Something is broken either with your query or with the way it is processed. :('
        }, 500

    # Select page
    page = request_json.get('page', 1)
    show = min(request_json.get('show', 10), 100)

    # Select sorting
    sort_fields = request_json.get("sort", [])
    sort_expressions = [
        getattr(Flag, item["field"]).desc(
        ) if item["direction"] == "desc" else getattr(Flag, item["field"])
        for item in sort_fields
    ]

    # Run query
    start = time.time()
    try:
        results = [flag_model_to_dict(flag) for flag in
                   Flag.select()
                   .where(peewee_query)
                   .order_by(*sort_expressions)
                   .paginate(page, show)
                   ]
    except Exception:
        return {
            'error': f'Failed to run the query.'
        }, 500
    elapsed = time.time() - start

    total = Flag.select().where(peewee_query).count()
    total_pages = -(-total // show)

    metadata = {
        "paging": {
            "current": page,
            "last": total_pages,
            "hasNext": page + 1 <= total_pages,
            "hasPrev": page > 1
        },
        "results": {
            "total": total,
            "fetched": len(results),
            "executionTime": elapsed
        }
    }

    return {
        'results': results,
        'metadata': metadata
    }


@app.route('/config')
@basic
def get_config():
    player = request.args['player']
    address = request.remote_addr

    socketio.emit('playerConnect', {
        'message': f'{player} has connected from {address}.'
    })

    return config


@app.route('/flag-format')
@basic
def get_flag_format():
    return {
        "format": config['game']['flag_format']
    }


@app.route('/trigger-submit', methods=['POST'])
@basic
def trigger_submit():
    logger.info(
        f"Submitter triggered manually by {st.bold(request.json['player'])}.")
    submitter_wrapper()

    return {
        'message': 'Flag submission completed. Check the web dashboard.'
    }


@app.route('/webhooks')
@basic
def get_webhooks():
    try:
        results = [model_to_dict(webhook) for webhook in
                   Webhook.select().order_by(Webhook.exploit)
                   ]

        metadata = {
            "total": len(results)
        }

        return {
            'results': results,
            'metadata': metadata
        }
    except Exception:
        return {
            'error': f'Failed to fetch webhooks.'
        }, 500


@app.route('/webhooks', methods=['POST'])
@basic
def create_webhook():
    try:
        data = request.json
        exploit = data.get('exploit', token_hex(4))
        player = data.get('player', 'anon')
        new_webhook = Webhook.create(
            id=uuid.uuid4(), exploit=exploit, player=player)
        return {'id': str(new_webhook.id)}, 201
    except Exception as e:
        return {'error': f'Failed to create webhook: {str(e)}'}, 500


@app.route('/webhooks/<string:webhook_id>', methods=['PUT'])
@basic
def update_webhook(webhook_id):
    try:
        data = request.json
        webhook = Webhook.get_by_id(uuid.UUID(webhook_id))

        if 'exploit' in data:
            webhook.exploit = data['exploit']
        if 'player' in data:
            webhook.player = data['player']
        if 'disabled' in data:
            webhook.disabled = data['disabled']

        webhook.save()

        return {'id': str(webhook.id), 'message': 'Webhook updated successfully'}, 200
    except DoesNotExist:
        return {'error': 'Webhook not found'}, 404
    except Exception as e:
        return {'error': f'Failed to update webhook: {str(e)}'}, 500


@app.route('/<string:webhook_id>', methods=['GET', 'POST', 'PUT'])
def exfiltrate(webhook_id):
    try:
        webhook = Webhook.get((Webhook.id == uuid.UUID(
            webhook_id)) & (Webhook.disabled == False))

        contains_flags = request.get_data(as_text=True)
        flags = re.findall(config['game']['flag_format'], contains_flags)
        if not flags:
            return '', 204

        target = request.args.get('target', 'unknown')
        exploit = webhook.exploit
        player = webhook.player

        new_flags = []
        duplicate_flags = []

        for flag_value in flags:
            try:
                with db.connection_context():
                    Flag.create(value=flag_value, exploit=exploit, target=target,
                                tick=tick_number, player=player, status='queued')
                new_flags.append(flag_value)
            except IntegrityError:
                duplicate_flags.append(flag_value)

        if new_flags:
            logger.success(f"{st.bold(player)} exfiltrated " +
                           (f"{st.bold(1)} flag " if len(new_flags) == 1 else f"{st.bold(len(new_flags))} flags ") +
                           f"from {st.bold(target)} using {st.bold(exploit)}. 🚩  — {st.faint(truncate(' '.join(new_flags), 50))}")

        socketio.emit('enqueue', {
            'new': len(new_flags),
            'dup': len(duplicate_flags),
            'player': player,
            'target': target,
            'exploit': exploit
        })

        return '', 204
    except Exception:
        return '', 404


@app.route('/')
@basic
def dashboard():
    return send_from_directory(app.static_folder, 'index.html')


def submitter_wrapper():
    flags = [flag.value for flag in
             Flag.select().where(Flag.status == 'queued')]

    if not flags:
        socketio.emit('submitSkip', {
            'message': 'No flags in the queue! Submission skipped.'
        })
        socketio.emit('analyticsUpdate', generate_exploit_analytics())

        logger.info(f"No flags in the queue! Submission skipped.")

        return

    socketio.emit('submitStart', {
        'message': f'Submitting {len(flags)} flags...',
        'data': {
            'count': len(flags)
        }
    })

    logger.info(st.bold(f"Submitting {len(flags)} flags..."))

    accepted, rejected = submit_func(flags)

    if accepted:
        logger.success(f"{st.bold(len(accepted))} flags accepted. ✅")
    else:
        logger.warning(
            f"No flags accepted, or your script is not returning accepted flags.")

    if rejected:
        logger.warning(f"{st.bold(len(rejected))} flags rejected.")

    if len(flags) != len(accepted) + len(rejected):
        logger.error(
            f"{st.bold(len(flags) - len(accepted) - len(rejected))} responses missing. Flags may be submitted, but your stats may be inaccurate.")

    with db.atomic():
        if accepted:
            to_accept = Flag.select().where(Flag.value.in_(list(accepted.keys())))
            for flag in to_accept:
                flag.status = 'accepted'
                flag.response = accepted[flag.value]
            Flag.bulk_update(to_accept, fields=[Flag.status, Flag.response])

        if rejected:
            to_reject = Flag.select().where(Flag.value.in_(list(rejected.keys())))
            for flag in to_reject:
                flag.status = 'rejected'
                flag.response = rejected[flag.value]
            Flag.bulk_update(to_reject, fields=[Flag.status, Flag.response])

    with db.connection_context():
        queued_count = Flag.select().where(Flag.status == 'queued').count()
        accepted_count = Flag.select().where(Flag.status == 'accepted').count()
        rejected_count = Flag.select().where(Flag.status == 'rejected').count()

    socketio.emit('submitComplete', {
        'message': f'{len(accepted)} flag{"s" if len(accepted) > 1 else ""} accepted, {len(rejected)} rejected.',
        'data': {
            'queued': queued_count,
            'accepted': accepted_count,
            'rejected': rejected_count,
            'delta': {
                'accepted': len(accepted),
                'rejected': len(rejected)
            }
        }
    })

    socketio.emit('analyticsUpdate', generate_exploit_analytics())

    queued_count_st = st.color(
        st.bold(queued_count), 'green') if queued_count == 0 else st.bold(queued_count)

    accepted_count_st = st.color(st.bold(
        accepted_count), 'green') if accepted_count > 0 else st.color(st.bold(accepted_count), 'yellow')

    rejected_count_st = st.color(st.bold(
        rejected_count), 'green') if rejected_count == 0 else st.color(st.bold(rejected_count), 'yellow')

    logger.info(
        f"{st.bold('Stats')} — {queued_count_st} queued, {accepted_count_st} accepted, {rejected_count_st} rejected.")


def tick_clock():
    global tick_number, tick_start

    tick_number += 1
    tick_start = datetime.now()
    next_tick_start = tick_start + \
        timedelta(seconds=config['game']['tick_duration'])

    socketio.emit('tickStart', {
        'current': tick_number,
    })

    logger.info(f'Started tick {st.bold(str(tick_number))}. ' +
                f'Next tick scheduled for {st.bold(next_tick_start.strftime("%H:%M:%S"))}. ⏱️')


def generate_exploit_analytics():
    tick_window = 10
    latest_tick = tick_number
    # add 1 to ignore -11th tick
    oldest_tick = max(0, latest_tick - tick_window + 1)

    query = Flag.select(Flag.player, Flag.exploit, Flag.tick, fn.COUNT(Flag.id).alias('flag_count')) \
                .where((Flag.tick >= oldest_tick) & (Flag.tick <= latest_tick) & (Flag.status == 'accepted') & (Flag.exploit != 'manual')) \
                .group_by(Flag.player, Flag.exploit, Flag.tick)
    results = [(result.player, result.exploit, result.tick,
                result.flag_count) for result in query]

    tick_indices = [i for i in range(oldest_tick, latest_tick + 1)]
    report = {'ticks': tick_indices, 'exploits': {}}

    for player, exploit, tick, flag_count in results:
        key = f'{player}-{exploit}'
        if key not in report['exploits']:
            report['exploits'][key] = {
                'player': player,
                'exploit': exploit,
                'data': {
                    'accepted': [0] * len(tick_indices)
                }
            }

        report['exploits'][key]['data']['accepted'][tick_indices.index(
            tick)] = flag_count

    return report


def setup_database(log=True):
    postgres = PostgresqlDatabase(
        config['database']['name'],
        user=config['database']['user'],
        password=config['database']['password'],
        host=config['database']['host'],
        port=config['database']['port']
    )

    db.initialize(postgres)
    try:
        db.connect()
    except Exception as e:
        logger.error(
            f"An error occurred when connecting to the database:\n{st.color(e, 'red')}")
        exit(1)

    db.create_tables([Flag, Webhook])
    Flag.add_index(Flag.value)

    if log:
        logger.success('Database connected.')


def configure_flask():
    # Configure CORS
    if os.environ.get('PYTHON_ENV') == 'development':
        CORS(app)

    # Set static path
    app.static_folder = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'web', 'dist')

    # Disable logs
    logging.getLogger('werkzeug').setLevel(logging.ERROR)


def submit_func(flags):
    module_name = config['submitter']['module']
    # Ensure it's always the latest one
    imported_module = reload(import_module(module_name))
    imported_func = getattr(imported_module, 'submit')

    return imported_func(flags)


def load_config():
    # Remove datetime resolver
    # https://stackoverflow.com/a/52312810
    yaml.SafeLoader.yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != 'tag:yaml.org,2002:timestamp'] for
        k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    # Load server.yaml
    if not os.path.isfile('server.yaml'):
        logger.error(
            f"{st.bold('server.yaml')} not found in the current working directory. Exiting...")
        exit(1)

    with open('server.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    if not yaml_data:
        logger.error(f"{st.bold('fast.yaml')} is empty. Exiting...")
        exit(1)

    # Load and validate server config
    if not validate_data(yaml_data, server_yaml_schema, custom=[validate_delay, validate_interval]):
        logger.error(f"Fix errors in {st.bold('server.yaml')} and rerun.")
        exit(1)

    deep_update(config, yaml_data)

    # Wrap single team ip in a list
    if type(config['game']['team_ip']) != list:
        config['game']['team_ip'] = [config['game']['team_ip']]

    if config['server'].get('password'):
        conn_str = f"http://username:***@{config['server']['host']}:{config['server']['port']}"
    else:
        conn_str = f"http://{config['server']['host']}:{config['server']['port']}"

    logger.success(f'Fast server configured successfully.')
    logger.info(f'Server will run at {st.color(conn_str, "cyan")}.')


def update_tick_clock():
    global tick_start, tick_number, game_start

    now = datetime.now()
    tick_duration = timedelta(seconds=config['game']['tick_duration'])

    if config['game'].get('start'):
        game_start_str = config['game'].get('start')
        if len(game_start_str) == 19:
            datetime_format = "%Y-%m-%d %H:%M:%S"
        else:
            datetime_format = "%Y-%m-%d %H:%M"

        game_start = datetime.strptime(game_start_str, datetime_format)
    elif os.path.isfile(RECOVERY_CONFIG_PATH):
        with open(RECOVERY_CONFIG_PATH) as file:
            recovery_data = json.loads(file.read())

        game_start = datetime.fromtimestamp(float(recovery_data['started']))
    else:
        game_start = now
        with open(RECOVERY_CONFIG_PATH, 'w') as file:
            file.write(json.dumps({
                'started': game_start.timestamp(),
            }))

    if game_start < now:
        tick_number = (now - game_start) // tick_duration

        into_tick = (now - game_start) % tick_duration
        tick_start = now + tick_duration - into_tick

        logger.info(
            f"Tick clock will continue from tick {st.bold(tick_number + 1)}. Tick scheduled for {st.bold(tick_start.strftime('%H:%M:%S'))}. ⏱️")
    elif game_start == now:
        tick_number = -1
        tick_start = now

        logger.info(f"Tick clock started from tick 0.")
    elif game_start > now:
        tick_number = -1
        tick_start = game_start

        logger.info(
            f"Game has not started yet. Tick 0 scheduled for {st.bold(tick_start.strftime('%H:%M:%S'))}. ⏱️")


def create_dot_dir():
    dot_dir_path = '.fast'
    if not os.path.exists(dot_dir_path):
        os.makedirs(dot_dir_path)
        logger.success(f'Created .fast directory.')


def banner():
    vers = '1.1.0-dev'
    print(f"""
\033[32;1m     .___    ____\033[0m    ______         __ 
\033[32;1m    /   /\__/   /\033[0m   / ____/_  ____ / /_  
\033[32;1m   /   /   /  ❬` \033[0m  / /_/ __ `/ ___/ __/
\033[32;1m  /___/   /____\ \033[0m / __/ /_/ (__  ) /_  
\033[32;1m /    \___\/     \033[0m/_/  \__,_/____/\__/  
\033[32;1m/\033[0m""" + f"\033[32mserver\033[0m \033[2mv{vers}\033[0m".rjust(52) + "\n")
