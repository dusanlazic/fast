from models import Flag
from pyparsing import *

# Symbols
and_ = ['and', '&', '&&', ',']
or_ = ['or', '|', '||']
not_ = ['not', '~', '!']
eq = ['==', '=', 'equals', 'eq', 'is']
ne = ['!=', '<>', 'not equals', 'ne', 'is not']
gt = ['>', 'gt', 'over', 'above', 'greater than']
lt = ['<', 'lt', 'under', 'below', 'less than']
ge = ['>=', 'ge', 'min', 'not under', 'not below']
le = ['<=', 'le', 'max', 'not over', 'not above']

comparisons = eq + ne + gt + lt + ge + le

# Field
field = Word(alphas, alphanums)

# Values
value = QuotedString(quoteChar='"', unquoteResults=True, escChar='\\') | Word(printables, excludeChars='[](),')
value_list = Group(Suppress('[') + DelimitedList(value, delim=',', allow_trailing_delim=True) + Suppress(']'), aslist=True)

# Conditions
matches_condition = Group(field + one_of(['matches'], caseless=True) + value)
compare_condition = Group(field + one_of(comparisons, caseless=True) + value)
in_condition = Group(field + one_of(['in', 'not in'], caseless=True) + value_list)

condition = matches_condition | compare_condition | in_condition

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
        if relation.lower() in eq:
            return (getattr(Flag, field) == value)
        elif relation.lower() in ne:
            return (getattr(Flag, field) != value)
        elif relation.lower() in lt:
            return (getattr(Flag, field) < value)
        elif relation.lower() in gt:
            return (getattr(Flag, field) > value)
        elif relation.lower() in le:
            return (getattr(Flag, field) <= value)
        elif relation.lower() in ge:
            return (getattr(Flag, field) >= value)
        elif relation.lower() == 'matches':
            return (getattr(Flag, field).regexp(value))
        elif relation.lower() == 'in':
            return (getattr(Flag, field).in_(value))
        elif relation.lower() == 'not in':
            return (getattr(Flag, field).not_in(value))
    
    left, operator, right = tree
    if operator.lower() in and_:
        return (build_query(left) & build_query(right))
    elif operator.lower() in or_:
        return (build_query(left) | build_query(right))


def parse_query(input):
    return boolean_condition.parse_string(input)[0]
