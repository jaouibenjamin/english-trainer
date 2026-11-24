// Hashing for codes, pictures and one-time codes (docs/BACKEND.md 4.2). Web Crypto only, no dependency.
//   inner  = HMAC-SHA256(pepper, purpose | pupil id | secret)
//   stored = PBKDF2-HMAC-SHA256(inner, salt, iterations) -> 32 bytes
// The pepper lives only in the functions' secrets. Without it a leaked table gives nothing.
const enc = new TextEncoder();

export const hex = (b: Uint8Array): string => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
export function unhex(s: string): Uint8Array {
  if (!/^([0-9a-f]{2})*$/i.test(s)) throw new Error("not hex");
  const out = new Uint8Array(s.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(s.slice(2 * i, 2 * i + 2), 16);
  return out;
}
export function randomBytes(n: number): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(n));
}
/** n decimal digits, each uniform (rejection sampling, no modulo bias) */
export function randomDigits(n: number): string {
  let s = "";
  while (s.length < n) {
    for (const b of randomBytes(n * 2)) if (b < 250 && s.length < n) s += String(b % 10);
  }
  return s;
}

export async function hmac(key: Uint8Array, msg: string): Promise<Uint8Array> {
  const k = await crypto.subtle.importKey("raw", key, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", k, enc.encode(msg)));
}
export async function sha256hex(s: string): Promise<string> {
  return hex(new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(s))));
}

/** how many slow hashes this process has computed; tests use it to prove every path does the same work */
export const stats = { kdf: 0 };

export type Purpose = "code" | "code-legacy" | "pic" | "otc";
export async function kdf(pepper: Uint8Array, purpose: Purpose, pupil: string, secret: string, salt: Uint8Array, iter: number): Promise<string> {
  stats.kdf++;
  const inner = await hmac(pepper, `${purpose}|${pupil}|${secret}`);
  const key = await crypto.subtle.importKey("raw", inner, "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations: iter }, key, 256);
  return hex(new Uint8Array(bits));
}

/** what the Google Sheet stored: SHA-256(salt + ":" + code), hex (backend/Code.gs hash()) */
export const legacySheetHash = (salt: string, code: string): Promise<string> => sha256hex(salt + ":" + code);

/** short, stable ids for lookups and buckets; keyed, so they cannot be reversed or recomputed without the key */
export async function tag(key: Uint8Array, label: string, value: string, bytes = 32): Promise<string> {
  return hex((await hmac(key, `${label}|${value}`)).slice(0, bytes));
}
