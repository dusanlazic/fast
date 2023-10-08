import os
from peewee import Model, DatabaseProxy, SqliteDatabase

db = DatabaseProxy()


class ServerBaseModel(Model):
    class Meta:
        database = db


sqlite_db = SqliteDatabase(os.path.join('.fast', 'fast.db'))


class ClientBaseModel(Model):
    class Meta:
        database = sqlite_db
