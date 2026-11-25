// Test rig: the real core functions against the local PostgreSQL started by tests/functions.py, with a clock the
// tests move and a stand-in for Supabase Auth that keeps its users in the same auth.users table.
import postgres from "npm:postgres@3.4.7";
import { type Body, type Ctx, type Deps, login, recover, register, type Reply, type Sessions, type Sql, teacherReset } from "../_shared/core.ts";
import { tag } from "../_shared/crypto.ts";
import { installPgGuard } from "../_shared/pgguard.ts";
installPgGuard(); // the same guard as production (_shared/pgguard.ts)

export const sql = postgres({
  path: Deno.env.get("WI_PG_SOCKET")!,
  user: "postgres",
  database: Deno.env.get("WI_PG_DB") ?? "wi_test",
  max: 12,
  onnotice: () => {},
});
export const pepper = new TextEncoder().encode("test pepper, 32 bytes of nothing");
export const clock = { ms: Date.UTC(2027, 0, 11, 6, 0, 0) }; // a Monday morning; every test moves forward from where the last one stopped
export const MIN = 60_000, HOUR = 3_600_000, DAY = 86_400_000;

export const sessions: Sessions = {
  async create() {
    return (await sql`insert into auth.users (email) values (${"p-" + crypto.randomUUID() + "@pupils.invalid"}) returning id`)[0].id;
  },
  issue: (userId) => Promise.resolve({ access_token: "t:" + userId, refresh_token: "r:" + userId }),
  async remove(userId) {
    await sql`delete from auth.users where id = ${userId}`;
  },
  userOf: (token) => Promise.resolve(token.startsWith("t:") ? token.slice(2) : null),
};
export const deps: Deps = { sql: sql as unknown as Sql, sessions, pepper, now: () => new Date(clock.ms), serverKey: "test-server-key" };

let ipN = 0;
/** a fresh address, as an attacker with many networks would have */
export const freshIp = () => `198.51.${(++ipN >> 8) & 255}.${ipN & 255}`;
export const SCHOOL = "203.0.113.7";

export interface Cls { id: string; code: string }
let classN = 0;
export async function newClass(opt: { roster?: string[]; max?: number } = {}): Promise<Cls> {
  const code = "TEST" + String(++classN).padStart(4, "0");
  const id = (await sql`insert into public.classes (name, roster_only, max_pupils) values (${"class " + classN}, ${!!opt.roster}, ${opt.max ?? 60}) returning id`)[0].id;
  await sql`insert into private.class_codes values (${id}, decode(${await tag(pepper, "class", code)}, 'hex'))`;
  for (const n of opt.roster ?? []) await sql`insert into public.roster values (${id}, app.name_key(${n}), ${n})`;
  return { id, code };
}
export const user = (r: Reply): string => ((r as Body).session.access_token as string).slice(2);
const ctx = (ip?: string, token?: string): Ctx => ({ ip: ip ?? SCHOOL, token });

export const reg = (c: Cls, name: string, code = "4827", pictures: number[] = [3, 11], ip?: string) =>
  register(deps, { class_code: c.code, name, code, pictures }, ctx(ip));
export const log = (c: Cls, name: string, code: string, o: { ip?: string; device_token?: string; new_code?: string; pictures?: number[] } = {}) =>
  login(deps, { class_code: c.code, name, code, device_token: o.device_token, new_code: o.new_code, pictures: o.pictures }, ctx(o.ip));
export const recPic = (c: Cls, name: string, pictures: number[], new_code = "5938", new_pictures: number[] = [7, 2], ip?: string) =>
  recover(deps, { class_code: c.code, name, pictures, new_code, new_pictures }, ctx(ip));
export const recOtc = (c: Cls, name: string, otc: string, new_code = "6049", new_pictures: number[] = [9, 4], ip?: string) =>
  recover(deps, { class_code: c.code, name, otc, new_code, new_pictures }, ctx(ip));
export const reset = (token: string | undefined, pupil_id: string) => teacherReset(deps, { pupil_id }, ctx(SCHOOL, token));

/** run SQL as the API would for a signed-in user: role authenticated and that user's JWT claims */
// deno-lint-ignore no-explicit-any
export function asUser<T>(uid: string, fn: (tx: any) => Promise<T>): Promise<T> {
  return sql.begin(async (tx) => {
    await tx`select set_config('request.jwt.claims', ${JSON.stringify({ sub: uid, role: "authenticated" })}, true)`;
    await tx`set local role authenticated`;
    return await fn(tx);
  }) as Promise<T>;
}
export const saves = async (uid: string): Promise<boolean> => {
  try {
    const base = await asUser(uid, (tx) => tx`select updated_at from public.progress`);
    const r = await asUser(uid, (tx) => tx`select public.save_progress(${JSON.stringify({ at: clock.ms })}::text::jsonb, ${base[0]?.updated_at ?? null}) as v`);
    return r[0].v.ok === true;
  } catch {
    return false;
  }
};

export function eq(got: unknown, want: unknown, what: string) {
  const a = JSON.stringify(got), b = JSON.stringify(want);
  if (a !== b) throw new Error(`${what}: got ${a}, want ${b}`);
}
export function ok(cond: unknown, what: string) {
  if (!cond) throw new Error(what);
}
export const e = (r: Reply): string => (r.ok ? "ok" : r.e);
export const settings = (o: Record<string, number>) => sql`update private.settings set ${sql(o)}`;
export const pupilId = async (c: Cls, name: string): Promise<string> => (await sql`select id from public.pupils where class_id = ${c.id} and name_key = app.name_key(${name})`)[0].id;
