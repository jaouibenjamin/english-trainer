#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The game page's Latin font is asked for early by js/csplog.js (it was a static tag in index.html), for the look in use.

    python3 tests/font_preload.py

With the design flag off: the link is the old tag to the letter (URL, rel, as, type, crossorigin), the font is downloaded
once (a preload that does not match the font's own request would download it twice, and Chrome warns), and the text is in
that font. With the flag on: the new look's font instead, and no request for the old look's. With storage blocked or the
block failing: the page still loads and the font still arrives through game.css's @font-face. On the other pages nothing
is added: run.html keeps its own static tag, the others never had one."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, fails
from playwright.async_api import async_playwright

PL, RU = 'assets/font/playpen-latin.woff2', 'assets/font/rubik-latin.woff2'
LINKS = "[...document.querySelectorAll('link[rel=preload][as=font]')].map(l=>[l.getAttribute('href'),l.getAttribute('as'),l.getAttribute('type'),l.getAttribute('crossorigin')])"
BLOCK = "Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})"


async def page(b, url, init=None):
    c = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    pg = await c.new_page()
    reqs, warn, errs = [], [], []
    pg.on('request', lambda r: reqs.append(r.url))
    pg.on('console', lambda m: warn.append(m.text) if m.type in ('warning', 'error') and ('preload' in m.text or 'font' in m.text.lower()) else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.add_init_script("Object.defineProperty(window,'API_URL',{get:()=>'',set(){},configurable:true})")
    if init: await pg.add_init_script(init)
    await pg.goto(P.BASE.rsplit('/', 1)[0] + '/' + url)
    return c, pg, reqs, warn, errs


async def main():
    procs = P.start_servers()
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            # flag off: the old tag exactly, one download, the text in that font
            c, pg, reqs, warn, errs = await page(b, 'index.html#map')
            await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(3500)
            L = await pg.evaluate(LINKS)
            check('flag off: the early font link is the old static tag to the letter (URL, as, type, crossorigin)', [PL, 'font', 'font/woff2', ''] in L and not any(h == RU for h, *_ in L), L)
            n = sum(u.endswith(PL) for u in reqs)
            check('flag off: the Latin font is downloaded once (the preload matches the font\'s own request)', n == 1, n)
            check('flag off: no new-look font', not any(u.endswith(RU) for u in reqs))
            used = await pg.evaluate("document.fonts.check(\"700 20px 'Playpen Sans Hebrew'\",'Word')&&[...document.fonts].some(f=>f.family.includes('Playpen')&&f.status==='loaded'&&f.unicodeRange.includes('U+0-FF'))")
            check('flag off: English text is drawn in the old look\'s font (loaded)', used, used)
            check('flag off: no browser warning about a preload (unused or mismatched)', not warn, warn)
            check('flag off: no page error', not errs, errs)
            await c.close()
            # flag on: the new look's font, not the old one's preload
            c, pg, reqs, warn, errs = await page(b, 'index.html?ds=1#map')
            await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(3500)
            L = await pg.evaluate(LINKS)
            check('flag on: the early font link is the new look\'s font, not the old one\'s', [RU, 'font', 'font/woff2', ''] in L and not any(h == PL for h, *_ in L), L)
            check('flag on: the new look\'s font is downloaded once', sum(u.endswith(RU) for u in reqs) == 1, sum(u.endswith(RU) for u in reqs))
            check('flag on: no browser warning about a preload (unused or mismatched)', not warn, warn)
            await c.close()
            # storage blocked: no early link from the flag, the page loads, the font arrives through @font-face
            c, pg, reqs, warn, errs = await page(b, 'index.html#map', BLOCK)
            await pg.wait_for_selector('.scr', timeout=15000); await pg.wait_for_timeout(3500)
            ok = await pg.evaluate("document.fonts.check(\"700 20px 'Playpen Sans Hebrew'\",'Word')")
            check('storage blocked: the page loads and the Latin font still arrives (once)', await pg.locator('.scr').count() >= 1 and ok and sum(u.endswith(PL) for u in reqs) == 1, [ok, sum(u.endswith(PL) for u in reqs), errs[:2]])
            await c.close()
            # the block itself failing (no URLSearchParams, no createElement for link): nothing added, the page as before
            c, pg, reqs, warn, errs = await page(b, 'index.html#map', "window.__ce=Document.prototype.createElement;Document.prototype.createElement=function(t){if(String(t).toLowerCase()==='link'&&!window.__done){window.__done=1;throw new Error('test')}return window.__ce.apply(this,arguments)}")
            await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(3500)
            check('the block failing: the page loads and the font still arrives through @font-face (once)', sum(u.endswith(PL) for u in reqs) == 1 and await pg.evaluate("document.fonts.check(\"700 20px 'Playpen Sans Hebrew'\",'Word')") and not errs, [sum(u.endswith(PL) for u in reqs), errs[:2]])
            await c.close()
            # the violation record still works (its block is untouched)
            c, pg, reqs, warn, errs = await page(b, 'index.html#map')
            await pg.wait_for_selector('.map .isl')
            await pg.evaluate("(()=>{const i=new Image();i.src='https://example.org/x.png'})()"); await pg.wait_for_timeout(800)
            rec = await pg.evaluate("JSON.parse(localStorage.getItem('wi_csp')||'[]')")
            check('the CSP record still records a blocked request', any(r.get('o') == 'https://example.org' and r.get('d') == 'img-src' for r in rec), rec)
            await c.close()
            # the other pages: nothing added
            for url, want in (('run.html', [[PL, 'font', 'font/woff2', '']]), ('trainer.html', []), ('worksheet.html', []), ('world.html', [])):
                c, pg, reqs, warn, errs = await page(b, url)
                await pg.wait_for_timeout(1200)
                L = [x for x in await pg.evaluate(LINKS) if 'latin' in x[0]]
                check(f'{url}: the Latin font links are as before ({len(want)}), none added', L == want, L)
                await c.close()
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
