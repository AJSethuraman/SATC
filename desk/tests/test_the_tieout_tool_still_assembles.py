"""The tie-out tool must at least be importable and whole.

WHY THIS EXISTS, and it is a near miss rather than a theory. On 6 September 2026
the comparison functions were moved out of `tools/tieout.py` into `comparing`, so
that `proving` could share them without dragging `ssl` onto the import path. The
extraction took the `Line` dataclass with it — the record every verdict is
returned in — and `check()` was left referring to a name that no longer existed.

THE WHOLE SUITE PASSED. 462 tests, green, with the tie-out tool unable to produce
a single result. Nothing here exercises `check()`, because `check()` fetches and
this desk's conftest replaces the socket layer; so the one tool whose output the
firm is being asked to trust had no test that it assembled at all. It was found
by running it by hand against irs.gov, which is exactly the check that is not
supposed to be the safety net.

WHAT THIS CAN AND CANNOT DO. It cannot fetch, so it cannot tell whether the tool
gets the right answer — the live run is still the only thing that proves that,
and 531 of 533 is still a measurement taken by hand. What it CAN do is fail on
the commit that leaves the tool unable to run: every name `check()` reaches for
exists, `Line` can be built and read, and the parsing that has no network in it
works on real input.
"""
from __future__ import annotations

import dataclasses
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import comparing                                            # noqa: E402
import record                                               # noqa: E402
import tieout                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402


def test_every_global_check_reaches_for_exists():
    """The exact failure above: `check()` referred to `Line` after `Line` was
    moved out. Reading the function's own bytecode is the only way to catch a
    name error inside a branch no offline test can reach."""
    # `__builtins__` is a DICT inside an imported module and a MODULE inside
    # __main__, so `dir(__builtins__)` there lists dict methods and `Exception`
    # reads as undefined. Import the module by name and the question is exact.
    import builtins

    absent = [n for n in tieout.check.__code__.co_names
              if not hasattr(tieout, n) and not hasattr(builtins, n)]
    # Attribute lookups on locals land in `co_names` too (`source.id`, `got.at`),
    # so this narrows to names that look module-level: capitalised, or private.
    unresolved = [n for n in absent if n[0].isupper() or n.startswith("_")]
    assert not unresolved, (
        f"`check()` reaches for {unresolved}, which `tieout` does not define. "
        f"The tool cannot produce a result, and no offline test runs it.")


def test_the_verdict_record_is_whole():
    fields = {f.name for f in dataclasses.fields(tieout.Line)}
    for needed in ("desk", "citation", "verdict", "how", "matched_chars",
                   "stopped_at", "sha256", "fetched_at", "url"):
        assert needed in fields, f"Line lost {needed!r}"
    line = tieout.Line("d", "c", "S1", "t", "u", 10, tieout.TIED
                       if hasattr(tieout, "TIED") else "TIED")
    assert line.verdict


def test_the_comparison_is_borrowed_and_not_copied():
    """One folding table, one meaning for a marked omission. Two copies would
    disagree within a week and report different verdicts about one passage."""
    assert tieout.normalise is comparing.normalise
    assert tieout.elided_match is comparing.elided_match
    assert tieout.ELLIPSIS is comparing.ELLIPSIS


def test_comparing_reaches_nothing_that_reaches_the_network():
    """The property that let `proving` import it at all. `tools/tieout.py`
    fetches, so importing it pulls in `ssl`, and this suite replaces the socket
    layer — every test of `proving` failed inside `ssl.py` until the comparison
    moved somewhere that imports neither."""
    src = (HERE / "comparing.py").read_text()
    for forbidden in ("import urllib", "import ssl", "import socket",
                      "import http", "import requests", "subprocess"):
        assert forbidden not in src, (
            f"comparing.py reaches {forbidden!r}; anything the engine's front "
            f"door imports must not be able to reach the network")


def test_the_brief_is_parsed_back_out_of_real_text():
    """`brief_passages` is the half of the tool with no network in it, and it is
    the half that decides what goes on the `ours` side of every comparison. A
    citation the brief does not carry is a finding in itself."""
    desk = record.load(DESKS / "cash-and-bank")
    parsed = tieout.brief_passages(desk)
    assert parsed, "the brief parsed to nothing"
    held = {p.citation for p in desk.passages}
    assert set(parsed) <= held, (
        f"the brief carries citations the record does not: "
        f"{sorted(set(parsed) - held)}")
    # AND THE TEXT IS THE PASSAGE'S, not a summary of it.
    for citation, text in parsed.items():
        stored = desk.passage(citation)
        assert comparing.normalise(text)[:80] == \
            comparing.normalise(stored.text)[:80], citation
