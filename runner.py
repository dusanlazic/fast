import re
import os
import sys
import yaml
import shlex
import argparse
import subprocess
import multiprocessing
from importlib import import_module
from util.styler import TextStyler as st
from util.log import logger
from models import Flag
from database import db

exploit_name = ''
shell_command = []
config = []
tick_number = os.getenv('TICK_NUMBER')

manager = multiprocessing.Manager()
flags_collected = manager.Value('i', 0)
lock = manager.Lock()


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
        pool.map(exploit_wrapper, [(exploit_func, target)
                 for target in args.targets])

    logger.info(
        f"{st.bold(exploit_name)} retrieved {st.bold(str(flags_collected.value))}/{len(args.targets)} flags.")


def exploit_wrapper(args):
    exploit_func, target = args
    try:
        flag = exploit_func(target)

        if check_flag_format(flag):
            logger.success(
                f"{st.bold(exploit_name)} retrieved the flag from {st.bold(target)}. 🚩 — {st.faint(flag)}")

            flag = Flag(value=flag, exploit_name=exploit_name,
                        target_ip=target, tick_number=tick_number, status='queued')
            flag.save()

            with lock:
                flags_collected.value += 1
        else:
            logger.warning(
                f"{st.bold(exploit_name)} failed to retrieve the flag from {st.bold(target)}. — {st.color(flag[:50], 'yellow')}")

    except Exception as e:
        exception_name = '.'.join([type(e).__module__, type(e).__qualname__])

        logger.error(
            f"{st.bold(exploit_name)} failed to complete for target {st.bold(target)}. — {st.color(exception_name, 'red')}")


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

    args = parser.parse_args()
    main(args)
