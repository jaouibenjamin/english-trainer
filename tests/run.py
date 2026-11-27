# suite:   # picked up by tests/all.py
"""Beach Run (run.html): start, play a whole run with the right and wrong answers, check scoring, and take screenshots.
   Also: the runner model is our own file and loads in both looks, Pitzi the crab runs when the model is missing, and
   nothing in the game's files points to another host (tests/remote_guard.py).
   python3 tests/run.py [--shots DIR]"""
import asyncio, os, re, subprocess, sys, time, socket
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remote_guard
from csp_wait import csp_wait
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
        pg = csp_wait(await c.new_page())
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
        pg = csp_wait(await c.new_page())
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


SMALL = """[...document.querySelectorAll('#rstage *')].filter(e=>e.offsetParent&&[...e.childNodes].some(n=>n.nodeType===3&&/[\\p{L}\\p{N}]/u.test(n.textContent))&&parseFloat(getComputedStyle(e).fontSize)<16)
 .map(e=>[e.className||e.tagName,e.textContent.trim().slice(0,16),getComputedStyle(e).fontSize])"""
FLASH = """(()=>{const lum=c=>{const m=c.match(/[\\d.]+/g).map(Number);const f=v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4};return [.2126*f(m[0])+.7152*f(m[1])+.0722*f(m[2]),m[3]===undefined?1:m[3]]};
 const e=document.querySelector('#flash'),s=getComputedStyle(e),a=lum(s.color)[0],b=lum(s.backgroundColor),r=e.getBoundingClientRect();
 return {text:e.textContent,opaque:b[1]>=.99,ratio:+((Math.max(a,b[0])+.05)/(Math.min(a,b[0])+.05)).toFixed(2),w:Math.round(r.width),stage:Math.round(document.querySelector('#rstage').getBoundingClientRect().width)}})()"""
TARGETS = """[...document.querySelectorAll('#rstage button,#rstage a')].filter(e=>e.offsetParent&&getComputedStyle(e).visibility!=='hidden')
 .map(e=>{const r=e.getBoundingClientRect();return [e.className||e.tagName,e.dataset.k||e.dataset.go||e.dataset.pace||'',Math.round(r.width),Math.round(r.height)]})"""

async def ds_check(pg, tag, on, css):
    """the flag: off, the page is as before (no class, no extra stylesheet, nothing stored); on, the new look and its two stylesheets"""
    st = await pg.evaluate("[document.documentElement.classList.contains('ds'),localStorage.getItem('wi_ds'),getComputedStyle(document.querySelector('.card')).borderImageSource]")
    if on:
        check(st[0] and st[1] == '1' and 'ds.css' in css and 'run-ds.css' in css and 'panel' in st[2], f'{tag}: ?ds=1 shows the new look and remembers it on the device {st[:2]} {css}')
        if '--quick' not in sys.argv or tag.startswith('r390'):
            await ds_targets(pg, tag, 'the start menu')
    else:
        check(not st[0] and st[1] is None and css == ['run.css'] and st[2] == 'none', f'{tag}: flag off, no class, nothing stored, only run.css requested {st} {css}')

async def ds_targets(pg, tag, where):
    """in the new look every button and link on the screen is at least 48px tall, and the pad buttons and the gold button too"""
    t = await pg.evaluate(TARGETS)
    small = [x for x in t if x[3] < 48]
    check(t and not small, f'{tag}: {where}: every button and link is 48px or more {small}')
    tiny = await pg.evaluate(SMALL)
    check(not tiny, f'{tag}: {where}: no text under 16px {tiny[:4]}')

async def ds_calm_short(b):
    """new look with the game's own calm switch: "right" / "almost" fade and end hidden (the plate never stays over the
    road). A returning, signed-in pupil (best score and name lines) on a short phone, 360x740 and 360x640: the gold
    "run" button is on the screen without scrolling, and a new pupil's too"""
    c = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1, has_touch=True)
    pg = csp_wait(await c.new_page()); errs = []; watch(pg, errs)
    await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
    await pg.add_init_script("try{localStorage.setItem('word-islands-settings-v1',JSON.stringify({music:false,sfx:false,calm:true}))}catch(e){}")
    await pg.goto(BASE + '?ds=1'); await pg.wait_for_selector('[data-go="run"]', state='visible', timeout=15000)
    await pg.click('[data-go="run"]'); await pg.evaluate('window.__runFast=8; __run.noHit(true)')
    await pg.wait_for_function('!!__run.G().gate', timeout=60000)
    await pg.evaluate('__run.goLane(__run.lanes().indexOf(__run.answer()))')
    await pg.wait_for_function('!__run.G().gate', timeout=60000)
    await pg.evaluate('window.__runFast=1e-9')
    mid = await pg.evaluate("[document.documentElement.classList.contains('calm'),getComputedStyle(document.querySelector('#flash')).animationName]")
    await pg.wait_for_timeout(1500)
    op = await pg.evaluate("getComputedStyle(document.querySelector('#flash')).opacity")
    check(mid == [True, 'dsstill'] and op == '0', f'new look, calm: "right" fades and is hidden again 1.5 s after the answer {mid} opacity {op}')
    real = [e for e in errs if 'WebGL' not in e and 'GPU stall' not in e]
    check(not real, f'new look, calm: no page errors {real[:3]}')
    await c.close()
    # a returning pupil: a best score and a signed-in name (a backend URL that nothing is sent to in this check)
    REC = "try{localStorage.setItem('aam-unit1-v1',JSON.stringify({pts:120,u:{c:'TEST',n:'Testpupil',p:'0000'},r:{runs:3,best:9,pace:'mid',miss:[],dpts:0}}))}catch(e){}"
    for w, h in ((360, 740), (360, 640)):
        for who, rec in (('returning', True), ('new', False)):
            c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1, has_touch=True)
            pg = csp_wait(await c.new_page())
            await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='http://127.0.0.1:9/never';" if rec else "window.API_URL='';"))
            await pg.route('http://127.0.0.1:9/**', lambda r: r.abort())
            if rec: await pg.add_init_script(REC)
            await pg.goto(BASE + '?ds=1'); await pg.wait_for_selector('[data-go="run"]', state='visible', timeout=15000); await pg.wait_for_timeout(300)
            R = await pg.evaluate("(()=>{const m=document.querySelector('#menu');m.scrollTop=0;const b=document.querySelector('[data-go=run]').getBoundingClientRect();return {bottom:Math.round(b.bottom),top:Math.round(b.top),h:innerHeight,lines:document.querySelectorAll('#menu .who').length,scroll:m.scrollHeight>m.clientHeight}})()")
            check(R['bottom'] <= R['h'] and R['top'] >= 0 and (R['lines'] >= 2 if rec else True), f'new look, {who} pupil at {w}x{h}: the "run" button is on the screen without scrolling {R}')
            if SHOTS and rec:
                os.makedirs(SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(SHOTS, f'ds_{who}_{w}x{h}_start.png'))
            await c.close()

async def ds_slow(b):
    """new look on a small phone (360x740) on slow wifi, with reduced motion asked by the device: the menu stays hidden
    until both stylesheets are in, so the old look never shows; the question card in the new look ends as high as in
    today's look (the lanes stay above the road); the card does not slide in and "right" only fades"""
    c = await b.new_context(viewport={'width': 360, 'height': 740}, device_scale_factor=1, has_touch=True, reduced_motion='reduce')
    pg = csp_wait(await c.new_page())
    errs = []; watch(pg, errs)
    await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
    async def slow(route):
        await asyncio.sleep(3); await route.continue_()
    await pg.route('**/css/run-ds.css', slow)
    # every frame from the start: was the menu ever on screen with content before the new look's stylesheet was in?
    await pg.add_init_script("""window.__early={frames:0,shown:0};(function f(){const m=document.querySelector('#menu');
      if(m&&m.children.length){const css=[...document.styleSheets].some(s=>(s.href||'').endsWith('/css/run-ds.css'));__early.frames+=css?0:1;
       if(!css&&getComputedStyle(m).visibility!=='hidden')__early.shown++}requestAnimationFrame(f)})()""")
    await pg.goto(BASE + '?ds=1')
    await pg.wait_for_selector('[data-go="run"]', state='visible', timeout=15000)
    E = await pg.evaluate('__early')
    late = await pg.evaluate("[getComputedStyle(document.querySelector('#menu')).visibility,getComputedStyle(document.querySelector('.card')).borderImageSource.includes('panel')]")
    check(E['frames'] > 0 and E['shown'] == 0 and late == ['visible', True], f'360x740 new look, slow stylesheet: the menu stays hidden until the new look is in (frames with the menu built but the new look not yet in: {E["frames"]}, shown: {E["shown"]}) {late}')
    fit = await pg.evaluate("(()=>{const m=document.querySelector('#menu'),h=document.querySelector('.crabhead.hero').getBoundingClientRect();m.scrollTop=1e5;const b=document.querySelector('#menu .sm-btn').getBoundingClientRect();const r=[Math.round(h.top),Math.round(b.bottom),innerHeight];m.scrollTop=0;return r})()")
    check(fit[0] >= 0 and fit[1] <= fit[2], f'360x740 new look: the start menu shows its picture whole at the top and scrolls down to the last button {fit}')
    await pg.click('[data-go="run"]'); await pg.evaluate('window.__runFast=8; __run.noHit(true)')
    lows = []; motion = []
    for _ in range(6):
        await pg.wait_for_function('!!__run.G().gate||__run.G().ended', timeout=60000)
        if await pg.evaluate('__run.G().ended'): break
        await pg.wait_for_timeout(450)
        lows.append(await pg.evaluate("Math.round(document.querySelector('#banner').getBoundingClientRect().bottom)"))
        anim = [await pg.evaluate("getComputedStyle(document.querySelector('#banner')).animationName")]
        await pg.evaluate('__run.goLane(__run.lanes().indexOf(__run.answer()))')
        await pg.wait_for_function('!__run.G().gate', timeout=60000)
        anim.append(await pg.evaluate("getComputedStyle(document.querySelector('#flash')).animationName"))
        motion.append(anim)
    check(lows and max(lows) <= 205, f'360x740 new look: the question card ends at 205px or higher, as in today\'s look (195), so the lanes stay above the road {lows}')
    check(motion and all(m == ['none', 'dsstill'] for m in motion), f'360x740 new look, reduced motion: the card does not slide in and "right" only fades {motion[:2]}')
    real = [e for e in errs if 'WebGL' not in e and 'GPU stall' not in e]
    check(not real, f'360x740 new look: no page errors or failed requests {real[:3]}')
    await c.close()

BIDI = """(async()=>{const {POOL}=await import('./js/xdata.js');const {esc}=await import('./js/state.js');const fmt=FMT;const tips=[...new Set(Object.values(POOL).flatMap(o=>Object.values(o).flat()).map(e=>e.tip).filter(Boolean))];
 const box=document.createElement('div');box.className='banner';box.style.cssText='position:fixed;left:0;top:0;width:360px;visibility:hidden';document.body.appendChild(box);
 const out={n:tips.length,text:[],stop:[],checked:0,arrow:[],arrows:0};
 /* the box drawn for the character at index i of the line's text */
 const at=(p,i)=>{const w=document.createTreeWalker(p,NodeFilter.SHOW_TEXT);let n,off=0;while((n=w.nextNode())){if(i<off+n.length){const r=document.createRange();r.setStart(n,i-off);r.setEnd(n,i-off+1);return r.getBoundingClientRect()}off+=n.length}return null};
 out.empty=tips.filter(t=>/\\(\\s*\\)/.test(t));
 /* the same line as Beach Run draws it (mixed) and as the mock exam draws it (its own fmt, read from js/mock.js) */
 for(const [who,draw] of [['run',__run.mixed],['exam',fmt]])for(const t of tips){box.innerHTML=`<p class="ans">${draw(t)}</p>`;const p=box.firstChild;
  if(p.textContent!==t)out.text.push([who,t]);
  /* an English sentence that ends with a full stop, question mark or "!" (at the end of the line, before a Hebrew
     note or before a bracket): the mark is drawn right after the sentence's last letter, not at the far side */
  for(const m of t.matchAll(/[a-z'\\u2019][.?!](?=$| \\(| [\\u0590-\\u05FF])/g)){const L=at(p,m.index),D=at(p,m.index+1);if(who==='run')out.checked++;
   if(who==='run'&&Math.abs(D.top-L.top)<4&&!(D.left>=L.right-1))out.stop.push([t,Math.round(L.right),Math.round(D.left)])}
  /* an arrow points at the word after it: → has it on its right, ← on its left */
  for(const m of t.matchAll(/[\\u2192\\u2190]/g)){let j=m.index+1;while(t[j]===' ')j++;if(j>=t.length)continue;const A=at(p,m.index),N=at(p,j);
   if(Math.abs(A.top-N.top)>=4)continue;out.arrows++;const ok=m[0]==='\\u2192'?N.left>=A.right-1:N.right<=A.left+1;if(!ok)out.arrow.push([who,t,m[0],Math.round(A.left),Math.round(N.left)])}}
 box.remove();return out})()"""

async def bidi(b):
    """explanation lines mix Hebrew and English: the words are the same as before, an English sentence keeps its full
    stop (or ? or !) at its end (it used to show as ".I study English at school"), and an arrow points at its word"""
    c = await b.new_context(viewport={'width': 390, 'height': 844})
    pg = csp_wait(await c.new_page())
    await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
    await pg.goto(BASE); await pg.wait_for_selector('[data-go="run"]', timeout=15000)
    src = open(os.path.join(ROOT, 'js', 'mock.js'), encoding='utf-8').read()
    fmt_src = re.search(r'^const fmt=(.*?);$', src, re.M).group(1)   # the mock exam's own formatter, as it is in the file
    R = await pg.evaluate(BIDI.replace('FMT', fmt_src, 1))
    check(R['n'] > 50 and not R['text'], f'every explanation ({R["n"]}) reads the same words as before {R["text"][:2]}')
    check(R['checked'] > 5 and not R['stop'], f'an English sentence keeps its full stop at its end ({R["checked"]} checked) {R["stop"][:2]}')
    check(R['arrows'] > 10 and not R['arrow'], f'every arrow in an explanation points at the word it leads to, in Beach Run and in the mock exam ({R["arrows"]} checked) {R["arrow"][:2]}')
    check(not R['empty'], f'no explanation shows empty brackets (a word without the teacher\'s translation) {R["empty"][:2]}')
    await c.close()

async def play(b, w, h, tag, qs=''):
    """a whole run; qs='?ds=1' plays it in the new look, which must change nothing but the styling"""
    errs = []
    css = []
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=w < 700)
    pg = csp_wait(await c.new_page())
    watch(pg, errs)
    await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body="window.API_URL='';"))
    pg.on('request', lambda r: css.append(r.url.split('/')[-1]) if '/css/' in r.url else None)
    await pg.goto(BASE + qs)
    await pg.wait_for_selector('[data-go="run"]', timeout=15000)
    await pg.wait_for_function('window.__heroLoaded!==undefined', timeout=30000)
    await ds_check(pg, tag, bool(qs), css)
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
    if qs: await ds_targets(pg, tag, 'the HUD and the touch pad')
    seen = 0; wrong_done = False; shot_gate = False; t0 = time.time()
    while time.time() - t0 < 240:
        st = await pg.evaluate('(()=>{const G=__run.G();return G?{ended:G.ended,gate:!!G.gate,z:G.gateObj?G.gateObj.position.z:null,asked:G.asked}:null})()')
        if st['ended']: break
        if st['gate'] and st['z'] is not None:
            if not shot_gate and st['z'] > -30:
                await shot(pg, f'{tag}_03_gate'); shot_gate = True
                if qs: await ds_targets(pg, tag, 'the question card and the dash button')
            if st['z'] > -12:
                # the gate's lanes and its answer in one read: two reads could straddle the gate passing (lanes of this
                # gate, no answer any more), which a slow machine (all.py's parallel load) once did
                lanes, a = await pg.evaluate('[__run.lanes(),__run.answer()]')
                if lanes and a is not None and a in lanes:
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
                        if qs:
                            F = await pg.evaluate(FLASH)
                            check(F['opaque'] and F['ratio'] >= 4.5 and F['w'] < F['stage'], f'{tag}: "almost" over the road sits on its own solid plate, 4.5:1 or more {F}')
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
    if qs: await ds_targets(pg, tag, 'the end menu')
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
    await pg.wait_for_function('!__run.G().gate', timeout=60000)
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
    check(not bad, f'no URL of another host in js/, css/, the pages and the tools (allowed: only the class backend in config.js) {bad[:3]}')
    bad = remote_guard.self_test()
    check(not bad, f'the guard catches a planted remote URL in js/mock.js, js/voice.js, js/run.js, css/game.css, trainer.html and index.html {bad[:2]}')
    bad = remote_guard.private_paths() + remote_guard.private_self_test()
    check(not bad, f'the storage address (host or account folder) is written nowhere in the repo, and the scan catches a planted one {bad[:3]}')
    bad = remote_guard.credits()
    check(not bad, f'assets/CREDITS.md is up to date and names every file under assets/ and vendor/, and only those {bad[:2]}')
    bad = remote_guard.local_assets()
    check(not bad, f'every 3D model and picture is in assets/sources.tsv, on disk and matches its sha256; models under 3 MB {bad[:3]}')
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
            await bidi(b)
            await play(b, 390, 844, 'r390x844')
            await play(b, 390, 844, 'r390x844_ds', '?ds=1')
            await ds_slow(b)
            await ds_calm_short(b)
            await looks(b)
            if '--quick' not in sys.argv:
                await play(b, 1366, 640, 'r1366x640')
                await play(b, 1366, 768, 'r1366x768_ds', '?ds=1')
            await b.close()
    finally:
        proc.terminate()
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    sys.exit(1 if fails else 0)

asyncio.run(main())
