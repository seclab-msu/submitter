import os
from flask import Flask, request, render_template, abort
import random
from time import time
import datetime
from traceback import print_exc

from db import connect, IntegrityError
from run_nowait import run_process_nowait

app = Flask(__name__)

CHANGE_DELAY = 0
USE_REGISTRATION = bool(int(os.getenv('USE_REGISTRATION', '1')))
USE_FLAG_REPLACER = True

generate_flag = lambda: '%030x' % random.randrange(16**30)

def delayed_change_flag(task, task_prefix):
    new_flag = generate_flag()

    if task_prefix is not None:
        if task_prefix.startswith('const'):
            print('not changing flag because prefix starts with const')
            return
        new_flag = task_prefix + '_' + new_flag

    print('starting process')
    run_process_nowait([
        'python3',
        'change_flag.py',
        str(CHANGE_DELAY),
        task,
        new_flag
    ])
    print('started process')

def get_scores():
    conn = connect()
    c = conn.cursor()

    try:
        c.execute('''
                select name, coalesce(sum(accepted_flags.score), 0) as score
                from users
                left outer join accepted_flags on users.name = accepted_flags.user
                where active=true
                group by name
                order by score desc
        ''')
        return [(name, score) for name, score in c.fetchall()]
    finally:
        conn.close()

def check_user_active(name):
    conn = connect()
    c = conn.cursor()

    try:
        c.execute("select active from users where name=?", (name,))
        res = c.fetchone()
        if res:
            return res[0]
    except IntegrityError as e:
        print("Some error,  while check_user_active", e)
        return False
    c.close()

def check_user(name, cursor):
    if hasattr(cursor, 'insert_if_not_exists'):
        cursor.insert_if_not_exists("insert into users values (?, false)", (name,))
    else:
        try:
            cursor.execute("insert into users (name, active) values (?, false)", (name,))
        except IntegrityError:
            pass

def register_user(name):
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute("insert into users (name, active) values (?, false)", (name,))
        return "ok"
    except IntegrityError:
        return "user exists"
    finally:
        conn.commit()
        conn.close()

def register_flag(user, flag, user_ip):
    conn = connect()

    now = datetime.datetime.now(tz=datetime.timezone.utc)

    c = conn.cursor()

    try:
        c.execute("insert into submissions values (?, ?, ?, ?::inet)", (user, flag, now, user_ip))

        c.execute(
            "select name, value, prefix from tasks where flag = ?", (flag,)
        )

        task = c.fetchone()

        if task is None:
            return 'no such flag'

        task_name, task_value, task_prefix = task

        if not USE_REGISTRATION:
            check_user(user, c)

        c.execute(
            "insert into accepted_flags values (?, ?, ?, ?, ?::inet)",
            (user, task_name, task_value, now, user_ip)
        )
        if USE_FLAG_REPLACER:
            print('running change flag')
            delayed_change_flag(task_name, task_prefix)
            print('done running change flag')
        return 'ok'
    except IntegrityError:
        return 'already'
    finally:
        conn.commit()
        conn.close()


@app.route("/")
def main():
    try:
        return render_template('index.html',
                               scores=get_scores(),
                               registration=USE_REGISTRATION)
    except:
        print_exc()
        raise

@app.route("/register", methods=['POST'])
def register():
    if not USE_REGISTRATION:
        abort(403)

    user = request.form['user'].strip()

    return register_user(user)

@app.route("/submit", methods=['POST'])
def submit():
    user = request.form['user'].strip()
    flag = request.form['flag'].strip()
    user_ip = request.remote_addr

    if user == '':
        return 'no name'

    if len(user) > 150:
        return 'too long'

    if USE_REGISTRATION:
        if not check_user_active(user):
            return "user inactive"

    try:
        return register_flag(user, flag, user_ip)
    except:
        print_exc()
        raise

if __name__ == "__main__":
    app.run(port=8080)
