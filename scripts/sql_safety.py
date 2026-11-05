"""PostgreSQL AST validation for reviewed migration SQL, not a SQL sandbox."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _validate(sql):
    from pglast.parser import parse_sql_json, ParseError
    try:
        tree = json.loads(parse_sql_json(sql))
    except ParseError:
        raise SystemExit('Migration is not valid PostgreSQL SQL; psql commands are not supported') from None
    for raw in tree.get('stmts', []):
        statement = raw['stmt']
        if 'TransactionStmt' in statement:
            raise SystemExit('Transaction control is not permitted inside a migration')
        setting = statement.get('VariableSetStmt')
        if setting is not None and (setting.get('name') or '').lower() in ('', 'standard_conforming_strings', 'transaction', 'session characteristics'):
            raise SystemExit('Migration must preserve standard_conforming_strings')
    # A direct GUC setter must not change how later psql statements parse literals.
    def visit(value):
        if isinstance(value, dict):
            call=value.get('FuncCall')
            if call:
                names=[part.get('String',{}).get('sval') for part in call.get('funcname',[])]
                if names and names[-1]=='set_config':
                    arguments=call.get('args',[])
                    name=arguments[0].get('A_Const',{}).get('sval',{}).get('sval') if arguments else None
                    if name is None or name.lower() == 'standard_conforming_strings':
                        raise SystemExit('Migration must preserve standard_conforming_strings')
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(tree)


def validate_sql(sql):
    try:
        _validate(sql)
    except ImportError:
        # Preserve direct `python3 scripts/...` usage after `make tools` setup.
        interpreter=ROOT/'.venv-tools/bin/python'
        if not interpreter.exists():
            raise SystemExit('Run make tools to install the pinned PostgreSQL parser') from None
        result=subprocess.run([str(interpreter),str(Path(__file__))],input=sql,text=True,capture_output=True)
        if result.returncode:
            raise SystemExit(result.stderr.strip() or 'Migration SQL validation failed')


if __name__=='__main__':
    try:_validate(sys.stdin.read())
    except ImportError:raise SystemExit('Run make tools to install the pinned PostgreSQL parser') from None
