from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd, cwd=ROOT):
    print('>', ' '.join(str(c) for c in cmd))
    subprocess.check_call(cmd, cwd=cwd)


def main():
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11+ is required.')

    venv_dir = ROOT / '.venv'
    if not venv_dir.exists():
        run([sys.executable, '-m', 'venv', str(venv_dir)])

    py = venv_dir / ('Scripts/python.exe' if sys.platform.startswith('win') else 'bin/python')

    run([str(py), '-m', 'pip', 'install', '--upgrade', 'pip'])
    run([str(py), '-m', 'pip', 'install', '-e', '.[dev]'])

    env = ROOT / '.env'
    example = ROOT / '.env.example'
    if not env.exists() and example.exists():
        shutil.copy(example, env)
        print('Created .env from .env.example')

    print('\nEdit .env and set SEC_USER_AGENT before live SEC runs.')
    run([str(py), '-m', 'pytest', '-q'])

    print('\nNext commands (no activation required):')
    print(r'Windows: .venv\Scripts\python.exe run_sample.py')
    print('Mac/Linux: .venv/bin/python run_sample.py')

if __name__ == '__main__':
    main()
