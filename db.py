import os
import sqlite3
import psycopg2
import psycopg2.extensions

SQLITE_SCHEMA = 'sqlite:///'
POSTGRES_SCHEMA = 'postgresql://'

DB = os.environ.get('SCORES_DB', 'sqlite:///db/scores.db')

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

class PgCursor(object):
    def __init__(self, conn, *args, **kwargs):
        self.cursor = conn.cursor(*args, **kwargs)

    def execute(self, sql, *args, **kwargs):
        return self.cursor.execute(
            sql.replace('?', '%s').replace("datetime('now')", "now()"),
            *args, **kwargs
        )

    def insert_if_not_exists(self, sql, *args, **kwargs):
        return self.execute(sql + ' on conflict do nothing', *args, **kwargs)

    def close(self):
        self.cursor.close()

    def __getattr__(self, name):
        return getattr(self.cursor, name)

class ConnectPg(object):
    def __init__(self, pg_uri):
        self.conn = psycopg2.connect(pg_uri)

    def cursor(self, *args, **kwargs):
        return PgCursor(self.conn, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.conn, name)


def connect_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute('pragma foreign_keys=ON')
    return conn

def init_db():
    db = DB

    if db.startswith(SQLITE_SCHEMA):
        db_path = db[len(SQLITE_SCHEMA):]
        connect = lambda: connect_sqlite(db_path)
        conn = connect()
        IntegrityError = sqlite3.IntegrityError
        os.chmod(db_path, 0o664)

    elif db.startswith(POSTGRES_SCHEMA):
        connect = lambda: ConnectPg(db)
        IntegrityError = psycopg2.IntegrityError
        conn = connect()
    else:
        raise Exception(
            "Unknown db schema in uri %s. Should be either %s or %s" %
                (db, SQLITE_SCHEMA, POSTGRES_SCHEMA)
            )
    create_tables(conn)
    return connect, IntegrityError

def create_tables(conn):

    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (name text primary key, value real, flag text, prefix text)''')

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (name text primary key,
                  score real,
                  active bool,
                  last_submission timestamptz)''')


    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 ("user" text, flag text, time timestamptz, ip inet)''')

    c.execute('''CREATE TABLE IF NOT EXISTS accepted_flags
                 ("user" text,
                  task text,
                  time timestamptz,
                  ip inet,
                  primary key("user", task),
                  foreign key("user") references users(name),
                  foreign key(task) references tasks(name))''')

    conn.commit()
    conn.close()

connect, IntegrityError = init_db()
