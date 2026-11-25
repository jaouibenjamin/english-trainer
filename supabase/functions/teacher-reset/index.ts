// Edge Function teacher-reset. The logic is in ../_shared/core.ts (teacherReset); this file only wires it to HTTP.
import { teacherReset } from "../_shared/core.ts";
import { ORIGINS, prodDeps } from "../_shared/deps.ts";
import { handler } from "../_shared/http.ts";

Deno.serve(handler(teacherReset, prodDeps, ORIGINS));
