from peewee import CharField, DateTimeField, IntegerField, Check
from datetime import datetime
from database import BaseModel

class Flag(BaseModel):
    value = CharField()
    exploit_name = CharField()
    target_ip = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(constraints=[Check("status IN ('queued', 'accepted', 'declined')")])
    comment = CharField(null=True)


class ExploitDetails:
    def __init__(self, name, targets, cmd=None, timeout=None, env=None):
        self.name = name
        self.targets = targets
        self.cmd = cmd
        self.timeout = timeout
        self.env = env