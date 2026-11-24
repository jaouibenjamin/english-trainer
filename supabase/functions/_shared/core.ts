// The functions' logic, free of HTTP and of Supabase, so it runs unchanged against a local PostgreSQL in tests.
// Rules (docs/BACKEND.md 4.3, 4.4): validate everything, trust nothing from the caller, record a try before hashing,
// do the same work and give the same answer whether a name exists or not, never log or return a secret.
import { b64url, hex, kdf, legacySheetHash, randomBytes, randomDigits, sameHex, tag, unhex } from "./crypto.ts";
import { isClassCode, isCode, isDeviceToken, isName, isOtc, isPictures, isUuid, isWeakCode, normClassCode, normName, pictureSecret } from "./validate.ts";

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
  /** only for admin-wrap-legacy: the caller must present exactly this key */
  serverKey?: string;
}
export interface Ctx {
  ip: string;
  token?: string;
}
// deno-lint-ignore no-explicit-any
export type Body = Record<string, any>;
export type Reply = { ok: true; [k: string]: unknown } | { ok: false; e: string; wait?: number };

const ZERO = "00000000-0000-0000-0000-000000000000";
const fail = (e: string, wait?: number): Reply => (wait === undefined ? { ok: false, e } : { ok: false, e, wait });
/** loose shape before the class's own settings are known: a short list of small whole numbers */
const picsLike = (x: unknown): x is number[] => isPictures(x, Array.isArray(x) ? x.length : 0, 99) && (x as number[]).length <= 4;

async function buckets(d: Deps, body: Body, ctx: Ctx) {
  const now = d.now();
  // the address is hashed with a random salt that lives two days; the raw address is never stored or logged
  const day = (t: Date) => t.toISOString().slice(0, 10);
  const salt = (await d.sql`select private.ip_salt(${day(now)}::date, ${hex(randomBytes(16))}) as v`)[0].v as string;
  // the same address under yesterday's salt, so a per-address limit does not start again at midnight
  const prev = (await d.sql`select private.ip_salt(${day(new Date(now.getTime() - 86_400_000))}::date, ${hex(randomBytes(16))}) as v`)[0].v as string;
  return {
    now: now.toISOString(),
    ipPrev: await tag(unhex(prev), "ip", ctx.ip || "unknown", 8),
    dev: isDeviceToken(body.device_token) ? await tag(d.pepper, "dev", body.device_token) : "",
    ip: await tag(unhex(salt), "ip", ctx.ip || "unknown", 8),
    lookup: await tag(d.pepper, "class", normClassCode(body.class_code)),
  };
}

// deno-lint-ignore no-explicit-any
async function begin(d: Deps, kind: string, body: Body, ctx: Ctx): Promise<{ b: any; k: Awaited<ReturnType<typeof buckets>> }> {
  const k = await buckets(d, body, ctx);
  const b = (await d.sql`select private.auth_begin(${kind}, ${k.lookup}, ${normName(body.name)}, ${k.dev}, ${k.ip}, ${k.ipPrev}, ${k.now}::timestamptz) as v`)[0].v;
  return { b, k };
}

/** the new code and pictures, hashed for this pupil */
async function secrets(d: Deps, pupil: string, code: string, pictures: number[], iter: number): Promise<string> {
  const cs = randomBytes(16), ps = randomBytes(16);
  return JSON.stringify({
    code_salt: hex(cs),
    code_hash: await kdf(d.pepper, "code", pupil, code, cs, iter),
    pic_salt: hex(ps),
    pic_hash: await kdf(d.pepper, "pic", pupil, pictureSecret(pictures), ps, iter),
    iter,
  });
}

/** a token for this device, handed out only after a correct sign-in; the database keeps its HMAC */
async function newDevice(d: Deps) {
  const token = b64url(randomBytes(32));
  return { token, hash: await tag(d.pepper, "dev", token) };
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

async function opened(d: Deps, r: { pupil: string; auth_user: string | null; old_auth_user?: string | null; name: string }, device?: string): Promise<Reply> {
  if (r.old_auth_user) await d.sessions.remove(r.old_auth_user); // already cut off in the database
  const st = (await d.sql`select private.pupil_state(${r.pupil}::uuid) as v`)[0].v;
  const session = await sessionFor(d, r.pupil, r.auth_user);
  return { ok: true, session, s: st.state ?? {}, updated_at: st.updated_at ?? null, name: r.name, ...(device ? { device_token: device } : {}) };
}

export async function register(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  if (!isClassCode(body.class_code) || !isName(body.name) || !isCode(body.code) || !picsLike(body.pictures)) return fail("input");
  if (isWeakCode(body.code)) return fail("weak");
  const { b, k } = await begin(d, "register", { ...body, device_token: undefined }, ctx);
  if (b.s === "locked") return fail("locked", b.wait);
  if (b.s !== "go") return fail("class");
  if (!isPictures(body.pictures, b.pic_count, b.pic_choices)) return fail("input");
  const id = crypto.randomUUID();
  const next = await secrets(d, id, body.code, body.pictures, b.iter_default);
  const dev = await newDevice(d);
  const r = (await d.sql`select private.register_pupil(${id}::uuid, ${b.class}::uuid, ${normName(body.name)}, ${next}::text::jsonb, ${dev.hash}, ${k.now}::timestamptz) as v`)[0].v;
  if (r.s !== "ok") return fail(r.s); // taken | roster | full
  return opened(d, { pupil: id, auth_user: null, name: r.name }, dev.token);
}

/** Sign in with the code. A pupil who came from the Sheet must send `new_code` and `pictures` in the same request;
    without them a right old code answers `setup` and opens nothing. */
export async function login(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  if (!isClassCode(body.class_code) || !isName(body.name) || !isCode(body.code)) return fail("input");
  const upgrade = body.new_code !== undefined || body.pictures !== undefined;
  if (upgrade && (!isCode(body.new_code) || !picsLike(body.pictures))) return fail("input");
  if (upgrade && isWeakCode(body.new_code)) return fail("weak");
  const { b, k } = await begin(d, "code", body, ctx);
  if (b.s === "locked") return fail("locked", b.wait);
  if (b.s !== "go") return fail("class");
  if (upgrade && !isPictures(body.pictures, b.pic_count, b.pic_choices)) return fail("input");
  // one slow hash on every path: against the pupil's salt, or against a throw-away one when there is nothing to compare with
  const pupil: string = b.pupil ?? ZERO;
  const salt = b.salt ? unhex(b.salt) : randomBytes(16);
  const iter: number = b.iter ?? b.iter_default;
  const hash = b.algo === "legacy-sha256"
    ? await kdf(d.pepper, "code-legacy", pupil, await legacySheetHash(String(b.legacy_salt ?? ""), body.code), salt, iter)
    : await kdf(d.pepper, "code", pupil, body.code, salt, iter);
  const next = upgrade ? await secrets(d, pupil, body.new_code, body.pictures, b.iter_default) : null;
  const dev = k.dev ? null : await newDevice(d); // a device without a token gets one, if the code is right
  const r = (await d.sql`select private.auth_finish(${b.attempt}::bigint, ${hash}, ${next}::text::jsonb, ${dev?.hash ?? ""}, ${k.now}::timestamptz) as v`)[0].v;
  if (!r.ok) return fail(r.setup ? "setup" : "pin"); // pin: wrong code, no such pupil, code reset and not set yet: one answer
  return opened(d, r, dev?.token);
}

/** "I forgot my code": the secret pictures, or the teacher's one-time code; plus the new code and new pictures. */
export async function recover(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  const byOtc = body.otc !== undefined;
  if (!isClassCode(body.class_code) || !isName(body.name) || !isCode(body.new_code) || !picsLike(body.new_pictures)) return fail("input");
  if (byOtc ? !isOtc(body.otc) : !picsLike(body.pictures)) return fail("input");
  if (isWeakCode(body.new_code)) return fail("weak");
  const { b, k } = await begin(d, byOtc ? "otc" : "picture", body, ctx);
  if (b.s === "locked") return fail("locked", b.wait);
  if (b.s !== "go") return fail("class");
  if (!isPictures(body.new_pictures, b.pic_count, b.pic_choices) || (!byOtc && !isPictures(body.pictures, b.pic_count, b.pic_choices))) return fail("input");
  const pupil: string = b.pupil ?? ZERO;
  const salt = b.salt ? unhex(b.salt) : randomBytes(16);
  const proof = await kdf(d.pepper, byOtc ? "otc" : "pic", pupil, byOtc ? body.otc : pictureSecret(body.pictures), salt, b.iter ?? b.iter_default);
  // the new code and pictures are hashed before the answer is known, so right and wrong cost the same
  const next = await secrets(d, pupil, body.new_code, body.new_pictures, b.iter_default);
  const dev = await newDevice(d); // every device the pupil had is forgotten; this one starts again
  const r = (await d.sql`select private.auth_finish(${b.attempt}::bigint, ${proof}, ${next}::text::jsonb, ${dev.hash}, ${k.now}::timestamptz) as v`)[0].v;
  if (!r.ok) return fail(byOtc ? "otc" : "picture");
  return opened(d, r, dev.token);
}

/** The caller must be a signed-in teacher of that pupil's class. The token decides who she is; nothing in the body does. */
export async function teacherReset(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  const action = body.action ?? "reset";
  if (!["reset", "unlock", "unlock_class"].includes(action) || !isUuid(action === "unlock_class" ? body.class_id : body.pupil_id)) return fail("input");
  const teacher = ctx.token ? await d.sessions.userOf(ctx.token) : null;
  if (!teacher) return fail("forbidden");
  if (action !== "reset") { // clear locks only: the code and the pictures are not touched
    const now = d.now().toISOString();
    const u = action === "unlock"
      ? (await d.sql`select private.teacher_unlock(${teacher}::uuid, ${body.pupil_id}::uuid, ${now}::timestamptz) as v`)[0].v
      : (await d.sql`select private.teacher_unlock_class(${teacher}::uuid, ${body.class_id}::uuid, ${now}::timestamptz) as v`)[0].v;
    return u.ok ? { ok: true } : fail("forbidden");
  }
  const iter = (await d.sql`select kdf_iter from private.settings`)[0].kdf_iter as number;
  const otc = randomDigits(6);
  const salt = randomBytes(16);
  const hash = await kdf(d.pepper, "otc", body.pupil_id, otc, salt, iter);
  const r = (await d.sql`select private.teacher_reset(${teacher}::uuid, ${body.pupil_id}::uuid, ${hex(salt)}, ${hash}, ${iter}::int, ${d.now().toISOString()}::timestamptz) as v`)[0].v;
  if (!r.ok) return fail("forbidden"); // not her pupil and "no such pupil" look the same
  if (r.old_auth_user) await d.sessions.remove(r.old_auth_user);
  return { ok: true, otc, expires_at: r.expires_at, name: r.name }; // shown to the teacher once; only its hash is stored
}

/** Migration, once: wraps the Sheet's fast hashes with the pepper so they never stay bare in the database.
    Only the holder of the server key may call it; a few per call so one call stays inside the CPU limit. */
export async function wrapLegacy(d: Deps, _body: Body, ctx: Ctx): Promise<Reply> {
  if (!d.serverKey || !ctx.token || !sameHex(await tag(d.pepper, "k", ctx.token), await tag(d.pepper, "k", d.serverKey))) return fail("forbidden");
  const iter = (await d.sql`select kdf_iter from private.settings`)[0].kdf_iter as number;
  const rows = (await d.sql`select private.legacy_next(8) as v`)[0].v as { pupil: string; hash: string }[];
  let remaining = 0;
  for (const row of rows) {
    const salt = randomBytes(16);
    const hash = await kdf(d.pepper, "code-legacy", row.pupil, row.hash, salt, iter);
    remaining = (await d.sql`select private.legacy_store(${row.pupil}::uuid, ${hex(salt)}, ${hash}, ${iter}::int) as v`)[0].v as number;
  }
  return { ok: true, wrapped: rows.length, remaining };
}

const CLASS_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"; // no 0/O, 1/I/L
function classCode(): string {
  let out = "";
  while (out.length < 8) for (const x of randomBytes(16)) if (x < 248 && out.length < 8) out += CLASS_ALPHABET[x % 31];
  return out;
}
/** Owner only (the server key): create a class, give a class a new code, switch the copy phase on or off.
    The class code is shown once, here; the database keeps only a keyed lookup of it. */
export async function adminClass(d: Deps, body: Body, ctx: Ctx): Promise<Reply> {
  if (!d.serverKey || !ctx.token || !sameHex(await tag(d.pepper, "k", ctx.token), await tag(d.pepper, "k", d.serverKey))) return fail("forbidden");
  if (body.action === "create" && typeof body.name === "string" && body.name.length >= 1 && body.name.length <= 40) {
    const code = classCode();
    const id = (await d.sql`select private.class_create(${body.name}, ${String(body.grade ?? "").slice(0, 20)}, ${await tag(d.pepper, "class", code)}) as v`)[0].v;
    return { ok: true, class_id: id, class_code: code };
  }
  if (body.action === "rotate" && isUuid(body.class_id)) {
    const code = classCode();
    const done = (await d.sql`select private.class_rotate(${body.class_id}::uuid, ${await tag(d.pepper, "class", code)}) as v`)[0].v;
    return done ? { ok: true, class_code: code } : fail("input");
  }
  if (body.action === "shadow_on" || body.action === "shadow_off") {
    const r = (await d.sql`select private.shadow_set(${body.action === "shadow_on"}) as v`)[0].v;
    for (const u of r.old_auth_users as string[]) await d.sessions.remove(u);
    return { ok: true, shadow_mode: r.shadow_mode, signed_out: r.old_auth_users.length };
  }
  return fail("input");
}
