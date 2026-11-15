#!/usr/bin/env python3
"""End-to-end play-through for Word Islands (headless Chrome via Playwright).

    python3 tests/play.py            # full: every level of every island (local mode), island 1 at a second
                                     # viewport, class mode against the mock backend, audio levels
    python3 tests/play.py --quick    # island 1 only in each mode
    python3 tests/play.py --shots DIR  # also save a PNG of every screen into DIR

It starts its own static server for the repo and, for class mode, the mock Apps Script backend
(tests/mock.js, a small Node stand-in for the Apps Script runtime that runs backend/Code.gs unchanged). Exits non-zero on any failed check or page error.
"""
import asyncio, math, os, subprocess, sys, time, socket
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCK = os.environ.get('MOCK', os.path.join(ROOT, 'tests', 'mock.js'))
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
QUICK = '--quick' in sys.argv
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
PORT, API_PORT = 8791, 8765
BASE = f'http://127.0.0.1:{PORT}/index.html'
fails, shot_n = [], [0]


def check(label, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + label + (' ' + str(extra) if extra else ''), flush=True)
    if not ok:
        fails.append(label)


def port_open(p):
    s = socket.socket()
    try:
        s.settimeout(.3); s.connect(('127.0.0.1', p)); return True
    except OSError:
        return False
    finally:
        s.close()


async def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        await pg.wait_for_timeout(450)          # let the background cross-fade finish
        await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))


async def lv(pg, kind, timeout=15000):
    await pg.wait_for_function(f"window.__lv&&window.__lv.kind==='{kind}'", timeout=timeout)


async def play_sling(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'sling')
    box = await pg.locator('#cv').bounding_box()
    n, miss_done, missed_shot = 0, False, False
    if use_hint:
        await pg.click('[data-a=hint]')
    while n < 40:
        n += 1
        if await pg.locator('.result').count():
            return True
        st = await pg.evaluate("""(()=>{const L=window.__lv;if(!L||L.kind!=='sling')return null;const g=L.g;if(g.fly||g.lock||!g.bub.length)return null;
            const ok=g.bub.find(b=>b.ok),bad=g.bub.find(b=>!b.ok&&!b.bad);return {ok:[ok.x,ok.y],bad:bad?[bad.x,bad.y]:null,geo:L.geom(),K:L.K,G:L.G,i:g.i}})()""")
        if not st:
            await pg.wait_for_timeout(200); continue
        geo, K, G = st['geo'], st['K'], st['G']
        tx, ty = st['ok']
        if wrong_first and not miss_done and st['bad']:
            tx, ty = st['bad']; miss_done = True
        vy = -15.0
        a, b, c = .5 * G, vy, geo['AY'] - ty
        t = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)       # first time the ball is at the balloon's height
        dy = -vy / K                                            # the ball is released from the pulled-back position
        a, b, c = .5 * G, vy, geo['AY'] + dy - ty
        t = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
        vx = (tx - geo['AX']) / (t - 1 / K)
        dx = -vx / K
        x0, y0 = box['x'] + geo['AX'], box['y'] + geo['AY']
        await pg.mouse.move(x0, y0); await pg.mouse.down()
        await pg.mouse.move(x0 + dx / 2, y0 + dy / 2, steps=3); await pg.mouse.move(x0 + dx, y0 + dy, steps=3)
        if tag and st['i'] == 1:
            await pg.wait_for_timeout(120); await shot(pg, tag + '_aim')
        await pg.mouse.up()
        if tag and SHOTS and st['i'] == 0 and miss_done and wrong_first and not missed_shot:
            missed_shot = True
            await pg.wait_for_timeout(750); await pg.screenshot(path=os.path.join(SHOTS, tag + '_miss.png')); await pg.wait_for_timeout(750)
        else:
            await pg.wait_for_timeout(1500)
    return False


async def play_listen(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'listen')
    done_wrong = False
    for _ in range(60):
        if await pg.locator('.result').count():
            return True
        ans = await pg.evaluate("(()=>{const L=window.__lv;return L&&L.kind==='listen'&&!L.g.lock?L.answer():null})()")
        if not ans:
            await pg.wait_for_timeout(200); continue
        if use_hint:
            await pg.click('[data-a=hint]'); use_hint = False
        if wrong_first and not done_wrong:
            done_wrong = True
            await pg.locator(f'.bub:not(.bad):not([data-w="{ans}"])').first.click(force=True)
            await pg.wait_for_timeout(250)
            if tag: await shot(pg, tag + '_wrong')
            await pg.click('.replay', force=True)
        await pg.locator(f'.bub[data-w="{ans}"]').click(force=True)
        await pg.wait_for_timeout(400)
        if tag and not done_wrong: pass
        await pg.wait_for_timeout(1000)
    return False


async def play_read(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'read')
    await pg.locator('.t').first.click()                    # gloss a word
    gl = await pg.locator('#gl').inner_text()
    check('read: tapping a word shows its gloss', '=' in gl, gl.replace('\n', ' ')[:40])
    if tag: await shot(pg, tag + '_gloss')
    await pg.click('[data-a=toq]')
    done_wrong = False
    for _ in range(40):
        if await pg.locator('.result').count():
            return True
        if not await pg.locator('.bottle').count():
            if await pg.locator('[data-a=unpeek]').count():
                await pg.click('[data-a=unpeek]')
            await pg.wait_for_timeout(200); continue
        ans = await pg.evaluate("(()=>{const L=window.__lv;return L&&!L.g.lock?L.answer():null})()")
        if ans is None:
            await pg.wait_for_timeout(200); continue
        if use_hint:
            use_hint = False
            await pg.click('[data-a=hint]'); await pg.wait_for_timeout(200)
            check('read: hint opens the story with a marked sentence', await pg.locator('.sn.hl').count() > 0)
            if tag: await shot(pg, tag + '_hint')
            await pg.click('[data-a=unpeek]')
        if wrong_first and not done_wrong:
            done_wrong = True
            await pg.locator(f'.bottle:not([data-o="{ans}"])').first.click(); await pg.wait_for_timeout(250)
            if tag: await shot(pg, tag + '_wrong')
            await pg.click('[data-a=peek]'); await pg.wait_for_timeout(150)
            check('read: peek shows the story again', await pg.locator('.story').count() == 1)
            await pg.click('[data-a=unpeek]')
        await pg.locator(f'.bottle[data-o="{ans}"]').click()
        await pg.wait_for_timeout(1500)
    return False


async def play_bridge(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'bridge')
    done_wrong, shots = False, set()
    for _ in range(120):
        if await pg.locator('.result').count():
            return True
        nxt = await pg.evaluate("(()=>{const L=window.__lv;return L&&L.kind==='bridge'&&!L.g.lock?[L.next(),L.g.r.kind]:null})()")
        if not nxt or nxt[0] is None:
            await pg.wait_for_timeout(200); continue
        want, kind = nxt
        if use_hint:
            use_hint = False; await pg.click('[data-a=hint]')
        if wrong_first and not done_wrong:
            done_wrong = True
            await pg.locator(f'.pl:not(.used):not([data-t="{want}"])').first.click()
            await pg.wait_for_timeout(300)
            if tag: await shot(pg, tag + '_snap')
            await pg.wait_for_timeout(700)
        await pg.locator(f'.pl:not(.used)[data-t="{want}"]').first.click()
        await pg.wait_for_timeout(260)
        if tag and kind not in shots:
            shots.add(kind); await shot(pg, tag + '_' + kind)
    return False


PLAYERS = {'sling': play_sling, 'listen': play_listen, 'read': play_read, 'bridge': play_bridge}


async def play_level(pg, isl, typ, **kw):
    await pg.evaluate(f"location.hash='play/{isl}/{typ}'")
    ok = await PLAYERS[typ](pg, **kw)
    check(f'island {isl} {typ}: played to the result screen', ok)
    if not ok:
        return 0
    await pg.wait_for_timeout(1700 if SHOTS else 300)
    stars = await pg.locator('.bs.on').count()
    return stars


async def new_page(b, w, h, api=None, errs=None):
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=True, locale='he-IL')
    pg = await c.new_page()
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.on('requestfailed', lambda r: errs.append('requestfailed: ' + r.url) if 'fonts.g' not in r.url else None)   # the classic trainer uses Google Fonts; offline CI cannot reach them
    pg.on('response', lambda r: errs.append(f'http {r.status}: {r.url}') if r.status >= 400 else None)
    if api:
        await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body=f"window.API_URL='{api}';"))
    return c, pg


async def local_run(b, w, h, full, errs):
    tag = f'{w}x{h}'
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.goto(BASE); await pg.wait_for_selector('.title .btn'); await pg.wait_for_timeout(600)
    await shot(pg, f'{tag}_01_title')
    check(f'[{tag}] local mode: no login, title shown', await pg.locator('#lc').count() == 0)
    await pg.click('.title .btn', force=True); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(500)
    await shot(pg, f'{tag}_02_map')
    check(f'[{tag}] map: 6 islands, only the first open', await pg.locator('.isl').count() == 6 and await pg.locator('.isl.locked').count() == 5)
    check(f'[{tag}] map: no leaderboard button in local mode', await pg.locator('[data-to=board]').count() == 0)
    await pg.locator('.isl.locked').first.click(); await pg.wait_for_timeout(300)
    check(f'[{tag}] locked island explains itself', await pg.locator('#toast.on').count() == 1)
    await pg.click('.isl.i1'); await pg.wait_for_selector('.lvrow'); await pg.wait_for_timeout(400)
    await shot(pg, f'{tag}_03_island')
    check(f'[{tag}] island 1 lists 4 levels', await pg.locator('.lvrow').count() == 4)
    # onboarding hint on the very first slingshot level
    await pg.evaluate("location.hash='play/1/sling'"); await lv(pg, 'sling'); await pg.wait_for_timeout(500)
    check(f'[{tag}] first run shows the animated drag hint', await pg.locator('#coach:not([hidden])').count() == 1)
    await shot(pg, f'{tag}_04_sling_start')
    s1 = await play_level(pg, 1, 'sling', wrong_first=True, tag=f'{tag}_05_sling')
    await shot(pg, f'{tag}_06_result_sling')
    check(f'[{tag}] sling with one miss still earns 3 stars', s1 == 3, s1)
    check(f'[{tag}] one-tap next level button present', await pg.locator('.result .btn.green').count() == 1)
    await pg.click('.result .btn.green')                     # next level = listening
    await lv(pg, 'listen'); await pg.wait_for_timeout(700); await shot(pg, f'{tag}_07_listen')
    s2 = await play_level(pg, 1, 'listen', wrong_first=True, use_hint=True, tag=f'{tag}_08_listen')
    await shot(pg, f'{tag}_09_result_listen')
    check(f'[{tag}] hint caps the level at 2 stars', s2 == 2, s2)
    await pg.evaluate("location.hash='play/1/read'"); await lv(pg, 'read'); await pg.wait_for_timeout(500); await shot(pg, f'{tag}_10_read_story')
    s3 = await play_level(pg, 1, 'read', wrong_first=True, use_hint=False, tag=f'{tag}_11_read')
    await shot(pg, f'{tag}_12_result_read')
    check(f'[{tag}] read with one wrong pick gives 2 stars', s3 == 2, s3)
    s4 = await play_level(pg, 1, 'bridge', wrong_first=True, tag=f'{tag}_13_bridge')
    await shot(pg, f'{tag}_14_result_bridge')
    check(f'[{tag}] bridge finished with stars', s4 >= 2, s4)
    st = await pg.evaluate("(()=>{const S=__game.S();return {tot:__game.totalStars(),pts:S.pts,w:Object.keys(S.w).length,st:Object.keys(S.st).length,read:S.read[1],g:S.g.st}})()")
    check(f'[{tag}] stars saved', st['tot'] == s1 + s2 + s3 + s4, st)
    check(f'[{tag}] points, word knowledge and reading score recorded', st['pts'] > 0 and st['w'] >= 7 and st['st'] >= 7 and st['read'] == 4, st)
    # replay with a worse result must not lower stars; points must still go up
    pts0 = st['pts']
    await play_level(pg, 1, 'listen', wrong_first=True, use_hint=True)
    st2 = await pg.evaluate("(()=>{const S=__game.S();return {tot:__game.totalStars(),pts:S.pts}})()")
    check(f'[{tag}] replay keeps best stars and raises points', st2['tot'] == st['tot'] and st2['pts'] > pts0, st2)
    await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(400)
    check(f'[{tag}] island 2 unlocked after island 1', await pg.locator('.isl.i2.locked').count() == 0)
    await shot(pg, f'{tag}_15_map_progress')
    await pg.reload(); await pg.wait_for_timeout(800)
    check(f'[{tag}] progress survives reload', await pg.evaluate("__game.totalStars()") == st['tot'])
    for name, h in [('collection', 'collection'), ('settings', 'settings'), ('help', 'help')]:
        await pg.evaluate(f"location.hash='{h}'"); await pg.wait_for_timeout(500); await shot(pg, f'{tag}_2{["collection","settings","help"].index(name)}_{name}')
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.setrow')
    await pg.click('[data-k=music]'); await pg.click('[data-k=sfx]')
    check(f'[{tag}] sound toggles persist', await pg.evaluate("JSON.parse(localStorage.getItem('word-islands-settings-v1')).music===false&&JSON.parse(localStorage.getItem('word-islands-settings-v1')).sfx===false"))
    await pg.click('[data-k=music]'); await pg.click('[data-k=sfx]')
    check(f'[{tag}] settings link to the classic trainer', await pg.locator('a[href="trainer.html"]').count() == 1)
    await pg.evaluate("location.hash='collection'"); await pg.wait_for_selector('.ball')
    opened = await pg.locator('.ball:not(.locked)').count()
    check(f'[{tag}] collection unlocks by stars', opened >= 2, opened)
    await pg.locator('.ball:not(.locked)').nth(1).click(); await pg.wait_for_timeout(200)
    check(f'[{tag}] chosen ball is saved', await pg.evaluate("__game.S().g.ball") == 1)
    if full:
        for isl in (2, 3, 4, 5):
            # islands open by stars; give the stars a strong player would have by then, then play for real
            await pg.evaluate("(n=>{const S=__game.S();for(let i=1;i<n;i++)for(const t of['sling','listen','read','bridge'])S.g.st[i+'-'+t]=Math.max(S.g.st[i+'-'+t]||0,2);localStorage.setItem('aam-unit1-v1',JSON.stringify(S))})(%d)" % isl)
            for typ in ('sling', 'listen', 'read', 'bridge'):
                await pg.evaluate(f"location.hash='island/{isl}'"); await pg.wait_for_timeout(150)
                s = await play_level(pg, isl, typ, wrong_first=(typ == 'bridge'))
                check(f'[{tag}] island {isl} {typ} stars', s >= 2, s)
                if typ == 'sling': await shot(pg, f'{tag}_3{isl}_island{isl}_result')
            await pg.evaluate(f"location.hash='play/{isl}/sling'"); await lv(pg, 'sling'); await pg.wait_for_timeout(600); await shot(pg, f'{tag}_4{isl}_island{isl}_sling')
        await pg.evaluate("(()=>{const S=__game.S();for(let i=1;i<6;i++)for(const t of['sling','listen','read','bridge'])S.g.st[i+'-'+t]=3;localStorage.setItem('aam-unit1-v1',JSON.stringify(S))})()")
        for typ in ('sling', 'listen'):
            await pg.evaluate("location.hash='island/6'"); await pg.wait_for_timeout(150)
            s = await play_level(pg, 6, typ)
            check(f'[{tag}] bonus island {typ} stars', s == 3, s)
        await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(500); await shot(pg, f'{tag}_50_map_all_open')
        check(f'[{tag}] all islands open at the end', await pg.locator('.isl.locked').count() == 0)
        m = await pg.evaluate("__game.measure(40)")
        check('audio: offline render peak below 0.5 and not silent', 0.02 < m['peak'] < 0.5, m)
    # old trainer still works and links back
    await pg.goto(BASE.replace('index.html', 'trainer.html')); await pg.wait_for_timeout(500)
    check(f'[{tag}] classic trainer loads with a link back to the game', await pg.locator('a[href="./"]').count() == 1 and await pg.locator('.tile').count() == 6)
    await c.close()


async def class_run(b, w, h, errs):
    tag = f'class {w}x{h}'
    api = f'http://127.0.0.1:{API_PORT}/'
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    await pg.goto(BASE); await pg.wait_for_selector('#lc'); await pg.wait_for_timeout(500)
    # a few invented classmates so the leaderboard and the teacher screen look like a real class
    mates = [('נועה', 640, 31, 3, 4), ('איתי', 505, 24, 2, 2), ('מאיה', 410, 19, 1, 6), ('עומר', 220, 9, 0, 1)]
    taken = await pg.evaluate('''async ([api, mates]) => { const out = []; for (const [n, pts, words, reads, streak] of mates) {
        const post = d => fetch(api, {method: 'POST', body: JSON.stringify(d)}).then(r => r.json());
        const r = await post({a: 'register', c: 'EN-1234', n, p: '1111'}); out.push(r.ok ? '' : r.e);
        await post({a: 'save', c: 'EN-1234', n, p: '1111', s: {pts, streak, day: '2026-11-14', k: {words, reads}, st: {their: [6, 4], special: [5, 2], subject: [6, 3], 'a lot of': [4, 2]}}}); } return out }''', [api, mates])
    name = None
    for cand in ('יובל', 'תמר', 'אורי', 'שירה', 'דניאל', 'רוני', 'גיא', 'ליה', 'אדם', 'מיכל', 'עידו', 'הילה'):
        r = await pg.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'login',c:'EN-1234',n,p:'0000'})})).json()", [api, cand])
        if r.get('e') == 'nouser':
            name = cand; break
    check(f'[{tag}] a free pupil name is available on the mock backend', name is not None)
    await shot(pg, f'class_01_login')
    check(f'[{tag}] login is required', await pg.locator('#lc').count() == 1)
    await pg.fill('#lc', 'EN-1234'); await pg.fill('#ln', name); await pg.fill('#lp', '4321')
    await pg.click('[data-m=login]'); await pg.wait_for_function("document.querySelector('.err').textContent.length>3")
    check(f'[{tag}] unknown name gets a friendly message', 'פעם ראשונה' in await pg.locator('.err').inner_text())
    await shot(pg, f'class_02_login_error')
    await pg.fill('#lp', '4321'); await pg.click('[data-m=register]'); await pg.wait_for_selector('.map .isl')
    check(f'[{tag}] register lands on the map with the leaderboard button', await pg.locator('[data-to=board]').count() == 1)
    s = await play_level(pg, 1, 'sling')
    check(f'[{tag}] perfect sling gives 3 stars', s == 3, s)
    await shot(pg, f'class_03_result')
    for typ in ('listen', 'read'):
        s = await play_level(pg, 1, typ)
        check(f'[{tag}] perfect {typ} gives 3 stars', s == 3, s)
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('[data-a=logout]'); await shot(pg, 'class_05_settings')
    check(f'[{tag}] pupils get no teacher entry in settings', await pg.locator('[data-to=teacher]').count() == 0)
    pts = await pg.evaluate("__game.S().pts")
    await pg.evaluate("location.hash='board'"); await pg.wait_for_selector('.lb li')
    txt = await pg.locator('.lb li.me').inner_text()
    check(f'[{tag}] own row on the leaderboard with points', name in txt and f'{pts:,}' in txt, txt.replace('\n', ' '))
    check(f'[{tag}] leaderboard lists the whole class', await pg.locator('.lb li').count() >= 5)
    await shot(pg, f'class_04_board')
    # a second device logs in and gets the same progress
    c2, p2 = await new_page(b, w, h, api=api, errs=errs)
    await p2.goto(BASE); await p2.wait_for_selector('#lc')
    await p2.fill('#lc', 'en-1234'); await p2.fill('#ln', name); await p2.fill('#lp', '0000'); await p2.click('[data-m=login]')
    await p2.wait_for_function("document.querySelector('.err')&&document.querySelector('.err').textContent.length>3")
    check(f'[{tag}] wrong secret code is refused', 'הקוד הסודי' in await p2.locator('.err').inner_text())
    await p2.fill('#lp', '4321'); await p2.click('[data-m=login]'); await p2.wait_for_selector('.map .isl')
    st = await p2.evaluate("(()=>{const S=__game.S();return [__game.totalStars(),S.pts,Object.keys(S.w).length]})()")
    check(f'[{tag}] second device receives stars, points and word knowledge', st[0] == 9 and st[1] == pts and st[2] >= 7, st)
    # the classic trainer shares the login and must not drop the game stars when it saves
    await p2.goto(BASE.replace('index.html', 'trainer.html') + '#quiz'); await p2.wait_for_timeout(500)
    await p2.click('[data-a=start]'); await p2.wait_for_timeout(300)
    ans = await p2.evaluate("V.qs[V.i].opts.indexOf(V.qs[V.i].ans)"); await p2.click(f'.opt >> nth={ans}'); await p2.wait_for_timeout(3600)
    await p2.goto(BASE + '#map'); await p2.wait_for_selector('.map .isl')
    await p2.evaluate("location.hash='settings'"); await p2.wait_for_selector('[data-a=logout]')
    await p2.click('[data-a=logout]'); await p2.wait_for_selector('#lc')
    check(f'[{tag}] logout returns to login and clears local progress', await p2.evaluate("__game.totalStars()") == 0)
    await p2.fill('#ln', name); await p2.fill('#lp', '4321'); await p2.click('[data-m=login]'); await p2.wait_for_selector('.map .isl')
    st2 = await p2.evaluate("[__game.totalStars(),__game.S().pts]")
    check(f'[{tag}] stars survive a save made by the classic trainer', st2[0] == 9 and st2[1] > pts, st2)
    # teacher screen
    await p2.evaluate("location.hash='teacher'"); await p2.wait_for_selector('#tt')
    await p2.fill('#tt', '111'); await p2.click('[data-a=tlogin]'); await p2.wait_for_function("document.querySelector('.err').textContent.length>3")
    check(f'[{tag}] wrong teacher code is refused', 'קוד המורה' in await p2.locator('.err').inner_text())
    await p2.fill('#tt', '654321'); await p2.click('[data-a=tlogin]'); await p2.wait_for_selector('.kid')
    row = (await p2.locator('.kid', has_text=name).inner_text()).replace('\n', ' ')
    known = await p2.evaluate("__game.S().w ? Object.values(__game.S().w).filter(v=>v>=2).length : 0")
    check(f'[{tag}] teacher card lists the pupil with words learned and a finished story', name in row and f'{known} / 59' in row and known >= 3 and '1 / 5' in row, row)
    check(f'[{tag}] teacher sees the hardest words', await p2.locator('.hard > div').count() >= 1)
    await shot(p2, 'class_06_teacher')
    await c.close(); await c2.close()


async def main():
    procs = []
    if not port_open(PORT):
        procs.append(subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    have_mock = os.path.exists(MOCK)
    if have_mock and not port_open(API_PORT):
        procs.append(subprocess.Popen(['node', MOCK], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for _ in range(40):
        if port_open(PORT) and (not have_mock or port_open(API_PORT)): break
        time.sleep(.1)
    errs = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await local_run(b, 390, 844, not QUICK, errs)
            await local_run(b, 360, 740, False, errs)
            if have_mock:
                await class_run(b, 390, 844, errs)
            else:
                check('mock backend available for class mode', False, MOCK)
            await b.close()
    finally:
        for pr in procs: pr.terminate()
    check('no page errors, console errors or failed requests', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

asyncio.run(main())
