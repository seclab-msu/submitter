import os
from flask import Flask, request, render_template
import random
from time import time
from datetime import datetime
from traceback import print_exc

from db import connect, IntegrityError
from run_nowait import run_process_nowait

app = Flask(__name__)

CHANGE_DELAY = 0
USE_ANTIBOT = bool(int(os.getenv('USE_ANTIBOT', '1')))

if USE_ANTIBOT:
    from antibot import check, init_session
    init_session(app)

generate_flag = lambda: '%030x' % random.randrange(16**30)

def delayed_change_flag(task, task_prefix):
    new_flag = generate_flag()

    if task_prefix is not None:
        if task_prefix.startswith('const'):
            print 'not changing flag because prefix starts with const'
            return
        new_flag = task_prefix + '_' + new_flag

    print 'starting process'
    run_process_nowait([
        'python',
        'change_flag.py',
        str(CHANGE_DELAY),
        task,
        new_flag
    ])
    print 'started process'

def get_scores():
    conn = connect()
    c = conn.cursor()

    try:
        c.execute('select name, score from users order by score desc, last_submission')
        return [(name, score) for name, score in c.fetchall()]
    finally:
        conn.close()

def check_user(name, cursor):
    if hasattr(cursor, 'insert_if_not_exists'):
        cursor.insert_if_not_exists("insert into users values (?, 0)", (name,))
    else:
        try:
            cursor.execute("insert into users (name, score) values (?, 0)", (name,))
        except IntegrityError:
            pass

def register_flag(user, flag):
    conn = connect()

    now = datetime.now()

    c = conn.cursor()

    try:
        c.execute("insert into submissions values (?, ?, ?)", (user, flag, now))

        c.execute(
            "select name, value, prefix from tasks where flag = ?", (flag,)
        )

        task = c.fetchone()

        if task is None:
            return 'no such flag'

        task_name, task_value, task_prefix = task

        check_user(user, c)

        c.execute(
            "insert into accepted_flags values (?, ?, ?)",
            (user, task_name, now)
        )
        c.execute(
            "update users set score = score + ?, last_submission = datetime('now') where name = ?",
            (task_value, user)
        )
        print 'running change flag'
        delayed_change_flag(task_name, task_prefix)
        print 'done running change flag'
        return 'ok'
    except IntegrityError:
        return 'already'
    finally:
        conn.commit()
        conn.close()


@app.route("/")
def main():
    try:
        return render_template('index.html', scores=get_scores())
    except:
        print_exc()
        raise

@app.route("/submit", methods=['POST'])
def submit():
    user = request.form['user'].strip()
    flag = request.form['flag'].strip()

    if user == '':
        return 'no name'

    if len(user) > 150:
        return 'too long'

    if USE_ANTIBOT:
        res = check(request)
        if res:
            return res
    try:
        return register_flag(user, flag)
    except:
        print_exc()
        raise

if __name__ == "__main__":
    app.run(port=8080)
