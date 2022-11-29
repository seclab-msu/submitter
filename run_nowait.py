import os
import time
import random
import threading
from subprocess import Popen, check_call

TIMEOUT = 50

def random_bytes_hexed(n_bytes):
    hex_fmt = "{:0" + str(n_bytes * 2) + "x}"
    return hex_fmt.format(random.getrandbits(n_bytes * 8))

def run_process_with_timeout(argv, timeout=TIMEOUT):
    t = time.time()
    process = Popen(argv, preexec_fn=os.setsid)
    while time.time() - t < timeout:
        if process.poll() is not None:
            return
        time.sleep(0.5)
    process.kill()
    process.wait()

def run_docker_with_timeout(container, args, docker_args, timeout=TIMEOUT):
    t = time.time()
    name = '%s-%s' % (container, random_bytes_hexed(16))
    argv = ['docker', 'run', '--name', name, '--rm']
    argv += docker_args + [container] + args
    process = Popen(argv, preexec_fn=os.setsid)
    while time.time() - t < timeout:
        if process.poll() is not None:
            return
        time.sleep(0.5)
    print('timeout exceeded: killing container', name)
    check_call(['docker', 'kill', name])
    process.wait()

def run_process_nowait(argv, timeout=TIMEOUT):
    thread = threading.Thread(
        target=run_process_with_timeout, args=(argv, timeout)
    )
    thread.start()

def run_docker_nowait(container, argv, docker_args=[], timeout=TIMEOUT):
    thread = threading.Thread(
        target=run_docker_with_timeout, args=(
            container,
            argv,
            docker_args,
            timeout
        )
    )
    thread.start()
