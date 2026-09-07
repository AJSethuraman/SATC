"""The holes, read out of the queue where they were invisible.

THE FIRM, 7 September 2026: *"what's the simplest thing? like the desk can
simply ask for info, if we don't have it and if we do not (and it the answer
can't be tied to some data point) it's a hole in what we need to know"*.

Two states, and `engine.REASONS` already told them apart:

    context_not_on_file    there IS somewhere to record it and this engagement
                           has not -- a GAP, fixed by a preparer
    no_field_for_this_fact there is NOWHERE to record it, anywhere -- a HOLE,
                           fixed by the firm deciding the fact exists

What was missing was anywhere to read them out. The rarer and more valuable of
the two sat in a queue of thirty entries with nothing pointing at it, and a
session went and built a file format instead.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import unsupported                                          # noqa: E402
from tools import holes                                     # noqa: E402


def _entry(**kw):
    base = dict(id="U1", question="q", concluded="", believed_authority="",
                failed_because="authority_absent", recorded="2026-09-07",
                model="m", working="w")
    base.update(kw)
    return unsupported.Unsupported(**base)


def test_a_hole_is_reported_with_the_position_that_asked():
    """A hole with no position behind it is a request nobody can check."""
    out = holes.report([_entry(
        id="U9", failed_because=holes.HOLE, question="is this client different?",
        needs_field="capitalization_rule", asked_by="POS1")])
    assert "## Holes (1)" in out
    assert "capitalization_rule" in out
    assert "POS1" in out
    assert "is this client different?" in out


def test_a_gap_is_not_a_hole():
    out = holes.report([_entry(id="U4", failed_because=holes.GAP,
                               question="what does this client do?")])
    assert "## Holes (0)" in out
    assert "## Gaps (1)" in out
    assert "what does this client do?" in out


def test_the_two_are_never_summed():
    """Filing them together buries the rarer one, which is the whole point."""
    out = holes.report([
        _entry(id="U1", failed_because=holes.HOLE, needs_field="f", asked_by="P"),
        _entry(id="U2", failed_because=holes.GAP),
        _entry(id="U3", failed_because="authority_absent"),
    ])
    assert "## Holes (1)" in out and "## Gaps (1)" in out
    assert "3 refusals read" in out


def test_no_holes_says_so_rather_than_printing_nothing():
    """An empty list is a finding -- no position has yet asked for a fact with
    nowhere to live. A report that prints nothing reads as one that failed."""
    out = holes.report([_entry(failed_because="authority_absent")])
    assert "None recorded" in out
    assert "has not fired" in out


def test_no_value_a_client_gave_ever_reaches_the_report():
    """`unsupported/` is a file in this repository. A hole is the NAME of a fact
    and the position that wanted it, never the answer."""
    out = holes.report([_entry(
        failed_because=holes.HOLE, needs_field="capitalization_rule",
        asked_by="POS1",
        question="does this client use a $5,000 threshold?")])
    # The question is the caller's own words and is retained deliberately; what
    # must never appear is a recorded VALUE, and `Unsupported` has no field for
    # one. Asserted as the property rather than trusted: a future field carrying
    # a value would go red here.
    assert not any(f.name.endswith("_value") or f.name == "value"
                   for f in unsupported.Unsupported.__dataclass_fields__.values())


def test_it_runs_against_the_real_queue(capsys):
    """Run, not described. The report had only ever been seen empty."""
    assert holes.main([]) == 0
    out = capsys.readouterr().out
    assert "# Holes and gaps" in out
    assert "## Holes (" in out and "## Gaps (" in out


def test_a_missing_queue_says_so_and_fails(capsys, tmp_path):
    assert holes.main([str(tmp_path / "nope.md")]) == 1
    assert "no queue at" in capsys.readouterr().out
