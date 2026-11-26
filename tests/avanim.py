#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""Character animations (js/avanim.js, assets/al/avanim/): one 2 s animated WebP per character, played once on tap.

    python3 tests/avanim.py

Files: every character in js/world_data.js has one, it is an animated WebP under 150 KB, listed in
assets/al/sources.tsv with its sha256. In world.html?ds=1 (the picker): no animation file is requested before a tap;
a tap requests exactly that character's file and the still portrait comes back afterwards; with prefers-reduced-motion
or calm mode a tap requests nothing and the portrait stays still. Without the flag, world.html requests none."""
import asyncio, hashlib, os, re, socket, subprocess, sys, time
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
CAP = 150 * 1024
fails = []


def check(label, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + label + (' ' + str(extra) if extra else ''), flush=True)
    if not ok:
        fails.append(label)


NO_FILE = set()   # the waist-up set (#108): every character, the owl too, has its own sign-off animation


def files_check():
    art = open(os.path.join(ROOT, 'js', 'world_art.js'), encoding='utf-8').read()
    data = open(os.path.join(ROOT, 'js', 'world_data.js'), encoding='utf-8').read()
    ids = re.findall(r"\{id:'([a-z-]+)'", data)
    anim = dict(re.findall(r"'avanim/([a-z-]+)':'([^']+)'", art))
    want = set(ids) - NO_FILE
    check(f'every one of the {len(ids)} characters but {sorted(NO_FILE)} has an animation file, and no other', len(ids) == 30 and set(anim) == want, sorted(want ^ set(anim)))
    rows = {}
    for ln in open(os.path.join(ROOT, 'assets', 'al', 'sources.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) > 5 and c[0] == 'al-avanim':
            rows['assets/' + c[1]] = c
    bad = []
    for i, f in anim.items():
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            bad.append((i, 'missing')); continue
        b = open(p, 'rb').read()
        if not (b[:4] == b'RIFF' and b[8:12] == b'WEBP' and b'ANIM' in b[:200]):
            bad.append((i, 'not an animated webp'))
        if len(b) >= CAP:
            bad.append((i, f'{len(b) // 1024} KB'))
        r = rows.get(f)
        if not r or r[5] != hashlib.sha256(b).hexdigest() or r[3] not in f:
            bad.append((i, 'sources.tsv row or sha256'))
    check('each is an animated WebP under 150 KB, listed in sources.tsv with its job id and sha256', not bad, bad[:5])
    return ids


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


async def run(ids):
    port = free_port()
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(('127.0.0.1', port), .2).close(); break
            except OSError:
                time.sleep(.1)
        base = f'http://127.0.0.1:{port}/world.html'
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=CHROME)

            async def page(motion='no-preference'):
                ctx = await b.new_context(viewport={'width': 390, 'height': 844}, reduced_motion=motion)
                pg = await ctx.new_page(); seen = []; errs = []
                pg.on('request', lambda r: seen.append(r.url) if '/avanim/' in r.url else None)
                pg.on('pageerror', lambda e: errs.append(str(e)))
                return ctx, pg, seen, errs

            # flag off: the gate, nothing requested
            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?screen=picker'); await pg.wait_for_timeout(800)
            check('flag off: world.html requests no animation file', not seen, seen[:2])
            await ctx.close()

            # flag on: nothing before a tap; a tap plays that character once, then the still portrait is back
            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?ds=1&screen=picker'); await pg.wait_for_selector('#avgrid .wi-av'); await pg.wait_for_timeout(800)
            check('flag on: no animation file is requested before a tap', not seen, seen[:2])
            first = await pg.evaluate("[...document.querySelectorAll('#avgrid .wi-av')].findIndex((b,i)=>!b.classList.contains('wi-av--locked')&&i!==%d)" % ids.index('owl'))
            await pg.locator('#avgrid .wi-av').nth(first).click(); await pg.wait_for_timeout(400)
            want = ids[first]
            src = await pg.evaluate("document.querySelector('#avgrid [aria-pressed=true] .wi-av__art').getAttribute('src')")
            check('a tap requests exactly that character\'s animation and shows it', len(seen) == 1 and f'/avanim/{want}.' in seen[0] and '/avanim/' in src, [seen, src])
            await pg.wait_for_timeout(2600)
            src = await pg.evaluate("document.querySelector('#avgrid [aria-pressed=true] .wi-av__art').getAttribute('src')")
            check('after it has played, the still portrait is back', f'/av/{want}.' in src and '/avanim/' not in src, src)
            # the owl now has its own animation (it had the CSS bob before the waist-up set)
            n0 = len(seen)
            got = await pg.evaluate("""async()=>{const img=document.querySelectorAll('#avgrid .wi-av__art')[%d];const m=await import('./js/avanim.js');
              const r=m.playAv(img,'owl');await new Promise(z=>setTimeout(z,300));return [r,img.getAttribute('src'),img.classList.contains('wi-av__art--bob')]}""" % ids.index('owl'))
            check('the owl: its own animation file is requested and shown (no CSS bob)', got[0] and '/avanim/owl.' in got[1] and not got[2] and len(seen) == n0 + 1 and '/avanim/owl.' in seen[-1], [got, seen[n0:]])
            check('no page errors', not errs, errs[:2])
            await ctx.close()

            # reduced motion: a tap requests nothing, the portrait stays
            ctx, pg, seen, errs = await page('reduce')
            await pg.goto(base + '?ds=1&screen=picker'); await pg.wait_for_selector('#avgrid .wi-av'); await pg.wait_for_timeout(600)
            await pg.locator('#avgrid .wi-av').nth(first).click(); await pg.wait_for_timeout(600)
            check('prefers-reduced-motion: a tap requests no animation and nothing moves', not seen, seen[:2])
            await ctx.close()

            # calm mode: the same
            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?ds=1&screen=picker'); await pg.wait_for_selector('#avgrid .wi-av'); await pg.wait_for_timeout(600)
            await pg.evaluate("document.documentElement.classList.add('calm')")
            await pg.locator('#avgrid .wi-av').nth(first).click(); await pg.wait_for_timeout(600)
            check('calm mode: a tap requests no animation and nothing moves', not seen, seen[:2])
            await ctx.close()
            await b.close()
    finally:
        srv.terminate()


ids = files_check()
asyncio.run(run(ids))
print(f'{len(fails)} FAILED: ' + '; '.join(fails) if fails else 'ALL PASSED')
sys.exit(1 if fails else 0)
