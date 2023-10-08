import re
import ipaddress
from jsonschema import validate, ValidationError
from util.hosts import explode_ipv6_range, IPV4_PATTERN
from util.styler import TextStyler as st
from util.log import logger


def validate_data(data, schema, custom=None):
    try:
        validate(instance=data, schema=schema)

        if callable(custom):
            custom(data)
        elif isinstance(custom, list) and all(callable(func) for func in custom):
            [func(data) for func in custom]

        return True
    except ValidationError as e:
        path = '.'.join((str(x) for x in e.path))
        logger.error(f"Error found in field {st.bold(path)}: {e.message}")
        return False


def validate_targets(exploits):
    for exploit_idx, exploit in enumerate(exploits):
        if not exploit.get('targets'):
            continue
        for target_idx, target in enumerate(exploit['targets']):
            if not validate_target(target):
                raise ValidationError(f"Target '{st.bold(target)}' in exploit '{st.bold(exploit['name'])}' is not a valid IP, IP range or hostname.",
                                      path=['exploits', exploit_idx, 'targets', target_idx])


def validate_target(target_entry):
    # Single IPv4 or IPv6
    try:
        ipaddress.ip_address(target_entry)
        return True
    except ValueError:
        pass
    # IPv4 range
    if re.match(IPV4_PATTERN, target_entry):
        return validate_ipv4_range(target_entry)
    # IPv6 range
    if ':' in target_entry:
        return validate_ipv6_range(target_entry)
    # Hostname
    return validate_hostname(target_entry)


# IPv4 validations


def validate_octet_range(octet):
    if "-" in octet:
        start, end = octet.split("-")
        return start.isdigit() and end.isdigit() and 0 <= int(start) <= int(end) <= 255
    else:
        return octet.isdigit() and 0 <= int(octet) <= 255


def validate_ipv4_range(ip_range):
    octets = ip_range.split(".")

    return len(octets) == 4 and all(validate_octet_range(octet) for octet in octets)


# IPv6 validations


def validate_hextet_range(hextet):
    if "-" in hextet:
        start, end = hextet.split("-")
        try:
            start_value, end_value = int(start, 16), int(end, 16)
            return 0 <= start_value <= end_value <= 0xFFFF
        except ValueError:
            return False
    else:
        try:
            value = int(hextet, 16)
            return 0 <= value <= 0xFFFF
        except ValueError:
            return False


def validate_ipv6_range(ip_range):
    ip_range = explode_ipv6_range(ip_range)
    hextets = ip_range.split(":")

    return len(hextets) == 8 and all(validate_hextet_range(hextet) for hextet in hextets)


# Hostname validatoin


def validate_hostname(hostname):
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    if len(hostname) > 253:
        return False

    labels = hostname.split(".")

    if re.match(r"[0-9]+$", labels[-1]):
        return False

    allowed = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(label) for label in labels)


# Other validations


def validate_delay(server_yaml_data):
    if server_yaml_data['submitter'].get('delay') is None:
        return

    tick_duration = server_yaml_data['game']['tick_duration']
    delay = server_yaml_data['submitter']['delay']

    if delay >= tick_duration:
        raise ValidationError(f"Submitter delay ({delay}s) takes longer than the tick itself ({tick_duration}s).", path=[
                              'submitter', 'delay'])


def validate_interval(server_yaml_data):
    if server_yaml_data['submitter'].get('interval') is None:
        return

    interval = server_yaml_data['submitter']['interval']
    duration = server_yaml_data['game']['tick_duration']

    if duration % interval != 0:
        raise ValidationError(f"Submitter interval ({interval}s) must divide tick duration ({duration}s).", path=[
                              'submitter', 'interval'])


connect_schema = {
    "type": "object",
    "properties": {
        "protocol": {
            "type": "string",
            "enum": ["http", "https"]
        },
        "host": {
            "type": "string",
            "format": "hostname",
        },
        "port": {
            "type": "integer",
            "minimum": 1,
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
        "batches": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "minimum": 1},
                "size": {"type": "integer", "minimum": 1},
                "wait": {"type": "number", "exclusiveMinimum": 0}
            },
            "oneOf": [
                {"required": ["wait", "count"], "not": {"required": ["size"]}},
                {"required": ["wait", "size"], "not": {"required": ["count"]}}
            ]
        },
        "targets": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
    },
    "required": ["name"],
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
        "start": {
            "type": "string",
            "pattern": "^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$"
        },
        "teams_json_url": {
            "type": "string",
            "format": "uri"
        }
    },
    "required": ["tick_duration", "flag_format", "team_ip"],
    "additionalProperties": False,
}


submitter_schema = {
    "type": "object",
    "properties": {
        "delay": {"type": "number", "exclusiveMinimum": 0},
        "interval": {"type": "number", "exclusiveMinimum": 0},
        "module": {"type": "string"},
    },
    "oneOf": [
        {"required": ["delay"]},
        {"required": ["interval"]}
    ],
    "additionalProperties": False,
}


server_schema = {
    "type": "object",
    "properties": {
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "password": {"type": "string"}
    },
    "additionalProperties": False,
}


database_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "user": {"type": "string"},
        "password": {"type": "string"},
        "host": {"type": "string", "format": "hostname"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
    },
    "additionalProperties": False,
}


server_yaml_schema = {
    "type": "object",
    "properties": {
        "game": game_schema,
        "submitter": submitter_schema,
        "server": server_schema,
        "database": database_schema
    },
    "required": ["game", "submitter"],
}
