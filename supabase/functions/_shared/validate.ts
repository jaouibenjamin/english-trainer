// Input rules. Same name rule as the Sheet backend (backend/Code.gs NAME_RE) so nothing changes for the pupils.
export const NAME_RE = /^[\p{L}\p{M}'’״׳ .\-]{2,20}$/u;
export const normName = (x: unknown): string => String(x ?? "").trim().replace(/\s+/g, " ");
export const isName = (x: unknown): x is string => typeof x === "string" && NAME_RE.test(normName(x));
export const isCode = (x: unknown): x is string => typeof x === "string" && /^\d{4}$/.test(x);
export const isOtc = (x: unknown): x is string => typeof x === "string" && /^\d{6}$/.test(x);
export const normClassCode = (x: unknown): string => String(x ?? "").trim().toUpperCase();
export const isClassCode = (x: unknown): x is string => typeof x === "string" && /^[A-Z0-9-]{4,16}$/.test(normClassCode(x));
/** the random id the game keeps on the device; only used hashed */
export const isDevice = (x: unknown): x is string => typeof x === "string" && /^[A-Za-z0-9_-]{16,64}$/.test(x);
export const isPicture = (x: unknown, choices: number): x is number => Number.isInteger(x) && (x as number) >= 1 && (x as number) <= choices;
export const isUuid = (x: unknown): x is string =>
  typeof x === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(x);
