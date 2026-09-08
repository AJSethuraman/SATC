"""Silence is an answer — and an answer nobody writes down is not one.

`consult` returns an empty list when no desk answers on that subject, and
`be-the-desk` correctly calls that a real result rather than a routing failure.
But nothing recorded it. `unsupported.from_question` — the front door for a
question the record cannot start on — was reachable only from
`tools/file_close_questions.py`, a batch tool somebody runs by hand.

So the live path had exactly one outcome that vanished. A desk that refuses
leaves a refusal `holes.py` reads out; a desk that is ASKED SOMETHING NOBODY
BUILT A DESK FOR left nothing at all, and that is the case the firm most needs
to see:

    "You do not prep it with information and if it can't get the information
     that means there's an actual hole."   -- the firm, 8 September 2026

MEASURED, the same day, on twenty month-end questions written in a bookkeeper's
words rather than any desk's vocabulary: fifteen reached a desk and **five
reached nothing**. Two of those five were subjects a desk already holds — a
deposit the books do not show is `cash-and-bank`'s own reconciliation subject,
and an owner taking money out is what `personal-or-business` has a ratified
position about. Under the old path all five were silent and none was filed.

This is enforced in code rather than asked for in the skill, for the reason
`docs/LOCAL-LLM-PATTERN.md` rule 6 gives and the desk's own README repeats: the
same policy written as skill prose was obeyed "100%, 4%, 0% of runs".
"""
from __future__ import annotations

import ask
import unsupported
from conftest import DESKS

#: A subject no desk in this repository is built for. Kept deliberately mundane:
#: the point is that an ordinary close question can reach nothing.
UNHELD = "We prepaid twelve months of insurance in March. Do I need to spread it?"

#: One a desk does hold, so the test proves the filing is CONDITIONAL and not
#: something that fires on every question.
HELD = "He bought lunch for the crew on site. Is that fully deductible?"


def test_a_question_no_desk_holds_is_filed(tmp_path):
    queue = tmp_path / "unfiled" / "CLOSE.md"

    briefs, filed = ask.consult_or_file(UNHELD, queue=queue, desks=DESKS)

    assert briefs == [], "no desk holds this; consult must still say nothing"
    assert filed is not None, (
        "the question reached no desk and was not recorded — this is the one "
        "outcome that used to vanish")
    assert filed.question == UNHELD
    assert filed.failed_because == "authority_absent"
    assert queue.exists(), "nothing was written where holes.py would read it"
    assert UNHELD in queue.read_text(encoding="utf-8")


def test_a_question_a_desk_holds_is_not_filed(tmp_path):
    """Filing on every question would turn the queue into a log of traffic."""
    queue = tmp_path / "unfiled" / "CLOSE.md"

    briefs, filed = ask.consult_or_file(HELD, queue=queue, desks=DESKS)

    assert briefs, "a desk holds this subject"
    assert filed is None, "a routed question is not an unsupported one"
    assert not queue.exists(), "nothing should have been written"


def test_the_same_unheld_question_twice_is_one_entry(tmp_path):
    """A close asks the same thing on twenty lines. The queue is findings.

    `append` is idempotent on the entry, and this pins that the live path
    actually gets that guarantee rather than numbering a fresh id each time and
    walking past it — which is exactly how the queue lost every refusal after
    the first once before.
    """
    queue = tmp_path / "unfiled" / "CLOSE.md"

    ask.consult_or_file(UNHELD, queue=queue, desks=DESKS)
    ask.consult_or_file(UNHELD, queue=queue, desks=DESKS)

    assert len(unsupported.parse(queue.read_text(encoding="utf-8"))) == 1


def test_two_different_unheld_questions_are_two_entries(tmp_path):
    """The mirror of the guard above: idempotency must not swallow a new one.

    THE SECOND QUESTION IS CHOSEN, NOT ANY OLD ONE. The first draft used "the
    payroll service withdrew a fee that doesn't match THE INVOICE" and it
    ROUTED -- `invoice` is a declared subject on `capitalization-and-de-minimis`
    -- so the test failed against correct code. The bookkeeper's own phrasing,
    "doesn't match what they INVOICED", reaches nothing: the same inflection
    under-firing every `SUBJECTS.md` warns about, one letter wide, found by a
    test written carelessly. Owner contributions are held by no desk at all.
    """
    queue = tmp_path / "unfiled" / "CLOSE.md"
    other = ("The owner transferred $5,000 of his own money into the business "
             "account. Is that income?")

    ask.consult_or_file(UNHELD, queue=queue, desks=DESKS)
    ask.consult_or_file(other, queue=queue, desks=DESKS)

    entries = unsupported.parse(queue.read_text(encoding="utf-8"))
    assert len(entries) == 2
    assert {e.question for e in entries} == {UNHELD, other}
