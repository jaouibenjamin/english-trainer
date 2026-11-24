// The real Sessions: Supabase Auth through the admin API (docs/BACKEND.md 4.1).
// NOT EXERCISED BY THE LOCAL TESTS: there is no Supabase project yet. It is type-checked against the pinned
// client only. Before any pupil is moved, run the four functions once against a real project and check:
// generateLink + verifyOtp with public sign-up disabled, and that a deleted user's refresh token is dead.
import { createClient, type SupabaseClient } from "npm:@supabase/supabase-js@2.119.2";
import type { Session, Sessions } from "./core.ts";

export function gotrueSessions(url: string, serverKey: string): Sessions {
  const opts = { auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false } };
  const admin: SupabaseClient = createClient(url, serverKey, opts);
  return {
    async create() {
      // a label, not an address: .invalid can never receive mail, and it holds no name
      const { data, error } = await admin.auth.admin.createUser({ email: `p-${crypto.randomUUID()}@pupils.invalid`, email_confirm: true });
      if (error || !data.user) throw new Error("auth: create user");
      return data.user.id;
    },
    async issue(userId: string): Promise<Session> {
      const u = await admin.auth.admin.getUserById(userId);
      const email = u.data.user?.email;
      if (u.error || !email) throw new Error("auth: user");
      // a one-use sign-in token for that user; nothing is sent anywhere, it is redeemed here and now
      const link = await admin.auth.admin.generateLink({ type: "magiclink", email });
      const token_hash = link.data.properties?.hashed_token;
      if (link.error || !token_hash) throw new Error("auth: link");
      const once = createClient(url, serverKey, opts); // its own client: verifyOtp must not turn the admin client into the pupil
      const v = await once.auth.verifyOtp({ token_hash, type: "magiclink" });
      const s = v.data.session;
      if (v.error || !s) throw new Error("auth: verify");
      return { access_token: s.access_token, refresh_token: s.refresh_token, expires_in: s.expires_in, expires_at: s.expires_at, token_type: s.token_type };
    },
    async remove(userId: string) {
      try {
        await admin.auth.admin.deleteUser(userId);
      } catch { /* the database link is already cut; an orphan auth user maps to no pupil and sees nothing */ }
    },
    async userOf(token: string) {
      const { data, error } = await admin.auth.getUser(token);
      return error || !data.user ? null : data.user.id;
    },
  };
}
