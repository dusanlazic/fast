import os
import sys
import json
import yaml
from importlib import import_module
from bottle import Bottle, request, response
from apscheduler.schedulers.background import BackgroundScheduler
from models import Flag
from database import db
from util.log import logger
from util.styler import TextStyler as st
from util.helpers import seconds_from_now

app = Bottle()


def main():
    setup_database()
    game, submitter, server = load_config()

    delay = submitter['delay']
    run_every_nth = submitter.get('run_every_nth_tick') or 1
    interval = run_every_nth * game['tick_duration']
    first_run = (run_every_nth - 1) * game['tick_duration'] + delay

    sys.path.append(os.getcwd())
    module = import_module(submitter.get('module') or 'submitter')
    submit_func = getattr(module, 'submit')

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=submitter_wrapper,
        args=(submit_func,),
        trigger='interval',
        seconds=interval,
        id='submitter',
        next_run_time=seconds_from_now(first_run)
    )

    submitter_wrapper(submit_func)  # Run submitter to submit queued flags
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
            logger.success((f"{st.bold(1)} flag " if len(new_flags) == 1 else f"{st.bold(len(new_flags))} flags ") +
                        f"received from {st.bold(exploit_name)} by {st.bold(player)} after owning {st.bold(target_ip)}. 🚩")

    response.content_type = 'application/json'
    return json.dumps({
        'duplicates': duplicate_flags,
        'new':  new_flags,
        'flags_in_queue': Flag.select().where(Flag.status == 'queued').count()
    })


@app.route('/queue-size', method='GET')
def get_queue_size():
    return json.dumps({
        'flags_in_queue': Flag.select().where(Flag.status == 'queued').count()
    })


@app.route('/stats', method='GET')
def get_stats():
    return json.dumps({
        'queued': Flag.select().where(Flag.status == 'queued').count(),
        'accepted': Flag.select().where(Flag.status == 'accepted').count(),
        'rejected': Flag.select().where(Flag.status == 'rejected').count()
    })


@app.route('/trigger-submit', method='POST')
def trigger_submit():
    _, submitter, _ = load_config()

    sys.path.append(os.getcwd())
    module = import_module(submitter.get('module') or 'submitter')
    submit_func = getattr(module, 'submit')

    submitter_wrapper(submit_func)

    # TODO: Improve interactivity
    return json.dumps({
        'message': 'Flags submitted. (WIP)'
    })


@app.route('/health', method='GET')
def test():
    return json.dumps({
        'message': 'Hello from Fast submitter server!'
    })


def submitter_wrapper(submit):
    flags = [flag.value for flag in
             Flag.select().where(Flag.status == 'queued')]

    if not flags:
        logger.info(f"No flags in the queue! Submission skipped.")
        return

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


def load_config():
    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        logger.success(f'Fast Bottle server configured successfully.')

        return data['game'], data['submitter'], data['server']


def splash():
    print("""
 ()__              __          _   
 ||  |__          / _|        | |  
 ||  |   |____   | |_ __ _ ___| |_ 
 ||  | s |    |  |  _/ _` / __| __|
 ||  | e | rv |  | || (_| \__ \ |_ 
 ||''|   | er |  |_| \__,_|___/\__|
 ||  `'''|    |  
 ||      `''''`   Flag Acquisition
 ||   v0.1       and Submission Tool
 ||""")


if __name__ == "__main__":
    main()
