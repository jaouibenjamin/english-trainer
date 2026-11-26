#!/usr/bin/env python3
# suite: needs=psql,node,gpg   # picked up by tests/all.py
"""Operations tools against the local PostgreSQL (docs/BACKEND.md sections 5, 6, 8). One command from the repo root:

    python3 tests/ops.py

- the catalogue seed is current (generated from the content files) and loads twice; a real key earns, an unknown one not
- tools/migrate_sheet.py: refuses a CSV inside the repo, dry run writes nothing, apply, a second run changes nothing,
  never prints a hash or salt, caps points, lists outliers
- backup_export with the public role only: token, 6-hour rule, 30-minute window, chunks are ciphertext; then
  tools/backup_fetch.py over HTTP (a local stand-in for the REST API) and tools/restore.py into a second, empty
  database with gpg: rows per table and the totals check equal
Needs PostgreSQL 16, node, gpg. Every name, code, key and token here is made up."""
import hashlib, http.server, json, os, shutil, subprocess, sys, tempfile, threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, 'db'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pg

passed = failed = 0


def check(what, cond, info=''):
    global passed, failed
    if cond:
        passed += 1; print('PASS', what)
    else:
        failed += 1; print('FAIL', what, ' <-', str(info)[:300])


def eq(what, got, want):
    check(what, got == want, f'got {got!r}, want {want!r}')


def tool(args, env=None):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, **(env or {})))


# ---------------------------------------------------------------- catalogue
print('-- catalogue seed')
gen = subprocess.run(['node', 'tools/seed_catalog.mjs', '--stdout'], capture_output=True, text=True, cwd=ROOT)
with open(os.path.join(ROOT, 'supabase/seed/catalog.sql')) as f:
    seed = f.read()
check('supabase/seed/catalog.sql is current (else: node tools/seed_catalog.mjs, commit both)', gen.returncode == 0 and gen.stdout == seed, gen.stderr)

db = pg.start()
tmp = tempfile.mkdtemp(prefix='wi-ops-')
os.chmod(tmp, 0o755)
gnupg = os.path.join(tmp, 'gnupg')
os.mkdir(gnupg, 0o700)
srv = None
try:
    url = f'postgresql://postgres@/{pg.DB}?host={db.sock}&port={db.port}'
    os.environ['PSQL'] = os.path.join(db.bin, 'psql')
    for _ in range(2):
        db.admin(seed)
    n_items, n_levels = db.one('select count(*) from public.items'), db.one('select count(*) from public.levels')
    check('the seed loads, twice, without doubles', int(n_items) > 50 and int(n_levels) > 20, (n_items, n_levels))
    alltab = sorted(r[0] for r in db.admin("select table_schema || '.' || table_name from information_schema.tables where table_schema in ('public', 'private') and table_type = 'BASE TABLE'"))
    inc = [r[0] for r in db.admin('select unnest(private.backup_tables())')]
    exc = [r[0] for r in db.admin('select unnest(private.backup_excluded())')]
    eq('every table is either backed up or left out on purpose (a new table must be put in one list)', sorted(inc + exc), alltab)
    eq('the left-out ones: address salts and buckets, typed names, the bare Sheet hashes (review S-d), the 2-day counter of new codes', sorted(exc),
       ['private.auth_attempts', 'private.auth_buckets', 'private.auth_lock_events', 'private.class_misses', 'private.ip_salts', 'private.legacy_import', 'private.teacher_resets'])
    eq('the mock exam paper has its size', db.one("select size from public.levels where game = 'exam' and level_key = 'mock'"), '20')

    # ---------------------------------------------------------------- migrate_sheet
    print('-- tools/migrate_sheet.py')
    cls = db.one("insert into public.classes (name) values ('ops class') returning id")
    codes = {'Testa': '8353', 'Probe': '9053', 'Sample Two': '6149', 'Dummy': '7159', 'x': '4827', 'Fixty': '5839'}
    with open(os.path.join(HERE, 'fixtures/sheet_sample.csv')) as f:
        text = f.read()
    for line in text.splitlines()[1:]:
        salt = line.split(',')[1]
        for n, c in codes.items():
            if f'HASH:{n},' in line:
                text = text.replace(f'HASH:{n},', hashlib.sha256(f'{salt}:{c}'.encode()).hexdigest() + ',', 1)
    csv_path = os.path.join(tmp, 'pupils.csv')
    with open(csv_path, 'w') as f:
        f.write(text)
    env = {'WI_DATABASE_URL': url}
    r = tool(['tools/migrate_sheet.py', os.path.join(HERE, 'fixtures/sheet_sample.csv'), '--class', cls], env)
    check('a CSV inside the repository is refused', r.returncode != 0 and 'inside the repository' in r.stderr, r.stderr)
    r = tool(['tools/migrate_sheet.py', csv_path, '--class', cls], env)
    check('dry run: reports what it would do', r.returncode == 0 and 'DRY RUN' in r.stdout and '8 new pupils' in r.stdout, r.stdout + r.stderr)
    eq('dry run: nothing written', db.one('select count(*) from public.pupils'), '0')
    r = tool(['tools/migrate_sheet.py', csv_path, '--class', cls, '--apply'], env)
    out = r.stdout + r.stderr
    check('apply: pupils in, codes staged', r.returncode == 0 and '8 new pupils' in r.stdout and '5 codes staged' in r.stdout and '1 names refused' in r.stdout and '3 broken blobs' in r.stdout, out)
    salts_and_hashes = [ln.split(',')[i] for ln in text.splitlines()[1:] for i in (1, 2)]
    check('no salt or hash is ever printed', not any(s and s in out for s in salts_and_hashes))
    check('the outliers are shown as CSV row numbers, not names (review S-f)', 'CSV rows 8, 5' in r.stdout, r.stdout)
    check('no name is printed at all', not any(n in out for n in ('Testa', 'Probe', 'Sample Two', 'Dummy', 'Mocky', 'Fixty')), out)
    eq('points enter as one migrated row each, capped at 50,000',
       db.admin("select p.display_name, t.points from public.pupil_totals t join public.pupils p on p.id = t.pupil_id where p.display_name in ('Testa', 'Fixty', 'Mocky') order by 1"),
       [['Fixty', '50000'], ['Mocky', '0'], ['Testa', '1200']])
    eq('markup in a name is refused', db.one("select count(*) from public.pupils where display_name like '%<%'"), '0')
    eq('a broken blob comes over as an empty one; so do a \\u0000 in a string and 1e999 (Python reads them, jsonb does not: B3-bis)',
       db.admin("select p.display_name, g.state::text, t.points from public.progress g join public.pupils p on p.id = g.pupil_id join public.pupil_totals t on t.pupil_id = p.id where p.display_name in ('Fixty', 'Nully', 'Huge') order by 1"),
       [['Fixty', '{}', '50000'], ['Huge', '{}', '0'], ['Nully', '{}', '10']])
    eq('the staging table holds the fast hashes, for the server role only', db.one('select count(*) from private.legacy_import'), '5')
    pts_before = db.one('select sum(delta) from public.points')
    r = tool(['tools/migrate_sheet.py', csv_path, '--class', cls, '--apply'], env)
    check('a second run (the nightly re-sync) adds nobody and no points', r.returncode == 0 and '0 new pupils' in r.stdout and '0 blobs written' in r.stdout
          and db.one('select sum(delta) from public.points') == pts_before and db.one('select count(*) from public.pupils') == '8', r.stdout + r.stderr)
    db.admin("update private.pupil_secrets set code_algo = 'v1' where false")    # nothing wrapped yet: the staging rows are re-written
    with open(csv_path, 'w') as f:
        f.write(text.replace('{""pts"":900}', '{""pts"":950}'))
    r = tool(['tools/migrate_sheet.py', csv_path, '--class', cls, '--apply'], env)
    check('a changed blob on the Sheet is copied over (the Sheet is the truth until the switch)', '1 blobs written' in r.stdout, r.stdout)
    pid = db.one("select id from public.pupils where display_name = 'Probe'")
    db.admin(f"delete from private.legacy_import where pupil_id = '{pid}'; insert into private.pupil_secrets (pupil_id, code_hash, code_salt) values ('{pid}', decode(repeat('ab', 32), 'hex'), '\\x00')")
    tool(['tools/migrate_sheet.py', csv_path, '--class', cls, '--apply'], env)
    eq('a code already set in Supabase is never staged again', db.one(f"select count(*) from private.legacy_import where pupil_id = '{pid}'"), '0')
    r = tool(['tools/migrate_sheet.py', '--wrap'], {'SUPABASE_URL': '', 'SUPABASE_SERVICE_KEY': ''})
    check('--wrap needs the project address and the server key from the environment', r.returncode != 0 and 'SUPABASE_URL' in r.stderr, r.stderr)
    src = open(os.path.join(ROOT, 'tools/migrate_sheet.py')).read()
    check('the tool never reads the pepper', 'PEPPER' not in src.replace('never has the pepper', '').replace('pepper', ''), '')

    # some play, so the export has answers, ledger rows and a teacher
    uid = db.one("insert into auth.users (email) values ('p-ops@pupils.invalid') returning id")
    db.admin(f"update public.pupils set auth_user_id = '{uid}' where display_name = 'Testa'")
    tuid = db.one("insert into auth.users (email) values ('teacher-ops@test.invalid') returning id")
    db.admin(f"insert into public.teachers values ('{tuid}', '{cls}')")
    ev = [{'type': 'answer', 'game': 'en', 'item': 'goal', 'correct': True, 'first_try': True},
          {'type': 'answer', 'game': 'en', 'item': 'not-a-word', 'correct': True, 'first_try': True},
          {'type': 'level', 'game': 'en', 'level': '1-sling', 'stars': 2}, {'type': 'read', 'text': '1'}]
    res, err = db.rpc(('authenticated', uid), 'record_events', {'p_batch': '6f1d7a0e-0000-4000-8000-000000000001', 'p_events': ev})
    check('a seeded word and level earn; an unknown word earns nothing', err is None and res['added'] == 3 and res['flagged'] == 1 and res['points'] == 1200 + 10 + 20 + 30 + 50, (res, err))

    # ---------------------------------------------------------------- backup export
    print('-- backup_export, backup_fetch.py, restore.py')
    genv = dict(os.environ, GNUPGHOME=gnupg)
    k = subprocess.run(['gpg', '--batch', '--passphrase', '', '--quick-gen-key', 'WI drill test <drill@example.invalid>', 'rsa2048', 'default', 'never'], capture_output=True, text=True, env=genv)
    fpr = [ln.split(':')[9] for ln in subprocess.run(['gpg', '--with-colons', '--list-keys'], capture_output=True, text=True, env=genv).stdout.splitlines() if ln.startswith('fpr:')][:1]
    k2 = subprocess.run(['gpg', '--batch', '--passphrase', '', '--quick-add-key', (fpr or ['x'])[0], 'rsa2048', 'encr', 'never'], capture_output=True, text=True, env=genv)
    pub = subprocess.run(['gpg', '--armor', '--export'], capture_output=True, text=True, env=genv).stdout
    check('a made-up owner key: RSA with an encryption subkey (the real one is 4096)', k.returncode == 0 and k2.returncode == 0 and 'BEGIN PGP PUBLIC KEY BLOCK' in pub, k.stderr)
    token = 'made-up-export-token-' + 'f' * 40
    anon = ('anon', None)
    res, err = db.rpc(anon, 'backup_export', {'p_token': token})
    eq('not set up: refused', (res or {}).get('e'), 'setup')
    db.admin(f"update private.settings set backup_pubkey = {db.lit(pub)}, backup_token_hash = '{hashlib.sha256(token.encode()).hexdigest()}', backup_chunk = 3")
    res, err = db.rpc(anon, 'backup_export', {'p_token': token + 'x'})
    eq('a wrong token: refused', (res or {}).get('e'), 'token')
    res, err = db.rpc(anon, 'backup_export', {'p_token': token, 'p_table': 'public.pupils', 'p_offset': 0})
    eq('a chunk before an export was opened: refused', (res or {}).get('e'), 'closed')
    res, err = db.rpc(anon, 'backup_export', {'p_token': token})
    check('the public role opens an export: the table list', err is None and res['ok'] and 'private.pupil_secrets' in res['tables'], (res, err))
    res, err = db.rpc(anon, 'backup_export', {'p_token': token})
    check('a second export within 6 hours: refused with the wait', (res or {}).get('e') == 'wait' and res['wait'] > 21000, res)
    res, err = db.rpc(anon, 'backup_export', {'p_token': token, 'p_table': 'auth.users', 'p_offset': 0})
    eq('a table outside the list: refused', (res or {}).get('e'), 'input')
    res, err = db.rpc(anon, 'backup_export', {'p_token': token, 'p_table': 'public.pupils;drop table public.items', 'p_offset': 0})
    eq('SQL in the table name: refused', (res or {}).get('e'), 'input')
    res, err = db.rpc(anon, 'backup_export', {'p_token': token, 'p_table': 'public.pupils', 'p_offset': 0})
    check('a chunk is ciphertext only, with the next offset', err is None and res['data'].startswith('-----BEGIN PGP MESSAGE') and res['rows'] == 3 and res['next'] == 3
          and 'Testa' not in res['data'], (res, err))
    for t in ('private.pupil_secrets', 'private.legacy_import', 'private.settings'):
        _, err = db.as_('anon', None, f'select count(*) from {t}')
        check(f'the public role still cannot read {t} itself', err is not None)
    db.admin("update private.settings set backup_opened_at = now() - interval '31 minutes'")
    res, err = db.rpc(anon, 'backup_export', {'p_token': token, 'p_table': 'public.pupils', 'p_offset': 0})
    eq('after 30 minutes the export is closed', (res or {}).get('e'), 'closed')
    db.admin("update private.settings set backup_opened_at = null")

    # the REST API, as far as these tools use it: POST /rest/v1/rpc/<fn> with the public key, run as anon
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['content-length'])))
            ok = self.path.startswith('/rest/v1/rpc/') and self.headers.get('apikey') == 'made-up-public-key'
            res, err = db.rpc(anon, self.path.rsplit('/', 1)[1], body) if ok else (None, 'no')
            data = json.dumps(res).encode()
            self.send_response(200 if err is None else 401)
            self.send_header('content-type', 'application/json'); self.send_header('content-length', str(len(data))); self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    out_dir = os.path.join(tmp, 'export')
    r = tool(['tools/backup_fetch.py', out_dir], {'SUPABASE_URL': '', 'SUPABASE_ANON_KEY': '', 'BACKUP_TOKEN': ''})
    check('the scheduled job before the project exists: a note, exit 0, nothing contacted', r.returncode == 0 and 'not set up' in r.stdout and not os.path.exists(out_dir), r.stdout + r.stderr)
    r = tool(['tools/backup_fetch.py', out_dir], {'SUPABASE_URL': f'http://127.0.0.1:{srv.server_port}', 'SUPABASE_ANON_KEY': 'made-up-public-key', 'BACKUP_TOKEN': token})
    check('an address that is not a Supabase project: not contacted, and the job goes red (review S-g)', r.returncode != 0 and 'in part' in r.stderr and not os.path.exists(out_dir), r.stdout + r.stderr)
    r = tool(['tools/backup_fetch.py', out_dir], {'SUPABASE_URL': 'https://abcdefgh.supabase.co', 'SUPABASE_ANON_KEY': '', 'BACKUP_TOKEN': ''})
    check('only the address set: red, nothing contacted', r.returncode != 0 and 'SUPABASE_ANON_KEY' in r.stderr and not os.path.exists(out_dir), r.stdout + r.stderr)
    fenv = {'SUPABASE_URL': f'http://127.0.0.1:{srv.server_port}', 'SUPABASE_ANON_KEY': 'made-up-public-key', 'BACKUP_TOKEN': token, 'WI_LOCAL_TEST': '1'}
    r = tool(['tools/backup_fetch.py', out_dir], fenv)
    check('backup_fetch.py: every table, in chunks', r.returncode == 0 and 'encrypted chunks' in r.stdout, r.stdout + r.stderr)
    man = json.load(open(os.path.join(out_dir, 'manifest.json')))
    files = [c['file'] for c in man['chunks']]
    blob = ''.join(open(os.path.join(out_dir, f)).read() for f in files)
    check('nothing readable lands on disk: no name, no salt', all(open(os.path.join(out_dir, f)).read().startswith('-----BEGIN PGP MESSAGE') for f in files)
          and 'Testa' not in blob and 'made-up-salt' not in blob and 'Testa' not in json.dumps(man))
    eq('rows in the manifest = rows in the database (pupils)', man['tables']['public.pupils'], 8)
    r = tool(['tools/backup_fetch.py', os.path.join(tmp, 'again')], fenv)
    check('the same token again within 6 hours: refused', r.returncode != 0 and 'wait' in r.stderr, r.stderr)

    # ---------------------------------------------------------------- restore drill into a second, empty database
    adm = [os.path.join(db.bin, 'psql'), '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-h', db.sock, '-p', str(db.port), '-U', 'supabase_admin']
    stub = ''.join(ln for ln in open(os.path.join(HERE, 'db/stub.sql')).readlines()
                   if not ln.startswith('create role') and not ln.startswith('grant anon, authenticated, service_role to postgres'))

    def empty_db(name):
        subprocess.run(adm + ['-d', 'postgres', '-c', f'create database {name}'], check=True, capture_output=True)
        subprocess.run(adm + ['-d', name, '-v', f'DBNAME={name}', '-f', '-'], input=stub, capture_output=True, text=True)
        for f in sorted(os.listdir(os.path.join(ROOT, 'supabase/migrations'))):
            m = subprocess.run([os.path.join(db.bin, 'psql'), '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-h', db.sock, '-p', str(db.port), '-U', 'postgres', '-d', name,
                                '-f', os.path.join(ROOT, 'supabase/migrations', f)], capture_output=True, text=True)
            if m.returncode:
                print(m.stderr)
    empty_db('wi_drill')
    drill = f'postgresql://postgres@/wi_drill?host={db.sock}&port={db.port}'
    renv = {'WI_RESTORE_DATABASE_URL': drill, 'GNUPGHOME': gnupg}
    r = tool(['tools/restore.py', out_dir], {'WI_RESTORE_DATABASE_URL': drill, 'GNUPGHOME': os.path.join(tmp, 'nokeys')})
    check('without the private key nothing is restored', r.returncode != 0 and 'decrypt' in r.stderr, r.stdout + r.stderr)
    r = tool(['tools/restore.py', out_dir], renv)
    check('restore.py: every table, ids kept, the totals check green', r.returncode == 0 and 'restore drill passed' in r.stdout, r.stdout + r.stderr)
    q = lambda d, sql: subprocess.run([os.path.join(db.bin, 'psql'), '-X', '-A', '-t', '-h', db.sock, '-p', str(db.port), '-U', 'postgres', '-d', d, '-c', sql],
                                      capture_output=True, text=True).stdout.strip()
    tot = 'select string_agg(p.display_name || \':\' || t.points || \':\' || t.answers, \',\' order by p.display_name) from public.pupil_totals t join public.pupils p on p.id = t.pupil_id'
    eq('the board is the same in the drill database', q('wi_drill', tot), q(pg.DB, tot))
    eq('the code hashes came back (they still need the pepper); the bare Sheet hashes were never in the backup',
       (q('wi_drill', 'select count(*) from private.pupil_secrets'), q('wi_drill', 'select count(*) from private.legacy_import')), (q(pg.DB, 'select count(*) from private.pupil_secrets'), '0'))
    eq('nobody is signed in there, and teachers are added by hand', q('wi_drill', 'select count(*) filter (where auth_user_id is not null), (select count(*) from public.teachers) from public.pupils'), '0|0')
    res = q('wi_drill', "insert into public.answers (pupil_id, item_id, pts, flag, correct, first_try) select id, (select min(id) from public.items), 0, 0, true, true from public.pupils limit 1 returning id > 0")
    eq('new rows there get new ids (sequences moved on)', res.splitlines()[0] if res else '', 't')
    r = tool(['tools/restore.py', out_dir], renv)
    check('a second restore into a database that is not empty: refused', r.returncode != 0 and 'empty drill project' in r.stderr, r.stderr)
    bad = json.load(open(os.path.join(out_dir, 'manifest.json')))
    bad['tables']['public.pupils; drop table x'] = 1
    json.dump(bad, open(os.path.join(out_dir, 'manifest.json'), 'w'))
    r = tool(['tools/restore.py', out_dir], renv)
    check('a manifest naming a table it should not: refused', r.returncode != 0 and 'refused' in r.stderr, r.stderr)
    # a restore that meets a row the drill database refuses (a name the table's rule rejects): it stops, and says which
    # table, not which row
    bad_dir = os.path.join(tmp, 'bad-export')
    os.mkdir(bad_dir)
    marker = 'Leakmarker' + 'x' * 45                                   # longer than a class name may be (40)
    enc = subprocess.run(['gpg', '--batch', '--yes', '--armor', '--trust-model', 'always', '--encrypt', '-r', 'drill@example.invalid', '-o', os.path.join(bad_dir, '001-public.classes-0.asc')],
                         input=json.dumps([{'id': '00000000-0000-4000-8000-00000000c1a5', 'name': marker, 'grade': '', 'roster_only': True, 'max_pupils': 60, 'created_at': '2026-11-01T00:00:00Z'}]),
                         capture_output=True, text=True, env=genv)
    json.dump({'at': 'x', 'tables': {'public.classes': 1}, 'chunks': [{'file': '001-public.classes-0.asc', 'table': 'public.classes', 'offset': 0, 'rows': 1}]},
              open(os.path.join(bad_dir, 'manifest.json'), 'w'))
    empty_db('wi_drill2')
    r = tool(['tools/restore.py', bad_dir], {'WI_RESTORE_DATABASE_URL': f'postgresql://postgres@/wi_drill2?host={db.sock}&port={db.port}', 'GNUPGHOME': gnupg})
    check('a restore that meets a refused row stops, naming the table only', enc.returncode == 0 and r.returncode != 0 and 'a row of public.classes was refused' in r.stderr and marker not in r.stderr, (r.returncode, r.stdout[-300:], r.stderr[-300:], enc.returncode, enc.stderr[-200:]))

    # ---------------------------------------------------------------- review B3: nothing of a pupil in the server's log
    r = tool(['tools/migrate_sheet.py', csv_path, '--class', '00000000-0000-4000-8000-0000000000ff'], env)
    check('a run that fails (no such class) fails without data in its message', r.returncode != 0 and 'no such class' in r.stderr, r.stderr)
    log = open(os.path.join(db.sock, 'log'), encoding='utf-8', errors='replace').read()
    check('the server log has the failed statement', 'no such class' in log)
    # rows the client would never send, sent anyway: the database reads them one by one and counts the refused ones
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import migrate_sheet
    rep_ = migrate_sheet.import_rows(url, cls, [{'name': 'Infyrow', 'salt': 'made-up-salt-9', 'hash': 'f' * 64, 'state': {'x': float('nan')}, 'points': 1},
                                                {'name': 'Okrow', 'salt': '', 'hash': '', 'state': {}, 'points': 1}], False)
    eq('a row jsonb cannot read (NaN) is counted, not logged; the rest goes on (dry run)', (rep_['unreadable'], rep_['new']), (1, 1))
    log = open(os.path.join(db.sock, 'log'), encoding='utf-8', errors='replace').read()
    leaks = [x for x in salts_and_hashes + ['Testa', 'Probe', 'Sample Two', 'Dummy', 'Mocky', 'Fixty', 'Nully', 'Huge', 'Infyrow', 'made-up-salt', 'f' * 64, 'Leakmarker'] if x and x in log]
    check('and no name, salt or hash anywhere in it, after dry runs, imports, a failed import and a restore', not leaks, leaks[:3])
finally:
    if srv:
        srv.shutdown()
    db.stop()
    shutil.rmtree(tmp, ignore_errors=True)

print(f'\n{passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
