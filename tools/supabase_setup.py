#!/usr/bin/env python3
"""The one-button setup of the Supabase project for the trial: docs/owner/DAY0.md without the laptop.

Run by .github/workflows/supabase-setup.yml (workflow_dispatch, the owner only), never by hand from a chat session.
The repository is public, so its Actions log is world-readable: nothing secret may reach stdout or stderr. Every key
this tool fetches, the pepper it makes and the trial class's code are announced to GitHub with ::add-mask:: before
anything else is done with them, and every line printed (also the CLI's output) goes through redact() as well.

In order, each step first reads what is there and changes only what differs (a second run changes nothing and says
so):
  0. the project: ACTIVE_HEALTHY, region eu-*, organization on the free plan; public empty with no auth users and no
     storage buckets (a new project), or holding exactly our own migrations (a run that stopped half way). Anything
     else: stop before writing anything.
  1. Auth: sign-ups OFF first (before any table exists), then the rest of A3, A5 to A8 through the Management API.
  2. the API exposes schema public only (A9); pg_graphql off; pg_cron on; no table in the realtime publication.
  3. supabase db push (0001 to 0009), the catalog seed, raw_days = 30.
  4. function secrets: PUPIL_PEPPER (made here with openssl, set once, never shown, never replaced) and
     ALLOWED_ORIGINS.
  5. the five functions (not admin-wrap-legacy); already deployed ones are left alone unless --redeploy.
  6. the trial class "Trial" (through admin-class, the only code path that makes a class code), its code stored in the
     project's Vault for the owner to copy in the dashboard; the roster Test and Tester.
  7. live_check.py --stage 1 with the publishable key; the checklist of what only the dashboard can set; the reminder
     to revoke the access token.

  --rotate-trial does only this: a new code for the trial class (admin-class rotate), put in the Vault. For when the
  code was lost (the Vault refused it, the answer never came, or it was deleted before it was copied).

    python3 tools/supabase_setup.py --confirm "setup trial" --cli /path/to/supabase
        needs SUPABASE_ACCESS_TOKEN and SUPABASE_DB_PASSWORD in the environment
    --dry-run --api http://127.0.0.1:PORT --project-url http://127.0.0.1:PORT --cli tests/setup_fake_cli.py
        what tests/setup_check.py runs against its stand-in of the Management API and a local database"""
import argparse, glob, hashlib, json, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_FILE = os.path.join(ROOT, 'supabase', 'project_ref')   # the one place the project's ref is written (tools/project_ref.py)


def project_ref():
    try:
        return open(REF_FILE, encoding='utf-8').read().strip()
    except OSError:
        return ''
CONFIRM = 'setup trial'
FUNCTIONS = ['pupil-login', 'pupil-register', 'pupil-recover', 'teacher-reset', 'admin-class']
ORIGIN = 'https://jaouibenjamin.github.io'
GAME = ORIGIN + '/english-trainer/'
TRIAL, TRIAL_PUPILS = 'Trial', ['Test', 'Tester']
VAULT_NAME = 'wi_trial_class_code'
# The settings of DAY0.md section 1 that the Management API can set. Every external_*_enabled other than email is
# switched off too (Google is switched on later, at the teacher's step).
AUTH = {
    'external_email_enabled': True, 'mailer_autoconfirm': False, 'mailer_secure_email_change_enabled': True,
    'external_anonymous_users_enabled': False, 'external_phone_enabled': False,
    'security_manual_linking_enabled': False,
    'mfa_totp_enroll_enabled': False, 'mfa_phone_enroll_enabled': False, 'mfa_web_authn_enroll_enabled': False,
    'jwt_exp': 3600, 'refresh_token_rotation_enabled': True, 'security_refresh_token_reuse_interval': 10,
    'site_url': GAME, 'uri_allow_list': GAME + 'teacher.html',
}
RATE_VERIFY = 150          # token verifications per 5 minutes: at least this (A7); a higher value is left as it is


class Stop(Exception):
    pass


def ours():
    """Our migrations as the CLI records them (the version is the part before the first _), and the tables they make."""
    files = sorted(glob.glob(os.path.join(ROOT, 'supabase', 'migrations', '*.sql')))
    tables = set()
    for f in files:
        tables |= set(re.findall(r'create table (?:if not exists )?public\.([a-z_][a-z0-9_]*)', open(f, encoding='utf-8').read(), re.I))
    return [os.path.basename(f).split('_')[0] for f in files], tables


class Setup:
    def __init__(self, a):
        self.a = a
        self.ref = a.ref
        self.token = os.environ.get('SUPABASE_ACCESS_TOKEN', '')
        self.dbpw = os.environ.get('SUPABASE_DB_PASSWORD', '')
        self.hidden = []
        self.changed, self.manual = [], []
        self.next_said = False

    # ---------- output: nothing secret, ever ----------
    @staticmethod
    def forms(v):
        """A value as it may appear in output: as it is, URL-encoded (a connection string, a query) and JSON-encoded."""
        return {v, urllib.parse.quote(v, safe=''), urllib.parse.quote_plus(v), json.dumps(v)[1:-1]}

    def mask(self, v):
        if v:
            for f in sorted(self.forms(v), key=len, reverse=True):
                if f not in self.hidden:
                    sys.stdout.write(f'::add-mask::{f}\n'); sys.stdout.flush()
                    self.hidden.append(f)

    def redact(self, s):
        for v in sorted(self.hidden, key=len, reverse=True):
            if v and len(v) >= 6:
                s = s.replace(v, '***')
        return s

    def say(self, s=''):
        print(self.redact(str(s)), flush=True)

    def change(self, what):
        self.changed.append(what)
        self.say(f'  changed: {what}')

    # ---------- the Management API ----------
    def http(self, method, url, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={**(headers or {}), **({'content-type': 'application/json'} if data else {})})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read().decode() or 'null'
                return r.status, json.loads(raw) if raw.strip()[:1] in '[{"' or raw.strip() in ('null', 'true', 'false') else raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors='replace')
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw

    def api(self, method, path, body=None, ok=(200, 201, 204)):
        s, j = self.http(method, self.a.api + path, body, {'authorization': f'Bearer {self.token}'})
        if s not in ok:
            raise Stop(f'{method} {path.split("?")[0]}: HTTP {s} {self.redact(json.dumps(j) if not isinstance(j, str) else j)[:300]}')
        return j

    def sql(self, query):
        return self.api('POST', f'/v1/projects/{self.ref}/database/query', {'query': query}, ok=(200, 201))

    def rows(self, select):
        r = self.sql(f"select coalesce(json_agg(wi_row), '[]'::json) as rows from ({select}) wi_row")
        v = (r or [{}])[0].get('rows', [])
        return json.loads(v) if isinstance(v, str) else v

    def one(self, select):
        r = self.rows(select)
        return next(iter(r[0].values())) if r else None

    # ---------- 0. the project ----------
    def check_project(self):
        self.say('0. the project')
        p = self.api('GET', f'/v1/projects/{self.ref}')
        status, region, org = p.get('status'), p.get('region', ''), p.get('organization_id')
        self.say(f'  status {status}, region {region}')
        if status != 'ACTIVE_HEALTHY':
            raise Stop(f'the project is {status}, not ACTIVE_HEALTHY. Next: restore it in the Supabase dashboard (free), then run again')
        if not str(region).startswith('eu-'):
            raise Stop(f'the region is {region}, not in the EU (DAY0.md step 0), and a region cannot be changed. Next: create a new '
                       'project in Frankfurt (eu-central-1) on the Free plan and send the lead its ref; keep this one untouched')
        o = self.api('GET', f'/v1/organizations/{org}')
        plan = str(o.get('plan', '')).lower()
        self.say(f'  plan {plan or "(not given)"}')
        if plan != 'free':
            raise Stop(f'the organization\'s plan is "{plan}", not free (the owner\'s rule: free only). Next: tell the lead')
        versions, tables = ours()
        have = [r['t'] for r in self.rows("select tablename as t from pg_tables where schemaname = 'public'")]
        hist = []
        if self.one("select to_regclass('supabase_migrations.schema_migrations') is not null as e"):
            hist = [r['v'] for r in self.rows('select version as v from supabase_migrations.schema_migrations order by version')]
        if not have and not hist:
            users = self.one('select count(*) as n from auth.users')
            buckets = self.one('select count(*) as n from storage.buckets') if self.one("select to_regclass('storage.buckets') is not null as e") else 0
            if users or buckets:
                raise Stop(f'public is empty but the project is not new ({users} auth users, {buckets} storage buckets). '
                           'Next: tell the lead these two numbers')
            self.say('  public is empty, no auth users, no storage buckets: a fresh project')
        elif hist == versions[:len(hist)] and set(have) <= tables:
            self.say(f'  it holds our own migrations {", ".join(hist) or "(none recorded)"} and nothing else: carrying on')
        else:
            foreign = sorted(set(have) - tables)[:10]
            raise Stop(f'public is not empty and not ours ({len(have)} tables, e.g. {foreign or have[:10]}; migrations {hist[:10]}): '
                       'Next: tell the lead this line')
        self.versions = versions

    # ---------- 1. Auth ----------
    def auth(self):
        self.say('1. Auth settings')
        path = f'/v1/projects/{self.ref}/config/auth'
        cfg = self.api('GET', path)
        if cfg.get('disable_signup') is not True:
            self.api('PATCH', path, {'disable_signup': True})
            if self.api('GET', path).get('disable_signup') is not True:
                raise Stop('sign-ups could not be switched off. Next: switch them off in the dashboard (DAY0.md section 1, A3), then run again')
            self.change('sign-ups OFF')
        else:
            self.say('  sign-ups already OFF')
        cfg = self.api('GET', path)
        want = dict(AUTH)
        for k, v in cfg.items():
            if re.fullmatch(r'external_[a-z0-9_]+_enabled', k) and k not in want and v is True:
                want[k] = False
        if not isinstance(cfg.get('rate_limit_verify'), int) or cfg['rate_limit_verify'] < RATE_VERIFY:
            want['rate_limit_verify'] = RATE_VERIFY
        diff = {k: v for k, v in want.items() if cfg.get(k) != v}
        if diff:
            s, _ = self.http('PATCH', self.a.api + path, diff, {'authorization': f'Bearer {self.token}'})
            if s not in (200, 201, 204):                  # one field the API does not take: set the others one by one
                for k, v in diff.items():
                    self.http('PATCH', self.a.api + path, {k: v}, {'authorization': f'Bearer {self.token}'})
            now = self.api('GET', path)
            for k, v in diff.items():
                if now.get(k) == v:
                    self.change(f'{k} = {v}')
                else:
                    self.manual.append(f'Authentication: set {k} to {v} by hand (the API did not take it)')
        else:
            self.say('  the other Auth settings are already right')

    # ---------- 2. API, extensions, realtime ----------
    def api_and_extensions(self):
        self.say('2. API schemas, extensions, realtime')
        pg = self.api('GET', f'/v1/projects/{self.ref}/postgrest')
        if str(pg.get('db_schema', '')).replace(' ', '') != 'public':
            self.api('PATCH', f'/v1/projects/{self.ref}/postgrest', {'db_schema': 'public'})
            self.change('exposed schemas: public only')
        else:
            self.say('  exposed schemas: public only already')
        ext = {r['e'] for r in self.rows('select extname as e from pg_extension')}
        if 'pg_graphql' in ext:
            try:
                self.sql('drop extension if exists pg_graphql')
                self.change('pg_graphql off')
            except Stop as e:
                self.manual.append(f'Database → Extensions: switch pg_graphql off ({e})')
        else:
            self.say('  pg_graphql already off')
        if 'pg_cron' not in ext:
            try:
                self.sql('create extension if not exists pg_cron with schema pg_catalog')
                self.change('pg_cron on')
            except Stop:
                # migration 0003 creates it too; after db push, database() stops if the nightly job is not there
                self.say('  pg_cron: not switched on here; migration 0003 tries again, and step 3 checks the nightly job'
                         + (' (not available in the dry run: local database)' if self.a.dry_run else ''))
        else:
            self.say('  pg_cron already on')
        if self.one("select count(*) as n from pg_publication_tables where pubname = 'supabase_realtime'"):
            self.manual.append('Database → Publications: take every table out of supabase_realtime (realtime off)')
        else:
            self.say('  realtime: no table published')

    # ---------- 3. the database ----------
    def cli(self, *args, input_=None):
        cmd = [self.a.cli] + list(args)
        env = dict(os.environ)
        env['SUPABASE_ACCESS_TOKEN'], env['SUPABASE_DB_PASSWORD'] = self.token, self.dbpw   # the CLI reads both from env
        r = subprocess.run(cmd, cwd=ROOT, env=env, input=input_, capture_output=True, text=True, timeout=1800)
        for line in (r.stdout + r.stderr).splitlines():
            self.say('  | ' + line)
        if r.returncode:
            raise Stop(f'supabase {" ".join(args[:2])} failed (exit {r.returncode})')
        return r.stdout + r.stderr

    def history(self):
        if not self.one("select to_regclass('supabase_migrations.schema_migrations') is not null as e"):
            return []
        return [r['v'] for r in self.rows('select version as v from supabase_migrations.schema_migrations order by version')]

    def database(self):
        self.say('3. migrations, catalog, raw answers window')
        if self.history() == self.versions:
            self.say(f'  migrations {self.versions[0]} to {self.versions[-1]} already applied')
        else:
            self.cli('link', '--project-ref', self.ref)
            self.cli('db', 'push', '--include-all', input_='y\n')
            if self.history() != self.versions:
                raise Stop(f'after db push the project records {self.history()}, not {self.versions}')
            self.change(f'migrations {self.versions[0]} to {self.versions[-1]} applied')
        if self.one("select to_regclass('cron.job') is not null as e"):
            if not self.one("select count(*) as n from cron.job where jobname = 'wi-maintenance'"):
                raise Stop('the nightly maintenance is NOT scheduled (cron job wi-maintenance missing)')
            self.say('  maintenance is scheduled: every night at 02:17 UTC')
        elif not self.a.dry_run:
            raise Stop('pg_cron is missing: the nightly maintenance is NOT scheduled')
        seed = open(os.path.join(ROOT, 'supabase', 'seed', 'catalog.sql'), encoding='utf-8').read()
        m = re.search(r'--\s*(\d+) items, (\d+) levels', seed)
        n_items, n_levels = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        have = (self.one('select count(*) as n from public.items'), self.one('select count(*) as n from public.levels'))
        if m and have == (n_items, n_levels):
            self.say(f'  catalog already seeded ({n_items} items, {n_levels} levels)')
        else:
            self.sql(seed)
            self.change(f'catalog seeded ({self.one("select count(*) as n from public.items")} items)')
        if self.one('select raw_days as n from private.settings') != 30:
            self.sql('update private.settings set raw_days = 30')
            self.change('raw_days = 30')
        else:
            self.say('  raw_days already 30')

    # ---------- 4. function secrets ----------
    def function_secrets(self):
        self.say('4. function secrets')
        have = {s.get('name'): s.get('value') for s in (self.api('GET', f'/v1/projects/{self.ref}/secrets') or [])}
        if 'PUPIL_PEPPER' in have:
            self.say('  PUPIL_PEPPER already set: left as it is (it is never replaced)')
        else:
            r = subprocess.run(['openssl', 'rand', '-base64', '32'], capture_output=True, text=True)
            pepper = r.stdout.strip()
            if r.returncode or len(pepper) < 40:
                raise Stop('openssl could not make the pepper')
            self.mask(pepper)
            self.api('POST', f'/v1/projects/{self.ref}/secrets', [{'name': 'PUPIL_PEPPER', 'value': pepper}])
            del pepper
            self.change('PUPIL_PEPPER set (made in this job; nobody has seen it)')
        if have.get('ALLOWED_ORIGINS') in (hashlib.sha256(ORIGIN.encode()).hexdigest(), ORIGIN):
            self.say('  ALLOWED_ORIGINS already set')
        else:
            self.api('POST', f'/v1/projects/{self.ref}/secrets', [{'name': 'ALLOWED_ORIGINS', 'value': ORIGIN}])
            self.change('ALLOWED_ORIGINS set')

    # ---------- 5. functions ----------
    def functions(self):
        self.say('5. functions')
        have = {f.get('slug') for f in (self.api('GET', f'/v1/projects/{self.ref}/functions') or [])}
        for f in FUNCTIONS:
            if f in have and not self.a.redeploy:
                self.say(f'  {f} already deployed')
                continue
            self.cli('functions', 'deploy', f, '--project-ref', self.ref, '--use-api')
            self.change(f'{f} deployed')
        if 'admin-wrap-legacy' in have:
            self.manual.append('Edge Functions: delete admin-wrap-legacy (the Sheet import, not used in the fresh start)')

    # ---------- 6. the trial class ----------
    def trial(self):
        self.say('6. the trial class')
        cid = self.one(f"select id::text as id from public.classes where name = '{TRIAL}' order by created_at limit 1")
        if cid:
            if self.one(f"select count(*) as n from vault.secrets where name = '{VAULT_NAME}'") if self.vault() else 0:
                self.say(f'  {TRIAL} already exists; its code is in the Vault as {VAULT_NAME}')
            else:
                self.say(f'  {TRIAL} already exists; its code is not in the Vault (copied and deleted, or never stored)')
                self.manual.append(f'if you do not have the {TRIAL} class code: run this workflow again with mode rotate-trial '
                                   f'(a new code, put in the Vault as {VAULT_NAME})')
        else:
            if not self.vault():
                self.say(f'  the Vault is not there (no vault.create_secret): {TRIAL} is NOT made here, so its code cannot be lost')
                self.manual.append('the Vault is not available: make the trial class by hand (docs/owner/DAY0.md step 7)')
                return
            self.say(f'  {TRIAL} does not exist yet: making it through admin-class, its code going to the Vault')
            code, cid = self.admin_class({'action': 'create', 'name': TRIAL, 'grade': '5'})
            self.change(f'class {TRIAL} made')                # recorded before the Vault, so a stop after it says so
            self.store_code(code, 'made')
            del code
        n = self.one(f"select count(*) as n from public.roster where class_id = '{cid}'")
        if n != len(TRIAL_PUPILS):
            names = ', '.join(f"'{x}'" for x in TRIAL_PUPILS)
            self.sql(f"insert into public.roster (class_id, name_key, display_name) select '{cid}', app.name_key(n), n "
                     f"from unnest(array[{names}]) n on conflict do nothing")
            self.change(f'roster of {TRIAL}: {", ".join(TRIAL_PUPILS)}')
        else:
            self.say(f'  roster of {TRIAL} already {", ".join(TRIAL_PUPILS)}')

    def vault(self):
        # by name, not by an exact signature: the hosted create_secret has more parameters, with defaults
        # (new_secret, new_name, new_description, new_key_id), so to_regprocedure('...(text,text,text)') found nothing
        return self.one("select exists (select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
                        "where n.nspname = 'vault' and p.proname = 'create_secret') as e")

    def admin_class(self, body):
        """Calls the project's admin-class with a server key (the legacy service_role key first, then the secret key);
        returns (class_code, class_id), both checked, the code masked before anything else."""
        keys = self.api('GET', f'/v1/projects/{self.ref}/api-keys?reveal=true') or []
        cands = [k.get('api_key') for k in keys if k.get('name') == 'service_role'] + \
                [k.get('api_key') for k in keys if k.get('type') == 'secret']
        cands = [k for k in cands if k]
        for k in cands:
            self.mask(k)
        made = None
        for k in cands:
            s, j = self.http('POST', f'{self.a.project_url}/functions/v1/admin-class', body, {'authorization': f'Bearer {k}', 'apikey': k})
            if s == 200 and isinstance(j, dict) and j.get('ok'):
                made = j
                break
        del cands, keys
        if not made:
            raise Stop(f'admin-class refused every server key or did not answer ({body["action"]}): nothing was stored. '
                       f'If the class now exists, run again with mode rotate-trial; otherwise make it by hand (DAY0.md step 7)')
        code = str(made.get('class_code', ''))
        self.mask(code)
        cid = str(made.get('class_id', body.get('class_id', '')))
        if not re.fullmatch(r'[A-Z0-9]{8}', code) or not re.fullmatch(r'[0-9a-f-]{36}', cid):
            raise Stop('admin-class answered in an unexpected shape: run again with mode rotate-trial')
        return code, cid

    def store_code(self, code, how):
        note = 'The trial class code (docs/owner/DAY0.md): copy it into the password manager, then delete this secret'
        try:                                            # named arguments: the hosted functions have more, with defaults
            if self.one(f"select count(*) as n from vault.secrets where name = '{VAULT_NAME}'"):
                self.sql(f"select vault.update_secret(id, new_secret => '{code}') from vault.secrets where name = '{VAULT_NAME}'")
            else:
                self.sql(f"select vault.create_secret(new_secret => '{code}', new_name => '{VAULT_NAME}', new_description => '{note}')")
        except Stop:
            raise Stop(f'the {TRIAL} class code was {how} but could not be put in the Vault, so it is lost: '
                       'run this workflow again with mode rotate-trial for a new one')
        self.change(f'its code put in the Vault as {VAULT_NAME}')

    # ---------- rotate-trial: a new code for the trial class ----------
    def rotate_trial(self):
        self.say('the trial class: a new code')
        cid = self.one(f"select id::text as id from public.classes where name = '{TRIAL}' order by created_at limit 1")
        if not cid:
            raise Stop(f'there is no class {TRIAL}: run the setup (mode real) first')
        if not self.vault():
            raise Stop('the Vault is not available: rotate by hand (admin-class rotate, DAY0.md step 7)')
        code, _ = self.admin_class({'action': 'rotate', 'class_id': cid})
        self.change(f'class {TRIAL} given a new code (the old one no longer works)')
        self.store_code(code, 'given a new code')
        del code

    # ---------- 7. check, checklist ----------
    def stage1(self):
        self.say('7. live_check.py --stage 1')
        if self.a.dry_run:
            self.say('  skipped in the dry run')
            return
        keys = self.api('GET', f'/v1/projects/{self.ref}/api-keys?reveal=true') or []
        pub = next((k.get('api_key') for k in keys if k.get('type') == 'publishable'), None) or \
            next((k.get('api_key') for k in keys if k.get('name') == 'anon'), None)
        for k in keys:                                  # the reveal lists every key: hide all but the public one
            if k.get('api_key') and k.get('api_key') != pub:
                self.mask(k.get('api_key'))
        del keys
        env = {k: v for k, v in os.environ.items() if not k.startswith('SUPABASE_')}
        env.update(SUPABASE_URL=self.a.project_url, SUPABASE_ANON_KEY=pub or '')
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests', 'live_check.py'), '--stage', '1'], env=env,
                           capture_output=True, text=True, timeout=600)
        for line in (r.stdout + r.stderr).splitlines():
            self.say('  | ' + line)
        if r.returncode:
            self.manual.append('live_check stage 1 is not all green: fix the FAIL lines above in the dashboard')

    def run(self):
        if self.a.confirm != CONFIRM:
            raise Stop(f'the confirmation was not "{CONFIRM}". Next: run it again and type exactly: {CONFIRM}')
        if not re.fullmatch(r'[a-z]{20}', self.ref or ''):
            raise Stop('supabase/project_ref holds no project ref yet. Next: the lead sets it (tools/project_ref.py set <ref>) '
                       'and ships it to main; then run again')
        if not self.a.dry_run and (not self.token or not self.dbpw):
            raise Stop('SUPABASE_ACCESS_TOKEN and SUPABASE_DB_PASSWORD must be set (GitHub secrets)')
        if not self.a.dry_run and not (self.a.api.startswith('https://') and self.a.project_url == f'https://{self.ref}.supabase.co'):
            raise Stop('a real run talks only to https://api.supabase.com and the project itself')
        self.mask(self.token); self.mask(self.dbpw)
        if self.a.rotate_trial:
            p = self.api('GET', f'/v1/projects/{self.ref}')
            if p.get('status') != 'ACTIVE_HEALTHY':
                raise Stop(f'the project is {p.get("status")}, not ACTIVE_HEALTHY')
            self.rotate_trial()
            return
        self.check_project()
        self.auth()
        self.api_and_extensions()
        self.database()
        self.function_secrets()
        self.functions()
        self.trial()
        self.stage1()


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--confirm', default='')
    p.add_argument('--ref', default=None, help='default: the ref in supabase/project_ref')
    p.add_argument('--api', default='https://api.supabase.com')
    p.add_argument('--project-url', default=None)
    p.add_argument('--cli', default='supabase')
    p.add_argument('--redeploy', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--rotate-trial', action='store_true', help='only give the trial class a new code, into the Vault')
    a = p.parse_args()
    a.ref = a.ref or project_ref()
    a.project_url = a.project_url or f'https://{a.ref}.supabase.co'
    s = Setup(a)
    try:
        s.run()
        code = 0
    except Stop as e:
        s.say(f'\nSTOPPED: {s.redact(str(e))}')
        s.next_said = 'Next:' in str(e)
        code = 1
    except Exception as e:                          # no traceback: it could quote a value; the type and a redacted line only
        s.say(f'\nSTOPPED: {type(e).__name__}: {s.redact(str(e))[:300]}')
        code = 1
    if code:
        # A refusal or a stop: what stopped it (above), what was changed, what to do next. No list, no revoke reminder:
        # the token is still needed for the next run.
        if not s.changed:
            s.say('Nothing was changed.')
            if not s.next_said:                     # an unexpected stop (a timeout, an odd answer) carries no next step
                s.say('Next: run it again; if it stops the same way, send the lead the STOPPED line (it holds no secret).')
        else:
            s.say('Changed before it stopped: ' + '; '.join(s.changed) + '.')
            s.say('Next: fix what stopped it, then run again; the run carries on from where it stopped.')
        sys.exit(code)
    s.say('\n== what is left for the owner ==')
    for m in ['A1: 2FA on the Supabase, GitHub and Google accounts; recovery codes on paper',
              'A2: GitHub → Settings → Code security: secret scanning and push protection on'] + s.manual:
        s.say(f'  - {m}')
    if s.a.rotate_trial or any('class Trial' in c for c in s.changed):
        s.say(f'  - the trial class code: Supabase → Project Settings → Vault (or Integrations → Vault) → {VAULT_NAME}: '
              'copy it into the password manager, then delete that secret')
    s.say('  - send the lead only "setup done" and the publishable key (sb_publishable_…)')
    s.say('\n' + ('nothing changed: the project was already set up' if not s.changed else f'{len(s.changed)} changes made'))
    if s.token:                                     # a run that used the access token, and finished
        s.say('\nNOW: revoke the access token (supabase.com → Account → Access Tokens → the setup token → Revoke), and delete '
              'both secrets from the supabase-setup environment (GitHub → Settings → Environments → supabase-setup).')
    sys.exit(code)


if __name__ == '__main__':
    main()
