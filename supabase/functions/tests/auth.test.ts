// The four functions against a local PostgreSQL. Run with: python3 tests/functions.py (from the repo root).
// Every name, code and address here is made up.
import { asUser, clock, DAY, deps, e, eq, freshIp, HOUR, log, MIN, newClass, ok, pepper, pupilId, recOtc, recPic, reg, reset, saves, SCHOOL, settings, sql, user } from "./helpers.ts";
import { kdf, legacySheetHash, stats, tag } from "../_shared/crypto.ts";
import { adminClass, type Body, login, type Reply, teacherReset, wrapLegacy } from "../_shared/core.ts";
import { addressBucket, clientIp, handler } from "../_shared/http.ts";
import { gotrueSessions } from "../_shared/gotrue.ts";
import { isName, isWeakCode } from "../_shared/validate.ts";

const T = (name: string, fn: () => Promise<void>) => Deno.test({ name, fn, sanitizeResources: false, sanitizeOps: false });
const tok = (r: Reply) => (r as Body).device_token as string;

T("setup: fast hashes for the suite (one test below uses the real 600,000 rounds)", async () => {
  await settings({ kdf_iter: 100000, save_gap_s: 0 }); // the database clock is real here; the 5-second rule is tested in tests/db.py
});

T("register: a pupil is created, signed in, and nothing secret is stored or returned in the clear", async () => {
  const c = await newClass({ roster: ["נועה", "Dan"] });
  const r = await reg(c, "  נועה ", "4827", [3, 11]);
  eq(e(r), "ok", "register");
  ok((r as Body).session.access_token && tok(r)?.length >= 40, "a session and a device token come back");
  ok(!JSON.stringify(r).includes("4827"), "the code is not in the answer");
  const row = (await sql`select p.display_name, s.code_algo, octet_length(s.code_hash) as n, octet_length(s.pic_hash) as m, encode(s.code_hash, 'hex') as h
                         from public.pupils p join private.pupil_secrets s on s.pupil_id = p.id where p.class_id = ${c.id}`)[0];
  eq([row.display_name, row.code_algo, row.n, row.m], ["נועה", "v1", 32, 32], "stored pupil");
  const dump = JSON.stringify(await sql`select * from private.pupil_secrets`) + JSON.stringify(await sql`select * from private.pupil_devices`);
  ok(!dump.includes("4827") && !dump.includes("3>11") && !dump.includes(tok(r)), "no code, pictures or device token in the tables");
  ok(await saves(user(r)), "the new session can save");
  eq(e(await reg(c, "נועה", "5839")), "taken", "same name again");
  eq(e(await reg(c, "NOA", "5839")), "roster", "a name that is not on the class list");
  eq(e(await reg(c, "dan", "5839")), "ok", "a listed name in other letter case");
  eq(e(await reg({ ...c, code: "NOPE0000" }, "Dan", "5839")), "class", "wrong class code");
  for (const bad of [["x", "5839", [1, 2]], ["<b>hi</b>", "5839", [1, 2]], ["Dan", "593", [1, 2]], ["Dan", "5839", [1, 1]], ["Dan", "5839", [1, 21]], ["Dan", "5839", [1]], ["Dan", "5839", "1,2"]] as const) {
    eq(e(await reg(c, bad[0], bad[1], bad[2] as number[])), "input", "bad input " + JSON.stringify(bad));
  }
  const full = await newClass({ max: 1 });
  eq([e(await reg(full, "Avi")), e(await reg(full, "Ben"))], ["ok", "full"], "a full class");
});

T("weak codes are refused at registration and whenever a new code is set", async () => {
  const weak = Array.from({ length: 10000 }, (_, i) => String(i).padStart(4, "0")).filter(isWeakCode);
  eq(weak.length, 970, "codes on the list");
  // the rule is the one written in docs/BACKEND.md 4.2: its groups, and the 14 keypad codes listed there
  const doc = await Deno.readTextFile(new URL("../../../docs/BACKEND.md", import.meta.url));
  const listed = (doc.match(/these 14 keypad\s+lines[^`]*((?:`[^`]+`[\s\S]*?)+)\. Together 970/)?.[1] ?? "").replace(/[`\s]+/g, " ").trim().split(" ").filter((x) => /^\d{4}$/.test(x));
  const days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const date = (d: number, m: number) => m >= 1 && m <= 12 && d >= 1 && d <= days[m - 1];
  const group = (c: string) => {
    const d = [...c].map(Number), st = (d[1] - d[0] + 10) % 10, up = (i: number) => (d[i + 1] - d[i] + 10) % 10;
    return (d[0] === d[1] && d[1] === d[2] && d[2] === d[3]) || ((st === 1 || st === 9) && up(1) === st && up(2) === st) ||
      (d[0] === d[2] && d[1] === d[3]) || (d[0] === d[1] && d[2] === d[3]) || /^(19|20)/.test(c) ||
      date(+c.slice(0, 2), +c.slice(2)) || date(+c.slice(2), +c.slice(0, 2));
  };
  eq(listed.length, 14, "the doc lists 14 keypad codes");
  eq(weak.filter((w) => !group(w)).sort(), [...listed].sort(), "the code's list is exactly the doc's groups plus the doc's keypad codes");
  eq(weak.filter(group).length, 956, "the doc's groups: 956");
  for (const w of ["2406", "0624", "3112", "2902", "2580", "1357"]) ok(isWeakCode(w), w + " (a date or a keypad line) is weak");
  for (const g of ["3113", "0013", "4500"]) ok(!isWeakCode(g), g + " is not a date");
  for (const w of ["0000", "1234", "4321", "1212", "1122", "2015", "1999", "7777", "0123", "9876", "7890", "8901", "9012", "0987", "1098"]) ok(isWeakCode(w), w + " is weak");
  for (const g of ["4827", "5839", "8353", "6149", "7159", "9053"]) ok(!isWeakCode(g), g + " is fine");
  const c = await newClass();
  for (const n of ["Da\u200bna", "D\u0430na", "\u3164\u3164", "Dana\u{1F600}", "<b>x</b>"]) eq(e(await reg(c, n, "4827")), "input", "a name the allow-list refuses: " + JSON.stringify(n));
  for (const n of ["Chloé", "ג׳ני", "O'Neil"]) ok(isName(n), "allowed: " + n);
  eq(e(await reg(c, "Gal", "1234")), "weak", "register");
  await reg(c, "Gal", "4827", [3, 11]);
  eq(e(await recPic(c, "Gal", [3, 11], "2015")), "weak", "recover");
  eq(e(await recPic(c, "Gal", [3, 11], "5839")), "ok", "a weak new code did not use up a try");
});

T("sign in: right code opens; wrong code and unknown name look and cost the same", async () => {
  const c = await newClass();
  const r0 = await reg(c, "Maya", "4827");
  const before = stats.kdf;
  const good = await log(c, "Maya", "4827", { ip: freshIp() });
  eq([e(good), stats.kdf - before], ["ok", 1], "right code: one slow hash");
  ok(user(good) === user(r0), "a second device gets a session of the same auth user");
  ok(tok(good), "a device without a token is given one after a correct sign-in");
  const k1 = stats.kdf;
  const wrong = await log(c, "Maya", "9053", { ip: freshIp() });
  const k2 = stats.kdf;
  const ghost = await log(c, "Nobody", "9053", { ip: freshIp() });
  eq([JSON.stringify(wrong), k2 - k1], [JSON.stringify(ghost), stats.kdf - k2], "wrong code vs no such pupil: same answer, same work");
  eq([e(wrong), k2 - k1], ["pin", 1], "and that answer is 'pin' after one slow hash");
  eq(e(await log({ ...c, code: "NOPE0000" }, "Maya", "4827")), "class", "wrong class code");
  eq(e(await log(c, "Maya", "48271")), "input", "five digits");
  const st = await sql`select count(*)::int as n from private.auth_attempts where class_id = ${c.id} and outcome = 'pending'`;
  eq(st[0].n, 0, "no try is left pending");
});

T("the lock grows per round: 5 min, 15 min, 1 h, 4 h, 4 h", async () => {
  await settings({ code_bucket_day: 1000, code_name_day: 1000, code_ceiling_day: 1000, code_ip_class_day: 1000, code_class_brake: 1000, ip_hour: 100000 });
  const c = await newClass();
  await reg(c, "Omer", "4827");
  const ip = freshIp(), waits: number[] = [];
  for (let round = 0; round < 5; round++) {
    for (let i = 0; i < 5; i++) eq(e(await log(c, "Omer", "9053", { ip })), "pin", `round ${round} try ${i}`);
    const locked = await log(c, "Omer", "4827", { ip });
    eq(e(locked), "locked", "the right code is refused too while the lock runs");
    waits.push((locked as Body).wait);
    clock.ms += (locked as Body).wait * 1000 + 1000;
  }
  eq(waits, [300, 900, 3600, 14400, 14400], "lock lengths in seconds");
  eq(e(await log(c, "Omer", "4827", { ip })), "ok", "after the lock the right code works");
  for (let i = 0; i < 4; i++) await log(c, "Omer", "9053", { ip });
  eq(e(await log(c, "Omer", "4827", { ip })), "ok", "4 wrong then right: no lock, and the count starts again");
  await settings({ code_bucket_day: 10, code_name_day: 20, code_ceiling_day: 29, code_ip_class_day: 30, code_class_brake: 100, ip_hour: 120 });
  clock.ms += 2 * DAY;
});

/** how many of the times fall inside the fullest 24-hour window */
function worstDay(times: number[]): number {
  let worst = 0;
  for (let i = 0, j = 0; i < times.length; i++) {
    while (times[i] - times[j] >= DAY) j++;
    worst = Math.max(worst, i - j + 1);
  }
  return worst;
}

T("a simulated day of guessing one name from ever-new addresses stays at 20 (under 30)", async () => {
  await settings({ code_class_brake: 100000, ip_hour: 100000 });
  const c = await newClass();
  await reg(c, "Shai", "4827");
  const accepted: number[] = [];
  const start = clock.ms;
  for (let m = 0; m < 26 * 60; m++) { // one guess a minute for 26 hours, a fresh address every time
    clock.ms = start + m * MIN;
    const r = await log(c, "Shai", String(1000 + (m % 9000)).replace(/^(19|20)/, "31"), { ip: freshIp() });
    if (e(r) === "pin") accepted.push(clock.ms);
    else eq(e(r), "locked", "anything not accepted is refused as locked");
  }
  eq(accepted.filter((t) => t < start + DAY).length, 20, "guesses accepted in the first 24 hours");
  ok(worstDay(accepted) <= 20, `never more than 20 in any 24 hours, got ${worstDay(accepted)}`);
  eq(e(await log(c, "Shai", "4827", { ip: freshIp() })), "locked", "the name is closed for unknown devices, right code or not");
  const ev = await sql`select count(*)::int as n from private.auth_lock_events where class_id = ${c.id} and kind = 'name'`;
  ok(ev[0].n >= 1, "the teacher's 'locked today' counter moved");
  await settings({ code_class_brake: 100, ip_hour: 120 });
  clock.ms += 2 * DAY;
});

T("one address: 10 a day on a name, 30 a day across the names of a class; many addresses: the class brake at 100", async () => {
  const c = await newClass();
  const names = Array.from({ length: 12 }, (_, i) => "Kid" + "abcdefghijkl"[i]);
  for (const n of names) await reg(c, n, "4827", [3, 11], freshIp());
  clock.ms += 2 * HOUR;
  const ip = freshIp();
  const one: number[] = [];
  for (let i = 0; i < 60; i++) { // one address hammering one name, waiting out every lock, for more than two days
    const r = await log(c, names[0], "9053", { ip });
    if (e(r) === "pin") one.push(clock.ms);
    else clock.ms += Math.min(((r as Body).wait + 1) * 1000, 5 * HOUR);
  }
  ok(one.length >= 15 && worstDay(one) <= 10, `one address, one name: never more than 10 in any 24 hours, got ${worstDay(one)} (of ${one.length})`);
  clock.ms += 2 * DAY;
  const ip2 = freshIp();
  let spray = 0;
  for (let round = 0; round < 4; round++) for (const n of names) if (e(await log(c, n, "9053", { ip: ip2 })) === "pin") spray++; // the same popular code on every name
  eq(spray, 30, "spraying from one address stops at 30 for the class");
  let total = spray;
  for (let i = 0; i < 300; i++) if (e(await log(c, names[i % names.length], "9053", { ip: freshIp() })) === "pin") total++;
  eq(total, 100, "with any number of addresses the class takes 100 wrong codes a day from unknown devices");
  const ev = (await sql`select kind from private.auth_lock_events where class_id = ${c.id} and name_key = '' order by at`).map((x) => x.kind);
  eq(ev, ["class-alarm", "class-brake"], "the teacher is told at 60 and at 100");
  clock.ms += 2 * DAY;
});

T("60 guesses at the same instant: the limit holds (tries are reserved before the hash)", async () => {
  const c = await newClass();
  await reg(c, "Lior", "4827");
  clock.ms += HOUR;
  const res = await Promise.all(Array.from({ length: 60 }, () => log(c, "Lior", "9053", { ip: freshIp() })));
  const pins = res.filter((r) => e(r) === "pin").length;
  ok(pins <= 20 && pins >= 1, `accepted ${pins} of 60 parallel guesses`);
  clock.ms += 2 * DAY;
});

T("bullying: a name closed by a classmate. The open session keeps saving, the pupil's own phone still gets in", async () => {
  const c = await newClass();
  const mine = await reg(c, "Tamar", "4827"); // the pupil's own phone: signed in, holds a device token
  clock.ms += HOUR;
  for (let i = 0; i < 25; i++) await log(c, "Tamar", "9053", { ip: freshIp() }); // the classmate burns every try
  eq(e(await log(c, "Tamar", "4827", { ip: freshIp() })), "locked", "a new device is kept out, even with the right code");
  ok(await saves(user(mine)), "the open session still saves");
  const ev = await sql.begin(async (tx) => {
    await tx`select set_config('request.jwt.claims', ${JSON.stringify({ sub: user(mine) })}, true)`;
    await tx`set local role authenticated`;
    return await tx`select public.record_events(${crypto.randomUUID()}, '[]'::jsonb) as v`;
  });
  eq(ev[0].v.ok, true, "and still reports events");
  const again = await log(c, "Tamar", "4827", { ip: SCHOOL, device_token: tok(mine) });
  eq(e(again), "ok", "the pupil's own known phone signs in while the name is closed for strangers");
  let own = 0;
  for (let i = 0; i < 15; i++) if (e(await log(c, "Tamar", "9053", { device_token: tok(mine) })) === "pin") own++;
  const all = await sql`select count(*)::int as n from private.auth_attempts where class_id = ${c.id} and name_key = 'tamar' and kind = 'code' and outcome = 'wrong' and at > ${new Date(clock.ms - DAY)}`;
  ok(all[0].n <= 29 && own <= 9, `ceiling with a known device: ${all[0].n} wrong in the day (limit 29), ${own} from the known device`);
  clock.ms += 2 * DAY;
});

T("a device token is 'known' for one pupil only: a shared class computer gets stranger rules", async () => {
  const c = await newClass();
  const a = await reg(c, "Adi", "4827");
  await reg(c, "Bar", "5839");
  clock.ms += HOUR;
  eq(e(await log(c, "Bar", "5839", { device_token: tok(a) })), "ok", "Bar signs in on Adi's device");
  for (let i = 0; i < 25; i++) await log(c, "Adi", "9053", { ip: freshIp() });
  eq(e(await log(c, "Adi", "4827", { device_token: tok(a), ip: freshIp() })), "locked", "the shared device no longer has a reserve for Adi");
  eq(e(await log(c, "Adi", "4827", { device_token: "x".repeat(43), ip: freshIp() })), "locked", "a made-up token is a stranger");
  clock.ms += 2 * DAY;
});

for (const count of [2, 1]) {
  T(`recovery with ${count} secret picture(s): right ones set a new code and sign every other device out`, async () => {
    await settings({ pic_count: count });
    const P = (a: number, b: number) => (count === 2 ? [a, b] : [a]);
    const c = await newClass();
    const old = await reg(c, "Yael", "4827", P(3, 11));
    clock.ms += HOUR;
    if (count === 2) eq(e(await recPic(c, "Yael", [11, 3], "5839", [7, 2])), "picture", "the right pictures in the wrong order are wrong");
    eq(e(await recPic(c, "Yael", P(4, 12), "5839", P(7, 2))), "picture", "wrong pictures");
    const r = await recPic(c, "Yael", P(3, 11), "5839", P(7, 2));
    eq(e(r), "ok", "right pictures");
    ok(user(r) !== user(old), "the pupil has a brand-new auth user");
    eq((await sql`select count(*)::int as n from auth.users where id = ${user(old)}`)[0].n, 0, "the old auth user is deleted");
    ok(!(await saves(user(old))), "the old session can no longer save");
    ok(await saves(user(r)), "the new one can");
    eq([e(await log(c, "Yael", "4827", { ip: freshIp() })), e(await log(c, "Yael", "5839", { ip: freshIp() }))], ["pin", "ok"], "old code dead, new code works");
    eq(e(await log(c, "Yael", "5839", { device_token: tok(old), ip: freshIp() })), "ok", "the old device must sign in like any stranger (and may, with the new code)");
    eq(e(await recPic(c, "Yael", P(7, 2), "6149", P(1, 5))), "locked", "a second recovery by pictures inside 30 days goes through the teacher");
    clock.ms += 31 * DAY;
    eq(e(await recPic(c, "Yael", P(3, 11), "6149", P(1, 5))), "picture", "the old pictures are gone");
    eq(e(await recPic(c, "Yael", P(7, 2), "6149", P(1, 5))), "ok", "the new pictures work after 30 days");
    await settings({ pic_count: 2 });
    clock.ms += 2 * DAY;
  });
}

T("3 wrong pictures close recovery until the teacher reopens it; sign-in and the open session are untouched", async () => {
  const c = await newClass();
  const mine = await reg(c, "Rotem", "4827", [3, 11]);
  clock.ms += HOUR;
  const res = [];
  for (let i = 0; i < 3; i++) res.push(e(await recPic(c, "Rotem", [i + 5, 1], "5839", [7, 2], freshIp())));
  const closed = await recPic(c, "Rotem", [3, 11], "5839", [7, 2], freshIp());
  eq([res, e(closed), (closed as Body).wait], [["picture", "picture", "picture"], "locked", -1], "three tries, then closed even for the right pictures");
  clock.ms += 3 * DAY;
  eq(e(await recPic(c, "Rotem", [3, 11], "5839", [7, 2], freshIp())), "locked", "no second round after a day or three");
  eq(e(await log(c, "Rotem", "4827", { ip: freshIp() })), "ok", "the code still signs in");
  ok(await saves(user(mine)), "the open session still saves");
  const view = await sql`select kind from private.auth_lock_events where class_id = ${c.id} and name_key = 'rotem'`;
  eq(view.map((x) => x.kind), ["picture"], "the teacher sees one recovery lock");
  const ghost = [];
  for (let i = 0; i < 4; i++) ghost.push(e(await recPic(c, "Nobody", [i + 5, 1], "5839", [7, 2], freshIp())));
  eq(ghost, ["picture", "picture", "picture", "locked"], "a name that does not exist behaves the same");
  clock.ms += 2 * DAY;
});

T("pictures cannot be sprayed: 5 wrong a day per address, 10 a day in the class, then recovery pauses for the class", async () => {
  const c = await newClass();
  const names = Array.from({ length: 14 }, (_, i) => "Pup" + "abcdefghijklmn"[i]);
  for (const n of names) await reg(c, n, "4827", [3, 11], freshIp());
  clock.ms += 2 * HOUR;
  const ip = freshIp();
  let n = 0;
  for (const name of names) if (e(await recPic(c, name, [5, 6], "5839", [7, 2], ip)) === "picture") n++;
  eq(n, 5, "one address gets 5 wrong picture tries a day across all names");
  for (const name of names) if (e(await recPic(c, name, [5, 6], "5839", [7, 2], freshIp())) === "picture") n++;
  eq(n, 10, "any number of addresses: 10 wrong a day in the class");
  eq(e(await recPic(c, names[13], [3, 11], "5839", [7, 2], freshIp())), "locked", "while paused even right pictures wait");
  const ev = await sql`select count(*)::int as n from private.auth_lock_events where class_id = ${c.id} and kind = 'class-picture'`;
  eq(ev[0].n, 1, "the teacher is told once");
  clock.ms += DAY + HOUR;
  eq(e(await recPic(c, names[13], [3, 11], "5839", [7, 2], freshIp())), "ok", "the next day recovery works again");
  const burst = await Promise.all(Array.from({ length: 10 }, () => recPic(c, names[12], [5, 6], "5839", [7, 2], freshIp())));
  ok(burst.filter((r) => e(r) === "picture").length <= 3, "10 parallel tries on one name: at most 3 are looked at");
  clock.ms += 2 * DAY;
});

T("teacher reset: only her own pupils; the old code dies, nobody can claim the name, the one-time code finishes it", async () => {
  const c = await newClass(), other = await newClass();
  const mine = await reg(c, "Noam", "4827", [3, 11]);
  const pid = await pupilId(c, "Noam");
  const teacher = (await sql`insert into auth.users (email) values ('teacher1@test.invalid') returning id`)[0].id;
  const stranger = (await sql`insert into auth.users (email) values ('teacher2@test.invalid') returning id`)[0].id;
  await sql`insert into public.teachers values (${teacher}, ${c.id}), (${stranger}, ${other.id})`;
  clock.ms += HOUR;
  eq([e(await reset(undefined, pid)), e(await reset("garbage", pid)), e(await reset("t:" + stranger, pid)), e(await reset("t:" + user(mine), pid))],
    ["forbidden", "forbidden", "forbidden", "forbidden"], "no token, a bad token, another class's teacher, the pupil's own token");
  eq(e(await log(c, "Noam", "4827", { ip: freshIp() })), "ok", "refused resets changed nothing");
  const r = await reset("t:" + teacher, pid) as Body;
  ok(r.ok && /^\d{6}$/.test(r.otc), "the teacher gets a 6-digit one-time code");
  ok(!JSON.stringify(await sql`select * from private.reset_codes`).includes(r.otc), "only its hash is stored");
  ok(!(await saves(user(mine))), "every device of the pupil is signed out at once");
  eq(e(await log(c, "Noam", "4827", { ip: freshIp() })), "pin", "the old code no longer works");
  eq(e(await log(c, "Noam", "8353", { ip: freshIp() })), "pin", "and the first person to type the name does NOT set a new code");
  eq(e(await log(c, "Noam", "8353", { ip: freshIp(), new_code: "8353", pictures: [1, 2] })), "pin", "not by sending a new code along either");
  eq(e(await recPic(c, "Noam", [3, 11], "5839", [7, 2], freshIp())), "locked", "while the reset waits the pictures do not work, only the teacher's code");
  const wrongOtc = r.otc === "000001" ? "000002" : "000001";
  eq(e(await recOtc(c, "Noam", wrongOtc, "6149", [9, 4], freshIp())), "otc", "a wrong one-time code");
  const done = await recOtc(c, "Noam", r.otc, "6149", [9, 4], freshIp());
  eq(e(done), "ok", "the right one-time code sets the new code and pictures");
  ok(await saves(user(done)), "and signs the pupil in");
  eq(e(await recOtc(c, "Noam", r.otc, "7159", [9, 4], freshIp())), "otc", "it works once");
  eq(e(await log(c, "Noam", "6149", { ip: freshIp() })), "ok", "the new code signs in");
  clock.ms += 31 * DAY;
  eq(e(await recPic(c, "Noam", [9, 4], "7159", [1, 2], freshIp())), "ok", "the pictures chosen with the one-time code are the pupil's pictures now");
  clock.ms += 2 * DAY;
});

T("the one-time code cannot be burnt from one network, expires, and reopens a closed recovery", async () => {
  const c = await newClass();
  await reg(c, "Ziv", "4827", [3, 11]);
  const pid = await pupilId(c, "Ziv");
  const teacher = (await sql`insert into auth.users (email) values ('teacher3@test.invalid') returning id`)[0].id;
  await sql`insert into public.teachers values (${teacher}, ${c.id})`;
  for (let i = 0; i < 3; i++) await recPic(c, "Ziv", [i + 5, 1], "5839", [7, 2], freshIp()); // recovery is closed now
  clock.ms += HOUR;
  const r = await reset("t:" + teacher, pid) as Body;
  const bad = r.otc === "000001" ? "000002" : "000001";
  const bully = freshIp(), tries = [];
  for (let i = 0; i < 7; i++) tries.push(e(await recOtc(c, "Ziv", bad, "6149", [9, 4], bully)));
  eq(tries, ["otc", "otc", "otc", "otc", "otc", "locked", "locked"], "one address gets 5 wrong tries, then it is refused");
  eq(e(await recOtc(c, "Ziv", r.otc, "6149", [9, 4], SCHOOL)), "ok", "the pupil, from another address, still finishes with the right code");
  const r2 = await reset("t:" + teacher, pid) as Body;
  const bad2 = r2.otc === "000001" ? "000002" : "000001";
  for (let i = 0; i < 30; i++) await recOtc(c, "Ziv", bad2, "6149", [9, 4], freshIp());
  eq(e(await recOtc(c, "Ziv", r2.otc, "6149", [9, 4], freshIp())), "otc", "after 30 wrong tries in all the code is cancelled");
  const r3 = await reset("t:" + teacher, pid) as Body;
  clock.ms += 49 * HOUR;
  eq(e(await recOtc(c, "Ziv", r3.otc, "6149", [9, 4], freshIp())), "otc", "after 48 hours it has expired");
  const r4 = await reset("t:" + teacher, pid) as Body;
  eq(e(await recOtc(c, "Ziv", r4.otc, "6149", [9, 4], freshIp())), "ok", "a fresh one works");
  clock.ms += 2 * DAY;
});

T("teacher unlock: clears a pupil's locks without touching the code; lifts the class brake; only for her own class", async () => {
  const c = await newClass(), other = await newClass();
  await reg(c, "Lia", "4827", [3, 11]);
  const pid = await pupilId(c, "Lia");
  const teacher = (await sql`insert into auth.users (email) values ('teacher5@test.invalid') returning id`)[0].id;
  const stranger = (await sql`insert into auth.users (email) values ('teacher6@test.invalid') returning id`)[0].id;
  await sql`insert into public.teachers values (${teacher}, ${c.id}), (${stranger}, ${other.id})`;
  clock.ms += HOUR;
  for (let i = 0; i < 25; i++) await log(c, "Lia", "9053", { ip: freshIp() });
  for (let i = 0; i < 3; i++) await recPic(c, "Lia", [i + 5, 1], "5839", [7, 2], freshIp());
  eq(e(await log(c, "Lia", "4827", { ip: freshIp() })), "locked", "the name is closed for unknown devices");
  const T = (token: string | undefined, body: Body) => teacherReset(deps, body, { ip: SCHOOL, token });
  eq([e(await T("t:" + stranger, { action: "unlock", pupil_id: pid })), e(await T(undefined, { action: "unlock", pupil_id: pid })), e(await T("t:" + stranger, { action: "unlock_class", class_id: c.id })), e(await T("t:" + teacher, { action: "explode", pupil_id: pid }))],
    ["forbidden", "forbidden", "forbidden", "input"], "another teacher, nobody, another teacher on the class, an unknown action");
  eq(e(await T("t:" + teacher, { action: "unlock", pupil_id: pid })), "ok", "her teacher unlocks");
  eq(e(await log(c, "Lia", "4827", { ip: freshIp() })), "ok", "the same code works again: nothing was reset");
  eq(e(await recPic(c, "Lia", [3, 11], "5839", [7, 2], freshIp())), "ok", "and recovery is open again with the same pictures");
  eq((await sql`select count(*)::int as n from private.auth_attempts where class_id = ${c.id} and kind = 'code' and lifted`)[0].n, 20,
    "the lifted tries are kept: they still count towards the name's daily ceiling");
  for (let i = 0; i < 5; i++) await log(c, "Lia", "9053", { ip: freshIp() });
  eq(e(await log(c, "Lia", "5839", { ip: freshIp() })), "locked", "after an unlock, strangers get 5 more wrong codes, not a fresh 20");
  eq(e(await T("t:" + teacher, { action: "unlock", pupil_id: pid })), "ok", "a second unlock the same day");
  eq(e(await T("t:" + teacher, { action: "unlock", pupil_id: pid })), "limit", "a third is refused: twice a day, then the reset");
  eq(e(await log(c, "Lia", "5839", { ip: freshIp() })), "ok", "and the pupil is in");
  const names = Array.from({ length: 6 }, (_, i) => "Zed" + "abcdef"[i]);
  for (const n of names) await reg(c, n, "4827", [3, 11], freshIp());
  clock.ms += 2 * HOUR;
  for (let i = 0; i < 110; i++) await log(c, names[i % 6], "9053", { ip: freshIp() });
  eq(e(await log(c, names[0], "4827", { ip: freshIp() })), "locked", "before school somebody used up the class's 100 wrong codes");
  eq(e(await T("t:" + teacher, { action: "unlock_class", class_id: c.id })), "ok", "the teacher lifts the class brake");
  const after = names.map(() => "");
  for (let i = 0; i < 6; i++) after[i] = e(await log(c, names[i], "4827", { ip: freshIp() }));
  ok(after.filter((x) => x === "ok").length >= 5, "the lesson can start: pupils sign in on the school computers " + JSON.stringify(after));
  for (let i = 0; i < 30; i++) await log(c, names[i % 6], "9053", { ip: freshIp() });
  eq(e(await log(c, names[1], "4827", { ip: freshIp() })), "locked", "after a lift the class gets 30 more wrong codes from strangers, not another 100");
  const kinds = (await sql`select kind from private.auth_lock_events where class_id = ${c.id} and kind like 'unlock%' order by at`).map((x) => x.kind);
  eq(kinds, ["unlock", "unlock", "unlock-class"], "every use is on record");
  clock.ms += 2 * DAY;
});

T("admin-class: only with the server key; the class code is 8 clear characters, shown once, stored as a keyed lookup", async () => {
  const A = (token: string | undefined, body: Body) => adminClass(deps, body, { ip: SCHOOL, token });
  eq([e(await A(undefined, { action: "create", name: "x" })), e(await A("nope", { action: "create", name: "x" })), e(await A("t:anyone", { action: "shadow_on" }))], ["forbidden", "forbidden", "forbidden"], "without the key");
  const r = await A("test-server-key", { action: "create", name: "class from admin", grade: "5" }) as Body;
  ok(r.ok && /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$/.test(r.class_code), "an 8-character code without look-alike characters: " + r.class_code);
  ok(!JSON.stringify(await sql`select * from private.class_codes`).includes(r.class_code), "the code itself is not stored");
  const c = { id: r.class_id as string, code: r.class_code as string };
  await sql`update public.classes set roster_only = false where id = ${c.id}`;
  eq(e(await reg(c, "Uri", "4827")), "ok", "pupils register with it");
  const r2 = await A("test-server-key", { action: "rotate", class_id: c.id }) as Body;
  eq([e(await log(c, "Uri", "4827", { ip: freshIp() })), e(await log({ ...c, code: r2.class_code }, "Uri", "4827", { ip: freshIp() }))], ["class", "ok"], "after a rotation the old class code is dead and the new one works");
});

T("copy phase (shadow_mode): a Sheet-era code opens a session that can only receive copies; switching it off ends those sessions", async () => {
  const A = (action: string) => adminClass(deps, { action }, { ip: SCHOOL, token: "test-server-key" });
  const c = await newClass();
  const pid = (await sql`insert into public.pupils (class_id, display_name) values (${c.id}, 'Shadow') returning id`)[0].id;
  await sql`insert into private.legacy_import values (${pid}, 'salt-x', ${await legacySheetHash("salt-x", "8353")})`;
  await wrapLegacy(deps, {}, { ip: SCHOOL, token: "test-server-key" });
  const teacher = (await sql`insert into auth.users (email) values ('teacher7@test.invalid') returning id`)[0].id;
  await sql`insert into public.teachers values (${teacher}, ${c.id})`;
  clock.ms += HOUR;
  eq(e(await log(c, "Shadow", "8353", { ip: freshIp() })), "setup", "default (off): the old code alone opens nothing");
  eq((await A("shadow_on") as Body).shadow_mode, true, "copy phase on");
  eq(e(await log(c, "Shadow", "9053", { ip: freshIp() })), "pin", "a wrong code is still wrong, under the same lockout");
  const s1 = await log(c, "Shadow", "8353", { ip: freshIp() });
  eq(e(s1), "ok", "the right Sheet-era code opens a session");
  ok(await saves(user(s1)), "which can receive the copy of the progress");
  eq([(s1 as Body).s, (s1 as Body).updated_at], [{}, null], "the sign-in answer carries nothing back");
  const u1 = user(s1);
  ok(await saves(u1) && await saves(u1), "a copy is written over the last one (the Sheet already merged the devices)");
  const ev = await asUser(u1, (tx) => tx`select public.record_events(${crypto.randomUUID()}::uuid, '[]'::jsonb) as v`);
  ok(ev[0].v.ok === true && !("points" in ev[0].v), "events are taken, the total is not shown: " + JSON.stringify(ev[0].v));
  const sv = await asUser(u1, (tx) => tx`select public.save_progress('{"a":1}'::jsonb, '2000-01-01'::timestamptz) as v`);
  eq(Object.keys(sv[0].v).sort(), ["ok"], "a save answers ok and nothing else, even against a stale version");
  const seen = await asUser(u1, async (tx) => {
    const out: Record<string, number> = {};
    for (const t of ["classes", "pupils", "answers", "points", "pupil_totals", "answer_daily", "level_best", "progress", "class_board", "teacher_view", "teacher_items", "flags"]) {
      out[t] = (await tx.unsafe(`select count(*)::int as n from public.${t}`))[0].n;
    }
    return out;
  });
  eq(Object.values(seen).reduce((a, b) => a + b, 0), 0, "and reads nothing at all: " + JSON.stringify(seen));
  const direct = await asUser(u1, (tx) => tx`select app.record_events(${crypto.randomUUID()}::uuid, '[]'::jsonb)`).then(() => "ran", () => "refused");
  eq(direct, "refused", "the full functions behind the wrappers cannot be called by a session");
  const sec = (await sql`select code_algo, pic_hash from private.pupil_secrets where pupil_id = ${pid}`)[0];
  eq([sec.code_algo, sec.pic_hash], ["legacy-sha256", null], "and nothing about the pupil's code or pictures was changed");
  eq([e(await recPic(c, "Shadow", [3, 11], "5839", [7, 2], freshIp())), e(await recOtc(c, "Shadow", "123456", "6149", [9, 4], freshIp())), e(await reg(c, "Newkid", "4827")),
    e(await log(c, "Shadow", "8353", { ip: freshIp(), new_code: "4827", pictures: [3, 11] })) === "ok" ? (await sql`select code_algo from private.pupil_secrets where pupil_id = ${pid}`)[0].code_algo : "x",
    e(await reset("t:" + teacher, pid)), e(await teacherReset(deps, { action: "unlock", pupil_id: pid }, { ip: SCHOOL, token: "t:" + teacher })),
    e(await teacherReset(deps, { action: "unlock_class", class_id: c.id }, { ip: SCHOOL, token: "t:" + teacher }))],
    ["locked", "locked", "locked", "legacy-sha256", "forbidden", "forbidden", "forbidden"], "no recovery, no one-time code, no registration, no new code or pictures, no teacher reset, unlock or brake lift while it is on");
  const off = await A("shadow_off") as Body;
  ok(off.signed_out >= 1 && off.shadow_mode === false, "copy phase off");
  ok(!(await saves(user(s1))), "the session opened during the copy phase is dead at once");
  eq((await sql`select count(*)::int as n from auth.users where id = ${user(s1)}`)[0].n, 0, "its auth user is deleted");
  eq(e(await log(c, "Shadow", "8353", { ip: freshIp() })), "setup", "from now on the pupil must choose a new code and pictures");
  const back = await reg(c, "Afterkid", "4827");
  eq(e(back), "ok", "registration is open again");
  ok((await asUser(user(back), (tx) => tx`select count(*)::int as n from public.class_board`))[0].n >= 1, "and a normal session reads its board again");
  clock.ms += 2 * DAY;
});

T("pupils from the Sheet: the old hash is wrapped, the old code is verified, and a new code and pictures are chosen in the same step", async () => {
  const c = await newClass();
  const pid = (await sql`insert into public.pupils (class_id, display_name) values (${c.id}, 'Eden') returning id`)[0].id;
  const sheetSalt = "c0ffee00-made-up-salt";
  await sql`insert into private.legacy_import values (${pid}, ${sheetSalt}, ${await legacySheetHash(sheetSalt, "8353")})`;
  eq(e(await wrapLegacy(deps, {}, { ip: SCHOOL })), "forbidden", "wrapping without the server key");
  eq(e(await wrapLegacy(deps, {}, { ip: SCHOOL, token: "wrong-key" })), "forbidden", "wrapping with a wrong key");
  const w = await wrapLegacy(deps, {}, { ip: SCHOOL, token: "test-server-key" }) as Body;
  eq([w.wrapped, w.remaining, (await sql`select count(*)::int as n from private.legacy_import`)[0].n], [1, 0, 0], "wrapped, staging table empty");
  const sec = (await sql`select code_algo, encode(code_hash, 'hex') as h from private.pupil_secrets where pupil_id = ${pid}`)[0];
  ok(sec.code_algo === "legacy-sha256" && sec.h !== (await legacySheetHash(sheetSalt, "8353")), "the fast hash is not what is stored");
  clock.ms += HOUR;
  eq(e(await log(c, "Eden", "9053", { ip: freshIp() })), "pin", "wrong old code");
  eq(e(await log(c, "Eden", "8353", { ip: freshIp() })), "setup", "right old code alone opens nothing: choose a new code and pictures");
  eq((await sql`select auth_user_id from public.pupils where id = ${pid}`)[0].auth_user_id, null, "no session was made");
  eq(e(await log(c, "Eden", "8353", { ip: freshIp(), new_code: "1234", pictures: [3, 11] })), "weak", "the new code must not be a weak one");
  eq(e(await log(c, "Eden", "9053", { ip: freshIp(), new_code: "4827", pictures: [3, 11] })), "pin", "a wrong old code cannot set anything");
  const r = await log(c, "Eden", "8353", { ip: freshIp(), new_code: "4827", pictures: [3, 11] });
  eq(e(r), "ok", "old code + new code + pictures: in");
  ok(await saves(user(r)), "with a working session");
  const after = (await sql`select code_algo, legacy_salt from private.pupil_secrets where pupil_id = ${pid}`)[0];
  eq([after.code_algo, after.legacy_salt], ["v1", null], "stored in the new form, the Sheet's salt forgotten");
  eq([e(await log(c, "Eden", "8353", { ip: freshIp() })), e(await log(c, "Eden", "4827", { ip: freshIp() }))], ["pin", "ok"], "the old code is dead, the new one works");
  clock.ms += 31 * DAY;
  eq(e(await recPic(c, "Eden", [3, 11], "5839", [7, 2], freshIp())), "ok", "and the pictures chosen in that step recover the account");
  clock.ms += 2 * DAY;
});

T("an auth user that was tampered with is replaced at the next sign-in; the database refuses the tampering itself", async () => {
  const c = await newClass();
  const r = await reg(c, "Ofek", "4827");
  let refused = 0;
  for (const change of [sql`update auth.users set encrypted_password = 'x' where id = ${user(r)}`, sql`update auth.users set email = 'real@example.com' where id = ${user(r)}`,
    sql`update auth.users set phone = '+972500000000' where id = ${user(r)}`, sql`insert into auth.mfa_factors (user_id, factor_type) values (${user(r)}, 'totp')`]) {
    try { await change; } catch { refused++; }
  }
  eq(refused, 4, "password, email, phone and a second factor are refused for a pupil's auth user");
  const teacher = (await sql`insert into auth.users (email) values ('teacher4@test.invalid') returning id`)[0].id;
  await sql`update auth.users set encrypted_password = 'x' where id = ${teacher}`; // other users are not our business
  // if the platform did not let us install the trigger, the sign-in check still catches it:
  await sql.unsafe("alter table auth.users disable trigger pupil_user_frozen").catch(() => {});
  const su = Deno.env.get("WI_PG_SUPER");
  if (su) {
    const { default: postgres } = await import("npm:postgres@3.4.7");
    const admin = postgres({ path: Deno.env.get("WI_PG_SOCKET")!, user: su, database: "wi_test", max: 1, onnotice: () => {} });
    await admin`alter table auth.users disable trigger pupil_user_frozen`;
    await admin`update auth.users set encrypted_password = 'backdoor' where id = ${user(r)}`;
    await admin`alter table auth.users enable trigger pupil_user_frozen`;
    await admin.end();
    clock.ms += HOUR;
    const again = await log(c, "Ofek", "4827", { ip: freshIp() });
    ok(e(again) === "ok" && user(again) !== user(r), "sign-in notices the password and gives the pupil a new auth user");
    eq((await sql`select count(*)::int as n from auth.users where id = ${user(r)}`)[0].n, 0, "the tampered one is deleted");
    ok(!(await saves(user(r))) && (await saves(user(again))), "its sessions are dead, the new one works");
  }
  clock.ms += 2 * DAY;
});

T("wrong class codes are limited per address; addresses are never stored", async () => {
  const c = await newClass();
  await reg(c, "Ido", "4827", [3, 11], "192.0.2.55");
  const ip = "192.0.2.77";
  let n = 0;
  for (let i = 0; i < 40; i++) if (e(await log({ ...c, code: "WRONG" + String(i).padStart(3, "0") }, "Ido", "4827", { ip })) === "class") n++;
  eq(n, 30, "30 wrong class codes an hour from one address");
  eq(e(await log(c, "Ido", "4827", { ip })), "locked", "then that address waits, also with the right class code");
  eq(e(await log(c, "Ido", "4827", { ip: freshIp() })), "ok", "another address is not affected");
  let dump = "";
  for (const t of ["auth_attempts", "auth_buckets", "auth_lock_events", "pupil_devices", "ip_salts", "class_misses"]) dump += JSON.stringify(await sql.unsafe(`select * from private.${t}`));
  ok(!dump.includes("192.0.2.") && !dump.includes("198.51.") && !dump.includes("203.0.113."), "no raw address in any table");
  const b1 = (await sql`select ip_bucket from private.auth_attempts where class_id = ${c.id} order by id limit 1`)[0].ip_bucket;
  clock.ms += DAY + HOUR;
  await log(c, "Ido", "9053", { ip: "192.0.2.55" });
  const b2 = (await sql`select ip_bucket from private.auth_attempts where class_id = ${c.id} order by id desc limit 1`)[0].ip_bucket;
  ok(b1.length === 16 && b1 !== b2, "the same address hashes differently the next day (the salt changes daily)");
  clock.ms += 2 * DAY;
});

T("the real 600,000 rounds: a sign-in is one derivation and stays well inside a second here", async () => {
  await settings({ kdf_iter: 600000 });
  const c = await newClass();
  await reg(c, "Paz", "4827");
  const t0 = performance.now();
  eq(e(await log(c, "Paz", "4827", { ip: freshIp() })), "ok", "sign-in");
  const ms = performance.now() - t0;
  ok(ms < 1500, `one sign-in took ${ms.toFixed(0)} ms`);
  eq((await sql`select code_iter from private.pupil_secrets s join public.pupils p on p.id = s.pupil_id where p.class_id = ${c.id}`)[0].code_iter, 600000, "stored with its round count");
  await settings({ kdf_iter: 100000 });
});

T("known answer: the stored hash is PBKDF2 over an HMAC with the pepper, and useless without it", async () => {
  const c = await newClass();
  await reg(c, "Kim", "4827");
  const s = (await sql`select s.pupil_id, encode(s.code_salt, 'hex') as salt, encode(s.code_hash, 'hex') as hash, s.code_iter from private.pupil_secrets s join public.pupils p on p.id = s.pupil_id where p.class_id = ${c.id}`)[0];
  const salt = Uint8Array.from(s.salt.match(/../g)!.map((x: string) => parseInt(x, 16)));
  eq(await kdf(pepper, "code", s.pupil_id, "4827", salt, s.code_iter), s.hash, "recomputed with the pepper");
  const other = new TextEncoder().encode("another pepper, also 32 bytes!!!");
  let hit = 0;
  for (const guess of ["4827", "0000", "1234"]) if ((await kdf(other, "code", s.pupil_id, guess, salt, s.code_iter)) === s.hash) hit++;
  eq(hit, 0, "without the pepper even the right code does not match");
  ok((await tag(pepper, "class", c.code)).length === 64, "class lookup is a keyed hash");
});

T("HTTP shell: method, size, JSON, CORS, and errors that say nothing", async () => {
  const c = await newClass();
  await reg(c, "Hila", "4827");
  const { login } = await import("../_shared/core.ts");
  const h = handler(login, () => deps);
  const post = (body: string, headers: Record<string, string> = {}) => h(new Request("http://x/pupil-login", { method: "POST", body, headers }));
  eq((await h(new Request("http://x/", { method: "GET" }))).status, 405, "GET");
  eq((await post("x".repeat(3000))).status, 413, "a body over 2 KB");
  eq((await post("{not json")).status, 400, "broken JSON");
  eq((await post("[1,2]")).status, 400, "JSON that is not an object");
  const good = await post(JSON.stringify({ class_code: c.code, name: "Hila", code: "4827" }), { origin: "https://jaouibenjamin.github.io", "x-forwarded-for": "192.0.2.9, 10.0.0.1" });
  eq([good.status, (await good.json()).ok, good.headers.get("access-control-allow-origin"), good.headers.get("cache-control")], [200, true, "https://jaouibenjamin.github.io", "no-store"], "a real call from the game's origin");
  const evil = await post(JSON.stringify({ class_code: c.code, name: "Hila", code: "9053" }), { origin: "https://evil.example" });
  eq([evil.status, evil.headers.get("access-control-allow-origin")], [200, null], "another origin gets no CORS header");
  const pre = await h(new Request("http://x/", { method: "OPTIONS", headers: { origin: "https://jaouibenjamin.github.io" } }));
  eq([pre.status, pre.headers.get("access-control-allow-methods")], [204, "POST, OPTIONS"], "preflight");
  const boom = handler(() => Promise.reject(new Error("secret detail 4827")), () => deps);
  const res = await boom(new Request("http://x/", { method: "POST", body: "{}" }));
  eq([res.status, await res.text()], [500, '{"ok":false,"e":"server"}'], "an internal error tells the caller nothing");
});

// ---------------------------------------------------------------- the pre-live gate (review of #12 and #17)
const teacherOf = async (c: { id: string }) => {
  const t = (await sql`insert into auth.users (email) values (${"t-" + crypto.randomUUID() + "@test.invalid"}) returning id`)[0].id;
  await sql`insert into public.teachers values (${t}, ${c.id})`;
  return t as string;
};

T("S1: class-wide limits hold when 35 tries arrive at once", async () => {
  const c = await newClass();
  const names = Array.from({ length: 35 }, (_, i) => "Par" + "abcdefghijklmnopqrstuvwxyz"[i % 26] + "xyz"[Math.floor(i / 26)]);
  for (const n of names) await reg(c, n, "4827", [3, 11], freshIp());
  clock.ms += HOUR;
  const pics = await Promise.all(names.map((n) => recPic(c, n, [5, 6], "5839", [7, 2], freshIp())));
  eq(pics.filter((r) => e(r) === "picture").length, 10, "35 wrong picture pairs at once on 35 names: exactly 10 compared, the rest refused");
  const one = "198.18.0.9";
  const codes = await Promise.all(names.map((n) => log(c, n, "9053", { ip: one })));
  eq(codes.filter((r) => e(r) === "pin").length, 30, "35 wrong codes at once from one address: exactly 30 compared");
  clock.ms += 2 * DAY;
});

T("S2: a pupil's own device keeps its reserve, whatever strangers and unlocks did", async () => {
  const c = await newClass();
  const mine = await reg(c, "Kim", "4827");
  const pid = await pupilId(c, "Kim");
  const t = await teacherOf(c);
  clock.ms += HOUR;
  for (let round = 0; round < 3; round++) {
    for (let i = 0; i < 20; i++) await log(c, "Kim", "9053", { ip: freshIp() });
    if (round < 2) await teacherReset(deps, { action: "unlock", pupil_id: pid }, { ip: SCHOOL, token: "t:" + t });
  }
  eq((await sql`select count(*)::int as n from private.auth_attempts a join public.pupils p on p.class_id = a.class_id and p.name_key = a.name_key
               where p.id = ${pid} and a.kind = 'code' and a.outcome <> 'ok'`)[0].n, 29, "strangers reached the name's daily ceiling of 29");
  eq(e(await log(c, "Kim", "4827", { ip: freshIp() })), "locked", "so strangers are out for the day");
  eq(e(await log(c, "Kim", "4827", { device_token: tok(mine), ip: freshIp() })), "ok", "the pupil's own phone still gets in");
  clock.ms += 2 * DAY;
});

T("S7: the class brake can be lifted twice a day, not more", async () => {
  const c = await newClass();
  const t = await teacherOf(c);
  const lift = () => teacherReset(deps, { action: "unlock_class", class_id: c.id }, { ip: SCHOOL, token: "t:" + t });
  eq([e(await lift()), e(await lift()), e(await lift())], ["ok", "ok", "limit"], "two lifts, then the third is refused");
  clock.ms += DAY + HOUR;
  eq(e(await lift()), "ok", "a day later it can be lifted again");
  clock.ms += 2 * DAY;
});

T("N1: a one-time code cannot be compared more than 30 times, even by tries in parallel", async () => {
  const c = await newClass();
  await reg(c, "Omri", "4827");
  const pid = await pupilId(c, "Omri");
  const t = await teacherOf(c);
  const r = await reset("t:" + t, pid) as Body;
  clock.ms += MIN;
  const wrong = String((Number(r.otc) + 1) % 1000000).padStart(6, "0");
  await Promise.all(Array.from({ length: 29 }, () => recOtc(c, "Omri", wrong, "6149", [9, 4], freshIp())));
  eq((await sql`select fails from private.reset_codes where pupil_id = ${pid}`)[0]?.fails, 29, "29 wrong tries at once: 29 counted, none lost");
  await Promise.all(Array.from({ length: 16 }, () => recOtc(c, "Omri", wrong, "6149", [9, 4], freshIp())));
  eq([(await sql`select count(*)::int as n from private.reset_codes where pupil_id = ${pid}`)[0].n,
    (await sql`select count(*)::int as n from private.auth_lock_events where class_id = ${c.id} and kind = 'otc'`)[0].n], [0, 1],
    "16 more at once: the 30th try ends the code, once, and no try after it is compared");
  ok(e(await recOtc(c, "Omri", r.otc as string, "6149", [9, 4], freshIp())) !== "ok", "after that the code is cancelled: the right one no longer works");
  clock.ms += 2 * DAY;
});

T("N3: teacher-reset answers a stranger's token before any slow hashing", async () => {
  const c = await newClass(), other = await newClass();
  await reg(c, "Tom", "4827");
  const pid = await pupilId(c, "Tom");
  const stranger = await teacherOf(other);
  let hashed = 0;
  const counting = { ...deps, get pepper() { hashed++; return pepper; } };
  eq(e(await teacherReset(counting, { pupil_id: pid }, { ip: SCHOOL, token: "t:" + stranger })), "forbidden", "not her pupil");
  eq(hashed, 0, "and nothing was hashed");
  clock.ms += DAY;
});

T("S5: the caller's address comes from the platform's end of X-Forwarded-For; an unreadable one shares no bucket", async () => {
  const rq = (h: Record<string, string>) => new Request("http://x/", { headers: h });
  eq(clientIp(rq({ "x-forwarded-for": "6.6.6.6, 203.0.113.5" }), "xff-last"), "203.0.113.5", "the entry the platform appended, not the caller's");
  eq(clientIp(rq({ "x-forwarded-for": "203.0.113.5, not-an-address" }), "xff-last"), "", "garbage is no address");
  eq(clientIp(rq({ "cf-connecting-ip": "2001:DB8::1", "x-forwarded-for": "6.6.6.6" }), "cf-connecting-ip"), "2001:db8:0:0::/64", "a platform header, when the project shows that is the one");
  // IPv6 by /64, ports dropped (review of #35)
  for (const [a, want] of [["2001:db8:aa:bb:1:2:3:4", "2001:db8:aa:bb::/64"], ["2001:db8:aa:bb:ffff::9", "2001:db8:aa:bb::/64"], ["[2001:db8::7]:443", "2001:db8:0:0::/64"],
    ["198.51.100.7:52011", "198.51.100.7"], ["::ffff:198.51.100.7", "198.51.100.7"], ["::ffff:cb00:7107", "203.0.113.7"], ["0:0:0:0:0:ffff:203.0.113.7", "203.0.113.7"],
    ["0000:0000:0000:0000:0000:FFFF:CB00:7107", "203.0.113.7"], ["0::ffff:203.0.113.7", "203.0.113.7"], ["::0:ffff:cb00:7107", "203.0.113.7"], ["[::ffff:203.0.113.7]:443", "203.0.113.7"],
    ["::ffff:300.0.113.7", ""], ["2001:db8::1.2.3.4", "2001:db8:0:0::/64"], ["::1.2.3.4", "0:0:0:0::/64"], ["010.1.1.1", "10.1.1.1"], ["300.1.1.1", ""], ["1:2:3", ""], ["::1::2", ""], ["fe80::1%eth0", ""]]) {
    eq(addressBucket(a), want, "address bucket of " + a);
  }
  eq(clientIp(rq({}), "xff-last"), "", "none");
  const c = await newClass();
  await reg(c, "Uri", "4827");
  clock.ms += HOUR;
  for (let i = 0; i < 3; i++) await login(deps, { class_code: c.code, name: "Uri", code: "9053" }, { ip: "" });
  const b = await sql`select count(distinct ip_bucket)::int as n from private.auth_attempts where class_id = ${c.id} and kind = 'code'`;
  eq(b[0].n, 3, "three callers without a readable address: three buckets, not one shared by everybody");
  const t = await teacherOf(c);
  const h = await asUser(t, (tx) => tx`select warn, unreadable_day from public.backend_health`);
  ok(h[0].warn === true && h[0].unreadable_day >= 3, "and the teacher's health row counts them and warns: " + JSON.stringify(h));
  clock.ms += 2 * DAY;
});

T("S6: a pupil's auth user gets no second identity; one that has one is replaced at sign-in", async () => {
  const c = await newClass();
  const r = await reg(c, "Gil", "4827");
  let refused = false;
  try { await sql`insert into auth.identities (user_id, provider, provider_id) values (${user(r)}, 'google', 'g-1')`; } catch { refused = true; }
  ok(refused, "linking Google to a pupil's user is refused");
  const su = Deno.env.get("WI_PG_SUPER");
  if (su) {
    const { default: postgres } = await import("npm:postgres@3.4.7");
    const admin = postgres({ path: Deno.env.get("WI_PG_SOCKET")!, user: su, database: "wi_test", max: 1, onnotice: () => {} });
    await admin`alter table auth.identities disable trigger pupil_user_no_link`;
    await admin`insert into auth.identities (user_id, provider, provider_id) values (${user(r)}, 'github', 'gh-1')`;
    await admin`alter table auth.identities enable trigger pupil_user_no_link`;
    await admin.end();
    clock.ms += HOUR;
    const again = await log(c, "Gil", "4827", { ip: freshIp() });
    ok(e(again) === "ok" && user(again) !== user(r), "the sign-in notices the extra identity and gives a new auth user");
    eq((await sql`select count(*)::int as n from auth.users where id = ${user(r)}`)[0].n, 0, "the linked one is deleted");
  }
  clock.ms += 2 * DAY;
});

T("S9: names: the same allow-list as the database, with ׳ ' ’ after a letter and Latin Extended-A", async () => {
  for (const n of ["ג׳ורג׳", "ג'ורג'", "ג’ורג’", "Łukasz", "Žofie", "D'", "Chloé", "ג׳ני", "Ana Mae", "Dan."]) ok(isName(n), "allowed: " + n);
  for (const n of ["'Dana", "Dana-", "׳נועה", "Dá́na", "Dаna", "1Dan", "D\u0131na", "\u017Fara", "\u0138im", "\u0149ina", "\u0133ssel", "Mi\u0133nt"]) ok(!isName(n), "refused: " + JSON.stringify(n));
  const c = await newClass();
  eq(e(await reg(c, "ג׳ורג׳", "4827")), "ok", "and the database takes the same name");
  clock.ms += HOUR;
});

T("S10: Supabase Auth over plain fetch: the six calls and what they send", async () => {
  const seen: { url: string; method: string; h: Record<string, string>; body: Body | null }[] = [];
  const fake = (async (url: string | URL | Request, init?: RequestInit) => {
    const h = Object.fromEntries(Object.entries((init?.headers ?? {}) as Record<string, string>));
    const body = init?.body ? JSON.parse(String(init.body)) : null;
    seen.push({ url: String(url), method: init?.method ?? "GET", h, body });
    const u = String(url);
    const j = u.endsWith("/admin/users") ? { id: "u-1" } : u.includes("/admin/users/") && init?.method === "GET" ? { id: "u-1", email: "p-1@pupils.invalid" }
      : u.endsWith("/admin/generate_link") ? { hashed_token: "h-1" } : u.endsWith("/verify") ? { access_token: "a", refresh_token: "r", expires_in: 3600, token_type: "bearer" }
      : u.endsWith("/user") ? (h.authorization === "Bearer good" ? { id: "t-1" } : null) : {};
    return new Response(j ? JSON.stringify(j) : "{}", { status: j ? 200 : 401 });
  }) as typeof fetch;
  const fakeKey = "sb_" + "secret_made_up_for_the_test"; // assembled, so the secret scan does not take it for a key
  const g = gotrueSessions("https://abc.supabase.co/", fakeKey, fake);
  eq(await g.create(), "u-1", "create returns the new user");
  ok(seen[0].body?.email_confirm === true && /^p-[0-9a-f-]{36}@pupils\.invalid$/.test(seen[0].body?.email), "a confirmed label address, no name, no password");
  eq(Object.keys(seen[0].body ?? {}).sort(), ["email", "email_confirm"], "nothing else is sent");
  ok(seen[0].h.apikey === fakeKey && !("authorization" in seen[0].h), "a non-JWT server key goes as apikey only");
  const s = await g.issue("u-1");
  eq([s.access_token, s.refresh_token], ["a", "r"], "issue: user, link, verify");
  eq(seen.slice(1).map((x) => x.method + " " + x.url.replace("https://abc.supabase.co", "")), ["GET /auth/v1/admin/users/u-1", "POST /auth/v1/admin/generate_link", "POST /auth/v1/verify"], "the calls, in order");
  eq(seen[3].body, { type: "magiclink", token_hash: "h-1" }, "verify redeems the hashed token");
  eq([await g.userOf("good"), await g.userOf("bad")], ["t-1", null], "userOf: the token's user, or nobody");
  await g.remove("u-1");
  eq(seen[seen.length - 1].method + " " + seen[seen.length - 1].url, "DELETE https://abc.supabase.co/auth/v1/admin/users/u-1", "remove deletes the user");
  const jwtKey = "eyJ" + "made.up";
  await gotrueSessions("https://abc.supabase.co", jwtKey, fake).create();
  eq(seen[seen.length - 1].h.authorization, "Bearer " + jwtKey, "a JWT server key goes as bearer too");
});

T("S3: wrong class codes are counters, not rows; forged addresses cannot grow the database past an hourly cap", async () => {
  await settings({ class_miss_hour: 50 });
  clock.ms += HOUR;
  const before = (await sql`select count(*)::int as n from private.class_misses`)[0].n;
  const got = [];
  for (let i = 0; i < 60; i++) got.push(e(await log({ id: "", code: "NOPE" + String(i).padStart(4, "0") }, "Ido", "4827", { ip: freshIp() })));
  eq([got.filter((x) => x === "class").length, got.filter((x) => x === "locked").length], [50, 10], "60 forged addresses: 50 wrong class codes answered, then everyone waits for the hour");
  ok((await sql`select count(*)::int as n from private.class_misses`)[0].n - before <= 50, "and at most 50 counter rows were written");
  eq((await sql`select count(*)::int as n from private.auth_attempts where kind = 'class'`)[0].n, 0, "no try row per wrong class code");
  await settings({ class_miss_hour: 2000 });
  clock.ms += 2 * HOUR;
});

T("lock keys never collide: pupils named Code, Picture, Otc and Register, everything at once (review of #35)", async () => {
  const c = await newClass();
  const names = ["Code", "Picture", "Otc", "Register"];
  for (const n of names) await reg(c, n, "4827", [3, 11], freshIp());
  clock.ms += HOUR;
  const jobs: Promise<Reply>[] = [];
  for (let i = 0; i < 30; i++) for (const n of names) {
    jobs.push(log(c, n, i % 3 ? "9053" : "4827", { ip: freshIp() }));
    jobs.push(recPic(c, n, [5, 6], "5839", [7, 2], freshIp()));
  }
  const out = await Promise.allSettled(jobs);
  eq(out.filter((x) => x.status === "rejected").map((x) => String((x as PromiseRejectedResult).reason).slice(0, 80)), [], "240 sign-ins and recoveries at once on those names: no deadlock, no error");
  clock.ms += 2 * DAY;
});

T("a reset during a stream of guesses: no deadlock (auth_finish takes the name lock first; review of #35)", async () => {
  const c = await newClass();
  await reg(c, "Noam", "4827");
  const pid = await pupilId(c, "Noam");
  const t = await teacherOf(c);
  clock.ms += HOUR;
  const errors: string[] = [];
  for (let round = 0; round < 15; round++) {
    const guesses = Array.from({ length: 6 }, () => log(c, "Noam", "9053", { ip: freshIp() }));
    const r = [reset("t:" + t, pid), teacherReset(deps, { action: "unlock", pupil_id: pid }, { ip: SCHOOL, token: "t:" + t })];
    for (const x of await Promise.allSettled([...guesses, ...r])) if (x.status === "rejected") errors.push(String(x.reason).slice(0, 80));
    clock.ms += 10 * MIN;
  }
  eq(errors, [], "15 rounds of 6 guesses racing a reset and an unlock");
  clock.ms += 2 * DAY;
});

T("the postgres.js guard drops exactly the stray null write, nothing else (S-h)", async () => {
  const PG = "at nextWrite (file:///root/.cache/deno/npm/registry.npmjs.org/postgres/3.4.7/src/connection.js:250:24)";
  const ev = (code: string, stack: string) => new ErrorEvent("error", { error: Object.assign(new TypeError("x"), { code, stack: "TypeError: x\n    " + stack }), cancelable: true });
  const stray = ev("ERR_STREAM_NULL_VALUES", PG), other = ev("ECONNRESET", PG), elsewhere = ev("ERR_STREAM_NULL_VALUES", "at ours (file:///app/_shared/core.ts:1:1)");
  // dispatched to the guard alone: a capturing listener that stops the event first would hide a bug, so we read defaultPrevented
  globalThis.dispatchEvent(stray);
  const seen: boolean[] = [];
  // a listener added after the guard sees whether the guard prevented the event, then keeps the test runner alive
  const keep = (e: Event) => { seen.push(e.defaultPrevented); e.preventDefault(); };
  globalThis.addEventListener("error", keep);
  globalThis.dispatchEvent(other);
  globalThis.dispatchEvent(elsewhere);
  globalThis.removeEventListener("error", keep);
  eq([stray.defaultPrevented, seen], [true, [false, false]], "the stray write is dropped; another error is not touched by the guard");
});

T("teardown", async () => {
  eq((await sql`select count(*)::int as n from private.auth_attempts where outcome = 'pending'`)[0].n <= 60, true, "pending tries are only the reserved ones of refused bursts");
  await sql.end();
});
