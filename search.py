from functools import reduce
from models import Flag

def json_to_peewee_query(json_filter):
    operator = json_filter.get("operator", "AND").upper()

    if "conditions" in json_filter:
        queries = [json_to_peewee_query(cond) for cond in json_filter["conditions"]]
        if operator == "AND":
            return reduce(lambda x, y: x & y, queries)
        elif operator == "OR":
            return reduce(lambda x, y: x | y, queries)
        elif operator == "NOT":
            return ~queries[0]

    field = json_filter["field"]
    
    if field == "value" and "regex" in json_filter:
        regex = json_filter["regex"]
        return Flag.value.regexp(regex)

    elif field == "exploit" and "in" in json_filter:
        in_ = json_filter.get("in")
        conditions = [
            ((Flag.player == player) & (Flag.exploit == exploit))
            for player, exploit in (item.split('/') for item in in_)  # split 'player/exploit' into (player, exploit)
        ]
        return reduce(lambda x, y: x | y, conditions)

    elif field == "tick":
        eq = json_filter.get("eq", None)
        ge = json_filter.get("ge", None)
        le = json_filter.get("le", None)
        if eq:
            return Flag.tick == eq
        if ge and le:
            return Flag.tick.between(ge, le)
        elif ge:
            return Flag.tick >= ge
        elif le:
            return Flag.tick <= le

    elif field == "target" and "in" in json_filter:
        in_ = json_filter.get("in")
        return Flag.exploit.in_(in_)
    
    elif field == "timestamp":
        after = json_filter.get("after", None)
        before = json_filter.get("before", None)
        if after and before:
            return Flag.timestamp.between(after, before)
        elif after:
            return Flag.timestamp >= after
        elif le:
            return Flag.timestamp <= le
    
    elif field == "status" and "in" in json_filter:
        in_ = json_filter.get("in")
        return Flag.status.in_(in_)

    if field == "response" and "regex" in json_filter:
        regex = json_filter["regex"]
        return Flag.value.regexp(regex)
