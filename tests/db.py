#!/usr/bin/env python3
# suite: needs=psql   # picked up by tests/all.py
"""Backend database tests (docs/BACKEND.md sections 2 and 5). One command, no Docker, no Supabase project:

    python3 tests/db.py            # access rules, points, then the load test
    python3 tests/db.py --no-load  # skip the load test
    python3 tests/db.py --load     # only the load test

Starts a throw-away local PostgreSQL (tests/db/pg.py), applies supabase/migrations as written, and acts as a visitor,
a pupil or a teacher only through five API-shaped calls (select, rpc, insert, update, delete), so the same assertions
can run against a real project's REST API later (docs/BACKEND.md section 11 lists what this stand-in cannot prove).
Set-up and the "what is really in the table" checks use SQL as the owner. All names and codes are made up.
Exit code 0 only when every check passed."""
import secrets, json, os, sys, threading, time, uuid
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db'))
import pg

PASS = FAIL = 0


def check(label, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(('PASS ' if ok else 'FAIL ') + label + ('' if ok else '   <- ' + str(detail)[:300]))


def rows_n(label, res, n):
    rows, err = res
    check(label, err is None and len(rows) == n, err or f'{len(rows)} rows: {rows[:3]}')


def denied(label, res, what='permission denied'):
    val, err = res
    check(label, err is not None and what in err, err or f'no error: {str(val)[:200]}')


def eq(label, got, want):
    check(label, got == want, f'got {got!r}, want {want!r}')


U = lambda n: str(uuid.UUID(int=n))          # fixed ids, easy to read in failures
C1, C2 = U(0xC1), U(0xC2)
T1, T2, STRAY = U(0x71), U(0x72), U(0x99)
KIDS = {k: (U(0xA00 + i), U(0xB00 + i)) for i, k in enumerate('ABCDEFGHX')}    # name -> (auth user id, pupil id)
NAMES = dict(A='נועה', B='איתי', C='מאיה', D='עומר', E='שחר', F='רוני', G='טל', H='גיל', X='דנה')
uid = lambda k: KIDS[k][0]
pid = lambda k: KIDS[k][1]
ANON = ('anon', None)
kid = lambda k: ('authenticated', uid(k))
TEACHER1, TEACHER2, NOBODY = ('authenticated', T1), ('authenticated', T2), ('authenticated', STRAY)
SERVER = ('service_role', None)
NOW = int(time.time() * 1000)
BASE = NOW - 40 * 3600 * 1000                 # answers are placed on a timeline that starts 40 hours ago


def ans(n=1, minute=0, step_s=30, key='cat', correct=True, first=True, **extra):
    return [dict(type='answer', game='en', item=key if n == 1 else f'{key}{i}', correct=correct, first_try=first,
                 t=BASE + minute * 60000 + i * step_s * 1000, **extra) for i in range(n)]


def record(db, k, events, batch=None):
    return db.rpc(kid(k), 'record_events', dict(p_batch=batch or str(uuid.uuid4()), p_events=events))


def fixture(db):
    sql = [f"insert into public.classes (id, name, grade, name_form) values ('{C1}', 'test class 1', '5', 'first'), ('{C2}', 'test class 2', '5', 'first');"]
    users = [T1, T2, STRAY] + [a for a, _ in KIDS.values()]
    sql.append("insert into auth.users (id, email) values " + ', '.join(f"('{u}', '{u}@test.invalid')" for u in users) + ';')
    sql.append(f"insert into public.teachers values ('{T1}', '{C1}'), ('{T2}', '{C2}');")
    for k, (a, p) in KIDS.items():
        sql.append(f"insert into public.pupils (id, class_id, display_name, auth_user_id) values ('{p}', '{C2 if k == 'X' else C1}', '{NAMES[k]}', '{a}');")
        sql.append(f"insert into private.pupil_secrets (pupil_id, code_salt, code_hash, pic_salt, pic_hash) values ('{p}', '\\x01', decode(repeat('ab', 32), 'hex'), '\\x02', decode(repeat('cd', 32), 'hex'));")
    sql.append(f"insert into private.class_codes values ('{C1}', decode(repeat('11', 32), 'hex')), ('{C2}', decode(repeat('22', 32), 'hex'));")
    sql.append(f"insert into public.roster values ('{C1}', 'נועה', 'נועה'), ('{C2}', 'דנה', 'דנה');")
    # the catalogue, as the seed generated from the content files will provide it
    keys = ['cat', 'dog', 'sun', 'hat', 'same', 'hard', 'bword0', 'bword1', 'xword0', 'xword1'] + [f'{p}{i}' for p in ('w', 'd', 'old', 'burst') for i in range(200 if p == 'burst' else 30)]
    sql.append("insert into public.items (game, item_key) values " + ', '.join(f"('en', '{k}')" for k in keys) + ';')
    sql.append("insert into public.levels (game, level_key, size) values " + ', '.join(f"('math', 'bay:{i}', 0)" for i in range(1, 9))
               + ", ('read', 't1', 0), ('read', 't2', 0), ('exam', 'p1', 20);")
    sql.append('update private.settings set save_gap_s = 0;')      # the 5-second rule has its own test (test_saves)
    db.admin('\n'.join(sql))


PUBLIC_TABLES = ['classes', 'roster', 'teachers', 'pupils', 'items', 'levels', 'level_best', 'answers', 'points', 'pupil_totals', 'progress', 'flags', 'answer_daily']
VIEWS = ['class_board', 'teacher_view', 'teacher_items', 'backend_health']
PRIVATE_TABLES = ['class_codes', 'pupil_secrets', 'reset_codes', 'pupil_devices', 'legacy_import', 'auth_attempts', 'auth_buckets',
                  'auth_lock_events', 'ip_salts', 'answer_batches', 'pupil_days', 'settings', 'deletions', 'maintenance_log', 'class_misses',
                  'teacher_resets', 'limbo', 'removed_pupils', 'schools', 'grades', 'pupil_carry']
PUPIL_KEYED = ['pupil_totals', 'progress', 'answers', 'points', 'flags', 'answer_daily', 'level_best']
PUPIL_KEYED_PRIVATE = ['pupil_secrets', 'reset_codes', 'pupil_devices', 'legacy_import', 'answer_batches', 'pupil_days', 'removed_pupils', 'pupil_carry']


def test_catalogue(db):
    """Whole-catalogue checks: they also catch a table or function added later without its lock."""
    print('\n== catalogue: grants, RLS, definer functions ==')
    rel = """select n.nspname || '.' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
             where n.nspname in ('public', 'private', 'app') and case when c.relkind in ('r', 'v', 'm', 'p') then %s else false end order by 1"""
    seq = """select n.nspname || '.' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
             where n.nspname in ('public', 'private', 'app') and case when c.relkind = 'S' then has_sequence_privilege('%s', c.oid, 'USAGE,SELECT,UPDATE') else false end"""
    fn = """select n.nspname || '.' || p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where n.nspname in ('public', 'private', 'app') and has_function_privilege('%s', p.oid, 'EXECUTE') order by 1"""
    ALLP = "'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'"
    eq('anon: no right on any table or view', db.admin(rel % f"has_table_privilege('anon', c.oid, {ALLP})"), [])
    eq('anon: no right on any sequence', db.admin(seq % 'anon'), [])
    eq('anon: may run exactly two functions, the keep-alive and the token-guarded encrypted export', db.admin(fn % 'anon'), [['public.backup_export'], ['public.ping']])
    eq('anon: no usage on schema private or app', db.admin("select has_schema_privilege('anon', 'private', 'USAGE') or has_schema_privilege('anon', 'app', 'USAGE')"), [['f']])
    eq('authenticated: no usage on schema private', db.admin("select has_schema_privilege('authenticated', 'private', 'USAGE')"), [['f']])
    eq('authenticated: no right on any private table',
       db.admin(rel % f"n.nspname = 'private' and has_table_privilege('authenticated', c.oid, {ALLP})"), [])
    eq('authenticated: may write to no table except the class list (teacher only, by policy)',
       db.admin(rel % "has_table_privilege('authenticated', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE')"), [['public.roster']])
    eq('authenticated: no right on any sequence', db.admin(seq % 'authenticated'), [])
    eq('authenticated: may run exactly the listed functions', [r[0] for r in db.admin(fn % 'authenticated')],
       ['app.class_id', 'app.name_chars_ok', 'app.name_key', 'app.name_ok', 'app.obj', 'app.pupil_id', 'app.reads_class', 'app.reads_pupil', 'app.safe_int', 'app.shadow', 'app.teaches', 'app.teaches_pupil', 'app.week_start',
        'public.grade_board', 'public.ping', 'public.record_events', 'public.save_progress', 'public.teacher_delete_pupil', 'public.teacher_remove_pupil',
        'public.teacher_removed', 'public.teacher_restore_pupil'])
    eq('row level security is on for every table in public and private',
       db.admin("""select n.nspname || '.' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
                   where n.nspname in ('public', 'private') and c.relkind = 'r' and not c.relrowsecurity"""), [])
    eq('every table in public has a policy or no grant at all', db.admin(
        """select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = 'public' and c.relkind = 'r' and has_table_privilege('authenticated', c.oid, 'SELECT')
             and not exists (select 1 from pg_policy p where p.polrelid = c.oid)"""), [])
    eq('every security definer function pins its search_path to nothing', db.admin(
        """select n.nspname || '.' || p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname in ('public', 'private', 'app') and p.prosecdef
             and not exists (select 1 from unnest(coalesce(p.proconfig, '{}')) c where c in ('search_path=""', 'search_path='))"""), [])
    eq('every view is a security barrier', db.admin(
        """select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = 'public' and c.relkind = 'v' and c.reloptions::text like '%security_barrier=true%'"""), [[str(len(VIEWS))]])
    eq('this file knows every table (a new table must be added to the lists above and so to the tests)',
       sorted(r[0] for r in db.admin("select n.nspname || '.' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname in ('public', 'private') and c.relkind = 'r'")),
       sorted(['public.' + t for t in PUBLIC_TABLES] + ['private.' + t for t in PRIVATE_TABLES]))


def test_anon(db):
    print('\n== anon (the public key, not signed in) sees nothing ==')
    for t in PUBLIC_TABLES + VIEWS:
        denied(f'anon: select {t}', db.select(ANON, t))
    for t in ('pupil_secrets', 'class_codes'):
        denied(f'anon: select private.{t}', db.as_('anon', None, f'select * from private.{t}'))
    denied('anon: record_events', db.rpc(ANON, 'record_events', dict(p_batch=str(uuid.uuid4()), p_events=[])))
    denied('anon: save_progress', db.rpc(ANON, 'save_progress', dict(p_state={})))
    denied('anon: maintenance', db.rpc(ANON, 'maintenance'))
    denied('anon: insert a pupil', db.insert(ANON, 'pupils', dict(class_id=C1, display_name='mallory')))
    denied('anon with a forged pupil id in the claims still has no grant', db.select(('anon', uid('A')), 'pupils'))
    eq('anon: the keep-alive answers true and nothing else', db.rpc(ANON, 'ping'), (True, None))


def test_pupil(db):
    print('\n== pupil A against pupil B (same class) and pupil X (another class) ==')
    A = kid('A')
    db.admin(f"""update public.progress set state = '{{"secret":"b"}}' where pupil_id = '{pid('B')}';
                 update public.progress set state = '{{"secret":"x"}}' where pupil_id = '{pid('X')}';""")
    record(db, 'B', ans(2, minute=0, key='bword') + [dict(type='level', game='math', level='bay:1', stars=2)])
    record(db, 'X', ans(2, minute=0, key='xword'))
    db.admin(f"insert into public.flags (pupil_id, kind, day) values ('{pid('A')}', 'rate', current_date)")
    rows, err = db.select(A, 'pupils', 'id')
    eq('A reads the pupils table: only their own row', (rows, err), ([{'id': pid('A')}], None))
    for t in ('answers', 'points', 'pupil_totals', 'progress', 'answer_daily', 'level_best'):
        rows, err = db.select(A, t, 'distinct pupil_id')
        check(f"A reads {t}: no row of another pupil", err is None and all(r['pupil_id'] == pid('A') for r in rows), err or rows)
    rows_n("A reads B's progress by id: nothing", db.select(A, 'progress', where=dict(pupil_id=pid('B'))), 0)
    rows_n("A reads X's answers by id: nothing", db.select(A, 'answers', where=dict(pupil_id=pid('X'))), 0)
    rows_n("A reads B's answers by id: nothing", db.select(A, 'answers', where=dict(pupil_id=pid('B'))), 0)
    rows_n("A reads B's best levels by id: nothing", db.select(A, 'level_best', where=dict(pupil_id=pid('B'))), 0)
    rows_n('A reads classes: only their own class', db.select(A, 'classes', 'id'), 1)
    rows_n('A reads teachers: nothing', db.select(A, 'teachers'), 0)
    denied('A reads the item catalogue: refused', db.select(A, 'items'))
    denied('A reads the level catalogue: refused', db.select(A, 'levels'))
    rows_n('A reads the class list: nothing', db.select(A, 'roster'), 0)
    rows_n('A reads flags (also their own): nothing', db.select(A, 'flags'), 0)
    rows_n('A reads teacher_view: nothing', db.select(A, 'teacher_view'), 0)
    rows_n('A reads teacher_items: nothing', db.select(A, 'teacher_items'), 0)
    for t in PRIVATE_TABLES:
        denied(f'A reads private.{t} (codes, pictures, locks): refused', db.as_(*A, f'select * from private.{t}'))
    denied('A reads code hashes through a join', db.as_(*A, 'select s.code_hash from public.pupils p join private.pupil_secrets s on s.pupil_id = p.id'))
    denied('A calls a private function', db.as_(*A, 'select * from private.totals_check()'))

    print('-- writes')
    denied('A inserts an answer directly', db.insert(A, 'answers', dict(pupil_id=pid('A'), item_id=1, pts=10, correct=True, first_try=True)))
    denied('A inserts points directly', db.insert(A, 'points', dict(pupil_id=pid('A'), delta=100000, reason='fix')))
    denied('A updates their total', db.update(A, 'pupil_totals', dict(points=999999)))
    denied('A updates the points of their answers', db.update(A, 'answers', dict(pts=10)))
    denied('A deletes answers', db.delete(A, 'answers'))
    denied('A gives themselves 3 stars on a level directly', db.insert(A, 'level_best', dict(pupil_id=pid('A'), game='math', level_key='bay:1', stars=3)))
    denied("A updates B's progress", db.update(A, 'progress', dict(state={}), dict(pupil_id=pid('B'))))
    denied('A updates their own progress row directly (only save_progress may)', db.update(A, 'progress', dict(state={})))
    denied('A inserts a progress row for B', db.insert(A, 'progress', dict(pupil_id=pid('B'))))
    denied('A moves to another class', db.update(A, 'pupils', dict(class_id=C2)))
    denied('A renames themselves', db.update(A, 'pupils', dict(display_name='admin')))
    denied('A points their row at another auth user', db.update(A, 'pupils', dict(auth_user_id=uid('B'))))
    denied('A registers a pupil directly', db.insert(A, 'pupils', dict(class_id=C1, display_name='ghost')))
    denied('A makes themselves a teacher', db.insert(A, 'teachers', dict(user_id=uid('A'), class_id=C1)))
    denied('A clears a flag', db.delete(A, 'flags'))
    denied('A adds an item to the catalogue', db.insert(A, 'items', dict(game='en', item_key='zzz')))
    denied('A adds a name to the class list: refused by policy', db.insert(A, 'roster', dict(class_id=C1, name_key='ghost', display_name='ghost')), 'row-level security')
    rows_n('A deletes from the class list: nothing happens', db.delete(A, 'roster'), 0)
    denied('A deletes a pupil as if a teacher', db.rpc(A, 'teacher_delete_pupil', dict(p_pupil=pid('B'))), 'not your pupil')
    denied('A runs maintenance', db.rpc(A, 'maintenance'))

    print('-- save_progress writes the caller only; two devices do not overwrite each other')
    r1, err = db.rpc(A, 'save_progress', dict(p_state={'pts': 1000000, 'k': {'words': 7}, 'streak': 3}))
    eq("A's first save is taken", (r1 and r1['ok'], err), (True, None))
    eq("A's blob is saved", db.one(f"select state ->> 'pts' from public.progress where pupil_id = '{pid('A')}'"), '1000000')
    eq("B's blob is untouched", db.one(f"select state ->> 'secret' from public.progress where pupil_id = '{pid('B')}'"), 'b')
    r2, _ = db.rpc(A, 'save_progress', dict(p_state={'pts': 1000000, 'dev': 'phone'}, p_base=r1['updated_at']))
    eq('a save that names the version it saw is taken', r2['ok'], True)
    r3, _ = db.rpc(A, 'save_progress', dict(p_state={'dev': 'old laptop'}, p_base=r1['updated_at']))
    eq('a second device with a stale version is not written; it gets the current blob back to join',
       (r3['ok'], r3.get('conflict'), r3['state'].get('dev'), db.one(f"select state ->> 'dev' from public.progress where pupil_id = '{pid('A')}'")), (False, True, 'phone', 'phone'))
    r4, _ = db.rpc(A, 'save_progress', dict(p_state={'dev': 'no version'}))
    eq('a save that names no version does not overwrite an existing blob either', (r4['ok'], r4.get('conflict')), (False, True))
    r5, _ = db.rpc(A, 'save_progress', dict(p_state={'pts': 1000000, 'k': {'words': 7}, 'streak': 3, 'dev': 'joined'}, p_base=r3['updated_at']))
    eq('after joining, the save with the fresh version is taken', r5['ok'], True)
    denied('a blob over the size limit is refused', db.rpc(A, 'save_progress', dict(p_state={'x': 'a' * 41000})), 'bad input')
    denied('a blob that is not an object is refused', db.rpc(A, 'save_progress', dict(p_state=[1, 2])), 'bad input')

    print('-- a signed-in user who is neither pupil nor teacher')
    for t in ['pupils', 'answers', 'points', 'pupil_totals', 'progress', 'classes', 'teachers', 'roster', 'flags', 'level_best'] + VIEWS:
        rows_n(f'stray user reads {t}: nothing', db.select(NOBODY, t), 0)
    denied('stray user records events', record_as(db, NOBODY, []), 'not a pupil')
    denied('stray user saves progress', db.rpc(NOBODY, 'save_progress', dict(p_state={})), 'not a pupil')
    rows_n('authenticated with no user id in the token reads the board: nothing', db.select(('authenticated', None), 'class_board'), 0)


def record_as(db, who, events):
    return db.rpc(who, 'record_events', dict(p_batch=str(uuid.uuid4()), p_events=events))


def test_points(db):
    print('\n== points are decided by the database ==')
    A = kid('A')
    tot = lambda k: db.admin(f"select points, answers, first_try, wrong from public.pupil_totals where pupil_id = '{pid(k)}'")[0]
    flags = lambda k: sorted(tuple(r) for r in db.admin(f"select kind, n from public.flags where pupil_id = '{pid(k)}'"))
    b1 = str(uuid.uuid4())
    r, err = record(db, 'A', ans(1, 1, key='cat') + ans(1, 2, key='dog', first=False) + ans(1, 3, key='sun', correct=False, first=False), b1)
    eq('right first try 10 + right later 4 + wrong 0 + daily bonus 20', (r and r['points'], err), (34, None))
    eq('totals row: points, answers, first try, wrong', tot('A'), ['34', '3', '1', '2'])
    r, _ = record(db, 'A', ans(1, 1, key='cat'), b1)
    eq('the same batch sent again is counted once', (r.get('dup'), tot('A')[0]), (True, '34'))
    b_before = tot('B')
    r, _ = record(db, 'A', ans(1, 5, key='hat', pts=1000, flag=0, pupil_id=pid('B'), delta=5000, points=99999))
    eq('forged fields in an event (pts, pupil_id, points) are ignored: A gets 10, B gets nothing', (r['points'], tot('B')), (44, b_before))
    eq('the blob says 1,000,000 points; the board says 44', db.select(A, 'class_board', 'points', dict(me=True)), ([{'points': 44}], None))
    rows, err = db.select(A, 'class_board', 'display_name, me')
    eq('the board shows the whole class and nobody else', (sorted(r['display_name'] for r in rows), err), (sorted(NAMES[k] for k in 'ABCDEFGH'), None))
    eq('the board marks the caller', [r['display_name'] for r in rows if r['me']], [NAMES['A']])
    eq("another class's board is their own only", db.select(kid('X'), 'class_board', 'display_name')[0], [{'display_name': NAMES['X']}])
    eq('the board has no ids', db.admin("select string_agg(column_name, ',' order by ordinal_position) from information_schema.columns where table_schema = 'public' and table_name = 'class_board'"), [['display_name,points,words,streak,me,week']])

    print('-- answers: kept, 0 points, flagged')
    r, _ = record(db, 'C', ans(25, minute=1, step_s=1, key='w'))
    eq('25 answers in 25 seconds: 20 get points, 5 are flagged', (r['added'], r['flagged'], r['points']), (25, 5, 20 * 10 + 20))
    eq('all 25 rows are kept', db.one(f"select count(*) || '/' || count(*) filter (where flag = 1 and pts = 0) from public.answers where pupil_id = '{pid('C')}'"), '25/5')
    eq("the teacher's flag row", flags('C'), [('rate', '5')])
    r, _ = record(db, 'C', ans(200, minute=10, step_s=0, key='burst'))
    eq('200 answers stamped with one instant: only 20 more get points', r['points'], 220 + 200)
    db.admin('update private.settings set max_pointed_day = 5, unusual_answers = 3')
    r, _ = record(db, 'D', ans(8, minute=1, step_s=10, key='d'))
    eq('over the daily cap: 5 answers with points, 3 flagged', (r['points'], r['flagged']), (5 * 10 + 20, 3))
    eq('flags: over the cap, and "unusual" already at the lower mark', flags('D'), [('daycap', '3'), ('unusual', '1')])
    db.admin(f"update private.pupil_days set pointed = 0 where pupil_id = '{pid('D')}'")
    r, _ = record(db, 'D', ans(4, minute=30, step_s=10, key='d'))
    db.admin('update private.settings set max_pointed_day = 600, unusual_answers = 300')
    eq('the cap also counts by arrival: a device that claims another day earns nothing more today', (r['points'], r['flagged']), (70, 4))
    r, _ = record(db, 'E', [dict(type='answer', game='en', item='same', correct=True, first_try=True, t=BASE + i * 60000) for i in range(9)])
    eq('one item right 9 times in a day: 6 count, 3 flagged', (r['points'], r['flagged']), (6 * 10 + 20, 3))
    n_items = db.one('select count(*) from public.items')
    r, _ = record(db, 'E', [dict(type='answer', game='en', item='not in the catalogue', correct=True, first_try=True), 'junk', 7, None,
                           dict(type='answer', game='EN;drop', item='cat', correct=True, first_try=True), dict(type='gift', points=500), dict(game='en', item='cat')])
    eq('unknown items, unknown event types and junk earn nothing, are flagged, nothing breaks', (r['added'], r['flagged'], r['points']), (0, 7, 80))
    eq('and nothing a pupil sent was written into the catalogue or the answers',
       (db.one('select count(*) from public.items'), db.one(f"select count(*) from public.answers where pupil_id = '{pid('E')}'")), (n_items, '9'))
    r, _ = record(db, 'E', [dict(type='answer', game='en', item='w1', correct=True, first_try=True, t=NOW + 10 * 86400000),
                           dict(type='answer', game='en', item='w2', correct=True, first_try=True, t=NOW - 400 * 86400000)])
    eq('times from the future or from last year are pulled into the allowed window',
       db.admin(f"select bool_and(at <= now() and at > now() - interval '49 hours') from public.answers where pupil_id = '{pid('E')}'"), [['t']])
    denied('a batch over 200 events is refused whole', record(db, 'E', ans(201, key='w')), 'bad input')
    denied('events that are not an array are refused', db.rpc(kid('E'), 'record_events', dict(p_batch=str(uuid.uuid4()), p_events={'a': 1})), 'bad input')

    print('-- honest offline play is not cheating; back-dating earns no extra bonus')
    dbx = lambda k: db.admin(f"select kind, n from public.flags where pupil_id = '{pid(k)}'")
    record(db, 'H', [dict(type='answer', game='en', item='hat', correct=True, first_try=True, t=NOW - 60000)])      # the laptop, a minute ago
    r, _ = record(db, 'H', [dict(type='answer', game='en', item=f'w{i}', correct=True, first_try=True, t=NOW - 45 * 60000 + i * 20000) for i in range(29)])   # the phone, played 45 minutes ago, arriving now
    eq('29 answers played earlier on another device, arriving late: all count, nothing is flagged', (r['points'], r['flagged'], dbx('H')), (10 + 20 + 290, 0, []))
    eq('answers from three claimed days in one call bring one daily bonus, not three',
       record_as(db, kid('X'), [dict(type='answer', game='en', item=f'w{i}', correct=True, first_try=True, t=NOW - i * 20 * 3600 * 1000) for i in range(3)])[0]['points'] - int(tot('X')[0]) + 30, 30)

    print('-- one pupil cannot fill the database')
    rows_before = int(db.one('select count(*) from public.answers')) + int(db.one('select count(*) from private.answer_batches'))
    sent = 0
    for i in range(250):            # 50,000 answers and 50 empty calls from one console
        r, err = record(db, 'F', [dict(type='answer', game='en', item=f'burst{j}', correct=False, first_try=False) for j in range(200)])
        sent += 200
    for i in range(50):
        record(db, 'F', [])
    stored = int(db.one(f"select count(*) from public.answers where pupil_id = '{pid('F')}'"))
    batches = int(db.one(f"select count(*) from private.answer_batches where pupil_id = '{pid('F')}'"))
    check(f'{sent} answers sent: at most 300 rows stored for the day, and one batch row per call that stored something', stored <= 300 and batches <= 6, f'{stored} rows, {batches} batch rows')
    eq('the rest is one counter on one flag row', db.admin(f"select n > 49000 from public.flags where pupil_id = '{pid('F')}' and kind = 'daycap'"), [['t']])
    db.admin('update private.settings set max_calls_day = 300')
    r, _ = record(db, 'F', [dict(type='level', game='math', level='bay:1', stars=3)])
    db.admin('update private.settings set max_calls_day = 1500')
    eq('past the daily number of calls nothing at all is processed', (r.get('capped'), r['added']), (True, 0))
    denied('a call over 64 KB is refused before it is looked at', record(db, 'F', [dict(type='answer', game='en', item='x' * 700) for _ in range(100)]), 'bad input')
    db.admin(f"delete from private.pupil_days where pupil_id = '{pid('F')}'; delete from public.flags where pupil_id = '{pid('F')}'")

    print('-- levels, reading, exam, Beach Run: every source of points is priced here')
    lv = lambda i, s: dict(type='level', game='math', level=f'bay:{i}', stars=s)
    r, _ = record(db, 'F', [lv(1, 3)])
    eq('3 stars: 45 + daily bonus 20', r['points'], 65)
    r, _ = record(db, 'F', [lv(1, 4), lv(1, -1), lv(99, 3), dict(type='level', game='math', level='bay:1', stars='3'), dict(type='level', game='read', level='t1', stars=3)])
    eq('4 stars, -1 stars, an unknown level, stars as text, a text passed off as a level: nothing', (r['points'], r['flagged']), (65, 5))
    r, _ = record(db, 'F', [lv(1, 1), lv(2, 2)])
    eq('best stars per level are kept (3 stays 3)', sorted(tuple(x) for x in db.admin(f"select level_key, stars from public.level_best where pupil_id = '{pid('F')}'")), [('bay:1', '3'), ('bay:2', '2')])
    db.admin('update private.settings set max_levels_day = 4, unusual_levels = 4')
    r, _ = record(db, 'F', [lv(i, 3) for i in range(3, 8)])
    db.admin('update private.settings set max_levels_day = 20, unusual_levels = 12')
    eq('levels over the daily cap earn nothing and are flagged; "unusual" marks the day', (r['points'], [f for f in flags('F') if f[0] != 'items']), (65 + 15 + 30 + 45, [('levels', '4'), ('unusual', '1')]))
    r, _ = record(db, 'G', [dict(type='read', text='t1'), dict(type='read', text='t1'), dict(type='read', text='nope')])
    eq('a perfect text pays 50 once; again pays nothing; an unknown text is flagged', (r['points'], r['flagged']), (70, 1))
    r, _ = record(db, 'G', [dict(type='exam', paper='p1', right=12), dict(type='exam', paper='p1', right=21), dict(type='exam', paper='p1', right=20), dict(type='exam', paper='p1', right=1), dict(type='exam', paper='p1', right=20)])
    eq('exam: 5 a right answer, never more right answers than the paper has, 3 papers a day', (r['points'], r['flagged']), (70 + 60 + 100 + 5, 2))
    r, _ = record(db, 'G', [dict(type='run', points=40), dict(type='run', points=40), dict(type='run', points=5), dict(type='run', points=61), dict(type='run', points=-5), dict(type='run', points=2.5)])
    eq('Beach Run: 60 a day in total, whatever is sent', (r['points'], r['flagged']), (235 + 60, 4))
    eq('the ledger names every source', sorted(tuple(x) for x in db.admin(f"select reason, sum(delta) from public.points where pupil_id = '{pid('G')}' group by 1")), [('day', '20'), ('exam', '165'), ('read', '50'), ('run', '60')])

    print('-- a damaged or hostile blob cannot break the board or the teacher screen')
    v = db.rpc(kid('B'), 'save_progress', dict(p_state={"k": {"words": "many", "reads": {"a": 1}}, "streak": 1e30, "pts": "x", "g": {"st": {"l1": 99, "l2": "x"}}}, p_base=db.one(f"select to_json(updated_at) #>> '{{}}' from public.progress where pupil_id = '{pid('B')}'")))
    db.admin(f"""update public.progress set state = '{{"k": 5, "g": [1, 2], "streak": -4}}' where pupil_id = '{pid('C')}'""")
    rows, err = db.select(A, 'class_board', 'display_name, words, streak')
    check('the board still loads for the class', v[0]['ok'] and err is None and len(rows) == 8, err or rows)
    eq("the teacher's stars come from the server's level ledger, not from the blob (99 stars claimed, 2 earned)",
       db.select(TEACHER1, 'teacher_view', 'stars, levels, words, streak', dict(pupil_id=pid('B'))), ([{'stars': 2, 'levels': 1, 'words': 0, 'streak': 1000}], None))
    eq('pupil_totals equals the ledgers for every pupil', db.admin('select * from private.totals_check()'), [])


def test_teacher(db):
    print('\n== a teacher sees only her class ==')
    T = TEACHER1
    rows, err = db.select(T, 'pupils', 'class_id')
    check('teacher 1 reads pupils: her 8, none of class 2', err is None and len(rows) == 8 and all(r['class_id'] == C1 for r in rows), err or rows)
    rows_n('teacher 1 reads teacher_view: 8 rows', db.select(T, 'teacher_view'), 8)
    rows_n("teacher 1 reads class 2's pupil by id: nothing", db.select(T, 'pupils', where=dict(id=pid('X'))), 0)
    for t in ('answers', 'points', 'pupil_totals', 'progress', 'answer_daily', 'flags', 'level_best'):
        rows_n(f"teacher 1 reads {t} of a class 2 pupil: nothing", db.select(T, t, where=dict(pupil_id=pid('X'))), 0)
    rows, err = db.select(T, 'teacher_items', 'distinct class_id')
    check('teacher_items: only her class', err is None and all(r['class_id'] == C1 for r in rows), err or rows)
    rows_n('teacher_items: an item needs 3 tries to appear', db.select(T, 'teacher_items', where=dict(item_key='sun')), 0)
    rows_n('teacher 1 reads classes: one', db.select(T, 'classes'), 1)
    rows_n('teacher 1 reads teachers: herself only', db.select(T, 'teachers'), 1)
    eq('teacher 1 sees the flags of her pupil', db.select(T, 'flags', 'kind', dict(pupil_id=pid('C'), kind='rate'))[0], [{'kind': 'rate'}])
    eq('teacher_view row: server points, code and recovery status, locks today',
       db.select(T, 'teacher_view', 'points, answers, code_status, recovery_status, locked_today', dict(pupil_id=pid('A')))[0],
       [dict(points=44, answers=4, code_status='set', recovery_status='open', locked_today=0)])
    db.admin(f"""insert into private.auth_lock_events (class_id, name_key, kind) values ('{C1}', '{NAMES['A']}', 'code'), ('{C1}', '{NAMES['A']}', 'code'), ('{C2}', '{NAMES['A']}', 'code');
                 insert into private.auth_buckets (class_id, name_key, kind, bucket, locked_until) values ('{C1}', '{NAMES['A']}', 'picture', '*', 'infinity');
                 update private.pupil_secrets set code_hash = null where pupil_id = '{pid('A')}';""")
    eq("teacher_view after a reset and locks: waiting, closed, locked 2 times today (not the other class's 1)",
       db.select(T, 'teacher_view', 'code_status, recovery_status, locked_today', dict(pupil_id=pid('A')))[0], [dict(code_status='waiting', recovery_status='closed', locked_today=2)])
    # the class's day is private.settings.tz, as for the points and the roll-up, not a zone written into the view. A zone
    # whose date differs from Jerusalem's right now, a lock a minute before the later of the two midnights (today in one
    # zone only) and a flag on the edge of the week: the view must follow settings.tz, whichever side that is
    z = next(z for z in ('Pacific/Kiritimati', 'Pacific/Pago_Pago') if db.one(f"select (now() at time zone '{z}')::date <> (now() at time zone 'Asia/Jerusalem')::date") == 't')
    db.admin(f"update private.settings set tz = '{z}'")
    seen = lambda: db.select(T, 'teacher_view', 'locked_today, flags_week', dict(pupil_id=pid('B')))[0][0]
    before = seen()
    mid = lambda zone: f"(date_trunc('day', now() at time zone '{zone}') at time zone '{zone}')"
    today = lambda zone: f"(now() at time zone '{zone}')::date"
    db.admin(f"""insert into private.auth_lock_events (class_id, name_key, kind, at) values ('{C1}', '{NAMES['B']}', 'code', greatest({mid(z)}, {mid('Asia/Jerusalem')}) - interval '1 minute');
                 insert into public.flags (pupil_id, kind, day) values ('{pid('B')}', 'unusual', case when {today(z)} < {today('Asia/Jerusalem')} then {today(z)} - 6 else {today(z)} - 7 end)
                   on conflict (pupil_id, kind, day) do update set n = public.flags.n + 1;""")
    want = db.admin(f"select ({mid(z)} < {mid('Asia/Jerusalem')})::int, ({today(z)} < {today('Asia/Jerusalem')})::int")[0]
    after = seen()
    eq(f"teacher_view's locks today and flags this week follow settings.tz ({z}), not Jerusalem's day",
       [after['locked_today'] - before['locked_today'], after['flags_week'] - before['flags_week']], [int(want[0]), int(want[1])])
    db.admin("update private.settings set tz = 'Asia/Jerusalem'")
    eq('teacher_view never carries a hash', db.admin("select count(*) from information_schema.columns where table_schema = 'public' and table_name = 'teacher_view' and (column_name like '%hash%' or column_name like '%salt%')"), [['0']])
    # the teacher's screen (docs/PHASE3.md step 2) reads exactly these three views: who sees what, every reader against
    # every view. A teacher: her class only. A pupil's session, a signed-in user who teaches nothing: no row. anon: refused.
    screen = {'teacher_view': 'class_id', 'teacher_items': 'class_id', 'backend_health': 'warn'}
    got = {}
    for who, label in [(TEACHER1, 'teacher 1'), (TEACHER2, 'teacher 2'), (kid('A'), 'a pupil'), (NOBODY, 'a user who teaches nothing')]:
        for v, col in screen.items():
            rows, err = db.select(who, v, col)
            got[(label, v)] = [err is None, sorted({r[col] for r in rows}) if col == 'class_id' else len(rows)]
    eq("the teacher's screen: teacher 1 reads her class only (pupils, hard words) and one health row",
       [got[('teacher 1', 'teacher_view')], got[('teacher 1', 'teacher_items')], got[('teacher 1', 'backend_health')]], [[True, [C1]], [True, [C1]], [True, 1]])
    eq("teacher 2 reads her class only, never class 1's",
       [got[('teacher 2', 'teacher_view')][1], C1 in got[('teacher 2', 'teacher_items')][1], got[('teacher 2', 'backend_health')]], [[C2], False, [True, 1]])
    eq("a pupil's session and a user who teaches nothing: no row in any of the three",
       [got[(w, v)] for w in ('a pupil', 'a user who teaches nothing') for v in screen], [[True, []], [True, []], [True, 0]] * 2)
    for v in screen:
        denied(f'anon reads {v}: refused', db.select(ANON, v))
    denied('teacher 1 reads the secrets table: refused like anyone', db.as_(*T, 'select * from private.pupil_secrets'))
    denied('teacher 1 writes points', db.insert(T, 'points', dict(pupil_id=pid('A'), delta=5, reason='fix')))
    denied('teacher 1 edits an answer', db.update(T, 'answers', dict(pts=0)))
    denied("teacher 1 adds a name to class 2's list: refused by policy", db.insert(T, 'roster', dict(class_id=C2, name_key='x y', display_name='x y')), 'row-level security')
    rows, err = db.insert(T, 'roster', dict(class_id=C1, name_key='new kid', display_name='New Kid'))
    eq('teacher 1 adds a name to her own class list', (rows and rows[0]['name_key'], err), ('new kid', None))
    rows_n("teacher 1 deletes from class 2's list: nothing happens", db.delete(T, 'roster', dict(class_id=C2)), 0)
    # step 3 of docs/PHASE3.md: what teacher.html sends, checked here by the database itself
    denied('teacher 1 adds a name whose key is not the one the database computes: refused', db.insert(T, 'roster', dict(class_id=C1, name_key='Dana Lee', display_name='Dana Lee')), 'violates check constraint')
    denied('teacher 1 adds a name already on her list: refused (no double)', db.insert(T, 'roster', dict(class_id=C1, name_key='new kid', display_name='New  Kid'.replace('  ', ' '))), 'duplicate key')
    rows, err = db.select(T, 'classes', 'id')
    eq("teacher 1 reads the classes: hers only (the page's class list and its unlock button)", ([r['id'] for r in rows or []], err), ([C1], None))
    rows, err = db.select(T, 'teacher_view', 'pupil_id, class_id')
    eq('the screen gets each pupil id and class id, of her class only (the actions name them)', (bool(rows) and all(r['pupil_id'] and r['class_id'] == C1 for r in rows), err), (True, None))
    n_pupils = db.admin(f"select count(*) from public.pupils where class_id = '{C1}'")
    rows, err = db.delete(T, 'roster', dict(class_id=C1, name_key='new kid'))
    eq('teacher 1 removes exactly one name from her own list, and gets it back (the page shows what was removed)', ([r['name_key'] for r in rows or []], err), (['new kid'], None))
    eq('removing a name from the list removes no pupil', db.admin(f"select count(*) from public.pupils where class_id = '{C1}'"), n_pupils)
    denied('teacher 1 deletes a pupil of class 2', db.rpc(T, 'teacher_delete_pupil', dict(p_pupil=pid('X'))), 'not your pupil')

    print('-- deleting a pupil removes them from every table')
    g, name = pid('G'), NAMES['G']
    db.admin(f"""insert into private.reset_codes (pupil_id, salt, hash, expires_at) values ('{g}', '\\x01', decode(repeat('ee', 32), 'hex'), now() + interval '1 day');
                 insert into private.pupil_devices (pupil_id, device_hash) values ('{g}', '\\x0102');
                 insert into private.legacy_import values ('{g}', 's', repeat('a', 64));
                 insert into private.removed_pupils (pupil_id, class_id, removed_at) values ('{g}', '{C1}', now());
                 insert into private.pupil_carry (pupil_id, pts, tries) values ('{g}', 1, 1);
                 insert into public.answer_daily (pupil_id, day, item_id, tries) values ('{g}', current_date - 100, 1, 1);
                 insert into public.flags (pupil_id, kind, day) values ('{g}', 'rate', current_date);
                 insert into public.level_best (pupil_id, game, level_key, stars) values ('{g}', 'math', 'bay:1', 1);
                 insert into private.auth_attempts (class_id, name_key, kind) values ('{C1}', '{name}', 'code');
                 insert into private.auth_buckets (class_id, name_key, kind, bucket) values ('{C1}', '{name}', 'code', 'd:x');
                 insert into private.auth_lock_events (class_id, name_key, kind) values ('{C1}', '{name}', 'code');""")
    record(db, 'G', ans(1, 50, key='cat'))
    count = lambda: {t: int(db.one(f"select count(*) from {sch}.{t} where pupil_id = '{g}'")) for sch, ts in (('public', PUPIL_KEYED), ('private', PUPIL_KEYED_PRIVATE)) for t in ts} | \
        {t: int(db.one(f"select count(*) from private.{t} where class_id = '{C1}' and name_key = '{name}'")) for t in ('auth_attempts', 'auth_buckets', 'auth_lock_events')} | \
        {'pupils': int(db.one(f"select count(*) from public.pupils where id = '{g}'")), 'auth.users': int(db.one(f"select count(*) from auth.users where id = '{uid('G')}'"))}
    before = count()
    check('before: the pupil has rows in every table that can hold them', all(v > 0 for v in before.values()), before)
    eq('every table with a pupil_id column is covered by this test', sorted(r[0] for r in db.admin("select table_schema || '.' || table_name from information_schema.columns where column_name = 'pupil_id' and table_schema in ('public', 'private') and table_name not in ('teacher_view', 'deletions')")),
       sorted(['public.' + t for t in PUPIL_KEYED] + ['private.' + t for t in PUPIL_KEYED_PRIVATE]))
    v, err = db.rpc(T, 'teacher_delete_pupil', dict(p_pupil=g))
    after = count()
    check('teacher 1 deletes her pupil: nothing of them is left anywhere, the auth user included', err is None and all(x == 0 for x in after.values()), err or after)
    eq('the deletion is on record (who, which class, how much), without the name',
       db.admin(f"select teacher, class_id, pupil_id, answers > 0 from private.deletions"), [[T1, C1, g, 't']])
    check('the record holds no name column', 'name' not in db.one("select string_agg(column_name, ',') from information_schema.columns where table_schema = 'private' and table_name = 'deletions'"))
    rows_n('teacher 2 reads pupils: only class 2', db.select(TEACHER2, 'pupils'), 1)
    rows_n('teacher 2 reads the board: only class 2', db.select(TEACHER2, 'class_board'), 1)

    print('-- constraints')
    bad = lambda name: db.psql(f"insert into public.pupils (class_id, display_name) values ('{C1}', $n${name}$n$)")[1]
    check('a name with markup is refused by the table', bad('<b>x</b>') is not None)
    check('a spreadsheet formula as a name is refused', bad('=1+1') is not None)
    check('a one-letter name is refused', bad('x') is not None)
    check('a name with a zero-width character is refused (it would look like another pupil)', bad('Da\u200bna') is not None)
    check('a name with a direction-override character is refused', bad('Da\u202ena') is not None and bad('\ufeffDana') is not None)
    denied("the class list has the same rule: a teacher's token cannot store markup in it", db.insert(TEACHER1, 'roster', dict(class_id=C1, name_key='<b onclick=x>', display_name='<b onclick=x>')), 'violates check constraint')
    denied('nor an invisible character', db.insert(TEACHER1, 'roster', dict(class_id=C1, name_key='da\u200bna', display_name='Da\u200bna')), 'violates check constraint')
    check('the same name twice in a class is one pupil', 'duplicate key' in (bad(NAMES['A']) or ''))
    check('the same name in another class is allowed; letter case does not make a second pupil',
          bad("O'Neil-Ben") is None and db.psql(f"insert into public.pupils (class_id, display_name) values ('{C2}', $n$O'Neil-Ben$n$)")[1] is None
          and 'duplicate key' in (db.psql(f"insert into public.pupils (class_id, display_name) values ('{C2}', $n$o'neil-ben$n$)")[1] or ''))
    print('-- names: an allow-list (Hebrew or Latin letters), not a list of what is forbidden')
    for n, why in [('\u3164\u3164', 'Hangul filler (renders blank)'), ('Da\u2060na', 'word joiner'), ('Da\u00adna', 'soft hyphen'), ('Da\u180ena', 'Mongolian vowel separator'),
                   ('Da\u061cna', 'Arabic letter mark (bidi)'), ('D\u0430na', 'Cyrillic a'), ('\u0394ana', 'Greek letter'), ('Dana\U0001F600', 'emoji'), ('Da\u00a0na', 'no-break space'),
                   ('Dana\u0301\u0301\u0301', 'stacked combining marks'), (' Dana', 'a leading space'), ('Dana ', 'a trailing space'), ('D4na', 'a digit'),
                   ('Dana\u200f', 'right-to-left mark'), ('a' * 21, '21 letters')]:
        check(f'refused: {why}', bad(n) is not None)
    for n, why in [("'Dana", 'an apostrophe first'), ('D\u0131na', 'dotless i (Dına looks like Dina)'), ('\u017Fara', 'long s'), ('\u0138im', 'kra'), ('\u0149ina', "n preceded by '"), ('\u0133ssel', 'ij ligature'), ('Dana-', 'a hyphen last'), ("Da ''", 'an apostrophe after a space'), ('׳נועה', 'a geresh first')]:
        check(f'refused: {why}', bad(n) is not None)
    for n in ['Noa', 'נועה', "O'Neil", 'Chloé', 'בר-לב', 'ג׳ני', 'Ana Mae', 'Dan.', 'ג׳ורג׳', "ג'ורג'", 'ג’ורג’', 'Łukasz', 'Žofie', "D'"]:
        r = db.psql(f"select app.name_ok($n${n}$n$)")[0][0][0]
        check(f'allowed: {n}', r == 't', r)

    print('-- maintenance (server role only)')
    record(db, 'H', ans(4, minute=0, key='old') + ans(1, 5, key='hard', correct=False, first=False) + ans(1, 6, key='hard', correct=False, first=False) + ans(1, 7, key='hard'))
    before = db.admin(f"select points, answers from public.pupil_totals where pupil_id = '{pid('H')}'")
    # the day of an answer is the class's day (Asia/Jerusalem), never UTC's: answers on both sides of local midnight,
    # winter (UTC+2: midnight is 22:00 UTC) and summer (UTC+3: 21:00 UTC), and on both sides of 00:00 UTC (02:00 or
    # 03:00 local, the same local day). Fixed dates, so the check does not depend on when the suite runs.
    EDGE = [('d20', '2026-03-10 21:59:59+00', '2026-03-10'), ('d21', '2026-03-10 22:00:01+00', '2026-03-11'),
            ('d22', '2026-07-10 20:59:59+00', '2026-07-10'), ('d23', '2026-07-10 21:00:01+00', '2026-07-11'),
            ('d24', '2026-03-10 23:59:59+00', '2026-03-11'), ('d25', '2026-03-11 00:00:01+00', '2026-03-11')]
    # written straight into the ledger (they are older than any batch may claim), and into the pupil's totals with
    # them, so totals still equal the ledgers
    book = lambda n: f"insert into public.pupil_totals (pupil_id, points, answers, first_try) values ('{pid('X')}', {10 * n}, {n}, {n}) on conflict (pupil_id) do update set points = public.pupil_totals.points + {10 * n}, answers = public.pupil_totals.answers + {n}, first_try = public.pupil_totals.first_try + {n};"
    db.admin(' '.join(f"insert into public.answers (at, pupil_id, item_id, pts, correct, first_try) select '{at}', '{pid('X')}', id, 10, true, true from public.items where game = 'en' and item_key = '{k}';" for k, at, _ in EDGE) + book(len(EDGE)))
    db.admin("update private.settings set raw_days = 0; insert into auth.audit_log_entries (ip_address, created_at) values ('203.0.113.9', now() - interval '40 days'), ('203.0.113.9', now())")
    m, err = db.rpc(SERVER, 'maintenance')
    db.admin('update private.settings set raw_days = 90')
    check('the server role runs maintenance; totals still equal the ledgers', err is None and m.get('ok') is True and m.get('rolled', 0) > 0, err or m)
    eq('old answers are rolled up, not lost: totals unchanged', db.admin(f"select points, answers from public.pupil_totals where pupil_id = '{pid('H')}'"), before)
    # only the answers this case placed 40 hours back: H also has answers from "45 minutes ago" (the late-arrival case
    # above), which are a past local day when the suite runs in the first 45 minutes after midnight in Israel, and are
    # then rightly rolled too (lead's report, 25.11 22:20 UTC: 36/34/340)
    eq('the roll-up holds them per day and item', db.admin(f"select sum(d.tries), sum(d.first_try), sum(d.pts) from public.answer_daily d join public.items i on i.id = d.item_id where d.pupil_id = '{pid('H')}' and i.item_key in ('old0', 'old1', 'old2', 'old3', 'hard')"), [['7', '5', '50']])
    eq('near midnight, each answer is rolled into its own day in Israel, not the UTC day (22:00 UTC in winter, 21:00 in summer, 00:00 UTC splits nothing)',
       db.admin(f"select i.item_key, d.day::text from public.answer_daily d join public.items i on i.id = d.item_id where d.pupil_id = '{pid('X')}' and i.item_key in ('d20', 'd21', 'd22', 'd23', 'd24', 'd25') order by 1"),
       [[k, day] for k, _, day in EDGE])
    # the class's evening, pinned: local midnight exactly 30 minutes ago (a zone made for it), one answer just before,
    # one just after. The one before is a finished day and is rolled; the one after stays raw. This is the window the
    # report hit, made the same every time.
    import datetime as _dt
    cut = _dt.datetime.now(_dt.timezone.utc).replace(second=0, microsecond=0) - _dt.timedelta(minutes=30)
    off = (-(cut.hour * 60 + cut.minute)) % 1440
    off = off - 1440 if off > 720 else off                          # UTC-12:00 .. UTC+12:00
    zone = f"<{'+' if off >= 0 else '-'}{abs(off) // 60:02d}{abs(off) % 60:02d}>{'-' if off >= 0 else '+'}{abs(off) // 60:02d}:{abs(off) % 60:02d}"
    db.admin(f"insert into public.answers (at, pupil_id, item_id, pts, correct, first_try) select now() - interval '31 minutes', '{pid('X')}', id, 10, true, true from public.items where game = 'en' and item_key = 'd26';"
             f"insert into public.answers (at, pupil_id, item_id, pts, correct, first_try) select now() - interval '29 minutes', '{pid('X')}', id, 10, true, true from public.items where game = 'en' and item_key = 'd27';"
             + book(2) + f"update private.settings set raw_days = 0, tz = '{zone}'")
    m2, err2 = db.rpc(SERVER, 'maintenance')
    yday = (cut + _dt.timedelta(minutes=off) - _dt.timedelta(days=1)).date().isoformat()
    left = db.admin(f"select i.item_key from public.answers a join public.items i on i.id = a.item_id where a.pupil_id = '{pid('X')}' and i.item_key in ('d26', 'd27') order by 1")
    rolled = db.admin(f"select i.item_key, d.day::text from public.answer_daily d join public.items i on i.id = d.item_id where d.pupil_id = '{pid('X')}' and i.item_key in ('d26', 'd27') order by 1")
    db.admin("update private.settings set raw_days = 90, tz = 'Asia/Jerusalem'")
    eq('local midnight 30 minutes ago: the answer of 31 minutes ago is rolled into yesterday, the one of 29 minutes ago stays raw; totals still equal the ledgers',
       (err2, m2 and m2.get('totals_wrong'), left, rolled), (None, 0, [['d27']], [['d26', yday]]))
    eq('weak items still count rolled-up answers', db.select(TEACHER1, 'teacher_items', 'tries, wrong', dict(item_key='hard'))[0], [dict(tries=3, wrong=2)])
    eq("the Auth log's addresses older than 30 days are deleted, and the answer says so", (db.one('select count(*) from auth.audit_log_entries'), m.get('audit_purged')), ('1', True))
    db.psql('revoke delete on auth.audit_log_entries from postgres', user='supabase_admin')
    m2, _ = db.rpc(SERVER, 'maintenance')
    db.psql('grant delete on auth.audit_log_entries to postgres', user='supabase_admin')
    eq('where the platform does not allow that purge, maintenance reports it instead of hiding it', (m2.get('audit_purged'), m2.get('ok')), (False, False))
    rows_n('the server role reads everything (RLS does not apply to it)', db.select(SERVER, 'pupils'), 10)

    print('-- the teacher\'s daily cap of new codes (review of #86, S7)')
    cap = U(0xCA9)
    db.admin(f"insert into public.pupils (id, class_id, display_name) values ('{cap}', '{C1}', 'Capper'); delete from private.teacher_resets; update private.settings set reset_teacher_day = 1")
    try:
        call = f"select private.teacher_reset('{T1}', '{cap}', '01', repeat('ee', 32), 1000, now()) ->> 'e'"
        out = {}
        slow = threading.Thread(target=lambda: out.setdefault('a', db.psql(f"begin; select coalesce(({call}), 'ok'); select pg_sleep(0.8); commit;")))
        slow.start(); time.sleep(0.3)
        out['b'] = db.psql(f"select coalesce(({call}), 'ok')"); slow.join()
        eq('two new codes at the same moment against her last one left: the second waits for the first and is refused (her lock)',
           [out['a'][0][0][0], out['b'][0][0][0], db.one('select count(*) from private.teacher_resets')], ['ok', 'limit', '1'])
        h, _ = db.select(TEACHER1, 'backend_health', 'resets_day, resets_cap')
        eq('backend_health shows her own count and cap', h, [dict(resets_day=1, resets_cap=1)])
        h2, _ = db.select(TEACHER2, 'backend_health', 'resets_day, resets_cap')
        eq("and not another teacher's: teacher 2 has made none", h2, [dict(resets_day=0, resets_cap=1)])
        denied('a teacher reads nothing of the counter itself', db.as_(*TEACHER1, 'select * from private.teacher_resets'))
    finally:
        db.admin(f"update private.settings set reset_teacher_day = 15; delete from private.teacher_resets; delete from public.pupils where id = '{cap}'")


def test_removal(db):
    """Remove from the class with 14 days to undo it (0009_soft_delete.sql), next to delete for good."""
    print('\n== removing a pupil from the class: hidden at once, back on undo, deleted for good after 14 days ==')
    T = TEACHER1
    r1, r2, r3, ru1, ru2 = U(0xE01), U(0xE02), U(0xE03), U(0xE11), U(0xE12)
    db.admin(f"""insert into auth.users (id) values ('{ru1}'), ('{ru2}');
                 insert into public.pupils (id, class_id, display_name, auth_user_id) values ('{r1}', '{C1}', 'Remy', '{ru1}'), ('{r2}', '{C1}', 'Rina', '{ru2}'),
                   ('{r3}', '{C1}', 'Roni', null);""")
    R1, A = ('authenticated', ru1), ('authenticated', uid('A'))
    record_as(db, R1, ans(3, key='sun'))
    pts = db.one(f"select points from public.pupil_totals where pupil_id = '{r1}'")
    in_view = lambda who, p: any(r['pupil_id'] == p for r in (db.select(who, 'teacher_view', 'pupil_id')[0] or []))
    removed = lambda who: db._json(who, "select coalesce(jsonb_agg(to_jsonb(t)), '[]') from public.teacher_removed() t")
    denied("teacher 2 removes a pupil of class 1: refused", db.rpc(TEACHER2, 'teacher_remove_pupil', dict(p_pupil=r1)), 'not your pupil')
    denied('a pupil removes a classmate: refused', db.rpc(A, 'teacher_remove_pupil', dict(p_pupil=r1)), 'not your pupil')
    v, err = db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=r1))
    check('teacher 1 removes her pupil: done, with the day it is deleted for good (14 days)', err is None and v.get('ok') is True and v.get('purge_at'), err or v)
    check('at once: gone from her screen', not in_view(T, r1))
    board, _ = db.select(A, 'class_board', 'display_name')
    check("gone from the class board the classmates see", 'Remy' not in [b['display_name'] for b in board or []], board)
    eq('the pupil\'s session is over: the auth user is deleted, the pupil row holds none', [db.one(f"select count(*) from auth.users where id = '{ru1}'"), db.one(f"select coalesce(auth_user_id::text, '-') from public.pupils where id = '{r1}'")], ['0', '-'])
    rows_n('teacher 1 reads nothing of the removed pupil (its hidden class is nobody\'s)', db.select(T, 'pupils', where=dict(id=r1)), 0)
    rows_n('and nor does anyone else', db.select(TEACHER2, 'pupils', where=dict(id=r1)), 0)
    lst, err = removed(T)
    check('her removed list shows the pupil, with the day of the purge', err is None and [x['display_name'] for x in lst] == ['Remy'], err or lst)
    lst2, _ = removed(TEACHER2)
    eq("teacher 2's removed list is empty", lst2, [])
    eq('the records wait for the way back', db.one(f"select points from public.pupil_totals where pupil_id = '{r1}'"), pts)
    eq('the sign-in cannot find the name in the class any more (no pupil of that name in class 1)', db.one(f"select count(*) from public.pupils where class_id = '{C1}' and name_key = 'remy'"), '0')
    denied('teacher 2 cannot undo it', db.rpc(TEACHER2, 'teacher_restore_pupil', dict(p_pupil=r1)), 'not your pupil')
    v, err = db.rpc(T, 'teacher_restore_pupil', dict(p_pupil=r1))
    check('undo: back in her class, on her screen, with every point', err is None and v.get('ok') is True and in_view(T, r1) and db.one(f"select points from public.pupil_totals where pupil_id = '{r1}'") == pts, err or v)
    eq('and off the removed list', removed(T)[0], [])
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=r1))
    db.admin(f"insert into public.pupils (class_id, display_name) values ('{C1}', 'Remy')")      # a new pupil took the name meanwhile
    v, _ = db.rpc(T, 'teacher_restore_pupil', dict(p_pupil=r1))
    eq('undo while a new pupil has the name: refused as taken (with the day the removed record goes), nothing moves', [v.get('ok'), v.get('e'), bool(v.get('purge_at')), in_view(T, r1)], [False, 'taken', True, False])
    v, err = db.rpc(T, 'teacher_delete_pupil', dict(p_pupil=r1))
    check('delete for good works on a removed pupil at once (a parent\'s request does not wait 14 days)', err is None and db.one(f"select count(*) from public.pupils where id = '{r1}'") == '0'
          and db.one(f"select count(*) from public.answers where pupil_id = '{r1}'") == '0', err)
    eq('on record with her class, not the hidden one', db.admin(f"select class_id from private.deletions where pupil_id = '{r1}'"), [[C1]])
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=r2)); db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=r3))
    db.admin(f"update private.removed_pupils set removed_at = now() - interval '15 days' where pupil_id = '{r2}'")
    m, _ = db.rpc(SERVER, 'maintenance')
    eq('the nightly maintenance deletes a pupil removed 15 days ago, for good, and not one removed today',
       [m.get('removed_purged'), db.one(f"select count(*) from public.pupils where id = '{r2}'"), db.one(f"select count(*) from public.pupils where id = '{r3}'"),
        db.one(f"select count(*) from private.deletions where pupil_id = '{r2}' and teacher = '{T1}' and class_id = '{C1}'")], [1, '0', '1', '1'])
    db.admin(f"update private.removed_pupils set removed_at = now() - interval '13 days' where pupil_id = '{r3}'")
    m, _ = db.rpc(SERVER, 'maintenance')
    eq('removed 13 days ago: still there (the purge waits the whole 14 days)', [m.get('removed_purged'), db.one(f"select count(*) from public.pupils where id = '{r3}'")], [0, '1'])
    db.admin(f"delete from public.pupils where id in ('{r3}') or (class_id = '{C1}' and display_name = 'Remy'); delete from private.deletions where pupil_id in ('{r1}', '{r2}')")

    print('-- review of #94: the sign-in, the purge and the undo against each other')
    teacher_tx = lambda sql: f"begin; select set_config('request.jwt.claims', '{json.dumps(dict(role='authenticated', sub=T1))}', true); set local role authenticated; {sql}"
    def two(first, second, hold=0.8):
        """first runs in its own session and holds its locks for `hold` seconds; second starts meanwhile"""
        out = {}
        th = threading.Thread(target=lambda: out.setdefault('a', db.psql(first + f" select pg_sleep({hold}); commit;")))
        th.start(); time.sleep(0.3); out['b'] = db.psql(second); th.join()
        return out['a'], out['b']
    k1, ku = U(0xE21), U(0xE22)
    db.admin(f"insert into auth.users (id) values ('{ku}'); insert into public.pupils (id, class_id, display_name) values ('{k1}', '{C1}', 'Kiki')")
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=k1))
    eq('B1: the sign-in\'s last step (link the session) for a pupil removed meanwhile: refused, nothing linked',
       [db.one(f"select coalesce(private.link_auth_user('{k1}', '{ku}')::text, 'null')"), db.one(f"select coalesce(auth_user_id::text, '-') from public.pupils where id = '{k1}'")], ['null', '-'])
    db.admin(f"update private.removed_pupils set removed_at = now() - interval '15 days' where pupil_id = '{k1}'")
    a, b = two(teacher_tx(f"select public.teacher_restore_pupil('{k1}') ->> 'ok';"), "select private.purge_removed(now());")
    eq('B2: an undo that starts first wins: the purge waits for it, finds the pupil back in the class, deletes nothing',
       [a[1], b[0][0][0] if b[0] else None, db.one(f"select count(*) from public.pupils where id = '{k1}' and class_id = '{C1}'")], [None, '0', '1'])
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=k1))
    db.admin(f"update private.removed_pupils set removed_at = now() - interval '15 days' where pupil_id = '{k1}'")
    a, b = two("begin; select private.purge_removed(now());", teacher_tx(f"select public.teacher_restore_pupil('{k1}')::text; commit;"))
    eq('B2: a purge that starts first wins: the undo waits, then says the pupil is gone (never "back")',
       [json.loads(b[0][-1][0]) if b[0] else b, db.one(f"select count(*) from public.pupils where id = '{k1}'")], [dict(ok=False, e='gone'), '0'])
    k2 = U(0xE23)
    db.admin(f"insert into public.pupils (id, class_id, display_name) values ('{k2}', '{C1}', 'Lulu')")
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=k2))
    nw = json.dumps(dict(code_salt='01', code_hash='ee' * 32, pic_salt='02', pic_hash='dd' * 32, iter=600000))
    db.admin(f"insert into public.roster (class_id, name_key, display_name) values ('{C1}', 'lulu', 'Lulu') on conflict do nothing")
    a, b = two(f"begin; select private.register_pupil('{U(0xE24)}', '{C1}', 'Lulu', '{nw}'::jsonb, '00', now()) ->> 's';",
               teacher_tx(f"select public.teacher_restore_pupil('{k2}') ->> 'e'; commit;"))
    eq('S1: an undo while the same name registers: it waits for the name, then says taken (no raw error that would carry the name)',
       [a[1], b[1], [r for r in a[0] + b[0] if r and r[0] in ('taken', 'ok')]], [None, None, [['ok'], ['taken']]])
    db.admin(f"insert into private.auth_lock_events (class_id, name_key, kind) values ('{C1}', 'lulu', 'code')")
    db.admin(f"update private.removed_pupils set removed_at = now() - interval '15 days' where pupil_id = '{k2}'")
    db.rpc(SERVER, 'maintenance')
    eq("S2: purging the removed Lulu keeps the new Lulu's sign-in records (the name is hers now)",
       [db.one(f"select count(*) from public.pupils where id = '{k2}'"), db.one(f"select count(*) from private.auth_lock_events where class_id = '{C1}' and name_key = 'lulu'")], ['0', '1'])
    k3 = U(0xE25)
    db.admin(f"insert into public.pupils (id, class_id, display_name) values ('{k3}', '{C1}', 'Momo')")
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=k3))
    imp = json.loads(db.one(f"""select private.sheet_import('{C1}', '[{{"name": "Momo", "points": 5}}]'::jsonb)::text"""))
    eq('S3: the Sheet import skips a name the teacher took out of the class, and says so',
       [imp.get('skipped_removed'), imp.get('new'), db.one(f"select count(*) from public.pupils where class_id = '{C1}' and name_key = 'momo'")], [1, 0, '0'])
    db.admin(f"update public.classes set max_pupils = (select count(*) from public.pupils where class_id = '{C1}') where id = '{C1}'")
    v, _ = db.rpc(T, 'teacher_restore_pupil', dict(p_pupil=k3))
    eq('S5: undo into a full class: refused as full', v, dict(ok=False, e='full'))
    db.admin(f"update public.classes set max_pupils = 60 where id = '{C1}'")
    c3, k4 = U(0xC3), U(0xE26)
    db.admin(f"insert into public.classes (id, name, name_form) values ('{c3}', 'gone class', 'first'); insert into public.teachers values ('{T1}', '{c3}');"
             f"insert into public.pupils (id, class_id, display_name) values ('{k4}', '{c3}', 'Nini')")
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=k4))
    lim = db.one(f"select limbo_id from private.limbo where class_id = '{c3}'")
    db.admin(f"delete from public.classes where id = '{c3}'")           # the owner deletes a class by hand
    db.rpc(SERVER, 'maintenance')
    eq('S4: a class deleted by hand: what it left in its hidden class is deleted by the next purge, and the hidden class dropped',
       [db.one(f"select count(*) from public.pupils where id = '{k4}'"), db.one(f"select count(*) from public.classes where id = '{lim}'")], ['0', '0'])
    print('-- review of #94, follow-ups')
    k5, k6 = U(0xE27), U(0xE28)
    db.admin(f"insert into public.pupils (id, class_id, display_name) values ('{k5}', '{C1}', 'Ofri')")
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=k5))
    db.admin(f"update public.classes set max_pupils = (select count(*) from public.pupils where class_id = '{C1}') + 1 where id = '{C1}';"
             f"insert into public.roster (class_id, name_key, display_name) values ('{C1}', 'pazit', 'Pazit') on conflict do nothing")
    a, b = two(f"begin; select private.register_pupil('{k6}', '{C1}', 'Pazit', '{nw}'::jsonb, '00', now()) ->> 's';",
               teacher_tx(f"select public.teacher_restore_pupil('{k5}') ->> 'e'; commit;"))
    eq('the last place: a registration holds the head count, the undo waits for it and is refused as full (never one over)',
       [[r for r in a[0] + b[0] if r and r[0] in ('ok', 'full')], db.one(f"select count(*) <= max_pupils from public.pupils p join public.classes c on c.id = p.class_id where c.id = '{C1}' group by c.max_pupils")],
       [[['ok'], ['full']], 't'])
    db.admin(f"update public.classes set max_pupils = 60 where id = '{C1}'")
    gone_user = U(0xE29)
    eq('the link step with a user that no longer exists (a removal and an undo inside one sign-in): no error, nothing linked',
       db.psql(f"select coalesce(private.link_auth_user('{k6}', '{gone_user}')::text, 'null')"), ([['null']], None))
    q1, q2 = U(0xE2A), U(0xE2B)
    db.admin(f"insert into public.pupils (id, class_id, display_name) values ('{q1}', '{C1}', 'Rami'), ('{q2}', '{C1}', 'Sagi')")
    db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=q1)); db.rpc(T, 'teacher_remove_pupil', dict(p_pupil=q2))
    db.admin(f"update private.removed_pupils set removed_at = now() - interval '15 days' where pupil_id in ('{q1}', '{q2}'); update private.settings set purge_per_run = 1")
    m1, _ = db.rpc(SERVER, 'maintenance')
    left = db.one(f"select count(*) from public.pupils where id in ('{q1}', '{q2}')")
    m2, _ = db.rpc(SERVER, 'maintenance')
    eq('the purge stops at its bound for the night (purge_per_run, here 1) and the next run goes on',
       [m1.get('removed_purged'), left, m2.get('removed_purged'), db.one(f"select count(*) from public.pupils where id in ('{q1}', '{q2}')")], [1, '1', 1, '0'])
    db.admin("update private.settings set purge_per_run = 200")
    db.admin(f"delete from public.pupils where class_id = '{C1}' and display_name in ('Lulu', 'Momo', 'Pazit') or id in ('{k3}', '{k5}'); delete from auth.users where id = '{ku}'; delete from private.deletions")


def test_storage(db):
    """The free plan's 500 MB: what one pupil's device can add in a day, and the brake for everybody (PR 12 re-check)."""
    print('\n== storage: saves, batches, the brake, housekeeping ==')
    sv_uid, sv_pid = U(0xD01), U(0xD02)
    db.admin(f"insert into auth.users (id) values ('{sv_uid}'); insert into public.pupils (id, class_id, display_name, auth_user_id) values ('{sv_pid}', '{C2}', 'Saver', '{sv_uid}')")
    S = ('authenticated', sv_uid)
    day = lambda: db.admin(f"select saves, save_kb from private.pupil_days where pupil_id = '{sv_pid}' and day = (now() at time zone (select tz from private.settings))::date")
    print('-- save_progress is rationed (review PB1b)')
    r1, err = db.rpc(S, 'save_progress', dict(p_state={'a': 1}))
    r2, _ = db.rpc(S, 'save_progress', dict(p_state={'a': 1}, p_base=r1['updated_at']))
    eq('the same blob again: nothing written, nothing counted', (r2.get('unchanged'), r2['updated_at'] == r1['updated_at'], day()[0][0]), (True, True, '1'))
    db.admin('update private.settings set save_gap_s = 5')
    r3, _ = db.rpc(S, 'save_progress', dict(p_state={'a': 2}, p_base=r1['updated_at']))
    check('a second write within 5 seconds is refused with the wait', r3['ok'] is False and r3['e'] == 'wait' and 1 <= r3['retry_after'] <= 5, r3)
    eq('and nothing was written', db.one(f"select state ->> 'a' from public.progress where pupil_id = '{sv_pid}'"), '1')
    db.admin('update private.settings set save_gap_s = 0, max_saves_day = 3')
    got = [db.rpc(S, 'save_progress', dict(p_state={'a': 10 + i}, p_base=db.one(f"select updated_at from public.progress where pupil_id = '{sv_pid}'")))[0] for i in range(5)]
    eq('at most max_saves_day writes a day (3 here, 300 normally)', [g['ok'] for g in got], [True, True, False, False, False])
    check('past it: daycap and the seconds until midnight in Israel', got[2]['e'] == 'daycap' and 0 < got[2]['retry_after'] <= 86400, got[2])
    eq('one flag for the teacher, however many tries', db.one(f"select n from public.flags where pupil_id = '{sv_pid}' and kind = 'saves'"), '1')
    db.admin(f"update private.settings set max_saves_day = 300; delete from private.pupil_days where pupil_id = '{sv_pid}'; delete from public.flags where pupil_id = '{sv_pid}'")
    size0 = int(db.one("select pg_total_relation_size('public.progress')"))
    t0 = time.time()
    rows, err = db.as_('authenticated', sv_uid, """
      do $f$ declare r jsonb; b timestamptz; okn int := 0; i int; blob text;
      begin
        for i in 1..5000 loop
          select string_agg(md5(random()::text || i || j), '') into blob from generate_series(1, 1200) j;      -- about 39 KB, a new one each time
          select updated_at into b from public.progress where pupil_id = app.pupil_id();
          r := public.save_progress(jsonb_build_object('x', blob), b);
          if (r ->> 'ok')::boolean then okn := okn + 1; end if;
        end loop;
        perform set_config('wi.okn', okn::text, true);
      end $f$;
      select current_setting('wi.okn')""")
    okn = int(rows[-1][0]) if rows and not err else -1
    grown = int(db.one("select pg_total_relation_size('public.progress')")) - size0
    check(f'5,000 saves of a 39 KB blob, as fast as possible: {okn} written (4 MB a day at most)', 0 < okn <= 110, err or okn)
    check(f'the table grew by {grown / 1048576:.1f} MB, not hundreds (before the fix: 428 MB from 28,000 saves)', grown < 6 * 1048576, grown)
    print(f'     ({time.time() - t0:.0f} s)')
    eq('the day is flagged once', db.one(f"select n from public.flags where pupil_id = '{sv_pid}' and kind = 'saves'"), '1')

    print('-- record_events: batches per day, one Beach Run row per day, the storage brake')
    db.admin('update private.settings set max_batches_day = 2')
    rr = [record_as(db, S, ans(1, 0, key=f'w{i}'))[0] for i in range(3)]
    eq('a batch row only for a call that stored something, at most max_batches_day a day', [bool(x.get('capped')) for x in rr], [False, False, True])
    db.admin('update private.settings set max_batches_day = 300')
    for p_ in (10, 15, 5):
        record_as(db, S, [dict(type='run', points=p_)])
    eq('three Beach Runs in a day: one ledger row, grown in place', db.admin(f"select count(*), sum(delta) from public.points where pupil_id = '{sv_pid}' and reason = 'run'"), [['1', '30']])
    db.admin('update private.settings set storage_brake = true')
    n0 = db.one(f"select count(*) from public.answers where pupil_id = '{sv_pid}'")
    r, _ = record_as(db, S, ans(1, 0, key='w9'))
    eq('with the brake on, nothing is stored, and the answer says so (the device keeps the batch: review S4)',
       ((r.get('ok'), r.get('e')), db.one(f"select count(*) from public.answers where pupil_id = '{sv_pid}'"),
        db.one(f"select n from public.flags where pupil_id = '{sv_pid}' and kind = 'storage'")), ((False, 'brake'), n0, '1'))
    db.admin(f"update private.pupil_days set calls = 5000 where pupil_id = '{sv_pid}'")
    r, _ = record_as(db, S, ans(1, 0, key='w8'))
    eq('past the day\'s calls the brake still says brake, not capped (review of #35)', (r.get('ok'), r.get('e')), (False, 'brake'))
    db.admin("update private.settings set raw_days = 0")
    m, _ = db.rpc(SERVER, 'maintenance')
    db.admin("update private.settings set raw_days = 90")
    eq('with the brake on, the nightly roll-up waits too (it would write before vacuum frees: review S3)', (m or {}).get('rolled'), 0)
    db.admin('update private.settings set storage_brake = false')

    print('-- the nightly housekeeping: its log, the brake, the purges')
    db.admin(f"""insert into private.pupil_devices values ('{sv_pid}', '\\x01', now() - interval '40 days'), ('{sv_pid}', '\\x02', now());
                insert into public.flags (pupil_id, kind, day) values ('{sv_pid}', 'rate', current_date - 400);
                insert into private.maintenance_log (at, result) values (now() - interval '70 days', '{{}}');
                insert into public.points (pupil_id, delta, reason, ref, at) values ('{sv_pid}', 20, 'day', 'x1', now() - interval '100 days'),
                  ('{sv_pid}', 20, 'day', 'x2', now() - interval '99 days'), ('{sv_pid}', 7, 'run', 'x3', now() - interval '98 days');
                update public.pupil_totals set points = points + 47 where pupil_id = '{sv_pid}';""")
    db.admin('update private.settings set storage_brake_mb = 1')
    m, err = db.rpc(SERVER, 'maintenance')
    check('over the storage mark: the brake goes on and the answer is not ok', err is None and m['storage_brake'] is True and m['ok'] is False and db.one('select storage_brake from private.settings') == 't', err or m)
    h, err = db.select(TEACHER2, 'backend_health')
    check("the teacher's health row warns", err is None and len(h) == 1 and h[0]['warn'] is True and h[0]['storage_brake'] is True, err or h)
    rows_n('a pupil reads no health row', db.select(S, 'backend_health'), 0)
    db.admin('update private.settings set storage_brake_mb = 350')
    m, err = db.rpc(SERVER, 'maintenance')
    check('below it again: the brake goes off', err is None and m['storage_brake'] is False and db.one('select storage_brake from private.settings') == 'f', err or m)
    h, _ = db.select(TEACHER2, 'backend_health')
    check('and the health row is quiet when the night went well', h and h[0]['warn'] is (not m['ok']), (h, m))
    eq("each night's answer is in the log; rows older than 60 days are gone", db.admin("select count(*) >= 2, count(*) filter (where at < now() - interval '60 days') from private.maintenance_log"), [['t', '0']])
    eq('devices not seen for 30 days are forgotten', db.one(f"select count(*) from private.pupil_devices where pupil_id = '{sv_pid}'"), '1')
    eq('flags older than a year are deleted', db.one(f"select count(*) from public.flags where pupil_id = '{sv_pid}' and day < current_date - 365"), '0')
    eq('old daily-bonus and Beach Run rows become one row per reason; the total is unchanged',
       sorted(tuple(x) for x in db.admin(f"select reason, delta from public.points where pupil_id = '{sv_pid}' and ref = 'rolled'")), [('day', '40'), ('run', '7')])
    eq('the totals still equal the ledgers', db.admin('select * from private.totals_check()'), [])


def test_load(db):
    """35 pupils of one class save inside the same 10 seconds, three rounds. Every save and every answer must be there."""
    print('\n== load: 35 pupils, 3 rounds, all at once ==')
    N, ROUNDS, PER = 35, 3, 10
    cls = U(0xC9)
    kids = [(U(0x1A000 + i), U(0x1B000 + i)) for i in range(N)]
    HEB = 'אבגדהוזחטיכלמנסעפצקרשת'   # no final letters: a final letter has the key of its plain form (0010)
    assert N <= 22 * 22
    db.admin(f"insert into public.classes (id, name, name_form) values ('{cls}', 'load class', 'first');"
             + "insert into auth.users (id) values " + ', '.join(f"('{a}')" for a, _ in kids) + ';'
             + 'insert into public.pupils (id, class_id, display_name, auth_user_id) values '
             + ', '.join(f"('{p}', '{cls}', 'load {HEB[i % 22]}{HEB[i // 22]}', '{a}')" for i, (a, p) in enumerate(kids)) + ';'
             + "insert into public.items (game, item_key) values " + ', '.join(f"('load', 'i{j}')" for j in range(60)) + ';')
    base = int(time.time() * 1000) - 30 * 60000
    errors, seen = [], {}
    for rnd in range(ROUNDS):
        gate, times = threading.Barrier(N), [0.0] * N

        def one(i):
            who = ('authenticated', kids[i][0])
            ev = [dict(type='answer', game='load', item=f'i{rnd * PER + j}', correct=True, first_try=True, t=base + (rnd * PER + j) * 20000) for j in range(PER)]
            gate.wait()
            t0 = time.time()
            a = db.rpc(who, 'save_progress', dict(p_state={'round': rnd, 'pad': 'x' * 8000, 'k': {'words': rnd}}, p_base=seen.get(i)))
            b = db.rpc(who, 'record_events', dict(p_batch=str(uuid.uuid4()), p_events=ev))
            c = db.select(who, 'class_board')
            times[i] = time.time() - t0
            for v, err in (a, b, c):
                if err:
                    errors.append(err)
            if a[0] and a[0].get('ok'):
                seen[i] = a[0]['updated_at']
            else:
                errors.append('save not taken: ' + str(a)[:120])
        t0 = time.time()
        th = [threading.Thread(target=one, args=(i,)) for i in range(N)]
        [t.start() for t in th]; [t.join() for t in th]
        wall = time.time() - t0
        print(f'   round {rnd + 1}: {N} pupils saved a blob, {PER} answers and read the board in {wall:.2f}s (slowest pupil {max(times):.2f}s)')
        check(f'round {rnd + 1}: every pupil finished inside 10 seconds', wall < 10, f'{wall:.1f}s')
    eq('no pupil got an error', errors, [])
    eq('no lost save: every blob is the last round', db.admin(f"select count(*) from public.progress g join public.pupils p on p.id = g.pupil_id where p.class_id = '{cls}' and g.state ->> 'round' = '{ROUNDS - 1}'"), [[str(N)]])
    eq('no lost answer: 30 rows per pupil', db.admin(f"select count(*), min(n), max(n) from (select count(*) n from public.answers a join public.pupils p on p.id = a.pupil_id where p.class_id = '{cls}' group by a.pupil_id) x"), [[str(N), str(ROUNDS * PER), str(ROUNDS * PER)]])
    eq('every total is exact: 30 x 10 + daily bonus', db.admin(f"select distinct t.points from public.pupil_totals t join public.pupils p on p.id = t.pupil_id where p.class_id = '{cls}'"), [[str(ROUNDS * PER * 10 + 20)]])

    print('-- one pupil, two devices and retries at the same moment')
    a, p = kids[0]
    dup = str(uuid.uuid4())
    jobs = [(str(uuid.uuid4()), f'i{30 + i}') for i in range(12)] + [(dup, 'i59')] * 6
    gate, errs = threading.Barrier(len(jobs)), []

    def two(b, key):
        gate.wait()
        v, err = db.rpc(('authenticated', a), 'record_events', dict(p_batch=b, p_events=[dict(type='answer', game='load', item=key, correct=True, first_try=False)]))
        if err:
            errs.append(err)
    th = [threading.Thread(target=two, args=j) for j in jobs]
    [t.start() for t in th]; [t.join() for t in th]
    eq('12 parallel batches and one batch sent 6 times: no error', errs, [])
    eq('13 answers stored, not 18 and not fewer', db.one(f"select count(*) from public.answers where pupil_id = '{p}'"), str(ROUNDS * PER + 13))
    eq('the total moved by exactly 13 x 4', db.one(f"select points from public.pupil_totals where pupil_id = '{p}'"), str(ROUNDS * PER * 10 + 20 + 13 * 4))
    gate, got = threading.Barrier(8), []

    def save(i):
        gate.wait()
        got.append(db.rpc(('authenticated', a), 'save_progress', dict(p_state={'writer': i}, p_base=seen[0]))[0])
    th = [threading.Thread(target=save, args=(i,)) for i in range(8)]
    [t.start() for t in th]; [t.join() for t in th]
    eq('8 devices save over the same version at once: exactly one is taken, 7 are told to join', sorted(bool(g and g.get('ok')) for g in got), [False] * 7 + [True])
    eq('pupil_totals equals the ledgers after the load', db.admin('select * from private.totals_check()'), [])


def test_grades(db):
    """docs/GRADES_V1.md: grades, the grade board, a first name and one surname letter, the carry, teacher_add."""
    print('-- grades (0010)')
    u = lambda n: f'00000000-0000-4000-9000-{n:012d}'
    db.admin("insert into auth.users (id) select ('00000000-0000-4000-9000-' || lpad(g::text, 12, '0'))::uuid from generate_series(1, 9) g")
    lk = lambda: secrets.token_hex(32)
    a = db.one(f"select private.class_create('ה׳1', 'ה׳', '{lk()}')")
    b = db.one(f"select private.class_create('ה׳2', 'ה׳', '{lk()}')")
    o = db.one(f"select private.class_create('ו׳1', 'ו׳', '{lk()}')")
    t = db.one("insert into public.classes (name, name_form) values ('Trial grades', 'first') returning id")   # as the trial: made before 0010
    eq('class_create: two classes of one grade share it; another grade is another; every new class takes a surname letter',
       db.admin(f"select (select grade_id from public.classes where id = '{a}') = (select grade_id from public.classes where id = '{b}'), "
                f"(select grade_id from public.classes where id = '{a}') <> (select grade_id from public.classes where id = '{o}'), "
                f"(select count(*) from public.classes where id in ('{a}', '{b}', '{o}') and name_form = 'first_initial' and kind = 'class')"), [['t', 't', '3']])
    check('class_create refuses a class without its grade', db.psql(f"select private.class_create('x', ' ', '{lk()}')", user='supabase_admin')[1] is not None)
    check('a class name names one class', 'duplicate key' in (db.psql(f"select private.class_create('ה׳1', 'ה׳', '{lk()}')", user='supabase_admin')[1] or ''))
    ins = lambda c, name, n: db.psql(f"insert into public.pupils (class_id, display_name, auth_user_id) values ('{c}', $n${name}$n$, '{u(n)}')", user='supabase_admin')[1]
    eq('names in a new class: one letter yes; a first name alone, a full surname, two letters, a digit not on the roster: no',
       [ins(a, 'נועה כ.', 1) is None, ins(a, 'Dan', 9) is None, ins(a, 'Dan Levi', 9) is None, ins(a, 'Dan Le.', 9) is None, ins(a, 'Dan L2.', 9) is None],
       [True, False, False, False, False])
    rin = lambda name: db.psql(f"insert into public.roster values ('{a}', app.name_key($n${name}$n$), $n${name}$n$)", user='supabase_admin')[1]
    eq('the roster: a digit after the letter for a clash (2 to 9); never two letters, a full surname, 0 or 1, or a digit in a first name',
       [rin('נועה כ2.') is None, rin('נועה כה.') is None, rin('Avi Levi') is None, rin('Avi L1.') is None, rin('Avi2 L.') is None], [True, False, False, False, False])
    eq('a clash: the digit form registers because the roster holds it', ins(a, 'נועה כ2.', 2), None)
    eq('a final letter is the plain letter: "נועה ך." is the pupil "נועה כ." (one pupil, not two)',
       [db.one("select app.name_key('נועה ך.') = app.name_key('נועה כ.')"), 'duplicate key' in (ins(a, 'נועה ך.', 9) or '')], ['t', True])
    eq('the trial class (first): a first name alone still works', ins(t, 'Test', 3), None)
    ins(b, 'Uri ב.', 4); ins(o, 'Maya מ.', 5)
    # 10 points each, through the ledger, so the totals still equal the ledgers (the load test checks every pupil)
    db.admin(f"""insert into public.points (pupil_id, delta, reason) select id, 10, 'fix' from public.pupils where class_id in ('{a}', '{b}', '{o}', '{t}');
                 update public.pupil_totals set points = points + 10 where pupil_id in (select id from public.pupils where class_id in ('{a}', '{b}', '{o}', '{t}'))""")
    board = lambda who: db._json(who, "select coalesce(jsonb_agg(to_jsonb(t) order by t.display_name), '[]') from public.grade_board() t")
    got, err = board(('authenticated', u(1)))
    eq('grade board for a pupil of ה׳1: the pupils of ה׳ with their class, no other grade, no trial, own row marked',
       err or sorted((r['display_name'], r['class'], r['me']) for r in got), [('Uri ב.', 'ה׳2', False), ('נועה כ.', 'ה׳1', True), ('נועה כ2.', 'ה׳1', False)])
    eq('grade board for the trial pupil (no grade): empty', board(('authenticated', u(3)))[0], [])
    eq('grade board for anonymous: refused', 'permission denied' in (board(('anon', None))[1] or ''), True)
    db.admin(f"insert into public.teachers values ('{u(6)}', '{o}')")
    eq('grade board for the teacher of ו׳1: her grade only', [r['display_name'] for r in board(('authenticated', u(6)))[0]], ['Maya מ.'])
    db.admin(f"insert into public.teachers values ('{u(7)}', '{b}')")
    p_uri = db.one(f"select id from public.pupils where class_id = '{b}'")
    v, err = db.rpc(('authenticated', u(7)), 'teacher_remove_pupil', dict(p_pupil=p_uri))
    eq('a removed pupil: their hidden class is kind limbo in the same grade, and they leave the grade board',
       [err, db.admin(f"select c.kind, c.grade_id = (select grade_id from public.classes where id = '{b}') from public.pupils p join public.classes c on c.id = p.class_id where p.id = '{p_uri}'"),
        sorted(r['display_name'] for r in board(('authenticated', u(1)))[0])], [None, [['limbo', 't']], ['נועה כ.', 'נועה כ2.']])
    eq('teacher_add: by user id and class name; again is "already"; an unknown class or user is refused',
       [db.one(f"select private.teacher_add('{u(8)}', 'ה׳1')"), db.one(f"select private.teacher_add('{u(8)}', 'ה׳1')"),
        db.one(f"select private.teacher_add('{u(8)}', 'nope')"),
        db.one("select private.teacher_add('00000000-0000-4000-9000-999999999999', 'ה׳1')")], ['ok', 'already', 'class', 'user'])
    eq('the grade board crosses class lines with these columns only: name (with the letter), class, points, me; no ids',
       sorted(board(('authenticated', u(1)))[0][0].keys()), ['class', 'display_name', 'me', 'rank', 'week'])
    eq('the new tables are not reachable through the API', [db.as_('authenticated', u(1), f'select count(*) from private.{x}')[1] is not None for x in ('schools', 'grades', 'pupil_carry')], [True] * 3)
    # the carry: old daily rows and a finished school year are folded, totals unchanged
    p_noa = db.one(f"select id from public.pupils where class_id = '{a}' and display_name = 'נועה כ.'")
    db.admin(f"""insert into public.items (game, item_key) values ('carry', 'one') on conflict do nothing;
                 insert into public.answer_daily (pupil_id, day, item_id, tries, correct, pts) select '{p_noa}', current_date - 200, id, 3, 2, 20 from public.items where game = 'carry';
                 insert into public.answers (pupil_id, item_id, correct, first_try, pts, at) select '{p_noa}', id, true, true, 10, private.year_start(now())::timestamptz - interval '2 days' from public.items where game = 'carry';
                 update public.pupil_totals set points = points + 30, answers = answers + 4 where pupil_id = '{p_noa}';""")
    before = db.admin(f"select * from private.totals_check() where pupil_id = '{p_noa}'")
    res = db.one("select private.fold_history(now())")
    eq('fold_history: the old daily row and last school year\'s answer are folded into the carry and deleted; totals still add up',
       [before, db.admin(f"select pts, tries from private.pupil_carry where pupil_id = '{p_noa}'"),
        db.one(f"select count(*) from public.answer_daily where pupil_id = '{p_noa}'"), db.one(f"select count(*) from public.answers where pupil_id = '{p_noa}'"),
        db.admin(f"select * from private.totals_check() where pupil_id = '{p_noa}'")], [[], [['30', '4']], '0', '0', []])
    eq('limits with headroom for a grade at one address (ip_hour 3000, register_ip_hour 1500; per class 300 and 150)',
       db.admin('select ip_hour, register_ip_hour, ip_class_hour, register_ip_class_hour from private.settings'), [['3000', '1500', '300', '150']])
    eq('year_end must be a day every year has: 02-30 and 02-29 are refused, 06-30 is taken',
       [db.psql(f"update private.settings set year_end = '{d}'", user='supabase_admin')[1] is None for d in ('02-30', '02-29', '06-30', '08-31')], [False, False, True, True])
    db.admin(f"""insert into public.answer_daily (pupil_id, day, item_id, tries, pts) select '{p_noa}', current_date - 300 - g, i.id, 1, 1
                  from generate_series(1, 3) g, public.items i where i.game = 'carry';
                  update public.pupil_totals set points = points + 3, answers = answers + 3 where pupil_id = '{p_noa}';
                  update private.settings set fold_per_run = 2;""")
    db.one("select private.fold_history(now())")
    eq('the fold is bounded per run (fold_per_run): 2 of 3 old rows tonight, the last one the next night; totals right throughout',
       [db.one(f"select count(*) from public.answer_daily where pupil_id = '{p_noa}'"), db.admin(f"select * from private.totals_check() where pupil_id = '{p_noa}'")], ['1', []])
    db.one("select private.fold_history(now())")
    eq('and the next night folds the rest', db.one(f"select count(*) from public.answer_daily where pupil_id = '{p_noa}'"), '0')
    db.admin("update private.settings set fold_per_run = 50000")
    db.admin(f"insert into public.pupils (class_id, display_name) select '{a}', 'Big' || chr(65 + g / 26) || chr(65 + g % 26) || ' B.' from generate_series(0, 329) g")
    # 0011: the server sends the top 10 and the caller's own row, never the whole grade (review of the board)
    in_order = lambda who: db._json(who, "select coalesce(jsonb_agg(to_jsonb(t) - 'n' order by t.n), '[]') "
                                         "from public.grade_board() with ordinality t(display_name, class, week, me, rank, n)")
    # 0012: the boards rank this week's points, from the ledger (these pupils are deleted below, with their rows)
    db.admin(f"insert into public.points (pupil_id, delta, reason) select id, 1000 - row_number() over (order by display_name)::int, 'fix' "
             f"from public.pupils where class_id = '{a}' and display_name like 'Big%'")
    noa_pts = int(db.one(f"select app.week_points('{p_noa}', app.week_start(now()))"))
    got, err = in_order(('authenticated', u(1)))
    eq('a grade of 330 more pupils, all ahead of Noa: she gets 11 rows, the top 10 (ranks 1 to 10, in order) and her own '
       'row last with her rank (331); nobody else of the grade', err or [(r['display_name'], r['week'], r['rank'], r['me']) for r in got],
       [(f'BigA{chr(65 + i)} B.', 999 - i, i + 1, False) for i in range(10)] + [('נועה כ.', noa_pts, 331, True)])
    got, err = in_order(('authenticated', u(8)))
    eq('her class teacher: the top 10 only, no own row', err or [(len(got), any(r['me'] for r in got))], [(10, False)])
    db.admin(f"delete from public.points x using public.pupils p where p.id = x.pupil_id and p.class_id = '{a}' and p.display_name like 'Big%';"
             f"insert into public.points (pupil_id, delta, reason) select id, 1000, 'fix' from public.pupils where class_id = '{a}' and display_name like 'Big%'")
    got, err = in_order(('authenticated', u(1)))
    eq('330 pupils tied for first: still 10 of them (all rank 1) and Noa (rank 331): ties never lengthen the answer',
       err or [len(got), sorted({r['rank'] for r in got[:10]}), got[10]['rank'], got[10]['me']], [11, [1], 331, True])
    p_big = db.one(f"select id from public.pupils where class_id = '{a}' and display_name = 'BigMR B.'")
    db.admin(f"update public.pupils set auth_user_id = '{u(9)}' where id = '{p_big}'")
    got, err = in_order(('authenticated', u(9)))
    eq('a pupil tied with the top 10 but not picked: their own row still comes, with the shared rank',
       err or [len(got), got[-1]['display_name'], got[-1]['rank'], got[-1]['me'], sum(r['me'] for r in got)], [11, 'BigMR B.', 1, True, 1])
    db.admin(f"delete from public.pupils where class_id = '{a}' and display_name like 'Big%'")
    # 0012, the week itself: Sunday 00:00 in Israel, in winter, in summer and in the week summer time ends
    eq('the week starts on Sunday 00:00 Asia/Jerusalem (winter +02, summer +03, and the Sunday summer time ends)',
       db.admin("select to_char(app.week_start(t) at time zone 'utc', 'YYYY-MM-DD HH24:MI') from unnest(array["
                "'2026-11-26 12:00Z', '2026-11-21 21:59Z', '2026-11-21 22:00Z', '2026-04-01 12:00Z', '2026-10-29 12:00Z']::timestamptz[]) t"),
       [['2026-11-21 22:00'], ['2026-11-14 22:00'], ['2026-11-21 22:00'], ['2026-03-28 21:00'], ['2026-10-24 21:00']])
    w0 = int(db.one(f"select app.week_points('{p_noa}', app.week_start(now()))"))
    db.admin(f"insert into public.points (pupil_id, delta, reason, at) values ('{p_noa}', 5, 'fix', app.week_start(now()) - interval '1 minute'), "
             f"('{p_noa}', 7, 'fix', app.week_start(now())); "
             f"insert into public.points (pupil_id, delta, reason, ref) values ('{p_noa}', 100, 'migrated', ''), ('{p_noa}', 1000, 'day', 'rolled'); "
             f"update public.pupil_totals set points = points + 1112 where pupil_id = '{p_noa}'")
    me_row = lambda who: db.select(who, 'class_board', 'points, week', dict(me=True))[0]
    eq("a point at Saturday 23:59 is last week's, one at Sunday 00:00 this week's; an import ('migrated') and the roll-up's "
       "merged rows do not count; the class board shows the week and, unchanged, the all-time total",
       [int(db.one(f"select app.week_points('{p_noa}', app.week_start(now()))")) - w0,
        me_row(('authenticated', u(1))) == [dict(points=int(db.one(f"select points from public.pupil_totals where pupil_id = '{p_noa}'")), week=w0 + 7)]],
       [7, True])
    db.admin(f"insert into public.pupils (class_id, display_name, auth_user_id) values ('{a}', 'Zero ז.', '{u(9)}')")
    got, err = in_order(('authenticated', u(9)))
    eq('a pupil with no points this week: in nobody\'s top 10, their own row last with week 0; nobody else with 0',
       err or [got[-1]['display_name'], got[-1]['week'], got[-1]['me'], got[-1]['rank'] == len(got), [r['week'] for r in got[:-1] if r['week'] <= 0]],
       ['Zero ז.', 0, True, True, []])
    eq('a client still asking the grade board for all-time points gets an error, not a wrong number',
       'points' in (db._json(('authenticated', u(1)), "select jsonb_agg(points) from public.grade_board()")[1] or ''), True)
    eq('the helper that sums any pupil\'s week is not callable by a pupil',
       'permission denied' in (db.as_('authenticated', u(1), f"select app.week_points('{p_noa}', now())")[1] or ''), True)
    db.admin("delete from public.pupils where display_name = 'Zero ז.'")
    check('no class is ever named like the hidden ones', db.psql(f"select private.class_create('Removed', 'ה׳', '{lk()}')", user='supabase_admin')[1] is not None)
    db.admin("insert into public.classes (name, name_form) values ('removed', 'first')")      # one made by hand, as a real class
    p_noa2 = db.one(f"select id from public.pupils where class_id = '{a}' and display_name = 'נועה כ2.'")
    db.admin(f"insert into public.teachers values ('{u(9)}', '{a}') on conflict do nothing")
    v, err = db.rpc(('authenticated', u(9)), 'teacher_remove_pupil', dict(p_pupil=p_noa2))
    eq('a real class named "removed" does not stop a removal: the hidden class is made as limbo', [err, (v or {}).get('ok')], [None, True])


def main():
    args = sys.argv[1:]
    db = pg.start()
    try:
        if '--load' not in args:
            fixture(db)
            test_catalogue(db); test_anon(db); test_pupil(db); test_points(db); test_teacher(db); test_removal(db); test_storage(db); test_grades(db)
        if '--no-load' not in args:
            test_load(db)
    finally:
        db.stop()
    print(f'\n{PASS} passed, {FAIL} failed')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
