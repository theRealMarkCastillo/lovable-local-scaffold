# Lovable stack: verified sources and scaffold decisions

Checked 2026-11-05. Product defaults can change; inspect each export's package.json,
server configuration, migrations and integrations. No source below establishes that
all exports are identical or that this scaffold reproduces every Cloud feature.

| Topic | Verified detail | Scaffold decision |
| --- | --- | --- |
| Framework | FAQ dates the TanStack Start default to May 13, 2026; Enterprise June 22 | New instances default to Node SSR; keep Vite for older exports |
| Backend | Cloud uses Supabase's open-source foundation | Preserve SDK interfaces using pinned self-hosted services |
| Node export | Lovable documents Nitro node-server output and Node.js 22 | Build inside Linux Docker and run standalone .output |
| Configuration | Actual exports may embed browser values at build time and read server values at runtime | Keep both contracts explicit; never serialize all environment values |
| Identity/integrations | Providers, secrets, jobs, AI and connectors require separate migration work | Local email is the baseline; Keycloak/social login stays opt-in |

Sources: [Lovable FAQ](https://docs.lovable.dev/introduction/faq),
[built-in backend](https://docs.lovable.dev/features/cloud),
[external deployment guide](https://docs.lovable.dev/tips-tricks/external-deployment-hosting),
[TanStack partnership](https://tanstack.com/blog/lovable-partnership).

## Framework and dependencies

TanStack Start still uses React and can use Vite as its build tool. “TanStack” does
not mean React or Vite disappears; the distinction here is a server application
versus an older browser-only build. The minimal reference uses ordinary upstream
TanStack plugins plus Nitro, not Lovable's build wrapper or platform hooks. Existing
exports should retain their wrapper and required options rather than copying both
sets of plugins. Versions are locked for this example, not asserted as universal
Lovable defaults. Nitro's Vite integration is under active development.

Sources: [TanStack setup](https://tanstack.com/start/latest/docs/framework/react/build-from-scratch),
[hosting](https://tanstack.com/start/latest/docs/framework/react/guide/hosting),
[Nitro Node runtime](https://nitro.build/deploy/runtimes/node).

## Backend coverage and operations

The pinned Supabase stack supplies database, Auth, REST API, Storage, Realtime and
Edge Runtime. Mailpit captures local messages. Studio is optional. Full upstream
self-hosting guidance lists 4 GB RAM minimum and 8 GB+ recommended; a subset's actual
needs must be measured. Redis, Keycloak, MinIO, workers and telemetry are modules to
add when app behavior needs them, not required containers for every export.

The template intentionally retains the pinned stack's legacy HS256 key path. Current
upstream recommends generating asymmetric signing and new API keys. An upgrade must
be separately tested across Auth, gateway, functions and client compatibility. Local
success with the legacy path does not validate key rotation or production hardening.

Sources: [Supabase Docker](https://supabase.com/docs/guides/self-hosting/docker),
[pinned source provenance](../vendor/UPSTREAM.md).

## Hosting and secrets

Fly accepts a Dockerfile and a configured internal service port. Render supports
Docker web services, runtime environment settings and HTTP health paths. Their
configuration files describe only the application image in the managed-backend
path. Local Compose is not automatically translated into provider-managed services.
Keep secrets in provider settings; don't reference sensitive Docker build arguments.

Sources: [Fly configuration](https://fly.io/docs/reference/configuration/),
[Render Docker](https://render.com/docs/docker),
[Render health checks](https://render.com/docs/health-checks),
[Render environment settings](https://render.com/docs/configure-environment-variables).

## Database alternative boundary

Neon has authentication and a PostgREST-compatible Data API in addition to Postgres.
That broadens possible migration paths. This scaffold has not validated replacing
Supabase's full Auth, Storage, Realtime and Functions contract with Neon services.
Keep that as an explicit adapter/migration project rather than claiming changing a
connection string makes an exported application compatible.

Source: [Neon Data API](https://neon.com/blog/a-postgrest-compatible-data-api-now-on-neon).
