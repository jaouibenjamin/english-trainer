#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The teacher's page (teacher.html) in a real browser, against a stand-in Supabase on the project's address.

    python3 tests/teacher.py              # phone and laptop
    python3 tests/teacher.py --shots DIR  # also save PNGs

The page's own logic is tested without a browser in tests/teacher_check.mjs; this suite checks the wiring in Chrome:
the sign-in trip (to the project's /authorize and back with a code, PKCE checked by the stand-in), the screen behind
?tsb=1 (her class, the hard words, the health warning), a pupil's name that is HTML shown as text, nothing of the
session in storage, sign-out, and the back button after leaving the page. The Content-Security-Policy is bypassed here
only, because the stand-in answers on the project's address (tests/csp_check.py holds the page to its policy)."""
import asyncio, base64, hashlib, json, os, sys, urllib.parse
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, fails

SB, KEY = 'https://abcdefghijklmnop.supabase.co', 'public-key-for-tests-0123456789'
PAGE = f'http://127.0.0.1:{P.PORT}/teacher.html'
EVIL = '<img src=x onerror="window.__pwned=1">'
ROWS = {'teacher_view': [dict(display_name='פלונית', points=44, answers=4, error_pct=25, stars=3, locked_today=2, code_status='set', recovery_status='open', flags_week=0),
                         dict(display_name=None, points=0, answers=0, error_pct=0, stars=0, locked_today=0, code_status='set', recovery_status='open', flags_week=0),
                         dict(display_name=EVIL, points=10, answers=1, error_pct=0, stars=0, locked_today=0, code_status='waiting', recovery_status='closed', flags_week=1)],
        'teacher_items': [dict(item_key='hobby', tries=9, wrong=6, error_pct=67), dict(item_key='kick', tries=5, wrong=1, error_pct=20)],
        'backend_health': [dict(warn=True)]}
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': 'apikey, authorization, content-type', 'access-control-allow-methods': 'GET, POST, OPTIONS'}


def standin(log, slow=None):
    codes, live = {}, set()

    async def route(r):
        req = r.request; u = urllib.parse.urlparse(req.url); q = urllib.parse.parse_qs(u.query)
        if req.method == 'OPTIONS':
            return await r.fulfill(status=204, headers=CORS)
        log.append(dict(path=u.path + ('?' + u.query if u.query else ''), auth=req.headers.get('authorization', ''), apikey=req.headers.get('apikey', '')))
        if u.path == '/auth/v1/authorize':                     # Google said yes: back to the page with a code
            code = f'code-{len(codes) + 1}'
            codes[code] = dict(challenge=q['code_challenge'][0], method=q['code_challenge_method'][0], redirect=q['redirect_to'][0])
            return await r.fulfill(status=302, headers={'location': q['redirect_to'][0] + '?code=' + code})
        body = json.loads(req.post_data or 'null')
        if u.path == '/auth/v1/token' and q.get('grant_type') == ['pkce']:
            if slow and slow[0]:
                await asyncio.sleep(slow[0])
            c = codes.pop(body['auth_code'], None)
            ok = c and c['method'] == 's256' and base64.urlsafe_b64encode(hashlib.sha256(body['code_verifier'].encode()).digest()).rstrip(b'=').decode() == c['challenge']
            if not ok:
                return await r.fulfill(status=400, headers=CORS, json={'error': 'invalid_grant'})
            tok = f'acc-{len(log)}'; live.add(tok)
            return await r.fulfill(status=200, headers=CORS, json=dict(access_token=tok, refresh_token='ref-' + tok, expires_in=3600, user=dict(id='u1', email='teacher.one@example.org')))
        if u.path == '/auth/v1/logout':
            live.discard(req.headers.get('authorization', '').replace('Bearer ', ''))
            return await r.fulfill(status=204, headers=CORS)
        if u.path.startswith('/rest/v1/'):
            if req.headers.get('authorization', '').replace('Bearer ', '') not in live:
                return await r.fulfill(status=401, headers=CORS, json={'message': 'JWT expired'})
            return await r.fulfill(status=200, headers=CORS, json=ROWS.get(u.path[9:], []))
        return await r.fulfill(status=404, headers=CORS, body='')
    return route


async def run(b, w, h, tag):
    log, errs, slow = [], [], [0]
    c = await b.new_context(viewport={'width': w, 'height': h}, bypass_csp=True)
    await c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='text/javascript', body=f"window.API_URL='';window.BACKEND={{url:'{SB}',key:'{KEY}'}};"))
    await c.route(SB + '/**', standin(log, slow))
    # a request made while the page goes into the back-forward cache does not pass Playwright's routing (nor its request
    # events): the page's own calls are recorded instead, and such a request never reaches a real host (the browser has
    # no proxy here, and the project's made-up name resolves to nowhere). That the browser then delivers it is checked
    # on a real device (docs/PHASE3.md, step 4).
    await c.add_init_script("addEventListener('pageshow', e => { if (e.persisted) window.__restored = true });"
                            "window.__calls = []; const f = window.fetch; window.fetch = function (u, o) { window.__calls.push([String(u), !!(o && o.keepalive), document.visibilityState]); return f.apply(this, arguments) }")
    pg = await c.new_page()
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
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
    status = await pg.eval_on_selector_all('#class tbody tr', 'e=>e.map(r=>r.lastElementChild.textContent)')
    check(f'[{tag}] the status column: locks today, a code waiting, recovery closed, flagged', any('ננעל היום 2' in s for s in status) and any('מחכה לקוד חדש' in s and 'השחזור סגור' in s and 'לבדיקה' in s for s in status), status)
    hard = await pg.eval_on_selector_all('#hard li', 'e=>e.map(x=>x.textContent)')
    check(f'[{tag}] the hard words, hardest first', len(hard) == 2 and hard[0].startswith('hobby') and '6 טעויות מתוך 9' in hard[0], hard)
    check(f'[{tag}] the health warning shows', await pg.is_visible('#health'))
    rest = [x for x in log if x['path'].startswith('/rest/v1/')]
    check(f'[{tag}] every read went with her token and the publishable key, and only to her three views', len(rest) == 3 and all(x['auth'].startswith('Bearer acc-') and x['apikey'] == KEY for x in rest)
          and sorted(x['path'].split('?')[0] for x in rest) == ['/rest/v1/backend_health', '/rest/v1/teacher_items', '/rest/v1/teacher_view'], rest)
    store = await pg.evaluate('JSON.stringify([Object.keys(sessionStorage),Object.keys(localStorage)])')
    check(f'[{tag}] nothing of the session in storage (only the device switch)', json.loads(store) == [[], ['wi_tsb']], store)
    await P.shot(pg, f'teacher-{tag}')

    n0 = len(log)
    await pg.click('#out'); await pg.wait_for_selector('#in:not([hidden])'); await pg.wait_for_timeout(200)
    out = next((i for i in range(n0, len(log)) if log[i]['path'] == '/auth/v1/logout?scope=local'), None)
    # a read still on its way may land after the revoke: what matters is that the revoke went out and nothing used
    # her token after it (re-review of #83)
    check(f'[{tag}] sign-out: the screen is emptied at once and the session revoked; nothing uses her token after', await pg.is_hidden('#screen') and await pg.locator('#class tbody tr').count() == 0
          and out is not None and log[out]['auth'].startswith('Bearer acc-') and not any(x['auth'] == log[out]['auth'] for x in log[out + 1:]), log[n0:])

    await pg.click('#in'); await pg.wait_for_selector('#class tbody tr')
    n = len(log)
    # the page's own pagehide handler, fired as the browser fires it when the page is left. (On a real navigation the
    # revoke goes out with keepalive from the unloading page, which the browser sends by itself: Playwright neither
    # routes nor reports it, so it is checked through the event here and on a real device in docs/LIVE_STAGE.md.)
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

    slow[0] = 1.5                                                    # slow wifi: the code exchange takes a while
    await pg.goto(PAGE); await pg.wait_for_selector('#in:not([hidden])'); await pg.click('#in')
    await pg.wait_for_function("document.querySelector('#msg')?.textContent==='מתחברים…'")
    check(f'[{tag}] back from Google on slow wifi: "signing in…" and no button to tap again until the exchange answers', await pg.is_hidden('#in') and await pg.is_hidden('#out'))
    await pg.wait_for_selector('#out:not([hidden])'); slow[0] = 0
    await pg.click('#out'); await pg.wait_for_selector('#in:not([hidden])')
    await pg.goto(PAGE + '?tsb=0'); await pg.wait_for_selector('#in:not([hidden])')
    await pg.click('#in'); await pg.wait_for_selector('#out:not([hidden])'); await pg.wait_for_timeout(300)
    check(f'[{tag}] without the switch (?tsb=0) there is no screen after sign-in', await pg.is_hidden('#screen') and await pg.locator('#class tbody tr').count() == 0)
    errs = [e for e in errs if 'ERR_NAME_NOT_RESOLVED' not in e]   # that keepalive revoke, to the stand-in's made-up host
    check(f'[{tag}] no error in the console', not errs, errs[:3])
    await c.close()
    await sleeping_laptop(b, w, h, tag)


async def sleeping_laptop(b, w, h, tag):
    """A laptop that slept 31 minutes with the page in front: no tap, no visibility event, its timers did not run while it
    slept. The page's own 30-second check must sign her out and empty the screen (re-review of #82). Playwright's clock
    moves Date by 31 minutes without firing any timer, then runs 31 seconds of timers."""
    log = []
    c = await b.new_context(viewport={'width': w, 'height': h}, bypass_csp=True)
    await c.route('**/config.js', lambda r: r.fulfill(status=200, content_type='text/javascript', body=f"window.API_URL='';window.BACKEND={{url:'{SB}',key:'{KEY}'}};"))
    await c.route(SB + '/**', standin(log))
    pg = await c.new_page()
    await pg.clock.install()
    await pg.goto(PAGE + '?tsb=1'); await pg.wait_for_selector('#in:not([hidden])')
    await pg.click('#in'); await pg.wait_for_selector('#class tbody tr')
    await pg.clock.set_system_time(await pg.evaluate('Date.now()') + 31 * 60000)
    await pg.clock.run_for(31000); await pg.wait_for_timeout(300)
    check(f'[{tag}] a laptop that woke after 31 minutes: signed out by the 30-second check, nothing of her class on the screen, no tap needed',
          await pg.is_visible('#in') and await pg.locator('#class tbody tr').count() == 0 and any(x['path'] == '/auth/v1/logout?scope=local' for x in log), [x['path'] for x in log[-2:]])
    await c.close()


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
