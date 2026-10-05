"""Test setup for the season simulator.

TWO KINDS OF TEST LIVE HERE, AND THEY MUST NOT SHARE A PROCESS.

* Pure tests (the world, the guard's path arithmetic, the checkers against
  planted snapshots, the report) run in this pytest process.
* Anything that boots satc_system's app or drives client-documents runs in a
  WORKER SUBPROCESS, exactly as the launcher does. `satc.app.state` builds its
  `STATE` singleton at import time, and the guard refuses to run in a process
  where it already exists -- so an in-process season would test a simulator
  nobody runs.

The scratch-root block below is copied from `satc_system/tests/conftest.py:14-62`
(a locked `pytest-of-<user>` on this machine errored every `tmp_path` test);
copied rather than imported, as that file explains.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# No bytecode from THIS process either: the checkers import satc_system and
# client-documents modules, and a __pycache__ left in their folders is a write
# into projects this one only reads.
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_TEMPROOT = "PYTEST_DEBUG_TEMPROOT"


def _usable_scratch_root() -> Path | None:
    if os.environ.get(_TEMPROOT):
        return None
    root = Path(tempfile.gettempdir()) / "satc-sim-pt"
    if HERE.parents[1] in root.resolve().parents:
        return None
    if len(str(root)) > 100:
        return None
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return None
    return root


SCRATCH_ROOT = _usable_scratch_root()
if SCRATCH_ROOT is not None:
    os.environ[_TEMPROOT] = str(SCRATCH_ROOT)

# The checkers import satc_system and client-documents modules (pure ones --
# never satc.app). Put both on the path the way the worker does.
from season_sim import paths  # noqa: E402

paths.put_projects_on_path()
