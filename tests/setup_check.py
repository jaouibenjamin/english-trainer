#!/usr/bin/env python3
# suite: needs=psql   # picked up by tests/all.py
"""The one-button setup (tools/supabase_setup.py, .github/workflows/supabase-setup.yml), tested without Supabase:

    python3 tests/setup_check.py

A stand-in for the Management API (and the project's admin-class function) runs here on a local port, backed by the
same throw-away PostgreSQL as tests/db.py, started EMPTY (the stand-in for a new project: tests/db/stub.sql only, plus
a stand-in Vault); tests/setup_fake_cli.py stands in for the Supabase CLI. Nothing is sent to any real project. It
proves, on a fresh project:
  - sign-ups are switched off before anything else is written, and before any table exists;
  - migrations 0001 to 0009, the catalog and raw_days 30 end up in the database; the five functions are deployed,
    never admin-wrap-legacy; the pepper and ALLOWED_ORIGINS are set; the trial class with Test and Tester exists and its
    code is in the Vault;
  - no secret reaches the log: the access token, the database password (which the stand-in CLI echoes), the server
    keys, the pepper and the class code appear only on ::add-mask:: lines;
and that a second run changes nothing and says so; that a paused project, a region outside the EU, a paid plan, a
public schema that is not ours, or a wrong confirmation stops it before any write; that a refused legacy key falls
back to the secret key. It also reads the workflow: dispatch only, the owner and game/main only, contents: read,
actions pinned by commit, the CLI pinned by checksum, inputs passed through env, the secrets only in the setup step."""
import glob, hashlib, json, os, re, secrets, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db'))
import pg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = 'abcdefghijklmnopqrst'
fails = []


def check(label, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + label + ('' if ok else f'   <- {str(detail)[:400]}'))
    if not ok:
        fails.append(label)


VAULT = """
create schema if not exists vault;
create table if not exists vault.secrets (id uuid primary key default gen_random_uuid(), name text unique, secret text, description text);
create or replace function vault.create_secret(s text, n text, d text) returns uuid language sql as
  $$ insert into vault.secrets (secret, name, description) values (s, n, d) returning id $$;
"""


class Fake:
    """The project as the Management API shows it, over a local database."""

    def __init__(self, db, **kw):
        self.db = db
        self.project = {'ref': REF, 'status': kw.get('status', 'ACTIVE_HEALTHY'), 'region': kw.get('region', 'eu-central-1'), 'organization_id': 'org-x'}
        self.plan = kw.get('plan', 'free')
        self.auth = {'disable_signup': False, 'external_email_enabled': True, 'external_google_enabled': False, 'external_github_enabled': True,
                     'external_anonymous_users_enabled': True, 'external_phone_enabled': False, 'mailer_autoconfirm': True,
                     'jwt_exp': 3600, 'rate_limit_verify': 30, 'site_url': 'http://localhost:3000', 'uri_allow_list': ''}
        self.reject = set(kw.get('reject', ()))          # Auth fields the stand-in refuses, like an API that does not know them
        self.postgrest = {'db_schema': 'public,graphql_public'}
        self.secrets = {}                                # name -> raw value (the API itself shows a digest)
        self.functions = set(kw.get('functions', ()))
        self.service = 'svc_' + secrets.token_hex(20)
        self.secret_key = 'sk_' + secrets.token_hex(20)
        self.publishable = 'pk_' + secrets.token_hex(20)
        self.accept = {self.secret_key} if kw.get('legacy_refused') else {self.service, self.secret_key}
        self.codes, self.log = [], []

    def ntables(self):
        return int(self.db.psql("select count(*) from pg_tables where schemaname = 'public'", user='supabase_admin')[0][0][0])

    def sql(self, q):
        rows, err = self.db.psql(q, user='supabase_admin')
        if err and 'ERROR' in err:
            return 400, {'message': err.strip().splitlines()[-1]}
        if q.lstrip().lower().startswith("select coalesce(json_agg(wi_row)"):
            return 201, [{'rows': '\n'.join(r[0] for r in rows) if rows else '[]'}]     # psql splits a multi-line value
        self.log.append(('sql', q.strip()[:60], self.ntables()))
        return 201, []

    def db_push(self):
        self.db.psql('create schema if not exists supabase_migrations; create table if not exists supabase_migrations.schema_migrations (version text primary key, name text)', user='supabase_admin')
        have = {r[0] for r in self.db.psql('select version from supabase_migrations.schema_migrations', user='supabase_admin')[0]}
        out = []
        for f in sorted(glob.glob(os.path.join(ROOT, 'supabase', 'migrations', '*.sql'))):
            v = os.path.basename(f).split('_')[0]
            if v in have:
                continue
            out.append(f'Applying migration {os.path.basename(f)}...')
            rows, err = self.db.psql(None, file=f)
            if err and 'ERROR' in err:
                return {'ok': False, 'out': '\n'.join(out + [err])}
            out += [ln for ln in (err or '').splitlines() if 'NOTICE' in ln]
            self.db.psql(f"insert into supabase_migrations.schema_migrations values ('{v}', '{os.path.basename(f)}')", user='supabase_admin')
        self.log.append(('db_push', len(out), self.ntables()))
        return {'ok': True, 'out': '\n'.join(out) or 'Remote database is up to date.'}

    def handle(self, method, path, body, headers):
        p = path.split('?')[0]
        base = f'/v1/projects/{REF}'
        if method == 'GET' and p == base:
            return 200, self.project
        if method == 'GET' and p == '/v1/organizations/org-x':
            return 200, {'id': 'org-x', 'plan': self.plan}
        if p == base + '/config/auth':
            if method == 'GET':
                return 200, dict(self.auth)
            if self.reject & set(body):
                return 400, {'message': 'unknown field'}
            self.auth.update(body)
            self.log.append(('auth', sorted(body), self.ntables()))
            return 200, dict(self.auth)
        if p == base + '/postgrest':
            if method == 'PATCH':
                self.postgrest.update(body); self.log.append(('postgrest', body, self.ntables()))
            return 200, self.postgrest
        if method == 'POST' and p == base + '/database/query':
            return self.sql(body['query'])
        if p == base + '/secrets':
            if method == 'POST':
                for s in body:
                    self.secrets[s['name']] = s['value']
                self.log.append(('secrets', [s['name'] for s in body], self.ntables()))
                return 201, None
            return 200, [{'name': k, 'value': hashlib.sha256(v.encode()).hexdigest()} for k, v in self.secrets.items()]
        if method == 'GET' and p == base + '/functions':
            return 200, [{'slug': f, 'status': 'ACTIVE'} for f in sorted(self.functions)]
        if method == 'GET' and p == base + '/api-keys':
            return 200, [{'name': 'anon', 'type': 'legacy', 'api_key': 'anon_' + self.publishable},
                         {'name': 'service_role', 'type': 'legacy', 'api_key': self.service},
                         {'name': 'default', 'type': 'publishable', 'api_key': self.publishable},
                         {'name': 'default', 'type': 'secret', 'api_key': self.secret_key}]
        if method == 'POST' and p == '/functions/v1/admin-class':
            key = headers.get('authorization', '').removeprefix('Bearer ')
            if key not in self.accept or 'admin-class' not in self.functions:
                return 403, {'ok': False, 'e': 'forbidden'}
            code = ''.join(secrets.choice('ABCDEFGHJKMNPQRSTUVWXYZ23456789') for _ in range(8))
            cid = self.db.psql(f"select private.class_create('{body['name']}', '{body['grade']}', '{secrets.token_hex(32)}')", user='supabase_admin')[0][0][0]
            self.codes.append(code)
            self.log.append(('class', body['name'], self.ntables()))
            return 200, {'ok': True, 'class_id': cid, 'class_code': code}
        if method == 'POST' and p == '/_fake/db_push':
            return 200, self.db_push()
        if method == 'POST' and p == '/_fake/deploy':
            self.functions.add(body['name']); self.log.append(('deploy', body['name'], self.ntables()))
            return 200, {'ok': True}
        return 404, {'message': f'no route {method} {p}'}


def serve(fake):
    class H(BaseHTTPRequestHandler):
        def _go(self):
            n = int(self.headers.get('content-length') or 0)
            body = json.loads(self.rfile.read(n).decode()) if n else None
            s, j = fake.handle(self.command, self.path, body, {k.lower(): v for k, v in self.headers.items()})
            out = json.dumps(j).encode()
            self.send_response(s); self.send_header('content-type', 'application/json'); self.send_header('content-length', str(len(out))); self.end_headers()
            self.wfile.write(out)
        do_GET = do_POST = do_PATCH = _go

        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def project(**kw):
    os.environ['WI_MIGRATIONS'] = tempfile.mkdtemp(prefix='wi-nomig-')       # an empty project: the stub only
    db = pg.start()
    rows, err = db.psql(VAULT, user='supabase_admin')
    if err and 'ERROR' in err:
        db.stop(); raise RuntimeError(err)
    fake = Fake(db, **kw)
    return db, fake, serve(fake)


def run(srv, fake, confirm='setup trial', extra=()):
    url = f'http://127.0.0.1:{srv.server_address[1]}'
    log = tempfile.mktemp(prefix='wi-cli-')
    env = dict(os.environ, WI_FAKE_API=url, WI_FAKE_CLI_LOG=log)
    env['SUPABASE_ACCESS_TOKEN'], env['SUPABASE_DB_PASSWORD'] = fake.token, fake.dbpw          # made-up values (fresh())
    env.pop('HTTPS_PROXY', None); env.pop('https_proxy', None)
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'supabase_setup.py'), '--dry-run', '--confirm', confirm, '--ref', REF,
                        '--api', url, '--project-url', url, '--cli', os.path.join(ROOT, 'tests', 'setup_fake_cli.py')] + list(extra),
                       env=env, capture_output=True, text=True, timeout=600)
    cli = [json.loads(ln) for ln in open(log, encoding='utf-8')] if os.path.exists(log) else []
    return r, cli


def leaks(out, values):
    """Every secret may appear only on its own ::add-mask:: line."""
    bad = []
    for v in values:
        for ln in out.splitlines():
            if v and v in ln and ln != f'::add-mask::{v}':
                bad.append(ln[:80].replace(v, '<SECRET>'))
    return bad


def secrets_of(fake):
    return [fake.token, fake.dbpw, fake.service, fake.secret_key, fake.secrets.get('PUPIL_PEPPER', '')] + fake.codes


def fresh():
    db, fake, srv = project(functions={'admin-wrap-legacy'})
    fake.token, fake.dbpw = 'tok_' + secrets.token_hex(16), 'pw_' + secrets.token_hex(16)
    try:
        r, cli = run(srv, fake)
        out = r.stdout + r.stderr
        check('a fresh project: the setup ends without stopping', r.returncode == 0 and 'STOPPED' not in out, out[-1500:])
        writes = [e for e in fake.log]
        check('the first write is "sign-ups off", alone, with no table in public', writes and writes[0] == ('auth', ['disable_signup'], 0), writes[:2])
        first_table = next((i for i, e in enumerate(writes) if e[2] > 0), len(writes))
        check('sign-ups were off before any table existed', fake.auth['disable_signup'] is True and first_table > 0, writes[:first_table + 1])
        check('Auth as DAY0 section 1: email on, confirm email, no anonymous, other providers off, verify limit 150, site and redirect',
              fake.auth['external_email_enabled'] and not fake.auth['mailer_autoconfirm'] and not fake.auth['external_anonymous_users_enabled']
              and not fake.auth['external_github_enabled'] and fake.auth['rate_limit_verify'] == 150
              and fake.auth['uri_allow_list'].endswith('/english-trainer/teacher.html') and fake.auth['security_refresh_token_reuse_interval'] == 10, fake.auth)
        check('the API exposes schema public only', fake.postgrest['db_schema'] == 'public', fake.postgrest)
        v = db.psql('select string_agg(version, \',\' order by version) from supabase_migrations.schema_migrations', user='supabase_admin')[0][0][0]
        want = ','.join(os.path.basename(f).split('_')[0] for f in sorted(glob.glob(os.path.join(ROOT, 'supabase', 'migrations', '*.sql'))))
        check(f'migrations {want} applied through the CLI (link, then db push confirmed)', v == want and ['link', '--project-ref', REF] in cli, (v, cli[:2]))
        n = db.psql('select (select count(*) from public.items), (select count(*) from public.levels), (select raw_days from private.settings)', user='supabase_admin')[0][0]
        check('catalog seeded (88 items, 39 levels) and raw_days 30', n == ['88', '39', '30'], n)
        pep = fake.secrets.get('PUPIL_PEPPER', '')
        check('PUPIL_PEPPER set: 32 random bytes, base64', len(pep) == 44 and pep.endswith('='), len(pep))
        check('ALLOWED_ORIGINS is the game\'s origin only', fake.secrets.get('ALLOWED_ORIGINS') == 'https://jaouibenjamin.github.io', fake.secrets.get('ALLOWED_ORIGINS'))
        deployed = [c[2] for c in cli if c[:2] == ['functions', 'deploy']]
        check('exactly the five functions deployed (--use-api), never admin-wrap-legacy',
              sorted(deployed) == sorted(['pupil-login', 'pupil-register', 'pupil-recover', 'teacher-reset', 'admin-class'])
              and all('--use-api' in c for c in cli if c[:2] == ['functions', 'deploy']), deployed)
        check('admin-wrap-legacy found deployed: the owner is told to delete it', 'delete admin-wrap-legacy' in out)
        t = db.psql("select c.name, (select string_agg(display_name, ',' order by display_name) from public.roster r where r.class_id = c.id), "
                    "(select count(*) from private.class_codes k where k.class_id = c.id) from public.classes c", user='supabase_admin')[0]
        check('the class Trial, with its code lookup and the roster Test, Tester', t == [['Trial', 'Test,Tester', '1']], t)
        vs = db.psql("select secret from vault.secrets where name = 'wi_trial_class_code'", user='supabase_admin')[0]
        check('the class code is in the Vault, and it is the one admin-class made', vs == [[fake.codes[0]]] if fake.codes else False, vs)
        bad = leaks(out, secrets_of(fake))
        check('no secret in the log: token, database password (echoed by the CLI), server keys, pepper, class code only on ::add-mask:: lines',
              not bad and all(f'::add-mask::{s}' in out for s in (fake.token, fake.dbpw, fake.service, pep, fake.codes[0] if fake.codes else '-')), bad)
        check('the log ends with the revoke reminder', 'revoke the access token' in out)
        n_writes = len(fake.log)
        r2, cli2 = run(srv, fake)
        out2 = r2.stdout + r2.stderr
        check('a second run changes nothing and says so', r2.returncode == 0 and 'nothing changed' in out2 and len(fake.log) == n_writes
              and not [c for c in cli2 if c[:1] != ['link']] and len(fake.codes) == 1, (out2[-800:], fake.log[n_writes:], cli2))
        check('the second run leaves the pepper as it was', fake.secrets.get('PUPIL_PEPPER') == pep)
        r3, cli3 = run(srv, fake, extra=['--redeploy'])
        check('--redeploy deploys the five functions again, and nothing else', r3.returncode == 0
              and len([c for c in cli3 if c[:2] == ['functions', 'deploy']]) == 5 and not [c for c in cli3 if c[:2] == ['db', 'push']], cli3)
    finally:
        srv.shutdown(); db.stop()


def refused(label, kw=None, prep=None, confirm='setup trial'):
    db, fake, srv = project(**(kw or {}))
    fake.token, fake.dbpw = 'tok_' + secrets.token_hex(16), 'pw_' + secrets.token_hex(16)
    try:
        if prep:
            db.psql(prep, user='supabase_admin')
        r, cli = run(srv, fake, confirm=confirm)
        out = r.stdout + r.stderr
        check(f'{label}: stops before any write', r.returncode == 1 and 'STOPPED' in out and not fake.log and not cli, (out[-600:], fake.log, cli))
    finally:
        srv.shutdown(); db.stop()


def fallback():
    db, fake, srv = project(legacy_refused=True, reject={'mfa_web_authn_enroll_enabled'})
    fake.token, fake.dbpw = 'tok_' + secrets.token_hex(16), 'pw_' + secrets.token_hex(16)
    try:
        r, cli = run(srv, fake)
        out = r.stdout + r.stderr
        check('the legacy service_role key refused: the secret key makes the class', r.returncode == 0 and len(fake.codes) == 1, out[-800:])
        check('an Auth field the API refuses: the others are set one by one, and that one is left to the owner by hand',
              'mfa_web_authn_enroll_enabled' in out and 'by hand' in out and fake.auth.get('jwt_exp') == 3600 and fake.auth['disable_signup'] is True, out[-800:])
        check('no secret in the log on that path either', not leaks(out, secrets_of(fake)))
    finally:
        srv.shutdown(); db.stop()


def workflow():
    path = os.path.join(ROOT, '.github', 'workflows', 'supabase-setup.yml')
    w = open(path, encoding='utf-8').read()
    on = w.split('\non:', 1)[1].split('\npermissions:', 1)[0]
    check('workflow: started by hand only (workflow_dispatch; no push, pull_request, schedule or workflow_run)',
          'workflow_dispatch:' in on and not re.search(r'^\s{2}(push|pull_request\w*|schedule|workflow_run|workflow_call|repository_dispatch):', on, re.M), on[:200])
    check('workflow: permissions contents: read, and no job asks for more', re.search(r'^permissions:\n  contents: read\n', w, re.M) is not None
          and w.count('permissions:') == 1)
    jobs = re.findall(r"^    if: (.+)$", w, re.M)
    check('workflow: each job only for the owner (actor and triggering actor) on game or main', len(jobs) == 2 and all(
        "github.actor == 'jaouibenjamin'" in j and "github.triggering_actor == 'jaouibenjamin'" in j
        and "github.ref == 'refs/heads/game'" in j and "github.ref == 'refs/heads/main'" in j for j in jobs), jobs)
    uses = re.findall(r'uses:\s*(\S+)', w)
    check('workflow: every action pinned by a 40-character commit', uses and all(re.fullmatch(r'[\w.-]+/[\w.-]+@[0-9a-f]{40}', u) for u in uses), uses)
    check('workflow: the CLI pinned by version and sha256, checked before use', re.search(r'cli-linux-x64-\d+\.\d+\.\d+\.tgz', w) is not None
          and re.search(r'echo "[0-9a-f]{64}  cli\.tgz" \| sha256sum -c -', w) is not None)
    runs = re.findall(r'run: \|\n((?:          .*\n?)+)', w)
    check('workflow: no ${{ }} inside a script (inputs and secrets reach the shell through env only)', runs and not any('${{' in r for r in runs))
    check('workflow: no set -x, no verbose curl', not re.search(r'set -[a-z]*x|curl [^\n]*(-v\b|--verbose)', w))
    check('workflow: the secrets appear only in the setup step\'s env, and the real job uses the supabase-setup environment',
          w.count('secrets.') == 2 and 'environment: supabase-setup' in w and w.index('secrets.') > w.index('name: Set up the project'))
    check('workflow: persist-credentials false on every checkout', w.count('actions/checkout@') == w.count('persist-credentials: false'))


def main():
    workflow()
    fresh()
    refused('a paused project', {'status': 'INACTIVE'})
    refused('a project outside the EU', {'region': 'us-east-1'})
    refused('an organization on a paid plan', {'plan': 'pro'})
    refused('a public schema with someone else\'s table', prep='create table public.orders (id int)')
    refused('a wrong confirmation', confirm='setup')
    fallback()
    print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
