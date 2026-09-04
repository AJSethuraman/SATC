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

import pytest

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
