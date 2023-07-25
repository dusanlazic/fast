from setuptools import setup, find_packages

setup(
    name="fast",
    version="0.1",
    description="Flag Acquisition and Submission Tool ─ Easily manage your exploits in A/D competitions",
    author="Dušan Lazić",
    author_email="lazicdusan1104@gmail.com",
    url="https://github.com/dusanlazic/fast",
    install_requires=[
        'requests',
        'loguru',
        'pyyaml',
        'peewee',
        'psycopg2-binary',
        'flask',
        'flask_httpauth',
        'flask_socketio',
        'jsonschema',
        'APScheduler',
        'gunicorn',
        'gevent-websocket'
    ],
    packages=find_packages(),
    py_modules=['cli', 'client', 'database', 'handler', 'models', 'runner', 'server'],
    entry_points= {
        'console_scripts': [
            'fast = client:main',
            'server = server:main',
            'reset = cli:reset',
            'fire = cli:fire',
            'submit = cli:submit',
        ],
    }
)