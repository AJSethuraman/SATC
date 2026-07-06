"""Expose the repo-root ``satc_credit_core`` shared package to this project's
tests, so ``PYTHONPATH=src pytest`` keeps working with no editable install."""

import sys
from pathlib import Path

_SHARED = str(Path(__file__).resolve().parent.parent / "satc_credit_core")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
