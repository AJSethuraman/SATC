from __future__ import annotations
import subprocess
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent


def load_env_file(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    load_env_file(ROOT / '.env')
    ua = os.getenv('SEC_USER_AGENT', '').strip()
    if not ua:
        raise SystemExit('SEC_USER_AGENT missing. Run python bootstrap.py, then edit .env and set SEC_USER_AGENT.')

    cmd = ['credit-packet', 'build', '--ticker', 'AAPL', '--years', '3', '--output', 'outputs/aapl_packet.md']
    try:
        subprocess.check_call(cmd, cwd=ROOT)
    except FileNotFoundError:
        raise SystemExit('credit-packet command not found. Activate .venv or run python bootstrap.py first.')

if __name__ == '__main__':
    main()
