#!/usr/bin/env python3
# suite: quick=--quick   # picked up by tests/all.py
"""The previous ship's files mixed with this one's: no screen breaks while a phone still has old files in its cache.

    python3 tests/cache_mix.py               # every file that changed since the previous ship, one at a time
    python3 tests/cache_mix.py --quick       # the same, title and map only
    python3 tests/cache_mix.py --prev REF    # another previous ship than PREV_SHIP below

GitHub Pages lets a browser keep each file for 10 minutes (max-age=600), so for a while after a ship a phone can run the
new page with an old module, or an old page with a new one. A new named export that an old copy does not have, a
renamed file, a changed function signature: any of them breaks every screen for that pupil until the cache runs out.
For every js/, css/ and index.html file that differs between REF and this checkout, the test serves REF's copy of that
one file and this checkout's copy of everything else, and opens the title, the map, one level and the teacher screen:
each must be drawn with no page error, console error or failed request. A self-test first serves a copy of js/ui.js
without one named export and must see the page fail, so a pass means the check can see a break.
Also, without a browser: every named import of a module's export that the previous ship's copy of that module does not
have is listed and fails (it is exactly the break above); an export added since then must be read through the module's
namespace (`import * as UI`) with a fallback. The exports added since the previous ship, and how each is used, are listed.
Needs the previous ship in the local clone (`git fetch origin main`; the test says so and fails if it is missing)."""
import asyncio, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import play as P
from play import check, fails, new_page
from playwright.async_api import async_playwright

QUICK = '--quick' in sys.argv
# THE PREVIOUS SHIP: main's commit as the class has it now. Bump it with every ship (CLAUDE.md, "Branches and deploy").
PREV_SHIP = '13a3496'
PREV = sys.argv[sys.argv.index('--prev') + 1] if '--prev' in sys.argv else PREV_SHIP
ROOT = P.ROOT
SCREENS = [('title', '#', '.scr.title .btn'), ('map', '#map', '.map .isl'), ('level', '#play/1/sling', '.lv'), ('teacher', '#teacher', '.teacher')]
if QUICK:
    SCREENS = SCREENS[:2]


def git(*a):
    return subprocess.run(['git', *a], cwd=ROOT, capture_output=True)


def changed():
    """the files the page loads that differ between PREV and this checkout, and exist in PREV"""
    out = git('diff', '--name-only', PREV, '--', 'js', 'css', 'index.html').stdout.decode().split()
    return [f for f in out if re.fullmatch(r'(js/[\w.-]+\.js|css/[\w.-]+\.css|index\.html)', f) and git('cat-file', '-e', f'{PREV}:{f}').returncode == 0]


def serve(body, typ):
    async def h(route, request=None):
        await route.fulfill(status=200, content_type=typ, body=body)
    return h


EXPORT = re.compile(r'^export\s+(?:async\s+)?(?:const|let|var|function\*?|class)\s+([A-Za-z_$][\w$]*)|^export\s*\{([^}]*)\}', re.M)
IMPORT = re.compile(r'^import\s*\{([^}]*)\}\s*from\s*[\'"](\./[\w.-]+\.js)[\'"]', re.M)


def exports(src):
    out = set()
    for a, b in EXPORT.findall(src):
        if a: out.add(a)
        for part in b.split(','):
            part = part.strip()
            if part: out.add(part.split(' as ')[-1].strip())
    return out


def static_check():
    """named imports of exports the previous ship lacks (the break), and the exports added since (with their uses)"""
    bad, added = [], {}
    mods = sorted(f for f in os.listdir(os.path.join(ROOT, 'js')) if f.endswith('.js'))
    now = {f: open(os.path.join(ROOT, 'js', f), encoding='utf-8').read() for f in mods}
    for f in mods:
        old = git('show', f'{PREV}:js/{f}')
        if old.returncode: continue   # a module new since the previous ship: every importer of it is new too
        new_names = exports(now[f]) - exports(old.stdout.decode())
        if new_names: added[f] = {n: [] for n in sorted(new_names)}
    for f, src in now.items():
        for names, frm in IMPORT.findall(src):
            target = frm[2:]
            if target not in added: continue
            for part in names.split(','):
                n = part.strip().split(' as ')[0].strip()
                if n in added[target]:
                    bad.append(f'js/{f} imports {{{n}}} from {frm}'); added[target][n].append(f'js/{f}: named import (BREAKS)')
        for m in re.finditer(r'import\s*\*\s*as\s*(\w+)\s*from\s*[\'"](\./[\w.-]+\.js)[\'"]', src):
            ns, target = m.group(1), m.group(2)[2:]
            for n in added.get(target, {}):
                if re.search(r'\b' + ns + r'\.' + re.escape(n) + r'\b', src):
                    guarded = re.search(r'typeof\s+' + ns + r'\.' + re.escape(n) + r'\s*===?\s*[\'"]function[\'"]', src) is not None
                    added[target][n].append(f'js/{f}: through {ns}.{n}' + (' with a fallback' if guarded else ' WITHOUT a fallback'))
                    if not guarded: bad.append(f'js/{f} reads {ns}.{n} without a fallback')
    return bad, added


async def screen(b, path, sel, served):
    """open one screen with the files in `served` (path -> bytes) taking the place of this checkout's; the errors seen"""
    errs = []
    c, pg = await new_page(b, 390, 844, errs=errs)
    for f, body in served.items():
        typ = 'text/html; charset=utf-8' if f.endswith('.html') else 'text/css' if f.endswith('.css') else 'text/javascript'
        await pg.route('**/' + f, serve(body, typ))
    try:
        await pg.goto(P.BASE + path)
        await pg.wait_for_selector(sel, timeout=12000)
        await pg.wait_for_timeout(600)
    except Exception as e:
        errs.append(f'not drawn: {sel} ({str(e).splitlines()[0][:80]})')
    await c.close()
    return errs


async def main():
    if git('cat-file', '-e', PREV + '^{commit}').returncode:
        check(f'the previous ship ({PREV}) is in this clone (run: git fetch origin main)', False)
        print(f"\n{len(fails)} FAILED: " + '; '.join(fails)); sys.exit(1)
    files = changed()
    print(f'previous ship {PREV} = {git("rev-parse", "--short", PREV).stdout.decode().strip()}; {len(files)} files differ: {", ".join(files)}')
    bad, added = static_check()
    for mod, names in added.items():
        for n, uses in names.items():
            print(f'  new since the previous ship: js/{mod} exports {n}; used by: ' + ('; '.join(uses) or 'no other module'))
    check(f'no module names an export that the previous ship\'s copy lacks (a new export is read through the namespace, with a fallback): {sum(len(v) for v in added.values())} new exports', not bad, bad)
    procs = P.start_servers()
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
            # self-test: an "old" js/ui.js that lacks one named export the new js/main.js imports must break the page
            ui = open(os.path.join(ROOT, 'js', 'ui.js'), encoding='utf-8').read()
            broken = re.sub(r'^export const spr=', 'const spr=', ui, count=1, flags=re.M)
            e = await screen(b, '#', '.scr.title .btn', {'js/ui.js': broken.encode()})
            check('self-test: an old copy without a named export the new code imports is seen as a broken page', broken != ui and any('spr' in x for x in e), e[:3])
            # this checkout alone: the baseline must be clean, or every mix below would fail for another reason
            for name, path, sel in SCREENS:
                e = await screen(b, path, sel, {})
                check(f'this checkout alone: {name} is drawn with no error', not e, e[:3])
            for f in files:
                old = git('show', f'{PREV}:{f}').stdout
                for name, path, sel in SCREENS:
                    e = await screen(b, path, sel, {f: old})
                    check(f'{f} from the previous ship, the rest from this checkout: {name} is drawn with no error', not e, e[:3])
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
