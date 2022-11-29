import os
import sys
import sqlite3
from subprocess import check_call

from db import connect

def get_tasks(conn):
    c = conn.cursor()
    c.execute('select name from tasks')
    result = [row[0] for row in c.fetchall()]
    c.close()
    return result

def get_flag(conn, task):
    c = conn.cursor()
    c.execute(
        'select flag from tasks where name = ?',
        (task, )
    )
    result = c.fetchone()[0]
    c.close()
    return result

if __name__ == "__main__":
    conn = connect()
    if len(sys.argv) > 1:
        tasks = [sys.argv[1]]
    else:
        tasks = get_tasks(conn)
        print('will reset flags for all tasks:', tasks)
    flags = {task: get_flag(conn, task) for task in tasks}
    conn.close()
    for task in tasks:
        print('resetting flag for task', task, '(to value', flags[task], ')')
        check_call([
            'python3',
            'change_flag.py',
            str(0),
            task,
            flags[task]
        ], preexec_fn=os.setsid)
        print('done')

