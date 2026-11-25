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

const SB = 'https://abcdefghijklmnop.supabase.co', KEY = 'public-key-for-tests-0123456789', PAGE = 'https://example.github.io/english-trainer/teacher.html';
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
    /** the answer is decided when the request arrives (as a real server would); a delay only holds its delivery, so a
        late answer is a valid one and only the page's own guard can refuse it (review S2 of #82) */
    async fetch(u, init = {}) {
      const res = g.answer(u, init);
      if (g.delay) await g.delay;
      return res;
    },
    answer(u, init) {
      const url = new URL(u), body = init.body ? JSON.parse(init.body) : null, auth = (init.headers || {}).authorization || '';
      log.push({ path: url.pathname + url.search, body, auth, apikey: (init.headers || {}).apikey, keepalive: !!init.keepalive });
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
      return out(404, null);
    },
  };
  return g;
}
/** a tab: its address, its history, its sessionStorage, a clock with timers */
function tab(shared) {
  const clock = shared ? shared.clock : { now: Date.UTC(2027, 0, 11, 8, 0, 0), timers: [], seq: 0 };
  const store = new Map(), visits = [];
  const t = {
    clock, store, visits, outs: [],
    location: { origin: 'https://example.github.io', pathname: '/english-trainer/teacher.html', search: '', hash: '', assign(u) { visits.push(u); } },
    history: { replaceState(_, __, u) { t.replaced = u; const x = new URL(u); t.location.search = x.search; t.location.hash = x.hash; } },
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
/** she keeps working for `ms`: the clock runs, with a tap every 20 minutes */
const stay = (t, ms) => { for (let left = ms; left > 0; left -= 20 * 60000) { t.advance(Math.min(left, 20 * 60000)); t.auth.touch(); } };

// ---- 1. the whole sign-in
{
  const t = tab();
  const r = await t.signIn();
  const go = new URL(t.visits[0]), q = go.searchParams;
  eq('sign-in goes to Supabase Auth for Google, with PKCE (S256), this page as the only redirect, and Google asks which account', [go.origin + go.pathname, q.get('provider'), q.get('code_challenge_method'), q.get('redirect_to'), (q.get('code_challenge') || '').length, q.get('prompt')], [SB + '/auth/v1/authorize', 'google', 's256', PAGE, 43, 'select_account']);
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
  stay(t, 59.5 * 60000);                                          // she keeps working: a tap every 20 minutes
  const before = t.server.log.length, a0 = [...t.server.sessions.values()][0].access_token;
  const a = await t.auth.token();
  eq('an access token about to end is refreshed (the refresh token turns over)', [/^acc-\d+$/.test(a) && a !== a0, t.server.log.length - before, t.server.log.at(-1).path], [true, 1, '/auth/v1/token?grant_type=refresh_token']);
  t.server.refuseRefresh = true; stay(t, 59.5 * 60000);
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
  await tick();
  const issued = [...t.server.sessions.values()][0];
  eq('a late answer after sign-out keeps no session, and the session it brought is revoked at once (with keepalive)', [r.state, r.e, t.auth.signedIn(), issued.alive,
     t.server.log.some(l => l.path === '/auth/v1/logout?scope=local' && l.auth === 'Bearer ' + issued.access_token && l.keepalive)], ['out', 'stale', false, false, true]);
  const u = tab();
  await u.signIn();
  stay(u, 59.5 * 60000);
  let rel2; u.server.delay = new Promise(r => { rel2 = r; });
  const tp = u.auth.token();                                     // the refresh is on its way, slowly
  await tick();
  u.server.delay = null;
  await u.auth.signOut('out');                                   // she signs out meanwhile
  rel2();
  eq('a late refresh after sign-out is not kept', [await tp, u.auth.signedIn()], [null, false]);
}
// ---- 10b. review of #82: the guard cannot be broken, the clock decides, refreshes are shared
{
  // B1: on slow wifi she taps "sign in" again while the first exchange is on its way; the page then goes into the
  // back-forward cache. The late answer must not come back to life there.
  const inFlight = async (t, meanwhile) => {
    await t.auth.begin();
    t.location.search = new URL(t.server.authorize(t.visits.at(-1), 'teacher.one@example.org')).search;
    let release; t.server.delay = new Promise(r => { release = r; });
    const p = t.auth.finish();
    await tick();
    await meanwhile();
    t.server.delay = null; release();
    const r = await p; await tick();
    return [r.e, t.auth.signedIn(), await t.auth.token(), [...t.server.sessions.values()][0].alive];
  };
  const t = tab();
  eq('B1: a second tap on "sign in" while the exchange is on its way: the late answer is refused and its session revoked',
     await inFlight(t, () => t.auth.begin()), ['stale', false, null, false]);
  const t2 = tab();
  eq('B1: leaving the page (pagehide, into the back-forward cache) while the exchange is on its way: back from the cache, nobody is signed in',
     await inFlight(t2, async () => t2.auth.left()), ['stale', false, null, false]);
  const u = tab();
  await u.signIn();
  u.auth.left(); u.auth.left();
  eq('B1: leaving raises the guard every time, with or without a session (no early return)', [u.auth.signedIn(), u.outs], [false, ['left']]);
  // B2: the laptop slept 45 minutes (its timer never ran); the first tap after that is the next person's
  const v = tab();
  await v.signIn();
  v.clock.now += 45 * 60000;
  v.auth.touch(); await tick();
  eq('B2: a tap after 45 minutes asleep signs out (idle), it does not buy another 30 minutes', [v.auth.signedIn(), v.outs, v.server.log.at(-1).path], [false, ['idle'], '/auth/v1/logout?scope=local']);
  // S1: a background refresh is not activity
  const w = tab();
  await w.signIn();
  w.advance(29 * 60000); w.auth.touch(); w.advance(29 * 60000); w.auth.touch();     // her last tap: minute 58
  w.advance(90 * 1000); await w.auth.token();                                         // minute 59.5: the screen refreshes by itself
  w.advance(28.5 * 60000 + 1000); await tick();                                       // minute 88: 30 minutes after her last tap
  eq('S1: a refresh in the background does not count as a tap: 30 minutes after her last one she is signed out', [w.auth.signedIn(), w.outs], [false, ['idle']]);
  // S3: three reads at once with the token about to end share one refresh
  const x = tab();
  await x.signIn();
  stay(x, 59.5 * 60000);
  const n0 = x.server.log.length;
  const all = await Promise.all([x.auth.token(), x.auth.token(), x.auth.token()]);
  eq('S3: calls made together share one refresh, and every one gets the new token', [x.server.log.slice(n0).filter(l => l.path.includes('refresh_token')).length, new Set(all).size, all[0] && all[0].startsWith('acc-')], [1, 1, true]);
  // S5: the page is also served at …/teacher (no .html), which is not on the redirect list
  const y = tab();
  y.location.pathname = '/english-trainer/teacher';
  eq('S5: no sign-in starts from any address but …/teacher.html', [await y.auth.begin(), y.visits.length, y.store.size], ['path', 0, 0]);
  // nice: a fragment is cleaned from the address, never read
  const z = tab();
  z.location.hash = '#access_token=planted&refresh_token=planted';
  const f = await z.auth.finish();
  eq('a fragment in the address (#access_token=…) is removed and never used', [f.state, z.location.hash, z.server.log.length], ['out', '', 0]);
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
