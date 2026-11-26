#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The welcome film (js/intro.js, css/ds-intro.css, assets/al/intro/), behind the design flag.

    python3 tests/intro.py

Flag off: index.html requests none of it. Flag on, first open (forced with ?intro=1, since an automated browser does not
get it otherwise): the poster with "watch" and "skip" (both 48 px or more), the film is not requested before a tap and
nothing plays by itself; a tap requests the film and plays it with sound, the narration's captions show as live text;
"skip" closes it and stores wi_intro=1, and the next open shows nothing and requests nothing; Escape closes it too.
No page error and no Content-Security-Policy violation. The film is H.264 + AAC at 44.1 or 48 kHz, under 9.5 MB, listed with its sha256."""
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
    film = re.search(r"FILM='([^']+)'", js).group(1); poster = re.search(r"LOGO='([^']+)'", js).group(1)
    light = re.search(r"FILM_LIGHT='([^']+)'", js).group(1)
    rows = {}
    for ln in open(os.path.join(ROOT, 'assets', 'al', 'sources.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) > 5:
            rows['assets/' + c[1]] = c
    ok = True; info = {}
    for f in (film, light, poster):
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or rows.get(f, [None] * 6)[5] != hashlib.sha256(open(p, 'rb').read()).hexdigest():
            ok = False; info[f] = 'missing or not listed with its sha256'
    check('the film, its light version and the logo exist and are listed in sources.tsv with their sha256', ok, info)
    size = os.path.getsize(os.path.join(ROOT, film))
    try:
        pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,channels,sample_rate,width:format=duration', '-of', 'json', os.path.join(ROOT, film)], capture_output=True, text=True).stdout)
        st = {s['codec_name']: s for s in pr['streams']}
        fmt_ok = 'h264' in st and st.get('aac', {}).get('channels') in (1, 2) and st.get('aac', {}).get('sample_rate') in ('44100', '48000') and st['h264'].get('width', 0) <= 560 and float(pr['format']['duration']) <= 40
    except Exception as e:
        fmt_ok = False; st = str(e)
    check('the film is H.264 at most 560 px wide with AAC at 44.1 or 48 kHz (a 96 kHz track crackled on phones, LESSONS 13), at most 40 s and under 9.5 MB', fmt_ok and size < 9.5 * 1024 * 1024, [size, list(st)])
    ls = os.path.getsize(os.path.join(ROOT, light))
    check('the light version is under 3.5 MB', ls < 3.5 * 1024 * 1024, ls)
    return film


SOUND = """(()=>{window.__snd=[];const open=()=>document.documentElement.classList.contains('wi-intro-open');
 // every kind of source node that has its own start() (a decoded clip's AudioBufferSourceNode does), and the shared one
 for(const C of [AudioScheduledSourceNode,AudioBufferSourceNode,OscillatorNode,ConstantSourceNode])if(Object.prototype.hasOwnProperty.call(C.prototype,'start')){const S0=C.prototype.start;C.prototype.start=function(...a){__snd.push({k:this.constructor.name,open:open()});return S0.apply(this,a)}}
 const P0=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){const u=String(this.currentSrc||this.src||'');__snd.push({k:'media',silent:u.startsWith('data:')||u.startsWith('blob:'),film:this.classList.contains('wi-intro__film'),open:open()});return P0.call(this)};
 if(window.speechSynthesis){const s0=speechSynthesis.speak.bind(speechSynthesis);speechSynthesis.speak=u=>{__snd.push({k:'speech',silent:!u.volume,open:open()});return s0(u)}}})()"""
# taken the moment the page's body gets its first element (the game's own markup, while the page is still being read,
# before any module runs): what the child would see at the first paint
COVER = """(()=>{const look=f=>{const h=document.documentElement;
 window.__cover={pending:h.classList.contains('wi-intro-pending'),open:h.classList.contains('wi-intro-open'),vis:getComputedStyle(f).visibility,bg:getComputedStyle(h).backgroundColor,style:!!document.getElementById('wi-intro-cover')}};
 const mo=new MutationObserver(()=>{const f=document.body&&document.body.firstElementChild;if(f){mo.disconnect();look(f)}});
 mo.observe(document,{childList:true,subtree:true})})()"""


def sounding(log, while_open):
    """what made a sound: an oscillator or a decoded clip started, a media element played (not the film, not the silent
    unlock clip), the browser voice spoke (not the silent unlock)"""
    return [x for x in log if x['open'] == while_open and not x.get('film') and not x.get('silent')]


async def opening(page, base):
    """the opening flow of docs/INTRO.md, and the game's sound held while the film is open"""
    # flag off: dsflag.js does nothing at all (no class, no cover style), also with ?intro=1
    ctx, pg, seen, errs = await page()
    await pg.add_init_script(COVER); await pg.goto(base + '?intro=1'); await pg.wait_for_timeout(600)
    cv = await pg.evaluate('window.__cover')
    check('flag off: no cover, no hold, no style (dsflag.js does nothing)', cv and not cv['pending'] and not cv['open'] and not cv['style'] and cv['vis'] != 'hidden', cv)
    await ctx.close()
    # a device that has seen it: no splash, no cover
    ctx, pg, seen, errs = await page()
    await pg.add_init_script("localStorage.setItem('wi_ds','1');localStorage.setItem('wi_intro','1');Object.defineProperty(navigator,'webdriver',{get:()=>false})"); await pg.add_init_script(COVER)
    await pg.goto(base); await pg.wait_for_timeout(900)
    cv = await pg.evaluate('window.__cover')
    check('a device that has seen the film: no splash, no cover, nothing of it requested', cv and not cv['pending'] and not cv['style'] and await pg.locator('#wi-intro').count() == 0 and not seen, [cv, seen[:2]])
    await ctx.close()
    # first open: navy from the first paint, the game laid out but hidden; never the title before the logo
    ctx, pg, seen, errs = await page()
    await pg.add_init_script(COVER); await pg.add_init_script(SOUND)
    await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro')
    cv = await pg.evaluate('window.__cover')
    check('first open: navy from the first paint, the game hidden (laid out) under it, the sound held', cv['pending'] and cv['open'] and cv['vis'] == 'hidden' and cv['bg'] == 'rgb(5, 14, 34)', cv)
    check('the overlay took over the cover (no pending class once it is in the page)', not await pg.evaluate("document.documentElement.classList.contains('wi-intro-pending')"))
    # every way sound could start under it: taps anywhere (the game's audio unlock), a key, the film's own tap, the tab hidden and back
    await pg.mouse.click(30, 700); await pg.keyboard.press('Shift'); await pg.wait_for_timeout(900)
    await pg.locator('#wi-intro .wi-intro__play').tap(); await pg.wait_for_timeout(1500)
    for hid in (True, False):
        await pg.evaluate(f"Object.defineProperty(document,'hidden',{{configurable:true,get:()=>{str(hid).lower()}}});Object.defineProperty(document,'visibilityState',{{configurable:true,get:()=>'{'hidden' if hid else 'visible'}'}});document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(300)
    await pg.mouse.click(200, 500); await pg.wait_for_timeout(800)
    # an effect the game plays without a tap (a star, the unlock fanfare a moment after a result)
    await pg.evaluate("void import('./js/audio.js').then(a=>{a.SND.tap();a.SND.star(0);a.SND.win();a.SND.unlock();a.SND.pop()})"); await pg.wait_for_timeout(500)
    log = await pg.evaluate('__snd')
    check('while the film is open no game sound starts: no music, no effect, no clip, no voice (taps, a key, the tab hidden and back, effects asked for)', not sounding(log, True), sounding(log, True)[:5])
    check('the film itself did play', any(x.get('film') for x in log), log[:4])
    await pg.locator('#wi-intro .wi-intro__skip').tap(); await pg.wait_for_timeout(1500)
    log = await pg.evaluate('__snd')
    check('once it closes, the game\'s music starts as it would have', any(x['k'] == 'OscillatorNode' and not x['open'] for x in log), [x['k'] for x in sounding(log, False)][:5])
    fade = await pg.evaluate("({gone:!document.getElementById('wi-intro'),cls:document.documentElement.className,focus:!!document.activeElement&&!!document.activeElement.closest('#view')})")
    check('it faded onto the first screen: the overlay gone, no cover class left, the focus on the first screen', fade['gone'] and 'wi-intro' not in fade['cls'] and fade['focus'], fade)
    await ctx.close()
    # the music off in the settings: still off after the film
    ctx, pg, seen, errs = await page()
    await pg.add_init_script("localStorage.setItem('word-islands-settings-v1',JSON.stringify({music:false,sfx:true}))"); await pg.add_init_script(SOUND)
    await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.mouse.click(30, 700); await pg.wait_for_timeout(500)
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(1500)
    check('with the music turned off in the settings, it stays off after the film', not [x for x in await pg.evaluate('__snd') if x['k'] == 'OscillatorNode'])
    await ctx.close()
    # the film offered over a level (a link to #play): what the game says behind it (its voice, js/state.js say) waits
    # for the film to close, then plays
    ctx, pg, seen, errs = await page()
    await pg.add_init_script(SOUND)
    await pg.goto(base + '?ds=1&intro=1#play/1/listen'); await pg.wait_for_selector('#wi-intro'); await pg.mouse.click(30, 700); await pg.wait_for_timeout(1500)
    await pg.evaluate("window.__said=null;void import('./js/state.js').then(m=>m.say('hobby')).then(v=>{window.__said=v})"); await pg.wait_for_timeout(3000)
    log = await pg.evaluate('__snd')
    check('what the game says behind the film (a level\'s word) is held while it is open', not sounding(log, True) and await pg.evaluate('window.__said') is None, sounding(log, True)[:5])
    await ctx.close()
    # on the title (nothing behind that speaks on its own): a word asked for while the film is open is said once it closes
    ctx, pg, seen, errs = await page()
    await pg.add_init_script(SOUND)
    await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.mouse.click(30, 700); await pg.wait_for_timeout(1000)
    await pg.evaluate("window.__said=null;void import('./js/state.js').then(m=>m.say('hobby')).then(v=>{window.__said=v})"); await pg.wait_for_timeout(1500)
    check('the word waits while the film is open', await pg.evaluate('window.__said') is None and not sounding(await pg.evaluate('__snd'), True))
    await pg.locator('#wi-intro .wi-intro__skip').click(); await pg.wait_for_timeout(5000)
    log = await pg.evaluate('__snd')
    check('after the film closes, the held word is said', any(x['k'] in ('AudioBufferSourceNode', 'media', 'speech') and not x['open'] and not x.get('silent') for x in log) and await pg.evaluate('window.__said') is True, [x for x in log if not x['open'] and x['k'] != 'OscillatorNode'][:6])
    await ctx.close()
    # the film cannot load: "מתחילים" at once with a line, and the device does not remember it (offered again)
    ctx, pg, seen, errs = await page()
    await pg.route('**/*.mp4', lambda r: r.abort())
    await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.wait_for_timeout(900)
    await pg.locator('#wi-intro .wi-intro__play').tap(); await pg.wait_for_selector('#wi-intro .wi-intro__done:not([hidden])', timeout=12000)
    fl = await pg.evaluate("document.querySelector('#wi-intro .wi-intro__fail').hidden?'':document.querySelector('#wi-intro .wi-intro__fail').textContent")
    check('a film that cannot load: "מתחילים" with "הסרטון לא נטען. אפשר לראות אותו אחר כך בהגדרות."', fl == 'הסרטון לא נטען. אפשר לראות אותו אחר כך בהגדרות.', fl)
    await pg.locator('#wi-intro .wi-intro__done').tap(); await pg.wait_for_timeout(700)
    check('and the device does not remember it, so it is offered again', await pg.evaluate("localStorage.getItem('wi_intro')") is None and await pg.locator('#wi-intro').count() == 0)
    await ctx.close()
    # reduced motion: fades only
    ctx, pg, seen, errs = await page()
    await pg.emulate_media(reduced_motion='reduce'); await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro')
    an = await pg.evaluate("[getComputedStyle(document.querySelector('.wi-intro__logo')).animationName,getComputedStyle(document.querySelector('.wi-intro__play')).animationName]")
    check('reduced motion: the logo and the button fade in, no pop and no rise', an == ['wi-in-fade', 'wi-in-fade'], an)
    await ctx.close()
    # the smallest phones: the logo and both buttons inside the screen with 16 px gutters
    for w, h in ((360, 740), (320, 568)):
        ctx, pg, seen, errs = await page()
        await pg.set_viewport_size({'width': w, 'height': h}); await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.wait_for_timeout(1300)
        r = await pg.evaluate("['.wi-intro__logo','.wi-intro__play','.wi-intro__snd','.wi-intro__skip'].map(s=>{const b=document.querySelector(s).getBoundingClientRect();return [s,Math.round(b.left),Math.round(b.right),Math.round(b.top),Math.round(b.bottom)]})")
        check(f'{w}x{h}: the logo, the button, "עם קול" and "דלגו" inside the screen with 16 px gutters', all(l >= 12 and rt <= w - 12 and t >= 0 and bt <= h for _, l, rt, t, bt in r), r)
        await ctx.close()


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
            await pg.add_init_script("Object.defineProperty(navigator,'connection',{get:()=>undefined})")
            await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro', timeout=5000); await pg.wait_for_timeout(600)
            await pg.wait_for_timeout(900)   # the logo pops in, then the button rises
            sz = await pg.evaluate("[...document.querySelectorAll('#wi-intro button')].filter(b=>!b.hidden).map(b=>{const r=b.getBoundingClientRect();return [b.textContent,Math.round(r.width),Math.round(r.height)]})")
            check('first open: the logo, "▶ צפייה בסרטון" (60 px high) and "דלגו", 48 px or more', len(sz) == 2 and all(w >= 48 and h >= 48 for _, w, h in sz) and any('צפייה בסרטון' in t and h >= 60 for t, w, h in sz), sz)
            lg = await pg.evaluate("(()=>{const i=document.querySelector('#wi-intro .wi-intro__logo');return {alt:i.alt,ok:i.complete&&i.naturalWidth>0,snd:document.querySelector('#wi-intro .wi-intro__snd').textContent,focus:document.activeElement&&document.activeElement.textContent}})()")
            check('the logo "ניצני אופק" is there, "עם קול" under the button, and the button has the focus', lg['alt'] == 'ניצני אופק' and lg['ok'] and 'עם קול' in lg['snd'] and 'צפייה בסרטון' in (lg['focus'] or ''), lg)
            st = await pg.evaluate("(()=>{const v=document.querySelector('#wi-intro video');return {paused:v.paused,src:v.currentSrc||v.getAttribute('src')||''}})()")
            check('nothing plays by itself and the film is not requested before a tap', st['paused'] and not st['src'] and not [u for u in seen if '.mp4' in u], [st, seen])
            await pg.locator('#wi-intro .wi-intro__play').tap(); await pg.wait_for_timeout(1800)
            st = await pg.evaluate("(()=>{const v=document.querySelector('#wi-intro video');const c=document.querySelector('#wi-intro .wi-intro__cap');return {t:v.currentTime,muted:v.muted,cap:c.hidden?'':c.textContent}})()")
            check('a tap requests the film and plays it with sound', [u for u in seen if '.mp4' in u] and st['t'] > 0.5 and not st['muted'], st)
            mp4 = [u for u in seen if '.mp4' in u]
            check('a browser that does not report its link (Safari, iPhones) gets the light film', mp4 and all('intro-light' in u for u in mp4), mp4)
            check('while the film is open the rest of the page is inert', await pg.evaluate("[...document.body.children].filter(n=>n.id!=='wi-intro').every(n=>n.inert)"))
            check('"skip" stays on screen while the film plays', await pg.locator('#wi-intro .wi-intro__skip').is_visible())
            check('the narration shows as a live caption', st['cap'].startswith('הצלצול'), st['cap'])
            await pg.evaluate("(()=>{const v=document.querySelector('#wi-intro video');Object.defineProperty(v,'currentTime',{configurable:true,get:()=>24});v.dispatchEvent(new Event('timeupdate'))})()"); await pg.wait_for_timeout(200)  # the test server cannot seek (no range requests): the player is told it is at 24 s
            ln = await pg.evaluate("[...document.querySelectorAll('#wi-intro .wi-intro__line')].map(l=>[l.textContent.slice(0,6),getComputedStyle(l).direction])")
            check('a mixed caption: the English line is LTR and the Hebrew line RTL, each on its own', len(ln) == 2 and ln[0][1] == 'ltr' and ln[1][1] == 'rtl' and ln[1][0].startswith('היי'), ln)
            await pg.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(200)
            st = await pg.evaluate("(()=>{const v=document.querySelector('#wi-intro video'),b=document.querySelector('#wi-intro .wi-intro__play');return {paused:v.paused,play:getComputedStyle(b).opacity>0&&document.querySelector('#wi-intro').dataset.s==='pause'}})()")
            check('a hidden tab pauses the film, and "watch" comes back to go on', st['paused'] and st['play'], st)
            await pg.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(200)
            check('coming back does not start the sound by itself', await pg.evaluate("document.querySelector('#wi-intro video').paused"))
            await pg.locator('#wi-intro .wi-intro__skip').tap(); await pg.wait_for_timeout(700)
            gone = await pg.locator('#wi-intro').count() == 0
            stored = await pg.evaluate("localStorage.getItem('wi_intro')")
            check('"skip" closes it and this device remembers it', gone and stored == '1', [gone, stored])
            check('after closing nothing on the page is inert', await pg.evaluate("![...document.querySelectorAll('[inert]')].length"))
            n0 = len(seen)
            await pg.goto(base + '?ds=1'); await pg.wait_for_timeout(900)
            check('the next open shows nothing and requests nothing of it', await pg.locator('#wi-intro').count() == 0 and len(seen) == n0, seen[n0:])
            check('no page error and no CSP violation', not errs, errs[:3])
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(700)
            check('Escape closes it', await pg.locator('#wi-intro').count() == 0)
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.add_init_script("Object.defineProperty(navigator,'connection',{get:()=>({saveData:false,effectiveType:'4g'})})")
            await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.locator('#wi-intro .wi-intro__play').tap(); await pg.wait_for_timeout(900)
            mp4 = [u for u in seen if '.mp4' in u]
            check('on a fast link (4G, no data saving) the tap loads the full film', mp4 and all('/intro.hf_' in u for u in mp4), mp4)
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.add_init_script("Object.defineProperty(navigator,'connection',{get:()=>({saveData:false,effectiveType:'3g'})})")
            await pg.goto(base + '?ds=1&intro=1'); await pg.wait_for_selector('#wi-intro'); await pg.locator('#wi-intro .wi-intro__play').tap(); await pg.wait_for_timeout(900)
            mp4 = [u for u in seen if '.mp4' in u]
            check('on a slow (3G) or saved-data connection the tap loads the light film only', mp4 and all('intro-light' in u for u in mp4), mp4)
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
            await pg.goto(base + '?ds=1'); await pg.wait_for_selector('#wi-intro', timeout=5000)
            check('the plain first open (a real browser, no ?intro=1) shows the opening once', await pg.locator('#wi-intro .wi-intro__play').count() == 1)
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(700)
            await pg.goto(base + '?ds=1'); await pg.wait_for_timeout(900)
            check('and not again on the next open', await pg.locator('#wi-intro').count() == 0)
            await ctx.close()

            ctx, pg, seen, errs = await page()
            await pg.goto(base + '?ds=1'); await pg.wait_for_timeout(900)
            check('an automated browser without ?intro=1 does not get it (so the other suites run as before)', await pg.locator('#wi-intro').count() == 0 and not seen, seen[:2])
            await ctx.close()
            await opening(page, base)
            await b.close()
    finally:
        srv.terminate()


film = files_check()
asyncio.run(run(film))
print(f'{len(fails)} FAILED: ' + '; '.join(fails) if fails else 'ALL PASSED')
sys.exit(1 if fails else 0)
