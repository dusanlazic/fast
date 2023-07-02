import subprocess
import threading
import os
import yaml
from apscheduler.schedulers.background import BlockingScheduler
from util.helpers import seconds_from_now
from util.styler import TextStyler as st
from util.log import logger, create_log_dir
from itertools import product
from database import db
from models import Flag, ExploitDetails

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')

tick_number = 0


def main():
    splash()
    setup_database()
    create_log_dir()
    game, submitter = load_config()
    exploits = load_exploits()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_exploits,
        args=(exploits,),
        trigger='interval',
        seconds=game['tick_duration'],
        id='exploits',
        next_run_time=seconds_from_now(0)
    )

    delay = submitter['tick_start_delay']
    run_every_nth = submitter.get('run_every_nth_tick') or 1
    interval = run_every_nth * game['tick_duration']
    first_run = (run_every_nth - 1) * game['tick_duration'] + delay

    scheduler.add_job(
        func=run_submitter,
        trigger='interval',
        seconds=interval,
        id='submitter',
        next_run_time=seconds_from_now(first_run)
    )
    
    scheduler.start()


def run_exploits(exploits):
    global tick_number

    logger.info(f'Started tick {st.bold(str(tick_number))}. ⏱️')
    for exploit in exploits:
        threading.Thread(target=run_exploit, args=(exploit,)).start()

    tick_number += 1


def run_submitter():
    logger.debug("Running submitter...")


def run_exploit(exploit):
    runner_command = ['python3', RUNNER_PATH] + \
        exploit.targets + ['--exploit', exploit.name]
    if exploit.cmd:
        runner_command.extend(['--cmd', exploit.cmd])
    if exploit.timeout:
        runner_command.extend(['--timeout', str(exploit.timeout)])

    logger.info(
        f'Running {st.bold(exploit.name)} at {st.bold(len(exploit.targets))} target{"s" if len(exploit.targets) > 1 else ""}...')

    subprocess.run(runner_command, text=True, env={
                   **exploit.env, **os.environ})

    logger.info(f'{st.bold(exploit.name)} finished.')


def load_exploits():
    logger.info('Loading exploits...')
    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        exploits = [parse_exploit_entry(exploit)
                    for exploit in data['exploits']]
        logger.success(f'Loaded {len(exploits)} exploits.')
        return exploits


def expand_ip_range(ip_range):
    octets = ip_range.split('.')
    ranges = [list(range(int(octet.split('-')[0]), int(octet.split('-')[1]) + 1))
              if '-' in octet else [int(octet)] for octet in octets]
    return ['.'.join(map(str, octets)) for octets in product(*ranges)]


def parse_exploit_entry(entry):
    name = entry.get('name')
    cmd = entry.get('cmd')
    targets = [ip for ip_range in entry['targets']
               for ip in expand_ip_range(ip_range)]
    timeout = entry.get('timeout')
    env = entry.get('env') or {}

    return ExploitDetails(name, targets, cmd, timeout, env)


def load_config():
    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        logger.success(f'Fast configured successfully.')

        return data['game'], data['submitter']


def setup_database():
    db.connect()
    db.create_tables([Flag])
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
