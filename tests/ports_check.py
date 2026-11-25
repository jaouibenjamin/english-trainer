#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The suites start their own servers on free ports and never use one that is already listening.

    python3 tests/ports_check.py

Needs only python3 and node (no browser). It proves: two imports get different ports; the servers that are started
serve this checkout and the mock backend answers on its own port; and when a port is already taken, the run stops and
says so instead of going on against a server it did not start."""
import json, os, socket, subprocess, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
fails = []


def check(label, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + label + (' ' + str(extra) if extra else ''), flush=True)
    if not ok: fails.append(label)


def child(code):
    return subprocess.run([sys.executable, '-c', 'import sys;sys.argv=["x"];sys.path.insert(0,%r)\n' % HERE + code], capture_output=True, text=True, timeout=60)


def main():
    a = child('import play;print(play.PORT,play.API_PORT)').stdout.split()
    b = child('import play;print(play.PORT,play.API_PORT)').stdout.split()
    check('each run picks its own ports, different for the pages and the mock backend', len(a) == 2 and len(b) == 2 and a[0] != a[1] and a != b and '8791' not in a + b and '8765' not in a + b, (a, b))

    import play as P
    procs = P.start_servers(mock=True)
    try:
        page = urllib.request.urlopen(f'http://127.0.0.1:{P.PORT}/tests/ports_check.py', timeout=5).read()
        check('the test server serves this checkout', page == open(os.path.abspath(__file__), 'rb').read())
        r = json.loads(urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{P.API_PORT}/', data=json.dumps({'a': 'login', 'c': 'EN-1234', 'n': 'x', 'p': '0000'}).encode()), timeout=5).read())
        check('the mock backend answers on its own port', r.get('ok') is False and 'e' in r, r)
    finally:
        for p in procs: p.terminate()
        for p in procs: p.wait(timeout=10)
    check('the servers are gone when the run ends', not P.port_open(P.PORT) and not P.port_open(P.API_PORT))

    # a port that is already taken: the run must stop and say why
    for which in ('PORT', 'API_PORT'):
        r = child(f'''import socket,play
s=socket.socket();s.bind(('127.0.0.1',play.{which}));s.listen(1)
play.start_servers(mock=True)
print('went on')''')
        check(f'a taken {"page" if which == "PORT" else "mock backend"} port stops the run with a message', r.returncode != 0 and 'went on' not in r.stdout and 'already in use' in r.stderr, (r.returncode, r.stderr.strip()[-160:]))
    r = child('''import play
play.MOCK='/nonexistent/mock.js'
play.start_servers(mock=True)
print('went on')''')
    check('a mock backend that does not come up stops the run with a message', r.returncode != 0 and 'went on' not in r.stdout and 'did not start' in r.stderr, (r.returncode, r.stderr.strip()[-160:]))
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
