from peewee import *

db = SqliteDatabase('flags.db')

class BaseModel(Model):
    class Meta:
        database = db
