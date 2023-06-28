import subprocess
import time
import threading
import os
from util.styler import TextStyler as st
from util.log import logger
from itertools import product

TICK_DURATION = 10
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')


def main():
    splash()
    tick_counter = 0

    exploits = load_exploits()

    while True:
        logger.info(f'Started tick {st.bold(tick_counter)} ⌛')
        for exploit in exploits:
            threading.Thread(target=run_exploit, args=exploit).start()

        time.sleep(TICK_DURATION)
        tick_counter += 1


def run_exploit(exploit, targets):
    logger.info(f'Running {st.bold(exploit)} at {st.bold(len(targets))} target{"s" if len(targets) > 1 else ""}')

    subprocess.run(
        ['python3', RUNNER_PATH, '--exploit', exploit] + targets, text=True)

    logger.info(f'{st.bold(exploit)} finished.')


def load_exploits():
    logger.info('Loading exploits...')
    with open('exploits.txt', 'r') as file:
        exploits = [parse_exploit_entry(line) for line in file.readlines()]
        logger.success(f'Loaded {len(exploits)} exploits')
        return exploits


def expand_ip_range(ip_range):
    octets = ip_range.split('.')
    ranges = [list(range(int(octet.split('-')[0]), int(octet.split('-')[1]) + 1))
              if '-' in octet else [int(octet)] for octet in octets]
    return ['.'.join(map(str, octets)) for octets in product(*ranges)]


def parse_exploit_entry(line):
    parts = line.split()
    exploit = parts[0]
    ips = [ip for ip_range in parts[1:] for ip in expand_ip_range(ip_range)]
    return (exploit, ips)


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
