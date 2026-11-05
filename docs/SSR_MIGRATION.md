# Migrating a real Lovable export: SSR and identity

## Current Lovable default

Lovable documents TanStack Start for new apps created from May 13, 2026
(June 22 for Enterprise workspaces); older apps use React/Vite. Treat the server adapter as the primary migration path for current
exports. The static reference frontend remains useful for learning Supabase APIs and
older exports, but it is not a universal hosting adapter.

Source: https://docs.lovable.dev/introduction/faq

## Runnable reference adapter

New instances default to the TanStack reference in `web-tanstack/`. Use
`make frontend KIND=tanstack` for an existing instance or `KIND=vite` for the static
example. Backend volumes, users and keys remain shared when switching. The Node
container has no published port; nginx is the public entry point.

This reference loads explicit public config at request time, so changing its origin
does not require embedding new values in its JavaScript bundle. Existing Lovable
exports usually use VITE_* build variables and need a rebuild. The demo keeps user
sessions in the browser and renders a signed-out shell on the server. For private
SSR data, add verified request-scoped authentication and authorization first. Never
share a privileged client or user session between requests.

A GET server function checks internal database API connectivity with the anonymous
role. It does not fetch private data. Per-response nonces allow framework hydration
scripts under CSP; HTML and serialized config use private/no-store caching. The
standalone Node image works without the local nginx container against a configured
external Supabase development backend; see CLOUD.md.

## Tested case: remix-of-revops-dashboard

The exported app used TanStack Start, Supabase Auth, Lovable-managed Google/Apple
login, and a bundled synthetic analytics dataset. It had generated profiles types
but no SQL migrations. It was run locally in a separate `revops-local` stack using
the scaffold's pinned Supabase distribution, a Node server and nginx ingress.

Verified in that app: Linux ARM64 build, local signup and captured email callback,
profile creation and two-user RLS, all SSR routes, dashboard drill-down/filters/ARR
toggle, and local sign-in/out. Browser checks blocked external HTTP; none were
attempted. TypeScript and focused lint passed. This does not establish compatibility
with every Lovable export or with Linux x64, cloud hosting, or real provider login.

## Preflight before choosing an adapter

```sh
python3 scripts/preflight.py /path/to/export
python3 scripts/inventory.py /path/to/export
```

Both tools are read-only and print no source snippets or environment secret values.
Preflight reports framework, managed auth dependency, migration presence and missing
optional npm lock entries. It does not automatically install, rewrite or migrate.

| Export | Hosting requirement |
| --- | --- |
| React + Vite with no server routes | Existing reference web Dockerfile is a candidate |
| TanStack Start | Node/server runtime plus ingress; inspect its Nitro configuration |
| Next.js or another SSR framework | Its own server build/output adapter |

A template's Dockerfile cannot be copied unchanged across these architectures.
For the tested TanStack/Nitro version, the Node adapter used `NITRO_PRESET=node-server`
and `node .output/server/index.mjs`. Inspect the installed configuration wrapper
before applying that convention to another version. Preserve required project
Vite optimizer settings and avoid duplicating plugins already supplied by Lovable.

## Node image pattern

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Inject only public backend URL/key for the specific app's Vite contract.
# Keep .env*, node_modules, output and generated local secrets out of build context.
ENV NITRO_PRESET=node-server
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/.output ./.output
USER node
CMD ["node", ".output/server/index.mjs"]
```

This Dockerfile illustrates adapting an export; the runnable reference is in
`web-tanstack/Dockerfile`. Set the actual app's public build variables explicitly. Server requests use
the internal gateway address; browsers use the selected public origin. Public Vite
values may require a rebuild when the origin changes. Never bake database passwords,
signing secrets or service-role keys into browser variables or image layers.

## Lessons to preserve

- Keep original cloud configuration intact. If an export tracks `.env`, generate
  local credentials into a distinct ignored file and explicitly exclude all `.env*`
  from Docker's context. Never initialize over the original app's configuration.
- Check clean Linux builds. The tested export's lockfile contained macOS ARM bindings
  but omitted Linux bindings for Rolldown, esbuild, Lightning CSS and other build
  tools. Restoring optional lock metadata and npm normalization fixed it without
  changing existing package versions. A simple package-lock-only refresh was not
  sufficient initially. Do not use audit-fix --force as a portability workaround.
- Treat generated database types as incomplete evidence. The case app received a
  documented, local-only profiles reconstruction; authoritative SQL must be exported
  before migrating real schema/data. Do not silently assume the same policies.
- Replace managed login deliberately. Local email login is a useful default;
  Supabase Auth remains the session/identity layer. Google/Apple need registrations.
- Preserve application access semantics and document them. The case app's analytics
  remained a public synthetic demo; adding a sign-in button does not gate server data.
- Avoid incidental cloud dependencies in local mode: fonts, telemetry, AI proxies,
  embedded backend URLs and auth brokers. Inspect browser **and server** destinations.
  Blocking browser egress is evidence for exercised browser paths, not proof about
  every server path or future connector.
- Keep stack names, ports, volumes and credentials independent. Use the scaffold's
  fresh-init name/port parameters instead of copying a live `.env` or fixed names.

## Optional Keycloak

Supabase Auth supports Keycloak as an upstream provider:

```text
App → Supabase Auth → Keycloak → optional Google/Apple/enterprise identity
App ← Supabase session ← Keycloak login
```

This preserves Supabase user IDs/session issuance and RLS. It can help shared SSO
or enterprise federation; it is not required for ordinary email-based local work.
Keycloak is **not added or configured** by this scaffold update.

A future opt-in integration needs a distinct client per app/environment, the exact
Supabase callback (`PUBLIC_URL/supabase/auth/v1/callback` here), a realm issuer URL
reachable consistently by browser and Auth container, and explicit Auth environment
passthrough for `GOTRUE_EXTERNAL_KEYCLOAK_ENABLED`, `CLIENT_ID`, `SECRET`, `URL`, and
`REDIRECT_URI` using that full Keycloak prefix. The app then calls Supabase OAuth
with provider `keycloak`. Keep provider secrets at Auth/Keycloak, never the browser.
Validate linking, first/returning login, refresh, logout and cross-user RLS. Replacing
Supabase tokens directly with Keycloak JWTs is a separate authorization migration.

References:
- https://supabase.com/docs/guides/auth/social-sign-in/auth-keycloak
- https://supabase.com/docs/guides/self-hosting/self-hosted-oauth
- https://nitro.build/deploy

For repository and manual backend exports, use the [backend import runbook](BACKEND_IMPORT.md).
