import os
import sys
from importlib import import_module
from fast import load_config, submitter_wrapper


def main():
    _, submitter = load_config()

    sys.path.append(os.getcwd())
    module = import_module(submitter.get('module') or 'submitter')
    submit_func = getattr(module, 'submit')

    submitter_wrapper(submit_func)
