import yaml
from submit_handler import SubmitClient

def main():
    with open('fast.yaml', 'r') as file:
        data = yaml.safe_load(file)
        connect = data['connect']

    SubmitClient(
        host=connect['host'],
        port=connect['port'],
        player=connect.get('player') or 'anon'
    ).trigger_submit()
