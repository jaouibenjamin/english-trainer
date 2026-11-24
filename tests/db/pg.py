"""A throw-away local PostgreSQL for the backend tests: no Docker, no Supabase project.
start() makes a fresh cluster in a temp dir, loads tests/db/stub.sql (the stand-in for what Supabase provides) and
every file of supabase/migrations in order, as the non-superuser `postgres`, and returns a Db to talk to it with psql."""
import glob, json, os, pwd, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = 'wi_test'


def bindir():
    for c in [shutil.which('pg_config')]:
        if c:
            d = subprocess.run([c, '--bindir'], capture_output=True, text=True).stdout.strip()
            if os.path.exists(os.path.join(d, 'initdb')):
                return d
    found = sorted(glob.glob('/usr/lib/postgresql/*/bin/initdb')) + sorted(glob.glob('/opt/homebrew/opt/postgresql*/bin/initdb'))
    if found:
        return os.path.dirname(found[-1])
    w = shutil.which('initdb')
    if w:
        return os.path.dirname(w)
    sys.exit('PostgreSQL is not installed. Debian/Ubuntu: sudo apt-get install -y postgresql   macOS: brew install postgresql@16')


class Db:
    def __init__(self, bin_, sock, port, as_user):
        self.bin, self.sock, self.port, self.as_user = bin_, sock, port, as_user

    def psql(self, sql, user='postgres', vars_=None, file=None):
        """Runs sql in one psql call. Returns (rows, error): rows = list of lists of strings, error = None or the message."""
        cmd = [os.path.join(self.bin, 'psql'), '-X', '-q', '-A', '-t', '-F', '\x1f', '-v', 'ON_ERROR_STOP=1',
               '-h', self.sock, '-p', str(self.port), '-U', user, '-d', DB]
        for k, v in (vars_ or {}).items():
            cmd += ['-v', f'{k}={v}']
        cmd += ['-f', file] if file else ['-f', '-']
        r = subprocess.run(cmd, input=None if file else sql, capture_output=True, text=True)
        rows = [ln.split('\x1f') for ln in r.stdout.split('\n') if ln != '']
        if r.returncode != 0:
            return rows, (r.stderr.strip() or 'psql failed')
        return rows, None

    def as_(self, role, uid, sql):
        """sql as the API would run it: the role and the JWT claims set for one transaction, like PostgREST does.
        role: 'anon' | 'authenticated' | 'service_role'; uid: the auth user's id or None."""
        claims = json.dumps({'role': role, **({'sub': uid} if uid else {})})
        pre = f"begin;\nselect set_config('request.jwt.claims', '{claims}', true) \\gset _c\nset local role {role};\n"
        return self.psql(pre + sql.rstrip().rstrip(';') + ';\ncommit;\n')

    # ---- the API surface. The suites use only these five calls to act as a visitor, pupil or teacher, so the same
    # ---- assertions can later run against a real project: a second driver would send them to the REST API with
    # ---- that user's token instead of setting the role and the JWT claims in a transaction, as done here.
    @staticmethod
    def lit(v):
        if v is None:
            return 'null'
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, (int, float)):
            return repr(v)
        if isinstance(v, (dict, list)):
            return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
        return "'" + str(v).replace("'", "''") + "'"

    def _where(self, where):
        return (' where ' + ' and '.join(f'{k} = {self.lit(v)}' for k, v in where.items())) if where else ''

    def _json(self, who, sql):
        rows, err = self.as_(who[0], who[1], sql)
        if err:
            return None, err
        return json.loads(rows[0][0]), None

    def select(self, who, table, cols='*', where=None):
        return self._json(who, f"select coalesce(jsonb_agg(to_jsonb(t)), '[]') from (select {cols} from public.{table}{self._where(where)}) t")

    def rpc(self, who, fn, args=None):
        a = ', '.join(f'{k} => {self.lit(v)}' for k, v in (args or {}).items())
        return self._json(who, f'select to_jsonb(public.{fn}({a}))')

    def insert(self, who, table, values):
        cols, vals = ', '.join(values), ', '.join(self.lit(v) for v in values.values())
        return self._json(who, f"with x as (insert into public.{table} ({cols}) values ({vals}) returning *) select coalesce(jsonb_agg(to_jsonb(x)), '[]') from x")

    def update(self, who, table, values, where=None):
        sets = ', '.join(f'{k} = {self.lit(v)}' for k, v in values.items())
        return self._json(who, f"with x as (update public.{table} set {sets}{self._where(where)} returning *) select coalesce(jsonb_agg(to_jsonb(x)), '[]') from x")

    def delete(self, who, table, where=None):
        return self._json(who, f"with x as (delete from public.{table}{self._where(where)} returning *) select coalesce(jsonb_agg(to_jsonb(x)), '[]') from x")

    def admin(self, sql):
        rows, err = self.psql(sql)
        if err:
            raise RuntimeError(err + '\n--- in ---\n' + sql[:400])
        return rows

    def one(self, sql):
        return self.admin(sql)[0][0]


def start(verbose=False):
    bin_ = bindir()
    as_user = None
    if os.geteuid() == 0:          # PostgreSQL refuses to run as root: use the system's postgres user, or nobody
        for u in ('postgres', 'nobody'):
            try:
                pwd.getpwnam(u); as_user = u; break
            except KeyError:
                pass
        if not as_user:
            sys.exit('running as root and no postgres/nobody user to run the test database as')
    base = tempfile.mkdtemp(prefix='wi-pg-')
    os.chmod(base, 0o755)
    data, sock = os.path.join(base, 'data'), base
    if as_user:
        shutil.chown(base, as_user)
    wrap = (lambda c: ['runuser', '-u', as_user, '--'] + c) if as_user else (lambda c: c)
    port = 54000 + os.getpid() % 1000
    run = lambda c, **k: subprocess.run(wrap(c), capture_output=True, text=True, **k)
    r = run([os.path.join(bin_, 'initdb'), '-D', data, '-U', 'supabase_admin', '-A', 'trust', '-E', 'UTF8', '--locale=C.UTF-8'])
    if r.returncode:
        r = run([os.path.join(bin_, 'initdb'), '-D', data, '-U', 'supabase_admin', '-A', 'trust', '-E', 'UTF8', '--no-locale'])
    if r.returncode:
        sys.exit('initdb failed:\n' + r.stderr)
    opts = f"-c listen_addresses='' -c unix_socket_directories='{sock}' -p {port} -c fsync=off -c max_connections=120 -c timezone=UTC"
    r = run([os.path.join(bin_, 'pg_ctl'), '-D', data, '-o', opts, '-l', os.path.join(base, 'log'), '-w', 'start'])
    if r.returncode:
        sys.exit('could not start PostgreSQL:\n' + r.stderr + r.stdout)
    db = Db(bin_, sock, port, as_user)

    def stop():
        run([os.path.join(bin_, 'pg_ctl'), '-D', data, '-m', 'immediate', '-w', 'stop'])
        shutil.rmtree(base, ignore_errors=True)
    db.stop = stop
    try:
        cmd = [os.path.join(bin_, 'psql'), '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-h', sock, '-p', str(port), '-U', 'supabase_admin']
        r = subprocess.run(cmd + ['-d', 'postgres', '-c', f'create database {DB}'], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        r = subprocess.run(cmd + ['-d', DB, '-v', f'DBNAME={DB}', '-f', os.path.join(ROOT, 'tests/db/stub.sql')], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError('stub.sql: ' + r.stderr)
        for f in sorted(glob.glob(os.path.join(os.environ.get('WI_MIGRATIONS') or os.path.join(ROOT, 'supabase/migrations'), '*.sql'))):
            rows, err = db.psql(None, file=f)
            if err:
                raise RuntimeError(os.path.basename(f) + ': ' + err)
            if verbose:
                print('applied', os.path.basename(f))
    except Exception:
        stop()
        raise
    return db
