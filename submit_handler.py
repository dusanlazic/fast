import os
import json
import requests

headers = {
    'Content-Type': 'application/json'
}


class SubmitClient(object):
    def __init__(self, host, port, player='anon'):
        self.host = host
        self.port = port
        self.player = player
        self.url = f'http://{self.host}:{self.port}'

    def enqueue(self, flags, exploit_name, target_ip):
        payload = json.dumps({
            'flags': flags,
            'exploit_name': exploit_name,
            'target_ip': target_ip,
            'player': self.player
        })
        response = requests.post(
            f'{self.url}/enqueue', data=payload, headers=headers)
        return response.json()

    def sync(self):
        response = requests.get(f'{self.url}/sync')
        return response.json()
    
    def get_game_config(self, force_fetch=False):
        if force_fetch or not os.path.isfile('.game.json'):
            response = requests.get(f'{self.url}/game')
            with open('.game.json', 'w') as file:
                file.write(response.text)
                return response.json()

        with open('.game.json') as file:
            return json.loads(file.read())

    def get_stats(self):
        response = requests.get(f'{self.url}/stats')
        return response.json()

    def trigger_submit(self):
        payload = json.dumps({
            'player': self.player
        })

        response = requests.post(f'{self.url}/trigger-submit', data=payload, headers=headers)
        return response.json()
