#!/usr/bin/env python3
"""Mock exam results on the teacher screen, behind their switch (?tmock=1), against the mock backend.

    python3 tests/teacher_mock.py              # phone and laptop
    python3 tests/teacher_mock.py --shots DIR  # also save PNGs

Checks: without the switch the screen is as before; with it each pupil's card shows the papers taken, the last and
the first result and the last paper by skill; a backend that does not send the new field yet (an older deployment)
draws the cards as before; nothing a backend sends is drawn as text; and looking at the screen changes nothing in a
pupil's record."""
import asyncio, json, os, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, port_open, fails

CLASS, TEACHER = 'EN-1234', '654321'      # the mock backend's own test values
TRY1 = {'at': 1000, 'total': [9, 20], 'sc': {'words': [3, 5], 'grammar': [2, 5], 'reading': [2, 5], 'writing': [2, 5]}, 'miss': ['a:1'], 'wrong': [['a:1', 'zzz']]}
TRY2 = {'at': 2000, 'total': [15, 20], 'sc': {'words': [5, 5], 'grammar': [4, 5], 'reading': [3, 5], 'writing': [3, 5]}, 'miss': [], 'wrong': []}
PUPILS = {'אביגיל': [TRY1, TRY2], 'בארי': [], 'גילי': [TRY1]}
POST = "async ([api,d])=>(await fetch(api,{method:'POST',body:JSON.stringify(d)})).json()"
CARDS = """(()=>Object.fromEntries([...document.querySelectorAll('.kid')].map(k=>[k.querySelector('.kn b').textContent,{km:[...k.querySelectorAll('.km')].map(p=>p.innerText.replace(/\\s+/g,' ').trim()),rows:k.querySelectorAll('p').length,wide:k.scrollWidth>k.clientWidth+1}])))()"""


def servers():
    if hasattr(P, 'start_servers'):      # each run on its own free ports
        return P.start_servers(mock=True)
    procs = []
    if not port_open(P.PORT):
        procs.append(subprocess.Popen([sys.executable, '-m', 'http.server', str(P.PORT), '--bind', '127.0.0.1'], cwd=P.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    if not port_open(P.API_PORT):
        procs.append(subprocess.Popen(['node', P.MOCK], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for _ in range(60):
        if port_open(P.PORT) and port_open(P.API_PORT): break
        time.sleep(.1)
    return procs


async def sign_in(pg, query=''):
    await pg.wait_for_load_state('networkidle'); await pg.goto('about:blank'); await pg.goto(P.BASE + query + '#teacher'); await pg.wait_for_selector('#tt')      # a fresh page each time: the teacher code is not kept
    await pg.fill('#tc', CLASS); await pg.fill('#tt', TEACHER); await pg.click('[data-a=tlogin]')
    try:
        await pg.wait_for_selector('.kid', timeout=8000)
    except Exception:
        raise SystemExit('the teacher screen did not open: ' + (await pg.inner_text('#view'))[:200])


async def run(b, w, h, errs, api, first):
    tag = f'{w}x{h}'
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    bodies = []
    pg.on('request', lambda r: bodies.append(r.post_data or '') if r.url.startswith(api) else None)
    await pg.goto(P.BASE); await pg.wait_for_selector('#lc')
    if first:
        for name, tries in PUPILS.items():
            r = await pg.evaluate(POST, [api, {'a': 'register', 'c': CLASS, 'n': name, 'p': '2468'}])
            s = {'pts': 50, 'day': '2026-11-20', 'streak': 1, 'k': {'words': 5, 'reads': 1}, 'g': {'st': {'1-sling': 3}}, 'x': {'tries': tries, 'prac': {}, 'seen': []}}
            r2 = await pg.evaluate(POST, [api, {'a': 'save', 'c': CLASS, 'n': name, 'p': '2468', 's': s}])
            check(f'pupil {list(PUPILS).index(name) + 1} is on the mock backend with {len(tries)} mock papers', (r.get('ok') or r.get('e') == 'taken') and r2.get('ok'), [r, r2])
    before = await pg.evaluate(POST, [api, {'a': 'login', 'c': CLASS, 'n': 'אביגיל', 'p': '2468'}])

    # ---- switch off ----
    await sign_in(pg)
    cards = await pg.evaluate(CARDS)
    check(f'[{tag}] off: the cards show nothing about the mock exam', all(not v['km'] for v in cards.values()) and all(n in cards for n in PUPILS), list(cards))
    rows_off = {n: cards[n]['rows'] for n in PUPILS}

    # ---- switch on ----
    await sign_in(pg, '?tmock=1')
    cards = await pg.evaluate(CARDS)
    a, bb, g = cards['אביגיל']['km'], cards['בארי']['km'], cards['גילי']['km']
    check(f'[{tag}] on: two papers show the count, the last and the first result', len(a) == 2 and '2 ניסיונות' in a[0] and 'אחרון 15 / 20' in a[0] and 'ראשון 9 / 20' in a[0], a)
    check(f'[{tag}] on: and the last paper by skill, in the exam\'s order', len(a) == 2 and a[1] == 'מילים 5 / 5 דקדוק 4 / 5 קריאה 3 / 5 כתיבה 3 / 5', a)
    check(f'[{tag}] on: a pupil without a paper is marked "not yet"', bb == ['מבחן דמו: עוד לא ניסה/תה'], bb)
    check(f'[{tag}] on: one paper shows no "first" result', len(g) == 2 and 'ניסיון אחד' in g[0] and 'אחרון 9 / 20' in g[0] and 'ראשון' not in g[0], g)
    check(f'[{tag}] on: no card is wider than its box', not any(v['wide'] for v in cards.values()))
    text = await pg.inner_text('.kids')
    check(f'[{tag}] on: what a pupil typed in the exam is not on the screen', 'zzz' not in text and 'a:1' not in text)
    if P.SHOTS:
        os.makedirs(P.SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(P.SHOTS, f'teacher-mock-{tag}.png'), full_page=False)
        await pg.locator('.kid', has_text='אביגיל').screenshot(path=os.path.join(P.SHOTS, f'teacher-mock-card-{tag}.png'))

    # ---- an older deployment: the backend sends no "mock" field ----
    async def old(route):
        r = await route.fetch(); d = await r.json()
        if isinstance(d.get('kids'), list):
            for k in d['kids']: k.pop('mock', None)
        await route.fulfill(content_type='application/json', body=json.dumps(d))
    await pg.route(api, old)
    await sign_in(pg)
    cards = await pg.evaluate(CARDS)
    check(f'[{tag}] an older backend (no mock field): the cards are drawn as before, with no mock rows and no error', all(not cards[n]['km'] for n in PUPILS) and {n: cards[n]['rows'] for n in PUPILS} == rows_off, cards)
    await pg.unroute(api)

    # ---- a backend that sends rubbish: nothing of it is drawn ----
    async def hostile(route):
        r = await route.fetch(); d = await r.json()
        bad = [{'n': '<img src=x onerror="window.__pwned=1">', 'last': ['<b>9</b>', 20], 'first': [1, 2], 'sc': {'words': ['<i>', 5]}},
               {'n': 2, 'last': [25, 20], 'first': [-1, 20], 'sc': {'words': [5, 5], 'grammar': [1e9, 5], 'evil': [1, 1]}},
               'text']
        for i, k in enumerate(d.get('kids', [])[:3]): k['mock'] = bad[i]
        await route.fulfill(content_type='application/json', body=json.dumps(d))
    await pg.route(api, hostile)
    await sign_in(pg)
    R = await pg.evaluate("({pwned:!!window.__pwned,tags:document.querySelectorAll('.kid .km img,.kid .km b:not(:first-child) *,.kid .km i').length,html:[...document.querySelectorAll('.kid .km')].map(p=>p.innerText.replace(/\\s+/g,' ').trim())})")
    check(f'[{tag}] rubbish from a backend is never drawn: no markup, no impossible number, only checked values',
          not R['pwned'] and R['tags'] == 0 and not any(x in ' '.join(R['html']) for x in ('<', '25 / 20', '1000000000', 'evil', '-1')), R)
    await pg.unroute(api)

    # ---- read-only ----
    after = await pg.evaluate(POST, [api, {'a': 'login', 'c': CLASS, 'n': 'אביגיל', 'p': '2468'}])
    check(f'[{tag}] the pupil\'s record is the same after the teacher looked', json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True))
    acts = sorted({json.loads(x).get('a') for x in bodies if x})
    check(f'[{tag}] the screen only ever asked the backend for the teacher view (the test itself registered, saved and signed in)', set(acts) <= {'teacher', 'register', 'save', 'login'} and 'reset' not in acts, acts)
    await pg.goto(P.BASE + '?tmock=0#teacher'); await pg.wait_for_selector('#tt')
    check(f'[{tag}] ?tmock=0 takes the switch away', await pg.evaluate("JSON.parse(localStorage.getItem('word-islands-settings-v1')).tmock===false"))
    await c.close()


async def main():
    procs = servers()
    api = f'http://127.0.0.1:{P.API_PORT}/'
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            await run(b, 390, 844, errs, api, True)
            await run(b, 1366, 768, errs, api, False)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
