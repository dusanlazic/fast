from datetime import datetime, timedelta


def truncate(string, length):
    if length < 4:
        raise AttributeError("Max length must be at least 4 characters.")

    if string and len(string) > length:
        return string[:length - 3] + "..."
    return string


def seconds_from_now(seconds):
    return datetime.now() + timedelta(seconds=seconds)
