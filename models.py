from collections import namedtuple
from peewee import CharField, DateTimeField, IntegerField, Check
from datetime import datetime
from database import BaseModel, FallbackBaseModel

class Flag(BaseModel):
    value = CharField(unique=True)
    exploit = CharField()
    player = CharField()
    tick = IntegerField()
    target = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(constraints=[Check("status IN ('queued', 'accepted', 'rejected')")])
    response = CharField(null=True)


class FallbackFlag(FallbackBaseModel):
    value = CharField()
    exploit = CharField()
    target = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(constraints=[Check("status IN ('pending', 'forwarded')")])


Batching = namedtuple('Batching', 'count size wait')

class ExploitDetails:
    def __init__(self, name, targets, module=None, run=None, prepare=None, cleanup=None, timeout=None, env=None, delay=None, batching=None):
        self.name = name
        self.targets = targets
        self.module = module
        self.run = run
        self.prepare = prepare
        self.cleanup = cleanup
        self.timeout = timeout
        self.env = env
        self.delay = delay
        self.batching = batching
