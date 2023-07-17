from peewee import *

db = PostgresqlDatabase(
    'fast', 
    user='admin',
    password='admin',
    host='localhost'
)


class BaseModel(Model):
    class Meta:
        database = db
