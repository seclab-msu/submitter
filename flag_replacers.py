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
    }
}

REPLACE_FUNCS = {}

DOCKER_EXEC = shlex.split('docker exec -i -t')
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


REPLACE_FUNCS['their-sql-mysql'] = replace_flag_in_their_mysql
REPLACE_FUNCS['their-sql-node'] = replace_flag_in_their_node