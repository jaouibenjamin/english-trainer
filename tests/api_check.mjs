// The backend adapter js/api.js, without a browser:  node tests/api_check.mjs
// suite:   // picked up by tests/all.py
// 1. With today's config (no BACKEND key) it sends byte for byte what js/state.js sent before the adapter existed.
// 2. 'dual': the Sheet's answer is the answer, whatever Supabase does; the shadow copy never counts twice.
// 3. The events read off two saves. All names, codes and addresses are made up.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
let pass = 0, fail = 0;
const check = (label, ok, detail = '') => { ok ? pass++ : fail++; console.log((ok ? 'PASS ' : 'FAIL ') + label + (ok ? '' : '   <- ' + String(detail).slice(0, 300) + '\n    calls:\n      ' + trace())); };
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want), `got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
const tick = (ms = 30) => new Promise(r => setTimeout(r, ms));

const SHEET = 'https://script.example/macros/s/TEST/exec', SB = 'https://abcdefghijklmnop.supabase.co', KEY = 'public-key-for-tests-0123456789';
let n = 0;
const loaded = [];
/** S-c (review of #50): wait until every adapter copy is idle (no shadow run, no copy, no logout in progress), not a
    fixed time; capped, so a test that holds an answer on purpose still goes on */
let sent = 0;   // every request any copy made, for idle()
const idle = async (cap = 1500) => {
  // until every copy is settled; or, while a test holds an answer on purpose (nothing can settle), until no request
  // has gone out for 150 ms; at most cap
  await tick();
  const t0 = Date.now(); let n = -1, quiet = 0;
  for (;;) {
    const all = () => Promise.race([Promise.all(loaded.map(m => m.settled())).then(() => true), tick(20).then(() => false)]);
    if (await all()) { await tick(1); if (await all()) return; }
    if (sent === n) quiet += 20; else { n = sent; quiet = 0; }
    if (quiet >= 150 || Date.now() - t0 > cap) return;
  }
};
/** S2 (review of #55): on a failure, the calls of the test that failed, so a flake can be told from a bug */
let lastCalls = [];
const trace = () => lastCalls.slice(-14).map(c => (c.url.startsWith(SB) ? c.url.slice(SB.length).replace(/\?.*$/, '') : 'SHEET:' + (c.body && c.body.a)) + ' ' + ((c.init.headers || {}).authorization || '').replace('Bearer ', '@') + ' ' + JSON.stringify(c.body || '').slice(0, 60)).join('\n      ');
/** a fresh copy of the module under a given config, with fetch and localStorage replaced. shared: the store of another
    copy (two tabs of one browser). on(): puts this copy's storage and fetch back (two devices, one after the other). */
async function load(backend, route, shared) {
  const calls = shared ? shared.calls : [], store = shared ? shared.store : new Map(), listeners = [], group = shared ? shared.group : [];
  // another copy on the same storage is another tab: it hears the 'storage' event of a change, as a browser tab does
  const tell = (k, o, v) => { if (o !== v) for (const g of group) if (g !== listeners) for (const [t, f] of g) if (t === 'storage') f({ key: k, oldValue: o, newValue: v }); };
  const ls = { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => { const o = store.has(k) ? store.get(k) : null; store.set(k, String(v)); tell(k, o, String(v)); }, removeItem: k => { const o = store.has(k) ? store.get(k) : null; store.delete(k); tell(k, o, null); } };
  group.push(listeners);
  lastCalls = calls;
  const f = async (url, init = {}) => {
    const c = { url: String(url), init, body: init.body ? JSON.parse(init.body) : null, at: calls.length };
    calls.push(c); sent++;
    const r = await route(c);
    if (r instanceof Error) throw r;
    return { ok: (r.status || 200) < 400, status: r.status || 200, json: async () => { if (r.badJson) throw new SyntaxError('Unexpected token <'); return r.json; } };
  };
  const on = () => { globalThis.localStorage = ls; globalThis.fetch = f; };
  globalThis.window = globalThis;
  globalThis.addEventListener = (t, f) => listeners.push([t, f]);
  globalThis.document = { visibilityState: 'visible', addEventListener: (t, f) => listeners.push([t, f]) };
  globalThis.API_URL = '  ' + SHEET + ' ';
  if (backend === undefined) delete globalThis.BACKEND; else globalThis.BACKEND = backend;
  on();
  const m = await import(pathToFileURL(path.join(ROOT, 'js/api.js')).href + '?v=' + (++n));
  if (m.settled) loaded.push(m);
  return { m, calls, store, listeners, group, on, hide: () => { globalThis.document.visibilityState = 'hidden'; for (const [t, f] of listeners) if (t === 'visibilitychange') f(); } };
}
const sheetOk = c => c.url === SHEET ? { json: { ok: true, s: { pts: 5 } } } : null;

// ---- 1. the default is the Sheet, unchanged
{
  /* the function js/state.js had before the adapter, verbatim, as the reference */
  const reference = async (API, a, d) => { const sent = []; const f = async (u, i) => { sent.push([u, i]); return { json: async () => ({ ok: true }) }; };
    const fetch = f; const r = await fetch(API, { method: 'POST', body: JSON.stringify({ a, ...d }), keepalive: a === 'save' }); try { await r.json(); } catch (e) { return { ok: false, e: 'server' }; } return sent[0]; };
  for (const [a, d] of [['login', { c: 'EN-0000', n: 'נועה', p: '4827' }], ['save', { c: 'EN-0000', n: 'נועה', p: '4827', s: { pts: 7, st: { cat: [2, 1] } } }], ['board', { c: 'x', n: 'y', p: '0000' }], ['teacher', { c: 'x', t: '123456' }], ['reset', { c: 'x', t: '1', n: 'y' }], ['register', { c: 'x', n: 'y', p: '4827' }]]) {
    const { m, calls } = await load(undefined, sheetOk);
    const out = await m.api(a, d);
    const want = await reference(SHEET, a, d);
    eq(`default config, ${a}: the same request as before (address, method, body, keepalive)`, [calls.length, calls[0].url, calls[0].init], [1, want[0], want[1]]);
    eq(`default config, ${a}: the Sheet's answer comes back untouched`, out, { ok: true, s: { pts: 5 } });
  }
  const { m } = await load(undefined, sheetOk);
  eq('no BACKEND key: mode sheet', m.MODE, 'sheet');
  for (const bad of [{ mode: 'dual' }, { mode: 'dual', url: 'http://abcdefghijklmnop.supabase.co', key: KEY }, { mode: 'dual', url: 'https://evil.example', key: KEY }, { mode: 'dual', url: SB + '.evil.example', key: KEY },
    { mode: 'dual', url: SB, key: 'short' }, { mode: 'Dual', url: SB, key: KEY }, { mode: 'supabase ', url: SB, key: KEY }, 'dual', null, 5]) {
    const x = await load(bad, sheetOk);
    await x.m.api('save', { s: {} }); await tick();
    eq(`a wrong or half-filled BACKEND ${JSON.stringify(bad).slice(0, 60)} falls back to the Sheet alone`, [x.m.MODE, x.calls.map(c => c.url)], ['sheet', [SHEET]]);
  }
  const { m: mbad } = await load(undefined, c => c.url === SHEET ? { badJson: true } : null);
  eq('default config: an answer that is not JSON (an Apps Script error page) gives {ok:false, e:"server"}, as js/state.js does', await mbad.api('save', {}), { ok: false, e: 'server' });
  const { m: m2 } = await load(undefined, () => new Error('offline'));
  let threw = false; try { await m2.api('save', {}); } catch (e) { threw = true; }
  check('default config: a network failure is thrown to the caller as before (the game turns it into "no connection")', threw);
  const src = fs.readFileSync(path.join(ROOT, 'js/state.js'), 'utf8');
  check('js/state.js gets api() from the adapter and still exports it', /import \{api,forget\} from '\.\/api\.js';export \{api\};/.test(src) && !/fetch\(API,/.test(src));
  check('and tells it at logout and at relogin (B1)', /export function relogin\(\)\{const u=S\.u;if\(!u\)return null;forget\(false\);/.test(src) && /return false;\n forget\(true\);/.test(src));
}

// ---- 2. dual write
const CRED = { c: 'EN-0000', n: 'נועה', p: '4827' };
const ses = at => ({ ok: true, session: { access_token: 'acc1', refresh_token: 'ref1', expires_at: Math.floor(Date.now() / 1000) + 3600 }, device_token: 'd'.repeat(43), updated_at: at, s: {} });
function supabase(state) {   // a tiny stand-in for the project: sign-in, save_progress, record_events
  return c => {
    if (c.url === SHEET) return { json: state.sheet ?? { ok: true } };
    state.seen.push(c.url.replace(SB, ''));
    if (state.down) return state.down === 'throw' ? new Error('down') : { status: 500, json: null };
    if (c.url.endsWith('/functions/v1/pupil-login')) { state.logins.push(c.body); return { json: typeof state.login === 'function' ? state.login(c.body) : state.login ?? ses('t0') }; }
    if (c.url.includes('/auth/v1/token?grant_type=refresh_token')) return { json: { access_token: 'acc-r', refresh_token: 'ref-r', expires_in: 3600 } };
    if (c.url.includes('/auth/v1/logout')) { (state.logouts ??= []).push(c.init.headers.authorization); return { status: 204, json: null }; }
    if (c.url.endsWith('/rpc/save_progress')) { state.saves.push(c.body); if (state.conflict-- > 0) return { json: { ok: false, conflict: true, state: {}, updated_at: 't9' } }; return { json: { ok: true, updated_at: 't' + state.saves.length } }; }
    if (c.url.endsWith('/rpc/record_events')) { state.batches.push(c.body); if (state.loseAnswer-- > 0) return new Error('answer lost'); return { json: { ok: true, points: 30, flagged: 0 } }; }
    return { status: 404, json: null };
  };
}
const fresh = o => ({ seen: [], logins: [], saves: [], batches: [], conflict: 0, loseAnswer: 0, ...o });
{
  const st = fresh();
  const { m, calls, store } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  eq('dual: mode', m.MODE, 'dual');
  st.sheet = { ok: true, s: { pts: 1 } };
  const r = await m.api('login', CRED); await idle();
  eq('dual login: the answer is the Sheet\'s', r, { ok: true, s: { pts: 1 } });
  eq('dual login: the Sheet was asked first, then the shadow sign-in', [calls[0].url, st.seen], [SHEET, ['/functions/v1/pupil-login']]);
  eq('the shadow sign-in sends class code, name and code and nothing else', st.logins[0], { class_code: 'EN-0000', name: 'נועה', code: '4827' });
  st.sheet = { ok: true };
  await m.api('save', { ...CRED, s: { pts: 10, st: { cat: [1, 0] } } }); await idle();
  eq('first save after a sign-in: counted from the record the Sheet had at sign-in (review of #50)', [st.saves.length, st.batches.length, (st.batches[0] || { p_events: [] }).p_events.map(e => e.item)], [1, 1, ['cat']]);
  await m.api('save', { ...CRED, s: { pts: 34, st: { cat: [2, 0], dog: [1, 1] } } }); await idle();
  eq('second save: the difference goes as events', (st.batches[1] || { p_events: [] }).p_events.map(e => [e.item, e.first_try]), [['cat', true], ['dog', false]]);
  check('saves go with the session, never with the code', calls.filter(c => c.url.includes('/rest/')).every(c => c.init.headers.authorization === 'Bearer acc1' && !JSON.stringify(c.body).includes('4827')));
  const all = [...store.entries()].map(([k, v]) => k + v).join('|');
  check('nothing kept on the device by the adapter holds the code or the name', !all.includes('4827') && !all.includes('נועה'), all.slice(0, 200));
  check('the shadow log has numbers only', m.shadowLog().length >= 3 && !JSON.stringify(m.shadowLog()).includes('נועה') && m.shadowLog().some(l => l.k === 'save' && l.server === 30) && m.shadowLog().some(l => l.k === 'sheet' && l.pts === 34), JSON.stringify(m.shadowLog()));
  for (const a of ['board', 'teacher', 'reset']) { const before = st.seen.length; await m.api(a, CRED); await idle(); eq(`dual ${a}: the Sheet only`, st.seen.length, before); }
  m.forget(true); await idle();
  check('sign out: the session is removed from this device, the device token stays', !store.get('wi-sb-session').includes('ref1') && store.get('wi-sb-session').includes('ddd'));
}
for (const down of ['throw', 500]) {
  const st = fresh({ down, sheet: { ok: true, s: { pts: 3 } } });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  const t0 = Date.now();
  const r1 = await m.api('login', CRED), r2 = await m.api('save', { ...CRED, s: { pts: 3 } });
  eq(`dual, Supabase ${down === 'throw' ? 'unreachable' : 'answering 500'}: the pupil gets the Sheet's answers`, [r1, r2], [{ ok: true, s: { pts: 3 } }, { ok: true, s: { pts: 3 } }]);
  check('and does not wait for it', Date.now() - t0 < 200);
  await idle();
}
{
  const st = fresh({ sheet: { ok: false, e: 'pin' } });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  const r = await m.api('save', { ...CRED, s: { pts: 3 } }); await idle();
  eq('dual: a save the Sheet refuses is not copied', [r, st.seen], [{ ok: false, e: 'pin' }, []]);
  st.sheet = new Error('offline');
  const x = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, c => c.url === SHEET ? new Error('offline') : supabase(st)(c));
  let threw = false; try { await x.m.api('save', CRED); } catch (e) { threw = true; }
  check('dual: a Sheet network failure is thrown exactly as in sheet mode, and nothing is copied', threw && st.seen.length === 0);
}
{
  const st = fresh({ loseAnswer: 1 });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  await m.api('login', CRED); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [1, 0] } } }); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [3, 0] } } }); await idle();    // the server takes it, the answer is lost
  await m.api('save', { ...CRED, s: { st: { cat: [4, 0] } } }); await idle();    // the same batch must go again first
  await m.api('save', { ...CRED, s: { st: { cat: [4, 0] } } }); await idle();
  eq('a batch whose answer was lost is sent again under the same id (the server counts it once)', [st.batches.length >= 2, st.batches[0].p_batch === st.batches[1].p_batch, st.batches[1].p_events.length], [true, true, 2]);
  await m.api('save', { ...CRED, s: { st: { cat: [5, 0] } } }); await idle();
  const last = st.batches[st.batches.length - 1];
  eq('afterwards only what is new since the last batch the server took, under a new id', [last.p_events.length, last.p_batch !== st.batches[0].p_batch], [1, true]);
  eq('in total every answer was put in a batch exactly once', [...new Map(st.batches.map(b => [b.p_batch, b.p_events.length])).values()].reduce((a, b) => a + b, 0), 4);
}
{
  const st = fresh({ conflict: 1 });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  await m.api('login', CRED); await idle();
  await m.api('save', { ...CRED, s: { pts: 1 } }); await idle();
  eq('shadow: when another device saved first the copy is written again over the version the server named (the Sheet is the truth)', st.saves.map(s => s.p_base), ['t0', 't9']);
  const st2 = fresh({ login: { ok: false, e: 'pin' } });
  const y = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st2));
  for (let i = 0; i < 5; i++) { await y.m.api('save', { ...CRED, s: { pts: i } }); await idle(); }
  eq('a pupil the shadow side does not know yet: one sign-in try, not one per save', st2.logins.length, 1);
}

// ---- 2b. pacing (review S8): the newest state, at most every saveEveryS, at once when the page is hidden; "wait" and
// "daycap" keep it and try again
{
  const { m, listeners, calls } = await load(undefined, sheetOk);
  eq('sheet mode registers nothing on the page', listeners.length, 0);
  m.forget(true); m.forget(false); await idle();
  eq('and logout or relogin in sheet mode contacts nobody', calls.length, 0);
}
{
  const st = fresh();
  const { m, hide, calls } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 2 }, supabase(st));
  await m.api('login', CRED); await idle();
  for (let i = 1; i <= 6; i++) { await m.api('save', { ...CRED, s: { pts: i, st: { cat: [i, 0] } } }); await tick(20); }
  eq('6 saves of the game inside the 2 s window: one copy now', st.saves.length, 1);
  await tick(2200); await idle();
  eq('and one more when the time is up, with the newest state only', [st.saves.length, st.saves[1].p_state.pts], [2, 6]);
  eq('every answer still went in a batch exactly once', st.batches.reduce((a, b) => a + b.p_events.length, 0), 5);
  await m.api('save', { ...CRED, s: { pts: 7, st: { cat: [7, 0] } } }); await idle();
  eq('a save right after a copy waits', st.saves.length, 2);
  hide(); await idle();
  eq('until the page is hidden: then it goes at once', [st.saves.length, st.saves[2].p_state.pts], [3, 7]);
  check('with keepalive, so it survives the page', calls.filter(c => c.url.endsWith('/rpc/save_progress')).pop().init.keepalive === true);
  check('the public key that is not a JWT is never sent as a bearer', calls.filter(c => c.url.startsWith(SB)).every(c => c.init.headers.authorization !== 'Bearer ' + KEY));
}
{
  const st = fresh();
  let answer = { ok: false, e: 'wait', retry_after: 1 };
  const base = supabase(st);
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, c => {
    if (c.url.endsWith('/rpc/save_progress') && answer) { st.saves.push(c.body); const a = answer; answer = null; return { json: a }; }
    return base(c);
  });
  await m.api('login', CRED); await idle();
  await m.api('save', { ...CRED, s: { pts: 1 } }); await idle();
  eq('the server says wait 1 s: nothing more is sent before that', st.saves.length, 1);
  await m.api('save', { ...CRED, s: { pts: 2 } }); await idle();
  eq('not even for a newer save', st.saves.length, 1);
  await tick(1100);
  eq('after it, the newest state goes', [st.saves.length, st.saves[1].p_state.pts], [2, 2]);
  answer = { ok: false, e: 'daycap', retry_after: 3600 };
  await m.api('save', { ...CRED, s: { pts: 3 } }); await idle();
  await m.api('save', { ...CRED, s: { pts: 4 } }); await tick(200);
  eq('the day\'s saves are used up: kept on the device, not sent again today', st.saves.length, 3);
  check('and noted as such, not as an error', m.shadowLog().some(l => l.k === 'save' && l.e === 'daycap'));
}
{
  const st = fresh();
  let brake = true;
  const base = supabase(st);
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, c => {
    if (c.url.endsWith('/rpc/record_events') && brake) { st.batches.push(c.body); return { json: { ok: false, e: 'brake', points: 0 } }; }
    return base(c);
  });
  await m.api('login', CRED); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [1, 0] } } }); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [2, 0] } } }); await idle();
  eq('the storage brake: the batch is refused and kept on the device', [st.batches.length, m.shadowLog().some(l => l.k === 'brake')], [1, true]);
}
{
  const st = fresh();
  const { m } = await load({ mode: 'supabase', url: SB, key: KEY, saveEveryS: 2, unfinished: true }, supabase(st));
  await m.api('login', CRED); await idle();
  const r1 = await m.api('save', { ...CRED, s: { pts: 1 } });
  const r2 = await m.api('save', { ...CRED, s: { pts: 2 } });
  eq("'supabase': the first save goes, the next one inside the 2 s window is kept and the game hears ok", [r1, r2, st.saves.length], [{ ok: true }, { ok: true }, 1]);
  st.conflict = 1;
  await tick(2200); await idle();
  eq('the kept save meets another device\'s version', st.saves.length, 2);
  const r3 = await m.api('save', { ...CRED, s: { pts: 3 } });
  eq('the next save of the game is told to join (stale, with the server\'s state)', [r3.ok, r3.e], [false, 'stale']);
}

// ---- 2c. the reviews of #21 and #35: shared devices, sign-in once, events even when a save waits, 2 hours of play
{
  const { m } = await load({ mode: 'supabase', url: SB, key: KEY }, sheetOk);
  eq("'supabase' without the second key (unfinished: true) stays on the Sheet (S-b)", m.MODE, 'sheet');
}
{
  const A = { c: 'EN-0000', n: 'Testa', p: '4827' }, Bp = { c: 'EN-0000', n: 'Probe', p: '5839' };
  const st = fresh({ login: b => b.name === 'Testa' ? { ...ses('t0'), session: { access_token: 'tok-A', refresh_token: 'ref-A', expires_at: Math.floor(Date.now() / 1000) + 3600 } } : { ok: false, e: 'pin' } });
  const { m, calls, store } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  await m.api('login', A); await idle();
  await m.api('save', { ...A, s: { pts: 1 } }); await idle();
  await m.api('login', Bp); await idle();
  for (let i = 0; i < 3; i++) { await m.api('save', { ...Bp, s: { pts: 100 + i } }); await idle(); }
  const restAfterB = calls.filter(c => c.url.includes('/rest/') && c.body && c.body.p_state && c.body.p_state.pts >= 100);
  eq('two pupils on one device: B\'s progress is never sent with A\'s session (B1)', restAfterB.length, 0);
  eq('A\'s session was revoked on the server when B came', st.logouts, ['Bearer tok-A']);
  check('and is gone from the device', !(store.get('wi-sb-session') || '').includes('tok-A'));
  check('the device keeps no name: only a hash of class code and name', !(store.get('wi-sb-owner') || '').includes('Probe') && /^"[0-9a-f]{24}"$/.test(store.get('wi-sb-owner') || ''), store.get('wi-sb-owner'));
  eq('B (unknown to Supabase) was tried once, then not again today (S-a)', st.logins.filter(b => b.name === 'Probe').length, 1);
  await m.api('login', Bp); await idle();
  eq('not even at the next Sheet sign-in', st.logins.filter(b => b.name === 'Probe').length, 1);
  await m.api('login', A); await idle();
  await m.api('login', A); await idle();
  eq('A again: signed in once, and the second sign-in on the Sheet does not open another session (S-a)', st.logins.filter(b => b.name === 'Testa').length, 2);
  const before = (st.logouts || []).length;
  m.forget(true); await idle();
  check('logout: the session is revoked on the server and nothing of the pupil stays on the device (B1)', (st.logouts || []).length === before + 1
    && !store.get('wi-sb-base') && !store.get('wi-sb-pending') && !(store.get('wi-sb-session') || '').includes('access'), [st.logouts, [...store.keys()]]);
}
{
  const st = fresh();
  const base = supabase(st);
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, c => {
    if (c.url.endsWith('/rpc/save_progress') && st.saves.length >= 1) { st.saves.push(c.body); return { json: { ok: false, e: 'wait', retry_after: 30 } }; }
    return base(c);
  });
  await m.api('login', CRED); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [1, 0] } } }); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [3, 0] } } }); await idle();
  eq('a save the server asks to wait: its events still go now, not tomorrow (B2)', [st.saves.length, st.batches.length, st.batches[0] && st.batches[0].p_events.length], [2, 1, 2]);
}
{
  // two hours of steady play on a virtual clock: an answer every 4 s, the game saving after each one (B2)
  const real = { now: Date.now, st: globalThis.setTimeout, ct: globalThis.clearTimeout };
  let now = Date.UTC(2027, 0, 11, 7, 0, 0), seq = 0, timers = [];
  Date.now = () => now;
  globalThis.setTimeout = (f, ms) => { const id = ++seq; timers.push({ id, at: now + (ms || 0), f }); return id; };
  globalThis.clearTimeout = id => { timers = timers.filter(t => t.id !== id); };
  const flushMicro = () => new Promise(r => real.st(r, 0));
  let M = null;                                                  // the adapter, once loaded: advance() waits until it is idle (S5)
  const advance = async ms => {
    const end = now + ms;
    for (;;) {
      timers.sort((a, b) => a.at - b.at);
      const t = timers[0];
      if (!t || t.at > end) break;
      timers.shift(); now = Math.max(now, t.at); t.f(); await flushMicro(); if (M) await M.settled(); await flushMicro();
    }
    now = end; await flushMicro(); if (M) await M.settled();
  };
  try {
    const st = fresh(); let lastOk = 0, writes = 0, refused = 0;
    const base = supabase(st);
    const { m, hide } = await load({ mode: 'dual', url: SB, key: KEY }, c => {     // the real pacing: 30 s
      if (c.url.endsWith('/rpc/save_progress')) {
        st.saves.push(c.body);
        if (now - lastOk < 5000 || writes >= 300) { refused++; return { json: { ok: false, e: writes >= 300 ? 'daycap' : 'wait', retry_after: 5 } }; }
        lastOk = now; writes++; return { json: { ok: true, updated_at: 't' + writes } };
      }
      return base(c);
    });
    M = m;
    await m.api('login', CRED); await advance(1000);
    const answers = 1800;
    for (let i = 1; i <= answers; i++) { await m.api('save', { ...CRED, s: { pts: i * 10, st: { cat: [i, 0] } } }); await advance(4000); }
    hide(); await advance(60000);
    const sent = st.batches.reduce((a, b) => a + b.p_events.length, 0);
    eq('every answer reached the server in a batch exactly once (the first save sets the base)', sent, answers - 1);
    eq('and the last state the game saved is the one stored', st.saves[st.saves.length - 1].p_state.pts, answers * 10);
  } finally { Date.now = real.now; globalThis.setTimeout = real.st; globalThis.clearTimeout = real.ct; }
}

// ---- 2d. the review of #39: a save in flight across a change of pupil, logout, long waits, an expired token
{
  // blocker 1: pupil A's slow save is still in flight when A logs out and B signs in on the same device
  // (fixed waits here: the test holds an answer on purpose, so the adapter is not idle until it is released)
  let release; const slow = new Promise(r => { release = r; });
  const st = fresh({ login: b => ({ ...ses('t0'), session: { access_token: 'tok-' + b.name, refresh_token: 'ref-' + b.name, expires_at: Math.floor(Date.now() / 1000) + 3600 } }) });
  const base = supabase(st);
  let slowOnce = false;
  const { m, calls, store, hide } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, async c => {
    if (c.url.endsWith('/rpc/save_progress') && c.body.p_state.who === 'A' && c.body.p_state.n === 2 && !slowOnce) { slowOnce = true; await slow; }
    return base(c);
  });
  const A = { c: 'EN-0000', n: 'Testa', p: '4827' }, Bp = { c: 'EN-0000', n: 'Probe', p: '5839' };
  await m.api('login', A); await tick();
  await m.api('save', { ...A, s: { who: 'A', n: 1, st: { cat: [1, 0] } } }); await tick();
  await m.api('save', { ...A, s: { who: 'A', n: 2, st: { cat: [3, 0] } } }); await tick();     // kept (inside the window)
  hide(); await tick();                                                                        // the page hides: A's save goes, and the server is slow
  globalThis.document.visibilityState = 'visible';
  m.forget(true); await tick();                                                                // A logs out
  await m.api('login', Bp); await tick();                                                      // B signs in
  release(); await tick(100);                                                                  // A's slow answer arrives now
  await m.api('save', { ...Bp, s: { who: 'B', n: 1, st: { dog: [1, 0] } } }); await tick();
  await m.api('save', { ...Bp, s: { who: 'B', n: 2, st: { dog: [2, 0] } } }); await tick();
  hide(); await tick(50); globalThis.document.visibilityState = 'visible';
  const withB = calls.filter(c => c.init.headers && c.init.headers.authorization === 'Bearer tok-Probe');
  eq("A's slow save: nothing of A goes with B's session (no A state, no A answer)", withB.filter(c => JSON.stringify(c.body).includes('"who":"A"') || JSON.stringify(c.body).includes('"cat"')).length, 0);
  eq("B's first save sets B's own base, so B's events are B's only", st.batches.filter(b => b.p_events.some(e => e.item === 'dog')).map(b => b.p_events.length), [1]);
  check("and A's state is not waiting to be sent again", !JSON.stringify([...store.values()]).includes('"who":"A"'));
}
{
  // 2: logout sends what was played since the last copy, then revokes
  const st = fresh();
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, supabase(st));
  await m.api('login', CRED); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [1, 0] } } }); await idle();                // written at once (the first)
  for (let i = 2; i <= 9; i++) { await m.api('save', { ...CRED, s: { st: { cat: [i, 0] } } }); await tick(5); }   // kept: inside the window
  eq('8 answers inside the window: not sent yet', st.batches.length, 0);
  m.forget(true); await idle(400);
  eq('logout: they are sent first, then the session is revoked', [st.batches.reduce((a, b) => a + b.p_events.length, 0), (st.logouts || []).length, st.seen.lastIndexOf('/auth/v1/logout?scope=local') > st.seen.lastIndexOf('/rest/v1/rpc/record_events')], [8, 1, true]);
}
{
  // 3: many answers after a long wait go in parts of 200, none cut; a part that failed goes again under its own id
  const st = fresh();
  let failPart = 2;
  const base = supabase(st);
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, c => {
    if (c.url.endsWith('/rpc/record_events')) { st.batches.push(c.body); if (st.batches.length - 1 === failPart) { failPart = -1; return new Error('lost'); } return { json: { ok: true, points: 1, flagged: 0 } }; }
    return base(c);
  });
  await m.api('login', CRED); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [0, 0], dog: [0, 0] } } }); await idle();
  await m.api('save', { ...CRED, s: { st: { cat: [450, 0], dog: [300, 0] } } }); await idle(400);
  await m.api('save', { ...CRED, s: { st: { cat: [450, 0], dog: [300, 0] }, x: 1 } }); await idle(400);
  const byId = new Map(st.batches.map(b => [b.p_batch, b.p_events.length]));
  eq('750 answers: 4 parts (200, 200, 200, 150), each id once in the end, none cut', [...byId.values()], [200, 200, 200, 150]);
  eq('the part whose answer was lost went again under the same id, the parts before it did not', st.batches.map(b => b.p_batch).filter((x, i, a) => a.indexOf(x) !== i).length, 1);
}
{
  // 4: an expired access token is refreshed before the session is revoked, so the refresh token dies too
  const st = fresh({ login: { ...ses('t0'), session: { access_token: 'old', refresh_token: 'ref1', expires_at: Math.floor(Date.now() / 1000) - 10 } } });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  await m.api('login', CRED); await idle();
  m.forget(true); await idle(400);
  eq('logout with an expired access token: refreshed first, then revoked with the fresh one', st.logouts, ['Bearer acc-r']);
}

let R = null, real = null, S = null;   // the route, the load and js/state.js of the real-flow tests (one js/api.js per process)
let reloads = 0;
globalThis.location = { reload() { reloads++; } };
// ---- 2e. the review of #41: one guard for every late answer (a session id and the generation, checked by one op)
const A = { c: 'EN-0000', n: 'Testa', p: '4827' }, Bp = { c: 'EN-0000', n: 'Probe', p: '5839' };
const perPupil = b => ({ ...ses('t0'), session: { access_token: 'tok-' + b.name, refresh_token: 'ref-' + b.name, expires_at: Math.floor(Date.now() / 1000) + 3600 } });
const gate = () => { let open; const p = new Promise(r => { open = r; }); return { p, open }; };
const sesOf = store => JSON.parse(store.get('wi-sb-session') || 'null') || {};
const bearer = c => (c.init.headers || {}).authorization || '';
{
  // B1: A's copy at hide time asks for a fresh token (the hour is over) and that answer is late. Meanwhile B signs in.
  const g = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  let slowRefresh = true;
  const { m, calls, store, hide } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, async c => {
    if (c.url.includes('grant_type=refresh_token') && slowRefresh) { slowRefresh = false; await g.p; return { json: { access_token: 'late-A', refresh_token: 'late-ref-A', expires_in: 3600 } }; }
    return base(c);
  });
  await m.api('login', A); await idle(400);
  await m.api('save', { ...A, s: { who: 'A', n: 1, st: { cat: [1, 0] } } }); await idle(400);
  await m.api('save', { ...A, s: { who: 'A', n: 2, st: { cat: [2, 0] } } }); await idle(400);   // kept (inside the window)
  store.set('wi-sb-session', JSON.stringify({ ...sesOf(store), expires_at: Math.floor(Date.now() / 1000) - 10 }));   // an hour later
  hide(); await idle(400); globalThis.document.visibilityState = 'visible';                     // A's copy waits for the refresh
  await m.api('login', Bp); await idle(400);                                                 // B signs in on the same device
  const sidB = sesOf(store).sid;
  g.open(); await idle(400);                                                                 // the late refresh of A arrives
  eq('B1: a late token refresh of A does not put A\'s session back after B signed in', [sesOf(store).access_token, sesOf(store).sid === sidB && !!sidB], ['tok-Probe', true]);
  await m.api('save', { ...Bp, s: { who: 'B', st: { dog: [1, 0] } } }); await idle(400);
  check('and nothing goes with the late token, B\'s save goes with B\'s session', calls.filter(c => c.url.includes('/rest/') && JSON.stringify(c.body).includes('"who":"B"')).every(c => bearer(c) === 'Bearer tok-Probe')
    && calls.filter(c => bearer(c).includes('late-A')).length === 0, calls.filter(c => c.url.includes('/rest/')).map(bearer));
}
{
  // B2: a logout while the shadow is busy and a save of the pupil waits behind it (with the code). Afterwards nothing
  // may sign the pupil in again.
  const g = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  const { m, store } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, async c => {
    if (c.url.endsWith('/pupil-login') && st.logins.length === 0) { const r = base(c); await g.p; return r; }
    return base(c);
  });
  await m.api('login', A);                                       // the shadow sign-in is slow
  await m.api('save', { ...A, s: { st: { cat: [1, 0] } } });    // waits behind it, with the code
  m.forget(true);                                                // A logs out
  g.open(); await idle(400); await m.settled(); await idle(400);
  eq('B2: logout while a save waits behind a slow sign-in: no session is left, A was signed in once and revoked once', [!!sesOf(store).refresh_token, st.logins.length, (st.logouts || []).length], [false, 1, 1]);
  check('and nothing of A stays on the device (base, batch, owner, marks)', ['wi-sb-base', 'wi-sb-pending', 'wi-sb-owner', 'wi-sb-stop', 'wi-sb-netfail'].every(k => !store.has(k)), [...store.keys()]);
  await m.api('save', { ...A, s: { st: { cat: [2, 0] } } }); await idle(400);   // a save that comes after the logout (an old tab, a late timer)
  eq('a resurrect after logout needs a new Sheet answer: the shadow signs in only for a request it is given', st.logins.length, 2);
}
{
  // S2: A's logout is slow (the copy of the last answers takes long). B signs in meanwhile: B's session survives it.
  const g = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  const { m, store } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, async c => {
    if (c.url.endsWith('/rpc/save_progress') && c.body.p_state.n === 2) { const r = base(c); await g.p; return r; }
    return base(c);
  });
  await m.api('login', A); await idle(400);
  await m.api('save', { ...A, s: { n: 1, st: { cat: [1, 0] } } }); await idle(400);
  await m.api('save', { ...A, s: { n: 2, st: { cat: [3, 0] } } }); await idle(400);
  m.forget(true); await idle(400);                                  // A's copy is on its way, slowly
  const pB = m.api('login', Bp); await idle(400);
  eq('S2: B, signing in during A\'s logout, waits for it', st.logins.map(b => b.name), ['Testa']);
  g.open(); await pB; await idle(400); await m.settled();
  eq('then A\'s answers are copied, A\'s session alone is revoked, and B is signed in', [st.batches.reduce((a, b) => a + b.p_events.length, 0), st.logouts, sesOf(store).access_token], [2, ['Bearer tok-Testa'], 'tok-Probe']);
}
{
  // S2 and S4, two tabs: tab 1 logs A out slowly, tab 2 signs B in meanwhile. Tab 1 leaves B's session alone.
  const g = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  const route = async c => { if (c.url.endsWith('/rpc/save_progress') && c.body.p_state.n === 2) { const r = base(c); await g.p; return r; } return base(c); };
  const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, route);
  const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, route, t1);
  await t1.m.api('login', A); await idle(400);
  await t1.m.api('save', { ...A, s: { n: 1, st: { cat: [1, 0] } } }); await idle(400);
  await t1.m.api('save', { ...A, s: { n: 2, st: { cat: [3, 0] } } }); await idle(400);
  t1.m.forget(true); await idle(400);                               // tab 1: A leaves, the copy is slow
  await t2.m.api('login', Bp); await idle(400);                   // tab 2: B signs in
  g.open(); await idle(400); await t1.m.settled(); await t2.m.settled();
  eq('two tabs: a late logout in tab 1 does not end B\'s session from tab 2', [sesOf(t1.store).access_token, (st.logouts || []).includes('Bearer tok-Probe')], ['tok-Probe', false]);
  check('and A\'s late copy left nothing of A in B\'s storage', !JSON.stringify([...t1.store.values()]).includes('"cat"'), [...t1.store.entries()]);
}
{
  // S4: two tabs, two module copies on one storage. Tab 1 copies A slowly; tab 2 signs B in. A's late answer must not
  // become B's base, and none of A's answers go with B's session.
  const g = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  const route = async c => { if (c.url.endsWith('/rpc/save_progress') && c.body.p_state.who === 'A' && c.body.p_state.n === 2) { const r = base(c); await g.p; return r; } return base(c); };
  const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route);
  const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route, t1);
  await t1.m.api('login', A); await idle(400);
  await t1.m.api('save', { ...A, s: { who: 'A', n: 1, st: { cat: [1, 0] } } }); await idle(400);
  await t1.m.api('save', { ...A, s: { who: 'A', n: 2, st: { cat: [4, 0] } } }); await idle(400);   // slow
  await t2.m.api('login', Bp); await idle(400);
  g.open(); await idle(400);
  await t2.m.api('save', { ...Bp, s: { who: 'B', st: { dog: [1, 0] } } }); await idle(400);
  await t2.m.api('save', { ...Bp, s: { who: 'B', st: { dog: [2, 0] } } }); await idle(400);
  check('S4, two tabs: A\'s late answer did not become the base or the batch of B', !JSON.stringify([...t1.store.values()]).includes('"who":"A"'), [...t1.store.entries()]);
  eq('and B\'s events are B\'s only, sent with B\'s session', st.batches.filter(b => b.p_events.some(e => e.item === 'dog')).map(b => b.p_events.map(e => e.item).join()), ['dog']);
  eq('nothing of A went with B\'s session', t1.calls.filter(c => bearer(c) === 'Bearer tok-Probe' && JSON.stringify(c.body).includes('cat')).length, 0);
}
{
  // S3: one pupil, two devices (two storages). Each answer is counted once, by the device it was played on.
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  let sheet = { ok: true, s: {} };
  const route = c => c.url === SHEET ? { json: c.body.a === 'login' ? sheet : { ok: true } } : base(c);
  const d1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route);
  const d2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, route);
  const total = () => st.batches.reduce((a, b) => a + b.p_events.filter(e => e.item === 'cat').length, 0);
  d2.on(); await d2.m.api('login', A); await idle(400); await d2.m.api('save', { ...A, s: { st: { cat: [0, 0] } } }); await idle(400);   // device 2 has its base
  d1.on(); await d1.m.api('login', A); await idle(400);
  await d1.m.api('save', { ...A, s: { st: { cat: [0, 0] } } }); await idle(400);
  await d1.m.api('save', { ...A, s: { st: { cat: [5, 1] } } }); await idle(400);          // 5 answers on device 1
  d2.on(); sheet = { ok: true, s: { st: { cat: [5, 1] } } };
  await d2.m.api('login', A); await idle(400);                                             // device 2 signs in: the Sheet has device 1's 5
  await d2.m.api('save', { ...A, s: { st: { cat: [6, 1] } } }); await idle(400);          // the game joined them and 1 more is played
  d2.hide(); await idle(400); globalThis.document.visibilityState = 'visible';
  eq('S3: two devices, the record joined on a Sheet sign-in: device 1\'s answers are not counted again by device 2', total(), 6);
  await d2.m.api('save', { ...A, s: { st: { cat: [8, 1] } } }); await idle(400);          // 2 more, kept (inside the window)
  d1.on(); sheet = { ok: true, s: { st: { cat: [8, 1] } } };
  await d1.m.api('login', A); await idle(400);                                             // a pull of device 1: it joins device 2's 8
  await d1.m.api('save', { ...A, s: { st: { cat: [11, 1] } } }); await idle(400);          // and plays 3 more
  d2.on(); sheet = { ok: true, s: { st: { cat: [11, 1] } } };
  await d2.m.api('login', A); await idle(400);                                             // a pull of device 2: the Sheet has its own kept 8 too
  await d2.m.api('save', { ...A, s: { st: { cat: [11, 1] } } }); await idle(400);
  d2.hide(); await idle(400); globalThis.document.visibilityState = 'visible';
  eq('and the answers device 2 kept back are still counted once, not lost under the lift', total(), 11);
}
{
  // S1, the real flow: state.js's own logout() 500 ms after the last of 8 answers
  const st = fresh({ login: perPupil });
  R = supabase(st);
  real = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, c => R(c));   // the copy state.js imports keeps this fetch and storage
  const { on, store } = real;
  globalThis.dispatchEvent = () => {}; globalThis.Event = class { constructor(t) { this.type = t; } };
  globalThis.document.documentElement = { classList: { toggle() {} } };
  on();
  S = await import(pathToFileURL(path.join(ROOT, 'js/state.js')).href + '?real');   // with the plain js/api.js it imports
  eq('state.js loads js/api.js in the mode under test', (await import(pathToFileURL(path.join(ROOT, 'js/api.js')).href)).MODE, 'dual');
  for (const wait of [0, 500]) {                                 // logout straight after the last answer, and 500 ms after it
    const b0 = st.batches.reduce((a, b) => a + b.p_events.length, 0), l0 = (st.logouts || []).length;
    eq('sign in through state.js', await S.auth('login', A.c, A.n, A.p), null);
    await idle(400);
    S.mark({ en: 'cat' }, true); await tick(2700);               // the first answer: saved after 2.5 s, the copy sets the base
    for (let i = 0; i < 8; i++) { S.mark({ en: 'cat' }, i % 3 > 0); if (i < 7) await tick(300); }   // a child's taps, 300 ms apart
    await tick(wait);
    const t0 = Date.now();
    eq(`logout() ${wait} ms after the last answer`, await S.logout(), true);
    for (let i = 0; i < 100 && (st.logouts || []).length === l0; i++) await idle(400);
    eq(`S1: logout ${wait} ms after the last of 8 answers: the 8 are copied, then the session is revoked, all within 8 s`, [st.batches.reduce((a, b) => a + b.p_events.length, 0) - b0, (st.logouts || []).length - l0, Date.now() - t0 < 8000, st.seen.lastIndexOf('/auth/v1/logout?scope=local') > st.seen.lastIndexOf('/rest/v1/rpc/record_events')], [8, 1, true, true]);
  }
  check('and nothing of the pupil stays with the adapter', !store.has('wi-sb-base') && !store.has('wi-sb-owner') && !sesOf(store).refresh_token, [...store.keys()]);
}
// ---- 2f. the review of #50: data bound to the pupil, not only operations bound to the session
/** tabs of one browser take turns through navigator.locks (Web Locks) when there is one; without it, the guard alone */
const locks = on => {
  let tail = Promise.resolve();
  const l = { request: (name, o, f) => { if (!f) f = o; const r = tail.then(() => f()); tail = r.catch(() => {}); return r; } };   // request(name[, options], f)
  Object.defineProperty(globalThis, 'navigator', { value: on ? { locks: l } : {}, configurable: true, writable: true });
};
const evCount = (st, w) => new Map(st.batches.flatMap(b => b.p_events.length && b.p_events.some(e => e.item === w) ? [[b.p_batch, b.p_events.filter(e => e.item === w).length]] : [])).values();
const counted = (st, w) => [...evCount(st, w)].reduce((a, b) => a + b, 0);   // each batch id once: the server ignores a repeat
{
  // late_pull (X1): the game's boot pull() waits on a cold Sheet; A logs out, B signs in, then A's answer arrives
  locks(false);
  const g = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  let hold = false;
  const { m, store } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, async c => {
    if (c.url === SHEET && hold && c.body.a === 'login' && c.body.n === 'Testa') { hold = false; await g.p; return { json: { ok: true, s: {} } }; }
    return base(c);
  });
  await m.api('login', A); await m.settled();
  hold = true; const pull = m.api('login', A); await idle(400);
  m.forget(true); await m.settled();
  await m.api('login', Bp); await m.settled();
  g.open(); await pull; await idle(400); await m.settled();
  eq('late_pull: A\'s late Sheet answer after logout signs nobody in and leaves B\'s session alone', [sesOf(store).access_token, st.logins.filter(b => b.name === 'Testa').length, (st.logouts || []).includes('Bearer tok-Probe')], ['tok-Probe', 1, false]);
}
for (const L of [false, true]) {
  // tabs_timer (X2): tab 1 holds A's newest state for the next copy; tab 2 signs B in; tab 1's timer and its
  // pagehide listener fire afterwards
  locks(L);
  const st = fresh({ login: perPupil });
  const route = supabase(st);
  const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 1.5 }, route);
  const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 1.5 }, route, t1);
  await t1.m.api('login', A); await t1.m.settled();
  await t1.m.api('save', { ...A, s: { who: 'A', st: { cat: [1, 0] } } }); await t1.m.settled();
  await t1.m.api('save', { ...A, s: { who: 'A', st: { cat: [4, 0] } } }); await t1.m.settled();   // waits for the timer
  await t2.m.api('login', Bp); await t2.m.settled();
  t1.hide(); globalThis.document.visibilityState = 'visible'; await tick(1800); await idle(400);
  eq(`tabs_timer${L ? ' (with locks)' : ''}: tab 1's timer and pagehide do not send A's state with B's session`,
    t1.calls.filter(c => bearer(c) === 'Bearer tok-Probe' && JSON.stringify(c.body).includes('"who":"A"')).length + st.batches.filter(b => b.p_events.some(e => e.item === 'cat') && t1.calls.some(c => c.body === b && bearer(c) === 'Bearer tok-Probe')).length, 0);
  check('and A\'s state is not left on the device for B', !JSON.stringify([...t1.store.values()]).includes('"who":"A"'), [...t1.store.keys()]);
}
for (const L of [false, true]) {
  // null_sid (X3): both tabs without a session; A signs in from tab 1, B from tab 2, the answers cross
  locks(L);
  const gA = gate(), gB = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  const route = async c => {
    if (c.url.endsWith('/pupil-login')) { const r = base(c); await (c.body.name === 'Testa' ? gA.p : gB.p); return r; }
    return base(c);
  };
  const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route);
  const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route, t1);
  await t1.m.api('login', A); await idle(400);
  await t2.m.api('login', Bp); await idle(400);
  gA.open(); await idle(400);
  gB.open(); await idle(400); await t1.m.settled(); await t2.m.settled();
  await t2.m.api('save', { ...Bp, s: { who: 'B', st: { dog: [1, 0] } } }); await t2.m.settled();
  await t2.m.api('save', { ...Bp, s: { who: 'B', st: { dog: [2, 0] } } }); await t2.m.settled();
  eq(`null_sid${L ? ' (with locks)' : ''}: crossing sign-ins in two tabs: B's saves never go with A's token`,
    t1.calls.filter(c => c.url.includes('/rest/') && JSON.stringify(c.body).includes('"who":"B"')).map(bearer).filter(b => b !== 'Bearer tok-Probe'), []);
  check('the device holds B\'s session, and A\'s session that came too late was ended on the server', sesOf(t1.store).access_token === 'tok-Probe' && (st.logouts || []).includes('Bearer tok-Testa'), [sesOf(t1.store).access_token, st.logouts]);
}
{
  // close_tab (S-a): one device; answers 1.5 s apart are held for the next copy, the tab is closed and the hide-time
  // copy does not make it; the pupil opens the game again
  locks(false);
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  let rec = {};
  const route = c => { if (c.url === SHEET) { if (c.body.a === 'save') rec = c.body.s; return { json: c.body.a === 'login' ? { ok: true, s: rec } : { ok: true } }; } return base(c); };
  const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, route);
  await t1.m.api('login', A); await t1.m.settled();
  for (let i = 1; i <= 9; i++) { await t1.m.api('save', { ...A, s: { st: { cat: [i, 0] } } }); await t1.m.settled(); }
  const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, route, t1);   // the same storage, a new page
  await t2.m.api('login', A); await t2.m.settled();
  await t2.m.api('save', { ...A, s: { st: { cat: [9, 0] } } }); await t2.m.settled();
  t2.hide(); globalThis.document.visibilityState = 'visible'; await idle(400); await t2.m.settled();
  eq('close_tab: the tab closed before its copy; at the next visit all 9 answers are counted once', counted(st, 'cat'), 9);
}
{
  // lift_order: a pull's answer is handled while the copy of an earlier save is still running; the Sheet already
  // holds this device's newer save
  locks(false);
  const g = gate();
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  let rec = {};
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, async c => {
    if (c.url === SHEET) { if (c.body.a === 'save') rec = c.body.s; return { json: c.body.a === 'login' ? { ok: true, s: rec } : { ok: true } }; }
    if (c.url.endsWith('/rpc/save_progress') && c.body.p_state.st.cat[0] === 2) { const r = base(c); await g.p; return r; }
    return base(c);
  });
  await m.api('login', A); await m.settled();
  await m.api('save', { ...A, s: { st: { cat: [1, 0] } } }); await m.settled();
  await m.api('save', { ...A, s: { st: { cat: [2, 0] } } }); await idle(400);     // its copy is slow
  await m.api('save', { ...A, s: { st: { cat: [5, 0] } } }); await idle(400);     // the Sheet takes 5; the copy waits
  await m.api('login', A); await idle(400);                                       // a pull: the Sheet has this device's 5
  g.open(); await idle(400); await m.settled();
  eq('lift_order: this device\'s own answers are not lifted away by a pull that overtook their copy', counted(st, 'cat'), 5);
}
for (const L of [false, true]) {
  // same_pupil_tabs (S-b): one pupil in two tabs; tab 1's copy is slow, tab 2 copies twice meanwhile
  locks(L);
  const g = gate();
  const st = fresh({ login: perPupil, sheet: { ok: true, s: {} } });
  const base = supabase(st);
  let slow = false;
  const route = async c => {
    if (c.url.endsWith('/rpc/record_events') && slow && c.body.p_events.some(e => e.item === 'cat')) { slow = false; const r = base(c); await g.p; return r; }
    return base(c);
  };
  const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route);
  const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route, t1);
  await t1.m.api('login', { ...A }); await t1.m.settled();
  await t2.m.api('login', { ...A }); await t2.m.settled();
  await t1.m.api('save', { ...A, s: { st: { pre: [1, 0] } } }); await t1.m.settled();             // a first copy: the base is set
  slow = true;
  await t1.m.api('save', { ...A, s: { st: { pre: [1, 0], cat: [3, 0] } } }); await idle(400);         // 3 answers in tab 1, the copy is slow
  await t2.m.api('save', { ...A, s: { st: { dog: [2, 0] } } }); await idle(400);                    // 2 in tab 2
  await t2.m.api('save', { ...A, s: { st: { dog: [2, 0], sun: [1, 0] } } }); await idle(400);       // 1 more in tab 2
  g.open(); await idle(400); await t1.m.settled(); await t2.m.settled();
  await t2.m.api('save', { ...A, s: { st: { dog: [2, 0], sun: [1, 0] } } }); await t2.m.settled();  // tab 2 saves again
  await t1.m.api('save', { ...A, s: { st: { pre: [1, 0], cat: [4, 0] } } }); await t1.m.settled(); // 1 more in tab 1
  eq(`same_pupil_tabs${L ? ' (with locks)' : ''}: every answer counted once (cat 4, dog 2, sun 1)`, [counted(st, 'cat'), counted(st, 'dog'), counted(st, 'sun')], [4, 2, 1]);
}
locks(false);
// ---- 2g. the review of #55: counting (an object handed over is not ours; a save sent is mine before it is answered)
{
  // alias (G1): the game keeps the Sheet's answer and plays into it in place (S.st is r.s.st) before the copy runs
  locks(false);
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, c => c.url === SHEET ? { json: c.body.a === 'login' ? { ok: true, s: { st: { cat: [2, 0] } } } : { ok: true } } : base(c));
  const r = await m.api('login', A);
  r.s.st.cat = [4, 1];                                         // 2 answers played into the very object the Sheet answered
  await idle();
  await m.api('save', { ...A, s: { st: { cat: [4, 1] } } }); await idle();
  eq('alias: answers the game played into the Sheet\'s answer are counted (2)', counted(st, 'cat'), 2);
}
{
  // aba with latency (G1), the real flow through js/state.js: A, then B, then A again on one device; Supabase answers
  // in 200 ms, so each sign-in's copy waits behind the last logout while the child is already playing
  const st = fresh({ login: perPupil });
  const rec = {}, base = supabase(st);
  const pupilOf = new Map([['Bearer tok-Testa', 'A'], ['Bearer tok-Probe', 'B']]);
  const byPupil = { A: new Map(), B: new Map() };
  R = async c => {
    if (c.url === SHEET) { const n = c.body.n; if (c.body.a === 'save') rec[n] = JSON.parse(JSON.stringify(c.body.s)); return { json: c.body.a === 'save' ? { ok: true } : { ok: true, s: JSON.parse(JSON.stringify(rec[n] || {})) } }; }
    await tick(200);
    if (c.url.endsWith('/rpc/record_events')) { const who = pupilOf.get(bearer(c)); if (who) byPupil[who].set(c.body.p_batch, c.body.p_events.length); }
    return base(c);
  };
  real.on();
  const play = async (P, n, word) => {
    eq(`aba: ${P.n} signs in`, await S.auth('login', P.c, P.n, P.p), null);
    for (let i = 0; i < n; i++) { S.mark({ en: word }, true); await tick(300); }
    await tick(2700);                                          // the game's save after 2.5 s
    eq(`aba: ${P.n} logs out`, await S.logout(), true);
  };
  await play(A, 2, 'cat'); await play(Bp, 1, 'dog'); await play(A, 2, 'cat');
  await tick(1500); await idle();
  const sum = mp => [...mp.values()].reduce((a, b) => a + b, 0);
  eq('aba with latency: A\'s 4 answers and B\'s 1 are each counted once, by the right account', [sum(byPupil.A), sum(byPupil.B)], [4, 1]);
}
{
  // close_no_ack (G2): taps 1.5 s apart, the Sheet takes every save but its answers never come back: the tab closes first
  locks(false);
  const st = fresh({ login: perPupil });
  const base = supabase(st);
  let rec = {}, answer = true;
  const route = c => {
    if (c.url !== SHEET) return base(c);
    if (c.body.a === 'save') { rec = JSON.parse(JSON.stringify(c.body.s)); if (!answer) return new Promise(() => {}); }
    return { json: c.body.a === 'login' ? { ok: true, s: JSON.parse(JSON.stringify(rec)) } : { ok: true } };
  };
  const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, route);
  await t1.m.api('login', A); await idle();
  await t1.m.api('save', { ...A, s: { st: { cat: [1, 0] } } }); await idle();   // answered and copied
  answer = false;
  for (let i = 2; i <= 10; i++) { t1.m.api('save', { ...A, s: { st: { cat: [i, 0] } } }); await tick(20); }   // sent, never answered
  await idle(400);
  const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, route, t1);   // the tab was closed; a new page
  answer = true;
  await t2.m.api('login', A); await idle();
  await t2.m.api('save', { ...A, s: { st: { cat: [10, 0] } } }); await idle();
  t2.hide(); globalThis.document.visibilityState = 'visible'; await idle();
  eq('close_no_ack: saves sent but never answered before the tab closed are still counted once (10 of 10)', counted(st, 'cat'), 10);
}
{
  // logout_backlog (G3): 750 answers waiting when the pupil logs out
  locks(false);
  const st = fresh({ login: perPupil, sheet: { ok: true, s: {} } });
  const { m, calls } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, supabase(st));
  await m.api('login', A); await idle();
  await m.api('save', { ...A, s: { st: { pre: [1, 0] } } }); await idle();
  await m.api('save', { ...A, s: { st: { pre: [1, 0], cat: [450, 0], dog: [300, 0] } } }); await idle();   // held
  const k0 = calls.length;
  m.forget(true); await idle();
  eq('logout_backlog: a 750-answer backlog is copied whole at logout, then the session is revoked', [counted(st, 'cat'), counted(st, 'dog'), (st.logouts || []).length], [450, 300, 1]);
  check('a logout is not a closing page: no keepalive, so no 64 KiB cut', calls.slice(k0).every(c => !c.init.keepalive));
}
{
  // fight (G4): two tabs, two pupils, saving in turn. The tab whose pupil lost the device stops copying and reloads.
  for (const L of [false, true]) {
    locks(L); reloads = 0;
    const st = fresh({ login: perPupil, sheet: { ok: true, s: {} } });
    const route = supabase(st);
    const t1 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route);
    const t2 = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, route, t1);
    await t1.m.api('login', A); await idle();
    await t2.m.api('login', Bp); await idle();
    for (let i = 1; i <= 8; i++) {
      await t1.m.api('save', { ...A, s: { st: { cat: [i, 0] } } }); await idle(400);
      await t2.m.api('save', { ...Bp, s: { st: { dog: [i, 0] } } }); await idle(400);
    }
    eq(`fight${L ? ' (with locks)' : ''}: two sign-ins in all, not a stream; tab 1 reloads once; B's 8 answers counted`, [st.logins.length, reloads, counted(st, 'dog')], [2, 1, 8]);
  }
  locks(false);
}
{
  // a sign-in paused for the address ('locked') is tried again after its wait, not only tomorrow (G4)
  const st = fresh({ login: { ok: false, e: 'locked', wait: 90 } });
  const { m, store } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  await m.api('login', A); await idle();
  const nf = JSON.parse(store.get('wi-sb-netfail') || 'null');
  eq('locked: no day-long stop, a pause of at least 10 minutes', [store.has('wi-sb-stop'), !!nf && nf.ms === 90000], [false, true]);
}
{
  // the 64 KiB keepalive budget of a page being hidden: what does not fit waits for the next visit, nothing is cut
  locks(false);
  const st = fresh({ login: perPupil, sheet: { ok: true, s: {} } });
  const { m, calls, hide } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 600 }, supabase(st));
  await m.api('login', A); await m.settled();
  await m.api('save', { ...A, s: { st: { pre: [1, 0] } } }); await m.settled();
  await m.api('save', { ...A, s: { st: { pre: [1, 0], cat: [450, 0], dog: [300, 0] } } }); await m.settled();   // held: inside the 600 s
  hide(); await idle(400); await m.settled(); globalThis.document.visibilityState = 'visible';
  const kept = calls.filter(c => c.init.keepalive).reduce((a, c) => a + (c.init.body || '').length, 0);
  check('hide time: the keepalive requests stay inside 64 KiB together', kept > 0 && kept <= 65536, kept);
  await m.api('save', { ...A, s: { st: { pre: [1, 0], cat: [450, 0], dog: [300, 0] } } }); hide(); await idle(400); await m.settled();
  globalThis.document.visibilityState = 'visible';
  await m.api('save', { ...A, s: { st: { pre: [1, 0], cat: [450, 0], dog: [300, 0] } } }); hide(); await idle(400); await m.settled();
  globalThis.document.visibilityState = 'visible';
  eq('and the rest goes at the next hide, each answer once (1 + 450 + 300)', [counted(st, 'pre'), counted(st, 'cat'), counted(st, 'dog')], [1, 450, 300]);
}
locks(false);
{
  // the guard itself: no code path writes the device's session, base, batch, stale record or queue, or reads the token,
  // except through op() (or keep() and signOut(), which only op calls, and note(), the device log)
  const src = fs.readFileSync(path.join(ROOT, 'js/api.js'), 'utf8');
  const cut = (text, head) => { const i = text.indexOf(head); if (i < 0) return text; let d = 0, j = text.indexOf('{', i); for (; j < text.length; j++) { if (text[j] === '{') d++; else if (text[j] === '}' && --d === 0) break; } return text.slice(0, i) + text.slice(j + 1); };
  let rest = src;
  for (const h of ['function op(', 'function keep(', 'function signOut(', 'function note(']) rest = cut(rest, h);
  rest = rest.replace(/^const set=.*$/m, '');
  eq('the one guard: no raw storage write outside op(), keep(), signOut(), note()', rest.match(/(^|[^.\w])set\(/gm), null);
  eq('no access token read outside op()', rest.match(/access_token|refresh_token/g), null);
  eq('the queue is written only through op() (and emptied by signOut)', rest.match(/(^|[^\w.])queued=(?!null,qOverwrite)/gm), null);
  eq('the dead rpc() is gone', /async function rpc\(/.test(src), false);
}

// ---- 3. events from two saves
{
  const { m } = await load(undefined, sheetOk);
  const ev = m.events(
    { st: { cat: [2, 1], sun: [1, 0] }, g: { st: { 'i1-quiz': 2 } }, m: { st: { 'bay-1': 1 } }, read: { t1: 2 }, k: { reads: 0 }, x: { tries: [{ at: 1, total: [5, 10] }] } },
    { st: { cat: [5, 2], sun: [1, 0], hat: 'junk', dog: [1, 9] }, g: { st: { 'i1-quiz': 3, 'i2-quiz': 1, bad: 'x' } }, m: { st: { 'bay-1': 1, 'bay-2': 7 } }, read: { t1: 4, t2: 1 }, k: { reads: 1 }, x: { tries: [{ at: 1, total: [5, 10] }, { at: 2, total: [8, 10] }] } });
  eq('answers: 3 new tries on "cat", one of them not at the first try; "dog" 1 try (wrong can never exceed tries)',
    ev.filter(e => e.type === 'answer').map(e => e.item + (e.first_try ? '+' : '-')).sort(), ['cat+', 'cat+', 'cat-', 'dog-']);
  eq('levels: only stars that went up, never more than 3', ev.filter(e => e.type === 'level').map(e => [e.game, e.level, e.stars]), [['en', 'i1-quiz', 3], ['en', 'i2-quiz', 1], ['math', 'bay-2', 3]]);
  eq('a text is reported when the count of perfect texts went up', ev.filter(e => e.type === 'read').map(e => e.text), ['t1', 't2']);
  eq('a finished exam paper is reported once', ev.filter(e => e.type === 'exam'), [{ type: 'exam', paper: 'mock', right: 8 }]);
  eq('no event carries points', ev.some(e => 'pts' in e || 'points' in e), false);
  eq('the same record twice: nothing', m.events({ st: { cat: [1, 0] } }, { st: { cat: [1, 0] } }), []);
  eq('garbage in, nothing out', [m.events(null, null), m.events('x', 5), m.events({ st: 5 }, { st: [1] })], [[], [], []]);
  eq('a counter that jumped absurdly is capped (600 answers a word, the server\'s own daily ceiling)', m.events({}, { st: { cat: [100000, 0] } }).length, 600);
  eq('and 4,000 events at most for one save', m.events({}, { st: Object.fromEntries(Array.from({ length: 10 }, (_, i) => ['w' + i, [1000, 0]])) }).length, 4000);
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
