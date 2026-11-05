"""Synthetic, isolated local backend import exercise. Removes only its own stack."""
from pathlib import Path
import tempfile,shutil,subprocess,sys,socket,json,time,zipfile
import urllib.request,urllib.error

REPO=Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

with tempfile.TemporaryDirectory(prefix='lovable-backend-integration-') as directory:
    root=Path(directory).resolve();(root/'scripts').mkdir()
    for name in ('stack.py','backend.py'):shutil.copyfile(REPO/'scripts'/name,root/'scripts'/name)
    for name in ('compose.yaml','compose.tanstack.yaml'):shutil.copyfile(REPO/name,root/name)
    (root/'vendor').symlink_to(REPO/'vendor',target_is_directory=True)
    (root/'web').symlink_to(REPO/'web',target_is_directory=True)
    source=root/'export';source.mkdir()
    def write(name,text):
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
    write('supabase/migrations/20261105010100_base.sql', '''CREATE SCHEMA import_demo;
CREATE TABLE import_demo.records(id serial PRIMARY KEY, body text NOT NULL);
INSERT INTO import_demo.records(body) VALUES ('synthetic');
ALTER TABLE import_demo.records ENABLE ROW LEVEL SECURITY;
GRANT USAGE ON SCHEMA import_demo TO anon;
GRANT SELECT ON import_demo.records TO anon;
''')
    write('supabase/functions/_shared/helper.ts', "export const label = 'shared-source';\n")
    write('supabase/functions/deno.json', '{"imports":{"helper":"./_shared/helper.ts"}}')
    write('supabase/functions/private/deno.json', '{"imports":{"helper":"../_shared/helper.ts"}}')
    write('supabase/functions/private/index.ts', "import {label} from 'helper'; Deno.serve(()=>Response.json({label,configured:Deno.env.get('SYNTHETIC_SECRET')==='synthetic-only'}));")
    write('supabase/functions/webhook/index.ts', "import {label} from 'helper'; Deno.serve(()=>Response.json({label,public:true}));")
    write('supabase/config.toml','[functions.private]\nverify_jwt=true\n[functions.webhook]\nverify_jwt=false\n')
    ports=[free_port() for _ in range(3)];name='backend-check-'+root.name.rsplit('-',1)[-1].lower()
    def run(*args,check=True):
        result=subprocess.run([sys.executable,*map(str,args)],cwd=root,capture_output=True,text=True)
        if check and result.returncode:
            # Synthetic fixtures only; output does not contain credentials.
            raise AssertionError(result.stdout+'\n'+result.stderr)
        return result
    stack=root/'scripts/stack.py';backend=root/'scripts/backend.py'
    run(stack,'init','--name',name,'--port',ports[0],'--admin-port',ports[1],'--mail-port',ports[2],'--frontend','vite')
    run(backend,'import',source,'--name','fixture')
    run(backend,'activate','fixture')
    secrets=root/'.env.functions';secrets.write_text('SYNTHETIC_SECRET=synthetic-only\n');secrets.chmod(0o600)
    # Import temporary stack module, so all Docker commands are project-scoped.
    sys.path.insert(0,str(root/'scripts'));import stack as local
    local.render()
    try:
        local.compose('up','-d','--wait','--wait-timeout','180','db','api-gw','rest','auth','mail','functions',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def sql(command):
            result=local.compose('exec','-T','db','psql','-At','-v','ON_ERROR_STOP=1','-U','postgres','-d','postgres',input=command,text=True,capture_output=True)
            return result.stdout.strip()
        run(backend,'migrate','fixture','--layout','supabase','--execute')
        run(backend,'migrate','fixture','--layout','supabase','--execute')
        assert sql('SELECT count(*) FROM import_demo.records;')=='1'
        assert sql("SELECT count(*) FROM supabase_migrations.schema_migrations WHERE version='20261105010100';")=='1'
        assert sql('SET ROLE anon; SELECT count(*) FROM import_demo.records;').endswith('0')
        write('supabase/migrations/20261105010101_followup.sql', 'ALTER TABLE import_demo.records ADD COLUMN extra text;')
        run(backend,'import',source,'--name','fixture-v2')
        run(backend,'migrate','fixture-v2','--layout','supabase','--execute')
        assert sql("SELECT count(*) FROM supabase_migrations.schema_migrations;")=='2'
        assert sql('SELECT count(*) FROM import_demo.records;')=='1'
        print('PASS: SQL applied once, Supabase history, incremental bundle and RLS enforced',flush=True)
        other=root/'drizzle-export';(other/'drizzle/migrations/meta').mkdir(parents=True)
        (other/'drizzle/migrations/z_first.sql').write_text('CREATE SCHEMA import_drizzle; CREATE TABLE import_drizzle.parent(id int PRIMARY KEY);')
        (other/'drizzle/migrations/a_second.sql').write_text('CREATE TABLE import_drizzle.child(parent_id int REFERENCES import_drizzle.parent(id));')
        (other/'drizzle/migrations/meta/_journal.json').write_text(json.dumps({'entries':[{'tag':'z_first','when':1},{'tag':'a_second','when':2}]}))
        run(backend,'import',other,'--name','drizzle')
        run(backend,'migrate','drizzle','--layout','drizzle','--execute')
        run(backend,'migrate','drizzle','--layout','drizzle','--execute')
        assert sql('SELECT count(*) FROM drizzle.__drizzle_migrations;')=='2'
        print('PASS: Drizzle journal order and history, including repeated application',flush=True)
        broken=root/'broken';(broken/'supabase/migrations').mkdir(parents=True)
        (broken/'supabase/migrations/20261105010200_failure.sql').write_text('CREATE TABLE import_demo.must_rollback(id int); SELECT * FROM missing_synthetic_table;')
        run(backend,'import',broken,'--name','broken')
        assert run(backend,'migrate','broken','--layout','supabase','--execute',check=False).returncode
        assert sql("SELECT to_regclass('import_demo.must_rollback') IS NULL;")=='t'
        print('PASS: failing migration rolls back its DDL and ledger entry',flush=True)
        csvdir=root/'csv-input';csvdir.mkdir();(csvdir/'records.csv').write_text('id,label\n1,csv-synthetic\n')
        sql('CREATE TABLE import_demo.csv_records(id int PRIMARY KEY,label text NOT NULL);')
        run(backend,'import',source,'--name','csv','--csv',csvdir)
        run(backend,'csv-load','csv','--file','csv/records.csv','--table','import_demo.csv_records','--columns','id,label','--execute')
        assert sql('SELECT label FROM import_demo.csv_records;')=='csv-synthetic'
        assert run(backend,'csv-load','csv','--file','csv/records.csv','--table','import_demo.csv_records','--columns','id,label','--execute',check=False).returncode
        assert sql('SELECT count(*) FROM import_demo.csv_records;')=='1'
        print('PASS: mapped CSV load and duplicate rejection without partial data',flush=True)
        dump=root/'synthetic.backup'
        with dump.open('wb') as output:
            local.compose('exec','-T','db','pg_dump','-Fc','--compress=zstd','-n','import_demo','-U','postgres','postgres',stdout=output)
        archive=root/'database.zip'
        with zipfile.ZipFile(archive,'w') as target:target.write(dump,'export/synthetic.backup')
        run(backend,'import',source,'--name','restore','--database',archive)
        run(backend,'backup-list','restore')
        toc=root/'.imports/restore/database/restore.list'
        # Backup includes this synthetic schema only; retain its complete catalog.
        run(backend,'restore','restore','--toc',toc) # plan must not mutate existing rows
        assert sql('SELECT count(*) FROM import_demo.records;')=='1'
        sql('DROP SCHEMA import_demo CASCADE;')
        run(backend,'restore','restore','--toc',toc,'--execute')
        assert sql('SELECT body FROM import_demo.records;')=='synthetic'
        assert sql("SELECT nextval('import_demo.records_id_seq');")=='2'
        print('PASS: zstd ZIP backup capture, private TOC, plan-only restore, selected schema/data/sequence restore',flush=True)
        env=local.env_values(root/'.env')
        def request(slug,token=None):
            headers={'Content-Type':'application/json'}
            if token:headers['Authorization']='Bearer '+token
            req=urllib.request.Request(f'http://localhost:{ports[1]}/functions/v1/{slug}',data=b'{}',headers=headers)
            try:response=urllib.request.urlopen(req,timeout=20)
            except urllib.error.HTTPError as error:response=error
            return response.status,response.read()
        for _ in range(20):
            status,payload=request('webhook')
            if status==200:break
            time.sleep(1)
        assert status==200,(status,payload)
        assert json.loads(payload)['label']=='shared-source'
        assert request('private')[0]==401
        assert request('private','invalid')[0]==401
        status,payload=request('private',env['ANON_KEY'])
        assert status==200,(status,payload)
        assert json.loads(payload)['configured'] is True
        assert request('_shared')[0]==404
        print('PASS: imported functions, shared code/import map, private secret, per-function JWT policy and unknown-slug denial',flush=True)
    finally:
        local.compose('--profile','admin','--profile','pooler','down','-v','--remove-orphans',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        print('Removed only the disposable integration stack/volumes.',flush=True)
