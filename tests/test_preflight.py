from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/preflight.py'

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'package.json').write_text('{"dependencies":{"@supabase/supabase-js":"2.0.0"}}')
    def write(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value)
    def result(self):
        return json.loads(subprocess.check_output([sys.executable,str(SCRIPT),str(self.root)]))
    def assert_no_missing_warning(self,result):
        self.assertFalse(any('No exported SQL migrations' in note for note in result['notes']))
    def test_supabase_only(self):
        self.write('supabase/migrations/1_initial.sql','SELECT 1;')
        result=self.result();self.assertEqual(result['exported_migrations'],1)
        self.assertTrue(result['migration_layouts']['supabase']['valid']);self.assert_no_missing_warning(result)
    def test_drizzle_only_uses_authoritative_order(self):
        for tag in ('z_first','a_second'):self.write(f'drizzle/migrations/{tag}.sql','SELECT 1;')
        self.write('drizzle/migrations/meta/_journal.json',json.dumps({'entries':[{'tag':'z_first','when':1},{'tag':'a_second','when':2}]}))
        result=self.result();self.assertEqual(result['exported_migrations'],2)
        self.assertEqual(result['migration_layouts']['drizzle']['order'],['drizzle/migrations/z_first.sql','drizzle/migrations/a_second.sql'])
        self.assert_no_missing_warning(result)
    def test_both_layouts_counted(self):
        self.write('supabase/migrations/1_initial.sql','SELECT 1;')
        self.write('drizzle/migrations/first.sql','SELECT 1;')
        self.write('drizzle/migrations/meta/_journal.json','{"entries":[{"tag":"first","when":1}]}')
        self.assertEqual(self.result()['exported_migrations'],2)
    def test_missing_or_invalid_drizzle_journal_is_distinct_from_missing_schema(self):
        self.write('drizzle/migrations/first.sql','SELECT 1;')
        for value in (None,'not json','{"entries":[{"tag":"absent","when":1}]}'):
            if value is not None:self.write('drizzle/migrations/meta/_journal.json',value)
            result=self.result()
            self.assertEqual(result['exported_migrations'],1)
            self.assertFalse(result['migration_layouts']['drizzle']['valid'])
            self.assertTrue(any('invalid or incomplete' in note for note in result['notes']))
            self.assert_no_missing_warning(result)
    def test_no_sql_warns_missing_schema(self):
        result=self.result();self.assertEqual(result['exported_migrations'],0)
        self.assertTrue(any('No exported SQL migrations' in note for note in result['notes']))

if __name__=='__main__':unittest.main()
