#!/usr/bin/env python3
"""Fetch one encrypted backup export (docs/BACKEND.md section 6, Backup). Used by .github/workflows/keepalive.yml and
by the owner by hand. Needs only the PUBLIC key and the export token, never the server key:

    SUPABASE_URL=https://<project>.supabase.co SUPABASE_ANON_KEY=... BACKUP_TOKEN=... python3 tools/backup_fetch.py OUT_DIR

Writes OUT_DIR/manifest.json (tables, chunks, row counts: no data) and one OUT_DIR/NNN-<table>-<offset>.asc per chunk,
each encrypted by the database to the owner's public key. Only the owner's private key opens them (tools/restore.py).
Exit 0 and a note when the project is not set up yet (no address or key), so the scheduled job stays green until then."""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request


def base_url():
    u = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
    if re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', u):
        return u
    # the local test (tests/backup_check.py) serves the same API on this machine only
    if os.environ.get('WI_LOCAL_TEST') == '1' and re.fullmatch(r'http://127\.0\.0\.1:\d+', u):
        return u
    return None


def rpc(base, key, name, args):
    req = urllib.request.Request(f'{base}/rest/v1/rpc/{name}', data=json.dumps(args).encode(), method='POST',
                                 headers={'content-type': 'application/json', 'apikey': key, 'authorization': 'Bearer ' + key})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == 3:
                raise SystemExit(f'{name}: HTTP {e.code}')
        except urllib.error.URLError as e:
            if i == 3:
                raise SystemExit(f'{name}: {e.reason}')
        time.sleep(2 ** i)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit('usage: backup_fetch.py OUT_DIR')
    base, key, token = base_url(), os.environ.get('SUPABASE_ANON_KEY', '').strip(), os.environ.get('BACKUP_TOKEN', '').strip()
    if not base or not key or not token:
        print('backup: not set up yet (SUPABASE_URL, SUPABASE_ANON_KEY, BACKUP_TOKEN); nothing fetched')
        return 0
    out = argv[0]
    os.makedirs(out, exist_ok=True)
    start = rpc(base, key, 'backup_export', {'p_token': token})
    if not start.get('ok'):
        raise SystemExit('backup refused: ' + str(start.get('e')) + (f" (wait {start['wait']} s)" if 'wait' in start else ''))
    if not all(isinstance(t, str) and re.fullmatch(r'(public|private)\.[a-z_]{1,40}', t) for t in start.get('tables', [])):
        raise SystemExit('backup refused: the table list is not what this tool expects')
    man = {'at': start['at'], 'tables': {}, 'chunks': []}
    n = 0
    for table in start['tables']:
        off, rows = 0, 0
        while off is not None:
            c = rpc(base, key, 'backup_export', {'p_token': token, 'p_table': table, 'p_offset': off})
            if not c.get('ok'):
                raise SystemExit(f'backup of {table} refused: {c.get("e")}')
            if not str(c.get('data', '')).startswith('-----BEGIN PGP MESSAGE-----'):
                raise SystemExit(f'backup of {table}: the database did not return ciphertext; nothing written')
            n += 1
            name = f'{n:03d}-{table}-{off}.asc'
            with open(os.path.join(out, name), 'w') as f:
                f.write(c['data'])
            if not isinstance(c.get('rows'), int) or not (c.get('next') is None or isinstance(c['next'], int) and c['next'] > off):
                raise SystemExit(f'backup of {table}: an answer this tool does not expect')
            man['chunks'].append({'file': name, 'table': table, 'offset': off, 'rows': c['rows']})
            rows += c['rows']
            off = c['next']
        man['tables'][table] = rows
    with open(os.path.join(out, 'manifest.json'), 'w') as f:
        json.dump(man, f, indent=1)
    print(f"backup: {len(man['tables'])} tables, {n} encrypted chunks, {sum(man['tables'].values())} rows")
    return 0


if __name__ == '__main__':
    sys.exit(main())
