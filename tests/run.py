"""Beach Run (run.html): start, play a whole run with the right and wrong answers, check scoring, and take screenshots.
   python3 tests/run.py [--shots DIR]"""
import asyncio, os, subprocess, sys, time, socket
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8797
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

async def play(b, w, h, tag):
    errs = []
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=w < 700)
    pg = await c.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'cloudfront' not in m.text and 'Failed to load resource' not in m.text else None)
    await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
    await pg.goto(BASE)
    await pg.wait_for_selector('[data-go="run"]', timeout=15000)
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
    check(not real, f'{tag}: no page errors {real[:3]}')
    await c.close()

async def main():
    proc = None
    if not port_open(PORT):
        proc = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if port_open(PORT): break
            time.sleep(.1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
            await play(b, 390, 844, 'r390x844')
            if '--quick' not in sys.argv:
                await play(b, 1366, 640, 'r1366x640')
            await b.close()
    finally:
        if proc: proc.terminate()
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    sys.exit(1 if fails else 0)

asyncio.run(main())
