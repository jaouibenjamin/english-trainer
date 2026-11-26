#!/usr/bin/env python3
"""The stand-in for the Supabase CLI in tests/setup_check.py (not a suite). It forwards `link`, `db push` and
`functions deploy` to the stand-in Management API at $WI_FAKE_API, which applies them to the local database. On
`link` it also prints the database password on purpose, so the test proves tools/supabase_setup.py hides what a real
CLI might echo."""
import json, os, sys, urllib.request

api = os.environ['WI_FAKE_API']


def post(path, body):
    req = urllib.request.Request(api + path, data=json.dumps(body).encode(), method='POST', headers={'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


a = sys.argv[1:]
with open(os.environ['WI_FAKE_CLI_LOG'], 'a', encoding='utf-8') as f:
    f.write(json.dumps(a) + '\n')
if a[:1] == ['link']:
    import urllib.parse
    pw = os.environ.get('SUPABASE_DB_PASSWORD', '')
    print(f"Connecting to remote database with password {pw} ...")
    print(f"postgresql://postgres.ref:{urllib.parse.quote(pw, safe='')}@pooler.example:6543/postgres")
    print(json.dumps({'password': pw}))
    print('Finished supabase link.')
elif a[:2] == ['db', 'push']:
    if sys.stdin.read(1) != 'y':
        sys.exit('db push was not confirmed')
    r = post('/_fake/db_push', {})
    print(r['out'])
    sys.exit(0 if r['ok'] else 1)
elif a[:2] == ['functions', 'deploy']:
    r = post('/_fake/deploy', {'name': a[2], 'args': a[3:]})
    print(f'Deployed Function {a[2]}')
    sys.exit(0 if r['ok'] else 1)
else:
    sys.exit(f'fake supabase: unknown command {a}')
