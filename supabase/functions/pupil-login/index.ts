// Edge Function pupil-login. The logic is in ../_shared/core.ts (login); this file only wires it to HTTP.
import { login } from "../_shared/core.ts";
import { ORIGINS, prodDeps } from "../_shared/deps.ts";
import { handler } from "../_shared/http.ts";

Deno.serve(handler(login, prodDeps, ORIGINS));
