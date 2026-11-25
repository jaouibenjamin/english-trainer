#!/usr/bin/env python3
"""The tests' static server (started by tests/play.py start_servers; not a suite of its own).

    python3 tests/static_server.py PORT [MOCK_ORIGIN]

Serves this checkout on 127.0.0.1:PORT like `python3 -m http.server`. One difference: when the mock backend runs, its
origin (another port, so another origin) is added to connect-src in the pages' Content-Security-Policy, the way the
real pages list the class's Apps Script. The pages in the repository are not changed, and only the pages it serves to
the tests carry it. (Patching the page in the browser instead would make Chrome treat it as a public page and refuse
its calls to the local mock.)"""
import functools, http.server, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1])
MOCK = sys.argv[2] if len(sys.argv) > 2 else ''


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')
        if MOCK and path.endswith('.html') and os.path.isfile(path):
            body = open(path, 'rb').read().replace(b"connect-src 'self'", b"connect-src 'self' " + MOCK.encode(), 1)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return __import__('io').BytesIO(body)
        return super().send_head()


if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Handler, directory=ROOT)).serve_forever()
