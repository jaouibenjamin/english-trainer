#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The welcome film (js/intro.js, css/ds-intro.css, assets/al/intro/), behind the design flag.

    python3 tests/intro.py

Flag off: index.html requests none of it. Flag on, first open (forced with ?intro=1, since an automated browser does not
get it otherwise): the poster with "watch" and "skip" (both 48 px or more), the film is not requested before a tap and
nothing plays by itself; a tap requests the film and plays it with sound, the narration's captions show as live text;
"skip" closes it and stores wi_intro=1, and the next open shows nothing and requests nothing; Escape closes it too.
No page error and no Content-Security-Policy violation. The film is H.264 + mono AAC, under 2.2 MB, listed with its sha256."""
import asyncio, hashlib, os, re, socket, subprocess, sys, time, json
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
fails = []


def check(label, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + label + (' ' + str(extra) if extra else ''), flush=True)
    if not ok:
        fails.append(label)


def files_check():
    js = open(os.path.join(ROOT, 'js', 'intro.js'), encoding='utf-8').read()
    film = re.search(r"FILM='([^']+)'", js).group(1); poster = re.search(r"POSTER='([^']+)'", js).group(1)
    rows = {}
    for ln in open(os.path.join(ROOT, 'assets', 'al', 'sources.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) > 5:
            rows['assets/' + c[1]] = c
    ok = True; info = {}
    for f in (film, poster):
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or rows.get(f, [None] * 6)[5] != hashlib.sha256(open(p, 'rb').read()).hexdigest():
            ok = False; info[f] = 'missing or not listed with its sha256'
    check('the film and its poster exist and are listed in sources.tsv with their sha256', ok, info)
    size = os.path.getsize(os.path.join(ROOT, film))
    try:
        pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,channels,width:format=duration', '-of', 'json', os.path.join(ROOT, film)], capture_output=True, text=True).stdout)
        st = {s['codec_name']: s for s in pr['streams']}
        fmt_ok = 'h264' in st and st.get('aac', {}).get('channels') == 1 and st['h264'].get('width', 0) <= 400 and float(pr['format']['duration']) <= 31
    except Exception as e:
        fmt_ok = False; st = str(e)
    check('the film is H.264 at most 400 px wide with mono AAC, at most 31 s and under 2.2 MB', fmt_ok and size < 2.2 * 1024 * 1024, [size, list(st)])
    return film


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


async def run(film):
    port = free_port()
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(('127.0.0.1', port), .2).close(); break
            except OSError:
                time.sleep(.1)
        base = f'http://127.0.0.1:{port}/index.html'
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=CHROME, args=['--autoplay-policy=no-user-gesture-required'])

            async def page():
                ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True)
                await ctx.route('**/*', lambda r: r.abort() if not r.request.url.startswith(f'http://127.0.0.1:{port}/') else (r.fulfill(body="window.API_URL='';", content_type='text/javascript') if r.request.url.split('?')[0].endswith('/config.js') else r.continue_()))
                pg = await ctx.new_page(); seen = []; errs = []
                pg.on('request', lambda r: seen.append(r.url) if re.search(r'intro', r.url) else None)
                pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.on('console', lambda m: errs.append(m.text) if 'Content Security Policy' in m.text else None)
                return ctx, pg, seen, errs

            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?intro=1'); await pg.wait_for_timeout(900)
            check('flag off: nothing of the film is requested, no overlay', not [u for u in seen if '/js/intro.js' in u or 'ds-intro' in u or '/al/intro/' in u] and await pg.locator('#wi-intro').count() == 0, seen[:3])
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro', timeout=5000); await pg.wait_for_timeout(600)
            sz = await pg.evaluate("[...document.querySelectorAll('#wi-intro button')].filter(b=>!b.hidden).map(b=>{const r=b.getBoundingClientRect();return [b.textContent,Math.round(r.width),Math.round(r.height)]})")
            check('first open: the poster with "watch" and "skip", both 48 px or more', len(sz) == 2 and all(w >= 48 and h >= 48 for _, w, h in sz), sz)
            st = await pg.evaluate("(()=>{const v=document.querySelector('#wi-intro video');return {paused:v.paused,src:v.currentSrc||v.getAttribute('src')||'',poster:v.poster}})()")
            check('nothing plays by itself and the film is not requested before a tap', st['paused'] and not st['src'] and not [u for u in seen if '.mp4' in u] and '/al/intro/poster' in st['poster'], [st, seen])
            await pg.locator('#wi-intro .wi-intro__play').tap(); await pg.wait_for_timeout(1800)
            st = await pg.evaluate("(()=>{const v=document.querySelector('#wi-intro video');const c=document.querySelector('#wi-intro .wi-intro__cap');return {t:v.currentTime,muted:v.muted,cap:c.hidden?'':c.textContent}})()")
            check('a tap requests the film and plays it with sound', [u for u in seen if '.mp4' in u] and st['t'] > 0.5 and not st['muted'], st)
            check('the narration shows as a live caption', st['cap'].startswith('בלילה'), st['cap'])
            await pg.locator('#wi-intro .wi-intro__skip').tap(); await pg.wait_for_timeout(300)
            gone = await pg.locator('#wi-intro').count() == 0
            stored = await pg.evaluate("localStorage.getItem('wi_intro')")
            check('"skip" closes it and this device remembers it', gone and stored == '1', [gone, stored])
            n0 = len(seen)
            await pg.goto(base + '?ds=1'); await pg.wait_for_timeout(900)
            check('the next open shows nothing and requests nothing of it', await pg.locator('#wi-intro').count() == 0 and len(seen) == n0, seen[n0:])
            check('no page error and no CSP violation', not errs, errs[:3])
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
            check('Escape closes it', await pg.locator('#wi-intro').count() == 0)
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?ds=1'); await pg.wait_for_timeout(900)
            check('an automated browser without ?intro=1 does not get it (so the other suites run as before)', await pg.locator('#wi-intro').count() == 0 and not seen, seen[:2])
            await ctx.close()
            await b.close()
    finally:
        srv.terminate()


film = files_check()
asyncio.run(run(film))
print(f'{len(fails)} FAILED: ' + '; '.join(fails) if fails else 'ALL PASSED')
sys.exit(1 if fails else 0)
