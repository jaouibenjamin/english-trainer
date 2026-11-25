/**
 * @OnlyCurrentDoc
 * (the line above limits this script to the one spreadsheet it lives in, instead of all your Google Sheets)
 *
 * English Trainer backend. Lives inside a Google Sheet (Extensions > Apps Script).
 * 1. Run setup() once.  2. Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
 * The sheet holds first names, salted PIN hashes and scores. Nothing here is stored in the GitHub repo.
 * Class list: write the pupils' first names in column A of the `roster` tab (from row 2). Once it holds at least one name,
 * only those names can register. Left empty, anyone with the class code can register any name.
 */
const KIDS = 'kids', CFG = 'config', ROSTER = 'roster', MAX_KIDS = 60, TEACHER_TRIES = 10, MAX_FAILS = 5, LOCK_MS = 5 * 60000;
const HEAD = ['name', 'salt', 'hash', 'points', 'words', 'reads', 'streak', 'lastDay', 'fails', 'lockUntil', 'state', 'updated'];
const NAME_RE = /^[\p{L}\p{M}'’״׳ .\-]{2,20}$/u;

function setup() {
  const ss = SpreadsheetApp.getActive();
  const c = ss.getSheetByName(CFG) || ss.insertSheet(CFG);
  if (!c.getRange('B1').getValue()) {
    c.getRange(1, 1, 2, 2).setValues([['class code', 'EN-' + digits(4)], ['teacher code', digits(6)]]);
  }
  const k = ss.getSheetByName(KIDS) || ss.insertSheet(KIDS);
  if (k.getLastRow() === 0) k.appendRow(HEAD);
  k.getRange('A:C').setNumberFormat('@');
  k.getRange('H:H').setNumberFormat('@');
  k.getRange('K:K').setNumberFormat('@');
  roster(ss);
}

/* the class list tab; made on first use so an older sheet gets it without running setup() again */
function roster(ss) {
  let r = ss.getSheetByName(ROSTER);
  if (!r) { r = ss.insertSheet(ROSTER); r.getRange(1, 1, 1, 1).setValues([['name']]); }
  const last = r.getLastRow();
  if (last < 2) return [];
  return r.getRange(2, 1, last - 1, 1).getValues().map(function (x) { return String(x[0] || '').trim().replace(/\s+/g, ' '); }).filter(String);
}

function digits(n) { let s = ''; for (let i = 0; i < n; i++) s += Math.floor(Math.random() * 10); return s; }
function norm(x) { return String(x || '').trim().toUpperCase(); }
function num(x, max) { x = Math.floor(Number(x)); return x > 0 ? Math.min(x, max) : 0; }
function parse(x) { try { return JSON.parse(String(x || '{}')) || {}; } catch (e) { return {}; } }
function dayStr(v) { return v instanceof Date ? v.getFullYear() + '-' + (v.getMonth() + 1) + '-' + v.getDate() : String(v || ''); }
function hash(salt, pin) {
  const b = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, salt + ':' + pin, Utilities.Charset.UTF_8);
  return b.map(function (x) { return ((x + 256) % 256).toString(16).padStart(2, '0'); }).join('');
}

function doGet() { return out({ ok: true, service: 'english-trainer' }); }
function doPost(e) {
  let d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return out({ ok: false, e: 'input' }); }
  const lock = LockService.getScriptLock();
  try { lock.waitLock(15000); } catch (err) { return out({ ok: false, e: 'busy' }); }
  try { return out(handle(d)); } catch (err) { return out({ ok: false, e: 'server' }); } finally { lock.releaseLock(); }
}
function out(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

function handle(d) {
  const ss = SpreadsheetApp.getActive();
  const cs = ss.getSheetByName(CFG), ks = ss.getSheetByName(KIDS);
  if (!cs || !ks) return { ok: false, e: 'setup' };
  const cfg = cs.getRange(1, 1, 2, 2).getValues();
  const classCode = String(cfg[0][1]).trim(), teacherCode = String(cfg[1][1]).trim();
  if (!classCode || norm(d.c) !== norm(classCode)) return { ok: false, e: 'class' };
  const last = ks.getLastRow();
  const rows = last > 1 ? ks.getRange(2, 1, last - 1, HEAD.length).getValues() : [];

  if (d.a === 'teacher' || d.a === 'reset') {
    // the teacher code opens every pupil's record, so guessing is slowed down: 10 wrong codes close the door for 5 minutes (the same wait the pupils get)
    const guard = cs.getRange(2, 3, 1, 2), gv = guard.getValues()[0], now = Date.now();
    if (Number(gv[1]) > now) return { ok: false, e: 'locked' };
    if (!teacherCode || String(d.t || '').trim() !== teacherCode) {
      const f = (Number(gv[0]) || 0) + 1;
      guard.setValues([f >= TEACHER_TRIES ? [0, now + 5 * 60000] : [f, 0]]);
      return { ok: false, e: 'teacher' };
    }
    if (Number(gv[0])) guard.setValues([[0, 0]]);
    if (d.a === 'reset') {
      /* a pupil forgot the secret code: the teacher (or the parent, by clearing the hash cell in column C) resets it.
         The next sign-in with that name and any 4 digits makes those digits the new code. Progress stays. */
      const rn = String(d.n || '').trim().replace(/\s+/g, ' '), ri = rows.findIndex(function (r) { return String(r[0]) === rn; });
      if (ri < 0) return { ok: false, e: 'nouser' };
      ks.getRange(ri + 2, 2, 1, 2).setValues([['', '']]);
      ks.getRange(ri + 2, 9, 1, 2).setValues([[0, 0]]);
      return { ok: true };
    }
    return teacherView(rows);
  }

  const name = String(d.n || '').trim().replace(/\s+/g, ' '), pin = String(d.p || '');
  if (!NAME_RE.test(name) || !/^\d{4}$/.test(pin)) return { ok: false, e: 'input' };
  const i = rows.findIndex(function (r) { return String(r[0]) === name; });

  if (d.a === 'register') {
    if (i >= 0) return { ok: false, e: 'taken' };
    const list = roster(ss);
    if (list.length && list.indexOf(name) < 0) return { ok: false, e: 'roster' };
    if (rows.length >= MAX_KIDS) return { ok: false, e: 'full' };
    const salt = Utilities.getUuid();
    ks.appendRow([name, salt, hash(salt, pin), 0, 0, 0, 0, '', 0, 0, '{}', new Date()]);
    return { ok: true, s: {} };
  }
  if (i < 0) return { ok: false, e: 'nouser' };

  const r = rows[i], rowNo = i + 2, now = Date.now();
  /* code reset (the hash cell is empty): signing in sets the new code. A device still signed in with the old code is asked to sign in again. */
  if (!String(r[2]).trim()) {
    if (d.a !== 'login') return { ok: false, e: 'pin' };
    const salt = Utilities.getUuid();
    ks.getRange(rowNo, 2, 1, 2).setValues([[salt, hash(salt, pin)]]);
    ks.getRange(rowNo, 9, 1, 2).setValues([[0, 0]]);
    return { ok: true, s: parse(r[10]), newpin: true };
  }
  if (Number(r[9]) > now) return { ok: false, e: 'locked' };
  if (hash(String(r[1]), pin) !== String(r[2])) {
    const f = Number(r[8]) + 1;
    ks.getRange(rowNo, 9, 1, 2).setValues([f >= MAX_FAILS ? [0, now + LOCK_MS] : [f, 0]]);
    return { ok: false, e: 'pin' };
  }
  if (Number(r[8])) ks.getRange(rowNo, 9, 1, 2).setValues([[0, 0]]);

  if (d.a === 'login') return { ok: true, s: parse(r[10]) };
  if (d.a === 'save') {
    const s = d.s || {}, js = JSON.stringify(s), k = s.k || {};
    if (js.length > 30000) return { ok: false, e: 'big' };
    ks.getRange(rowNo, 4, 1, 5).setValues([[num(s.pts, 1e6), num(k.words, 200), num(k.reads, 50), num(s.streak, 400), String(s.day || '').slice(0, 10)]]);
    ks.getRange(rowNo, 11, 1, 2).setValues([[js, new Date()]]);
    return { ok: true };
  }
  if (d.a === 'board') {
    return { ok: true, rows: rows.map(function (x) { return { n: String(x[0]), pts: Number(x[3]) || 0, words: Number(x[4]) || 0, streak: Number(x[6]) || 0 }; })
      .sort(function (a, b) { return b.pts - a.pts; }) };
  }
  return { ok: false, e: 'action' };
}

/* The mock exam for the teacher screen, read from what the pupil's record already holds (x.tries; nothing new is
   saved and the sheet is not written): how many papers (of the last 20 the device keeps), the oldest and the last
   total among them, and the last paper by skill. null = no paper yet. The record is written by the pupil's own
   browser, so anything in it may be damaged or made up: every value is read with nv() and clamped, and an error in
   one record gives null, never an error for the whole teacher screen. */
/* a number from pupil-written JSON. Number() of an object such as {"toString":1} throws, so only real numbers and strings are read */
function nv(v) { return typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN; }
function mockOf(x) {
  try {
    const int = function (v) { v = Math.floor(nv(v)); return v > 0 ? Math.min(v, 999) : 0; };
    const pair = function (p) { const b = int(p[1]); return [Math.min(int(p[0]), b), b]; };
    const t = x && Array.isArray(x.tries) ? x.tries.filter(function (r) { return r && Array.isArray(r.total) && int(r.total[1]) > 0; }) : [];
    if (!t.length) return null;
    const last = t[t.length - 1], sc = {};
    ['words', 'grammar', 'reading', 'writing'].forEach(function (k) {
      const p = last.sc && last.sc[k];
      if (Array.isArray(p) && int(p[1]) > 0) sc[k] = pair(p);
    });
    return { n: Math.min(t.length, 99), first: pair(t[0].total), last: pair(last.total), sc: sc };
  } catch (e) { return null; }   // one record must never take the whole teacher screen down
}

/* A key of the class's hard-words list: written by the pupil's own browser, so only something that looks like an
   English word or short phrase is counted there (letters, spaces, apostrophes, hyphens; at most 40 characters). */
function wordKey(w) { return typeof w === 'string' && /^[A-Za-z][A-Za-z' -]{0,39}$/.test(w); }
function teacherView(rows) {
  const agg = Object.create(null);   // no inherited keys: a pupil's "__proto__" or "constructor" is just another key, and is not a word
  const kids = rows.map(function (x) {
    const state = parse(x[10]), st = state.st || {}, lv = (state.g && state.g.st) || {};
    let tries = 0, miss = 0, stars = 0, levels = 0;
    Object.keys(st).forEach(function (w) {
      if (!Array.isArray(st[w])) return;   // one damaged record must not take the whole screen down
      const t = nv(st[w][0]) || 0, m = nv(st[w][1]) || 0;   // nv(): Number() of a pupil-written object can throw
      tries += t; miss += m;
      if (!wordKey(w)) return;   // the pupil's own counts above still include it; the class list does not
      const a = agg[w] || (agg[w] = [0, 0]);
      a[0] += t; a[1] += m;
    });
    Object.keys(lv).forEach(function (k) { const v = Math.min(3, Math.floor(nv(lv[k]) || 0)); if (v > 0) { stars += v; levels++; } });
    return { n: String(x[0]), pts: Number(x[3]) || 0, words: Number(x[4]) || 0, reads: Number(x[5]) || 0, streak: Number(x[6]) || 0, day: dayStr(x[7]),
      stars: stars, levels: levels, tries: tries, miss: miss, mock: mockOf(state.x) };
  }).sort(function (a, b) { return b.stars - a.stars || b.words - a.words; });
  const hard = Object.keys(agg).filter(function (w) { return agg[w][0] >= 3 && agg[w][1] > 0; })
    .map(function (w) { return [w, Math.min(100, Math.round(agg[w][1] / agg[w][0] * 100)), agg[w][0]]; })   // more misses than tries cannot pass 100%
    .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 9);
  return { ok: true, kids: kids, hard: hard };
}
