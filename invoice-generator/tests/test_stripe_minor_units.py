"""The amount handed to Stripe must be in the currency's smallest unit.

The invoice's own arithmetic was never wrong here. What was wrong was the
single number handed to the payment processor, which is the worst place for a
money bug to live: the books say one thing, the card statement says another,
and the reconciliation that would catch it happens weeks later.

See ``stripe_utils.to_minor_units``.
"""
import pytest

from currencies import decimals_for
from stripe_utils import to_minor_units


# The regression, stated as the two numbers that mattered.
def test_a_yen_invoice_is_not_charged_one_hundred_times_over():
    # ¥1,500 was sent to Checkout as 150000 and charged as ¥150,000.
    assert to_minor_units(1500, "JPY") == 1500


def test_a_dinar_invoice_is_not_charged_one_tenth():
    # KWD 1.500 was sent as 150 fils instead of 1500, and never settled.
    assert to_minor_units(1.500, "KWD") == 1500


@pytest.mark.parametrize(
    "code", ["JPY", "KRW", "VND", "CLP", "ISK", "XAF", "XOF", "RWF"]
)
def test_zero_decimal_currencies_pass_the_amount_through_whole(code):
    assert to_minor_units(2500, code) == 2500
    assert decimals_for(code) == 0


@pytest.mark.parametrize("code", ["BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"])
def test_three_decimal_currencies_scale_by_a_thousand(code):
    assert to_minor_units(12.345, code) == 12345
    assert decimals_for(code) == 3


@pytest.mark.parametrize("code", ["USD", "EUR", "GBP", "CAD", "AUD", "INR"])
def test_two_decimal_currencies_are_unchanged_by_the_fix(code):
    # The overwhelmingly common path must behave exactly as it did before.
    assert to_minor_units(1234.56, code) == 123456


def test_case_is_not_load_bearing():
    # create_checkout_session lowercases the code before calling this.
    assert to_minor_units(1500, "jpy") == to_minor_units(1500, "JPY")


def test_an_unknown_currency_falls_back_to_two_decimals():
    # Stripe would reject the currency itself long before the amount matters,
    # so the safe fallback is the near-universal case rather than a crash.
    assert to_minor_units(10, "ZZZ") == 1000


def test_rounding_lands_on_the_nearest_whole_minor_unit():
    assert to_minor_units(19.999, "USD") == 2000
    assert to_minor_units(0.4, "JPY") == 0


def test_a_half_minor_unit_rounds_to_even_and_that_is_unchanged():
    """Python's round() is banker's rounding, and this pins it deliberately.

    ``round(2.5)`` is 2, not 3. That behaviour is inherited from the
    ``int(round(amount * 100))`` this replaced, and it is left alone: the fix
    above was about the *multiplier* being wrong for 23 currencies, and
    quietly changing how half a cent rounds on a live payment path at the same
    time would have hidden one change inside another.

    Recorded here so the next reader knows it is a decision and not an
    oversight. A half-minor-unit balance can only arise from a flat tax or
    discount entered to three decimals; a percentage total is already rounded
    to two by ``Invoice.total``.
    """
    assert to_minor_units(0.025, "USD") == 2   # 2.5 -> 2, not 3
    assert to_minor_units(0.035, "USD") == 4   # 3.5 -> 4


# --- when Stripe itself says no -------------------------------------------
#
# `is_chargeable` asks whether we know how many minor units an amount is. It
# does NOT assert that Stripe will present the currency: KPW, CUP and IRR are
# ordinary two-decimal ISO codes and Stripe takes none of them. That gap is
# deliberately not closed with a second hard-coded list — Stripe's supported
# list is not reachable from here, and writing one from memory is exactly what
# put HUF on the divergent list on a misreading. Stripe is the authority, so
# its refusal is translated instead of guessed at.
#
# Raised by Codex on PR #289, round five.

def test_a_currency_stripe_rejects_comes_back_as_a_readable_refusal(
    monkeypatch
):
    import stripe

    import stripe_utils

    class Settled:
        id = 1
        balance_due = 100.0
        currency = "kpw"
        invoice_number = "INV-1"

    def refuse(**kwargs):
        raise stripe.InvalidRequestError(
            "Invalid currency: kpw", param="currency"
        )

    monkeypatch.setattr(stripe.checkout.Session, "create", staticmethod(refuse))
    monkeypatch.setattr(stripe_utils, "configure", lambda key: None)

    with pytest.raises(stripe_utils.UnsupportedCurrency) as caught:
        stripe_utils.create_checkout_session(
            Settled(), "sk_test", "https://x.example", "acct_1"
        )
    message = str(caught.value)
    assert "KPW" in message
    assert "record payment by hand" in message


def test_any_other_stripe_rejection_is_left_alone(monkeypatch):
    """Only a currency complaint is reworded. Swallowing the rest into a
    currency message would hide a real configuration error behind the wrong
    explanation."""
    import stripe

    import stripe_utils

    class Settled:
        id = 1
        balance_due = 100.0
        currency = "usd"
        invoice_number = "INV-1"

    def refuse(**kwargs):
        raise stripe.InvalidRequestError(
            "No such destination: acct_1", param="destination"
        )

    monkeypatch.setattr(stripe.checkout.Session, "create", staticmethod(refuse))
    monkeypatch.setattr(stripe_utils, "configure", lambda key: None)

    with pytest.raises(stripe.InvalidRequestError):
        stripe_utils.create_checkout_session(
            Settled(), "sk_test", "https://x.example", "acct_1"
        )
