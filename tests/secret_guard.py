#!/usr/bin/env python3
# suite:   # picked up by tests/all.py
"""No server key in the repo. Run by the `security` workflow next to gitleaks, and by hand: python3 tests/secret_guard.py

It replaces a grep for the *name* of Supabase's server role. That name has to appear in the migrations (grants) and
in the docs, so the check now looks for key *material* instead:
  1. a JWT whose role is anything but "anon" (the anon key is the only key that may be public);
  2. a Supabase secret key of the new format;
  3. a value assigned to a variable that must only ever be a reference (server key, pepper, database URL, JWT secret),
     also when the value is folded onto the next line (YAML `>` or `|`);
  4. a private key block of any kind (RSA, EC, OpenSSH, PKCS8, encrypted, PGP: the backup key is a PGP key);
  5. a database URL with a password for a host that is not this machine;
  6. a database password assigned to its usual variable names;
  7. a bare `password = "…"` line, as in a toml `[db]` section;
  8. a libpq connection string (`host=… password=…`, also with spaces around =) with a password that is not a reference;
  9. a `password:` key with a value in YAML or JSON;
 10. in the tests only: a made-up key shaped like a vendor's (`sb_publishable_…`, `sk_live_`/`rk_live_…`, `ghp_`/`gho_`/
     `ghs_…`, `github_pat_…`, `AKIA…`, `AIza…`, `xoxb-…`), also glued to a prefix, and any JWT whatever its role. A fake
     key in a test is written so that it cannot be taken for a real one (`public-key-for-tests-0123456789`): the repo's
     other scanner (gitleaks) cannot tell the difference and turns every branch red (docs/LESSONS.md, entry 13).
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
TOML_PW = re.compile(r'(?im)^[ \t]*["\']?(\w*password|pass|pwd)["\']?[ \t]*=[ \t]*["\']([^"\'$\n]{6,})["\']')
DSN_PW = re.compile(r'(?i)\b(?:host|hostaddr|dbname|user)[ \t]*=[ \t]*\S+[^\n]*?\bpassword[ \t]*=[ \t]*["\']?([^\s"\'$<\[{]{4,})|\bpassword[ \t]*=[ \t]*["\']?([^\s"\'$<\[{]{4,})[^\n]*?\b(?:host|hostaddr|dbname)[ \t]*=[ \t]*\S')
# YAML or JSON: `password: hunter2`, `"password": "hunter2",` (the whole rest of the line is the value; review N6)
KV_PW = re.compile(r'(?im)^[ \t{-]*["\']?(\w*password|passwd|pwd)["\']?[ \t]*:[ \t]*["\']?([^\s"\'$<\[{#(),;]{6,})["\']?[ \t]*,?[ \t]*$')
# no leading \b: a key glued to a prefix (xsb_publishable_…, TEST_sb_publishable_…) is still a key (review of #88)
VENDOR_SHAPED = re.compile(r'sb_publishable_[A-Za-z0-9_-]{10,}|[sr]k_(?:live|test)_[A-Za-z0-9]{10,}|gh[opsur]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'
                           r'|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|xox[abprs]-[A-Za-z0-9-]{10,}')
NOT_A_VALUE = {'string', 'str', 'null', 'none', 'true', 'false', 'required', 'optional', 'secret', 'redacted'}
LOCAL = {'localhost', '127.0.0.1', '::1', 'db', 'host'}


def jwt_role(tok):
    try:
        part = tok.split('.')[1]
        return json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))).get('role', '?')
    except Exception:
        return '?'


def scan(text, test=False):
    """Returns the list of findings (rule names) in one file's text. Never returns the secret itself. `test`: the file is
    a test, where a key is always made up and must not look like a vendor's."""
    out = []
    if test and VENDOR_SHAPED.search(text):
        out.append("a made-up key shaped like a vendor's (write it so it cannot pass for one)")
    if test and JWT.search(text):
        out.append('a JWT in a test, whatever its role (build it from pieces at run time)')
    for m in JWT.finditer(text):
        if jwt_role(m.group(0)) != 'anon':
            out.append('a JWT that is not the anon key')
    if NEW_SECRET.search(text):
        out.append('a Supabase secret key')
    for m in ASSIGN.finditer(text):
        out.append(f'a value assigned to {m.group(1)} (must be a reference to a secret, never the value)')
    for m in DBPW.finditer(text):
        out.append(f'a database password assigned to {m.group(1)}')
    for m in TOML_PW.finditer(text):
        out.append('a password written in a settings file')
    for m in KV_PW.finditer(text):
        if m.group(2).lower() not in NOT_A_VALUE:
            out.append('a password written as a YAML or JSON value')
    if DSN_PW.search(text):
        out.append('a connection string with a password')
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
           '-----BEGIN OPENSSH ' + 'PRIVATE KEY-----', 'BACKUP_EXPORT_TOKEN=' + 't' * 32,
           '[db]\nport = 54322\n' + 'pass' + 'word = "hunter2hunter2"', 'host=db.abcdefgh.supabase.co port=5432 user=postgres pass' + 'word=hunter2x dbname=postgres',
           "psql 'pass" + "word=hunter2x host=db.example.com'", 'db:\n  pass' + 'word: hunter2hunter2\n', '{"pass' + 'word": "hunter2hunter2",\n "user": "x"}',
           'host = db.example.com port = 5432 pass' + 'word = hunter2x']
    good = [tok('anon'), f'grant all on all tables in schema public to {role};', 'SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}',
            "key = os.environ['SUPABASE_SERVICE_ROLE_KEY']", 'const pepper = Deno.env.get("PUPIL_PEPPER")', 'sb_' + 'publishable_A1b2C3d4E5f6G7h8',
            'postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.co/postgres', 'postgres://postgres:postgres@localhost:5432/wi_test',
            'PUPIL_PEPPER=$(openssl rand -base64 32)', 'const pepper = Uint8Array.from(atob(need("PUPIL_PEPPER")), (c) => c.charCodeAt(0));',
            'PGPASSWORD=$DB_PASS psql', 'PBKDF2-HMAC-SHA256(password = inner, salt = 16 random bytes)', '-----BEGIN PGP PUBLIC KEY BLOCK-----',
            'env:\n  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.X }}\n  OTHER: value', '[db]\npassword = env("SUPABASE_DB_PASSWORD")',
            'host=/tmp/sock port=5432 password=$PGPASSWORD', "r = {'password': secrets.token_urlsafe(24)}", 'password = ""',
            'password: ${{ secrets.DB_PASSWORD }}', '  password: string;', 'interface X {\n  password: string\n}', '"password": "$DB_PASSWORD",']
    # rule 10: in a test, a vendor-shaped fake fails; the same text outside the tests (the publishable key is public by
    # design, in config.js and the docs) passes, and so does a fake written as the tests write it
    fake = ["KEY = '" + 'sb_' + "publishable_test_0123456789abcdef'", 'sk_' + 'live_0123456789abcd', 'rk_' + 'live_0123456789abcd', 'gh' + 'p_' + 'a' * 36,
            'gh' + 'o_' + 'a' * 36, 'gh' + 's_' + 'a' * 36, 'github' + '_pat_' + '11ABCDEFG0' * 3, 'AK' + 'IA' + 'ABCDEFGHIJKLMNOP', 'AI' + 'za' + 'B' * 35,
            'xo' + 'xb-' + '1234567890-abcdef', tok('anon'),                                          # an anon JWT too, in a test
            'x' + 'sb_' + 'publishable_test_0123456789abcdef', 'TEST_' + 'sb_' + 'publishable_test_0123456789abcdef']   # glued to a prefix
    ok10 = all(scan(x, test=True) for x in fake) and not any(scan(x) for x in fake[:1]) and not scan("KEY = 'public-key-for-tests-0123456789'", test=True)
    for x in fake:
        if not scan(x, test=True): print('self-test: rule 10 misses', x[:12] + '…')
    if not ok10: print('self-test: rule 10 (vendor-shaped fakes in tests) does not hold')
    bad = bad + fake
    ok = ok10 and all(scan(x) or scan(x, test=True) for x in bad) and not any(scan(x) for x in good)
    for x in bad:
        if not (scan(x) or scan(x, test=True)): print('self-test: not caught:', x[:30] + '…')
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
        for what in scan(text, test=f.startswith('tests/') or '/tests/' in f):
            bad += 1
            print(f'SECRET? {f}: {what}')
    print(f'secret_guard: {n} files scanned, {bad} findings')
    sys.exit(1 if bad or not self_test() else 0)


if __name__ == '__main__':
    main()
