"""Read-only hints from a local export. Never print source snippets or .env contents."""
from pathlib import Path
import json
import os
import re
import sys
if len(sys.argv)!=2:raise SystemExit("Usage: python3 scripts/inventory.py /path/to/export")
root=Path(sys.argv[1]).resolve()
if not root.is_dir():raise SystemExit("Export folder does not exist")
skip={".git","node_modules","dist","build",".next",".runtime",".venv","vendor"}
patterns={"supabase_client":r"@supabase/supabase-js|createClient\(","supabase_auth":r"supabase\.auth|signInWithOAuth", "storage":r"\.storage\.from\(","realtime":r"postgres_changes|\.channel\(","functions":r"functions\.invoke|Deno\.serve", "possible_lovable_runtime":r"ai\.gateway\.lovable|lovable-api|lovable\.dev", "server_framework":r"@tanstack/react-start|@tanstack/start|next/server"}
result={"root":str(root),"matches":{key:[] for key in patterns},"migration_files":[],"function_files":[],"package_dependencies":{}}
def candidates():
 for current, dirs, names in os.walk(root,followlinks=False):
  dirs[:] = [name for name in dirs if name not in skip and not (Path(current)/name).is_symlink()]
  for name in names: yield Path(current)/name
for p in candidates():
 rel=p.relative_to(root)
 if p.is_symlink() or any(part in skip for part in rel.parts) or not p.is_file() or p.name.startswith('.env') or p.stat().st_size>1000000:continue
 if p.name=='package.json':
  try:
   package=json.loads(p.read_text());result["package_dependencies"][str(rel)]=sorted(set(package.get('dependencies',{}))|set(package.get('devDependencies',{})))
  except (ValueError,UnicodeError):pass
 if 'migrations' in rel.parts and p.suffix=='.sql':result['migration_files'].append(str(rel))
 if 'functions' in rel.parts and p.suffix in ('.ts','.js'):result['function_files'].append(str(rel))
 if p.suffix not in ('.js','.jsx','.ts','.tsx','.json','.sql','.toml'):continue
 try:text=p.read_text()
 except UnicodeError:continue
 for name,pattern in patterns.items():
  if re.search(pattern,text):result['matches'][name].append(str(rel))
print(json.dumps(result,indent=2))
