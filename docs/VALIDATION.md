# Validation — 2026-11-05

## Executed locally

- Pinned official Supabase Docker distribution `self-hosted/v0.8.3`, commit
  `bc27d2661edd09a5d0b8d76ce33da6d4071a756e`, copied with license/provenance.
- Base and admin/pooler-profile Compose configs validate. Hosted-client Compose
  config validates with placeholder public values; no external backend was contacted.
- Fresh generated signing/database/dashboard credentials; generated files are private
  and ignored. Web receives only its public backend URL and public anon key.
- React/Vite Docker build succeeds with npm lockfile. npm reported zero audit
  vulnerabilities during lock generation; this is not a full dependency/image audit.
- Default ten-service local stack starts. Repeated `make up` preserves data and
  checks the already-applied versioned migration checksum.
- `make smoke` passes on localhost and OrbStack HTTPS: signup, Mailpit confirmation,
  password login, anonymous denial, two-user RLS for reads/inserts/updates, private
  file ownership isolation, real Edge Runtime execution, anonymous function rejection,
  and logout refresh-token revocation. Existing access JWT expiration is separate.
- Chrome browser checks pass on both origins: sign-in, note creation, Realtime updates
  between two tabs, Edge Function invocation, private file upload/download, logout,
  and first-signup email confirmation using the browser's PKCE flow.
- Desktop 1280px and mobile 390px layouts inspected; no horizontal overflow.
- Switching PUBLIC_URL to `https://web.lovable-local.orb.local` updates Auth URLs,
  email verification paths, browser config and function origin. Verified TLS uses
  the existing public OrbStack CA in Python; certificate validation is not disabled.
- Fly CLI accepts the optional web manifest. Render web manifest passes its public
  JSON schema. Neither was deployed.
- Python scripts compile; read-only export inventory detects expected Supabase APIs
  in the reference frontend. Local documentation links and authored-file whitespace
  checked. Generated secrets/test fixtures are excluded from Git.

## Still pending / deliberately outside this example

- Production data/user/connector migration. A synthetic TanStack Start dashboard
  was separately adapted and tested; see SSR_MIGRATION.md.
- Turnkey SSR frontend option in this reference app. The tested case supplies an
  adapter pattern; framework-specific server session behavior remains app-specific.
- Real internet tunnel, hosted Supabase backend and cloud runtime smoke validation.
- Social providers, external SMTP delivery, recovery/invitation product flows, payment
  and AI connectors, production load, backup/restore, and comprehensive security audit.
- Optional Studio/admin and pooler runtime behavior; their Compose config is validated.
- Asymmetric/opaque key upgrade and key rotation/revocation exercises.

## State left for the user

Default stack runs at https://web.lovable-local.orb.local. Mailpit is available at
http://localhost:18025; it is loopback-only and must not be tunneled. Synthetic
smoke/browser accounts, notes, uploads and captured messages remain local. Create
an account through the app to choose your own credentials. No demo/demo-password
account is seeded here. No external OAuth clients or paid services were provisioned.
The source is now published in the private [GitHub repository](https://github.com/theRealMarkCastillo/lovable-local-scaffold).
The reviewed main commit is abb67e1; subsequent review fixes and documentation are recorded alongside this report.

## Feedback from the dashboard migration — 2026-11-05

- Fresh initialization now accepts --name, --port, --admin-port and --mail-port.
  Temporary-folder checks verified custom localhost origins, project-scoped volume
  names and refusal to overwrite an existing initialization. Invalid names, out-of-range
  ports and duplicate host ports fail before any credentials are written.
- Existing running configuration retains its lovable-local identity and selected
  OrbStack URL. `make up` and the complete Auth/email/RLS/Storage/Function/logout
  smoke check passed after the update. No existing database volumes were renamed.
- Read-only preflight identifies the dashboard as TanStack Start with managed auth,
  detects its original missing Linux optional lock entries, and reports none for
  its repaired lock. The tool does not install packages or change an export.
- SSR adapter guidance, identity boundaries, optional Keycloak and migration lessons
  are documented in SSR_MIGRATION.md and linked from the migration guide/README.
- Python compilation, Compose validation, documentation links and authored-file
  whitespace checks passed. No new cloud or social-provider runtime checks occurred.

At that checkpoint the reference frontend remained React/Vite. The next section
records the subsequently added runnable TanStack reference.

- Existing unmanaged `.env` files are refused before initialization, validation or
  origin changes; temporary-folder checks confirmed their bytes remain unchanged.
- Preflight reports environment filenames and generated database type availability
  without exposing values. The guide now includes a migration evidence checklist
  and explicitly identifies the current TanStack Start default.

## Runnable TanStack reference and source verification — 2026-11-05

- Official Lovable FAQ, backend and external-deployment documentation were checked,
  along with TanStack/Nitro, Supabase, Fly, Render and Neon sources. See
  [verified stack details](LOVABLE_STACK.md). Enterprise default date and Neon's
  Auth/Data API capabilities are included rather than assuming older defaults.
- Minimal TanStack Start reference uses locked dependencies, Nitro node-server and
  Node.js 22. New project initialization defaults to TanStack and localhost;
  temporary-folder initialization/Compose checks passed. Existing instances without
  FRONTEND_KIND remain Vite until explicitly switched.
- Linux ARM64 Docker build and TypeScript checks passed. npm reported zero audit
  vulnerabilities for the reference dependency lock at this check. Nitro reports
  upstream module-directive/bundler warnings; these did not prevent the build.
- The browser found a Nitro/Node Request-constructor incompatibility in the custom
  server entry. Preserving Nitro's request object fixed the observed failure.
- Chrome checks passed: server-rendered signed-out content, hydration, actual server
  function/backend request, independent per-response CSP nonces, real 404s, blocked
  admin API path and mobile width. Exercised browser requests stayed local; this
  does not prove every future server path or connector is local.
- Shared workbench checks passed in BOTH adapters: login, notes, two-tab Realtime,
  Edge Function, private upload/download, logout, signup and PKCE email confirmation.
  Existing backend volumes/accounts were retained during adapter switching.
- Expanded make smoke passed Auth/email/two-user RLS/private storage/function/logout
  plus SSR HTML, nonce uniqueness, no-store caching and absence of privileged values
  in the rendered document. Browser interaction checks were run separately in Chrome.
- The standalone Node Docker image rendered without nginx, ran as the node user,
  and received no service-role key, database password, JWT secret or DATABASE_URL.
  It used the existing local backend network; no external backend was contacted.
- Node Render Blueprint passed provider JSON-schema validation. Fly configuration
  passed CLI validation with a placeholder app name. These are configuration checks,
  not cloud deployments. No resources, OAuth clients or new remote repos were created.

Remaining boundaries: authenticated SSR is not implemented (sessions are browser
managed); Linux AMD64, real Google/Apple/Keycloak flows, cloud runtime, external SMTP,
key rotation and production restore/backup exercises remain unvalidated. The pinned
Supabase vendor files were not upgraded. Those changes were subsequently committed and pushed; see the current review section.

## Backend export collection and local execution — 2026-11-05

- Added an explicit backend import workflow, verified against current Lovable
  migration/export and Supabase self-hosted-function documentation. The runbook
  distinguishes source artifacts, database archives, CSVs, storage bytes, secrets,
  providers, jobs and external integrations.
- Collection is non-executing, ignores source secret files, preserves artifact
  checksums in private ignored bundles, and refuses overwrite/symlink/tampering.
  SQL, restore and CSV commands plan by default; mutations require --execute and
  target the selected local Compose database, with no remote database URL option.
- Thirteen offline regression tests passed for order, integrity, sensitive files,
  invalid archives, CSV mapping and non-executing plans.
- Disposable local synthetic-stack checks passed for Supabase version history and
  repeat/incremental bundle application, Drizzle journal order/history, RLS, failed-migration rollback,
  mapped CSV inserts/duplicate rejection, zstd custom archive inside ZIP, catalog
  inspection and selected schema/data/sequence restoration.
- Imported function tests passed for shared modules, root/per-function Deno maps,
  one-line test secrets, declared public versus JWT-verified policies, invalid token
  denial and unknown-slug denial. JWT verification alone does not prove user identity;
  legacy anon JWTs can pass it. The integration test explicitly covers that behavior.
- Disposable stack and volumes were removed by its cleanup. The default demo was
  left on its existing TanStack/origin configuration; make check, make up and the
  full sample smoke checks passed after moving sample mounts into generated config.

No real Lovable database archive, identities or stored files were provided/imported.
Storage upload/ownership mapping, real external schedules, OAuth/SMTP/provider
credentials and cloud runtime remain manual and unvalidated. Capturing all artifacts
is not equivalent to proving a particular application has fully migrated. Unsupported
custom function entrypoints and incompatible archive versions fail for adapter review.
Those source changes were subsequently committed and pushed; no cloud deployment occurred.

## Review fixes — 2026-11-05

The review findings and implementation plan are resolved locally; see
[REVIEW.md](REVIEW.md) for exact fixes, commands, test counts and runtime evidence.
Application and documentation changes include the review fixes described above. No
cloud resource or production data was changed. Earlier publication statements refer
to the historical baseline; use Git history for subsequent fixes.

### Running the added checks

Make bootstraps `.venv-tools` using Python 3.11+ and installs pinned `pglast==8.7`
from `requirements-tools.txt` ([parser documentation](https://pglast.readthedocs.io/en/latest/parser.html)). First setup needs package-download access. The parser
is developer tooling, excluded from app images; `make tools` also enables direct
`python3 scripts/...` commands via a subprocess fallback. Its PostgreSQL 18 grammar
does not prove compatibility with the pinned backend's PostgreSQL version. SQL is
still executed transactionally on that backend; unsupported operations fail there.

Run Python tests and `make frontend-test` (Node 22+) without a browser. With the local
app running, the optional browser regression requires Playwright and Chrome:

```sh
npm install --prefix .runtime/browser-tools --no-save playwright@1.62.1
make browser-test
```

Alternatively set `SCAFFOLD_PLAYWRIGHT_PATH` to an installed `playwright/index.mjs`.
The default uses installed Chrome. To use Playwright's Chromium, install that
browser explicitly and set `SCAFFOLD_BROWSER_CHANNEL=chromium`. The test reads this
project's local `.env`, creates synthetic accounts/notes/files, and refuses nonlocal
origins. Keep its captured confirmation messages private. Extra local CA trust may
be needed for OrbStack; do not disable certificate verification. The regression
uses bounded waits and leaves its synthetic records for inspection.

## URL and callback follow-up — 2026-11-05

Added the cross-environment [URL/callback contract](URLS_AND_CALLBACKS.md), including
external registrations, internal endpoints, cloud differences and imported-app limits.
`make tunnel` now reads the configured local web port; the Supabase repos also provide
`make tunnel-set` as an alias for their origin action. Dry-run checks covered the
project port, a custom port and invalid-port refusal without launching ngrok. No
running origin, external registration or cloud deployment was changed. Public-tunnel
and social-provider runtime validation remain pending.
