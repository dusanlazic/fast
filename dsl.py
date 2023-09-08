from datetime import datetime, timedelta
from models import Flag
from pyparsing import *

# Parsing formats
def parse_timedelta(tokens):
    tokens = tokens[0]
    value = int(tokens[0])
    unit = tokens[1].lower()
    if unit in seconds:
        return datetime.now() - timedelta(seconds=value)
    if unit in minutes:
        return datetime.now() - timedelta(minutes=value)
    if unit in hours:
        return datetime.now() - timedelta(hours=value)

def parse_time(tokens):
    tokens = tokens[0]
    hour = int(tokens[0])
    minute = int(tokens[1])
    second = int(tokens[2]) if len(tokens) > 2 else 0

    return datetime.now().replace(
        hour=hour,
        minute=minute,
        second=second,
        microsecond=0
    )

# Symbols
and_ = ['and', '&', '&&', ',']
or_ = ['or', '|', '||']
not_ = ['not', '~', '!']
eq = ['==', '=', 'equals', 'eq', 'is']
ne = ['!=', '<>', 'not equals', 'ne', 'is not']
gt = ['>', 'gt', 'over', 'above', 'greater than']
lt = ['<', 'lt', 'under', 'below', 'less than']
ge = ['>=', 'ge', 'min', 'not under', 'not below', 'after']
le = ['<=', 'le', 'max', 'not over', 'not above', 'before']
between = ['between']
matches = ['matches', 'matching', 'regex']
in_ = ['in', 'of']
not_in = ['not in', 'not of']
contains = ['contains', 'containing']
starts = ['starts with', 'starting with', 'begins with', 'beginning with']
ends = ['ends with', 'ending with']
seconds = ['s', 'sec', 'second', 'seconds']
minutes = ['m', 'min', 'mins', 'minute', 'minutes']
hours = ['h', 'hour', 'hours']

comparisons = eq + ne + gt + lt + ge + le
wildcards = contains + starts + ends
time_units = seconds + minutes + hours

# Field
field = Word(alphas, alphanums)

# Values
value = QuotedString(quoteChar='"', unquoteResults=True, escChar='\\') | QuotedString(quoteChar="'", unquoteResults=True, escChar='\\') | Word(printables, excludeChars='[](),')
value_list = Group(Suppress('[') + DelimitedList(value, delim=',', allow_trailing_delim=True) + Suppress(']'), aslist=True)
value_timedelta = Group(Word(nums) + one_of(time_units, caseless=True) + Suppress(CaselessKeyword('ago'))).set_parse_action(parse_timedelta)
value_time = Group(Regex('2[0-3]|[01]?\d') + Suppress(one_of(': - ')) + Regex('[0-5]?\d') + Optional(Suppress(one_of(': - ')) + Regex('[0-5]?\d'))).set_parse_action(parse_time)
value_instant = value_time | value_timedelta
value_range = Group(Suppress('[') + value_instant + Suppress(',') + value_instant + Suppress(']')) | \
              Group(value_instant + Suppress(CaselessKeyword('and')) + value_instant) | \
              Group(Suppress('[') + value + Suppress(',') + value + Suppress(']')) | \
              Group(value + Suppress(CaselessKeyword('and')) + value)

# Conditions
wildcard_condition = Group(field + one_of(wildcards, caseless=True) + value)
matches_condition = Group(field + one_of(matches, caseless=True) + value)
compare_condition = Group(field + one_of(comparisons, caseless=True) + (value_instant | value))
between_condition = Group(field + one_of(between, caseless=True) + value_range)
in_condition = Group(field + one_of(in_ + not_in, caseless=True) + value_list)

condition = wildcard_condition | matches_condition | compare_condition | between_condition | in_condition

# Logical operators
NOT = one_of(not_, caseless=True)
AND = one_of(and_, caseless=True)
OR = one_of(or_, caseless=True)

def makeLRlike(numterms):
    if numterms is None:
        initlen = 2
        incr = 1
    else:
        initlen = {0:1,1:2,2:3,3:5}[numterms]
        incr = {0:1,1:1,2:2,3:4}[numterms]

    def pa(s,l,t):
        t = t[0]
        if len(t) > initlen:
            ret = t[:initlen]
            i = initlen
            while i < len(t):
                ret = [ret] + t[i:i+incr]
                i += incr
            return [ret]
    return pa

boolean_condition = infixNotation(
    condition,
    [
        (NOT, 1, opAssoc.RIGHT, makeLRlike(None)),
        (AND, 2, opAssoc.LEFT, makeLRlike(2)),
        (OR, 2, opAssoc.LEFT, makeLRlike(2))
    ]
)

def build_query(tree):
    if len(tree) == 2 and tree[0] in not_:
        return ~(build_query(tree[1]))

    if isinstance(tree, str):
        return tree
    
    if len(tree) == 3 and isinstance(tree[0], str):
        field, relation, value = tree
        rel = relation.lower()

        if rel in eq:
            return (getattr(Flag, field) == value)
        elif rel in ne:
            return (getattr(Flag, field) != value)
        elif rel in lt:
            return (getattr(Flag, field) < value)
        elif rel in gt:
            return (getattr(Flag, field) > value)
        elif rel in le:
            return (getattr(Flag, field) <= value)
        elif rel in ge:
            return (getattr(Flag, field) >= value)
        elif rel in matches:
            return (getattr(Flag, field).regexp(value))
        elif rel in in_:
            return (getattr(Flag, field).in_(value))
        elif rel in not_in:
            return (getattr(Flag, field).not_in(value))
        elif rel in contains:
            return (getattr(Flag, field).contains(value))
        elif rel in starts:
            return (getattr(Flag, field).startswith(value))
        elif rel in ends:
            return (getattr(Flag, field).endswith(value))
        elif rel in between:
            return (getattr(Flag, field).between(*value))
    
    left, operator, right = tree
    if operator.lower() in and_:
        return (build_query(left) & build_query(right))
    elif operator.lower() in or_:
        return (build_query(left) | build_query(right))


def parse_query(input):
    return boolean_condition.parse_string(input)[0]
