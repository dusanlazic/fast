import os
import yaml
import time
import hashlib
import threading
import subprocess
from copy import deepcopy
from itertools import product
from database import fallbackdb
from models import ExploitDetails, FallbackFlag, Partition
from handler import SubmitClient
from util.styler import TextStyler as st
from util.helpers import seconds_from_now
from util.log import logger, create_log_dir
from util.validation import validate_data, validate_targets, connect_schema, exploits_schema
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from apscheduler.schedulers.background import BlockingScheduler

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')


cached_exploits = (None, None)  # (hash, exploits)
handler: SubmitClient = None
connect = {
    'protocol': 'http',  # TODO: Support https
    'host': '127.0.0.1',
    'port': '2023',
    'player': 'anon'
}


def main():
    splash()
    create_log_dir()
    load_config()
    setup_handler()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_exploits,
        trigger='interval',
        seconds=handler.game['tick_duration'],
        id='exploits',
        next_run_time=seconds_from_now(0)
    )

    scheduler.add_job(
        func=enqueue_from_fallback,
        trigger='interval',
        seconds=handler.game['tick_duration'],
        id='fallback_flagstore',
        next_run_time=seconds_from_now(0)
    )

    scheduler.start()


def run_exploits():
    exploits = load_exploits()
    if not exploits:
        logger.info(f'No exploits defined in {st.bold("fast.yaml")}. Skipped.')
        return

    exploits_to_run = []
    for exploit in exploits:
        if not exploit.partition:
            exploits_to_run.append(exploit)
        else:
            exploits_to_run.extend(partition_exploit(exploit))

    for exploit in exploits_to_run:
        threading.Thread(target=run_exploit, args=(exploit,)).start()


def run_exploit(exploit):
    runner_command = ['python', RUNNER_PATH] + \
        exploit.targets + ['--name', exploit.name]
    if exploit.module:
        runner_command.extend(['--module', exploit.module])
    if exploit.run:
        runner_command.extend(['--run', exploit.run])
    if exploit.prepare:
        runner_command.extend(['--prepare', exploit.prepare])
    if exploit.cleanup:
        runner_command.extend(['--cleanup', exploit.cleanup])
    if exploit.timeout:
        runner_command.extend(['--timeout', str(exploit.timeout)])
    if exploit.partitioned is not None:
        runner_command.extend(['--partitioned', str(exploit.partitioned)])
    if exploit.delay:
        time.sleep(exploit.delay)

    parts = f" (part {exploit.part_num}/{exploit.part_total})" if hasattr(exploit, 'part_num') else ""
    logger.info(
        f'Running {st.bold(exploit.name)} {parts} at {st.bold(len(exploit.targets))} target{"s" if len(exploit.targets) > 1 else ""}...')

    subprocess.run(runner_command, text=True, env={
                   **exploit.env, **os.environ})

    logger.info(f'{st.bold(exploit.name)}{parts} finished.')


def enqueue_from_fallback():
    flags = [flag for flag in FallbackFlag.select().where(FallbackFlag.status == 'pending')]
    if flags:
        logger.info(f'Forwarding {len(flags)} flags from the fallback flagstore...')
        handler.enqueue_from_fallback(flags)


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
    run = entry.get('run')
    prepare = entry.get('prepare')
    cleanup = entry.get('cleanup')
    module = None if run else (entry.get('module') or name).replace('.py', '')
    targets = [ip for ip_range in entry['targets'] for ip in expand_ip_range(ip_range)]
    timeout = entry.get('timeout')
    env = entry.get('env') or {}
    delay = entry.get('delay')
    partition = Partition(
        entry['partition'].get('count'),
        entry['partition'].get('size'),
        entry['partition'].get('wait')
    ) if entry.get('partition') else None

    return ExploitDetails(name, targets, module, run, prepare, cleanup, timeout, env, delay, partition)


def partition_exploit(exploit):
    if exploit.partition.count:
        target_partitions = partition_by_count(exploit.targets, exploit.partition.count)
    elif exploit.partition.size:
        target_partitions = partition_by_size(exploit.targets, exploit.partition.size)
    else:
        logger.warning(f'Partition {st.bold("size")} or {st.bold("count")} must be specified when partitioning targets. Fix configuration for {st.bold(exploit.name or exploit.module)}.')
        return [exploit]
    
    exploits = []
    for i, targets in enumerate(target_partitions):
        new_exploit = deepcopy(exploit)
        new_exploit.targets = targets
        new_exploit.delay = (exploit.delay or 0) + i * exploit.partition.wait
        new_exploit.partition = None
        new_exploit.partitioned = 0
        new_exploit.part_num = i + 1
        new_exploit.part_total = len(target_partitions)
        exploits.append(new_exploit)
    
    exploits[0].partitioned = -1
    exploits[-1].partitioned = 1 if len(exploits) > 1 else None

    return exploits


def partition_by_size(targets, size):
    return [targets[i:i + size] for i in range(0, len(targets), size)]


def partition_by_count(targets, count):
    size = len(targets) // count
    remainder = len(targets) % count
    partitions = [targets[i * size : (i + 1) * size] for i in range(count)]
    for i in range(remainder):
        partitions[i].append(targets[count * size + i])
    return partitions


def load_config():
    # Load fast.yaml
    with open('fast.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Load and validate connection config
    logger.info('Loading connection config...')
    connect_data = yaml_data.get('connect')
    if connect_data:
        connect.update(connect_data)

        if not validate_data(connect, connect_schema):
            logger.error(f"Fix errors in {st.bold('connect')} section in {st.bold('fast.yaml')} and rerun.")
            exit(1)

    # Load and validate exploits config
    logger.info('Checking exploits config...')
    exploits_data = yaml_data.get('exploits')
    if not exploits_data:
        logger.warning(f"{st.bold('exploits')} section is missing in {st.bold('fast.yaml')}. Please add {st.bold('exploits')} section to start running exploits in the next tick.")
    elif exploits_data and not validate_data(exploits_data, exploits_schema, custom=validate_targets):
        logger.error(f"Fix errors in {st.bold('exploits')} section in {st.bold('fast.yaml')} and rerun.")
        exit(1)
    
    logger.success('No errors found in exploits config.')


def setup_handler(fire_mode=False):
    global handler

    # Fetch, apply and persist server's game configuration
    logger.info('Fetching game config...')

    if connect.get('password'):
        conn_str = f"{connect['protocol']}://{connect['player']}:***@{connect['host']}:{connect['port']}"
    else:
        conn_str = f"{connect['protocol']}://{connect['host']}:{connect['port']}"

    logger.info(f"Connecting to {st.color(conn_str, 'cyan')}")

    try:
        handler = SubmitClient(connect)

        config_repr = f"{handler.game['tick_duration']}s tick, {handler.game['flag_format']}, {' '.join(handler.game['team_ip'])}"
        logger.success(f'Game configured successfully. — {st.faint(config_repr)}')

        # Synchronize client with server's tick clock
        if not fire_mode:
            handler.sync()
    except HTTPError as e:
        if e.response.status_code == 401:
            error = f'Failed to authenticate with the Fast server. Check the password with your teammates and try again.'
        else:
            error = f'HTTP error occurred while connecting to the Fast server. Status code: {e.response.status_code}, Reason: {e.response.text}'
    except ConnectionError as e:
        error = f'Error connecting to the Fast server at URL {conn_str}. Ensure the server is up and running, your configuration is correct, and your network connection is stable.'
    except Timeout as e:
        error = f"Connection to Fast server has timed out."
    except RequestException as e:
        exception_name = '.'.join([type(e).__module__, type(e).__qualname__])
        error = f"Some unexpected error occurred during connecting to Fast server. — {st.color(exception_name, 'red')}"
    else:
        error = None
    finally:
        if error:
            logger.error(error)
            exit(1)

    # Setup fallback db
    fallbackdb.connect(reuse_if_open=True)
    fallbackdb.create_tables([FallbackFlag])


def splash():
    vers = '0.0.1'
    print(f"""
[34;1m     .___    ____[0m    ______         __ 
[34;1m    /   /\__/   /[0m   / ____/_  ____ / /_  
[34;1m   /   /   /  ❬` [0m  / /_/ __ `/ ___/ __/
[34;1m  /___/   /____\ [0m / __/ /_/ (__  ) /_  
[34;1m /    \___\/     [0m/_/  \__,_/____/\__/  
[34;1m/[0m                      [34mclient[0m [2mv{vers}[0m
""")
