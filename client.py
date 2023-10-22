import os
import yaml
import time
import socket
import hashlib
import requests
import threading
import subprocess
from database import sqlite_db
from models import ExploitDefinition, FallbackFlag, Attack, Batching, DigestValuePair
from handler import SubmitClient
from util.styler import TextStyler as st
from util.helpers import seconds_from_now
from util.log import logger, create_log_dir
from util.validation import validate_data, validate_targets, connect_schema, listener_schema, exploits_schema
from util.hosts import process_targets
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from apscheduler.schedulers.background import BlockingScheduler

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = os.path.join(DIR_PATH, 'runner.py')

prev_exploit_defs = DigestValuePair(digest=None, value=None)
prev_teams_json_digest = None

handler: SubmitClient = None
connect = {
    'protocol': 'http',
    'host': '127.0.0.1',
    'port': 2023,
    'player': 'anon'
}
listener = {
    'host': '127.0.0.1',
    'port': 21000
}


def main():
    banner()
    create_log_dir()
    create_dot_dir()
    load_config()
    start_socket_listener()
    setup_handler()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=begin_tick,
        trigger='interval',
        seconds=handler.game['tick_duration'],
        id='tick',
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


def begin_tick():
    exploit_defs = load_exploit_definitions()
    if not exploit_defs:
        logger.info(f'No exploits defined in {st.bold("fast.yaml")}. Skipped.')
        return

    fetch_teams_json()

    for e in exploit_defs:
        threading.Thread(target=start_runner, args=(e,)).start()


def start_runner(exploit: ExploitDefinition, immediately=False):
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
            runner_command.extend(
                ['--batch-count', str(exploit.batching.count)])
        elif exploit.batching.size:
            runner_command.extend(['--batch-size', str(exploit.batching.size)])
    if exploit.delay and not immediately:
        time.sleep(exploit.delay)

    subprocess.run(runner_command, text=True, env={
                   **exploit.env, **os.environ})

    logger.info(f'{st.bold(exploit.name)} finished.')


def enqueue_from_fallback():
    flags = [flag for flag in FallbackFlag.select().where(
        FallbackFlag.status == 'pending')]
    if flags:
        logger.info(
            f'Forwarding {len(flags)} flags from the fallback flagstore...')
        handler.enqueue_from_fallback(flags)


def load_exploit_definitions():
    global prev_exploit_defs

    with open('fast.yaml', 'r') as file:
        digest = hashlib.md5(file.read().encode()).hexdigest()
        if prev_exploit_defs.digest == digest:
            return prev_exploit_defs.value

        try:
            file.seek(0)
            logger.info('Reloading exploits...')
            yaml_data = yaml.safe_load(file)

            exploits_data = yaml_data.get('exploits', 'MISSING')
            if exploits_data == 'MISSING':
                logger.warning(
                    f"{st.bold('exploits')} section is missing in {st.bold('fast.yaml')}. Please add {st.bold('exploits')} section to start running exploits in the next tick.")
                return
            elif exploits_data == None:
                logger.warning(
                    f"{st.bold('exploits')} section contains no exploits. Please add your exploits to start running them in the next tick.")
                return

            if not validate_data(exploits_data, exploits_schema, custom=validate_targets):
                if prev_exploit_defs.value:
                    logger.error(
                        f"Errors found in 'exploits' section in {st.bold('fast.yaml')}. The previous configuration will be reused in the following tick.")
                else:
                    logger.error(
                        f"Errors found in 'exploits' section in {st.bold('fast.yaml')}. Please fix the errors to start running exploits in the next tick.")

                return prev_exploit_defs.value

            exploits_defs = [parse_exploit_definition(exploit)
                             for exploit in yaml_data['exploits']]
            logger.success(f'Loaded {st.bold(len(exploits_defs))} exploits.')
            prev_exploit_defs = DigestValuePair(digest, exploits_defs)
            return exploits_defs
        except Exception as e:
            if prev_exploit_defs.value:
                logger.error(
                    f"Failed to load exploits from the new {st.bold('fast.yaml')} file. The previous configuration will be reused in the following tick.")
            else:
                logger.error(
                    f"Failed to load exploits from the new {st.bold('fast.yaml')} file. Please fix the errors to start running exploits in the next tick.")

            print(e.with_traceback())

            return prev_exploit_defs.value


def parse_exploit_definition(entry):
    name = entry.get('name')
    run = entry.get('run')
    prepare = entry.get('prepare')
    cleanup = entry.get('cleanup')
    module = None if run else (entry.get('module') or name).replace('.py', '')
    targets = process_targets(
        entry['targets']) if entry.get('targets') else ['auto']
    timeout = entry.get('timeout')
    env = entry.get('env') or {}
    delay = entry.get('delay')
    batching = Batching(
        entry['batches'].get('count'),
        entry['batches'].get('size'),
        entry['batches'].get('wait')
    ) if entry.get('batches') else None

    return ExploitDefinition(name, targets, module, run, prepare, cleanup, timeout, env, delay, batching)


def load_config():
    # Load fast.yaml
    if not os.path.isfile('fast.yaml'):
        logger.error(
            f"{st.bold('fast.yaml')} not found in the current working directory. Exiting...")
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
            logger.error(
                f"Fix errors in {st.bold('connect')} section in {st.bold('fast.yaml')} and rerun.")
            exit(1)

    logger.info('Loading listener config...')
    listener_data = yaml_data.get('listener')
    if listener_data:
        listener.update(listener_data)

        if not validate_data(listener, listener_schema):
            logger.error(
                f"Fix errors in {st.bold('listener')} section in {st.bold('fast.yaml')} and rerun.")
            exit(1)

    # Load and validate exploits config
    logger.info('Checking exploits config...')
    exploits_data = yaml_data.get('exploits', 'MISSING')
    if exploits_data == 'MISSING':
        logger.warning(
            f"{st.bold('exploits')} section is missing in {st.bold('fast.yaml')}. Please add {st.bold('exploits')} section to start running exploits in the next tick.")
    elif exploits_data == None:
        logger.warning(
            f"{st.bold('exploits')} section contains no exploits. Please add your exploits to start running them in the next tick.")
    elif exploits_data and not validate_data(exploits_data, exploits_schema, custom=validate_targets):
        logger.error(
            f"Fix errors in {st.bold('exploits')} section in {st.bold('fast.yaml')} and rerun.")
        exit(1)

    logger.success('No errors found in exploits config.')


def setup_handler():
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
        logger.success(
            f'Game configured successfully. — {st.faint(config_repr)}')

        # Synchronize client with server's tick clock
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
    sqlite_db.connect(reuse_if_open=True)
    sqlite_db.create_tables([FallbackFlag, Attack])


def start_socket_listener():
    threading.Thread(target=listen_for_commands, daemon=True).start()


def listen_for_commands():
    host = listener['host']
    port = listener['port']

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    logger.success(
        f"Socket server is listening for commands on {st.color(f'{host}:{port}', 'cyan')}...")

    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(
            target=handle_command, args=(conn, addr))
        client_thread.start()


def handle_command(conn, addr):
    with conn:
        logger.info(f"Connection with {addr} established.")
        while True:
            command = conn.recv(1024).decode('utf-8')
            if not command:
                conn.sendall(b'Missing command.\n')
                break

            tokens = command.split()
            if not tokens:
                conn.sendall(b'Missing command.\n')
                break

            if tokens[0] == "exit":
                conn.sendall(b'Exiting...\n')
                break
            elif tokens[0] == "fire" and len(tokens) > 1:
                exploits = load_exploit_definitions()
                selected_exploits = [
                    e for e in exploits if e.name in tokens[1:]]
                logger.info(
                    f"Immediately starting {st.bold(len(selected_exploits))} exploits...")
                for e in selected_exploits:
                    threading.Thread(target=start_runner,
                                     args=(e, True)).start()
                conn.sendall(
                    f'Started {len(selected_exploits)} exploits.\n'.encode('utf-8'))
                break
            conn.sendall(b'Unknown command?\n')
            break
        logger.info(f"Connection with {addr} closed.")


def fetch_teams_json():
    global prev_teams_json_digest

    endpoint = handler.game.get('teams_json_url')
    if not endpoint:
        logger.info("Skipped fetching teams.json as its url is not set.")
        return

    attempts_remaining = 10
    while attempts_remaining:
        try:
            response = requests.get(endpoint, timeout=10)
            response.raise_for_status()
            logger.success(
                f'Got response from {endpoint} ({len(response.content)})')
        except Exception as e:
            exception_name = '.'.join(
                [type(e).__module__, type(e).__qualname__])
            logger.error(
                f"An error occurred while fetching teams.json. Retrying in 2s. — {st.color(exception_name, 'red')}")
            time.sleep(2)
            attempts_remaining -= 1
            continue

        digest = hashlib.md5(response.text.encode()).hexdigest()
        if not prev_teams_json_digest or digest != prev_teams_json_digest:
            break

        logger.warning(
            'teams.json has not been updated yet. Fetching again in 2s.')
        time.sleep(2)
        attempts_remaining -= 1

    if not attempts_remaining:
        logger.error(
            'Failed to fetch updated teams.json file.')
        logger.info('Old teams.json will be reused.')
        return

    with open(os.path.join('.fast', 'teams.json'), 'w') as file:
        file.write(response.text)
    prev_teams_json_digest = digest
    logger.success(f'New teams.json saved ({digest}).')


def create_dot_dir():
    dot_dir_path = '.fast'
    if not os.path.exists(dot_dir_path):
        os.makedirs(dot_dir_path)
        logger.success(f'Created .fast directory.')


def banner():
    vers = '1.1.0-czechia'
    print(f"""
\033[34;1m     .___    ____\033[0m    ______         __ 
\033[34;1m    /   /\__/   /\033[0m   / ____/_  ____ / /_  
\033[34;1m   /   /   /  ❬` \033[0m  / /_/ __ `/ ___/ __/
\033[34;1m  /___/   /____\ \033[0m / __/ /_/ (__  ) /_  
\033[34;1m /    \___\/     \033[0m/_/  \__,_/____/\__/  
\033[34;1m/\033[0m""" + f"\033[34mclient\033[0m \033[2mv{vers}\033[0m".rjust(52) + "\n")
