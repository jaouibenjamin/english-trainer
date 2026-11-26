#!/usr/bin/env python3
# suite: quick=--quick   # picked up by tests/all.py
"""The previous ship's files mixed with this one's: no screen breaks while a phone still has old files in its cache.

    python3 tests/cache_mix.py               # every mix, every screen, the design flag off and on
    python3 tests/cache_mix.py --quick       # one old file at a time, title, map and the collection
    python3 tests/cache_mix.py --prev REF    # another previous ship than PREV_SHIP below
    python3 tests/cache_mix.py --only "teacher page,worksheet"   # every mix, these screens only

GitHub Pages lets a browser keep each file for 10 minutes (max-age=600), so for a while after a ship a phone can run the
new page with an old module, or an old page with new ones. A new named export that an old copy does not have, a renamed
file, a changed function, a new contract between two files: any of them can break a screen for that pupil.

Without a browser (tests/mixcheck.py, on tests/jsmods.py's strict tokenizer; the rules are in mixcheck's docstring):
every import and export form is one it knows; an export added since the previous ship is never bound by name, and every
read of it through a module object is guarded at that read (typeof ..==='function' around it, or ?? right after a data
export); a module object it cannot follow fails; and every name the previous ship's modules import still exists here.
The exports added since the previous ship are listed with every use. A self-test feeds it one mutant per known blind
spot, and controls that must pass.

In the browser, for every js/, css/ and *.html file that differs between REF and this checkout and existed in REF:
  - that one file from REF, the rest from this checkout;
  - every such file from REF except that one (the other direction), and all of them from REF;
and, with the design flag off and on, the title, the map, the four level types, Fraction Bay's map and a level of it, the
collection, the mock exam, and the teacher, Beach Run and worksheet pages: each must be drawn with no page error, console
error or failed request, and with the flag on no picture may be left as a blank stand-in. Self-tests: a ui.js without a
named export must break the page; a ui.js that writes stand-ins for a main.js that cannot put them back must be seen.
Needs the previous ship in the local clone (`git fetch origin main`; the test says so and fails if it is missing)."""
import asyncio, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
import jsmods
from mixcheck import static_check
from play import check, fails, new_page
from playwright.async_api import async_playwright

QUICK = '--quick' in sys.argv
WANT = tuple(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else ()
# THE PREVIOUS SHIP: main's commit as the class has it now. Bump it with every ship (CLAUDE.md, "Branches and deploy").
PREV_SHIP = '72d80d3'
PREV = sys.argv[sys.argv.index('--prev') + 1] if '--prev' in sys.argv else PREV_SHIP
ROOT = P.ROOT
SCREENS = [('title', 'index.html#', '.scr.title .btn'), ('map', 'index.html#map', '.map .isl'), ('collection', 'index.html#collection', '.scr.coll'),
           ('sling', 'index.html#play/1/sling', '.lv'), ('listen', 'index.html#play/1/listen', '.lv'), ('read', 'index.html#play/1/read', '.lv'),
           ('bridge', 'index.html#play/1/bridge', '.lv'), ('Fraction Bay', 'index.html#math', '.scr.map .isl'), ('Fraction Bay level', 'index.html#mplay/1/pizza', '.lv'),
           ('mock exam', 'index.html#mock', '.scr.mockhub'), ('teacher page', 'teacher.html', '#msg:not(:empty)'), ('Beach Run', 'run.html', '#menu [data-go=run]'),
           ('worksheet', 'worksheet.html?i=1', '#sheet .page')]
# the worksheet is behind a device switch (js/worksheet.js): on for this test, so the sheet itself is drawn
INIT = {'worksheet': "localStorage.setItem('word-islands-settings-v1', JSON.stringify({sheet: true}))"}
if QUICK or WANT:
    SCREENS = [s for s in SCREENS if s[0] in (WANT or ('title', 'map', 'collection'))]
# with the design flag on, a stand-in still on a picture the new look does not draw over is a blank picture
BLANK = """()=>[...document.querySelectorAll('img[srcset^="data:image/svg"]')].filter(im=>{const cs=getComputedStyle(im);
 return !(cs.backgroundImage.includes('url(')&&(cs.objectPosition.startsWith('-9999')||cs.height==='0px'))}).map(im=>im.getAttribute('src'))"""


def git(*a):
    return subprocess.run(['git', *a], cwd=ROOT, capture_output=True)


def changed():
    """the files a page loads that differ between PREV and this checkout, and exist in PREV"""
    out = git('diff', '--name-only', PREV, '--', 'js', 'css', '*.html').stdout.decode().split()
    return [f for f in out if re.fullmatch(r'(js/[\w.-]+\.js|css/[\w.-]+\.css|[\w-]+\.html)', f) and git('cat-file', '-e', f'{PREV}:{f}').returncode == 0]


# ---------- without a browser: tests/mixcheck.py ----------


MUTANTS = [   # (what, now {file: src}, prev {file: src}): each must be reported (bad or unknown)
    ('a second name in export const a=..,NEW=..', {'ui.js': 'export const a=1,NEW=2;', 'main.js': "import {NEW} from './ui.js';"}, {'ui.js': 'export const a=1;', 'main.js': ''}),
    ('a re-export of a new name', {'ui.js': 'export const NEW=2;export const a=1;', 'state.js': "export {NEW} from './ui.js';", 'main.js': ''}, {'ui.js': 'export const a=1;', 'state.js': '', 'main.js': ''}),
    ('import(..).then(m=>m.newFn())', {'avatar.js': 'export function newFn(){}export function old(){}', 'main.js': "import('./avatar.js').then(m=>m.newFn());"}, {'avatar.js': 'export function old(){}', 'main.js': ''}),
    ('an alias of a dynamically imported module', {'avatar.js': 'export function newFn(){}', 'main.js': "let AV;import('./avatar.js').then(m=>{AV=m});function f(){AV.newFn()}"}, {'avatar.js': '', 'main.js': ''}),
    ('an import as the second statement on a line', {'ui.js': 'export const NEW=1;', 'main.js': "const x=1;import {NEW} from './ui.js';"}, {'ui.js': '', 'main.js': ''}),
    ('an indented import', {'ui.js': 'export const NEW=1;', 'main.js': "   import {NEW} from './ui.js';"}, {'ui.js': '', 'main.js': ''}),
    ('export {q as zz} not at the start of a line', {'ui.js': 'const q=1;const r=2;export {q as zz};', 'main.js': "import {zz} from './ui.js';"}, {'ui.js': '', 'main.js': ''}),
    ('a typeof guard elsewhere, the call unguarded', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';const ok=typeof UI.NEW==='function';UI.NEW();"}, {'ui.js': '', 'main.js': ''}),
    ('a destructured import()', {'avatar.js': 'export function newFn(){}', 'main.js': "import('./avatar.js').then(({newFn})=>newFn());"}, {'avatar.js': '', 'main.js': ''}),
    ('a bare read of a new data export', {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';const e=WD.ENERGY;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a new data export in a call argument, no fallback', {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';show(WD.ENERGY,1);"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a fallback that applies to a member, not the export', {'world_data.js': 'export const SOON={};', 'avatar.js': "import * as WD from './world_data.js';const s=WD.SOON.x||0;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a destructured namespace const {ENERGY}=WD', {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';const {ENERGY}=WD;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a renamed destructuring const {a,ENERGY:e}=WD', {'world_data.js': 'export const ENERGY=5;export const a=1;', 'avatar.js': "import * as WD from './world_data.js';const {a,ENERGY:e}=WD;"}, {'world_data.js': 'export const a=1;', 'avatar.js': ''}),
    ('an optional-chain read WD?.ENERGY', {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';const e=WD?.ENERGY;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a computed read WD[k]', {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';const e=WD['ENERGY'];"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a data export with || (it would turn a false flag true)', {'helpdata.js': 'export const GLOSSARY=false;', 'help.js': "import * as HD from './helpdata.js';const g=HD.GLOSSARY||true;"}, {'helpdata.js': '', 'help.js': ''}),
    ('a read in the else branch of the guard', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';typeof UI.NEW==='function'?0:UI.NEW();"}, {'ui.js': '', 'main.js': ''}),
    ('a read after an if guard with an empty body', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';if(typeof UI.NEW==='function'){}UI.NEW();"}, {'ui.js': '', 'main.js': ''}),
    ('a guard joined by || before ?', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';const x=a||typeof UI.NEW==='function'?UI.NEW():0;"}, {'ui.js': '', 'main.js': ''}),
    ('an if guard joined by ||', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';if(a||typeof UI.NEW==='function'){UI.NEW()}"}, {'ui.js': '', 'main.js': ''}),
    ('a read after the && chain of the guard ends', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';typeof UI.NEW==='function'&&a||UI.NEW();"}, {'ui.js': '', 'main.js': ''}),
    ('a guard on another name', {'ui.js': 'export const NEW=()=>1;export const NEW2=()=>1;', 'main.js': "import * as UI from './ui.js';typeof UI.NEW2==='function'&&UI.NEW();"}, {'ui.js': '', 'main.js': ''}),
    ('a static namespace alias const U=UI', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';const U=UI;U.NEW();"}, {'ui.js': '', 'main.js': ''}),
    ('a static alias of a data namespace W2.ENERGY', {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';const W2=WD;const e=W2.ENERGY;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a chained .then(m=>m).then(x=>x.newFn())', {'avatar.js': 'export function newFn(){}', 'main.js': "import('./avatar.js').then(m=>m).then(x=>x.newFn());"}, {'avatar.js': '', 'main.js': ''}),
    ('a module object passed on f(UI)', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';f(UI);"}, {'ui.js': '', 'main.js': ''}),
    ("precedence: 'x'+WD.ENERGY??''", {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';const s='x'+WD.ENERGY??'';"}, {'world_data.js': '', 'avatar.js': ''}),
    ('precedence: 2*WD.ENERGY??1', {'world_data.js': 'export const ENERGY=5;', 'avatar.js': "import * as WD from './world_data.js';const s=2*WD.ENERGY??1;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('precedence: !WD.FLAG??1', {'world_data.js': 'export const FLAG=true;', 'avatar.js': "import * as WD from './world_data.js';const s=!WD.FLAG??1;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('a function export read as data WD.fn??0', {'world_data.js': 'export function fn(){}', 'avatar.js': "import * as WD from './world_data.js';(WD.fn??0)();"}, {'world_data.js': '', 'avatar.js': ''}),
    ('an arrow export read as data', {'world_data.js': 'export const fn=(a)=>a;', 'avatar.js': "import * as WD from './world_data.js';const f=WD.fn??null;"}, {'world_data.js': '', 'avatar.js': ''}),
    ('export {NEW as default} with import d from', {'ui.js': 'const NEW=1;export {NEW as default};', 'main.js': "import d from './ui.js';"}, {'ui.js': '', 'main.js': ''}),
    ("the previous ship's code imports a name that is gone", {'ui.js': 'export const b=1;', 'main.js': ''}, {'ui.js': 'export const a=1;', 'main.js': "import {a} from './ui.js';"}),
    ("the previous ship's code imports a module that is gone", {'main.js': ''}, {'old.js': 'export const a=1;', 'main.js': "import {a} from './old.js';"}),
    ('export default (a form it does not know)', {'ui.js': 'export default 1;', 'main.js': ''}, {'ui.js': '', 'main.js': ''}),
    ('export * (a form it does not know)', {'ui.js': "export * from './state.js';", 'main.js': ''}, {'ui.js': '', 'main.js': ''}),
    ('a destructuring export (a form it does not know)', {'ui.js': 'export const {a,b}=o;', 'main.js': ''}, {'ui.js': '', 'main.js': ''}),
]
CONTROLS = [   # the same shapes written safely: none may be reported
    ('a new export read through the namespace with a guard at the use', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';const f=n=>typeof UI.NEW==='function'?UI.NEW(n):'';"}, {'ui.js': '', 'main.js': ''}),
    ('a new data export read with ?? fallbacks', {'world_data.js': 'export const ENERGY=5;export const SOON=[];', 'avatar.js': "import * as WD from './world_data.js';const e=WD.ENERGY??3,s=f(WD.SOON??[]),o={a:WD.ENERGY??0};"}, {'world_data.js': '', 'avatar.js': ''}),
    ('guards that cover the read: the if body, the && rest, a ?: true branch', {'ui.js': 'export const NEW=()=>1;', 'main.js': "import * as UI from './ui.js';if(typeof UI.NEW==='function'&&ok){UI.NEW()}typeof UI.NEW==='function'&&UI.NEW(1);const x=ok&&typeof UI.NEW==='function'?UI.NEW():0;"}, {'ui.js': '', 'main.js': ''}),
    ('an alias that is only tested and read guarded', {'avatar.js': 'export function newFn(){}', 'main.js': "let AV=null;import('./avatar.js').then(m=>{AV=m});function f(){if(AV&&typeof AV.newFn==='function')AV.newFn()}"}, {'avatar.js': '', 'main.js': ''}),
    ('a module with nothing new, passed on in an object', {'sling.js': 'export const a=1;', 'main.js': "import * as sling from './sling.js';const LV={sling};LV.sling.a;"}, {'sling.js': 'export const a=1;', 'main.js': ''}),
    ('a guarded dynamic read', {'avatar.js': 'export function newFn(){}', 'main.js': "import('./avatar.js').then(m=>{if(typeof m.newFn==='function')m.newFn()});"}, {'avatar.js': '', 'main.js': ''}),
]


async def screen(b, path, sel, served, ds, init=None):
    """open one page with the files in `served` (path -> bytes) instead of this checkout's; (errors, blank pictures)"""
    errs = []
    c, pg = await new_page(b, 390, 844, errs=errs)
    if init:
        await pg.add_init_script(init)
    for f, body in served.items():
        typ = 'text/html; charset=utf-8' if f.endswith('.html') else 'text/css' if f.endswith('.css') else 'text/javascript'
        await pg.route('**/' + f, serve(body, typ))
    url = path
    if ds:
        url = path.replace('#', '?ds=1#', 1) if '#' in path else path + ('&' if '?' in path else '?') + 'ds=1'
    blank = []
    try:
        await pg.goto(P.BASE.rsplit('/', 1)[0] + '/' + url)
        await pg.wait_for_selector(sel, timeout=12000)
        await pg.wait_for_timeout(700)
        if ds:
            blank = await pg.evaluate(BLANK)
    except Exception as e:
        errs.append(f'not drawn: {sel} ({str(e).splitlines()[0][:80]})')
    await c.close()
    return errs, blank


def serve(body, typ):
    async def h(route, request=None):
        await route.fulfill(status=200, content_type=typ, body=body)
    return h


async def main():
    if git('cat-file', '-e', PREV + '^{commit}').returncode:
        check(f'the previous ship ({PREV}) is in this clone (run: git fetch origin main)', False)
        print(f"\n{len(fails)} FAILED: " + '; '.join(fails)); sys.exit(1)
    files = changed()
    print(f'previous ship {PREV} = {git("rev-parse", "--short", PREV).stdout.decode().strip()}; {len(files)} files differ and existed then: {", ".join(files)}')
    # ---------- without a browser ----------
    for what, now, prev in MUTANTS:
        bad, added, unknown = static_check(now, prev)
        check(f'static self-test, a mutant: {what} is reported', bool(bad or unknown), (bad, unknown))
    for what, now, prev in CONTROLS:
        bad, added, unknown = static_check(now, prev)
        check(f'static self-test, a control: {what} is not reported', not bad and not unknown, (bad, unknown))
    js = sorted(f for f in os.listdir(os.path.join(ROOT, 'js')) if f.endswith('.js'))
    now = {f: open(os.path.join(ROOT, 'js', f), encoding='utf-8').read() for f in js}
    prev = {f: git('show', f'{PREV}:js/{f}').stdout.decode() for f in js if git('cat-file', '-e', f'{PREV}:js/{f}').returncode == 0}
    bad, added, unknown = static_check(now, prev)
    check(f'every import and export in js/ (now and in the previous ship) is a form the reader knows ({len(now)} + {len(prev)} modules)', not unknown, unknown[:5])
    for m, names in added.items():
        for n, uses in names.items():
            print(f'  new since the previous ship: js/{m} exports {n}; used: ' + ('; '.join(uses) or 'by no other module'))
    check(f'no export added since the previous ship is bound by name or read unguarded ({sum(len(v) for v in added.values())} added)', not bad, bad)
    # ---------- in the browser ----------
    procs = P.start_servers()
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            ui = open(os.path.join(ROOT, 'js', 'ui.js'), encoding='utf-8').read()
            broken = re.sub(r'^export const spr=', 'const spr=', ui, count=1, flags=re.M)
            e, _ = await screen(b, 'index.html#', '.scr.title .btn', {'js/ui.js': broken.encode()}, False)
            check('browser self-test: an old copy without a named export the new code imports is seen as a broken page', broken != ui and any('spr' in x for x in e), e[:3])
            ungated = ui.replace('globalThis.__wiSettles===true&&', '', 1)
            if 'js/main.js' in files:
                e, blank = await screen(b, 'index.html#collection', '.scr.coll', {'js/ui.js': ungated.encode(), 'js/main.js': git('show', f'{PREV}:js/main.js').stdout}, True)
                check('browser self-test: stand-ins written for a main.js that cannot put them back are seen as blank pictures', ungated != ui and bool(blank), (blank, e[:2]))
            mixes = [('this checkout alone', {})]
            olds = {f: git('show', f'{PREV}:{f}').stdout for f in files}
            for f in files:
                mixes.append((f'{f} from the previous ship', {f: olds[f]}))
            if not QUICK:
                for f in files:
                    mixes.append((f'every changed file from the previous ship except {f}', {g: olds[g] for g in files if g != f}))
                mixes.append(('every changed file from the previous ship', dict(olds)))
            for what, served in mixes:
                bad_here = []
                for ds in (False, True):
                    for name, path, sel in SCREENS:
                        e, blank = await screen(b, path, sel, served, ds, INIT.get(name))
                        if e or blank:
                            bad_here.append((name, 'flag on' if ds else 'flag off', e[:2], blank[:3]))
                check(f'{what}: {len(SCREENS)} screens, flag off and on, drawn with no error and no blank picture', not bad_here, bad_here[:4])
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
