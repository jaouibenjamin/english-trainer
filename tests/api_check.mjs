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
const check = (label, ok, detail = '') => { ok ? pass++ : fail++; console.log((ok ? 'PASS ' : 'FAIL ') + label + (ok ? '' : '   <- ' + String(detail).slice(0, 300))); };
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want), `got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
const tick = (ms = 30) => new Promise(r => setTimeout(r, ms));

const SHEET = 'https://script.example/macros/s/TEST/exec', SB = 'https://abcdefghijklmnop.supabase.co', KEY = 'public-key-for-tests-0123456789';
let n = 0;
/** a fresh copy of the module under a given config, with fetch and localStorage replaced */
async function load(backend, route) {
  const calls = [], store = new Map(), listeners = [];
  globalThis.window = globalThis;
  globalThis.addEventListener = (t, f) => listeners.push([t, f]);
  globalThis.document = { visibilityState: 'visible', addEventListener: (t, f) => listeners.push([t, f]) };
  globalThis.API_URL = '  ' + SHEET + ' ';
  if (backend === undefined) delete globalThis.BACKEND; else globalThis.BACKEND = backend;
  globalThis.localStorage = { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) };
  globalThis.fetch = async (url, init = {}) => {
    const c = { url: String(url), init, body: init.body ? JSON.parse(init.body) : null, at: calls.length };
    calls.push(c);
    const r = await route(c);
    if (r instanceof Error) throw r;
    return { ok: (r.status || 200) < 400, status: r.status || 200, json: async () => { if (r.badJson) throw new SyntaxError('Unexpected token <'); return r.json; } };
  };
  const m = await import(pathToFileURL(path.join(ROOT, 'js/api.js')).href + '?v=' + (++n));
  return { m, calls, store, listeners, hide: () => { globalThis.document.visibilityState = 'hidden'; for (const [t, f] of listeners) if (t === 'visibilitychange') f(); } };
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
  check('js/state.js gets api() from the adapter and still exports it', /import \{api\} from '\.\/api\.js';export \{api\};/.test(src) && !/fetch\(API,/.test(src));
}

// ---- 2. dual write
const CRED = { c: 'EN-0000', n: 'נועה', p: '4827' };
const ses = at => ({ ok: true, session: { access_token: 'acc1', refresh_token: 'ref1', expires_at: Math.floor(Date.now() / 1000) + 3600 }, device_token: 'd'.repeat(43), updated_at: at, s: {} });
function supabase(state) {   // a tiny stand-in for the project: sign-in, save_progress, record_events
  return c => {
    if (c.url === SHEET) return { json: state.sheet ?? { ok: true } };
    state.seen.push(c.url.replace(SB, ''));
    if (state.down) return state.down === 'throw' ? new Error('down') : { status: 500, json: null };
    if (c.url.endsWith('/functions/v1/pupil-login')) { state.logins.push(c.body); return { json: state.login ?? ses('t0') }; }
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
  const r = await m.api('login', CRED); await tick();
  eq('dual login: the answer is the Sheet\'s', r, { ok: true, s: { pts: 1 } });
  eq('dual login: the Sheet was asked first, then the shadow sign-in', [calls[0].url, st.seen], [SHEET, ['/functions/v1/pupil-login']]);
  eq('the shadow sign-in sends class code, name and code and nothing else', st.logins[0], { class_code: 'EN-0000', name: 'נועה', code: '4827' });
  st.sheet = { ok: true };
  await m.api('save', { ...CRED, s: { pts: 10, st: { cat: [1, 0] } } }); await tick();
  eq('first save on a device: the blob is copied, no events yet (nothing to compare with)', [st.saves.length, st.batches.length], [1, 0]);
  await m.api('save', { ...CRED, s: { pts: 34, st: { cat: [2, 0], dog: [1, 1] } } }); await tick();
  eq('second save: the difference goes as events', st.batches[0].p_events.map(e => [e.item, e.first_try]), [['cat', true], ['dog', false]]);
  check('saves go with the session, never with the code', calls.filter(c => c.url.includes('/rest/')).every(c => c.init.headers.authorization === 'Bearer acc1' && !JSON.stringify(c.body).includes('4827')));
  const all = [...store.entries()].map(([k, v]) => k + v).join('|');
  check('nothing kept on the device by the adapter holds the code or the name', !all.includes('4827') && !all.includes('נועה'), all.slice(0, 200));
  check('the shadow log has numbers only', m.shadowLog().length >= 3 && !JSON.stringify(m.shadowLog()).includes('נועה') && m.shadowLog().some(l => l.k === 'save' && l.server === 30) && m.shadowLog().some(l => l.k === 'sheet' && l.pts === 34), JSON.stringify(m.shadowLog()));
  for (const a of ['board', 'teacher', 'reset']) { const before = st.seen.length; await m.api(a, CRED); await tick(); eq(`dual ${a}: the Sheet only`, st.seen.length, before); }
  m.signOut();
  check('sign out: the session is removed from this device, the device token stays', !store.get('wi-sb-session').includes('ref1') && store.get('wi-sb-session').includes('ddd'));
}
for (const down of ['throw', 500]) {
  const st = fresh({ down, sheet: { ok: true, s: { pts: 3 } } });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  const t0 = Date.now();
  const r1 = await m.api('login', CRED), r2 = await m.api('save', { ...CRED, s: { pts: 3 } });
  eq(`dual, Supabase ${down === 'throw' ? 'unreachable' : 'answering 500'}: the pupil gets the Sheet's answers`, [r1, r2], [{ ok: true, s: { pts: 3 } }, { ok: true, s: { pts: 3 } }]);
  check('and does not wait for it', Date.now() - t0 < 200);
  await tick();
}
{
  const st = fresh({ sheet: { ok: false, e: 'pin' } });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  const r = await m.api('save', { ...CRED, s: { pts: 3 } }); await tick();
  eq('dual: a save the Sheet refuses is not copied', [r, st.seen], [{ ok: false, e: 'pin' }, []]);
  st.sheet = new Error('offline');
  const x = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, c => c.url === SHEET ? new Error('offline') : supabase(st)(c));
  let threw = false; try { await x.m.api('save', CRED); } catch (e) { threw = true; }
  check('dual: a Sheet network failure is thrown exactly as in sheet mode, and nothing is copied', threw && st.seen.length === 0);
}
{
  const st = fresh({ loseAnswer: 1 });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  await m.api('login', CRED); await tick();
  await m.api('save', { ...CRED, s: { st: { cat: [1, 0] } } }); await tick();
  await m.api('save', { ...CRED, s: { st: { cat: [3, 0] } } }); await tick();    // the server takes it, the answer is lost
  await m.api('save', { ...CRED, s: { st: { cat: [4, 0] } } }); await tick();    // the same batch must go again first
  await m.api('save', { ...CRED, s: { st: { cat: [4, 0] } } }); await tick();
  eq('a batch whose answer was lost is sent again under the same id (the server counts it once)', [st.batches.length >= 2, st.batches[0].p_batch === st.batches[1].p_batch, st.batches[1].p_events.length], [true, true, 2]);
  await m.api('save', { ...CRED, s: { st: { cat: [5, 0] } } }); await tick();
  const last = st.batches[st.batches.length - 1];
  eq('afterwards only what is new since the last batch the server took, under a new id', [last.p_events.length, last.p_batch !== st.batches[0].p_batch], [1, true]);
  eq('in total every answer was put in a batch exactly once', [...new Map(st.batches.map(b => [b.p_batch, b.p_events.length])).values()].reduce((a, b) => a + b, 0), 4);
}
{
  const st = fresh({ conflict: 1 });
  const { m } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st));
  await m.api('login', CRED); await tick();
  await m.api('save', { ...CRED, s: { pts: 1 } }); await tick();
  eq('shadow: when another device saved first the copy is written again over the version the server named (the Sheet is the truth)', st.saves.map(s => s.p_base), ['t0', 't9']);
  const st2 = fresh({ login: { ok: false, e: 'pin' } });
  const y = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0 }, supabase(st2));
  for (let i = 0; i < 5; i++) { await y.m.api('save', { ...CRED, s: { pts: i } }); await tick(); }
  eq('a pupil the shadow side does not know yet: one sign-in try, not one per save', st2.logins.length, 1);
}

// ---- 2b. pacing (review S8): the newest state, at most every saveEveryS, at once when the page is hidden; "wait" and
// "daycap" keep it and try again
{
  const { listeners } = await load(undefined, sheetOk);
  eq('sheet mode registers nothing on the page', listeners.length, 0);
}
{
  const st = fresh();
  const { m, hide, calls } = await load({ mode: 'dual', url: SB, key: KEY, saveEveryS: 0.3 }, supabase(st));
  await m.api('login', CRED); await tick();
  for (let i = 1; i <= 6; i++) { await m.api('save', { ...CRED, s: { pts: i, st: { cat: [i, 0] } } }); await tick(20); }
  eq('6 saves of the game inside 0.3 s: one copy now', st.saves.length, 1);
  await tick(400);
  eq('and one more when the time is up, with the newest state only', [st.saves.length, st.saves[1].p_state.pts], [2, 6]);
  eq('every answer still went in a batch exactly once', st.batches.reduce((a, b) => a + b.p_events.length, 0), 5);
  await m.api('save', { ...CRED, s: { pts: 7, st: { cat: [7, 0] } } }); await tick();
  eq('a save right after a copy waits', st.saves.length, 2);
  hide(); await tick();
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
  await m.api('login', CRED); await tick();
  await m.api('save', { ...CRED, s: { pts: 1 } }); await tick();
  eq('the server says wait 1 s: nothing more is sent before that', st.saves.length, 1);
  await m.api('save', { ...CRED, s: { pts: 2 } }); await tick();
  eq('not even for a newer save', st.saves.length, 1);
  await tick(1100);
  eq('after it, the newest state goes', [st.saves.length, st.saves[1].p_state.pts], [2, 2]);
  answer = { ok: false, e: 'daycap', retry_after: 3600 };
  await m.api('save', { ...CRED, s: { pts: 3 } }); await tick();
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
  await m.api('login', CRED); await tick();
  await m.api('save', { ...CRED, s: { st: { cat: [1, 0] } } }); await tick();
  await m.api('save', { ...CRED, s: { st: { cat: [2, 0] } } }); await tick();
  eq('the storage brake: the batch is refused and kept on the device', [st.batches.length, m.shadowLog().some(l => l.k === 'brake')], [1, true]);
}
{
  const st = fresh();
  const { m } = await load({ mode: 'supabase', url: SB, key: KEY, saveEveryS: 0.3 }, supabase(st));
  await m.api('login', CRED); await tick();
  const r1 = await m.api('save', { ...CRED, s: { pts: 1 } });
  const r2 = await m.api('save', { ...CRED, s: { pts: 2 } });
  eq("'supabase': the first save goes, the next one inside 0.3 s is kept and the game hears ok", [r1, r2, st.saves.length], [{ ok: true }, { ok: true }, 1]);
  st.conflict = 1;
  await tick(400);
  eq('the kept save meets another device\'s version', st.saves.length, 2);
  const r3 = await m.api('save', { ...CRED, s: { pts: 3 } });
  eq('the next save of the game is told to join (stale, with the server\'s state)', [r3.ok, r3.e], [false, 'stale']);
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
  eq('a counter that jumped is capped (at most 50 answers an item per save, 200 events a save)', m.events({}, { st: { cat: [100000, 0] } }).length, 50);
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
