import os
import sys
import yaml
import logging
import functools
from importlib import import_module
from datetime import datetime, timedelta
from flask import Flask, request, render_template
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler
from models import Flag
from database import db
from util.log import logger
from util.styler import TextStyler as st
from util.helpers import seconds_from_now, truncate, deep_update
from util.validation import validate_data, validate_delay, server_yaml_schema

app = Flask(__name__)
auth = HTTPBasicAuth()
socketio = SocketIO(app)

tick_number = 0
tick_start = datetime.max
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
    }
}


def main():
    splash()
    setup_database()
    configure_flask()
    load_config()

    game, submitter, server = config['game'], config['submitter'], config['server']

    # Schedule tick clock

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=tick_clock,
        trigger='interval',
        seconds=game['tick_duration'],
        id='clock',
        next_run_time=seconds_from_now(0)
    )

    # Schedule flag submitting

    delay = submitter['delay']
    run_every_nth = submitter['run_every_nth_tick']
    interval = run_every_nth * game['tick_duration']
    first_run = (run_every_nth - 1) * game['tick_duration'] + delay

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
        next_run_time=seconds_from_now(first_run)
    )

    # Run scheduler and Flask server

    scheduler.start()

    socketio.run(
        app,
        host=server['host'],
        port=server['port']
    )


@auth.verify_password
def authenticate(username, password):
    return password == config['server']['password']


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

    with db.atomic():
        duplicate_flags = [flag.value for flag in Flag.select().where(
            Flag.value.in_(flags))]
        new_flags = [flag for flag in flags if flag not in duplicate_flags]

        if new_flags:
            Flag.bulk_create([Flag(value=flag, exploit=exploit, target=target, tick=tick_number,
                                   player=player, status='queued') for flag in new_flags])
    
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

    return dict({
        'duplicates': duplicate_flags,
        'new':  new_flags
    })


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

    return dict({
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
    })


@app.route('/config')
@basic
def get_config():
    player = request.args['player']
    address = request.remote_addr

    socketio.emit('log_event', {
        'message': f'{player} has connected from {address}.'
    })

    return dict(config)


@app.route('/trigger-submit', methods=['POST'])
@basic
def trigger_submit():
    logger.info(f"Submitter triggered manually by {st.bold(request.json['player'])}.")
    submitter_wrapper(submit_func)

    # TODO: Improve interactivity
    return dict({
        'message': 'Flags submitted.'
    })


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

    queued_count_st = st.color(
        st.bold(queued_count), 'green') if queued_count == 0 else st.bold(queued_count)

    accepted_count_st = st.color(st.bold(
        accepted_count), 'green') if accepted_count > 0 else st.color(st.bold(accepted_count), 'yellow')

    rejected_count_st = st.color(st.bold(
        rejected_count), 'green') if rejected_count == 0 else st.color(st.bold(rejected_count), 'yellow')

    logger.info(
        f"{st.bold('Stats')} — {queued_count_st} queued, {accepted_count_st} accepted, {rejected_count_st} rejected.")


def setup_database():
    db.connect()
    db.create_tables([Flag])
    Flag.add_index(Flag.value)
    logger.success('Database connected.')


def tick_clock():
    global tick_number, tick_start

    tick_start = datetime.now()
    next_tick_start = tick_start + \
        timedelta(seconds=config['game']['tick_duration'])

    logger.info(f'Started tick {st.bold(str(tick_number))}. ' +
                f'Next tick scheduled for {st.bold(next_tick_start.strftime("%H:%M:%S"))}. ⏱️')

    tick_number += 1


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


if __name__ == "__main__":
    main()
