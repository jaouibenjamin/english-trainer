#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The result screen sits over the island's own beach (BG(i.bg)); js/main.js play() fetches that picture while the
level is played, once the level's own voice clips are in, so the result card never stands on an empty background.
Checked in the page's own clock, by order, not by timing:
  - the island background was asked for while the level was still open (without the line in play() it is asked
    for only when the result screen sets it, after the level has closed: this check fails);
  - when it was asked for, no voice clip was still loading (the voice comes first on a slow line). Every clip is made
    to take 0.6 s, so asking at once, without waiting for the clips, fails this check.
For each level type of island 1, with and without the new look.
    python3 tests/result_bg.py"""
import asyncio, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
import play as P
from play import check, new_page, fails

# the last moment the level was still open (window.__lv is removed when the level ends, before the result screen sets
# its background), in performance.now() time
MARK = "setInterval(()=>{if(window.__lv)window.__open=performance.now()},5)"
ORDER = """(()=>{const E=performance.getEntriesByType('resource'),bg=E.find(e=>e.name.endsWith('/assets/bg/sling1.jpg'));
  const clips=E.filter(e=>e.initiatorType==='fetch'&&/\\.mp3(\\?|$)/.test(e.name));
  const busy=bg?clips.filter(c=>c.startTime<bg.startTime&&c.responseEnd>bg.startTime).map(c=>c.name.split('/').pop()):null;
  return {bg:bg?Math.round(bg.startTime):null,open:window.__open?Math.round(window.__open):null,clips:clips.length,busy}})()"""


async def main():
    procs = P.start_servers(mock=False)
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            for ds in (False, True):
                for kind in ('sling', 'listen', 'read', 'bridge'):
                    c, pg = await new_page(b, 390, 844, errs=[])
                    await pg.add_init_script(MARK)
                    async def slow(route):   # every clip takes 0.6 s, as on a slow line: the level's first clips are still loading when it opens
                        await asyncio.sleep(0.6); await route.continue_()
                    await pg.route(re.compile(r'\.mp3(\?|$)'), slow)
                    await pg.goto(P.BASE + ('?ds=1' if ds else '') + '#map'); await pg.wait_for_selector('.map .isl')
                    ok = await P.play_level(pg, 1, kind)
                    await pg.wait_for_selector('.result', timeout=60000)
                    o = await pg.evaluate(ORDER)
                    tag = f'[{"new look" if ds else "live look"}] {kind}'
                    check(f'{tag}: the island background was asked for while the level was still open', o['bg'] is not None and o['open'] is not None and o['bg'] < o['open'], o)
                    check(f'{tag}: when it was asked for, no voice clip was still loading', o['busy'] == [], o)
                    await c.close()
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
