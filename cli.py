from gevent import monkey
monkey.patch_all()
import os
import json
import argparse
import threading
from util.log import logger
from util.styler import TextStyler as st
from client import load_exploits, load_config, setup_handler, run_exploit
from server import setup_database
from database import db
from models import Flag
from handler import SubmitClient


def fire():
    parser = argparse.ArgumentParser(
        description="Run exploits manually. Useful if you do not want to wait for the next tick.")
    parser.add_argument("names", metavar="Name", type=str, nargs="+",
                        help="Names of the exploits as in fast.yaml")
    args = parser.parse_args()

    load_config()
    setup_handler(fire_mode=True)
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


def submit():
    SubmitClient().trigger_submit()


def reset():
    RECOVERY_CONFIG_PATH = '.recover.json'

    if os.path.isfile(RECOVERY_CONFIG_PATH):
        with open(RECOVERY_CONFIG_PATH) as file:
            backup = json.loads(file.read())

        # TODO: Improve interactivity
        os.remove(RECOVERY_CONFIG_PATH)
        logger.info(
            "Tick number reset. If you changed your mind, you can still copy it:")
        logger.info(st.color(backup, 'green'))

    setup_database()
    confirm_string = "drop table flags;"

    print(f"{st.color('?', 'green')} Do you want to {st.color('delete', 'red')} the existing flags?")
    confirmation = input(
        f'  Type {st.color(confirm_string, "blue")} to delete all the previous flags. Type anything else to keep them.\n> ') == confirm_string

    if confirmation:
        db.drop_tables([Flag])
        logger.success("Table 'Flag' dropped.")
    else:
        logger.success("Understood. Skipped deleting flags.")
