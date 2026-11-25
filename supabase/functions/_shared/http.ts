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
  return addressBucket(raw.trim());
}

/** One bucket per IPv4 address, and per /64 for IPv6 (a home or school gets a whole /64, so per address would be
    2^64 fresh tries: review of #35). A port is dropped ("1.2.3.4:5678", "[2001:db8::1]:443"); anything else is "". */
export function addressBucket(a: string): string {
  let m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?::\d{1,5})?$/.exec(a);
  if (m) return m.slice(1, 5).every((x) => Number(x) <= 255) ? m.slice(1, 5).map(Number).join(".") : "";
  m = /^\[([0-9A-Fa-f:.]+)\](?::\d{1,5})?$/.exec(a);
  const v6 = (m ? m[1] : a).toLowerCase();
  if (!/^[0-9a-f:.]{2,45}$/.test(v6) || !v6.includes(":")) return "";
  const halves = v6.split("::");
  if (halves.length > 2) return "";
  const part = (x: string) => (x ? x.split(":") : []);
  const head = part(halves[0]), tail = halves.length === 2 ? part(halves[1]) : [];
  const last = halves.length === 2 ? tail : head;
  if (last.length && /\./.test(last[last.length - 1])) { // an IPv4 address at the end (::ffff:1.2.3.4): two groups
    const q = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(last.pop()!);
    if (!q || !q.slice(1, 5).every((x) => Number(x) <= 255)) return "";
    const [w, x, y, z] = q.slice(1, 5).map(Number);
    last.push(((w << 8) | x).toString(16), ((y << 8) | z).toString(16));
  }
  const fill = halves.length === 2 ? 8 - head.length - tail.length : 0;
  const groups = [...head, ...Array(Math.max(0, fill)).fill("0"), ...tail];
  if (groups.length !== 8 || fill < 0 || (halves.length === 2 && fill < 1) || !groups.every((g) => /^[0-9a-f]{1,4}$/.test(g))) return "";
  const n = groups.map((g) => parseInt(g, 16));
  // an IPv4 address written as IPv6, in any of its spellings (::ffff:1.2.3.4, ::ffff:102:304, 0:0:0:0:0:ffff:..., 0::ffff:...):
  // the IPv4 address's own bucket (review of #35 and #41)
  if (n.slice(0, 5).every((x) => x === 0) && n[5] === 0xffff) return [n[6] >> 8, n[6] & 255, n[7] >> 8, n[7] & 255].join(".");
  return groups.slice(0, 4).map((g) => g.replace(/^0+(?=.)/, "")).join(":") + "::/64";
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
