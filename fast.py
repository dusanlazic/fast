import subprocess
import time
import threading
import sys
from util.styler import TextStyler as st
from util.log import logger
from itertools import product

EXPLOITS_FILE = 'exploits.txt'
TICK_DURATION = 10


def main():
    tick_counter = 0

    exploits = load_exploits()

    while True:
        logger.info(f'Started tick {st.bold(tick_counter)} ⌛')
        for exploit in exploits:
            threading.Thread(target=run_exploit, args=exploit).start()

        time.sleep(TICK_DURATION)
        tick_counter += 1


def run_exploit(exploit, targets):
    logger.info(f'Running {st.bold(exploit)} at {st.bold(len(targets))} targets')

    subprocess.run(
        ['python3', 'runner.py', '--exploit', exploit] + targets, text=True)

    logger.info(f'Exploit {exploit} finished.')


def load_exploits():
    logger.info('Loading exploits...')
    with open(EXPLOITS_FILE, 'r') as file:
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


def ascii():
    print("""
 ()__              __          _   
 ||  |__          / _|        | |  
 ||--|   |____   | |_ __ _ ___| |_ 
 ||--|---|    |  |  _/ _` / __| __|
 ||  |---|----|  | || (_| \__ \ |_ 
 ||''|   |----|  |_| \__,_|___/\__|
 ||  `'''|    |  
 ||      `''''`   Flag Acquisition
 ||              and Submission Tool
 ||""")


if __name__ == '__main__':
    ascii()
    main()
