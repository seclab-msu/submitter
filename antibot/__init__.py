import os
import json
import base64
import string
import random
import hashlib
import requests

from flask import session, abort, request
from flask_session import Session

import db

DIR = os.path.dirname(__file__)

DIFFICULTY = 17
SALTS = 2

GWS = 'http://127.0.0.1:4050/'

DH_MOD = 899877779931337
DH_G = 10

PNG = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\xc2\x00\x00\x00\xbb\x08\x02\x00\x00\x00\xe0'

scripts = {}
scripts_enc = {}

sha256_obfuscated = open(os.path.join(DIR, 'sha256_obfuscated.js')).read()
solve_obfuscated = open(os.path.join(DIR, 'solve_obfuscated.js')).read()
pow_template = open(os.path.join(DIR, 'pow_template.js')).read()
dropper_template = open(os.path.join(DIR, 'dropper.js')).read()

def xor(s, key):
    res = bytearray(s)
    k = bytearray(key)
    for i in xrange(len(res)):
        res[i] = res[i] ^ k[i % len(k)]
    return str(res)

def xoriter(s, keyit):
    res = bytearray(s)
    for i in xrange(len(res)):
        res[i] = res[i] ^ ord(next(keyit))
    return str(res)

def md5_gen(k):
    idx = 0
    state = hashlib.md5(str(idx) + k).digest()
    #print hashlib.md5(str(idx) + k).hexdigest()
    while True:
        for c in state:
            yield c
        idx += 1
        state = hashlib.md5(str(idx) + state + k).digest()
        #print hashlib.md5(str(idx) + k).hexdigest()

def init_session(app):
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SQLALCHEMY_DATABASE_URI'] = db.DB
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_NAME'] = 'sc0r3board'
    Session(app)
    app.session_interface.db.create_all()

    @app.route("/s/<string:name>", methods=['GET', 'POST'])
    def get_script(name):
        if name in scripts:
            s = scripts[name]
            del scripts[name]
            return s
        elif name in scripts_enc:
            enc = scripts_enc[name]
            try:
                k_int = pow(long(request.form['n']), enc['a'], DH_MOD)
                k_hex = '{:x}'.format(k_int)
                if len(k_hex) % 2:
                    k_hex = '0' + k_hex
                k = k_hex.decode('hex')
                #print "KI: a=", enc['a'], "B=", long(request.form['n']), "K=",k_int
                #print 'K', [ord(c) for c i]n
                return PNG + xoriter(enc['data'], md5_gen(k))
            except Exception, e:
                print e
        abort(404)

def bad():
    return random.choice(['ok', 'again', 'no such flag'])

def random_bytes(N):
    return (('{:0%dx}' % (N * 2)) .format(random.getrandbits(N * 8))).decode('hex')

def random_string(alphabet, N):
    return ''.join(random.choice(alphabet) for _ in range(N))

def check_user_agent(request):
    BAD = [
        'curl',
        'python-requests',
        'urllib'
    ]
    ua = request.headers.get('User-Agent', '')
    if not('Mozilla' in ua or 'Opera' in ua) or any(bad in ua for bad in BAD):
        return False
    return True

def check_referer(request):
    return bool(request.headers.get('Referer', ''))

def make_pow():
    salts = [
        map(ord, random_bytes(random.randint(20, 30))) for _ in xrange(SALTS)
    ]
    respkey = random_bytes(20)
    powkey = random_string(string.lowercase, 5)

    return {
        'salts': salts,
        'respkey': respkey,
        'key': powkey
    }

def gen_pow_script(pow_params):
    pow_script = pow_template \
        .replace('{salts}', json.dumps(pow_params['salts'])) \
        .replace('{difficulty}', str(DIFFICULTY)) \
        .replace('{paramname}', pow_params['key']) \
        .replace('{respkey}', repr(pow_params['respkey']))

    return sha256_obfuscated + '\n' + solve_obfuscated + '\n' + pow_script

def gen_dropper(url, a):
    A = pow(DH_G, a, DH_MOD)
    #print 'A', A, '(a ', a, ')'
    return dropper_template.replace('{A}', str(A)).replace('{url}',url)

def send_script(scr):
    try:
        res = requests.post(GWS, data=scr)
        if res.status_code != 200:
            raise Exception(
                'Bad resp from GWS: %d %s',
                res.status_code,
                repr(res.content)
            )
        path = res.content
        print 'Used GWS to store script, path is', path
        return path
    except Exception, ex:
        print 'Failed to use GWS, fallback', ex
    name = random_string(string.ascii_letters + string.digits, 10)
    scripts[name] = scr
    return 's/' + name

def send_script_enc(scr):
    a = random.randint(101501510104175, DH_MOD)
    try:
        res = requests.post(GWS + '?a='+str(a), data=scr)
        if res.status_code != 200:
            raise Exception(
                'Bad resp from GWS: %d %s',
                res.status_code,
                repr(res.content)
            )
        path = res.content
        print 'Used GWS to store enc script, path is', path
        return path, a
    except Exception, ex:
        print 'Failed to use GWS, fallback', ex
    name = random_string(string.ascii_letters + string.digits, 10)
    scripts_enc[name] = {
        'a': a, 'data': scr
    }
    return 's/' + name, a

def check_solution(pow_params, solution):
    salts = pow_params['salts']
    if len(solution) != len(salts):
        return False
    for i in xrange(len(salts)):
        hash_hex = hashlib.sha256(''.join(map(chr, salts[i] + solution[i]))).hexdigest()
        hash_bits = '{:0256b}'.format(int(hash_hex, 16))
        if any(bit != '0' for bit in hash_bits[:DIFFICULTY]):
            return False
    return True

def check(request):
    if not check_user_agent(request):
        return bad()
    if not check_referer(request):
        return bad()
    if 'pow' not in session:
        session['pow'] = make_pow()
        return 'again'
    sid = session.sid
    pow_params = session['pow']
    key = pow_params['key']
    if key not in request.form:
        print 'give ', DIFFICULTY, 'bits', len(pow_params['salts']), 'hashes to', sid
        pow_script, a = send_script_enc(gen_pow_script(pow_params))
        return 'accepted ' + send_script(gen_dropper(pow_script, a))
    pow_resp = request.form[key]
    try:
        decrypted = xor(base64.b64decode(pow_resp), pow_params['respkey'])
        solution = json.loads(decrypted)
    except Exception, ex:
        print sid, pow_resp, pow_params['respkey']
        print 'decr', repr(decrypted)
        print ex
        return bad()
    finally:
        # regen pow anyway
        session['pow'] = make_pow()
    if not check_solution(pow_params, solution):
        print 'POW FAILED', sid, pow_resp, pow_params, decrypted
        return bad()
    print 'good pow from', sid