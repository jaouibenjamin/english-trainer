// Production wiring: secrets from the function environment, one database connection per worker.
// PUPIL_PEPPER (32 random bytes, base64) is set once with `supabase secrets set`; it is never in the repo, the
// database or a chat. SUPABASE_URL, SUPABASE_DB_URL and the server key are provided by the platform.
import postgres from "npm:postgres@3.4.7";
import type { Deps, Sql } from "./core.ts";
import { gotrueSessions } from "./gotrue.ts";

let cached: Deps | undefined;
const need = (name: string): string => {
  const v = Deno.env.get(name);
  if (!v) throw new Error("missing secret"); // which one is in the deploy checklist, not in a log a pupil could trigger
  return v;
};

export function prodDeps(): Deps {
  if (cached) return cached;
  const pepper = Uint8Array.from(atob(need("PUPIL_PEPPER")), (c) => c.charCodeAt(0));
  if (pepper.length < 32) throw new Error("pepper too short");
  const sql = postgres(need("SUPABASE_DB_URL"), { max: 2, idle_timeout: 20, prepare: false, onnotice: () => {} });
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? need("SUPABASE_SECRET_KEY");
  cached = { sql: sql as unknown as Sql, sessions: gotrueSessions(need("SUPABASE_URL"), key), pepper, now: () => new Date(), serverKey: key };
  return cached;
}
export const ORIGINS = Deno.env.get("ALLOWED_ORIGINS") ?? undefined;
