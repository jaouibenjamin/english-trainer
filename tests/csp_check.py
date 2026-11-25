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
inline script added to a page must not run and must be reported.

Also: the two developer tools (tools/*.html) carry policies of their own; when config.js names a BACKEND url, its
origin must be in every page's connect-src (else dual mode's copies would be refused and only logged); the class's
Apps Script path (a POST answered by a redirect to a second host) is replayed against two local stand-ins, with and
without the second host in the policy; and js/csplog.js keeps the last 10 violations as directive and origin only."""
import asyncio, base64, glob, hashlib, http.server, json, os, re, sys, threading
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, fails

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">')
CONNECT = ["'self'", 'https://script.google.com', 'https://script.googleusercontent.com', 'blob:']
GOOGLE = ('https://script.google.com', 'https://script.googleusercontent.com')
sha = lambda body: "'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
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
            h = sha(body)
            check(f'{p}: an inline script is only an import map allowed by its hash (its hash now: {h})', 'importmap' in tag and h in (m[0] if m else ''), tag)
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
            if re.search(r'<[a-z][^>]*\son[a-z]+\s*=', line):
                bad.append(f'{os.path.relpath(f, ROOT)}:{n}')
    check('no inline event handler in the HTML the scripts write', not bad, bad[:5])
    check('every page loads js/csplog.js right after its policy', all(re.search(r'<meta http-equiv="Content-Security-Policy" content="[^"]+">\n<script src="js/csplog.js"></script>', open(os.path.join(ROOT, p), encoding='utf-8').read()) for p in pages))
    # the developer tools: a policy of their own, before their one inline script, which it allows by its hash
    for t in sorted(glob.glob(os.path.join(ROOT, 'tools', '*.html'))):
        s = open(t, encoding='utf-8').read(); n = os.path.relpath(t, ROOT); m = META.findall(s)
        bodies = [b for tag, b in re.findall(r'<script([^>]*)>(.*?)</script>', s, re.S) if 'src=' not in tag]
        ok = len(m) == 1 and s.index('<meta http-equiv') < s.find('<script') and all(sha(x) in m[0] for x in bodies) and 'unsafe' not in m[0].split('script-src')[1].split(';')[0] and "object-src 'none'" in m[0] and "base-uri 'none'" in m[0]
        check(f'{n}: a policy of its own, its inline script allowed only by its hash', ok, [sha(x) for x in bodies])
    # dual mode: the Supabase project must be allowed on every page, or its copies would be refused
    cfg = open(os.path.join(ROOT, 'config.js'), encoding='utf-8').read()
    check('config.js: a BACKEND url, if any, is in every page\'s connect-src', backend_allowed(cfg, pols) is None, backend_allowed(cfg, pols))
    fake = {'index.html': "default-src 'self'; connect-src 'self' https://script.google.com"}
    check('self-test: a BACKEND url missing from the policy is caught', backend_allowed("window.BACKEND={mode:'dual',url:'https://abcd.supabase.co',key:'k'};", fake) == ['index.html'])
    check('self-test: a BACKEND url in the policy passes', backend_allowed("window.BACKEND = {mode:'dual', url:'https://abcd.supabase.co'}", {'index.html': "connect-src 'self' https://abcd.supabase.co"}) is None)


def backend_allowed(cfg, pols):
    """None when config.js names no BACKEND url, or names one whose origin every page's connect-src lists; else the
    pages that miss it"""
    code = re.sub(r'(?m)^\s*//[^\n]*', '', re.sub(r'/\*.*?\*/', '', cfg, flags=re.S))      # comments out; an https:// inside a string stays
    m = re.search(r'BACKEND\s*=\s*\{[^}]*\burl\s*:\s*[\'"]([^\'"]+)[\'"]', code)
    if not m:
        return None
    u = re.match(r'(https?://[^/]+)', m.group(1))
    origin = u.group(1) if u else m.group(1)
    miss = [p for p, pol in pols.items() if origin not in next((x.split()[1:] for x in pol.split(';') if x.split()[:1] == ['connect-src']), [])]
    return miss or None


def standins():
    """the class's Apps Script path, on this machine: A answers a POST with a 302 to B (another origin), B answers the
    JSON; both send the CORS header the real ones send. A third server serves a page with the real policy, the two
    Google hosts swapped for A and B (or B left out), and a script that makes the game's call."""
    def serve(handler):
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler); threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv
    class Quiet(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def send(self, code, body=b'', ctype='application/json', extra=()):
            self.send_response(code); self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Content-Type', ctype)
            for k, v in extra: self.send_header(k, v)
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    b_srv = serve(type('B', (Quiet,), {'do_GET': lambda self: self.send(200, b'{"ok":true,"via":"echo"}')}))
    bo = f'http://127.0.0.1:{b_srv.server_port}'
    def a_post(self):
        self.rfile.read(int(self.headers.get('Content-Length') or 0)); self.send(302, extra=(('Location', bo + '/macros/echo?user_content_key=x'),))
    a_srv = serve(type('A', (Quiet,), {'do_POST': a_post}))
    ao = f'http://127.0.0.1:{a_srv.server_port}'
    pol = META.findall(open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read())[0]
    page_pol = {'/ok': pol.replace(GOOGLE[1], bo).replace(GOOGLE[0], ao), '/neg': pol.replace(' ' + GOOGLE[1], '').replace(GOOGLE[0], ao)}
    probe = ("fetch(%s,{method:'POST',body:JSON.stringify({a:'board'})}).then(r=>r.json()).then(j=>{window.__r=j&&j.ok?'ok':'bad'})"
             ".catch(e=>{window.__r='refused'})" % json.dumps(ao + '/macros/s/x/exec')).encode()
    def c_get(self):
        if self.path == '/probe.js':
            return self.send(200, probe, 'text/javascript')
        if self.path in page_pol:
            return self.send(200, ('<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="%s"><script src="/probe.js"></script>' % page_pol[self.path]).encode(), 'text/html')
        self.send(404, b'')
    c_srv = serve(type('C', (Quiet,), {'do_GET': c_get}))
    return f'http://127.0.0.1:{c_srv.server_port}', (a_srv, b_srv, c_srv)


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
    check(f'[{tag}] and nothing in the device\'s own log of them (js/csplog.js)', await pg.evaluate("localStorage.getItem('wi_csp')") is None)
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
            # every switch together with the new look (docs/LESSONS.md 8: switches fine alone can break together)
            await visit(b, B + 'index.html?ds=1&help=1&card=1&games=1&sheet=1&tmock=1', '.title .btn', errs, 'game-all-switches',
                        then=[('#map', '.map .isl'), ('#island/1', '.xtb'), ('#extra/1/tf', '#tfk'), ('#settings', '.scr.settings'), ('#card', '#stage[data-scr=card]'), ('#play/1/read', 'lv:read')])
            await visit(b, B + 'trainer.html', '#app', errs, 'trainer')
            await visit(b, B + 'worksheet.html?island=1', 'body', errs, 'worksheet')
            await visit(b, B + 'world.html', 'body', errs, 'world')
            await visit(b, B + 'ds.html', 'body', errs, 'ds')
            for q in ('', '?style=lowpoly', '?ds=1'):      # ?ds=1: Beach Run in the new look (css/run-ds.css)
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
            log = json.loads(await pg.evaluate("localStorage.getItem('wi_csp')") or '[]')
            check('the device log keeps directive and origin only: no path, no query', {'d': 'img-src', 'o': 'https://example.org'} in log and any(x['o'] == 'inline' for x in log) and all(set(x) == {'d', 'o'} for x in log) and '/x.png' not in json.dumps(log), log)
            await pg.evaluate("(()=>{for(let i=0;i<12;i++){const m=document.createElement('img');m.src='https://e'+i+'.example.org/p?q=1';document.body.appendChild(m)}})()")
            await pg.wait_for_timeout(400)
            log = json.loads(await pg.evaluate("localStorage.getItem('wi_csp')") or '[]')
            check('the device log keeps the last 10 only, and never a query', len(log) == 10 and 'q=1' not in json.dumps(log), len(log))
            await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.scr.settings .csp')
            t = await pg.inner_text('.scr.settings .csp')
            check('the settings screen shows the log in a plain line', 'חסימות אבטחה' in t and 'img-src https://e11.example.org' in t, t[:120])
            await c.close()
            # the developer tools still work under their own policies (a context of its own: cors.html asks another host, on purpose)
            c = await b.new_context(); pg = await c.new_page(); await pg.add_init_script(LISTEN)
            await pg.route('https://tool.example.org/**', lambda r: r.fulfill(status=200, body='x', headers={'Access-Control-Allow-Origin': '*'}))
            await pg.goto(B + 'tools/sheet.html?part=0'); await pg.wait_for_timeout(1500)
            r = await pg.evaluate("({w:document.getElementById('c').width,csp:window.__csp})")
            check('tools/sheet.html draws its sheet under its policy, with no violation', r['w'] > 0 and not r['csp'], r)
            await pg.goto(B + 'tools/cors.html?u=https://tool.example.org/a.png'); await pg.wait_for_function("document.getElementById('o').textContent!=='checking…'", timeout=10000)
            r = await pg.evaluate("({t:document.getElementById('o').textContent,csp:window.__csp})")
            check('tools/cors.html makes its https request under its policy, with no violation', r['t'].startswith('OK 200') and not r['csp'], r)
            await c.close()
            # the class's Apps Script path, replayed: a POST, a 302 to a second host, the JSON from there
            base, srvs = standins()
            for path, want in (('/ok', 'ok'), ('/neg', 'refused')):
                c = await b.new_context(); pg = await c.new_page()
                await pg.goto(base + path); await pg.wait_for_function('window.__r!==undefined', timeout=10000)
                got = await pg.evaluate('window.__r')
                check(f'two-hop stand-in {path}: ' + ('the call through the redirect succeeds under the real policy' if want == 'ok' else 'without the second host the redirected call is refused'), got == want, got)
                await c.close()
            for s_ in srvs: s_.shutdown()
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors (a violation is one), or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
