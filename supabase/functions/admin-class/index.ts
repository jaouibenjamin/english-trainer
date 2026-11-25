// Edge Function admin-class. Owner only, with the server key: create a class, rotate its code, copy phase on/off.
// The logic is in ../_shared/core.ts (adminClass); this file only wires it to HTTP.
import { adminClass } from "../_shared/core.ts";
import { ORIGINS, prodDeps } from "../_shared/deps.ts";
import { handler } from "../_shared/http.ts";

Deno.serve(handler(adminClass, prodDeps, ORIGINS));
