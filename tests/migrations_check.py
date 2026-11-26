#!/usr/bin/env python3
# suite: needs=psql   # picked up by tests/all.py
"""Migrations already on `game` are append-only (docs/LESSONS.md entry 16, docs/BACKEND.md section 9).

`supabase db push` runs each migration file once and never again: a project that ran a file keeps what it made, even
if the file is edited later. So a file that is on `game` (from where the owner may run runbook B1 at any time) must
never change, and a change goes into a new file after the last one. This suite proves it:

  1. every migration file on `game` is here, byte for byte (none edited, renamed or removed);
  2. every other file sorts after the last one on `game`;
  3. two local databases end with the same schema: one built fresh from every file here, the other from `game`'s files
     first, then a class with its teacher, pupils, answers and settings in it, and only then the new files (what a
     project that ran B1 earlier and has been used gets from the next `supabase db push`): a new file that cannot run
     on a table with rows (a column added NOT NULL without a default, a check the old rows break) fails here.

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


ROWS = """
insert into auth.users (id) values ('00000000-0000-4000-8000-0000000000a1'), ('00000000-0000-4000-8000-0000000000b1');
insert into public.classes (id, name) values ('00000000-0000-4000-8000-0000000000c1', 'Test class');
insert into public.teachers (user_id, class_id) values ('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-0000000000c1');
insert into public.roster (class_id, name_key, display_name) values ('00000000-0000-4000-8000-0000000000c1', 'pupil one', 'Pupil One');
insert into public.pupils (id, class_id, display_name, auth_user_id)
  values ('00000000-0000-4000-8000-0000000000d1', '00000000-0000-4000-8000-0000000000c1', 'Pupil One', '00000000-0000-4000-8000-0000000000b1');
insert into private.auth_lock_events (class_id, name_key, kind) values ('00000000-0000-4000-8000-0000000000c1', 'pupil one', 'code');
insert into public.flags (pupil_id, kind, day) values ('00000000-0000-4000-8000-0000000000d1', 'rate', current_date);
insert into public.pupils (id, class_id, display_name) values ('00000000-0000-4000-8000-0000000000d2', '00000000-0000-4000-8000-0000000000c1', 'Pupil Two');
-- once game holds 0009: a pupil taken out of the class too (a hidden class and a removed row), so a later file meets them
do $$ begin
  if to_regprocedure('public.teacher_remove_pupil(uuid)') is not null then
    perform set_config('request.jwt.claims', '{"role": "authenticated", "sub": "00000000-0000-4000-8000-0000000000a1"}', true);
    execute 'select public.teacher_remove_pupil(''00000000-0000-4000-8000-0000000000d2'')';
  end if;
end $$;
"""


def schema(files_dir, then=None):
    """The schema (pg_dump --schema-only) of a fresh database built from the .sql files in files_dir, in order; with
    `then`, rows are put in after those files and the files in `then` are applied on top of them."""
    os.environ['WI_MIGRATIONS'] = files_dir
    db = pg.start()
    try:
        if then:
            rows, err = db.psql(ROWS, user='supabase_admin')
            if err:
                raise RuntimeError('rows: ' + err)
            for f in then:
                rows, err = db.psql(None, file=f)
                if err:
                    raise RuntimeError(f'{os.path.basename(f)} on a database with rows: {err}')
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
        try:
            a = schema(old, then=[os.path.join(ROOT, MIG, f) for f in new])
        except RuntimeError as e:
            a = ([str(e)], [], [])
    b = schema(os.path.join(ROOT, MIG))
    diff = a[0] if len(a[0]) == 1 else [ln for ln in set(a[0]) ^ set(b[0])][:5]     # one line: the error of a new file
    check(f"the same schema both ways: fresh from all {len(here)} files, and game's {len(on_game)} with a class in it, then the {len(new)} new ones (tables, views, functions, grants)",
          a == b and len(a[0]) > 100, diff or (a[1] != b[1], a[2] != b[2]))
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
