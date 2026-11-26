#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The new world in the live game behind the design flag (?ds=1, js/avatar.js): character, its name, energy, today's focus.

    python3 tests/world.py              # phone and laptop
    python3 tests/world.py --shots DIR  # also save PNGs of the map dock and the picker

Flag off: nothing of it is fetched, drawn or stored, and #avatar is an unknown address as before (the title screen). Flag on: the map has the dock;
the picker shows the 20 characters, 8 open at level 1 and one more per level up to 13 (a chosen one is kept);
a newly opened character is announced once on the map; names come only from the two fixed lists (version 2); the choice and the name (two indexes into
the fixed lists, never text) are kept in the wi_world key on the device only, never in the progress record and never
in a request to the backend (checked against the mock backend in class mode); energy only goes up; today's focus names
the open island with the most words to fix and takes the pupil there."""
import asyncio, hashlib, json, os, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, fails

CLASS = 'EN-1234'      # the mock backend's own test class
STARTERS = ['girl-curls', 'boy-cap', 'girl-braids', 'boy-curls', 'girl-glasses', 'boy-blond', 'girl-ponytail', 'boy-scarf']   # the human kids: always open
LADDER = ['fox', 'cat', 'turtle', 'owl', 'parrot', 'robot-box', 'diver', 'penguin', 'shark', 'octopus', 'robot-bell', 'pilot']   # levels 2 to 13
LEVELS = [0, 40, 90, 150, 220, 300, 380, 460, 540, 620, 700, 760, 820, 890, 950, 1020, 1080, 1150, 1220, 1280, 1350, 1410, 1480]   # js/world_data.js ENERGY
OLD_LEVELS = LEVELS[:13]   # the ladder before Fraction Bay counted (13 levels, then one per 250)


def old_level(pts):
    return 13 + (pts - 820) // 250 if pts >= 820 else next(k for k, t in enumerate(OLD_LEVELS) if t > pts)
POST = "async ([api,d])=>(await fetch(api,{method:'POST',body:JSON.stringify(d)})).json()"
WORLD_FILES = ('js/avatar.js', 'css/avatar.css', 'js/world_data.js', 'js/world_art.js', 'js/avanim.js')
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


async def tap_to_open(pg, sel, route):
    """click a stone and return the time from the tap to the level's address, in the page's own clock (the tap's event
    time to the hashchange), so a busy test machine's round trips do not count"""
    await pg.evaluate("""(()=>{window.__tt={};if(!window.__ttOn){window.__ttOn=1;
      addEventListener('click',e=>{if(e.target.closest&&e.target.closest('.w-st'))__tt.tap=e.timeStamp},true);
      addEventListener('hashchange',()=>{if(location.hash.startsWith('#play/')&&__tt.tap!==undefined&&__tt.hc===undefined)__tt.hc=performance.now()})}})()""")
    await pg.click(sel)
    await pg.wait_for_function("window.__tt.hc!==undefined", timeout=5000)
    assert await pg.evaluate('location.hash') == '#' + route, await pg.evaluate('location.hash')
    t = await pg.evaluate('window.__tt')
    return t['hc'] - t['tap']


async def to_path(pg, isl):
    """an island's path, the way a child gets there: from the map, once the map has fetched the path's pictures
    (window.__world.pathArt, a promise: no wall-clock wait), then the island"""
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    ok = await pg.evaluate('window.__world.pathArt')
    check_ok = ok is True
    if not check_ok:
        raise AssertionError(f'the map did not fetch the path pictures: {ok}')
    await pg.evaluate(f"location.hash='island/{isl}'"); await pg.wait_for_selector('.w-path .w-st')


async def flag_off(b, w, h, errs):
    tag = f'off {w}x{h}'
    c, pg, reqs = await page(b, w, h, errs, SEED)
    await pg.goto(P.BASE + '#map'); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(600)
    check(f'[{tag}] the map has no dock and no character on it', await pg.locator('.wd').count() == 0 and await pg.locator('.wtok').count() == 0)
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
    check(f'[{tag}] picker: the 20 characters, the 8 human kids open at level 1, the other 12 locked', len(av) == 20 and [a['id'] for a in av if not a['locked']] == STARTERS and [a['id'] for a in av if a['locked']] == LADDER, av)
    lab = await pg.evaluate("[...document.querySelectorAll('.wpick__av.is-locked')].map(b=>[b.querySelector('.wpick__lock').textContent,b.getAttribute('aria-disabled'),/אפשר לפתוח ברמה/.test(b.getAttribute('aria-label')),!!b.querySelector('.wpick__key')])")
    check(f'[{tag}] a locked tile shows a lock and "רמה N", says the whole sentence to a screen reader, and is not selectable', lab == [[f'רמה {n}', 'true', True, True] for n in range(2, 14)], lab)
    seen = await pg.evaluate(BADGES)
    check(f'[{tag}] the character on a locked tile is in view (0.7) and its badge is one line inside the tile, nothing cut off', not seen['bad'] and seen['op'] == ['0.7'], seen)
    await P.shot(pg, f'world-picker-{w}x{h}')
    await pg.click('.wpick__av[data-id=penguin]', force=True); await pg.wait_for_timeout(100)   # aria-disabled: a tap still reaches it, and it explains
    t = await pg.inner_text('.wpick__note')
    check(f'[{tag}] a tap on a locked character says kindly how to get there (one neutral form, no gender slash), and does not choose it', 'אפשר לפתוח ברמה 9' in t and 'עוד 8 רמות' in t and 'אף פעם לא מפסידים' in t and '/' not in t and await pg.locator('.wpick__av.is-selected').count() == 0, t)
    await pg.click('.wpick__ok', force=True); await pg.wait_for_timeout(100)      # aria-disabled: still pressable, it explains
    check(f'[{tag}] "next" without a character asks for one first', await pg.locator('.wpick__spin').count() == 0 and 'קודם בוחרים דמות' in await pg.inner_text('.wpick__why'))
    await pg.click('.wpick__av[data-id=girl-curls]'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
    await pg.locator('.wpick__spin').nth(0).locator('.wpick__arrow').nth(1).click()
    await pg.locator('.wpick__spin').nth(1).locator('.wpick__arrow').nth(1).click(); await pg.locator('.wpick__spin').nth(1).locator('.wpick__arrow').nth(1).click()
    check(f'[{tag}] name: the arrows step through the two lists', (await pg.inner_text('.wpick__name')).strip() == 'Happy Tiger', await pg.inner_text('.wpick__name'))
    await P.shot(pg, f'world-name-{w}x{h}')
    await pg.click('.wpick__ok'); await pg.wait_for_selector('.wd__pic'); await pg.wait_for_timeout(300)
    ls = await pg.evaluate(LS)
    rec = json.loads(ls.get('wi_world', 'null') or 'null')
    check(f'[{tag}] the choice is kept in wi_world as an id, two indexes and the lists\' version (and the level already announced, and the island it stands on)', rec == {'v': 1, 'p': {'local': {'av': 'girl-curls', 'nm': [1, 2], 'nv': 2, 'en': 0, 'sl': 1, 'at': 1}}}, rec)
    check(f'[{tag}] and not in the progress record', 'girl-curls' not in ls.get('aam-unit1-v1', '') and 'Tiger' not in ls.get('aam-unit1-v1', ''))
    check(f'[{tag}] the map shows the character and its name (one word per line)', 'Happy Tiger' in ' '.join((await pg.inner_text('.wd__hi')).split()))
    clip = await pg.evaluate("[...document.querySelectorAll('.wd__hi bdi')].map(e=>e.scrollWidth>e.clientWidth+1)")
    check(f'[{tag}] neither word of the name is cut off', clip and not any(clip), clip)
    await pg.click('.wd__en'); await pg.wait_for_timeout(100)
    check(f'[{tag}] the energy chip explains energy', 'אף פעם לא נגמרת' in await pg.inner_text('.wd__note') and await pg.locator('.wd__note:visible').count() == 1)
    await c.close()

    # ---- a pupil with progress: energy from what was learned, focus on island 1 ----
    c, pg, reqs = await page(b, w, h, errs, SEED)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(400)
    W = await pg.evaluate('window.__world')
    check(f'[{tag}] energy: 10 per star, 5 per word known, 5 per story read (11 stars, 1 word, 1 story = 120, level 3)', W['energy']['points'] == 120 and W['energy']['level'] == 3, W['energy'])
    check(f'[{tag}] focus: island 1, the three words of its list got wrong and not known yet', W['focus'] and W['focus']['island'] == 1 and W['focus']['count'] == 3, W['focus'])
    await P.shot(pg, f'world-map-{w}x{h}')
    # energy only goes up: the pupil forgets a word and loses stars on this device; the energy stays
    await pg.evaluate("(()=>{const S=__game.S();S.w.song=0;S.g.st['2-sling']=0;S.read={}})()")
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings'); await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    W2 = await pg.evaluate('window.__world')
    check(f'[{tag}] energy never goes down', W2['energy']['points'] == 120 and W2['energy']['level'] == 3, W2['energy'])
    await pg.click('.wd__focus'); await pg.wait_for_selector('.w-path .w-st')      # with the flag the island is a path of stones
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
    await pg.click('.wpick__av[data-id=girl-braids]'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
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
    await pg.click('.wpick__av[data-id=girl-braids]'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
    await pg.click('.wpick__ok'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    await pg.evaluate('__game.push()'); await pg.wait_for_timeout(800)
    ls = await pg.evaluate(LS)
    rec = json.loads(ls.get('wi_world', 'null') or 'null')
    key = 'h:' + hashlib.sha256(f'wi|{CLASS}|נועה'.encode()).hexdigest()
    check('class: the record is kept per pupil, under a SHA-256 of class and name', rec and list(rec['p']) == [key] and rec['p'][key]['av'] == 'girl-braids', rec)
    raw = ls.get('wi_world', '')
    check('class: neither the class code nor the name is in the stored record', CLASS not in raw and 'נועה' not in raw and CLASS.lower() not in raw, raw[:120])
    sent = [(u, d) for u, d in reqs if u.startswith(api)]
    check('class: the game talked to the backend (a save went out)', any('"save"' in d for _, d in sent), [d[:60] for _, d in sent])
    bad = [d[:120] for _, d in sent if any(x in d for x in ('girl-braids', 'wi_world', '"av"', '"nm"', '"en"'))]
    check('class: nothing of the character, its name or the energy reaches the backend', not bad, bad)
    await c.close()
    # the same pupil, the class code typed in lower case and the name with stray spaces: the same record
    c, pg, reqs = await page(b, 390, 844, errs, SEED, api=api, user={'c': CLASS.lower(), 'n': '  נועה ', 'p': '1357'})
    await pg.add_init_script("if(!sessionStorage.getItem('w2')){sessionStorage.setItem('w2','1');localStorage.setItem('wi_world',%s)}" % json.dumps(raw))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    W = await pg.evaluate('window.__world')
    check('class: the same pupil with the code in another case finds the same character', W['key'] == key and W['avatar'] == 'girl-braids', W)
    await c.close()


async def damaged(b, errs):
    """a damaged or edited wi_world never breaks the map, and a huge energy is read as the cap, quickly"""
    for name, raw in (('not JSON', '{oops'), ('records in a list', '{"v":1,"p":[1,2]}'),
                      ('wrong values', '{"v":1,"p":{"local":{"av":"<img src=x onerror=alert(1)>","nm":["a",99],"en":"999"}}}'),
                      ('huge energy', '{"v":1,"p":{"local":{"av":"fox","nm":[0,0],"en":1e300}}}'),
                      ('prototype key', '{"v":1,"p":{"__proto__":{"av":"fox"},"constructor":1}}'),
                      ('bad version and level', '{"v":1,"p":{"local":{"nv":"2","nm":[1,1],"sl":"<b>x</b>"}}}')):
        c, pg, reqs = await page(b, 390, 844, errs, SEED)
        await pg.add_init_script("if(!sessionStorage.getItem('w')){sessionStorage.setItem('w','1');localStorage.setItem('wi_world',%s)}" % json.dumps(raw))
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd', timeout=5000); await pg.wait_for_timeout(200)
        W = await pg.evaluate('window.__world')
        if name == 'huge energy':
            check(f'damaged wi_world ({name}): the map opens, energy read as the cap 100000, level worked out (417: 23 + (100000 - 1480) // 250)', W['energy']['points'] == 100000 and W['energy']['level'] == 23 + (100000 - 1480) // 250 and W['avatar'] == 'fox', W['energy'])
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
    check('no digest: the dock says, kindly, that there are no characters on this phone; no picker, no "?" ring', 'במכשיר הזה אין דמויות' in t and 'משחקים כרגיל' in t and await pg.locator('button.wd__me').count() == 0 and await pg.locator('.wd__pic').count() == 0, t)
    await pg.evaluate("location.hash='avatar'"); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(200)
    check('no digest: #avatar goes back to the map', await pg.locator('.wpick').count() == 0)
    check('no digest: nothing is stored', 'wi_world' not in await pg.evaluate(LS))
    await c.close()


async def name_with_focus(b, errs):
    """the longest name next to today's focus on a narrow phone; a stray record key is dropped on the next write;
    the sync bar's class comes and goes with the dock"""
    rec = {'v': 1, 'p': {'local': {'av': 'fox', 'nm': [10, 5], 'nv': 2, 'en': 0}, 'c:EN-1234|נועה': {'av': 'owl'}, 'junk': 1}}
    for w, h in ((360, 740), (390, 844)):
        c, pg, reqs = await page(b, w, h, errs, SEED)
        await pg.add_init_script("if(!sessionStorage.getItem('w')){sessionStorage.setItem('w','1');localStorage.setItem('wi_world',%s)}" % json.dumps(json.dumps(rec, ensure_ascii=False)))
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd__focus'); await pg.wait_for_timeout(300)
        clip = await pg.evaluate("[...document.querySelectorAll('.wd__hi bdi')].map(e=>[e.textContent,e.scrollWidth>e.clientWidth+1])")
        check(f'[{w}x{h}] with the focus showing, the longest name "Mighty Dolphin" is whole', [x[0] for x in clip] == ['Mighty', 'Dolphin'] and not any(x[1] for x in clip), clip)
        check(f'[{w}x{h}] the dock marks #stage for the sync bar', await pg.evaluate("document.getElementById('stage').classList.contains('wdock')"))
        await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings')
        check(f'[{w}x{h}] and the mark is gone on the next screen', not await pg.evaluate("document.getElementById('stage').classList.contains('wdock')"))
        if w == 360:
            await pg.evaluate("location.hash='avatar'"); await pg.wait_for_selector('.wpick__grid'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
            await pg.click('.wpick__ok'); await pg.wait_for_selector('.map .wd')
            keys = list(json.loads((await pg.evaluate(LS))['wi_world'])['p'])
            check('a write keeps only well-formed record keys (local, h:...), the stray ones are dropped', keys == ['local'], keys)
        await c.close()


async def goto_hash(pg, h, sel):
    """go to a screen again (through settings, so the same address draws afresh)"""
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings')
    await pg.evaluate(f"location.hash='{h}'"); await pg.wait_for_selector(sel); await pg.wait_for_timeout(250)


async def set_world(pg, rec):
    await pg.evaluate("r=>localStorage.setItem('wi_world',JSON.stringify({v:1,p:{local:r}}))", rec)


async def notice_clear(b, errs):
    """the new-character notice never covers the character on the map (or Pitzi's "?" badge): for the island played now
    from 1 to 6, one and several new characters, with and without a chosen character, at 390, 360, 320x640 and 320x568.
    It stays between the map's header and the dock, its buttons are 48 px, and on the island screen (the path) there is
    no notice at all"""
    LOOK = """(()=>{const n=document.querySelector('.wnew'),t=document.querySelector('.wtok,.wask');if(!n||!t)return {n:!!n,t:!!t};
      if(t.hidden)return {n:true,t:true,hit:false,band:true,btn:[...n.querySelectorAll('button')].every(x=>x.getBoundingClientRect().height>=48),h:true,island:(window.__world.token||{}).island,tight:false,aside:true};
      const a=n.getBoundingClientRect(),c=t.getBoundingClientRect(),d=document.querySelector('.wd').getBoundingClientRect();
      let top=0;for(const e of document.querySelectorAll('.maphead,.subjpill'))top=Math.max(top,e.getBoundingClientRect().bottom);
      return {n:true,t:true,hit:!(a.right<=c.left||a.left>=c.right||a.bottom<=c.top||a.top>=c.bottom),band:a.top>=top-0.5&&a.bottom<=d.top+0.5,
        btn:[...n.querySelectorAll('button')].every(x=>x.getBoundingClientRect().height>=48),h:!!n.querySelector('.wnew__h').getBoundingClientRect().height,
        island:(window.__world.token||{}).island,tight:n.classList.contains('wnew--tight')}})()"""
    bad, seen, tight, aside = [], set(), [], []
    for w, h in ((390, 844), (360, 740), (320, 640), (320, 568)):
        for done in range(0, 6):
            st = {f'{i}-{t}': 3 for i in range(1, done + 1) for t in ('sling', 'listen', 'read', 'bridge')}
            for av in ('girl-curls', None):
                for sl, en in ((1, LEVELS[1]), (1, LEVELS[5])):   # one new character, then several (3 portraits and "ועוד 2")
                    r = {'en': en, 'sl': sl}
                    if av: r.update({'av': av, 'nm': [0, 0], 'nv': 2})
                    c, pg, reqs = await page(b, w, h, errs, {'g': {'st': st}})
                    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(json.dumps({'v': 1, 'p': {'local': r}})))
                    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wnew'); await pg.wait_for_timeout(400)
                    L = await pg.evaluate(LOOK)
                    seen.add(L.get('island'))
                    if L.get('tight'): tight.append((w, h, L.get('island'), av))
                    if not (L['n'] and L['t'] and not L['hit'] and L['band'] and L['btn'] and L['h']): bad.append((w, h, done, av, sl, en, L))
                    if (w, h, done, av, en) == (320, 568, 1, None, LEVELS[5]): await P.shot(pg, 'world-notice-320x568-tight')
                    if L.get('aside'):
                        aside.append((w, h, L.get('island')))
                        await pg.click('.wnew__later'); await pg.wait_for_timeout(100)
                        back = await pg.evaluate("(()=>{const q=document.querySelector('.wask');return !!q&&!q.hidden&&!document.querySelector('.wnew')})()")
                        if not back: bad.append((w, h, done, av, sl, en, 'the badge did not come back after "אחר כך"'))
                    if (w, h, done, av, en) == (390, 844, 0, 'girl-curls', LEVELS[1]): await P.shot(pg, 'world-notice-390x844-top')
                    await c.close()
    check(f'the notice never covers the character (or the "?" badge), stays between header and dock, 48 px buttons (islands {sorted(x for x in seen if x)})', not bad and {1, 2, 4, 6} <= seen, bad[:3])
    check(f'where no place clears Pitzi\'s "?" badge, it steps aside while the notice (which offers the same choice) is up, and comes back with "אחר כך"; never the character token ({sorted(set(aside))})', all(True for _ in aside) and not [x for x in bad if isinstance(x[-1], str)], aside)
    check('it drops its sentence only where nothing else fits (a short screen)', all(x[1] < 640 for x in tight), tight)
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(json.dumps({'v': 1, 'p': {'local': {'av': 'girl-curls', 'nm': [0, 0], 'nv': 2, 'en': LEVELS[5], 'sl': 1}}})))
    await pg.goto(P.BASE + '?ds=1#island/1'); await pg.wait_for_selector('.w-path .w-st'); await pg.wait_for_timeout(300)
    check('the island screen (the path and its walker) never shows the notice', await pg.locator('.wnew').count() == 0 and await pg.locator('.w-walker').count() == 1)
    await c.close()


async def ladder(b, errs):
    """8 characters at level 1, and each level from 2 to 13 opens exactly the next one; the map says so once, with the
    new character's portrait and a way to the picker; two levels at once say "characters" and show the newest; a device
    that first opens the map at a high level is not told about old news"""
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    bad, shown_twice = [], []
    for L in range(1, 14):
        await set_world(pg, {'en': LEVELS[L - 1], 'sl': max(1, L - 1)})
        await goto_hash(pg, 'map', '.map .wd')
        W = await pg.evaluate('window.__world')
        n = await pg.locator('.wnew').count()
        want = [] if L == 1 else [LADDER[L - 2]]
        if W['energy']['level'] != L or W['fresh'] != want or n != (1 if want else 0): bad.append([L, W['energy']['level'], W['fresh'], n])
        if want:
            if L == 2:
                t = await pg.inner_text('.wnew'); src = await pg.get_attribute('.wnew__pic', 'src')
                check('level 2: the map says "דמות חדשה נפתחה!" with the new character\'s portrait and a button to the picker', 'דמות חדשה נפתחה!' in t and LADDER[0] in src and await pg.locator('.wnew__ok').count() == 1, [t, src])
                await P.shot(pg, 'world-new-character-390x844')
                a = await pg.evaluate(AUDIT.replace(".wd *,.wd__note,.wpick *", ".wnew,.wnew *"))
                check('the notice: every text at least 4.5:1, every button at least 44 px', not a['bad'] and not a['small'], a)
            await goto_hash(pg, 'map', '.map .wd')
            if await pg.locator('.wnew').count(): shown_twice.append(L)
        await pg.evaluate("location.hash='avatar'"); await pg.wait_for_selector('.wpick__grid')
        open_ = await pg.evaluate("[...document.querySelectorAll('.wpick__av:not(.is-locked)')].map(b=>b.dataset.id)")
        if open_ != STARTERS + LADDER[:L - 1]: bad.append([L, 'open', open_])
        await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .wd')
    check('each level from 1 to 13 opens exactly the next character (8 at level 1, all 20 at 13), and the map says it once', not bad, bad)
    check('the notice shows only once for each level', not shown_twice, shown_twice)
    # the notice's buttons
    await set_world(pg, {'en': LEVELS[1], 'sl': 1}); await goto_hash(pg, 'map', '.wnew')
    await pg.click('.wnew__later'); check('"later" closes the notice and stays on the map', await pg.locator('.wnew').count() == 0 and await pg.evaluate('location.hash') == '#map')
    await set_world(pg, {'en': LEVELS[2], 'sl': 2}); await goto_hash(pg, 'map', '.wnew')
    await pg.click('.wnew__ok'); await pg.wait_for_selector('.wpick__grid')
    check('the notice\'s button opens the picker', await pg.evaluate('location.hash') == '#avatar')
    # two levels at once
    await set_world(pg, {'en': LEVELS[4], 'sl': 3}); await goto_hash(pg, 'map', '.wnew')
    W = await pg.evaluate('window.__world')
    check('two levels at once: "דמויות חדשות נפתחו!" with the newest one', W['fresh'] == LADDER[2:4] and 'דמויות חדשות נפתחו!' in await pg.inner_text('.wnew') and LADDER[3] in await pg.get_attribute('.wnew__pic', 'src'), W['fresh'])
    # a jump from level 2 to 7: five new characters, the newest three shown and "ועוד 2"
    await set_world(pg, {'en': LEVELS[6], 'sl': 2}); await goto_hash(pg, 'map', '.wnew')
    J = await pg.evaluate("(()=>({fresh:__world.fresh,pics:[...document.querySelectorAll('.wnew__pic')].map(i=>i.getAttribute('src').split('/').pop().split('.')[0]),more:(document.querySelector('.wnew__more')||{}).textContent||'',t:document.querySelector('.wnew').innerText}))()")
    check('a jump from level 2 to 7: the newest three portraits, "ועוד 2", and how many are waiting', J['fresh'] == LADDER[1:6] and J['pics'] == LADDER[5:2:-1] and J['more'] == 'ועוד 2' and '5 דמויות חדשות מחכות לכם' in J['t'], J)
    a = await pg.evaluate(AUDIT.replace(".wd *,.wd__note,.wpick *", ".wnew,.wnew *"))
    box = await pg.evaluate("(()=>{const r=document.querySelector('.wnew').getBoundingClientRect(),d=document.querySelector('.wd').getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect();return {top:r.top>=s.top,clear:r.bottom<=d.top+1}})()")
    check('the notice with several portraits reads (4.5:1, 44 px), is whole on the screen and above the dock', not a['bad'] and not a['small'] and box['top'] and box['clear'], [a, box])
    await P.shot(pg, 'world-new-characters-390x844')
    # first map visit at a high level: no notice, the level is remembered
    await set_world(pg, {'en': LEVELS[6]}); await goto_hash(pg, 'map', '.map .wd')
    rec = json.loads((await pg.evaluate(LS))['wi_world'])['p']['local']
    check('a device that first opens the map at level 7 is not told about old news; level 7 is remembered', await pg.locator('.wnew').count() == 0 and rec.get('sl') == 7, rec)
    await c.close()


async def loader_look(b, errs):
    """the wait before a level, in the new look: navy over the whole board, the new Pitzi (the old sprite is not
    downloaded), the same words, role=status, an honest "עוד רגע…" only after 5 s, still with reduced motion; without
    the flag the loader is exactly as today"""
    import slow_net as SN
    # when a loader appears and when its extra line appears, recorded by the page itself (no wall-clock guess here)
    REC = "window.__ld=[];new MutationObserver(()=>{const l=document.querySelector('.loader');if(l&&!l.__t){l.__t=1;__ld.push(['loader',performance.now()])}const m=l&&l.querySelector('.loader__more');if(m&&m.textContent&&!l.__m){l.__m=1;__ld.push(['more',performance.now()])}}).observe(document,{subtree:true,childList:true,characterData:true})"
    for ds, reduce in ((True, False), (True, True), (False, False)):
        c, pg, reqs = await page(b, 390, 844, [], {'g': {'st': {'1-sling': 3}}})
        if reduce: await pg.emulate_media(reduced_motion='reduce')
        await pg.add_init_script(REC)
        cdp = await c.new_cdp_session(pg); await cdp.send('Network.enable')
        await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': SN.PROFILE['latency'], 'downloadThroughput': SN.PROFILE['down'], 'uploadThroughput': SN.PROFILE['up']})
        await pg.goto(P.BASE + ('?ds=1' if ds else '') + '#play/1/listen', wait_until='commit')
        # the play loader only (the boot one, before the style sheets are in, can be in the old look on a slow phone)
        await pg.wait_for_function("((document.getElementById('stage')||{}).dataset||{}).scr==='play'&&!!document.querySelector('.loader')", timeout=90000); await pg.wait_for_timeout(500)
        LAY = "(()=>{const l=document.querySelector('.loader');if(!l)return null;const i=l.querySelector('img'),t=l.querySelector('p');return [i.offsetTop,i.offsetLeft,t.offsetTop,t.offsetLeft]})()"   # layout boxes: the bob (a transform) does not count
        pz0 = await pg.evaluate(LAY)
        L = await pg.evaluate("""(()=>{const l=document.querySelector('.loader'),r=l.getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect(),i=l.querySelector('img'),cs=getComputedStyle(l);
          return {cover:Math.abs(r.left-s.left)<1&&Math.abs(r.top-s.top)<1&&Math.abs(r.width-s.width)<1&&Math.abs(r.height-s.height)<1,bg:cs.backgroundColor,role:l.getAttribute('role'),
            text:l.querySelector('p').textContent,more:!!l.querySelector('.loader__more'),art:getComputedStyle(i).backgroundImage,anim:getComputedStyle(i).animationName,srcset:!!i.getAttribute('srcset')}})()""")
        old = [u for u, _ in reqs if u.endswith('/assets/sp/crab_wave.webp')]
        await pg.wait_for_timeout(6000)
        pz1 = await pg.evaluate(LAY)
        ld = await pg.evaluate('window.__ld')
        t = dict(ld); more = (t['more'] - t['loader']) if 'more' in t and 'loader' in t else None
        at58 = await pg.evaluate("(()=>{const m=document.querySelector('.loader .loader__more');return m?m.textContent:null})()")
        at46 = more is not None and more < 4900
        if ds:
            tag = 'reduced motion' if reduce else 'motion'
            check(f'[loader, new look, {tag}] navy (--wi-navy-900) over the whole board', L['cover'] and L['bg'] == 'rgb(11, 30, 63)', L)
            check(f'[loader, new look, {tag}] the new Pitzi is drawn (the loader\'s old picture has its stand-in, so the loader itself asks for no old crab; play() still preloads CORE, item (b)); same words; role=status', 'pitzi/wave' in L['art'] and L['srcset'] and L['text'] == 'רגע, מפליגים…' and L['role'] == 'status', L)
            check(f'[loader, new look, {tag}] nothing moves when "עוד רגע…" appears (Pitzi and the words stay where they were)', pz1 is not None and all(abs(x - y) < 0.5 for x, y in zip(pz0, pz1)), (pz0, pz1))
            check(f'[loader, new look, {tag}] "עוד רגע…" only after 5 s of waiting (measured by the page: 5.0 to 5.6 s after the loader)', more is not None and 4990 <= more <= 5600 and at58 == 'עוד רגע…', (more, at58))
            if reduce:
                check('[loader, new look, reduced motion] Pitzi does not bob', L['anim'] == 'none', L['anim'])
            else:
                a = await pg.evaluate(AUDIT.replace(".wd *,.wd__note,.wpick *", ".loader p"))
                check('[loader, new look] its words at least 4.5:1', not a['bad'], a['bad'])
                await P.shot(pg, 'world-loader-390x844')
        else:
            check('[loader, flag off] exactly as today: no role, no extra line after 5 s, the old background', L['role'] is None and not L['more'] and at58 is None and L['bg'] == 'rgba(255, 244, 222, 0.6)', L)
        await c.close()


async def reachable(b, errs):
    """the ladder fits what a pupil can earn: the level that opens the last character (and the last "soon" level) is
    reachable with today's content, and needs both subjects (above what English alone gives); levels 1 to 13 never moved"""
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    R = await pg.evaluate("""async()=>{const A=await import('./js/avatar.js'),D=await import('./js/world_data.js');const top=Math.max(...D.AVATARS.map(a=>a.open),...D.SOON);
      const lv=p=>p>=A.LEVELS[A.LEVELS.length-1]?A.LEVELS.length+Math.floor((p-A.LEVELS[A.LEVELS.length-1])/D.ENERGY.after):A.LEVELS.findIndex(t=>t>p);
      return {max:A.MAX_ENERGY,levels:A.LEVELS,top,need:A.LEVELS[top-1],english:980,lvMax:lv(A.MAX_ENERGY),lvEn:lv(980),worth:D.ENERGY.worth}}""")
    check(f'the last level ({R["top"]}) opens at {R["need"]} energy, within the {R["max"]} a pupil can earn (level {R["lvMax"]} at the most)', R['top'] <= len(R['levels']) and R['need'] is not None and R['need'] <= R['max'] and R['lvMax'] >= R['top'], R)
    check(f'the last level needs both subjects: English alone (980) reaches level {R["lvEn"]}, below {R["top"]}', R['lvEn'] < R['top'] and R['need'] > R['english'], R)
    check('the ladder in the test is the one in js/world_data.js, and levels 1 to 13 never moved', R['levels'] == LEVELS and R['levels'][:13] == OLD_LEVELS and R['max'] == 1640 and R['worth'] == {'star': 10, 'word': 5, 'story': 5, 'mstar': 20}, R)
    await c.close()


async def energy_migration(b, errs):
    """the new ladder never takes anything back: from every stored energy (each old threshold, one below it, the
    English maximum 980, far past the ladder) the level is at least what it was; energy is worked out from saved stars
    (math stars add 20 each), the stored number only ever goes up"""
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    pts = sorted({0, 1, 980, 1069, 1070, 1319, 1320, 5000} | set(OLD_LEVELS) | {max(0, t - 1) for t in OLD_LEVELS})
    bad = []
    for en in pts:
        await set_world(pg, {'av': 'fox', 'nm': [0, 0], 'nv': 2, 'en': en, 'sl': max(1, old_level(en))})
        await goto_hash(pg, 'map', '.map .wd')
        E = await pg.evaluate('window.__world.energy')
        stored = json.loads(await pg.evaluate("localStorage.getItem('wi_world')"))['p']['local']['en']
        if E['level'] < old_level(en) or E['points'] < en or stored < en: bad.append((en, old_level(en), E['level'], E['points'], stored))
    check(f'from every stored energy ({len(pts)} cases, the English maximum 980 among them) the level never goes down and the energy is kept', not bad, bad)
    await set_world(pg, {'av': 'fox', 'nm': [0, 0], 'nv': 2, 'en': 980, 'sl': 13})
    await goto_hash(pg, 'map', '.map .wd')
    E = await pg.evaluate('window.__world.energy')
    check('a pupil at the English maximum (980, level 13 before) is now at level 15', E['level'] == 15 and E['points'] == 980, E)
    await c.close()
    # math stars count, from the saved record (S.m.st): 2 stars = 40 = level 2; nothing new is stored but the energy
    c, pg, reqs = await page(b, 390, 844, errs, {'m': {'st': {'1-pizza': 2}, 'plays': 1}})
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    E = await pg.evaluate('window.__world.energy')
    rec = json.loads(await pg.evaluate("localStorage.getItem('wi_world')"))['p']['local']
    check('Fraction Bay stars give energy (2 stars = 40 = level 2), worked out from the saved math record', E['points'] == 40 and E['level'] == 2 and rec.get('en') == 40 and set(rec) <= {'av', 'nm', 'nv', 'en', 'sl', 'at'}, (E, rec))
    await c.close()
    # a stored math value is read as at most 3 stars per level, never below 0, never a word: no lasting extra energy
    for st, want in (({'1-pizza': 99}, 60), ({'1-pizza': -2, '1-sling': 'x', '1-sheet': None}, 0), ({'1-pizza': 2.5, '9-pizza': 3, 'nope': 3}, 40)):
        c, pg, reqs = await page(b, 390, 844, errs, {'m': {'st': st, 'plays': 1}})
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
        E = await pg.evaluate('window.__world.energy')
        check(f'a stored math record {st} gives {want} energy (whole stars, at most 3 per real level, nothing for a bad value or an unknown level)', E['points'] == want, E)
        await c.close()
    # at the English maximum, the next level needs Fraction Bay: the energy note says so (and only then)
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    await set_world(pg, {'av': 'fox', 'nm': [0, 0], 'nv': 2, 'en': 980, 'sl': 15}); await goto_hash(pg, 'map', '.map .wd')
    E = await pg.evaluate('window.__world.energy'); note = await pg.evaluate("document.querySelector('.wd__note').textContent")
    check('at the English maximum (980, level 15), the note adds that Fraction Bay gives energy too', E['mathOnly'] is True and 'גם במפרץ השברים מרוויחים אנרגיה.' in note, (E, note))
    await set_world(pg, {'av': 'fox', 'nm': [0, 0], 'nv': 2, 'en': 300, 'sl': 6}); await goto_hash(pg, 'map', '.map .wd')
    E = await pg.evaluate('window.__world.energy'); note = await pg.evaluate("document.querySelector('.wd__note').textContent")
    check('below it (300, level 6), English can still get there: no such line', E['mathOnly'] is False and 'מפרץ השברים' not in note, (E, note))
    await c.close()
    # every math star already won: Fraction Bay has nothing left to give, so no such line
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    keys = await pg.evaluate("import('./js/mdata.js').then(m=>m.M_ISLANDS.flatMap(i=>i.levels.map(t=>i.id+'-'+t)))")
    await c.close()
    c, pg, reqs = await page(b, 390, 844, errs, {'m': {'st': {k: 3 for k in keys}, 'plays': 1}})
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    await set_world(pg, {'av': 'fox', 'nm': [0, 0], 'nv': 2, 'en': 1640, 'sl': 23}); await goto_hash(pg, 'map', '.map .wd')
    E = await pg.evaluate('window.__world.energy'); note = await pg.evaluate("document.querySelector('.wd__note').textContent")
    check('with every math star won (and past the ladder), no Fraction Bay line', E['mathOnly'] is False and 'מפרץ השברים' not in note, (E, note))
    await c.close()
    # a phone still holding the last ship's world_data.js (it has no ENERGY or SOON, so math gives nothing there): no
    # Fraction Bay line. The old file is this one without those two exports.
    old_wd = re.sub(r'export const (ENERGY|SOON)=(\{.*?\};|\[.*?\];)', '', open(os.path.join(P.ROOT, 'js', 'world_data.js'), encoding='utf-8').read(), flags=re.S)
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.route('**/js/world_data.js', lambda r: r.fulfill(content_type='text/javascript', body=old_wd))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    await set_world(pg, {'av': 'fox', 'nm': [0, 0], 'nv': 2, 'en': 980, 'sl': 13}); await goto_hash(pg, 'map', '.map .wd')
    E = await pg.evaluate('window.__world.energy'); note = await pg.evaluate("document.querySelector('.wd__note').textContent")
    check('with the last ship\'s world_data.js cached (math gives 0 there), no Fraction Bay line', E['mathOnly'] is False and 'מפרץ השברים' not in note, (E, note))
    await c.close()


async def soon_tiles(b, errs):
    """levels 14 to 23 open nothing until the designer's characters exist: the picker shows them as "בקרוב" tiles with
    their level, no picture (nothing broken), not buttons, named for a screen reader"""
    for w, h in ((390, 844), (320, 568), (1366, 768)):
        c, pg, reqs = await page(b, w, h, errs)
        await pg.goto(P.BASE + '?ds=1#avatar'); await pg.wait_for_selector('.wpick__grid')
        T = await pg.evaluate("""[...document.querySelectorAll('.wpick__soon-tile')].map(t=>{const r=t.getBoundingClientRect();return {tag:t.tagName,img:t.querySelectorAll('img').length,txt:t.textContent,
          label:t.getAttribute('aria-label'),tab:t.tabIndex,w:r.width,h:r.height}})""")
        ok = len(T) == 10 and all(t['tag'] != 'BUTTON' and t['img'] == 0 and t['txt'] == f'בקרוברמה {n}' and t['label'] == f'דמות חדשה בקרוב, ברמה {n}' and t['tab'] < 0 and t['w'] >= 44 for t, n in zip(T, range(14, 24)))
        check(f'[{w}x{h}] ten "בקרוב" tiles for levels 14 to 23: no picture, not buttons, named', ok, T[:2])
        G = await pg.evaluate("(()=>{const a=document.querySelector('.wpick__av').getBoundingClientRect(),t=document.querySelector('.wpick__soon-tile').getBoundingClientRect();return {av:[Math.round(a.width),Math.round(a.height)],soon:[Math.round(t.width),Math.round(t.height)],sx:document.documentElement.scrollWidth,W:innerWidth}})()")
        check(f'[{w}x{h}] the "בקרוב" tiles are the size of the character tiles, and nothing scrolls sideways', G['soon'] == G['av'] and G['sx'] <= G['W'], G)
        O = await pg.evaluate("[...new Set([...document.querySelectorAll('.wpick__av')].map(b=>(b.classList.contains('is-locked')?'locked ':'open ')+getComputedStyle(b.querySelector('.wpick__art')).opacity))]")
        check(f'[{w}x{h}] open characters are drawn in full, only locked ones dimmed', sorted(O) == ['locked 0.7', 'open 1'], O)
        a = await pg.evaluate(AUDIT.replace(".wd *,.wd__note,.wpick *", ".wpick__soon-tile *"))
        check(f'[{w}x{h}] the "בקרוב" tiles\' words at least 4.5:1', not a['bad'], a['bad'])
        if w == 390:
            await pg.evaluate("document.querySelector('.wpick__soon-tile').scrollIntoView()"); await P.shot(pg, 'world-soon-390x844')
        await c.close()


async def kept(b, errs):
    """a pupil who already has a character that would now be locked keeps it (picker and map), and nothing is taken away"""
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.add_init_script("if(!sessionStorage.getItem('w')){sessionStorage.setItem('w','1');localStorage.setItem('wi_world',JSON.stringify({v:1,p:{local:{av:'pilot',nm:[0,0],nv:2,en:0}}}))}")
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd__pic'); await pg.wait_for_timeout(300)
    W = await pg.evaluate('window.__world')
    check('kept: level 1 with the pilot (opens at 13): the map still shows the pilot and its name', W['avatar'] == 'pilot' and W['energy']['level'] == 1 and 'pilot' in await pg.get_attribute('.wd__pic', 'src') and 'Brave Fox' in ' '.join((await pg.inner_text('.wd__hi')).split()), W)
    await pg.click('.wd__me'); await pg.wait_for_selector('.wpick__grid')
    r = await pg.evaluate("(()=>{const b=document.querySelector('.wpick__av[data-id=pilot]');return [b.classList.contains('is-locked'),b.classList.contains('is-selected'),document.querySelectorAll('.wpick__av:not(.is-locked)').length]})()")
    check('kept: in the picker the pilot is chosen and not locked; the other locked ones stay locked', r == [False, True, 9], r)
    await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin'); await pg.click('.wpick__ok'); await pg.wait_for_selector('.map .wd')
    rec = json.loads((await pg.evaluate(LS))['wi_world'])['p']['local']
    check('kept: saving again keeps the pilot', rec['av'] == 'pilot', rec)
    await c.close()


async def old_names(b, errs):
    """a name kept from the earlier lists (no version) reads as "no name yet": nobody gets a different name silently"""
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.add_init_script("if(!sessionStorage.getItem('w')){sessionStorage.setItem('w','1');localStorage.setItem('wi_world',JSON.stringify({v:1,p:{local:{av:'fox',nm:[6,8],en:0}}}))}")
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    W = await pg.evaluate('window.__world')
    t = ' '.join((await pg.inner_text('.wd__hi')).split())
    check('old name: the character stays, the name reads as "no name yet" (the dock says hello)', W['avatar'] == 'fox' and W['name'] is None and t == 'שלום!', [W, t])
    rec = json.loads((await pg.evaluate(LS))['wi_world'])['p']['local']
    check('old name: and is dropped from the record on the next write', 'nm' not in rec or rec['nm'] is None, rec)
    await c.close()


BADGES = """(()=>{const bad=[],op=new Set();for(const b of document.querySelectorAll('.wpick__av.is-locked')){const t=b.getBoundingClientRect(),g=b.querySelector('.wpick__lock'),r=g.getBoundingClientRect();
 op.add(getComputedStyle(b.querySelector('.wpick__art')).opacity);
 if(g.scrollWidth>g.clientWidth+1||r.height>28||r.left<t.left-0.5||r.right>t.right+0.5)bad.push([b.dataset.id,g.textContent,Math.round(r.width),Math.round(r.height),g.scrollWidth-g.clientWidth])}
 return {bad,op:[...op]}})()"""
FIT = """async()=>{const {NAME_A,NAME_B}=await import('./js/world_data.js');const out=[];
 const hi=document.querySelector('.wd__hi');const bd=[...hi.querySelectorAll('bdi')];
 for(const a of NAME_A)for(const b of NAME_B){bd[0].textContent=a.en;bd[1].textContent=b.en;
  for(const e of bd)if(e.scrollWidth>e.clientWidth+1)out.push('map '+a.en+' '+b.en)}
 return out}"""
FIT_PICK = """async()=>{const {NAME_A,NAME_B}=await import('./js/world_data.js');const out=[];
 const n=document.querySelector('.wpick__name bdi'),box=document.querySelector('.wpick__name'),body=document.querySelector('.wpick__body').getBoundingClientRect();
 const ws=[...document.querySelectorAll('.wpick__w')];
 for(const a of NAME_A)for(const b of NAME_B){n.textContent=a.en+' '+b.en;const r=box.getBoundingClientRect();
  if(box.scrollWidth>box.clientWidth+1||r.left<body.left-1||r.right>body.right+1||r.height>60)out.push('name '+a.en+' '+b.en+' '+Math.round(r.width)+'x'+Math.round(r.height))}
 for(const [k,L] of [[0,NAME_A],[1,NAME_B]])for(const x of L){const w=ws[k];w.querySelector('bdi').textContent=x.en;w.querySelector('small').textContent=x.he;
  if(w.scrollWidth>w.clientWidth+1)out.push('word '+x.en)}
 return out}"""


async def names(b, errs):
    """all 144 names fit, one word per line on the map and on one line in the picker, at 360 and 320 px; the surprise
    button and the arrows only ever give names from the two lists"""
    for w, h in ((360, 740), (320, 640), (320, 568)):
        c, pg, reqs = await page(b, w, h, errs, SEED)
        await pg.add_init_script("if(!sessionStorage.getItem('w')){sessionStorage.setItem('w','1');localStorage.setItem('wi_world',JSON.stringify({v:1,p:{local:{av:'fox',nm:[0,0],nv:2,en:0}}}))}")
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd__focus'); await pg.wait_for_timeout(300)
        bad = await pg.evaluate(FIT)
        check(f'[{w}x{h}] all 144 names fit in the map dock next to today\'s focus, one word per line, nothing cut off', not bad, bad[:6])
        await pg.click('.wd__me'); await pg.wait_for_selector('.wpick__grid')
        seen = await pg.evaluate(BADGES)
        check(f'[{w}x{h}] every locked tile: the character in view and "רמה N" whole on one line inside the tile', not seen['bad'], seen)
        await pg.evaluate("document.querySelector('.scr.wpick').scrollTop=1e5")   # as after scrolling down to the button
        await pg.click('.wpick__ok'); await pg.wait_for_selector('.wpick__spin')
        bad = await pg.evaluate(FIT_PICK)
        check(f'[{w}x{h}] all 144 names fit on one line in the picker, and every word with its Hebrew under it', not bad, bad[:6])
        top = await pg.evaluate("document.querySelector('.wpick__h').getBoundingClientRect().top")
        check(f'[{w}x{h}] the name step starts at its heading (on the screen, even after the picker scrolled to its button)', top >= 0, top)
        if w == 320:
            seen = set()
            for _ in range(40):
                await pg.click('.wpick__dice'); seen.add(' '.join((await pg.inner_text('.wpick__name')).split()))
            for _ in range(13):
                await pg.locator('.wpick__spin').nth(1).locator('.wpick__arrow').nth(0).click(); seen.add(' '.join((await pg.inner_text('.wpick__name')).split()))
            ok = await pg.evaluate("async s=>{const {NAME_A,NAME_B}=await import('./js/world_data.js');const A=new Set(NAME_A.map(x=>x.en)),B=new Set(NAME_B.map(x=>x.en));return s.filter(n=>{const [a,b]=n.split(' ');return !(A.has(a)&&B.has(b))})}", sorted(seen))
            check('the surprise button and the arrows only give names from the two lists (adjective + animal)', len(seen) > 20 and not ok, [len(seen), ok])
            await P.shot(pg, 'world-name-320x640')
        await c.close()


async def fin_logout(b, errs):
    """the all-played toast is said once per pupil: a logout lets the next pupil on the same tab hear it too"""
    api = f'http://127.0.0.1:{P.API_PORT}/'
    st = {f'{i}-{t}': 2 for i, ts in ((1, 'sling listen read bridge'), (2, 'sling listen read bridge'), (3, 'sling listen read bridge'), (4, 'sling listen read bridge'), (5, 'sling listen read bridge'), (6, 'sling listen')) for t in ts.split()}
    c, pg, reqs = await page(b, 320, 568, errs, api=api)
    await pg.goto(P.BASE); await pg.wait_for_selector('#lc')
    for n in ('דנה', 'יואב'):
        await pg.evaluate(POST, [api, {'a': 'register', 'c': CLASS, 'n': n, 'p': '2580'}])
    await c.close()
    c, pg, reqs = await page(b, 320, 568, errs, {'g': {'st': st}}, api=api, user={'c': CLASS, 'n': 'דנה', 'p': '2580'})
    on = "document.getElementById('toast').classList.contains('on')"
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    check('finished map, first pupil: the toast is said', await pg.evaluate(on))
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('[data-a=logout]'); await pg.click('[data-a=logout]'); await pg.wait_for_selector('#lc', timeout=10000)
    # the next pupil on this tab, with all levels played too (set in memory: the test does not replay a whole year)
    await pg.evaluate("(st=>{const S=__game.S();S.u={c:'%s',n:'יואב',p:'2580'};S.g={st}})" % CLASS + "(%s)" % json.dumps(st))
    await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    check('after a logout, the next pupil on the same tab is told too', await pg.evaluate(on))
    await c.close()


async def map_token(b, errs):
    """the character on the map: on the island played now, a hop once when that island changes, skippable, none with
    reduced motion; Pitzi as today when no character is chosen or the device cannot keep one (docs/DESIGN.md)"""
    two = {'g': {'st': {'1-sling': 3, '1-listen': 3, '1-read': 3, '1-bridge': 3, '2-sling': 1}}}
    rec = lambda **k: json.dumps({'v': 1, 'p': {'local': dict({'av': 'fox', 'nm': [0, 0], 'en': 0}, **k)}})
    # the island whose picture is nearest the token (it stands at the island's side, as Pitzi does)
    WHERE = """(()=>{const t=document.querySelector('.wtok');if(!t)return null;const r=t.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;
      let best=0,d=1e9;for(const i of document.querySelectorAll('.isl')){const p=i.querySelector('.pw').getBoundingClientRect(),e=Math.hypot(p.left+p.width/2-x,p.top+p.height/2-y);if(e<d){d=e;best=+[...i.classList].find(c=>/^i\\d$/.test(c)).slice(1)}}
      return best})()"""
    LOOK = """(()=>{const t=document.querySelector('.wtok'),r=t.getBoundingClientRect(),g=document.querySelector('.isl.cur .tag').getBoundingClientRect(),cs=getComputedStyle(t);
      const pw=document.querySelector('.isl.cur .pw').getBoundingClientRect().width;
      return {w:r.width,h:r.height,want:Math.round(Math.min(44,pw*.6)),tag:!(r.right<=g.left||r.left>=g.right||r.bottom<=g.top||r.top>=g.bottom),ring:cs.borderTopWidth,shadow:getComputedStyle(t,'::after').content!=='none',hit:cs.pointerEvents,
        aria:t.getAttribute('aria-hidden'),inside:r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight}})()"""
    for w, h in ((390, 844), (360, 740), (320, 568), (768, 1024), (1366, 768)):
        tag = f'token {w}x{h}'
        c, pg, reqs = await page(b, w, h, errs, two)
        await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec(at=1)))
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_function('!window.__hop||window.__hop.playState==="finished"', timeout=5000); await pg.wait_for_timeout(100)   # the hop (900 ms) is over before measuring
        W = await pg.evaluate('window.__world.token')
        on = await pg.evaluate(WHERE)
        check(f'[{tag}] the character stands on the island played now (2, "ממשיכים כאן"), in place of the crab', on == 2 and W['island'] == 2 and await pg.locator('.isl.i2.cur').count() == 1 and await pg.evaluate("getComputedStyle(document.querySelector('.isl.cur .here')).display") == 'none', (on, W))
        L = await pg.evaluate(LOOK)
        check(f'[{tag}] a framed token of 44 px (at most 60% of a small island), 3 px ring, a ground shadow, on screen, never over the "ממשיכים כאן" tag, decoration only', L['w'] == L['want'] and L['h'] == L['want'] and (w < 390 or L['w'] == 44) and L['ring'] == '3px' and L['shadow'] and not L['tag'] and L['inside'] and L['hit'] == 'none' and L['aria'] == 'true', L)
        check(f'[{tag}] it hopped from island 1 to 2, once, and the new island is remembered', W['hop'] == {'from': 1, 'to': 2, 'anim': True} and json.loads(await pg.evaluate("localStorage.getItem('wi_world')"))['p']['local']['at'] == 2, W)
        await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings'); await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_timeout(200)
        check(f'[{tag}] back on the map: no second hop', (await pg.evaluate('window.__world.token'))['hop'] is None)
        lab = await pg.get_attribute('.isl.i2', 'aria-label')
        check(f'[{tag}] the island played now says so to a screen reader (flag on only)', lab == 'אי בית הספר, ממשיכים כאן', lab)
        if w == 390:
            await P.shot(pg, 'world-token-390x844')
        await c.close()
    # a tap ends the hop at once
    c, pg, reqs = await page(b, 390, 844, errs, two)
    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec(at=1)))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_timeout(100)
    await pg.mouse.click(195, 160); await pg.wait_for_timeout(50)
    check('a tap anywhere ends the hop at once', await pg.evaluate("window.__hop.playState") == 'finished')
    await c.close()
    # a tap on an island during the hop ends it and still opens that island
    c, pg, reqs = await page(b, 390, 844, errs, two)
    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec(at=1)))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_timeout(100)
    await pg.click('.isl.i1', force=True); await pg.wait_for_timeout(50)
    hs = await pg.evaluate("window.__hop.playState")
    await pg.wait_for_function("location.hash==='#island/1'", timeout=3000)
    check('a tap on an island during the hop ends it and that island opens', hs == 'finished')
    await c.close()
    # a key ends it too
    c, pg, reqs = await page(b, 390, 844, errs, two)
    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec(at=1)))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_timeout(100)
    await pg.keyboard.press('Tab'); await pg.wait_for_timeout(50)
    check('a key ends the hop at once', await pg.evaluate("window.__hop.playState") == 'finished')
    d = await pg.evaluate("window.__hop.effect.getTiming().duration")
    check('the hop is 900 ms with a squash on landing', d == 900 and 'scale(1.14, 0.84)' in await pg.evaluate("JSON.stringify(window.__hop.effect.getKeyframes().map(k=>k.transform))"), d)
    await c.close()
    # reduced motion: no hop, the character is simply there
    c, pg, reqs = await page(b, 390, 844, errs, two)
    await pg.emulate_media(reduced_motion='reduce')
    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec(at=1)))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_timeout(200)
    W = await pg.evaluate('window.__world.token')
    check('reduced motion: no hop, the character is on island 2 at once', W['hop'] == {'from': 1, 'to': 2, 'anim': False} and await pg.evaluate(WHERE) == 2, W)
    await c.close()
    # every island full: on the last open island
    full = {'g': {'st': {f'{i}-{t}': 3 for i, ts in ((1, 'sling listen read bridge'), (2, 'sling listen read bridge'), (3, 'sling listen read bridge'), (4, 'sling listen read bridge'), (5, 'sling listen read bridge'), (6, 'sling listen')) for t in ts.split()}}}
    c, pg, reqs = await page(b, 390, 844, errs, full)
    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec(at=6)))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_timeout(300)
    check('every island full: the character stands on the last island', await pg.evaluate(WHERE) == 6)
    await c.close()
    # an `at` on an island not open is no position: no hop from it
    c, pg, reqs = await page(b, 390, 844, errs, two)
    await pg.add_init_script("if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec(at=4)))
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wtok'); await pg.wait_for_timeout(300)
    W = await pg.evaluate('window.__world.token')
    check('a remembered island that is not open is no position: no hop, the character simply on island 2', W['hop'] is None and await pg.evaluate(WHERE) == 2, W)
    await c.close()
    # no character yet: Pitzi stands on the island as today, with a small "?" badge by him that opens the picker; its tap
    # area never covers an island's picture (the island stays the island's button)
    five = {'g': {'st': {f'{i}-{t}': 3 for i, ts in ((1, 'sling listen read bridge'), (2, 'sling listen read bridge'), (3, 'sling listen read bridge'), (4, 'sling listen read bridge'), (5, 'sling listen read bridge')) for t in ts.split()}}}
    for w, h, seedx, cur in ((390, 844, two, 2), (360, 740, two, 2), (320, 568, two, 2), (768, 1024, two, 2), (1366, 768, two, 2), (1366, 768, five, 6), (360, 740, five, 6), (320, 568, five, 6)):
        c, pg, reqs = await page(b, w, h, errs, seedx)
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wask'); await pg.wait_for_timeout(300)
        k = await pg.evaluate("""(()=>{const b=document.querySelector('.wask').getBoundingClientRect(),d=document.querySelector('.wask__dot').getBoundingClientRect(),c=document.querySelector('.isl.cur .here').getBoundingClientRect();
          const ov=[...document.querySelectorAll('.isl .pw,.isl .tag,.isl .hb')].map(p=>{const r=p.getBoundingClientRect();return Math.max(0,Math.min(b.right,r.right)-Math.max(b.left,r.left))*Math.max(0,Math.min(b.bottom,r.bottom)-Math.max(b.top,r.top))}).reduce((x,y)=>x+y,0);
          const cx=b.left+b.width/2,cy=b.top+b.height/2,near=Math.hypot(cx-(c.left+c.width/2),cy-(c.top+c.height/2))<=c.width+b.width/2;
          return {w:b.width,dot:d.width,ov,near,cur:+[...document.querySelector('.isl.cur').classList].find(x=>/^i\\d$/.test(x)).slice(1),here:getComputedStyle(document.querySelector('.isl.cur .here')).display,
          label:document.querySelector('.wask').getAttribute('aria-label'),in:b.left>=0&&b.right<=innerWidth&&b.top>=0&&b.bottom<=innerHeight}})()""")
        check(f'[no character {w}x{h}, island {cur}] Pitzi as today; a small "?" badge by him, named, on screen; its tap area (48 px, or 32 with no room) never over an island\'s picture or tag', await pg.locator('.wtok').count() == 0 and k['cur'] == cur and k['here'] != 'none' and k['near'] and k['w'] >= 32 and k['dot'] <= 24 and k['ov'] == 0 and k['label'] and k['in'], k)
        if w >= 768:
            check(f'[no character {w}x{h}, island {cur}] with room beside Pitzi, the badge keeps a 48 px tap area', k['w'] >= 48, k)
        if (w, h) == (390, 844):
            await P.shot(pg, 'world-ask-390x844')
            box = await pg.evaluate("(()=>{const r=document.querySelector('.isl.i2 .pw').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()")
            await pg.mouse.click(box[0], box[1]); await pg.wait_for_function("location.hash==='#island/2'", timeout=3000)
            check('a tap on the island\'s picture opens the island, not the picker', True)
            await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wask'); await pg.wait_for_timeout(300)
            await pg.click('.wask'); await pg.wait_for_selector('.wpick__grid')
            check('the "?" badge opens the picker', True)
        await c.close()
    # flag off: the island's name for a screen reader stays exactly as today
    c, pg, reqs = await page(b, 390, 844, errs, two)
    await pg.goto(P.BASE + '#map'); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(200)
    check('flag off: the island played now keeps its label as today', await pg.get_attribute('.isl.i2', 'aria-label') == 'אי בית הספר')
    await c.close()
    # a device that cannot keep a character: nothing on the map
    api = f'http://127.0.0.1:{P.API_PORT}/'
    c, pg, reqs = await page(b, 390, 844, errs, two, api=api, user={'c': CLASS, 'n': 'נועה', 'p': '1357'})
    await pg.add_init_script("try{Object.defineProperty(window.crypto,'subtle',{get:()=>undefined,configurable:true})}catch(e){}")
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
    check('no digest: no token, no "?", Pitzi as today', await pg.locator('.wtok,.wask').count() == 0 and await pg.evaluate("getComputedStyle(document.querySelector('.isl.cur .here')).display") != 'none')
    await c.close()


async def island_path(b, errs):
    """an island as a path of stones: the levels in their order, each with its name; the character on the next stone,
    gliding to a tapped one before the level opens; a second tap and the back button never held up (docs/DESIGN.md)"""
    st = {'g': {'st': {'1-sling': 3, '1-listen': 2}}}
    rec = json.dumps({'v': 1, 'p': {'local': {'av': 'fox', 'nm': [0, 0], 'en': 0, 'at': 1}}})
    five = {'g': {'st': {f'{i}-{t}': 3 for i, ts in ((1, 'sling listen read bridge'), (2, 'sling listen read bridge'), (3, 'sling listen read bridge'), (4, 'sling listen read bridge'), (5, 'sling listen read bridge')) for t in ts.split()}}}
    seed = "if(!sessionStorage.t){sessionStorage.t=1;localStorage.setItem('wi_world',%s)}" % json.dumps(rec)
    NAMES = ['קלע המילים', 'תופסים צלילים', 'בקבוק הסיפור', 'גשר המשפטים']
    SUBS = ['פוגעים במילה הנכונה', 'שומעים מילה ולוחצים עליה', 'קוראים סיפור ועונים', 'בונים משפט וחוצים']
    GEO = """(()=>{const v=document.documentElement.getBoundingClientRect(),W=innerWidth,H=innerHeight;
      const st=[...document.querySelectorAll('.w-path .w-st')].map(b=>{const r=b.getBoundingClientRect(),n=b.querySelector('.w-st__name').getBoundingClientRect();
        const fs=[...b.querySelectorAll('.w-st__name b,.w-st__name small')].map(e=>parseFloat(getComputedStyle(e).fontSize));
        return {to:b.dataset.to,name:b.querySelector('.w-st__name b').textContent,sub:b.querySelector('.w-st__name small').textContent,fs:Math.min(...fs),
          w:r.width,h:r.height,in:r.left>=0&&r.right<=W&&n.left>=0&&n.right<=W&&n.top>=0&&n.bottom<=H,state:b.className.replace(/.*w-st--/,''),plate:[n.left,n.top,n.right,n.bottom]}});
      const ov=(a,c)=>!(a[2]<=c[0]||a[0]>=c[2]||a[3]<=c[1]||a[1]>=c[3]);
      const clash=st.some((x,i)=>st.some((y,j)=>j>i&&ov(x.plate,y.plate)));
      const lit=document.querySelector('.w-line__lit'),dim=document.querySelector('.w-line__dim');
      const line={lit:lit?lit.getAttribute('points').split(' ').length:0,dim:dim?dim.getAttribute('points').split(' ').length:0};
      const gc=document.querySelector('.w-st--current .w-st__art'),glow=gc?getComputedStyle(gc).animationName:null;
      const wk=document.querySelector('.w-walker'),wr=wk&&wk.getBoundingClientRect(),cur=document.querySelector('.w-st--current');
      const near=wk&&cur?Math.abs((wr.left+wr.width/2)-(cur.getBoundingClientRect().left+cur.getBoundingClientRect().width/2))<4:null;
      return {st,near,clash,line,glow,wk:wr?[wr.width,wr.height]:null,list:!!document.querySelector('.lvlist')}})()"""
    for w, h in ((390, 844), (360, 740), (320, 568), (768, 1024), (1366, 768)):
        tag = f'path {w}x{h}'
        c, pg, reqs = await page(b, w, h, errs, st)
        await pg.add_init_script(seed)
        await to_path(pg, 1); await pg.wait_for_timeout(400)
        g = await pg.evaluate(GEO)
        check(f'[{tag}] the stones are the levels in order, with the names and sub-lines of today\'s list', [x['to'] for x in g['st']] == ['play/1/sling', 'play/1/listen', 'play/1/read', 'play/1/bridge'] and [x['name'] for x in g['st']] == NAMES and [x['sub'] for x in g['st']] == SUBS and not g['list'], g['st'])
        check(f'[{tag}] labels never below 15 px, and no two labels overlap', all(x['fs'] >= 15 for x in g['st']) and not g['clash'], [(x['fs'], x['plate']) for x in g['st']])
        check(f'[{tag}] a dotted line joins the stones: gold up to the glowing stone (3 stones), dim after it (2)', g['line'] == {'lit': 3, 'dim': 2}, g['line'])
        check(f'[{tag}] the glowing stone pulses; the character is a 52 px token', g['glow'] == 'wglow' and g['wk'] == [52, 52], (g['glow'], g['wk']))
        check(f'[{tag}] played stones lit, the first not played glowing, the rest open (no level is locked today)', [x['state'] for x in g['st']] == ['done', 'done', 'current', 'open'], [x['state'] for x in g['st']])
        check(f'[{tag}] every stone at least 48 px, every stone and its name on the screen', all(x['w'] >= 48 and x['h'] >= 48 and x['in'] for x in g['st']), g['st'])
        check(f'[{tag}] the character stands on the glowing stone', g['near'] is True, g['near'])
        a = await pg.evaluate(AUDIT.replace(".wd *,.wd__note,.wpick *", ".w-path *"))
        check(f'[{tag}] every name and number at least 4.5:1', not a['bad'], a['bad'])
        if w == 390:
            await P.shot(pg, 'world-path-390x844')
        await c.close()
    # a tap: the character walks (under 0.6 s), then the tapped level opens
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.add_init_script(seed)
    await to_path(pg, 1)
    dt = await tap_to_open(pg, '.w-st[data-to="play/1/bridge"]', 'play/1/bridge')
    check('a tapped stone: the character glides there and that level opens, in under 0.6 s', dt < 650, round(dt))
    await P.lv(pg, 'bridge')
    await c.close()
    # the label is part of the stone's button: a tap on it opens that level
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.add_init_script(seed)
    await to_path(pg, 1)
    await pg.click('.w-st[data-to="play/1/listen"] .w-st__name small')
    await pg.wait_for_function("location.hash==='#play/1/listen'", timeout=3000)
    check('a tap on a label opens its level (stone and label are one button)', True)
    await c.close()
    # a second tap during the walk wins; the back button during the walk is never held up
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.add_init_script(seed)
    await to_path(pg, 1)
    await pg.evaluate("window.__opens=[];addEventListener('hashchange',()=>{if(location.hash.startsWith('#play/'))__opens.push(location.hash)})")
    await pg.click('.w-st[data-to="play/1/bridge"]'); await pg.wait_for_timeout(120)
    dt = await tap_to_open(pg, '.w-st[data-to="play/1/sling"]', 'play/1/sling'); await pg.wait_for_timeout(600)
    check('a second tap during the glide ends it and goes at once: that level opens, and only it', await pg.evaluate('__opens') == ['#play/1/sling'] and dt < 400, (await pg.evaluate('__opens'), round(dt)))
    await to_path(pg, 1)
    await pg.evaluate("window.__opens=[]")   # the same page (only the address after # changed): its listener is still there
    await pg.click('.w-st[data-to="play/1/read"]'); await pg.click('.w-st[data-to="play/1/read"]', force=True, no_wait_after=True); await pg.wait_for_timeout(800)
    check('two quick taps on a stone open its level once', await pg.evaluate('__opens') == ['#play/1/read'], await pg.evaluate('__opens'))
    await to_path(pg, 1)
    await pg.click('.w-st[data-to="play/1/read"]'); await pg.wait_for_timeout(100); await pg.click('[data-a=nav][data-to="map"]')
    await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(700)
    check('the back button during the walk: back on the map, and no level opens after', await pg.evaluate('location.hash') == '#map')
    await c.close()
    # keyboard: the stones in order, Enter opens
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.add_init_script(seed)
    await to_path(pg, 1)
    order = await pg.evaluate("[...document.querySelectorAll('button,a[href]')].filter(e=>e.closest('.w-path')).map(e=>e.dataset.to)")
    check('keyboard and screen-reader order equals the level order', order == ['play/1/sling', 'play/1/listen', 'play/1/read', 'play/1/bridge'], order)
    labels = await pg.evaluate("[...document.querySelectorAll('.w-path .w-st')].map(b=>b.getAttribute('aria-label'))")
    check('each stone is named with its number, its level and its stars', labels[0].startswith('שלב 1: קלע המילים, שלושה כוכבים') and 'כאן אתם עכשיו' in labels[2], labels)
    await pg.focus('.w-st[data-to="play/1/listen"]'); await pg.keyboard.press('Enter')
    await pg.wait_for_function("location.hash==='#play/1/listen'", timeout=3000)
    check('Enter on a stone opens its level', True)
    await c.close()
    # reduced motion: no walk, the level opens at once
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.emulate_media(reduced_motion='reduce'); await pg.add_init_script(seed)
    await to_path(pg, 1)
    dt = await tap_to_open(pg, '.w-st[data-to="play/1/read"]', 'play/1/read')
    check('reduced motion: no walk, the level opens at once', dt < 400, round(dt))
    await to_path(pg, 1)
    check('reduced motion: the glowing stone does not pulse', await pg.evaluate("getComputedStyle(document.querySelector('.w-st--current .w-st__art')).animationName") == 'none')
    await c.close()
    # no character: no walker, a tap opens at once; the bonus island has its two stones
    c, pg, reqs = await page(b, 390, 844, errs, {'g': {'st': {f'{i}-{t}': 3 for i, ts in ((1, 'sling listen read bridge'), (2, 'sling listen read bridge'), (3, 'sling listen read bridge'), (4, 'sling listen read bridge'), (5, 'sling listen read bridge')) for t in ts.split()}}})
    await to_path(pg, 6); await pg.wait_for_timeout(200)
    g = await pg.evaluate(GEO)
    check('the bonus island: its two levels as two stones, no character when none is chosen', [x['to'] for x in g['st']] == ['play/6/sling', 'play/6/listen'] and await pg.locator('.w-walker').count() == 0, g['st'])
    dt = await tap_to_open(pg, '.w-st[data-to="play/6/listen"]', 'play/6/listen')
    check('no character: a tap opens the level at once', dt < 400, round(dt))
    await c.close()
    # a device that cannot keep a character: the path, without a character
    api = f'http://127.0.0.1:{P.API_PORT}/'
    c, pg, reqs = await page(b, 390, 844, errs, st, api=api, user={'c': CLASS, 'n': 'נועה', 'p': '1357'})
    await pg.add_init_script("try{Object.defineProperty(window.crypto,'subtle',{get:()=>undefined,configurable:true})}catch(e){}")
    await to_path(pg, 1); await pg.wait_for_timeout(200)
    check('no digest: the path is there, without a character', await pg.locator('.w-walker').count() == 0 and await pg.locator('.w-path .w-st').count() == 4)
    await c.close()
    # a locked island stays locked: its address goes back to the map
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.goto(P.BASE + '?ds=1#island/4'); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(200)
    check('a locked island stays locked with the flag (its address goes to the map)', await pg.evaluate('location.hash') == '#map' and await pg.locator('.w-path').count() == 0)
    await c.close()
    # a slow phone: the backdrop delayed. The island area is never empty, and it never flips from list to path late:
    # the path only if the art is here within about 0.3 s, else the list for this visit
    SAMPLE = """(()=>{const L=document.querySelector('.lvlist'),rows=L&&getComputedStyle(L).visibility==='visible'?[...L.querySelectorAll('.lvrow')].filter(r=>r.getBoundingClientRect().height>0).length:0;
      const st=document.querySelectorAll('.w-path .w-st').length;return rows?'list':st?'path':'empty'})()"""
    for delay in (0, 800, 2000, 3500):
        c, pg, reqs = await page(b, 390, 844, [], st)
        await pg.add_init_script(seed)
        def slow(d):
            async def h(r):
                await asyncio.sleep(d / 1000); await r.continue_()
            return h
        await pg.route('**/assets/al/bg/english.*', slow(delay))
        await pg.goto(P.BASE + '?ds=1#island/1'); await pg.wait_for_selector('.scr.island')
        seen = []
        for _ in range(45):
            seen.append(await pg.evaluate(SAMPLE)); await pg.wait_for_timeout(100)
        flips = [k for k in range(1, len(seen)) if seen[k] != seen[k - 1]]
        late = [k for k in flips if k > 8]   # a swap after about 0.9 s (module, then at most 0.3 s for the pictures)
        check(f'backdrop {delay} ms, straight onto the island: the island area is never empty, and never changes late' + (' (the list for this visit)' if delay >= 800 else ''), 'empty' not in seen and not late and (delay < 800 or seen[-1] == 'list'), ''.join(x[0] for x in seen))
        await c.close()
    # the map fetches the path's pictures after its own, decoded, and says when (window.__world.pathArt): then the island
    # opens on its path even on a slow line
    c, pg, reqs = await page(b, 390, 844, [], st)
    await pg.add_init_script(seed)
    async def slow8(r):
        await asyncio.sleep(0.8); await r.continue_()
    await pg.route('**/assets/al/bg/english.*', slow8)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    own = await pg.evaluate("[...document.querySelectorAll('.map img')].map(i=>i.currentSrc||i.src)")
    ok = await pg.evaluate('window.__world.pathArt')
    urls = [u for u, _ in reqs]
    art = [k for k, u in enumerate(urls) if '/assets/al/bg/english.' in u or '/assets/al/ui/stone-' in u]
    mine = [urls.index(u) for u in own if u in urls]
    check('the map fetches the path\'s pictures (backdrop and the two stones), after its own pictures, and says when they are in', ok is True and len(art) >= 3 and (not mine or max(mine) < min(art)), (ok, len(art), max(mine) if mine else None, min(art) if art else None))
    await pg.evaluate("location.hash='island/1'"); await pg.wait_for_selector('.scr.island')
    await pg.wait_for_function("document.querySelector('.w-path .w-st')||document.querySelector('.lvlist')")
    seen = [await pg.evaluate(SAMPLE)]
    for _ in range(10):
        await pg.wait_for_timeout(100); seen.append(await pg.evaluate(SAMPLE))
    check('then the island opens on its path, at once and for good', set(seen) == {'path'}, ''.join(x[0] for x in seen))
    await c.close()
    # on a slow CPU, with the pictures already in: the list never flashes before the path, and the island area is empty
    # for at most about 0.3 s (every frame recorded)
    for rate in (1, 4):
        c, pg, reqs = await page(b, 390, 844, [], st)
        await pg.add_init_script(seed)
        await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
        assert await pg.evaluate('window.__world.pathArt') is True
        cdp = await c.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate', {'rate': rate})
        await pg.evaluate("""(()=>{window.__fr=[];const t0=performance.now(),S=()=>{const L=document.querySelector('.lvlist'),rows=L&&getComputedStyle(L).visibility==='visible'?L.querySelectorAll('.lvrow').length:0;
          const st=document.querySelectorAll('.w-path .w-st').length;return rows?'list':st?'path':(document.querySelector('.scr.island')?'empty':'map')};
          const f=()=>{__fr.push([Math.round(performance.now()-t0),S()]);if(performance.now()-t0<1500)requestAnimationFrame(f)};requestAnimationFrame(f);location.hash='island/1'})()""")
        await pg.wait_for_timeout(1800)
        fr = await pg.evaluate('window.__fr')
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
        isl = [x for x in fr if x[1] != 'map']
        empty = [t for t, k in isl if k == 'empty']
        span = (max(empty) - min(empty)) if empty else 0
        check(f'CPU x{rate}, pictures already in: the list never shows before the path, the area is empty at most about 0.35 s, then the path for good', isl and 'list' not in [k for _, k in isl] and isl[-1][1] == 'path' and span <= 350, (span, ''.join(k[0] for _, k in isl)))
        await c.close()
    # on a slow line (tests/slow_net.py's profile), the path's pictures are asked for only after every picture the map
    # shows (its <img>s) has arrived: compared in the browser's own network log (one clock, no polling), title then map
    import slow_net as SN
    c, pg, reqs = await page(b, 390, 844, [], st)
    await pg.add_init_script(seed)
    cdp = await c.new_cdp_session(pg); await cdp.send('Network.enable')
    await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': SN.PROFILE['latency'], 'downloadThroughput': SN.PROFILE['down'], 'uploadThroughput': SN.PROFILE['up']})
    log = {}
    def _sent(e): log[e['requestId']] = {'url': e['request']['url'], 'sent': e['timestamp'], 'done': None}
    def _done(e):
        if e['requestId'] in log: log[e['requestId']]['done'] = e['timestamp']
    cdp.on('Network.requestWillBeSent', _sent); cdp.on('Network.loadingFinished', _done)
    await pg.goto(P.BASE + '?ds=1#', wait_until='commit')
    await pg.wait_for_selector('.scr.title .btn', timeout=150000)
    await pg.wait_for_function("document.readyState==='complete'", timeout=150000)   # after the load event: it no longer holds anything back
    await pg.evaluate("location.hash='map'")
    await pg.wait_for_selector('.scr.map .wd', timeout=150000)
    ok = await pg.wait_for_function('window.__world&&window.__world.pathArt', timeout=150000)
    ok = await pg.evaluate('window.__world.pathArt')
    shown = set(await pg.evaluate("[...document.querySelectorAll('.scr.map img')].map(i=>i.currentSrc||i.src).filter(u=>u&&!u.startsWith('data:'))"))
    path = [r for r in log.values() if '/assets/al/bg/english.' in r['url'] or '/assets/al/ui/stone-' in r['url']]
    own = [r for r in log.values() if r['url'] in shown]
    first = min((r['sent'] for r in path), default=None)
    last = max((r['done'] or 1e18 for r in own), default=None)
    check('slow line, title then map: the path\'s pictures are asked for only after every picture the map shows has arrived (same network log), and still arrive', ok is True and first is not None and last is not None and first >= last, {'own': len(own), 'path': len(path), 'gap s': round(first - last, 2) if first and last else None})
    await c.close()
    # leaving the map for anything but an island drops a preload still under way; the next map fetches again
    c, pg, reqs = await page(b, 390, 844, [], st)
    await pg.add_init_script(seed)
    async def slow3(r):
        await asyncio.sleep(3); await r.continue_()
    await pg.route('**/assets/al/bg/english.*', slow3)
    await pg.goto(P.BASE + '?ds=1#map'); await pg.wait_for_selector('.map .wd')
    await pg.wait_for_function("performance.getEntriesByType('resource').length>0"); await pg.wait_for_timeout(300)
    await pg.evaluate("window.__p1=window.__world.pathArt;location.hash='settings'"); await pg.wait_for_selector('.scr.settings')
    first = await pg.evaluate('window.__p1')
    await pg.unroute('**/assets/al/bg/english.*')
    await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .wd')
    second = await pg.evaluate('window.__world.pathArt')
    check('leaving the map for settings drops the preload under way; the next map fetches it again', first is False and second is True, (first, second))
    await c.close()
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.goto(P.BASE + '#map'); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(3000)
    check('flag off: the map fetches nothing of the path', not [u for u, _ in reqs if '/assets/al/bg/english.' in u or '/assets/al/ui/stone-' in u])
    await c.close()
    # Pitzi's hint: the list screen's words, one line under the path
    for w, h in ((390, 844), (360, 740), (320, 568), (768, 1024), (1366, 768)):
        c, pg, reqs = await page(b, w, h, errs, st)
        await pg.add_init_script(seed)
        await to_path(pg, 1); await pg.wait_for_timeout(300)
        k = await pg.evaluate("""(()=>{const t=document.querySelector('.w-hint');if(!t)return null;const r=t.getBoundingClientRect(),g=document.querySelector('.w-stage').getBoundingClientRect();
          const hit=[...document.querySelectorAll('.w-st,.w-st__name')].some(e=>{const q=e.getBoundingClientRect();return !(q.right<=r.left||q.left>=r.right||q.bottom<=r.top||q.top>=r.bottom)});
          return {text:t.textContent,under:r.top>=g.bottom-1,in:r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight,hit,fs:parseFloat(getComputedStyle(t).fontSize)}})()""")
        check(f'[hint {w}x{h}] Pitzi\'s hint, the same words as the list screen, one line under the path, on screen, over no stone', k and k['text'] == 'אפשר לחזור לכל שלב ולאסוף עוד כוכבים' and k['under'] and k['in'] and not k['hit'] and k['fs'] >= 15, k)
        a = await pg.evaluate(AUDIT.replace(".wd *,.wd__note,.wpick *", ".w-hint"))
        check(f'[hint {w}x{h}] at least 4.5:1', not a['bad'], a['bad'])
        await c.close()
    c, pg, reqs = await page(b, 390, 844, errs)
    await pg.add_init_script(seed)
    await to_path(pg, 1); await pg.wait_for_timeout(200)
    check('an island not played yet: "בחרו שלב. יש ארבעה, כמו חלקי המבחן"', await pg.inner_text('.w-hint') == 'בחרו שלב. יש ארבעה, כמו חלקי המבחן')
    await c.close()
    c, pg, reqs = await page(b, 390, 844, errs, five)
    await to_path(pg, 6); await pg.wait_for_timeout(200)
    check('the bonus island: "כאן יש שני שלבים: חודשים בקלע, מספרים בהאזנה"', await pg.inner_text('.w-hint') == 'כאן יש שני שלבים: חודשים בקלע, מספרים בהאזנה')
    await c.close()
    # a stone picture that fails during a glide: the list comes back, and the level being walked to still opens
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.add_init_script(seed)
    await to_path(pg, 1); await pg.wait_for_timeout(200)
    await pg.click('.w-st[data-to="play/1/bridge"]'); await pg.wait_for_timeout(60)
    await pg.evaluate("document.querySelector('.w-path .w-st__art').dispatchEvent(new Event('error'))")
    back = await pg.evaluate("!!document.querySelector('.lvlist') && !document.querySelector('.w-path') && !document.querySelector('.w-hint')")
    await pg.wait_for_function("location.hash==='#play/1/bridge'", timeout=3000)
    check('a picture failing mid-glide: the list comes back, and the level walked to still opens', back)
    await c.close()
    # the path's art fails to load: today's list, never a blank screen (the failed loads are expected here, so their
    # console lines go to a list of their own)
    for what, pat in (('the backdrop', '**/assets/al/bg/english.*'), ('a stone picture', '**/assets/al/ui/stone-current.*')):
        c, pg, reqs = await page(b, 390, 844, [], st)
        await pg.add_init_script(seed)
        await pg.route(pat, lambda r: r.abort())
        await pg.goto(P.BASE + '?ds=1#island/1'); await pg.wait_for_selector('.scr.island'); await pg.wait_for_timeout(3200)
        v = await pg.evaluate("({rows:[...document.querySelectorAll('.lvlist .lvrow')].filter(r=>r.getBoundingClientRect().height>0&&getComputedStyle(r.closest('.lvlist')).visibility==='visible').length,path:document.querySelectorAll('.w-path').length,cls:document.querySelector('.scr.island').classList.contains('wpath')})")
        check(f'{what} cannot load: today\'s list of levels, visible, and no path', v == {'rows': 4, 'path': 0, 'cls': False}, v)
        if v['rows'] == 4:
            await pg.click('.lvrow >> nth=1'); await pg.wait_for_function("location.hash==='#play/1/listen'", timeout=3000)
        check(f'{what} cannot load: the list still opens its levels', v['rows'] == 4)
        await c.close()
    # flag off: today's list, nothing of the path fetched
    c, pg, reqs = await page(b, 390, 844, errs, st)
    await pg.goto(P.BASE + '#island/1'); await pg.wait_for_selector('.lvrow'); await pg.wait_for_timeout(300)
    check('flag off: today\'s list of levels, no path, nothing of it fetched', await pg.locator('.lvrow').count() == 4 and await pg.locator('.w-path').count() == 0 and not [u for u, _ in reqs if 'worldpath' in u or 'avatar' in u])
    await c.close()


async def anim(b, errs):
    """the picker plays a character's short animation when it is tapped (js/avanim.js): the file is requested only then,
    never with reduced motion, and never without the flag"""
    for reduce in (False, True):
        c, pg, reqs = await page(b, 390, 844, errs)
        if reduce:
            await pg.emulate_media(reduced_motion='reduce')
        await pg.goto(P.BASE + '?ds=1#avatar'); await pg.wait_for_selector('.wpick__grid'); await pg.wait_for_timeout(500)
        before = [u for u, _ in reqs if '/avanim/' in u]
        await pg.click('.wpick__av[data-id=girl-curls]'); await pg.wait_for_timeout(600)
        after = [u for u, _ in reqs if '/avanim/' in u]
        if reduce:
            check('reduced motion: tapping a character requests no animation', not before and not after, after)
        else:
            check('no animation file is requested before a tap', not before, before)
            check('tapping a character plays its animation (one file, that character\'s)', len(after) == 1 and 'girl-curls' in after[0], after)
        await c.close()
    # a missing animation file: straight back to the still portrait, never a broken picture
    c, pg, reqs = await page(b, 390, 844, [])
    await pg.route('**/assets/al/avanim/**', lambda r: r.fulfill(status=404, body=''))
    await pg.goto(P.BASE + '?ds=1#avatar'); await pg.wait_for_selector('.wpick__grid')
    await pg.click('.wpick__av[data-id=girl-curls]'); await pg.wait_for_timeout(400)
    r = await pg.evaluate("(()=>{const i=document.querySelector('.wpick__av.is-selected img');return {src:i.getAttribute('src'),ok:i.complete&&i.naturalWidth>0}})()")
    check('a missing animation file falls back to the still portrait at once (no broken picture)', '/av/girl-curls.' in r['src'] and r['ok'], r)
    await c.close()
    # the title screen on a short phone: the crab never sits on a subject button
    c, pg, reqs = await page(b, 320, 568, errs)
    await pg.goto(P.BASE + '?ds=1'); await pg.wait_for_selector('.title .btn'); await pg.wait_for_timeout(400)
    ov = await pg.evaluate("(()=>{const c=document.querySelector('.tcrab').getBoundingClientRect();return [...document.querySelectorAll('.title .btn')].filter(e=>{const r=e.getBoundingClientRect();return c.width&&Math.min(r.right,c.right)>Math.max(r.left,c.left)&&Math.min(r.bottom,c.bottom)>Math.max(r.top,c.top)}).length})()")
    check('320x568, new look: the title crab lies over no button', ov == 0, ov)
    await c.close()
    c, pg, reqs = await page(b, 390, 844, errs, SEED)
    await pg.goto(P.BASE + '#map'); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(400)
    check('flag off: nothing of the animations is fetched', not [u for u, _ in reqs if 'avanim' in u], [u for u, _ in reqs if 'avanim' in u])
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
            check(f'[{tag}] the title screen and the page say ניצני אופק, with a line about what is inside', r['title'] == 'ניצני אופק' and r['h1'] == 'ניצני אופק' and r['sub'] == 'אנגלית, חשבון ועוד: כל יום קצת', r)
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
            t = await pg.evaluate("document.getElementById('toast').classList.contains('on')?document.getElementById('toast').textContent:''")
            check(f'[finished {w}x{h}] instead, its line is said once as a toast', 'עברתם בכל האיים' in t and 'חסרים לכם עוד 22 כוכבים באיים שבמסגרת הצהובה' in t, t)
            await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings'); await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .wd'); await pg.wait_for_timeout(300)
            check(f'[finished {w}x{h}] and only once in a visit', not await pg.evaluate("document.getElementById('toast').classList.contains('on')"))
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
            await anim(b, errs)
            await ladder(b, errs)
            await notice_clear(b, errs)
            await loader_look(b, errs)
            await reachable(b, errs)
            await energy_migration(b, errs)
            await soon_tiles(b, errs)
            await kept(b, errs)
            await old_names(b, errs)
            await names(b, errs)
            await fin_logout(b, errs)
            await map_token(b, errs)
            await island_path(b, errs)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
