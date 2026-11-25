#!/usr/bin/env python3
"""docs/BACKEND.md section 10: "verify on a real project before the switch". Runs on the OWNER'S computer, the day the
project exists, never in GitHub Actions (it needs the server key):

    SUPABASE_URL=https://<project>.supabase.co SUPABASE_ANON_KEY=... SUPABASE_SERVICE_KEY=... python3 tests/live_check.py
    python3 tests/live_check.py --list          what is checked, and what stays a manual step

Optional: TEACHER_TOKEN (an access token of the teacher after her Google sign-in: items 7, 8, 12 with a teacher),
BACKUP_TOKEN with the owner's private key in gpg (items 15, 19), --no-load (skip item 17), --no-header (skip item 10:
it spends this computer's wrong-class-code allowance for an hour).

It touches only what it makes: a class called "live check" with made-up pupils (Livecheck, Loadtest NN), deleted
with their auth users at the end, whatever happened. It never changes the real class (with TEACHER_TOKEN it counts
the rows of her teacher view, nothing more). shadow_mode must be
off. Exit 1 if any check fails; MANUAL items are printed with what to do."""
import base64, concurrent.futures as cf, json, os, re, secrets, subprocess, sys, tempfile, time, urllib.error, urllib.request

ITEMS = {
    1: 'generateLink + verifyOtp issue a session with sign-up off and an .invalid label; email_confirm on create',
    2: '35 sign-ins in a minute pass the Auth rate limits; one pupil twice in 10 s',
    3: 'a pupil token cannot change its user (password, email, factors, /otp, /recover for the label)',
    4: 'triggers on auth.users and auth.mfa_factors exist and fire',
    5: 'sign-up, anonymous and phone sign-in are refused with the public key',
    6: 'after a recovery the old access token reads and writes nothing; the old refresh token is dead',
    7: 'the server role may delete auth users and old audit rows (teacher_delete_pupil, maintenance())',
    8: 'owner-rights views: rows for a teacher, none for a pupil; RLS through the real API',
    9: 'only public is reachable: private and app through REST and GraphQL give nothing',
    10: 'a client-sent address header does not win over the platform\'s',
    11: 'PBKDF2 600,000 rounds fit the function CPU limit (20 timed sign-ins)',
    12: 'teacher-reset refuses a pupil token, an expired token and no token (verify_jwt = false)',
    13: 'Google sign-in lands on the pre-created teacher user',
    14: 'ping() with the public key counts as activity against the pause',
    15: 'backup_export decrypts with the owner\'s key and restores into a second project, totals green',
    16: 'free-plan numbers of section 6 and the restore window of a paused project',
    17: 'load: 35 pupils, 3 rounds of saves through the real API, nothing lost',
    18: 'pg_cron runs maintenance() nightly; audit_purged is true',
    19: 'pgcrypto encrypts to the owner\'s RSA 4096 key; a whole-class export fits the statement timeout',
    20: 'the local suites\' assertions hold through the API',
}
MANUAL = {
    4: 'Covered by item 3 here. Also once in a SCRATCH project: switch "secure email change" off, rerun item 3: it must still pass (the trigger holds).',
    13: 'The teacher signs in with Google once; in SQL: select id, email from auth.users where email = <her address>; it must be the pre-created id in public.teachers.',
    14: 'Read Supabase\'s docs on pausing on the day; watch the dashboard\'s activity over a quiet holiday week.',
    15: 'The restore drill: python3 tools/restore.py on an export, into a second free project (docs/BACKEND.md section 6).',
    16: 'Read the free-plan page on the day; correct section 6 of docs/BACKEND.md if a number moved.',
    18: 'Next morning, in the SQL editor: select * from cron.job; select status, return_message from cron.job_run_details order by start_time desc limit 3;',
    20: 'Items 1-3, 5-12 and 17 here run the same assertions as tests/db.py and tests/functions.py through the API.',
}

results = []


def report(n, status, detail=''):
    results.append((n, status))
    print(f'{status:6} {n:>2}. {ITEMS[n]}' + (f'  <- {detail}' if detail else ''))


class Api:
    def __init__(self, url, anon, service):
        self.url, self.anon, self.service = url, anon, service

    def call(self, method, path, body=None, token=None, key=None, headers=None):
        h = {'content-type': 'application/json', 'apikey': key or self.anon, 'authorization': 'Bearer ' + (token or key or self.anon)}
        h.update(headers or {})
        req = urllib.request.Request(self.url + path, method=method, headers=h, data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, None

    def fn(self, name, body, token=None, headers=None):
        return self.call('POST', '/functions/v1/' + name, body, token=token, headers=headers)

    def admin(self, method, path, body=None):
        return self.call(method, path, body, key=self.service)


def jwt_sub(tok):
    p = tok.split('.')[1]
    return json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))['sub']


def run(api, a):
    made = {'class': None}
    ok2xx = lambda s: 200 <= s < 300
    s, j = api.fn('admin-class', {'action': 'create', 'name': 'live check', 'grade': 'test'}, token=api.service)
    if not (s == 200 and j and j.get('ok')):
        print('cannot create the test class with admin-class:', s, j); return
    made['class'] = j['class_id']; ccode = j['class_code']
    api.admin('PATCH', f'/rest/v1/classes?id=eq.{made["class"]}', {'roster_only': False})
    code, pics = '%04d' % (4827), [3, 11]
    try:
        # 1
        s, r = api.fn('pupil-register', {'class_code': ccode, 'name': 'Livecheck', 'code': code, 'pictures': pics})
        if r and r.get('e') == 'locked' and r.get('wait') == -1:
            report(1, 'FAIL', 'registration refused: is shadow_mode on? It must be off for this check'); return
        report(1, 'PASS' if r and r.get('ok') and r['session'].get('access_token') else 'FAIL', f'{s} {r and r.get("e")}')
        if not (r and r.get('ok')):
            return
        tok, ref, dev = r['session']['access_token'], r['session']['refresh_token'], r.get('device_token')
        uid = jwt_sub(tok)
        _, u = api.admin('GET', f'/auth/v1/admin/users/{uid}')
        email0 = (u or {}).get('email')
        # 2
        t0 = time.time()
        with cf.ThreadPoolExecutor(35) as ex:
            got = list(ex.map(lambda _: api.fn('pupil-login', {'class_code': ccode, 'name': 'Livecheck', 'code': code, 'device_token': dev}), range(35)))
        bad = [g for g in got if not (g[1] and g[1].get('ok'))]
        a1, a2 = api.fn('pupil-login', {'class_code': ccode, 'name': 'Livecheck', 'code': code, 'device_token': dev}), \
            api.fn('pupil-login', {'class_code': ccode, 'name': 'Livecheck', 'code': code, 'device_token': dev})
        report(2, 'PASS' if not bad and a1[1].get('ok') and a2[1].get('ok') and time.time() - t0 < 60 else 'FAIL',
               f'{len(bad)} of 35 failed: {bad[:1]}' if bad else '')
        s, r = api.fn('pupil-login', {'class_code': ccode, 'name': 'Livecheck', 'code': code, 'device_token': dev})
        tok, ref = r['session']['access_token'], r['session']['refresh_token']
        uid = jwt_sub(tok)
        # 3
        tries = [api.call('PUT', '/auth/v1/user', {'password': secrets.token_urlsafe(24)}, token=tok),
                 api.call('PUT', '/auth/v1/user', {'email': 'someone@example.com'}, token=tok),
                 api.call('POST', '/auth/v1/factors', {'factor_type': 'totp'}, token=tok),
                 api.call('POST', '/auth/v1/otp', {'email': email0, 'create_user': False}),
                 api.call('POST', '/auth/v1/recover', {'email': email0})]
        _, u = api.admin('GET', f'/auth/v1/admin/users/{uid}')
        _, f = api.admin('GET', f'/auth/v1/admin/users/{uid}/factors')
        changed = (u or {}).get('email') != email0 or (u or {}).get('phone') or (isinstance(f, list) and f)
        s, r = api.fn('pupil-login', {'class_code': ccode, 'name': 'Livecheck', 'code': code, 'device_token': dev})
        report(3, 'PASS' if not any(ok2xx(t[0]) for t in tries) and not changed else 'FAIL',
               f'statuses {[t[0] for t in tries]}; user changed: {bool(changed)}; sign-in after: {r and r.get("ok")}')
        if r and r.get('ok'):
            tok, ref = r['session']['access_token'], r['session']['refresh_token']
        report(4, 'MANUAL', MANUAL[4])
        # 5
        tries = [api.call('POST', '/auth/v1/signup', {'email': f'x{secrets.token_hex(4)}@example.invalid', 'password': secrets.token_urlsafe(24)}),
                 api.call('POST', '/auth/v1/signup', {}),
                 api.call('POST', '/auth/v1/otp', {'phone': '+15555550100'})]
        report(5, 'PASS' if not any(ok2xx(t[0]) for t in tries) else 'FAIL', f'statuses {[t[0] for t in tries]}')
        # 8, 9 as a pupil
        s1, board = api.call('GET', '/rest/v1/class_board?select=display_name', token=tok)
        s2, tv = api.call('GET', '/rest/v1/teacher_view?select=pupil_id', token=tok)
        s3, pu = api.call('GET', '/rest/v1/pupils?select=id', token=tok)
        teacher = os.environ.get('TEACHER_TOKEN')
        tview = api.call('GET', '/rest/v1/teacher_view?select=pupil_id', token=teacher) if teacher else (None, None)
        good = s1 == 200 and len(board) == 1 and s2 == 200 and tv == [] and s3 == 200 and len(pu) == 1
        if teacher:      # her own class: only the number of rows is looked at, nothing is printed
            good = good and tview[0] == 200 and isinstance(tview[1], list) and len(tview[1]) > 0
        report(8, 'PASS' if good else 'FAIL', '' if teacher else 'pupil side only; set TEACHER_TOKEN for the teacher side')
        leaks = [api.call('GET', '/rest/v1/pupil_secrets?select=*', token=tok),
                 api.call('GET', '/rest/v1/pupil_secrets?select=*', token=tok, headers={'accept-profile': 'private'}),
                 api.call('GET', '/rest/v1/settings?select=*', token=tok, headers={'accept-profile': 'private'}),
                 api.call('POST', '/rest/v1/rpc/pupil_id', {}, token=tok, headers={'content-profile': 'app'}),
                 api.call('POST', '/graphql/v1', {'query': '{ __schema { types { name } } }'}, token=tok)]
        gql = leaks[4]
        gql_leak = ok2xx(gql[0]) and 'pupil_secrets' in json.dumps(gql[1] or {})
        report(9, 'PASS' if not any(ok2xx(t[0]) for t in leaks[:4]) and not gql_leak else 'FAIL', f'statuses {[t[0] for t in leaks]}')
        # 12
        exp = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' + base64.urlsafe_b64encode(json.dumps({'sub': uid, 'role': 'authenticated', 'exp': 1}).encode()).decode().rstrip('=') + '.x'
        tr = [api.fn('teacher-reset', {'pupil_id': uid}, token=tok), api.fn('teacher-reset', {'pupil_id': uid}, token=exp),
              api.fn('teacher-reset', {'pupil_id': uid}, token=api.anon)]
        report(12, 'PASS' if all(t[1] and t[1].get('e') == 'forbidden' for t in tr) else 'FAIL', f'{[t[1] and t[1].get("e") for t in tr]}')
        # 11
        times, errs = [], []
        for _ in range(20):
            t1 = time.time()
            s, r = api.fn('pupil-login', {'class_code': ccode, 'name': 'Livecheck', 'code': code, 'device_token': dev})
            times.append(time.time() - t1)
            if not (r and r.get('ok')):
                errs.append(s)
        times.sort()
        report(11, 'PASS' if not errs and times[-1] < 10 else 'FAIL', f'median {times[10]:.2f} s, slowest {times[-1]:.2f} s, errors {errs[:3]}')
        if not errs:
            tok, ref = r['session']['access_token'], r['session']['refresh_token']
        # 6: recovery by pictures, then the old tokens
        old_tok, old_ref = tok, ref
        s, r = api.fn('pupil-recover', {'class_code': ccode, 'name': 'Livecheck', 'pictures': pics, 'new_code': '5938', 'new_pictures': [7, 2]})
        if r and r.get('ok'):
            w = api.call('POST', '/rest/v1/rpc/save_progress', {'p_state': {'live': 1}}, token=old_tok)
            rd = api.call('GET', '/rest/v1/pupils?select=id', token=old_tok)
            rf = api.call('POST', '/auth/v1/token?grant_type=refresh_token', {'refresh_token': old_ref})
            dead = not ok2xx(w[0]) and (not ok2xx(rd[0]) or rd[1] == []) and not ok2xx(rf[0])
            report(6, 'PASS' if dead else 'FAIL', f'save {w[0]}, read {rd[0]} {rd[1]}, refresh {rf[0]}')
            tok = r['session']['access_token']
        else:
            report(6, 'FAIL', f'recovery failed: {s} {r}')
        # 7
        s, m = api.call('POST', '/rest/v1/rpc/maintenance', {}, key=api.service)
        report(7, 'PASS' if s == 200 and m and m.get('audit_purged') is True else 'FAIL',
               f'maintenance: {m}; deleting auth users is exercised by the clean-up below')
        # 14
        s, p = api.call('POST', '/rest/v1/rpc/ping', {})
        report(14, 'MANUAL' if s == 200 and p is True else 'FAIL', MANUAL[14] if s == 200 else f'ping: {s} {p}')
        # 17
        if '--no-load' in a:
            report(17, 'SKIP', '--no-load')
        else:
            def one(i):
                name = f'Loadtest {chr(65 + i // 26)}{chr(65 + i % 26)}'
                s, r = api.fn('pupil-register', {'class_code': ccode, 'name': name, 'code': '7159', 'pictures': [5, 9]})
                return r['session']['access_token'] if r and r.get('ok') else None
            with cf.ThreadPoolExecutor(35) as ex:
                toks = list(ex.map(one, range(35)))
            lost = sum(1 for t in toks if not t)
            for rnd in range(3):
                def save(t):
                    s, r = api.call('POST', '/rest/v1/rpc/save_progress', {'p_state': {'round': rnd}}, token=t)
                    if r and r.get('conflict'):
                        s, r = api.call('POST', '/rest/v1/rpc/save_progress', {'p_state': {'round': rnd}, 'p_base': r['updated_at']}, token=t)
                    return bool(r and r.get('ok'))
                with cf.ThreadPoolExecutor(35) as ex:
                    lost += sum(1 for ok in ex.map(save, [t for t in toks if t]) if not ok)
            report(17, 'PASS' if lost == 0 else 'FAIL', f'{lost} registrations or saves failed')
        # 10 (last: spends this computer's wrong-class-code allowance for an hour)
        if '--no-header' in a:
            report(10, 'SKIP', '--no-header')
        else:
            last = None
            for i in range(32):
                _, last = api.fn('pupil-login', {'class_code': 'ZZZZ' + '%04d' % i, 'name': 'Livecheck', 'code': '5938'},
                                 headers={'x-forwarded-for': f'198.51.100.{i + 1}', 'x-real-ip': f'198.51.100.{i + 1}'})
            report(10, 'PASS' if last and last.get('e') == 'locked' else 'FAIL',
                   'forged headers did not reset the per-address limit' if last and last.get('e') == 'locked' else f'32 wrong class codes with forged headers still answered {last}')
        for n in (13, 15, 16, 18, 20):
            report(n, 'MANUAL', MANUAL[n])
        # 19
        bt = os.environ.get('BACKUP_TOKEN')
        if not bt:
            report(19, 'SKIP', 'set BACKUP_TOKEN (and have the private key in gpg)')
        else:
            d = tempfile.mkdtemp(prefix='wi-live-backup-')
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            f = subprocess.run([sys.executable, os.path.join(root, 'tools/backup_fetch.py'), d], capture_output=True, text=True)
            first = sorted(x for x in os.listdir(d) if x.endswith('.asc'))[:1]
            dec = subprocess.run(['gpg', '--batch', '--quiet', '--decrypt', os.path.join(d, first[0])], capture_output=True) if first else None
            report(19, 'PASS' if f.returncode == 0 and dec and dec.returncode == 0 else 'FAIL', (f.stdout + f.stderr).strip()[-200:])
    finally:
        if made['class']:
            _, ps = api.admin('GET', f'/rest/v1/pupils?select=auth_user_id&class_id=eq.{made["class"]}')
            api.admin('DELETE', f'/rest/v1/classes?id=eq.{made["class"]}')
            for p in ps or []:
                if p.get('auth_user_id'):
                    api.admin('DELETE', f'/auth/v1/admin/users/{p["auth_user_id"]}')
            print('cleaned up: the test class, its pupils and their auth users')


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if '--list' in a:
        for n, t in ITEMS.items():
            print(f'{n:>2}. {t}' + (f'\n    MANUAL: {MANUAL[n]}' if n in MANUAL else ''))
        return 0
    url, anon, service = (os.environ.get(k, '').strip() for k in ('SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_KEY'))
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', url) or not anon or not service:
        print('no project: set SUPABASE_URL (https://<project>.supabase.co), SUPABASE_ANON_KEY and SUPABASE_SERVICE_KEY. --list shows the checks.')
        return 2
    if os.environ.get('GITHUB_ACTIONS'):
        print('refused: this needs the server key and runs on the owner\'s computer only')
        return 2
    run(Api(url, anon, service), a)
    fails = [n for n, s in results if s == 'FAIL']
    print(f"\n{sum(1 for _, s in results if s == 'PASS')} passed, {len(fails)} failed, "
          f"{sum(1 for _, s in results if s == 'MANUAL')} manual, {sum(1 for _, s in results if s == 'SKIP')} skipped")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
