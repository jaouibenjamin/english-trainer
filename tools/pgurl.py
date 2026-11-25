"""psql against a database URL without putting the password on a command line (shared by migrate_sheet.py and
restore.py). The URL comes from an environment variable on the owner's computer; it is split into libpq's own
variables (PGPASSWORD and friends) for the child process only. Nothing here prints the URL."""
import os, secrets, shutil, subprocess, urllib.parse


def env_for(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ('postgres', 'postgresql'):
        raise SystemExit('the database address must start with postgresql://')
    q = dict(urllib.parse.parse_qsl(u.query))
    env = dict(os.environ)
    for k in ('PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE', 'PGSSLMODE', 'PGSERVICE', 'PGPASSFILE'):
        env.pop(k, None)
    host = q.get('host') or u.hostname or ''
    env.update(PGHOST=host, PGPORT=str(q.get('port') or u.port or 5432), PGUSER=urllib.parse.unquote(u.username or 'postgres'),
               PGDATABASE=(u.path or '/postgres').lstrip('/') or 'postgres')
    if u.password:
        env['PGPASSWORD'] = urllib.parse.unquote(u.password)
    if not host.startswith('/') and host not in ('localhost', '127.0.0.1'):
        env['PGSSLMODE'] = q.get('sslmode', 'require')
    return env


def literal(text):
    """text as a dollar-quoted SQL literal whose tag cannot occur in it"""
    while True:
        tag = '$wi' + secrets.token_hex(6) + '$'
        if tag not in text:
            return tag + text + tag


def run(url, sql):
    """runs sql in one transaction; returns (stdout, stderr, returncode)"""
    psql = os.environ.get('PSQL') or shutil.which('psql')
    if not psql:
        raise SystemExit('psql is not installed')
    r = subprocess.run([psql, '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '--single-transaction'],
                       input=sql, capture_output=True, text=True, env=env_for(url))
    return r.stdout, r.stderr, r.returncode
