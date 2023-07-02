from datetime import datetime, timedelta

def incrs(number_string):
    """
    Increments a number written as a string.
    """
    return str(int(number_string) + 1)


def truncate(string, length):
    if length < 4:
        raise AttributeError("Max length must be at least 4 characters.")
    
    if string and len(string) > length:
        return string[:length - 3] + "..."
    return string


def seconds_from_now(seconds):
    return datetime.now() + timedelta(seconds=seconds)
