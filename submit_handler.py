import json
import time
import requests
from util.log import logger
from util.styler import TextStyler as st
from datetime import datetime, timedelta

IMMUTABLE_CONFIG_PATH = '.config.json'

headers = {
    'Content-Type': 'application/json'
}


class SubmitClient(object):
    def __init__(self, connect=None):
        if connect:
            self.connect = connect
            self._client_configure()
        else:
            self._runner_configure()

    def _client_configure(self):
        self._update_url()
        response = requests.get(f'{self.url}/config', params={'player': self.connect['player']})
        server_config = response.json()
        self.game = server_config['game']

        immutable_config = {
            'game': self.game,
            'connect': self.connect
        }

        # Persist config so runners can reuse it.
        with open(IMMUTABLE_CONFIG_PATH, 'w') as file:
            file.write(json.dumps(immutable_config))

    def _runner_configure(self):
        with open(IMMUTABLE_CONFIG_PATH) as file:
            immutable_config = json.loads(file.read())
        
        self.game = immutable_config['game']
        self.connect = immutable_config['connect']
        self._update_url()

    def _update_url(self):
        protocol = self.connect['protocol']
        host = self.connect['host']
        port = self.connect['port']

        if self.connect.get('password') != None:
            user = self.connect['player']
            password = self.connect['password']
            self.url = f"{protocol}://{user}:{password}@{host}:{port}"
        else:
            self.url = f"{protocol}://{host}:{port}"

    def sync(self):
        response = requests.get(f'{self.url}/sync')
        sync_data = response.json()

        wait_until = datetime.now() + timedelta(seconds=sync_data['tick']['remaining'])
        logger.info(f'Synchronizing with the server... Tick will start at {st.bold(wait_until.strftime("%H:%M:%S"))}.')
        time.sleep(sync_data['tick']['remaining'])

    def enqueue(self, flags, exploit_name, target_ip):
        payload = json.dumps({
            'flags': flags,
            'exploit_name': exploit_name,
            'target_ip': target_ip,
            'player': self.connect['player']
        })
        response = requests.post(
            f'{self.url}/enqueue', data=payload, headers=headers)
        return response.json()

    def notifyExploitStart(self, exploit_name, targets):
        payload = json.dumps({
            'exploit_name': exploit_name,
            'targets': targets,
            'player': self.connect['player']
        })

        requests.post(f'{self.url}/notify/exploit-start', data=payload, headers=headers)

    def notifyExploitEnd(self, exploit_name):
        payload = json.dumps({
            'exploit_name': exploit_name,
            'player': self.connect['player']
        })

        requests.post(f'{self.url}/notify/exploit-end', data=payload, headers=headers)

    def trigger_submit(self):
        payload = json.dumps({
            'player': self.connect['player']
        })

        response = requests.post(f'{self.url}/trigger-submit', data=payload, headers=headers)
        return response.json()
