"""A fact the firm decided to record is checked where it is RECORDED.

`dec-unitcost`, 14 September 2026 — the firm, on the eighth docket: **"Add it,
with a format check."**

THE FIELD WAS ONE WORD. `corpus/SUBJECTS.md` gained `unit_cost` on its
`Records:` line and nothing else changed; that half was measured in a scratch
copy before it was put to the firm. **The check is the content of the answer**,
and the card they answered says why:

    Fact values are free text. So the field would accept `$185`, `185.00` and
    "one eighty five" alike — and a threshold question answered off a mistyped
    value is a wrong answer with a real number under it.

WHAT IT COST TO NOT HAVE THE FIELD, from the live round trip `a276e4aed20a`:
the asker supplied the per-unit cost, the brief said *"NOT ON FILE and cannot be
put on file"*, and the desk escalated `no_field_for_this_fact` exactly as
instructed. Two of four purchases were each under $200 in total, so no unit
inside either can exceed $200 and § 1.162-3(c)(1)(iv) settles them on the
definition alone. That answer existed and was thrown away at the door.

WHY THE RECORD IS A WORSE PLACE FOR THIS FIGURE THAN IT LOOKS, and why the check
is forgiving about spelling. `$2,500` is how the firm's own POS2 writes the de
minimis ceiling. A check that refused the record's own spelling would be a check
nobody could satisfy from the documents in front of them — so `$` and thousands
separators are accepted, the string is stored EXACTLY as typed, and `money()` is
the only way anything gets a number out of it. Nothing normalises the stored
value: *facts are recorded, not inferred*, and a value silently rewritten cannot
be checked against the file it came from.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402


# ── the field exists, and it is declared in the record rather than in code ───

def test_the_corpus_declares_a_place_for_what_something_cost():
    desk = record.load(CORPUS)
    assert "unit_cost" in desk.records, (
        "the firm answered 'Add it' on the eighth docket; the Records line in "
        "corpus/SUBJECTS.md is where that answer lives")


def test_a_cost_on_file_is_no_longer_a_fact_with_nowhere_to_go():
    """The defect the field was added for, stated as its own test.

    `unrecorded` is what `brief` prints under *"Told to us, and this desk has
    NOWHERE to record it"*, and it is what made the desk throw the answer away."""
    desk = record.load(CORPUS)
    ctx = record.Context(facts={"unit_cost": "185.00"})
    assert ctx.unrecorded(desk.records) == (), (
        "a per-unit cost still has nowhere to live")


# ── the shape ───────────────────────────────────────────────────────────────

#: HOW AN ACCOUNTANT WRITES ONE. `$2,500` is POS2's own spelling of the ceiling.
WRITTEN = ["185", "185.00", "2500", "$2,500", "1,250.50", "$185", "0.99", "0"]

#: NOT AMOUNTS. Every one of these would sit on file looking recorded, and a
#: threshold question answered off one would be wrong with a real number under
#: it — which is worse than a refusal, because it reads as arithmetic.
NOT_AMOUNTS = ["one eighty five", "about 200", "185 each", "100-200", "$",
               "12.345", "2,50", "185 dollars", "n/a", "-185"]


@pytest.mark.parametrize("value", WRITTEN)
def test_an_amount_a_person_would_type_is_recorded(value):
    ctx = record.Context(facts={"unit_cost": value})
    assert ctx.facts["unit_cost"] == value, (
        "the stored value was rewritten; it must survive exactly as typed so it "
        "can be checked against the file it came from")
    assert ctx.money("unit_cost") is not None


@pytest.mark.parametrize("value", NOT_AMOUNTS)
def test_a_value_nobody_could_answer_a_threshold_from_is_refused(value):
    with pytest.raises(record.RecordError) as raised:
        record.Context(facts={"unit_cost": value})
    said = str(raised.value)
    assert "unit_cost" in said and repr(value) in said, (
        "the refusal must print the fact and what was actually typed, or the "
        "person who wrote it cannot tell which value is the problem")


def test_the_refusal_says_where_the_check_ran_and_why():
    """A refusal naming a gap and not the remedy is a dead end wearing a reason."""
    with pytest.raises(record.RecordError) as raised:
        record.Context(facts={"unit_cost": "about two hundred"})
    said = str(raised.value)
    assert "185" in said, "the refusal does not show how to write one"
    assert "RECORDED" in said, (
        "the refusal does not say it fired at recording rather than at "
        "answering, which is the whole of the firm's answer")


# ── what it does NOT do ─────────────────────────────────────────────────────

def test_a_fact_the_file_does_not_carry_is_not_a_badly_shaped_one():
    """`missing()` and `standing_rule()` both read blank as "nobody said". An
    exception here would refuse the ordinary case of a file that has not been
    asked this yet — which is most files."""
    for blank in ("", "   "):
        ctx = record.Context(facts={"unit_cost": blank})
        assert ctx.missing(("unit_cost",)) == ("unit_cost",)
        assert ctx.money("unit_cost") is None


def test_every_other_fact_is_free_text_and_is_not_checked():
    """`trade` is "general contractor"; `capitalization_rule` is a sentence.
    A shape table that crept outward would refuse the facts the desk already
    holds."""
    ctx = record.Context(facts={"trade": "general contractor",
                                "taxpayer": "a sole proprietor",
                                "capitalization_rule": "the IRS de minimis "
                                                       "ceiling, $2,500"})
    assert ctx.known() == ("capitalization_rule", "taxpayer", "trade")
    assert set(record.SHAPES) == {"unit_cost"}, (
        "a name added to SHAPES is a deliberate act and needs a test of its "
        "own; this one exists so adding a second silently turns this red")


def test_the_number_is_read_through_money_and_never_off_the_string():
    """Comparing the strings would make `$2,500` and `2500` two different facts,
    which is the defect the shape check exists to keep out."""
    a = record.Context(facts={"unit_cost": "$2,500"})
    b = record.Context(facts={"unit_cost": "2500.00"})
    assert a.facts["unit_cost"] != b.facts["unit_cost"]
    assert a.money("unit_cost") == b.money("unit_cost")


def test_money_returns_nothing_for_a_fact_that_has_no_shape():
    """`money()` on free text must not guess. `trade` has no number in it and
    asking for one is a caller error, answered with None rather than a parse."""
    ctx = record.Context(facts={"trade": "general contractor"})
    assert ctx.money("trade") is None
    assert ctx.money("nothing_like_this") is None


# ── the check cannot be routed around ───────────────────────────────────────

def test_a_cost_written_into_a_problem_on_file_line_goes_through_the_check():
    """`Context` is frozen, so every path that builds one goes through the
    constructor. This is the path a recorded problem takes, and it is the one a
    future caller is most likely to add without noticing the check exists."""
    good = record._on_file("unit_cost: 185.00; trade: roofer", "problem X")
    assert good.money("unit_cost") is not None
    with pytest.raises(record.RecordError):
        record._on_file("unit_cost: one eighty five", "problem X")


def test_the_shipped_record_still_loads():
    """The field was added to a corpus that already holds 98 problems, and an
    `On file` line anywhere in it now goes through a check that did not exist
    when it was written."""
    desk = record.load(CORPUS)
    assert len(desk.problems) == 98
