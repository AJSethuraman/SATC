"""A figure the schedule will not bill says so before the estimate goes out.

D25, FROM THE WALK OF 5 SEPTEMBER 2026.

The interview asks *"How much for the sorting? **($175 minimum)**"*. I answered
**100**. It was accepted with no message. The Review page showed the stored
answer as **100**. The estimate then read **Records sorting — $175.00**.

**THE RAISE IS RIGHT AND IS THE FIRM'S OWN INSTRUCTION**, 26 August 2026:
*"we'll set our price to 175 - and we will say 175 is the minimum so if the
preparer thinks it'll take more than that much worth of hours they should adjust
the estimate"*. `pricing._preparer_amount` says why it raises rather than
refuses: *"the alternative is an estimate that will not render over a typo
somebody can fix in five seconds -- and the minimum is the firm's decision,
which means it is the answer whenever the entered number disagrees."*

**The silence is the defect.** Somebody who deliberately agreed $100 of sorting
with a client sends an estimate saying $175 and has no idea why, and the last
page they checked before sending still says 100.

DERIVED FROM THE SCHEDULE, NOT WRITTEN FOR THE SORTING LINE. Any `amount_from`
question with a `minimum` behind it is reported the same way. A check that names
one field is a check that will miss the second one somebody adds -- which is the
shape D9, E2 and E4 all turned out to have in the same week.
"""
from __future__ import annotations

import re

import pytest

import pricing
import web


# ── the reporter ──────────────────────────────────────────────────────────────

def test_there_is_a_floored_question_to_report():
    """The denominator. If no line in the schedule has both `amount_from` and a
    `minimum`, this whole file is about a branch that cannot be reached."""
    schedule = pricing.load()
    floored = [k for k, u in (schedule.get("per_unit") or {}).items()
               if u.get("amount_from") and isinstance(u.get("minimum"), (int, float))]
    assert floored, "no preparer-priced line carries a floor"


def test_a_figure_below_the_floor_is_reported():
    """THE DEFECT."""
    got = pricing.overridden_answers({"sorting_amount": 100})
    assert len(got) == 1
    assert got[0]["entered"] == 100
    assert got[0]["billed"] == 175
    assert got[0]["question"] == "sorting_amount"
    assert got[0]["line"] == "Records sorting"


def test_a_figure_at_or_above_the_floor_is_not():
    """The control. Reporting an override that did not happen is its own lie."""
    assert pricing.overridden_answers({"sorting_amount": 175}) == []
    assert pricing.overridden_answers({"sorting_amount": 300}) == []


def test_an_unanswered_question_is_not_an_override():
    """Blank means "charge the minimum", which the help text already says. That
    is the default working, not a figure being moved."""
    assert pricing.overridden_answers({}) == []
    assert pricing.overridden_answers({"sorting_amount": None}) == []
    assert pricing.overridden_answers({"sorting_amount": ""}) == []


def test_a_non_number_is_left_to_the_pricing_engine():
    """`_preparer_amount` raises a PricingError naming the line, which is a
    better message than anything this reporter could produce -- so it must not
    swallow the case on the way past."""
    assert pricing.overridden_answers({"sorting_amount": "lots"}) == []
    assert pricing.overridden_answers({"sorting_amount": True}) == []


def test_the_report_agrees_with_what_is_actually_billed():
    """THE PROPERTY THAT MATTERS. A note saying "billed at 175" beside a line
    the engine prices at something else is worse than no note."""
    schedule = pricing.load()
    unit = schedule["per_unit"]["records_sorting"]
    reported = pricing.overridden_answers({"sorting_amount": 100})[0]
    assert pricing._preparer_amount(unit, {"sorting_amount": 100}) == reported["billed"]


# ── it reaches the page ───────────────────────────────────────────────────────

def _review(answers):
    """The real review body, with a session carrying these answers."""
    import interview as iv

    session = iv.Interview()
    session.answers.update(answers)
    return web.review_body("2026-0001", session, [])


def test_the_review_page_says_the_figure_will_move():
    """The last page anybody looks at before the estimate goes out."""
    body = _review({"sorting_amount": 100})
    assert "billed at" in body
    assert "175.00" in body
    assert "Records sorting" in body


def test_the_review_page_says_what_the_estimate_will_read():
    """Naming the document it affects, because that is the thing being sent."""
    body = _review({"sorting_amount": 100})
    assert "The estimate will say" in body
    assert "100.00" in body, "the number that was typed is gone from the sentence"


def test_the_typed_answer_is_still_shown_as_typed():
    """The control. The row must still report what the preparer actually
    answered -- replacing it with 175 would hide the disagreement rather than
    show it, which is the same silence facing the other way."""
    body = _review({"sorting_amount": 100})
    row = next(r for r in body.split("<tr>") if "sorting" in r.lower()
               or "How much for the sorting" in r)
    assert ">100<" in row or ">100 " in row or "100</td>" in row.replace("\n", "")


def test_a_figure_above_the_floor_gets_no_note():
    body = _review({"sorting_amount": 300})
    assert "billed at" not in body
