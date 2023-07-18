from peewee import CharField, DateTimeField, IntegerField, Check
from datetime import datetime
from database import BaseModel

class Flag(BaseModel):
    value = CharField()
    exploit = CharField()
    target = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(constraints=[Check("status IN ('queued', 'accepted', 'rejected')")])
    comment = CharField(null=True)


class ExploitDetails:
    def __init__(self, name, targets, module=None, cmd=None, timeout=None, env=None, delay=None):
        self.name = name
        self.targets = targets
        self.module = module
        self.cmd = cmd
        self.timeout = timeout
        self.env = env
        self.delay = delay
