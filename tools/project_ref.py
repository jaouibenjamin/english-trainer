#!/usr/bin/env python3
"""The Supabase project's ref, written in one place: supabase/project_ref (one line, 20 lower-case letters).

Everything that can read a file reads it from there (tools/supabase_setup.py; the docs say `REF=$(cat
supabase/project_ref)`). What cannot read a file at run time, the game's config.js and each page's
Content-Security-Policy, holds the address as text; tests/project_ref_check.py fails when any address of a project in
the repository is not this one. Changing the project is then one command and one small pull request:

    python3 tools/project_ref.py                      the ref, or "not set"
    python3 tools/project_ref.py check                every https://<ref>.supabase.co in the repository is this one
    python3 tools/project_ref.py set NEWREF [--from OLDREF]
        writes NEWREF into supabase/project_ref and replaces OLDREF (default: the ref the file held) by NEWREF in every
        tracked text file (config.js, the pages' policies, tests that name it); then runs check. Review the diff.

The ref is public by design (it is in config.js and every page's policy): this is about not shipping a stale one."""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, 'supabase', 'project_ref')
REF = re.compile(r'[a-z]{20}')
# a project address: 20 lower-case letters (Supabase refs) then .supabase.co, not a sub-domain of something else
ADDR = re.compile(r'(?<![A-Za-z0-9.-])([a-z0-9]{20})\.supabase\.co(?!\.?[A-Za-z0-9-])')


def read():
    try:
        v = open(FILE, encoding='utf-8').read().strip()
    except OSError:
        return ''
    return v if REF.fullmatch(v) else ''


def tracked():
    out = subprocess.run(['git', '-C', ROOT, 'ls-files', '-z'], capture_output=True, text=True).stdout.split('\0')
    for f in out:
        p = os.path.join(ROOT, f)
        if f and os.path.isfile(p):
            try:
                yield f, open(p, encoding='utf-8').read()
            except (UnicodeDecodeError, OSError):
                continue


def addresses(text):
    return {m.group(1) for m in ADDR.finditer(text)}


def stale(ref, files):
    """(file, other ref) for every project address that is not `ref`."""
    return sorted((f, r) for f, t in files for r in addresses(t) if r != ref)


def replace(text, old, new):
    return re.sub(rf'(?<![A-Za-z0-9]){re.escape(old)}(?![A-Za-z0-9])', new, text)


def main():
    a = sys.argv[1:]
    if not a:
        print(read() or 'not set (supabase/project_ref holds no ref)')
        return 0
    if a[0] == 'check':
        ref = read()
        bad = stale(ref, tracked())
        for f, r in bad:
            print(f'{f}: names the project {r}, not {ref or "(supabase/project_ref is not set)"}')
        print('project ref: ' + ('OK' if not bad else f'{len(bad)} stale') + f' ({ref or "not set"})')
        return 1 if bad else 0
    if a[0] == 'set' and len(a) in (2, 4) and (len(a) == 2 or a[2] == '--from'):
        new, old = a[1], (a[3] if len(a) == 4 else read())
        if not REF.fullmatch(new) or (old and not REF.fullmatch(old)):
            print('a ref is 20 lower-case letters'); return 2
        changed = []
        if old and old != new:
            for f, t in tracked():
                if old in t:
                    open(os.path.join(ROOT, f), 'w', encoding='utf-8').write(replace(t, old, new))
                    changed.append(f)
        open(FILE, 'w', encoding='utf-8').write(new + '\n')
        print('supabase/project_ref: ' + new)
        for f in changed:
            print('  ' + f)
        return main_check()
    print(__doc__)
    return 2


def main_check():
    sys.argv = [sys.argv[0], 'check']
    return main()


if __name__ == '__main__':
    sys.exit(main())
