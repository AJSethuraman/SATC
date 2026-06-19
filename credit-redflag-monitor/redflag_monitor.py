#!/usr/bin/env python3
"""Convenience runner so the spec's `python redflag_monitor.py` works in-place.

This file shares a name with the ``redflag_monitor`` package, so before
importing we drop this directory from ``sys.path`` (otherwise this script would
shadow the package) and put ``src/`` first.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if p and Path(p).resolve() != _HERE]
sys.path.insert(0, str(_HERE / "src"))

from redflag_monitor.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
