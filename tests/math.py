#!/usr/bin/env python3
# suite: quick=--quick   # picked up by tests/all.py
"""End-to-end play-through for Fraction Bay (מפרץ השברים), the math world (headless Chrome via Playwright).

    python3 tests/math.py              # every level of every math island, at 390x844 and 360x740, plus a laptop pass
    python3 tests/math.py --quick      # island 1 and one level of each later island, 390x844 only
    python3 tests/math.py --shots DIR  # also save a PNG of every screen

The exercise generators are checked separately and much harder by tests/mdata_check.mjs (node).
"""
import asyncio, os, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, shot, lv, new_page, port_open, play_sling, fails

QUICK = '--quick' in sys.argv


async def tap_slice(pg, j, s):
    """a real tap inside slice s of pizza j (at 60% of the radius, on the slice's middle line)"""
    box = await pg.locator(f'.pz[data-j="{j}"]').bounding_box()
    d = await pg.evaluate(f"__lv.state().pz[{j}].d")
    import math
    a = -math.pi / 2 + (s + .5) * 2 * math.pi / d
    cx, cy, w = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2, box['width']
    await pg.mouse.click(cx + math.cos(a) * w * .25, cy + math.sin(a) * w * .25)


async def play_pizza(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'pizza')
    if use_hint:
        await pg.click('[data-a=hint]')
    missed = not wrong_first
    for _ in range(200):
        if await pg.locator('.result').count():
            return True
        st = await pg.evaluate("(()=>{const L=window.__lv;if(!L||L.kind!=='pizza')return null;const t=L.state();if(!t||L.g.lock)return null;const p=t.p;"
                               "return {step:t.step,i:L.g.i,kind:p.kind,need:p.ans.w*p.ans.d+p.ans.n,d:p.ans.d,s:p.b?p.a.n+p.b.n:0,opts:t.opts?t.opts.map(o=>typeof o==='number'?o:(o.ok?1:0)):null,"
                               "pz:t.pz.map(q=>({on:q.on,d:q.d,cut:q.cut}))}})()")
        if not st:
            await pg.wait_for_timeout(150); continue
        step = st['step']
        if tag and st['i'] == 0:
            await shot(pg, f'{tag}_{step}')
        if step == 'build':
            if not missed:   # one slice short: the table says how many are missing
                await tap_slice(pg, 0, 0); await pg.click('[data-a=mpzok]'); await pg.wait_for_timeout(200)
                check('pizza: a short table is refused with a count', await pg.locator('#toast.on').count() == 1)
                missed = True
                await tap_slice(pg, 0, 0)   # tapping the last topped slice again takes it off
                continue
            left = st['need']
            for j, q in enumerate(st['pz']):
                k = min(q['d'], left)
                if k:
                    await tap_slice(pg, j, k - 1)
                left -= k
            await pg.click('[data-a=mpzok]')
        elif step == 'count':
            k = st['opts'].index(st['s'])
            if not missed:
                bad = next(i for i, v in enumerate(st['opts']) if v != st['s'])
                await pg.click(f'.mc[data-k="{bad}"]'); missed = True; await pg.wait_for_timeout(150)
            await pg.click(f'.mc[data-k="{k}"]')
        elif step == 'merge':
            await pg.click('[data-a=mmerge]')
        elif step == 'cut':
            j = next(i for i, q in enumerate(st['pz']) if not q['cut'])
            await pg.locator(f'.pz[data-j="{j}"]').click()
        elif step == 'eat':
            j = next(i for i, q in enumerate(st['pz']) if q['cut'] and q['on'] > 0)
            await tap_slice(pg, j, st['pz'][j]['on'] - 1)
        elif step == 'wholes':
            j = next(i for i, q in enumerate(st['pz']) if q['on'] == q['d'])
            await pg.locator(f'.pz[data-j="{j}"]').click()
        elif step == 'ask':
            k = st['opts'].index(1)
            if not missed:
                bad = st['opts'].index(0)
                await pg.click(f'.mc[data-k="{bad}"]'); missed = True; await pg.wait_for_timeout(200)
                if tag:
                    await shot(pg, f'{tag}_wrong')
            await pg.click(f'.mc[data-k="{k}"]')
            await pg.wait_for_timeout(1700)
        await pg.wait_for_timeout(120)
    return False


async def type_sheet(pg, w, n, d, form):
    async def put(slot, v):
        await pg.click(f'.aslot[data-k="{slot}"]')
        for _ in range(3):
            await pg.click('.key.kdel')
        for ch in str(v):
            await pg.click(f'.key[data-k="{ch}"]')
    if form != 'imp':
        await put('w', w if w else '')
    await put('n', n if n else '')
    await put('d', d if n else '')
    await pg.click('.key[data-k="ok"]')
    await pg.wait_for_timeout(250)


async def play_sheet(pg, wrong_first=False, use_hint=False, tag=None):
    await lv(pg, 'sheet')
    if use_hint:
        await pg.click('[data-a=hint]')
        check('sheet: the hint shows the first step', await pg.locator('.mfb.mhint .mst').count() == 1)
    for _ in range(80):
        if await pg.locator('.result').count():
            return True
        st = await pg.evaluate("(()=>{const L=window.__lv;if(!L||L.kind!=='sheet'||L.g.lock)return null;const a=L.answer();return a?{w:a.w,n:a.n,d:a.d,form:L.form(),i:L.g.i}:null})()")
        if not st:
            await pg.wait_for_timeout(150); continue
        w, n, d, form = st['w'], st['n'], st['d'], st['form']
        if tag and st['i'] == 0:
            await shot(pg, f'{tag}_q')
        if wrong_first and st['i'] == 0:
            big = w * d + n
            if form != 'imp' and big > d and n:
                # the right value in the wrong form: told so, kindly, and it does not count towards the worked solution
                await type_sheet(pg, 0, big, d, form)
                check('sheet: an improper answer to a mixed question is called right in value, wrong in form', await pg.locator('.mfb.mwarn').count() == 1, await pg.locator('#fb').inner_text())
                if tag: await shot(pg, f'{tag}_form')
            elif form != 'imp':
                await type_sheet(pg, w + 1, n, d, form)
                check('sheet: a wrong answer is marked wrong', await pg.locator('.mfb.mbad').count() == 1)
            else:
                await type_sheet(pg, 0, n + 1, d, form)
                check('sheet: a wrong answer is marked wrong', await pg.locator('.mfb.mbad').count() == 1)
        if wrong_first and st['i'] == 1:
            for k in range(2):
                await type_sheet(pg, w + 2, n, d, form) if form != 'imp' else await type_sheet(pg, 0, n + 2, d, form)
            check('sheet: two wrong answers show the worked solution', await pg.locator('.mfb.msol .mst').count() >= 2)
            if tag: await shot(pg, f'{tag}_solution')
            await pg.click('.mfb .btn')
            await pg.wait_for_timeout(300)
            continue
        await type_sheet(pg, w, n, d, form)
        ok = await pg.locator('.mfb.mok').count() == 1
        if not ok:
            check(f'sheet: the right answer is accepted ({w} {n}/{d} {form})', False, await pg.locator('#fb').inner_text())
            return False
        await pg.wait_for_timeout(1450)
    return False


PLAY = {'pizza': play_pizza, 'sling': play_sling, 'sheet': play_sheet}


async def level(pg, isl, typ, tag, **kw):
    await pg.evaluate(f"location.hash='mplay/{isl}/{typ}'")
    ok = await PLAY[typ](pg, tag=tag, **kw)
    check(f'math island {isl} {typ}: played to the result screen', ok)
    if not ok:
        return 0
    await pg.wait_for_timeout(1700 if P.SHOTS else 300)
    if tag:
        await shot(pg, f'{tag}_result')
    return await pg.locator('.bs.on').count()


async def run(b, w, h, full, errs, laptop=False):
    t = f'm{w}x{h}'
    P.LAPTOP = laptop
    c, pg = await new_page(b, w, h, errs=errs)
    await pg.goto(P.BASE); await pg.wait_for_selector('.title .sb'); await pg.wait_for_timeout(600)
    await shot(pg, f'{t}_01_title')
    check(f'[{t}] title offers English, the mock exam and math', await pg.locator('.title .sb').count() == 3)
    await pg.click('.title .sb.blue', force=True); await pg.wait_for_selector('.mmap .isl'); await pg.wait_for_timeout(500)
    await shot(pg, f'{t}_02_map')
    check(f'[{t}] math map: 4 islands, only the first open', await pg.locator('.isl').count() == 4 and await pg.locator('.isl.locked').count() == 3)
    geo = await pg.evaluate("(()=>{const r=[...document.querySelectorAll('.isl')].map(e=>e.getBoundingClientRect()),H=innerHeight,W=innerWidth,t=document.querySelector('.mtitle').getBoundingClientRect();"
                            "let over=0;for(let i=0;i<r.length;i++)for(let j=i+1;j<r.length;j++){const a=r[i],b=r[j];if(a.left<b.right&&b.left<a.right&&a.top<b.bottom&&b.top<a.bottom)over++}"
                            "return {over,inside:r.every(x=>x.left>=-2&&x.right<=W+2&&x.bottom<=H+2),titleClear:r.every(x=>x.top>=t.bottom-4||x.right<t.left||x.left>t.right)}})()")
    check(f'[{t}] math map: islands do not overlap, stay on screen and below the title', geo['over'] == 0 and geo['inside'] and geo['titleClear'], geo)
    await pg.locator('.isl.locked').first.click(); await pg.wait_for_timeout(300)
    check(f'[{t}] a locked math island explains itself', await pg.locator('#toast.on').count() == 1)
    await pg.click('.isl.i1'); await pg.wait_for_selector('.lvrow'); await pg.wait_for_timeout(400)
    await shot(pg, f'{t}_03_island')
    check(f'[{t}] math island 1 lists 3 levels', await pg.locator('.lvrow').count() == 3)
    got = 0
    got += await level(pg, 1, 'pizza', f'{t}_04_pizza1', wrong_first=True)
    got += await level(pg, 1, 'sling', f'{t}_05_sling1', wrong_first=True)
    got += await level(pg, 1, 'sheet', f'{t}_06_sheet1', wrong_first=True)
    check(f'[{t}] island 1: stars earned', got >= 6, got)
    await pg.evaluate("location.hash='math'"); await pg.wait_for_selector('.mmap .isl'); await pg.wait_for_timeout(400)
    check(f'[{t}] island 2 opens after island 1', await pg.locator('.isl.i2.locked').count() == 0)
    plan = [(2, 'pizza'), (2, 'sling'), (2, 'sheet'), (3, 'pizza'), (3, 'sling'), (3, 'sheet'), (4, 'sheet'), (4, 'sling')] if full else [(2, 'pizza'), (3, 'pizza'), (4, 'sheet')]
    if not full:   # a short run opens the later islands directly
        await pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('aam-unit1-v1'));s.m.st={'1-pizza':3,'1-sling':3,'1-sheet':3,'2-pizza':3,'2-sling':3};localStorage.setItem('aam-unit1-v1',JSON.stringify(s))})()")
        await pg.reload(); await pg.wait_for_timeout(800)
    for isl, typ in plan:
        await level(pg, isl, typ, f'{t}_{isl}_{typ}' if isl in (3, 4) or typ == 'pizza' else None)
    await pg.evaluate("location.hash='math'"); await pg.wait_for_selector('.mmap .isl'); await pg.wait_for_timeout(500)
    await shot(pg, f'{t}_09_map_after')
    check(f'[{t}] all four math islands open at the end', await pg.locator('.isl.locked').count() == 0)
    saved = await pg.evaluate("JSON.parse(localStorage.getItem('aam-unit1-v1')).m")
    check(f'[{t}] math progress is saved with the account record (S.m)', isinstance(saved, dict) and len(saved.get('st', {})) >= 4, saved)
    # the English world is untouched and reachable both ways
    await pg.click('[data-to=""]'); await pg.wait_for_selector('.title .sb'); await pg.click('.title .sb.green', force=True); await pg.wait_for_selector('.map .isl')
    check(f'[{t}] the English map still has its 6 islands, and math stars do not count there', await pg.locator('.isl').count() == 6 and '0 / 66' in await pg.locator('.sign.total').inner_text())
    await shot(pg, f'{t}_10_english_map')
    check(f'[{t}] the English map has a way back to the subjects', await pg.locator('.subjpill').count() == 1)
    await c.close()


async def main():
    procs = P.start_servers()
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await run(b, 390, 844, not QUICK, errs)
            if not QUICK:
                await run(b, 360, 740, False, errs)
                await run(b, 1366, 640, False, errs, laptop=True)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors or failed requests', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
