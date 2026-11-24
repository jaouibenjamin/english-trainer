// Edge Function pupil-recover. The logic is in ../_shared/core.ts (recover); this file only wires it to HTTP.
import { recover } from "../_shared/core.ts";
import { ORIGINS, prodDeps } from "../_shared/deps.ts";
import { handler } from "../_shared/http.ts";

Deno.serve(handler(recover, prodDeps, ORIGINS));
