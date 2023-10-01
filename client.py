import os
import yaml
import time
import hashlib
import threading
import subprocess
from copy import deepcopy
from itertools import product
from database import fallbackdb
from models import ExploitDetails, FallbackFlag, Batching
from handler import SubmitClient
from util.styler import TextStyler as st
from util.helpers import seconds_from_now
from util.log import logger, create_log_dir
from util.validation import validate_data, validate_targets, connect_schema, exploits_schema
from util.hosts import process_targets
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from apscheduler.schedulers.background import BlockingScheduler

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')


cached_exploits = (None, None)  # (hash, exploits)
handler: SubmitClient = None
connect = {
    'protocol': 'http',
    'host': '127.0.0.1',
    'port': 2023,
    'player': 'anon'
}


def main():
    banner()
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

    for exploit in exploits:
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
    if exploit.batching:
        runner_command.extend(['--batch-wait', str(exploit.batching.wait)])

        if exploit.batching.count:
            runner_command.extend(['--batch-count', str(exploit.batching.count)])
        elif exploit.batching.size:
            runner_command.extend(['--batch-size', str(exploit.batching.size)])
    if exploit.delay:
        time.sleep(exploit.delay)

    logger.info(
        f'Running {st.bold(exploit.name)} at {st.bold(len(exploit.targets))} target{"s" if len(exploit.targets) > 1 else ""}...')

    subprocess.run(runner_command, text=True, env={
                   **exploit.env, **os.environ})

    logger.info(f'{st.bold(exploit.name)} finished.')


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

            exploits_data = yaml_data.get('exploits', 'MISSING')
            if exploits_data == 'MISSING':
                logger.warning(f"{st.bold('exploits')} section is missing in {st.bold('fast.yaml')}. Please add {st.bold('exploits')} section to start running exploits in the next tick.")
                return
            elif exploits_data == None:
                logger.warning(f"{st.bold('exploits')} section contains no exploits. Please add your exploits to start running them in the next tick.")
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


def parse_exploit_entry(entry):
    name = entry.get('name')
    run = entry.get('run')
    prepare = entry.get('prepare')
    cleanup = entry.get('cleanup')
    module = None if run else (entry.get('module') or name).replace('.py', '')
    targets = process_targets(entry['targets'])
    timeout = entry.get('timeout')
    env = entry.get('env') or {}
    delay = entry.get('delay')
    batching = Batching(
        entry['batches'].get('count'),
        entry['batches'].get('size'),
        entry['batches'].get('wait')
    ) if entry.get('batches') else None

    return ExploitDetails(name, targets, module, run, prepare, cleanup, timeout, env, delay, batching)


def load_config():
    # Load fast.yaml
    if not os.path.isfile('fast.yaml'):
        logger.error(f"{st.bold('fast.yaml')} not found in the current working directory. Exiting...")
        exit(1)

    with open('fast.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    if not yaml_data:
        logger.error(f"{st.bold('fast.yaml')} is empty. Exiting...")
        exit(1)

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
    exploits_data = yaml_data.get('exploits', 'MISSING')
    if exploits_data == 'MISSING':
        logger.warning(f"{st.bold('exploits')} section is missing in {st.bold('fast.yaml')}. Please add {st.bold('exploits')} section to start running exploits in the next tick.")
    elif exploits_data == None:
        logger.warning(f"{st.bold('exploits')} section contains no exploits. Please add your exploits to start running them in the next tick.")
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


def banner():
    vers = '1.1.0-dev'
    print(f"""
\033[34;1m     .___    ____\033[0m    ______         __ 
\033[34;1m    /   /\__/   /\033[0m   / ____/_  ____ / /_  
\033[34;1m   /   /   /  ❬` \033[0m  / /_/ __ `/ ___/ __/
\033[34;1m  /___/   /____\ \033[0m / __/ /_/ (__  ) /_  
\033[34;1m /    \___\/     \033[0m/_/  \__,_/____/\__/  
\033[34;1m/\033[0m""" + f"\033[34mclient\033[0m \033[2mv{vers}\033[0m".rjust(52) + "\n")
