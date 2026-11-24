#!/usr/bin/env python3
"""No server key in the repo. Run by the `security` workflow next to gitleaks, and by hand: python3 tests/secret_guard.py

It replaces a grep for the *name* of Supabase's server role. That name has to appear in the migrations (grants) and
in the docs, so the check now looks for key *material* instead:
  1. a JWT whose role is anything but "anon" (the anon key is the only key that may be public);
  2. a Supabase secret key of the new format;
  3. a value assigned to a variable that must only ever be a reference (server key, pepper, database URL, JWT secret),
     also when the value is folded onto the next line (YAML `>` or `|`);
  4. a private key block of any kind (RSA, EC, OpenSSH, PKCS8, encrypted, PGP: the backup key is a PGP key);
  5. a database URL with a password for a host that is not this machine;
  6. a database password assigned to its usual variable names.
A file that is not UTF-8 is read as latin-1, never skipped. What it cannot see: a key that was base64-encoded,
compressed or split into pieces; gitleaks runs next to it.
`--self-test` proves each rule fires and that the legitimate forms pass."""
import base64, json, os, re, subprocess, sys

JWT = re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')
NEW_SECRET = re.compile(r'sb_secret_[A-Za-z0-9_-]{10,}')
ASSIGN = re.compile(r'(?i)\b(\w*SERVICE_ROLE\w*|SUPABASE_SERVICE\w*|\w*SERVICE_KEY\w*|\w*SECRET_KEY\w*|\w*PEPPER\w*|SUPABASE_DB_URL|\w*JWT_SECRET\w*|\w*EXPORT_TOKEN\w*)\b["\']?[ \t]*[:=][ \t]*(?:[>|][+-]?[ \t]*)?\r?\n?[ \t]*["\']?([A-Za-z0-9+/_=-]{20,})')
DBPW = re.compile(r'(?i)\b(PGPASSWORD|POSTGRES_PASSWORD|\w*DB_PASSWORD|db_pass\w*)\b["\']?[ \t]*[:=][ \t]*["\']?([^\s"\'$<\[{(]{6,})')
PRIVATE_KEY = re.compile(r'BEGIN [A-Z0-9 ]*PRIVATE KEY')
DB_URL = re.compile(r'postgres(?:ql)?://[^\s:/@\'"<\[$]+:([^\s@\'"]{4,})@([^\s:/\'"]+)')
LOCAL = {'localhost', '127.0.0.1', '::1', 'db', 'host'}


def jwt_role(tok):
    try:
        part = tok.split('.')[1]
        return json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))).get('role', '?')
    except Exception:
        return '?'


def scan(text):
    """Returns the list of findings (rule names) in one file's text. Never returns the secret itself."""
    out = []
    for m in JWT.finditer(text):
        if jwt_role(m.group(0)) != 'anon':
            out.append('a JWT that is not the anon key')
    if NEW_SECRET.search(text):
        out.append('a Supabase secret key')
    for m in ASSIGN.finditer(text):
        out.append(f'a value assigned to {m.group(1)} (must be a reference to a secret, never the value)')
    for m in DBPW.finditer(text):
        out.append(f'a database password assigned to {m.group(1)}')
    if PRIVATE_KEY.search(text):
        out.append('a private key')
    for m in DB_URL.finditer(text):
        if m.group(2).lower() not in LOCAL and not re.match(r'^[\[<$]|^(password|pass|xxx+|\*+)$', m.group(1), re.I):
            out.append('a database URL with a password')
    return out


def self_test():
    b = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip('=')
    tok = lambda role: '.'.join([b({'alg': 'HS256', 'typ': 'JWT'}), b({'iss': 'supabase', 'role': role, 'iat': 1700000000}), 'x' * 43])
    role = 'service' + '_role'            # assembled here so this file never holds a string the guard would flag
    bad = [tok(role), tok('authenticated'), 'sb_' + 'secret_' + 'A1b2C3d4E5f6G7h8', 'SUPABASE_SERVICE_ROLE_KEY=' + 'q' * 40,
           'PUPIL_PEPPER: "' + 'Zm9v' * 8 + '"', '-----BEGIN ' + 'PRIVATE KEY-----', 'postgresql://postgres:' + 'hunter2hunter2' + '@db.abcdefgh.supabase.co:5432/postgres',
           'SUPABASE_SERVICE_ROLE_KEY: >-\n    ' + 'q' * 40, 'service_role_key:\n  ' + 'q' * 40, 'const PEPPER = "' + 'Zm9v' * 8 + '"', 'SERVICE_KEY=' + 'k' * 30,
           'PG' + 'PASSWORD=hunter2', 'db_' + 'password = "s3cretpw"', '-----BEGIN PGP ' + 'PRIVATE KEY BLOCK-----', '-----BEGIN ENCRYPTED ' + 'PRIVATE KEY-----',
           '-----BEGIN OPENSSH ' + 'PRIVATE KEY-----', 'BACKUP_EXPORT_TOKEN=' + 't' * 32]
    good = [tok('anon'), f'grant all on all tables in schema public to {role};', 'SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}',
            "key = os.environ['SUPABASE_SERVICE_ROLE_KEY']", 'const pepper = Deno.env.get("PUPIL_PEPPER")', 'sb_publishable_A1b2C3d4E5f6G7h8',
            'postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.co/postgres', 'postgres://postgres:postgres@localhost:5432/wi_test',
            'PUPIL_PEPPER=$(openssl rand -base64 32)', 'const pepper = Uint8Array.from(atob(need("PUPIL_PEPPER")), (c) => c.charCodeAt(0));',
            'PGPASSWORD=$DB_PASS psql', 'PBKDF2-HMAC-SHA256(password = inner, salt = 16 random bytes)', '-----BEGIN PGP PUBLIC KEY BLOCK-----',
            'env:\n  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.X }}\n  OTHER: value']
    ok = all(scan(x) for x in bad) and not any(scan(x) for x in good)
    for x in bad:
        if not scan(x): print('self-test: not caught:', x[:30] + '…')
    for x in good:
        if scan(x): print('self-test: false alarm:', x[:60], scan(x))
    print('secret_guard self-test:', f'{len(bad)} bad caught, {len(good)} good passed' if ok else 'FAILED')
    return ok


def main():
    if '--self-test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))      # the whole repository, wherever it is run from
    files = subprocess.run(['git', 'ls-files', '-z'], capture_output=True, text=True, check=True).stdout.split('\0')
    bad = n = 0
    for f in files:
        if not f or f.startswith('vendor/'):
            continue
        try:
            raw = open(f, 'rb').read()
        except (FileNotFoundError, IsADirectoryError):
            continue
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('latin-1')      # never skipped: a key is ASCII whatever the rest of the file is
        n += 1
        for what in scan(text):
            bad += 1
            print(f'SECRET? {f}: {what}')
    print(f'secret_guard: {n} files scanned, {bad} findings')
    sys.exit(1 if bad or not self_test() else 0)


if __name__ == '__main__':
    main()
