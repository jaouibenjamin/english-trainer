#!/usr/bin/env python3
"""The game's files are ours: nothing in js/, css/, the pages or the tools may point to another host.
    python3 tests/remote_guard.py
Scans js/**, css/**, *.html, tools/*.html, config.js and manifest.webmanifest for any http(s) or protocol-relative URL and
for the old storage host by name. Exactly one thing is allowed: the class backend URL in config.js. XML namespace
names (w3.org) are names, not requests.
It is a static scan of the text: a URL built from pieces at run time is not seen (tests/run.py watches the real requests).
Also fails when the owner's storage address (its host, or the account folder) is written anywhere in the repo.
Also checks that every asset path in js/run.js and tools/sheet.html exists and matches assets/sources.tsv (tests/assets_local.py check),
and that assets/CREDITS.md is up to date and names every file under assets/ and vendor/ (tests/credits.py check)."""
import glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = re.compile(r"""(?:https?:)?//[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+[^\s"'`)<>]*""")
ALLOWED = {'config.js': re.compile(r'https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec')}
NAMESPACE = re.compile(r'http://www\.w3\.org/(2000/svg|1999/xlink|1999/xhtml|1998/Math/MathML)')
# No file is excused. A new entry would be: file -> the one exact URL tolerated in it, once.
OLD = 'https://cdn.example.net/account_x/'      # a made-up storage address, used by the self-test
PENDING = {}


def files():
    pats = ['js/**/*.js', 'css/**/*.css', '*.html', 'tools/*.html', 'config.js', 'manifest.webmanifest']
    return sorted({os.path.relpath(f, ROOT).replace(os.sep, '/') for p in pats for f in glob.glob(os.path.join(ROOT, p), recursive=True)})


def read(f):
    return open(os.path.join(ROOT, f), encoding='utf-8').read()


def remote_urls(read=read):
    """[(file, line number, url)] for everything that is not allowed (read: how a file's text is got; the self-test changes it)"""
    bad = []
    for f in files():
        seen_pending = 0
        for n, line in enumerate(read(f).split('\n'), 1):
            found = [m.group(0) for m in URL.finditer(line)]
            hits = []
            for u in found:
                if NAMESPACE.fullmatch(u) or (f in ALLOWED and ALLOWED[f].fullmatch(u)):
                    continue
                if PENDING.get(f) == u and not seen_pending:      # the one known constant, once
                    seen_pending = 1
                    continue
                hits.append(u)
            if 'cloudfront' in line.lower() and not found:
                hits = ['cloudfront']
            bad += [(f, n, h[:90]) for h in hits]
    return bad


def self_test():
    """the guard must catch what it is for; [problem]"""
    def planted(target, extra):
        return lambda f: read(f) + (extra if f == target else '')
    cases = [('js/mock.js', "\nfetch('https://example.org/x.mp3');\n", 'https://example.org/x.mp3'),
             ('js/voice.js', "\nconst B2='" + OLD + "other';\n", OLD + 'other'),
             ('js/mock.js', "\nconst VB2='" + OLD + "hf_20261121_';\n", OLD + 'hf_20261121_'),      # a second copy of the tolerated string, when one is still there
             ('js/run.js', "\nnew Image().src='//cdn.example.net/a.png';\n", '//cdn.example.net/a.png'),
             ('css/game.css', "\n.x{background:url(https://example.org/a.png)}\n", 'https://example.org/a.png'),
             ('trainer.html', '\n<link href="https://fonts.googleapis.com/css2?family=Rubik" rel="stylesheet">\n', 'https://fonts.googleapis.com/css2?family=Rubik'),
             ('index.html', '\n<script src="https://script.google.com/macros/s/abc/exec"></script>\n', 'https://script.google.com/macros/s/abc/exec'),      # the backend URL is allowed in config.js only
             ('js/main.js', "\n// abc123.Cloud" + "Front.net\n", None)]
    base, out = remote_urls(), []
    for target, extra, want in cases:
        if want and want.startswith(OLD) and want == PENDING.get(target) and not any(PENDING[target] in ln for ln in read(target).split('\n')):
            continue      # a tolerated constant that is no longer in its file: its entry in PENDING is stale and should go
        got = [b for b in remote_urls(planted(target, extra)) if b not in base]
        if not got or got[0][0] != target or (want and got[0][2] != want[:90]):
            out.append(f'not caught: {extra.strip()} planted in {target} {got[:1]}')
    return out


# The owner's storage: its host and the account folder in it must not be written anywhere in the repo, not in the lists,
# the tests or the tools either (the build scripts get the address at run time, tests/storage.py).
PRIVATE = re.compile(rb'user_[A-Za-z0-9]{16,}|[a-z0-9-]+\.cloudfront\.net', re.I)


def tracked():
    """every file of the repo (git's list; without git, everything below the root except .git)"""
    import subprocess
    try:
        out = subprocess.run(['git', '-C', ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], capture_output=True, check=True).stdout
        return sorted(f for f in out.decode().split('\0') if f and os.path.isfile(os.path.join(ROOT, f)))
    except Exception:
        return sorted(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/') for d, ds, fs in os.walk(ROOT) for f in fs if '.git' not in d.split(os.sep))


def private_paths(read_bytes=None):
    """[(file, line number)] wherever the storage host or the account folder is written; the text itself is not printed"""
    read_bytes = read_bytes or (lambda f: open(os.path.join(ROOT, f), 'rb').read())
    bad = []
    for f in tracked():
        data = read_bytes(f)
        bad += [(f, data.count(b'\n', 0, m.start()) + 1) for m in PRIVATE.finditer(data)][:3]
    return bad


def private_self_test():
    """the scan must catch both forms, in a list and in a test; [problem]"""
    host, folder = b'abc123.cloud' + b'front.net', b'user_' + b'A1b2C3d4E5f6G7h8I9j0'
    real = lambda f: open(os.path.join(ROOT, f), 'rb').read()
    out = []
    for target, extra in (('assets/sources.tsv', b'https://' + host + b'/x.png\n'), ('tests/remote_guard.py', b'# ' + folder + b'\n'), ('README.md', folder + b'/' + b'\n')):
        got = private_paths(lambda f: real(f) + (extra if f == target else b''))
        if not any(g[0] == target for g in got):
            out.append('not caught: a storage address planted in ' + target)
    return out


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


def credits():
    """assets/CREDITS.md is up to date, names every file under assets/ and vendor/ and no other; [problem]"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import credits as C
    return C.problems()


if __name__ == '__main__':
    r, a, t = remote_urls(), local_assets(), self_test()
    c = credits()
    pv = private_paths()
    for x in pv: print('FAIL the storage address is written in', *x)
    c = c + [str(x) for x in pv] + private_self_test()
    for x in r: print('FAIL remote URL', *x)
    for x in a: print('FAIL asset', *x)
    for x in t: print('FAIL self-test', x)
    for x in c[:20]: print('FAIL credits', x)
    t = t + c
    if PENDING: print('note: one known URL is still tolerated in each of:', sorted(PENDING))
    print('ALL PASSED' if not (r or a or t) else f'{len(r) + len(a) + len(t)} FAILED', f'({len(files())} files scanned)')
    sys.exit(1 if r or a or t else 0)
