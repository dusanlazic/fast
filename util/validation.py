from jsonschema import validate, ValidationError
from util.styler import TextStyler as st
from util.log import logger


def validate_data(data, schema, custom=None):
    try:
        validate(instance=data, schema=schema)

        if custom:
            custom(data)

        return True
    except ValidationError as e:
        path = '.'.join((str(x) for x in e.path))
        logger.error(f"Error found in field {st.bold(path)}: {e.message}")
        return False


def validate_targets(exploits):
    for exploit_idx, exploit in enumerate(exploits):
        for target_idx, target in enumerate(exploit['targets']):
            if not validate_ip_range(target):
                raise ValidationError(f"Target '{st.bold(target)}' in exploit '{st.bold(exploit['name'])}' is not a valid IP or IP range.",
                                      path=['exploits', exploit_idx, 'targets', target_idx])


def validate_quartet(quartet):
    return quartet.isdigit() and 0 <= int(quartet) <= 255


def validate_ip(ip):
    quartets = ip.split(".")

    return len(quartets) == 4 and all(validate_quartet(quartet) for quartet in quartets)


def validate_range_quartet(quartet):
    if "-" in quartet:
        start, end = quartet.split("-")
        return start.isdigit() and end.isdigit() and 0 <= int(start) <= int(end) <= 255
    else:
        return validate_quartet(quartet)


def validate_ip_range(ip_range):
    if not '-' in ip_range:
        return validate_ip(ip_range)

    quartets = ip_range.split(".")

    return len(quartets) == 4 and all(validate_range_quartet(quartet) for quartet in quartets)


def validate_delay(server_yaml_data):
    tick_duration = server_yaml_data['game']['tick_duration']
    delay = server_yaml_data['submitter']['delay']

    if delay >= tick_duration:
        raise ValidationError(f"Submitter delay ({delay}s) takes longer than the tick itself ({tick_duration}s).", path=['submitter', 'delay'])


connect_schema = {
    "type": "object",
    "properties": {
        "protocol": {
            "type": "string",
            "enum": ["http"]  # TODO: Support https
        },
        "host": {
            "type": "string",
            "format": "hostname",
        },
        "port": {
            "type": "integer",
            "minimum": 1024,
            "maximum": 65535
        },
        "player": {
            "type": "string",
            "maxLength": 20
        },
        "password": {
            "type": "string"
        }
    },
    "additionalProperties": False
}


exploit_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "maxLength": 100
        },
        "timeout": {
            "type": "number",
            "exclusiveMinimum": 0
        },
        "module": {
            "type": "string",
        },
        "run": {
            "type": "string",
        },
        "prepare": {
            "type": "string",
        },
        "cleanup": {
            "type": "string",
        },
        "env": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "string"
                }
            }
        },
        "delay": {
            "type": "number",
            "exclusiveMinimum": 0
        },
        "targets": {
            "type": "array",
            "items": {
                "type": "string",
                "format": "hostname"
            }
        },
    },
    "required": ["name", "targets"],
    "additionalProperties": False
}


exploits_schema = {
    "type": "array",
    "items": exploit_schema
}


game_schema = {
    "type": "object",
    "properties": {
        "tick_duration": {
            "type": "number",
            "exclusiveMinimum": 0
        },
        "flag_format": {
            "type": "string"
        },
        "team_ip": {
            "oneOf": [
                {"type": "string", "format": "hostname"},
                {"type": "array", "items": {"type": "string", "format": "hostname"}},
            ]
        },
    },
    "required": ["tick_duration", "flag_format", "team_ip"],
    "additionalProperties": False,
}


submitter_schema = {
    "type": "object",
    "properties": {
        "delay": {"type": "number", "exclusiveMinimum": 0},
        "run_every_nth_tick": {"type": "integer", "minimum": 1},
        "module": {"type": "string"},
    },
    "required": ["delay"],
    "additionalProperties": False,
}


server_schema = {
    "type": "object",
    "properties": {
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
        "password": {"type": "string"}
    },
    "additionalProperties": False,
}


server_yaml_schema = {
    "type": "object",
    "properties": {
        "game": game_schema,
        "submitter": submitter_schema,
        "server": server_schema,
    },
    "required": ["game", "submitter"],
}
