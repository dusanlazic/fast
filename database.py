from peewee import Model, PostgresqlDatabase, SqliteDatabase

db = PostgresqlDatabase(
    'fast', 
    user='admin',
    password='admin',
    host='localhost'
)


class BaseModel(Model):
    class Meta:
        database = db


fallbackdb = SqliteDatabase('fallback.db')


class FallbackBaseModel(Model):
    class Meta:
        database = fallbackdb
