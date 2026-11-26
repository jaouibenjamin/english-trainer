"""A stand-in Supabase project for the game's pupil side, in a browser test (never a real project). Not a suite.

It answers on the project's address, through Playwright's routing (the page's Content-Security-Policy is bypassed in
those tests only), the way supabase/functions/_shared/core.ts and the database answer the game:
  - pupil-register, pupil-login, pupil-recover: the session, the device token, the record, the name; or the error word
    (input, weak, class, pin, taken, roster, full, picture, otc) and, when `lock` is set, locked with wait, by and help;
  - the token refresh and logout; and with a session: the pupil's own row (pupils), the record (progress), the board
    (class_board, with me), save_progress and record_events.
Used by tests/supabase_mode.py (step 6) and the sign-in screens' suite (step 5). Names and codes are made up.

    prj = Project(); await context.route(SB + '/**', prj.route)
    prj.log: every request (path, query, method, auth, body); prj.dead = True: every session refused from now on;
    prj.lock = {'wait': 300, 'by': 'name', 'help': 'teacher'}: the three functions answer locked;
    prj.next['recover'] = {'ok': False, 'e': 'locked', 'wait': -1, 'by': 'name', 'help': 'teacher'}: that answer, once."""
import json, re, urllib.parse

SB, KEY = 'https://abcdefghijklmnop.supabase.co', 'public-key-for-tests-0123456789'
REAL, TRIAL = '11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222'
PA, PB, PT = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
CODES = ('4827', '5839')
PUPILS = {('EN-0000', 'testa'): dict(id=PA, cls=REAL, code='4827', name='Testa'),
          ('EN-0000', 'probe'): dict(id=PB, cls=REAL, code='5839', name='Probe'),
          ('TRIAL-01', 'testa'): dict(id=PT, cls=TRIAL, code='4827', name='Testa')}
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': 'apikey, authorization, content-type, prefer', 'access-control-allow-methods': 'GET, POST, OPTIONS'}
NEW_CFG = f"window.API_URL='';window.BACKEND={{mode:'supabase',url:'{SB}',key:'{KEY}',everyone:true,saveEveryS:0}};"
SHEET_CFG = "window.API_URL='https://script.example/macros/s/TEST/exec';"
SHEET_ERA = {'u': {'c': 'EN-0000', 'n': 'Testa', 'p': '4827'}, 'pts': 120, 'st': {'cat': [3, 0]}, 'day': '2026-1-1', 'streak': 1}


WEAK = re.compile(r'^(\d)\1{3}$|^(0123|1234|2345|3456|4567|5678|6789|9876|8765|7654|6543|5432|4321|3210)$')
CLASSES = {'EN-0000': REAL, 'TRIAL-01': TRIAL}
ROSTER = {('EN-0000', 'testa'), ('EN-0000', 'probe'), ('EN-0000', 'newbie'), ('TRIAL-01', 'testa')}


class Project:
    """the stand-in: the pupil functions, the token, the pupil's own row, the record, the board and the two writes"""
    def __init__(self):
        self.log, self.tokens, self.progress, self.dead, self.n, self.lock = [], {}, {}, False, 0, None
        self.pupils = {k: dict(v, pics=[3, 17]) for k, v in PUPILS.items()}
        self.otc = {}   # (class code, name key) -> the teacher's one-time code
        self.no_who = False   # the pupil's own row cannot be read (503)
        self.unset = False    # the project's functions are not deployed yet: they answer 404
        self.next = {}  # 'register' | 'login' | 'recover' -> an answer given once, on the next call (the screens' waits table)

    def opened(self, p):
        self.n += 1; tok = f"tok-{p['id'][:4]}-{self.n}"; self.tokens[tok] = p
        s, at = self.state(p['id'])
        return {'ok': True, 'session': {'access_token': tok, 'refresh_token': 'ref-' + tok, 'expires_in': 3600}, 'device_token': 'd' * 43, 'updated_at': at, 's': s, 'name': p['name']}

    def pupil_fn(self, kind, b):
        """register, login, recover: as core.ts answers them (the checks the game can meet)"""
        code = lambda x: isinstance(x, str) and re.fullmatch(r'\d{4}', x) is not None
        pics = lambda x: isinstance(x, list) and len(x) == 2 and len(set(x)) == 2 and all(isinstance(i, int) and 1 <= i <= 20 for i in x)
        c, n = str(b.get('class_code', '')).upper(), str(b.get('name', '')).strip().lower()
        if not c or not n:
            return {'ok': False, 'e': 'input'}
        if kind == 'register' and not (code(b.get('code')) and pics(b.get('pictures'))):
            return {'ok': False, 'e': 'input'}
        if kind == 'login' and not code(b.get('code')):
            return {'ok': False, 'e': 'input'}
        if kind == 'recover' and not (code(b.get('new_code')) and pics(b.get('new_pictures')) and (pics(b.get('pictures')) or re.fullmatch(r'\d{6}', str(b.get('otc', ''))))):
            return {'ok': False, 'e': 'input'}
        if WEAK.match(str(b.get('code') if kind == 'register' else b.get('new_code') if kind == 'recover' else '')):
            return {'ok': False, 'e': 'weak'}
        if self.lock:
            return {'ok': False, 'e': 'locked', **self.lock}
        if c not in CLASSES:
            return {'ok': False, 'e': 'class'}
        p = self.pupils.get((c, n))
        if kind == 'register':
            if p:
                return {'ok': False, 'e': 'taken'}
            if (c, n) not in ROSTER:
                return {'ok': False, 'e': 'roster'}
            p = self.pupils[(c, n)] = dict(id=f'dddddddd-dddd-4ddd-8ddd-{len(self.pupils):012d}', cls=CLASSES[c], code=b['code'], name=str(b['name']).strip(), pics=b['pictures'])
            return self.opened(p)
        if kind == 'login':
            return self.opened(p) if p and b.get('code') == p['code'] else {'ok': False, 'e': 'pin'}
        by_otc = 'otc' in b
        right = p and (self.otc.get((c, n)) == str(b.get('otc')) if by_otc else b.get('pictures') == p['pics'])
        if not right:
            return {'ok': False, 'e': 'otc' if by_otc else 'picture'}
        p.update(code=b['new_code'], pics=b['new_pictures']); self.otc.pop((c, n), None)
        for t in [t for t, q in self.tokens.items() if q is p]:
            del self.tokens[t]   # every other device of the pupil is signed out
        return self.opened(p)

    def state(self, pid):
        return self.progress.get(pid, ({}, None))

    async def route(self, r):
        req = r.request; u = urllib.parse.urlparse(req.url)
        if req.method == 'OPTIONS':
            return await r.fulfill(status=204, headers=CORS)
        body = json.loads(req.post_data or 'null')
        auth = req.headers.get('authorization', '')
        self.log.append(dict(path=u.path, query=u.query, method=req.method, auth=auth, body=req.post_data or ''))
        ok = lambda j, status=200: r.fulfill(status=status, headers=CORS, json=j)
        if u.path.startswith('/functions/v1/pupil-') and self.unset:
            return await r.fulfill(status=404, headers=CORS, json={'code': 'NOT_FOUND', 'message': 'Requested function was not found'})   # not deployed yet
        if u.path.startswith('/functions/v1/pupil-'):
            kind = u.path.rsplit('-', 1)[1]
            return await ok(self.next.pop(kind) if kind in self.next else self.pupil_fn(kind, body or {}))
        if u.path == '/auth/v1/token':
            p = self.tokens.get(str(body.get('refresh_token', ''))[4:])
            if self.dead or not p:
                return await ok({'error': 'invalid_grant'}, 400)
            self.n += 1; tok = f"tok-{p['id'][:4]}-{self.n}"; self.tokens[tok] = p
            return await ok({'access_token': tok, 'refresh_token': 'ref-' + tok, 'expires_in': 3600})
        if u.path == '/auth/v1/logout':
            self.tokens.pop(auth.replace('Bearer ', ''), None)
            return await r.fulfill(status=204, headers=CORS)
        p = None if self.dead else self.tokens.get(auth.replace('Bearer ', ''))
        if not p:
            return await ok({'message': 'JWT expired'}, 401)
        if u.path == '/rest/v1/pupils':
            return await ok(None, 503) if self.no_who else await ok([{'id': p['id'], 'class_id': p['cls']}])
        if u.path == '/rest/v1/progress':
            s, at = self.state(p['id'])
            return await ok([{'state': s, 'updated_at': at}] if at else [])
        if u.path == '/rest/v1/class_board':
            rows = [dict(display_name=q['name'], points=int(self.state(q['id'])[0].get('pts', 0)), words=0, streak=0, me=q['id'] == p['id']) for q in PUPILS.values() if q['cls'] == p['cls']]
            return await ok(sorted(rows, key=lambda x: -x['points']))
        if u.path == '/rest/v1/rpc/save_progress':
            self.n += 1; self.progress[p['id']] = (body['p_state'], f'at-{self.n}')
            return await ok({'ok': True, 'updated_at': f'at-{self.n}'})
        if u.path == '/rest/v1/rpc/record_events':
            return await ok({'ok': True, 'points': 0, 'flagged': 0})
        return await ok(None, 404)


