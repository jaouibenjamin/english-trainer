#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The trial of the new backend as config.js sets it up: default visitors stay on the Sheet; only a device opened with
?new=1 reaches the class's Supabase project.

    python3 tests/trial_config.py

config.js names the project with mode 'supabase' and no everyone key, and leaves the publishable key empty until the
lead pastes it. Checked in Chrome with the page's own Content-Security-Policy (not bypassed), every request to the
project's address answered by the stand-in (tests/sb_standin.py), so nothing ever reaches the real project:
  - config.js as committed (no key): no device uses the project, ?new=1 included; not one request goes to it;
  - config.js with a key (a made-up one, as the lead will paste the real one):
      - a default visitor: the Sheet's game, no request to the project, nothing stored for the trial;
      - ?new=1: the device is in the trial (the sign-in screens of the new backend), and remembers it; signing in
        reaches the project, and only the project's address (the policy lets it through);
      - ?new=0: the device leaves the trial and is on the Sheet again;
  - no other config value switches anyone: the line is exactly mode, url and key (no everyone)."""
import asyncio, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, fails
from sb_standin import Project
from playwright.async_api import async_playwright

PROJECT = 'https://ibmhoqgpdbyfwrsnwqoy.supabase.co'
PAGE = f'http://127.0.0.1:{P.PORT}/index.html'
CFG = open(os.path.join(P.ROOT, 'config.js'), encoding='utf-8').read()
TEST_KEY = 'made-up-key-for-the-trial-test-0123456789'   # not shaped like a vendor's key (LESSONS 15): the lead pastes the real one, once


async def device(b, cfg, prj, query=''):
    """a page of the game with this config.js; every request to the project's address goes to the stand-in"""
    c = await b.new_context(viewport={'width': 390, 'height': 844})
    hits = []

    async def project(r):
        hits.append(r.request.url.replace(PROJECT, ''))
        await prj.route(r)
    # the later route wins in Playwright: any other project is refused (and noted), then the class's goes to the stand-in
    await c.route(re.compile(r'https://[a-z0-9-]+\.supabase\.co/.*'), lambda r: (hits.append('OTHER ' + r.request.url), r.abort()))
    await c.route(PROJECT + '/**', project)
    await c.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body=cfg))
    await c.route('https://script.google.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{"ok":false,"e":"pin"}'))
    pg = await c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'Content Security Policy' in m.text else None)
    await pg.goto(PAGE + query + '#map'); await pg.wait_for_selector('.scr, .si'); await pg.wait_for_timeout(800)
    return c, pg, hits, errs


mode = lambda pg: pg.evaluate("import('./js/api.js').then(m=>m.MODE)")


async def main():
    line = [ln for ln in CFG.split('\n') if ln.startswith('window.BACKEND')]
    check('config.js names the project for a trial: mode supabase, its address, a key, and no everyone key',
          len(line) == 1 and re.fullmatch(r"window\.BACKEND = \{mode: 'supabase', url: '" + re.escape(PROJECT) + r"', key: '[A-Za-z0-9_-]*'\};(\s*// gitleaks:allow \([^\n]*\))?", line[0]) is not None, line)
    keyed = re.sub(r"key: '[A-Za-z0-9_-]*'", "key: '" + TEST_KEY + "'", CFG)
    procs = P.start_servers()
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])

            # config.js as committed: no key yet (or the lead's key, once pasted: then this is the keyed case below)
            if "key: ''" in CFG:
                for q in ('', '?new=1'):
                    c, pg, hits, errs = await device(b, CFG, Project(), q)
                    check(f"config.js as committed (no key), {q or 'a default visitor'}: the Sheet, not one request to the project", await mode(pg) == 'sheet' and not hits, hits)
                    await c.close()

            # with a key: a default visitor
            prj = Project()
            c, pg, hits, errs = await device(b, keyed, prj)
            st = await pg.evaluate("JSON.stringify(Object.keys(localStorage))")
            check('with the key, a default visitor: the Sheet\'s game, no request to the project, nothing stored for the trial',
                  await mode(pg) == 'sheet' and not hits and 'wi_new' not in st and 'wi-sb' not in st and await pg.locator('.si').count() == 0, [hits, st])
            await c.close()

            # with a key: ?new=1, then the same device without it, then ?new=0
            prj = Project()
            c, pg, hits, errs = await device(b, keyed, prj, '?new=1')
            check('?new=1: the device is in the trial (the new sign-in screens), and remembers it', await mode(pg) == 'supabase' and await pg.locator('.si').count() == 1 and await pg.evaluate("localStorage.getItem('wi_new')") == '1')
            r = await pg.evaluate("import('./js/state.js').then(m=>m.enter('login',{c:'EN-0000',n:'Testa',code:'4827'}))")
            check('signing in reaches the project (through its own address, allowed by the page\'s policy)', r == {'ok': True} and '/functions/v1/pupil-login' in hits and not [h for h in hits if h.startswith('OTHER')], [r, hits])
            check('no request was refused by the Content-Security-Policy', not errs, errs[:3])
            await pg.close()
            pg = await c.new_page(); await pg.goto(PAGE + '#map'); await pg.wait_for_selector('.scr, .si'); await pg.wait_for_timeout(500)
            check('the same device without ?new=1: still in the trial', await mode(pg) == 'supabase')
            await pg.close()
            n0 = len(hits)
            pg = await c.new_page(); await pg.goto(PAGE + '?new=0#map'); await pg.wait_for_selector('.scr, .si'); await pg.wait_for_timeout(800)
            check('?new=0: the device leaves the trial, is on the Sheet again, and its session is ended', await mode(pg) == 'sheet' and await pg.evaluate("localStorage.getItem('wi_new')") is None and any(h.startswith('/auth/v1/logout') for h in hits[n0:]), hits[n0:])
            await c.close()
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
