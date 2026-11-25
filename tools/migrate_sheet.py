#!/usr/bin/env python3
"""Copy one class from the Google Sheet into Supabase (docs/BACKEND.md 4.2 and section 8). Runs on the owner's computer.

    WI_DATABASE_URL=postgresql://... python3 tools/migrate_sheet.py PUPILS.csv --class CLASS_ID            dry run
    WI_DATABASE_URL=postgresql://... python3 tools/migrate_sheet.py PUPILS.csv --class CLASS_ID --apply    writes

PUPILS.csv is the Sheet's pupils tab saved as CSV (File > Download > CSV), with its header row: name, salt, hash,
points, words, reads, streak, lastDay, fails, lockUntil, state, updated. It holds fast hashes of the codes, so:
it must be OUTSIDE this repository (the tool refuses a file inside it), and it is deleted after use.

A dry run does the whole import inside the database and then throws it away, so it shows exactly what --apply would
do. The same command is the nightly re-sync of the copy phase: it is safe to run again (docs/BACKEND.md section 8).

This tool never has the pepper and never asks for it. After --apply, the Sheet's hashes wait in a staging table that
only the server role can read; wrap them at once with the admin function (needs the server key, on this computer only):

    SUPABASE_URL=https://<project>.supabase.co SUPABASE_SERVICE_KEY=... python3 tools/migrate_sheet.py --wrap

Output: counts, and the CSV row numbers of the pupils whose points are above three times the class median (for the
teacher to look at). No name, code, salt, hash or blob is ever printed, and none goes into a statement the database
could write to its log: the rows travel as COPY data."""
import argparse, csv, json, os, re, sys, unicodedata, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pgurl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = ['name', 'salt', 'hash', 'points', 'words', 'reads', 'streak', 'lastDay', 'fails', 'lockUntil', 'state', 'updated']
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def inside_repo(path):
    p, r = os.path.realpath(path), os.path.realpath(ROOT)
    return p == r or p.startswith(r + os.sep)


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.reader(f))
    if not rows or [h.strip() for h in rows[0][:len(HEAD)]] != HEAD:
        raise SystemExit('this is not the pupils tab: the first row must be ' + ', '.join(HEAD))
    out, skipped = [], 0
    for r in rows[1:]:
        r = (r + [''] * len(HEAD))[:len(HEAD)]
        d = dict(zip(HEAD, r))
        if not d['name'].strip():
            continue
        try:
            state = json.loads(d['state']) if d['state'].strip() else {}
            # what Python reads but the database's jsonb refuses (review of #27, B3-bis): NaN, Infinity, a number too
            # large for a float, a \u0000 in a string. Such a blob is broken: the pupil comes over without it.
            if '\\u0000' in json.dumps(state, allow_nan=False):
                raise ValueError('NUL')
        except (ValueError, OverflowError, RecursionError):
            state, skipped = {}, skipped + 1
        try:
            pts = max(0, int(float(d['points'] or 0)))
        except (ValueError, OverflowError):            # 'NaN', 'inf', '1e999'
            pts = 0
        clean = lambda x: x.replace('\x00', '')
        out.append({'name': clean(d['name']), 'salt': clean(d['salt']).strip(), 'hash': clean(d['hash']).strip().lower(),
                    'state': state if isinstance(state, dict) else {}, 'points': pts})
    return out, skipped


def import_rows(url, class_id, rows, apply):
    """The rows go as COPY data, never inside a statement (review B3: a failing statement is written whole into the
    server's log, which on Supabase is the dashboard). A dry run is the same work, rolled back."""
    # The rows arrive as text and are read as JSON one by one inside a block that catches the error, so a row the
    # database refuses is counted ("unreadable"), never logged with its content (review of #27, B3-bis).
    script = ("begin;\n"
              "create temp table wi_rows (n int, r text) on commit drop;\n"
              "create temp table wi_ok (n int, r jsonb) on commit drop;\n"
              "\\copy wi_rows (n, r) from pstdin\n"
              "do $wi$ declare x record; begin for x in select n, r from wi_rows loop\n"
              "  begin insert into wi_ok values (x.n, x.r::jsonb); exception when others then null; end;\n"
              "end loop; end $wi$;\n"
              f"select private.sheet_import('{class_id}'::uuid, (select coalesce(jsonb_agg(r order by n), '[]') from wi_ok))\n"
              "  || jsonb_build_object('unreadable', (select count(*) from wi_rows) - (select count(*) from wi_ok));\n"
              + ("commit;\n" if apply else "rollback;\n"))
    out, err, rc = pgurl.run_with_rows(url, script, [(i, json.dumps(r, ensure_ascii=True)) for i, r in enumerate(rows)])
    if rc:
        raise SystemExit(('the import failed, nothing was written: ' if apply else 'the dry run failed: ') + (err.strip().splitlines() or ['?'])[0])
    return json.loads(out.strip().splitlines()[-1])


def wrap():
    base, key = os.environ.get('SUPABASE_URL', ''), os.environ.get('SUPABASE_SERVICE_KEY', '')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', base) or not key:
        raise SystemExit('set SUPABASE_URL (https://<project>.supabase.co) and SUPABASE_SERVICE_KEY')
    total = 0
    for _ in range(1000):
        req = urllib.request.Request(base + '/functions/v1/admin-wrap-legacy', data=b'{}', method='POST',
                                     headers={'content-type': 'application/json', 'authorization': 'Bearer ' + key, 'apikey': key})
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.load(r)
        if not j.get('ok'):
            raise SystemExit('the admin function refused: ' + str(j.get('e')))
        total += j['wrapped']
        if j['remaining'] == 0:
            print(f'wrapped {total} codes; the staging table is empty')
            return
    raise SystemExit('stopped after 1000 calls with codes still waiting')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('csv', nargs='?', help="the pupils tab as CSV, outside this repository")
    ap.add_argument('--class', dest='class_id', help='the class id (from admin-class)')
    ap.add_argument('--apply', action='store_true', help='write (default: dry run)')
    ap.add_argument('--wrap', action='store_true', help='wrap the staged hashes with the admin function')
    a = ap.parse_args(argv)
    if a.wrap:
        return wrap()
    if not a.csv or not a.class_id:
        ap.error('a CSV file and --class are needed')
    if inside_repo(a.csv):
        raise SystemExit('refused: the CSV holds code hashes and must not be inside the repository. Move it out and delete it after use.')
    if not UUID.match(a.class_id):
        raise SystemExit('--class must be the class id (a uuid)')
    url = os.environ.get('WI_DATABASE_URL')
    if not url:
        raise SystemExit('set WI_DATABASE_URL to the database address (with its password) for this run only')
    rows, broken = read_csv(a.csv)
    rep = import_rows(url, a.class_id, rows, a.apply)
    print(('APPLIED' if a.apply else 'DRY RUN (nothing written; add --apply)') +
          f": {len(rows)} rows read, {rep['new']} new pupils, {rep['existing']} already there, {rep['blobs']} blobs written, "
          f"{rep['hashes_staged']} codes staged, {rep['refused_names']} names refused, {broken} broken blobs"
          + (f", {rep['refused_rows'] + rep['unreadable']} rows the database refused" if rep['refused_rows'] + rep['unreadable'] else ''))
    if rep['look_at']:
        # row numbers of the CSV, not names (review S-f): the owner looks them up in the Sheet
        key = lambda n: re.sub(r'\s+', ' ', unicodedata.normalize('NFC', n).strip()).lower()
        where = {key(r['name']): i + 2 for i, r in enumerate(rows)}      # +2: the header is row 1
        print(f"points above 3 x the class median ({rep['median']}): CSV rows " + ', '.join(str(where.get(key(n), '?')) for n in rep['look_at']))
    if a.apply and rep['hashes_staged']:
        print('next: wrap the staged codes now (python3 tools/migrate_sheet.py --wrap), then delete the CSV')
    return 0


if __name__ == '__main__':
    sys.exit(main())
