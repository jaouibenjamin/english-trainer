#!/usr/bin/env python3
"""The settings screen on short phones: everything on the screen, nothing over anything else.

    python3 tests/settings_fit.py              # six window sizes, not signed in and signed in
    python3 tests/settings_fit.py --shots DIR  # also save a PNG of each

Signed in is drawn without a backend: the page is given a class address that the test itself answers with "no
connection", so the account panel shows and nothing leaves the machine."""
import asyncio, os, subprocess, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, new_page, port_open, fails

SIZES = [(390, 844), (412, 780), (360, 740), (360, 700), (360, 640), (1366, 768)]
FAKE = f'http://127.0.0.1:{P.PORT}/no-backend'
MEASURE = """(()=>{const s=document.getElementById('stage').getBoundingClientRect(),out=[];
 const parts=[...document.querySelectorAll('.settings>.top,.settings .panel,.settings>.guide')].filter(e=>e.getBoundingClientRect().height).map(e=>[e.className,e.getBoundingClientRect()]);
 for(const [n,r] of parts)if(r.bottom>s.bottom+1||r.top<s.top-1)out.push('off the screen: '+n);
 for(let i=0;i<parts.length;i++)for(let j=i+1;j<parts.length;j++){const a=parts[i][1],b=parts[j][1];
  /* the crab of the note may wave over a corner; its text box may not touch a panel */
  const bb=parts[j][0].includes('guide')?document.querySelector('.settings>.guide p').getBoundingClientRect():b;
  if(a.top<bb.bottom-2&&a.bottom>bb.top+2&&a.left<bb.right-2&&a.right>bb.left+2)out.push('overlap: '+parts[i][0]+' / '+parts[j][0])}
 const small=[...document.querySelectorAll('.settings .setrow,.settings .btn')].filter(e=>e.getBoundingClientRect().height<44).length;
 return {out,small,panels:document.querySelectorAll('.settings .panel').length}})()"""


async def one(b, w, h, signed, errs):
    tag = f"{'signed in' if signed else 'not signed in'} {w}x{h}"
    c, pg = await new_page(b, w, h, api=FAKE if signed else None, errs=errs)
    if signed:
        await pg.route('**/no-backend', lambda r: r.fulfill(content_type='application/json', body='{"ok":false,"e":"net"}'))
        await pg.add_init_script("localStorage.setItem('aam-unit1-v1',JSON.stringify({u:{c:'EN-0000',n:'נטע',p:'0000'}}))")
    await pg.goto(P.BASE + '#settings'); await pg.wait_for_selector('.scr.settings'); await pg.wait_for_timeout(500)
    m = await pg.evaluate(MEASURE)
    check(f'[{tag}] settings: everything is on the screen and nothing lies over anything', not m['out'], m['out'])
    check(f'[{tag}] settings: every row and button is at least 44 px high', m['small'] == 0, m['small'])
    check(f'[{tag}] settings: the account panel is {"there" if signed else "not there"}', m['panels'] == (4 if signed else 3), m['panels'])
    if signed:
        check(f'[{tag}] settings: the sign-out button is whole and can be pressed', await pg.evaluate("(()=>{const b=document.querySelector('[data-a=logout]').getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect();return b.bottom<=s.bottom&&b.top>=s.top})()"))
    await P.shot(pg, f"settings-{'signed-in' if signed else 'local'}-{w}x{h}")
    await c.close()


async def main():
    procs = P.start_servers(mock=False)      # its own servers on free ports (tests/play.py)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            for signed in (False, True):
                for w, h in SIZES:
                    await one(b, w, h, signed, errs)
            await b.close()
    finally:
        for p in procs: p.terminate()
    check('no page errors, console errors or requests to another host', not errs, errs[:6])
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
