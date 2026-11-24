#!/usr/bin/env python3
"""The extra practice games (js/extra.js), behind their switch. For now: true or not? (js/tf.js).

    python3 tests/extra.py              # phone sizes, laptop, and a signed-in pupil against the mock backend
    python3 tests/extra.py --shots DIR  # also save a PNG of every screen

Checks: with the switch off nothing of it shows; with it on, the island has a button and still fits; every card is a
word of the teacher's list with a meaning from that list; a wrong answer explains and the word comes back; buttons,
swipe and keys all answer; the word is spoken from its recording, never by the browser; and playing changes nothing
in the pupil's progress, saves nothing and sends nothing."""
import asyncio, json, os, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, port_open, fails

KEY, SET_KEY = 'aam-unit1-v1', 'word-islands-settings-v1'
CARD = "(window.__lv&&!window.__lv.ended&&window.__lv.card())||null"
LIST = "(async p=>{const D=await import('/js/data.js');return D.wordsOf(p).map(w=>[w.en,w.he])})"
PROGRESS = "(()=>{const s=window.__game.S();return JSON.stringify([s.w,s.st,s.read,s.pts,s.g,s.m,s.x,s.day,s.streak])})()"
FITS = """(()=>{const s=document.getElementById('stage').getBoundingClientRect();
 const out=[...document.querySelectorAll('#view .scr>*,#view button')].filter(e=>{const r=e.getBoundingClientRect();return r.height&&(r.bottom>s.bottom+1||r.top<s.top-1||r.left<s.left-1||r.right>s.right+1)}).map(e=>e.className);
 const parts=[...document.querySelectorAll('#view .scr>*,#view .lvlist>*')].filter(e=>!e.classList.contains('lvlist')&&e.getBoundingClientRect().height).map(e=>[e.className,e.getBoundingClientRect()]);
 for(let i=0;i<parts.length;i++)for(let j=i+1;j<parts.length;j++){const a=parts[i][1],b=parts[j][1];if(a.top<b.bottom-2&&a.bottom>b.top+2&&a.left<b.right-2&&a.right>b.left+2)out.push('overlap: '+parts[i][0]+' / '+parts[j][0])}
 return out.slice(0,4)})()"""


async def press(pg, yes, how):
    """answer the card on screen: by button, by swipe or by key"""
    if how == 'button':
        await pg.click('.tfy' if yes else '.tfx')
    elif how == 'key':
        await pg.keyboard.press('ArrowRight' if yes else 'ArrowLeft')
    else:
        box = await pg.locator('#tfk').bounding_box()
        x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] * .7
        await pg.mouse.move(x, y); await pg.mouse.down()
        for k in range(1, 7):
            await pg.mouse.move(x + (22 if yes else -22) * k, y)
        await pg.mouse.up()


async def local(b, w, h, errs, full):
    tag = f'{w}x{h}'
    c, pg = await new_page(b, w, h, errs=errs)

    # ---- switch off ----
    await pg.goto(P.BASE + '#island/1'); await pg.wait_for_selector('.scr.island')
    check(f'[{tag}] off: the island has no extra games', await pg.locator('.xtr,.xtb').count() == 0)
    await pg.goto(P.BASE + '#extra/1/tf'); await pg.wait_for_selector('.scr.map,.map .isl')
    check(f'[{tag}] off: the game\'s address leads to the map', await pg.locator('#tfk').count() == 0)
    check(f'[{tag}] off: the switch is not stored', await pg.evaluate(f"!('games' in (JSON.parse(localStorage.getItem('{SET_KEY}'))||{{}}))"))

    # ---- switch on ----
    await pg.goto(P.BASE + '?games=1#island/1'); await pg.wait_for_selector('.xtb'); await pg.wait_for_timeout(400)
    off = await pg.evaluate(FITS)
    check(f'[{tag}] on: the island screen fits with the extra row, nothing lies over anything', not off, off)
    bh = await pg.evaluate("document.querySelector('.xtb').getBoundingClientRect().height")
    check(f'[{tag}] on: the button is at least 44 px high', bh >= 44, bh)
    check(f'[{tag}] on: all four levels are still there', await pg.locator('.lvrow').count() == 4)
    await P.shot(pg, f'extra-{tag}-island')
    if not full:
        await c.close(); return
    await pg.goto(P.BASE + '#extra/3/tf'); await pg.wait_for_selector('.scr.map,.map .isl')
    check(f'[{tag}] on: an island that is still closed cannot be practised', await pg.locator('#tfk').count() == 0)
    await pg.goto(P.BASE + '#extra/1/nosuch'); await pg.wait_for_selector('.scr.map,.map .isl')
    check(f'[{tag}] on: an unknown game leads to the map', await pg.locator('#tfk').count() == 0)

    await pg.goto(P.BASE + '#island/1'); await pg.wait_for_selector('.xtb')
    stored = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    progress = await pg.evaluate(PROGRESS)
    words = dict(await pg.evaluate(LIST + '(1)'))
    await pg.click('.xtb'); await pg.wait_for_selector('#tfk')
    off = await pg.evaluate(FITS)
    check(f'[{tag}] the card screen fits', not off, off)
    small = await pg.evaluate("[...document.querySelectorAll('.tf button')].filter(e=>e.getBoundingClientRect().height<44||e.getBoundingClientRect().width<44).length")
    check(f'[{tag}] every button is at least 44 px', small == 0, small)
    await P.shot(pg, f'extra-{tag}-card')

    # ---- a wrong answer explains, and the word comes back ----
    first = await pg.evaluate(CARD)
    n = await pg.evaluate('window.__lv.g.n')
    check(f'[{tag}] a round has 8 words', n == 8, n)
    await press(pg, not first['truth'], 'button'); await pg.wait_for_selector('.tfe')
    exp = await pg.inner_text('.tfe')
    check(f'[{tag}] a wrong answer shows the word with its own meaning', first['en'] in exp and words[first['en']].split(',')[0] in exp)
    check(f'[{tag}] and says the word will come back; nothing ended', 'תחזור' in exp and await pg.evaluate('window.__lv.g.queue.length') == n and await pg.evaluate('window.__lv.g.done') == 0)
    await P.shot(pg, f'extra-{tag}-explain')
    await pg.keyboard.press('Enter'); await pg.wait_for_selector('.tfy')
    check(f'[{tag}] the word went to the end of the round', (await pg.evaluate('window.__lv.g.queue.at(-1).w.en')) == first['en'])

    # ---- play to the end: buttons, swipe and keys; every card is checked against the teacher's list ----
    bad, seen, wrongs, how_used = [], [], 1, set()
    for step in range(40):
        k = await pg.evaluate(CARD)
        if not k: break
        await pg.wait_for_selector('.tfy')
        if k['en'] not in words: bad.append('not a word of the list: ' + k['en'])
        elif k['he'] not in words.values(): bad.append('not a meaning of the list: ' + k['he'])
        elif (words[k['en']] == k['he']) != k['truth']: bad.append('wrong truth for ' + k['en'])
        shown = await pg.inner_text('#tfk')
        if k['en'] not in shown or k['he'].split(',')[0] not in shown: bad.append('card text for ' + k['en'])
        seen.append(k['en'])
        how = ('button', 'swipe', 'key')[step % 3]; how_used.add(how)
        if step == 4:   # one more mistake, by swipe, later in the round
            await press(pg, not k['truth'], 'swipe'); await pg.wait_for_selector('.tfe'); wrongs += 1
            await pg.click('[data-a=tfnext]'); await pg.wait_for_selector('.tfy'); continue
        await press(pg, k['truth'], how)
        await pg.wait_for_timeout(1150)
    check(f'[{tag}] every card is a word of the teacher\'s list with a meaning from that list, and its answer is right', not bad, bad[:4])
    check(f'[{tag}] buttons, swipe and arrow keys all answer', how_used == {'button', 'swipe', 'key'})
    await pg.wait_for_selector('.tfend')
    end = await pg.evaluate('window.__lv.ended')
    check(f'[{tag}] the round ends only when every word was answered right once', len(set(seen)) == 8 and len(seen) == 8 + wrongs - 1, (len(seen), wrongs))
    check(f'[{tag}] the end screen counts first tries and lists the words to go over', end['n'] == 8 and end['first'] == 8 - len(end['missed']) and 1 <= len(end['missed']) <= 2 and first['en'] in end['missed'], end)
    text = await pg.inner_text('.tfend')
    check(f'[{tag}] it shows no stars and no points', 'כוכב' not in text and 'נקודות' not in text and await pg.locator('.tfend .star,.tfend .bigstars').count() == 0)
    off = await pg.evaluate(FITS)
    check(f'[{tag}] the end screen fits', not off, off)
    await P.shot(pg, f'extra-{tag}-end')

    # ---- voice ----
    plays = await pg.evaluate("window.__plays.map(p=>p.url)")
    spoken = [t for t in await pg.evaluate("window.__spoken") if t.strip()]   # the game's own silent wake-up of the speech engine (a blank) is not content
    check(f'[{tag}] each card says its word from a recording', len(plays) >= 8, len(plays))
    check(f'[{tag}] the browser voice was never used', spoken == [], spoken)

    # ---- nothing kept ----
    await pg.wait_for_timeout(3200)
    check(f'[{tag}] the pupil\'s progress is exactly as before (no stars, no points, no word marked)', await pg.evaluate(PROGRESS) == progress)
    check(f'[{tag}] nothing was stored on the device', await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())") == stored)
    await pg.click('.tfend [data-force]'); await pg.wait_for_selector('#tfk')
    check(f'[{tag}] "another round" deals a new round', await pg.evaluate('window.__lv.g.done') == 0)
    await pg.click('.tf .top .rb'); await pg.wait_for_selector('.scr.island')
    check(f'[{tag}] back leads to the island, and the game is gone', await pg.evaluate('!window.__lv'))

    await pg.goto(P.BASE + '?games=0#island/1'); await pg.wait_for_selector('.scr.island')
    check(f'[{tag}] ?games=0 takes the switch away', await pg.locator('.xtr').count() == 0)
    await c.close()


async def klass(b, errs):
    tag = 'class'
    api = f'http://127.0.0.1:{P.API_PORT}/'
    name = 'גפן'
    c, pg = await new_page(b, 390, 844, api=api, errs=errs)
    posts = []
    pg.on('request', lambda r: posts.append(r.post_data or '') if r.url.startswith(api) else None)
    await pg.goto(P.BASE); await pg.wait_for_selector('#lc')
    r = await pg.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'register',c:'EN-1234',n,p:'2468'})})).json()", [api, name])
    check(f'[{tag}] a pupil is registered on the mock backend', r.get('ok') or r.get('e') == 'taken', r)
    await pg.evaluate(f"localStorage.setItem('{KEY}',JSON.stringify({{u:{{c:'EN-1234',n:'{name}',p:'2468'}}}}))")
    await pg.goto(P.BASE + '?games=1#extra/1/tf'); await pg.wait_for_selector('#tfk')
    await pg.wait_for_timeout(4500)                       # the game's own sign-in refresh and first save must be over
    await pg.wait_for_selector('#tfk')
    n0, pts = len(posts), await pg.evaluate('window.__game.S().pts')
    for step in range(40):
        k = await pg.evaluate(CARD)
        if not k: break
        await pg.wait_for_selector('.tfy')
        if step == 1:
            await press(pg, not k['truth'], 'button'); await pg.wait_for_selector('.tfe'); await pg.click('[data-a=tfnext]'); continue
        await press(pg, k['truth'], 'button'); await pg.wait_for_timeout(1150)
    await pg.wait_for_selector('.tfend')
    await pg.wait_for_timeout(3200)                       # longer than the save delay
    check(f'[{tag}] a whole round, with a mistake, sends nothing to the backend', len(posts) == n0, [p[:80] for p in posts[n0:]])
    check(f'[{tag}] and the points for the class table did not move', await pg.evaluate('window.__game.S().pts') == pts)
    await c.close()


async def main():
    procs = []
    if not port_open(P.PORT):
        procs.append(subprocess.Popen([sys.executable, '-m', 'http.server', str(P.PORT), '--bind', '127.0.0.1'], cwd=P.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    if not port_open(P.API_PORT):
        procs.append(subprocess.Popen(['node', P.MOCK], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for _ in range(40):
        if port_open(P.PORT) and port_open(P.API_PORT): break
        time.sleep(.1)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await local(b, 390, 844, errs, True)
            await local(b, 360, 740, errs, False)
            await local(b, 360, 640, errs, True)
            await local(b, 1366, 768, errs, True)
            await klass(b, errs)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
