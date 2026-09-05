"""What the file already says, and what happens when it does not say it.

THE HOLE THIS CLOSES. `ask.consult` took a question and nothing else, so a Home
Depot charge from a general contractor and the same charge from a hairstylist
reached the same desk as the same question. The firm, 5 September 2026, holding
`personal-or-business/POS1` rather than ratifying it: *"the Accountant should've
already recorded and known what sort of business we're dealing with ... if
they're missing that piece of information, something was just missing from the
file."*

The rule these tests defend is that the desk is TOLD, never that it works it out.
A desk that inferred the trade from the vendor would be running exactly the
reasoning the position forbids, and it would be right often enough to be trusted.
"""
from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

import ask
import engine
import positions
import record
from conftest import DESKS, ROOT

#: A question whose SUBJECT this desk answers from S1, which is where POS1's
#: citation lives. "Home Depot" will not do, and the reason is worth keeping:
#: the word `home` fires S3, the home-office source, so the vendor question
#: routes to the wrong rule on the first word of the shop's name.
ASKED = "they bought clothing at that store — is it a personal expense?"

CONTRACTOR = record.Context(facts={"trade": "general contractor"})
STYLIST = record.Context(facts={"trade": "hairstylist"})


@pytest.fixture
def pob():
    return record.load(DESKS / "personal-or-business")


def _needing(desk):
    q = next((q for q in desk.positions if q.needs), None)
    assert q is not None, f"{desk.name} declares no needs, so nothing is proved"
    return q


def _ratified(desk, q):
    """The same desk with that position ratified, which is what makes it bite.

    Both positions that declare a need are still PROPOSALS -- the firm held them
    on 5 September 2026 asking for exactly this input. So the gate is exercised
    against a ratified copy rather than by ratifying on their behalf, which is
    the one thing an agent may never do here.
    """
    return dataclasses.replace(desk, positions=tuple(
        dataclasses.replace(p, ratified="for this test only") if p is q else p
        for p in desk.positions))


# -- the record ---------------------------------------------------------------

def test_a_need_the_desk_does_not_record_cannot_load(tmp_path, pob):
    """A need nothing can meet is a position that can never be served, and it
    would fail at answer time as a refusal blaming the caller for our typo."""
    with pytest.raises(record.RecordError) as e:
        record.load(_desk_with(tmp_path, pob, needs="favourite colour"))
    assert "favourite colour" in str(e.value)
    assert "Records:" in str(e.value)


def test_the_records_line_stops_at_the_blank_line(pob):
    """Read with the wrapping-field reader, this swallowed the italic paragraph
    that explains the fact and parsed FOUR facts out of one -- named things like
    "in the firm's words". A silent over-read is the same defect as a silent
    truncation and this file is where it would land."""
    assert pob.records == ("trade",)
    text = (DESKS / "personal-or-business" / "SUBJECTS.md").read_text(encoding="utf-8")
    assert "*What the client does" in text, "the prose that broke it is gone"


def test_a_problem_can_carry_the_facts_it_was_written_with():
    """So ratifying a position with a need does not silently convert a desk's
    measured score into a column of refusals."""
    p = record.parse_problems(
        "## P1 · a title\n\n**Citation:** X\n\n**Answer:** yes\n\n"
        "**Facts:** something happened\n\n**On file:** trade: general contractor\n")[0]
    assert p.context.facts == {"trade": "general contractor"}
    assert p.context.missing(("trade",)) == ()
    assert p.context.missing(("taxpayer",)) == ("taxpayer",)


def test_a_problem_with_no_on_file_line_meets_no_need():
    p = record.parse_problems(
        "## P1 · a title\n\n**Citation:** X\n\n**Answer:** yes\n\n"
        "**Facts:** something happened\n")[0]
    assert p.context.missing(("trade",)) == ("trade",)


@pytest.mark.parametrize("bad", ["trade", "trade:", ": general contractor"])
def test_an_on_file_entry_that_is_not_a_named_fact_is_refused(bad):
    with pytest.raises(record.RecordError):
        record.parse_problems(
            "## P1 · t\n\n**Citation:** X\n\n**Answer:** y\n\n**Facts:** f\n\n"
            f"**On file:** {bad}\n")


# -- the gate -----------------------------------------------------------------

def test_the_rule_refuses_when_the_fact_is_not_on_file(pob):
    q = _needing(pob)
    desk = _ratified(pob, q)
    out = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                       desk, question=ASKED)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "context_not_on_file"
    assert "trade" in out.detail


def test_the_same_rule_serves_once_the_file_says_what_they_do(pob):
    q = _needing(pob)
    desk = _ratified(pob, q)
    out = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                       desk, question=ASKED,
                       context=CONTRACTOR)
    assert not isinstance(out, engine.Refusal), getattr(out, "detail", out)


def test_the_value_does_not_decide_it_only_its_presence(pob):
    """A contractor and a hairstylist both get served: the position tells the
    ANSWERER what to weigh, and the engine does not adjudicate a trade. An engine
    that read the value would be inferring, one layer lower down."""
    q = _needing(pob)
    desk = _ratified(pob, q)
    served = [engine.serve(engine.Answer(position=q.position, citation=q.citation),
                           desk, question=ASKED, context=c)
              for c in (CONTRACTOR, STYLIST)]
    assert not any(isinstance(o, engine.Refusal) for o in served)


def test_a_desk_whose_positions_need_nothing_is_untouched():
    """Narrowing only. The cost of the new gate is paid by the two positions
    that opted into it and by nothing else."""
    desk = record.load(DESKS / "cash-and-bank")
    assert not any(q.needs for q in desk.positions)
    q = next(q for q in desk.positions if not q.proposed)
    out = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                       desk, question="an uncleared cheque")
    assert not isinstance(out, engine.Refusal)


def test_the_scoreboard_sees_the_same_gate_as_the_caller(pob):
    """`_check` is shared on purpose. If grading skipped this, the scoreboard
    would stop measuring what the gate actually does -- the shape of nearly
    every real bug in this operation."""
    q = _needing(pob)
    desk = _ratified(pob, q)
    problem = record.Problem(id="X1", title="t", citation=q.citation,
                             answer=q.position, facts=ASKED)
    graded = engine.grade(engine.Answer(position=q.position, citation=q.citation),
                          problem, desk)
    assert graded.reason == "context_not_on_file"

    with_facts = dataclasses.replace(problem, context=CONTRACTOR)
    assert engine.grade(engine.Answer(position=q.position, citation=q.citation),
                        with_facts, desk).outcome is engine.Outcome.CORRECT


# -- the brief ----------------------------------------------------------------

def test_the_brief_names_the_fact_it_was_not_given(pob):
    """The half that matters. Printing only what is on file leaves an answerer to
    assume the rest was not needed; printing the gap by name is what lets it
    escalate instead of reasoning from the vendor."""
    text = ask.brief(ASKED, pob)
    assert "NOT ON FILE" in text and "trade" in text
    assert "do not infer it" in text


def test_the_brief_repeats_what_it_was_given(pob):
    text = ask.brief(ASKED, pob, CONTRACTOR)
    assert "general contractor" in text
    assert "NOT ON FILE" not in text


def test_consult_carries_the_context_into_every_brief():
    out = ask.consult(ASKED, DESKS, CONTRACTOR)
    assert out, "the question no longer reaches a desk"
    assert any("general contractor" in brief for _, brief in out)


# -- what must never leave --------------------------------------------------

def test_no_recorded_value_reaches_the_refusal_queue(pob, tmp_path):
    """The queue is a file in this repository. A trade is not identity, but the
    mapping is open by construction, so nothing a caller passes is written to
    disk -- only which facts were missing, which is a list of NAMES."""
    q = _needing(pob)
    desk = _ratified(pob, q)
    out = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                       desk, question=ASKED,
                       context=record.Context(facts={"trade": "SECRET-VALUE"}))
    assert not isinstance(out, engine.Refusal)
    refused = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                           desk, question=ASKED,
                           context=record.Context(facts={"other": "SECRET-VALUE"}))
    assert isinstance(refused, engine.Refusal)
    assert "SECRET-VALUE" not in refused.detail


def test_the_context_holds_no_field_for_a_person():
    """There is deliberately nowhere to put a name, a TIN or an address: the
    fields are a mapping the DESK names, and every desk that names one names a
    fact about the work."""
    fields = {f.name for f in dataclasses.fields(record.Context)}
    assert fields == {"facts"}
    for d in sorted(DESKS.iterdir()):
        if not (d / "SUBJECTS.md").is_file():
            continue
        for name in record.load(d).records:
            assert name not in ("name", "client", "ssn", "ein", "tin", "address"), (
                f"{d.name} records {name!r}, which is identity and belongs in the vault")


def _desk_with(tmp_path, desk, *, needs):
    """A copy of a real desk on disk with one position's Needs rewritten."""
    import shutil
    dst = tmp_path / desk.name
    shutil.copytree(DESKS / desk.name, dst)
    p = dst / "positions" / "POSITIONS.md"
    p.write_text(p.read_text(encoding="utf-8").replace(
        "**Needs:** trade", f"**Needs:** {needs}"), encoding="utf-8")
    return dst
