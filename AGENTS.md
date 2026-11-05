# Lovable local scaffold

Standalone repo, independent of ai-companions. Local Docker/Compose app validation
is expected. No cloud deployments or provider registration without an explicit request.
Keep generated `.env` and `.runtime` files private and ignored. Never expose service-role
keys in frontend configuration, weaken RLS to fix a demo, tunnel Studio/Mailpit/admin
ports, copy production identities/data by default, or reset unrelated stacks.
Keep vendor/supabase unchanged; adaptations live in scripts/stack.py and compose.yaml.
Validate with make check, make up, make smoke. Record executed versus pending checks.
