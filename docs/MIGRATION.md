# Migrating an exported Lovable application

## Scope: preserve the backend contract

This scaffold demonstrates Supabase-compatible local APIs. It does not export data
from Lovable, connect to your accounts, rewrite an app, migrate production users,
or reimplement every Lovable connector. Start with a copy and synthetic data.

First identify whether the app uses Lovable's built-in backend or a separately
owned Supabase project. Also identify static React/Vite versus a server framework
such as TanStack Start. They require different hosting containers.

Run the read-only inventory helper against an exported folder:

```sh
python3 scripts/inventory.py /absolute/path/to/export
```

It reports likely interfaces and file locations without printing source lines,
secrets or `.env` values. Static matches are leads, not proof of runtime behavior.

Run `python3 scripts/preflight.py /path/to/export` as well for framework and
cross-platform lockfile checks. See [SSR migration lessons](SSR_MIGRATION.md) for
the tested TanStack Start dashboard case and optional Keycloak integration.

## Suggested migration sequence

1. Get the export/Git checkout and dependency lock. Build it independently before
   replacing this reference frontend. Keep a recoverable copy of the source/backend.
2. Inventory `supabase-js`, generated client setup, auth helpers, database migrations,
   RLS/grants/triggers/extensions, storage buckets/policies, Realtime subscriptions,
   Edge Functions, scheduled jobs, secrets, server routes and external API calls.
3. Separate **frontend hosting** from **backend migration**. A local frontend can
   still be calling the original cloud backend; that is not a fully local migration.
4. Start a fresh local Supabase database. Replace the sample migration with the app's
   reviewed migration sequence **before first use**; don't combine unrelated sample
   schemas blindly. This runner records checksums and rejects edited applied files.
5. Add synthetic fixtures for application data. Reproduce RLS, policies, grants,
   triggers, functions and required extensions, not just table definitions. Verify
   anonymous access denial and two-user/tenant isolation through the same browser API.
6. Configure the exported client with this local gateway URL and anon/public key.
   Exported Vite `VITE_*` values may be build-time; this example uses runtime config.
   Never replace browser anon credentials with a service-role key to bypass errors.
7. Add function source and its secrets explicitly. Our sample mounts only `analyze`;
   additional functions need mounts/configuration. Keep function JWT checks and
   user authorization. Per-function authorization can still be required even when
   the runtime validates a JWT (an anon API key can itself be a valid JWT).
8. Recreate bucket settings and object policies. Actual files and metadata are a
   separate migration; a database dump alone does not copy object bytes.
9. Configure local signup/confirmation/recovery URLs and email capture. Social login
   providers need their own development clients and registered callbacks. In this
   Supabase variant provider credentials belong to Auth, not to local Keycloak.
10. Replace any Lovable-managed AI gateway, connector proxy or secret-injection
    dependency with a provider adapter/credentials or a deliberate local fixture.
    Stripe, Google, Apple, mail delivery and AI providers remain external when real.
11. Inspect runtime network calls. Exercise core flows with the original backend
    unavailable or blocked in the browser, without disrupting the original service.
    Confirm no writes are going to a production project.
12. Validate the chosen hosted path separately. Keep production data/user migration
    and cutover planning out of the initial local demo exercise.

## Evidence required before calling a migration complete

Record these separately; a green login screen does not establish all of them:

| Evidence | What to establish |
| --- | --- |
| Framework/build | Correct static or server adapter; clean target-OS build; lock changes reviewed |
| Configuration isolation | Original env files unchanged; old backend URL/key absent from generated browser output; privileged keys absent from frontend |
| Data/schema | Authoritative migrations versus explicitly labeled local reconstructions; preserve grants, policies, triggers, functions and object bytes |
| Identity | Signup/confirmation, returning login, refresh/logout and provider callbacks; independent local identities |
| Authorization | Anonymous denial and two-user/tenant isolation through the real API; decide whether dashboard pages themselves are public |
| Network behavior | Browser egress recorded/blocked for exercised paths; inspect server destinations separately |
| Product behavior | Core interactions and settled desktop/mobile rendering, not just HTTP 200 responses |
| Scope/state | What was only configured, what was runtime-tested, and what remains local/uncommitted/undeployed |

Pause finite UI animations or wait for them to settle before judging chart screenshots.
The dashboard's animated funnel looked incomplete in an early capture even though
its settled rendering and interactions were correct.

## Identity and authorization

Do not automatically merge accounts by email or copy production identities into
development. A deliberate user migration must preserve foreign-key ownership,
provider identifiers and password-hash compatibility where supported, and account
for session/token changes, recovery, verification and provider policy. New local
users are the default in this repo. An existing cloud access token should not be
accepted by a fresh local project's independent signing keys.

Supabase uses browser access to APIs protected by RLS. The earlier FastAPI/Keycloak
scaffold uses a different trust model. Replacing one with the other is an application
migration, not a connection-string change. Neon alone is Postgres, not the Supabase
Auth/PostgREST/Storage/Realtime/Functions platform.

## What should be optional?

Add SMTP capture, scheduler/worker, Redis, S3 backend, telemetry or search only when
required by the imported app. Do not add competing authentication systems or file
backends simply because another template includes them. A browser-only connector
used by the Lovable editor is different from a runtime dependency in the exported app.

References:
- https://docs.lovable.dev/tips-tricks/deployment-hosting-ownership
- https://docs.lovable.dev/integrations/supabase
- https://supabase.com/docs/guides/self-hosting/docker
- https://supabase.com/docs/guides/local-development

For repository and manual backend exports, use the [backend import runbook](BACKEND_IMPORT.md).
