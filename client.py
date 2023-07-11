import requests
import json

headers = {
    'Content-Type': 'application/json'
}


class SubmitClient(object):
    def __init__(self, host, port, player):
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

    def get_queue_size(self):
        response = requests.get(f'{self.url}/queue-size')
        return response.json()['flags_in_queue']
    
    def get_stats(self):
        response = requests.get(f'{self.url}/stats')
        return response.json()

    def trigger_submit(self):
        response = requests.post(f'{self.url}/trigger-submit')
        return response.json()

    def test_connection(self):
        response = requests.get(f'{self.url}/health', timeout=10)
        return response.json()
