#!/usr/bin/env python3
"""The download code of the build scripts against a made-up storage on this machine: python3 tests/storage_check.py
Whatever goes wrong (a redirect, an error status, wrong bytes, a file that is too large), the script must refuse, keep
nothing in the cache, and say which file and what happened without printing any part of the storage's address.
No network beyond 127.0.0.1. tests/voice_local.py needs numpy; without it only tests/assets_local.py is checked."""
import contextlib, http.server, io, os, sys, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets_local as A

FOLDER = 'user_' + 'Zz9Yy8Xx7Ww6Vv5Uu4'           # a made-up account folder
fails = []


def check(ok, what, info=''):
    print(('PASS ' if ok else 'FAIL ') + what, info if not ok else '')
    if not ok:
        fails.append(what)


class Fake(http.server.BaseHTTPRequestHandler):
    mode = 'redirect'
    def do_GET(self):
        if Fake.mode == 'redirect':
            self.send_response(302); self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/{FOLDER}/elsewhere/x.png'); self.end_headers()
        elif Fake.mode == 'gone':
            self.send_response(404); self.end_headers()
        else:
            body = b'not the file' if Fake.mode == 'wrong' else b'x' * 4096
            self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass


def attempt(fetch, row, cache):
    """(what the script said, what it left in the cache)"""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            fetch(row, cache); said = 'no error'
        except BaseException as e:
            said = f'{type(e).__name__}: {e}'
    return said + out.getvalue(), os.listdir(cache)


def main():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_port}/{FOLDER}/'
    secret = [FOLDER, FOLDER.lower(), str(srv.server_port), '127.0.0.1', 'elsewhere']
    os.environ['no_proxy'] = os.environ['NO_PROXY'] = '127.0.0.1'
    mods = [('assets_local', A, [r for r in A.read_manifest() if r['kind'] == 'hero-pic'][0])]
    try:
        import voice_local as V
        mods.append(('voice_local', V, [r for r in V.read_manifest() if r['kind'] == 'narr-he'][0]))
    except ImportError:
        print('note: numpy is not installed, tests/voice_local.py is not checked here')
    for name, M, row in mods:
        M.BASE = base
        for mode, word in (('redirect', 'redirect'), ('gone', '404'), ('wrong', 'src_sha256')):
            Fake.mode = mode
            with tempfile.TemporaryDirectory() as cache:
                said, left = attempt(M.fetch, dict(row), cache)
            stem = os.path.basename(row['file']).rsplit('.', 1)[0]
            check(said != 'no error' and word in said and stem in said, f'{name}: a storage that answers with "{mode}" is refused, and the message names the file and what happened', said[:160])
            check(not any(s in said for s in secret), f'{name}: that message holds no part of the storage address', said[:200])
            check(left == [], f'{name}: nothing is kept in the cache after "{mode}"', left)
        Fake.mode = 'big'
        cap = ('MAX_BYTES', A.MAX_BYTES) if M is A else None
        if cap:
            M.MAX_BYTES = 1000
            with tempfile.TemporaryDirectory() as cache:
                said, left = attempt(M.fetch, dict(row), cache)
            M.MAX_BYTES = cap[1]
            check('cap' in said and left == [] and not any(s in said for s in secret), f'{name}: a file over the size cap is refused, nothing kept, no address in the message', said[:160])
        M.BASE = None
        with tempfile.TemporaryDirectory() as cache:
            said, left = attempt(M.fetch, dict(row), cache)
        check('WI_STORAGE_BASE' in said and left == [], f'{name}: without a base the message says how to give one', said[:120])
    srv.shutdown()
    print('ALL PASSED' if not fails else f'{len(fails)} FAILED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
