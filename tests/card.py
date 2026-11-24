#!/usr/bin/env python3
"""The progress card (js/card.js), behind its switch.

    python3 tests/card.py              # phone, small phone, laptop, and a signed-in pupil against the mock backend
    python3 tests/card.py --shots DIR  # also save PNGs of the screens and the saved picture

Checks: with the switch off nothing of it shows; with it on, the card shows the numbers of the pupil's progress; the
picture is a PNG made on the device; the only personal detail is the first name of a signed-in pupil; nothing is
saved and nothing is sent."""
import asyncio, json, os, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, port_open, fails

KEY, SET_KEY = 'aam-unit1-v1', 'word-islands-settings-v1'
# a pupil with some progress: island 1 full, island 2 partly; 3 words learned; 2 stories read
STATE = {'g': {'st': {'1-sling': 3, '1-listen': 3, '1-read': 3, '1-bridge': 3, '2-sling': 2, '2-listen': 1}, 'ball': 0, 'ob': {}, 'plays': 6},
         'w': {'goal': 2, 'kick': 3, 'song': 2, 'hobby': 1}, 'read': {'1': 5, '2': 3, '3': 0}, 'pts': 120}
WANT = {'stars': 15, 'max': 66, 'words': 3, 'wordsMax': 59, 'reads': 2, 'readsMax': 5}
SHARE_STUB = """(()=>{window.__shared=[];navigator.canShare=d=>!!(d&&d.files&&d.files.length);
 navigator.share=async d=>{window.__shared.push({keys:Object.keys(d).sort(),n:d.files.length,type:d.files[0].type,name:d.files[0].name,size:d.files[0].size})}})()"""
NO_SHARE = "(()=>{try{delete Navigator.prototype.share;delete Navigator.prototype.canShare}catch(e){}navigator.share=undefined;navigator.canShare=undefined})()"
PIXELS = """(async()=>{const C=await import('/js/card.js'),cv=await C.cardCanvas(),c=cv.getContext('2d'),d=c.getImageData(0,0,cv.width,cv.height).data;
 let dark=0,gold=0;for(let i=0;i<d.length;i+=4){if(d[i]<110&&d[i+1]<90&&d[i+2]<80)dark++;if(d[i]>220&&d[i+1]>160&&d[i+1]<200&&d[i+2]<90)gold++}
 const band=(y0,y1)=>{let n=0;const q=c.getImageData(60,y0,cv.width-120,y1-y0).data;for(let i=0;i<q.length;i+=4)if(q[i]<110&&q[i+1]<90&&q[i+2]<80)n++;return n};
 return {w:cv.width,h:cv.height,corner:[d[0],d[1],d[2]],dark,gold,nameBand:band(225,305)}})()"""


async def seed(pg, extra=None):
    s = dict(STATE)
    if extra: s.update(extra)
    await pg.add_init_script(f"if(!sessionStorage.getItem('seeded')){{sessionStorage.setItem('seeded','1');localStorage.setItem('{KEY}',JSON.stringify({json.dumps(s, ensure_ascii=False)}))}}")


async def fits(pg):
    return await pg.evaluate("""(()=>{const s=document.getElementById('stage').getBoundingClientRect();
      const out=[...document.querySelectorAll('#view .scr>*,#view .btn,#view .setrow')].filter(e=>{const r=e.getBoundingClientRect();return r.height&&(r.bottom>s.bottom+1||r.top<s.top-1||r.left<s.left-1||r.right>s.right+1)}).map(e=>e.className);
      /* the parts of the screen must not lie over one another either */
      const parts=[...document.querySelectorAll('#view .scr>*,#view .scr>.fill>*')].filter(e=>!e.classList.contains('fill')&&e.getBoundingClientRect().height).map(e=>[e.className,e.getBoundingClientRect()]);
      for(let i=0;i<parts.length;i++)for(let j=i+1;j<parts.length;j++){const a=parts[i][1],b=parts[j][1];if(a.top<b.bottom-2&&a.bottom>b.top+2&&a.left<b.right-2&&a.right>b.left+2)out.push('overlap: '+parts[i][0]+' / '+parts[j][0])}
      return out.slice(0,4)})()""")


async def local(b, w, h, errs, share):
    tag = f'{w}x{h}' + (' share' if share else '')
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.add_init_script(SHARE_STUB if share else NO_SHARE)
    await seed(pg)

    # ---- switch off ----
    await pg.goto(P.BASE + '#settings'); await pg.wait_for_selector('.scr.settings')
    check(f'[{tag}] off: settings has no card row', await pg.locator('[data-to=card]').count() == 0)
    await pg.goto(P.BASE + '#card'); await pg.wait_for_selector('.scr.settings')
    check(f'[{tag}] off: the card address leads back to settings, no card is drawn', await pg.locator('#rc').count() == 0)
    check(f'[{tag}] off: the switch is not stored', await pg.evaluate(f"!('card' in (JSON.parse(localStorage.getItem('{SET_KEY}'))||{{}}))"))

    # ---- switch on ----
    await pg.goto(P.BASE + '?card=1#settings'); await pg.wait_for_selector('[data-to=card]')
    check(f'[{tag}] ?card=1 gives the device the switch and settings a row', await pg.evaluate(f"JSON.parse(localStorage.getItem('{SET_KEY}')).card===true"))
    off = await fits(pg)
    check(f'[{tag}] on: the settings screen still fits with the extra row', not off, off)
    row_h = await pg.evaluate("document.querySelector('[data-to=card]').getBoundingClientRect().height")
    check(f'[{tag}] on: the row is at least 44 px high', row_h >= 44, row_h)
    await P.shot(pg, f'card-{tag}-settings')
    await pg.goto(P.BASE + '#settings'); await pg.wait_for_selector('[data-to=card]')
    before = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    await pg.click('[data-to=card]'); await pg.wait_for_selector('#rc')
    d = await pg.evaluate("(async()=>(await import('/js/card.js')).cardData())()")
    check(f'[{tag}] the card counts the pupil\'s progress', all(d[k] == v for k, v in WANT.items()), d)
    check(f'[{tag}] one row for each island, with its own stars', [(i['got'], i['max']) for i in d['islands']] == [(12, 12), (3, 12), (0, 12), (0, 12), (0, 12), (0, 6)], d['islands'])
    text = await pg.inner_text('#rc')
    check(f'[{tag}] the screen shows those numbers', all(x in text for x in ('15 / 66', '12 / 12', '3 / 12', '3 / 59', '2 / 5', d['date'])))
    check(f'[{tag}] not signed in to a class: no name on the card', d['name'] == '' and await pg.locator('.rch b').count() == 0)
    off = await fits(pg)
    check(f'[{tag}] the card screen fits', not off, off)
    small = await pg.evaluate("[...document.querySelectorAll('.rcard .btn,.rcard .rb')].filter(e=>e.getBoundingClientRect().height<44).length")
    check(f'[{tag}] every button is at least 44 px high', small == 0, small)
    await P.shot(pg, f'card-{tag}')

    # ---- the picture ----
    px = await pg.evaluate(PIXELS)
    check(f'[{tag}] the picture is 1080x1350, light, with text and gold bars', px['w'] == 1080 and px['h'] == 1350 and min(px['corner']) > 235 and px['dark'] > 8000 and px['gold'] > 3000, px)
    check(f'[{tag}] no name is drawn on the picture', px['nameBand'] < 600, px['nameBand'])
    async with pg.expect_download() as dl:
        await pg.click('[data-a=cardsave]')
    f = await dl.value
    path = await f.path()
    data = open(path, 'rb').read()
    check(f'[{tag}] "save as picture" downloads a PNG whose file name is the same for everyone', f.suggested_filename == 'word-islands-card.png' and data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) > 20000, (f.suggested_filename, len(data)))
    check(f'[{tag}] the PNG carries no text or other metadata', not any(k in data for k in (b'tEXt', b'iTXt', b'zTXt', b'eXIf')))
    if P.SHOTS:
        os.makedirs(P.SHOTS, exist_ok=True); open(os.path.join(P.SHOTS, f'card-{tag}-picture.png'), 'wb').write(data)
    if share:
        await pg.click('[data-a=cardshare]'); await pg.wait_for_function('window.__shared.length===1')
        s = (await pg.evaluate('window.__shared'))[0]
        check(f'[{tag}] "share" hands the device one PNG and nothing else (no text, no link)', s['keys'] == ['files'] and s['n'] == 1 and s['type'] == 'image/png' and s['name'] == 'word-islands-card.png', s)
    else:
        check(f'[{tag}] a device that cannot share files has no share button', await pg.locator('[data-a=cardshare]').count() == 0)
    await pg.wait_for_timeout(300)
    after = await pg.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
    check(f'[{tag}] opening the card and saving the picture stored nothing', before == after)
    await pg.click('.rcard .top .rb'); await pg.wait_for_selector('.scr.settings')
    check(f'[{tag}] back leads to settings', True)

    await pg.goto(P.BASE + '?card=0#settings'); await pg.wait_for_selector('.scr.settings')
    check(f'[{tag}] ?card=0 takes the switch away', await pg.locator('[data-to=card]').count() == 0)
    await c.close()


async def klass(b, errs):
    tag = 'class'
    api = f'http://127.0.0.1:{P.API_PORT}/'
    name = 'נטע'
    c, pg = await new_page(b, 390, 844, api=api, errs=errs)
    await pg.add_init_script(NO_SHARE)
    posts = []
    pg.on('request', lambda r: posts.append(r.post_data or '') if r.url.startswith(api) else None)
    await pg.goto(P.BASE); await pg.wait_for_selector('#lc')
    r = await pg.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'register',c:'EN-1234',n,p:'2468'})})).json()", [api, name])
    check(f'[{tag}] a pupil is registered on the mock backend', r.get('ok') or r.get('e') == 'taken', r)
    await pg.evaluate(f"localStorage.setItem('{KEY}',JSON.stringify(Object.assign({json.dumps(STATE, ensure_ascii=False)},{{u:{{c:'EN-1234',n:'{name}',p:'2468'}}}})))")
    await pg.goto(P.BASE + '?card=1#card'); await pg.wait_for_selector('#rc')
    await pg.wait_for_timeout(4500)                       # the sign-in refresh may draw the screen again, and the game's own first save (the device's progress going to the account) must be over
    await pg.wait_for_selector('#rc')
    d = await pg.evaluate("(async()=>(await import('/js/card.js')).cardData())()")
    check(f'[{tag}] signed in: the card carries the first name the pupil signed in with', d['name'] == name and (await pg.inner_text('.rch b')) == name, d['name'])
    px = await pg.evaluate(PIXELS)
    check(f'[{tag}] and the picture has it too', px['nameBand'] > 1500, px['nameBand'])
    keys = sorted(await pg.evaluate("(async()=>Object.keys((await import('/js/card.js')).cardData()))()"))
    check(f'[{tag}] the card holds a name, a date and counts, nothing else', keys == ['date', 'islands', 'max', 'name', 'reads', 'readsMax', 'stars', 'words', 'wordsMax'], keys)
    n0 = len(posts)
    async with pg.expect_download() as dl:
        await pg.click('[data-a=cardsave]')
    await dl.value
    await pg.wait_for_timeout(3200)                       # longer than the save delay
    new = posts[n0:]
    check(f'[{tag}] making the picture sends nothing to the backend', not new, [p[:80] for p in new])
    check(f'[{tag}] nothing the backend was sent mentions the card', not any('card' in p for p in posts))
    # with the account panel the settings screen is at its fullest: the card row must not make it any taller than it is
    # without the switch (at 360x640 it is already a little too tall on its own)
    BOTTOM = "Math.max(...[...document.querySelectorAll('.settings .panel')].map(e=>e.getBoundingClientRect().bottom))"
    for w, h in ((390, 844), (360, 740), (360, 640)):
        await pg.set_viewport_size({'width': w, 'height': h})
        await pg.goto(P.BASE + '?card=0#settings'); await pg.wait_for_selector('.scr.settings'); await pg.wait_for_timeout(300)
        base = await pg.evaluate(BOTTOM)
        await pg.goto(P.BASE + '?card=1#settings'); await pg.wait_for_selector('[data-to=card]'); await pg.wait_for_timeout(300)
        mine = await pg.evaluate(BOTTOM)
        check(f'[{tag}] signed in at {w}x{h}: settings fits, or is no taller with the card row than without', mine <= h or mine <= base + 1, (base, mine))
        if h > 700:
            off = await fits(pg)
            check(f'[{tag}] signed in at {w}x{h}: and it fits', not off, off)
        row_h = await pg.evaluate("document.querySelector('[data-to=card]').getBoundingClientRect().height")
        check(f'[{tag}] signed in at {w}x{h}: the row is at least 44 px high', row_h >= 44, row_h)
        await P.shot(pg, f'card-class-settings-{w}x{h}')
    await P.shot(pg, 'card-class')
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
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            await local(b, 390, 844, errs, False)
            await local(b, 390, 844, errs, True)
            await local(b, 360, 740, errs, False)
            await local(b, 360, 640, errs, False)
            await local(b, 1366, 768, errs, False)
            await klass(b, errs)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
