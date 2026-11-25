// The teacher's sign-in (js/teacher_auth.js, teacher.html), without a browser:  node tests/teacher_check.mjs
// suite:   // picked up by tests/all.py
// A stand-in for Supabase Auth (GoTrue) issues codes bound to a PKCE challenge and a redirect, once, for 5 minutes.
// Checked: the whole sign-in; a code this tab did not start; another tab's or an attacker's code (verifier mismatch);
// a replayed code; an expired session; a second teacher on the same browser; the back button after sign-out and after
// leaving; open-redirect attempts; 30 minutes idle; a late answer after sign-out; nothing of the session in storage;
// and the page inert without a project. All names and addresses are made up.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const { teacherAuth, projectOf } = await import(pathToFileURL(path.join(ROOT, 'js/teacher_auth.js')).href);
let pass = 0, fail = 0;
const check = (label, ok, detail = '') => { ok ? pass++ : fail++; console.log((ok ? 'PASS ' : 'FAIL ') + label + (ok ? '' : '   <- ' + String(detail).slice(0, 300))); };
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want), `got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);

const SB = 'https://abcdefghijklmnop.supabase.co', KEY = 'sb_publishable_test_0123456789abcdef', PAGE = 'https://example.github.io/english-trainer/teacher.html';
const b64url = b => Buffer.from(b).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

/** Supabase Auth, as far as this page uses it */
function gotrue(clock) {
  const codes = new Map(), sessions = new Map(), log = [];
  let n = 0;
  const g = {
    log, codes, sessions, delay: null, refuseRefresh: false,
    /** the browser at Google and back: what /authorize would redirect to, for the teacher `email` */
    authorize(u, email) {
      const q = new URL(u).searchParams;
      const code = 'code-' + (++n);
      codes.set(code, { challenge: q.get('code_challenge'), method: q.get('code_challenge_method'), redirect: q.get('redirect_to'), email, at: clock.now, used: false });
      return q.get('redirect_to') + (q.get('redirect_to').includes('?') ? '&' : '?') + 'code=' + code;
    },
    async fetch(u, init = {}) {
      const url = new URL(u), body = init.body ? JSON.parse(init.body) : null, auth = (init.headers || {}).authorization || '';
      log.push({ path: url.pathname + url.search, body, auth, apikey: (init.headers || {}).apikey, keepalive: !!init.keepalive, method: init.method, prefer: (init.headers || {}).prefer });
      if (g.delay) await g.delay;
      if (g.down) throw new TypeError('Failed to fetch');
      const out = (status, j) => ({ status, json: async () => j });
      if (url.pathname === '/auth/v1/token' && url.searchParams.get('grant_type') === 'pkce') {
        const c = codes.get(body.auth_code);
        if (!c || c.used || clock.now - c.at > 300000) return out(400, { error: 'invalid_grant' });
        c.used = true;                                   // a code is good once
        const ok = c.method === 's256' && b64url(crypto.createHash('sha256').update(body.code_verifier).digest()) === c.challenge;
        if (!ok) return out(400, { error: 'invalid_grant', error_description: 'code challenge does not match previously saved code verifier' });
        const s = { access_token: 'acc-' + (++n), refresh_token: 'ref-' + n, expires_in: 3600, user: { id: 'u-' + c.email, email: c.email } };
        sessions.set(s.refresh_token, { ...s, alive: true }); return out(200, s);
      }
      if (url.pathname === '/auth/v1/token' && url.searchParams.get('grant_type') === 'refresh_token') {
        const s = sessions.get(body.refresh_token);
        if (!s || !s.alive || g.refuseRefresh) return out(400, { error: 'invalid_grant' });
        s.alive = false;
        const t = { access_token: 'acc-' + (++n), refresh_token: 'ref-' + n, expires_in: 3600, user: s.user };
        sessions.set(t.refresh_token, { ...t, alive: true }); return out(200, t);
      }
      if (url.pathname === '/auth/v1/logout') {
        for (const s of sessions.values()) if ('Bearer ' + s.access_token === auth) s.alive = false;
        return out(204, null);
      }
      if (url.pathname === '/functions/v1/teacher-reset') {
        const s = [...sessions.values()].find(x => 'Bearer ' + x.access_token === auth && x.alive);
        if (!s) return out(401, { message: 'Invalid JWT' });
        return out(200, body.action === 'reset' ? { ok: true, otc: '123456', expires_at: '2027-01-12T08:00:00Z', name: 'Noa' } : { ok: true });
      }
      if (url.pathname.startsWith('/rest/v1/')) {
        const s = [...sessions.values()].find(x => 'Bearer ' + x.access_token === auth && x.alive);
        if (!s) return out(401, { message: 'JWT expired' });
        if (init.method === 'DELETE') return out(200, []);
        if (init.method === 'POST') return out(201, null);
        return out(200, (g.rows[url.pathname.slice(9)] || {})[s.user.email] || []);
      }
      return out(404, null);
    },
    rows: {},
  };
  return g;
}
/** a tab: its address, its history, its sessionStorage, a clock with timers */
function tab(shared) {
  const clock = shared ? shared.clock : { now: Date.UTC(2027, 0, 11, 8, 0, 0), timers: [], seq: 0 };
  const store = new Map(), visits = [];
  const t = {
    clock, store, visits, outs: [],
    location: { origin: 'https://example.github.io', pathname: '/english-trainer/teacher.html', search: '', assign(u) { visits.push(u); } },
    history: { replaceState(_, __, u) { t.replaced = u; const x = new URL(u); t.location.search = x.search; } },
    storage: { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) },
    advance(ms) { clock.now += ms; for (const x of clock.timers.filter(x => x.at <= clock.now).sort((a, b) => a.at - b.at)) { clock.timers = clock.timers.filter(y => y !== x); x.f(); } },
  };
  t.server = shared ? shared.server : gotrue(clock);
  t.auth = teacherAuth({
    url: SB, key: KEY, fetch: t.server.fetch, crypto: globalThis.crypto, store: t.storage, location: t.location, history: t.history,
    now: () => clock.now, setTimeout: (f, ms) => { const id = ++clock.seq; clock.timers.push({ id, at: clock.now + ms, f }); return id; },
    clearTimeout: id => { clock.timers = clock.timers.filter(x => x.id !== id); }, onOut: why => t.outs.push(why),
  });
  /** the full trip: the button, Google (as `email`), back to the page */
  t.signIn = async (email = 'teacher.one@example.org') => {
    await t.auth.begin();
    const back = t.server.authorize(t.visits[t.visits.length - 1], email);
    t.location.search = new URL(back).search;
    return t.auth.finish();
  };
  return t;
}
const tick = () => new Promise(r => setTimeout(r, 5));

// ---- 1. the whole sign-in
{
  const t = tab();
  const r = await t.signIn();
  const go = new URL(t.visits[0]), q = go.searchParams;
  eq('sign-in goes to Supabase Auth for Google, with PKCE (S256) and this page as the only redirect', [go.origin + go.pathname, q.get('provider'), q.get('code_challenge_method'), q.get('redirect_to'), (q.get('code_challenge') || '').length], [SB + '/auth/v1/authorize', 'google', 's256', PAGE, 43]);
  eq('back from Google: signed in as the teacher', [r.state, r.user && r.user.email], ['in', 'teacher.one@example.org']);
  eq('the code is exchanged with the verifier, the publishable key only (no bearer)', [t.server.log[0].path, !!t.server.log[0].body.code_verifier, t.server.log[0].auth, t.server.log[0].apikey], ['/auth/v1/token?grant_type=pkce', true, '', KEY]);
  eq('the code leaves the address bar and the history at once', [t.replaced, t.location.search], [PAGE, '']);
  eq('nothing of the session is stored: the verifier is gone, no token in sessionStorage', [...t.store.keys()], []);
  check('the session is usable', (await t.auth.token()) === 'acc-2');
}
// ---- 2. a code this tab did not start (a link, another tab): refused, nothing sent
{
  const t = tab();
  t.location.search = '?code=code-from-a-link';
  const r = await t.auth.finish();
  eq('a code with no sign-in started in this tab is refused without a request (the state check)', [r.state, r.e, t.server.log.length], ['out', 'flow', 0]);
  const u = tab();
  await u.auth.begin();
  u.clock.now += 11 * 60000;
  u.location.search = '?' + new URL(u.server.authorize(u.visits[0], 'teacher.one@example.org')).searchParams;
  const r2 = await u.auth.finish();
  eq('a sign-in started more than 10 minutes ago is refused too', [r2.state, r2.e, u.server.log.length], ['out', 'flow', 0]);
}
// ---- 3. verifier mismatch: an attacker's own code (or another tab's) fed to this tab
{
  const victim = tab(), attacker = tab(victim);
  await attacker.auth.begin();
  const evil = attacker.server.authorize(attacker.visits[0], 'attacker@example.org');   // the attacker's code, for the attacker's challenge
  await victim.auth.begin();                                                             // the victim started a sign-in of her own
  victim.location.search = new URL(evil).search;                                         // and is sent back with the attacker's code
  const r = await victim.auth.finish();
  eq('a code made for another verifier is refused by the server: nobody is signed in (no login CSRF)', [r.state, r.e, victim.auth.user()], ['out', 'code', null]);
}
// ---- 4. a replayed code
{
  const t = tab();
  const r1 = await t.signIn();
  const used = [...t.server.codes.keys()][0];
  t.auth.left();                                               // the page is reloaded with the old address (or the code is replayed)
  t.location.search = '?code=' + used;
  const r2 = await t.auth.finish();
  eq('a replayed code is refused: no verifier any more, and the server would refuse it too', [r1.state, r2.state, r2.e, t.server.log.filter(l => l.path.includes('pkce')).length], ['in', 'out', 'flow', 1]);
  const u = tab(); await u.auth.begin();
  const back = u.server.authorize(u.visits[0], 'teacher.one@example.org');
  u.location.search = new URL(back).search;
  const v = JSON.parse(u.store.get('wi-teacher-flow'));
  await u.server.fetch(SB + '/auth/v1/token?grant_type=pkce', { method: 'POST', body: JSON.stringify({ auth_code: new URL(back).searchParams.get('code'), code_verifier: v.verifier }) });   // the code is used once elsewhere
  const r3 = await u.auth.finish();
  eq('a code already used once (by anyone) is refused', [r3.state, r3.e], ['out', 'code']);
}
// ---- 5. an expired session
{
  const t = tab();
  await t.signIn();
  t.auth.touch(); t.clock.now += 59 * 60000; t.auth.touch();
  const before = t.server.log.length, a0 = [...t.server.sessions.values()][0].access_token;
  const a = await t.auth.token();
  eq('an access token about to end is refreshed (the refresh token turns over)', [/^acc-\d+$/.test(a) && a !== a0, t.server.log.length - before, t.server.log.at(-1).path], [true, 1, '/auth/v1/token?grant_type=refresh_token']);
  t.server.refuseRefresh = true; t.clock.now += 59 * 60000; t.auth.touch();
  const b = await t.auth.token();
  eq('a session the server no longer refreshes: signed out, and the page is told why', [b, t.auth.signedIn(), t.outs], [null, false, ['expired']]);
}
// ---- 6. a second teacher on the same browser
{
  const t = tab();
  await t.signIn('teacher.one@example.org');
  const first = 'Bearer ' + (await t.auth.token());
  const r = await t.signIn('teacher.two@example.org');           // without signing out first
  eq('a second teacher in the same tab: the first one\'s session is revoked before the second begins', [r.user.email, t.server.log.some(l => l.path.startsWith('/auth/v1/logout') && l.auth === first)], ['teacher.two@example.org', true]);
  const other = tab(t);                                          // another tab of the same browser: its own page, its own memory
  eq('another tab of the same browser does not see her session', [other.auth.signedIn(), other.auth.user()], [false, null]);
}
// ---- 7. the back button after sign-out, and after leaving the page
{
  const t = tab();
  await t.signIn();
  const a = 'Bearer ' + (await t.auth.token());
  await t.auth.signOut('out');
  eq('sign-out: no session here, revoked on the server', [t.auth.signedIn(), t.server.log.at(-1).path, t.server.log.at(-1).auth], [false, '/auth/v1/logout?scope=local', a]);
  eq('the back button (the page restored from the cache) finds nobody signed in', [t.auth.user(), await t.auth.token()], [null, null]);
  const u = tab();
  await u.signIn();
  u.auth.left();                                                  // a click to the game, a new address, closing the tab
  await tick();
  eq('leaving the page ends the session (back again, nobody is signed in) and revokes it, with keepalive (the page is going)', [u.auth.signedIn(), u.server.log.at(-1).path, u.server.log.at(-1).keepalive, u.outs], [false, '/auth/v1/logout?scope=local', true, ['left']]);
}
// ---- 8. open redirect attempts
{
  for (const q of ['?redirect_to=https://evil.example/x', '?next=//evil.example', '?redirect_to=' + encodeURIComponent(SB + '/auth/v1/authorize?provider=google&redirect_to=https://evil.example')]) {
    const t = tab();
    t.location.search = q;
    const f = await t.auth.finish();                                 // the page opened with it: nothing happens
    await t.auth.begin();
    eq(`open redirect: the page opened with ${q.slice(0, 30)}… sends nobody anywhere, and the sign-in still returns to this page only`, [f.state, t.server.log.length, new URL(t.visits[0]).searchParams.get('redirect_to')], ['out', 0, PAGE]);
  }
  const t = tab();
  t.location.search = '?error=access_denied&error_description=' + encodeURIComponent('<script>x</script>');
  const r = await t.auth.finish();
  eq('an error from Google is a plain "cancelled", its text is never shown', [r.state, r.e], ['out', 'denied']);
}
// ---- 9. 30 minutes idle
{
  const t = tab();
  await t.signIn();
  t.advance(29 * 60000); t.auth.touch(); t.advance(29 * 60000);
  eq('a tap within 30 minutes keeps her signed in', t.auth.signedIn(), true);
  t.advance(60001); await tick();
  eq('30 minutes without a tap or a key: signed out and revoked, and the page is told', [t.auth.signedIn(), t.server.log.at(-1).path, t.outs], [false, '/auth/v1/logout?scope=local', ['idle']]);
  const u = tab();
  await u.signIn();
  u.clock.now += 31 * 60000;                                      // the tab slept in the background: its timer did not run
  await u.auth.wake();
  eq('a page that comes back after more than 30 minutes asleep signs out at once', [u.auth.signedIn(), u.outs], [false, ['idle']]);
}
// ---- 10. a late answer after sign-out, after leaving
{
  const t = tab();
  await t.auth.begin();
  t.location.search = new URL(t.server.authorize(t.visits[0], 'teacher.one@example.org')).search;
  let release; t.server.delay = new Promise(r => { release = r; });
  const p = t.auth.finish();
  await tick();
  t.auth.left(); await t.auth.signOut('out');                    // she gave up and left while Google's answer was on its way
  t.server.delay = null; release();
  const r = await p;
  eq('a late answer after sign-out keeps no session', [r.state, r.e, t.auth.signedIn()], ['out', 'stale', false]);
  const u = tab();
  await u.signIn();
  u.clock.now += 59 * 60000; u.auth.touch();
  let rel2; u.server.delay = new Promise(r => { rel2 = r; });
  const tp = u.auth.token();                                     // the refresh is on its way, slowly
  await tick();
  u.server.delay = null;
  await u.auth.signOut('out');                                   // she signs out meanwhile
  rel2();
  eq('a late refresh after sign-out is not kept', [await tp, u.auth.signedIn()], [null, false]);
}
// ---- 12. step 2: her own views, read with her token only, and never after she is gone
{
  const t = tab();
  t.server.rows.teacher_view = { 'teacher.one@example.org': [{ display_name: 'Noa', points: 30 }] };
  await t.signIn();
  const r = await t.auth.read('/rest/v1/teacher_view?select=display_name,points');
  eq('read: her rows, with her token', [r, t.server.log.at(-1).auth.startsWith('Bearer acc-'), t.server.log.at(-1).path], [{ rows: [{ display_name: 'Noa', points: 30 }] }, true, '/rest/v1/teacher_view?select=display_name,points']);
  let release; t.server.delay = new Promise(x => { release = x; });
  const late = t.auth.read('/rest/v1/teacher_view');
  await tick();
  t.server.delay = null; await t.auth.signOut('out'); release();
  eq('a read whose answer comes after sign-out gives nothing to show', await late, null);
  const u = tab(t);
  await u.signIn('teacher.two@example.org');
  for (const s of u.server.sessions.values()) s.alive = false;      // the server ended her session (revoked elsewhere, expired)
  const r2 = await u.auth.read('/rest/v1/teacher_view');
  eq('a read refused by the server (401): signed out, nothing to show', [r2, u.auth.signedIn(), u.outs], [null, false, ['expired']]);
  const v = tab(t);
  eq('no read without a session (no request at all)', [await v.auth.read('/rest/v1/teacher_view'), v.server.log.length], [null, u.server.log.length]);
}
// ---- 13. step 3: her actions, with her token only, and a one-time code never handed over after she is gone
{
  const t = tab();
  await t.signIn();
  const r = await t.auth.write('/functions/v1/teacher-reset', { action: 'reset', pupil_id: 'p1' });
  const last = t.server.log.at(-1);
  eq('write: POST with her token, the body as given', [r.status, r.j.otc, last.method, last.auth.startsWith('Bearer acc-'), last.apikey, last.body], [200, '123456', 'POST', true, KEY, { action: 'reset', pupil_id: 'p1' }]);
  const d = await t.auth.write('/rest/v1/roster?class_id=eq.c1&name_key=eq.noa', undefined, 'DELETE', 'return=representation');
  eq('write: DELETE with no body and the Prefer asked for', [d.status, t.server.log.at(-1).method, t.server.log.at(-1).body, t.server.log.at(-1).prefer], [200, 'DELETE', null, 'return=representation']);
  let release; t.server.delay = new Promise(x => { release = x; });
  const late = t.auth.write('/functions/v1/teacher-reset', { action: 'reset', pupil_id: 'p1' });
  await tick();
  t.server.delay = null; await t.auth.signOut('out'); release();
  eq('a new code that comes back after sign-out is never handed to the page', await late, null);
  await t.signIn();
  let rel2; t.server.delay = new Promise(x => { rel2 = x; });
  const late2 = t.auth.write('/functions/v1/teacher-reset', { action: 'reset', pupil_id: 'p1' });
  await tick();
  t.server.delay = null; t.auth.left(); rel2();
  eq('nor after she left the page', await late2, null);
  await t.signIn();
  t.server.down = true;
  eq('no network: told as such (status 0), still signed in', [await t.auth.write('/functions/v1/teacher-reset', { action: 'unlock', pupil_id: 'p1' }), t.auth.signedIn()], [{ status: 0, j: null }, true]);
  t.server.down = false;
  for (const s of t.server.sessions.values()) s.alive = false;
  t.outs.length = 0;
  eq('an action refused by the server (401): signed out, nothing returned', [await t.auth.write('/functions/v1/teacher-reset', { action: 'unlock', pupil_id: 'p1' }), t.auth.signedIn(), t.outs], [null, false, ['expired']]);
  const n = t.server.log.length;
  eq('no action without a session (no request at all)', [await t.auth.write('/rest/v1/roster', { class_id: 'c1' }), t.server.log.length], [null, n]);
  const src = fs.readFileSync(path.join(ROOT, 'js/teacher.js'), 'utf8');
  check('teacher.js: the code never goes to the console, storage or the address bar', !/console\./.test(src) && !/(local|session)Storage\.setItem\([^)]*otc/i.test(src) && !/(location|history)[^;]*otc/i.test(src));
  check('teacher.js: every action waits for her "yes" and checks the epoch after each await', (src.match(/act\(`/g) || []).length === 5 && (src.match(/if\(!r\|\|e!==epoch\)return;/g) || []).length === 5);
}
// ---- 11. the page and the site
{
  eq('the page is inert without a project in config.js (or with a wrong one)', [projectOf(undefined), projectOf({}), projectOf({ url: 'https://evil.example', key: KEY }), projectOf({ url: SB, key: 'short' }), !!projectOf({ url: SB, key: KEY })], [null, null, null, null, true]);
  const html = fs.readFileSync(path.join(ROOT, 'teacher.html'), 'utf8');
  const csp = (html.match(/<meta http-equiv="Content-Security-Policy" content="([^"]+)">/) || [])[1] || '';
  check('teacher.html: its own strict policy (no inline script or style, requests to this site only until a project is named)', /script-src 'self';/.test(csp) && /style-src 'self';/.test(csp) && /connect-src 'self';/.test(csp) && !/unsafe/.test(csp) && /form-action 'none'/.test(csp), csp);
  check('teacher.html: no referrer leaves the page (the code is never in a Referer)', /<meta name="referrer" content="no-referrer">/.test(html));
  const pupil = fs.readdirSync(ROOT).filter(f => f.endsWith('.html') && f !== 'teacher.html').filter(f => /teacher_auth|teacher\.js/.test(fs.readFileSync(path.join(ROOT, f), 'utf8')));
  const imports = fs.readdirSync(path.join(ROOT, 'js')).filter(f => f.endsWith('.js') && f !== 'teacher.js' && /teacher_auth/.test(fs.readFileSync(path.join(ROOT, 'js', f), 'utf8')));
  eq('no pupil page and no other script loads the teacher\'s sign-in', [pupil, imports], [[], []]);
  const src = fs.readFileSync(path.join(ROOT, 'js/teacher_auth.js'), 'utf8');
  check('the session is never written to storage: the only stored key is the PKCE flow', (src.match(/store\.setItem\(/g) || []).length === 1 && /store\.setItem\(FLOW,/.test(src) && !/localStorage\s*[.[]/.test(src), src.match(/store\.setItem\([^)]*\)/g));
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
