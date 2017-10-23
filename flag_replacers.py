import json
import shlex
import subprocess
from collections import defaultdict

CONFIG = {
    'mysql_root_password': 'njf3g439gugre',
    'their_mysql1': {
        'container': 'hse-hw-their-app1',
        'db_name': 'test',
        'pass_table_name': 'passes',
        'admin_id': '1'
    },
    'their_mysql2': {
        'container': 'hse-hw-their-app2',
        'db_name': 'users_db',
        'pass_table_name': 'user_password',
        'admin_id': '0'
    },
    'their_node': {
        'container': 'hse-hw-their-app4',
        'db_path': '/var/www/site/userInfoDB.db',
        'pass_table_name': 'paroli',
        'admin_id': '0'
    },
    'xxe_indirect': {
        'container': 'xxe2',
        'db_path': '/tmp/registrations.db'
    },
    'php_xss_sqli_rce': {
        'cookies_path': '/home/asterite/xss-bot/runner/ibank/cookies.json'
    },
    'php_xss_sqli_rce_sql': {
        'container': 'php-xss-sqli-rce',
        'mysql_root_password': 'Admin2015'
    },
    'php_xss_sqli_rce_rce': {
        'container': 'php-xss-sqli-rce',
        'flag_path': '/etc/security/you/pwned/this/server/not/bad/flag'
    }

}

REPLACE_FUNCS = {}

DOCKER_EXEC = ['docker', 'exec']
UPDATE_QUERY_TPL = "UPDATE %s SET password = '%s' WHERE id = %s"


#REPLACE_FUNCS = defaultdict(lambda: default_replace_flag)

#def default_replace_flag(task, flag):
#    task_dir = '../' + task + '/'
#    template_filename = task_dir + '.flag_template'
#    flag_filename = task_dir + 'flag'
#    with open(template_filename) as template_file, open(flag_filename, 'w') as flag_file:
#        template = template_file.read()
#        flag_file.write(template.format(flag=flag))

def replace_flag_in_their_mysql(task, flag):
    for task_part in ['their_mysql1', 'their_mysql2']:
        config = CONFIG[task_part]
        query = UPDATE_QUERY_TPL % (
            config['pass_table_name'],
            flag,
            config['admin_id']
        )
        update_db = DOCKER_EXEC + [
            config['container'], 'mysql', '-u', 'root',
            '-p' + CONFIG['mysql_root_password'], config['db_name'], '-e', query
        ]
        print 'updating flag in', task_part, 'using command', update_db
        subprocess.check_call(update_db)

def replace_flag_in_their_node(task, flag):
    config = CONFIG['their_node']

    query = UPDATE_QUERY_TPL % (
        config['pass_table_name'],
        flag,
        config['admin_id']
    )
    update_db = DOCKER_EXEC + [
        config['container'], 'sqlite3', config['db_path'], query
    ]
    print 'updating flag in their_node using command', update_db
    subprocess.check_call(update_db)

def replace_flag_in_xxe_indirect(task, flag):
    config = CONFIG['xxe_indirect']

    query = "UPDATE secret SET flag = '%s'" % flag
    update_db = DOCKER_EXEC + [
        config['container'], 'sqlite3', config['db_path'], query
    ]
    print 'updating flag in bonus xxe_indirect using command', update_db
    subprocess.check_call(update_db)

def replace_flag_in_php_sqli_rce(task, flag):
    cookies_path = CONFIG['php_xss_sqli_rce']['cookies_path'];

    with open(cookies_path) as cookies_file:
        bot_cookies = json.load(cookies_file)

    for cookie in bot_cookies:
        if cookie['name'] == 'flag':
            cookie['value'] = flag

    print "updating flag in bot's cookie (internet bank)"

    with open(cookies_path, 'w') as cookies_file:
        json.dump(bot_cookies, cookies_file, indent=4)

def replace_flag_in_php_sqli_rce_sql(task, flag):
    config = CONFIG['php_xss_sqli_rce_sql']
    query = "UPDATE important_bank_data set flag = '%s'" % flag
    update_db = DOCKER_EXEC + [
        config['container'], 'mysql', '-u', 'root',
        '-p' + config['mysql_root_password'], 'bank', '-e', query
    ]
    print 'updating mysql flag in internet bank using command', update_db
    subprocess.check_call(update_db)

def replace_flag_in_php_sqli_rce_rce(task, flag):
    config = CONFIG['php_xss_sqli_rce_rce']
    change_flag_command = 'echo %s > %s' % (flag, config['flag_path'])
    update_flag = DOCKER_EXEC + [
        config['container'], 'bash', '-c', change_flag_command
    ]
    print 'updating rce flag in internet bank using command', update_flag
    subprocess.check_call(update_flag)

REPLACE_FUNCS['their-sql-mysql'] = replace_flag_in_their_mysql
REPLACE_FUNCS['their-sql-node'] = replace_flag_in_their_node
REPLACE_FUNCS['bonus-xxe-example-indirect'] = replace_flag_in_xxe_indirect
REPLACE_FUNCS['php-xss-sqli-rce'] = replace_flag_in_php_sqli_rce
REPLACE_FUNCS['php-xss-sqli-rce-sql'] = replace_flag_in_php_sqli_rce_sql
REPLACE_FUNCS['php-xss-sqli-rce-rce'] = replace_flag_in_php_sqli_rce_rce