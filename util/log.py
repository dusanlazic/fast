import os
import sys
import time
import traceback
from loguru import logger
from util.styler import TextStyler as st

LOG_DIR = 'logs'

config = {
    "handlers": [
        {"sink": sys.stdout,
         "format": "<d>{time:HH:mm:ss}</d> <level>{level: >8} |</level> {message}"},
    ],
}

logger.configure(**config)


def log_error(exploit_name, target, e):
    log_name = os.path.join(LOG_DIR, f'{exploit_name}_{target}_{int(time.time())}.txt')

    with open(log_name, 'w') as error_output:
        traceback.print_exc(file=error_output)
        logger.info(st.faint(f"Error log saved in {log_name}"))


def create_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        logger.success(f'Created directory for error logs.')
