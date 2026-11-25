#!/usr/bin/env python3
"""The restore drill (docs/BACKEND.md section 6): load one decrypted backup export into an EMPTY second project.
Runs on the owner's computer, where the private key is (gpg's keyring):

    WI_RESTORE_DATABASE_URL=postgresql://...drill project... python3 tools/restore.py EXPORT_DIR

The drill project must have the migrations applied (supabase db push) and nothing else: no seed, no pupils. Each
chunk is decrypted with gpg in memory and loaded in one transaction; ids are kept. Then the checks: rows per table
equal the manifest, and the points totals equal the ledgers (private.totals_check()). Exit 1 if anything differs.
Not restored, by design: sign-in sessions (pupils.auth_user_id is cleared: every pupil signs in again with their
code) and teachers (their Google users exist only in the original project; add them again by hand)."""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pgurl

SKIP = {'public.teachers'}
# replaced, not added: the settings row the migrations made, and the empty rows the pupils' insert trigger makes
REPLACE = {'private.settings', 'public.pupil_totals', 'public.progress'}


def decrypt(path):
    r = subprocess.run(['gpg', '--batch', '--quiet', '--decrypt', path], capture_output=True)
    if r.returncode:
        raise SystemExit(f'gpg could not decrypt {os.path.basename(path)} (is the private key on this computer?)')
    return r.stdout.decode('utf-8')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit('usage: restore.py EXPORT_DIR')
    url = os.environ.get('WI_RESTORE_DATABASE_URL')
    if not url:
        raise SystemExit('set WI_RESTORE_DATABASE_URL to the DRILL project (never the real one)')
    d = argv[0]
    with open(os.path.join(d, 'manifest.json')) as f:
        man = json.load(f)
    out, err, rc = pgurl.run(url, 'select (select count(*) from public.pupils) + (select count(*) from public.items);')
    if rc:
        raise SystemExit('cannot read the drill project: ' + (err.strip().splitlines() or ['?'])[0])
    if out.strip() != '0':
        raise SystemExit('refused: the target already holds pupils or a catalogue. Restore only into an empty drill project.')
    if not all(re.fullmatch(r'(public|private)\.[a-z_]{1,40}', t) for t in man['tables']) or \
       not all(c['table'] in man['tables'] and re.fullmatch(r'[0-9a-z._-]{1,80}\.asc', c['file']) for c in man['chunks']):
        raise SystemExit('the manifest names a table or file it should not: refused')
    tables = [t for t in man['tables'] if t not in SKIP]
    q = ' union all '.join(f"select '{t}', (select string_agg(quote_ident(attname), ', ' order by attnum) from pg_attribute "
                           f"where attrelid = '{t}'::regclass and attnum > 0 and not attisdropped and attgenerated = '')" for t in tables)
    out, err, rc = pgurl.run(url, q + ';')
    if rc:
        raise SystemExit('the drill project does not have the same tables (migrations applied?): ' + (err.strip().splitlines() or ['?'])[0])
    cols = dict(line.split('|', 1) for line in out.strip().splitlines())
    sql, emptied = ['set local statement_timeout = 0;'], set()
    for c in man['chunks']:
        t = c['table']
        if t in SKIP or c['rows'] == 0:
            continue
        rows = json.loads(decrypt(os.path.join(d, c['file'])))
        if len(rows) != c['rows']:
            raise SystemExit(f'{c["file"]}: {len(rows)} rows, the manifest says {c["rows"]}')
        if t == 'public.pupils':
            for r in rows:
                r['auth_user_id'] = None
        if t in REPLACE and t not in emptied:
            sql.append(f'delete from {t};')
            emptied.add(t)
        # ids kept as they were; generated columns are computed again
        sql.append(f"insert into {t} ({cols[t]}) overriding system value select {cols[t]} "
                   f"from jsonb_populate_recordset(null::{t}, {pgurl.literal(json.dumps(rows, ensure_ascii=False))}::jsonb);")
    # identity columns go on from the highest restored id
    sql.append("""do $s$ declare r record; begin
  for r in select a.attrelid::regclass::text as t, a.attname as c, pg_get_serial_sequence(a.attrelid::regclass::text, a.attname) as s
             from pg_attribute a join pg_class k on k.oid = a.attrelid join pg_namespace n on n.oid = k.relnamespace
            where n.nspname in ('public', 'private') and a.attidentity <> '' loop
    execute format('select setval(%L, greatest(coalesce((select max(%I) from %s), 0), 1))', r.s, r.c, r.t);
  end loop; end $s$;""")
    checks = [f"select '{t}', count(*) from {t};" for t in man['tables'] if t not in SKIP]
    sql += checks + ['select \'totals_wrong\', count(*) from private.totals_check();']
    out, err, rc = pgurl.run(url, '\n'.join(sql) + '\n')
    if rc:
        raise SystemExit('the restore failed, nothing was kept: ' + (err.strip().splitlines() or ['?'])[0])
    got = dict(line.split('|') for line in out.strip().splitlines())
    bad = [t for t in man['tables'] if t not in SKIP and int(got.get(t, -1)) != man['tables'][t]]
    for t in man['tables']:
        print(f"{t:28} {man['tables'][t]:>7} {'skipped' if t in SKIP else got.get(t)}")
    print('totals check:', 'ok' if got.get('totals_wrong') == '0' else 'WRONG for ' + got.get('totals_wrong', '?') + ' pupils')
    if bad or got.get('totals_wrong') != '0':
        print('RESTORE DRILL FAILED: ' + ', '.join(bad))
        return 1
    print('restore drill passed. Then load supabase/seed/catalog.sql (adds only what is new).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
