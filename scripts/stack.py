"""Adapt the pinned official stack without editing vendor files. SQL execution uses the pinned local PostgreSQL parser."""
from pathlib import Path
import argparse
import re
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import tempfile
import sys
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
RUNTIME = ROOT / ".runtime"

def env_values(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values

def write_env(values):
    # Same-directory atomic replacement; even an interrupted write stays private.
    content = "# Generated local credentials. Do not commit or paste into logs.\n" + "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
    target = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=ROOT, prefix=".env.", suffix=".tmp", delete=False) as output:
            target = Path(output.name)
            target.chmod(0o600)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(target, ENV)
    finally:
        if target is not None:
            target.unlink(missing_ok=True)


def validated_origin(value):
    if any(ord(char) <= 32 or ord(char) == 127 for char in value):
        raise SystemExit("PUBLIC_URL must not contain whitespace or control characters")
    origin = value.rstrip("/")
    try:
        parsed = urlparse(origin)
        port = parsed.port
        valid = (parsed.scheme in ("http", "https") and parsed.netloc and parsed.hostname
                 and not parsed.path and not parsed.query and not parsed.fragment
                 and parsed.username is None and parsed.password is None
                 and (port is None or 1 <= port <= 65535))
    except ValueError:
        valid = False
    if not valid:
        raise SystemExit("PUBLIC_URL must be an HTTP(S) origin, without credentials or a path")
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
        raise SystemExit("Non-loopback PUBLIC_URL requires HTTPS")
    return origin


def set_origin(value):
    initialize()
    values = env_values(ENV)
    values["PUBLIC_URL"] = validated_origin(value)
    validate_settings(values)
    write_env(values)


def jwt(secret, role):
    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
    now = int(time.time())
    header = encode(json.dumps({"alg":"HS256","typ":"JWT"},separators=(",",":")).encode())
    payload = encode(json.dumps({"role":role,"iss":"supabase-local","iat":now,"exp":now+315360000},separators=(",",":")).encode())
    message = header + "." + payload
    return message + "." + encode(hmac.new(secret.encode(),message.encode(),hashlib.sha256).digest())

def validate_settings(values):
    name = values.get("STACK_NAME", "lovable-local")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,49}", name):
        raise SystemExit("STACK_NAME must be 1-50 lowercase letters/digits/underscores/hyphens, starting with a letter or digit")
    if values.get("FRONTEND_KIND", "vite") not in ("vite", "tanstack"):
        raise SystemExit("FRONTEND_KIND must be vite or tanstack")
    ports = [values.get(key, default) for key, default in (("WEB_PORT", "8090"), ("ADMIN_PORT", "19800"), ("MAIL_PORT", "18025"))]
    if any(not str(port).isdigit() or not 1 <= int(port) <= 65535 for port in ports):
        raise SystemExit("Host ports must be integers from 1 to 65535")
    if len(set(map(int, ports))) != len(ports):
        raise SystemExit("WEB_PORT, ADMIN_PORT and MAIL_PORT must differ")

def initialize(options=None):
    if ENV.exists():
        if not ENV.read_text().startswith("# Generated local credentials."):
            raise SystemExit("Existing .env is not managed by this scaffold; refusing to change it. Preserve the export's cloud configuration and use a separate local environment file/stack directory. See docs/SSR_MIGRATION.md.")
        return
    options = options or {}
    name = options.get("name") or "lovable-local"
    port = str(options.get("port") or 8090)
    admin_port = str(options.get("admin_port") or 19800)
    mail_port = str(options.get("mail_port") or 18025)
    validate_settings({"STACK_NAME": name, "WEB_PORT": port, "ADMIN_PORT": admin_port, "MAIL_PORT": mail_port})
    values = env_values(ROOT / "vendor/supabase/.env.example")
    for key in ("COMPOSE_FILE",): values.pop(key, None)
    values.update(STACK_NAME=name, FRONTEND_KIND=options.get("frontend") or "tanstack", PUBLIC_URL="http://localhost:"+port, WEB_PORT=port, ADMIN_PORT=admin_port, MAIL_PORT=mail_port,
                  POSTGRES_PASSWORD=secrets.token_hex(24), JWT_SECRET=secrets.token_hex(32),
                  MINIO_ROOT_PASSWORD=secrets.token_hex(24),
                  DASHBOARD_USERNAME="local-admin", DASHBOARD_PASSWORD=secrets.token_urlsafe(24),
                  SECRET_KEY_BASE=secrets.token_hex(48), REALTIME_DB_ENC_KEY=secrets.token_hex(8),
                  VAULT_ENC_KEY=secrets.token_hex(16), PG_META_CRYPTO_KEY=secrets.token_hex(32),
                  LOGFLARE_PUBLIC_ACCESS_TOKEN=secrets.token_hex(24), LOGFLARE_PRIVATE_ACCESS_TOKEN=secrets.token_hex(24),
                  S3_PROTOCOL_ACCESS_KEY_ID=secrets.token_hex(16), S3_PROTOCOL_ACCESS_KEY_SECRET=secrets.token_hex(32),
                  POOLER_TENANT_ID=name, OPENAI_API_KEY="", DISABLE_SIGNUP="false",
                  ENABLE_EMAIL_AUTOCONFIRM="false", ENABLE_PHONE_SIGNUP="false", ENABLE_PHONE_AUTOCONFIRM="false",
                  SMTP_HOST="mail", SMTP_PORT="1025", SMTP_USER="", SMTP_PASS="", SMTP_SENDER_NAME="Local Workbench",
                  SMTP_ADMIN_EMAIL="noreply@example.test", FUNCTIONS_VERIFY_JWT="true")
    values["ANON_KEY"] = jwt(values["JWT_SECRET"], "anon")
    values["SERVICE_ROLE_KEY"] = jwt(values["JWT_SECRET"], "service_role")
    write_env(values)
    print("Generated ignored .env with unique local credentials; no secrets printed.")

def render():
    initialize()
    values = env_values(ENV)
    values.setdefault("STACK_NAME", "lovable-local")
    validate_settings(values)
    origin = validated_origin(values["PUBLIC_URL"])
    values.update(SUPABASE_PUBLIC_URL=origin+"/supabase", API_EXTERNAL_URL=origin+"/supabase/auth/v1",
                  SITE_URL=origin, ADDITIONAL_REDIRECT_URLS=origin+"/**", API_GW_HTTP_PORT=values.get("ADMIN_PORT","19800"),
                  MAILER_URLPATHS_CONFIRMATION="/supabase/auth/v1/verify", MAILER_URLPATHS_INVITE="/supabase/auth/v1/verify",
                  MAILER_URLPATHS_RECOVERY="/supabase/auth/v1/verify", MAILER_URLPATHS_EMAIL_CHANGE="/supabase/auth/v1/verify")
    write_env(values)
    RUNTIME.mkdir(exist_ok=True, mode=0o700)
    result = subprocess.run(["docker","compose","--env-file",str(ENV),"--project-directory",str(ROOT/"vendor/supabase"),
        "-f",str(ROOT/"vendor/supabase/docker-compose.yml"),"config","--format","json"],check=True,capture_output=True,text=True)
    config = json.loads(result.stdout)
    config["name"] = values["STACK_NAME"]
    for service in config["services"].values():
        service.pop("container_name",None)
        service.pop("ports",None)
    config["services"]["api-gw"].pop("depends_on",None)
    config["services"]["api-gw"]["ports"] = [{"target":8000,"published":values.get("ADMIN_PORT","19800"),"host_ip":"127.0.0.1","protocol":"tcp"}]
    # Preserve the hostname expected by the official Realtime tenant and gateway config,
    # while allowing separate Compose projects without globally fixed container names.
    config["services"]["realtime"].setdefault("networks",{})["default"] = {"aliases":["realtime-dev.supabase-realtime"]}
    for name in ("studio","meta"):
        config["services"][name]["profiles"] = ["admin"]
    config["services"]["supavisor"]["profiles"] = ["pooler"]
    for name in ("db-config","deno-cache"):
        config["volumes"][name].pop("name",None)
    config.setdefault("volumes",{}).update({"pg-data":{},"storage-data":{},"snippets":{}})
    config["networks"]["default"].pop("name",None)
    for service in config["services"].values():
        for mount in service.get("volumes",[]):
            source=mount.get("source","")
            volume = ("pg-data" if source.endswith("/volumes/db/data") else
                      "storage-data" if source.endswith("/volumes/storage") else
                      "snippets" if source.endswith("/volumes/snippets") else None)
            if volume:
                mount.update(type="volume", source=volume)
                mount.pop("bind",None)
    config["services"]["functions"]["volumes"].append({"type":"bind", "source":str(ROOT/"supabase/functions/analyze"), "target":"/home/deno/functions/analyze", "read_only":True})
    active = RUNTIME / "active-backend.json"
    if active.exists():
        from backend import load, function_settings
        selected = json.loads(active.read_text())
        bundle, manifest = load(selected["name"])
        directory = selected.get("directory", "")
        if not re.fullmatch(r"functions-[a-zA-Z0-9_-]+", directory) or not (RUNTIME/directory/"main/index.ts").is_file():
            raise SystemExit("Invalid imported function generation; reactivate bundle")
        policies = function_settings(bundle, manifest)
        if policies != selected["policies"]:
            raise SystemExit("Imported function configuration changed; reactivate explicitly")
        config["services"]["functions"]["environment"]["SCAFFOLD_FUNCTION_POLICIES"] = json.dumps(policies)
        mounts = config["services"]["functions"]["volumes"]
        mounts[:] = [mount for mount in mounts if mount.get("target") != "/home/deno/functions/analyze"]
        for mount in mounts:
            if mount.get("target") == "/home/deno/functions":
                mount.update(source=str(RUNTIME / selected["directory"]), read_only=True)
        secrets_file = ROOT / ".env.functions"
        if secrets_file.exists():
            if secrets_file.is_symlink() or secrets_file.stat().st_mode & 0o077:
                raise SystemExit("Set chmod 600 .env.functions before loading function secrets")
            reserved = set(config["services"]["functions"]["environment"])
            extra = env_values(secrets_file)
            if reserved.intersection(extra):
                raise SystemExit(".env.functions must not override runtime-managed settings")
            config["services"]["functions"]["environment"].update(extra)
    target=RUNTIME/"supabase.compose.json"
    target.write_text(json.dumps(config,indent=2)+"\n");target.chmod(0o600)
    return values

def compose(*args, **kwargs):
    extra = ["-f", str(ROOT/"compose.tanstack.yaml")] if env_values(ENV).get("FRONTEND_KIND", "vite") == "tanstack" else []
    return subprocess.run(["docker","compose","--project-directory",str(ROOT),"--env-file",str(ENV),
         "-f",str(RUNTIME/"supabase.compose.json"),"-f",str(ROOT/"compose.yaml"),*extra,*args],cwd=ROOT,check=True,**kwargs)

def migrate():
    if (RUNTIME / "active-backend.json").exists():
        print("Imported backend selected: sample SQL skipped; use scripts/backend.py migrate explicitly.")
        return
    from sql_safety import validate_sql
    paths = sorted((ROOT/"supabase/migrations").glob("*.sql"))
    for path in paths:
        validate_sql(path.read_text())
    for path in paths:
        checksum=hashlib.sha256(path.read_bytes()).hexdigest()
        # Filenames/checksums are repository-controlled; never interpolate user input.
        assert all(c.isalnum() or c in "_.-" for c in path.name)
        sql = rf"""BEGIN;
SELECT pg_advisory_xact_lock(879310);
SET LOCAL standard_conforming_strings=on;
CREATE SCHEMA IF NOT EXISTS scaffold_internal;
REVOKE ALL ON SCHEMA scaffold_internal FROM PUBLIC, anon, authenticated;
CREATE TABLE IF NOT EXISTS scaffold_internal.migrations(name text PRIMARY KEY, checksum text NOT NULL);
SELECT EXISTS(SELECT 1 FROM scaffold_internal.migrations WHERE name='{path.name}') AS applied \gset
\if :applied
DO $$ BEGIN IF (SELECT checksum FROM scaffold_internal.migrations WHERE name='{path.name}') <> '{checksum}' THEN RAISE EXCEPTION 'Applied migration was edited'; END IF; END $$;
\else
{path.read_text()}
INSERT INTO scaffold_internal.migrations VALUES ('{path.name}','{checksum}');
\endif
COMMIT;
"""
        compose("exec","-T","db","psql","-v","ON_ERROR_STOP=1","-U","postgres","-d","postgres",input=sql,text=True,stdout=subprocess.DEVNULL)
        print("Migration ready:",path.name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="check", choices=("init", "up", "origin", "admin", "down", "logs", "check", "frontend"))
    parser.add_argument("url", nargs="?")
    parser.add_argument("--frontend", choices=("tanstack", "vite"))
    parser.add_argument("--name")
    parser.add_argument("--port", type=int)
    parser.add_argument("--admin-port", type=int)
    parser.add_argument("--mail-port", type=int)
    args = parser.parse_args()
    initial = {key: getattr(args, key) for key in ("name", "port", "admin_port", "mail_port", "frontend") if getattr(args, key) is not None}
    if initial and (args.action != "init" or ENV.exists()):
        parser.error("Initial name/port flags require init with no existing .env; configure existing settings in .env instead")
    initialize(initial)
    action = args.action
    if action == "origin":
        if not args.url:raise SystemExit("Usage: make origin URL=https://your-host")
        set_origin(args.url)
    if action == "frontend":
        if args.url not in ("vite", "tanstack"): raise SystemExit("Use: make frontend KIND=tanstack (or vite)")
        values=env_values(ENV);values["FRONTEND_KIND"]=args.url;write_env(values)
    values=render()
    if action in ("up","origin","admin","frontend"):
        args=["--profile","admin"] if action=="admin" else []
        compose(*args,"up","--build","-d","--remove-orphans","--wait","--wait-timeout","300")
        migrate()
        print("App:", values["PUBLIC_URL"], "| Mail: http://localhost:"+values["MAIL_PORT"])
    elif action=="down":compose("--profile","admin","--profile","pooler","down")
    elif action=="logs":compose("logs","-f","--tail=50")
    elif action=="check":compose("--profile","admin","--profile","pooler","config","--quiet")
    elif action=="init":print("Initialized. Run make up.")
    else:raise SystemExit("Unknown action")
