import subprocess
import time
import threading
import os
import yaml
from util.helpers import incrs
from util.styler import TextStyler as st
from util.log import logger
from itertools import product
from database import db
from models import Flag

config = []
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')
env = os.environ.copy()

def main():
    splash()
    load_config()
    setup_database()
    exploits = load_exploits()

    env["TICK_NUMBER"] = '0'

    while True:
        logger.info(f'Started tick {st.bold(env["TICK_NUMBER"])}. ⌛')
        for exploit in exploits:
            threading.Thread(target=run_exploit, args=exploit).start()

        time.sleep(config['tick_duration'])
        env["TICK_NUMBER"] = incrs(env["TICK_NUMBER"])


def run_exploit(name, cmd, targets):
    runner_command = ['python3', RUNNER_PATH] + targets + ['--exploit', name]
    if cmd:
        runner_command.extend(['--cmd', cmd])

    logger.info(
        f'Running {st.bold(name)} at {st.bold(len(targets))} target{"s" if len(targets) > 1 else ""}...')

    subprocess.run(runner_command, text=True, env=env)

    logger.info(f'{st.bold(name)} finished.')


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
    ips = [ip for ip_range in entry['targets']
           for ip in expand_ip_range(ip_range)]

    return (name, cmd, ips)


def load_config():
    global config

    logger.info('Configuring...')
    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        config = data['config']
        logger.success(f'Fast configured successfully.')


def setup_database():
    db.connect()
    db.create_tables([Flag])


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
