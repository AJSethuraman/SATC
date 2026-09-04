"""What a partial run must say about itself.

`make fast` leaves out the eight tests that open a document, and those are the
ones this repository exists to be sure about — its first tenet is that nothing
may claim a document works without opening it.

So a run that skipped them has to SAY SO, at the end, where the result is read.
A green line from a run that opened no document looks exactly like a green line
from one that opened all of them, and only one means what the reader will take
it to mean. That is S2 — a check reports its denominator — applied to the test
run itself.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# ── pytest needs a scratch root it can actually use ──────────────────────────
#
# MEASURED, 4 September 2026: **1,165 errors and nothing passing** — every test
# that asks for `tmp_path`, failing at setup before its first line runs. The
# cause is not in this repository. `<temp>/pytest-of-<user>` on this machine
# carries a DACL that denies everything: `icacls` cannot read it back and
# PowerShell is refused identically, so pytest cannot scan its own scratch root
# and each request dies with `PermissionError [WinError 5]`.
#
# The same run reported `1434 passed, 2 skipped` earlier the same day. **A
# green number goes stale the moment the machine under it changes**, which is
# this repository's own first tenet pointed at its own test run.
#
# `canon/conftest.py` worked this out first; copied rather than imported,
# because canon lifts out whole and nothing outside it may depend on it.
#
# THE ROOT MUST NOT LIVE INSIDE THIS TREE — and here that matters more than
# anywhere else in the repository. The client-data guards walk these
# directories; a scratch root inside would have them read the suite's own
# fixtures and report a taxpayer identifier that never existed. It also must
# never land near `engagements/`, which holds real client files.
_TEMPROOT = "PYTEST_DEBUG_TEMPROOT"


def _usable_scratch_root() -> Path | None:
    """The root to impose, or None to leave pytest's own choice standing.

    Falling back is correct rather than fatal: on a machine whose default root
    works this does nothing, and on one where neither works the real errors
    should speak instead of an invented one.
    """
    if os.environ.get(_TEMPROOT):
        return None                    # an operator chose one; not ours to override
    root = (Path(tempfile.gettempdir()) / "satc-cd-pt").resolve()
    repo = Path(__file__).resolve().parents[1]
    if root == repo or repo in root.parents:
        return None                    # inside the tree the guards walk
    if len(str(root)) > 100:
        return None                    # Windows path budget; a long root breaks git
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


_LEFT_OUT: list = []


def pytest_deselected(items):
    """Count what pytest actually dropped, not what this file guesses it did.

    The first version counted `renders`-marked items inside
    `pytest_collection_modifyitems`, which sees the collection for THIS run --
    so selecting a single file left nothing to count and the banner went
    silent on exactly the runs most likely to mislead. `pytest_deselected` is
    handed the real deselections, whatever was selected.
    """
    _LEFT_OUT.extend(i for i in items if i.get_closest_marker("renders"))


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _LEFT_OUT:
        return
    write = terminalreporter.write_line
    write("")
    write("=" * 70)
    write(f"  THIS WAS NOT THE WHOLE SUITE. {len(_LEFT_OUT)} test(s) that open "
          f"a document")
    write("  were left out — the ones that prove a client can actually read")
    write("  what this software produces.")
    write("")
    write("  Green here does not mean a document renders. Run `python -m "
          "pytest`")
    write("  before pushing; CI runs the whole suite either way.")
    write("=" * 70)


# ── no test may see the owner's real Square token ────────────────────────────
#
# `payments.processor` now falls back to a token the owner sealed into their own
# profile with `payments --setup`. That is right for the app and poison for a
# suite: whether a test sees a token would depend on whether the person running
# it happens to have set Square up, so the same commit would pass on this
# machine and fail on a clean one -- or, worse, pass here for the wrong reason.
#
# Autouse and unconditional. A test that WANTS a remembered token points
# `square_setup.TOKEN_FILES` somewhere itself.
@pytest.fixture(autouse=True)
def _no_remembered_square_token(tmp_path_factory, monkeypatch):
    try:
        import square_setup
    except ImportError:                     # not every checkout has it yet
        return
    nowhere = tmp_path_factory.mktemp("no-square-token")
    monkeypatch.setattr(square_setup, "TOKEN_FILES",
                        {True: nowhere / "sandbox", False: nowhere / "production"})
