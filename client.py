import os
import yaml
import time
import hashlib
import threading
import subprocess
from itertools import product
from models import ExploitDetails
from submit_handler import SubmitClient
from util.styler import TextStyler as st
from util.helpers import seconds_from_now
from util.log import logger, create_log_dir
from apscheduler.schedulers.background import BlockingScheduler

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')


cached_exploits = (None, None)  # (hash, exploits)
config = {
    'connect': None,
    'game': None
}


def main():
    splash()
    create_log_dir()
    load_config()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_exploits,
        trigger='interval',
        seconds=config['game']['tick_duration'],
        id='exploits',
        next_run_time=seconds_from_now(0)
    )

    scheduler.start()


def run_exploits():
    for exploit in load_exploits():
        threading.Thread(target=run_exploit, args=(exploit,)).start()


def run_exploit(exploit):
    runner_command = ['python', RUNNER_PATH] + \
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
    module = None if cmd else (entry.get('module') or name).replace('.py', '')
    targets = [ip for ip_range in entry['targets']
               for ip in expand_ip_range(ip_range) if ip not in config['game']['team_ip']]
    timeout = entry.get('timeout')
    env = entry.get('env') or {}
    delay = entry.get('delay')

    return ExploitDetails(name, targets, module, cmd, timeout, env, delay)


def load_config():
    global config

    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
    
    logger.success(f'Local config loaded.')
    logger.info(f'Fetching game config...')

    connect = data['connect']
    game = SubmitClient(
        host=connect['host'],
        port=connect['port'],
        player=connect['player']
    ).get_game_config(force_fetch=True)

    logger.success(f'Game config fetched.')

    config = {
        'connect': connect,
        'game': game
    }

    logger.success(f'Fast client configured successfully.')
    return config


def splash():
    clie = st.color("client", "cyan")
    print(f"""
 ()__              __          _   
 ||  |__          / _| {clie} | |  
 ||  |   |____   | |_ __ _ ___| |_ 
 ||  |   |    |  |  _/ _` / __| __|
 ||  |   |    |  | || (_| \__ \ |_ 
 ||''|   |    |  |_| \__,_|___/\__|
 ||  `'''|    |  
 ||      `''''`   Flag Acquisition
 ||   v0.1       and Submission Tool
 ||""")
