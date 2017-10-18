import os
import sys
import sqlite3
from subprocess import check_call

DB = os.environ.get('SCORES_DB_PATH', 'db/scores.db')

def connect():
    conn = sqlite3.connect(DB)
    conn.execute('pragma foreign_keys=ON')
    return conn

def get_tasks(conn):
    c = conn.cursor()
    tasks_query = c.execute('select name from tasks')
    result = [row[0] for row in tasks_query]
    c.close()
    return result

def get_flag(conn, task):
    c = conn.cursor()
    flag_query = c.execute(
        'select flag from tasks where name = ?',
        (task, )
    )
    result = next(flag_query)[0]
    c.close()
    return result

if __name__ == "__main__":
    conn = connect()
    if len(sys.argv) > 1:
        tasks = [sys.argv[1]]
    else:
        tasks = get_tasks(conn)
        print 'will reset flags for all tasks:', tasks
    flags = {task: get_flag(conn, task) for task in tasks}
    conn.close()
    for task in tasks:
        print 'resetting flag for task', task, '(to value', flags[task], ')'
        check_call([
            'python',
            'change_flag.py',
            str(0),
            task,
            flags[task]
        ], preexec_fn=os.setsid)
        print 'done'

