# Email locally and in cloud environments

Supabase Auth owns account confirmation, password recovery and other identity email.
The local `mail` service is Mailpit: it captures those SMTP messages instead of
sending them to real inboxes. Do not add Keycloak or another identity implementation
just to test email.

## Common scaffold commands

All three scaffold repos expose the same email command names, with backend-specific
implementation:

| Command | This Supabase scaffold | Cloud stack scaffold |
| --- | --- | --- |
| `make email-config` | Regenerate local config and apply Auth/Mailpit service settings | Apply Keycloak realm SMTP/recovery settings |
| `make email-test` | Send a synthetic signup confirmation through Auth and verify capture | Send a synthetic application SMTP message |
| `make email-smoke` | Confirm a synthetic account, recover/change password through Auth APIs, test new login and reject old password | Verify Keycloak account/reset links, new login and application SMTP capture |

Start the stack with `make up`. Open the local inbox at **http://localhost:18025**
(or the project's chosen `MAIL_PORT`). SMTP stays on the Docker network at
`mail:1025`; it is not published to the host. Mailpit uses pinned v1.32.0 and
project-scoped `mail-data` storage capped at 500 messages. Stopping containers retains
messages. An upgrade from the former in-memory Mailpit container does not preserve
its old inbox; request fresh emails after upgrading. Auth/database volumes are unchanged.

`make email-config` is optional after `make up`, which already applies generated
settings. It does not reset users, rotate database credentials, apply SQL migrations
or deploy to cloud. It may start required local dependencies. These local overrides
intentionally point Auth at Mailpit, irrespective of upstream SMTP values.

Email test/smoke commands refuse cloud/ngrok targets and use only fresh synthetic
accounts and Mailpit data. Users/messages are retained locally, like the existing
full smoke; no privileged key or account credentials are printed. These tests use
Auth directly and do not require the sample notes schema, so they can also check an
imported Supabase backend. Custom hooks, signup policies, templates and disabled
email/password auth can require project-specific tests.

The recovery check validates backend behavior, not a password-reset screen. The demo
has no dedicated reset-password form. A derived app must handle its SDK's recovery
session/PKCE exchange and implement password update UX. An imported SSR app may need
its own request-scoped server/cookie callback adapter. Do not assume this API test
establishes that UI behavior.

## App email and cloud delivery

Supabase Auth covers identity email. Application notifications/invites with business
logic can use a server/Edge Function and a chosen SMTP or email API provider; that
transport/queue/template system is not bundled here. Keep credentials out of frontend
config. Add durable retry/outbox and duplicate handling when needed, rather than
coupling delivery to a database transaction or duplicating the identity layer.

| Setting / boundary | Local Compose | Cloud |
| --- | --- | --- |
| Auth SMTP destination | `mail:1025`, local override, no credentials | Managed Auth dashboard or self-hosted Auth environment |
| Self-hosted SMTP variables | `SMTP_HOST/PORT/USER/PASS/ADMIN_EMAIL/SENDER_NAME` feed upstream `GOTRUE_SMTP_*`; local override chooses Mailpit | Set the provider's supported values and TLS behavior through your hosted Auth configuration; verify with the pinned Auth release |
| Public return URLs | Derived from `PUBLIC_URL`, including `/supabase/auth/v1/verify` | Configure hosted Auth callbacks, site URL and explicit app redirect allowlist |
| Provider credentials | No real mail provider configured | Deployment secrets / managed provider settings; verified sender domain |
| App notifications | Add a server-side adapter if needed | Same adapter with environment-specific provider credentials |

Unlike the cloud stack's Python app transport, these repos do not use
`SMTP_SECURITY/USERNAME/PASSWORD/FROM` as a universal application email contract.
Use the auth/provider's actual configuration names; command consistency does not
mean the backend settings are identical. A hosted Supabase backend's SMTP settings
are separate from the frontend container's environment. See [CLOUD.md](CLOUD.md).

## Tunnels and sensitive links

Keep Mailpit off ngrok. It contains live confirmation/recovery tokens. Changing
`PUBLIC_URL` updates generated Auth/mail-return paths, but previously sent messages
keep their old URLs; request fresh ones. The tester opens the configured public
app URL. For real inbox delivery, configure a provider sandbox/SMTP service rather
than exposing the local inbox. Local Mailpit is not provisioned by cloud manifests.

Google/Apple provider registration, account emails sent by those providers, sender
DNS/deliverability and real SMTP/cloud email runtime are separate work. See
[URLs and callbacks](URLS_AND_CALLBACKS.md) and [security](SECURITY.md).

Sources: [Supabase self-hosted Auth settings](https://supabase.com/docs/guides/self-hosting/auth/config),
[Mailpit configuration](https://mailpit.axllent.org/docs/configuration/).
