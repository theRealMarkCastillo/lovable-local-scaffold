"""Offline regression checks for artifact integrity, ordering and execution boundaries."""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('backend', Path(__file__).resolve().parents[1] / 'scripts/backend.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class BackendImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.patches = [patch.object(backend, 'ROOT', self.root), patch.object(backend, 'IMPORTS', self.root / '.imports'), patch.object(backend, 'RUNTIME', self.root / '.runtime')]
        for item in self.patches:
            item.start(); self.addCleanup(item.stop)

    def write(self, path, content):
        target = self.source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def collect(self, **values):
        options = dict(name='test', source=self.source, sql=None, database=None, csv=None, storage=None, jobs=None)
        options.update(values)
        with contextlib.redirect_stdout(io.StringIO()):
            backend.collect(argparse.Namespace(**options))
        return backend.load(options['name'])

    def test_capture_order_sensitive_config_and_no_execution(self):
        self.write('supabase/migrations/20260102000000_second.sql', 'SELECT 2;')
        self.write('supabase/migrations/20260101000000_first.sql', 'SELECT 1;')
        self.write('supabase/functions/webhook/index.ts', "Deno.env.get('STRIPE_SECRET');")
        self.write('supabase/functions/_shared/helper.ts', 'export const x=1;')
        self.write('supabase/functions/webhook/deno.json', '{"imports":{}}')
        self.write('supabase/functions/.env', 'DO_NOT_COPY=secret')
        self.write('.env', 'ORIGINAL_CLOUD=preserve')
        self.write('supabase/config.toml', '[functions.webhook]\nverify_jwt=false\n')
        with patch.object(backend, 'local_stack', side_effect=AssertionError('must not execute')):
            root, data = self.collect()
        self.assertEqual([v for _, v, _ in backend.migration_order(root, data, 'supabase')], ['20260101000000', '20260102000000'])
        self.assertFalse((root / '.env').exists())
        self.assertFalse((root / 'supabase/functions/.env').exists())
        self.assertTrue((root / 'supabase/functions/_shared/helper.ts').exists())
        settings = backend.function_settings(root, data)
        self.assertFalse(settings['webhook']['verify_jwt'])
        self.assertTrue(settings['webhook']['import_map'].endswith('/webhook/deno.json'))
        self.assertEqual((root / 'manifest.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(root.stat().st_mode & 0o777, 0o700)

    def test_tampered_source_refused(self):
        self.write('supabase/migrations/1_one.sql', 'SELECT 1;')
        root, _ = self.collect()
        (root / 'supabase/migrations/1_one.sql').write_text('SELECT 2;')
        with self.assertRaises(SystemExit): backend.load('test')

    def test_additional_untracked_function_refused(self):
        self.write('supabase/functions/a/index.ts', 'Deno.serve(()=>new Response("ok"));')
        root, _ = self.collect()
        (root / 'supabase/functions/a/other.ts').write_text('unexpected')
        with self.assertRaises(SystemExit): backend.load('test')

    def test_symlink_refused_and_no_partial_bundle(self):
        folder = self.source / 'supabase/functions'
        folder.mkdir(parents=True)
        (folder / 'outside.ts').symlink_to('/etc/hosts')
        with self.assertRaises(SystemExit): self.collect()
        self.assertFalse((backend.IMPORTS / 'test').exists())

    def test_drizzle_journal_controls_order(self):
        self.write('drizzle/migrations/z_first.sql', 'SELECT 1;')
        self.write('drizzle/migrations/a_second.sql', 'SELECT 2;')
        self.write('drizzle/migrations/meta/_journal.json', json.dumps({'entries':[{'tag':'z_first','when':1},{'tag':'a_second','when':2}]}))
        root, data = self.collect()
        self.assertEqual([v for _,v,_ in backend.migration_order(root,data,'drizzle')], ['z_first','a_second'])

    def test_drizzle_missing_sql_and_duplicate_versions_refused(self):
        self.write('drizzle/migrations/meta/_journal.json', '{"entries":[{"tag":"missing","when":1}]}')
        self.write('supabase/migrations/1_a.sql', 'SELECT 1;')
        self.write('supabase/migrations/1_b.sql', 'SELECT 2;')
        root,data = self.collect()
        for layout in ('supabase','drizzle'):
            with self.assertRaises(SystemExit): backend.migration_order(root,data,layout)

    def test_plan_does_not_open_database(self):
        self.write('supabase/migrations/1_a.sql', 'SELECT 1;')
        self.collect()
        with patch.object(backend,'local_stack',side_effect=AssertionError('plan must not execute')), contextlib.redirect_stdout(io.StringIO()):
            backend.migrate(argparse.Namespace(name='test',layout='supabase',execute=False))

    def test_psql_shell_commands_refused(self):
        self.write('supabase/migrations/1_a.sql', '\\! touch /tmp/never\n')
        self.collect()
        with self.assertRaises(SystemExit): backend.migrate(argparse.Namespace(name='test',layout='supabase',execute=False))

    def test_manual_sql_and_storage_csv_are_preserved(self):
        first=self.write('first.sql','SELECT 1;');second=self.write('second.sql','SELECT 2;')
        self.write('objects/bucket/u/image.txt','bytes')
        self.write('tables/records.csv','id,name\n1,synthetic\n')
        root,data=self.collect(sql=[second,first],storage=self.source/'objects',csv=self.source/'tables')
        self.assertEqual([Path(p).name for p,_,_ in backend.migration_order(root,data,'manual')], ['0000-second.sql','0001-first.sql'])
        self.assertEqual((root/'storage/bucket/u/image.txt').read_text(),'bytes')
        self.assertEqual((root/'csv/records.csv').read_text(),'id,name\n1,synthetic\n')

    def test_wrong_backup_format_refused(self):
        dump=self.write('dump.sql','CREATE TABLE x(id int);')
        with self.assertRaises(SystemExit): self.collect(database=dump)
        self.assertFalse((backend.IMPORTS/'test').exists())

    def test_csv_mapping_validation_and_plan_only(self):
        self.write('tables/records.csv', 'id,name\n1,synthetic\n')
        self.collect(csv=self.source/'tables')
        args=argparse.Namespace(name='test', file='csv/records.csv', table='public.records', columns='id,name', execute=False)
        with patch.object(backend,'local_stack',side_effect=AssertionError('plan must not execute')), contextlib.redirect_stdout(io.StringIO()):
            backend.csv_load(args)
        args.table='public.records;drop'
        with self.assertRaises(SystemExit): backend.csv_load(args)
        args.table='public.records';args.file='../escape.csv'
        with self.assertRaises(SystemExit): backend.csv_load(args)


    def test_uncaptured_backup_is_not_restored(self):
        root,_=self.collect()
        (root/'database').mkdir()
        (root/'database/export.backup').write_bytes(b'PGDMP-not-captured')
        with patch.object(backend,'local_stack',side_effect=AssertionError('must refuse before database access')):
            with self.assertRaises(SystemExit):
                backend.backup(argparse.Namespace(name='test', action='backup-list'))


    def test_overwrite_and_unsafe_name_refused(self):
        self.collect()
        with self.assertRaises(SystemExit): self.collect()
        with self.assertRaises(SystemExit): self.collect(name='../escape')


if __name__ == '__main__':
    unittest.main()
