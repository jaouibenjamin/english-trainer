"""Beach Run (run.html): start, play a whole run with the right and wrong answers, check scoring, and take screenshots.
   Also: the runner model is our own file and loads in both looks, Pitzi the crab runs when the model is missing, and
   nothing in the game's files points to another host (tests/remote_guard.py).
   python3 tests/run.py [--shots DIR]"""
import asyncio, os, subprocess, sys, time, socket
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remote_guard
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def free_port():
    """a port nobody listens on: the test always starts its own server on this checkout, never reuses one that is already running"""
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]
PORT = free_port()
BASE = f'http://127.0.0.1:{PORT}/run.html'
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
fails = []

def check(c, msg):
    print(('ok   ' if c else 'FAIL ') + msg)
    if not c: fails.append(msg)

def port_open(p):
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', p)) == 0

async def shot(pg, name):
    """A screenshot of the WebGL page takes long (seconds with software rendering), and the test runs the game six times
    faster: a gate could pass unanswered meanwhile and count as a second miss. So the game stands still while the picture
    is taken (the frame loop keeps drawing; only game time stops) and goes on at its speed afterwards."""
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        fast = await pg.evaluate('(()=>{const f=window.__runFast;window.__runFast=1e-9;return f===undefined?null:f})()')
        try:
            await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))
        finally:
            await pg.evaluate('f=>{if(f===null)delete window.__runFast;else window.__runFast=f}', fast)

def watch(pg, errs, missing_ok=''):
    """every page error, console error, failed request, HTTP error and request to another host is an error
    (missing_ok: a path that is made to fail on purpose)"""
    expected = lambda u: bool(missing_ok) and missing_ok in u
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and not (missing_ok and 'Failed to load resource' in m.text) else None)
    pg.on('request', lambda r: errs.append('request to another host: ' + r.url) if not r.url.startswith((f'http://127.0.0.1:{PORT}/', 'data:', 'blob:')) else None)
    pg.on('requestfailed', lambda r: errs.append(f'requestfailed: {r.url} ({r.failure})') if not expected(r.url) else None)
    pg.on('response', lambda r: errs.append(f'http {r.status}: {r.url}') if r.status >= 400 and not expected(r.url) else None)


async def looks(b):
    """the low-poly look loads its own model; without the model file Pitzi the crab runs and the game still works"""
    for name in ('__proto__', 'constructor', 'toString', 'nosuchlook'):
        errs = []
        c = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1, has_touch=True)
        pg = await c.new_page()
        watch(pg, errs)
        models = []
        pg.on('response', lambda r: models.append(r.url.split('/')[-1]) if '/assets/3d/' in r.url else None)
        await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
        await pg.goto(BASE + '?style=' + name)
        try:
            await pg.wait_for_selector('[data-go="run"]', timeout=15000)
            await pg.wait_for_function('window.__heroLoaded!==undefined', timeout=30000)
            ok = await pg.evaluate("document.documentElement.classList.contains('anime')&&!document.documentElement.classList.contains('lowpoly')") and models == ['hf_20261122_113604_02d63541-4d63-4dff-a4b5-8682f1cdf94e.glb']
        except Exception as e:
            ok = False; errs.append(str(e)[:120])
        real = [e for e in errs if 'WebGL' not in e and 'GPU stall' not in e]
        check(ok and not real, f'?style={name}: an unknown look falls back to the anime look, no error {models} {real[:2]}')
        await c.close()
    for tag, url, block in (('lowpoly', BASE + '?style=lowpoly', False), ('no model', BASE, True)):
        errs = []
        c = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True)
        pg = await c.new_page()
        watch(pg, errs, missing_ok='assets/3d/' if block else '')
        models = []
        pg.on('response', lambda r: models.append((r.status, r.url.split('/')[-1])) if '/assets/3d/' in r.url else None)
        await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
        if block:
            await pg.route('**/assets/3d/**', lambda r: r.fulfill(status=404, body='gone'))
        await pg.goto(url)
        await pg.wait_for_selector('[data-go="run"]', timeout=15000)
        await pg.wait_for_function('window.__heroLoaded!==undefined', timeout=30000)
        R = await pg.evaluate('__run.runner()'); loaded = await pg.evaluate('__heroLoaded')
        if block:
            check(loaded is False and R['crab'] and not R['hero'], f'{tag}: the model file is missing, so Pitzi the crab is the runner {R}')
        else:
            check(loaded is True and R['hero'] and not R['crab'] and models == [(200, 'hf_20261122_091919_b439053f-4747-4a22-8aa0-0a67974a1928.glb')] and await pg.evaluate("document.documentElement.classList.contains('lowpoly')"), f'{tag}: the low-poly look loads its own model {R} {models}')
        pic = await pg.evaluate("(async()=>{const i=document.querySelector('.crabhead.hero');await i.decode().catch(()=>{});return [i.getAttribute('src'),i.naturalWidth]})()")
        check(pic[0].startswith('assets/x/hf_') and pic[0].endswith('.webp') and pic[1] == 512, f'{tag}: the menu picture is our own file {pic}')
        await pg.click('[data-go="run"]'); await pg.wait_for_timeout(1500)
        check(await pg.is_visible('#hud') and await pg.evaluate('__run.G().on&&!__run.G().ended'), f'{tag}: the run starts')
        await shot(pg, f"r390x844_look_{tag.replace(' ', '_')}")
        real = [e for e in errs if 'WebGL' not in e and 'GPU stall' not in e]
        check(not real, f'{tag}: no page errors, failed requests or requests to another host {real[:3]}')
        await c.close()


async def play(b, w, h, tag):
    errs = []
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=w < 700)
    pg = await c.new_page()
    watch(pg, errs)
    await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
    await pg.goto(BASE)
    await pg.wait_for_selector('[data-go="run"]', timeout=15000)
    await pg.wait_for_function('window.__heroLoaded!==undefined', timeout=30000)
    R = await pg.evaluate('__run.runner()')
    check(await pg.evaluate('__heroLoaded') is True and R['hero'] and not R['crab'] and 'Run' in R['clip'], f'{tag}: the runner model loaded from our own files and its run animation plays {R}')
    await pg.wait_for_timeout(700)
    await shot(pg, f'{tag}_01_start')
    await pg.click('[data-pace="fast"]')
    check(await pg.evaluate('JSON.parse(localStorage.getItem("aam-unit1-v1")).r.pace') == 'fast', f'{tag}: pace choice is saved')
    await pg.click('[data-pace="mid"]')
    await pg.click('[data-go="run"]')
    await pg.wait_for_timeout(1200)
    check(await pg.is_visible('#hud'), f'{tag}: HUD visible after start')
    await pg.evaluate('window.__runFast=6; window.__run.noHit(true)')
    await pg.wait_for_timeout(1200)
    await shot(pg, f'{tag}_02_running')
    seen = 0; wrong_done = False; shot_gate = False; t0 = time.time()
    while time.time() - t0 < 240:
        st = await pg.evaluate('(()=>{const G=__run.G();return G?{ended:G.ended,gate:!!G.gate,z:G.gateObj?G.gateObj.position.z:null,asked:G.asked}:null})()')
        if st['ended']: break
        if st['gate'] and st['z'] is not None:
            if not shot_gate and st['z'] > -30:
                await shot(pg, f'{tag}_03_gate'); shot_gate = True
            if st['z'] > -12:
                lanes = await pg.evaluate('__run.lanes()'); a = await pg.evaluate('__run.answer()')
                if lanes:
                    if not wrong_done:
                        i = next(k for k, t in enumerate(lanes) if t != a and t is not None)
                        wrong_done = True
                    else:
                        i = lanes.index(a)
                    await pg.evaluate(f'__run.goLane({i})')
                    while True:
                        g = await pg.evaluate('!!__run.G().gate')
                        if not g: break
                        await pg.wait_for_timeout(40)
                    seen += 1
                    if seen == 1:
                        await pg.wait_for_timeout(250); await shot(pg, f'{tag}_04_wrong')
                    if seen == 2:
                        await pg.wait_for_timeout(250); await shot(pg, f'{tag}_05_right')
        await pg.wait_for_timeout(60)
    G = await pg.evaluate('(()=>{const G=__run.G();return {ended:G.ended,asked:G.asked,right:G.right,first:G.firstRight,total:G.total,missed:G.missed.length,pts:G.pts,shells:G.shells}})()')
    print('   ', G)
    check(G['ended'], f'{tag}: run reached the finish line')
    check(G['missed'] == 1, f'{tag}: the one wrong answer is listed')
    check(G['total'] == 13 and G['asked'] == 13, f'{tag}: the missed question came back once (13 gates)')
    check(G['first'] == 11 and G['right'] == 12, f'{tag}: 11 right first time, plus the retry')
    check(G['pts'] == 11 * 3 + 1, f'{tag}: points 3 per first-time answer, 1 for the retry')
    await pg.wait_for_selector('.miss li', timeout=5000)
    await pg.wait_for_timeout(600)
    await shot(pg, f'{tag}_06_end')
    st = await pg.evaluate('JSON.parse(localStorage.getItem("aam-unit1-v1"))')
    check(st and st.get('r', {}).get('runs') == 1 and st['r']['best'] == 11, f'{tag}: run saved on the device (runs, best)')
    check(st and st.get('pts', 0) >= 34, f'{tag}: points added to the shared record')
    # play again works
    await pg.click('[data-go="run"]'); await pg.wait_for_timeout(800)
    check(await pg.evaluate('!__run.G().ended && __run.G().asked===0'), f'{tag}: run again starts fresh')
    # controls
    await pg.evaluate('__run.G().lane=1')
    await pg.keyboard.press('ArrowLeft'); await pg.keyboard.press('ArrowLeft')
    check(await pg.evaluate('__run.G().lane') == 0, f'{tag}: arrow keys change lane and stop at the edge')
    await pg.evaluate('window.__runFast=1'); await pg.keyboard.press('Space'); await pg.wait_for_timeout(120)
    check(await pg.evaluate('__run.G().y') > 0, f'{tag}: space jumps')
    # dash: once a gate is up, ArrowDown makes it come fast
    await pg.evaluate('window.__runFast=4')
    await pg.wait_for_function('!!__run.G().gate', timeout=60000)
    check(await pg.is_visible('#dash'), f'{tag}: the dash button shows while a question is up')
    await pg.keyboard.press('ArrowDown')
    check(await pg.evaluate('__run.G().dash'), f'{tag}: ArrowDown dashes to the gate')
    await pg.wait_for_function('!__run.G().gate', timeout=30000)
    check(not await pg.is_visible('#dash'), f'{tag}: the dash button hides after the gate')
    real = [e for e in errs if 'WebGL' not in e and 'GPU stall' not in e]
    check(not real, f'{tag}: no page errors, failed requests or requests to another host {real[:3]}')
    await c.close()

async def main():
    proc = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        if port_open(PORT) or proc.poll() is not None: break
        time.sleep(.1)
    if proc.poll() is not None or not port_open(PORT):
        sys.exit(f'the test server did not start on port {PORT}')
    bad = remote_guard.remote_urls()
    check(not bad, f'no URL of another host in js/, css/, the pages and the tools (allowed: the class backend in config.js, Google Fonts in trainer.html) {bad[:3]}')
    bad = remote_guard.self_test()
    check(not bad, f'the guard catches a planted remote URL in js/mock.js, js/voice.js, js/run.js and css/game.css {bad[:2]}')
    bad = remote_guard.local_assets()
    check(not bad, f'every 3D model and picture is in assets/sources.tsv, on disk and matches its sha256; models under 3 MB {bad[:3]}')
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
            await play(b, 390, 844, 'r390x844')
            await looks(b)
            if '--quick' not in sys.argv:
                await play(b, 1366, 640, 'r1366x640')
            await b.close()
    finally:
        proc.terminate()
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    sys.exit(1 if fails else 0)

asyncio.run(main())
