#!/usr/bin/env python3
"""Play-through of the mock exam (מבחן דמו): exam with one try per question, the check-in report, practice for the
weak skill, the locked and then unlocked retake, and a clean second paper.

    python3 tests/mock.py              # 390x844, 360x740 and a laptop window
    python3 tests/mock.py --quick      # 390x844 only
    python3 tests/mock.py --shots DIR  # also save a PNG of every screen
"""
import asyncio, os, subprocess, sys, time
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
    procs = []
    if not port_open(P.PORT):
        procs.append(subprocess.Popen([sys.executable, '-m', 'http.server', str(P.PORT), '--bind', '127.0.0.1'], cwd=P.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for _ in range(40):
            if port_open(P.PORT): break
            time.sleep(.1)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            await run(b, 390, 844, errs)
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
