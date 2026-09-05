"""The front door, which was a promise in a refusal message until it was built.

`routing.refusal_naming_the_desk` has always told a stopped agent to "Ask <desk>
with ask_desk, then come back with the citation." There was no `ask_desk`. Seven
desks, an engine, a measured gate, and nothing a caller could invoke — the record
complete and unreachable. These tests are about the door, not the record.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import ask
import engine
import record
from conftest import DESKS


def test_the_tool_the_refusal_message_names_exists():
    """The one that would have caught it. A refusal that instructs a caller to
    use a tool nobody wrote is a dead end wearing a next step's clothes."""
    import routing
    msg = routing.refusal_naming_the_desk(
        "is a brewery tab a business meal?", routing.registry(DESKS))
    assert "ask_desk" in msg, "fixture no longer proves it"
    assert callable(ask.consult) and callable(ask.answer)


def test_a_question_comes_back_with_what_it_may_be_answered_from():
    hits = ask.consult("is a brewery tab a business meal?", DESKS)
    assert [d for d, _ in hits] == ["meals-and-entertainment"]
    text = hits[0][1]
    assert "## The authority" in text and "26 CFR 1.274" in text


def test_silence_is_a_result():
    """A question touching no desk comes back empty — not routed to the nearest
    one. A router that always answers is one whose answer means nothing."""
    assert ask.consult("what time is the train", DESKS) == []


def test_the_brief_never_carries_the_answer_key():
    """`PROBLEMS.md` is the key. A desk scored against problems its answerer
    could read measures transcription, not knowledge."""
    desk = record.load(DESKS / "cash-and-bank")
    text = ask.brief("does the client hold materials at year end?", desk)
    for p in desk.problems:
        assert p.facts not in text, f"{p.id}'s facts reached the answerer"
        assert f"**Answer:** {p.answer}" not in text


def test_the_brief_never_carries_a_proposal():
    """A PROPOSED position is one agent's suggestion nobody has said yes to.
    Showing it would let a guess become the next agent's premise, which is the
    whole failure the two-store split exists to prevent."""
    for name in ("capitalization-and-de-minimis", "vehicle-expense"):
        desk = record.load(DESKS / name)
        proposals = [q for q in desk.positions if q.proposed]
        assert proposals, f"{name} no longer proves it"
        text = ask.brief("what is our capitalisation threshold?", desk)
        for q in proposals:
            assert q.position not in text, f"{name}/{q.id} reached the answerer"


def test_the_firms_own_positions_do_reach_the_answerer():
    """The other half. A ratified position is the firm's word and real
    authority — on a `human_only` source it is the desk's ENTIRE knowledge."""
    desk = record.load(DESKS / "cash-and-bank")
    ratified = [q for q in desk.positions if not q.proposed]
    assert ratified, "fixture no longer proves it"
    text = ask.brief("is an uncleared cheque a reconciling item?", desk)
    assert all(q.position in text for q in ratified)


def test_an_answer_goes_through_the_production_path():
    desk = record.load(DESKS / "cash-and-bank")
    cb4 = next(p for p in desk.problems if p.id == "CB4")

    good = ask.answer(cb4.facts, "cash-and-bank", position=cb4.answer,
                      citation=cb4.citation, desks=DESKS, keep=False)
    assert not isinstance(good, engine.Refusal)

    timing = next(c for c in desk.answered_by if "did not yet include" in c)
    bad = ask.answer(cb4.facts, "cash-and-bank",
                     position="a reconciling item, no entry in the books",
                     citation=timing, desks=DESKS, keep=False)
    assert isinstance(bad, engine.Refusal)
    assert bad.reason == "citation_does_not_support"


def test_an_escalation_is_a_first_class_answer():
    out = ask.answer("what did the client buy at the hardware store?",
                     "cash-and-bank", escalate="facts_not_established",
                     desks=DESKS, keep=False)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "facts_not_established"


def test_a_refusal_is_kept_with_its_reasoning(tmp_path):
    """A refusal is a finding, and the queue is the only thing that says what
    the record is missing. Thrown away, the finding is destroyed."""
    import shutil
    desks = tmp_path / "desks"
    shutil.copytree(DESKS / "cash-and-bank", desks / "cash-and-bank")

    out = ask.answer("is a brewery tab a business meal?", "cash-and-bank",
                     position="fully deductible", citation="26 CFR 9.9-9",
                     model="a test", desks=desks)
    assert isinstance(out, engine.Refusal)

    queue = desks / "cash-and-bank" / "unsupported" / "asked.md"
    assert queue.is_file(), "the refusal was dropped"
    import unsupported
    kept = unsupported.parse(queue.read_text(encoding="utf-8"))
    assert len(kept) == 1
    assert "brewery" in kept[0].question
    assert kept[0].failed_because == "authority_absent"


def test_keeping_is_the_default_and_the_default_is_the_point(tmp_path):
    """`keep=False` exists for measuring. Defaulting it off would make every
    caller who forgot it silently destroy the findings."""
    import inspect
    assert inspect.signature(ask.answer).parameters["keep"].default is True
