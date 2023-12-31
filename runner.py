import re
import os
import sys
import time
import shlex
import argparse
import threading
import subprocess
from util.helpers import truncate
from importlib import import_module
from handler import SubmitClient
from models import Batching
from util.styler import TextStyler as st
from util.log import logger, log_error, log_warning

exploit_name = ''
handler: SubmitClient = None


def main(args):
    global exploit_name, handler
    handler = SubmitClient()
    exploit_name = args.name

    if args.run:
        exploit_func = exploit_func_from_shell(args.run)
        prepare_func = None
        cleanup_func = None
    else:
        sys.path.append(os.getcwd())
        module = import_module(f'{args.module}')
        exploit_func = getattr(module, 'exploit')
        prepare_func = getattr(module, 'prepare', None)
        cleanup_func = getattr(module, 'cleanup', None)

    if args.prepare:
        def prepare_func(): return run_shell_command(args.prepare)
    if args.cleanup:
        def cleanup_func(): return run_shell_command(args.cleanup)

    threads = [
        threading.Thread(
            target=exploit_wrapper,
            name=target,
            args=(exploit_func, target))
        for target in args.targets
    ]

    batching = Batching(
        args.batch_count or None,
        args.batch_size or None,
        args.batch_wait or None
    ) if args.batch_wait else None

    if prepare_func:
        prepare_func()

    if batching:
        batches = batch_by_count(threads, batching.count) if batching.count else batch_by_size(threads, batching.size)
        for idx, threads in enumerate(batches):
            logger.info(f"Running batch {idx + 1}/{len(batches)} of {st.bold(exploit_name)} at {st.bold(len(threads))} targets.")
            for t in threads:
                t.start()

            if idx < len(batches) - 1:
                time.sleep(batching.wait)
    else:
        for t in threads:
            t.start()

        for t in join_threads(threads, args.timeout):
            logger.error(
                f"{st.bold(exploit_name)} took longer than {st.bold(str(args.timeout))} seconds for {st.bold(t.name)}. ⌛")

    if cleanup_func:
        cleanup_func()


def exploit_wrapper(exploit_func, target):
    try:
        response_text = exploit_func(target)
        found_flags = match_flags(response_text)

        if found_flags:
            response = handler.enqueue(found_flags, exploit_name, target)

            if 'own' in response:
                logger.warning(f"{st.bold(exploit_name)} retrieved own flag! Patch the service ASAP.")
                return
            elif 'pending' in response:
                logger.warning(f"{st.bold(exploit_name)} retrieved {response['pending']} flag{'s' if response['pending'] > 1 else ''}, but there is no connection to the server.")
                return

            new_flags, duplicate_flags = response['new'], response['duplicates'],
            new_flags_count, duplicate_flags_count = len(
                new_flags), len(duplicate_flags)

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
    except Exception as e:
        exception_name = '.'.join([type(e).__module__, type(e).__qualname__])
        logger.error(
            f"{st.bold(exploit_name)} failed with an error for {st.bold(target)}. — {st.color(exception_name, 'red')}")

        log_error(exploit_name, target, e)


def exploit_func_from_shell(command):
    def exploit_func(target):
        rendered_command = shlex.join([target if value ==
                                       '[ip]' else value for value in shlex.split(command)])
        return run_shell_command(rendered_command)

    return exploit_func


def run_shell_command(command):
    return subprocess.run(
        command,
        capture_output=True,
        shell=True,
        text=True
    ).stdout.strip()


def match_flags(text):
    matches = re.findall(handler.game['flag_format'], text)
    return matches if matches else None


def join_threads(threads, timeout):
    start = now = time.time()
    while now <= (start + timeout):
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=0)
        if all(not t.is_alive() for t in threads):
            return []
        time.sleep(0.1)
        now = time.time()
    else:
        return [t for t in threads if t.is_alive()]


def batch_by_size(threads, size):
    return [threads[i:i + size] for i in range(0, len(threads), size)]


def batch_by_count(threads, count):
    size = len(threads) // count
    remainder = len(threads) % count
    batches = [threads[i * size : (i + 1) * size] for i in range(count)]
    for i in range(remainder):
        batches[i].append(threads[count * size + i])
    return batches


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run exploits in parallel for given IP addresses.")
    parser.add_argument("targets", metavar="IP", type=str,
                        nargs="+", help="An IP address of the target")
    parser.add_argument("--name", metavar="Name", type=str,
                        required=True, help="Name of the exploit for its identification")
    parser.add_argument("--module", metavar="Exploit", type=str,
                        help="Name of the module containing the 'exploit' function")
    parser.add_argument("--run", metavar="Command", type=str,
                        help="Optional shell command for running the exploit if it is not a Python script")
    parser.add_argument("--prepare", metavar="Command", type=str,
                        help="Run prepare command from the module before attacking")
    parser.add_argument("--cleanup", metavar="Command", type=str,
                        help="Run cleanup command from the module after attacking")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Optional timeout for exploit in seconds")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Split targets list into batches of given size.")
    parser.add_argument("--batch-count", type=int, default=None,
                        help="Split targets list into given number of batches of equal size.")
    parser.add_argument("--batch-wait", type=int, default=None,
                        help="Number of seconds to wait for between running each batch.")

    args = parser.parse_args()
    main(args)
