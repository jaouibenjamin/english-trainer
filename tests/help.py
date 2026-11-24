#!/usr/bin/env python3
"""Word help and the slowly button (js/help.js), which only exist on a device that was given them (?help=1).

    python3 tests/help.py              # 390x844 and a laptop window
    python3 tests/help.py --quick      # 390x844 only
    python3 tests/help.py --shots DIR  # also save a PNG of every screen

Checks: without the switch nothing of it is drawn or stored; with it, a tap on an English word shows the meaning that is
in the game's data (and only that), by touch and by keyboard, never over something to press and never for the answer;
"the sentence in Hebrew" shows only a translation the data holds; the turtle says the same recorded clip slowly through
Web Audio and through the <audio> element, never with the browser voice; help costs no points, ends nothing, is noted
on the device only and is not part of what is saved to the class."""
import asyncio, json, os, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, shot, new_page, port_open, fails, lv

QUICK = '--quick' in sys.argv
ON = P.BASE + '?help=1'
SAVE_KEY, HELP_KEY = 'aam-unit1-v1', 'wi-help-v1'
ITEM = "(()=>{const L=window.__lv;if(!L||!L.items)return null;const it=L.items[L.i()];return it?{k:it.k,type:it.type,a:it.a,o:it.o,tiles:it.tiles,sent:it.sent||'',i:L.i()}:null})()"
# the bubble: its text, whether it lies over anything a pupil must press, and whether it is inside the stage
BUB = """(()=>{const b=document.getElementById('hbub');if(!b||b.hidden)return null;const r=b.getBoundingClientRect(),S=document.getElementById('stage').getBoundingClientRect();
 const over=[...document.querySelectorAll('.xo,.xtile,.xans,#xi,[data-a=mockcheck],.pl,.bottle,.bub,.btn:not(.hslow)')].filter(k=>{const q=k.getBoundingClientRect();return q.width&&r.left<q.right-1&&r.right>q.left+1&&r.top<q.bottom-1&&r.bottom>q.top+1}).length;
 const txt=[...document.querySelectorAll('.xqt,.xsent,.xraw,.xdesc,.xbigw,.slot')].filter(k=>{const q=k.getBoundingClientRect();return q.width&&r.left<q.right-1&&r.right>q.left+1&&r.top<q.bottom-1&&r.bottom>q.top+1}).length;
 return {text:b.textContent,over,txt,inside:r.left>=S.left-1&&r.right<=S.right+1&&r.top>=S.top-1&&r.bottom<=S.bottom+1,tags:[...b.querySelectorAll('*')].map(e=>e.tagName).join(','),html:b.innerHTML.length}})()"""
MEANING = "(async t=>{const m=(await import('/js/help.js')).meaning(t);return m&&m.he})"
HELPLOG = f"JSON.parse(localStorage.getItem('{HELP_KEY}')||'null')"
PTS = f"(JSON.parse(localStorage.getItem('{SAVE_KEY}'))||{{}}).pts||0"
# the <audio> element's play() is a stand-in in these tests (tests/play.py); this remembers the pace it was asked to play at
RATES = "(()=>{window.__rates=[];const P=HTMLMediaElement.prototype,p=P.play;P.play=function(){window.__rates.push({src:this.getAttribute('src')||'',rate:this.playbackRate,keep:this.preservesPitch!==false});return p.apply(this,arguments)}})()"


async def answer_right(pg, it):
    if it['type'] in ('choice', 'who', 'read'):
        await pg.click(f".xo[data-j=\"{it['o'].index(it['a'])}\"]")
    elif it['type'] == 'order':
        for w in sorted(it['tiles'], key=lambda w: it['a'].index(w)):
            await pg.locator('.xtiles .xtile', has_text=w).first.click()
        await pg.click('[data-a=mockcheck]')
    else:
        await pg.fill('#xi', it['a']); await pg.click('[data-a=mockcheck]')


async def off(b, w, h, errs):
    """without the switch: nothing new on any screen, nothing new stored"""
    t = f'off {w}x{h}'
    c, pg = await new_page(b, w, h, errs=errs)
    seen = {}
    await pg.goto(P.BASE + '#settings'); await pg.wait_for_selector('.setrow'); seen['toggles'] = await pg.locator('.setrow[role=switch]').count()
    await pg.goto(P.BASE + '#play/1/listen'); await lv(pg, 'listen'); await pg.wait_for_timeout(600); seen['listen'] = await pg.locator('.hw,.hsb,.hslow,#hbub').count()
    await pg.goto(P.BASE + '#play/1/read'); await lv(pg, 'read'); await pg.wait_for_timeout(300); seen['read'] = await pg.locator('.hw,.hsb,.hslow,#hbub').count()
    await pg.click('.read .t'); await pg.wait_for_timeout(200)
    await pg.goto(P.BASE + '#play/1/bridge'); await lv(pg, 'bridge'); await pg.wait_for_timeout(600); seen['bridge'] = await pg.locator('.hw,.hsb,.hslow,#hbub').count()
    await pg.goto(P.BASE + '#mockprac/grammar'); await pg.wait_for_selector('[data-a=mocknext]'); await pg.click('[data-a=mocknext]'); await pg.wait_for_selector('.xq'); seen['mock'] = await pg.locator('.hw,.hsb,.hslow,#hbub,[data-hk]').count()
    st = await pg.evaluate(f"({{all:Object.keys(localStorage).map(k=>k+'='+localStorage.getItem(k)).join(' '),keys:Object.keys(localStorage),log:localStorage.getItem('{HELP_KEY}')}})")
    check(f'[{t}] without the switch the settings have their three switches and no screen draws a help word, a sentence button, a turtle or a bubble', seen == {'toggles': 3, 'listen': 0, 'read': 0, 'bridge': 0, 'mock': 0}, seen)
    check(f'[{t}] without the switch nothing about help is stored on the device', st['log'] is None and 'help' not in st['all'], st['keys'])
    await c.close()


async def on(b, w, h, errs):
    t = f'on {w}x{h}'
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.add_init_script(RATES)
    # ---- the switch
    await pg.goto(ON + '#settings'); await pg.wait_for_selector('.setrow')
    check(f'[{t}] ?help=1 gives the device a fourth switch in the settings, turned on', await pg.locator('.setrow[role=switch]').count() == 4 and await pg.locator('.setrow[data-k=help][aria-checked=true]').count() == 1)
    box = await pg.locator('.setrow[data-k=help]').bounding_box()
    check(f'[{t}] the new switch is a full row, at least 44 px high, inside the screen', box and box['height'] >= 44 and box['x'] >= 0 and box['x'] + box['width'] <= w + 1, box)
    await shot(pg, f'help_{w}x{h}_01_settings')
    await pg.click('.setrow[data-k=help]'); await pg.wait_for_timeout(150)
    await pg.goto(P.BASE + '#play/1/read'); await lv(pg, 'read'); await pg.wait_for_timeout(200)
    check(f'[{t}] switched off in the settings: the turtle is gone again, and the switch stays in the settings', await pg.locator('.hslow').count() == 0)
    await pg.goto(P.BASE + '#settings'); await pg.wait_for_selector('.setrow[data-k=help][aria-checked=false]'); await pg.click('.setrow[data-k=help]'); await pg.wait_for_selector('.setrow[data-k=help][aria-checked=true]')

    # ---- listening: the turtle
    await pg.goto(P.BASE + '#play/1/listen'); await lv(pg, 'listen'); await pg.wait_for_function("__lv.g.said>0", timeout=6000); await pg.wait_for_timeout(500)
    sb = await pg.locator('#slw').bounding_box(); bubs = await pg.evaluate("[...document.querySelectorAll('.bub')].map(b=>{const r=b.getBoundingClientRect();return [r.top,r.bottom]})")
    check(f'[{t}] listening: the turtle hangs under the sign, at least 44 px, and no bubble lies under it', sb and sb['height'] >= 44 and sb['width'] >= 44 and all(top >= sb['y'] + sb['height'] - 1 for top, _ in bubs), [sb, bubs])
    await shot(pg, f'help_{w}x{h}_02_listen')
    pts0 = await pg.evaluate("(async()=>(await import('/js/state.js')).S.pts)()")
    R = await pg.evaluate("""(async()=>{const n=__plays.length,sp=__spoken.length,w=__lv.answer(),norm=__plays[n-1];document.querySelector('#slw').click();
      for(let i=0;i<200&&__plays.length===n;i++)await new Promise(r=>setTimeout(r,10));const p=__plays[__plays.length-1];
      return {more:__plays.length-n,via:p.via,url:p.url,same:p.url===norm.url,ratio:p.dur/norm.dur,spoken:__spoken.length-sp,word:w,i:__lv.g.i,miss:__lv.g.miss,lock:__lv.g.lock}})()""")
    check(f'[{t}] listening: the turtle plays the same recorded clip through Web Audio at three quarters of the pace (1.33 times as long), and the browser voice says nothing',
          R['more'] == 1 and R['via'] == 'buf' and R['same'] and 1.28 < R['ratio'] < 1.38 and R['spoken'] == 0, R)
    pts1 = await pg.evaluate("(async()=>(await import('/js/state.js')).S.pts)()")
    log = await pg.evaluate(HELPLOG)
    check(f'[{t}] listening: hearing it slowly costs nothing and ends nothing (same points, same word, no miss), and is noted on the device', pts1 == pts0 and R['i'] == 0 and R['miss'] == 0 and not R['lock'] and (log or {}).get('items', {}).get('listen:' + R['word'], {}).get('slow') == 1, [pts0, pts1, log])
    await c.close()

    # ---- the <audio> fallback (fetch of clips fails): the element is asked for the slow pace, with the pitch kept
    c, pg = await new_page(b, w, h, errs=errs, clips='nofetch')
    await pg.add_init_script(RATES)
    await pg.goto(ON + '#play/1/listen'); await lv(pg, 'listen'); await pg.wait_for_function("__plays.some(p=>p.via==='el')", timeout=9000); await pg.wait_for_timeout(400)
    R = await pg.evaluate("""(async()=>{const n=__rates.length;document.querySelector('#slw').click();for(let i=0;i<400&&__rates.length===n;i++)await new Promise(r=>setTimeout(r,10));
      const slow=__rates[__rates.length-1];await new Promise(r=>setTimeout(r,400));const m=__rates.length;document.querySelector('[data-a=again]').click();for(let i=0;i<400&&__rates.length===m;i++)await new Promise(r=>setTimeout(r,10));
      return {slow,after:__rates[__rates.length-1],first:__rates.filter(r=>/assets\\/voice/.test(r.src))[0]}})()""")
    check(f'[{t}] without Web Audio the <audio> element plays the clip at 0.75 with its pitch kept, and the next normal replay is back at full pace',
          R['slow'] and '/voice/en/' in R['slow']['src'] and abs(R['slow']['rate'] - .75) < .001 and R['slow']['keep'] and R['after']['rate'] == 1 and R['first']['rate'] == 1, R)
    await c.close()

    c, pg = await new_page(b, w, h, errs=errs)
    await pg.goto(ON + '#play/1/read'); await lv(pg, 'read'); await pg.wait_for_timeout(300)
    # ---- reading: the turtle reads the story slowly; the story's own word meanings are noted
    row = await pg.evaluate("[...document.querySelectorAll('.read .row .btn')].map(b=>{const r=b.getBoundingClientRect();return [Math.round(r.left),Math.round(r.right),Math.round(r.height)]})")
    check(f'[{t}] reading: the row holds "read to me", the turtle and "to the questions" side by side, all inside the screen and at least 44 px high', len(row) == 3 and all(l >= 0 and r <= w and hh >= 44 for l, r, hh in row) and all(row[i][1] <= row[i + 1][0] + 1 or row[i + 1][1] <= row[i][0] + 1 for i in range(2)), row)
    await shot(pg, f'help_{w}x{h}_03_read')
    R = await pg.evaluate("""(async()=>{const n=__plays.length,sp=__spoken.length;document.querySelector('[data-a=readslow]').click();for(let i=0;i<300&&__plays.length<n+2;i++)await new Promise(r=>setTimeout(r,10));
      const v=await import('/js/voice.js'),ps=__plays.slice(n),full=[];for(const p of ps){const ab=await (await fetch(p.url)).arrayBuffer(),d=(await new OfflineAudioContext(1,1,24000).decodeAudioData(ab)).duration;full.push((Math.min(d,p.e+.08)-Math.max(0,p.s-.03)))}
      return {n:ps.length,via:ps.map(p=>p.via),ratio:ps.map((p,i)=>p.dur/full[i]),spoken:__spoken.slice(sp).filter(x=>String(x).trim()).length}})()""")
    check(f'[{t}] reading: the turtle reads the title and the sentences one after another from the recorded clips, each 1.33 times as long', R['n'] >= 2 and all(v == 'buf' for v in R['via']) and all(1.28 < x < 1.38 for x in R['ratio']) and R['spoken'] == 0, R)
    await pg.evaluate("(async()=>(await import('/js/state.js')).hush())()")
    await pg.click('.read .t.v'); await pg.wait_for_timeout(200)
    log = await pg.evaluate(HELPLOG)
    check(f'[{t}] reading: a word looked up in the story is noted on the device under the story', bool((log or {}).get('items', {}).get('read:1', {}).get('w')), log)

    # ---- the bridge: the words of the am / is / are sentence
    await pg.goto(P.BASE + '#play/1/bridge'); await lv(pg, 'bridge'); await pg.wait_for_timeout(700)
    for _ in range(14):
        if await pg.evaluate("__lv.g.r&&__lv.g.r.kind") == 'tobe' and not await pg.evaluate("__lv.g.lock"): break
        nx = await pg.evaluate("__lv.g.lock?null:__lv.next()")
        if nx: await pg.evaluate("t=>{const e=[...document.querySelectorAll('.pl:not(.used)')].find(x=>x.dataset.t===t);e&&e.click()}", nx)
        await pg.wait_for_timeout(450)
    await pg.wait_for_function("__lv.g.r&&__lv.g.r.kind==='tobe'&&!__lv.g.lock", timeout=8000); await pg.wait_for_timeout(900)
    n_hw = await pg.locator('.bridge #span .hw').count(); n_bank = await pg.locator('.bridge .bank .hw').count()
    check(f'[{t}] bridge: the words of the sentence can be tapped; the three answer planks cannot', n_hw >= 1 and n_bank == 0 and await pg.locator('.bank .pl').count() == 3, [n_hw, n_bank])
    pts0 = await pg.evaluate("(async()=>(await import('/js/state.js')).S.pts)()"); g0 = await pg.evaluate("[__lv.g.i,__lv.g.miss,__lv.g.bad]")
    word = await pg.locator('.bridge #span .hw').first.get_attribute('data-hw')
    await pg.locator('.bridge #span .hw').first.click(); await pg.wait_for_timeout(200)
    B = await pg.evaluate(BUB); want = await pg.evaluate(MEANING, word)
    check(f'[{t}] bridge: the bubble shows the word and exactly the meaning the data holds, inside the screen, over nothing a pupil must press', B and B['text'] == f'{word} = {want}' and B['over'] == 0 and B['txt'] == 0 and B['inside'], [B, want])
    check(f'[{t}] the bubble is built from text only (a word, an equals sign, the meaning: no other markup)', B and B['tags'] == 'BDI,SPAN,SPAN', B)
    await shot(pg, f'help_{w}x{h}_04_bridge_bubble')
    await pg.locator('.bridge #span .hw').first.click(); await pg.wait_for_timeout(120)
    closed1 = await pg.evaluate(BUB) is None
    await pg.locator('.bridge #span .hw').first.focus(); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
    opened = await pg.evaluate(BUB); exp = await pg.locator('.bridge #span .hw').first.get_attribute('aria-expanded')
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(120)
    closed2 = await pg.evaluate(BUB) is None; role = await pg.evaluate("[document.getElementById('hbub').getAttribute('role'),document.getElementById('hbub').getAttribute('aria-live'),document.querySelector('.bridge #span .hw').tagName]")
    check(f'[{t}] the same word again closes the bubble; the keyboard opens it (Enter on the focused word) and Escape closes it', closed1 and opened and exp == 'true' and closed2, [closed1, opened, exp, closed2])
    check(f'[{t}] a help word is a real button and the bubble is announced to a screen reader (role=status, polite)', role == ['status', 'polite', 'BUTTON'], role)
    await pg.locator('.bridge #span .hw').first.click(); await pg.wait_for_timeout(120); await pg.mouse.click(5, h - 5); await pg.wait_for_timeout(120)
    check(f'[{t}] a tap anywhere else closes the bubble', await pg.evaluate(BUB) is None)
    pts1 = await pg.evaluate("(async()=>(await import('/js/state.js')).S.pts)()"); g1 = await pg.evaluate("[__lv.g.i,__lv.g.miss,__lv.g.bad]")
    check(f'[{t}] bridge: looking up words costs no points and counts as no mistake', pts1 == pts0 and g1 == g0, [pts0, pts1, g0, g1])
    gap = await pg.evaluate("__lv.g.r.gap")
    await pg.click(f'.bank .pl[data-t="{gap}"]'); await pg.wait_for_function("__lv.g.lock||__lv.g.r.kind!=='tobe'||__lv.g.i>0", timeout=5000)
    check(f'[{t}] bridge: after the help the right plank is still a first-time answer', await pg.evaluate("__lv.g.bad") == g0[2])

    # ---- the mock exam: help in the practice, none in the paper
    await pg.goto(P.BASE + '#mockprac/grammar'); await pg.wait_for_selector('[data-a=mocknext]'); await pg.click('[data-a=mocknext]'); await pg.wait_for_selector('.xq')
    seen = {'hw': 0, 'hsb': 0, 'answers': 0, 'bubble': 0, 'sent': 0}; shown = False; problems = []
    for _ in range(40):
        it = await pg.evaluate(ITEM)
        if not it: break
        await pg.wait_for_selector('.xq'); await pg.wait_for_timeout(150)
        hk = await pg.locator('div.xq').get_attribute('data-hk')
        if hk != 'mock:' + it['k']: problems.append(('key', hk, it['k']))
        seen['answers'] += await pg.locator('.xo .hw,.xtile .hw,.xopts .hsb').count()
        hws = await pg.locator('div.xq .hw').all()
        seen['hw'] += len(hws)
        names = [(await x.get_attribute('data-hw')).lower() for x in hws]
        if str(it['a']).lower() in names: problems.append(('answer is a help word', it['k']))
        if hws:
            await hws[0].click(); await pg.wait_for_timeout(150)
            B = await pg.evaluate(BUB); wd = await hws[0].get_attribute('data-hw'); want = await pg.evaluate(MEANING, wd)
            if not B or B['text'] != f'{wd} = {want}' or B['over'] or B['txt'] or not B['inside']: problems.append(('bubble', it['k'], B, want))
            else: seen['bubble'] += 1
            if not shown: await shot(pg, f'help_{w}x{h}_05_mock_word'); shown = True
            await pg.keyboard.press('Escape')
        if await pg.locator('div.xq .hsb').count():
            seen['hsb'] += 1
            await pg.click('div.xq .hsb'); await pg.wait_for_timeout(150)
            B = await pg.evaluate(BUB); full = it['sent'].replace('___', it['a'])
            want = await pg.evaluate("(async s=>(await import('/js/help.js')).sentenceHe(s))", full)
            if not B or not want or B['text'] != want or B['over'] or B['txt'] or not B['inside']: problems.append(('sentence', it['k'], B, want))
            else:
                seen['sent'] += 1
                if seen['sent'] == 1: await shot(pg, f'help_{w}x{h}_06_mock_sentence')
            await pg.keyboard.press('Escape')
        await answer_right(pg, it)
        try:
            await pg.wait_for_function(f"!window.__lv||window.__lv.i()!=={it['i']}||!!document.querySelector('[data-a=mocknext]')", timeout=6000)
        except Exception:
            problems.append(('stuck', it['k'])); break
        if await pg.locator('[data-a=mocknext]').count(): await pg.click('[data-a=mocknext]'); await pg.wait_for_timeout(150)
    check(f'[{t}] mock practice: questions carry help words, every bubble shows the data\'s own meaning and covers neither an answer nor the question, and no answer option or the answer itself is ever a help word',
          seen['hw'] > 5 and seen['bubble'] > 3 and seen['answers'] == 0 and not problems, [seen, problems[:3]])
    check(f'[{t}] mock practice: "the sentence in Hebrew" appeared only where the data holds the sentence, and showed exactly that translation', seen['hsb'] == seen['sent'], seen)
    log = await pg.evaluate(HELPLOG)
    check(f'[{t}] mock practice: each look-up is noted under its question', any(k.startswith('mock:') and v.get('w') for k, v in (log or {}).get('items', {}).items()), list((log or {}).get('items', {}))[:5])
    await pg.goto(P.BASE + '#mockrun'); await pg.wait_for_selector('.xstation,.xq', timeout=8000)
    if await pg.locator('[data-a=mocknext]').count(): await pg.click('[data-a=mocknext]')
    await pg.wait_for_selector('.xq'); n_exam = 0
    for _ in range(6):
        it = await pg.evaluate(ITEM)
        if not it: break
        n_exam += await pg.locator('.hw,.hsb,[data-hk]').count()
        await answer_right(pg, it)
        await pg.wait_for_function(f"!window.__lv||window.__lv.i()!=={it['i']}||!!document.querySelector('[data-a=mocknext]')", timeout=6000)
        if await pg.locator('[data-a=mocknext]').count(): await pg.click('[data-a=mocknext]'); await pg.wait_for_timeout(120)
    check(f'[{t}] the paper itself has no word help, even with the switch on: it is the rehearsal of the real test', n_exam == 0, n_exam)

    # ---- nothing invented, nothing injected, nothing sent
    R = await pg.evaluate("""(async()=>{const h=await import('/js/help.js'),d=await import('/js/data.js');
      const list=new Map(d.WORDS.map(w=>[w.en.toLowerCase(),w.he])),bad=[];
      for(const t of ['goal','a lot of','dining room','forty','Israel','May',"I'm sorry",'twenty-five','hobbies','is','zebra','xylophone','<img src=x onerror=alert(1)>']){const m=h.meaning(t),k=t.toLowerCase();
        const want=list.get(k)||d.GL[k]||null;if((m&&m.he)!==want)bad.push([t,m,want])}
      const el=document.createElement('button');el.className='hw';el.dataset.hw='<img src=x onerror="window.__pwned=1">';document.getElementById('view').appendChild(el);el.click();await new Promise(r=>setTimeout(r,150));
      const b=document.getElementById('hbub');const out={bad,planted:!b.hidden,pwned:!!window.__pwned,markup:h.words('<b>goal</b> & "piano"')};el.remove();return out})()""")
    check(f'[{t}] a meaning is only ever the entry of the teacher\'s word list or of the reading glossary; a word in neither gets none', not R['bad'], R['bad'])
    check(f'[{t}] text is never treated as markup: a planted "word" opens nothing and runs nothing, and sentence text is escaped', not R['planted'] and not R['pwned'] and '<b>' not in R['markup'] and '&lt;b&gt;' in R['markup'], R)
    saved = await pg.evaluate(f"localStorage.getItem('{SAVE_KEY}')||''")
    check(f'[{t}] the progress that is saved to the class holds nothing about help (it is noted next to it, on the device only)', 'help' not in saved and 'slow' not in saved and await pg.evaluate(HELPLOG) is not None, saved[:120])
    await c.close()


async def class_mode(b, w, h, errs):
    """with a class login: what is sent to the backend is the same with the switch on, and never mentions help"""
    api = f'http://127.0.0.1:{P.API_PORT}/'
    c, pg = await new_page(b, w, h, api=api, errs=errs)
    bodies = []
    pg.on('request', lambda r: bodies.append(r.post_data or '') if r.url.startswith(api) else None)
    await pg.goto(ON); await pg.wait_for_selector('#lc', timeout=10000)
    import random
    name = 'עז' + ''.join(random.choice('אבגדהוזחטיכלמנסעפצקרשת') for _ in range(4))      # a made-up name on the mock backend
    await pg.wait_for_timeout(400)      # a device that never signed in starts on "first time"
    await pg.fill('#lc', 'EN-1234'); await pg.fill('#ln', name); await pg.fill('#lp', '2468')
    await pg.click('.lcard .btn'); await pg.wait_for_selector('.title .btn', timeout=10000)
    await pg.goto(P.BASE + '#play/1/read'); await lv(pg, 'read'); await pg.wait_for_timeout(300)
    await pg.click('.read .t.v'); await pg.click('[data-a=readslow]'); await pg.wait_for_timeout(500)
    await pg.evaluate("(async()=>{const m=await import('/js/state.js');m.hush();m.award(1);m.save()})()"); await pg.wait_for_timeout(3600)      # a save goes out 2.5 s after the last change
    saves = [x for x in bodies if '"a":"save"' in x]
    check(f'[class {w}x{h}] with a class login and the switch on, saves still go out and none of them mentions help', len(saves) >= 1 and not any('help' in x or 'slow' in x for x in bodies), [len(bodies), len(saves)])
    await c.close()


async def main():
    procs = []
    have_mock = True
    if not port_open(P.PORT):
        procs.append(subprocess.Popen([sys.executable, '-m', 'http.server', str(P.PORT), '--bind', '127.0.0.1'], cwd=P.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    if not port_open(P.API_PORT):
        procs.append(subprocess.Popen(['node', os.path.join(P.ROOT, 'tests', 'mock.js')], cwd=P.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for _ in range(60):
        if port_open(P.PORT) and port_open(P.API_PORT): break
        time.sleep(.1)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await off(b, 390, 844, errs)
            await on(b, 390, 844, errs)
            await class_mode(b, 390, 844, errs)
            if not QUICK:
                P.LAPTOP = True
                await off(b, 1366, 768, errs)
                await on(b, 1366, 768, errs)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors, failed requests or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
