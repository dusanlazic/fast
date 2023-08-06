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
    attribute = getattr(Flag, field)
    conditions = []

    if "matches" in json_filter:
        condition = attribute.regexp(json_filter["matches"])
        conditions.append(condition)

    if "in" in json_filter:
        condition = attribute.in_(json_filter["in"])
        conditions.append(condition)

    if "eq" in json_filter:
        condition = attribute == json_filter["eq"]
        conditions.append(condition)
    
    if "lt" in json_filter:
        condition = attribute < json_filter["lt"]
        conditions.append(condition)
    
    if "gt" in json_filter:
        condition = attribute > json_filter["gt"]
        conditions.append(condition)

    if "ge" in json_filter and "le" in json_filter:
        condition = attribute.between(json_filter["ge"], json_filter["le"])
    else:
        if "ge" in json_filter:
            condition = attribute >= json_filter["ge"]
            conditions.append(condition)
        if "le" in json_filter:
            condition = attribute <= json_filter["le"]
            conditions.append(condition)

    return reduce(lambda x, y: x & y, conditions)