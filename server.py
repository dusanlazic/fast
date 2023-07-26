import os
import sys
import json
import yaml
import logging
import functools
import gunicorn.app.base
from importlib import import_module
from datetime import datetime, timedelta
from flask import Flask, request, render_template
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler
from models import Flag
from peewee import fn, IntegrityError, PostgresqlDatabase
from database import db
from util.log import logger
from util.styler import TextStyler as st
from util.helpers import truncate, deep_update
from util.validation import validate_data, validate_delay, server_yaml_schema

app = Flask(__name__)
auth = HTTPBasicAuth()
socketio = SocketIO(app)

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

    # Run scheduler and Flask server

    scheduler.start()

    socketio.run(
        app,
        host=server['host'],
        port=server['port']
    )

    FastServerApplication(socketio, {
        'bind': '%s:%s' % (server['host'], server['port']),
        'workers': 1
    }).run()


@auth.verify_password
def authenticate(username, password):
    return password == config['server']['password']


@auth.error_handler
def unauthorized():
    return {"error": "Unauthorized access"}, 401


def basic(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if config['server'].get('password'): 
            return auth.login_required(func)(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper


@app.route('/')
@basic
def dashboard():
    return render_template('dashboard.html')


@app.route('/enqueue', methods=['POST'])
@basic
def enqueue():
    flags = request.json['flags']
    exploit = request.json['exploit']
    target = request.json['target']
    player = request.json['player']
    timestamp = request.json.get('timestamp', None)
    tick = int((datetime.fromtimestamp(timestamp) - server_start).total_seconds() // config['game']['tick_duration']) if timestamp else tick_number

    new_flags = []
    duplicate_flags = []

    for flag_value in flags:
        try:
            with db.atomic():
                Flag.create(value=flag_value, exploit=exploit, target=target, 
                            tick=tick, player=player, status='queued')
            new_flags.append(flag_value)
        except IntegrityError:
            duplicate_flags.append(flag_value)
    
    if new_flags:
        logger.success(f"{st.bold(player)} retrieved " +
                    (f"{st.bold(1)} flag " if len(new_flags) == 1 else f"{st.bold(len(new_flags))} flags ") + 
                    f"from {st.bold(target)} using {st.bold(exploit)}. 🚩  — {st.faint(truncate(' '.join(new_flags), 50))}")

    socketio.emit('enqueue_event', {
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


@app.route('/vuln-report', methods=['POST'])
@basic
def vulnerability_report():
    exploit = request.json['exploit']
    target = request.json['target']
    player = request.json['player']

    socketio.emit('vulnerability_event', {
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


@app.route('/config')
@basic
def get_config():
    player = request.args['player']
    address = request.remote_addr

    socketio.emit('log_event', {
        'message': f'{player} has connected from {address}.'
    })

    return config


@app.route('/trigger-submit', methods=['POST'])
@basic
def trigger_submit():
    logger.info(f"Submitter triggered manually by {st.bold(request.json['player'])}.")
    submitter_wrapper(submit_func)

    # TODO: Improve interactivity
    return {
        'message': 'Flags submitted.'
    }


def submitter_wrapper(submit):
    flags = [flag.value for flag in
             Flag.select().where(Flag.status == 'queued')]

    if not flags:
        logger.info(f"No flags in the queue! Submission skipped.")

        socketio.emit('log_event', {
            'message': 'No flags in the queue! Submission skipped.'
        })

        return

    logger.info(st.bold(f"Submitting {len(flags)} flags..."))

    socketio.emit('log_event', {
        'message': f'Submitting {len(flags)} flags...'
    })

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
            to_accept = Flag.select().where(Flag.value.in_([flag for flag in accepted]))
            for flag in to_accept:
                flag.status = 'accepted'
                flag.response = accepted[flag.value]
            Flag.bulk_update(to_accept, fields=[Flag.status, Flag.response])

        if rejected:
            to_reject = Flag.select().where(Flag.value.in_([flag for flag in rejected]))
            for flag in to_reject:
                flag.status = 'rejected'
                flag.response = rejected[flag.value]
            Flag.bulk_update(to_reject, fields=[Flag.status, Flag.response])

        queued_count = Flag.select().where(Flag.status == 'queued').count()
        accepted_count = Flag.select().where(Flag.status == 'accepted').count()
        rejected_count = Flag.select().where(Flag.status == 'rejected').count()

    socketio.emit('submit_complete_event', {
        'message': f'{len(accepted)} flag{"s" if len(accepted) > 1 else ""} accepted, {len(rejected)} rejected.',
        'data': {
            'queued': queued_count,
            'accepted': accepted_count,
            'rejected': rejected_count,
            'acceptedDelta': len(accepted),
            'rejectedDelta': len(rejected)
        }
    })

    socketio.emit('report_event', {
        'report': generate_flags_per_tick_report()
    })

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

    logger.info(f'Started tick {st.bold(str(tick_number))}. ' +
                f'Next tick scheduled for {st.bold(next_tick_start.strftime("%H:%M:%S"))}. ⏱️')


def generate_flags_per_tick_report():
    tick_window = 10
    latest_tick = tick_number  # subtract 1 to ignore last tick
    oldest_tick = max(0, latest_tick - tick_window + 1)  # add 1 to ignore -11th tick

    query = Flag.select(Flag.player, Flag.exploit, Flag.tick, fn.COUNT(Flag.id).alias('flag_count')) \
                .where((Flag.tick >= oldest_tick) & (Flag.tick <= latest_tick) & (Flag.status == 'accepted')) \
                .group_by(Flag.player, Flag.exploit, Flag.tick)
    results = [(result.player, result.exploit, result.tick, result.flag_count) for result in query]

    report = {}
    tick_indices = [i for i in range(oldest_tick, latest_tick + 1)]

    for player, exploit, tick, flag_count in results:
        key = f'{player}-{exploit}'
        if key not in report:
            report[key] = {
                'player': player,
                'exploit': exploit,
                'data': {
                    'ticks': tick_indices,
                    'accepted': [0] * len(tick_indices)
                }
            }

        report[key]['data']['accepted'][tick_indices.index(tick)] = flag_count
    
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
    # Configure templates
    app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'views')

    # Set static path
    app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'static')

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
    serv = st.color("server", "green")
    print(f"""
 ()__              __          _   
 ||  |__          / _| {serv} | |
 ||  |   |____   | |_ __ _ ___| |_ 
 ||  |   |    |  |  _/ _` / __| __|
 ||  |   |    |  | || (_| \__ \ |_ 
 ||''|   |    |  |_| \__,_|___/\__|
 ||  `'''|    |  
 ||      `''''`   Flag Acquisition
 ||   v0.1       and Submission Tool
 ||""")

class FastServerApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == "__main__":
    main()
