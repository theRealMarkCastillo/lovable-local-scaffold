"""Real local Auth/email/RLS/Storage/Function checks. Never target a cloud backend."""
from pathlib import Path
import json
import os
import secrets
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from stack import ROOT, env_values

env=env_values(ROOT/".env")
BASE=env["PUBLIC_URL"].rstrip("/")
parts=urllib.parse.urlparse(BASE)
if parts.hostname not in ("localhost","127.0.0.1") and not (parts.hostname or "").endswith(".orb.local"):
    raise SystemExit("Synthetic smoke is restricted to localhost or local OrbStack hosts")
API=BASE+"/supabase"
MAIL="http://localhost:"+env["MAIL_PORT"]
TLS=ssl.create_default_context(cafile=os.getenv("DEMO_CA_FILE"))
if (parts.hostname or "").endswith(".orb.local") and not os.getenv("DEMO_CA_FILE"):
    cert=subprocess.run(["security","find-certificate","-a","-c","OrbStack","-p"],capture_output=True,text=True,check=True)
    if cert.stdout.strip():TLS.load_verify_locations(cadata=cert.stdout)
opener=urllib.request.build_opener(urllib.request.HTTPSHandler(context=TLS))

def request(path, method="GET", body=None, token=None, expected=(200,), raw=False, content_type=None, base=API):
    headers={"apikey":env["ANON_KEY"]}
    if token:headers["Authorization"]="Bearer "+token
    if body is not None:
        if isinstance(body,bytes):data=body;headers["Content-Type"]=content_type or "text/plain"
        else:data=json.dumps(body).encode();headers["Content-Type"]="application/json"
    else:data=None
    req=urllib.request.Request(base+path,data=data,headers=headers,method=method)
    try:resp=opener.open(req,timeout=30)
    except urllib.error.HTTPError as error:resp=error
    payload=resp.read()
    if resp.status not in expected:
        # Do not dump response bodies that might contain user tokens.
        raise AssertionError(f"{method} {path.split('?')[0]} returned {resp.status}; expected {expected}")
    if raw:return payload
    return json.loads(payload) if payload else None

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href","")
            if "/auth/v1/verify" in href:self.links.append(href)

def signup(label):
    email=f"{label}-{secrets.token_hex(5)}@example.test"
    password=secrets.token_urlsafe(18)+"aA1!"
    request("/auth/v1/signup","POST",{"email":email,"password":password,"data":{"name":label}},expected=(200,201))
    for _ in range(30):
        messages=request("/api/v1/messages",base=MAIL)["messages"]
        found=next((m for m in messages if any(to.get("Address")==email for to in m["To"])),None)
        if found:break
        time.sleep(1)
    else:raise AssertionError("Confirmation message was not captured by Mailpit")
    message=request("/api/v1/message/"+found["ID"],base=MAIL)
    links=Links();links.feed(message["HTML"])
    assert links.links,"No confirmation link"
    url=urllib.parse.urlparse(links.links[0])
    assert (url.scheme,url.netloc)==(parts.scheme,parts.netloc),"Confirmation link points outside configured local origin"
    response=opener.open(links.links[0],timeout=30);response.read()
    session=request("/auth/v1/token?grant_type=password","POST",{"email":email,"password":password})
    return {"email":email,"password":password,"user_id":session["user"]["id"],"access_token":session["access_token"],"refresh_token":session["refresh_token"]}

a=signup("owner");b=signup("other")
print("PASS: signup, captured confirmation email, verification link and password login for two users")
request("/rest/v1/notes",expected=(401,403))
row=request("/rest/v1/notes","POST",{"title":"Portable smoke note","body":"Row-level security owns this record."},a["access_token"],expected=(201,))
notes=request("/rest/v1/notes?select=*",token=a["access_token"])
note=next(item for item in notes if item["title"]=="Portable smoke note")
assert note["owner_id"]==a["user_id"]
assert request("/rest/v1/notes?id=eq."+note["id"],token=b["access_token"])==[]
request("/rest/v1/notes","POST",{"title":"forged owner","owner_id":a["user_id"]},b["access_token"],expected=(403,))
request("/rest/v1/notes?id=eq."+note["id"],"PATCH",{"title":"blocked update"},b["access_token"],expected=(204,))
assert request("/rest/v1/notes?id=eq."+note["id"],token=a["access_token"])[0]["title"]=="Portable smoke note"
print("PASS: anonymous denial and two-user RLS for reads, forged inserts and cross-user updates")
key=a["user_id"]+"/smoke.txt"
request("/storage/v1/object/uploads/"+key,"POST",b"private upload",a["access_token"],expected=(200,201))
assert request("/storage/v1/object/authenticated/uploads/"+key,token=a["access_token"],raw=True)==b"private upload"
request("/storage/v1/object/authenticated/uploads/"+key,token=b["access_token"],expected=(400,403,404),raw=True)
assert request("/storage/v1/object/list/uploads","POST",{"prefix":a["user_id"]},b["access_token"])==[]
request("/storage/v1/object/uploads/"+a["user_id"]+"/forged.txt","POST",b"blocked",b["access_token"],expected=(400,403))
print("PASS: private file upload/download and cross-user storage isolation")
for _ in range(20):
    try:
        result=request("/functions/v1/analyze","POST",{"text":"portable functions"},a["access_token"])
        break
    except AssertionError:
        time.sleep(2)
else:raise AssertionError("Edge function did not become ready")
assert result["words"]==2
request("/functions/v1/analyze","POST",{"text":"blocked"},env["ANON_KEY"],expected=(401,))
print("PASS: real Edge Runtime function and rejection of an anonymous API key as a user identity")
request("/auth/v1/logout","POST",token=a["access_token"],expected=(204,))
request("/auth/v1/token?grant_type=refresh_token","POST",{"refresh_token":a["refresh_token"]},expected=(400,401))
print("PASS: logout revokes refresh session (access JWT expiry is a separate concern)")
fixture=ROOT/".runtime/browser-fixture.json"
fixture.write_text(json.dumps({"email":a["email"],"password":a["password"],"user_id":a["user_id"]})+"\n");fixture.chmod(0o600)
print("Synthetic test accounts/data retained locally; no cloud backend was contacted.")

if env.get("FRONTEND_KIND", "vite") == "tanstack":
    import re
    def document():
        return opener.open(BASE+"/",timeout=30)
    first=document();html=first.read().decode();policy=first.headers.get("Content-Security-Policy", "")
    assert "TanStack Start · rendered by the Node server" in html
    assert "Sign in to your workspace" in html
    nonce=re.search(r"'nonce-([^']+)'", policy)
    assert nonce and ('nonce="'+nonce.group(1)+'"') in html
    assert "unsafe-inline" not in policy
    second=document();second.read()
    assert second.headers.get("Content-Security-Policy") != policy
    assert "no-store" in first.headers.get("Cache-Control", "")
    for key in ("SERVICE_ROLE_KEY", "POSTGRES_PASSWORD", "JWT_SECRET"):
        assert env[key] not in html, "Privileged value exposed in SSR HTML"
    assert "http://api-gw:8000" not in html
    request("/does-not-exist", base=BASE, expected=(404,),raw=True)
    request("/supabase/auth/v1/admin/users", base=BASE, expected=(404,),raw=True)
    print("PASS: rendered HTML, unique CSP nonces, private/no-store caching, no privileged config and real 404/admin denial")
