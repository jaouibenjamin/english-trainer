#!/usr/bin/env python3
"""Backend database tests (docs/BACKEND.md sections 2 and 5). One command, no Docker, no Supabase project:

    python3 tests/db.py            # access rules, points, then the load test
    python3 tests/db.py --no-load  # skip the load test
    python3 tests/db.py --load     # only the load test

Starts a throw-away local PostgreSQL (tests/db/pg.py), applies supabase/migrations as written, and acts as a visitor,
a pupil or a teacher only through five API-shaped calls (select, rpc, insert, update, delete), so the same assertions
can run against a real project's REST API later (docs/BACKEND.md section 11 lists what this stand-in cannot prove).
Set-up and the "what is really in the table" checks use SQL as the owner. All names and codes are made up.
Exit code 0 only when every check passed."""
import json, os, sys, threading, time, uuid
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
    sql = [f"insert into public.classes (id, name, grade) values ('{C1}', 'test class 1', '5'), ('{C2}', 'test class 2', '5');"]
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
                  'auth_lock_events', 'ip_salts', 'answer_batches', 'pupil_days', 'settings', 'deletions', 'maintenance_log']
PUPIL_KEYED = ['pupil_totals', 'progress', 'answers', 'points', 'flags', 'answer_daily', 'level_best']
PUPIL_KEYED_PRIVATE = ['pupil_secrets', 'reset_codes', 'pupil_devices', 'legacy_import', 'answer_batches', 'pupil_days']


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
    eq('anon: may run exactly one function, the keep-alive', db.admin(fn % 'anon'), [['public.ping']])
    eq('anon: no usage on schema private or app', db.admin("select has_schema_privilege('anon', 'private', 'USAGE') or has_schema_privilege('anon', 'app', 'USAGE')"), [['f']])
    eq('authenticated: no usage on schema private', db.admin("select has_schema_privilege('authenticated', 'private', 'USAGE')"), [['f']])
    eq('authenticated: no right on any private table',
       db.admin(rel % f"n.nspname = 'private' and has_table_privilege('authenticated', c.oid, {ALLP})"), [])
    eq('authenticated: may write to no table except the class list (teacher only, by policy)',
       db.admin(rel % "has_table_privilege('authenticated', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE')"), [['public.roster']])
    eq('authenticated: no right on any sequence', db.admin(seq % 'authenticated'), [])
    eq('authenticated: may run exactly the listed functions', [r[0] for r in db.admin(fn % 'authenticated')],
       ['app.class_id', 'app.name_key', 'app.name_ok', 'app.obj', 'app.pupil_id', 'app.reads_class', 'app.reads_pupil', 'app.safe_int', 'app.shadow', 'app.teaches', 'app.teaches_pupil',
        'public.ping', 'public.record_events', 'public.save_progress', 'public.teacher_delete_pupil'])
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
    eq('the board has no ids', db.admin("select string_agg(column_name, ',' order by ordinal_position) from information_schema.columns where table_schema = 'public' and table_name = 'class_board'"), [['display_name,points,words,streak,me']])

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
    eq('teacher_view never carries a hash', db.admin("select count(*) from information_schema.columns where table_schema = 'public' and table_name = 'teacher_view' and (column_name like '%hash%' or column_name like '%salt%')"), [['0']])
    denied('teacher 1 reads the secrets table: refused like anyone', db.as_(*T, 'select * from private.pupil_secrets'))
    denied('teacher 1 writes points', db.insert(T, 'points', dict(pupil_id=pid('A'), delta=5, reason='fix')))
    denied('teacher 1 edits an answer', db.update(T, 'answers', dict(pts=0)))
    denied("teacher 1 adds a name to class 2's list: refused by policy", db.insert(T, 'roster', dict(class_id=C2, name_key='x y', display_name='x y')), 'row-level security')
    rows, err = db.insert(T, 'roster', dict(class_id=C1, name_key='new kid', display_name='New Kid'))
    eq('teacher 1 adds a name to her own class list', (rows and rows[0]['name_key'], err), ('new kid', None))
    rows_n("teacher 1 deletes from class 2's list: nothing happens", db.delete(T, 'roster', dict(class_id=C2)), 0)
    denied('teacher 1 deletes a pupil of class 2', db.rpc(T, 'teacher_delete_pupil', dict(p_pupil=pid('X'))), 'not your pupil')

    print('-- deleting a pupil removes them from every table')
    g, name = pid('G'), NAMES['G']
    db.admin(f"""insert into private.reset_codes (pupil_id, salt, hash, expires_at) values ('{g}', '\\x01', decode(repeat('ee', 32), 'hex'), now() + interval '1 day');
                 insert into private.pupil_devices (pupil_id, device_hash) values ('{g}', '\\x0102');
                 insert into private.legacy_import values ('{g}', 's', repeat('a', 64));
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
    for n in ['Noa', 'נועה', "O'Neil", 'Chloé', 'בר-לב', 'ג׳ני', 'Ana Mae', 'Dan.']:
        r = db.psql(f"select app.name_ok($n${n}$n$)")[0][0][0]
        check(f'allowed: {n}', r == 't', r)

    print('-- maintenance (server role only)')
    record(db, 'H', ans(4, minute=0, key='old') + ans(1, 5, key='hard', correct=False, first=False) + ans(1, 6, key='hard', correct=False, first=False) + ans(1, 7, key='hard'))
    before = db.admin(f"select points, answers from public.pupil_totals where pupil_id = '{pid('H')}'")
    db.admin("update private.settings set raw_days = 0; insert into auth.audit_log_entries (ip_address, created_at) values ('203.0.113.9', now() - interval '40 days'), ('203.0.113.9', now())")
    m, err = db.rpc(SERVER, 'maintenance')
    db.admin('update private.settings set raw_days = 90')
    check('the server role runs maintenance; totals still equal the ledgers', err is None and m.get('ok') is True and m.get('rolled', 0) > 0, err or m)
    eq('old answers are rolled up, not lost: totals unchanged', db.admin(f"select points, answers from public.pupil_totals where pupil_id = '{pid('H')}'"), before)
    eq('the roll-up holds them per day and item', db.admin(f"select sum(tries), sum(first_try), sum(pts) from public.answer_daily where pupil_id = '{pid('H')}'"), [['7', '5', '50']])
    eq('weak items still count rolled-up answers', db.select(TEACHER1, 'teacher_items', 'tries, wrong', dict(item_key='hard'))[0], [dict(tries=3, wrong=2)])
    eq("the Auth log's addresses older than 30 days are deleted, and the answer says so", (db.one('select count(*) from auth.audit_log_entries'), m.get('audit_purged')), ('1', True))
    db.psql('revoke delete on auth.audit_log_entries from postgres', user='supabase_admin')
    m2, _ = db.rpc(SERVER, 'maintenance')
    db.psql('grant delete on auth.audit_log_entries to postgres', user='supabase_admin')
    eq('where the platform does not allow that purge, maintenance reports it instead of hiding it', (m2.get('audit_purged'), m2.get('ok')), (False, False))
    rows_n('the server role reads everything (RLS does not apply to it)', db.select(SERVER, 'pupils'), 10)


def test_storage(db):
    """The free plan's 500 MB: what one pupil's device can add in a day, and the brake for everybody (PR 12 re-check)."""
    print('\n== storage: saves, batches, the brake, housekeeping ==')
    sv_uid, sv_pid = U(0xD01), U(0xD02)
    db.admin(f"insert into auth.users (id) values ('{sv_uid}'); insert into public.pupils (id, class_id, display_name, auth_user_id) values ('{sv_pid}', '{C2}', 'Saver', '{sv_uid}')")
    S = ('authenticated', sv_uid)
    day = lambda: db.admin(f"select saves, save_kb from private.pupil_days where pupil_id = '{sv_pid}' and day = (now() at time zone 'Asia/Jerusalem')::date")
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
    eq('with the brake on, events are counted, not stored', (r.get('capped'), db.one(f"select count(*) from public.answers where pupil_id = '{sv_pid}'"),
       db.one(f"select n from public.flags where pupil_id = '{sv_pid}' and kind = 'storage'")), (True, n0, '1'))
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
    db.admin(f"insert into public.classes (id, name) values ('{cls}', 'load class');"
             + "insert into auth.users (id) values " + ', '.join(f"('{a}')" for a, _ in kids) + ';'
             + 'insert into public.pupils (id, class_id, display_name, auth_user_id) values '
             + ', '.join(f"('{p}', '{cls}', 'load {chr(0x5d0 + i % 27)}{chr(0x5d0 + i // 27)}', '{a}')" for i, (a, p) in enumerate(kids)) + ';'
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


def main():
    args = sys.argv[1:]
    db = pg.start()
    try:
        if '--load' not in args:
            fixture(db)
            test_catalogue(db); test_anon(db); test_pupil(db); test_points(db); test_teacher(db); test_storage(db)
        if '--no-load' not in args:
            test_load(db)
    finally:
        db.stop()
    print(f'\n{PASS} passed, {FAIL} failed')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
