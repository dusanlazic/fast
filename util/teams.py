import os
import json

TEAMS_KEY = 'teams'


def teams_json_exists():
    return os.path.exists(os.path.join('.fast', 'teams.json'))


def load_teams_json():
    with open(os.path.join('.fast', 'teams.json')) as file:
        return json.loads(file.read())


def get_all_team_ids(teams_json):
    # TODO: Make customizable
    return teams_json[TEAMS_KEY]


def get_team_host(team_id):
    # TODO: Make customizable
    return f'10.{int(team_id) // 255}.{team_id % 255}.0'
