#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""Every picture, stylesheet and script a design mock (docs/mock/*.html) points at is in the repo.

    python3 tests/mock_links.py

The mocks are drawn from the game's own files; when a file is replaced or removed (the 10 first waist-up stills in #122),
a mock that still names it shows a broken picture to the owner and the teacher. No server, no browser: the paths are read
from the files and looked up on disk."""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    bad, n = [], 0
    for page in sorted(glob.glob(os.path.join(ROOT, 'docs', 'mock', '*.html'))):
        html = open(page, encoding='utf-8').read()
        refs = re.findall(r'(?:src|href)="([^"#?]+)', html) + re.findall(r'url\(["\']?([^"\')#?]+)', html)
        for r in refs:
            if re.match(r'(?:[a-z]+:|//)', r): continue        # data:, https:, mailto: and the like are not files here
            n += 1
            if not os.path.isfile(os.path.normpath(os.path.join(os.path.dirname(page), r))):
                bad.append(os.path.relpath(page, ROOT) + ': ' + r)
    print(f"{'PASS' if not bad else 'FAIL'} every file a mock in docs/mock names is in the repo ({n} links)" + ('' if not bad else ': ' + '; '.join(bad[:10])))
    print('\nALL PASSED' if not bad else f'\n1 FAILED: {len(bad)} missing')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
