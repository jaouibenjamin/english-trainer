// Input rules. Names: the allow-list of the database's CHECK (app.name_ok, 0001_schema.sql), applied after NFC and
// squeezing spaces, so the function answers "input" instead of the table refusing the row: Hebrew letters, Latin
// letters (Latin-1 and Latin Extended-A: é, Ł, Ž), and space ' ’ ׳ ״ . - inside; 2 to 20; starts with a letter; ends
// with a letter, a dot, or ' ’ ׳ right after a letter.
// without ı Ĳ ĳ ĸ ŉ ſ (U+0131-U+0133, U+0138, U+0149, U+017F): Dına and Dina must not be two pupils (review of #35)
const L = "A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u0130\u0134-\u0137\u0139-\u0148\u014A-\u017E\u05D0-\u05EA";
const M = `${L}\u05F3\u05F4\u2019' .-`;
export const NAME_RE = new RegExp(`^[${L}](?:[${M}]{0,18}[${L}.]|(?:[${M}]{0,17}[${L}])?[\u05F3\u2019'])$`);
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

/** Codes everybody tries first (docs/BACKEND.md 4.2): four equal digits, runs up or down also across 9-0, abab, aabb,
    years 19xx and 20xx (408 codes), anything that reads as a date, DDMM or MMDD (a classmate often knows the
    birthday), and the 14 keypad lines listed in the doc. 970 of the 10,000 in all. */
const KEYPAD = new Set(["2580", "0852", "1470", "0741", "3690", "0963", "1357", "2468", "9753", "8642", "1379", "7913", "1397", "2684"]);
const DAYS = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const isDate = (day: number, month: number) => month >= 1 && month <= 12 && day >= 1 && day <= DAYS[month - 1];
export function isWeakCode(code: string): boolean {
  const d = [...code].map(Number);
  // runs up or down, also across 9-0 (7890, 8901, 0987: review N4)
  const step = (d[1] - d[0] + 10) % 10;
  const run = (step === 1 || step === 9) && (d[2] - d[1] + 10) % 10 === step && (d[3] - d[2] + 10) % 10 === step;
  const a = Number(code.slice(0, 2)), b = Number(code.slice(2));
  return (d[0] === d[1] && d[1] === d[2] && d[2] === d[3]) || run || (d[0] === d[2] && d[1] === d[3]) || (d[0] === d[1] && d[2] === d[3]) ||
    code.startsWith("19") || code.startsWith("20") || isDate(a, b) || isDate(b, a) || KEYPAD.has(code);
}
