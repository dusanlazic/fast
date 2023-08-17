from gevent import monkey
monkey.patch_all()
import os
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
    logger.info("Submission triggered...")
    client = SubmitClient()
    client.trigger_submit()
    stats = client.get_flagstore_stats()
    logger.info(f"{st.bold('Stats')} — {st.bold(stats['queued'])} queued, {st.bold(stats['accepted'])} accepted, {st.bold(stats['rejected'])} rejected.")


def reset():
    RECOVERY_CONFIG_PATH = '.recover.json'
    QMARK = st.color('?', 'cyan')
    PLUS = st.color('OK', 'green')
    INFO = st.faint('SKIP')

    if os.path.isfile(RECOVERY_CONFIG_PATH):
        print(f"{QMARK} Do you want to {st.color('reset the tick clock', 'red')}?")
        confirm_string = 'reset'
        confirmation = input(f"  Type {st.color(confirm_string, 'cyan')} to confirm. ") == confirm_string
        if confirmation:
            os.remove(RECOVERY_CONFIG_PATH)
            print(f"{PLUS} Tick clock cleared.")
        else:
            print(f"{INFO} Tick clock left intact.")

    setup_database(log=False)
    print(f"{QMARK} Do you want to {st.color('delete the existing flags', 'red')}?")
    confirm_string = ');drop table flags;--'
    confirmation = input(f'  Type {st.color(confirm_string, "cyan")} to delete all the previous flags.\n     > ') == confirm_string

    if confirmation:
        db.drop_tables([Flag])
        print(f"{PLUS} Table 'Flag' dropped.")
    else:
        print(f"{INFO} Flags left intact.")
