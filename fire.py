import client
import argparse
import threading
from util.log import logger
from util.styler import TextStyler as st
from client import load_exploits, load_config, run_exploit


def main():
    parser = argparse.ArgumentParser(
        description="Run exploits manually. Useful if you do not want to wait for the next tick.")
    parser.add_argument("names", metavar="Name", type=str, nargs="+",
                        help="Names of the exploits as in fast.yaml")
    args = parser.parse_args()

    client.config = load_config()
    exploits = load_exploits()

    selected_exploits = [e for e in exploits if e.name in args.names]

    invalid_names = [n for n in args.names if n not in [
        e.name for e in selected_exploits]]
    if invalid_names:
        logger.error(
            f"Exploits with the following names not found: {st.bold(', '.join(invalid_names))}")
        logger.info(
            f"Available exploits: {st.bold(', '.join([e.name for e in exploits]))}")

    for exploit in selected_exploits:
        exploit.delay = 0  # Ignore delay and run instantly
        threading.Thread(target=run_exploit, args=(exploit,)).start()
