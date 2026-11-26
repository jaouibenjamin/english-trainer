"""How heavy each screen is on a slow network, with the new look (?ds=1) on and off.

The profile is a slow phone network on a fresh device (nothing in the browser's cache): 50 KB/s down and up, 400 ms
added to every request (Chrome's own network emulation). A pupil is already signed in (the mock backend's test class)
and opens the screen's address directly. For each screen it reports:
  - requests and bytes until the screen is usable, and in all once the network is quiet;
  - the ten largest files;
  - time to usable: the screen is drawn (its own selector, no loader), the fonts are in, and every picture on screen
    (img, background, border image) has arrived.
The test server gzips text files here (WI_GZIP=1, tests/static_server.py), as GitHub Pages does. It speaks HTTP/1.1
(6 connections at once) where GitHub Pages speaks HTTP/2, so with many small files the times here are on the slow side.

  python3 tests/slow_net.py                 # the table (markdown) for every screen, flag on and off
  python3 tests/slow_net.py --only map      # one screen
  python3 tests/slow_net.py --fast          # no throttling: requests and bytes only, in a few seconds

The suite's budget check imports measure() and PROFILE from here."""
import asyncio, json, os, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
os.environ['WI_GZIP'] = '1'   # the test server sends text gzip-compressed, as GitHub Pages does
import play as P

PROFILE = {'latency': 400, 'down': 50 * 1024, 'up': 50 * 1024}
CLASS = 'EN-1234'      # the mock backend's own test class (tests/mock.js)
USER = {'c': CLASS, 'n': 'נועה', 'p': '1357'}

# every picture on screen has arrived (img, background, border image), the fonts are in, and the screen's own ready test
USABLE = """(ready)=>{try{if(!ready())return false}catch(e){return false}
 if(document.querySelector('.loader'))return false;
 if(document.fonts&&document.fonts.status!=='loaded')return false;
 const done=new Set(performance.getEntriesByType('resource').filter(e=>e.responseEnd>0).map(e=>e.name)),W=innerWidth,H=innerHeight;
 const urls=v=>[...String(v||'').matchAll(/url\\("?([^")]+)"?\\)/g)].map(m=>new URL(m[1],location.href).href).filter(u=>!u.startsWith('data:'));
 for(const e of document.querySelectorAll('body *')){const r=e.getBoundingClientRect();if(r.bottom<0||r.right<0||r.top>H||r.left>W)continue;
  const cs=getComputedStyle(e);if(cs.visibility==='hidden'||cs.display==='none')continue;
  if(e.tagName==='IMG'&&!(e.complete&&e.naturalWidth))return false;   // a picture not loaded yet has no height: it counts all the same
  if(!r.width||!r.height)continue;
  for(const u of [...urls(cs.backgroundImage),...urls(cs.borderImageSource)])if(!done.has(u))return false}
 return true}"""

# the screens: address, the screen's own "drawn" test, whether it exists without the flag
SCREENS = [
    ('title', 'index.html#', "()=>!!document.querySelector('.scr.title .btn')", True, True),
    ('login', 'index.html#login', "()=>!!document.querySelector('#lc,.scr.login input')", True, False),
    ('map', 'index.html#map', "()=>!!document.querySelector('.scr.map .isl')", True, True),
    ('island path', 'index.html#island/1', "()=>!!document.querySelector('.scr.island .lvrow,.scr.island .w-path .w-st')", True, True),
    ('picker', 'index.html#avatar', "()=>!!document.querySelector('.wpick__grid')", False, True),
    ('level sling', 'index.html#play/1/sling', "()=>!!window.__lv", True, True),
    ('level listen', 'index.html#play/1/listen', "()=>!!window.__lv", True, True),
    ('level read', 'index.html#play/1/read', "()=>!!window.__lv", True, True),
    ('level bridge', 'index.html#play/1/bridge', "()=>!!window.__lv", True, True),
    ('Fraction Bay map', 'index.html#math', "()=>!!document.querySelector('.scr.mmap .isl,.scr.mmap')", True, True),
    ('mock hub', 'index.html#mock', "()=>!!document.querySelector('.scr.mockhub')", True, True),
    ('Beach Run menu', 'run.html', "()=>{const m=document.querySelector('#menu');return !!m&&getComputedStyle(m).visibility!=='hidden'&&!!m.querySelector('[data-go=run]')}", True, True),
]


def base_url():
    return f'http://127.0.0.1:{P.PORT}/'


async def measure(b, path, ready, ds, w=390, h=844, throttle=True, timeout=180, quiet=2.0, signed_in=True, laptop=False):
    """open one address on a fresh device and return what it loaded; see the module's docstring"""
    api = f'http://127.0.0.1:{P.API_PORT}/'
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1 if laptop else 2, has_touch=not laptop, locale='he-IL')
    pg = await c.new_page()
    await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body=f"window.API_URL='{api}';"))
    if signed_in:
        await pg.add_init_script("if(!sessionStorage.getItem('seeded')){sessionStorage.setItem('seeded','1');localStorage.setItem('aam-unit1-v1',%s)}" % json.dumps(json.dumps({'u': USER})))
    cdp = await c.new_cdp_session(pg)
    await cdp.send('Network.enable')
    await cdp.send('Network.setCacheDisabled', {'cacheDisabled': False})
    if throttle:
        await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': PROFILE['latency'], 'downloadThroughput': PROFILE['down'], 'uploadThroughput': PROFILE['up']})
    reqs, last = {}, [time.monotonic()]

    def sent(e):
        u = e['request']['url']
        if u.startswith(('data:', 'blob:')): return
        reqs[e['requestId']] = {'url': u, 'bytes': 0, 'done': False, 'at': time.monotonic()}; last[0] = time.monotonic()

    def fin(e):
        r = reqs.get(e['requestId'])
        if r: r['bytes'] = int(e.get('encodedDataLength', 0)); r['done'] = True; last[0] = time.monotonic()

    def fail(e):
        r = reqs.get(e['requestId'])
        if r: r['done'] = True; r['failed'] = True; last[0] = time.monotonic()
    cdp.on('Network.requestWillBeSent', sent); cdp.on('Network.loadingFinished', fin); cdp.on('Network.loadingFailed', fail)
    q = ('?ds=1' if ds else '')
    url = base_url() + (path.replace('#', q + '#', 1) if '#' in path else path + q)
    t0 = time.monotonic()
    await pg.goto(url, wait_until='commit')
    usable, at_usable = None, None
    while time.monotonic() - t0 < timeout:
        try:
            ok = await pg.evaluate(f"({USABLE})({ready})")
        except Exception:
            ok = False
        if ok:
            usable = time.monotonic() - t0
            at_usable = {k: dict(v) for k, v in reqs.items()}
            break
        await asyncio.sleep(0.2)
    # then everything the screen goes on to fetch by itself (preloads), until the network is quiet
    while time.monotonic() - t0 < timeout and (time.monotonic() - last[0] < quiet or any(not r['done'] for r in reqs.values())):
        await asyncio.sleep(0.2)
    await c.close()
    files = lambda d: sorted(({'file': urllib.parse.urlsplit(r['url']).path.lstrip('/') or r['url'], 'bytes': r['bytes']} for r in d.values()), key=lambda x: -x['bytes'])
    allf = files(reqs)
    uf = files(at_usable or reqs)
    return {'usable_s': round(usable, 1) if usable is not None else None,
            'requests_usable': len(uf), 'bytes_usable': sum(x['bytes'] for x in uf),
            'requests': len(allf), 'bytes': sum(x['bytes'] for x in allf), 'top': allf[:10], 'all': allf,
            'failed': [r['url'] for r in reqs.values() if r.get('failed')]}


def kb(n):
    return f'{n / 1024:,.0f} KB'


async def main():
    args = sys.argv[1:]
    fast = '--fast' in args
    only = args[args.index('--only') + 1] if '--only' in args else None
    out = args[args.index('--json') + 1] if '--json' in args else None
    procs = P.start_servers(mock=True)
    rows = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            sem = asyncio.Semaphore(4)   # Chrome throttles each page on its own, so four at a time do not share the 50 KB/s

            async def one(name, path, ready, off_ok, on_ok, ds):
                if not (on_ok if ds else off_ok): return None
                async with sem:
                    r = await measure(b, path, ready, ds, throttle=not fast, signed_in=name != 'login')
                    r.update(screen=name, ds=ds); print(f'{name:18} {"on " if ds else "off"} {r["usable_s"]}s {r["requests"]} req {kb(r["bytes"])}', file=sys.stderr, flush=True)
                    return r
            jobs = [one(n, p, rd, off, on, ds) for (n, p, rd, off, on) in SCREENS if not only or n == only for ds in (False, True)]
            rows = [r for r in await asyncio.gather(*jobs) if r]
            await b.close()
    finally:
        for p in procs: p.terminate()
    if out:
        json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=1)
    print('| Screen | Flag | Usable (s) | Requests to usable | Bytes to usable | Requests in all | Bytes in all |')
    print('|---|---|---|---|---|---|---|')
    for r in rows:
        print(f"| {r['screen']} | {'on' if r['ds'] else 'off'} | {r['usable_s'] if r['usable_s'] is not None else '>180'} | {r['requests_usable']} | {kb(r['bytes_usable'])} | {r['requests']} | {kb(r['bytes'])} |")
    print()
    for r in rows:
        print(f"**{r['screen']}, flag {'on' if r['ds'] else 'off'}**: " + ', '.join(f"{x['file'].split('/')[-1][:40]} {kb(x['bytes'])}" for x in r['top']))
        if r['failed']: print('  failed: ' + ', '.join(r['failed'][:5]))


if __name__ == '__main__':
    asyncio.run(main())
