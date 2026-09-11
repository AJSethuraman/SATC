"""A fact somebody went and got, dropped without a word.

FOUND BY THE DESK ITSELF on the first live close, 8 September 2026, and it is
the best thing that came out of that night. Forge-Occam's rewards question
refused on a missing fact; it went and read the statements, obtained the fact,
and passed it back. The desk ran the answer three ways and reported that the
fact made **no difference to the output — accepted, ignored, and nothing said
so** — because `rewards-and-information-returns` declares `records =
('taxpayer',)` and has no field for *what the card issuer paid this reward for*.

It was careful that this is NOT `no_field_for_this_fact` failing: that reason
covers a POSITION asking for a fact with nowhere to live. This is a CALLER
supplying one nobody asked for. Its proposal, taken here verbatim:

    "when a Context carries a key no routed desk declares, say so in one line.
     Not a refusal. A fact somebody went and obtained is evidence the record's
     shape is missing something, and that evidence is currently discarded
     silently. **The fact that stopped a desk and cost a round trip is by that
     alone worth a field.**"

NOT A REFUSAL, DELIBERATELY. The answer is unaffected and withholding it would
punish the caller for doing the right thing. What is wrong is the silence: the
round trip that obtained the fact is the strongest evidence anyone will ever
have that the record wants a field, and it evaporated.

THIS IS THE SAME SHAPE AS `consult_or_file`, one layer over. There, a question
no desk held left no record. Here, a fact no desk declares leaves no record.
Both are silences that cost nothing to break and are invisible when kept.
"""
from __future__ import annotations

from pathlib import Path

import engine
import record
from engine import Answer

CORPUS = Path(__file__).resolve().parents[1] / "corpus"

QUESTION = "a business credit card paid a cash-back reward into the account — is that income?"
CITATION = "PLR 201027015, LAW AND ANALYSIS"
POSITION = ("an adjustment to the price paid, booked against the cost it arose "
            "from, and not income")

#: The fact Forge-Occam went and got. The desk declares `taxpayer`, not this.
OBTAINED = "recurring earning on spend, not a one-off sign-up award"


def _serve(facts):
    desk = record.load(CORPUS)
    return engine.serve(Answer(position=POSITION, citation=CITATION), desk,
                        question=QUESTION,
                        context=record.Context(facts=facts))


def test_a_fact_the_desk_does_not_declare_is_named_in_the_output():
    out = _serve({"taxpayer": "an LLC", "reward_basis": OBTAINED})
    text = str(out)
    assert "reward_basis" in text, (
        "the caller obtained this and passed it in; it changed nothing and "
        "nothing said so. That silence is the finding being discarded")


def test_it_is_not_a_refusal():
    """Punishing a caller for supplying a fact is the wrong direction."""
    out = _serve({"taxpayer": "an LLC", "reward_basis": OBTAINED})
    assert not isinstance(out, engine.Refusal), (
        "the answer is unaffected by the extra fact — refusing would punish "
        "the round trip that obtained it")


def test_a_declared_fact_is_not_named():
    """If every fact were listed the line would be noise within a day."""
    out = _serve({"taxpayer": "an LLC"})
    assert "does not declare" not in str(out)


def test_no_context_says_nothing():
    out = _serve({})
    assert "does not declare" not in str(out)
