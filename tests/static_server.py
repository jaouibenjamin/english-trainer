#!/usr/bin/env python3
"""The tests' static server (started by tests/play.py start_servers; not a suite of its own).

    python3 tests/static_server.py PORT [MOCK_ORIGIN]

Serves this checkout on 127.0.0.1:PORT like `python3 -m http.server`. One difference: when the mock backend runs, its
origin (another port, so another origin) is added to connect-src in the pages' Content-Security-Policy, the way the
real pages list the class's Apps Script. The pages in the repository are not changed, and only the pages it serves to
the tests carry it. (Patching the page in the browser instead would make Chrome treat it as a public page and refuse
its calls to the local mock.)

With WI_GZIP=1 in its environment (tests/slow_net.py sets it), text files (html, js, css, json, svg, the manifest) are
sent gzip-compressed to a browser that asks for it, as GitHub Pages sends them, so measured bytes match the live site.
With WI_REQLOG=<file>, every path it is asked for is appended to that file, one per line: what was really requested,
counted where it arrives, not as a browser reports it (tests/weight.py)."""
import functools, gzip, http.server, io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1])
MOCK = sys.argv[2] if len(sys.argv) > 2 else ''
GZIP = os.environ.get('WI_GZIP') == '1'
REQLOG = os.environ.get('WI_REQLOG', '')
TEXT = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json'}


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_head(self):
        if REQLOG:
            with open(REQLOG, 'a', encoding='utf-8') as f:
                f.write(self.path.split('?', 1)[0] + '\n')
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')
        ext = os.path.splitext(path)[1]
        zipped = GZIP and ext in TEXT and 'gzip' in self.headers.get('Accept-Encoding', '') and os.path.isfile(path)
        if (MOCK and ext == '.html' or zipped) and os.path.isfile(path):
            body = open(path, 'rb').read()
            if MOCK and ext == '.html':
                body = body.replace(b"connect-src 'self'", b"connect-src 'self' " + MOCK.encode(), 1)
            if zipped:
                body = gzip.compress(body, 6)
            self.send_response(200)
            self.send_header('Content-Type', TEXT.get(ext, 'text/html; charset=utf-8'))
            if zipped:
                self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return io.BytesIO(body)
        return super().send_head()


if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Handler, directory=ROOT)).serve_forever()
