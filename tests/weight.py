#!/usr/bin/env python3
# suite: quick=--quick   # picked up by tests/all.py
"""The download budget: the map's first load with the new look (?ds=1) stays light, and the live look gets no heavier.

    python3 tests/weight.py --quick    # requests and bytes (no throttling), and the checks below; under a minute
    python3 tests/weight.py            # also the time to usable on the slow profile (tests/slow_net.py), flag on and off

Budget, with the flag on: the map's own first load on a fresh device; the next screen's art that the map fetches ahead
on purpose (PATH_ART) is counted apart, with its own small cap. Ceiling, with the flag off: the live game's own numbers
on game when this budget was set (25.11.2026), so it never gets heavier. Both are counted the way tests/slow_net.py
counts them (gzip as on GitHub Pages, every request until the network is quiet).
Also checked, with the flag on:
  - an old-look picture that the new look draws over is never downloaded: it gets an empty stand-in of its own size in
    srcset written into its tag where the markup is built (js/ui.js spr; Safari loads src the moment an img is created),
    and every picture that has the stand-in has its new art drawn; innerHTML stays the browser's own;
  - js/dsflag.js asks early only for what the page goes on to use: its module list equals js/main.js's imports (and
    js/avatar.js's), and each screen's background is that screen's (Chrome warns about a preload that is not used);
and with the flag off: no srcset, no early requests, nothing of the new look."""
import asyncio, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tempfile
REQLOG = os.path.join(tempfile.mkdtemp(prefix='wi-weight-'), 'served.txt')
os.environ['WI_REQLOG'] = REQLOG   # the test server writes every path it is asked for (tests/static_server.py)
import slow_net as N
import play as P
from play import check, fails
from playwright.async_api import async_playwright

QUICK = '--quick' in sys.argv
KB = 1024
# with the flag on: the map's first load. Before the cuts (game aaeb727): 110 requests, 2,295 KB, usable in 37.7 s; after
# them: 62 requests, 836 KB, 19.2 s. The budget holds that (a little room for the headers); the 10 s target needs the
# decisions listed in PR #77 (the Latin font preloaded by index.html, the code the map does not use).
BUDGET_ON = {'requests': 64, 'bytes': 860 * KB, 'usable_s': 21.0}
# the next screen's art, fetched on purpose from the map once the map is in (the island path's backdrop and its stones,
# client engineer 1's #74): not part of what the map needs, so counted apart with a small cap of its own
PATH_ART = re.compile(r'assets/al/(bg/english\.|ui/stone-)')
PATH_CAP = {'requests': 4, 'bytes': 160 * KB}   # 160, not 110: bg/english kept at its full 752 px (sharp on 2x/3x phones, 125 KB), decided by the lead
# with the flag off: the live class's numbers on game (aaeb727, 25.11.2026): 88 requests, 1,913 KB. The ceiling has about
# 2% of room on purpose (1,950 KB), so an ordinary fix in a shared file does not fail it; it is raised on purpose, with a
# note here, by each live change that adds weight. Requests: not one more.
CEIL_OFF = {'requests': 88, 'bytes': 1950 * KB}
# with the flag on: Fraction Bay's map, first load. With its own islands (#99, misl-1..4): 48 requests, 778 KB on
# 26.11.2026 (689 KB with the English islands in their place). The cap holds that with a little room.
BUDGET_MATH = {'requests': 50, 'bytes': 800 * KB}

ROOT = P.ROOT


def import_graph(start):
    seen, todo = [], [start]
    while todo:
        f = todo.pop(0)
        if f in seen: continue
        seen.append(f)
        src = open(os.path.join(ROOT, f), encoding='utf-8').read()
        for m in re.finditer(r"^\s*import\s[^;]*?from\s*'([^']+)'|^import\s*'([^']+)'", src, re.M):
            n = os.path.normpath(os.path.join(os.path.dirname(f), m.group(1) or m.group(2)))
            if n not in seen: todo.append(n)
    return [os.path.basename(f)[:-3] for f in seen]


def lists():
    """js/dsflag.js's two module lists, as written"""
    src = open(os.path.join(ROOT, 'js', 'dsflag.js'), encoding='utf-8').read()
    get = lambda name: re.findall(r"'([a-z_]+)'", re.search(r'var %s=\[([^\]]*)\]' % name, src).group(1))
    return get('MODS'), get('WORLD')


# the swapped pictures: drawn over by the new look, so they must have the stand-in in srcset; and the other way round
SKIP = """()=>{const bad=[],odd=[];for(const im of document.querySelectorAll('img[src]')){const cs=getComputedStyle(im),drawn=cs.backgroundImage.includes('url(');
 const over=drawn&&(cs.objectPosition.startsWith('-9999')||cs.height==='0px'),blank=(im.getAttribute('srcset')||'').startsWith('data:');
 if(over&&!blank)bad.push(im.getAttribute('src'));if(blank&&!drawn)odd.push(im.getAttribute('src'))}return {bad,odd,n:document.querySelectorAll('img[srcset^="data:"]').length}}"""


# every srcset that is ADDED to an old picture already in the page: in Safari that picture has started loading by then.
# A stand-in written into the tag (js/ui.js spr) is there before the picture exists, so it is not seen here.
LATE = """window.__late=[];new MutationObserver(ms=>{for(const m of ms){const t=m.target;if(m.oldValue===null&&t.isConnected&&t.getAttribute('srcset')&&/assets\\/sp\\//.test(t.getAttribute('src')||''))__late.push(t.getAttribute('src'))}})
 .observe(document,{subtree:true,attributes:true,attributeFilter:['srcset'],attributeOldValue:true})"""


NATJS = """async()=>{const src=(await (await fetch('js/ui.js')).text());const t=/const NAT=(\\{[^}]*\\})/.exec(src)[1].replace(/(\\w+):/g,'"$1":');
 const N=JSON.parse(t),bad=[];for(const [k,[w,h]] of Object.entries(N)){const i=new Image();i.src='assets/sp/'+k+'.webp';await i.decode();if(i.naturalWidth!==w||i.naturalHeight!==h)bad.push([k,w,h,i.naturalWidth,i.naturalHeight])}
 return {n:Object.keys(N).length,bad}}"""


async def structure(b, errs):
    c = await b.new_context(); pg = await c.new_page(); await pg.goto(N.base_url() + 'index.html#'); R = await pg.evaluate(NATJS); await c.close()
    check(f'the stand-ins keep each old picture\'s own size ({R["n"]} listed in js/ui.js NAT, checked against the files)', R['n'] >= 10 and not R['bad'], R['bad'])
    mods, world = lists()
    graph = import_graph('js/main.js')
    check('dsflag.js asks early for exactly the modules js/main.js imports', mods == graph, (mods, graph))
    wg = [m for m in import_graph('js/avatar.js') if m not in graph]
    check('and for exactly the new world\'s own modules (js/avatar.js and its imports)', world == wg, (world, wg))
    api = f'http://127.0.0.1:{P.API_PORT}/'
    seed = {'u': N.USER, 'g': {'st': {f'{i}-{t}': 3 for i in (1, 2) for t in ('sling', 'listen', 'read', 'bridge')}}}
    for path, sel in (('#', '.scr.title .btn'), ('#map', '.map .isl'), ('#island/1', '.w-path .w-st,.scr.island .lvrow'), ('#avatar', '.wpick__grid'), ('#math', '.scr.mmap'), ('#mock', '.scr.mockhub'), ('#play/1/sling', '.lv')):
        for ds in (True, False):
            c = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True)
            pg = await c.new_page()
            warn, got = [], []
            pg.on('console', lambda m: warn.append(m.text) if 'preload' in m.text and 'not used' in m.text else None)
            pg.on('request', lambda r: got.append(r.url))
            open(REQLOG, 'w').close()   # what the server serves for this page only
            await pg.route('**/config.js', lambda r: r.fulfill(content_type='text/javascript', body=f"window.API_URL='{api}';"))
            await pg.add_init_script("if(!sessionStorage.s){sessionStorage.s=1;localStorage.setItem('aam-unit1-v1',%s)}" % json.dumps(json.dumps(seed)))
            await pg.add_init_script(LATE)
            await pg.goto(N.base_url() + 'index.html' + ('?ds=1' if ds else '') + path)
            if path == '#avatar' and not ds:
                await pg.wait_for_selector('.scr.title'); await c.close(); continue
            await pg.wait_for_selector(sel); await pg.wait_for_timeout(3500)   # Chrome's "preloaded but not used" warning comes after about 3 s
            S = await pg.evaluate(SKIP)
            tag = f'[{path} flag {"on" if ds else "off"}]'
            if ds:
                nat = await pg.evaluate("[Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML').set,Element.prototype.insertAdjacentHTML].every(f=>/\\[native code\\]/.test(Function.prototype.toString.call(f)))")
                check(f'{tag} innerHTML and insertAdjacentHTML are the browser\'s own with the flag on too (no page-wide hook)', nat)
                late = await pg.evaluate('window.__late')
                check(f'{tag} no stand-in comes late: none is added to an old picture already in the page (in Safari it would be loading)', not late, late[:5])
                check(f'{tag} every old picture the new look draws over has the stand-in ({S["n"]}), and every one that has it has its new art', not S['bad'] and not S['odd'], S)
                old = [u for u in got if re.search(r'/assets/sp/(isl_\d|star|star_off|lock|ic_gear)\.webp$', u)]
                served = [u for u in open(REQLOG, encoding='utf-8').read().split() if re.search(r'/assets/sp/(isl_\d|star|star_off|lock|ic_gear)\.webp$', u)]
                if path in ('#map', '#island/1', '#math'):
                    # counted twice: as the browser reports it, and as the server saw it (docs/LESSONS.md 14)
                    check(f'{tag} none of the swapped old pictures is requested (browser) or served (server)', not old and not served, (old, served))
                check(f'{tag} everything asked for early is used (Chrome warns of no unused preload)', not warn, warn)
                misl = [u for u in open(REQLOG, encoding='utf-8').read().split() if '/assets/al/map/misl-' in u]
                if path == '#math':
                    check(f'{tag} Fraction Bay\'s map draws its own islands (misl-1..4 served)', any('/misl-1.' in u for u in misl), misl)
                elif path in ('#map', '#island/1'):
                    check(f'{tag} the English screens never fetch Fraction Bay\'s islands', not misl, misl)
            else:
                L = await pg.evaluate("[document.querySelectorAll('img[srcset]').length,document.querySelectorAll('link[rel=modulepreload],link[rel=preload][as=image],link[rel=preload][as=style]').length,document.documentElement.classList.contains('ds'),[...document.querySelectorAll('link[rel=stylesheet]')].map(l=>l.getAttribute('href')).filter(h=>/ds|avatar|worldpath/.test(h))]")
                check(f'{tag} nothing of the new look: no srcset, no early requests, no new-look style sheets', L == [0, 0, False, []], L)
                if path == '#math':   # the new look's art is never served without the flag (Fraction Bay's own islands included)
                    al = [u for u in open(REQLOG, encoding='utf-8').read().split() if u.startswith('/assets/al/')]
                    check(f'{tag} nothing of the new look\'s art is served (assets/al/, Fraction Bay\'s islands included)', not al, al[:5])
                if path == '#map':   # the server's log works: the live look's own island picture is there (the control for the check above)
                    check(f'{tag} the server log sees the live look\'s pictures (isl_1.webp served)', '/assets/sp/isl_1.webp' in open(REQLOG, encoding='utf-8').read().split())
            await c.close()


async def budget(b):
    """what the map needs: every request but the deliberate next-screen prefetch (PATH_ART), which has its own cap"""
    for ds in (True, False):
        r = await N.measure(b, 'index.html#map', "()=>!!document.querySelector('.scr.map .isl')", ds, throttle=False)
        own = [x for x in r['all'] if not PATH_ART.search(x['file'])]
        pre = [x for x in r['all'] if PATH_ART.search(x['file'])]
        n, kb = len(own), sum(x['bytes'] for x in own)
        if ds:
            check(f'flag on, the map\'s own first load: {n} requests (budget {BUDGET_ON["requests"]}), {kb // KB} KB (budget {BUDGET_ON["bytes"] // KB})', n <= BUDGET_ON['requests'] and kb <= BUDGET_ON['bytes'], own[:5])
            pk = sum(x['bytes'] for x in pre)
            check(f'flag on, the next screen\'s art fetched ahead from the map: {len(pre)} requests (cap {PATH_CAP["requests"]}), {pk // KB} KB (cap {PATH_CAP["bytes"] // KB})', len(pre) <= PATH_CAP['requests'] and pk <= PATH_CAP['bytes'], pre)
        else:
            check(f'flag off, map first load: {n} requests (ceiling {CEIL_OFF["requests"]}), {kb // KB} KB (ceiling {CEIL_OFF["bytes"] // KB}): not heavier than the live game', n <= CEIL_OFF['requests'] and kb <= CEIL_OFF['bytes'] and not pre, (own[:5], pre))
    r = await N.measure(b, 'index.html#math', "()=>!!document.querySelector('.scr.mmap .isl')", True, throttle=False)
    n, kb = r['requests'], r['bytes']
    check(f'flag on, Fraction Bay\'s map first load: {n} requests (budget {BUDGET_MATH["requests"]}), {kb // KB} KB (budget {BUDGET_MATH["bytes"] // KB})', n <= BUDGET_MATH['requests'] and kb <= BUDGET_MATH['bytes'], r['top'][:5])
    if not QUICK:
        for ds in (True, False):
            r = await N.measure(b, 'index.html#map', "()=>!!document.querySelector('.scr.map .isl')", ds, throttle=True)
            if ds:
                check(f'flag on, map usable in {r["usable_s"]} s on the slow profile (budget {BUDGET_ON["usable_s"]} s)', r['usable_s'] is not None and r['usable_s'] <= BUDGET_ON['usable_s'], r['top'][:5])
            else:
                print(f'INFO flag off, map usable in {r["usable_s"]} s on the slow profile (reported, not checked: the live game is measured, not changed)')


async def main():
    procs = P.start_servers(mock=True)
    errs = []
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=P.CHROME, args=['--no-sandbox'])
            await budget(b)
            await structure(b, errs)
            await b.close()
    finally:
        for p in procs: p.terminate()
    print(f"\n{'ALL PASSED' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    asyncio.run(main())
