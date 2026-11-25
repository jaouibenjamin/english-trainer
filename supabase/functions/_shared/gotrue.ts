// The real Sessions: Supabase Auth's own HTTP API, called with plain fetch (review S10: no client library to pin,
// vendor or trust; these six calls are all we need). docs/BACKEND.md 4.1.
// NOT EXERCISED AGAINST SUPABASE BY THE LOCAL TESTS: tests/functions.py checks the requests against a stand-in;
// tests/live_check.py (stage 2) checks them against the project: generateLink + verify with sign-up off, and that a
// deleted user's refresh token is dead.
import type { Session, Sessions } from "./core.ts";

export function gotrueSessions(url: string, serverKey: string, fetchFn: typeof fetch = fetch): Sessions {
  const auth = url.replace(/\/+$/, "") + "/auth/v1";
  // the server key is sent as apikey; as a bearer only when it is a JWT (the new sb_secret_ keys are not)
  const admin = (extra: Record<string, string> = {}) => ({
    "content-type": "application/json",
    apikey: serverKey,
    ...(serverKey.startsWith("eyJ") ? { authorization: "Bearer " + serverKey } : {}),
    ...extra,
  });
  async function call(method: string, path: string, body?: unknown, headers: Record<string, string> = admin()): Promise<{ status: number; j: Record<string, unknown> | null }> {
    // a hanging Auth must not hold a function (and a pupil's sign-in) for ever: 10 s, then an error (review of #35)
    const r = await fetchFn(auth + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(10_000) });
    let j: Record<string, unknown> | null = null;
    try {
      j = await r.json();
    } catch { /* an empty answer (204) or not JSON */ }
    return { status: r.status, j };
  }
  const ok = (s: number) => s >= 200 && s < 300;
  return {
    async create() {
      // a label, not an address: .invalid can never receive mail, and it holds no name
      const r = await call("POST", "/admin/users", { email: `p-${crypto.randomUUID()}@pupils.invalid`, email_confirm: true });
      if (!ok(r.status) || typeof r.j?.id !== "string") throw new Error("auth: create user");
      return r.j.id;
    },
    async issue(userId: string): Promise<Session> {
      const u = await call("GET", `/admin/users/${encodeURIComponent(userId)}`);
      const email = u.j?.email;
      if (!ok(u.status) || typeof email !== "string") throw new Error("auth: user");
      // a one-use sign-in token for that user; nothing is sent anywhere, it is redeemed here and now
      const link = await call("POST", "/admin/generate_link", { type: "magiclink", email });
      const token_hash = link.j?.hashed_token ?? (link.j?.properties as Record<string, unknown> | undefined)?.hashed_token;
      if (!ok(link.status) || typeof token_hash !== "string") throw new Error("auth: link");
      // redeemed as an anonymous caller would, with the key as apikey only: the answer is the pupil's session
      const v = await call("POST", "/verify", { type: "magiclink", token_hash }, { "content-type": "application/json", apikey: serverKey });
      const s = v.j as Record<string, unknown> | null;
      if (!ok(v.status) || typeof s?.access_token !== "string" || typeof s?.refresh_token !== "string") throw new Error("auth: verify");
      return {
        access_token: s.access_token,
        refresh_token: s.refresh_token,
        expires_in: typeof s.expires_in === "number" ? s.expires_in : undefined,
        expires_at: typeof s.expires_at === "number" ? s.expires_at : undefined,
        token_type: typeof s.token_type === "string" ? s.token_type : undefined,
      };
    },
    async remove(userId: string) {
      try {
        await call("DELETE", `/admin/users/${encodeURIComponent(userId)}`);
      } catch { /* the database link is already cut; an orphan auth user maps to no pupil and sees nothing */ }
    },
    async userOf(token: string) {
      try {
        const r = await call("GET", "/user", undefined, { apikey: serverKey, authorization: "Bearer " + token });
        return ok(r.status) && typeof r.j?.id === "string" ? r.j.id : null;
      } catch {
        return null;
      }
    },
  };
}
