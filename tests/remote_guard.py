#!/usr/bin/env python3
"""The game's files are ours: nothing in js/, css/, the pages or the tools may point to another host.
    python3 tests/remote_guard.py
Scans js/**, css/**, *.html, tools/*.html, config.js and manifest.webmanifest for any http(s) or protocol-relative URL and
for the old storage host by name. Exactly two things are allowed for now: the class backend URL in config.js and Google
Fonts in trainer.html (the old trainer; fonts move into the repo next). XML namespace names (w3.org) are names, not requests.
Also checks that every asset path in js/run.js and tools/sheet.html exists and matches assets/sources.tsv (tests/assets_local.py check)."""
import glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = re.compile(r"""(?:https?:)?//[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+[^\s"'`)<>]*""")
ALLOWED = {'config.js': re.compile(r'https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec'),
           'trainer.html': re.compile(r'https://fonts\.googleapis\.com(/css2\?[^\s"\']*)?')}
NAMESPACE = re.compile(r'http://www\.w3\.org/(2000/svg|1999/xlink|1999/xhtml|1998/Math/MathML)')
# The voice clips move into the repo in their own pull request (branch assets/voice-local, guarded there by tests/play.py).
# Until it is merged these two files still name the old host. DELETE THIS LINE when that pull request is in.
PENDING = {'js/voice.js', 'js/mock.js'}


def files():
    pats = ['js/**/*.js', 'css/**/*.css', '*.html', 'tools/*.html', 'config.js', 'manifest.webmanifest']
    return sorted({os.path.relpath(f, ROOT).replace(os.sep, '/') for p in pats for f in glob.glob(os.path.join(ROOT, p), recursive=True)})


def remote_urls():
    """[(file, line number, url)] for everything that is not allowed"""
    bad = []
    for f in files():
        if f in PENDING:
            continue
        for n, line in enumerate(open(os.path.join(ROOT, f), encoding='utf-8'), 1):
            hits = [m.group(0) for m in URL.finditer(line) if not NAMESPACE.fullmatch(m.group(0)) and not (f in ALLOWED and ALLOWED[f].fullmatch(m.group(0)))]
            if 'cloudfront' in line.lower() and not hits:
                hits = ['cloudfront']
            bad += [(f, n, h[:90]) for h in hits]
    return bad


def local_assets():
    """every 3D model and picture js/run.js and tools/sheet.html name is in the manifest; [(file, problem)]"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import assets_local as A
    rows = {r['file']: r for r in A.read_manifest()}
    bad = []
    run = open(os.path.join(ROOT, 'js', 'run.js'), encoding='utf-8').read()
    sheet = open(os.path.join(ROOT, 'tools', 'sheet.html'), encoding='utf-8').read()
    used = {'3d/' + m for m in re.findall(r"M3D\+'([^']+)'", run)} | {'x/' + m for m in re.findall(r"HPIC\+'([^']+)'", run)} | {'x/src/' + m for m in re.findall(r"'\.\./assets/x/src/([^']+)'", sheet)}
    if len(used) != 27 or used != set(rows):
        bad.append(('assets/sources.tsv', 'the files named in js/run.js and tools/sheet.html are not exactly the manifest: ' + str(sorted(used ^ set(rows))[:4])))
    for f, r in rows.items():
        p = os.path.join(A.ASSETS, f)
        if not os.path.isfile(p) or A.sha256(open(p, 'rb').read()) != r['sha256']:
            bad.append((f, 'missing, or differs from its sha256'))
        elif r['kind'] == 'model-glb' and os.path.getsize(p) >= A.GLB_LIMIT:
            bad.append((f, 'a model must stay under 3 MB'))
    on_disk = {f'{d}/{f}' for d in ('3d', 'x/src') for f in os.listdir(os.path.join(A.ASSETS, d))}
    bad += [(f, 'a stray file: not in the manifest') for f in sorted(on_disk - set(rows))]
    return bad


if __name__ == '__main__':
    r, a = remote_urls(), local_assets()
    for x in r: print('FAIL remote URL', *x)
    for x in a: print('FAIL asset', *x)
    if PENDING: print('note: not scanned yet (voice pull request pending):', sorted(PENDING))
    print('ALL PASSED' if not r and not a else f'{len(r) + len(a)} FAILED', f'({len(files())} files scanned)')
    sys.exit(1 if r or a else 0)
