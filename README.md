# submitter

Submitter for jeopardy CTF-like tasks with flags

Submitter is currently written in python3. Requirements are `flask`, `uwsgi` and `psycopg2`

So, to install:
```
virtualenv -p env
. env/bin/activate
pip install flask uwsgi psycopg2
```

To run:

Test usage:
```
python main.py
```
Production usage (will open a UNIX socket, see `uwsgi.ini`):
```
uwsgi uwsgi.ini
```

## Database

SQLite and PostgreSQL are supported. SQLite will be used by default.
`SCORES_DB` environment variable can be used to configure database, it should
contain DB connection URL. See `db.py`.
