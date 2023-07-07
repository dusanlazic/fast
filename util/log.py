import os
import sys
import traceback
from datetime import datetime
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
    log_filename = get_log_filename(exploit_name, target)

    with open(log_filename, 'w') as error_output:
        traceback.print_exc(file=error_output)
        logger.info(st.faint(f"Error log saved in {log_filename}"))


def log_warning(exploit_name, target, response):
    log_filename = get_log_filename(exploit_name, target)

    with open(log_filename, 'w') as error_output:
        error_output.write(response)
        logger.info(st.faint(f"Response saved in {log_filename}"))


def create_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        logger.success(f'Created directory for error logs.')


def get_log_filename(exploit_name, target):
    return os.path.join(
        LOG_DIR, f'{exploit_name}_{target}_{datetime.now().strftime("%H_%M_%S")}.txt')
