"""Collect and review Lovable backend exports; execute only explicit local actions.

Python 3.11+; SQL execution uses the pinned local PostgreSQL parser. Import never executes exported code or SQL.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IMPORTS = ROOT / '.imports'
RUNTIME = ROOT / '.runtime'
BUILTINS = {'SUPABASE_URL', 'SUPABASE_PUBLIC_URL', 'SUPABASE_ANON_KEY',
            'SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_DB_URL', 'JWT_SECRET'}


def fail(message):
    raise SystemExit(message)


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, indent=2) + '\n')
    path.chmod(0o600)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not path.parts or '\\' in value:
        fail('Unsafe artifact path')
    return Path(*path.parts)


def bundle_path(name):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,49}', name):
        fail('Bundle name must start with a lowercase letter/digit and use only lowercase letters, digits, _ or -')
    return IMPORTS / name


def load(name):
    root = bundle_path(name)
    if root.is_symlink():
        fail('Symlinked bundles are refused')
    data = json.loads((root / 'manifest.json').read_text())
    if data.get('version') != 1 or data.get('name') != name:
        fail('Unsupported manifest')
    for item in data['files']:
        path = root / safe_relative(item['path'])
        if path.resolve() != path.absolute() or not path.is_file() or digest(path) != item['sha256']:
            fail('Artifact missing, symlinked or changed; create a new import bundle')
    expected = {item['path'] for item in data['files']}
    for folder in ('supabase', 'drizzle', 'manual'):
        for path in (root / folder).rglob('*'):
            if path.is_symlink() or (path.is_file() and path.relative_to(root).as_posix() not in expected):
                fail('Untracked or symlinked source artifact; create a new bundle')
    return root, data


def collect(args):
    target = bundle_path(args.name)
    source = args.source.expanduser().resolve()
    if not source.is_dir():
        fail('Source must be an extracted repository/export directory')
    if IMPORTS.resolve() != IMPORTS.absolute():
        fail('Symlinked import roots are refused')
    IMPORTS.mkdir(mode=0o700, exist_ok=True)
    IMPORTS.chmod(0o700)
    if target.exists():
        fail('Bundle already exists; use a new name instead of overwriting it')
    temp = Path(tempfile.mkdtemp(prefix='.collect-', dir=IMPORTS))
    files = []
    skipped = []
    def copy_file(src, dest, kind):
        if src.is_symlink() or not src.is_file():
            fail('Only regular files are accepted; symlinks are refused')
        dst = temp / safe_relative(dest)
        dst.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(src, dst)
        dst.chmod(0o600)
        files.append({'path': dest, 'kind': kind, 'bytes': dst.stat().st_size, 'sha256': digest(dst)})
    def tree(src, dest, kind, filter_source=False):
        if not src.exists():
            return
        if src.resolve() != src.absolute() or not src.is_dir():
            fail('Expected a real artifact directory')
        for current, dirs, names in os.walk(src, followlinks=False):
            current = Path(current)
            for name in list(dirs):
                child = current / name
                if child.is_symlink():
                    fail('Symlinks in artifact directories are refused')
                if filter_source and name in {'node_modules', '.git', '.runtime', '.imports'}:
                    dirs.remove(name)
            for name in sorted(names):
                child = current / name
                rel = child.relative_to(src)
                if filter_source and (name == '.env' or name.startswith('.env.') or name.endswith('.pem')):
                    skipped.append(str(PurePosixPath(dest) / rel.as_posix()))
                    continue
                copy_file(child, str(PurePosixPath(dest) / rel.as_posix()), kind)
    try:
        tree(source / 'supabase/migrations', 'supabase/migrations', 'supabase-sql', True)
        tree(source / 'drizzle/migrations', 'drizzle/migrations', 'drizzle', True)
        tree(source / 'supabase/functions', 'supabase/functions', 'function', True)
        if (source / 'supabase/config.toml').exists():
            copy_file(source / 'supabase/config.toml', 'supabase/config.toml', 'config')
        for index, sql in enumerate(args.sql or []):
            if not re.fullmatch(r'[a-zA-Z0-9_.-]+', sql.name): fail('Use simple alphanumeric SQL filenames')
            copy_file(sql, f'manual/sql/{index:04d}-{sql.name}', 'manual-sql')
        if args.database:
            src = args.database
            if src.is_symlink() or not src.is_file(): fail('Database export must be a regular file')
            if src.suffix.lower() == '.zip':
                with zipfile.ZipFile(src) as archive:
                    candidates = [info for info in archive.infolist() if not info.is_dir() and info.filename.endswith('.backup')]
                    if len(candidates) != 1:
                        fail('Database ZIP must contain exactly one .backup file')
                    info = candidates[0]
                    safe_relative(info.filename)
                    dst = temp / 'database/export.backup'
                    dst.parent.mkdir(mode=0o700)
                    with archive.open(info) as incoming, dst.open('wb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                    dst.chmod(0o600)
                    files.append({'path': 'database/export.backup', 'kind': 'database', 'bytes': dst.stat().st_size, 'sha256': digest(dst)})
            else:
                copy_file(src, 'database/export.backup', 'database')
            with (temp / 'database/export.backup').open('rb') as archive:
                if archive.read(5) != b'PGDMP':
                    fail('Expected a PostgreSQL custom-format backup; save plain reviewed DDL with --sql instead')
        if args.storage:
            tree(args.storage, 'storage', 'storage')
        if args.csv:
            tree(args.csv, 'csv', 'csv')
        if args.jobs:
            copy_file(args.jobs, 'jobs/' + args.jobs.name, 'jobs')
        files.sort(key=lambda item: item['path'])
        manifest = {'version': 1, 'name': args.name, 'files': files, 'skipped_sensitive_source_files': skipped}
        private_json(temp / 'manifest.json', manifest)
        temp.rename(target)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    print(f'Collected {len(files)} artifacts into .imports/{args.name}; no SQL, function or restore executed.')
    inspect(args.name)


def migration_order(root, data, layout):
    paths = [item['path'] for item in data['files']]
    if layout == 'supabase':
        files = sorted(path for path in paths if path.startswith('supabase/migrations/') and path.endswith('.sql'))
        if any(not re.fullmatch(r'[a-zA-Z0-9_.-]+', Path(path).name) for path in files): fail('Use simple SQL filenames')
        versions = [Path(path).name.split('_', 1)[0] for path in files]
        if any(not version.isdigit() for version in versions) or len(set(versions)) != len(versions):
            fail('Supabase migrations need unique numeric version prefixes')
        return [(path, version, None) for path, version in zip(files, versions)]
    if layout == 'manual':
        return [(path, Path(path).stem, None) for path in sorted(paths) if path.startswith('manual/sql/')]
    if not any(path.startswith('drizzle/migrations/') for path in paths):
        return []
    journal = root / 'drizzle/migrations/meta/_journal.json'
    if not journal.exists():
        fail('Drizzle SQL requires its authoritative meta/_journal.json order')
    entries = json.loads(journal.read_text())['entries']
    order = []
    for item in entries:
        tag = item['tag']
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', tag) or not isinstance(item['when'], int):
            fail('Unsupported Drizzle journal entry')
        path = f'drizzle/migrations/{tag}.sql'
        if path not in paths:
            fail('Drizzle journal references a missing SQL file')
        order.append((path, tag, item['when']))
    present = {path for path in paths if path.startswith('drizzle/migrations/') and path.endswith('.sql')}
    if present != {path for path, _, _ in order} or len(order) != len(present):
        fail('Drizzle journal and SQL files do not match exactly')
    if [when for _, _, when in order] != sorted({when for _, _, when in order}):
        fail('Drizzle journal timestamps must be unique and increasing')
    return order


def function_settings(root, data):
    base = root / 'supabase/functions'
    config_path = root / 'supabase/config.toml'
    config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
    settings = {}
    for child in sorted(base.iterdir()) if base.exists() else []:
        if not child.is_dir() or child.name.startswith('_'):
            continue
        if child.name == 'main' or not re.fullmatch(r'[a-zA-Z0-9_-]+', child.name):
            fail('Reserved or unsupported function directory name')
        cfg = config.get('functions', {}).get(child.name, {})
        if cfg.get('enabled', True) is False:
            continue
        if cfg.get('entrypoint') not in (None, f'./functions/{child.name}/index.ts'):
            fail('Custom function entrypoint requires an explicit adapter')
        if not (child / 'index.ts').exists():
            fail('Each active function needs index.ts')
        verify = cfg.get('verify_jwt', True)
        if not isinstance(verify, bool):
            fail('verify_jwt must be boolean')
        mapping = cfg.get('import_map')
        if mapping:
            mapping = safe_relative(mapping)
            if not mapping.parts or mapping.parts[0] != 'functions':
                fail('Import maps must be inside exported supabase/functions')
            mapping = Path(*mapping.parts[1:])
        else:
            mapping = next((Path(child.name) / name for name in ('deno.json', 'deno.jsonc') if (child / name).exists()), None)
            mapping = mapping or next((Path(name) for name in ('deno.json', 'deno.jsonc') if (base / name).exists()), None)
        if mapping and not (base / mapping).is_file():
            fail('Configured function import map is missing')
        settings[child.name] = {'verify_jwt': verify, 'import_map': f'/home/deno/functions/{mapping.as_posix()}' if mapping else None}
    return settings


def inspect(name):
    root, data = load(name)
    layouts = {}
    for layout in ('supabase', 'drizzle', 'manual'):
        try:
            order = migration_order(root, data, layout)
            layouts[layout] = [path for path, _, _ in order]
        except SystemExit as error:
            layouts[layout] = {'requires_review': str(error)}
    required = set()
    for item in data['files']:
        if item['kind'] == 'function' and Path(item['path']).suffix in ('.ts', '.js'):
            required.update(re.findall(r'Deno\.env\.get\([\'"]([A-Z][A-Z0-9_]*)[\'"]\)', (root / item['path']).read_text()))
    try:
        functions = function_settings(root, data)
    except (SystemExit, tomllib.TOMLDecodeError) as error:
        functions = {'requires_review': str(error)}
    print(json.dumps({'bundle': name, 'migration_order': layouts, 'functions': functions,
                      'function_secret_names': sorted(required - BUILTINS),
                      'artifact_counts': {kind: sum(item['kind'] == kind for item in data['files']) for kind in sorted({item['kind'] for item in data['files']})},
                      'manual_configuration': ['OAuth/provider credentials and callbacks', 'Function secrets (values are not exported)', 'Scheduled jobs and webhook endpoints', 'AI/connector provider replacements', 'Storage ownership/object mapping and CSV table mapping'],
                      'note': 'Checksums verified. Names/metadata only; no source, SQL, user data or secret values printed.'}, indent=2))


def local_stack():
    import stack
    stack.render()
    return stack


def logged(stack, *args, **kwargs):
    RUNTIME.mkdir(exist_ok=True, mode=0o700)
    log = RUNTIME / ('backend-' + uuid.uuid4().hex + '.log')
    with log.open('wb') as output:
        log.chmod(0o600)
        try:
            return stack.compose(*args, stdout=output, stderr=subprocess.STDOUT, **kwargs)
        except subprocess.CalledProcessError:
            fail(f'Local action failed; inspect private log {log}. Earlier migrations may already be applied; do not retry blindly.')


def sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def migrate(args):
    root, data = load(args.name)
    order = migration_order(root, data, args.layout)
    if not order:
        fail('No migrations in the selected layout')
    from sql_safety import validate_sql
    for path, _, _ in order:
        validate_sql((root / path).read_text())
    print(json.dumps({'layout': args.layout, 'order': [path for path, _, _ in order], 'execute': args.execute}))
    if not args.execute:
        return
    stack = local_stack()
    for path, version, when in order:
        sql = (root / path).read_text()
        checksum = digest(root / path)
        key = sql_literal(args.layout + '/' + path)
        ledger = ''
        if args.layout == 'supabase':
            ledger = f'''CREATE SCHEMA IF NOT EXISTS supabase_migrations;
CREATE TABLE IF NOT EXISTS supabase_migrations.schema_migrations(version text PRIMARY KEY, statements text[], name text);
DO $$ BEGIN IF EXISTS(SELECT 1 FROM supabase_migrations.schema_migrations WHERE version >= {sql_literal(version)}) THEN RAISE EXCEPTION 'Version already exists outside this import; review baseline/history'; END IF; END $$;
'''
            record = f'INSERT INTO supabase_migrations.schema_migrations(version,name) VALUES ({sql_literal(version)},{sql_literal(Path(path).stem)});'
        elif args.layout == 'drizzle':
            ledger = f'''CREATE SCHEMA IF NOT EXISTS drizzle;
CREATE TABLE IF NOT EXISTS drizzle.__drizzle_migrations(id serial PRIMARY KEY, hash text NOT NULL, created_at bigint);
DO $$ BEGIN IF EXISTS(SELECT 1 FROM drizzle.__drizzle_migrations WHERE created_at >= {when}) THEN RAISE EXCEPTION 'Drizzle history already contains this or a later migration'; END IF; END $$;
'''
            record = f"INSERT INTO drizzle.__drizzle_migrations(hash,created_at) VALUES ('{checksum}',{when});"
        else:
            record = ''
        command = f'''BEGIN;
SELECT pg_advisory_xact_lock(879311);
CREATE SCHEMA IF NOT EXISTS scaffold_imports;
REVOKE ALL ON SCHEMA scaffold_imports FROM PUBLIC, anon, authenticated;
CREATE TABLE IF NOT EXISTS scaffold_imports.applied(name text PRIMARY KEY, checksum text NOT NULL, first_bundle text NOT NULL);
SET LOCAL standard_conforming_strings=on;
SELECT EXISTS(SELECT 1 FROM scaffold_imports.applied WHERE name={key}) AS applied \\gset
\\if :applied
DO $$ BEGIN IF (SELECT checksum FROM scaffold_imports.applied WHERE name={key}) <> '{checksum}' THEN RAISE EXCEPTION 'Import checksum changed'; END IF; END $$;
\\else
{ledger}
{sql}
{record}
INSERT INTO scaffold_imports.applied VALUES ({key},'{checksum}',{sql_literal(args.name)});
\\endif
COMMIT;
'''
        logged(stack, 'exec', '-T', 'db', 'psql', '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', 'postgres', input=command.encode())
        print('Migration ready:', path)


def activate(name):
    root, data = load(name)
    settings = function_settings(root, data)
    RUNTIME.mkdir(exist_ok=True, mode=0o700)
    # New generation keeps an already active mount intact if preparation fails.
    stage = Path(tempfile.mkdtemp(prefix='functions-', dir=RUNTIME))
    for slug, cfg in settings.items():
        shutil.copytree(root / 'supabase/functions' / slug, stage / slug)
    for child in (root / 'supabase/functions').iterdir() if (root / 'supabase/functions').exists() else []:
        if child.name.startswith('_') or child.is_file():
            if child.is_dir(): shutil.copytree(child, stage / child.name)
            else: shutil.copyfile(child, stage / child.name)
    main = (ROOT / 'vendor/supabase/volumes/functions/main/index.ts').read_text()
    old = "  if (req.method !== 'OPTIONS' && VERIFY_JWT) {"
    new = "  const slug = new URL(req.url).pathname.split('/')[1];\n  const policies = JSON.parse(Deno.env.get('SCAFFOLD_FUNCTION_POLICIES') || '{}');\n  if (!Object.hasOwn(policies, slug)) return new Response('Not found', {status:404});\n  if (req.method !== 'OPTIONS' && policies[slug].verify_jwt !== false) {"
    if main.count(old) != 1 or main.count('const importMapPath = `/home/deno/functions/deno.jsonc`') != 1:
        fail('Pinned function router changed; adapter needs review')
    main = main.replace(old, new).replace('const importMapPath = `/home/deno/functions/deno.jsonc`', 'const importMapPath = policies[service_name].import_map || undefined')
    (stage / 'main').mkdir(mode=0o700)
    (stage / 'main/index.ts').write_text(main)
    for path in stage.rglob('*'):
        path.chmod(0o700 if path.is_dir() else 0o600)
    private_json(RUNTIME / 'active-backend.json', {'name': name, 'policies': settings, 'directory': stage.name})
    print('Activated local bundle configuration. Run make up; imported SQL is NOT applied automatically.')
    print('Public function slugs:', ', '.join(slug for slug, cfg in settings.items() if not cfg['verify_jwt']) or '(none)')


def backup(args):
    root, data = load(args.name)
    if not any(item['path'] == 'database/export.backup' and item['kind'] == 'database' for item in data['files']):
        fail('No captured database backup in bundle')
    archive = root / 'database/export.backup'
    if not archive.exists(): fail('No database backup in bundle')
    stack = local_stack()
    if args.action == 'backup-list':
        # Catalog may disclose object names; save it privately instead of printing it.
        target = root / 'database/restore.list'
        with archive.open('rb') as incoming, target.open('wb') as output:
            target.chmod(0o600)
            stack.compose('exec', '-T', 'db', 'pg_restore', '--list', stdin=incoming, stdout=output, stderr=subprocess.PIPE)
        print(f'Wrote private restore catalog: {target}. Copy/edit it to select entries; no restore executed.')
        return
    if not args.toc or not args.toc.is_file(): fail('Restore requires --toc with a reviewed selection list')
    selection = args.toc.read_text()
    selected = [line for line in selection.splitlines() if line.strip() and not line.lstrip().startswith(';')]
    if not selected: fail('Restore selection is empty')
    print(f'Restore plan: {len(selected)} selected entries; no --clean, ownership or grants; local Compose database only.')
    if not args.execute: return
    remote = '/tmp/scaffold-restore-' + uuid.uuid4().hex + '.list'
    stack.compose('cp', str(args.toc.resolve()), 'db:' + remote, stdout=subprocess.DEVNULL)
    try:
        with archive.open('rb') as incoming:
            logged(stack, 'exec', '-T', 'db', 'pg_restore', '--exit-on-error', '--single-transaction', '--no-owner', '--no-privileges', '--use-list', remote, '-U', 'postgres', '-d', 'postgres', stdin=incoming)
    finally:
        stack.compose('exec', '-T', 'db', 'rm', '-f', remote, stdout=subprocess.DEVNULL)
    print('Selected restore completed. Verify schema, rows, sequences, identity and RLS; a restore is not an idempotent migration.')


def csv_load(args):
    root, data = load(args.name)
    relative = safe_relative(args.file).as_posix()
    if not any(item['path'] == relative and item['kind'] == 'csv' for item in data['files']):
        fail('Choose a captured CSV artifact from this bundle')
    identifiers = args.table.split('.')
    columns = args.columns.split(',')
    if len(identifiers) != 2 or any(not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', item) for item in identifiers + columns):
        fail('Use schema.table and a comma-separated list of simple column names')
    print(json.dumps({'file': relative, 'table': args.table, 'columns': columns, 'execute': args.execute}))
    if not args.execute: return
    table = '.'.join('"' + item + '"' for item in identifiers)
    names = ','.join('"' + item + '"' for item in columns)
    command = f'\\copy {table} ({names}) FROM STDIN WITH (FORMAT csv, HEADER true)'
    stack = local_stack()
    with (root / relative).open('rb') as incoming:
        logged(stack, 'exec', '-T', 'db', 'psql', '-v', 'ON_ERROR_STOP=1', '--single-transaction', '-U', 'postgres', '-d', 'postgres', '-c', command, stdin=incoming)
    print('CSV load completed. This inserts rows; it does not merge or remap identities.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    imp = sub.add_parser('import')
    imp.add_argument('source', type=Path)
    imp.add_argument('--name', required=True)
    imp.add_argument('--sql', type=Path, action='append', help='Reviewed manually saved DDL, ordered as supplied; not a database dump')
    for option in ('database', 'storage', 'csv', 'jobs'):
        imp.add_argument('--' + option, type=Path)
    for action in ('inspect', 'activate', 'backup-list'):
        sub.add_parser(action).add_argument('name')
    sub.add_parser('deactivate')
    mig = sub.add_parser('migrate')
    mig.add_argument('name')
    mig.add_argument('--layout', choices=('supabase', 'drizzle', 'manual'), required=True)
    mig.add_argument('--execute', action='store_true')
    restore = sub.add_parser('restore')
    restore.add_argument('name')
    restore.add_argument('--toc', type=Path, required=True)
    restore.add_argument('--execute', action='store_true')
    csv = sub.add_parser('csv-load')
    csv.add_argument('name')
    csv.add_argument('--file', required=True)
    csv.add_argument('--table', required=True)
    csv.add_argument('--columns', required=True)
    csv.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if args.action == 'import': collect(args)
    elif args.action == 'inspect': inspect(args.name)
    elif args.action == 'migrate': migrate(args)
    elif args.action == 'activate': activate(args.name)
    elif args.action == 'csv-load': csv_load(args)
    elif args.action == 'deactivate':
        (RUNTIME / 'active-backend.json').unlink(missing_ok=True)
        print('Default sample configuration selected. Run make up. No imported data was removed.')
    else: backup(args)


if __name__ == '__main__':
    main()
