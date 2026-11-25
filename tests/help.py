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
 const over=[...document.querySelectorAll('.xo,.xtile,.xans,#xi,[data-a=mockcheck],.pl,.bottle,.bub,.btn:not(.hslow),.xpic,.xinv,.xkids')].filter(k=>{const q=k.getBoundingClientRect();return q.width&&r.left<q.right-1&&r.right>q.left+1&&r.top<q.bottom-1&&r.bottom>q.top+1}).length;
 const f=document.querySelector('.hw.on,.hsb.on'),fr=f&&f.getBoundingClientRect(),gap=fr?(r.top>=fr.bottom?r.top-fr.bottom:fr.top-r.bottom):null;
 const ptr=b.classList.contains('hpd')||b.classList.contains('hpu'),px=parseFloat(b.style.getPropertyValue('--px'))||0,aim=fr?Math.abs(r.left+px-(fr.left+fr.width/2)):null;
 /* txt: does it lie over the line its own word is in (or, for the sentence button, over that sentence)? */
 const ownEl=f&&(f.closest('.xsent,.xraw,.xdesc p,.xtext p,.slot')||(f.classList.contains('hsb')?f.previousElementSibling:null)),own=ownEl&&ownEl.getBoundingClientRect();
 const txt=own&&r.left<own.right-1&&r.right>own.left+1&&r.top<own.bottom-9&&r.bottom>own.top+9&&!f.closest('.xdesc p,.xtext p')?1:0;   // the middle of the line: its box is taller than its letters
 const hitc=[...document.querySelectorAll('.xcount')].filter(k=>{const q=k.getBoundingClientRect();return q.width&&r.left<q.right-1&&r.right>q.left+1&&r.top<q.bottom-1&&r.bottom>q.top+1}).length;
 /* nearFree: was there a place right under or over the word (10 px away) that lies over no answer, no picture or
    card of the question, not the counter and not the middle of the word's own line? Only then is a far bubble a fault. */
 const St=document.getElementById('stage').getBoundingClientRect(),hard=[...document.querySelectorAll('.xo,.xtile,.xans,#xi,[data-a=mockcheck],.pl,.bottle,.bub,.btn:not(.hslow),.xpic,.xinv,.xkids,.xcount')].map(k=>k.getBoundingClientRect()).filter(q=>q.width);
 const ov=(a,q)=>a.left<q.right-1&&a.right>q.left+1&&a.top<q.bottom-1&&a.bottom>q.top+1;
 const nearFree=fr?[fr.bottom+10,fr.top-r.height-10].some(y=>{const a={left:r.left,right:r.right,top:y,bottom:y+r.height};return y>=St.top+8&&a.bottom<=St.bottom-8&&!hard.some(q=>ov(a,q))&&!(own&&ov(a,{left:own.left,right:own.right,top:own.top+9,bottom:own.bottom-9}))}):false;
 const cs=getComputedStyle(b),lines=Math.round((r.height-parseFloat(cs.paddingTop)-parseFloat(cs.paddingBottom)-2*parseFloat(cs.borderTopWidth))/(parseFloat(cs.lineHeight)||25));
 return {text:b.textContent,over,txt,inside:r.left>=S.left-1&&r.right<=S.right+1&&r.top>=S.top-1&&r.bottom<=S.bottom+1,tags:[...b.querySelectorAll('*')].map(e=>e.tagName).join(','),html:b.innerHTML.length,gap,ptr,aim,hitc,lines,nearFree,lang:(b.querySelector('bdi')||{}).lang||''}})()"""
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
    fit = await pg.evaluate("[...document.querySelectorAll('.read .row .btn')].map(b=>{const r=b.getBoundingClientRect(),q=b.querySelector('span').getBoundingClientRect();return q.left>=r.left-1&&q.right<=r.right+1})")
    check(f'[{t}] reading: every label of the row is inside its own button', all(fit), fit)
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
    for _ in range(60):      # about 20 planks come before both am / is / are rounds have been seen
        if await pg.evaluate("__lv.g.r&&__lv.g.r.kind") == 'tobe' and not await pg.evaluate("__lv.g.lock"):
            await pg.wait_for_timeout(900)      # let the sentence be drawn before deciding that it has no help word
            if await pg.locator('.bridge #span button.hw').count(): break
        nx = await pg.evaluate("__lv.g.lock?null:__lv.next()")
        if nx: await pg.evaluate("t=>{const e=[...document.querySelectorAll('.pl:not(.used)')].find(x=>x.dataset.t===t);e&&e.click()}", nx)
        await pg.wait_for_timeout(450)
    await pg.wait_for_function("__lv.g.r&&__lv.g.r.kind==='tobe'&&!__lv.g.lock&&document.querySelector('.bridge #span button.hw')", timeout=8000); await pg.wait_for_timeout(900)
    n_hw = await pg.locator('.bridge #span button.hw').count(); n_bank = await pg.locator('.bridge .bank .hw').count()
    check(f'[{t}] bridge: the words of the sentence can be tapped; the three answer planks cannot', n_hw >= 1 and n_bank == 0 and await pg.locator('.bank .pl').count() == 3, [n_hw, n_bank])
    pts0 = await pg.evaluate("(async()=>(await import('/js/state.js')).S.pts)()"); g0 = await pg.evaluate("[__lv.g.i,__lv.g.miss,__lv.g.bad]")
    word = await pg.locator('.bridge #span button.hw').first.get_attribute('data-hw')
    await pg.locator('.bridge #span button.hw').first.click(); await pg.wait_for_timeout(200)
    B = await pg.evaluate(BUB); want = await pg.evaluate(MEANING, word)
    check(f'[{t}] bridge: the bubble shows the word and exactly the meaning the data holds, inside the screen, over nothing a pupil must press', B and B['text'] == f'{word} = {want}' and B['over'] == 0 and B['txt'] == 0 and B['inside'], [B, want])
    check(f'[{t}] the bubble is built from text only (a word, an equals sign, the meaning: no other markup)', B and B['tags'] == 'BDI,SPAN,SPAN', B)
    await shot(pg, f'help_{w}x{h}_04_bridge_bubble')
    await pg.locator('.bridge #span button.hw').first.click(); await pg.wait_for_timeout(120)
    closed1 = await pg.evaluate(BUB) is None
    await pg.locator('.bridge #span button.hw').first.focus(); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
    opened = await pg.evaluate(BUB); exp = await pg.locator('.bridge #span button.hw').first.get_attribute('aria-expanded')
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(120)
    closed2 = await pg.evaluate(BUB) is None; role = await pg.evaluate("[document.getElementById('hbub').getAttribute('role'),document.getElementById('hbub').getAttribute('aria-live'),document.querySelector('.bridge #span button.hw').tagName]")
    check(f'[{t}] the bubble sits next to its word (within 80 px) with a pointer aimed at the middle of the word, and its English is marked as English', B and B['gap'] is not None and B['gap'] <= 80 and (not B['ptr'] or B['aim'] <= 16) and (B['gap'] > 14 or B['ptr']) and B['lang'] == 'en', B)
    check(f'[{t}] the same word again closes the bubble; the keyboard opens it (Enter on the focused word) and Escape closes it', closed1 and opened and exp == 'true' and closed2, [closed1, opened, exp, closed2])
    check(f'[{t}] a help word is a real button and the bubble is announced to a screen reader (role=status, polite)', role == ['status', 'polite', 'BUTTON'], role)
    await pg.locator('.bridge #span button.hw').first.click(); await pg.wait_for_timeout(120); await pg.mouse.click(5, h - 5); await pg.wait_for_timeout(120)
    check(f'[{t}] a tap anywhere else closes the bubble', await pg.evaluate(BUB) is None)
    pts1 = await pg.evaluate("(async()=>(await import('/js/state.js')).S.pts)()"); g1 = await pg.evaluate("[__lv.g.i,__lv.g.miss,__lv.g.bad]")
    check(f'[{t}] bridge: looking up words costs no points and counts as no mistake', pts1 == pts0 and g1 == g0, [pts0, pts1, g0, g1])
    gap = await pg.evaluate("__lv.g.r.gap")
    await pg.click(f'.bank .pl[data-t="{gap}"]'); await pg.wait_for_function("__lv.g.lock||__lv.g.r.kind!=='tobe'||__lv.g.i>0", timeout=5000)
    check(f'[{t}] bridge: after the help the right plank is still a first-time answer', await pg.evaluate("__lv.g.bad") == g0[2])

    # ---- the mock exam: help in the practice, none in the paper
    seen = {'hw': 0, 'hsb': 0, 'answers': 0, 'bubble': 0, 'sent': 0, 'inert': 0, 'who': 0, 'far': 0, 'lines': 0, 'count': 0}; shown = False; problems = []
    numbers = await pg.evaluate("(async()=>(await import('/js/data.js')).WORDS.filter(w=>w.p===7).map(w=>w.en.toLowerCase()))()")
    for skill in ('grammar', 'reading', 'words'):
        await pg.goto(P.BASE + '#mockprac/' + skill); await pg.wait_for_selector('[data-a=mocknext]'); await pg.click('[data-a=mocknext]'); await pg.wait_for_selector('.xq')
        for _ in range(40):
            it = await pg.evaluate(ITEM)
            if not it: break   # this practice is over
            await pg.wait_for_selector('.xq'); await pg.wait_for_timeout(150)
            hk = await pg.locator('div.xq').get_attribute('data-hk')
            if hk != 'mock:' + it['k']: problems.append(('key', hk, it['k']))
            seen['answers'] += await pg.locator('.xo .hw,.xtile .hw,.xopts .hsb').count()
            hws = await pg.locator('div.xq button.hw').all()
            seen['hw'] += len(hws)
            names = [(await x.get_attribute('data-hw')).lower() for x in hws]
            if str(it['a']).lower() in names: problems.append(('answer is a help word', it['k']))
            seen['inert'] += await pg.locator('div.xq span.hw.hx').count()
            if it['type'] == 'who':
                seen['who'] += 1
                if any(n in numbers for n in names): problems.append(('a number word can be tapped in "who is it?"', it['k'], names))
            # one stop for the Tab key in each line; a place to tap is as high as its line (44 px in a sentence, 30 px in
            # a passage), at least 32 px wide, and never lies over another word
            T = await pg.evaluate("""(()=>{const g={},small=[];for(const b of document.querySelectorAll('div.xq button.hw')){(g[b.dataset.hg]=g[b.dataset.hg]||[]).push(b.tabIndex);
              const a=getComputedStyle(b,'::after'),r=b.getBoundingClientRect(),need=b.closest('.xsent,.xraw')?43.5:29.5;if(!r.width)continue;
              if(parseFloat(a.height)<need||parseFloat(a.width)<31.5)small.push([b.dataset.hw,a.width,a.height]);
              const top=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);if(top!==b&&r.top>=0&&r.bottom<=innerHeight&&!(top&&top.closest('#hbub')))small.push(['covered: '+b.dataset.hw,top&&(top.dataset.hw||top.className)])}
              return {lines:Object.keys(g).length,bad:Object.values(g).filter(v=>v.filter(x=>x===0).length!==1).length,small:small.slice(0,3),lang:[...document.querySelectorAll('div.xq .hw')].every(b=>b.lang==='en')}})()""")
            seen['lines'] += T['lines']
            if T['bad'] or T['small'] or not T['lang']: problems.append(('targets', it['k'], T))
            if hws:
                await hws[0].click(); await pg.wait_for_timeout(150)
                B = await pg.evaluate(BUB); wd = await hws[0].get_attribute('data-hw'); want = await pg.evaluate(MEANING, wd)
                if not B or B['text'] != f'{wd} = {want}' or B['over'] or B['txt'] or not B['inside']: problems.append(('bubble', it['k'], B, want))
                else:
                    if B['gap'] > 80 and B['nearFree']: seen['far'] += 1; problems.append(('far although a place next to the word was free', it['k'], wd, B['gap']))
                    seen['count'] += B['hitc']
                    if B['lines'] > 1 and len(B['text']) < 24: problems.append(('a short bubble is broken over several lines', it['k'], B))
                    seen['bubble'] += 1
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
    check(f'[{t}] mock practice: questions carry help words, every bubble shows the data\'s own meaning and covers neither an answer nor the line it explains, and no answer option or the answer itself is ever a help word',
          seen['hw'] > 5 and seen['bubble'] > 3 and seen['answers'] == 0 and not problems, [seen, problems[:3]])
    check(f'[{t}] mock practice: an answer word inside the text looks like the other help words but is not a button, and in "who is it?" no number word can be tapped', seen['inert'] >= 1 and seen['who'] >= 1, seen)
    check(f'[{t}] mock practice: each line of help words is one stop for the Tab key, and the bubble is next to its word whenever a place next to it is free, without hiding the counter', seen['lines'] >= 3 and seen['far'] == 0 and seen['count'] == 0, seen)
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

    # ---- the arrow keys move along the help words of a line
    K = await pg.evaluate("""(async()=>{const h=await import('/js/help.js'),d=document.createElement('p');d.dir='ltr';d.innerHTML=h.words('My hobby is far from the goal.',['far']);document.getElementById('view').appendChild(d);
      const bs=[...d.querySelectorAll('button.hw')],key=k=>document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true}));
      bs[0].focus();key('ArrowRight');const second=document.activeElement===bs[1],tabs=bs.map(b=>b.tabIndex);key('ArrowLeft');const back=document.activeElement===bs[0];key('End');const end=document.activeElement===bs[bs.length-1];
      const out={n:bs.length,second,tabs,back,end,inert:d.querySelector('span.hw.hx')&&d.querySelector('span.hw.hx').textContent,inertBtn:!!d.querySelector('button[data-hw=far]')};d.remove();return out})()""")
    check(f'[{t}] keyboard: one word of a line is in the tab order, the arrow keys, Home and End move along the line, and the skipped word is not a button', K['n'] == 2 and K['second'] and K['tabs'] == [-1, 0] and K['back'] and K['end'] and K['inert'] == 'far' and not K['inertBtn'], K)
    check(f'[{t}] the switch was taken out of the address after it was read', 'help' not in await pg.evaluate('location.search'), await pg.evaluate('location.href'))

    # ---- nothing invented, nothing injected, nothing sent
    R = await pg.evaluate("""(async()=>{const h=await import('/js/help.js'),d=await import('/js/data.js');
      const list=new Map(d.WORDS.map(w=>[w.en.toLowerCase(),w.he])),bad=[];
      for(const t of ['goal','a lot of','dining room','forty','Israel','May',"I'm sorry",'twenty-five','hobbies','is','zebra','xylophone','<img src=x onerror=alert(1)>']){const m=h.meaning(t),k=t.toLowerCase();
        const want=list.get(k)||null;if((m&&m.he)!==want)bad.push([t,m,want])}
      const el=document.createElement('button');el.className='hw';el.dataset.hw='<img src=x onerror="window.__pwned=1">';document.getElementById('view').appendChild(el);el.click();await new Promise(r=>setTimeout(r,150));
      const b=document.getElementById('hbub');const out={bad,planted:!b.hidden,pwned:!!window.__pwned,markup:h.words('<b>goal</b> & "piano"')};el.remove();return out})()""")
    check(f'[{t}] a meaning is only ever the entry of the teacher\'s word list; a word that is only in the reading glossary ("is", "hobbies") or in neither gets none', not R['bad'], R['bad'])
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
    await pg.evaluate(f"localStorage.setItem('{HELP_KEY}',JSON.stringify({{v:1,items:{{'read:1':{{n:1,w:['goal']}}}}}}))")
    await pg.goto(P.BASE + '#settings'); await pg.wait_for_selector('[data-a=logout]'); await pg.click('[data-a=logout]'); await pg.wait_for_selector('#lc', timeout=10000)
    check(f'[class {w}x{h}] signing out clears the device note, so the next pupil on this device does not inherit it', await pg.evaluate(HELPLOG) is None)
    await c.close()


async def no_voice(b, w, h, errs):
    """the recordings cannot be reached: a slow replay stays silent (never the browser voice), and the turtle hides"""
    c, pg = await new_page(b, w, h, errs=[], clips='error')
    await pg.goto(ON + '#map'); await pg.wait_for_selector('.map .isl,.scr.map'); await pg.wait_for_timeout(300)
    R = await pg.evaluate("""(async()=>{const m=await import('/js/state.js'),sp=()=>__spoken.filter(x=>String(x).trim()).length,n0=sp();
      const before=m.hasClip('goal'),a=await m.say('goal',undefined,true),n1=sp(),b=await m.say('kick',undefined,true),n2=sp(),after=m.hasClip('goal');
      const c=await m.say('song',undefined,true),n3=sp();await m.sayAll(['song','hobby'],.78,10,true);const n4=sp();
      const normal=await m.say('goal');await new Promise(r=>setTimeout(r,100));return {before,a,b,c,after,slowSpoken:n4-n0,steps:[n1-n0,n2-n0,n3-n0],normal,normalSpoken:sp()-n4}})()""")
    check(f'[no voice {w}x{h}] a slow replay whose recording fails stays silent: the browser voice says nothing, once, twice, or for a whole story', R['a'] is False and R['b'] is False and R['c'] is False and R['slowSpoken'] == 0, R)
    check(f'[no voice {w}x{h}] after two misses the turtle hides (no recording to play), while a normal replay still falls back as before', R['before'] is True and R['after'] is False and R['normalSpoken'] >= 1, R)
    await pg.goto(P.BASE + '#play/1/read'); await lv(pg, 'read'); await pg.wait_for_timeout(300)
    check(f'[no voice {w}x{h}] the story has no turtle while the recordings are out of reach', await pg.locator('[data-a=readslow]').count() == 0)
    await c.close()


async def fresh_zero(b, errs):
    """?help=0 on a device that never had the switch adds nothing"""
    c, pg = await new_page(b, 390, 844, errs=errs)
    await pg.goto(P.BASE + '?help=0#settings'); await pg.wait_for_selector('.scr.settings')
    st = await pg.evaluate("[localStorage.getItem('word-islands-settings-v1')||'',document.querySelectorAll('.setrow[role=switch]').length,location.search]")
    check('?help=0 on a device that never had the switch stores nothing, adds no settings row, and leaves the address clean', 'help' not in st[0] and st[1] == 3 and 'help' not in st[2], st)
    await c.close()


async def small(b, errs):
    """360 px wide: the reading row"""
    c, pg = await new_page(b, 360, 740, errs=errs)
    await pg.goto(ON + '#play/1/read'); await lv(pg, 'read'); await pg.wait_for_timeout(300)
    row = await pg.evaluate("[...document.querySelectorAll('.read .row .btn')].map(b=>{const r=b.getBoundingClientRect(),q=b.querySelector('span').getBoundingClientRect();return [Math.round(r.left),Math.round(r.right),Math.round(r.height),q.left>=r.left-1&&q.right<=r.right+1]})")
    check('[360x740] reading: three buttons in the row, inside the screen, at least 44 px high, every label inside its button', len(row) == 3 and all(l >= 0 and r <= 360 and hh >= 44 and ok for l, r, hh, ok in row), row)
    await shot(pg, 'help_360x740_read')
    await c.close()


async def main():
    procs = P.start_servers(mock=True)      # its own servers on free ports (tests/play.py)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await off(b, 390, 844, errs)
            await on(b, 390, 844, errs)
            await class_mode(b, 390, 844, errs)
            await no_voice(b, 390, 844, errs)
            await fresh_zero(b, errs)
            await small(b, errs)
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
