import os
import yaml
import time
import hashlib
import threading
import subprocess
from itertools import product
from models import ExploitDetails
from submit_handler import SubmitClient
from datetime import datetime, timedelta
from util.styler import TextStyler as st
from util.helpers import seconds_from_now
from util.log import logger, create_log_dir
from util.validation import validate_data, validate_targets, connect_schema, exploits_schema
from apscheduler.schedulers.background import BlockingScheduler

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')


cached_exploits = (None, None)  # (hash, exploits)
config = {
    'connect': {
        'host': '127.0.0.1',
        'port': '2023',
        'player': 'anon'
    },
    'game': {}
}


def main():
    splash()
    create_log_dir()
    load_config()
    sync()

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
    exploits = load_exploits()
    if not exploits:
        logger.info(f'No exploits defined in {st.bold("fast.yaml")}. Skipped.')
        return

    for exploit in exploits:
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
            yaml_data = yaml.safe_load(file)

            exploits_data = yaml_data.get('exploits')
            if not exploits_data:
                logger.warning(f"'exploits' section is missing in {st.bold('fast.yaml')}. Please add 'exploits' section to start running exploits in the next tick.")
                return

            if not validate_data(exploits_data, exploits_schema, custom=validate_targets):
                if cached_exploits[1]:
                    logger.error(
                    f"Errors found in 'exploits' section in {st.bold('fast.yaml')}. The previous configuration will be reused in the following tick.")
                else:
                    logger.error(
                    f"Errors found in 'exploits' section in {st.bold('fast.yaml')}. Please fix the errors to start running exploits in the next tick.")
                
                return cached_exploits[1]
            
            exploits = [parse_exploit_entry(exploit)
                        for exploit in yaml_data['exploits']]
            logger.success(f'Loaded {st.bold(len(exploits))} exploits.')
            cached_exploits = (digest, exploits)
            return exploits
        except Exception as e:
            if cached_exploits[1]:
                logger.error(
                f"Failed to load exploits from the new {st.bold('fast.yaml')} file. The previous configuration will be reused in the following tick.")
            else:
                logger.error(
                f"Failed to load exploits from the new {st.bold('fast.yaml')} file. Please fix the errors to start running exploits in the next tick.")
            
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
    # Load fast.yaml
    with open('fast.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Load and validate connection config
    logger.info('Loading connection config...')
    connect_data = yaml_data.get('connect')
    if connect_data:
        config['connect'].update(connect_data)

        if not validate_data(connect_data, connect_schema):
            logger.error(f"Fix errors in {st.bold('connect')} section in {st.bold('fast.yaml')} and rerun.")
            exit(1)

    # Load and validate exploits config
    exploits_data = yaml_data.get('exploits')
    if not exploits_data:
        print(exploits_data)
        logger.warning(f"{st.bold('exploits')} section is missing in {st.bold('fast.yaml')}. Please add {st.bold('exploits')} section to start running exploits in the next tick.")
    elif exploits_data and not validate_data(exploits_data, exploits_schema, custom=validate_targets):
        logger.error(f"Fix errors in {st.bold('exploits')} section in {st.bold('fast.yaml')} and rerun.")
        exit(1)  
    
    # Fetch game config from server
    logger.info('Fetching game config...')
    game_data = SubmitClient(
        host=config['connect']['host'],
        port=config['connect']['port']
    ).get_game_config(force_fetch=True)

    # Update game config
    config['game'].update(game_data)

    logger.success(f'Fast client configured successfully.')
    return config


def sync():
    connect = config['connect']
    sync_data = SubmitClient(
        host=connect['host'],
        port=connect['port']
    ).sync()

    wait_until = datetime.now() + timedelta(seconds=sync_data['next_delta'])
    logger.info(f'Synchronizing with the server... Tick will start at {st.bold(wait_until.strftime("%H:%M:%S"))}.')
    time.sleep(sync_data['next_delta'])


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
