#!/usr/bin/env python3
"""End-to-end play-through for Word Islands (headless Chrome via Playwright).

    python3 tests/play.py            # full: every level of every island (local mode), island 1 at a second
                                     # viewport, class mode against the mock backend, audio levels
    python3 tests/play.py --quick    # island 1 only in each mode
    python3 tests/play.py --voice    # only the speech checks (recorded clips, fallbacks, no-voice device)
    python3 tests/play.py --shots DIR  # also save a PNG of every screen into DIR

It starts its own static server for the repo and, for class mode, the mock Apps Script backend
(tests/mock.js, a small Node stand-in for the Apps Script runtime that runs backend/Code.gs unchanged). Exits non-zero on any failed check or page error.
"""
import asyncio, math, os, subprocess, sys, time, socket
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCK = os.environ.get('MOCK', os.path.join(ROOT, 'tests', 'mock.js'))
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
QUICK = '--quick' in sys.argv
VOICE_ONLY = '--voice' in sys.argv
LAPTOP = '--laptop' in sys.argv   # island 1 with a mouse (no touch) at two laptop window sizes
SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
PORT, API_PORT = 8791, 8765
BASE = f'http://127.0.0.1:{PORT}/index.html'
fails, shot_n = [], [0]

# The listening level must be tested the way pupils get it: with a voice. Headless Chrome has no speech engine,
# so the pages get a small stand-in that "speaks" (fires start/end and records the text). SPEECH_NONE is an
# engine that always fails, for the one test of the honest no-voice fallback.
SPEECH_OK = """(()=>{const spoken=[];window.__spoken=spoken;
 const voices=[{name:'Google US English',lang:'en-US',default:true,localService:true,voiceURI:'stub'}];
 const stub={speaking:false,pending:false,paused:false,getVoices:()=>voices,cancel(){this.speaking=false},pause(){},resume(){},addEventListener(){},removeEventListener(){},
  speak(u){spoken.push(u.text);this.speaking=true;setTimeout(()=>{u.onstart&&u.onstart({})},30);setTimeout(()=>{this.speaking=false;u.onend&&u.onend({})},Math.min(900,150+u.text.length*40))}};
 Object.defineProperty(window,'speechSynthesis',{configurable:true,get:()=>stub});
 window.SpeechSynthesisUtterance=function(t){this.text=t}})()"""
SPEECH_NONE = """(()=>{window.__spoken=[];
 const stub={speaking:false,pending:false,paused:false,getVoices:()=>[],cancel(){},pause(){},resume(){},addEventListener(){},removeEventListener(){},
  speak(u){setTimeout(()=>{u.onerror&&u.onerror({error:'synthesis-unavailable'})},20)}};
 Object.defineProperty(window,'speechSynthesis',{configurable:true,get:()=>stub});
 window.SpeechSynthesisUtterance=function(t){this.text=t}})()"""

# The recorded voice (js/voice.js) lives next to the game (assets/voice/en/, served by the test's own static server), so in
# 'ok' mode the real MP3 files are fetched and decoded by Chrome. The stand-in only records what is requested and can make the
# clips fail: 'error' (fetch and <audio> both fail), 'mute' (nothing ever answers: the game must give up), 'nofetch' (fetch
# fails, <audio> works). <audio>.play() is always a stand-in that records the URL and fires playing + ended (or error), so the
# tests do not sit through whole sentences. Load errors of the clip <audio> element are kept away from the game.
CLIPS_HOST = 'assets/voice/'
def clip_stub(mode='ok'):
    return """(()=>{const clips=[],plays=[];window.__clips=clips;window.__plays=plays;window.__fetched=[];window.__clipMode='%s';
 const HOST=/(^|\\/)assets\\/voice\\//;
 const realFetch=window.fetch;
 window.fetch=function(u,o){const url=String(u&&u.url||u);if(!HOST.test(url))return realFetch.apply(this,arguments);
  window.__fetched.push(url);const m=window.__clipMode;
  if(m==='mute')return new Promise(()=>{});
  if(m!=='ok')return Promise.reject(new TypeError('offline'));
  return realFetch.apply(this,arguments)};
 /* a scheduled clip is logged with its stretch and cut short, so the tests do not sit through whole sentences */
 const S=AudioBufferSourceNode.prototype,start=S.start;
 S.start=function(when,off,dur){const c=this.buffer&&this.buffer.clip;
  if(c){clips.push(c.url);plays.push({via:'buf',url:c.url,s:c.s,e:c.e,dur:this.buffer.duration,when:when-this.context.currentTime,state:this.context.state,t:performance.now()});
   setTimeout(()=>{try{this.stop()}catch(e){}},160)}
  return start.apply(this,arguments)};
 const P=HTMLMediaElement.prototype,pause=P.pause;
 const add=P.addEventListener,rem=P.removeEventListener;   // the elements are not in the document, so their listeners are wrapped directly
 P.addEventListener=function(t,f,o){if(t!=='error')return add.call(this,t,f,o);f.__w=f.__w||(e=>{if(!e.isTrusted)f.call(this,e)});return add.call(this,t,f.__w,o)};
 P.removeEventListener=function(t,f,o){return rem.call(this,t,(t==='error'&&f.__w)||f,o)};
 P.play=function(){const src=this.getAttribute('src')||'',n=this.__n=(this.__n||0)+1,real=HOST.test(src),m=window.__clipMode,mode=real?(m==='nofetch'?'ok':m):'ok',
   fire=(t,ms)=>setTimeout(()=>{if(this.__n===n)this.dispatchEvent(new Event(t))},ms);
  if(real){clips.push(src.split('#')[0]);plays.push({via:'el',url:src.split('#')[0],frag:src.split('#')[1]||'',t:performance.now()})}
  if(mode==='error')fire('error',20);else if(mode==='ok'){fire('playing',20);fire('ended',160)}
  return Promise.resolve()};
 P.pause=function(){this.__n=(this.__n||0)+1;return pause.call(this)}})()""" % mode
CLIP_OF = "(async t=>((await import('/js/voice.js')).clipOf(t)||{}).url||null)"


def s_pad(fit):
    return 30          # the rope holes of the wooden sign take the top 30px


def check(label, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + label + (' ' + str(extra) if extra else ''), flush=True)
    if not ok:
        fails.append(label)


def port_open(p):
    s = socket.socket()
    try:
        s.settimeout(.3); s.connect(('127.0.0.1', p)); return True
    except OSError:
        return False
    finally:
        s.close()


def voice_files():
    """The voice is ours: no clip URL may point to another host again, and every file the game can ask for is on disk."""
    import json, re
    vj = open(os.path.join(ROOT, 'js', 'voice.js'), encoding='utf-8').read()
    mj = open(os.path.join(ROOT, 'js', 'mock.js'), encoding='utf-8').read()
    audio_url = re.compile(r"(https?:)?//[^'\"`\s]*\.(mp3|wav|ogg|oga|m4a|aac|webm|opus|flac)\b|cloudfront\.net", re.I)
    check('voice: js/voice.js names no remote host (no cloudfront, no http/https at all)', 'cloudfront' not in vj and not re.search(r'https?:|//[a-z0-9.-]+\.[a-z]{2,}/', vj, re.I))
    check('voice: js/mock.js loads no remote audio (no cloudfront, no http(s) audio URL)', not audio_url.search(mj), (audio_url.search(mj) or [''])[0])
    base = json.loads(re.search(r'const BASE=(".*?");', vj).group(1))
    rows = json.loads('[' + re.search(r'const ROWS=\[\n(.*?)\];\n', vj, re.S).group(1) + ']')
    vb = re.search(r"const VB='(.*?)';", mj).group(1)
    narr = re.findall(r"\n (\w+):\['([^']+)','", mj)
    check('voice: clip paths are relative to the page and inside assets/voice/', base.startswith('assets/voice/en/') and vb.startswith('assets/voice/he/'), [base, vb])
    def ok(rel):
        f = os.path.join(ROOT, rel)
        if not os.path.isfile(f) or os.path.getsize(f) < 1000: return False
        b = open(f, 'rb').read(3)
        return b == b'ID3' or (b[0] == 0xFF and b[1] & 0xE0 == 0xE0)
    en = {base + r[1] + '.mp3' for r in rows}
    he = {vb + k + '.mp3' for _, k in narr}
    miss = sorted(f for f in en | he if not ok(f))
    check(f'voice: all {len(rows)} English rows ({len(en)} files) and {len(narr)} Hebrew lines point to a real, non-empty MP3 on disk', len(rows) > 300 and len(narr) == 7 and not miss, miss[:5])
    disk = {f'assets/voice/{d}/{f}' for d in ('en', 'he') if os.path.isdir(os.path.join(ROOT, 'assets', 'voice', d)) for f in os.listdir(os.path.join(ROOT, 'assets', 'voice', d))}
    check('voice: no stray files in assets/voice/en and he (every file is used)', disk == en | he, sorted(disk ^ (en | he))[:5])
    rows_ok = all(isinstance(r[2], int) and isinstance(r[3], int) and 0 <= r[2] < r[3] for r in rows)
    check('voice: every row has a stretch inside its file (start < end, in ms)', rows_ok)
    # the manifest pins every served file: a clip that was swapped, re-encoded or damaged is caught here
    import hashlib
    lines = open(os.path.join(ROOT, 'assets', 'voice', 'sources.tsv'), encoding='utf-8').read().split('\n')
    head, man = lines[0].split('\t'), [dict(zip(lines[0].split('\t'), ln.split('\t'))) for ln in lines[1:-1]]
    pinned = {'assets/voice/' + r['file']: r['sha256'] for r in man}
    wrong = sorted(f for f in en | he if not re.fullmatch(r'[0-9a-f]{64}', pinned.get(f, '')) or hashlib.sha256(open(os.path.join(ROOT, f), 'rb').read()).hexdigest() != pinned[f])
    check(f'voice: every served file is listed in assets/voice/sources.tsv with its sha256, and the {len(pinned)} files on disk match', 'sha256' in head and set(pinned) == en | he and not wrong, (sorted(set(pinned) ^ (en | he)) + wrong)[:5])


async def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        await pg.wait_for_timeout(450)          # let the background cross-fade finish
        await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))


async def lv(pg, kind, timeout=15000):
    await pg.wait_for_function(f"window.__lv&&window.__lv.kind==='{kind}'", timeout=timeout)


async def play_sling(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'sling')
    box = await pg.locator('#cv').bounding_box()
    n, miss_done, missed_shot = 0, False, False
    if use_hint:
        await pg.click('[data-a=hint]')
    while n < 40:
        n += 1
        if await pg.locator('.result').count():
            return True
        st = await pg.evaluate("""(()=>{const L=window.__lv;if(!L||L.kind!=='sling')return null;const g=L.g;if(g.fly||g.lock||!g.bub.length)return null;
            const ok=g.bub.find(b=>b.ok),bad=g.bub.find(b=>!b.ok&&!b.bad);return {ok:[ok.x,ok.y],bad:bad?[bad.x,bad.y]:null,geo:L.geom(),K:L.K,G:L.G,i:g.i}})()""")
        if not st:
            await pg.wait_for_timeout(200); continue
        geo, K, G = st['geo'], st['K'], st['G']
        tx, ty = st['ok']
        if wrong_first and not miss_done and st['bad']:
            tx, ty = st['bad']; miss_done = True
        vy = -15.0
        a, b, c = .5 * G, vy, geo['AY'] - ty
        t = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)       # first time the ball is at the balloon's height
        dy = -vy / K                                            # the ball is released from the pulled-back position
        a, b, c = .5 * G, vy, geo['AY'] + dy - ty
        t = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
        vx = (tx - geo['AX']) / (t - 1 / K)
        dx = -vx / K
        x0, y0 = box['x'] + geo['AX'], box['y'] + geo['AY']
        await pg.mouse.move(x0, y0); await pg.mouse.down()
        await pg.mouse.move(x0 + dx / 2, y0 + dy / 2, steps=3); await pg.mouse.move(x0 + dx, y0 + dy, steps=3)
        if tag and st['i'] == 1:
            await pg.wait_for_timeout(120); await shot(pg, tag + '_aim')
        await pg.mouse.up()
        if tag and SHOTS and st['i'] == 0 and miss_done and wrong_first and not missed_shot:
            missed_shot = True
            await pg.wait_for_timeout(750); await pg.screenshot(path=os.path.join(SHOTS, tag + '_miss.png')); await pg.wait_for_timeout(750)
        else:
            await pg.wait_for_timeout(1500)
    return False


async def play_listen(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'listen')
    done_wrong = False
    for _ in range(60):
        if await pg.locator('.result').count():
            return True
        ans = await pg.evaluate("(()=>{const L=window.__lv;return L&&L.kind==='listen'&&!L.g.lock?L.answer():null})()")
        if not ans:
            await pg.wait_for_timeout(200); continue
        if wrong_first and not done_wrong:
            done_wrong = True
            await pg.locator(f'.bub:not(.bad):not([data-w="{ans}"])').first.click(force=True)
            await pg.wait_for_timeout(250)
            w = await pg.evaluate("({bad:document.querySelectorAll('.bub.bad').length,glow:document.querySelectorAll('.bub.hinted').length,em:document.querySelector('.bub.bad em').textContent,st:document.querySelectorAll('.hud .hs>img[src*=\"star.webp\"]:not(.fall)').length})")
            check('listening: a wrong tap marks only the tapped bubble (with its meaning); nothing glows; one slip keeps 3 header stars', w['bad'] == 1 and w['glow'] == 0 and len(w['em']) > 0 and w['st'] == 3, w)
            if tag: await shot(pg, tag + '_wrong')
            await pg.click('[data-a=again]', force=True)
        if use_hint:
            await pg.click('[data-a=hint]'); use_hint = False; await pg.wait_for_timeout(150)
            check('hint: the first use says that the level is now limited to 2 stars', await pg.locator('#toast.on').count() == 1 and '2' in await pg.locator('#toast').inner_text())
            h = await pg.evaluate("({glow:document.querySelectorAll('.bub.hinted').length,st:document.querySelectorAll('.hud .hs>img[src*=\"star.webp\"]:not(.fall)').length,fall:document.querySelectorAll('.hud .fall').length})")
            check('hint: the right bubble glows and the header drops to 2 stars at once', h['glow'] == 1 and h['st'] == 2 and h['fall'] == 1, h)
            if tag: await shot(pg, tag + '_hint')
            await pg.wait_for_timeout(2900)                  # let the note leave before the next screenshot
        await pg.locator(f'.bub[data-w="{ans}"]').click(force=True)
        await pg.wait_for_timeout(400)
        if tag and not done_wrong: pass
        await pg.wait_for_timeout(1000)
    return False


async def play_read(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'read')
    await pg.locator('.t').first.click()                    # gloss a word
    gl = await pg.locator('#gl').inner_text()
    check('read: tapping a word shows its gloss', '=' in gl, gl.replace('\n', ' ')[:40])
    if tag: await shot(pg, tag + '_gloss')
    await pg.click('[data-a=toq]')
    done_wrong = False
    for _ in range(40):
        if await pg.locator('.result').count():
            return True
        if not await pg.locator('.bottle').count():
            if await pg.locator('[data-a=unpeek]').count():
                await pg.click('[data-a=unpeek]')
            await pg.wait_for_timeout(200); continue
        ans = await pg.evaluate("(()=>{const L=window.__lv;return L&&!L.g.lock?L.answer():null})()")
        if ans is None:
            await pg.wait_for_timeout(200); continue
        if use_hint:
            use_hint = False
            await pg.click('[data-a=hint]'); await pg.wait_for_timeout(200)
            check('read: hint opens the story with a marked sentence', await pg.locator('.sn.hl').count() > 0)
            if tag: await shot(pg, tag + '_hint')
            await pg.click('[data-a=unpeek]')
        if wrong_first and not done_wrong:
            done_wrong = True
            await pg.locator(f'.bottle:not([data-o="{ans}"])').first.click(); await pg.wait_for_timeout(250)
            if tag: await shot(pg, tag + '_wrong')
            await pg.click('[data-a=peek]'); await pg.wait_for_timeout(150)
            check('read: peek shows the story again', await pg.locator('.story').count() == 1)
            await pg.click('[data-a=unpeek]')
        await pg.locator(f'.bottle[data-o="{ans}"]').click()
        await pg.wait_for_timeout(1500)
    return False


async def play_bridge(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'bridge')
    done_wrong, shots = False, set()
    for _ in range(120):
        if await pg.locator('.result').count():
            return True
        nxt = await pg.evaluate("(()=>{const L=window.__lv;return L&&L.kind==='bridge'&&!L.g.lock?[L.next(),L.g.r.kind]:null})()")
        if not nxt or nxt[0] is None:
            await pg.wait_for_timeout(200); continue
        want, kind = nxt
        if use_hint:
            use_hint = False; await pg.click('[data-a=hint]')
        if tag and kind == 'tobe' and 'tobe' not in shots:
            shots.add('tobe'); await pg.wait_for_timeout(300); await shot(pg, tag + '_tobe')      # the question, before it is answered
            box = await pg.evaluate("(()=>{const b=document.querySelector('.bank').getBoundingClientRect(),H=innerHeight;return [document.querySelectorAll('.sentc,.hole').length,b.bottom/H,document.querySelectorAll('.bank.tobe .pl').length,document.querySelectorAll('.slot.gap').length,document.querySelector('.slot.gap').textContent,document.querySelectorAll('.slot.f').length]})()")
            check('bridge: am/is/are round shows the sentence once (on the bridge) with one marked gap and three planks', box[0] == 0 and box[2] == 3 and box[3] == 1 and box[4] == '?' and box[5] >= 2 and .3 < box[1] < .75, box)
        if wrong_first and not done_wrong and kind == 'build':
            done_wrong = True
            laid = await pg.locator('.slot.f').count()
            await pg.locator(f'.pl:not(.used):not([data-t="{want}"])').first.click()
            await pg.wait_for_timeout(300)
            check('bridge: a wrong plank shows the red note with the reason', await pg.locator('.rule.bad').count() == 1 and 'הקרש נשבר: ' in await pg.locator('.rule').inner_text())
            check('bridge: the broken plank falls from the bridge while its tray place waits', await pg.locator('.pl.ghost').count() == 1 and await pg.locator('.bank .pl.snap').count() == 1)
            if tag: await shot(pg, tag + '_snap')
            await pg.wait_for_timeout(750)
            check('bridge: the plank is back in the tray with a red outline and the laid planks stayed', await pg.locator('.bank .pl.back').count() == 1 and await pg.locator('.pl.ghost').count() == 0 and await pg.locator('.slot.f').count() == laid)
            if tag: await shot(pg, tag + '_snap_back')
            placed = await pg.evaluate("__lv.g.placed")
            if placed == 0:
                await pg.wait_for_timeout(300)
                await pg.locator(f'.pl:not(.used):not(.back):not([data-t="{want}"])').first.click(); await pg.wait_for_timeout(950)
                check('bridge: after a second miss on the first word the plank that starts the sentence is highlighted', await pg.locator(f'.bank .pl.lead[data-t="{want}"]').count() == 1)
                if tag: await shot(pg, tag + '_lead')
            await pg.locator(f'.pl:not(.used)[data-t="{want}"]').first.click()
            await pg.wait_for_timeout(260)
            check('bridge: the red note is gone after the next tap', await pg.locator('.rule.bad').count() == 0, await pg.locator('.rule').inner_text())
            if tag and 'build' not in shots:
                shots.add('build'); await shot(pg, tag + '_build')
            continue
        await pg.locator(f'.pl:not(.used)[data-t="{want}"]').first.click()
        await pg.wait_for_timeout(260)
        if tag and kind == 'build' and 'build' not in shots:
            shots.add('build'); await shot(pg, tag + '_build')
        if tag and kind == 'tobe' and 'tobe_done' not in shots:
            shots.add('tobe_done'); await pg.wait_for_timeout(1300); await shot(pg, tag + '_tobe_done')
    return False


PLAYERS = {'sling': play_sling, 'listen': play_listen, 'read': play_read, 'bridge': play_bridge}


async def play_level(pg, isl, typ, **kw):
    await pg.evaluate(f"location.hash='play/{isl}/{typ}'")
    ok = await PLAYERS[typ](pg, **kw)
    check(f'island {isl} {typ}: played to the result screen', ok)
    if not ok:
        return 0
    await pg.wait_for_timeout(1700 if SHOTS else 300)
    stars = await pg.locator('.bs.on').count()
    return stars


async def new_page(b, w, h, api=None, errs=None, speech=SPEECH_OK, clips='ok'):
    c = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1 if LAPTOP else 2, has_touch=not LAPTOP, locale='he-IL')
    pg = await c.new_page()
    await pg.add_init_script(speech)
    await pg.add_init_script(clip_stub(clips))
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    # An <audio> element aborts the download of its clip
    # when the next clip replaces it: only that (a media request under assets/voice/, net::ERR_ABORTED) is tolerated.
    aborted_clip = lambda r: CLIPS_HOST in r.url and r.resource_type == 'media' and r.failure == 'net::ERR_ABORTED'
    pg.on('requestfailed', lambda r: errs.append(f'requestfailed: {r.url} ({r.resource_type}, {r.failure})') if not aborted_clip(r) else None)
    pg.on('response', lambda r: errs.append(f'http {r.status}: {r.url}') if r.status >= 400 else None)   # a missing voice file is an error
    # config.js in the repository carries the real class backend: a test page never talks to it (local mode = no backend at all)
    # (pinned from an init script, not by intercepting the file: interception switches the browser cache off for the page)
    if api:
        await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body=f"window.API_URL='{api}';"))
    else:
        await pg.add_init_script("Object.defineProperty(window,'API_URL',{get:()=>'',set(){},configurable:true})")
    return c, pg


async def local_run(b, w, h, full, errs):
    tag = f'{w}x{h}'
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.goto(BASE); await pg.wait_for_selector('.title .btn'); await pg.wait_for_timeout(600)
    await shot(pg, f'{tag}_01_title')
    check(f'[{tag}] local mode: no login, title shown', await pg.locator('#lc').count() == 0)
    await pg.click('.title .btn', force=True); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(500)
    await shot(pg, f'{tag}_02_map')
    check(f'[{tag}] map: 6 islands, only the first open', await pg.locator('.isl').count() == 6 and await pg.locator('.isl.locked').count() == 5)
    check(f'[{tag}] map: no leaderboard button in local mode', await pg.locator('[data-to=board]').count() == 0)
    await pg.locator('.isl.locked').first.click(); await pg.wait_for_timeout(300)
    check(f'[{tag}] locked island explains itself', await pg.locator('#toast.on').count() == 1)
    await pg.click('.isl.i1'); await pg.wait_for_selector('.lvrow'); await pg.wait_for_timeout(400)
    await shot(pg, f'{tag}_03_island')
    check(f'[{tag}] island 1 lists 4 levels', await pg.locator('.lvrow').count() == 4)
    check(f'[{tag}] island: the unit name is a subtitle, not a counter-like pill', 'מילים מתוך' in await pg.locator('.isub').inner_text() and await pg.locator('.chip').count() == 1)
    # onboarding hint on the very first slingshot level
    await pg.evaluate("location.hash='play/1/sling'"); await lv(pg, 'sling'); await pg.wait_for_timeout(500)
    check(f'[{tag}] first run shows the animated drag hint', await pg.locator('#coach:not([hidden])').count() == 1)
    geo = await pg.evaluate("(()=>{const g=__lv.geom(),c=document.querySelector('#coach').getBoundingClientRect(),cv=document.querySelector('#cv').getBoundingClientRect(),b=__lv.g.bub.slice().sort((a,b)=>a.x-b.x),p=[...document.querySelectorAll('.pips i')].map(e=>e.getBoundingClientRect().left);return {dx:c.left-cv.left-g.AX,dy:c.top-cv.top-g.AY,gaps:[1,2,3].map(k=>Math.round(b[k].x-b[k-1].x)),ys:b.map(o=>Math.round(o.y)),R:g.R,W:g.W,x0:b[0].x,x3:b[3].x,pipsRtl:p[0]>p[1]&&document.querySelector('.pips i').className==='c'}})()")
    check(f'[{tag}] sling: the pull arrow starts right under the ball', abs(geo['dx']) < 2 and 10 < geo['dy'] < 50, geo)
    check(f'[{tag}] sling: four balloons in a balanced arc with even spacing, inside the screen', len(set(geo['gaps'])) == 1 and geo['gaps'][0] >= 2 * geo['R'] and geo['ys'][0] == geo['ys'][3] and geo['ys'][1] == geo['ys'][2] < geo['ys'][0] and geo['x0'] - geo['R'] >= 4 and geo['x3'] + geo['R'] <= geo['W'] - 4 and abs(geo['x0'] + geo['x3'] - geo['W']) < 1, geo)
    check(f'[{tag}] progress dots fill from the right', geo['pipsRtl'], geo)
    await shot(pg, f'{tag}_04_sling_start')
    s1 = await play_level(pg, 1, 'sling', wrong_first=True, tag=f'{tag}_05_sling')
    await shot(pg, f'{tag}_06_result_sling')
    check(f'[{tag}] sling with one miss still earns 3 stars', s1 == 3, s1)
    check(f'[{tag}] one-tap next level button present', await pg.locator('.result .btn.green').count() == 1)
    await pg.click('.result .btn.green')                     # next level = listening
    await lv(pg, 'listen'); await pg.wait_for_timeout(700); await shot(pg, f'{tag}_07_listen')
    L = await pg.evaluate("({ans:__lv.answer(),spoken:__spoken.slice(-1)[0],clip:__clips.slice(-1)[0],sign:document.querySelector('.listen .prompt').innerText,wordHidden:document.querySelector('#lw').hidden,btn:document.querySelector('#rl').textContent,tts:__lv.g.tts})")
    L['want'] = await pg.evaluate(CLIP_OF, L['ans'])
    heard = L['clip'] == L['want'] and L['ans'] not in await pg.evaluate('__spoken') if L['want'] else L['spoken'] == L['ans']
    check(f'[{tag}] listening: the word is spoken (recorded clip when there is one), not printed', L['tts'] and heard and L['wordHidden'] and L['ans'] not in L['sign'], L)
    check(f'[{tag}] listening: sign and button say the same thing', 'הקשיבו' in L['sign'] and L['btn'] == 'השמיעו שוב', L)
    s2 = await play_level(pg, 1, 'listen', wrong_first=True, use_hint=True, tag=f'{tag}_08_listen')
    await shot(pg, f'{tag}_09_result_listen')
    check(f'[{tag}] hint caps the level at 2 stars and the result says why', s2 == 2 and 'רמז' in await pg.locator('.result .note').inner_text(), s2)
    await pg.evaluate("location.hash='play/1/read'"); await lv(pg, 'read'); await pg.wait_for_timeout(500); await shot(pg, f'{tag}_10_read_story')
    s3 = await play_level(pg, 1, 'read', wrong_first=True, use_hint=False, tag=f'{tag}_11_read')
    await shot(pg, f'{tag}_12_result_read')
    check(f'[{tag}] one slip keeps 3 stars in reading too (same rule in every game)', s3 == 3, s3)
    s4 = await play_level(pg, 1, 'bridge', wrong_first=True, tag=f'{tag}_13_bridge')
    await shot(pg, f'{tag}_14_result_bridge')
    check(f'[{tag}] bridge with one broken plank keeps 3 stars', s4 == 3, s4)
    st = await pg.evaluate("(()=>{const S=__game.S();return {tot:__game.totalStars(),pts:S.pts,w:Object.keys(S.w).length,st:Object.keys(S.st).length,read:S.read[1],g:S.g.st}})()")
    check(f'[{tag}] stars saved', st['tot'] == s1 + s2 + s3 + s4, st)
    check(f'[{tag}] points, word knowledge and reading score recorded', st['pts'] > 0 and st['w'] >= 7 and st['st'] >= 7 and st['read'] == 4, st)
    # replay with a worse result must not lower stars; points must still go up
    pts0 = st['pts']
    await play_level(pg, 1, 'listen', wrong_first=True, use_hint=True)
    st2 = await pg.evaluate("(()=>{const S=__game.S();return {tot:__game.totalStars(),pts:S.pts}})()")
    check(f'[{tag}] replay keeps best stars and raises points', st2['tot'] == st['tot'] and st2['pts'] > pts0, st2)
    await star_loss(pg, tag)
    await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(400)
    check(f'[{tag}] no finish banner while levels are still unplayed', await pg.locator('.fin').count() == 0 and await pg.locator('.compass').count() == 1)
    cb = await pg.evaluate("(()=>{const r=document.querySelector('.compass').getBoundingClientRect(),s=document.querySelector('#stage').getBoundingClientRect();return [r.left-s.left,s.right-r.right,s.bottom-r.bottom,r.width]})()")
    check(f'[{tag}] the compass is whole, inside the screen', cb[0] >= 4 and cb[1] > 0 and cb[2] >= 4 and cb[3] > 40, cb)
    check(f'[{tag}] island 2 unlocked after island 1', await pg.locator('.isl.i2.locked').count() == 0)
    check(f'[{tag}] the "continue here" crab moved to the newest open island', await pg.locator('.isl.i2.cur .here').count() == 1 and await pg.locator('.isl.cur').count() == 1)
    await shot(pg, f'{tag}_15_map_progress')
    await pg.reload(); await pg.wait_for_timeout(800)
    check(f'[{tag}] progress survives reload', await pg.evaluate("__game.totalStars()") == st['tot'])
    for name, h in [('collection', 'collection'), ('settings', 'settings'), ('help', 'help')]:
        await pg.evaluate(f"location.hash='{h}'"); await pg.wait_for_timeout(500); await shot(pg, f'{tag}_2{["collection","settings","help"].index(name)}_{name}')
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('.setrow')
    await pg.click('[data-k=music]'); await pg.click('[data-k=sfx]')
    check(f'[{tag}] sound toggles persist', await pg.evaluate("JSON.parse(localStorage.getItem('word-islands-settings-v1')).music===false&&JSON.parse(localStorage.getItem('word-islands-settings-v1')).sfx===false"))
    await pg.click('[data-k=music]'); await pg.click('[data-k=sfx]')
    check(f'[{tag}] settings link to the classic trainer', await pg.locator('a[href="trainer.html"]').count() == 1)
    await pg.evaluate("location.hash='collection'"); await pg.wait_for_selector('.ball')
    opened = await pg.locator('.ball:not(.locked)').count()
    check(f'[{tag}] collection unlocks by stars', opened >= 2, opened)
    await pg.locator('.ball:not(.locked)').nth(1).click(); await pg.wait_for_timeout(200)
    check(f'[{tag}] chosen ball is saved', await pg.evaluate("__game.S().g.ball") == 1)
    if full:
        for isl in (2, 3, 4, 5):
            # islands open by stars; give the stars a strong player would have by then, then play for real
            await pg.evaluate("(n=>{const S=__game.S();for(let i=1;i<n;i++)for(const t of['sling','listen','read','bridge'])S.g.st[i+'-'+t]=Math.max(S.g.st[i+'-'+t]||0,2);localStorage.setItem('aam-unit1-v1',JSON.stringify(S))})(%d)" % isl)
            for typ in ('sling', 'listen', 'read', 'bridge'):
                await pg.evaluate(f"location.hash='island/{isl}'"); await pg.wait_for_timeout(150)
                s = await play_level(pg, isl, typ, wrong_first=(typ == 'bridge'))
                check(f'[{tag}] island {isl} {typ} stars', s >= 2, s)
                if typ == 'sling': await shot(pg, f'{tag}_3{isl}_island{isl}_result')
            await pg.evaluate(f"location.hash='play/{isl}/sling'"); await lv(pg, 'sling'); await pg.wait_for_timeout(600); await shot(pg, f'{tag}_4{isl}_island{isl}_sling')
        await pg.evaluate("(()=>{const S=__game.S();for(let i=1;i<6;i++)for(const t of['sling','listen','read','bridge'])S.g.st[i+'-'+t]=3;localStorage.setItem('aam-unit1-v1',JSON.stringify(S))})()")
        for typ in ('sling', 'listen'):
            await pg.evaluate("location.hash='island/6'"); await pg.wait_for_timeout(150)
            s = await play_level(pg, 6, typ)
            check(f'[{tag}] bonus island {typ} stars', s == 3, s)
        await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(500); await shot(pg, f'{tag}_50_map_all_open')
        check(f'[{tag}] all islands open at the end', await pg.locator('.isl.locked').count() == 0)
        await finished_map(pg, tag)
        m = await pg.evaluate("__game.measure(40)")
        check('audio: offline render peak below 0.5 and not silent', 0.02 < m['peak'] < 0.5, m)
    # old trainer still works and links back
    await pg.goto(BASE.replace('index.html', 'trainer.html')); await pg.wait_for_timeout(500)
    check(f'[{tag}] classic trainer loads with a link back to the game', await pg.locator('a[href="./"]').count() == 1 and await pg.locator('.tile').count() == 6)
    await c.close()


async def finished_map(pg, tag):
    fin = await pg.evaluate("(()=>{const f=document.querySelector('.fin');if(!f)return null;const r=f.getBoundingClientRect(),low=Math.max(...[...document.querySelectorAll('.isl')].map(e=>e.getBoundingClientRect().bottom));return {t:f.innerText,clear:r.top-low,cur:document.querySelectorAll('.isl.cur').length}})()")
    check(f'[{tag}] map at 66/66: finished banner under the islands, nothing left to point at', fin and 'סיימתם את כל האיים' in fin['t'] and '66' in fin['t'] and fin['clear'] >= 0 and fin['cur'] == 0 and await pg.locator('.isl.todo').count() == 0, fin)
    await pg.evaluate("(()=>{const S=__game.S();S.g.st['3-read']=2;S.g.st['5-bridge']=1;localStorage.setItem('aam-unit1-v1',JSON.stringify(S));__game.go('map')})()")
    await pg.wait_for_timeout(500)
    FIN = "(()=>{const f=document.querySelector('.fin'),lh=parseFloat(getComputedStyle(f.querySelector('small')).lineHeight)||16,s=document.querySelector('#stage').getBoundingClientRect(),r=f.getBoundingClientRect();return {t:f.innerText.replace(/\\s+/g,' '),cur:document.querySelectorAll('.isl.cur').length,todo:[...document.querySelectorAll('.isl.todo')].map(e=>+e.className.match(/i(\\d)/)[1]).sort(),notFull:[...document.querySelectorAll('.isl:not(.full)')].map(e=>+e.className.match(/i(\\d)/)[1]).sort(),ticks:document.querySelectorAll('.isl .ck').length,lines:Math.round(f.querySelector('small').getBoundingClientRect().height/lh),split:[...f.querySelectorAll('.nb')].some(e=>new Set([...e.getClientRects()].map(r=>Math.round(r.top/6))).size>1),trophy:f.querySelectorAll('.ft').length,inside:r.left>=s.left&&r.right<=s.right&&r.bottom<=s.bottom,low:Math.max(...[...document.querySelectorAll('.isl')].map(e=>e.getBoundingClientRect().bottom))<=r.top}})()"
    fin = await pg.evaluate(FIN)
    check(f'[{tag}] 63/66, all levels played: the banner does not say "finished", it says 3 stars are missing', 'סיימתם' not in fin['t'] and 'כל הכבוד' not in fin['t'] and fin['trophy'] == 0 and 'עברתם בכל האיים' in fin['t'] and 'חסרים לכם עוד 3 כוכבים' in fin['t'], fin)
    check(f'[{tag}] every island that is not at full stars is ringed (both of them), the full ones are ticked', fin['todo'] == [3, 5] and fin['notFull'] == [3, 5] and fin['ticks'] == 4 and fin['cur'] == 1, fin)
    check(f'[{tag}] the banner text sits in whole lines (no orphan word, no split phrase), inside the screen and under the islands', fin['lines'] <= 2 and not fin['split'] and fin['inside'] and fin['low'], fin)
    await shot(pg, f'{tag}_51_map_played_stars_missing')
    await pg.evaluate("(()=>{const S=__game.S();S.g.st['3-read']=3;S.g.st['5-bridge']=2;localStorage.setItem('aam-unit1-v1',JSON.stringify(S));__game.go('map')})()")
    await pg.wait_for_selector('.map .fin'); await pg.wait_for_timeout(300)
    fin = await pg.evaluate(FIN)
    check(f'[{tag}] 65/66: one star missing is said in the singular and only that island is ringed', 'סיימתם' not in fin['t'] and 'חסר לכם עוד כוכב אחד' in fin['t'] and fin['todo'] == [5] and fin['lines'] <= 2 and not fin['split'], fin)
    await pg.evaluate("(()=>{const S=__game.S();S.g.st['3-read']=3;S.g.st['5-bridge']=3;localStorage.setItem('aam-unit1-v1',JSON.stringify(S))})()")


async def star_loss(pg, tag):
    """One star rule, shown live: the second mistake in a level drops a header star and says why, in every game the same way."""
    stars = "document.querySelectorAll('.hud .hs>img[src*=\"star.webp\"]:not(.fall)').length"
    await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .isl')      # the result screen keeps the level's hash
    await pg.evaluate("location.hash='play/1/listen'"); await lv(pg, 'listen')
    for k in range(2):
        await pg.wait_for_function(f"window.__lv&&__lv.kind==='listen'&&!__lv.g.lock&&__lv.g.i==={k}", timeout=8000)
        ans = await pg.evaluate("__lv.answer()")
        await pg.locator(f'.bub:not([data-w="{ans}"])').first.click(force=True); await pg.wait_for_timeout(200)
        if k == 0:
            check(f'[{tag}] listening: after one slip the header still shows 3 stars', await pg.evaluate(stars) == 3)
            await pg.locator(f'.bub[data-w="{ans}"]').click(force=True)
    r = await pg.evaluate("({st:%s,fall:document.querySelectorAll('.hud .fall').length,toast:document.querySelector('#toast.on')?document.querySelector('#toast').innerText:''})" % stars)
    check(f'[{tag}] listening: the second mistake drops a header star, animated, with a one-line reason', r['st'] == 2 and r['fall'] == 1 and 'ירד כוכב' in r['toast'], r)
    await shot(pg, f'{tag}_08_listen_star_lost')
    await pg.wait_for_timeout(3000)                          # let the note leave


async def fallback_run(b, w, h, errs):
    """No voice on the device: the level must say so, flash the word on the sign and offer "show again"."""
    tag = f'no-speech {w}x{h}'
    c, pg = await new_page(b, w, h, errs=errs, speech=SPEECH_NONE, clips='error')    # no speech engine and the clips cannot be reached
    await pg.goto(BASE + '#play/1/listen'); await lv(pg, 'listen')
    await pg.wait_for_function("window.__lv&&window.__lv.g.tts===false&&!document.querySelector('#lw').hidden", timeout=8000)
    L = await pg.evaluate("({ans:__lv.answer(),word:document.querySelector('#lw').textContent,sign:document.querySelector('#lt').textContent,btn:document.querySelector('#rl').textContent})")
    check(f'[{tag}] the word is flashed and the sign states the task', L['word'] == L['ans'] and L['sign'] == 'אין קול במכשיר הזה. המילה תופיע לרגע: זכרו אותה ולחצו עליה' and L['btn'] == 'הראו שוב', L)
    await pg.wait_for_timeout(1700)
    check(f'[{tag}] after the flash the sign offers "show again" (never an empty plank)', await pg.locator('#spk:not([hidden])').count() == 1 and await pg.locator('#lw[hidden]').count() == 1)
    fit = await pg.evaluate("(()=>{const s=document.querySelector('.listen .prompt').getBoundingClientRect(),t=document.querySelector('#lt').getBoundingClientRect(),b=document.querySelector('#spk').getBoundingClientRect();return [t.top-s.top,s.bottom-b.bottom,t.left-s.left,s.right-t.right]})()")
    check(f'[{tag}] the longer sign text and its button stay inside the wooden sign', fit[0] > s_pad(fit) and fit[1] > 8 and fit[2] > 10 and fit[3] > 10, fit)
    await pg.wait_for_timeout(1600); await shot(pg, f'{w}x{h}_07_listen_fallback')
    await pg.click('[data-a=again]'); await pg.wait_for_timeout(250)
    check(f'[{tag}] "show again" flashes the word again', await pg.locator('#lw:not([hidden])').count() == 1)
    if SHOTS: await pg.screenshot(path=os.path.join(SHOTS, f'{w}x{h}_07_listen_fallback_word.png'))
    ok = await play_listen(pg)
    check(f'[{tag}] the level can be finished without a voice', ok)
    await c.close()


async def voice_run(b, w, h, errs):
    """The recorded voice: clips are used when they exist, the browser voice covers every gap, read-to-me goes sentence by sentence."""
    tag = f'voice {w}x{h}'
    SAY = "(async t=>{const m=await import('/js/state.js'),t0=performance.now();const ok=await m.say(t);return{ok,ms:performance.now()-t0}})"
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.goto(BASE + '#play/1/listen'); await lv(pg, 'listen')
    await pg.wait_for_function("__clips.length>0", timeout=5000)
    ans = await pg.evaluate("__lv.answer()"); want = await pg.evaluate(CLIP_OF, ans)
    R = await pg.evaluate("({clips:[...__clips],spoken:[...__spoken],tts:__lv.g.tts})")
    check(f'[{tag}] a word with a clip requests exactly its clip URL and the browser voice stays silent', bool(want) and want.startswith('assets/voice/en/') and want.endswith('.mp3') and R['clips'][-1] == want and ans not in R['spoken'] and R['tts'], {'want': want, **R})
    await pg.wait_for_function("__lv.g.said>0", timeout=3000)
    # the new path: Web Audio, only the measured stretch of the file, scheduled a moment ahead on a running context
    P = await pg.evaluate("(async()=>{const c=(await import('/js/voice.js')).clipOf(__lv.answer()),p=__plays[__plays.length-1];return {c,p,n:__plays.length}})()")
    c0, p0 = P['c'], P['p']
    D = await pg.evaluate("(async u=>{const ab=await (await fetch(u)).arrayBuffer();return (await new OfflineAudioContext(1,1,24000).decodeAudioData(ab)).duration})", c0['url'])
    span = (min(D, c0['e'] + .08) - max(0, c0['s'] - .03)) if c0['e'] > c0['s'] else D
    check(f'[{tag}] the word plays through Web Audio: its own stretch of the file (30 ms before, 80 ms after), about 80 ms ahead, on a running context',
          p0['via'] == 'buf' and p0['url'] == c0['url'] and c0['e'] > c0['s'] and abs(p0['dur'] - span) < .01 and .05 < p0['when'] < .12 and p0['state'] == 'running' and P['n'] == 1, P)
    check(f'[{tag}] the level waited for its first word and then a quarter of a second before speaking', await pg.evaluate("__plays[0].t-__lv.t") >= 240, await pg.evaluate("__plays[0].t-__lv.t"))
    f0 = await pg.evaluate("__fetched.length")
    t = await pg.evaluate("(async()=>{const n=__plays.length,t0=performance.now();document.querySelector('[data-a=again]').click();for(let i=0;i<100&&__plays.length===n;i++)await new Promise(r=>setTimeout(r,5));return __plays.length>n?__plays[__plays.length-1].t-t0:-1})()")
    check(f'[{tag}] "play again" replays at once from the decoded clip, without another download', 0 <= t < 150 and await pg.evaluate("__fetched.length") == f0 and await pg.evaluate("__plays.slice(-1)[0].via") == 'buf', {'ms': t})
    await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .isl')
    n = await pg.evaluate("__clips.length")
    r = await pg.evaluate(SAY, 'purple xylophone')
    R = await pg.evaluate("({clips:__clips.length,spoken:[...__spoken]})")
    check(f'[{tag}] a text without a clip falls back to the browser voice', r['ok'] and R['clips'] == n and R['spoken'][-1] == 'purple xylophone', R)
    r = await pg.evaluate(SAY, 'Goal'); R = await pg.evaluate("({clip:__clips.slice(-1)[0],spoken:[...__spoken]})")
    check(f'[{tag}] lookup ignores case and extra spaces when there is no exact match', r['ok'] and R['clip'] == await pg.evaluate(CLIP_OF, 'goal') and await pg.evaluate(CLIP_OF, '  a  lot of ') == await pg.evaluate(CLIP_OF, 'a lot of') and 'Goal' not in R['spoken'], R)
    # read to me: title, then every sentence, in order; leaving the story stops it
    await pg.evaluate("location.hash='play/1/read'"); await lv(pg, 'read')
    parts = await pg.evaluate("(async()=>{const d=await import('/js/data.js'),v=await import('/js/voice.js'),t=d.TEXTS.find(x=>x.p===1);return [t.title,...(t.text.match(/[^.!?]+[.!?]+[\"”]?\\s*/g)||[t.text])].map(x=>(v.clipOf(x)||{}).url||null)})()")
    n = await pg.evaluate("__clips.length"); await pg.click('[data-a=readall]')
    await pg.wait_for_function(f"__clips.length>={n + len(parts)}", timeout=20000)
    await pg.wait_for_timeout(900)
    got = (await pg.evaluate("[...__clips]"))[n:]
    check(f'[{tag}] read to me plays the title and each sentence clip once, in order', all(parts) and got == parts, {'want': len(parts), 'got': len(got)})
    await pg.evaluate("(async()=>{const m=await import('/js/state.js');window.__n0=__clips.length;await m.sayAll(['goal','purple xylophone','song'],1,50);window.__mix=[__clips.slice(__n0),__spoken.slice(-1)[0]]})()")
    mix = await pg.evaluate("__mix")
    check(f'[{tag}] a sentence without a clip is read by the browser voice and the clips carry on', mix == [[await pg.evaluate(CLIP_OF, 'goal'), await pg.evaluate(CLIP_OF, 'song')], 'purple xylophone'], mix)
    n = await pg.evaluate("__clips.length"); await pg.click('[data-a=readall]'); await pg.wait_for_timeout(700)
    await pg.click('[data-a=toq]'); m = await pg.evaluate("__clips.length"); await pg.wait_for_timeout(1500)
    check(f'[{tag}] read to me stops when the pupil moves on', 1 <= m - n <= 3 and await pg.evaluate("__clips.length") == m, {'started': m - n})
    await pg.evaluate("location.hash='map'"); await pg.wait_for_selector('.map .isl')
    # a clip that fails, and one that never starts, hand over to the browser voice (fresh page: nothing decoded yet)
    await pg.reload(); await pg.wait_for_selector('.map .isl')
    await pg.evaluate("window.__clipMode='error'"); r = await pg.evaluate(SAY, 'kick')
    check(f'[{tag}] a clip that errors falls back to the browser voice', r['ok'] and await pg.evaluate("__spoken.slice(-1)[0]") == 'kick' and r['ms'] < 1500, r)
    # the download fails but the <audio> element can still play: the old path takes over and plays the same stretch
    await pg.evaluate("window.__clipMode='nofetch'"); r = await pg.evaluate(SAY, 'card'); p1 = await pg.evaluate("__plays.slice(-1)[0]"); c1 = await pg.evaluate("(async()=>(await import('/js/voice.js')).clipOf('card'))()")
    check(f'[{tag}] a clip that cannot be fetched plays through the <audio> element, limited to the same stretch', r['ok'] and p1['via'] == 'el' and p1['url'] == c1['url'] and p1['frag'] == 't=%.2f,%.2f' % (max(0, c1['s'] - .03), c1['e'] + .08) and await pg.evaluate("__spoken.slice(-1)[0]") != 'card', {'r': r, 'p': p1})
    await pg.evaluate("window.__clipMode='mute'"); r = await pg.evaluate(SAY, 'song')
    check(f'[{tag}] a clip that neither downloads within 3 s nor starts within 2.5 s falls back to the browser voice', r['ok'] and await pg.evaluate("__spoken.slice(-1)[0]") == 'song' and 5300 < r['ms'] < 7500, r)
    # hush() stops a scheduled clip
    await pg.evaluate("window.__clipMode='ok'")
    r = await pg.evaluate("(async()=>{const m=await import('/js/state.js');await m.say('goal');const t0=performance.now(),p=m.say('piano');await new Promise(r=>setTimeout(r,40));m.hush();const ok=await p;return {ok,ms:performance.now()-t0}})()")
    check(f'[{tag}] hush() stops the clip at once', r['ok'] and r['ms'] < 140, r)
    await c.close()
    # no speech engine at all, clips reachable: the listening level keeps its voice
    c, pg = await new_page(b, w, h, errs=errs, speech=SPEECH_NONE)
    await pg.goto(BASE + '#play/1/listen'); await lv(pg, 'listen')
    await pg.wait_for_function("__lv.g.said>0", timeout=5000); await pg.wait_for_timeout(300)
    L = await pg.evaluate("({tts:__lv.g.tts,hidden:document.querySelector('#lw').hidden,btn:document.querySelector('#rl').textContent,clips:__clips.length})")
    check(f'[{tag}] without a speech engine the listening level still speaks through the clips', L['tts'] and L['hidden'] and L['btn'] == 'השמיעו שוב' and L['clips'] >= 1, L)
    ok = await play_listen(pg)
    check(f'[{tag}] and can be finished by ear', ok and await pg.evaluate("!window.__lv||window.__lv.g.tts!==false"))
    await c.close()


async def class_run(b, w, h, errs):
    tag = f'class {w}x{h}'
    api = f'http://127.0.0.1:{API_PORT}/'
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    await pg.goto(BASE); await pg.wait_for_selector('#lc'); await pg.wait_for_timeout(500)
    # a few invented classmates so the leaderboard and the teacher screen look like a real class
    mates = [('נועה', 640, 31, 3, 4), ('איתי', 505, 24, 2, 2), ('מאיה', 410, 19, 1, 6), ('עומר', 220, 9, 0, 1),
             ('אלה', 1180, 47, 5, 7), ('יונתן', 960, 42, 4, 3), ('רומי', 845, 38, 4, 5), ('נדב', 730, 33, 3, 2), ('טליה', 150, 12, 1, 1), ('אריאל', 95, 11, 0, 1), ('שחר', 60, 10, 0, 1)]   # with the pupil: a class of 12
    taken = await pg.evaluate('''async ([api, mates]) => { const out = []; for (const [n, pts, words, reads, streak] of mates) {
        const post = d => fetch(api, {method: 'POST', body: JSON.stringify(d)}).then(r => r.json());
        const r = await post({a: 'register', c: 'EN-1234', n, p: '1111'}); out.push(r.ok ? '' : r.e);
        await post({a: 'save', c: 'EN-1234', n, p: '1111', s: {pts, streak, day: new Date().toISOString().slice(0, 10), k: {words, reads}, g: {st: Object.fromEntries(Array.from({length: Math.round(words / 59 * 22)}, (_, i) => ['L' + i, 3]))},
            st: words < 13 ? {their: [6, 4], special: [5, 2], subject: [6, 3], 'a lot of': [4, 2]} : {their: [6, 1], special: [5, 0], subject: [6, 1], 'a lot of': [4, 2]}}}); } return out }''', [api, mates])
    name = None
    for cand in ('יובל', 'תמר', 'אורי', 'שירה', 'דניאל', 'רוני', 'גיא', 'ליה', 'אדם', 'מיכל', 'עידו', 'הילה', 'בן', 'גל', 'זיו', 'חן', 'טל', 'לי', 'מור', 'ניר', 'סהר', 'עדי', 'פז', 'צוף', 'קרן', 'רז', 'שי', 'תום'):
        r = await pg.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'login',c:'EN-1234',n,p:'0000'})})).json()", [api, cand])
        if r.get('e') == 'nouser':
            name = cand; break
    check(f'[{tag}] a free pupil name is available on the mock backend', name is not None)
    await shot(pg, f'class_01_login')
    check(f'[{tag}] login is required', await pg.locator('#lc').count() == 1)
    tabs = await pg.evaluate("[...document.querySelectorAll('.seg button')].map(b=>[b.textContent,b.getAttribute('aria-selected')])")
    check(f'[{tag}] a device that never signed in starts on "first time"; the tabs say who they are for', tabs == [['כבר נרשמתי', 'false'], ['פעם ראשונה שלי', 'true']] and 'שרק אתם יודעים' in await pg.locator('.lnote').inner_text(), tabs)
    await pg.click('.seg [data-m=login]'); await pg.wait_for_timeout(150)
    await shot(pg, f'class_01_login_returning')
    await pg.fill('#lc', 'EN-1234'); await pg.fill('#ln', name); await pg.fill('#lp', '4321')
    check(f'[{tag}] one form, one primary button', await pg.locator('.lcard .btn').count() == 1 and (await pg.locator('.lcard .btn').inner_text()).strip() == 'כניסה')
    await pg.click('.lcard .btn'); await pg.wait_for_function("document.querySelector('.err')&&document.querySelector('.err').textContent.length>3")
    check(f'[{tag}] unknown name gets a friendly message with a one-tap switch to first-time mode', 'לא מצאנו' in await pg.locator('.err').inner_text() and await pg.locator('.err .swl[data-m=register]').count() == 1)
    await shot(pg, f'class_02_login_error')
    await pg.click('.err .swl'); await pg.wait_for_timeout(150)
    check(f'[{tag}] the switch turns the form into sign-up and keeps what was typed', (await pg.locator('.lcard .btn').inner_text()).strip() == 'נרשמים' and await pg.input_value('#ln') == name and await pg.input_value('#lp') == '4321')
    await shot(pg, f'class_02_login_register')
    await pg.click('.lcard .btn'); await pg.wait_for_selector('.title .sb')   # signed in: the pupil picks a subject
    check(f'[{tag}] after signing in the pupil chooses English, the mock exam or math', await pg.locator('.title .sb').count() == 3)
    await pg.click('.title .sb.green', force=True); await pg.wait_for_selector('.map .isl'); await pg.wait_for_timeout(400)
    check(f'[{tag}] register lands on the map with the labelled leaderboard button', await pg.locator('[data-to=board] small').count() == 1)
    await shot(pg, 'class_07_map')
    s = await play_level(pg, 1, 'sling')
    check(f'[{tag}] perfect sling gives 3 stars', s == 3, s)
    check(f'[{tag}] the result card labels the number: points for the table', 'נקודות לטבלת הכיתה' in await pg.locator('.result .gain.cp').inner_text())
    await shot(pg, f'class_03_result')
    for typ in ('listen', 'read'):
        s = await play_level(pg, 1, typ)
        check(f'[{tag}] perfect {typ} gives 3 stars', s == 3, s)
    await pg.evaluate("location.hash='settings'"); await pg.wait_for_selector('[data-a=logout]'); await shot(pg, 'class_05_settings')
    check(f'[{tag}] the log-out button is not called by the word that leaves a level', 'התנתקות' in await pg.locator('[data-a=logout]').inner_text() and 'יציאה' not in await pg.locator('[data-a=logout]').inner_text())
    check(f'[{tag}] pupils get no teacher entry in settings', await pg.locator('[data-to=teacher]').count() == 0)
    pts = await pg.evaluate("__game.S().pts")
    await pg.evaluate("location.hash='board'"); await pg.wait_for_selector('.lb li')
    txt = await pg.locator('.lb li.me').inner_text()
    check(f'[{tag}] own row on the leaderboard with points', name in txt and f'{pts:,}' in txt, txt.replace('\n', ' '))
    lb = await pg.evaluate("async api=>{const S=__game.S();const r=await (await fetch(api,{method:'POST',body:JSON.stringify({a:'board',c:S.u.c,n:S.u.n,p:S.u.p})})).json();return {cls:r.rows.length,rank:r.rows.findIndex(d=>d.n===S.u.n)+1,li:document.querySelectorAll('.lb li:not(.sep):not(.nxt)').length,nxt:(document.querySelector('.lb li.nxt')||{}).innerText||'',gap:r.rows[r.rows.findIndex(d=>d.n===S.u.n)-1].pts-S.pts+1,sep:document.querySelectorAll('.lb li.sep').length,me:document.querySelectorAll('.lb li.me').length,ranks:[...document.querySelectorAll('.lb .rk')].map(e=>+e.textContent)}}", api)
    check(f'[{tag}] class of 12 or more, pupil outside the top five: only the top 5 and the own row are drawn', lb['cls'] >= 12 and lb['rank'] > 5 and lb['li'] == 6 and lb['sep'] == 1 and lb['me'] == 1 and lb['ranks'] == [1, 2, 3, 4, 5, lb['rank']], lb)

    check(f'[{tag}] own row says "place N of M" and the line under it gives the points to the next place, not to the leader', f"מקום {lb['rank']} מתוך {lb['cls']}" in txt and 'כל שלב מוסיף נקודות' in lb['nxt'] and f"עוד {lb['gap']:,} נקודות למקום הבא" in lb['nxt'], [txt.replace('\n', ' '), lb['nxt']])
    await shot(pg, f'class_04_board')
    # a second device logs in and gets the same progress
    c2, p2 = await new_page(b, w, h, api=api, errs=errs)
    await p2.goto(BASE); await p2.wait_for_selector('#lc')
    await p2.click('.seg [data-m=login]'); await p2.wait_for_timeout(100)
    await p2.fill('#lc', 'en-1234'); await p2.fill('#ln', name); await p2.fill('#lp', '0000'); await p2.click('.lcard .btn')
    await p2.wait_for_function("document.querySelector('.err')&&document.querySelector('.err').textContent.length>3")
    check(f'[{tag}] wrong secret code is refused', 'הקוד הסודי' in await p2.locator('.err').inner_text())
    await p2.fill('#lp', '4321'); await p2.click('.lcard .btn'); await p2.wait_for_selector('.title .sb'); await p2.click('.title .sb.green', force=True); await p2.wait_for_selector('.map .isl')
    st = await p2.evaluate("(()=>{const S=__game.S();return [__game.totalStars(),S.pts,Object.keys(S.w).length]})()")
    check(f'[{tag}] second device receives stars, points and word knowledge', st[0] == 9 and st[1] == pts and st[2] >= 7, st)
    # the classic trainer shares the login and must not drop the game stars when it saves
    await p2.goto(BASE.replace('index.html', 'trainer.html') + '#quiz'); await p2.wait_for_timeout(500)
    await p2.click('[data-a=start]'); await p2.wait_for_timeout(300)
    ans = await p2.evaluate("V.qs[V.i].opts.indexOf(V.qs[V.i].ans)"); await p2.click(f'.opt >> nth={ans}'); await p2.wait_for_timeout(3600)
    await p2.goto(BASE + '#map'); await p2.wait_for_selector('.map .isl')
    await p2.evaluate("location.hash='settings'"); await p2.wait_for_selector('[data-a=logout]')
    await p2.click('[data-a=logout]'); await p2.wait_for_selector('#lc')
    check(f'[{tag}] logout returns to login and clears local progress', await p2.evaluate("__game.totalStars()") == 0)
    check(f'[{tag}] a device that signed in before starts on "already registered"', await p2.locator('.seg [data-m=login][aria-selected=true]').count() == 1)
    await p2.fill('#ln', name); await p2.fill('#lp', '4321'); await p2.click('.lcard .btn'); await p2.wait_for_selector('.title .sb'); await p2.click('.title .sb.green', force=True); await p2.wait_for_selector('.map .isl')
    st2 = await p2.evaluate("[__game.totalStars(),__game.S().pts]")
    check(f'[{tag}] stars survive a save made by the classic trainer', st2[0] == 9 and st2[1] > pts, st2)
    # teacher screen
    await p2.evaluate("location.hash='teacher'"); await p2.wait_for_selector('#tt')
    await p2.fill('#tt', '111'); await p2.click('[data-a=tlogin]'); await p2.wait_for_function("document.querySelector('.err').textContent.length>3")
    check(f'[{tag}] wrong teacher code is refused', 'קוד המורה' in await p2.locator('.err').inner_text())
    await p2.fill('#tt', '654321'); await p2.click('[data-a=tlogin]'); await p2.wait_for_selector('.kid')
    row = (await p2.locator('.kid', has_text=name).inner_text()).replace('\n', ' ')
    known = await p2.evaluate("__game.S().w ? Object.values(__game.S().w).filter(v=>v>=2).length : 0")
    check(f'[{tag}] teacher card lists the pupil with words learned and a finished story', name in row and f'{known} / 59' in row and known >= 3 and '1 / 5' in row, row)
    check(f'[{tag}] teacher card leads with stars and levels', '9 / 66' in row and '3 / 22' in row, row)
    check(f'[{tag}] teacher sees the hardest words', await p2.locator('.hard > div').count() >= 1)
    red = await p2.locator('.kid .pill.r').count(); kids = await p2.locator('.kid').count()
    check(f'[{tag}] the "needs reinforcement" tag is kept for the few who need it', 0 < red < kids - 1, [red, kids])
    await shot(p2, 'class_06_teacher')
    # the sheet is tidied while the pupil plays: their row is renamed. The device's next save is refused for good.
    # Before: silent, the device kept the points and the sheet never saw them. Now: a bar asks to sign in again,
    # and what the device earned joins the renamed account.
    newname = name + ' כ'
    ok = await p2.evaluate("async ([api,a,b])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'__rename',from:a,to:b})})).json()", [api, name, newname])
    check(f'[{tag}] test setup: the pupil row is renamed on the mock', ok.get('ok'))
    await p2.evaluate("location.hash='map'"); await p2.wait_for_selector('.map .isl')
    mine = await p2.evaluate("(async()=>{__game.award(200);await __game.push();return __game.S().pts})()")
    await p2.wait_for_selector('#syncbar.on .syncb', timeout=8000)
    check(f'[{tag}] a refused save shows the sign-in-again bar on the map', await p2.locator('#syncbar.on').count() == 1)
    await shot(p2, 'class_07_syncbar')
    await p2.click('.syncb'); await p2.wait_for_selector('#lc')
    check(f'[{tag}] the bar opens sign-in with the old name filled in and a reason', await p2.input_value('#ln') == name and 'נשמרת' not in await p2.locator('.err').inner_text() and len(await p2.locator('.err').inner_text()) > 10, await p2.locator('.err').inner_text())
    await shot(p2, 'class_08_relogin')
    await p2.fill('#ln', newname); await p2.fill('#lp', '4321'); await p2.click('.lcard .btn'); await p2.wait_for_selector('.title .sb')
    await p2.wait_for_timeout(3500)
    srv = await p2.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'login',c:'EN-1234',n,p:'4321'})})).json()", [api, newname])
    got = (srv.get('s') or {}).get('pts', 0)
    check(f'[{tag}] the device progress reached the renamed account in the sheet', got >= mine and await p2.evaluate("__game.S().pts") >= mine, [got, mine])
    check(f'[{tag}] the bar is gone once the account takes the saves', await p2.locator('#syncbar.on').count() == 0)
    # a forgotten secret code: the teacher resets it from the teacher screen, and the next sign-in chooses a new one
    await p2.evaluate("location.hash='teacher'"); await p2.wait_for_selector('#tt')
    await p2.fill('#tt', '654321'); await p2.click('[data-a=tlogin]'); await p2.wait_for_selector('.kid')
    rb = p2.locator('.kid', has_text=newname).locator('.treset')
    await rb.click(); check(f'[{tag}] reset asks for a second tap', 'שוב' in await rb.inner_text())
    await rb.click(); await p2.wait_for_function("document.querySelector('#toast').textContent.includes('אופס')")
    await shot(p2, 'class_09_teacher_reset')
    await p2.evaluate("location.hash='settings'"); await p2.wait_for_selector('[data-a=logout]')
    await p2.click('[data-a=logout]'); await p2.wait_for_selector('#lc')
    check(f'[{tag}] sign-in offers help for a forgotten code', await p2.locator('[data-a=forgot]').count() == 1)
    await p2.click('[data-a=forgot]'); check(f'[{tag}] the forgot-code note explains the reset', 'לאפס' in await p2.locator('.err').inner_text())
    await p2.fill('#lc', 'EN-1234'); await p2.fill('#ln', newname); await p2.fill('#lp', '2468'); await p2.click('.lcard .btn'); await p2.wait_for_selector('.title .sb')
    await p2.wait_for_function("document.querySelector('#toast').textContent.includes('2468')", timeout=4000)
    await shot(p2, 'class_10_new_code')
    again = await p2.evaluate("async ([api,n])=>(await fetch(api,{method:'POST',body:JSON.stringify({a:'login',c:'EN-1234',n,p:'2468'})})).json()", [api, newname])
    check(f'[{tag}] after a reset the new code works and the progress is still there', again.get('ok') and (again.get('s') or {}).get('pts', 0) >= mine, again.get('e'))
    await c.close(); await c2.close()


async def main():
    procs = []
    if not port_open(PORT):
        procs.append(subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    have_mock = os.path.exists(MOCK)
    if have_mock and not port_open(API_PORT):
        procs.append(subprocess.Popen(['node', MOCK], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for _ in range(40):
        if port_open(PORT) and (not have_mock or port_open(API_PORT)): break
        time.sleep(.1)
    errs = []
    voice_files()
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            if LAPTOP:
                await local_run(b, 1366, 640, False, errs)
                await local_run(b, 1536, 730, False, errs)
                await local_run(b, 1920, 950, False, errs)
                await b.close()
                check('no page errors, console errors or failed requests', not errs, errs[:6])
                print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
                sys.exit(1 if fails else 0)
            if not VOICE_ONLY:
                await local_run(b, 390, 844, not QUICK, errs)
                await local_run(b, 360, 740, False, errs)
            await fallback_run(b, 390, 844, errs)
            await voice_run(b, 390, 844, errs)
            if VOICE_ONLY:
                pass
            elif have_mock:
                await class_run(b, 390, 844, errs)
            else:
                check('mock backend available for class mode', False, MOCK)
            await b.close()
    finally:
        for pr in procs: pr.terminate()
    check('no page errors, console errors or failed requests', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
