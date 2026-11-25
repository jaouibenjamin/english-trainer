#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""Mock exam results on the teacher screen, behind their switch (?tmock=1), against the mock backend.

    python3 tests/teacher_mock.py              # phone and laptop
    python3 tests/teacher_mock.py --shots DIR  # also save PNGs

Checks: without the switch the screen is as before; in the new look (?ds=1) the same cards, every button 48px or more,
no text under 4.5:1 against its own backing and no card wider than its box; with it each pupil's card shows the papers taken, the last and
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
PUPILS = {'אביגיל': [TRY1, TRY2], 'בארי': [], 'גילי': [TRY1], 'דליה': [dict(TRY1, at=1000 + i) for i in range(19)] + [TRY2]}   # 20 papers: the device keeps only the last 20
LONG = 'TESTWWWWWWWWWWWWWWWW'   # an obviously fake name: 20 wide letters with no space, the longest the sign-in form takes
PUPILS[LONG] = []
POST = "async ([api,d])=>(await fetch(api,{method:'POST',body:JSON.stringify(d)})).json()"
DS = """(()=>{const lum=c=>{const m=c.match(/[\\d.]+/g).map(Number);const f=v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4};return [.2126*f(m[0])+.7152*f(m[1])+.0722*f(m[2]),m[3]===undefined?1:m[3]]};
 const back=e=>{for(;e;e=e.parentElement){const b=getComputedStyle(e).backgroundColor;const l=lum(b);if(l[1]>=.99)return l[0]}return 1};
 const low=[];for(const e of document.querySelectorAll('#stage *')){if(!e.offsetParent)continue;const own=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());if(!own)continue;
  const a=lum(getComputedStyle(e).color)[0],b=back(e),r=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);if(r<4.5)low.push([e.tagName,e.className,e.textContent.trim().slice(0,20),r.toFixed(2)])}
 const small=[...document.querySelectorAll('#stage button,#stage a,#stage input')].filter(e=>e.offsetParent).map(e=>[e.className,Math.round(e.getBoundingClientRect().height)]).filter(x=>x[1]<48);
 return {ds:document.documentElement.classList.contains('ds'),css:[...document.styleSheets].some(x=>(x.href||'').endsWith('/css/ds-teacher.css')),low,small}})()"""
CARDS = """(()=>Object.fromEntries([...document.querySelectorAll('.kid')].map(k=>[k.querySelector('.kn b').textContent,{km:[...k.querySelectorAll('.km')].map(p=>p.innerText.replace(/\\s+/g,' ').trim()),rows:k.querySelectorAll('p').length,wide:k.scrollWidth>k.clientWidth+1||[...k.querySelectorAll('*')].some(e=>{const r=e.getBoundingClientRect(),K=k.getBoundingClientRect();return r.left<K.left-1||r.right>K.right+1})}])))()"""


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


TOAST = """(()=>{const lum=c=>{const m=c.match(/[\\d.]+/g).map(Number);const f=v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4};return .2126*f(m[0])+.7152*f(m[1])+.0722*f(m[2])};
 const t=document.querySelector('#toast .toastin');if(!t)return null;const s=getComputedStyle(t),a=lum(s.color),b=lum(s.backgroundColor);
 const bs=[...t.querySelectorAll('b')].map(e=>{const x=lum(getComputedStyle(e).color);return +((Math.max(x,b)+.05)/(Math.min(x,b)+.05)).toFixed(2)});
 return {text:t.innerText.replace(/\\s+/g,' '),bg:s.backgroundColor,ratio:+((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2),bold:bs}})()"""


async def resets(b, w, h, errs, api, tag, look):
    """'reset code' in both looks, in a page of its own (so the read-only checks below still see no reset): the toast
    after a reset that worked and after one that failed is readable (4.5:1 or more), and the button keeps its result
    after the 4 s disarm timer (it used to write "איפוס קוד" back on the disabled button)"""
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    await pg.goto(P.BASE + look); await pg.wait_for_selector('#lc')
    await sign_in(pg, look)
    btn = lambda n: pg.locator('.kid', has_text=n).locator('[data-a=treset]')
    await btn('גילי').click(); await btn('גילי').click()
    await pg.wait_for_function("document.querySelector('#toast .toastin')&&document.querySelector('#toast .toastin').textContent.includes('אופס')", timeout=8000)
    await pg.wait_for_timeout(300)
    T = await pg.evaluate(TOAST)
    check(f'[{tag} {look}] a reset that worked: the toast says so and is readable (4.5:1 or more, the name too)', T and 'אופס' in T['text'] and T['ratio'] >= 4.5 and all(r >= 4.5 for r in T['bold']), T)
    if P.SHOTS and 'ds=1' in look: await pg.screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-toast-ok-{tag}.png'))
    await pg.wait_for_timeout(4300)
    st = await pg.evaluate("(()=>{const b=[...document.querySelectorAll('.kid')].find(k=>k.textContent.includes('גילי')).querySelector('.treset');return [b.textContent,b.disabled]})()")
    check(f'[{tag} {look}] after the 4 s disarm timer the button still says the code was reset', st == ['הקוד אופס', True], st)
    async def fail(route):
        if '"reset"' in (route.request.post_data or ''): await route.fulfill(content_type='application/json', body='{"ok":false,"e":"net"}')
        else: await route.continue_()
    await pg.route(api, fail)
    await btn('בארי').click(); await btn('בארי').click()
    await pg.wait_for_function("document.querySelector('#toast .toastin')&&!document.querySelector('#toast .toastin').textContent.includes('אופס')", timeout=8000)
    await pg.wait_for_timeout(300)
    T = await pg.evaluate(TOAST)
    check(f'[{tag} {look}] a reset that failed: the toast is readable (4.5:1 or more) and the button is back to "reset code"', T and T['ratio'] >= 4.5 and await btn('בארי').inner_text() == 'איפוס קוד', T)
    if P.SHOTS and 'ds=1' in look: await pg.screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-toast-fail-{tag}.png'))
    await pg.unroute(api)
    await pg.wait_for_load_state('networkidle'); await pg.goto(P.BASE + '?ds=0'); await pg.wait_for_selector('#lc'); await pg.wait_for_load_state('networkidle')
    await c.close()


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
    d20 = cards['דליה']['km']
    check(f'[{tag}] on: with 20 papers the oldest score is called the oldest of the last 20, not the first', len(d20) == 2 and '20 ניסיונות' in d20[0] and 'הוותיק מ־20 האחרונים 9 / 20' in d20[0] and 'ראשון' not in d20[0], d20)
    check(f'[{tag}] on: no card is wider than its box (except the 20-letter name in the old look, a known overflow fixed only in the new look)', not any(v['wide'] for n, v in cards.items() if n != LONG))
    text = await pg.inner_text('.kids')
    check(f'[{tag}] on: what a pupil typed in the exam is not on the screen', 'zzz' not in text and 'a:1' not in text)
    if P.SHOTS:
        os.makedirs(P.SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(P.SHOTS, f'teacher-mock-{tag}.png'), full_page=False)
        await pg.locator('.kid', has_text='אביגיל').screenshot(path=os.path.join(P.SHOTS, f'teacher-mock-card-{tag}.png'))

    # ---- the new look (?ds=1): the same cards, in the dark shell ----
    await pg.wait_for_load_state('networkidle'); await pg.goto('about:blank'); await pg.goto(P.BASE + '?ds=1#teacher'); await pg.wait_for_selector('#tt')
    R = await pg.evaluate(DS)
    check(f'[{tag}] new look: the sign-in form is in the new look, buttons and fields 48px, every text 4.5:1 or more', R['ds'] and R['css'] and not R['small'] and not R['low'], R)
    if P.SHOTS: await pg.screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-signin-{tag}.png'))
    await sign_in(pg, '?ds=1')
    cards_ds = await pg.evaluate(CARDS)
    check(f'[{tag}] new look: the same cards and rows as the old look, none wider than its box, not even a 20-letter name', {n: (v['km'], v['rows']) for n, v in cards_ds.items()} == {n: (v['km'], v['rows']) for n, v in cards.items()} and not any(v['wide'] for v in cards_ds.values()) and LONG in cards_ds, cards_ds)
    R = await pg.evaluate(DS)
    check(f'[{tag}] new look: every button 48px or more and every text 4.5:1 or more against its own backing', R['ds'] and not R['small'] and not R['low'], R)
    if P.SHOTS:
        await pg.screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-{tag}.png'))
        await pg.screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-full-{tag}.png'), full_page=True)
        await pg.locator('.kid', has_text='אביגיל').screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-card-{tag}.png'))
        await pg.locator('.kid', has_text=LONG).screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-long-{tag}.png'))
    await pg.click('.kid:has-text("בארי") [data-a=treset]')
    armed = await pg.evaluate("(()=>{const b=document.querySelector('.treset[data-arm]');if(!b)return null;const s=getComputedStyle(b);return [b.textContent,s.color,Math.round(b.getBoundingClientRect().height)]})()")
    check(f'[{tag}] new look: "reset code" asks for a second tap and shows it in the warm colour, nothing sent yet', armed and armed[2] >= 48 and armed[1] == 'rgb(255, 138, 122)' and not any('"reset"' in x for x in bodies), armed)
    if P.SHOTS: await pg.locator('.kid', has_text='בארי').screenshot(path=os.path.join(P.SHOTS, f'teacher-ds-armed-{tag}.png'))
    await pg.wait_for_load_state('networkidle'); await pg.goto(P.BASE + '?ds=0'); await pg.wait_for_selector('#lc'); await pg.wait_for_load_state('networkidle')
    check(f'[{tag}] ?ds=0 takes the new look away', await pg.evaluate("localStorage.getItem('wi_ds')===null&&!document.documentElement.classList.contains('ds')"))

    for look in ('?ds=1', '?ds=0'):
        await resets(b, w, h, errs, api, tag, look)
    # ---- the new look with every other switch on at once (docs/LESSONS.md 8): same scan, toast included ----
    ALL = '?ds=1&card=1&help=1&games=1&sheet=1&tmock=1'
    await resets(b, w, h, errs, api, tag, ALL)
    c2, pg2 = await new_page(b, w, h, api=api, errs=errs)
    await pg2.goto(P.BASE + ALL); await pg2.wait_for_selector('#lc')
    await sign_in(pg2, ALL)
    R = await pg2.evaluate(DS)
    check(f'[{tag}] new look with card, help, games, sheet and tmock on: every button 48px or more, every text 4.5:1 or more', R['ds'] and not R['small'] and not R['low'], R)
    for q in ('?ds=0', '?card=0&games=0&sheet=0&tmock=0'):
        await pg2.wait_for_load_state('networkidle'); await pg2.goto(P.BASE + q); await pg2.wait_for_selector('#lc')
    await pg2.wait_for_load_state('networkidle'); await c2.close()

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
        d['hard'] = [['goal', 250, 5], ['<img src=x onerror="window.__pwned=1">', 50, 5], ['constructor', 40, 5], ['kick', 'x', 3], 'junk', ['song', -20, 4]]
        await route.fulfill(content_type='application/json', body=json.dumps(d))
    await pg.route(api, hostile)
    await sign_in(pg)
    R = await pg.evaluate("({pwned:!!window.__pwned,tags:document.querySelectorAll('.kid .km img,.kid .km b:not(:first-child) *,.kid .km i').length,html:[...document.querySelectorAll('.kid .km')].map(p=>p.innerText.replace(/\\s+/g,' ').trim())})")
    check(f'[{tag}] rubbish from a backend is never drawn: no markup, no impossible number, only checked values',
          not R['pwned'] and R['tags'] == 0 and not any(x in ' '.join(R['html']) for x in ('<', '25 / 20', '1000000000', 'evil', '-1')), R)
    H = await pg.evaluate("[...document.querySelectorAll('.hard > div')].map(d=>[d.querySelector('.en,bdi').textContent,d.querySelector('.pbar i').style.width])")
    check(f'[{tag}] the hard words from a backend: only words of the unit are shown, and each bar is between 0 and 100% wide', H == [['goal', '100%'], ['kick', '0%'], ['song', '0%']], H)
    await pg.unroute(api)

    # ---- a backend that answers with an error page: the teacher is told the server failed, not to check the internet ----
    await pg.route(api, lambda route: route.fulfill(content_type='text/html', body='<html><body>Error</body></html>'))
    await pg.wait_for_load_state('networkidle'); await pg.goto('about:blank'); await pg.goto(P.BASE + '#teacher'); await pg.wait_for_selector('#tt')
    await pg.fill('#tc', CLASS); await pg.fill('#tt', TEACHER); await pg.click('[data-a=tlogin]')
    await pg.wait_for_function("document.querySelector('.err')&&document.querySelector('.err').textContent.length>3")
    err = await pg.inner_text('.err')
    check(f'[{tag}] a server that answers with an error page: the message says the server failed, not the internet', err.startswith('משהו השתבש בשרת') and 'אינטרנט' not in err, err)
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
