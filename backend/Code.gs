/**
 * English Trainer backend. Lives inside a Google Sheet (Extensions > Apps Script).
 * 1. Run setup() once.  2. Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
 * The sheet holds first names, salted PIN hashes and scores. Nothing here is stored in the GitHub repo.
 */
const KIDS = 'kids', CFG = 'config', MAX_KIDS = 60;
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

  if (d.a === 'teacher') {
    if (!teacherCode || String(d.t || '').trim() !== teacherCode) return { ok: false, e: 'teacher' };
    return teacherView(rows);
  }

  const name = String(d.n || '').trim().replace(/\s+/g, ' '), pin = String(d.p || '');
  if (!NAME_RE.test(name) || !/^\d{4}$/.test(pin)) return { ok: false, e: 'input' };
  const i = rows.findIndex(function (r) { return String(r[0]) === name; });

  if (d.a === 'register') {
    if (i >= 0) return { ok: false, e: 'taken' };
    if (rows.length >= MAX_KIDS) return { ok: false, e: 'full' };
    const salt = Utilities.getUuid();
    ks.appendRow([name, salt, hash(salt, pin), 0, 0, 0, 0, '', 0, 0, '{}', new Date()]);
    return { ok: true, s: {} };
  }
  if (i < 0) return { ok: false, e: 'nouser' };

  const r = rows[i], rowNo = i + 2, now = Date.now();
  if (Number(r[9]) > now) return { ok: false, e: 'locked' };
  if (hash(String(r[1]), pin) !== String(r[2])) {
    const f = Number(r[8]) + 1;
    ks.getRange(rowNo, 9, 1, 2).setValues([f >= 5 ? [0, now + 5 * 60000] : [f, 0]]);
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

function teacherView(rows) {
  const agg = {};
  const kids = rows.map(function (x) {
    const st = parse(x[10]).st || {};
    Object.keys(st).forEach(function (w) {
      const a = agg[w] || (agg[w] = [0, 0]);
      a[0] += Number(st[w][0]) || 0; a[1] += Number(st[w][1]) || 0;
    });
    return { n: String(x[0]), pts: Number(x[3]) || 0, words: Number(x[4]) || 0, reads: Number(x[5]) || 0, streak: Number(x[6]) || 0, day: dayStr(x[7]) };
  }).sort(function (a, b) { return b.words - a.words; });
  const hard = Object.keys(agg).filter(function (w) { return agg[w][0] >= 3 && agg[w][1] > 0; })
    .map(function (w) { return [w, Math.round(agg[w][1] / agg[w][0] * 100), agg[w][0]]; })
    .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 9);
  return { ok: true, kids: kids, hard: hard };
}
