#!/usr/bin/env python3
# suite: quick=--quick   # picked up by tests/all.py
"""Play-through of the mock exam (מבחן דמו): exam with one try per question, the check-in report, practice for the
weak skill, the locked and then unlocked retake, and a clean second paper. And the quit button during a paper: it can
be tapped (touch and mouse), the first tap only asks, the question expires, a second tap leaves without a try or a
score, and the questions already shown count as seen, so the next paper draws fresh ones first.

    python3 tests/mock.py              # 390x844, 360x740 and a laptop window
    python3 tests/mock.py --quick      # 390x844 only
    python3 tests/mock.py --shots DIR  # also save a PNG of every screen
"""
import asyncio, os, re, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, shot, new_page, port_open, fails

QUICK = '--quick' in sys.argv

ITEM = "(()=>{const L=window.__lv;if(!L||!L.items)return null;const it=L.items[L.i()];return it?{k:it.k,type:it.type,skill:it.skill,a:it.a,o:it.o,tiles:it.tiles,i:L.i(),kind:L.kind}:null})()"


async def answer(pg, it, right=True):
    t = it['type']
    if t in ('choice', 'who', 'read'):
        dis = await pg.evaluate("[...document.querySelectorAll('.xo')].map(b=>b.disabled)")
        if right:
            j = it['o'].index(it['a'])
        else:
            cand = [k for k, o in enumerate(it['o']) if o != it['a'] and not dis[k]]
            if not cand:
                return False
            j = cand[0]
        await pg.click(f'.xo[data-j="{j}"]')
    elif t == 'order':
        words = it['tiles'] if not right else sorted(it['tiles'], key=lambda w: it['a'].index(w))
        if not right and words == sorted(it['tiles'], key=lambda w: it['a'].index(w)):
            words = list(reversed(words))
        for w in words:
            await pg.locator('.xtiles .xtile', has_text=w).first.click()
        await pg.click('[data-a=mockcheck]')
    else:
        await pg.fill('#xi', it['a'] if right else 'xyz')
        await pg.click('[data-a=mockcheck]')


async def exam(pg, wrong_skill=None, tag=None):
    """play a whole paper; every answer right except the skill named"""
    seen_station, n = set(), 0
    for _ in range(400):
        if await pg.locator('.mockrep').count():
            return n
        if await pg.locator('.xstation').count():
            k = await pg.locator('.xstation').get_attribute('data-k')
            if k not in seen_station and tag:
                await shot(pg, f'{tag}_station_{k}')
            seen_station.add(k)
            await pg.click('.xstation [data-a=mocknext]'); await pg.wait_for_timeout(250); continue
        it = await pg.evaluate(ITEM)
        if not it or not await pg.locator('.xq.label').count() or await pg.locator('.xo:disabled, #xi[readonly]').count():
            await pg.wait_for_timeout(150); continue
        if tag and it['i'] < 20 and it['type'] not in ('choice',) or (tag and it['i'] in (0, 1)):
            await shot(pg, f'{tag}_q{it["i"]:02d}_{it["type"]}')
        await answer(pg, it, right=it['skill'] != wrong_skill)
        n += 1
        await pg.wait_for_timeout(1100)
    return n


async def practise(pg, tag=None):
    await pg.wait_for_selector('.xrule'); await pg.wait_for_timeout(1800)
    if tag: await shot(pg, f'{tag}_rule')
    await pg.click('.xrule [data-a=mocknext]')
    done, reveal_shown = 0, False
    for _ in range(300):
        if await pg.locator('.mockrep').count():
            return done
        if await pg.locator('.xfb.sol [data-a=mocknext]').count():
            if tag and not reveal_shown: await shot(pg, f'{tag}_reveal')
            reveal_shown = True
            await pg.click('.xfb.sol [data-a=mocknext]'); await pg.wait_for_timeout(300); continue
        it = await pg.evaluate(ITEM)
        if not it or await pg.locator('.xo:disabled, #xi[readonly]').count() and not await pg.locator('.xfb.bad').count():
            await pg.wait_for_timeout(150); continue
        if await pg.locator('.xfb.bad').count():
            await answer(pg, it, right=True); done += 1
        elif it['i'] == 0:   # the first one: wrong twice, so the answer and the rule are shown
            await answer(pg, it, right=False); await pg.wait_for_timeout(300)
            if tag: await shot(pg, f'{tag}_try_again')
            check('practice: a wrong answer explains and allows one more try', await pg.locator('.xfb.bad').count() == 1)
            if await answer(pg, it, right=False) is not False:
                await pg.wait_for_timeout(300)
                check('practice: a second wrong answer shows the right answer and a next button', await pg.locator('.xfb.sol').count() == 1)
            continue
        elif it['i'] == 1:
            await answer(pg, it, right=False); await pg.wait_for_timeout(300)
            continue
        else:
            await answer(pg, it, right=True); done += 1
        await pg.wait_for_timeout(1000)
    return done


HIT = """(()=>{const b=document.querySelector('.xquit');if(!b)return null;const r=b.getBoundingClientRect();let hit=0;
 for(let i=0;i<5;i++)for(let j=0;j<5;j++){const e=document.elementFromPoint(r.left+r.width*(i+.5)/5,r.top+r.height*(j+.5)/5);if(e&&e.closest('.xquit')===b)hit++}
 return {hit,w:Math.round(r.width),h:Math.round(r.height),x:r.left+r.width/2,y:r.top+r.height/2,icon:b.querySelectorAll('svg path,svg line,svg polyline').length}})()"""


async def to_question(pg):
    """wait for the next question of the paper (passing a station screen) and return its item"""
    for _ in range(100):
        if await pg.locator('.xstation [data-a=mocknext]').count():
            await pg.click('.xstation [data-a=mocknext]'); await pg.wait_for_timeout(250); continue
        it = await pg.evaluate(ITEM)
        if it and await pg.locator('.xq.label').count() and not await pg.locator('.xo:disabled, #xi[readonly]').count():
            return it
        await pg.wait_for_timeout(150)
    return None


XFB = """async(FMT)=>{const {POOL}=await import('./js/xdata.js');const {esc}=await import('./js/state.js');const fmt=FMT;
 const tips=[...new Set(Object.values(POOL).flatMap(o=>Object.values(o).flat()).map(e=>e.tip).filter(Boolean))];
 const fb=document.getElementById('xfb');const out={n:tips.length,items:[],broken:[],arrow:[],arrows:0,text:[],split:[],wide:[],has:['It\\'s my birthday! I\\'m 12 years old.','Time: 4 o\\'clock','(Maya, Israel, June)'].filter(x=>!tips.some(t=>t.includes(x)))};
 const rects=(n,i)=>{const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+1);return r.getBoundingClientRect()};
 for(const [cls,html] of [['ok',t=>OKT],['sol',t=>SOLT]])
 for(const t of tips){fb.className='xfb '+cls;fb.innerHTML=html(t);const sp=fb.querySelector(':scope>span')||fb;   /* no span (the old box): measure the whole box */
  /* the explanation is one item of the column (one flowing text), not one line per piece */
  const kids=[...fb.childNodes].filter(n=>n.nodeType===1||n.textContent.trim()).map(n=>n.nodeName);
  if(kids.join(',')!==(cls==='ok'?'B,SPAN':'B,BDI,SPAN'))out.items.push([cls,t,kids.join(',')]);   // the answer's own word (sol) is the BDI
  if((sp===fb?[...fb.childNodes].slice(2).map(n=>n.textContent).join(''):sp.textContent)!==t)out.text.push([cls,t]);
  /* nothing in the box is wider than the screen */
  for(const e of [fb,...fb.querySelectorAll('*')]){const r=e.getBoundingClientRect();if(r.width&&(r.left<-0.5||r.right>innerWidth+0.5))out.wide.push([cls,t.slice(0,40),e.nodeName,Math.round(r.left),Math.round(r.right)])}
  /* no English word is broken across two lines (an apostrophe stays inside its word: "aren't") */
  const w=document.createTreeWalker(sp,NodeFilter.SHOW_TEXT);let n;const chars=[];while((n=w.nextNode()))for(let i=0;i<n.length;i++)chars.push([n,i,n.data[i]]);
  for(const m of t.matchAll(/[A-Za-z]+['\u2019][A-Za-z]+/g)){const f=chars[m.index],l=chars[m.index+m[0].length-1],bf=f[0].parentElement.closest('bdi'),bl=l[0].parentElement.closest('bdi'),a=rects(f[0],f[1]),b2=rects(l[0],l[1]);
   if(!bf||bf!==bl||Math.abs(a.top-b2.top)>4)out.broken.push([cls,m[0]])}
  /* numbers stay inside their English run ("I'm 12 years old." in order), brackets stay outside it so the Hebrew line
     mirrors them ("(Maya, Israel, June)"), and the reported sentences are each one run */
  const heb=c=>/[\\u0590-\\u05FF]/.test(c);
  chars.forEach(([nd,i,ch],k)=>{const inb=nd.parentElement.closest('bdi');
   if(/[()]/.test(ch)&&inb)out.split.push([cls,'bracket inside',inb.textContent]);
   if(/[0-9]/.test(ch)&&!inb){let a=k,b=k;while(a>0&&!heb(t[a-1]))a--;while(b<t.length-1&&!heb(t[b+1]))b++;if(/[A-Za-z]/.test(t.slice(a,b+1)))out.split.push([cls,'digit outside',t.slice(a,b+1)])}});
  const runs=[...sp.querySelectorAll('bdi')].map(b=>b.textContent);
  for(const x of ['It\\'s my birthday! I\\'m 12 years old.','Time: 4 o\\'clock','Maya, Israel, June'])if(t.includes(x)&&!runs.includes(x))out.split.push([cls,x,runs]);
  /* an arrow points at the word after it */
  for(const m of t.matchAll(/[\u2192\u2190]/g)){let j=m.index+1;while(/\\s/.test(t[j]||''))j++;if(j>=t.length)continue;const A=rects(...chars[m.index].slice(0,2)),N=rects(...chars[j].slice(0,2));
   if(Math.abs(A.top-N.top)>=4){out.arrow.push([cls,t,'wrapped away']);continue}out.arrows++;if(!(m[0]==='\u2192'?N.left>=A.right-1:N.right<=A.left+1))out.arrow.push([cls,t])}}
 fb.className='xfb';fb.innerHTML='';return out}"""


async def explanations(b, w, h, errs, ds=False):
    """every explanation of the question pool, drawn into the real feedback box of the mock exam (#xfb, a column) as
    the exam draws it after a right answer and after the answer is shown: one flowing text (not one line per English
    or Hebrew piece), no English word broken across lines ("aren't"), and every arrow pointing at its word"""
    t = f'xfb{w}x{h}' + (' ds' if ds else '')
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.goto(P.BASE + ('?ds=1' if ds else '') + '#mockprac/grammar'); await pg.wait_for_selector('.xrule'); await pg.click('.xrule [data-a=mocknext]')
    await pg.wait_for_selector('#xfb', state='attached')
    src = open(os.path.join(P.ROOT, 'js', 'mock.js'), encoding='utf-8').read()
    # the two boxes exactly as js/mock.js draws them: its fmt() and its two templates, read from the file
    fmt_src = re.search(r'^const fmt=(.*?);\s', src, re.M).group(1)
    ok_t = re.search(r"fb\.className='xfb ok';fb\.innerHTML=(`[^`]*`)", src).group(1)
    sol_t = re.search(r"fb\.className='xfb sol';fb\.innerHTML=(`.*`);$", src, re.M).group(1)   # the whole line: its button has a template of its own
    tpl = lambda x: x.replace("${fmt(it.tip||'')}", '${fmt(t)}').replace('${en(it.a)}', '<bdi dir="ltr" class="en">x</bdi>')
    sol_t = re.sub(r"\$\{btn\('mocknext',`[^`]*`,'[^']*'\)\}", '', tpl(sol_t))   # the "next" button is not part of the text
    check(f'[{t}] the two feedback boxes are read from js/mock.js', '${fmt(t)}' in tpl(ok_t) and '${fmt(t)}' in sol_t and '${' not in sol_t.replace('${fmt(t)}', ''), [ok_t, sol_t])
    R = await pg.evaluate(XFB.replace('const fmt=FMT', 'const fmt=' + fmt_src, 1).replace('async(FMT)=>', 'async()=>').replace('OKT', tpl(ok_t), 1).replace('SOLT', sol_t, 1))
    check(f'[{t}] every explanation ({R["n"]}) is one flowing text in the box, not one line per piece, and reads the same words', R['n'] > 50 and not R['items'] and not R['text'], (R['items'][:2], R['text'][:2]))
    check(f'[{t}] the sentences with a number or brackets are in the pool (so the next check covers them)', not R['has'], R['has'])
    check(f'[{t}] every English stretch is one run in its own order: numbers inside ("I\'m 12 years old."), brackets outside', not R['split'], R['split'][:3])
    check(f'[{t}] nothing in the box is wider than the {w}px screen', not R['wide'], R['wide'][:3])
    check(f'[{t}] no English word is broken across lines (an apostrophe stays inside: "aren\'t")', not R['broken'], R['broken'][:3])
    check(f'[{t}] every arrow points at its word and never wraps away from it ({R["arrows"]} checked)', R['arrows'] > 10 and not R['arrow'], R['arrow'][:2])
    await c.close()


async def quit_button(b, w, h, errs, laptop=False):
    """the quit button of a paper: a real tap (touch) and a real click (mouse) reach it, the first press only asks,
    the question expires after 2.6 s, the second press leaves; no try and no score are kept, and the questions already
    shown are added to x.seen (nothing else in the record changes), so a new paper draws fresh questions first"""
    t = f'xq{w}x{h}'
    P.LAPTOP = laptop
    for how in (('mouse',) if laptop else ('touch', 'mouse')):
        c, pg = await new_page(b, w, h, errs=errs)
        await pg.goto(P.BASE + '#mockrun'); await pg.wait_for_selector('.xstation')
        it = await to_question(pg)
        H = await pg.evaluate(HIT)
        check(f'[{t} {how}] the quit button is a 48px target with an icon, and every point of it takes the tap (25 of 25)', H and H['hit'] == 25 and H['w'] >= 48 and H['h'] >= 48 and H['icon'] >= 1, H)
        press = (lambda: pg.touchscreen.tap(H['x'], H['y'])) if how == 'touch' else (lambda: pg.mouse.click(H['x'], H['y']))
        before = await pg.evaluate("JSON.stringify(__game.S())")
        # two answered, the third shown: three questions were seen
        for _ in range(2):
            await answer(pg, it, right=False); await pg.wait_for_timeout(1100); it = await to_question(pg)
        items = await pg.evaluate("__lv.items.map(i=>i.k)")
        await press(); await pg.wait_for_timeout(300)
        toast = await pg.locator('#toast').inner_text()
        check(f'[{t} {how}] the first press only asks, and the paper stays', 'לצאת' in toast and await pg.evaluate("location.hash") == '#mockrun', toast)
        if how == 'touch' and w == 390: await shot(pg, f'{t}_quit_ask')
        await pg.wait_for_timeout(2700)
        await press(); await pg.wait_for_timeout(300)
        check(f'[{t} {how}] after 2.6 s the question has expired: the next press asks again and the paper stays', await pg.evaluate("location.hash") == '#mockrun')
        await press(); await pg.wait_for_timeout(600)
        check(f'[{t} {how}] a second press within 2.6 s leaves the paper', await pg.evaluate("location.hash") == '#mock')
        S0, S1 = __import__('json').loads(before), await pg.evaluate("__game.S()")
        x0, x1 = S0.get('x', {}), S1.get('x', {})
        check(f'[{t} {how}] a quit paper is not a try and has no score', x1.get('tries', []) == x0.get('tries', []) and S1.get('pts') == S0.get('pts'), [len(x1.get('tries', [])), S0.get('pts'), S1.get('pts')])
        added = [k for k in x1.get('seen', []) if k not in x0.get('seen', [])]
        check(f'[{t} {how}] the three questions shown, and only those, are now seen', sorted(added) == sorted(items[:3]), [added, items[:3]])
        rest0 = {k: v for k, v in S0.items() if k != 'x'}; rest1 = {k: v for k, v in S1.items() if k != 'x'}
        xr0 = {k: v for k, v in x0.items() if k != 'seen'}; xr1 = {k: v for k, v in x1.items() if k != 'seen'}
        check(f'[{t} {how}] nothing else in the record changed', rest0 == rest1 and xr0 == xr1, [k for k in set(rest0) | set(rest1) if rest0.get(k) != rest1.get(k)])
        if how == 'touch' and w == 390:
            # the check-in report: the events a save of this record would send (js/api.js events()) hold no paper
            ev = await pg.evaluate("async ([a,b])=>{const {events}=await import('./js/api.js');return events(a,b)}", [S0, S1])
            check(f'[{t} {how}] the check-in report gets no paper and no event at all from a quit', ev == [], ev)
            # the teacher's mock results (mock backend, same rules as backend/Code.gs mockOf): the same before and after
            api = f'http://127.0.0.1:{P.API_PORT}/'
            def post(d):   # straight from the test, so the page itself still talks to no other host
                import urllib.request, json as J
                with urllib.request.urlopen(urllib.request.Request(api, data=J.dumps(d).encode(), method='POST'), timeout=10) as r:
                    return J.loads(r.read())
            who = {'c': 'EN-1234', 'n': 'בודק', 'p': '2468'}   # the mock backend's test class, an obviously fake pupil
            post(dict(who, a='register'))
            mocks = []
            for st in (S0, S1):
                r = post(dict(who, a='save', s=st))
                tv = post({'a': 'teacher', 'c': 'EN-1234', 't': '654321'})
                mocks.append([r.get('ok'), next((k.get('mock') for k in tv.get('kids', []) if k.get('n') == 'בודק'), 'missing')])
            check(f'[{t} {how}] the mock results on the teacher screen are the same before and after a quit (nothing for a quit paper)', mocks[0] == mocks[1] and mocks[0][0], mocks)
        stored = await pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('aam-unit1-v1'));return s&&s.x&&s.x.seen})()")
        check(f'[{t} {how}] the seen questions are saved on the device', stored and all(k in stored for k in items[:3]))
        await pg.evaluate("location.hash='mockrun'"); await pg.wait_for_selector('.xstation')
        new = await pg.evaluate("__lv.items.map(i=>i.k)")
        check(f'[{t} {how}] the next paper draws fresh questions first: none of the three comes back', not set(new) & set(items[:3]), set(new) & set(items[:3]))
        await c.close()
    if w == 390:
        # the pool runs out: with every question seen, a paper still has its 20 (old ones, shuffled), and the seen
        # list keeps its cap of 400
        c, pg = await new_page(b, w, h, errs=errs); await pg.goto(P.BASE); await pg.wait_for_selector('.title .sb')
        R = await pg.evaluate("""async()=>{const {POOL,paper}=await import('./js/xdata.js');const all=Object.values(POOL).flatMap(o=>Object.values(o).flat()).map(i=>i.k);
          const p=paper(new Set(all),false);return {pool:all.length,n:p.length,kinds:new Set(p.map(i=>i.skill)).size}}""")
        check(f'[{t}] when every question has been seen, a paper still deals 20 (pool of {R["pool"]}, under the 400 kept)', R['n'] == 20 and R['kinds'] == 4 and R['pool'] < 400, R)
        await c.close()


async def run(b, w, h, errs, laptop=False):
    t = f'x{w}x{h}'
    P.LAPTOP = laptop
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.goto(P.BASE); await pg.wait_for_selector('.title .sb'); await pg.wait_for_timeout(500)
    await shot(pg, f'{t}_00_title')
    check(f'[{t}] the title offers the mock exam', await pg.locator('.title .sb.xm').count() == 1)
    await pg.click('.title .sb.xm', force=True); await pg.wait_for_selector('.xintro'); await pg.wait_for_timeout(700)
    await shot(pg, f'{t}_01_intro')
    await pg.click('[data-to=mockrun]'); await pg.wait_for_selector('.xstation')
    n = await exam(pg, wrong_skill='grammar', tag=f'{t}_02')
    check(f'[{t}] the exam has 20 questions', n == 20, n)
    await pg.wait_for_timeout(1800)
    await shot(pg, f'{t}_03_report')
    txt = await pg.locator('.mockrep').inner_text()
    check(f'[{t}] the report shows grammar as the skill to practise', 'דקדוק' in await pg.locator('.xmsg').inner_text() and await pg.locator('.xrow.r').count() == 1, txt[:200])
    check(f'[{t}] the report lists the mistakes with the right answers', await pg.locator('.xrev .xw').count() == 5)
    await pg.evaluate("location.hash='mock'"); await pg.wait_for_selector('.xcard'); await pg.wait_for_timeout(500)
    await shot(pg, f'{t}_04_hub_locked')
    check(f'[{t}] the retake waits for the practice', await pg.locator('.xgo button[disabled]').count() == 1)
    await pg.click('.xpr');
    done = await practise(pg, tag=f'{t}_05_prac')
    check(f'[{t}] the grammar practice is played to the end', done >= 6, done)
    await pg.wait_for_timeout(800); await shot(pg, f'{t}_06_prac_done')
    await pg.evaluate("location.hash='mock'"); await pg.wait_for_selector('.xcard'); await pg.wait_for_timeout(400)
    check(f'[{t}] after the practice the retake is open', await pg.locator('.xgo [data-to=mockrun]').count() == 1)
    first = await pg.evaluate("__game.S().x.tries[0]")
    await pg.click('.xgo [data-to=mockrun]'); await pg.wait_for_selector('.xstation')
    keys1 = set(await pg.evaluate("__game.S().x.seen"))
    n2 = await exam(pg)
    keys2 = await pg.evaluate("window.__lv?[]:__game.S().x.tries[1]?[]:[]")
    await pg.wait_for_timeout(1800)
    await shot(pg, f'{t}_07_report_ready')
    x = await pg.evaluate("__game.S().x")
    check(f'[{t}] the second paper is all right and says ready', len(x['tries']) == 2 and x['tries'][1]['total'][0] == 20 and 'מוכנים' in await pg.locator('.ribbon').inner_text(), x['tries'][-1]['total'])
    await pg.evaluate("location.hash='mock'"); await pg.wait_for_selector('.xhist'); await pg.wait_for_timeout(500)
    await shot(pg, f'{t}_08_hub_progress')
    check(f'[{t}] the hub shows the progress between the two papers', await pg.locator('.hb').count() == 2)
    await c.close()


async def main():
    procs = P.start_servers(mock=True)   # the mock backend: only the quit test talks to it, for the teacher view
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await run(b, 390, 844, errs)
            for w, h, lap in ((390, 844, False), (360, 740, False), (1366, 768, True)):
                await quit_button(b, w, h, errs, laptop=lap)
            for w, h in ((390, 844), (360, 740), (320, 640)):
                await explanations(b, w, h, errs)
            await explanations(b, 320, 640, errs, ds=True)   # the new look too (?ds=1)
            if not QUICK:
                await run(b, 360, 740, errs)
                await run(b, 1366, 640, errs, laptop=True)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors or failed requests', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
