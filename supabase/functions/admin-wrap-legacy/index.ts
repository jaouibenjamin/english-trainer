// Edge Function admin-wrap-legacy. Used once at migration, by the owner, with the server key.
// The logic is in ../_shared/core.ts (wrapLegacy); this file only wires it to HTTP.
import { wrapLegacy } from "../_shared/core.ts";
import { ORIGINS, prodDeps } from "../_shared/deps.ts";
import { handler } from "../_shared/http.ts";

Deno.serve(handler(wrapLegacy, prodDeps, ORIGINS));
