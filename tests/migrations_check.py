#!/usr/bin/env python3
# suite: needs=psql   # picked up by tests/all.py
"""Migrations already on `game` are append-only (docs/LESSONS.md entry 15, docs/BACKEND.md section 9).

`supabase db push` runs each migration file once and never again: a project that ran a file keeps what it made, even
if the file is edited later. So a file that is on `game` (from where the owner may run runbook B1 at any time) must
never change, and a change goes into a new file after the last one. This suite proves it:

  1. every migration file on `game` is here, byte for byte (none edited, renamed or removed);
  2. every other file sorts after the last one on `game`;
  3. two local databases end with the same schema: one built fresh from every file here, the other from `game`'s files
     first and then the new ones (what a project that ran B1 earlier gets from the next `supabase db push`).

    python3 tests/migrations_check.py

`game` is origin/game (fetched), or the local branch when there is no remote one."""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db'))
import pg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIG = 'supabase/migrations'
fails = []


def check(label, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + label + ('' if ok else f'   <- {str(detail)[:300]}'))
    if not ok:
        fails.append(label)


def git(*a):
    return subprocess.run(['git', '-C', ROOT] + list(a), capture_output=True, text=True)


def schema(files_dir):
    """The schema (pg_dump --schema-only) of a fresh database built from the .sql files in files_dir, in order."""
    os.environ['WI_MIGRATIONS'] = files_dir
    db = pg.start()
    try:
        r = subprocess.run([os.path.join(db.bin, 'pg_dump'), '-s', '-x', '-h', db.sock, '-p', str(db.port), '-U', 'supabase_admin', pg.DB],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError('pg_dump: ' + r.stderr)
        acl = db.psql("select n.nspname || '.' || c.relname || ' ' || coalesce(c.relacl::text, '') from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                      "where n.nspname in ('public', 'private', 'app') order by 1")[0]
        fn = db.psql("select p.oid::regprocedure::text || ' ' || coalesce(p.proacl::text, '') from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
                     "where n.nspname in ('public', 'private', 'app') order by 1")[0]
        return [ln for ln in r.stdout.splitlines() if not ln.startswith('--') and not ln.startswith('\\restrict') and not ln.startswith('\\unrestrict')], acl, fn
    finally:
        db.stop()


def main():
    base = next((b for b in ('origin/game', 'game') if git('rev-parse', '--verify', '-q', b).returncode == 0), None)
    if not base:
        sys.exit('no game branch to compare with (git fetch origin game)')
    on_game = sorted(x.split('/')[-1] for x in git('ls-tree', '--name-only', base, MIG + '/').stdout.split() if x.endswith('.sql'))
    here = sorted(f for f in os.listdir(os.path.join(ROOT, MIG)) if f.endswith('.sql'))
    changed = [f for f in on_game if f not in here or git('show', f'{base}:{MIG}/{f}').stdout != open(os.path.join(ROOT, MIG, f), encoding='utf-8').read()]
    check(f'every migration on {base} is here unchanged ({len(on_game)} files): append-only', on_game and not changed, changed)
    new = [f for f in here if f not in on_game]
    check('every new migration sorts after the last one on game', all(f > on_game[-1] for f in new) if on_game else True, (on_game[-1:], new))
    with tempfile.TemporaryDirectory() as old:
        for f in on_game:
            open(os.path.join(old, f), 'w', encoding='utf-8').write(git('show', f'{base}:{MIG}/{f}').stdout)
        for f in new:
            open(os.path.join(old, f), 'w', encoding='utf-8').write(open(os.path.join(ROOT, MIG, f), encoding='utf-8').read())
        a = schema(old)
    b = schema(os.path.join(ROOT, MIG))
    diff = [ln for ln in set(a[0]) ^ set(b[0])][:5]
    check(f"the same schema both ways: fresh from all {len(here)} files, and game's {len(on_game)} then the {len(new)} new ones (tables, views, functions, grants)",
          a == b and len(a[0]) > 100, diff or (a[1] != b[1], a[2] != b[2]))
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
