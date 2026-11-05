# Importing a Lovable backend into a local stack

This workflow covers repository exports and separately downloaded artifacts. It
collects files first, then makes local execution explicit. It does not fetch a live
Lovable project, copy real users by default, deploy anything, or convert every
export into a working app without review. Python 3.11+ is required.

## What to obtain

| Artifact | Where to obtain it | How this scaffold handles it |
| --- | --- | --- |
| Application source | Lovable Git sync or source download; extract ZIP first | Frontend/server build remains an app-specific adapter |
| Supabase SQL | `supabase/migrations/*.sql` in source export | Ordered application, transactional checksums and Supabase history |
| Drizzle SQL and journal | `drizzle/migrations/`, including `meta/_journal.json` | Journal order and Drizzle history; no Supabase CLI treatment |
| Manually saved DDL | Reviewed SQL saved from your own schema/export process | Repeat `--sql` in the intended order; no inferred policy reconstruction |
| Database structure/data/users | More → Database → Manage → Settings → Export project data | Capture `.backup` or its ZIP wrapper; inspect catalog, select, then restore |
| Per-table CSV | Database table export | Explicit schema/table/column mapping and transactional insert |
| Edge Function source | `supabase/functions/` in the source ZIP or Git-synced repository | Capture function folders, `_shared`, Deno maps and config; activate explicitly |
| Storage bytes | Download separately from More → Storage | Preserve directory structure/checksums; upload and ownership validation remain manual |
| Scheduled jobs | Inventory jobs in Lovable and database schedules; save definitions separately | `--jobs` captures a definition file; review destinations and enable manually |
| Secrets/provider settings | Inventory names; create credentials under your own accounts | Values are not exported or copied from the source `.env` |

Lovable's database export is a custom-format PostgreSQL archive with zstd compression,
not a SQL script. It includes database structure/data and user password hashes, but
not stored file bytes, Edge Function code, secrets, provider settings or API keys.
Obtain each missing artifact before calling the migration complete.

Sources checked 2026-11-05:
[Lovable database export](https://docs.lovable.dev/features/database-backups),
[Lovable external deployment](https://docs.lovable.dev/tips-tricks/external-deployment-hosting),
[Supabase self-hosted functions](https://supabase.com/docs/guides/self-hosting/self-hosted-functions).

## Source export versus database export

**Edge Function source normally comes with the project source ZIP or Git-synced
repository**, under `supabase/functions/`. It is not routinely a separate download.
Check that directory, including shared modules and Deno configuration, before looking
for another export mechanism. [Lovable's deployment guide](https://docs.lovable.dev/tips-tricks/external-deployment-hosting)
identifies the source location, and its [code export FAQ](https://docs.lovable.dev/introduction/faq)
describes source download and Git sync.

The **database backup** excludes Edge Function code. That exclusion describes the
backup archive, not the source-code bundle. Function secrets and provider credentials
also need separate configuration; downloading code does not transfer those values.

Compare the functions listed in Lovable's Edge Functions view with the latest source
export/checkout. If deployed functions have no matching source, resolve that specific
gap before migration: verify the selected project and branch, refresh Git sync or
redownload the source, then obtain any still-missing function source separately.
An absent directory establishes only that this checkout has no exported functions;
it does not prove the live backend has none.

Function **deployment** is a separate step even when the source is included. This
scaffold activates local runtime mounts; managed Supabase uses its deployment tools.
TanStack server functions stay in the Node application build.

## Collect and inspect

Run from the scaffold directory. The source is an extracted app repository; optional
arguments point to separate manual downloads. No credentials for Lovable are needed.

```sh
python3 scripts/backend.py import /path/to/export --name project-v1 \
  --database /path/to/database.backup \
  --storage /path/to/downloaded-files \
  --csv /path/to/table-exports \
  --jobs /path/to/reviewed-job-definitions.sql \
  --sql /path/to/manual-schema.sql
python3 scripts/backend.py inspect project-v1
```

Omit arguments you do not have. A database ZIP is accepted only when it contains
exactly one `.backup`; application source ZIPs must be extracted first. Directory
layout for storage downloads is preserved, not guessed from filenames. `--sql`
accepts reviewed DDL, not a replacement for the database backup restore process.

Collection writes ignored `.imports/project-v1/` with a manifest recording every
artifact's relative path, size and SHA-256. It refuses overwrite, symlinks and changed
artifacts. Directories are private and files are mode 0600. Both Git and Docker build
context exclude `.imports/`. Source `.env` files are not copied; source function
`.env*` and PEM files are skipped. Exported function code/config can themselves
contain sensitive literals, so the entire bundle stays private. Inspection prints
names/metadata and literal `Deno.env.get(...)` variable names, never SQL or values.
Dynamic secret references still need a manual inventory.

Treat bundles as immutable: import another version under a new name. Make deliberate
reviewed changes in the source copy before collecting, not inside a captured bundle.
No migration files means **missing authoritative schema**, not an invitation to
reconstruct production policies from generated types.

## Use an isolated project and select imported functions

Use a fresh scaffold copy, with its own name, ports, credentials and volumes. Do not
mix the example notes schema with an imported application's schema unintentionally.
Select the bundle before the first `make up` so sample SQL is skipped.

```sh
python3 scripts/stack.py init --name project-local --port 8094 --admin-port 19804 --mail-port 18029
python3 scripts/backend.py activate project-v1
# If needed, create .env.functions with new LOCAL/TEST credentials, then chmod 600 it.
make up
```

Activation prepares a separate runtime generation, mounts imported function code
instead of the example functions, and leaves upstream vendor files unchanged. It
does NOT execute SQL, restore data, start schedules, configure providers, or replace
the sample frontend with the imported app's source. Adapt that frontend as described
in [the SSR guide](SSR_MIGRATION.md). Default sample smoke tests need the sample
schema and are not a general validator of an imported app.

While an imported backend is selected, `make up` does not apply sample or imported
SQL. Schema changes stay explicit through the commands below.

To return to sample mounts:

```sh
python3 scripts/backend.py deactivate
make up
```

This does not remove imported database records. Use a separate fresh instance for
clean sample demonstrations rather than treating deactivation as a database reset.
Prepared runtime function generations remain under `.runtime/` until deliberately
cleaned up while no container is using them.

## Apply reviewed schema migrations

First review SQL, extensions, roles, triggers, RLS, storage bucket definitions and
external destinations. Exported SQL runs as the local database administrator; this
is not a SQL sandbox. Review job-creation statements before allowing them to run.

```sh
python3 scripts/backend.py migrate project-v1 --layout supabase
python3 scripts/backend.py migrate project-v1 --layout supabase --execute
```

Choose `--layout drizzle` when the export uses the Drizzle journal. Use `--layout
manual` for manually saved DDL, ordered as the `--sql` arguments were supplied. Do
not blindly run all three layouts if they describe the same schema.

Without `--execute`, the command reports order and validates artifacts without
opening a database. Execution targets only this project's Compose `db` service;
there is no cloud URL option. Each migration and its history entries commit in one
transaction under an advisory lock. A failed file rolls back; earlier files remain
applied. Repeating a bundle, or collecting a newer bundle with the same paths and checksums,
skips already-applied files.

Supabase-layout execution records numeric versions in
`supabase_migrations.schema_migrations`; Drizzle execution records hashes/timestamps
in `drizzle.__drizzle_migrations`. A private checksum ledger records the import
provenance. If the destination already contains an entry outside this bundle,
execution stops for baseline/history review instead of assuming equivalence. Unchanged migrations from earlier imports are recognized across bundles; renamed
files, edited applied SQL or pre-existing external history require deliberate
reconciliation. The runner does not automatically baseline an existing database. Manual SQL uses
only the private ledger. No migration-history repair is performed automatically.

Migrations with psql commands or explicit transaction control are refused. Operations
that cannot run in a transaction need a separate reviewed workflow. The runner does
not provide down migrations, parse every SQL statement for safety, or prove schema
compatibility. Inspect private `.runtime/backend-*.log` files on failure; these may
contain SQL/data and must not be pasted into public logs.

## Restore a database export selectively

Choose schema/data restoration deliberately. If migrations already created schema
or seed rows, do not restore duplicates over them. An initialized Supabase contains
managed schemas/roles/extensions; a wholesale restore can conflict with them.

```sh
python3 scripts/backend.py backup-list project-v1
# Copy .imports/project-v1/database/restore.list to a private review file.
# Edit that copy: comment out entries not being restored with semicolons.
python3 scripts/backend.py restore project-v1 --toc /path/to/reviewed.list
python3 scripts/backend.py restore project-v1 --toc /path/to/reviewed.list --execute
```

The catalog is saved privately instead of printed. `pg_restore` runs inside the
pinned database container, so host PostgreSQL tools are not required. It must support
the source archive version and zstd; an incompatible archive stops with an error.
The execution command uses one transaction, stops on error, and never adds `--clean`,
`--create`, ownership or privilege restoration. Those choices reduce collisions but
mean ownership/grants must be reviewed and applied separately from authoritative SQL.
There is no automatic retry, merge or migration baseline after a restore.

Select required data AND sequence values, reconcile any seed data, and verify new
record creation. Restoring users also requires compatible Auth schema and preserved
user IDs/relationships; sessions and provider credentials do not transfer. Test
sign-in, account links, password reset and RLS after restoration. A synthetic restore
check is not evidence that a real Lovable archive will restore without adaptation.

## Load table CSVs

Use CSV as an explicit per-table alternative to backup data, not an additional copy
of the same records. Apply authoritative schema first and respect foreign-key order.

```sh
python3 scripts/backend.py csv-load project-v1 \
  --file csv/records.csv --table public.records --columns id,name
# Add --execute after checking the file/header and target column order.
```

The loader expects comma-separated CSV with a header. It inserts inside one
transaction; constraint failures roll back. It does not infer types, merge/upsert,
remap IDs, restore sequences, recreate identities or recover missing RLS. Verify
sequence values after loading explicit serial IDs. Use a reviewed database backup
for Auth identities rather than treating CSVs as a password migration mechanism.

## Edge Functions, secrets and authentication

Activation preserves enabled functions with `index.ts`, shared modules, root/per-
function Deno import maps and the exported `verify_jwt` policy. Missing maps or custom
entrypoints fail for adapter review. The local router is generated from the pinned
upstream router outside `vendor/`; it selects auth/map settings per function. Only
known enabled slugs are served. The original blanket JWT policy is not disabled.

Set one-line function secrets explicitly in ignored `.env.functions` and `chmod 600`
the file. Runtime-managed Supabase/router values cannot be overridden there. Run
`make up` to recreate the function service when configuration changes. All functions
share this container's environment, so this is an app-level secret boundary, not a
separate secret store per function. Use scoped test credentials for external calls.

`verify_jwt=true` validates a token; it does not by itself establish signed-in-user
identity or business authorization. Legacy anon API JWTs can pass that check. Verify
user identity/permissions in function code for private data. An exported
`verify_jwt=false` function becomes public; webhook code must validate its provider
signature. Test missing/invalid credentials, ownership, CORS, webhook signatures,
dependencies and failure behavior per function. Never fix a failure by disabling
all authentication or giving a browser the service-role key.

For a changed function source, collect and activate a new bundle, then `make up`.
Relative shared imports are preserved. Remote Deno/npm imports may require internet
access and use a dependency cache; a fully offline app needs those dependencies
pinned/cached and separately verified. A successful import does not run connectors.

Managed Supabase uses its function deployment tools; self-hosted runtime code must
be installed/mounted on its host. The Fly/Render Node-only templates do not also
host Edge Runtime. TanStack server functions are part of the Node build and stay
separate from the Supabase Edge Functions deployment.

## Storage, jobs and external settings

Storage downloads are captured byte-for-byte under `storage/`. At the destination,
create buckets/policies from authoritative schema and upload bytes through the
Storage API using a reviewed bucket/object mapping. Preserve paths and original
user IDs when policies use user-folder prefixes. Restore/check object ownership,
content type and other metadata as well as the bytes. Test signed URLs, downloads,
cross-user denial and overwrite behavior. Do not copy loose files directly into
Supabase's managed storage volume and assume its metadata now exists. The tool does
not automate uploads or ownership reconstruction.

Captured job definitions are not executed. Review cron schedules, webhook/HTTP
URLs, credentials and target functions before recreating them. Keep the source and
local copies from running the same side effects concurrently. Database restores or
SQL can themselves contain job definitions; inspect the selected objects/statements
before executing them, then verify destination schedules and their first run.

Set OAuth clients/callbacks, SMTP, AI providers, payments and other connectors
separately. Secrets and connector connections are not recovered from a database
archive. Track remaining work in the migration checklist; collection is not proof
that a backend migration is complete.

## Verification

```sh
make backend-test              # offline integrity/order/plan regressions
make backend-test-integration  # starts and removes only a disposable synthetic stack
```

The integration exercise covers Supabase/Drizzle migration history, repeat execution,
RLS, rollback, mapped CSV, zstd custom backups and selected restore including sequence
values, plus imported functions/shared code/maps/secrets and mixed JWT/public policies.
For an actual export, add app-specific schema/data/Auth/Storage/function/job checks.
