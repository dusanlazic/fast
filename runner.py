import re
import os
import sys
import yaml
import shlex
import stopit
import argparse
import requests
import threading
import subprocess
from client import SubmitClient
from importlib import import_module
from util.styler import TextStyler as st
from util.log import logger, log_error, log_warning
from util.helpers import truncate

exploit_name = ''
shell_command = []
game, submitter = [], []

client: SubmitClient = None


def main(args):
    load_config()

    global exploit_name, shell_command
    exploit_name = args.name

    if args.cmd:
        shell_command = shlex.split(args.cmd)
        exploit_func = run_shell_command
    else:
        sys.path.append(os.getcwd())
        module = import_module(f'{args.module}')
        exploit_func = getattr(module, 'exploit')

    threads = [
        threading.Thread(
            target=exploit_wrapper,
            args=(exploit_func, target),
            kwargs={'timeout': args.timeout})
        for target in args.targets
    ]

    connect_to_server()

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # TODO: Get queue size through REST call
    queue_size = client.get_queue_size()
    logger.info(f"{st.bold(queue_size)} flags in the queue.")


@stopit.threading_timeoutable()
def exploit_wrapper(exploit_func, target):
    try:
        response_text = exploit_func(target)
        found_flags = match_flags(response_text)

        if found_flags:
            response = client.enqueue(found_flags, exploit_name, target)
            new_flags, duplicate_flags = response['new'], response['duplicates'],
            new_flags_count, duplicate_flags_count = len(new_flags), len(duplicate_flags)

            if new_flags_count == 0 and duplicate_flags_count > 0:
                logger.warning(f"{st.bold(exploit_name)} retrieved no new flags and " +
                               ("a duplicate flag " if duplicate_flags_count == 1 else f"{st.bold(duplicate_flags_count)} duplicate flags ") +
                               f"from {st.bold(target)}.")
                
            elif new_flags_count > 0 and duplicate_flags_count > 0:
                logger.success(f"{st.bold(exploit_name)} retrieved " +
                               ("a new flag " if new_flags_count == 1 else f"{st.bold(new_flags_count)} new flags, and ") +
                               ("a duplicate flag " if duplicate_flags_count == 1 else f"{st.bold(duplicate_flags_count)} duplicate flags ") +
                               f"from {st.bold(target)}. 🚩 — {st.faint(truncate(' '.join(new_flags), 50))}")
                
            elif new_flags_count > 0 and duplicate_flags_count == 0:
                logger.success(f"{st.bold(exploit_name)} retrieved " +
                               ("a new flag " if new_flags_count == 1 else f"{st.bold(new_flags_count)} new flags ") +
                               f"from {st.bold(target)}. 🚩 — {st.faint(truncate(' '.join(new_flags), 50))}")
        else:
            logger.warning(
                f"{st.bold(exploit_name)} retrieved no flags from {st.bold(target)}. — {st.color(repr(truncate(response_text, 50)), 'yellow')}")
            log_warning(exploit_name, target, response_text)

    except stopit.utils.TimeoutException as e:
        logger.error(
            f"{st.bold(exploit_name)} took longer than {st.bold(str(args.timeout))} seconds for {st.bold(target)}. ⌛"
        )
    except Exception as e:
        exception_name = '.'.join([type(e).__module__, type(e).__qualname__])
        logger.error(
            f"{st.bold(exploit_name)} failed with an error for {st.bold(target)}. — {st.color(exception_name, 'red')}")

        log_error(exploit_name, target, e)


def run_shell_command(target):
    rendered_command = [target if value ==
                        '[ip]' else value for value in shell_command]

    result = subprocess.run(
        rendered_command,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def match_flags(text):
    matches = re.findall(game['flag_format'], text)
    return matches if matches else None


def load_config():
    global game, submitter

    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        game, submitter = data['game'], data['submitter']


def connect_to_server():
    global client

    client = SubmitClient(
        host=submitter['host'],
        port=submitter['port'],
        player=submitter.get('player') or 'anon'
    )

    try:
        client.test_connection()
        # TODO: Implement an alternative store for flags while the server is down
    except Exception as e:
        exception_name = '.'.join([type(e).__module__, type(e).__qualname__])
        logger.error(f"Failed to connect to the submitter server at http://{submitter['host']}:{submitter['port']}. — {st.color(exception_name, 'red')}")

        log_error('submit_server', 'none', e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run exploits in parallel for given IP addresses.")
    parser.add_argument("targets", metavar="IP", type=str,
                        nargs="+", help="An IP address of the target")
    parser.add_argument("--name", metavar="Name", type=str,
                        required=True, help="Name of the exploit for its identification")
    parser.add_argument("--module", metavar="Exploit", type=str,
                        help="Name of the module containing the 'exploit' function")
    parser.add_argument("--cmd", metavar="Command", type=str,
                        help="Optional shell command for running the exploit if it is not a Python script")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Optional timeout for exploit in seconds")

    args = parser.parse_args()
    main(args)
