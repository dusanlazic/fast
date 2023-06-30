import os
import sys
import time
import traceback
from loguru import logger
from util.styler import TextStyler as st

log_dir = 'logs'

config = {
    "handlers": [
        {"sink": sys.stdout,
         "format": "<d>{time:HH:mm:ss}</d> <level>{level: >8} |</level> {message}"},
    ],
}

logger.configure(**config)


def log_error(exploit_name, target, e):
    log_name = f'{log_dir}/{exploit_name}_{target}_{int(time.time())}.txt'

    with open(log_name, 'w') as error_output:
        traceback.print_exc(file=error_output)
        logger.info(st.faint(f"Error log saved in {log_name}"))


def create_log_dir():
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        logger.success(f'Created directory for error logs.')
