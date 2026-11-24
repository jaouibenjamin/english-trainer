#!/usr/bin/env python3
"""Backend database tests (docs/BACKEND.md sections 2 and 5). One command, no Docker, no Supabase project:

    python3 tests/db.py            # access rules, points, then the load test
    python3 tests/db.py --no-load  # skip the load test
    python3 tests/db.py --load     # only the load test

Starts a throw-away local PostgreSQL (tests/db/pg.py), applies supabase/migrations as written, and talks to it the way
the Supabase API does: role anon / authenticated / service_role plus the JWT claims of the caller, per transaction.
All names and codes in here are made up. Exit code 0 only when every check passed."""
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
    check(label, err is None and len(rows) == n, err or f'{len(rows)} rows: {rows[:4]}')


def denied(label, res, what='permission denied'):
    rows, err = res
    check(label, err is not None and what in err, err or f'no error, rows: {rows[:3]}')


def eq(label, got, want):
    check(label, got == want, f'got {got!r}, want {want!r}')


U = lambda n: str(uuid.UUID(int=n))          # fixed ids, easy to read in failures
C1, C2 = U(0xC1), U(0xC2)
T1, T2, STRAY = U(0x71), U(0x72), U(0x99)
KIDS = {k: (U(0xA00 + i), U(0xB00 + i)) for i, k in enumerate('ABCDEFGHX')}    # name -> (auth user id, pupil id)
NAMES = dict(A='נועה', B='איתי', C='מאיה', D='עומר', E='שחר', F='רוני', G='טל', H='גיל', X='דנה')
uid = lambda k: KIDS[k][0]
pid = lambda k: KIDS[k][1]
NOW = int(time.time() * 1000)
BASE = NOW - 40 * 3600 * 1000                 # answers are placed on a timeline that starts 40 hours ago


def ans(n=1, minute=0, step_s=30, game='en', key='cat', correct=True, first=True, **extra):
    return [dict(game=game, item_key=key if n == 1 else f'{key}{i}', correct=correct, first_try=first,
                 t=BASE + minute * 60000 + i * step_s * 1000, **extra) for i in range(n)]


def record(db, k, rows, batch=None):
    q = "select public.record_answers('%s', $j$%s$j$::jsonb)" % (batch or uuid.uuid4(), json.dumps(rows, ensure_ascii=False))
    rws, err = db.as_('authenticated', uid(k), q)
    return (json.loads(rws[0][0]) if not err else None), err


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
    db.admin('\n'.join(sql))


PUBLIC_TABLES = ['classes', 'roster', 'teachers', 'pupils', 'items', 'answers', 'points', 'pupil_totals', 'progress', 'flags', 'answer_daily']
VIEWS = ['class_board', 'teacher_view', 'teacher_items']
PRIVATE_TABLES = ['class_codes', 'pupil_secrets', 'reset_codes', 'pupil_devices', 'auth_attempts', 'auth_buckets',
                  'auth_lock_events', 'ip_salts', 'answer_batches', 'pupil_days', 'settings']


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
    eq('anon: may not run any function', db.admin(fn % 'anon'), [])
    eq('anon: no usage on schema private or app', db.admin("select has_schema_privilege('anon', 'private', 'USAGE') or has_schema_privilege('anon', 'app', 'USAGE')"), [['f']])
    eq('authenticated: no usage on schema private', db.admin("select has_schema_privilege('authenticated', 'private', 'USAGE')"), [['f']])
    eq('authenticated: no right on any private table',
       db.admin(rel % f"n.nspname = 'private' and has_table_privilege('authenticated', c.oid, {ALLP})"), [])
    eq('authenticated: may write to no table except the class list (teacher only, by policy)',
       db.admin(rel % "has_table_privilege('authenticated', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE')"), [['public.roster']])
    eq('authenticated: no right on any sequence', db.admin(seq % 'authenticated'), [])
    eq('authenticated: may run exactly the listed functions', [r[0] for r in db.admin(fn % 'authenticated')],
       ['app.class_id', 'app.name_key', 'app.obj', 'app.pupil_id', 'app.safe_int', 'app.teaches', 'app.teaches_pupil',
        'public.record_answers', 'public.record_level', 'public.save_progress', 'public.teacher_delete_pupil'])
    eq('row level security is on for every table in public and private',
       db.admin("""select n.nspname || '.' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
                   where n.nspname in ('public', 'private') and c.relkind = 'r' and not c.relrowsecurity"""), [])
    eq('every table in public has a policy or no grant at all', db.admin(
        """select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = 'public' and c.relkind = 'r' and has_table_privilege('authenticated', c.oid, 'SELECT')
             and not exists (select 1 from pg_policy p where p.polrelid = c.oid)"""), [])
    eq('every security definer function pins its search_path', db.admin(
        """select n.nspname || '.' || p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace
           where n.nspname in ('public', 'private', 'app') and p.prosecdef
             and not exists (select 1 from unnest(coalesce(p.proconfig, '{}')) c where c like 'search_path=%')"""), [])
    eq('the three views are security barriers', db.admin(
        """select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = 'public' and c.relkind = 'v' and c.reloptions::text like '%security_barrier=true%'"""), [['3']])


def test_anon(db):
    print('\n== anon (the public key, not signed in) sees nothing ==')
    for t in PUBLIC_TABLES + VIEWS:
        denied(f'anon: select {t}', db.as_('anon', None, f'select * from public.{t}'))
    for t in ('pupil_secrets', 'class_codes'):
        denied(f'anon: select private.{t}', db.as_('anon', None, f'select * from private.{t}'))
    denied('anon: record_answers', db.as_('anon', None, f"select public.record_answers('{uuid.uuid4()}', '[]')"))
    denied('anon: save_progress', db.as_('anon', None, "select public.save_progress('{}')"))
    denied('anon: record_level', db.as_('anon', None, "select public.record_level('en', 'l1', 3)"))
    denied('anon: maintenance', db.as_('anon', None, 'select public.maintenance()'))
    denied('anon: insert a pupil', db.as_('anon', None, f"insert into public.pupils (class_id, display_name) values ('{C1}', 'mallory')"))
    denied('anon with a forged pupil id in the claims still has no grant', db.as_('anon', uid('A'), 'select * from public.pupils'))


def test_pupil(db):
    print('\n== pupil A against pupil B (same class) and pupil X (another class) ==')
    A = lambda sql: db.as_('authenticated', uid('A'), sql)
    db.admin(f"""update public.progress set state = '{{"secret":"b"}}' where pupil_id = '{pid('B')}';
                 update public.progress set state = '{{"secret":"x"}}' where pupil_id = '{pid('X')}';""")
    record(db, 'B', ans(2, minute=0, key='bword'))
    record(db, 'X', ans(2, minute=0, key='xword'))
    db.admin(f"insert into public.flags (pupil_id, kind, day) values ('{pid('A')}', 'rate', current_date)")
    rows, err = A('select id from public.pupils')
    eq('A reads the pupils table: only their own row', (rows, err), ([[pid('A')]], None))
    for t in ('answers', 'points', 'pupil_totals', 'progress', 'answer_daily'):
        rows, err = A(f'select distinct pupil_id from public.{t}')
        check(f"A reads {t}: no row of another pupil", err is None and all(r[0] == pid('A') for r in rows), err or rows)
    rows_n("A reads B's progress by id: nothing", A(f"select * from public.progress where pupil_id = '{pid('B')}'"), 0)
    rows_n("A reads X's answers by id: nothing", A(f"select * from public.answers where pupil_id = '{pid('X')}'"), 0)
    rows_n("A reads B's answers by id: nothing", A(f"select * from public.answers where pupil_id = '{pid('B')}'"), 0)
    rows_n('A reads classes: only their own class', A('select id from public.classes'), 1)
    rows_n('A reads teachers: nothing', A('select * from public.teachers'), 0)
    denied('A reads the item catalogue (it holds text other pupils sent): refused', A('select * from public.items'))
    rows_n('A reads the class list: nothing', A('select * from public.roster'), 0)
    rows_n('A reads flags (also their own): nothing', A('select * from public.flags'), 0)
    rows_n('A reads teacher_view: nothing', A('select * from public.teacher_view'), 0)
    rows_n('A reads teacher_items: nothing', A('select * from public.teacher_items'), 0)
    for t in PRIVATE_TABLES:
        denied(f'A reads private.{t} (codes, pictures, locks): refused', A(f'select * from private.{t}'))
    denied('A reads code hashes through a join', A('select s.code_hash from public.pupils p join private.pupil_secrets s on s.pupil_id = p.id'))
    denied('A calls a private function', A('select * from private.totals_check()'))

    print('-- writes')
    denied('A inserts an answer directly', A(f"insert into public.answers (pupil_id, item_id, pts, correct, first_try) values ('{pid('A')}', 1, 10, true, true)"))
    denied('A inserts points directly', A(f"insert into public.points (pupil_id, delta, reason) values ('{pid('A')}', 100000, 'fix')"))
    denied('A updates their total', A("update public.pupil_totals set points = 999999"))
    denied('A updates the points of their answers', A('update public.answers set pts = 10'))
    denied('A deletes answers', A('delete from public.answers'))
    denied("A updates B's progress", A(f"update public.progress set state = '{{}}' where pupil_id = '{pid('B')}'"))
    denied('A updates their own progress row directly (only save_progress may)', A("update public.progress set state = '{}'"))
    denied('A inserts a progress row for B', A(f"insert into public.progress (pupil_id) values ('{pid('B')}')"))
    denied('A moves to another class', A(f"update public.pupils set class_id = '{C2}'"))
    denied('A renames themselves', A("update public.pupils set display_name = 'admin'"))
    denied('A registers a pupil directly', A(f"insert into public.pupils (class_id, display_name) values ('{C1}', 'ghost')"))
    denied('A makes themselves a teacher', A(f"insert into public.teachers values ('{uid('A')}', '{C1}')"))
    denied('A clears a flag', A('delete from public.flags'))
    denied('A adds an item', A("insert into public.items (game, item_key) values ('en', 'zzz')"))
    rows, err = A(f"insert into public.roster values ('{C1}', 'ghost', 'ghost')")
    check('A adds a name to the class list: refused by policy', err is not None and 'row-level security' in err, err or rows)
    rows_n('A deletes from the class list: nothing happens', A('delete from public.roster returning 1'), 0)
    denied('A deletes a pupil as if a teacher', A(f"select public.teacher_delete_pupil('{pid('B')}')"), 'not your pupil')
    denied('A runs maintenance', A('select public.maintenance()'))

    print('-- save_progress writes the caller only')
    A("""select public.save_progress('{"pts": 1000000, "k": {"words": 7}, "streak": 3}')""")
    eq("A's blob is saved", db.one(f"select state ->> 'pts' from public.progress where pupil_id = '{pid('A')}'"), '1000000')
    eq("B's blob is untouched", db.one(f"select state ->> 'secret' from public.progress where pupil_id = '{pid('B')}'"), 'b')
    denied('a blob over the size limit is refused', A("select public.save_progress(jsonb_build_object('x', repeat('a', 41000)))"), 'bad input')
    denied('a blob that is not an object is refused', A("select public.save_progress('[1,2]')"), 'bad input')

    print('-- a signed-in user who is neither pupil nor teacher')
    S = lambda sql: db.as_('authenticated', STRAY, sql)
    for t in ['pupils', 'answers', 'points', 'pupil_totals', 'progress', 'classes', 'teachers', 'roster', 'flags'] + VIEWS:
        rows_n(f'stray user reads {t}: nothing', S(f'select * from public.{t}'), 0)
    denied('stray user records answers', S(f"select public.record_answers('{uuid.uuid4()}', '[]')"), 'not a pupil')
    denied('stray user saves progress', S("select public.save_progress('{}')"), 'not a pupil')
    rows_n('authenticated with no user id in the token reads the board: nothing', db.as_('authenticated', None, 'select * from public.class_board'), 0)


def test_points(db):
    print('\n== points are decided by the database ==')
    A = lambda sql: db.as_('authenticated', uid('A'), sql)
    tot = lambda k: db.admin(f"select points, answers, first_try, wrong from public.pupil_totals where pupil_id = '{pid(k)}'")[0]
    b1 = str(uuid.uuid4())
    r, err = record(db, 'A', ans(1, 1, key='cat') + ans(1, 2, key='dog', first=False) + ans(1, 3, key='sun', correct=False, first=False), b1)
    eq('right first try 10 + right later 4 + wrong 0 + daily bonus 20', (r and r['points'], err), (34, None))
    eq('totals row: points, answers, first try, wrong', tot('A'), ['34', '3', '1', '2'])
    r, _ = record(db, 'A', ans(1, 1, key='cat'), b1)
    eq('the same batch sent again is counted once', (r.get('dup'), tot('A')[0]), (True, '34'))
    b_before = tot('B')
    r, _ = record(db, 'A', ans(1, 5, key='hat', pts=1000, flag=0, pupil_id=pid('B'), delta=5000, points=99999))
    eq("forged fields in a row (pts, pupil_id, points) are ignored: A gets 10, B gets nothing", (r['points'], tot('B')), (44, b_before))
    eq('the blob says 1,000,000 points; the board says 44',
       db.as_('authenticated', uid('A'), "select points from public.class_board where me")[0], [['44']])
    rows, err = A('select display_name, me from public.class_board order by display_name')
    eq('the board shows the whole class and nobody else', (sorted(r[0] for r in rows), err), (sorted(NAMES[k] for k in 'ABCDEFGH'), None))
    eq('the board marks the caller', [r[0] for r in rows if r[1] == 't'], [NAMES['A']])
    rows, _ = db.as_('authenticated', uid('X'), 'select display_name from public.class_board')
    eq("another class's board is their own only", rows, [[NAMES['X']]])
    eq('the board has no ids', db.admin("select string_agg(column_name, ',' order by ordinal_position) from information_schema.columns where table_schema = 'public' and table_name = 'class_board'"), [['display_name,points,words,streak,me']])

    print('-- sanity checks: kept, 0 points, flagged')
    r, _ = record(db, 'C', ans(25, minute=1, step_s=1, key='w'))
    eq('25 answers in 25 seconds: 20 get points, 5 are flagged', (r['added'], r['flagged'], r['points']), (25, 5, 20 * 10 + 20))
    eq('all 25 rows are kept', db.one(f"select count(*) || '/' || count(*) filter (where flag = 1 and pts = 0) from public.answers where pupil_id = '{pid('C')}'"), '25/5')
    eq("the teacher's flag row", db.admin(f"select kind, n from public.flags where pupil_id = '{pid('C')}'"), [['rate', '5']])
    r, _ = record(db, 'C', ans(200, minute=10, step_s=0, key='burst'))
    eq('200 answers stamped with one instant: at most 20 more get points', r['points'], 220 + 200)
    db.admin('update private.settings set max_pointed_day = 5')
    r, _ = record(db, 'D', ans(8, minute=1, step_s=10, key='d'))
    db.admin('update private.settings set max_pointed_day = 600')
    eq('over the daily cap: 5 answers with points, 3 flagged', (r['points'], r['flagged']), (5 * 10 + 20, 3))
    eq('daycap flag', db.admin(f"select kind, n from public.flags where pupil_id = '{pid('D')}'"), [['daycap', '3']])
    r, _ = record(db, 'E', [dict(game='en', item_key='same', correct=True, first_try=True, t=BASE + i * 60000) for i in range(9)])
    eq('one item right 9 times in a day: 6 count, 3 flagged', (r['points'], r['flagged']), (6 * 10 + 20, 3))
    r, _ = record(db, 'E', [dict(game='EN;drop', item_key='x', correct=True, first_try=True), 'junk', dict(game='en', item_key='y' * 65, correct=True, first_try=True), 7, None])
    eq('rows that are not answers are dropped and flagged, nothing breaks', (r['added'], r['flagged'], r['points']), (0, 5, 80))
    seen = int(db.one(f"select coalesce(max(new_items), 0) from private.pupil_days where pupil_id = '{pid('E')}'"))
    db.admin(f'update private.settings set max_new_items = {seen + 3}')
    r, _ = record(db, 'E', ans(6, minute=20, step_s=10, key='new'))
    db.admin('update private.settings set max_new_items = 50')
    eq('a pupil cannot fill the item catalogue: 3 new items accepted, 3 refused', (r['added'], r['flagged']), (3, 3))
    r, _ = record(db, 'E', [dict(game='en', item_key='future', correct=True, first_try=True, t=NOW + 10 * 86400000),
                           dict(game='en', item_key='past', correct=True, first_try=True, t=NOW - 400 * 86400000)])
    span = db.admin(f"select bool_and(at <= now() and at > now() - interval '49 hours') from public.answers where pupil_id = '{pid('E')}'")
    eq('times from the future or from last year are pulled into the allowed window', span, [['t']])
    denied('a batch over 200 rows is refused whole', record(db, 'E', ans(201, key='big')), 'bad input')
    denied('rows that are not an array are refused', db.as_('authenticated', uid('E'), f"""select public.record_answers('{uuid.uuid4()}', '{{"a":1}}')"""), 'bad input')

    print('-- levels')
    F = lambda sql: db.as_('authenticated', uid('F'), sql)
    rows, err = F("select public.record_level('math', 'bay:1', 3)")
    eq('3 stars: 45 + daily bonus 20', (json.loads(rows[0][0])['points'], err), (65, None))
    denied('4 stars are refused', F("select public.record_level('math', 'bay:1', 4)"), 'bad input')
    denied('-1 stars are refused', F("select public.record_level('math', 'bay:1', -1)"), 'bad input')
    db.admin('update private.settings set max_levels_day = 3')
    for i in range(5):
        rows, _ = F(f"select public.record_level('math', 'bay:{i + 2}', 3)")
    db.admin('update private.settings set max_levels_day = 20')
    eq('levels over the daily cap earn nothing and are flagged', (json.loads(rows[0][0])['points'], db.admin(f"select kind, n from public.flags where pupil_id = '{pid('F')}'")), (65 + 2 * 45, [['levels', '3']]))

    print('-- a damaged or hostile blob cannot break the board or the teacher screen')
    db.as_('authenticated', uid('B'), """select public.save_progress('{"k": {"words": "many", "reads": {"a": 1}}, "streak": 1e400, "pts": "x", "g": {"st": {"l1": 99, "l2": "x", "l3": 2, "l4": null}}}')""")
    db.as_('authenticated', uid('C'), """select public.save_progress('{"k": 5, "g": [1, 2], "streak": -4}')""")
    rows, err = A('select display_name, words, streak from public.class_board order by display_name')
    check('the board still loads for the class', err is None and len(rows) == 8, err or rows)
    rows, err = db.as_('authenticated', T1, f"select stars, levels, words, streak from public.teacher_view where pupil_id = '{pid('B')}'")
    eq('the teacher view reads what is readable (stars capped at 3 a level)', (rows, err), ([['5', '2', '0', '1000']], None))

    eq('pupil_totals equals the ledgers for every pupil', db.admin('select * from private.totals_check()'), [])


def test_teacher(db):
    print('\n== a teacher sees only her class ==')
    T = lambda sql: db.as_('authenticated', T1, sql)
    rows, err = T('select class_id from public.pupils')
    check('teacher 1 reads pupils: her 8, none of class 2', err is None and len(rows) == 8 and all(r[0] == C1 for r in rows), err or rows)
    rows_n('teacher 1 reads teacher_view: 8 rows', T('select * from public.teacher_view'), 8)
    rows_n("teacher 1 reads class 2's pupil by id: nothing", T(f"select * from public.pupils where id = '{pid('X')}'"), 0)
    for t in ('answers', 'points', 'pupil_totals', 'progress', 'answer_daily', 'flags'):
        rows_n(f"teacher 1 reads {t} of a class 2 pupil: nothing", T(f"select * from public.{t} where pupil_id = '{pid('X')}'"), 0)
    rows, err = T('select distinct class_id from public.teacher_items')
    check('teacher_items: only her class', err is None and all(r[0] == C1 for r in rows), err or rows)
    rows, err = T("select item_key, tries, wrong, error_pct from public.teacher_items where item_key in ('sun', 'cat')")
    eq('teacher_items: an item needs 3 tries to appear', (rows, err), ([], None))
    rows_n('teacher 1 reads classes: one', T('select * from public.classes'), 1)
    rows_n('teacher 1 reads teachers: herself only', T('select * from public.teachers'), 1)
    rows, _ = T(f"select kind from public.flags where pupil_id = '{pid('C')}' and kind = 'rate'")
    eq('teacher 1 sees the flags of her pupil', rows, [['rate']])
    rows, _ = T(f"select points, answers, code_status, recovery_status, locked_today from public.teacher_view where pupil_id = '{pid('A')}'")
    eq('teacher_view row: server points, code and recovery status, locks today', rows, [['44', '4', 'set', 'open', '0']])
    db.admin(f"""insert into private.auth_lock_events (class_id, name_key, kind) values ('{C1}', '{NAMES['A']}', 'code'), ('{C1}', '{NAMES['A']}', 'code'), ('{C2}', '{NAMES['A']}', 'code');
                 insert into private.auth_buckets (class_id, name_key, kind, bucket, locked_until) values ('{C1}', '{NAMES['A']}', 'picture', '*', 'infinity');
                 update private.pupil_secrets set code_hash = null where pupil_id = '{pid('A')}';""")
    rows, _ = T(f"select code_status, recovery_status, locked_today from public.teacher_view where pupil_id = '{pid('A')}'")
    eq('teacher_view after a reset and locks: waiting, closed, locked 2 times today (not the other class\'s 1)', rows, [['waiting', 'closed', '2']])
    eq('teacher_view never carries a hash', db.admin("select count(*) from information_schema.columns where table_schema = 'public' and table_name = 'teacher_view' and (column_name like '%hash%' or column_name like '%salt%')"), [['0']])
    denied('teacher 1 reads the secrets table: refused like anyone', T('select * from private.pupil_secrets'))
    denied('teacher 1 writes points', T(f"insert into public.points (pupil_id, delta, reason) values ('{pid('A')}', 5, 'fix')"))
    denied('teacher 1 edits an answer', T('update public.answers set pts = 0'))
    rows, err = T(f"insert into public.roster values ('{C2}', 'x y', 'x y')")
    check("teacher 1 adds a name to class 2's list: refused by policy", err is not None and 'row-level security' in err, err or rows)
    rows, err = T(f"insert into public.roster values ('{C1}', 'new kid', 'New Kid') returning name_key")
    eq('teacher 1 adds a name to her own class list', (rows, err), ([['new kid']], None))
    rows_n("teacher 1 deletes from class 2's list: nothing happens", T(f"delete from public.roster where class_id = '{C2}' returning 1"), 0)
    denied('teacher 1 deletes a pupil of class 2', T(f"select public.teacher_delete_pupil('{pid('X')}')"), 'not your pupil')
    rows, err = T(f"select public.teacher_delete_pupil('{pid('G')}')")
    left = db.admin(f"""select (select count(*) from public.pupils where id = '{pid('G')}'), (select count(*) from public.pupil_totals where pupil_id = '{pid('G')}'),
                        (select count(*) from private.pupil_secrets where pupil_id = '{pid('G')}'), (select count(*) from auth.users where id = '{uid('G')}')""")
    eq('teacher 1 deletes her pupil: the row, totals, secrets and auth user are gone', (err, left), (None, [['0', '0', '0', '0']]))
    rows_n('teacher 2 reads pupils: only class 2', db.as_('authenticated', T2, 'select * from public.pupils'), 1)
    rows_n('teacher 2 reads the board: only class 2', db.as_('authenticated', T2, 'select * from public.class_board'), 1)

    print('-- constraints')
    bad = lambda name: db.psql(f"insert into public.pupils (class_id, display_name) values ('{C1}', $n${name}$n$)")[1]
    check('a name with markup is refused by the table', bad('<b>x</b>') is not None)
    check('a spreadsheet formula as a name is refused', bad('=1+1') is not None)
    check('a one-letter name is refused', bad('x') is not None)
    check('the same name in other letter case and spacing is the same pupil', 'duplicate key' in (bad(' ' + NAMES['A'] + '  ') or ''))
    check('the same name in another class is allowed', bad('  O\'Neil-Ben ') is None and db.psql(f"insert into public.pupils (class_id, display_name) values ('{C2}', $n$o'neil-ben$n$)")[1] is None)

    print('-- maintenance (server role only)')
    record(db, 'H', ans(4, minute=0, key='old') + ans(1, 5, key='hard', correct=False, first=False) + ans(1, 6, key='hard', correct=False, first=False) + ans(1, 7, key='hard'))
    before = db.admin(f"select points, answers from public.pupil_totals where pupil_id = '{pid('H')}'")
    db.admin('update private.settings set raw_days = 0')
    rows, err = db.as_('service_role', None, 'select public.maintenance()')
    db.admin('update private.settings set raw_days = 90')
    m = json.loads(rows[0][0]) if not err else {}
    check('the server role runs maintenance; totals still equal the ledgers', err is None and m.get('ok') is True and m.get('rolled', 0) > 0, err or m)
    eq('old answers are rolled up, not lost: totals unchanged', db.admin(f"select points, answers from public.pupil_totals where pupil_id = '{pid('H')}'"), before)
    eq('the roll-up holds them per day and item', db.admin(f"select sum(tries), sum(first_try), sum(pts) from public.answer_daily where pupil_id = '{pid('H')}'"), [['7', '5', '50']])
    rows, _ = db.as_('authenticated', T1, "select tries, wrong from public.teacher_items where item_key = 'hard'")
    eq('weak items still count rolled-up answers', rows, [['3', '2']])
    rows_n('the server role reads everything (RLS does not apply to it)', db.as_('service_role', None, 'select 1 from public.pupils'), 10)


def test_load(db):
    """35 pupils of one class save inside the same 10 seconds, three rounds. Every save and every answer must be there."""
    print('\n== load: 35 pupils, 3 rounds, all at once ==')
    N, ROUNDS, PER = 35, 3, 10
    cls = U(0xC9)
    kids = [(U(0x1A000 + i), U(0x1B000 + i)) for i in range(N)]
    db.admin(f"insert into public.classes (id, name) values ('{cls}', 'load class');"
             + "insert into auth.users (id) values " + ', '.join(f"('{a}')" for a, _ in kids) + ';'
             + 'insert into public.pupils (id, class_id, display_name, auth_user_id) values '
             + ', '.join(f"('{p}', '{cls}', 'load {chr(0x5d0 + i % 27)}{chr(0x5d0 + i // 27)}', '{a}')" for i, (a, p) in enumerate(kids)) + ';')
    base = int(time.time() * 1000) - 30 * 60000
    errors, slowest = [], 0.0
    for rnd in range(ROUNDS):
        gate, times = threading.Barrier(N), [0.0] * N

        def one(i):
            a, p = kids[i]
            rows = [dict(game='en', item_key=f'load{rnd}_{j}', correct=True, first_try=True, t=base + (rnd * PER + j) * 20000) for j in range(PER)]
            state = json.dumps({'round': rnd, 'pad': 'x' * 8000, 'k': {'words': rnd}})
            sql = (f"select public.save_progress($j${state}$j$::jsonb);\n"
                   f"select public.record_answers('{uuid.uuid4()}', $j${json.dumps(rows)}$j$::jsonb);\n"
                   "select count(*) from public.class_board")
            gate.wait()
            t0 = time.time()
            res = db.as_('authenticated', a, sql)
            times[i] = time.time() - t0
            if res[1]:
                errors.append(res[1])
        t0 = time.time()
        th = [threading.Thread(target=one, args=(i,)) for i in range(N)]
        [t.start() for t in th]; [t.join() for t in th]
        wall = time.time() - t0
        slowest = max(slowest, max(times))
        print(f'   round {rnd + 1}: {N} pupils saved a blob, {PER} answers and read the board in {wall:.2f}s (slowest pupil {max(times):.2f}s)')
        check(f'round {rnd + 1}: every pupil finished inside 10 seconds', wall < 10, f'{wall:.1f}s')
    eq('no pupil got an error', errors, [])
    eq('no lost save: every blob is the last round', db.admin(f"select count(*) from public.progress g join public.pupils p on p.id = g.pupil_id where p.class_id = '{cls}' and g.state ->> 'round' = '{ROUNDS - 1}'"), [[str(N)]])
    eq('no lost answer: 30 rows per pupil', db.admin(f"select count(*), min(n), max(n) from (select count(*) n from public.answers a join public.pupils p on p.id = a.pupil_id where p.class_id = '{cls}' group by a.pupil_id) x"), [[str(N), str(ROUNDS * PER), str(ROUNDS * PER)]])
    eq('every total is exact: 30 x 10 + daily bonus', db.admin(f"select distinct t.points from public.pupil_totals t join public.pupils p on p.id = t.pupil_id where p.class_id = '{cls}'"), [[str(ROUNDS * PER * 10 + 20)]])

    print('-- one pupil, two devices and retries at the same moment')
    a, p = kids[0]
    dup = str(uuid.uuid4())
    jobs = [(str(uuid.uuid4()), f'par{i}') for i in range(12)] + [(dup, 'dup')] * 6
    gate, errs = threading.Barrier(len(jobs)), []

    def two(b, key):
        rows = [dict(game='en', item_key=f'{key}_{j}', correct=True, first_try=False) for j in range(1)]
        gate.wait()
        res = db.as_('authenticated', a, f"select public.record_answers('{b}', $j${json.dumps(rows)}$j$::jsonb)")
        if res[1]:
            errs.append(res[1])
    th = [threading.Thread(target=two, args=j) for j in jobs]
    [t.start() for t in th]; [t.join() for t in th]
    eq('12 parallel batches and one batch sent 6 times: no error', errs, [])
    eq('13 answers stored, not 18 and not fewer', db.one(f"select count(*) from public.answers where pupil_id = '{p}'"), str(ROUNDS * PER + 13))
    eq('the total moved by exactly 13 x 4', db.one(f"select points from public.pupil_totals where pupil_id = '{p}'"), str(ROUNDS * PER * 10 + 20 + 13 * 4))
    eq('pupil_totals equals the ledgers after the load', db.admin('select * from private.totals_check()'), [])


def main():
    args = sys.argv[1:]
    db = pg.start()
    try:
        if '--load' not in args:
            fixture(db)
            test_catalogue(db); test_anon(db); test_pupil(db); test_points(db); test_teacher(db)
        if '--no-load' not in args:
            test_load(db)
    finally:
        db.stop()
    print(f'\n{PASS} passed, {FAIL} failed')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
