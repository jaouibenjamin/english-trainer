#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""Two devices of one pupil each quit a different mock-exam paper: the questions seen on both are kept on the server.

    python3 tests/seen_sync.py

A quit adds the questions shown to x.seen and saves (js/mock.js). The backend keeps the whole record of the last save,
so device B's save replaces A's seen list on the server. When A opens the game again it joins the server's record with
its own (js/state.js merge) and must save the union back: sig() has to notice a change in x.seen alone, otherwise A
never saves and A's questions are lost for good. Against the mock backend (tests/mock.js); no save is forced by the
test, only the game's own save after a join is waited for."""
import asyncio, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, fails
from playwright.async_api import async_playwright

CLASS, PIN, NAME = 'EN-1234', '2468', 'בודק שני'   # the mock backend's test class and an obviously fake pupil


def post(api, d):
    with urllib.request.urlopen(urllib.request.Request(api, data=json.dumps(d).encode(), method='POST'), timeout=10) as r:
        return json.loads(r.read())


def server_seen(api):
    r = post(api, {'a': 'login', 'c': CLASS, 'n': NAME, 'p': PIN})
    return set(((r.get('s') or {}).get('x') or {}).get('seen') or [])


async def device(b, api, errs):
    """a device of the pupil, already signed in (the record on the device names the pupil, as after a sign-in)"""
    c, pg = await new_page(b, 390, 844, api=api, errs=errs)
    await pg.add_init_script(f"try{{if(!localStorage.getItem('aam-unit1-v1'))localStorage.setItem('aam-unit1-v1',JSON.stringify({{u:{{c:'{CLASS}',n:'{NAME}',p:'{PIN}'}}}}))}}catch(e){{}}")
    await pg.goto(P.BASE); await pg.wait_for_selector('.title .sb', timeout=20000)
    return c, pg


async def quit_paper(pg):
    """open a paper, look at two questions, quit with two presses of the real button; returns the keys of the two"""
    await pg.evaluate("location.hash='mockrun'"); await pg.wait_for_selector('.xstation')
    keys = []
    for n in range(2):
        for _ in range(100):
            if await pg.locator('.xstation [data-a=mocknext]').count():
                await pg.click('.xstation [data-a=mocknext]'); await pg.wait_for_timeout(250); continue
            if await pg.locator('.xq.label').count() and not await pg.locator('.xo:disabled, #xi[readonly]').count(): break
            await pg.wait_for_timeout(150)
        keys.append(await pg.evaluate("__lv.items[__lv.i()].k"))
        if n == 0:   # answer the first one (any answer), so the second is shown
            await pg.locator('.xo').first.click(); await pg.wait_for_timeout(1300)
    await pg.click('.xquit'); await pg.wait_for_timeout(300); await pg.click('.xquit')
    await pg.wait_for_function("location.hash==='#mock'")
    return keys


async def wait_server(api, want, secs=12):
    for _ in range(secs * 4):
        if want <= server_seen(api): return True
        await asyncio.sleep(.25)
    return False


async def main():
    procs = P.start_servers(mock=True)
    api = f'http://127.0.0.1:{P.API_PORT}/'
    errs = []
    try:
        r = post(api, {'a': 'register', 'c': CLASS, 'n': NAME, 'p': PIN})
        check('test setup: the pupil is on the mock backend', r.get('ok') or r.get('e') == 'taken', r)
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            ca, a = await device(b, api, errs)
            cb, bb = await device(b, api, errs)   # both devices are open before either quits
            ka = await quit_paper(a)
            check('device A: its quit is saved to the server', await wait_server(api, set(ka)), [ka, sorted(server_seen(api))])
            kb = await quit_paper(bb)
            check('device B: its quit is saved too, and B did not know A\'s questions', await wait_server(api, set(kb)) and not set(ka) <= set(await bb.evaluate("__game.S().x.seen")), [kb, sorted(server_seen(api))])
            lost = set(ka) - server_seen(api)
            check('test setup: B\'s save replaced the record on the server, so A\'s questions are missing there for now', bool(lost), sorted(server_seen(api)))
            # A comes back to the game: it joins the server's record with its own and must save the union by itself
            await a.reload(); await a.wait_for_selector('#view .scr', timeout=20000)
            both = set(ka) | set(kb)
            check('device A comes back: the game itself saves the questions of both devices (nothing is lost)', await wait_server(api, both), [sorted(both - server_seen(api))])
            check('device A has both on the device too', both <= set(await a.evaluate("__game.S().x.seen")))
            # and B, opened again, gets A's questions from the server: its next paper draws fresh ones
            await bb.reload(); await bb.wait_for_selector('#view .scr', timeout=20000); await bb.wait_for_timeout(1500)
            check('device B opened again has the questions of both devices', both <= set(await bb.evaluate("__game.S().x.seen")))
            await ca.close(); await cb.close(); await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors or failed requests', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
