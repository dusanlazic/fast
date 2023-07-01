import re
import os
import sys
import yaml
import time
import shlex
import argparse
import subprocess
import multiprocessing
from importlib import import_module
from util.styler import TextStyler as st
from util.log import logger, log_error
from util.helpers import truncate
from models import Flag
from database import db

exploit_name = ''
shell_command = []
config = []


def main(args):
    load_config()
    connect_to_db()

    global exploit_name, shell_command
    exploit_name = args.exploit

    if args.cmd:
        shell_command = shlex.split(args.cmd)
        exploit_func = run_shell_command
    else:
        sys.path.append(os.getcwd())
        module = import_module(f'{exploit_name}')
        exploit_func = getattr(module, 'exploit')

    with multiprocessing.Pool() as pool:
        tasks = [(exploit_func, target) for target in args.targets]
        flags = []
        remaining = args.targets[:]

        start = time.time()
        it = pool.imap_unordered(
            exploit_wrapper,
            tasks
        )

        while (time.time() - start) <= args.timeout:
            try:
                target, flag = it.next(timeout=0.1)
                # When the exploit returns, run the following
                remaining.remove(target)

                if flag:
                    flags.append(flag)
            except StopIteration:
                break
            except multiprocessing.TimeoutError:
                pass

    if remaining:
        logger.error(f"{st.bold(exploit_name)} took longer than {st.bold(args.timeout)} seconds ⌛ for the following targets: {st.bold(', '.join(remaining))}.")

    logger.info(
        f"{st.bold(exploit_name)} retrieved {st.bold(str(len(flags)))}/{len(args.targets)} flags.")


def exploit_wrapper(args):
    exploit_func, target = args
    try:
        flag_value = exploit_func(target)

        if check_flag_format(flag_value):
            logger.success(
                f"{st.bold(exploit_name)} retrieved the flag from {st.bold(target)}. 🚩 — {st.faint(flag_value)}")

            return target, Flag(
                value=flag_value, 
                exploit_name=exploit_name,
                target_ip=target, 
                status='queued'
            )
        else:
            logger.warning(
                f"{st.bold(exploit_name)} failed to retrieve the flag from {st.bold(target)}. — {st.color(truncate(flag_value, 50), 'yellow')}")
    except Exception as e:
        exception_name = '.'.join([type(e).__module__, type(e).__qualname__])
        logger.error(
            f"{st.bold(exploit_name)} failed with an error for target {st.bold(target)}. — {st.color(exception_name, 'red')}")

        log_error(exploit_name, target, e)

    return target, None


def run_shell_command(target):
    rendered_command = [target if value ==
                        '[ip]' else value for value in shell_command]

    result = subprocess.run(
        rendered_command,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def check_flag_format(flag):
    if flag and re.fullmatch(config['flag_format'], flag):
        return True
    return False


def load_config():
    global config

    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        config = data['config']


def connect_to_db():
    db.connect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run exploits in parallel for given IP addresses.")
    parser.add_argument("targets", metavar="IP", type=str,
                        nargs="+", help="An IP address of the target")
    parser.add_argument("--exploit", metavar="Exploit", type=str,
                        required=True, help="Name of the module containing the 'exploit' function")
    parser.add_argument("--cmd", metavar="Command", type=str,
                        help="Optional shell command for running the exploit if it is not a Python script")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Optional timeout for exploit in seconds")

    args = parser.parse_args()
    main(args)
