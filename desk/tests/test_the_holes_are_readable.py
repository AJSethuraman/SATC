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

AND THEN IT READ ONE STORE OF THREE. The first version globbed `unfiled/*.md`
and printed **Gaps (0) — None recorded. The mechanism is live and has not
fired** on an evening when five `context_not_on_file` refusals stood in the
latest run, naming three facts and the positions that wanted them. Refusals are
recorded in `unfiled/`, in each desk's own `unsupported/`, and in the last run's
`served.json`; a report over one of them is not a clean report, it is an
unfinished read reported as a finding. The tests below pin BOTH halves: that the
two states are told apart, and that a count says what it was counted over.
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
    assert "### Holes (1)" in out
    assert "capitalization_rule" in out
    assert "POS1" in out
    assert "is this client different?" in out


def test_a_gap_is_not_a_hole():
    out = holes.report([_entry(id="U4", failed_because=holes.GAP,
                               question="what does this client do?")])
    assert "### Holes (0)" in out
    assert "### Gaps (1)" in out
    assert "what does this client do?" in out


def test_the_two_are_never_summed():
    """Filing them together buries the rarer one, which is the whole point."""
    out = holes.report([
        _entry(id="U1", failed_because=holes.HOLE, needs_field="f", asked_by="P"),
        _entry(id="U2", failed_because=holes.GAP),
        _entry(id="U3", failed_because="authority_absent"),
    ])
    assert "### Holes (1)" in out and "### Gaps (1)" in out
    assert "3 refusals read" in out


def test_no_holes_says_so_rather_than_printing_nothing():
    """An empty list is a finding -- no position has yet asked for a fact with
    nowhere to live. A report that prints nothing reads as one that failed."""
    out = holes.report([_entry(failed_because="authority_absent")])
    assert "None recorded" in out


def test_an_empty_count_says_what_it_was_counted_over():
    """THE SENTENCE THIS REPLACES WAS WRONG. It read *"the mechanism is live and
    has not fired"* -- a claim about the mechanism, made from one store of
    three, while the mechanism had fired five times into another. A zero may
    only ever be a zero OF WHAT WAS READ, and the wording has to carry that or
    the next reader takes it for the same absolute claim."""
    out = holes.report([_entry(failed_because="authority_absent")])
    assert "None recorded** in what was read" in out
    assert "has not fired" not in out, (
        "an absolute claim about the mechanism, from a partial read")


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


# ---------------------------------------------------------------------------
# READING ALL THREE STORES, and keeping the live run out of the durable count.


def test_every_store_a_refusal_lands_in_is_read():
    """The bug, stated as a property. `stores()` must find all three families,
    because the version that found one printed a zero over five live refusals."""
    kinds = {where.split("/")[0] for _, where, _ in holes.stores()}
    assert kinds == {"unfiled", "desks", "runs"}, (
        f"only {sorted(kinds)} read; a refusal filed anywhere else is invisible")


def test_only_the_latest_run_is_read():
    """An older run is a photograph of a record that has moved -- six of the
    queue's eleven authority gaps were answered within two days of being filed.
    Reading every run would report closed holes as open."""
    runs = [w for _, w, _ in holes.stores() if w.startswith("runs/")]
    assert len(runs) == 1, f"{len(runs)} runs read; only the latest is live"
    every = sorted(p.name for p in (HERE / "runs").glob("*asked-*")
                   if (p / "served.json").is_file())
    assert len(every) > 1, "no second run on disk — this test proves nothing"
    assert runs[0].split("/")[1] == every[-1]


def test_the_live_run_is_not_added_to_the_durable_count():
    """Two headings, never one number over both. The queue is every hole ever
    found and holes get filled; a total across both counts a closed one twice."""
    out = holes.report([
        holes.Entry(failed_because=holes.GAP, question="filed",
                    ref="U1", where="unfiled/x.md"),
        holes.Entry(failed_because=holes.GAP, question="tonight",
                    ref="Q8", where="runs/asked-x/served.json"),
    ])
    durable, live = out.split("## Live")
    assert "### Gaps (1)" in durable and "### Gaps (1)" in live
    assert "### Gaps (2)" not in out


def test_the_same_refusal_filed_and_live_is_reported_in_both():
    """A gap written down at close and hit again tonight is the NORMAL case, and
    both readings are wanted: the filed one says it is known, the live one says
    it is still open.

    THIS TEST IS WEAKER THAN IT LOOKS, said rather than left to be assumed. The
    partition is written on provenance (`_is_live`) instead of `e not in live`,
    and the equality form passes this test too -- `where` is part of `Entry`, so
    a filed row and a live row are never equal and equality can never drop one.
    What is pinned is the OUTPUT property. The implementation is the clearer of
    two that are equivalent today, and no test here distinguishes them."""
    same = dict(failed_because=holes.GAP, question="q", ref="U1")
    out = holes.report([holes.Entry(where="unfiled/x.md", **same),
                        holes.Entry(where="runs/asked-x/served.json", **same)])
    assert "2 refusals read" in out
    durable, live = out.split("## Live")
    assert "### Gaps (1)" in durable and "### Gaps (1)" in live


def test_a_run_names_the_fact_and_the_position_that_wanted_it():
    """The chain the firm made a condition of a desk asking for a field. The run
    writer recorded the reason and the prose and dropped both, so a run-sourced
    hole could not say which field or whose position -- recoverable only by
    parsing `detail`'s sentence, which is inferring."""
    got = holes._from_run(
        {"q": 4, "desk": "capitalization-and-de-minimis", "served": False,
         "reason": holes.GAP, "fact": "capitalization_rule",
         "by_position": "POS2", "question": "what is the threshold?"},
        "runs/asked-x/served.json")
    assert got.fact == "capitalization_rule" and got.by == "POS2"
    assert "capitalization_rule" in holes.report([got])


def test_a_run_recorded_before_the_chain_was_kept_says_so():
    """Blank, and SAID to be blank. The fact is named in `detail`'s sentence and
    reading it back out would be inferring -- so an old run reports the refusal
    and admits what it cannot say."""
    out = holes.report([holes._from_run(
        {"q": 4, "desk": "d", "served": False, "reason": holes.HOLE,
         "question": "q"}, "runs/asked-x/served.json")])
    assert "(field not recorded)" in out
    assert "the position that asked is not recorded here" in out


def test_the_live_close_run_is_actually_carried_into_the_report(capsys):
    """RUN, NOT DESCRIBED. The five gaps that were invisible are the reason this
    exists; asserting the plumbing without asserting they arrive would repeat
    the original mistake one layer up."""
    assert holes.main([]) == 0
    out = capsys.readouterr().out
    assert "## What was read" in out
    assert "runs/" in out and "unfiled/" in out
    assert "capitalization_rule" in out, (
        "the field the firm said to add, still unbuilt, and again unreported")


def test_a_json_run_handed_in_by_hand_is_read_as_a_run():
    """`main` dispatches on suffix, so a path given on the command line lands
    under the same heading it would have found itself."""
    p = HERE / "runs" / "reasked-2026-09-07-evening" / "served.json"
    entries = holes._read_one(p, str(p))
    assert entries and all(e.where.endswith(".json") for e in entries)
    assert all(e.failed_because for e in entries), "a served row leaked in"


def test_no_client_value_reaches_the_report_from_a_run_either():
    """`unfiled/` was checked for this; the run is a second door into the same
    file. A run row carries the caller's question and the fact's NAME, and the
    report prints no other field off it."""
    row = {"q": 1, "desk": "d", "served": False, "reason": holes.GAP,
           "question": "q", "fact": "trade", "by_position": "POS1",
           "detail": "SECRET", "working": "SECRET", "position": "SECRET",
           "citation": "SECRET"}
    out = holes.report([holes._from_run(row, "runs/asked-x/served.json")])
    assert "SECRET" not in out
