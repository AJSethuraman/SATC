"""Three forms the firm prices against the market, and the default that is not a floor.

**WHERE THESE CAME FROM.** A live client's plan, 5 October 2026, carried three
lines marked *(market)* — Form 5329 twice, Form 6251, Form 8801. Two of the
three were not in `fee-schedule.yaml` at all, so they had been priced at the
keyboard. That is exactly what the firm's own standing rule exists to stop:

    "if we have no price it should be assumed to be $175 ... but the goal would
     be to establish a price"

**AND A CORRECTION TO HOW I READ THAT RULE.** I reported the plan as
underpricing Form 5329, because `per_form.amount` is $50 and the plan charged
$30. The firm, 5 October 2026:

    "the standing rule was not meant to be $50 a form literally, this would
     conflict with market pricing and such. use the prices i gave you and add
     them to pricing engine"

So **$50 is a starting point, not a minimum.** A form priced below it is not an
error, and nothing here should treat it as one. The test that would have been
wrong is the one not written: a guard asserting every form is at least the
default would have fired on a correct invoice.

**THE $30 IS DERIVED, NOT GUESSED.** The plan quoted "Form 5329 x2 (market)"
at $60 and totalled $525. $325 + $35 + $60 + $60 + $45 is $525, so the 5329
line is $60 for the pair — $30 each. Two of them because each spouse files
their own 5329 on a joint return.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pricing  # noqa: E402

#: form key -> (the IRS form it is, what the firm charges)
MARKET_PRICED = {
    "early_withdrawal": ("Form 5329", 30),
    "amt": ("Form 6251", 60),
    "amt_credit": ("Form 8801", 45),
}


@pytest.fixture(scope="module")
def forms():
    schedule = pricing.load()
    return schedule["per_form"], schedule["per_form"]["forms"]


@pytest.mark.parametrize("key,expected", sorted(MARKET_PRICED.items()))
def test_each_market_priced_form_carries_its_own_amount(forms, key, expected):
    """Not inherited from the default. These were priced deliberately."""
    _, by_key = forms
    irs_form, amount = expected
    assert key in by_key, f"{irs_form} is not in the fee schedule"
    assert by_key[key].get("amount") == amount, (
        f"{irs_form} should be ${amount}; the schedule says "
        f"{by_key[key].get('amount')}")


@pytest.mark.parametrize("key,expected", sorted(MARKET_PRICED.items()))
def test_each_one_names_the_irs_form_it_is(forms, key, expected):
    """`amt` and `amt_credit` mean nothing to somebody reading the schedule in
    a year. The form number is the thing they will search for."""
    _, by_key = forms
    irs_form, _ = expected
    assert irs_form in by_key[key].get("detail", ""), (
        f"{key} does not say it is {irs_form}")


def test_a_form_may_be_priced_below_the_default(forms):
    """THE CORRECTION, as an assertion. $50 is where a form lands when nobody
    has priced it against the market — a starting point, not a floor. Form 5329
    at $30 is correct, and any future guard that treats the default as a
    minimum would fire on a real invoice."""
    per_form, by_key = forms
    assert by_key["early_withdrawal"]["amount"] < per_form["amount"], (
        "the case this test exists for has gone away — re-read it before deleting")


def test_the_live_plan_reconciles(forms):
    """The plan that produced these prices, added up against the schedule.

    No client detail here, only the figures: a standard package, a second city,
    two Form 5329s, a 6251 and an 8801.
    """
    schedule = pricing.load()
    _, by_key = forms
    total = (
        schedule["base"]["1040"]["tiers"]["standard"]["amount"]   # 325
        + schedule["per_unit"]["local_return"]["amount"]          # 35, second city
        + by_key["early_withdrawal"]["amount"] * 2                # 60
        + by_key["amt"]["amount"]                                 # 60
        + by_key["amt_credit"]["amount"]                          # 45
    )
    assert total == 525, f"the plan totals {total}, and it was quoted at 525"


def test_the_three_did_not_disturb_the_rest(forms):
    """The denominator. Adding two forms and repricing one must not have moved
    anything else — every other form still takes the default, except the one
    that always carried its own."""
    per_form, by_key = forms
    for key, value in by_key.items():
        if key in MARKET_PRICED or key == "earned_income_credit":
            continue
        assert "amount" not in value, (
            f"{key} picked up a price it did not have before")


# ── what the second Codex review caught ──────────────────────────────────────

def test_every_form_price_can_be_changed_from_the_price_screen(forms):
    """FOUND BY CODEX. `/prices` walked to the parent `per_form` amount and no
    further, so a form carrying its own price could not be edited in the
    browser at all \u2014 and changing "One price for any named form" no longer
    moved it either. A later price rise would have left those client charges
    quietly stale while the screen looked like it had covered everything.

    THE GAP WAS OLDER THAN THE FORMS THAT EXPOSED IT. `earned_income_credit`
    has carried its own $65 since 26 August 2026 and was unreachable the whole
    time; it only surfaced when three more joined it.
    """
    import registry_editor

    _, by_key = forms
    reachable = {row[0] for row in registry_editor._walk(pricing.load())}
    priced = {k for k, v in by_key.items() if isinstance(v, dict) and "amount" in v}
    missing = sorted(k for k in priced
                     if f"per_form.forms.{k}" not in reachable)
    assert not missing, (
        f"{len(missing)} form price(s) cannot be edited from /prices: {missing}")


def test_the_interview_does_not_promise_one_price_for_all_of_them(forms):
    """ALSO CODEX. The `extra_forms` help said each selection adds $50, which
    stopped being true the moment one of them was priced at $30 \u2014 so a client
    was shown guidance the estimate then contradicted.

    Asserted as "does not state a single figure as though it covered them all"
    rather than pinning the replacement wording, because the words are the
    firm's and a test that pins copy becomes the reason copy cannot change.
    """
    import interview as iv

    q = next(q for _, q in iv.all_questions(iv.load_schema())
             if q["id"] == "extra_forms")
    help_text = " ".join(str(q.get("help", "")).split())
    per_form, by_key = forms
    priced_differently = {v["amount"] for k, v in by_key.items()
                          if isinstance(v, dict) and "amount" in v}
    assert priced_differently, "no form carries its own price \u2014 re-read this test"
    assert f"${per_form['amount']} to the fee" not in help_text, (
        "the help still promises one price for every selection, and at least "
        f"one of them is priced at {sorted(priced_differently)}")
