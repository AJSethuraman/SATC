"""A form billed per form, not per return.

**THE OVERSIGHT, AND IT WAS NOT A MISSING TEST.** `per_form` fired a ticked
form exactly once and billed it once, from the day it was written until
5 October 2026. The suite had **seventeen** tests exercising counts on
`per_unit` and **none** on `per_form` — not because anyone skipped them, but
because there was nothing to count. The tests proved the code did what the
design said. Nobody asked whether the design matched a return.

It surfaced on a live joint return needing two Form 5329s, one per spouse. The
firm: *"we need to be able to bill by form obviously."* And: *"such an odd
oversight... it's hard to believe this wasn't part of your tests."* It was not.

**WHY THE COUNT CAME TO `per_form` RATHER THAN THE FORM MOVING OUT.** The
schedule's own note on the earned income credit says it stayed in `per_form`
rather than becoming a counted line because what `per_form` gives a line is the
printed `assumes` and `trigger` — *"a counted line has nowhere to say that"*.
Moving Form 5329 to `per_unit` to get a number would have dropped the sentence
that tells a client what the fee assumes about their 1099-R.

**A BLANK COUNT IS ONE, NOT NONE.** The same trap `per_unit` already guards: the
form was ticked, so it is on the return. A preparer who leaves the number alone
must not have the line disappear — that is an unbilled form, and it is the
failure mode that costs money quietly.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pricing  # noqa: E402

BASE = {
    "federal_form": "1040", "return_basis": "original", "tax_year": 2025,
    "joint_return": "yes",
    "return_features": ["itemizing"], "federal_schedules": ["A"],
    "states": ["OH"], "localities": ["Cleveland Heights"],
    "count_states": 1, "count_localities": 1,
    "count_rentals": 0, "count_farms": 0, "count_k1s": 0, "count_businesses": 0,
    "count_foreign_accounts": 0, "count_brokerages": 0,
    "count_sorting": 0, "sorting_amount": 0, "count_extension_estimates": 0,
    "extra_forms": ["early_withdrawal"],
    "additional_forms": [], "other_income_documents": "no",
    "has_dependents": "no", "eic_claimed": "no",
    "amt_applies": "no", "amt_credit_applies": "no",
    "prior_firm": "no", "returning_client": "no", "decision": "yes",
}


def _line(answers, service_contains="Early retirement"):
    for item in pricing.line_items(answers, pricing.load()):
        if service_contains in item.get("Service", ""):
            return item
    return None


def _answers(**over):
    a = copy.deepcopy(BASE)
    a.update(over)
    return a


# ── the thing that was missing ───────────────────────────────────────────────

@pytest.mark.parametrize("count,expected", [(1, "$30.00"), (2, "$60.00"), (3, "$90.00")])
def test_a_form_is_billed_once_per_form(count, expected):
    """THE WHOLE POINT. Two of them cost twice as much."""
    line = _line(_answers(count_early_withdrawal=count))
    assert line is not None, "the form was ticked and produced no line"
    assert line["Amount"] == expected


def test_a_count_above_one_shows_its_working():
    """Mirrors the K-1 rule: "2 x $30.00", never an unexplained $60. A client
    reading $60 against a $30 price on the fee page asks why."""
    line = _line(_answers(count_early_withdrawal=2))
    assert "2 × $30.00" in line["Detail"], line["Detail"]


def test_one_of_them_does_not_show_arithmetic():
    """A line reading "1 x $30.00" is a machine talking."""
    line = _line(_answers(count_early_withdrawal=1))
    assert "×" not in line["Detail"]


# ── the blank-count trap ─────────────────────────────────────────────────────

@pytest.mark.parametrize("blank", [None, "", 0])
def test_a_ticked_form_with_no_count_is_one_not_none(blank):
    """THE FAILURE THAT COSTS MONEY QUIETLY. The form is on the return — it was
    ticked. A blank number must not delete the line."""
    line = _line(_answers(count_early_withdrawal=blank))
    assert line is not None, f"a count of {blank!r} made the form vanish"
    assert line["Amount"] == "$30.00"


def test_a_form_not_ticked_produces_nothing_whatever_the_count_says():
    """The other direction. A stale count left on the answers must not bill a
    form nobody selected."""
    answers = _answers(count_early_withdrawal=3)
    answers["extra_forms"] = []
    assert _line(answers) is None


# ── the rest of the block is untouched ───────────────────────────────────────

def test_an_uncounted_form_still_bills_once():
    """Only the forms that say `counted_by` are counted. Everything else keeps
    the behaviour it has always had — this change must not silently multiply a
    form that cannot happen twice."""
    answers = _answers()
    answers["extra_forms"] = ["home_sale"]
    answers["count_early_withdrawal"] = 5          # stale, and irrelevant
    line = _line(answers, "Sale of a home")
    assert line is not None and line["Amount"] == "$50.00"
    assert "×" not in line["Detail"]


def test_the_counted_form_carries_its_assumption_still():
    """WHY THE COUNT CAME HERE instead of the form moving to `per_unit`. If the
    printed assumption is gone, the move would have been the better design and
    this whole approach is wrong."""
    answers = _answers(count_early_withdrawal=2)
    said = " ".join(str(a) for a in pricing.assumptions(answers, pricing.load()))
    assert "1099-R" in said, "the form's assumption no longer reaches the client"


def test_the_live_plan_now_reconciles():
    """The engagement that found this: standard package, a second city, two
    Form 5329s, a 6251 and an 8801. It priced $495 against a quoted $525, and
    the $30 gap was the second 5329."""
    answers = _answers(
        count_localities=2, localities=["Cleveland Heights", "Columbus"],
        count_businesses=1, schedule_c_kind="simple",
        return_features=["self_employment", "itemizing"],
        federal_schedules=["A", "C", "SE"],
        count_early_withdrawal=2, amt_applies="yes", amt_credit_applies="yes",
    )
    items = pricing.line_items(answers, pricing.load())
    assert pricing.estimate_total(items, pricing.load()) == "$525.00"


# ── what the Codex review caught, and it caught both ─────────────────────────

def test_the_count_is_an_answer_the_requote_offers():
    """FOUND BY CODEX ON THE PULL REQUEST. `requote` reads
    `pricing.answers_that_move_money` to decide what a preparer may change. A
    count it does not name is a price only somebody who already knew the answer
    id could move -- and `counted_by` was a new way to move money that the
    function did not walk.

    The function's own docstring warns about exactly this: read it out of the
    schedule, because a hand-kept list "would be the one that went stale".
    """
    moving = pricing.answers_that_move_money(pricing.load())
    assert "count_early_withdrawal" in moving


@pytest.mark.parametrize("qid", ["amt_applies", "amt_credit_applies", "eic_claimed"])
def test_individual_only_pricing_questions_are_gated_to_the_1040(qid):
    """ALSO CODEX. An 1120, 1120-S or 1065 interview was being asked whether
    the alternative minimum tax applies, and whether the earned income credit
    is claimed. Neither prices anything on an entity return -- `per_form` is
    reached through `extra_forms`, which is gated -- so the answer would have
    looked like a control and done nothing.

    `eic_claimed` had the gap before any of this and is fixed with them.
    """
    import interview as iv
    q = next(q for _, q in iv.all_questions(iv.load_schema()) if q["id"] == qid)
    assert q.get("showIf") == "federal_form == '1040'", (
        f"{qid} is asked on entity returns, where it prices nothing")
