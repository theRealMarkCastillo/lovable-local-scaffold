# Optional hosted paths

No resources are provisioned or deployed by this repository. Local behavior and
Compose validation do not establish cloud correctness.

## Path A: frontend container + managed Supabase

This is the most direct hosted counterpart when preserving Supabase SDK calls.
Deploy the same web Dockerfile on Fly or Render; use a separate managed Supabase
project for Auth, database APIs, Storage, Realtime and Functions. Apply the reviewed
app migrations, configure private buckets/policies, and deploy function source there.
Our sample SQL runner is local-only; use the destination's reviewed migration tool.

`compose.hosted.yaml` runs just the web container against an external backend:

```sh
# Create .env.hosted from .env.hosted.example; supply only public client values.
docker compose --env-file .env.hosted -f compose.hosted.yaml up --build -d
```

This command **uses a real external backend**; it is not a fully local validation
mode. Use a development backend with synthetic data. Set its site/redirect URLs to
the web origin, configure SMTP/social providers and verify external callbacks.
The sample frontend's relative function calls work with its configured Supabase URL.
If importing another frontend, inspect its build-time configuration and SSR behavior.

`cloud/render.yaml` and `cloud/fly.web.toml` are web-only examples. They do not deploy
Supabase or migrate data. Set `SUPABASE_BROWSER_URL` to the hosted project's HTTPS
API URL and `SUPABASE_BROWSER_KEY` to its public anon/publishable key. Do not set
service-role credentials. Local `/supabase/*` routes are unused in this mode.
Use the provider's runtime config/secrets settings and verify actual deployment.

## Path B: self-host the stack on your own VM

The official Supabase Docker distribution is intended to support self-hosting.
A VM that runs Compose can run the complete stack, but this repository's settings
are development defaults, not a production deployment definition. Provide HTTPS
at the ingress, review every port and route, protect admin access, configure real
SMTP, secure disks/backups, and plan upgrades, resource sizing and restore drills.
Never copy the local `.env` or synthetic local credentials into production.

Multiple stateful Supabase services are not equivalent to a small stateless app
container. Database and file volumes must persist, and failures/maintenance need
operational handling. Studio/Mailpit must not become public with a copied config.
The upstream minimum for the full stack is 4 GB RAM, with 8 GB+ recommended.

## Path C: replace Supabase components with an explicit API stack

A Neon Postgres connection alone does not reproduce the Supabase SDK interfaces.
Neon also offers Auth and a PostgREST-compatible Data API, so describing it as only
Postgres is incomplete. Adopting those interfaces still requires explicit identity,
RLS and application migration; it is not a tested URL-only replacement for this stack.
[Neon Data API](https://neon.com/blog/a-postgrest-compatible-data-api-now-on-neon).
Keeping Supabase Auth/RLS/Storage/etc. on a different database requires validating
its extensions, roles, schema requirements and connection assumptions; this repo
does not claim a self-hosted Supabase-on-Neon configuration is supported/tested.
Alternatively, redesign the app around an API, OIDC provider and S3 storage, using
the separate local-cloud-demo as a reference. That is a deliberate application
migration and should not be combined with the first local compatibility exercise.

References:
- https://supabase.com/docs/guides/self-hosting/docker
- https://render.com/docs/docker
- https://fly.io/docs/reference/configuration/

## TanStack Node image on Fly or Render

Use `web-tanstack/Dockerfile` with repository-root build context. Templates:
`cloud/render.tanstack.yaml` and `cloud/fly.tanstack.toml`. These run the Node app
itself; local nginx and the local backend are not deployed. Set PUBLIC_URL,
SUPABASE_BROWSER_URL, SUPABASE_BROWSER_KEY and SUPABASE_SERVER_URL explicitly to
a separate development backend. The browser URL must be publicly reachable;
the server URL may use the same HTTPS API or a private route accessible to the host.
Only the first three values are serialized as public configuration. Do not provide
service-role keys. Apply the sample schema before using the sample server check.
The image binds 0.0.0.0 and honors PORT; /health checks the app process, not every
backend service. The connection button separately exercises backend access.

This reference reads runtime configuration through a server loader, unlike most
Lovable exports with embedded VITE_* build configuration. Preserve and configure
both browser build values and server runtime values for an actual export.

Local validation does not prove provider behavior. Cloud deployment, custom domains,
SMTP/OAuth callbacks, provider secrets and resource sizing remain untested here.

For the Node-only Compose form, copy `.env.hosted.tanstack.example` to an ignored
`.env.hosted.tanstack`, configure a development backend, then run:

```sh
docker compose --env-file .env.hosted.tanstack -f compose.hosted.tanstack.yaml up --build -d
```

This mode intentionally calls the configured external development backend. It does
not start a local Supabase or automatically convert its database to Neon.

For repository and manual backend exports, use the [backend import runbook](BACKEND_IMPORT.md).
