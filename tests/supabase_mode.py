#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""'supabase' mode of the game (docs/PHASE3.md step 6) in a real browser, against a stand-in Supabase on the project's
address (never a real project).

    python3 tests/supabase_mode.py

The adapter's calls are tested without a browser in tests/api_check.mjs (section 9); this suite checks js/state.js on
the device, the three cases of docs/PHASE4.md A and the rest of step 6:
  - a device with the Sheet's progress signs in to the new backend and starts from the new record only; the Sheet's
    record on the device is untouched, and with the Sheet's config the game finds it again;
  - a device signed in to a trial class signs in to the real class: nothing of the trial comes along;
  - pupil A signs out, pupil B signs in on the same device: B gets nothing of A's, and A's record left the device;
  - the same pupil signs in again after the session ended: what the device played meanwhile is kept and saved;
  - the code goes to pupil-login only, and is in no storage of the device;
  - a reopened game reads the record with the session (no sign-in), and the board comes from Supabase.
  - register and recover (by the pictures, or the teacher's one-time code) through enter(), the seam with step 5; a
    lock's wait, scope and help reach the screen; a recovery signs the pupil's other device out.
  - the whole flow in the game: the sign-in screens of step 5 (js/signin.js) on the real page, register and sign in,
    through enter(), the adapter and the stand-in, to the game signed in.
The screens' own details are tests/signin.py's; the stand-in is tests/sb_standin.py, shared with it. The Content-Security-
Policy is bypassed here only, because the stand-in answers on the project's address. Names and codes are made up."""
import asyncio, json, os, re, sys, urllib.parse
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, fails

from sb_standin import SB, KEY, REAL, TRIAL, PA, PB, PT, CODES, PUPILS, NEW_CFG, SHEET_CFG, SHEET_ERA, Project
PAGE = f'http://127.0.0.1:{P.PORT}/index.html'
async def device(b, prj, cfg=NEW_CFG, seed=None, ctx=None):
    """a page of the game; ctx: the same device (browser storage) as an earlier page"""
    c = ctx or await b.new_context(viewport={'width': 390, 'height': 844}, bypass_csp=True)
    if not ctx:
        await c.route(SB + '/**', prj.route)
        if seed is not None:
            await c.add_init_script("if(!localStorage.getItem('seeded')){localStorage.setItem('seeded','1');localStorage.setItem('aam-unit1-v1',%s)}" % json.dumps(json.dumps(seed)))
    await c.unroute('**/config.js')
    await c.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body=cfg))
    pg = await c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(PAGE + '#map')
    await pg.wait_for_selector('.scr, .si')   # .si: the sign-in screens of step 5, once they are on game
    return c, pg, errs


ST = "(async()=>{const m=await import('./js/state.js');return (%s)})()"
js = lambda pg, expr: pg.evaluate(ST % expr)
enter = lambda pg, c, n, code: js(pg, f"m.enter('login',{{c:{json.dumps(c)},n:{json.dumps(n)},code:{json.dumps(code)}}})")
# every storage of the device except the Sheet's own record, which keeps its era's code for the way back (docs/PHASE4.md A)
storage = lambda pg: pg.evaluate("JSON.stringify([Object.entries(localStorage).filter(([k])=>k!=='aam-unit1-v1'&&k!=='seeded'),Object.entries(sessionStorage)])")


async def no_code(pg, prj, label):
    st = await storage(pg)
    # whole values only: a timestamp, or a segment of a random uuid (the session id, a batch id), may hold the digits
    hits = [st[max(0, m.start() - 80):m.end() + 20] for x in CODES for m in re.finditer(r'(?<![0-9a-f-])' + x + r'(?![0-9a-f-])', st)]
    check(f'{label}: no code in any storage of the device', not hits, hits)
    leaks = [l['path'] for l in prj.log if any(x in l['body'] + l['query'] for x in CODES) and l['path'] != '/functions/v1/pupil-login']
    check(f'{label}: the code went to pupil-login only', not leaks, leaks)


async def main():
    procs = P.start_servers()
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])

            # 1. a device with the Sheet's progress
            prj = Project()
            c, pg, errs = await device(b, prj, seed=SHEET_ERA)
            check("the Sheet's progress is not read in 'supabase' mode: nobody is signed in, nothing of it in S", await js(pg, "[m.NEW,m.KEY,m.S.u,m.S.pts]") == [True, 'wi-new-v1', None, 0])
            r = await enter(pg, 'EN-0000', 'Testa', '4827')
            check('sign in (the seam): ok', r == {'ok': True}, r)
            got = await js(pg, "[m.S.u,m.S.pts,m.S.st,m.S.who]")
            check('it starts from the new record only (zero), signed in as {c, n}, bound to its pupil and class', got == [{'c': 'EN-0000', 'n': 'Testa'}, 0, {}, {'p': PA, 'c': REAL}], got)
            old = await pg.evaluate("localStorage.getItem('aam-unit1-v1')")
            check("the Sheet's record on the device is untouched", json.loads(old) == SHEET_ERA, old)
            await no_code(pg, prj, 'after sign-in')
            pts = await js(pg, "(m.award(9),m.push(),m.S.pts)")
            await pg.wait_for_timeout(300)
            check('a save goes to Supabase with the session', pts > 0 and prj.state(PA)[0].get('pts') == pts, [pts, prj.state(PA)])
            await pg.close()
            _, pg, _ = await device(b, prj, cfg=SHEET_CFG, ctx=c)
            got = await js(pg, "[m.NEW,m.S.u&&m.S.u.n,m.S.pts,m.S.st]")
            check("the way back: with the Sheet's config the game finds the Sheet-era progress as it was", got == [False, 'Testa', 120, {'cat': [3, 0]}], got)
            await c.close()
            check('no page error', not errs, errs[:3])

            # 2. a trial class, then the real class, on one device
            prj = Project(); prj.progress[PA] = ({'pts': 7}, 'at-0')
            c, pg, _ = await device(b, prj)
            await enter(pg, 'TRIAL-01', 'Testa', '4827')
            await js(pg, "(m.award(15),m.S.st.dog=[2,0],m.saveLocal(),m.S.pts)")
            r = await enter(pg, 'EN-0000', 'Testa', '4827')
            got = await js(pg, "[m.S.pts,m.S.st,m.S.who.c,m.S.stash||null]")   # the Sheet's one slot (stash) is never used in this mode
            check('trial class, then the real class with the same name: only the real record (7), nothing of the trial joined', r == {'ok': True} and got[:3] == [7, {}, REAL], got)
            check("the trial's unsaved play is kept aside for the trial pupil only", got[3] is None and (await js(pg, "(m.S.aside||[]).map(x=>[x.who,x.s.st.dog])")) == [[{'p': PT, 'c': TRIAL}, [2, 0]]], got[3])
            await c.close()

            # 3. pupil A signs out, pupil B signs in
            prj = Project()
            c, pg, _ = await device(b, prj)
            await enter(pg, 'EN-0000', 'Testa', '4827')
            await js(pg, "(m.award(10),m.S.st.cat=[2,1],m.push())")
            await pg.wait_for_timeout(300)
            out = await js(pg, "m.logout()")
            check('A signs out: allowed (everything was saved)', out is True, out)
            await pg.wait_for_timeout(500)
            check('the session was revoked on the server', any(l['path'] == '/auth/v1/logout' for l in prj.log), [l['path'] for l in prj.log])
            st = await storage(pg)
            check("A's record and session left the device", 'Testa' not in st and 'tok-aaaa' not in st, st[:300])
            await enter(pg, 'EN-0000', 'Probe', '5839')
            got = await js(pg, "[m.S.u.n,m.S.pts,m.S.st,m.S.who.p]")
            check("B signs in: B's own record only, nothing of A's", got == ['Probe', 0, {}, PB], got)
            await no_code(pg, prj, 'two pupils')
            await c.close()

            # 4. the session ends; the same pupil signs in again
            prj = Project()
            c, pg, _ = await device(b, prj)
            await enter(pg, 'EN-0000', 'Testa', '4827')
            await js(pg, "(m.award(5),m.push())")
            await pg.wait_for_timeout(300)
            saved = prj.state(PA)[0].get('pts')
            prj.dead = True
            await pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('wi-sb-session'));s.expires_at=1;localStorage.setItem('wi-sb-session',JSON.stringify(s))})()")
            local = await js(pg, "(m.award(6),m.push(),m.S.pts)")
            await pg.wait_for_timeout(300)
            got = await js(pg, "[m.needsRelogin(),m.syncState().err]")
            check("the session ended on the server: the game asks to sign in again ('signin')", got == [True, 'signin'], got)
            rl = await js(pg, "m.relogin()")
            check('relogin() gives class and name to fill in, and the reason', rl == {"c": "EN-0000", "n": "Testa", "e": "signin"}, rl)
            prj.dead = False
            await enter(pg, 'EN-0000', 'Testa', '4827')
            await pg.wait_for_timeout(3000)
            got = await js(pg, "[m.S.pts,m.needsRelogin()]")
            check('signed in again: what the device played meanwhile (beyond the last save) is kept, and saved', local > saved and got == [local, False] and prj.state(PA)[0].get('pts') == local, [saved, local, got, prj.state(PA)])
            await no_code(pg, prj, 'after the session ended')
            await c.close()

            # 4b. B1 (review of #111): who cannot be read after the new sign-in: nothing is lost, the sign-in does not count
            prj = Project()
            c, pg, _ = await device(b, prj)
            await enter(pg, 'EN-0000', 'Testa', '4827')
            await js(pg, "(m.award(5),m.push())"); await pg.wait_for_timeout(300)
            saved = prj.state(PA)[0].get('pts')
            prj.dead = True
            await pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('wi-sb-session'));s.expires_at=1;localStorage.setItem('wi-sb-session',JSON.stringify(s))})()")
            local = await js(pg, "(m.award(6),m.push(),m.S.pts)"); await pg.wait_for_timeout(300)
            await js(pg, "m.relogin()")
            prj.dead = False; prj.no_who = True
            r = await enter(pg, 'EN-0000', 'Testa', '4827')
            got = await js(pg, "[m.S.u,(m.S.aside||[]).map(x=>x.s.pts)[0]]")
            check("the pupil's own row cannot be read: the sign-in answers net, and the unsaved play is still put aside", r == {'ok': False, 'e': 'net'} and got == [None, local] and local > saved, [r, got, saved, local])
            prj.no_who = False
            await enter(pg, 'EN-0000', 'Testa', '4827'); await pg.wait_for_timeout(3000)
            check('signing in once it can be read: joined and saved', await js(pg, "m.S.pts") == local and prj.state(PA)[0].get('pts') == local, [local, prj.state(PA)])
            await c.close()

            # 4c. pupil A's unsaved play, then pupil B on the device: kept aside for A, never joined into B
            prj = Project()
            c, pg, _ = await device(b, prj)
            await enter(pg, 'EN-0000', 'Testa', '4827')
            await js(pg, "(m.award(5),m.push())"); await pg.wait_for_timeout(300)
            prj.dead = True
            await pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('wi-sb-session'));s.expires_at=1;localStorage.setItem('wi-sb-session',JSON.stringify(s))})()")
            local = await js(pg, "(m.award(6),m.S.st.owl=[1,0],m.push(),m.S.pts)"); await pg.wait_for_timeout(300)
            await js(pg, "m.relogin()")
            prj.dead = False
            await enter(pg, 'EN-0000', 'Probe', '5839')
            got = await js(pg, "[m.S.u.n,m.S.pts,m.S.st,(m.S.aside||[]).map(x=>x.who)]")
            check("B signs in: nothing of A's in B's game; A's unsaved play is kept aside for A", got == ['Probe', 0, {}, [{'p': PA, 'c': REAL}]], got)
            await js(pg, "m.logout()"); await pg.wait_for_timeout(300)
            await enter(pg, 'EN-0000', 'Testa', '4827'); await pg.wait_for_timeout(3000)
            got = await js(pg, "[m.S.pts,m.S.st.owl,m.S.aside||null]")
            check("A signs in again: A's play is joined and saved, and B never had it", got == [local, [1, 0], None] and prj.state(PA)[0].get('pts') == local and prj.state(PB)[0].get('pts') in (None, 0), [got, prj.state(PA), prj.state(PB)])
            await c.close()

            # 4c2. review of #111: A's play is aside, then B's own session ends with unsaved play: both kept, each for its pupil
            prj = Project()
            c, pg, _ = await device(b, prj)
            async def ended():
                prj.dead = True
                await pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('wi-sb-session'));s.expires_at=1;localStorage.setItem('wi-sb-session',JSON.stringify(s))})()")
            await enter(pg, 'EN-0000', 'Testa', '4827'); await js(pg, "(m.award(5),m.push())"); await pg.wait_for_timeout(300)
            await ended(); a_local = await js(pg, "(m.award(6),m.push(),m.S.pts)"); await pg.wait_for_timeout(300); await js(pg, "m.relogin()")
            prj.dead = False
            await enter(pg, 'EN-0000', 'Probe', '5839'); await js(pg, "(m.award(1),m.push())"); await pg.wait_for_timeout(300)
            await ended(); b_local = await js(pg, "(m.award(4),m.push(),m.S.pts)"); await pg.wait_for_timeout(300); await js(pg, "m.relogin()")
            prj.dead = False
            got = await js(pg, "(m.S.aside||[]).map(x=>[x.who.p,x.s.pts])")
            check('two pupils whose sessions ended, each with unsaved play: one place each, neither overwritten', sorted(got) == sorted([[PA, a_local], [PB, b_local]]), got)
            await enter(pg, 'EN-0000', 'Testa', '4827'); await pg.wait_for_timeout(3000)
            check("A signs in: A's own play (not B's) is joined and saved; B's stays aside", await js(pg, "m.S.pts") == a_local and prj.state(PA)[0].get('pts') == a_local and await js(pg, "(m.S.aside||[]).map(x=>x.who.p)") == [PB], [a_local, await js(pg, "[m.S.pts,m.S.aside]")])
            # at most four places, the oldest dropped first
            await js(pg, "(m.S.aside=[1,2,3,4].map(i=>({n:'x'+i,s:{pts:i},who:{p:'p'+i,c:'c'},at:i})),m.saveLocal())")
            await ended(); await js(pg, "(m.award(2),m.push())"); await pg.wait_for_timeout(300); await js(pg, "m.relogin()")
            got = await js(pg, "(m.S.aside||[]).map(x=>x.who.p)")
            check('at most four places kept aside, the oldest dropped first', got == ['p2', 'p3', 'p4', PA], got)
            prj.dead = False
            await c.close()

            # 4d. the same pupil id in another class is another record (bound to pupil and class, not the pupil alone)
            prj = Project(); prj.progress[PA] = ({'pts': 2}, 'at-0')
            c, pg, _ = await device(b, prj)
            await enter(pg, 'EN-0000', 'Testa', '4827')
            await js(pg, f"(m.S.who={{p:{json.dumps(PA)},c:{json.dumps(TRIAL)}}},m.award(4),m.saveLocal())")
            await enter(pg, 'EN-0000', 'Testa', '4827')
            got = await js(pg, "[m.S.pts,(m.S.aside||[]).map(x=>x.who.c)]")
            check('a record of the same pupil id in another class is not joined', got == [2, [TRIAL]], got)
            await c.close()

            # 4e. two tabs, two pupils (G4 in this mode): the replaced tab shows the dialog and sends nothing more
            prj = Project()
            c, pg, _ = await device(b, prj)
            await enter(pg, 'EN-0000', 'Testa', '4827')
            _, pg2, _ = await device(b, prj, ctx=c)
            await enter(pg2, 'EN-0000', 'Probe', '5839')
            await pg.wait_for_selector('#wi-displaced', timeout=5000)
            check('the first tab shows "someone else signed in on this device"', await pg.is_visible('#wi-displaced'))
            n0 = len(prj.log)
            await js(pg, "(m.award(3),m.push())"); await pg.wait_for_timeout(500)
            sent = [l['path'] for l in prj.log[n0:]]
            check("the replaced tab sends nothing more (its save would take the device back and end B's session)", not sent, sent)
            # the adapter's own guard, not only the game's: a save handed straight to it from the replaced tab sends nothing
            n0 = len(prj.log)
            r = await js(pg, "m.api('save',{c:'EN-0000',n:'Testa',s:{pts:99}})"); await pg.wait_for_timeout(500)
            sent = [l['path'] for l in prj.log[n0:]]
            check("a save handed to the adapter in the replaced tab: refused, no request at all", r == {'ok': False, 'e': 'net'} and not sent, [r, sent])
            r = await js(pg2, "(m.award(2),m.push())"); await pg2.wait_for_timeout(500)
            check("B's tab still saves with B's session", r is True and prj.state(PB)[0].get('pts', 0) > 0, [r, prj.state(PB)])
            await c.close()

            # 5. a reopened game: the record with the session, the board from Supabase
            prj = Project(); prj.progress[PB] = ({'pts': 30}, 'at-0')
            c, pg, _ = await device(b, prj)
            await enter(pg, 'EN-0000', 'Testa', '4827')
            await pg.close()
            prj.progress[PA] = ({'pts': 21, 'st': {'cat': [1, 0]}}, 'at-9')   # played on another device meanwhile
            n0 = len(prj.log)
            _, pg, _ = await device(b, prj, ctx=c)
            await pg.wait_for_timeout(1000)
            paths = [l['path'] for l in prj.log[n0:]]
            check('reopened: no sign-in, the record is read with the session', '/rest/v1/progress' in paths and '/functions/v1/pupil-login' not in paths, paths)
            got = await js(pg, "[m.S.pts,m.S.st]")
            check("and joined with the device's (the other device's play is here)", got == [21, {'cat': [1, 0]}], got)
            await pg.goto(PAGE + '#board')
            # the board of 'supabase' mode is js/boards.js's (.scr.bd, tests/boards.py)
            await pg.wait_for_function("document.querySelector('.scr.bd')&&document.querySelector('.scr.bd').textContent.includes('Probe')", timeout=8000)
            txt = await pg.text_content('.scr.bd')
            check('the board comes from Supabase: both pupils of the class', 'Probe' in txt and 'Testa' in txt, txt[:200])
            await no_code(pg, prj, 'reopened')
            await c.close()
            # 6. register and recover through the seam; the server's word, and a lock's wait, scope and help, reach the screen
            prj = Project()
            c, pg, _ = await device(b, prj)
            ent = lambda kind, f: js(pg, f"m.enter({json.dumps(kind)},{json.dumps(f)})")
            got = [await ent('register', {'c': 'EN-0000', 'n': 'Newbie', 'code': '1234', 'pics': [2, 9]}),
                   await ent('register', {'c': 'EN-0000', 'n': 'Zed', 'code': '4826', 'pics': [2, 9]}),
                   await ent('register', {'c': 'EN-0000', 'n': 'Testa', 'code': '4826', 'pics': [2, 9]})]
            check('register refused: weak code, not on the class list, name taken', got == [{'ok': False, 'e': e} for e in ('weak', 'roster', 'taken')], got)
            r = await ent('register', {'c': 'EN-0000', 'n': 'Newbie', 'code': '4826', 'pics': [2, 9]})
            got = await js(pg, "[m.S.u,m.S.pts,!!(m.S.who&&m.S.who.p)]")
            check('register: in, from zero, bound to the new pupil', r == {'ok': True} and got == [{'c': 'EN-0000', 'n': 'Newbie'}, 0, True], [r, got])
            reg = [l for l in prj.log if l['path'] == '/functions/v1/pupil-register'][-1]
            check('register sends class code, name, code and the two pictures in order, and nothing else', json.loads(reg['body']) == {'class_code': 'EN-0000', 'name': 'Newbie', 'code': '4826', 'pictures': [2, 9]}, reg['body'])
            await js(pg, "m.logout()"); await pg.wait_for_timeout(300)
            c2, pg2, _ = await device(b, prj)   # Testa's other device, signed in
            await enter(pg2, 'EN-0000', 'Testa', '4827')
            r = await ent('recover', {'c': 'EN-0000', 'n': 'Testa', 'newCode': '7395', 'newPics': [1, 2], 'pics': [4, 5]})
            check('recover with the wrong pictures: "picture"', r == {'ok': False, 'e': 'picture'}, r)
            r = await ent('recover', {'c': 'EN-0000', 'n': 'Testa', 'newCode': '7395', 'newPics': [1, 2], 'pics': [3, 17]})
            check('recover with the right pictures: in, with the new code', r == {'ok': True} and await js(pg, "m.S.u.n") == 'Testa', r)
            await js(pg2, "(m.award(1),m.push())"); await pg2.wait_for_timeout(500)
            check("the pupil's other device is signed out: its next save asks to sign in again", await js(pg2, "[m.needsRelogin(),m.syncState().err]") == [True, 'signin'])
            prj.otc[('EN-0000', 'testa')] = '482913'
            r = await ent('recover', {'c': 'EN-0000', 'n': 'Testa', 'newCode': '8462', 'newPics': [6, 7], 'otc': '482913'})
            rec = [json.loads(l['body']) for l in prj.log if l['path'] == '/functions/v1/pupil-recover'][-1]
            check("recover with the teacher's one-time code: in; the old pictures are not sent", r == {'ok': True} and 'pictures' not in rec and rec['otc'] == '482913', [r, rec])
            prj.lock = {'wait': 900, 'by': 'address', 'help': 'teacher'}
            r = await enter(pg, 'EN-0000', 'Testa', '8462')
            check("locked: the screen gets the wait, whom it is for, and who can end it", r == {'ok': False, 'e': 'locked', 'wait': 900, 'by': 'address', 'help': 'teacher'}, r)
            st = await storage(pg) + await storage(pg2)
            hits = [(x, st[max(0, st.find(x) - 60):st.find(x) + 10]) for x in ('4826', '7395', '8462', '4827', '482913') if re.search(r'(?<![0-9a-f-])' + x + r'(?![0-9a-f-])', st)]
            check('register and recover: no code, old or new, in any storage of either device', not hits, hits)
            await c.close(); await c2.close()
            # the Sheet's class (today's): the map has no pill row and nothing moves
            prj0 = Project(); c0, pg0, e0 = await device(b, prj0, cfg=SHEET_CFG, seed=SHEET_ERA)
            await pg0.goto(PAGE + '#map'); await pg0.wait_for_selector('.scr.map', timeout=8000)
            check("the Sheet's class: no pill row on the map, no 'who' class (the islands where they were)", await pg0.locator('.maprow-who').count() == 0 and await pg0.locator('.scr.map.who').count() == 0 and await pg0.locator('.si-who').count() == 0)
            # nothing moved for the Sheet's class: the top island at the map's own margin, the subjects button where css/math.css puts it
            for w, h, mt0 in ((390, 844, 100), (360, 740, 100), (320, 568, 88)):
                await pg0.set_viewport_size({'width': w, 'height': h}); await pg0.goto(PAGE + '#title'); await pg0.goto(PAGE + '#map'); await pg0.wait_for_selector('.scr.map .isl.i6', timeout=8000)
                g = await pg0.evaluate("[document.querySelector('.isl.i6').style.top,getComputedStyle(document.querySelector('.subjpill')).top]")
                check(f"the Sheet's class at {w}: the top island at {mt0}px and the subjects button at 70px, as before", g == [f'{mt0}px', '70px'], g)
            await c0.close()
            # 7. the whole flow in the game: the sign-in screens (js/signin.js) on the real page, enter(), the adapter, the stand-in
            prj = Project()
            c, pg, errs = await device(b, prj)
            await pg.goto(PAGE + '#login'); await pg.wait_for_selector('.si[data-scr="entry"]')
            check('in the game, signed out: the sign-in screens of step 5', await pg.is_visible('.si[data-scr="entry"]'))
            tap = lambda sel: pg.locator(sel).first.click()
            async def main_btn():
                await tap('.si-bar .wi-btn--block')
                await pg.wait_for_function("!document.querySelector('.si-bar .wi-btn--block')||!document.querySelector('.si-bar .wi-btn--block').textContent.includes('רגע')", timeout=8000)
            async def keys(d):
                for k in d: await tap(f'.si-key[data-k="{k}"]')
            await tap('[data-si="start"][data-f="reg"]')
            await pg.fill('#si-c', 'EN-0000'); await pg.fill('#si-n', 'Newbie'); await main_btn()
            await keys('4826'); await keys('4826'); await main_btn()
            for n in (2, 9): await tap(f'.si-tile[data-no="{n}"]')
            await main_btn(); await main_btn()
            for n in (2, 9): await tap(f'.si-tile[data-no="{n}"]')
            await main_btn()
            await pg.wait_for_selector('.si[data-scr="done"]', timeout=8000)
            reg = [json.loads(l['body']) for l in prj.log if l['path'] == '/functions/v1/pupil-register']
            check('register through the screens: one request to pupil-register, with the pictures tapped, in order', reg == [{'class_code': 'EN-0000', 'name': 'Newbie', 'code': '4826', 'pictures': [2, 9]}], reg)
            await main_btn()
            await pg.wait_for_selector('.scr.title, .scr.map', timeout=8000)
            got = await js(pg, "[m.S.u,!!(m.S.who&&m.S.who.p)]")
            check('then the game, signed in as the new pupil (no code kept)', got == [{'c': 'EN-0000', 'n': 'Newbie'}, True], got)
            await js(pg, "m.logout()"); await pg.wait_for_timeout(300)
            await pg.goto(PAGE + '#login'); await pg.wait_for_selector('.si[data-scr="entry"]')
            await tap('[data-si="start"][data-f="in"]')
            await pg.fill('#si-c', 'EN-0000'); await pg.fill('#si-n', 'Testa'); await keys('1111'); await main_btn()
            check('a wrong code in the game: the screen says so, nothing signed in', 'לא נכונים' in (await pg.inner_text('.si')) and await js(pg, "m.S.u") is None)
            await keys('4827'); await main_btn()
            await pg.wait_for_selector('.scr.title, .scr.map', timeout=8000)
            check('sign in through the screens: the game, signed in as Testa', await js(pg, "m.S.u") == {'c': 'EN-0000', 'n': 'Testa'})
            await no_code(pg, prj, 'the whole flow in the game')
            check('the whole flow in the game: no page error', not errs, errs[:3])
            await c.close()
            # 8. a class of form first_initial (docs/GRADES_V1.md 0011): no letter, the server says so, the child adds it
            prj = Project()
            c, pg, errs = await device(b, prj)
            await pg.goto(PAGE + '#login'); await pg.wait_for_selector('.si[data-scr="entry"]')
            await tap('[data-si="start"][data-f="reg"]')
            await pg.fill('#si-c', 'GR-0001'); await pg.fill('#si-n', 'Noa'); await main_btn()
            await keys('4826'); await keys('4826'); await main_btn()
            for n in (2, 9): await tap(f'.si-tile[data-no="{n}"]')
            await main_btn(); await main_btn()
            for n in (2, 9): await tap(f'.si-tile[data-no="{n}"]')
            await main_btn()
            await pg.wait_for_selector('.si[data-scr="a1"] .si-err', timeout=8000)
            check('first_initial, no letter: the server answers e:name, the child is back on step 1 with the letter asked for',
                  'חסרה האות' in await pg.inner_text('.si-err') and await pg.get_attribute('#si-l', 'aria-required') == 'true' and await js(pg, "m.S.u") is None)
            await pg.fill('#si-l', 'k'); await main_btn()
            check('the code typed before is kept', await pg.input_value('#si-p') == '4826')
            await main_btn(); await main_btn(); await main_btn()
            for n in (2, 9): await tap(f'.si-tile[data-no="{n}"]')
            await main_btn()
            await pg.wait_for_selector('.si[data-scr="done"]', timeout=8000)
            reg = [json.loads(l['body']) for l in prj.log if l['path'] == '/functions/v1/pupil-register']
            check('the second request: "Noa K.", the same code and pictures', [r['name'] for r in reg] == ['Noa', 'Noa K.'] and reg[-1]['code'] == '4826' and reg[-1]['pictures'] == [2, 9], reg)
            await main_btn()
            await pg.wait_for_selector('.scr.title, .scr.map', timeout=8000)
            await pg.wait_for_selector('.si-who', timeout=8000)
            await pg.wait_for_timeout(400); who = await pg.evaluate("[...document.querySelectorAll('.si-who')].map(e=>e.textContent).join('|')")
            check('the game, signed in as "Noa K."; the pill shows the name and "זה לא אני · יציאה"', await js(pg, "m.S.u") == {'c': 'GR-0001', 'n': 'Noa K.'} and 'Noa\u00a0K.' in who and 'זה לא אני · יציאה' in who, [who, await js(pg, 'm.S.u')])
            # the title: the pill at the top of the screen (docs/mock/signin.html); with the design flag, the character chosen on this device
            await pg.goto(PAGE + '#title'); await pg.wait_for_selector('.scr.title .si-titletop .si-who', timeout=8000)
            m = await pg.evaluate("(()=>{const p=document.querySelector('.si-titletop'),s=document.querySelector('.scr.title');return {first:s.firstElementChild===p,top:Math.round(p.getBoundingClientRect().top),av:document.querySelectorAll('.si-av').length,n:document.querySelectorAll('.si-who').length}})()")
            check('the title: the pill is the first thing on the screen, at the top; one pill; no avatar without the design flag', m['first'] and m['top'] < 40 and m['av'] == 0 and m['n'] == 1, m)
            await pg.evaluate("""(async()=>{const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode('wi|GR-0001|Noa K.'));const k='h:'+[...new Uint8Array(d)].map(b=>b.toString(16).padStart(2,'0')).join('');localStorage.setItem('wi_world',JSON.stringify({v:1,p:{[k]:{av:'fox',nm:null,en:0}}}))})()""")
            await pg.goto(PAGE + '?ds=1#title'); await pg.wait_for_selector('.si-titletop .si-av', timeout=8000)
            src = await pg.get_attribute('.si-titletop .si-av', 'src')
            check('with the design flag: the character this pupil chose on this device is in the pill', '/av/fox' in src or 'fox' in src.split('/')[-1], src)
            await pg.goto(PAGE + '?ds=1#map'); await pg.wait_for_selector('.si-who', timeout=8000); await pg.wait_for_timeout(300)
            check('the map: one pill, with the character', await pg.locator('.si-who').count() == 1 and await pg.locator('.si-who .si-av').count() == 1)
            # the map: the pill in its own row under the header (docs/SIGNIN.md), at every width, in both looks
            for ds in ('?ds=1', '?ds=0'):
                for w, h in ((390, 844), (360, 740), (320, 568)):
                    await pg.set_viewport_size({'width': w, 'height': h})
                    await pg.goto(PAGE + ds + '#map'); await pg.wait_for_selector('.maprow-who .si-who', timeout=8000); await pg.wait_for_timeout(300)
                    m = await pg.evaluate("""(()=>{const r=s=>{const e=document.querySelector(s);return e?e.getBoundingClientRect():null},p=r('.maprow-who .si-who'),hd=r('.maphead'),sg=r('.maphead .sign.total'),sj=r('.subjpill'),i6=r('.isl.i6 .pw'),dk=r('.wd'),fn=document.querySelector('.si-who .si-fn'),b=document.querySelector('.si-who .si-nm');
                      const hit=(a,c)=>!!a&&!!c&&a.left<c.right&&c.left<a.right&&a.top<c.bottom&&c.top<a.bottom;
                      return {n:document.querySelectorAll('.si-who').length,belowHead:p.top>=hd.bottom-1,belowSign:p.top>=sg.bottom,aboveSubj:p.bottom<=sj.top+1,isl:hit(p,i6),dock:hit(p,dk),
                        name:fn.scrollWidth<=fn.clientWidth+1&&fn.clientWidth>0,btn:b.scrollWidth<=b.clientWidth+1&&b.getBoundingClientRect().height>=44,inside:p.left>=0&&p.right<=innerWidth}})()""")
                    check(f'map {ds} {w}: one pill, in its row under the header (below the stars sign) and above "מקצועות", over no island and not on the dock; the name whole, the button whole, on screen',
                          m['n'] == 1 and m['belowHead'] and m['belowSign'] and m['aboveSubj'] and not m['isl'] and not m['dock'] and m['name'] and m['btn'] and m['inside'], m)
            await pg.set_viewport_size({'width': 390, 'height': 844})
            await no_code(pg, prj, 'first_initial in the game')
            check('first_initial in the game: no page error', not errs, errs[:3])
            await c.close()
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
