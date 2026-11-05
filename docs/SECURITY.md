# Security and secret boundaries

## Local default

`make init` generates fresh secrets rather than reusing upstream example values.
It creates an ignored `.env` (0600). The generated Compose file contains resolved
credentials and is also ignored under `.runtime` (directory 0700, file 0600).
Do not commit, upload, print or paste either file. Docker operators can inspect
container secrets; plaintext files are local convenience, not a secret vault.

Only the frontend/public anon key is rendered into browser config. The web
container receives no service-role key, database password or JWT signing secret.
The other services receive upstream-required credentials at runtime. Never use
frontend build variables to carry privileged keys. Read-only inventory ignores
`.env` and never prints matched source lines.

The sample follows the usual browser supabase-js model: sessions are persisted by
the SDK in browser storage, so XSS protection matters. It does **not** use the
HttpOnly BFF session pattern from local-cloud-demo. A server-rendered/SSR app needs
its framework's Supabase server/cookie integration; don't assume a static app's
session model covers server routes.

## Authorization

Postgres RLS enforces note ownership; user folders and storage RLS enforce private
file access. Buckets are not public. Frontend visibility is not access control.
The example function checks the caller through Auth, because a valid anon API key
is not an authenticated user. Never solve an RLS error by passing a service-role
key to the browser, removing policies, or disabling JWT checks globally.

The sample migration gives authenticated users explicit CRUD grants and policies;
anonymous users have no note-table privileges. Database/service roles can bypass
RLS by design, so keep those credentials privileged. Imported schemas need their
own verified policies; the sample policies don't automatically protect other tables.

## Public entry point vs administration

Public app port 8090 proxies only Auth, REST, Storage, Functions, Realtime and GraphQL
paths. It blocks Auth admin routes and gateway/Studio/database administration routes.
The raw gateway/Studio port 19800 and SMTP capture UI 18025 bind to loopback. Database,
internal service ports and pooler ports are not published. Do not tunnel the admin
or Mailpit ports. Docker/OrbStack may offer their own hostnames; consider those
local administrative surfaces too, and expose only the `web` service in a demo.

Gateway and Studio still have privileged functionality even if Studio is stopped.
The generated dashboard credentials are separate from application users. Local
Mailpit can view verification/recovery tokens. Treat messages as sensitive and
avoid logging/copying token-bearing URLs. nginx access logs are disabled; upstream
services may log request information, so inspect logs before sharing them.

## Outside local development

Choose a stable HTTPS origin, configure exact redirects, use separate provider
registrations and credentials per environment, and validate email/social login.
Local self-hosting does not replicate managed Supabase's operational protections.
Before production, review invitation/tenant policy, signup/abuse controls, API quotas,
TLS, database grants, storage quotas, dependencies/images, backup/restore, patching,
log redaction, key rotation, monitoring, revocation and operational ownership.

The pinned stack supports legacy signing keys for local compatibility. Follow
upstream guidance for asymmetric/opaque key upgrades and test every service together.
Don't rotate secrets by editing a database password in `.env` after initialization:
existing database role passwords and signing relationships require a coordinated
procedure. This template deliberately has no automatic destructive reset command.

Google/Apple/SMTP/payment/AI credentials are not configured. Supabase Auth is already
the identity layer here; Keycloak would be an optional reviewed federation choice,
not an additional mandatory local login service. Apple real login needs a registered
HTTPS domain and provider-specific key lifecycle handling.

## Identity transitions

Private UI state is user-owned and async results are checked against an identity
snapshot before being shown. Sign-out/account changes clear state and invalidate
older work, including a later sign-in by the same user. This supplements RLS; it
never replaces authorization. `make browser-test` exercises delayed notes/files
across an account switch. See [review fixes and limits](REVIEW.md).

Email capture, recovery checks and cloud SMTP configuration: [EMAIL.md](EMAIL.md).
