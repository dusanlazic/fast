import os
import sys
import yaml
from importlib import import_module
from client import SubmitClient
from util.log import logger, log_error
from util.styler import TextStyler as st


def main():
    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        submitter = data['submitter']

    client = SubmitClient(
        host=submitter['host'],
        port=submitter['port'],
        player=submitter.get('player') or 'anon'
    )

    try:
        client.test_connection()
    except Exception as e:
        exception_name = '.'.join([type(e).__module__, type(e).__qualname__])
        logger.error(f"Failed to connect to the submitter server at http://{submitter['host']}:{submitter['port']}. — {st.color(exception_name, 'red')}")

        log_error('submit_server', 'none', e)
    
    client.trigger_submit()