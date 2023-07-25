import json
import time
import requests
from util.log import logger
from util.styler import TextStyler as st
from datetime import datetime, timedelta
from database import fallbackdb
from models import FallbackFlag

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
        self._connect_to_fallbackdb()

    def _client_configure(self):
        self._update_url()
        response = requests.get(f'{self.url}/config', params={'player': self.connect['player']})
        response.raise_for_status()
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

    def _connect_to_fallbackdb(self):
        fallbackdb.connect(reuse_if_open=True)

    def sync(self):
        response = requests.get(f'{self.url}/sync')
        sync_data = response.json()

        wait_until = datetime.now() + timedelta(seconds=sync_data['tick']['remaining'])
        logger.info(f'Synchronizing with the server... Tick will start at {st.bold(wait_until.strftime("%H:%M:%S"))}.')
        time.sleep(sync_data['tick']['remaining'])

    def enqueue(self, flags, exploit, target):
        payload = json.dumps({
            'flags': flags,
            'exploit': exploit,
            'target': target,
            'player': self.connect['player']
        })

        if target in self.game['team_ip']:
            try:
                response = requests.post(f'{self.url}/vuln-report', data=payload, headers=headers)
            except Exception:
                pass
            return {'own': len(flags)}
        
        try:
            response = requests.post(
                f'{self.url}/enqueue', data=payload, headers=headers)
        except Exception:
            for flag_value in flags:
                with fallbackdb.atomic():
                    FallbackFlag.create(value=flag_value, exploit=exploit, target=target, 
                                        status='pending')
            return {'pending': len(flags)}
        else:
            return response.json()

    def enqueue_from_fallback(self, flags):
        for flag in flags:
            payload = json.dumps({
                'flags': [flag.value],
                'exploit': flag.exploit,
                'target': flag.target,
                'player': self.connect['player'],
                'timestamp': flag.timestamp.timestamp()
            })
            try:
                response = requests.post(
                    f'{self.url}/enqueue', data=payload, headers=headers)
                response.raise_for_status()
            except Exception:
                logger.error("Server is unavailable. Skipping...")
                break
            else:
                with fallbackdb.atomic():
                    FallbackFlag.update(status='forwarded').where(FallbackFlag.value == flag.value).execute()

    def trigger_submit(self):
        payload = json.dumps({
            'player': self.connect['player']
        })

        response = requests.post(f'{self.url}/trigger-submit', data=payload, headers=headers)
        return response.json()
