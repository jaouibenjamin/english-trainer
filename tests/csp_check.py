#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""Content-Security-Policy: one policy on every page, and no page or switch breaks under it.

    python3 tests/csp_check.py              # the rules in the files, then every page and switch in the browser
    python3 tests/csp_check.py --shots DIR  # also save a PNG of each

In the files: each page has exactly one policy, the same everywhere; scripts only from this site (no 'unsafe-inline', no
'unsafe-eval'); the only inline script is run.html's import map, allowed by its hash; no inline event handler
(onclick=, onerror=...) in a page or in the HTML the scripts write; requests only to this site and the class's Apps
Script hosts. In the browser: every page, and the game under each switch (?ds, ?help, ?card, ?games, ?sheet, ?mock) and
on its screens, runs with no violation report and no console error. A self-test proves a violation is caught: an
inline script added to a page must not run and must be reported."""
import asyncio, base64, glob, hashlib, os, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, fails

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">')
CONNECT = ["'self'", 'https://script.google.com', 'https://script.googleusercontent.com', 'data:', 'blob:']
# a violation, in the page's own words: the listener writes it to window.__csp as well as to the console
LISTEN = "window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective+' '+e.blockedURI))"


def static():
    pages = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, '*.html')))
    pols = {}
    for p in pages:
        s = open(os.path.join(ROOT, p), encoding='utf-8').read()
        m = META.findall(s)
        check(f'{p}: exactly one Content-Security-Policy', len(m) == 1, len(m))
        if m:
            pols[p] = m[0]
            head = s[:s.index('<meta http-equiv="Content-Security-Policy"')]
            check(f'{p}: the policy comes before any script or style', '<script' not in head and '<link' not in head and '<style' not in head)
        for tag, body in re.findall(r'<script([^>]*)>(.*?)</script>', s, re.S):
            if 'src=' in tag:
                continue
            h = "'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
            check(f'{p}: an inline script is only an import map allowed by its hash', 'importmap' in tag and h in (m[0] if m else ''), tag)
        ev = re.findall(r'<[a-z][^>]*\son[a-z]+\s*=', s)
        check(f'{p}: no inline event handler', not ev, ev[:3])
    check('the same policy on every page', len(set(pols.values())) == 1, set(pols.values()))
    pol = next(iter(pols.values()), '')
    d = {x.split()[0]: x.split()[1:] for x in pol.split(';') if x.strip()}
    check("script-src: this site (and the import map's hash) only", d.get('script-src', [None])[0] == "'self'" and all(v.startswith("'sha256-") for v in d.get('script-src', [])[1:]), d.get('script-src'))
    check('nothing unsafe for scripts', 'unsafe' not in ' '.join(d.get('script-src', []) + d.get('default-src', [])))
    check('connect-src: this site and the class backend only (Supabase stays out until dual is on)', d.get('connect-src') == CONNECT, d.get('connect-src'))
    check("object-src 'none', base-uri 'none', form-action 'none'", d.get('object-src') == ["'none'"] and d.get('base-uri') == ["'none'"] and d.get('form-action') == ["'none'"])
    check("default-src 'self'", d.get('default-src') == ["'self'"])
    bad = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'js', '**', '*.js'), recursive=True)):
        for n, line in enumerate(open(f, encoding='utf-8'), 1):
            if re.search(r'<[a-z][^>]*\son(click|error|load|input|change|submit|key[a-z]+|mouse[a-z]+|pointer[a-z]+|touch[a-z]+|focus|blur)\s*=', line):
                bad.append(f'{os.path.relpath(f, ROOT)}:{n}')
    check('no inline event handler in the HTML the scripts write', not bad, bad[:5])


async def visit(b, url, ready, errs, tag, w=390, h=844, then=()):
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.add_init_script(LISTEN)
    await pg.goto(url); await pg.wait_for_selector(ready, timeout=30000); await pg.wait_for_timeout(700)
    for route, sel in then:
        await pg.evaluate(f"location.hash={route!r}")
        if sel.startswith('lv:'):
            await P.lv(pg, sel[3:])      # a level is up (tests/play.py)
        else:
            await pg.wait_for_selector(sel, timeout=15000)
        await pg.wait_for_timeout(500)
    v = await pg.evaluate('window.__csp')
    check(f'[{tag}] no Content-Security-Policy violation', not v, v[:4])
    await P.shot(pg, f'csp-{tag}')
    await c.close()


async def main():
    static()
    procs = P.start_servers(mock=False)      # its own servers on free ports (tests/play.py)
    errs = []
    B = f'http://127.0.0.1:{P.PORT}/'
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
            game = [('#map', '.map .isl'), ('#island/1', '.lvrow'), ('#play/1/sling', 'lv:sling'), ('#play/1/listen', 'lv:listen'),
                    ('#play/1/read', 'lv:read'), ('#play/1/bridge', 'lv:bridge'), ('#settings', '.scr.settings'), ('#help', '.scr.help'),
                    ('#collection', '.scr.coll'), ('#math', '#stage[data-scr=math]'), ('#mock', '#stage[data-scr=mock]')]
            await visit(b, B + 'index.html', '.title .btn', errs, 'game', then=game)
            await visit(b, B + 'index.html?ds=1', '.title .btn', errs, 'game-ds', then=game[:1] + [('#settings', '.scr.settings')])
            await visit(b, B + 'index.html?help=1&card=1&games=1&sheet=1', '.title .btn', errs, 'game-switches',
                        then=[('#island/1', '.xtb'), ('#extra/1/tf', '#tfk'), ('#extra/1/pairs', '.prk'), ('#extra/1/scramble', '.scl'),
                              ('#card', '#stage[data-scr=card]'), ('#settings', '.scr.settings'), ('#play/1/read', 'lv:read')])
            await visit(b, B + 'index.html', '.title .btn', errs, 'game-laptop', 1366, 768, then=game[:3])
            await visit(b, B + 'trainer.html', '#app', errs, 'trainer')
            await visit(b, B + 'worksheet.html?island=1', 'body', errs, 'worksheet')
            await visit(b, B + 'world.html', 'body', errs, 'world')
            await visit(b, B + 'ds.html', 'body', errs, 'ds')
            for q in ('', '?style=lowpoly'):
                c, pg = await new_page(b, 390, 844, errs=errs)
                await pg.add_init_script(LISTEN)
                await pg.goto(B + 'run.html' + q); await pg.wait_for_function('window.__heroLoaded!==undefined', timeout=60000); await pg.wait_for_timeout(800)
                v = await pg.evaluate('window.__csp')
                check(f'[run{q}] Beach Run starts under the policy (three.js, its models) with no violation', not v, v[:4])
                await P.shot(pg, f'csp-run{q.replace("?", "-").replace("=", "-")}')
                await c.close()
            # self-test: the policy is really there and a violation is really caught
            c, pg = await new_page(b, 390, 844, errs=[])
            await pg.add_init_script(LISTEN)
            await pg.goto(B + 'index.html'); await pg.wait_for_selector('.title .btn')
            await pg.evaluate("(()=>{const s=document.createElement('script');s.textContent='window.__inj=1';document.head.appendChild(s);const i=document.createElement('img');i.src='https://example.org/x.png';document.body.appendChild(i)})()")
            await pg.wait_for_timeout(300)
            r = await pg.evaluate("({inj:window.__inj,csp:window.__csp})")
            check('self-test: an inline script added to the page does not run, and is reported', r['inj'] is None and any(x.startswith('script-src') for x in r['csp']), r)
            check('self-test: a picture from another host is blocked and reported', any(x.startswith('img-src') for x in r['csp']), r)
            await c.close()
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors (a violation is one), or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
