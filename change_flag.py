import sys
import os
import sqlite3
import base64
from time import sleep

from flag_replacers import REPLACE_FUNCS
from db import connect

def replace_flag(task, flag):
    REPLACE_FUNCS[task](task, flag)

def change_flag(delay, task, flag):
    sleep(delay)

    replace_flag(task, flag)

    conn = connect()

    c = conn.cursor()

    users = c.execute('update tasks set flag=? where name = ?', (flag, task))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    delay = int(sys.argv[1])
    task = sys.argv[2]
    flag = sys.argv[3]
    change_flag(delay, task, flag)
