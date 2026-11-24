// Input rules. Names: the same characters as the Sheet backend allowed (backend/Code.gs NAME_RE), narrowed to
// Hebrew and Latin letters and normalised (NFC), so two look-alike spellings cannot be two pupils.
export const NAME_RE = /^[\p{Script=Hebrew}\p{Script=Latin}\p{M}'’״׳ .\-]{2,20}$/u;
export const normName = (x: unknown): string => String(x ?? "").normalize("NFC").trim().replace(/\s+/g, " ");
export const isName = (x: unknown): x is string => typeof x === "string" && x.length <= 60 && NAME_RE.test(normName(x));
export const isCode = (x: unknown): x is string => typeof x === "string" && /^\d{4}$/.test(x);
export const isOtc = (x: unknown): x is string => typeof x === "string" && /^\d{6}$/.test(x);
export const normClassCode = (x: unknown): string => String(x ?? "").trim().toUpperCase();
export const isClassCode = (x: unknown): x is string => typeof x === "string" && /^[A-Z0-9-]{4,16}$/.test(normClassCode(x));
/** the token the server handed this device after a correct sign-in; only ever used hashed */
export const isDeviceToken = (x: unknown): x is string => typeof x === "string" && /^[A-Za-z0-9_-]{40,64}$/.test(x);
export const isUuid = (x: unknown): x is string =>
  typeof x === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(x);

/** the secret pictures: `count` different whole numbers from 1 to `choices`, in the order they were tapped */
export function isPictures(x: unknown, count: number, choices: number): x is number[] {
  return Array.isArray(x) && x.length === count && x.every((n) => Number.isInteger(n) && n >= 1 && n <= choices) && new Set(x).size === count;
}
export const pictureSecret = (x: number[]): string => x.join(">");

/** Codes everybody tries first: four equal digits, runs up or down, abab, aabb, years 19xx and 20xx. About 400 of 10,000. */
export function isWeakCode(code: string): boolean {
  const d = [...code].map(Number);
  const step = d[1] - d[0];
  const run = Math.abs(step) === 1 && d[2] - d[1] === step && d[3] - d[2] === step;
  return (d[0] === d[1] && d[1] === d[2] && d[2] === d[3]) || run || (d[0] === d[2] && d[1] === d[3]) || (d[0] === d[1] && d[2] === d[3]) ||
    code.startsWith("19") || code.startsWith("20");
}
