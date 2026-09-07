"""Every field on a served answer is about the SOURCE. None is about the answer.

THE INCIDENT, 7 September 2026, found by a session testing the installed plugin
on the Forge rather than by anyone building it. It aimed five traps at
`fixed-assets` — the largest desk, and the one carrying no ratified positions at
all — and FOUR SERVED. The sharpest cited § 1.263(a)-2(d)(1), whose own text
opens *"a taxpayer must capitalize amounts paid to acquire or produce a unit of
real or personal property"*, and concluded **"deducted, not capitalized"**. The
literal negation of its own citation, served `tier=primary`, `binding=True`, no
caveat.

WHY EVERY CHECK PASSED AND WAS RIGHT TO. `tier` is the regulation's standing.
`binding` says the firm declared that source as authority that binds — not that
this answer binds. `checked_subject` is word overlap between the question and
the desk's subjects. `checked` is when somebody last confirmed the PASSAGE
against its publisher. Together they read to an accountant as *"this was
checked"*, and the one thing they think was checked is the one thing that was
not. The tester's words: *"Served carries no field for 'did anyone check that
this paragraph says this?'"*

AND THE SKILL ALREADY SAID SO, WHICH WAS NOT ENOUGH. `ask-desk` carries the
sentence *"what it does not verify is that the conclusion follows"* — in prose,
at the top, read once by the agent and long gone by the time an answer is
rendered onward to a person. A warning that does not travel with the thing it
warns about is a warning nobody reads.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import engine                                               # noqa: E402
import record                                               # noqa: E402

TRAP_Q = "is the invoice price of a forklift deducted or capitalized?"
TRAP_CITE = "26 CFR 1.263(a)-2(d)(1)"


@pytest.fixture(scope="module")
def trap():
    """The tester's sharpest trap, served. It STILL serves — that is the point.
    Nothing here claims to have made it refuse; the domain guard cannot reach
    it, because a tax question cited to a tax regulation is in the right body of
    authority and simply says the opposite of what was claimed."""
    out = ask.answer(TRAP_Q, "fixed-assets",
                     position="deducted, not capitalized",
                     citation=TRAP_CITE, model="the trap", keep=False)
    assert isinstance(out, engine.Served), (
        "the trap now refuses — good, but this file's premise has moved and its "
        "docstring is describing something that no longer happens")
    return out


def test_the_answer_says_nobody_checked_the_conclusion(trap):
    assert trap.unchecked, "a served answer carries no such statement"
    assert "NOBODY CHECKED" in trap.unchecked


def test_it_says_what_WAS_checked_rather_than_only_what_was_not(trap):
    """A bare disclaimer trains a reader to skip it. Naming the three real
    checks is what makes the fourth one's absence legible."""
    for real in ("citation resolves", "subject", "primary"):
        assert real in trap.unchecked, f"never says {real!r} was checked"


def test_the_cited_paragraph_travels_with_the_answer(trap):
    """Until a judge exists the reader IS the check, and they cannot perform it
    on a citation they have to go and look up. Making them fetch it is what
    turns the review nominal."""
    assert trap.passage, "the answer arrives without the words it rests on"
    assert "must capitalize" in trap.passage


def test_the_answer_therefore_refutes_itself_on_sight(trap):
    """THE WHOLE POINT, asserted as the property rather than trusted. Printed
    together, position and passage contradict each other in two lines. Printed
    apart, the same answer reads as settled law."""
    assert "deducted, not capitalized" in trap.position
    assert "must capitalize" in trap.passage


def test_it_cannot_be_left_off(trap):
    """Computed inside `serve`, never passed in — so no caller can omit it and
    no code path can produce a Served without it."""
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for prob in desk.problems:
            out = engine.serve(
                engine.Answer(position=prob.answer, citation=prob.citation),
                desk, question=prob.facts)
            if isinstance(out, engine.Served):
                assert out.unchecked, f"{prob.id} on {d.name} served without it"
                assert out.passage or out.position, (
                    f"{prob.id} on {d.name} served with neither passage nor "
                    f"position — nothing for a reader to check against")


def test_binding_is_described_as_a_property_of_the_source(trap):
    """`binding` is the field most likely to be misread, and it is not renamed —
    ten call sites to fix a READING problem is the wrong tool. Instead the
    sentence beside it says what it means."""
    assert "about the SOURCE" in trap.unchecked
    assert "None of it is about the conclusion" in trap.unchecked


def test_a_non_binding_answer_says_so_in_the_same_sentence():
    """The other branch, so the wording cannot quietly assert "binding" on an
    answer that does not bind."""
    out = ask.answer("what do I do with a $10 service charge nobody entered?",
                     "cash-and-bank",
                     position="an entry in the books",
                     citation='IRS Pub. 583 (12/2024), "Reconciling the '
                              'checking account" — what the books are updated for',
                     model="m", keep=False)
    assert isinstance(out, engine.Served)
    assert "does not bind" in out.unchecked or out.binding, (
        "a non-binding source served with binding language")


def test_the_skill_tells_the_agent_to_pass_both_on():
    """The object carrying it is half. An agent that renders `position` and
    `citation` and drops the rest has undone the whole thing, so the skill has
    to say so where the agent reads what to do with an answer."""
    skill = (HERE / "skills" / "ask-desk" / "SKILL.md").read_text(encoding="utf-8")
    flat = " ".join(skill.split())
    assert "out.unchecked" in flat and "out.passage" in flat, (
        "the skill never shows the agent printing them")
    assert "MUST pass both on" in flat
    assert "not boilerplate to trim" in flat


def test_a_position_backed_answer_has_something_to_read():
    """FOUND BY RUNNING THE ROUND TRIP, not by a test.

    The first version read `passage.text`, and a ratified position has none —
    it carries the firm's own WORDS in `.position`. So the cash desk served
    "Read the passage." with nothing underneath it: a disclaimer pointing at an
    empty string, which is worse than no disclaimer because it looks discharged.

    On a `human_only` source the firm's words ARE the desk's entire knowledge of
    the authority, so they are both the right thing to show and the only thing
    there is.
    """
    out = ask.answer("what do I do with a $10 service charge nobody entered?",
                     "cash-and-bank", position="an entry in the books",
                     citation='IRS Pub. 583 (12/2024), "Reconciling the '
                              'checking account" — what the books are updated for',
                     model="m", keep=False)
    assert isinstance(out, engine.Served)
    assert out.passage, "served 'read this' with nothing to read"


def test_nothing_anywhere_serves_an_empty_thing_to_read():
    """The property, over every recorded answer on every desk — because the
    empty one was found by eye on three examples, and eye-checks do not scale."""
    empty = []
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for prob in desk.problems:
            out = engine.serve(
                engine.Answer(position=prob.answer, citation=prob.citation),
                desk, question=prob.facts)
            if isinstance(out, engine.Served) and not out.passage.strip():
                empty.append(f"{prob.id} on {d.name}")
    assert not empty, (
        "these serve a 'read it yourself' pointing at nothing: " + ", ".join(empty))


def test_a_ratified_answer_does_not_claim_nobody_checked_it():
    """ALSO FOUND BY RUNNING IT. The firm DID check a position-backed answer —
    they ratified that conclusion for that citation, and `_check` refuses any
    restatement, so the words served are theirs. Saying "nobody checked" there
    is a lie in the safe direction, and a disclaimer that cries wolf on the
    safest answers teaches a reader to skip it on the dangerous ones."""
    out = ask.answer("what do I do with a $10 service charge nobody entered?",
                     "cash-and-bank", position="an entry in the books",
                     citation='IRS Pub. 583 (12/2024), "Reconciling the '
                              'checking account" — what the books are updated for',
                     model="m", keep=False)
    assert "NOBODY CHECKED THAT THIS PARAGRAPH SAYS THIS" not in out.unchecked
    assert "THE FIRM RATIFIED THIS CONCLUSION" in out.unchecked
    assert "fits these particular facts" in out.unchecked, (
        "claims the answer is checked without naming what still is not")


def test_an_unratified_answer_still_gets_the_hard_sentence(trap):
    """And the split must not become a way for the dangerous case to get the
    gentle wording."""
    assert "NOBODY CHECKED THAT THIS PARAGRAPH SAYS THIS" in trap.unchecked
    assert "THE FIRM RATIFIED" not in trap.unchecked
