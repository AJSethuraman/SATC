"""Where the two real projects are, and how both get into one process.

Nothing is copied. `satc_system` is a src-layout package (`satc`), installed
editable in CI and put on `sys.path` here when it is not. `client-documents` is
flat modules with `pythonpath = .` (its `pytest.ini`), so its folder goes at
`sys.path[0]`, the way `exercise.py:43` does it.

THE COLLISIONS. client-documents has top-level modules named `requests`
(it shadows the HTTP library, and `intake.py:33` relies on that) and
`packaging` (it shadows the PyPI package pytest depends on). Nothing in the repo
had imported both projects in one process before this. So after import the
simulator asserts that both names resolve INSIDE client-documents; if they do
not, it refuses rather than driving a client-documents that is silently using
somebody else's module.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]                 # season-simulator/
REPO = HERE.parents[3]                    # the worktree root
SATC_SRC = REPO / "satc_system" / "src"
SATC_ROOT = REPO / "satc_system"
CD = REPO / "client-documents"

SHADOWED = ("requests", "packaging")


def put_projects_on_path() -> None:
    cd = str(CD)
    if sys.path[:1] != [cd]:
        if cd in sys.path:
            sys.path.remove(cd)
        sys.path.insert(0, cd)
    # ALWAYS this checkout's satc, right behind client-documents. Asking
    # `find_spec("satc")` first was tried and was wrong: any stray folder named
    # `satc` on the path (a scratch directory, the script's own folder) is a
    # namespace package to Python, "found", and `satc.app` then does not exist.
    # An editable install points at the same files, so putting the source
    # first costs nothing when one is present.
    src = str(SATC_SRC)
    if src in sys.path:
        sys.path.remove(src)
    sys.path.insert(1, src)


def assert_no_shadowing() -> list[str]:
    """Every shadowed name must be client-documents' own module. Returns the paths."""
    out = []
    for name in SHADOWED:
        mod = sys.modules.get(name)
        if mod is None:
            mod = __import__(name)
        where = Path(getattr(mod, "__file__", "") or "").resolve()
        if where.parent != CD.resolve():
            raise RuntimeError(
                f"`import {name}` resolved to {where}, not client-documents/{name}.py. "
                f"Something imported the PyPI {name!r} first; client-documents would "
                f"then run against the wrong module. Run the client-documents calls "
                f"in a fresh worker process.")
        out.append(str(where))
    return out
