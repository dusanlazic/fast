from datetime import datetime, timedelta


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
