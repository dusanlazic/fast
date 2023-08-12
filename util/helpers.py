from datetime import datetime, timedelta
from playhouse.shortcuts import model_to_dict


def truncate(string, length):
    if length < 4:
        raise AttributeError("Max length must be at least 4 characters.")

    if string and len(string) > length:
        return string[:length - 3] + "..."
    return string


def seconds_from_now(seconds):
    return datetime.now() + timedelta(seconds=seconds)


def deep_update(left, right):
    """
    Update a dictionary recursively in-place.
    """
    for key, value in right.items():
        if isinstance(value, dict) and value:
            returned = deep_update(left.get(key, {}), value)
            left[key] = returned
        else:
            left[key] = right[key]
    return left


def flag_model_to_dict(instance):
    flag_dict = model_to_dict(instance)
    flag_dict['timestamp'] = instance.timestamp.isoformat()

    return flag_dict
