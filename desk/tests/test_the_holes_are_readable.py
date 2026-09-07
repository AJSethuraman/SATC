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


# ---------------------------------------------------------------------------
# A FACT NAME HAS TO LOOK LIKE ONE, and this is the bug that produced the rule.
#
# On 7 September a session set out to remove the last fact from a desk's
# `Records:` line and left the line in place, reading `**Records:** *(nothing)*`.
# The parser read the placeholder AS A FACT. The desk then declared it recorded
# something called `*(nothing)*`; `serve` would have treated it as a fact an
# engagement could be missing, and `ask.brief` would have printed it to an
# answerer as a real question about the client.
#
# (The removal itself was also wrong and was reverted — the firm had answered
# "Add the field" on `dec-cap-field` that morning, and the line is their
# decision. The parser bug it exposed is real either way.)


def test_a_placeholder_in_a_records_line_is_not_a_fact():
    import record as rec
    from pathlib import Path as _P
    body = (_P(HERE / "desks" / "capitalization-and-de-minimis" / "SUBJECTS.md")
            .read_text(encoding="utf-8"))
    broken = body.replace("**Records:** capitalization_rule",
                          "**Records:** *(nothing)*")
    with pytest.raises(rec.RecordError) as e:
        rec.parse_subjects(broken, 'capitalization-and-de-minimis')
    assert "not a fact name" in str(e.value)


@pytest.mark.parametrize("name", ["*(nothing)*", "the trade", "n/a", "-", "(none)"])
def test_only_a_name_gets_through(name):
    import record as rec
    from pathlib import Path as _P
    body = (_P(HERE / "desks" / "capitalization-and-de-minimis" / "SUBJECTS.md")
            .read_text(encoding="utf-8"))
    with pytest.raises(rec.RecordError):
        rec.parse_subjects(body.replace("**Records:** capitalization_rule",
                                        f"**Records:** {name}"),
                           'capitalization-and-de-minimis')


def test_the_real_records_lines_all_still_load():
    """The guard must not eat the record it is guarding."""
    import record as rec
    n = 0
    for d in sorted((HERE / "desks").iterdir()):
        if (d / "SOURCES.md").is_file():
            n += len(rec.load(d).records)
    assert n >= 3, f"only {n} declared facts across every desk; the guard bit"


def test_case_is_normalised_rather_than_refused():
    """`TRADE` is not a bad name, it is the same name shouted. The parser
    lowercases before it validates, and that is worth pinning: a guard that
    refused it would make the record fussy about something that does not
    matter, which is how guards get loosened later."""
    import record as rec
    from pathlib import Path as _P
    body = (_P(HERE / "desks" / "capitalization-and-de-minimis" / "SUBJECTS.md")
            .read_text(encoding="utf-8"))
    reg = rec.parse_subjects(
        body.replace("**Records:** capitalization_rule",
                     "**Records:** CAPITALIZATION_RULE"),
        "capitalization-and-de-minimis")
    assert reg.records == ("capitalization_rule",)
