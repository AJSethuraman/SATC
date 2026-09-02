"""The suite split, checked.

`make fast` leaves out the nine tests that open a document. That is a useful
thing and a dangerous one: a green line from a run that opened no document
looks exactly like a green line from one that opened all of them, and only one
of them means what the reader takes it to mean.

So two things have to hold, and neither is obvious enough to leave unchecked:
the nine are still marked, and a run that skips them says so.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The nine, by name. Listed rather than counted, because "nine tests carry
# the mark" would still pass if somebody marked nine of the fast ones and
# unmarked these.
RENDERS = {
    "tests/test_pipeline.py::test_the_opening_package_reaches_pdf",
    "tests/test_presend.py::test_a_pack_missing_an_asset_is_refused_and_nothing_is_written",
    "tests/test_presend.py::test_force_without_a_reason_is_refused",
    "tests/test_presend.py::test_force_with_a_reason_writes_the_pack_and_logs_what_failed",
    "tests/test_web.py::test_the_browser_can_build_the_pack_the_terminal_builds",
    "tests/test_web.py::test_the_browser_cannot_skip_the_gate",
    "tests/test_web.py::test_an_override_through_the_browser_is_recorded",
    "tests/test_web.py::test_the_failed_checks_come_before_the_green_ones_on_the_page",
    "tests/test_adhoc.py::test_a_document_sent_on_its_own_comes_out_as_a_pdf_a_client_can_open",
}


def _collect(*args: str) -> set[str]:
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only", *args],
        cwd=ROOT, capture_output=True, text=True).stdout
    return {line.strip() for line in out.splitlines() if "::" in line}


def test_the_ones_that_open_a_document_are_the_ones_marked():
    assert _collect("-m", "renders") == RENDERS


def test_the_mark_is_registered():
    """An unregistered mark still selects, but pytest warns on every use and a
    warning nobody reads is how a typo'd mark silently selects nothing."""
    out = subprocess.run([sys.executable, "-m", "pytest", "--markers"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    assert "@pytest.mark.renders:" in out
    # `markers` is a LINE LIST: a wrapped description is read as a second
    # marker. `pytest --markers` printed "@pytest.mark.tests carry this and
    # they are 64% of..." until the description was put on one line.
    assert "@pytest.mark.tests" not in out


def test_a_fast_run_refuses_to_look_like_a_full_one():
    """The whole safety of the split. Run one fast test with the render tests
    deselected, and the summary must say what was left out."""
    # Over a file that HAS render tests in it, so the deselection is real.
    # `test_presend.py` carries three of the nine.
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "not renders",
         "tests/test_presend.py"],
        cwd=ROOT, capture_output=True, text=True).stdout
    assert "THIS WAS NOT THE WHOLE SUITE" in out, out[-1500:]
    assert "3 test(s) that open a document" in out, (
        "the banner counted something other than what pytest deselected")


def test_a_whole_run_says_nothing_of_the_sort():
    """A check that fires on every run is noise, and noise is not read."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_the_split.py::test_the_mark_is_registered"],
        cwd=ROOT, capture_output=True, text=True).stdout
    assert "THIS WAS NOT THE WHOLE SUITE" not in out
