#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The live look's warm-up (js/main.js warmIslands): after the first screen, the levels' sprites (CORE) are fetched
ahead, then the six island pictures. It must:
  - start by itself, without any level being opened (a warm-up that never starts would pass every other suite: the
    level just fetches its sprites when it opens);
  - fetch the island pictures only after the levels' sprites;
  - while a level is open, not fetch the island pictures (they would compete with the level's own sprites and voice
    on a slow line), and fetch them once the child has left the level;
  - ask for a level's background with high priority, ahead of anything fetched for later;
  - not run at all with the new look (?ds=1), which fetches only its own art.
Checked by order of requests, not by timing.
    python3 tests/warmup.py"""
import asyncio, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
import play as P
from play import check, new_page, fails

CORE_PROBE = '/assets/sp/plank_0.webp'     # a CORE sprite no first screen shows
ISL_PROBE = '/assets/sp/isl_2.webp'        # an island picture (title and settings screens show none)


async def page(b, path, hold=None, hold_for=None):
    """open `path`, logging every request (time, url, priority); optionally hold the requests matching `hold`"""
    c, pg = await new_page(b, 390, 844, errs=[])
    log, t0 = [], time.monotonic()
    cdp = await c.new_cdp_session(pg); await cdp.send('Network.enable')
    cdp.on('Network.requestWillBeSent', lambda e: log.append((time.monotonic() - t0, e['request']['url'], e['request'].get('initialPriority'))))
    if hold:
        async def h(route):
            await asyncio.sleep(hold_for); await route.continue_()
        await pg.route(hold, h)
    await pg.goto(P.BASE + path, wait_until='commit')
    return c, pg, log, t0


def first(log, part):
    return next((t for t, u, _ in log if part in u), None)


async def wait_for(log, part, s):
    end = time.monotonic() + s
    while time.monotonic() < end and first(log, part) is None:
        await asyncio.sleep(0.1)
    return first(log, part)


async def main():
    procs = P.start_servers(mock=False)
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])

            # by itself, after the title: sprites first, island pictures only once they are in (one sprite held 2 s)
            c, pg, log, t0 = await page(b, '#', hold='**' + CORE_PROBE, hold_for=2)
            await pg.wait_for_selector('.title .btn', timeout=30000); drawn = time.monotonic() - t0
            k = await wait_for(log, CORE_PROBE, 10); i = await wait_for(log, ISL_PROBE, 10)
            check('the warm-up starts by itself after the title screen (no level opened)', k is not None and k - drawn < 3, round(k - drawn, 2) if k else None)
            check('the island pictures are fetched only once the levels\' sprites are in (a sprite held 2 s holds them)', k is not None and i is not None and i - k >= 1.5, (k, i))
            await c.close()

            c, pg, log, t0 = await page(b, '#map')
            await pg.wait_for_selector('.map .isl', timeout=30000); drawn = time.monotonic() - t0
            k = await wait_for(log, CORE_PROBE, 10)
            check('the warm-up starts by itself after the map', k is not None and k - drawn < 3, round(k - drawn, 2) if k else None)
            await c.close()

            # a level opened while the sprites still load (one held 3 s): no island picture while it is open; after leaving, yes
            c, pg, log, t0 = await page(b, '#play/1/listen', hold='**' + CORE_PROBE, hold_for=3)
            await pg.wait_for_function("window.__lv&&window.__lv.kind==='listen'", timeout=30000)
            await pg.wait_for_timeout(3000)
            check('while a level is open, the island pictures are not fetched', first(log, ISL_PROBE) is None, first(log, ISL_PROBE))
            pri = [p for _, u, p in log if u.endswith('/assets/bg/listen.jpg')]
            check('the level\'s background is asked for with high priority', bool(pri) and pri[0] in ('High', 'VeryHigh'), pri)
            await pg.evaluate("location.hash='settings'")
            i = await wait_for(log, ISL_PROBE, 10)
            check('once the child has left the level, the island pictures are fetched', i is not None, i)
            await c.close()

            # the new look fetches none of the old warm-up
            c, pg, log, t0 = await page(b, '?ds=1#map')
            await pg.wait_for_selector('.map', timeout=30000)
            k = await wait_for(log, CORE_PROBE, 8)
            check('with the new look (?ds=1) there is no old warm-up', k is None, k)
            await c.close()
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
