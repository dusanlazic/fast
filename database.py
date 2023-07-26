from peewee import Model, Proxy, PostgresqlDatabase, SqliteDatabase

db = Proxy()


class BaseModel(Model):
    class Meta:
        database = db


fallbackdb = SqliteDatabase('fallback.db')


class FallbackBaseModel(Model):
    class Meta:
        database = fallbackdb
