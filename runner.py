import argparse
import multiprocessing
from importlib import import_module


def main(args):
    """
    This module will run your exploit on all specified targets.
    """
    module = import_module(f'exploits.{args.exploit.strip(".py")}')
    exploit = getattr(module, 'exploit')

    with multiprocessing.Pool() as pool:
        pool.map(exploit, args.targets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run exploits in parallel for given IP addresses.")
    parser.add_argument("targets", metavar="IP", type=str,
                        nargs="+", help="An IP address of the target")
    parser.add_argument("--exploit", metavar="Exploit", type=str,
                        required=True, help="Name of the module containing the 'exploit' function")

    args = parser.parse_args()
    main(args)
