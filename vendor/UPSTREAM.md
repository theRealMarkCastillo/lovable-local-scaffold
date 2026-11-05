# Pinned official Supabase distribution

Source: https://github.com/supabase/supabase/tree/self-hosted/v0.8.3/docker
Tag: self-hosted/v0.8.3
Commit: bc27d2661edd09a5d0b8d76ce33da6d4071a756e

vendor/supabase contains the unmodified Docker distribution. Apache-2.0 license
is retained in vendor/SUPABASE-LICENSE. Container components have their own licenses.
Generated local adaptations are in scripts/stack.py: scoped container names/network
aliases, loopback-only ports, admin/pooler profiles, named data volumes, and unique
local credentials. compose.yaml adds the example web app, Mailpit, local SMTP
settings, and the example function mount. Review upstream changes before updating.
