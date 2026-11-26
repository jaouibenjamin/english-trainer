#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""The Supabase project's ref lives in one place, supabase/project_ref (tools/project_ref.py):

    python3 tests/project_ref_check.py

Every https://<ref>.supabase.co in a tracked file (config.js, the pages' Content-Security-Policy, docs, tests) must be
the ref in that file, so a project that was replaced cannot stay in a page. Also tests the tool itself: a look-alike
sub-domain is not a project address, a replace touches only the whole ref, and tools/supabase_setup.py reads its
default ref from the file."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import project_ref as pr

fails = []


def check(label, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + label + ('' if ok else f'   <- {str(detail)[:400]}'))
    if not ok:
        fails.append(label)


A, B = 'a' * 20, 'b' * 19 + 'c'
bad = pr.stale(pr.read(), pr.tracked())
check(f'every project address in the repository is the ref in supabase/project_ref ({pr.read() or "not set"})', not bad, bad[:10])
check('a stale project on a page is found', pr.stale(A, [('index.html', f'connect-src https://{B}.supabase.co')]) == [('index.html', B)])
check('the current project on a page is fine', pr.stale(A, [('config.js', f"url: 'https://{A}.supabase.co'")]) == [])
check('a look-alike is not a project address (a sub-domain, a longer name, a suffix)',
      pr.addresses(f'x.{A}.supabase.co {A}x.supabase.co https://{A}.supabase.co.evil.example.org') == set())
check('replace changes the whole ref only', pr.replace(f'{A} {A}z z{A} https://{A}.supabase.co', A, B) == f'{B} {A}z z{A} https://{B}.supabase.co')
check('a ref is 20 lower-case letters; the placeholder is not one', pr.REF.fullmatch(A) and not pr.REF.fullmatch('not-set-yet') and not pr.REF.fullmatch(A.upper()))
out = subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, "tools"); import supabase_setup as s; print(s.project_ref())'],
                     cwd=ROOT, capture_output=True, text=True).stdout.strip()
check('tools/supabase_setup.py reads its default ref from supabase/project_ref', out == open(pr.FILE, encoding='utf-8').read().strip(), out)
print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
sys.exit(1 if fails else 0)
