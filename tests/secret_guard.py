#!/usr/bin/env python3
"""No server key in the repo. Run by the `security` workflow next to gitleaks, and by hand: python3 tests/secret_guard.py

It replaces a grep for the *name* of Supabase's server role. That name has to appear in the migrations (grants) and
in the docs, so the check now looks for key *material* instead:
  1. a JWT whose role is anything but "anon" (the anon key is the only key that may be public);
  2. a Supabase secret key of the new format;
  3. a value assigned to a variable that must only ever be a reference (server key, pepper, database URL, JWT secret);
  4. a private key block;
  5. a database URL with a password for a host that is not this machine.
`--self-test` proves each rule fires and that the legitimate forms pass."""
import base64, json, re, subprocess, sys

JWT = re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')
NEW_SECRET = re.compile(r'sb_secret_[A-Za-z0-9_-]{10,}')
ASSIGN = re.compile(r'(?i)\b(\w*SERVICE_ROLE\w*|SUPABASE_SERVICE\w*|PUPIL_PEPPER\w*|SUPABASE_DB_URL|\w*JWT_SECRET)\b["\']?\s*[:=]\s*["\']?([A-Za-z0-9+/_=-]{20,})')
PRIVATE_KEY = re.compile(r'BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY')
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
           'PUPIL_PEPPER: "' + 'Zm9v' * 8 + '"', '-----BEGIN ' + 'PRIVATE KEY-----', 'postgresql://postgres:' + 'hunter2hunter2' + '@db.abcdefgh.supabase.co:5432/postgres']
    good = [tok('anon'), f'grant all on all tables in schema public to {role};', 'SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}',
            "key = os.environ['SUPABASE_SERVICE_ROLE_KEY']", 'const pepper = Deno.env.get("PUPIL_PEPPER")', 'sb_publishable_A1b2C3d4E5f6G7h8',
            'postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.co/postgres', 'postgres://postgres:postgres@localhost:5432/wi_test',
            'PUPIL_PEPPER=$(openssl rand -base64 32)']
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
    files = subprocess.run(['git', 'ls-files', '-z'], capture_output=True, text=True, check=True).stdout.split('\0')
    bad = n = 0
    for f in files:
        if not f or f.startswith('vendor/'):
            continue
        try:
            text = open(f, encoding='utf-8').read()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue          # binary assets
        n += 1
        for what in scan(text):
            bad += 1
            print(f'SECRET? {f}: {what}')
    print(f'secret_guard: {n} text files scanned, {bad} findings')
    sys.exit(1 if bad or not self_test() else 0)


if __name__ == '__main__':
    main()
