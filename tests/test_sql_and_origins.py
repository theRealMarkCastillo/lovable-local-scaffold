"""Regression checks for PostgreSQL transaction grammar and atomic origin updates."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sql_safety import validate_sql
spec=importlib.util.spec_from_file_location('origin_stack',ROOT/'scripts/stack.py')
stack=importlib.util.module_from_spec(spec);spec.loader.exec_module(stack)


class SQLValidationTests(unittest.TestCase):
    def test_all_transaction_forms_are_rejected(self):
        for sql in ('COMMIT WORK;', 'COMMIT TRANSACTION;', 'END;', 'ABORT;',
                    'ROLLBACK WORK;', 'BEGIN TRANSACTION;', 'START TRANSACTION;',
                    'SAVEPOINT x;', 'RELEASE SAVEPOINT x;', 'ROLLBACK TO SAVEPOINT x;',
                    "PREPARE TRANSACTION 'x';", "COMMIT PREPARED 'x';", "ROLLBACK PREPARED 'x';",
                    'COMMIT AND CHAIN;', '/* prefix */ COMMIT /* between */ WORK;',
                    'SELECT 1; COMMIT WORK;', 'SET TRANSACTION READ ONLY;',
                    'SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;'):
            with self.subTest(sql=sql), self.assertRaises(SystemExit):validate_sql(sql)
    def test_quoted_text_and_routines_do_not_trigger_transaction_rejection(self):
        for sql in ("SELECT 'COMMIT WORK;';", 'SELECT $$COMMIT WORK;\n\\! not-a-command$$;',
                    '-- COMMIT WORK;\nSELECT 1;', 'CREATE TABLE "COMMIT"(id int);',
                    "CREATE FUNCTION f() RETURNS int LANGUAGE plpgsql AS $$BEGIN RETURN 1; END;$$;",
                    "CREATE FUNCTION f() RETURNS int LANGUAGE SQL BEGIN ATOMIC SELECT 1; END;",
                    "SELECT set_config('search_path','public',false);"):
            with self.subTest(sql=sql):validate_sql(sql)
    def test_invalid_sql_psql_commands_and_lexical_setting_changes_are_rejected(self):
        for sql in ('SELECT 1; \\gexec', '\\! echo forbidden', 'this is not SQL;',
                    'SET standard_conforming_strings=off;', 'RESET ALL;',
                    "SELECT set_config('standard_conforming_strings','off',true);",
                    "SELECT set_config('STANDARD_CONFORMING_STRINGS','off',true);"):
            with self.subTest(sql=sql),self.assertRaises(SystemExit):validate_sql(sql)


class OriginTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.environment=self.root/'.env'
        self.original=b'# Generated local credentials. Do not commit or paste into logs.\nSTACK_NAME=review-unit\nPUBLIC_URL=http://localhost:8099\nWEB_PORT=8099\nADMIN_PORT=19809\nMAIL_PORT=18039\n'
        self.environment.write_bytes(self.original);self.environment.chmod(0o600)
        for attribute,value in [('ROOT',self.root),('ENV',self.environment)]:
            item=patch.object(stack,attribute,value);item.start();self.addCleanup(item.stop)
    def test_invalid_origin_never_changes_environment(self):
        for origin in ('https://example.test/path','http://example.test','https://user:pass@example.test',
                       'https://example.test?query=1','https://example.test/#fragment',
                       'https://example.test:invalid','https://example.test:0',
                       'https://example.test\nANON_KEY=bad',' https://example.test'):
            with self.subTest(origin=origin),self.assertRaises(SystemExit):stack.set_origin(origin)
            self.assertEqual(self.environment.read_bytes(),self.original)
    def test_valid_origin_is_normalized_and_written_privately(self):
        stack.set_origin('https://example.test/')
        self.assertEqual(stack.env_values(self.environment)['PUBLIC_URL'],'https://example.test')
        self.assertEqual(self.environment.stat().st_mode&0o777,0o600)
        self.assertFalse(list(self.root.glob('.env.*.tmp')))
    def test_failed_atomic_replace_preserves_original(self):
        with patch.object(stack.os,'replace',side_effect=OSError('synthetic replacement failure')):
            with self.assertRaises(OSError):stack.set_origin('https://example.test')
        self.assertEqual(self.environment.read_bytes(),self.original)
        self.assertFalse(list(self.root.glob('.env.*.tmp')))


if __name__=='__main__':unittest.main()
