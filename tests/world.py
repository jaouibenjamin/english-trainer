#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The new world in the live game behind the design flag (?ds=1, js/avatar.js): character, its name, energy, today's focus.

    python3 tests/world.py              # phone and laptop
    python3 tests/world.py --shots DIR  # also save PNGs of the map dock and the picker

Flag off: nothing of it is fetched, drawn or stored, and #avatar is an unknown address as before (the title screen). Flag on: the map has the dock;
the picker shows the 20 characters with the four rewards locked at level 1; the choice and the name (two indexes into
the fixed lists, never text) are kept in the wi_world key on the device only, never in the progress record and never
in a request to the backend (checked against the mock backend in class mode); energy only goes up; today's focus names
the open island with the most words to fix and takes the pupil there."""
import asyncio, hashlib, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, fails

CLASS = 'EN-1234'      # the mock backend's own test class
POST = "async ([api,d])=>(await fetch(api,{method:'POST',body:JSON.stringify(d)})).json()"
WORLD_FILES = ('js/avatar.js', 'css/avatar.css', 'js/world_data.js', 'js/world_art.js')
LS = "Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))"
# 11 stars on islands 1-2, one word known, one story read, and four words got wrong on island 1 (parts 1)
SEED = {'g': {'st': {'1-sling': 3, '1-listen': 2, '1-read': 3, '1-bridge': 2, '2-sling': 1}}, 'w': {'song': 3, 'kick': 0, 'far': 0, 'play': 1},
        'st': {'kick': [3, 2], 'far': [2, 1], 'play': [2, 1], 'guitar': [1, 1]}, 'read': {'1': 1}}


async def page(b, w, h, errs, seed=None, api=None, user=None):
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    reqs = []
    pg.on('request', lambda r: reqs.append((r.url, r.post_data or '')))
    st = dict(seed or {})
    if user:
        st['u'] = user
    if st:
        await pg.add_init_script("if(!sessionStorage.getItem('seeded')){sessionStorage.setItem('seeded','1');localStorage.setItem('aam-unit1-v1',%s)}" % json.dumps(json.dumps(st)))
    return c, pg, reqs


async def flag_off(b, w, h, errs):
    tag = f'off {w}x{h}'
    c, pg, reqs = await page(b, w, h, errs, SEED)
    await pg.goto(P.BASE + '#map'); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(600)
    check(f'[{tag}] the map has no dock', await pg.locator('.wd').count() == 0)
    await pg.evaluate("location.hash='avatar'"); await pg.wait_for_selector('.scr.title'); await pg.wait_for_timeout(300)
    check(f'[{tag}] #avatar is an unknown address, as before: the title screen', await pg.evaluate("document.getElementById('stage').dataset.scr") == 'title' and await pg.locator('.wpick').count() == 0)
    got = [u for u, _ in reqs if any(u.endswith(f) for f in WORLD_FILES)]
    check(f'[{tag}] none of the new world is fetched', not got, got)
    ls = await pg.evaluate(LS)
    check(f'[{tag}] nothing of it is stored', 'wi_world' not in ls, list(ls))
    await c.close()


async def flag_on(b, w, h, errs):
    tag = f'on {w}x{h}'
    # ---- a new pupil: no character, level 1, no focus ----
    c, pg, reqs = await page(b, w, h, errs)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(400)
    W = await pg.evaluate('window.__world')
    check(f'[{tag}] new pupil: the dock asks to choose a character; level 1, no focus', W['avatar'] is None and W['energy']['level'] == 1 and W['energy']['points'] == 0 and W['focus'] is None and 'בוחרים דמות' in await pg.inner_text('.wd'), W)
    box = await pg.evaluate("(()=>{const d=document.querySelector('.wd').getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect(),isl=[...document.querySelectorAll('.isl')].map(e=>e.getBoundingClientRect());return {inside:d.bottom<=s.bottom+1&&d.top>=s.top,over:isl.filter(r=>r.bottom>d.top+1&&r.top<d.bottom).length}})()")
    check(f'[{tag}] the dock is on the screen and no island lies under it', box['inside'] and box['over'] == 0, box)
    await pg.click('.wd__me'); await pg.wait_for_selector('.wpick__grid')
    av = await pg.evaluate("[...document.querySelectorAll('.wpick__av')].map(b=>({id:b.dataset.id,locked:b.classList.contains('is-locked')}))")
    check(f'[{tag}] picker: the 20 characters, the four rewards locked at level 1', len(av) == 20 and sorted(a['id'] for a in av if a['locked']) == ['octopus', 'penguin', 'pilot', 'robot-bell'], av)
    await P.shot(pg, f'world-picker-{w}x{h}')
    await pg.click('.wpick__av[data-id=penguin]'); await pg.wait_for_timeout(100)
    check(f'[{tag}] a locked character explains when it opens and is not chosen', 'ברמת אנרגיה 3' in await pg.inner_text('.wpick__note') and await pg.locator('.wpick__av.is-selected').count() == 0)
    await pg.click('.wpick__ok', force=True); await pg.wait_for_timeout(100)      # aria-disabled: still pressable, it explains
    check(f'[{tag}] "next" without a character asks for one first', await pg.locator('.wpick__spin').count() == 0 and 'קודם בוחרים דמות' in await pg.inner_text('.wpick__why'))
    await pg.click('.wpick__av[data-id=fox]'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
    await pg.locator('.wpick__spin').nth(0).locator('.wpick__arrow').nth(1).click()
    await pg.locator('.wpick__spin').nth(1).locator('.wpick__arrow').nth(1).click(); await pg.locator('.wpick__spin').nth(1).locator('.wpick__arrow').nth(1).click()
    check(f'[{tag}] name: the arrows step through the two lists', (await pg.inner_text('.wpick__name')).strip() == 'Sweet Piano', await pg.inner_text('.wpick__name'))
    await P.shot(pg, f'world-name-{w}x{h}')
    await pg.click('.wpick__ok'); await pg.wait_for_selector('.wd__pic'); await pg.wait_for_timeout(300)
    ls = await pg.evaluate(LS)
    rec = json.loads(ls.get('wi_world', 'null') or 'null')
    check(f'[{tag}] the choice is kept in wi_world as an id and two indexes', rec == {'v': 1, 'p': {'local': {'av': 'fox', 'nm': [1, 2], 'en': 0}}}, rec)
    check(f'[{tag}] and not in the progress record', 'fox' not in ls.get('aam-unit1-v1', '') and 'Piano' not in ls.get('aam-unit1-v1', ''))
    check(f'[{tag}] the map shows the character and its name (one word per line)', 'Sweet Piano' in ' '.join((await pg.inner_text('.wd__hi')).split()))
    clip = await pg.evaluate("[...document.querySelectorAll('.wd__hi bdi')].map(e=>e.scrollWidth>e.clientWidth+1)")
    check(f'[{tag}] neither word of the name is cut off', clip and not any(clip), clip)
    await pg.click('.wd__en'); await pg.wait_for_timeout(100)
    check(f'[{tag}] the energy chip explains energy', 'אף פעם לא נגמרת' in await pg.inner_text('.wd__note') and await pg.locator('.wd__note:visible').count() == 1)
    await c.close()

    # ---- a pupil with progress: energy from what was learned, focus on island 1 ----
    c, pg, reqs = await page(b, w, h, errs, SEED)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(400)
    W = await pg.evaluate('window.__world')
    check(f'[{tag}] energy: 10 per star, 5 per word known, 5 per story read (11 stars, 1 word, 1 story = 120, level 2)', W['energy']['points'] == 120 and W['energy']['level'] == 2, W['energy'])
    check(f'[{tag}] focus: island 1, the three words of its list got wrong and not known yet', W['focus'] and W['focus']['island'] == 1 and W['focus']['count'] == 3, W['focus'])
    await P.shot(pg, f'world-map-{w}x{h}')
    # energy only goes up: the pupil forgets a word and loses stars on this device; the energy stays
    await pg.evaluate("(()=>{const S=__game.S();S.w.song=0;S.g.st['2-sling']=0;S.read={}})()")
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings'); await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    W2 = await pg.evaluate('window.__world')
    check(f'[{tag}] energy never goes down', W2['energy']['points'] == 120 and W2['energy']['level'] == 2, W2['energy'])
    await pg.click('.wd__focus'); await pg.wait_for_selector('.lvrow')
    check(f'[{tag}] today\'s focus takes the pupil to that island', await pg.evaluate('location.hash') == '#island/1')
    await c.close()


# contrast of every visible text in the new world's parts, against the first opaque background behind it, and the size of
# every button in them; over the whole page, not only the dock (docs/LESSONS.md 8)
AUDIT = """(()=>{const lum=c=>{const m=c.match(/[\\d.]+/g).map(Number);const f=v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4};return [.2126*f(m[0])+.7152*f(m[1])+.0722*f(m[2]),m[3]===undefined?1:m[3]]};
 const bg=e=>{for(;e;e=e.parentElement){const c=getComputedStyle(e).backgroundColor,[l,a]=lum(c);if(a>.9)return l}return 1};
 const bad=[],small=[];
 for(const e of document.querySelectorAll('.wd *,.wd__note,.wpick *')){const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;
  if([...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())){const [l]=lum(getComputedStyle(e).color),b=bg(e),k=(Math.max(l,b)+.05)/(Math.min(l,b)+.05);if(k<4.5)bad.push(e.className+' '+k.toFixed(2)+' '+e.textContent.trim().slice(0,20))}
  if(e.tagName==='BUTTON'&&(r.height<44||r.width<44))small.push(e.className+' '+Math.round(r.width)+'x'+Math.round(r.height))}
 return {bad,small}})()"""


async def all_switches(b, w, h, errs):
    """the new look with every other switch on (games, help, card, sheet): the dock and the picker still read and fit"""
    tag = f'all switches {w}x{h}'
    c, pg, reqs = await page(b, w, h, errs, SEED)
    await pg.goto(P.BASE + '?ds=1&games=1&help=1&card=1&sheet=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(500)
    a = await pg.evaluate(AUDIT)
    check(f'[{tag}] map dock: every text at least 4.5:1, every button at least 44 px', not a['bad'] and not a['small'], a)
    box = await pg.evaluate("(()=>{const d=document.querySelector('.wd').getBoundingClientRect();const o=[...document.querySelectorAll('.isl,.subjpill,.maphead button,.fin,.compass')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.bottom>d.top+1&&r.top<d.bottom-1&&r.right>d.left&&r.left<d.right}).map(e=>e.className);return o})()")
    check(f'[{tag}] nothing of the map lies under the dock', not box, box)
    await pg.click('.wd__en'); await pg.wait_for_timeout(100)
    a = await pg.evaluate(AUDIT)
    check(f'[{tag}] the energy note reads', not a['bad'], a)
    await P.shot(pg, f'world-map-all-{w}x{h}')
    await pg.click('.wd__me'); await pg.wait_for_selector('.wpick__grid'); await pg.wait_for_timeout(300)
    a = await pg.evaluate(AUDIT)
    check(f'[{tag}] picker: every text at least 4.5:1, every button at least 44 px', not a['bad'] and not a['small'], a)
    await pg.click('.wpick__av[data-id=owl]'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
    a = await pg.evaluate(AUDIT)
    check(f'[{tag}] name step: every text at least 4.5:1, every button at least 44 px', not a['bad'] and not a['small'], a)
    await P.shot(pg, f'world-name-all-{w}x{h}')
    await c.close()


async def class_mode(b, errs):
    api = f'http://127.0.0.1:{P.API_PORT}/'
    c, pg, reqs = await page(b, 390, 844, errs, api=api)
    await pg.goto(P.BASE); await pg.wait_for_selector('#lc')
    r = await pg.evaluate(POST, [api, {'a': 'register', 'c': CLASS, 'n': 'נועה', 'p': '1357'}])
    check('class: a pupil registers on the mock backend', r.get('ok'), r)
    await c.close()
    c, pg, reqs = await page(b, 390, 844, errs, SEED, api=api, user={'c': CLASS, 'n': 'נועה', 'p': '1357'})
    await pg.goto(P.BASE + '?ds=1#avatar'); await pg.wait_for_selector('.wpick__grid')
    await pg.click('.wpick__av[data-id=owl]'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
    await pg.click('.wpick__ok'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    await pg.evaluate('__game.push()'); await pg.wait_for_timeout(800)
    ls = await pg.evaluate(LS)
    rec = json.loads(ls.get('wi_world', 'null') or 'null')
    key = 'h:' + hashlib.sha256(f'wi|{CLASS}|נועה'.encode()).hexdigest()
    check('class: the record is kept per pupil, under a SHA-256 of class and name', rec and list(rec['p']) == [key] and rec['p'][key]['av'] == 'owl', rec)
    raw = ls.get('wi_world', '')
    check('class: neither the class code nor the name is in the stored record', CLASS not in raw and 'נועה' not in raw and CLASS.lower() not in raw, raw[:120])
    sent = [(u, d) for u, d in reqs if u.startswith(api)]
    check('class: the game talked to the backend (a save went out)', any('"save"' in d for _, d in sent), [d[:60] for _, d in sent])
    bad = [d[:120] for _, d in sent if any(x in d for x in ('owl', 'wi_world', '"av"', '"nm"', '"en"'))]
    check('class: nothing of the character, its name or the energy reaches the backend', not bad, bad)
    await c.close()
    # the same pupil, the class code typed in lower case and the name with stray spaces: the same record
    c, pg, reqs = await page(b, 390, 844, errs, SEED, api=api, user={'c': CLASS.lower(), 'n': '  נועה ', 'p': '1357'})
    await pg.add_init_script("if(!sessionStorage.getItem('w2')){sessionStorage.setItem('w2','1');localStorage.setItem('wi_world',%s)}" % json.dumps(raw))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    W = await pg.evaluate('window.__world')
    check('class: the same pupil with the code in another case finds the same character', W['key'] == key and W['avatar'] == 'owl', W)
    await c.close()


async def damaged(b, errs):
    """a damaged or edited wi_world never breaks the map, and a huge energy is read as the cap, quickly"""
    for name, raw in (('not JSON', '{oops'), ('records in a list', '{"v":1,"p":[1,2]}'),
                      ('wrong values', '{"v":1,"p":{"local":{"av":"<img src=x onerror=alert(1)>","nm":["a",99],"en":"999"}}}'),
                      ('huge energy', '{"v":1,"p":{"local":{"av":"fox","nm":[0,0],"en":1e300}}}'),
                      ('prototype key', '{"v":1,"p":{"__proto__":{"av":"fox"},"constructor":1}}')):
        c, pg, reqs = await page(b, 390, 844, errs, SEED)
        await pg.add_init_script("if(!sessionStorage.getItem('w')){sessionStorage.setItem('w','1');localStorage.setItem('wi_world',%s)}" % json.dumps(raw))
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd', timeout=5000); await pg.wait_for_timeout(200)
        W = await pg.evaluate('window.__world')
        if name == 'huge energy':
            check(f'damaged wi_world ({name}): the map opens, energy read as the cap 100000, level worked out (403)', W['energy']['points'] == 100000 and W['energy']['level'] == 403 and W['avatar'] == 'fox', W['energy'])
        else:
            check(f'damaged wi_world ({name}): the map opens with no character, energy from what was learned', W['avatar'] is None and W['name'] is None and W['energy']['points'] == 120 and not await pg.evaluate('window.__pwned||false'), W)
        await c.close()


async def no_digest(b, errs):
    """a browser without crypto.subtle: signed in, no character can be kept, and the dock says so instead of offering one"""
    api = f'http://127.0.0.1:{P.API_PORT}/'
    c, pg, reqs = await page(b, 390, 844, errs, SEED, api=api, user={'c': CLASS, 'n': 'נועה', 'p': '1357'})
    await pg.add_init_script("try{Object.defineProperty(window.crypto,'subtle',{get:()=>undefined,configurable:true})}catch(e){}")
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    t = await pg.inner_text('.wd')
    check('no digest: the dock says, kindly, that there are no characters on this phone; no picker, no "?" ring', 'אין דמויות' in t and 'משחקים כרגיל' in t and await pg.locator('button.wd__me').count() == 0 and await pg.locator('.wd__pic').count() == 0, t)
    await pg.evaluate("location.hash='avatar'"); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(200)
    check('no digest: #avatar goes back to the map', await pg.locator('.wpick').count() == 0)
    check('no digest: nothing is stored', 'wi_world' not in await pg.evaluate(LS))
    await c.close()


async def name_with_focus(b, errs):
    """the longest name next to today's focus on a narrow phone; a stray record key is dropped on the next write;
    the sync bar's class comes and goes with the dock"""
    rec = {'v': 1, 'p': {'local': {'av': 'fox', 'nm': [1, 6], 'en': 0}, 'c:EN-1234|נועה': {'av': 'owl'}, 'junk': 1}}
    for w, h in ((360, 740), (390, 844)):
        c, pg, reqs = await page(b, w, h, errs, SEED)
        await pg.add_init_script("if(!sessionStorage.getItem('w')){sessionStorage.setItem('w','1');localStorage.setItem('wi_world',%s)}" % json.dumps(json.dumps(rec, ensure_ascii=False)))
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd__focus'); await pg.wait_for_timeout(300)
        clip = await pg.evaluate("[...document.querySelectorAll('.wd__hi bdi')].map(e=>[e.textContent,e.scrollWidth>e.clientWidth+1])")
        check(f'[{w}x{h}] with the focus showing, "Sweet Present" is whole', [x[0] for x in clip] == ['Sweet', 'Present'] and not any(x[1] for x in clip), clip)
        check(f'[{w}x{h}] the dock marks #stage for the sync bar', await pg.evaluate("document.getElementById('stage').classList.contains('wdock')"))
        await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings')
        check(f'[{w}x{h}] and the mark is gone on the next screen', not await pg.evaluate("document.getElementById('stage').classList.contains('wdock')"))
        if w == 360:
            await pg.evaluate("location.hash='avatar'"); await pg.wait_for_selector('.wpick__grid'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
            await pg.click('.wpick__ok'); await pg.wait_for_selector('.map .wd')
            keys = list(json.loads((await pg.evaluate(LS))['wi_world'])['p'])
            check('a write keeps only well-formed record keys (local, h:...), the stray ones are dropped', keys == ['local'], keys)
        await c.close()


async def brand(b, errs):
    """the platform's name (docs/PLAN.md, 25.11.2026): "ניצני אופק" with the flag, "איי המילים" without it; the English
    world keeps "איי המילים" either way"""
    for ds in (False, True):
        tag = 'flag on' if ds else 'flag off'
        c, pg, reqs = await page(b, 390, 844, errs)
        await pg.goto(P.BASE + ('?ds=1' if ds else '')); await pg.wait_for_selector('.title .btn'); await pg.wait_for_timeout(300)
        r = await pg.evaluate("({title:document.title,h1:document.querySelector('.title .logo h1').textContent,sub:document.querySelector('.title .logo p').textContent,en:document.querySelector('.title [data-to=map] small').textContent})")
        if ds:
            check(f'[{tag}] the title screen and the page say ניצני אופק, with a welcome line', r['title'] == 'ניצני אופק' and r['h1'] == 'ניצני אופק' and r['sub'] == 'ברוכים הבאים לניצני אופק', r)
        else:
            check(f'[{tag}] the title screen and the page keep איי המילים, as today', r['title'] == 'איי המילים' and r['h1'] == 'איי המילים' and r['sub'] == 'Word Islands · All About Me', r)
        check(f'[{tag}] the English world is still איי המילים', r['en'].startswith('איי המילים'), r['en'])
        await c.close()
    api = f'http://127.0.0.1:{P.API_PORT}/'
    for ds in (False, True):
        c, pg, reqs = await page(b, 390, 844, errs, api=api)
        await pg.goto(P.BASE + ('?ds=1' if ds else '') + '#login'); await pg.wait_for_selector('.login .logo h1')
        h = await pg.inner_text('.login .logo h1')
        check(f"[{'flag on' if ds else 'flag off'}] the login screen says {'ניצני אופק' if ds else 'איי המילים'}", h == ('ניצני אופק' if ds else 'איי המילים'), h)
        await P.shot(pg, f"brand-login-{'ds' if ds else 'off'}")
        await c.close()


async def finished(b, errs):
    """every level played: the all-played banner sits above the dock, both whole on the screen"""
    st = {f'{i}-{t}': 2 for i, ts in ((1, 'sling listen read bridge'), (2, 'sling listen read bridge'), (3, 'sling listen read bridge'), (4, 'sling listen read bridge'), (5, 'sling listen read bridge'), (6, 'sling listen')) for t in ts.split()}
    for w, h in ((390, 844), (360, 740), (320, 568), (1366, 768)):
        c, pg, reqs = await page(b, w, h, errs, {'g': {'st': st}})
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(400)
        r = await pg.evaluate("(()=>{const f=document.querySelector('.fin'),d=document.querySelector('.wd'),s=document.getElementById('stage').getBoundingClientRect();if(!f)return null;const a=f.getBoundingClientRect(),b=d.getBoundingClientRect();return {clear:a.bottom<=b.top+1,inside:a.top>=s.top&&b.bottom<=s.bottom+1}})()")
        if (w, h) == (320, 568):      # too short for the banner, the dock and six islands: the banner is left out (worldFits in js/main.js)
            check(f'[finished {w}x{h}] the all-played banner is left out on a phone this short; the islands keep their rings', r is None and await pg.locator('.isl.todo').count() > 0, r)
        else:
            check(f'[finished {w}x{h}] the all-played banner shows above the dock, both on the screen', r and r['clear'] and r['inside'], r)
        # a tap anywhere on an island's picture lands on that island (centre, top quarter, bottom quarter), and labels do not lie over another island's picture
        taps = await pg.evaluate("""(()=>[...document.querySelectorAll('.isl')].map(b=>{const id=[...b.classList].find(c=>/^i\\d$/.test(c)),r=b.querySelector('.pic').getBoundingClientRect(),x=r.left+r.width/2;
          return [r.top+r.height*.5,r.top+r.height*.25+2,r.top+r.height*.75].map(y=>{const e=document.elementFromPoint(x,y),hit=e&&e.closest('.isl');return hit&&hit.classList.contains(id)?null:id+'@'+Math.round(y)+'->'+(hit?[...hit.classList].find(c=>/^i\\d$/.test(c)):e&&e.className)})}).flat().filter(Boolean))()""")
        check(f'[finished {w}x{h}] a tap on each island\'s picture opens that island', not taps, taps)
        over = await pg.evaluate("""(()=>{const tags=[...document.querySelectorAll('.isl .tag')],pics=[...document.querySelectorAll('.isl .pic')],out=[];
          for(const t of tags){const a=t.getBoundingClientRect(),own=t.closest('.isl');for(const p of pics){if(p.closest('.isl')===own)continue;const b=p.getBoundingClientRect(),dy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top),dx=Math.min(a.right,b.right)-Math.max(a.left,b.left);if(dy>2&&dx>2)out.push([...own.classList].find(c=>/^i\\d$/.test(c))+' over '+[...p.closest('.isl').classList].find(c=>/^i\\d$/.test(c))+' by '+Math.round(dy))}}return out})()""")
        check(f'[finished {w}x{h}] no island label lies over another island\'s picture', not over, over)
        await P.shot(pg, f'world-finished-{w}x{h}')
        await c.close()


async def main():
    procs = P.start_servers(mock=True)      # its own servers on free ports (tests/play.py)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            for w, h in ((390, 844), (360, 740), (1366, 768)):
                await flag_off(b, w, h, errs)
                await flag_on(b, w, h, errs)
                await all_switches(b, w, h, errs)
            await class_mode(b, errs)
            await damaged(b, errs)
            await no_digest(b, errs)
            await name_with_focus(b, errs)
            await finished(b, errs)
            await brand(b, errs)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
