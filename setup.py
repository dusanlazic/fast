from setuptools import setup, find_packages

setup(
    name="fast",
    version="0.1",
    description="Flag Acquisition and Submission Tool ─ Easily manage your exploits in A/D competitions",
    author="Dušan Lazić",
    author_email="lazicdusan1104@gmail.com",
    url="https://github.com/dusanlazic/fast",
    install_requires=[
        'loguru',
        'pyyaml',
        'peewee',
        'stopit',
        'bottle',
        'APScheduler'
    ],
    packages=find_packages(),
    py_modules=['database', 'fast', 'fire', 'models', 'runner', 'submit', 'server', 'client'],
    entry_points= {
        'console_scripts': [
            'fast = fast:main',
            'fire = fire:main',
            'submit = submit:main',
            'submitter = server:main'
        ],
    }
)