// Edge Function pupil-register. The logic is in ../_shared/core.ts (register); this file only wires it to HTTP.
import { register } from "../_shared/core.ts";
import { ORIGINS, prodDeps } from "../_shared/deps.ts";
import { handler } from "../_shared/http.ts";

Deno.serve(handler(register, prodDeps, ORIGINS));
