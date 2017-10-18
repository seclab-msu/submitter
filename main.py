from flask import Flask, request, render_template
from subprocess import Popen, PIPE
import sqlite3
import os
import random
from time import time
from traceback import print_exc


DB = os.environ.get('SCORES_DB_PATH', 'db/scores.db')

app = Flask(__name__)

CHANGE_DELAY = 20

generate_flag = lambda: '%030x' % random.randrange(16**30)

def init_db():
    conn = sqlite3.connect(DB)
    os.chmod(DB, 0664)
    conn.execute('pragma foreign_keys=ON')

    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (name text primary key, value real, flag text, prefix text)''')

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 ( name text primary key, score real)''')


    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (user text, flag text)''')

    c.execute('''CREATE TABLE IF NOT EXISTS accepted_flags
                 (user text,
                  task text,
                  primary key(user, task),
                  foreign key(user) references users(name),
                  foreign key(task) references tasks(name))''')

    conn.commit()
    conn.close()

def delayed_change_flag(task, task_prefix):
    new_flag = generate_flag()

    if task_prefix is not None:
        new_flag = task_prefix + '_' + new_flag

    print 'starting process'

    Popen([
        'python',
        'change_flag.py',
        str(CHANGE_DELAY),
        task,
        new_flag
    ], preexec_fn=os.setsid)

    print 'started process'

def get_scores():
    conn = sqlite3.connect(DB)
    conn.execute('pragma foreign_keys=ON')

    c = conn.cursor()

    result = c.execute('select name, score from users order by score desc').fetchall()

    conn.commit()
    conn.close()

    return result

def check_user(name, cursor):
    try:
        cursor.execute("insert into users values (?, 0)", (name,))
    except sqlite3.IntegrityError:
        pass

def register_flag(user, flag):
    conn = sqlite3.connect(DB)
    conn.execute('pragma foreign_keys=ON')

    c = conn.cursor()

    try:
        c.execute("insert into submissions values (?, ?)", (user, flag))

        task = c.execute(
            "select name, value, prefix from tasks where flag = ?", (flag,)
        ).fetchone()

        if task is None:
            return 'no such flag'

        task_name, task_value, task_prefix = task

        check_user(user, c)

        c.execute(
            "insert into accepted_flags values (?, ?)", (user, task_name)
        )
        c.execute(
            "update users set score = score + ? where name = ?",
            (task_value, user)
        )
        print 'running change flag'
        delayed_change_flag(task_name, task_prefix)
        print 'done running change flag'
        return 'ok'
    except sqlite3.IntegrityError:
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

    try:
        return register_flag(user, flag)
    except:
        print_exc()
        raise ex


init_db()

if __name__ == "__main__":
    app.run(port=8080)
