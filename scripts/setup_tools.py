"""Install the pinned local SQL tooling in an ignored project virtual environment."""
from pathlib import Path
import subprocess
import venv

ROOT=Path(__file__).resolve().parents[1]
VENV=ROOT/'.venv-tools'
interpreter=VENV/'bin/python'
usable=interpreter.exists() and subprocess.run([str(interpreter),'-c','import sys'],capture_output=True).returncode==0
if not usable:venv.EnvBuilder(with_pip=True,symlinks=True,clear=True).create(VENV)
wanted=(ROOT/'requirements-tools.txt').read_text().strip().split('==')[1]
check=subprocess.run([str(interpreter),'-c',"from importlib.metadata import version; print(version('pglast'))"],capture_output=True,text=True)
if check.returncode or check.stdout.strip()!=wanted:
    subprocess.run([str(interpreter),'-m','pip','install','--disable-pip-version-check','-r',str(ROOT/'requirements-tools.txt')],check=True)
