#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The teacher's page (teacher.html) in a real browser, against a stand-in Supabase on the project's address.

    python3 tests/teacher.py              # phone and laptop
    python3 tests/teacher.py --shots DIR  # also save PNGs

The page's own logic is tested without a browser in tests/teacher_check.mjs; this suite checks the wiring in Chrome:
the sign-in trip (to the project's /authorize and back with a code, PKCE checked by the stand-in), the screen behind
?tsb=1 (her class, the hard words, the health warning), a pupil's name that is HTML shown as text, nothing of the
session in storage, sign-out, and the back button after leaving the page. Step 3, her actions: each asked first
(cancel sends nothing), a new code shown once (six digits, in no storage, address or console, wiped on close, sign-out
and leaving), unlock and its daily limit, unlock the class, the class list (add, a name already there, remove), a
refusal from the server, one action at a time, and an answer that comes back after she signed out (dropped). The Content-Security-Policy is bypassed here
only, because the stand-in answers on the project's address (tests/csp_check.py holds the page to its policy)."""
import asyncio, base64, hashlib, json, os, sys, urllib.parse
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, fails

SB, KEY = 'https://abcdefghijklmnop.supabase.co', 'public-key-for-tests-0123456789'
PAGE = f'http://127.0.0.1:{P.PORT}/teacher.html'
EVIL = '<img src=x onerror="window.__pwned=1">'
C1, P1, P2, P3 = '11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222', '33333333-3333-4333-8333-333333333333', '44444444-4444-4444-8444-444444444444'
OTC = '482913'
ROWS = {'teacher_view': [dict(pupil_id=P1, class_id=C1, display_name='פלונית', points=44, answers=4, error_pct=25, stars=3, locked_today=2, code_status='set', recovery_status='open', flags_week=0),
                         dict(pupil_id=P3, class_id=C1, display_name=None, points=0, answers=0, error_pct=0, stars=0, locked_today=0, code_status='set', recovery_status='open', flags_week=0),
                         dict(pupil_id=P2, class_id=C1, display_name=EVIL, points=10, answers=1, error_pct=0, stars=0, locked_today=0, code_status='waiting', recovery_status='closed', flags_week=1)],
        'classes': [dict(id=C1, name='ה׳1')],
        'teacher_items': [dict(item_key='hobby', tries=9, wrong=6, error_pct=67), dict(item_key='kick', tries=5, wrong=1, error_pct=20)],
        'backend_health': [dict(warn=True, resets_day=2, resets_cap=15)]}
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': 'apikey, authorization, content-type, prefer', 'access-control-allow-methods': 'GET, POST, DELETE, OPTIONS'}


def standin(log, st):
    codes, live = {}, set()
    roster = [dict(class_id=C1, name_key='פלונית', display_name='פלונית'), dict(class_id=C1, name_key='<b>x</b>', display_name=EVIL)]

    async def route(r):
        req = r.request; u = urllib.parse.urlparse(req.url); q = urllib.parse.parse_qs(u.query)
        if req.method == 'OPTIONS':
            return await r.fulfill(status=204, headers=CORS)
        log.append(dict(path=u.path + ('?' + u.query if u.query else ''), method=req.method, auth=req.headers.get('authorization', ''), apikey=req.headers.get('apikey', ''),
                        prefer=req.headers.get('prefer', ''), body=req.post_data))
        if u.path == '/auth/v1/authorize':                     # Google said yes: back to the page with a code
            code = f'code-{len(codes) + 1}'
            codes[code] = dict(challenge=q['code_challenge'][0], method=q['code_challenge_method'][0], redirect=q['redirect_to'][0])
            return await r.fulfill(status=302, headers={'location': q['redirect_to'][0] + '?code=' + code})
        body = json.loads(req.post_data or 'null')
        if u.path == '/auth/v1/token' and q.get('grant_type') == ['pkce']:
            if st.get('slow'):
                await asyncio.sleep(st['slow'])
            c = codes.pop(body['auth_code'], None)
            ok = c and c['method'] == 's256' and base64.urlsafe_b64encode(hashlib.sha256(body['code_verifier'].encode()).digest()).rstrip(b'=').decode() == c['challenge']
            if not ok:
                return await r.fulfill(status=400, headers=CORS, json={'error': 'invalid_grant'})
            tok = f'acc-{len(log)}'; live.add(tok)
            return await r.fulfill(status=200, headers=CORS, json=dict(access_token=tok, refresh_token='ref-' + tok, expires_in=3600, user=dict(id='u1', email='teacher.one@example.org')))
        if u.path == '/auth/v1/logout':
            live.discard(req.headers.get('authorization', '').replace('Bearer ', ''))
            return await r.fulfill(status=204, headers=CORS)
        if u.path.startswith('/rest/v1/') or u.path.startswith('/functions/v1/'):
            if req.headers.get('authorization', '').replace('Bearer ', '') not in live:
                return await r.fulfill(status=401, headers=CORS, json={'message': 'JWT expired'})
        if u.path == '/functions/v1/teacher-reset':             # the Edge Function: her pupil or her class, re-checked there
            if st.get('delay'):
                await asyncio.sleep(st['delay'])
            a, rep_ = body.get('action'), st.get('reply')
            if rep_:
                return await r.fulfill(status=200, headers=CORS, json=rep_)
            if a == 'reset' and body.get('pupil_id') in (P1, P2):
                return await r.fulfill(status=200, headers=CORS, json=dict(ok=True, otc=OTC, expires_at='2026-11-26T15:00:00Z', name='פלונית' if body['pupil_id'] == P1 else EVIL))
            if a == 'unlock' and body.get('pupil_id') in (P1, P2):
                st['unlocks'] = st.get('unlocks', 0) + 1
                return await r.fulfill(status=200, headers=CORS, json=dict(ok=True) if st['unlocks'] <= 2 else dict(ok=False, e='limit'))
            if a == 'unlock_class' and body.get('class_id') == C1:
                return await r.fulfill(status=200, headers=CORS, json=dict(ok=True))
            return await r.fulfill(status=200, headers=CORS, json=dict(ok=False, e='forbidden'))
        if u.path == '/rest/v1/roster' and req.method == 'POST':  # the database's rules: her class, the key, no repeat
            if body.get('class_id') != C1 or body.get('name_key') != ' '.join(body.get('display_name', '').split()).lower():
                return await r.fulfill(status=403 if body.get('class_id') != C1 else 400, headers=CORS, json={'code': '42501'})
            if any(x['name_key'] == body['name_key'] for x in roster):
                return await r.fulfill(status=409, headers=CORS, json={'code': '23505'})
            roster.append(dict(class_id=C1, name_key=body['name_key'], display_name=body['display_name']))
            return await r.fulfill(status=201, headers=CORS, body='')
        if u.path == '/rest/v1/roster' and req.method == 'DELETE':
            k = (q.get('name_key') or [''])[0]
            gone = [x for x in roster if q.get('class_id') == ['eq.' + x['class_id']] and k == 'eq.' + x['name_key']]
            for x in gone:
                roster.remove(x)
            return await r.fulfill(status=200, headers=CORS, json=gone)
        if u.path == '/rest/v1/roster':
            return await r.fulfill(status=200, headers=CORS, json=roster)
        if u.path.startswith('/rest/v1/'):
            return await r.fulfill(status=200, headers=CORS, json=ROWS.get(u.path[9:], []))
        return await r.fulfill(status=404, headers=CORS, body='')
    return route


async def run(b, w, h, tag):
    log, errs, said, st = [], [], [], {}
    c = await b.new_context(viewport={'width': w, 'height': h}, bypass_csp=True)
    await c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='text/javascript', body=f"window.API_URL='';window.BACKEND={{url:'{SB}',key:'{KEY}'}};"))
    await c.route(SB + '/**', standin(log, st))
    # a request made while the page goes into the back-forward cache does not pass Playwright's routing (nor its request
    # events): the page's own calls are recorded instead, and such a request never reaches a real host (the browser has
    # no proxy here, and the project's made-up name resolves to nowhere). That the browser then delivers it is checked
    # on a real device (docs/PHASE3.md, step 4).
    await c.add_init_script("addEventListener('pageshow', e => { if (e.persisted) window.__restored = true });"
                            "window.__calls = []; const f = window.fetch; window.fetch = function (u, o) { window.__calls.push([String(u), !!(o && o.keepalive), document.visibilityState]); return f.apply(this, arguments) }")
    pg = await c.new_page()
    pg.on('console', lambda m: (said.append(m.text), errs.append(m.text) if m.type == 'error' else None))
    pg.on('pageerror', lambda e: errs.append(str(e)))

    await pg.goto(PAGE + '?tsb=1'); await pg.wait_for_selector('#in:not([hidden])')
    check(f'[{tag}] signed out: the sign-in button only, no screen', await pg.is_hidden('#out') and await pg.is_hidden('#screen'))
    await pg.click('#in')
    await pg.wait_for_selector('#out:not([hidden])'); await pg.wait_for_selector('#class tbody tr')
    auth = next((x for x in log if x['path'].startswith('/auth/v1/authorize')), None)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(auth['path']).query) if auth else {}
    check(f'[{tag}] the sign-in went to the project for Google, with PKCE, back to this page only', q.get('provider') == ['google'] and q.get('code_challenge_method') == ['s256'] and q.get('redirect_to') == [PAGE], q)
    check(f'[{tag}] back on the page: signed in, and the code is gone from the address bar', await pg.text_content('#who') == 'teacher.one@example.org' and '?code' not in pg.url and pg.url == PAGE, pg.url)
    names = await pg.eval_on_selector_all('#class tbody td.name', 'e=>e.map(x=>x.textContent)')
    check(f'[{tag}] the screen: her class, a missing name empty (never "null")', set(names) == {'פלונית', EVIL, ''} and 'null' not in names, names)
    check(f'[{tag}] a name that is HTML is shown as text: no element made of it, nothing ran', await pg.evaluate('window.__pwned') is None and await pg.locator('#class img').count() == 0)
    status = await pg.eval_on_selector_all('#class tbody tr', 'e=>e.map(r=>r.cells[5].textContent)')
    check(f'[{tag}] the status column: locks today, a code waiting, recovery closed, flagged', any('ננעל היום 2' in s for s in status) and any('מחכה לקוד חדש' in s and 'השחזור סגור' in s and 'לבדיקה' in s for s in status), status)
    hard = await pg.eval_on_selector_all('#hard li', 'e=>e.map(x=>x.textContent)')
    check(f'[{tag}] the hard words, hardest first', len(hard) == 2 and hard[0].startswith('hobby') and '6 טעויות מתוך 9' in hard[0], hard)
    check(f'[{tag}] the health warning shows', await pg.is_visible('#health'))
    rest = [x for x in log if x['path'].startswith('/rest/v1/')]
    check(f'[{tag}] every read went with her token and the publishable key, and only to her views and her class list', len(rest) == 5 and all(x['auth'].startswith('Bearer acc-') and x['apikey'] == KEY and x['method'] == 'GET' for x in rest)
          and sorted(x['path'].split('?')[0] for x in rest) == ['/rest/v1/backend_health', '/rest/v1/classes', '/rest/v1/roster', '/rest/v1/teacher_items', '/rest/v1/teacher_view'], rest)
    check(f'[{tag}] the class list: her names, the HTML one as text', await pg.eval_on_selector_all('#roster li span', 'e=>e.map(x=>x.textContent)') == sorted(['פלונית', EVIL], key=lambda x: x) or
          set(await pg.eval_on_selector_all('#roster li span', 'e=>e.map(x=>x.textContent)')) == {'פלונית', EVIL}) 
    store = await pg.evaluate('JSON.stringify([Object.keys(sessionStorage),Object.keys(localStorage)])')
    check(f'[{tag}] nothing of the session in storage (only the device switch)', json.loads(store) == [[], ['wi_tsb']], store)
    await P.shot(pg, f'teacher-{tag}')
    await actions(pg, tag, log, said, st)

    await pg.click('#out'); await pg.wait_for_selector('#in:not([hidden])')
    check(f'[{tag}] sign-out: the screen is emptied at once and the session revoked', await pg.is_hidden('#screen') and await pg.locator('#class tbody tr').count() == 0
          and log[-1]['path'] == '/auth/v1/logout?scope=local' and log[-1]['auth'].startswith('Bearer acc-'), log[-1])

    await pg.click('#in'); await pg.wait_for_selector('#class tbody tr')
    n = len(log)
    # the page's own pagehide handler, fired as the browser fires it when the page is left. (On a real navigation the
    # revoke goes out with keepalive from the unloading page, which the browser sends by itself: Playwright neither
    # routes nor reports it, so it is checked through the event here, and on a real device with the teacher at step 4 of docs/PHASE3.md.)
    await pg.evaluate("dispatchEvent(new PageTransitionEvent('pagehide',{persisted:false}))"); await pg.wait_for_timeout(300)
    check(f'[{tag}] leaving the page (pagehide): the screen is emptied and her session revoked', await pg.is_hidden('#screen') and await pg.locator('#class tbody tr').count() == 0
          and any(x['path'] == '/auth/v1/logout?scope=local' for x in log[n:]), log[n:])
    await pg.click('#in'); await pg.wait_for_selector('#class tbody tr')
    m = await pg.evaluate('window.__calls.length')
    await pg.goto(f'http://127.0.0.1:{P.PORT}/index.html'); await pg.wait_for_timeout(300)        # a real navigation to the game
    await pg.go_back(wait_until='commit'); await pg.wait_for_selector('#in:not([hidden])')   # from the cache: no load event
    cached = await pg.evaluate('window.__restored === true')
    check(f'[{tag}] the back button brings the page back from the back-forward cache (the browser runs with it on)', cached)
    check(f'[{tag}] the back button: nobody signed in, nothing of her class on the screen', await pg.is_hidden('#out') and await pg.locator('#class tbody tr').count() == 0 and await pg.text_content('#who') == '')
    calls = json.loads(await pg.evaluate('JSON.stringify(window.__calls.slice(m))'.replace('m', str(m))))
    check(f'[{tag}] and the page revoked her session as it went into the cache (logout, keepalive), and asked nothing else', calls == [[SB + '/auth/v1/logout?scope=local', True, 'visible']], calls)

    st['slow'] = 1.5                                                    # slow wifi: the code exchange takes a while
    await pg.goto(PAGE); await pg.wait_for_selector('#in:not([hidden])'); await pg.click('#in')
    await pg.wait_for_function("document.querySelector('#msg').textContent==='מתחברים…'")
    check(f'[{tag}] back from Google on slow wifi: "signing in…" and no button to tap again until the exchange answers', await pg.is_hidden('#in') and await pg.is_hidden('#out'))
    await pg.wait_for_selector('#out:not([hidden])'); st['slow'] = 0
    await pg.click('#out'); await pg.wait_for_selector('#in:not([hidden])')
    await pg.goto(PAGE + '?tsb=0'); await pg.wait_for_selector('#in:not([hidden])')
    await pg.click('#in'); await pg.wait_for_selector('#out:not([hidden])'); await pg.wait_for_timeout(300)
    check(f'[{tag}] without the switch (?tsb=0) there is no screen after sign-in', await pg.is_hidden('#screen') and await pg.locator('#class tbody tr').count() == 0)
    errs = [e for e in errs if 'status of 409' not in e]     # the browser's own line for the stand-in's "already on the list"
    errs = [e for e in errs if 'ERR_NAME_NOT_RESOLVED' not in e]   # that keepalive revoke, to the stand-in's made-up host
    check(f'[{tag}] no error in the console', not errs, errs[:3])
    await c.close()


async def traces(pg):
    """Where else the code could still be read after it is wiped: the page's RegExp statics (RegExp.$_, lastMatch: what a
    regexp last ran on, readable from the console) and the whole JavaScript heap after a garbage collection (what any
    variable, closure or answer object still holds). Returns the places where OTC is found."""
    found = []
    if OTC in await pg.evaluate('String(RegExp.$_) + "|" + String(RegExp.lastMatch) + "|" + String(RegExp.input)'):
        found.append('RegExp statics')
    cdp = await pg.context.new_cdp_session(pg); chunks = []
    cdp.on('HeapProfiler.addHeapSnapshotChunk', lambda e: chunks.append(e['chunk']))
    await cdp.send('HeapProfiler.enable'); await cdp.send('HeapProfiler.collectGarbage')
    await cdp.send('HeapProfiler.takeHeapSnapshot', {'reportProgress': False}); await cdp.detach()
    if OTC in json.loads(''.join(chunks))['strings']:
        found.append('the heap')
    return found


def fn_calls(log, n):
    return [dict(x, body=json.loads(x['body'] or 'null')) for x in log[n:] if x['path'] == '/functions/v1/teacher-reset']


async def row_button(pg, name, label):
    return pg.locator('#class tbody tr', has=pg.locator('td.name', has_text=name)).get_by_role('button', name=label)


async def answer(pg, yes):
    await pg.wait_for_selector('#ask[open]')
    await pg.click('#ask-yes' if yes else '#ask-no')
    await pg.wait_for_selector('#ask:not([open])', state='attached')


async def actions(pg, tag, log, said, st):
    n = len(log)
    await (await row_button(pg, 'פלונית', 'קוד חדש')).click()
    check(f'[{tag}] a new code is asked first, with her pupil\'s name in the question', 'לתת לפלונית קוד חדש' in await pg.text_content('#ask-text'))
    await answer(pg, False); await pg.wait_for_timeout(200)
    check(f'[{tag}] cancel sends nothing', fn_calls(log, n) == [] and not await pg.is_visible('#code'))

    await (await row_button(pg, 'פלונית', 'קוד חדש')).click(); await answer(pg, True)
    await pg.wait_for_selector('#code[open]')
    calls = fn_calls(log, n)
    check(f'[{tag}] reset: one call to teacher-reset, her token, this pupil only', len(calls) == 1 and calls[0]['method'] == 'POST' and calls[0]['auth'].startswith('Bearer acc-')
          and calls[0]['body'] == dict(action='reset', pupil_id=P1), calls)
    check(f'[{tag}] while it is shown, the code is not in the RegExp statics (checked without a regexp)', 'RegExp statics' not in await traces(pg))
    check(f'[{tag}] the new code is shown, once, in big digits, with the name', await pg.text_content('#code-digits') == '482 913' and 'פלונית' in await pg.text_content('#code-name'))
    store = await pg.evaluate('JSON.stringify([sessionStorage,localStorage,location.href,history.length])')
    check(f'[{tag}] the code is in no storage and not in the address bar', OTC not in store and '482' not in pg.url, store)
    await P.shot(pg, f'teacher-code-{tag}')
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
    check(f'[{tag}] Escape does not hide the code by accident', await pg.text_content('#code-digits') == '482 913')
    await pg.click('#code-done')
    check(f'[{tag}] "written down": the code is wiped from the page', not await pg.is_visible('#code') and OTC not in await pg.content() and await pg.text_content('#code-digits') == '')
    check(f'[{tag}] and from everything else: not in the RegExp statics, not anywhere in the heap', await traces(pg) == [], await traces(pg))
    # S8: the 10 minutes are counted by the clock: a laptop that slept 11 minutes hides it at the first tap
    await (await row_button(pg, 'פלונית', 'קוד חדש')).click(); await answer(pg, True); await pg.wait_for_selector('#code[open]')
    await pg.evaluate("window.__now=Date.now; Date.now=()=>window.__now()+11*60000")
    await pg.mouse.click(5, 5)
    await pg.wait_for_selector('#code', state='hidden')
    check(f'[{tag}] the code is hidden at the first tap after 11 minutes asleep (the clock, not only a timer)', await pg.text_content('#code-digits') == '')
    await pg.evaluate("Date.now=window.__now")

    n = len(log)
    await (await row_button(pg, 'פלונית', 'שחרור נעילה')).click(); await answer(pg, True)
    await pg.wait_for_function("document.querySelector('#act').textContent.includes('שוחררה')")
    check(f'[{tag}] unlock: her pupil, the screen says so', [c['body'] for c in fn_calls(log, n)] == [dict(action='unlock', pupil_id=P1)])
    check(f'[{tag}] an HTML name has no unlock button (not locked) but its own reset', await (await row_button(pg, 'img', 'שחרור נעילה')).count() == 0 and await (await row_button(pg, 'img', 'קוד חדש')).count() == 1)
    st['unlocks'] = 2
    await (await row_button(pg, 'פלונית', 'שחרור נעילה')).click(); await answer(pg, True)
    await pg.wait_for_function("document.querySelector('#act').textContent.includes('פעמיים')")
    check(f'[{tag}] unlock a third time: the server\'s daily limit is told plainly', 'אפשר לתת קוד חדש' in await pg.text_content('#act'))

    n = len(log)
    await pg.get_by_role('button', name='שחרור נעילות לכל הכיתה').click()
    check(f'[{tag}] unlock the class is asked first, with the class name', 'ה׳1' in await pg.text_content('#ask-text'))
    await answer(pg, True); await pg.wait_for_function("document.querySelector('#act').textContent.includes('שוחררו')")
    check(f'[{tag}] unlock the class: her class only', [c['body'] for c in fn_calls(log, n)] == [dict(action='unlock_class', class_id=C1)])

    n = len(log)
    await pg.fill(f'#add-{C1}', '  Dana   Lee ')
    await pg.get_by_role('button', name='הוספה לרשימה').click(); await answer(pg, True)
    await pg.wait_for_function("[...document.querySelectorAll('#roster li span')].some(x=>x.textContent==='Dana Lee')")
    adds = [x for x in log[n:] if x['path'] == '/rest/v1/roster' and x['method'] == 'POST']
    check(f'[{tag}] add a name: trimmed, spaces squeezed, the key the database computes, her class', len(adds) == 1 and json.loads(adds[0]['body']) == dict(class_id=C1, name_key='dana lee', display_name='Dana Lee')
          and adds[0]['auth'].startswith('Bearer acc-'), adds)
    check(f'[{tag}] the field is emptied after the add', await pg.input_value(f'#add-{C1}') == '')
    await pg.fill(f'#add-{C1}', 'dana lee')
    await pg.get_by_role('button', name='הוספה לרשימה').click(); await answer(pg, True)
    await pg.wait_for_function("document.querySelector('#act').textContent.includes('כבר ברשימה')")
    check(f'[{tag}] a name already on the list: said so, nothing doubled', [x.lower() for x in await pg.eval_on_selector_all('#roster li span', 'e=>e.map(x=>x.textContent)')].count('dana lee') == 1)

    n = len(log)
    await pg.locator('#roster li', has=pg.locator('span', has_text='Dana Lee')).get_by_role('button', name='הסרה').click()
    check(f'[{tag}] remove is asked first', 'להסיר את "Dana Lee"' in await pg.text_content('#ask-text'))
    await answer(pg, True); await pg.wait_for_function("document.querySelector('#act').textContent.includes('הוסר')")
    await pg.wait_for_function("![...document.querySelectorAll('#roster li span')].some(x=>x.textContent==='Dana Lee')")
    dels = [x for x in log[n:] if x['method'] == 'DELETE']
    check(f'[{tag}] remove: one DELETE of exactly that name in that class, the rows asked back', len(dels) == 1 and dels[0]['path'] == f'/rest/v1/roster?class_id=eq.{C1}&name_key=eq.dana%20lee'
          and dels[0]['prefer'] == 'return=representation' and 'Dana Lee' not in await pg.eval_on_selector_all('#roster li span', 'e=>e.map(x=>x.textContent)'), dels)

    st['reply'] = dict(ok=False, e='limit')
    await (await row_button(pg, 'פלונית', 'קוד חדש')).click(); await answer(pg, True)
    await pg.wait_for_function("document.querySelector('#act').textContent.includes('24 שעות')")
    check(f'[{tag}] S7: her daily cap of new codes is told plainly, and the screen shows how many she made', not await pg.is_visible('#code') and '2 מתוך 15' in await pg.text_content('#quota'))
    st['reply'] = dict(ok=False, e='forbidden')
    await (await row_button(pg, 'פלונית', 'קוד חדש')).click(); await answer(pg, True)
    await pg.wait_for_function("document.querySelector('#act').textContent.includes('לא אושרה')")
    check(f'[{tag}] the server refuses: said so, no code shown', not await pg.is_visible('#code'))
    st.pop('reply')

    st['delay'] = 1.0; n = len(log)
    await (await row_button(pg, 'פלונית', 'קוד חדש')).click(); await answer(pg, True)
    await pg.wait_for_timeout(200)
    check(f'[{tag}] one action at a time: every action button waits', await pg.evaluate("[...document.querySelectorAll('button.act')].every(b=>b.disabled)"))
    await pg.click('#out'); await pg.wait_for_timeout(1300)
    check(f'[{tag}] a code that comes back after she signed out is never shown', len(fn_calls(log, n)) == 1 and not await pg.is_visible('#code') and await pg.text_content('#code-digits') == '')
    st.pop('delay')
    await pg.click('#in'); await pg.wait_for_selector('#class tbody tr')              # the next teacher at this computer
    check(f'[{tag}] S9: once the next teacher is signed in, that late code is nowhere: not in the RegExp statics, not in the heap', await traces(pg) == [], await traces(pg))
    await pg.click('#out'); await pg.wait_for_selector('#in:not([hidden])')

    await pg.click('#in'); await pg.wait_for_selector('#class tbody tr')
    await (await row_button(pg, 'פלונית', 'קוד חדש')).click(); await answer(pg, True); await pg.wait_for_selector('#code[open]')
    await pg.evaluate("dispatchEvent(new PageTransitionEvent('pagehide',{persisted:false}))"); await pg.wait_for_timeout(300)
    check(f'[{tag}] leaving the page with a code on the screen: wiped', not await pg.is_visible('#code') and await pg.text_content('#code-digits') == '')
    check(f'[{tag}] and nowhere else either (RegExp statics, heap)', await traces(pg) == [], await traces(pg))
    check(f'[{tag}] the code was never written to the console', not any(OTC in m for m in said), [m for m in said if OTC in m])
    await pg.click('#in'); await pg.wait_for_selector('#class tbody tr')


async def main():
    procs = P.start_servers()
    try:
        async with async_playwright() as p:
            # the browser of the other suites, with the back-forward cache ON (Playwright turns it off by default): the
            # back button must find a page that let her go, not one frozen with her session (review of #82, B1)
            b = await p.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--no-proxy-server', '--host-resolver-rules=MAP abcdefghijklmnop.supabase.co ~NOTFOUND'], ignore_default_args=['--disable-back-forward-cache'])
            await run(b, 390, 844, 'phone')
            await run(b, 1366, 768, 'laptop')
            await b.close()
    finally:
        for x in procs: x.terminate()
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    if '--shots' in sys.argv:
        P.SHOTS = sys.argv[sys.argv.index('--shots') + 1]
    asyncio.run(main())
