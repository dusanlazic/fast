import os
import sys
import yaml
from importlib import import_module
from datetime import datetime, timedelta
from bottle import Bottle, request, response
from apscheduler.schedulers.background import BackgroundScheduler
from models import Flag
from database import db
from util.log import logger
from util.styler import TextStyler as st
from util.helpers import seconds_from_now, truncate

app = Bottle()

tick_number = 0
tick_start = datetime.max
submit_func = None

config = {
    'game': None,
    'submitter': None,
    'server': None
}


def main():
    splash()
    setup_database()
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
    run_every_nth = submitter.get('run_every_nth_tick') or 1
    interval = run_every_nth * game['tick_duration']
    first_run = (run_every_nth - 1) * game['tick_duration'] + delay

    global submit_func
    sys.path.append(os.getcwd())
    module = import_module(submitter.get('module') or 'submitter')
    submit_func = getattr(module, 'submit')

    scheduler.add_job(
        func=submitter_wrapper,
        args=(submit_func,),
        trigger='interval',
        seconds=interval,
        id='submitter',
        next_run_time=seconds_from_now(first_run)
    )

    # Run scheduler and Bottle server

    scheduler.start()

    app.run(
        host=server.get('host') or '0.0.0.0',
        port=server.get('port') or 2023,
        quiet=True
    )


@app.route('/enqueue', method='POST')
def enqueue():
    flags = request.json['flags']
    exploit_name = request.json['exploit_name']
    target_ip = request.json['target_ip']
    player = request.json['player']

    with db.atomic():
        duplicate_flags = [flag.value for flag in Flag.select().where(
            Flag.value.in_(flags))]
        new_flags = [flag for flag in flags if flag not in duplicate_flags]

        if new_flags:
            Flag.bulk_create([Flag(value=flag, exploit_name=exploit_name, target_ip=target_ip,
                                   status='queued') for flag in new_flags])
            logger.success(f"{st.bold(player)} retrieved " +
                           (f"{st.bold(1)} flag " if len(new_flags) == 1 else f"{st.bold(len(new_flags))} flags ") + 
                           f"from {st.bold(target_ip)} using {st.bold(exploit_name)}. 🚩  — {st.faint(truncate(' '.join(new_flags), 50))}")

    return dict({
        'duplicates': duplicate_flags,
        'new':  new_flags,
        'flags_in_queue': Flag.select().where(Flag.status == 'queued').count()
    })


@app.route('/sync', method='GET')
def sync():
    now: datetime = datetime.now()
    next_tick_start: datetime = tick_start + \
        timedelta(seconds=config['game']['tick_duration'])

    return dict({
        'number': tick_number,
        'this_timestamp': tick_start.timestamp(),
        'next_timestamp': next_tick_start.timestamp(),
        'this_delta': (now - tick_start).total_seconds(),
        'next_delta': (next_tick_start - now).total_seconds()
    })


@app.route('/game', method='GET')
def get_game_config():
    return dict(config['game'])


@app.route('/stats', method='GET')
def get_stats():
    return dict({
        'queued': Flag.select().where(Flag.status == 'queued').count(),
        'accepted': Flag.select().where(Flag.status == 'accepted').count(),
        'rejected': Flag.select().where(Flag.status == 'rejected').count()
    })


@app.route('/trigger-submit', method='POST')
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
        return

    logger.info(st.bold(f"Submitting {len(flags)} flags..."))

    # TODO: Track more statues (duplicate flag, old flag, etc.)
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
            to_accept = Flag.select().where(Flag.value.in_(accepted))
            for flag in to_accept:
                flag.status = 'accepted'
            Flag.bulk_update(to_accept, fields=[Flag.status])

        if rejected:
            to_decline = Flag.select().where(Flag.value.in_(rejected))
            for flag in to_decline:
                flag.status = 'rejected'
            Flag.bulk_update(to_decline, fields=[Flag.status])

        queued_count = Flag.select().where(Flag.status == 'queued').count()
        accepted_count = Flag.select().where(Flag.status == 'accepted').count()
        rejected_count = Flag.select().where(Flag.status == 'rejected').count()

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


def load_config():
    global config

    with open('server.yaml', 'r') as file:
        config = yaml.safe_load(file)
        # TODO: Validate configuration

        if type(config['game']['team_ip']) != list:
            config['game']['team_ip'] = [config['game']['team_ip']]

        connect_string = st.color(
            f'http://{config["server"]["host"]}:{config["server"]["port"]}', 'green')

        logger.success(f'Fast server configured successfully.')
        logger.info(f'Server will run at {connect_string}.')


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