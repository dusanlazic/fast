import os
import sys
import time
import traceback
from pathlib import Path
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
    log_filename = get_log_filename(exploit_name, target, '_err')

    with open(log_filename, 'w') as error_output:
        traceback.print_exc(file=error_output)
        logger.info(st.faint(f"Error log saved in {log_filename}"))


def log_response(exploit_name, target, response):
    log_filename = get_log_filename(exploit_name, target, '_res')

    with open(log_filename, 'w') as error_output:
        error_output.write(response)
        logger.info(st.faint(f"Response saved in {log_filename}"))


def create_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        logger.success(f'Created directory for error logs.')


def get_log_filename(exploit_name, target, suffix=''):
    timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    filename = f"{timestamp}_{exploit_name}_{target}{suffix}"
    valid_filename = "".join(
        [c if c.isalnum() or c in ('_', '-') else '_' for c in filename]) + '.log'

    return os.path.join(LOG_DIR, valid_filename)


def delete_old_logs(minutes: int = 24) -> None:
    threshold_time = time.time() - minutes * 60
    count = 0

    folder = Path(LOG_DIR)
    for file in folder.iterdir():
        if file.is_file() and file.stat().st_mtime < threshold_time:
            file.unlink()
            count += 1

    if count:
        logger.success(
            f'Deleted {count} log files older than {minutes} minutes.')
