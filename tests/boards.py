#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The class and grade boards of 'supabase' mode (js/boards.js, docs/SIGNIN.md section 5, mock docs/mock/boards.html)
in the game, against the stand-in Supabase (tests/sb_standin.py; never a real project). Names are made up.
Checked:
  - the class board: the heading "הכיתה שלנו", rank, name (first name and letter), points (LTR); the pupil's own row
    in gold; no grade tab when the grade's board is empty (the trial class has no grade);
  - the grade board: the tabs "הכיתה" / "השכבה", "כל השכבה", the class as its own tag; up to 10 rows, and the
    pupil's own row under a thin line with its rank when further down;
  - a long Latin name: only the first name is cut, the letter whole; a name that is markup is shown as text;
  - the read is GET /rest/v1/rpc/grade_board with the session; the back arrow goes to the map;
  - 390 x 844, 360 x 740, 320 x 568: right to left, no sideways scroll, every target at least 44 px;
  - with the Sheet's config (today's class) the old board, unchanged (no js/boards.js fetched).
    python3 tests/boards.py [--shots DIR]"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
import play as P
from play import check, fails
from sb_standin import Project
from supabase_mode import device, enter

SHOTS = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
CLS = [dict(display_name=n, points=p, words=0, streak=0, me=n == 'Testa') for n, p in
       (('נועה כ.', 412), ('יואב ו.', 388), ('Testa', 351), ('דנה ש.', 297), ('<b>x</b> ק.', 120))]
NAMES = ['נועה כ.', 'יואב ו.', 'מאיה ל.', 'Alexandrina-Maximiliana K.', 'עומר ש.', 'תמר ד.', 'אורי ב.', 'שירה מ.', 'איתי ר.', 'ליה ג.', 'רון ח.', 'נגה פ.', 'Testa']
GRADE = [dict(display_name=n, **{'class': 'ה׳%d' % (i % 3 + 1)}, points=500 - i * 20, me=n == 'Testa') for i, n in enumerate(NAMES)]
# grade_board from 0011 (#134): at most the top ten and the caller's own row, in place order, each with its rank (ties share it)
RANKS = [1, 2, 2, 4, 5, 6, 7, 7, 9, 10]
GRADE11 = [dict(display_name=n, **{'class': 'ה׳1'}, points=400 - k * 10, me=False, rank=RANKS[k]) for k, n in enumerate(NAMES[:10])] + [dict(display_name='Testa', **{'class': 'ה׳2'}, points=120, me=True, rank=37)]


async def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))


async def open_board(b, prj, w=390, h=844):
    c, pg, errs = await device(b, prj)
    await pg.set_viewport_size({'width': w, 'height': h})
    r = await enter(pg, 'EN-0000', 'Testa', '4827')
    assert r == {'ok': True}, r
    await pg.goto(pg.url.split('#')[0] + '#board'); await pg.wait_for_selector('.scr.bd .bd-list, .scr.bd .bd-msg:not([role])', timeout=8000)
    return c, pg, errs


rows = lambda pg: pg.evaluate("[...document.querySelectorAll('.bd-list li')].map(li=>[li.querySelector('.bd-rk').textContent,li.querySelector('.bd-nm').textContent,(li.querySelector('.bd-cl')||{}).textContent||'',li.querySelector('.bd-pt').textContent,li.classList.contains('me')])")


async def main():
    procs = P.start_servers()
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            # 1. a class with no grade (the trial): the class board only
            prj = Project(); prj.boards['class'] = CLS
            c, pg, errs = await open_board(b, prj)
            check('class board: "הכיתה שלנו", no tabs (no grade board)', await pg.inner_text('.bd-h') == 'הכיתה שלנו' and await pg.locator('.bd-tabs').count() == 0)
            r = await rows(pg)
            check('the rows: rank, the name with its letter, the points; my row in gold; a name that is markup shown as text',
                  r == [['1', 'נועה כ.', '', '412', False], ['2', 'יואב ו.', '', '388', False], ['3', 'Testa', '', '351', True], ['4', 'דנה ש.', '', '297', False], ['5', '<b>x</b> ק.', '', '120', False]], r)
            check('points LTR, gold outline on my row', await pg.evaluate("[getComputedStyle(document.querySelector('.bd-pt')).direction,getComputedStyle(document.querySelector('li.me')).borderTopWidth]") == ['ltr', '2px'])
            reads = [(l['path'], l['method'], l['auth'][:7]) for l in prj.log if 'board' in l['path']]
            check('both reads with the session: class_board and rpc/grade_board (GET)', ('/rest/v1/class_board', 'GET', 'Bearer ') in reads and ('/rest/v1/rpc/grade_board', 'GET', 'Bearer ') in reads, reads)
            await shot(pg, 'b1-class')
            await pg.click('.bd-back'); await pg.wait_for_selector('.scr.map, .scr.title', timeout=8000)
            check('the back arrow: the map', await pg.locator('.scr.map').count() == 1)
            check('no page error', not errs, errs)
            await c.close()
            # 2. a class in a grade: both tabs
            for w, h in ((390, 844), (360, 740), (320, 568)):
                prj = Project(); prj.boards['class'] = CLS; prj.boards['grade'] = GRADE
                c, pg, errs = await open_board(b, prj, w, h)
                check(f'{w}: the tabs "הכיתה" / "השכבה", the class one chosen', await pg.evaluate("[...document.querySelectorAll('.bd-tab')].map(t=>t.textContent+':'+t.getAttribute('aria-selected'))") == ['הכיתה:true', 'השכבה:false'])
                await pg.click('.bd-tab[data-bt="grade"]'); await pg.wait_for_selector('.bd-cl')
                r = await rows(pg)
                check(f'{w}: grade board: "כל השכבה", 10 rows with the class tag, then mine under a line with its rank 13',
                      await pg.inner_text('.bd-h') == 'כל השכבה' and len(r) == 11 and r[0] == ['1', 'נועה כ.', 'ה׳1', '500', False] and r[-1] == ['13', 'Testa', 'ה׳1', '260', True]
                      and await pg.locator('.bd-sep').count() == 1 and sum(1 for x in r if x[4]) == 1, r)
                m = await pg.evaluate("""()=>{const li=[...document.querySelectorAll('.bd-list li')][3],fn=li.querySelector('.bd-fn'),ln=li.querySelector('.bd-ln'),cl=li.querySelector('.bd-cl'),pt=li.querySelector('.bd-pt');
                  const small=[...document.querySelectorAll('.scr.bd button')].filter(e=>{const r=e.getBoundingClientRect();return r.height<44||r.width<44}).map(e=>e.className);
                  return {cut:fn.scrollWidth>fn.clientWidth,ln:ln.scrollWidth<=ln.clientWidth+1,cl:cl.scrollWidth<=cl.clientWidth+1,pt:pt.getBoundingClientRect().left>=0,
                    sideways:document.documentElement.scrollWidth>innerWidth,dir:getComputedStyle(document.querySelector('.scr.bd')).direction,small}}""")
                check(f'{w}: a long Latin name: only the first name cut ({"cut" if m["cut"] else "fits"}), the letter, the class tag and the points whole; RTL, no sideways scroll, targets ≥ 44 px',
                      m['ln'] and m['cl'] and m['pt'] and not m['sideways'] and m['dir'] == 'rtl' and not m['small'] and (m['cut'] or w == 390), m)
                m = await pg.evaluate("(()=>{const r=document.querySelector('.bd-mine li.me').getBoundingClientRect();return {bottom:Math.round(r.bottom),top:Math.round(r.top),H:innerHeight}})()")
                check(f'{w}: my own row (rank 13) is on screen without scrolling, under the list', m['top'] >= 0 and m['bottom'] <= m['H'], m)
                await shot(pg, f'b2-grade-{w}')
                await pg.click('.bd-tab[data-bt="class"]'); await pg.wait_for_function("document.querySelector('.bd-h').textContent==='הכיתה שלנו'")
                check(f'{w}: back to the class tab', await pg.locator('.bd-cl').count() == 0)
                check(f'{w}: no page error', not errs, errs)
                await c.close()
            # 3. grade_board from 0011: the server's rank (ties shared), and my row from the server as the 11th
            prj = Project(); prj.boards['class'] = CLS; prj.boards['grade'] = GRADE11
            c, pg, errs = await open_board(b, prj, 360, 740)
            await pg.click('.bd-tab[data-bt="grade"]'); await pg.wait_for_selector('.bd-cl')
            r = await rows(pg)
            check('the 0011 shape: the ranks are the server\'s (1,2,2,4…7,7,9,10), then my row with rank 37 under the line',
                  [x[0] for x in r] == ['1', '2', '2', '4', '5', '6', '7', '7', '9', '10', '37'] and r[-1][1] == 'Testa' and r[-1][4] and await pg.locator('.bd-mine li.me').count() == 1, r)
            reads = [l['path'] + '?' + l['query'] for l in prj.log if 'grade_board' in l['path']]
            check('the grade read names no columns (works before and after 0011)', reads == ['/rest/v1/rpc/grade_board?'], reads)
            await c.close()
            # 4. today's class (the Sheet), a pupil signed in: the old board, js/boards.js never fetched
            from sb_standin import SHEET_CFG, SHEET_ERA
            prj = Project(); c, pg, errs = await device(b, prj, cfg=SHEET_CFG, seed=SHEET_ERA)
            check('the Sheet pupil is signed in', await pg.evaluate("(async()=>{const m=await import('./js/state.js');return !!m.S.u&&!m.NEW})()"))
            got = []; pg.on('request', lambda r: got.append(r.url) if 'boards.' in r.url else None)
            await pg.goto(pg.url.split('#')[0] + '#board'); await pg.wait_for_selector('.scr.board', timeout=8000); await pg.wait_for_timeout(500)
            check("the Sheet's config, signed in: the old board; no js/boards.js and no css/boards.css fetched", not got and await pg.locator('.scr.bd').count() == 0 and await pg.locator('.scr.board').count() == 1, got)
            await c.close()
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
