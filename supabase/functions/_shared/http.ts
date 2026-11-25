// The HTTP shell around a core function: method, size, JSON, CORS, the caller's address and token.
// It never logs a body, a name, a code or an address.
import type { Body, Ctx, Deps, Reply } from "./core.ts";

const MAX_BODY = 2048;
const DEFAULT_ORIGINS = "https://jaouibenjamin.github.io";

function cors(req: Request, allowed: string[]): Record<string, string> {
  const origin = req.headers.get("origin") ?? "";
  const h: Record<string, string> = { "vary": "Origin", "cache-control": "no-store" };
  if (allowed.includes(origin)) {
    h["access-control-allow-origin"] = origin;
    h["access-control-allow-methods"] = "POST, OPTIONS";
    h["access-control-allow-headers"] = "authorization, apikey, content-type, x-client-info";
    h["access-control-max-age"] = "86400";
  }
  return h;
}

/** The caller's address, only ever used hashed with a short-lived salt (core.ts buckets()). Review S5: the FIRST entry
    of X-Forwarded-For is whatever the caller wrote; the platform's proxy APPENDS the address it saw, so by default
    the LAST entry is taken. Which header the platform really uses is checked on the project (docs/BACKEND.md
    section 10, item 10) and set with CLIENT_IP_FROM: "xff-last" (default) or the name of a single-address header
    the platform sets itself (for example "cf-connecting-ip"). Anything that does not parse gives "", and the caller
    then gets a bucket of its own (core.ts), never one shared by everybody. */
export function clientIp(req: Request, from = Deno.env.get("CLIENT_IP_FROM") ?? "xff-last"): string {
  const raw = from === "xff-last" ? (req.headers.get("x-forwarded-for") ?? "").split(",").pop() ?? "" : req.headers.get(from) ?? "";
  const ip = raw.trim();
  return /^[0-9a-fA-F:.]{3,45}$/.test(ip) && /[0-9]/.test(ip) ? ip.toLowerCase() : "";
}

export function handler(fn: (d: Deps, body: Body, ctx: Ctx) => Promise<Reply>, deps: () => Promise<Deps> | Deps, origins?: string) {
  const allowed = (origins ?? DEFAULT_ORIGINS).split(",").map((s) => s.trim()).filter(Boolean);
  return async (req: Request): Promise<Response> => {
    const headers = { ...cors(req, allowed), "content-type": "application/json; charset=utf-8" };
    const json = (status: number, o: unknown) => new Response(JSON.stringify(o), { status, headers });
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (req.method !== "POST") return json(405, { ok: false, e: "method" });
    let body: unknown;
    try {
      const text = await req.text();
      if (text.length > MAX_BODY) return json(413, { ok: false, e: "big" });
      body = JSON.parse(text);
    } catch {
      return json(400, { ok: false, e: "input" });
    }
    if (!body || typeof body !== "object" || Array.isArray(body)) return json(400, { ok: false, e: "input" });
    const auth = req.headers.get("authorization") ?? "";
    const token = /^Bearer\s+\S+$/i.test(auth) ? auth.replace(/^Bearer\s+/i, "") : undefined;
    try {
      return json(200, await fn(await deps(), body as Body, { ip: clientIp(req), token }));
    } catch (err) {
      console.error("function error:", err instanceof Error ? err.name : "unknown"); // the kind of error only, never its text or the input
      return json(500, { ok: false, e: "server" });
    }
  };
}
