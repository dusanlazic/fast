from collections import namedtuple
from peewee import CharField, DateTimeField, IntegerField, UUIDField, BooleanField, Check, SQL
from datetime import datetime
from database import ServerBaseModel, ClientBaseModel


class Flag(ServerBaseModel):
    value = CharField(unique=True)
    exploit = CharField()
    player = CharField()
    tick = IntegerField()
    target = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(
        constraints=[Check("status IN ('queued', 'accepted', 'rejected')")])
    response = CharField(null=True)


class Webhook(ServerBaseModel):
    id = UUIDField(primary_key=True)
    exploit = CharField()
    player = CharField()
    disabled = BooleanField(default=False)


class FallbackFlag(ClientBaseModel):
    value = CharField()
    exploit = CharField()
    target = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(
        constraints=[Check("status IN ('pending', 'forwarded')")])


class Attack(ClientBaseModel):
    host = CharField(null=False)
    flag_id = CharField(null=True)

    class Meta:
        constraints = [SQL('UNIQUE(host, flag_id)')]


Batching = namedtuple('Batching', 'count size wait')


class ExploitDefinition:
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


DigestValuePair = namedtuple('DigestValuePair', 'digest value')
