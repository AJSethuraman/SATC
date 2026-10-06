"""The envelope tells the desk how to satisfy what the engine requires of it.

`relay.as_prompt` states its own purpose: *"THE PROTOCOL TRAVELS IN THE
ENVELOPE, not only in a SKILL.md. Four releases running, the Skill tool served a
stale `ask-desk` and an agent following it correctly produced the wrong output.
A desk reading this message has what it needs to answer even if its own skill is
months old."*

IT DID NOT. Until 25 September 2026 the envelope never said the words *judge*,
*judged* or *judgment* — measured, zero occurrences — while `corpus/SUBJECTS.md`
declares `Judged: required` and `engine` refuses `not_judged` without one. A desk
session following the envelope LITERALLY produced a refusal on every answer it
was otherwise right about.

AND THAT REFUSAL IS THE ONE THAT LEAVES NO TRACE. `ask.answer` excludes
`not_judged` from the queue on purpose — it says the caller was wired wrong, not
that the record is missing something — so the round trip was spent and nothing
anywhere recorded that it had been. Forge-Occam put five questions to the desk
in the Sarcia pilot; four came back refused.

WHAT THIS TEST DERIVES RATHER THAN ASSERTS. The requirement is read from the
CORPUS, not typed here: if the record declares a judge required, the envelope has
to say how to supply one. Change the record to make it optional and this relaxes
by itself, which is the difference between a check and a second copy of a rule.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import record
import relay

HERE = Path(__file__).resolve().parent.parent
CORPUS = HERE / "corpus"
REPLY_TO = "session_" + "a" * 20


@pytest.fixture
def envelope() -> str:
    return relay.as_prompt(relay.ask("what proves a deposit is revenue?",
                                     reply_to=REPLY_TO))


def test_the_record_really_does_require_a_judge():
    """The premise, stated out loud. If this ever goes false the test below
    stops meaning anything, and it should say so here rather than pass quietly."""
    assert record.load(CORPUS).judged == record.REQUIRED, (
        "the corpus no longer requires a second reader, so the check below is "
        "measuring nothing — read it again before deleting it")


def test_the_envelope_says_a_second_reader_is_needed(envelope):
    assert record.load(CORPUS).judged == record.REQUIRED
    assert re.search(r"judge|judged|judgment", envelope, re.I), (
        "the corpus requires a second reader and the envelope never mentions "
        "one. A desk following this message is refused `not_judged` on every "
        "answer it gets right.")


def test_the_envelope_says_how_to_supply_one(envelope):
    """Naming the requirement without the mechanism is a riddle, not a protocol."""
    for needed in ("judging.Judgment", "judged=", "because", "supports"):
        assert needed in envelope, f"the envelope never names {needed!r}"


def test_the_envelope_says_the_reader_may_not_be_the_answerer(envelope):
    """C6, and `Judgment.by` enforces it — so an envelope that omits it sends
    the answerer to build something the engine will reject."""
    assert re.search(r"other than.*answered|not be the party that answered",
                     envelope, re.I), (
        "the envelope does not say the second reader must be someone else, "
        "which is the one thing `Judgment.by` refuses")


def test_the_envelope_warns_that_this_refusal_is_not_filed(envelope):
    """The reason it cost a whole pilot leg and left nothing behind."""
    assert "not_judged" in envelope
    assert re.search(r"not\s+filed|leaves no trace|NOT filed", envelope), (
        "the envelope does not say that a `not_judged` refusal is excluded "
        "from the queue, so an answerer has no way to know the round trip "
        "vanished rather than being recorded as a finding")


def test_this_is_measured_against_the_real_gate_and_not_a_word_list():
    """An unjudged answer really is refused — so the prose above is about
    something that happens, not about something that used to.

    Without this the four checks above are a spell-check of a paragraph.
    """
    import ask
    import engine
    import conftest

    desk = record.load(CORPUS)
    ratified = [q for q in desk.positions if not q.proposed]
    assert ratified, "no ratified position to answer from"

    reasons = set()
    for q in ratified:
        out = ask.answer("what is our threshold?", position=q.position,
                         citation=q.citation, model="the desk session",
                         keep=False)
        if isinstance(out, engine.Refusal):
            reasons.add(out.reason)
    assert "not_judged" in reasons, (
        "no ratified position refuses `not_judged` when answered without a "
        "judgment, so the gate the envelope now explains is not the gate that "
        "fires. Re-read this test before trusting it: "
        f"what fired instead was {sorted(reasons)}")
