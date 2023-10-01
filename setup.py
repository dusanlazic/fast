from setuptools import setup, find_packages

setup(
    name="fast",
    version="1.1.0",
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
        'pyparsing',
        'flask',
        'flask_httpauth',
        'flask_socketio',
        'flask_cors',
        'jsonschema',
        'APScheduler==3.10.1',
        'gevent-websocket',
    ],
    packages=['util', 'web'],
    package_data={'web': ['dist/*', 'dist/assets/*']},
    py_modules=['cli', 'client', 'database', 'dsl', 'handler', 'models', 'runner', 'server'],
    entry_points= {
        'console_scripts': [
            'fast = client:main',
            'server = server:main',
            'reset = cli:reset',
            'fire = cli:fire',
            'submit = cli:submit'
        ],
    }
)