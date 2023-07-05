import re
import os
import sys
import yaml
import shlex
import stopit
import argparse
import threading
import subprocess
from queue import Queue
from importlib import import_module
from util.styler import TextStyler as st
from util.log import logger, log_error
from util.helpers import truncate
from models import Flag
from database import db

exploit_name = ''
shell_command = []
game = []

flags = Queue()


def main(args):
    load_config()
    connect_to_db()

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

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    with db.atomic():
        Flag.bulk_create(flags.queue)
        queue_size = Flag.select().where(Flag.status == 'queued').count()

        logger.info(
            f"{st.bold(exploit_name)} retrieved {st.bold(str(flags.qsize()))}/{len(args.targets)} flags. " +
            f"{st.bold(queue_size)} flags in the queue.")


@stopit.threading_timeoutable()
def exploit_wrapper(exploit_func, target):
    try:
        response_text = exploit_func(target)
        flag_value = match_flag(response_text)

        if flag_value:
            logger.success(
                f"{st.bold(exploit_name)} retrieved the flag from {st.bold(target)}. 🚩 — {st.faint(flag_value)}")

            flags.put(Flag(
                value=flag_value,
                exploit_name=exploit_name,
                target_ip=target,
                status='queued'
            ))
        else:
            logger.warning(
                f"{st.bold(exploit_name)} failed to retrieve the flag from {st.bold(target)}. — {st.color(repr(truncate(response_text, 50)), 'yellow')}")
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


def match_flag(text):
    match = re.search(game['flag_format'], text)
    if match:
        return match.group()
    return None


def load_config():
    global game

    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        game = data['game']


def connect_to_db():
    db.connect()


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
