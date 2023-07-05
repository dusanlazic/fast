import os
import sys
import yaml
import time
import hashlib
import threading
import subprocess
from importlib import import_module
from apscheduler.schedulers.background import BlockingScheduler
from util.helpers import seconds_from_now
from util.styler import TextStyler as st
from util.log import logger, create_log_dir
from itertools import product
from database import db
from models import Flag, ExploitDetails

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')

team_ip = ''
tick_number = 0
cached_exploits = (None, None)  # (hash, exploits)


def main():
    global team_ip

    splash()
    setup_database()
    create_log_dir()
    game, submitter = load_config()
    team_ip = game.get('team_ip')

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_exploits,
        trigger='interval',
        seconds=game['tick_duration'],
        id='exploits',
        next_run_time=seconds_from_now(0)
    )

    delay = submitter['tick_start_delay']
    run_every_nth = submitter.get('run_every_nth_tick') or 1
    interval = run_every_nth * game['tick_duration']
    first_run = (run_every_nth - 1) * game['tick_duration'] + delay

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

    submitter_wrapper(submit_func)  # Run submitter to submit queued flags
    scheduler.start()


def run_exploits():
    global tick_number

    logger.info(f'Started tick {st.bold(str(tick_number))}. ⏱️')
    for exploit in load_exploits():
        threading.Thread(target=run_exploit, args=(exploit,)).start()

    tick_number += 1


def run_exploit(exploit):
    runner_command = ['python3', RUNNER_PATH] + \
        exploit.targets + ['--name', exploit.name]
    if exploit.module:
        runner_command.extend(['--module', exploit.module])
    if exploit.cmd:
        runner_command.extend(['--cmd', exploit.cmd])
    if exploit.timeout:
        runner_command.extend(['--timeout', str(exploit.timeout)])
    if exploit.delay:
        time.sleep(exploit.delay)

    logger.info(
        f'Running {st.bold(exploit.name)} at {st.bold(len(exploit.targets))} target{"s" if len(exploit.targets) > 1 else ""}...')

    subprocess.run(runner_command, text=True, env={
                   **exploit.env, **os.environ})

    logger.info(f'{st.bold(exploit.name)} finished.')


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


def load_exploits():
    global cached_exploits

    with open('fast.yaml', 'r') as file:
        digest = hashlib.sha256(file.read().encode()).hexdigest()
        if cached_exploits[0] == digest:
            return cached_exploits[1]

        try:
            file.seek(0)
            logger.info('Reloading exploits...')
            data = yaml.safe_load(file)
            exploits = [parse_exploit_entry(exploit)
                        for exploit in data['exploits']]
            logger.success(f'Loaded {st.bold(len(exploits))} exploits.')
            cached_exploits = (digest, exploits)
            return exploits
        except Exception as e:
            logger.error(
                f'Failed to load new {st.bold("fast.yaml")} file. Reusing the old configuration.')
            return cached_exploits[1]


def expand_ip_range(ip_range):
    octets = ip_range.split('.')
    ranges = [list(range(int(octet.split('-')[0]), int(octet.split('-')[1]) + 1))
              if '-' in octet else [int(octet)] for octet in octets]
    return ['.'.join(map(str, octets)) for octets in product(*ranges)]


def parse_exploit_entry(entry):
    name = entry.get('name')
    cmd = entry.get('cmd')
    module = None if cmd else (entry.get('module') or name).replace('.py','')
    targets = [ip for ip_range in entry['targets']
               for ip in expand_ip_range(ip_range) if ip != team_ip]
    timeout = entry.get('timeout')
    env = entry.get('env') or {}
    delay = entry.get('delay')

    return ExploitDetails(name, targets, module, cmd, timeout, env, delay)


def load_config():
    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        logger.success(f'Fast configured successfully.')

        return data['game'], data['submitter']


def setup_database():
    db.connect()
    db.create_tables([Flag])
    Flag.add_index(Flag.value)
    logger.success('Database connected.')


def splash():
    print("""
 ()__              __          _   
 ||  |__          / _|        | |  
 ||  |   |____   | |_ __ _ ___| |_ 
 ||  |   |    |  |  _/ _` / __| __|
 ||  |   |    |  | || (_| \__ \ |_ 
 ||''|   |    |  |_| \__,_|___/\__|
 ||  `'''|    |  
 ||      `''''`   Flag Acquisition
 ||   v0.1       and Submission Tool
 ||""")
