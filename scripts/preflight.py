"""Read-only export preflight. No provider access, secret values, installs or file changes."""
import argparse
import json
import re
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("export",type=Path)
args=parser.parse_args()
root=args.export.resolve()
package_path=root/"package.json"
if not package_path.is_file():raise SystemExit("No package.json in export folder")
package=json.loads(package_path.read_text())
deps={**package.get("dependencies",{}),**package.get("devDependencies",{})}
framework=("tanstack-start" if "@tanstack/react-start" in deps else "next" if "next" in deps else "vite-static-candidate" if "vite" in deps else "unknown")
result={"framework":framework,"needs_server_container":framework in ("tanstack-start","next"),
        "supabase_client":"@supabase/supabase-js" in deps,"lovable_auth_broker":"@lovable.dev/cloud-auth-js" in deps,
        "exported_migrations":len(list((root/"supabase/migrations").glob("*.sql"))),
        "environment_files_present":[name for name in (".env", ".env.local", ".env.production", ".env.development") if (root/name).is_file()],
        "generated_database_types_present":(root/"src/integrations/supabase/types.ts").is_file(),
        "missing_optional_lock_entries":[],"notes":[]}
if result["environment_files_present"]:result["notes"].append("Existing environment files detected; preserve them. Use a distinct local env file and explicitly exclude .env* from Docker context; do not run scaffold initialization over the export's cloud config.")
if result["needs_server_container"]:result["notes"].append("Use a server image/adapter; static nginx alone is insufficient. See docs/SSR_MIGRATION.md.")
if result["lovable_auth_broker"]:result["notes"].append("Inspect sign-in calls: Lovable-managed OAuth does not become local Supabase OAuth by changing a URL.")
if result["supabase_client"] and not result["exported_migrations"]:result["notes"].append("No exported SQL migrations found; generated types do not recover grants, RLS, triggers, or auth configuration.")
lock_path=root/"package-lock.json"
if lock_path.exists():
    lock=json.loads(lock_path.read_text());packages=lock.get("packages",{})
    def resolve(parent,name):
        current=parent
        while current:
            candidate=current+"/node_modules/"+name
            if candidate in packages:return packages[candidate]
            current=current.rsplit("/node_modules/",1)[0] if "/node_modules/" in current else ""
        return packages.get("node_modules/"+name)
    for parent,entry in packages.items():
        for name,spec in entry.get("optionalDependencies",{}).items():
            found=resolve(parent,name)
            if found is None or (re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?",spec) and found.get("version")!=spec):
                result["missing_optional_lock_entries"].append({"parent":parent,"package":name,"required":spec})
    if result["missing_optional_lock_entries"]:result["notes"].append("Lockfile lacks compatible optional packages. Validate a clean Linux build; repair the lock with npm and review version changes, rather than deleting the lock and upgrading everything.")
else:result["notes"].append("No npm lockfile; preserve/validate the export's actual package manager lock before changing package managers.")
result["notes"].append("This is static evidence only. Check browser/server network destinations and test auth, RLS and callbacks against isolated synthetic data.")
print(json.dumps(result,indent=2))
