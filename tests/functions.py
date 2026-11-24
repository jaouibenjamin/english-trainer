#!/usr/bin/env python3
"""Edge Function tests (docs/BACKEND.md sections 3 and 4). One command from the repo root:

    python3 tests/functions.py

Starts the same throw-away local PostgreSQL as tests/db.py (stand-in + migrations), then runs the Deno tests in
supabase/functions/tests against it: the real function logic, a clock the tests move (a simulated day of guessing),
and a stand-in for Supabase Auth. Needs Deno 2 (https://deno.com, or `npm i -g deno`); set DENO to its path if it is
not on PATH. Supabase Auth itself is not exercised here: see section 10 of the doc."""
import os, shutil, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db'))
import pg

deno = os.environ.get('DENO') or shutil.which('deno')
if not deno:
    sys.exit('Deno is not installed. Install Deno 2 (npm i -g deno) or set DENO=/path/to/deno')
db = pg.start()
try:
    env = dict(os.environ, WI_PG_SOCKET=os.path.join(db.sock, f'.s.PGSQL.{db.port}'), WI_PG_DB=pg.DB, WI_PG_SUPER='supabase_admin', NO_COLOR='1')
    fdir = os.path.join(pg.ROOT, 'supabase', 'functions')
    chk = subprocess.run([deno, 'check'] + sorted(os.path.join(d, 'index.ts') for d in os.listdir(fdir) if os.path.exists(os.path.join(fdir, d, 'index.ts'))), cwd=fdir, env=env)
    r = subprocess.run([deno, 'test', '--allow-env', '--allow-read', '--allow-write', '--allow-net', '--no-check', 'tests/'] + sys.argv[1:], cwd=fdir, env=env)
    code = chk.returncode or r.returncode
finally:
    db.stop()
sys.exit(code)
