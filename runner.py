import os
import sys
import argparse
import multiprocessing
from util.styler import TextStyler as st
from util.log import logger
from importlib import import_module

exploit_name = ''


def main(args):
    """
    This module will run your exploit on all specified targets.
    """
    sys.path.append(os.getcwd())

    global exploit_name
    exploit_name = args.exploit.strip(".py")

    module = import_module(f'{exploit_name}')
    exploit = getattr(module, 'exploit')

    with multiprocessing.Pool() as pool:
        pool.map(exploit_wrapper, [(exploit, target)
                 for target in args.targets])


def exploit_wrapper(args):
    exploit_func, target = args
    try:
        flag = exploit_func(target)

        # TODO: Check user configured flag format
        if len(flag):
            logger.success(
                f"{st.bold(exploit_name)} retrieved flag from {st.bold(target)} 🚩")
        else:
            logger.warning(
                f"{st.bold(exploit_name)} did not return the flag correctly from {st.bold(target)}")
        # TODO: Store and submit flag
    except Exception as e:
        logger.error(
            f"{st.bold(exploit_name)} did not work on {st.bold(target)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run exploits in parallel for given IP addresses.")
    parser.add_argument("targets", metavar="IP", type=str,
                        nargs="+", help="An IP address of the target")
    parser.add_argument("--exploit", metavar="Exploit", type=str,
                        required=True, help="Name of the module containing the 'exploit' function")

    args = parser.parse_args()
    main(args)
