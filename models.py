from peewee import CharField, DateTimeField, IntegerField, Check
from datetime import datetime
from database import BaseModel

class Flag(BaseModel):
    value = CharField()
    exploit_name = CharField()
    target_ip = CharField()
    timestamp = DateTimeField(default=datetime.now)
    tick_number = IntegerField()
    status = CharField(constraints=[Check("status IN ('queued', 'accepted', 'declined')")])
    comment = CharField(null=True)
