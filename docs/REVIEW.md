# Review fixes — 2026-11-05

All findings from this review are resolved in the source accompanying this report.
No cloud deployment has occurred. The original review covered authored code,
configuration and docs at abb67e1; unchanged vendor code, dependency advisories,
production operations and provider runtime were outside its scope. Entire history
is not configured for these standalone repositories.

## Plan and resolution

1. **P1 — private responses crossing account changes: fixed.** The original browser
   reproduction delayed A's notes, signed out, then showed A's result under B.
   The UI now associates private data with a user and captures an identity generation
   for async work. Auth changes clear state; stale notes, file lists, downloads,
   function results, notices and realtime callbacks are ignored. Returning to the
   same user after logout also invalidates earlier work. RLS remains the database
   authorization boundary; the UI guard protects presentation state.
2. **P2 — migration transaction aliases: fixed.** The old regex accepted
   `COMMIT WORK`, allowing partial DDL to survive a later failure. The pinned
   PostgreSQL parser rejects top-level transaction control, including aliases,
   comments/options, savepoints and prepared transactions, before SQL is sent to
   psql. Literal parsing is fixed to `standard_conforming_strings=on`; direct lexical
   setting changes are rejected. Quoted text and routine bodies containing SQL
   keywords remain supported. This is not a SQL sandbox: review trusted migration
   source, dynamic SQL/routines, extensions and destination compatibility.
3. **P2 — invalid origin persisted before rejection: fixed.** Prospective settings
   are validated before writing. Same-directory atomic replacement preserves 0600
   permissions; rejected origins or failed replacements preserve the original file.
   Existing messages retain old confirmation URLs; request fresh email after changing
   a valid origin. No running instance's origin was changed by these checks.
4. **P2 — Drizzle-only exports reported as missing schema: fixed.** Preflight
   inventories both migration layouts and reports each count and authoritative order.
   Missing/invalid Drizzle journals have a distinct warning. Missing-schema warnings
   apply only when neither layout contains SQL. Supabase-only, Drizzle-only, combined,
   malformed/missing-journal and empty fixtures pass.


## Verified outcomes

- `make check backend-test frontend-test backend-test-integration smoke`: passed;
  **24 Python tests and 3 Node identity tests**. Disposable integration verified
  Supabase/Drizzle ordering/history, repeat application, failure rollback, CSV,
  selective zstd backup restore and imported-function policies. A `CREATE TABLE;
  COMMIT WORK; SELECT 1/0;` fixture was refused with no table or history change.
- Both default TanStack images rebuilt successfully, including client/server builds
  and type checks. Vite shares the same component and identity helper; its runtime
  was not rerun for these fixes.
- `make browser-test` passed against real local Auth/RLS with both A's notes and file
  list delayed until after logout, then B's reads delayed. A's data never rendered
  under B; B's data appeared when released.
- Full Chrome login/CRUD/two-tab Realtime/function/private upload/download/logout and
  signup/email/PKCE workflows passed in each scaffold.
- Origin regressions verified invalid URL forms and simulated atomic-write failure
  leave `.env` byte-for-byte unchanged. SQL regressions cover transaction aliases,
  lexical settings, invalid SQL, quoted text and routine bodies.

Only synthetic users/data and disposable databases/stacks were used. Disposable
resources were removed; normal smoke/browser records remain local. Cloud providers,
Google/Apple login, production auth operations and a full dependency audit remain
outside this validation. Successful checks establish the cases exercised, not a
blanket security guarantee. See [VALIDATION.md](VALIDATION.md) for wider limits.
