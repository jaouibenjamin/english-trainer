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
    fetched = []
    pg.on('request', lambda r: fetched.append(r.url))

    # ---- switch off ----
    await pg.goto(P.BASE + '#island/1'); await pg.wait_for_selector('.scr.island')
    check(f'[{tag}] off: the island has no extra games', await pg.locator('.xtr,.xtb').count() == 0)
    await pg.goto(P.BASE + '#extra/1/tf'); await pg.wait_for_selector('.scr.map,.map .isl')
    check(f'[{tag}] off: the game\'s address leads to the map', await pg.locator('#tfk').count() == 0)
    check(f'[{tag}] off: no game and no games stylesheet is fetched', not any(x in u for u in fetched for x in ('/tf.js', '/pairs.js', '/scramble.js', '/extra.css')), [u for u in fetched if 'extra' in u or 'tf.js' in u])
    check(f'[{tag}] off: the switch is not stored', await pg.evaluate(f"!('games' in (JSON.parse(localStorage.getItem('{SET_KEY}'))||{{}}))"))

    # ---- switch on ----
    await pg.goto(P.BASE + '?games=1#island/1'); await pg.wait_for_selector('.xtb'); await pg.wait_for_timeout(400)
    off = await pg.evaluate(FITS)
    check(f'[{tag}] on: the island screen fits with the extra row, nothing lies over anything', not off, off)
    bh = await pg.evaluate("Math.min(...[...document.querySelectorAll('.xtb')].map(b=>b.getBoundingClientRect().height))")
    check(f'[{tag}] on: one button per game, each at least 44 px high', bh >= 44 and await pg.locator('.xtb').count() == 3, bh)
    check(f'[{tag}] on: all four levels are still there', await pg.locator('.lvrow').count() == 4)
    await P.shot(pg, f'extra-{tag}-island')
    if not full:
        await c.close(); return
    await pg.goto(P.BASE + '#extra/3/tf'); await pg.wait_for_selector('.scr.map,.map .isl')
    check(f'[{tag}] on: an island that is still closed cannot be practised', await pg.locator('#tfk').count() == 0)
    await pg.goto(P.BASE + '#extra/1/nosuch'); await pg.wait_for_selector('.scr.map,.map .isl')
    check(f'[{tag}] on: an unknown game leads to the map', await pg.locator('#tfk').count() == 0)
    for k in ('__proto__', 'constructor', 'toString', 'hasOwnProperty'):
        await pg.goto(P.BASE + '#extra/1/' + k); await pg.wait_for_selector('.scr.map,.map .isl')
        check(f'[{tag}] on: "{k}" is not a game and leads to the map, with no error', await pg.locator('#tfk').count() == 0)

    await pg.goto(P.BASE + '#island/1'); await pg.wait_for_selector('.xtb')
    stored = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    progress = await pg.evaluate(PROGRESS)
    words = dict(await pg.evaluate(LIST + '(1)'))
    await pg.click('.xtb[data-to$="/tf"]'); await pg.wait_for_selector('#tfk')
    off = await pg.evaluate(FITS)
    check(f'[{tag}] the card screen fits', not off, off)
    small = await pg.evaluate("[...document.querySelectorAll('.tf button')].filter(e=>e.getBoundingClientRect().height<44||e.getBoundingClientRect().width<44).length")
    check(f'[{tag}] every button is at least 44 px', small == 0, small)
    await P.shot(pg, f'extra-{tag}-card')

    # ---- a wrong answer explains, and the word comes back ----
    first = await pg.evaluate(CARD)
    live = await pg.inner_text('#tfl')
    check(f'[{tag}] a screen reader is told the new card: the word and the meaning', first['en'] in live and first['he'].split(',')[0] in live, live)
    # (Alt+Left would also take the browser back a page, which is the browser's own business: Alt+Right has nowhere to go)
    await pg.keyboard.press('Alt+ArrowRight'); await pg.keyboard.press('Control+ArrowLeft'); await pg.keyboard.press('Meta+ArrowRight'); await pg.wait_for_timeout(150)
    check(f'[{tag}] an arrow key with Alt, Ctrl or Meta does not answer', await pg.locator('.tfe,.tfr').count() == 0 and await pg.evaluate('window.__lv.g.done') == 0)
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


PAIRS = "(()=>window.__lv&&window.__lv.kind==='pairs'?{cards:window.__lv.cards(),g:{found:[...window.__lv.g.found],open:window.__lv.g.open,lock:window.__lv.g.lock,turns:window.__lv.g.turns,misses:window.__lv.g.misses,n:window.__lv.g.n},ended:window.__lv.ended||null}:null)()"


async def pairs(b, w, h, errs, signed=False, api=None):
    """pairs: twelve closed cards, a word and its own meaning stay open, a wrong pair explains and turns back"""
    tag = f'pairs {w}x{h}' + (' class' if signed else '')
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    posts = []
    if signed:
        pg.on('request', lambda r: posts.append(r.post_data or '') if r.url.startswith(api) else None)
        await pg.goto(P.BASE); await pg.wait_for_selector('#lc')
        r = await pg.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'register',c:'EN-1234',n,p:'1357'})})).json()", [api, 'דור'])
        await pg.evaluate(f"localStorage.setItem('{KEY}',JSON.stringify({{u:{{c:'EN-1234',n:'דור',p:'1357'}}}}))")
    await pg.goto(P.BASE + '?games=1#island/1'); await pg.wait_for_selector('.xtb[data-to$="/pairs"]')
    if signed: await pg.wait_for_timeout(4500)          # the game's own sign-in refresh and first save must be over
    stored = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    progress = await pg.evaluate(PROGRESS)
    n0 = len(posts)
    words = dict(await pg.evaluate(LIST + '(1)'))
    await pg.click('.xtb[data-to$="/pairs"]'); await pg.wait_for_selector('.prk')
    R = await pg.evaluate(PAIRS)
    cards = R['cards']
    en_ = [x for x in cards if x['side'] == 'en']; he_ = [x for x in cards if x['side'] == 'he']
    check(f'[{tag}] twelve cards: six English words of the teacher\'s list and their six meanings, as written there', len(cards) == 12 and len(en_) == 6 and len(he_) == 6
          and all(x['text'] in words for x in en_) and all(any(y['k'] == x['k'] and words[y['text']].split(',')[0] == x['text'] for y in en_) for x in he_), cards)
    check(f'[{tag}] no two meaning cards are the same, so each belongs to one word only', len({x['text'] for x in he_}) == 6)
    closed = await pg.evaluate("[...document.querySelectorAll('.prk')].map(b=>[b.querySelector('.prt').textContent,b.getAttribute('aria-label')])")
    check(f'[{tag}] a closed card holds nothing to read, on screen or for a screen reader', all(t == '' and l == 'כרטיס סגור' for t, l in closed), closed[:3])
    off = await pg.evaluate(FITS)
    check(f'[{tag}] the board fits the screen', not off, off)
    small = await pg.evaluate("[...document.querySelectorAll('.pr button')].filter(e=>e.getBoundingClientRect().height<44||e.getBoundingClientRect().width<44).length")
    check(f'[{tag}] every card and button is at least 44 px', small == 0, small)
    await P.shot(pg, f'extra-{tag}-board')

    # a wrong pair: both shown, each explained with its own pair, then turned back; nothing found, nothing ended
    a = next(x for x in cards if x['side'] == 'en'); bb = next(x for x in cards if x['side'] == 'he' and x['k'] != a['k'])
    await pg.click(f'.prk[data-i="{a["i"]}"]'); await pg.click(f'.prk[data-i="{bb["i"]}"]'); await pg.wait_for_timeout(150)
    note = await pg.inner_text('#prx'); up = await pg.locator('.prk.up').count()
    en_b = next(x['text'] for x in en_ if x['k'] == bb['k'])
    check(f'[{tag}] a wrong pair stays open for a moment and explains both cards with their own pairs', up == 2 and a['text'] in note and words[a['text']].split(',')[0] in note and en_b in note and bb['text'] in note, note)
    await P.shot(pg, f'extra-{tag}-wrong')
    await pg.click(f'.prk[data-i="{a["i"]}"]')      # a tap while it is shown changes nothing
    await pg.wait_for_function("document.querySelectorAll('.prk.up').length===0", timeout=4000)
    R = await pg.evaluate(PAIRS)
    check(f'[{tag}] then both turn back; nothing is found and nothing ended', not R['g']['found'] and not R['g']['open'] and not R['g']['lock'] and R['g']['misses'] == 1 and not R['ended'], R['g'])

    # with the keyboard: Enter on a word and on its meaning finds the pair, and focus moves on to an open card
    def idx(k, side): return next(x['i'] for x in cards if x['k'] == k and x['side'] == side)
    await pg.focus(f'.prk[data-i="{idx(5, "en")}"]'); await pg.keyboard.press('Enter')
    await pg.focus(f'.prk[data-i="{idx(5, "he")}"]'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(120)
    fo = await pg.evaluate("(()=>{const a=document.activeElement;return {card:a.classList.contains('prk'),disabled:!!a.disabled,found:a.classList.contains('ok')}})()")
    check(f'[{tag}] keyboard: after a pair is found the focus moves to the next open card, not to the page', fo == {'card': True, 'disabled': False, 'found': False}, fo)
    # find every pair; the voice says each English word when its card is turned
    plays0 = await pg.evaluate("window.__plays.length")
    for k in range(5):
        for side in ('en', 'he'):
            i = next(x['i'] for x in cards if x['k'] == k and x['side'] == side)
            await pg.click(f'.prk[data-i="{i}"]')
        await pg.wait_for_timeout(120)
        if k == 0:
            st = await pg.evaluate("[...document.querySelectorAll('.prk.ok')].map(b=>[b.disabled,b.querySelector('.prt').textContent])")
            check(f'[{tag}] a word and its own meaning stay open, are marked found and cannot be turned again', len(st) == 4 and all(d and t for d, t in st), st)   # this pair and the one found by keyboard
            await pg.evaluate("i=>{const b=document.querySelector(`.prk[data-i='${i}']`);b.click();b.dispatchEvent(new MouseEvent('click',{bubbles:true}))}", i)
            check(f'[{tag}] a tap on a found card does nothing', (await pg.evaluate(PAIRS))['g']['open'] == [])
    await pg.wait_for_selector('.tfend')
    R = await pg.evaluate(PAIRS)
    text = await pg.inner_text('.tfend')
    check(f'[{tag}] the round ends when all six pairs are found, counts the tries and lists the six pairs', R['ended'] == {'turns': 7, 'misses': 1, 'n': 6} and all(x['text'] in text for x in en_), R['ended'])
    check(f'[{tag}] the keyboard carries on from "another round" when the round ends', await pg.evaluate("document.activeElement.matches('.tfend [data-force]')"))
    check(f'[{tag}] it shows no stars and no points', 'כוכב' not in text.replace('בלי כוכבים', '') and 'נקודות' not in text and await pg.locator('.tfend .bigstars').count() == 0)
    plays = await pg.evaluate("window.__plays.slice(%d).map(p=>p.url)" % plays0)
    spoken = [t for t in await pg.evaluate("window.__spoken") if t.strip()]
    check(f'[{tag}] each English card turned says its word from a recording; the browser voice is never used', len(plays) >= 5 and spoken == [], (len(plays), spoken))   # the five pairs after the keyboard one
    off = await pg.evaluate(FITS)
    check(f'[{tag}] the end screen fits', not off, off)
    await P.shot(pg, f'extra-{tag}-end')
    await pg.wait_for_timeout(3200)
    check(f'[{tag}] the pupil\'s progress is exactly as before and nothing was stored on the device',
          await pg.evaluate(PROGRESS) == progress and await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())") == stored)
    if signed:
        check(f'[{tag}] a whole round, with a mistake, sends nothing to the backend', len(posts) == n0, [p[:80] for p in posts[n0:]])
    await pg.click('.tfend [data-force]'); await pg.wait_for_selector('.prk')
    check(f'[{tag}] "another round" deals a new board', (await pg.evaluate(PAIRS))['g']['turns'] == 0)
    await c.close()


LETTERS = "(()=>window.__lv&&window.__lv.kind==='scramble'?{word:window.__lv.word(),tiles:window.__lv.tiles(),g:{done:window.__lv.g.done,first:window.__lv.g.first,pos:window.__lv.g.pos,lock:window.__lv.g.lock,n:window.__lv.g.n,queue:window.__lv.g.queue.map(q=>q.w.en)},ended:window.__lv.ended||null}:null)()"


async def letters(b, w, h, errs, signed=False, api=None):
    """letters: the meaning is shown, the word heard, its letters mixed; a wrong letter is not placed and explained"""
    tag = f'letters {w}x{h}' + (' class' if signed else '')
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    posts = []
    if signed:
        pg.on('request', lambda r: posts.append(r.post_data or '') if r.url.startswith(api) else None)
        await pg.goto(P.BASE); await pg.wait_for_selector('#lc')
        await pg.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'register',c:'EN-1234',n,p:'1357'})})).json()", [api, 'עמית'])
        await pg.evaluate(f"localStorage.setItem('{KEY}',JSON.stringify({{u:{{c:'EN-1234',n:'עמית',p:'1357'}}}}))")
    await pg.goto(P.BASE + '?games=1#island/1'); await pg.wait_for_selector('.xtb[data-to$="/scramble"]')
    if signed: await pg.wait_for_timeout(4500)
    stored = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    progress = await pg.evaluate(PROGRESS)
    n0 = len(posts)
    words = dict(await pg.evaluate(LIST + '(1)'))
    await pg.click('.xtb[data-to$="/scramble"]'); await pg.wait_for_selector('.scl')
    R = await pg.evaluate(LETTERS)
    check(f'[{tag}] a round has six words of the teacher\'s list, single words of 3 to 9 letters', R['g']['n'] == 6 and all(x in words and x.isalpha() and 3 <= len(x) <= 9 for x in R['g']['queue']), R['g'])
    word = R['word']
    shown = await pg.inner_text('.sck')
    tiles = ''.join(t['ch'] for t in R['tiles'])
    check(f'[{tag}] the card shows the word\'s own meaning and its letters mixed, in lower case, never already in order', words[word].split(',')[0] in shown and sorted(tiles) == sorted(word.lower()) and tiles != word.lower() and word not in shown, [word, tiles])
    off = await pg.evaluate(FITS)
    check(f'[{tag}] the screen fits', not off, off)
    small = await pg.evaluate("[...document.querySelectorAll('.sc button:not(.used)')].filter(e=>e.getBoundingClientRect().height<44||e.getBoundingClientRect().width<44).length")
    check(f'[{tag}] every tile and button is at least 44 px', small == 0, small)
    await P.shot(pg, f'extra-{tag}-card')

    # a wrong letter: not placed, the tile shakes, the line says which letter it is not; two in a row light the right tile
    want = word[0].lower()
    wrong = [t for t in R['tiles'] if t['ch'].lower() != want]
    await pg.click(f'.scl[data-l="{wrong[0]["i"]}"]'); await pg.wait_for_timeout(80)
    R2 = await pg.evaluate(LETTERS); msg = await pg.inner_text('#scm')
    check(f'[{tag}] a wrong letter is not placed and the line says the next letter is not that one', R2['g']['pos'] == 0 and wrong[0]['ch'] in msg and 'לא' in msg, msg)
    glow0 = await pg.locator('.scl.glow').count()
    await pg.click(f'.scl[data-l="{wrong[-1]["i"]}"]'); await pg.wait_for_timeout(80)
    glow = await pg.evaluate("[...document.querySelectorAll('.scl.glow')].map(b=>b.textContent)")
    check(f'[{tag}] after two wrong letters in a row the right tile glows', glow0 == 0 and len(glow) == 1 and glow[0].lower() == want, glow)
    await P.shot(pg, f'extra-{tag}-wrong')
    # build the word: by tap, and the next word by keyboard
    for k, ch in enumerate(word):
        t = await pg.evaluate("ch=>{const t=window.__lv.tiles().find(x=>!x.used&&x.ch.toLowerCase()===ch.toLowerCase());return t&&t.i}", ch)
        await pg.click(f'.scl[data-l="{t}"]')
    await pg.wait_for_timeout(100)
    done = await pg.inner_text('.sca,.tfa')
    check(f'[{tag}] the finished word shows with its meaning and says it will come back', word in done and words[word].split(',')[0] in done and 'תחזור' in done, done)
    await pg.wait_for_selector('.scl'); await pg.wait_for_timeout(200)
    R3 = await pg.evaluate(LETTERS)
    check(f'[{tag}] the word with a wrong letter went to the end of the round; nothing ended', R3['g']['queue'][-1] == word and R3['g']['done'] == 0 and not R3['ended'], R3['g'])
    for ch in R3['word']:
        await pg.keyboard.press(ch)
    await pg.wait_for_timeout(100)
    check(f'[{tag}] the keyboard builds a word too', R3['word'] in await pg.inner_text('.tfa'))
    # finish the round
    for _ in range(12):
        await pg.wait_for_timeout(1500)
        R4 = await pg.evaluate(LETTERS)
        if not R4 or R4['ended']: break
        for ch in R4['word']:
            t = await pg.evaluate("ch=>{const t=window.__lv.tiles().find(x=>!x.used&&x.ch.toLowerCase()===ch.toLowerCase());return t&&t.i}", ch)
            await pg.click(f'.scl[data-l="{t}"]')
    await pg.wait_for_selector('.tfend')
    end = (await pg.evaluate(LETTERS))['ended']; text = await pg.inner_text('.tfend')
    check(f'[{tag}] the round ends when every word was built, the word with a mistake came back once, and it is listed to go over', end['n'] == 6 and end['first'] == 5 and end['missed'] == [word] and word in text, end)
    check(f'[{tag}] it shows no stars and no points', 'נקודות' not in text and await pg.locator('.tfend .bigstars').count() == 0)
    spoken = [t for t in await pg.evaluate("window.__spoken") if t.strip()]
    check(f'[{tag}] the words are spoken from recordings; the browser voice is never used', len(await pg.evaluate("window.__plays")) >= 6 and spoken == [], spoken)
    off = await pg.evaluate(FITS)
    check(f'[{tag}] the end screen fits', not off, off)
    await P.shot(pg, f'extra-{tag}-end')
    await pg.wait_for_timeout(3200)
    check(f'[{tag}] the pupil\'s progress is exactly as before and nothing was stored on the device',
          await pg.evaluate(PROGRESS) == progress and await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())") == stored)
    if signed:
        check(f'[{tag}] a whole round, with mistakes, sends nothing to the backend', len(posts) == n0, [p[:80] for p in posts[n0:]])
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
    procs = P.start_servers(mock=True)      # its own servers on free ports (tests/play.py)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await local(b, 390, 844, errs, True)
            await local(b, 360, 740, errs, False)
            await local(b, 360, 640, errs, True)
            await local(b, 1366, 768, errs, True)
            await klass(b, errs)
            await pairs(b, 390, 844, errs)
            await pairs(b, 360, 640, errs)
            await pairs(b, 1366, 768, errs)
            await pairs(b, 390, 844, errs, signed=True, api=f'http://127.0.0.1:{P.API_PORT}/')
            await letters(b, 390, 844, errs)
            await letters(b, 360, 640, errs)
            await letters(b, 1366, 768, errs)
            await letters(b, 390, 844, errs, signed=True, api=f'http://127.0.0.1:{P.API_PORT}/')
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
