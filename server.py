from gevent import monkey
monkey.patch_all()
import os
import re
import sys
import json
import yaml
import time
import logging
import functools
from itertools import chain
from base64 import b64decode
from importlib import import_module
from datetime import datetime, timedelta
from flask import Flask, request, send_from_directory
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from models import Flag
from dsl import parse_query, build_query
from peewee import fn, IntegrityError, PostgresqlDatabase
from playhouse.shortcuts import model_to_dict
from database import db
from util.log import logger
from util.styler import TextStyler as st
from util.helpers import truncate, deep_update
from util.validation import validate_data, validate_delay, server_yaml_schema

app = Flask(__name__, static_url_path='')
auth = HTTPBasicAuth()
socketio = SocketIO(app, cors_allowed_origins="*")

tick_number = -1
tick_start = datetime.max
server_start = datetime.max
submit_func = None

config = {
    'game': {},
    'submitter': {
        'module': 'submitter',
        'run_every_nth_tick': 1
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

RECOVERY_CONFIG_PATH = '.recover.json'


def main():
    splash()
    configure_flask()
    load_config()
    setup_database()
    recover()

    game, submitter, server = config['game'], config['submitter'], config['server']

    # Schedule tick clock

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=tick_clock,
        trigger='interval',
        seconds=game['tick_duration'],
        id='clock',
        next_run_time=tick_start
    )

    # Schedule flag submitting

    delay = timedelta(seconds=submitter['delay'])
    run_every_nth = submitter['run_every_nth_tick']
    interval = run_every_nth * game['tick_duration']
    first_run =  tick_start + (run_every_nth - 1) * timedelta(seconds=game['tick_duration']) + delay

    global submit_func
    sys.path.append(os.getcwd())
    module = import_module(submitter['module'])
    submit_func = getattr(module, 'submit')

    scheduler.add_job(
        func=submitter_wrapper,
        args=(submit_func,),
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

    new_flags = []
    duplicate_flags = []

    for flag_value in flags:
        try:
            with db.atomic():
                Flag.create(value=flag_value, exploit=exploit, target=target, 
                            tick=tick_number, player=player, status='queued')
            new_flags.append(flag_value)
        except IntegrityError:
            duplicate_flags.append(flag_value)
    
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
        'new':  new_flags
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
        tick = int((datetime.fromtimestamp(timestamp) - server_start).total_seconds() // config['game']['tick_duration']) if timestamp else tick_number

        try:
            with db.atomic():
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
        'new':  new_flags
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
                with db.atomic():
                    new_flag = Flag.create(value=flag_value, tick=tick_number, player=player,
                    exploit='manual', target='unknown', status='queued')
                new_flags.append(new_flag)
            except IntegrityError:
                duplicate_flags.append(flag_value)
        
        return [
            {
                'status': flag.status, 
                'value': flag.value
            } for flag in new_flags
        ] + [
            {
                'status': 'duplicate',
                'value': value
            } for value in duplicate_flags
        ]
    elif action == 'submit':
        accepted, rejected = submit_func(flags)
        accepted_flags = []
        rejected_flags = []

        for value, response in accepted.items():
            try:
                with db.atomic():
                    flag = Flag.create(value=value, tick=tick_number, player=player, 
                    exploit='manual', target='unknown', status='accepted', response=response)
                accepted_flags.append(flag)
            except IntegrityError:
                pass
        
        for value, response in rejected.items():
            try:
                with db.atomic():
                    flag = Flag.create(value=value, tick=tick_number, player=player, 
                    exploit='manual', target='unknown', status='rejected', response=response)
                rejected_flags.append(flag)
            except IntegrityError:
                pass
        
        return [
            {
                'status': flag.status, 
                'value': flag.value,
                'response': flag.response
            } for flag in chain(accepted_flags, rejected_flags)
        ]
    else:
        return {
            'message': 'Vulnerability reported.'
        }


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
    submit_delay = config['submitter']['delay']

    elapsed = (now - tick_start).total_seconds()
    remaining = duration - elapsed

    next_submit: datetime = tick_start + timedelta(seconds=submit_delay + (duration if elapsed > submit_delay else 0))
    next_submit_remaining = (next_submit - now).total_seconds()

    return {
        'submitter': {
            'remaining': next_submit_remaining,
            'delay': submit_delay
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
    queued_count = Flag.select().where(Flag.status == 'queued').count()
    accepted_count = Flag.select().where(Flag.status == 'accepted').count()
    rejected_count = Flag.select().where(Flag.status == 'rejected').count()

    accepted_delta =  Flag.select().where(Flag.status == 'accepted', Flag.tick == tick_number).count()
    rejected_delta =  Flag.select().where(Flag.status == 'rejected', Flag.tick == tick_number).count()

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
def search():
    # TODO: Validate request
    request_json = request.json

    # Build search query
    # TODO: Validate query and handle errors
    parsed_query = parse_query(request_json['query'])
    peewee_query = build_query(parsed_query)
    
    # Select page
    page = request_json.get('page', 1)
    show = min(request_json.get('show', 10), 100)

    # Select sorting
    sort_fields = request_json.get("sort", [])
    sort_expressions = [
        getattr(Flag, item["field"]).desc() if item["direction"] == "desc" else getattr(Flag, item["field"])
        for item in sort_fields
    ]

    # Run query
    start = time.time()
    results = [model_to_dict(flag) for flag in 
        Flag.select()
        .where(peewee_query)
        .order_by(*sort_expressions)
        .paginate(page, show)
    ]
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

    response = {
        'results': results,
        'metadata': metadata
    }

    # Hide flags
    hide_flags = request_json.get('hide_flags', 'on')
    if hide_flags and hide_flags.lower() == 'off':
        return response

    response_str = json.dumps(response, default=str)
    redacted_response_str = re.sub(config['game']['flag_format'], '[REDACTED]', response_str)
    return json.loads(redacted_response_str)


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
    logger.info(f"Submitter triggered manually by {st.bold(request.json['player'])}.")
    submitter_wrapper(submit_func)

    # TODO: Improve interactivity
    return {
        'message': 'Flags submitted.'
    }


@app.route('/')
@basic
def dashboard():
    return send_from_directory(app.static_folder, 'index.html')


def submitter_wrapper(submit):
    flags = [flag.value for flag in
             Flag.select().where(Flag.status == 'queued')]

    if not flags:
        socketio.emit('submitSkip', {
            'message': 'No flags in the queue! Submission skipped.'
        })

        logger.info(f"No flags in the queue! Submission skipped.")

        return

    socketio.emit('submitStart', {
        'message': f'Submitting {len(flags)} flags...'
    })

    logger.info(st.bold(f"Submitting {len(flags)} flags..."))

    accepted, rejected = submit(flags)

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
    latest_tick = tick_number  # subtract 1 to ignore last tick
    oldest_tick = max(0, latest_tick - tick_window + 1)  # add 1 to ignore -11th tick

    query = Flag.select(Flag.player, Flag.exploit, Flag.tick, fn.COUNT(Flag.id).alias('flag_count')) \
                .where((Flag.tick >= oldest_tick) & (Flag.tick <= latest_tick) & (Flag.status == 'accepted') & (Flag.exploit != 'manual')) \
                .group_by(Flag.player, Flag.exploit, Flag.tick)
    results = [(result.player, result.exploit, result.tick, result.flag_count) for result in query]

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

        report['exploits'][key]['data']['accepted'][tick_indices.index(tick)] = flag_count

    return report


def setup_database():
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
        exit()
    
    db.create_tables([Flag])
    Flag.add_index(Flag.value)
    logger.success('Database connected.')


def configure_flask():
    # Configure CORS
    if os.environ.get('PYTHON_ENV') == 'development':
        CORS(app)

    # Set static path
    app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'dist')

    # Disable logs
    logging.getLogger('werkzeug').setLevel(logging.ERROR)


def load_config():
    # Load server.yaml
    with open('server.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Load and validate server config
    if not validate_data(yaml_data, server_yaml_schema, custom=validate_delay):
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


def recover():
    global tick_start, tick_number, server_start

    if os.path.isfile(RECOVERY_CONFIG_PATH):
        with open(RECOVERY_CONFIG_PATH) as file:
            recovery_data = json.loads(file.read())
        
        now = datetime.now()
        server_start = datetime.fromtimestamp(float(recovery_data['started']))
        tick_duration = timedelta(seconds=config['game']['tick_duration'])

        ticks_passed = (now - server_start) // tick_duration
        into_tick = (now - server_start) % tick_duration

        tick_start = now + tick_duration - into_tick
        tick_number = ticks_passed

        logger.info(f"Continuing from tick {st.bold(tick_number)}. Tick scheduled for {st.bold(tick_start.strftime('%H:%M:%S'))}. ⏱️")
        logger.info(f"To reset Fast and run from tick 0, run {st.bold('reset')} and rerun.")
    else:
        tick_start = server_start = datetime.now() + timedelta(seconds=0.5)
        with open(RECOVERY_CONFIG_PATH, 'w') as file:
            file.write(json.dumps({
                'started': tick_start.timestamp(),
            }))


def splash():
    vers = '0.0.1'
    print(f"""
[32;1m     .___    ____[0m    ______         __ 
[32;1m    /   /\__/   /[0m   / ____/_  ____ / /_  
[32;1m   /   /   /  ❬` [0m  / /_/ __ `/ ___/ __/
[32;1m  /___/   /____\ [0m / __/ /_/ (__  ) /_  
[32;1m /    \___\/     [0m/_/  \__,_/____/\__/  
[32;1m/[0m                      [32mserver[0m [2mv{vers}[0m
""")
