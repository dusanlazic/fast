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
        logger.error(f"Error found in field {st.bold(e.path[-1])}: {e.message}")
        return False


def validate_targets(exploits):
    for exploit in exploits:
        for target in exploit['targets']:
            if not validate_ip_range(target):
                raise ValidationError(f"Target '{st.bold(target)}' in exploit '{st.bold(exploit['name'])}' is not a valid IP or IP range.")


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
        "cmd": {
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
                "type": "string"
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