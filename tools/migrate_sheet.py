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

Output: counts, and the names whose points are above three times the class median (for the teacher to look at).
No code, salt, hash or blob is ever printed."""
import argparse, csv, json, os, re, sys, urllib.request

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
        except ValueError:
            state, skipped = {}, skipped + 1          # a broken blob: the pupil comes over without it
        try:
            pts = max(0, int(float(d['points'] or 0)))
        except ValueError:
            pts = 0
        out.append({'name': d['name'], 'salt': d['salt'].strip(), 'hash': d['hash'].strip().lower(),
                    'state': state if isinstance(state, dict) else {}, 'points': pts})
    return out, skipped


def import_rows(url, class_id, rows, apply):
    sql = (f"select private.sheet_import({pgurl.literal(class_id)}::uuid, {pgurl.literal(json.dumps(rows, ensure_ascii=False))}::jsonb, "
           f"{'false' if apply else 'true'});\n")
    out, err, rc = pgurl.run(url, sql)
    if not apply:
        m = re.search(r'DETAIL:\s+(\{.*\})', err)
        if rc and m and 'dry run' in err:
            return json.loads(m.group(1))
        raise SystemExit('the dry run failed: ' + (err.strip().splitlines() or ['?'])[0])
    if rc:
        raise SystemExit('the import failed, nothing was written: ' + (err.strip().splitlines() or ['?'])[0])
    return json.loads(out.strip())


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
          f"{rep['hashes_staged']} codes staged, {rep['refused_names']} names refused, {broken} broken blobs")
    if rep['look_at']:
        print(f"points above 3 x the class median ({rep['median']}): " + ', '.join(rep['look_at']))
    if a.apply and rep['hashes_staged']:
        print('next: wrap the staged codes now (python3 tools/migrate_sheet.py --wrap), then delete the CSV')
    return 0


if __name__ == '__main__':
    sys.exit(main())
