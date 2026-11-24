// The four functions' logic, free of HTTP and of Supabase, so it runs unchanged against a local PostgreSQL in tests.
// Rules (docs/BACKEND.md 4.3, 4.4): validate everything, trust nothing from the caller, record a try before hashing,
// do the same work and give the same answer whether a name exists or not, never log or return a secret.
import { hex, kdf, legacySheetHash, randomBytes, randomDigits, tag, unhex } from "./crypto.ts";
import { isClassCode, isCode, isDevice, isName, isOtc, isPicture, isUuid, normClassCode, normName } from "./validate.ts";

/** postgres.js tagged template, or anything shaped like it */
// deno-lint-ignore no-explicit-any
export type Sql = (strings: TemplateStringsArray, ...values: any[]) => Promise<any[]>;

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
  expires_at?: number;
  token_type?: string;
}
/** the only part that needs Supabase Auth; see gotrue.ts for the real one */
export interface Sessions {
  /** a new auth user for a pupil (no email of anyone, no password); returns its id */
  create(): Promise<string>;
  /** a fresh session for that auth user */
  issue(userId: string): Promise<Session>;
  /** delete the auth user; best effort, never throws */
  remove(userId: string): Promise<void>;
  /** the auth user a bearer token belongs to, or null */
  userOf(token: string): Promise<string | null>;
}
export interface Deps {
  sql: Sql;
  sessions: Sessions;
  pepper: Uint8Array;
  now: () => Date;
  /** how many secret pictures the game shows; must match the client */
  pictures?: number;
}
export interface Ctx {
  ip: string;
  token?: string;
}
// deno-lint-ignore no-explicit-any
export type Body = Record<string, any>;
export type Reply = { ok: true; [k: string]: unknown } | { ok: false; e: string; wait?: number };

const ZERO = "00000000-0000-0000-0000-000000000000";
const PICTURES = 20;
const fail = (e: string, wait?: number): Reply => (wait === undefined ? { ok: false, e } : { ok: false, e, wait });

async function buckets(d: Deps, body: Body, ctx: Ctx) {
  const now = d.now();
  const day = now.toISOString().slice(0, 10);
  // the address is hashed with a random salt that lives two days; the raw address is never stored or logged
  const salt = (await d.sql`select private.ip_salt(${day}::date, ${hex(randomBytes(16))}) as v`)[0].v as string;
  return {
    now: now.toISOString(),
    dev: await tag(d.pepper, "dev", String(body.device)),
    ip: await tag(unhex(salt), "ip", ctx.ip || "unknown", 8),
    lookup: await tag(d.pepper, "class", normClassCode(body.class_code)),
  };
}

// deno-lint-ignore no-explicit-any
async function begin(d: Deps, kind: string, body: Body, ctx: Ctx): Promise<{ b: any; k: Awaited<ReturnType<typeof buckets>> }> {
  const k = await buckets(d, body, ctx);
  const b = (await d.sql`select private.auth_begin(${kind}, ${k.lookup}, ${normName(body.name)}, ${k.dev}, ${k.ip}, ${k.now}::timestamptz) as v`)[0].v;
  return { b, k };
}

async function fresh(d: Deps, purpose: "code" | "pic" | "otc", pupil: string, secret: string, iter: number) {
  const salt = randomBytes(16);
  return { salt: hex(salt), hash: await kdf(d.pepper, purpose, pupil, secret, salt, iter) };
}

/** the session for a pupil; creates and links the auth user when there is none (first sign-in, or after a sign-out everywhere) */
async function sessionFor(d: Deps, pupil: string, authUser: string | null): Promise<Session> {
  let user = authUser;
  if (!user) {
    const made = await d.sessions.create();
    user = (await d.sql`select private.link_auth_user(${pupil}::uuid, ${made}::uuid) as v`)[0].v as string;
    if (user !== made) await d.sessions.remove(made); // a parallel sign-in linked one first
  }
  return d.sessions.issue(user);
}

export async function register(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  const pics = d.pictures ?? PICTURES;
  if (!isClassCode(body.class_code) || !isName(body.name) || !isCode(body.code) || !isDevice(body.device) || !isPicture(body.picture, pics)) {
    return fail("input");
  }
  const { b, k } = await begin(d, "register", body, ctx);
  if (b.s === "locked") return fail("locked", b.wait);
  if (b.s !== "go") return fail("class");
  const id = crypto.randomUUID();
  const code = await fresh(d, "code", id, body.code, b.iter_default);
  const pic = await fresh(d, "pic", id, String(body.picture), b.iter_default);
  const r = (await d.sql`select private.register_pupil(${id}::uuid, ${b.class}::uuid, ${normName(body.name)}, ${code.salt}, ${code.hash},
                                                       ${pic.salt}, ${pic.hash}, ${b.iter_default}::int, ${k.dev}, ${k.now}::timestamptz) as v`)[0].v;
  if (r.s !== "ok") return fail(r.s); // taken | roster | full
  return { ok: true, session: await sessionFor(d, id, null), s: {}, name: r.name };
}

export async function login(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  if (!isClassCode(body.class_code) || !isName(body.name) || !isCode(body.code) || !isDevice(body.device)) return fail("input");
  const { b, k } = await begin(d, "code", body, ctx);
  if (b.s === "locked") return fail("locked", b.wait);
  if (b.s !== "go") return fail("class");
  // one slow hash on every path: against the pupil's salt, or against a throw-away one when there is nothing to compare with
  const pupil: string = b.pupil ?? ZERO;
  const salt = b.salt ? unhex(b.salt) : randomBytes(16);
  const iter: number = b.iter ?? b.iter_default;
  const hash = b.algo === "legacy-sha256"
    ? await kdf(d.pepper, "code-legacy", pupil, await legacySheetHash(String(b.legacy_salt ?? ""), body.code), salt, iter)
    : await kdf(d.pepper, "code", pupil, body.code, salt, iter);
  const r = (await d.sql`select private.auth_finish(${b.attempt}::bigint, ${hash}, ${null}::jsonb, ${k.now}::timestamptz) as v`)[0].v;
  if (!r.ok) return fail("pin"); // wrong code, no such pupil, code reset and not set yet: one answer
  if (r.legacy) { // a code carried over from the Sheet: verified, now stored in the new form
    const up = await fresh(d, "code", r.pupil, body.code, b.iter_default);
    await d.sql`select private.set_code(${r.pupil}::uuid, ${up.salt}, ${up.hash}, ${b.iter_default}::int, false, ${k.now}::timestamptz)`;
  }
  const state = (await d.sql`select private.pupil_state(${r.pupil}::uuid) as v`)[0].v;
  return { ok: true, session: await sessionFor(d, r.pupil, r.auth_user), s: state, name: r.name, needs_picture: !!r.needs_picture };
}

/** "I forgot my code": the secret picture, or the teacher's one-time code, plus the new code.
    Also `{action: "set_picture"}` for a signed-in pupil who has no picture yet (pupils who came from the Sheet). */
export async function recover(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  const pics = d.pictures ?? PICTURES;
  if (body.action === "set_picture") {
    if (!isPicture(body.picture, pics)) return fail("input");
    const user = ctx.token ? await d.sessions.userOf(ctx.token) : null;
    const me = user ? (await d.sql`select private.pupil_of_user(${user}::uuid) as v`)[0]?.v : null;
    if (!me?.pupil) return fail("forbidden");
    const iter = (await d.sql`select kdf_iter from private.settings`)[0].kdf_iter as number;
    const pic = await fresh(d, "pic", me.pupil, String(body.picture), iter);
    const done = (await d.sql`select private.set_picture(${me.pupil}::uuid, ${pic.salt}, ${pic.hash}, ${iter}::int, true) as v`)[0].v;
    return done ? { ok: true } : fail("forbidden"); // a picture that exists is changed only through recovery with a one-time code
  }
  const byOtc = body.otc !== undefined;
  if (!isClassCode(body.class_code) || !isName(body.name) || !isCode(body.new_code) || !isDevice(body.device)) return fail("input");
  if (byOtc ? !isOtc(body.otc) || !isPicture(body.new_picture, pics) : !isPicture(body.picture, pics)) return fail("input");
  const { b, k } = await begin(d, byOtc ? "otc" : "picture", body, ctx);
  if (b.s === "locked") return fail("locked", b.wait);
  if (b.s !== "go") return fail("class");
  const pupil: string = b.pupil ?? ZERO;
  const salt = b.salt ? unhex(b.salt) : randomBytes(16);
  const proof = await kdf(d.pepper, byOtc ? "otc" : "pic", pupil, byOtc ? body.otc : String(body.picture), salt, b.iter ?? b.iter_default);
  // the new code (and picture) are hashed before the answer is known, so right and wrong cost the same
  const code = await fresh(d, "code", pupil, body.new_code, b.iter_default);
  const pic = byOtc ? await fresh(d, "pic", pupil, String(body.new_picture), b.iter_default) : null;
  const next = { code_salt: code.salt, code_hash: code.hash, pic_salt: pic?.salt ?? null, pic_hash: pic?.hash ?? null, iter: b.iter_default };
  const r = (await d.sql`select private.auth_finish(${b.attempt}::bigint, ${proof}, ${JSON.stringify(next)}::jsonb, ${k.now}::timestamptz) as v`)[0].v;
  if (!r.ok) return r.wait !== undefined ? fail("locked", r.wait) : fail(byOtc ? "otc" : "picture");
  if (r.old_auth_user) await d.sessions.remove(r.old_auth_user); // the other devices are already cut off in the database
  const state = (await d.sql`select private.pupil_state(${r.pupil}::uuid) as v`)[0].v;
  return { ok: true, session: await sessionFor(d, r.pupil, null), s: state, name: r.name };
}

/** The caller must be a signed-in teacher of that pupil's class. The token decides who she is; nothing in the body does. */
export async function teacherReset(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  if (!isUuid(body.pupil_id)) return fail("input");
  const teacher = ctx.token ? await d.sessions.userOf(ctx.token) : null;
  if (!teacher) return fail("forbidden");
  const iter = (await d.sql`select kdf_iter from private.settings`)[0].kdf_iter as number;
  const otc = randomDigits(6);
  const h = await fresh(d, "otc", body.pupil_id, otc, iter);
  const r = (await d.sql`select private.teacher_reset(${teacher}::uuid, ${body.pupil_id}::uuid, ${h.salt}, ${h.hash}, ${iter}::int, ${d.now().toISOString()}::timestamptz) as v`)[0].v;
  if (!r.ok) return fail("forbidden"); // not her pupil and "no such pupil" look the same
  if (r.old_auth_user) await d.sessions.remove(r.old_auth_user);
  return { ok: true, otc, expires_at: r.expires_at, name: r.name }; // shown to the teacher once; only its hash is stored
}
