import os
import json


def teams_json_exists():
    return os.path.exists(os.path.join('.fast', 'teams.json'))


def load_teams_json():
    with open(os.path.join('.fast', 'teams.json')) as file:
        return json.loads(file.read())


def get_all_team_ids(teams_json, teams_key):
    return teams_json[teams_key or 'teams']


def get_team_host(team_id, format):
    return format.replace('*', str(team_id))
