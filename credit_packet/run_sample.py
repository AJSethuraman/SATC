from __future__ import annotations
import subprocess
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def main():
    load_dotenv(ROOT / '.env', override=False)
    ua = os.getenv('SEC_USER_AGENT', '').strip()
    if not ua:
        raise SystemExit('SEC_USER_AGENT missing. Run python bootstrap.py, then edit .env and set SEC_USER_AGENT.')

    cmd = [
        sys.executable,
        '-m',
        'credit_packet.cli',
        'build',
        '--ticker', 'AAPL',
        '--years', '3',
        '--output', 'outputs/aapl_packet.md',
    ]
    subprocess.check_call(cmd, cwd=ROOT)

if __name__ == '__main__':
    main()
