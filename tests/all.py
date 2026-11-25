#!/usr/bin/env python3
"""Runs every test suite in tests/ and prints one line per suite.

    python3 tests/all.py              # every suite in its full form
    python3 tests/all.py --quick      # the short form, before every ship
    python3 tests/all.py --jobs 3     # three suites at a time (each has its own servers on free ports)
    python3 tests/all.py play card    # only the named suites
    python3 tests/all.py --list       # what would run, with each suite's first docstring line

A suite is any file in tests/ that has a marker line near its top, so a new suite is picked up by itself:

    # suite:                          a Python suite, run as `python3 tests/<file>`
    # suite: quick=--quick            its arguments with --quick (and full=... for the full form; quick=- is none)
    // suite: full=unit               a Node suite (`node tests/<file>`)
    // suite: needs=ffmpeg            a program it needs; if it is missing the suite counts as failed, not skipped
    // suite: name=backend            a name of its own (when two files would share one)

The exit code is non-zero if any suite failed, could not start, or needs a program that is not there.
Each suite's whole output is kept in a folder that is printed at the end."""
import argparse, os, re, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARK = re.compile(r'^\s*(?:#|//)\s*suite:(.*)$')


def suites():
    out = []
    for name in sorted(os.listdir(HERE)):
        path = os.path.join(HERE, name)
        if name == 'all.py' or not os.path.isfile(path) or not name.endswith(('.py', '.mjs', '.js')):
            continue
        with open(path, encoding='utf-8') as f:
            head = [next(f, '') for _ in range(40)]
        m = next((MARK.match(l) for l in head if MARK.match(l)), None)
        if not m:
            continue
        opts = dict(kv.split('=', 1) for kv in re.sub(r'(?:#|//)\s*picked up by tests/all\.py', '', m.group(1)).split() if '=' in kv)
        # its one-line description: the first line of its docstring or of its first comment
        doc = ''
        for l in head:
            t = l.strip()
            if not t or t.startswith('#!') or MARK.match(l) or t.startswith(('import', 'from ', 'const', 'let ')):
                continue
            t = re.sub(r'^(?:"""|/\*+|//+|#+)\s*', '', t).rstrip('*/ ').strip()
            if t:
                doc = t
                break
        out.append({'name': opts.get('name') or re.sub(r'\.(py|mjs|js)$', '', name), 'file': name, 'node': not name.endswith('.py'),
                    'quick': None if 'quick' not in opts else [] if opts['quick'] == '-' else opts['quick'].replace(',', ' ').split(),
                    'full': opts.get('full', '').replace(',', ' ').split(),
                    'needs': [n for n in opts.get('needs', '').split(',') if n], 'doc': doc})
    return out


def count(text):
    """passes and failures as the suites print them: lines that start with PASS or ok, and with FAIL"""
    p = len(re.findall(r'^(?:PASS|ok)\b', text, re.M))
    f = len(re.findall(r'^FAIL\b', text, re.M))
    return p, f


def run(s, quick, logs):
    missing = [n for n in s['needs'] if not shutil.which(n)]
    if missing:
        return dict(s, rc=None, secs=0, p=0, f=0, last=f"NOT RUN: needs {', '.join(missing)}")
    args = s['quick'] if quick and s['quick'] is not None else s['full']
    cmd = (['node'] if s['node'] else [sys.executable]) + [os.path.join('tests', s['file'])] + args
    t = time.time()
    log = os.path.join(logs, s['name'] + '.log')
    with open(log, 'w', encoding='utf-8') as fh:
        try:
            rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, timeout=3600).returncode
        except subprocess.TimeoutExpired:
            rc = 'timeout'
    text = open(log, encoding='utf-8', errors='replace').read()
    p, f = count(text)
    lines = [l for l in text.strip().splitlines() if l.strip()]
    # the suite's own result line if it prints one, else its last line
    last = next((l for l in reversed(lines) if re.search(r'ALL PASSED|FAILED|^checked \d+', l)), lines[-1] if lines else '')
    return dict(s, rc=rc, secs=time.time() - t, p=p, f=f, last=last[:90], cmd=' '.join(cmd))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('names', nargs='*', help='run only these suites')
    ap.add_argument('--quick', action='store_true', help='the short form of each suite')
    ap.add_argument('--jobs', type=int, default=1, help='suites at a time (default 1)')
    ap.add_argument('--list', action='store_true', help='list the suites and stop')
    a = ap.parse_args()
    found = suites()
    if a.names:
        unknown = [n for n in a.names if n not in {s['name'] for s in found}]
        if unknown:
            sys.exit(f"no such suite: {', '.join(unknown)} (python3 tests/all.py --list)")
        found = [s for s in found if s['name'] in a.names]
    if a.list:
        for s in found:
            args = s['quick'] if a.quick and s['quick'] is not None else s['full']
            print(f"{s['name']:<14} {('node ' if s['node'] else 'python3 ') + 'tests/' + s['file'] + (' ' + ' '.join(args) if args else ''):<42} {s['doc'][:70]}")
        return
    logs = tempfile.mkdtemp(prefix='wi-tests-')
    print(f"{len(found)} suites{' (quick)' if a.quick else ''}, {a.jobs} at a time", flush=True)
    bad = 0
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for r in ex.map(lambda s: run(s, a.quick, logs), found):
            ok = r['rc'] == 0 and r['f'] == 0   # a FAIL line fails the suite even if it forgot to set its exit code
            bad += not ok
            state = 'ok  ' if ok else 'FAIL'
            print(f"{state} {r['name']:<14} PASS {r['p']:>4}  FAIL {r['f']:>3}  {r['secs']:>5.0f}s  {r['last']}", flush=True)
    print(f"\n{'ALL PASSED' if not bad else str(bad) + ' SUITE(S) FAILED'}   (full output of each suite: {logs})")
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
