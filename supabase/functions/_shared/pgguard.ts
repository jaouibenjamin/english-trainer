// The postgres.js flake (review of #27, S-h): "May not write null values to stream" (ERR_STREAM_NULL_VALUES).
// Where it comes from (postgres@3.4.7, src/connection.js): write() batches small messages and schedules nextWrite()
// with setImmediate; a write that carries a callback, or 1 KB, calls nextWrite() at once, which sends the batch,
// clears the scheduled immediate and sets the batch to null. If that immediate still fires (it was already queued for
// this turn when it was cleared), nextWrite() runs again with nothing to send and calls socket.write(null), which
// throws inside the immediate: an uncaught error that ends the worker. Everything had already been written, so the
// throw is the only harm. Not reproduced here in 8 runs of the functions suite and 8,000 pipelined queries; seen by the
// reviewer twice in 11 runs, and the same driver runs in production. So this guard drops exactly that one error and
// nothing else: any other uncaught error still ends the worker as before. A patched pinned copy of the driver
// (`if (!chunk) return` in nextWrite) would be the fix at the source; this guard is the smaller change.
export function installPgGuard(): void {
  const g = globalThis as unknown as { __wiPgGuard?: boolean };
  if (g.__wiPgGuard) return;
  g.__wiPgGuard = true;
  globalThis.addEventListener("error", (e: ErrorEvent) => {
    const err = e.error as { code?: string; stack?: string } | undefined;
    // only that error, and only when it comes out of postgres.js's own connection code (review of #39); each one is
    // logged (the code only, never a value), so the dashboard shows how often it happens
    if (err && err.code === "ERR_STREAM_NULL_VALUES" && /postgres[\\/@][^\n]*connection\.js/.test(err.stack ?? "")) {
      e.preventDefault();
      console.warn("postgres.js: dropped a stray empty write (ERR_STREAM_NULL_VALUES)");
    }
  });
}
