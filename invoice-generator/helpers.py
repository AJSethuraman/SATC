"""Small shared helpers: currency formatting and form parsing."""
import math
from datetime import datetime

from currencies import format_amount

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CAD": "$",
    "AUD": "$",
    "INR": "₹",
    "CHF": "CHF ",
    "CNY": "¥",
    "BRL": "R$",
    "ZAR": "R",
    "MXN": "$",
    "SGD": "$",
    "NZD": "$",
}


def currency_symbol(code):
    return CURRENCY_SYMBOLS.get((code or "USD").upper(), "")


def format_money(amount, code="USD"):
    """Return a human-friendly currency string, e.g. ``$1,250.00``.

    Delegates to ``currencies.format_amount``, which honours the currency's
    **minor units** instead of assuming two decimal places everywhere. For the
    two-decimal currencies — which is every one this app offered before the
    picker existed, bar JPY — the output is character-for-character what this
    function always returned, and ``tests/test_currencies.py`` holds that.

    What changes is the rest of the world's money. ``format_money(1500,
    "JPY")`` used to render ``¥1,500.00``: decimals the yen does not have, on
    a document a client reads. It now renders ``¥1,500``. The same table is
    what ``stripe_utils.to_minor_units`` consults, so the figure printed on
    the invoice and the figure charged to the card are derived from one
    source rather than two that disagreed.
    """
    return format_amount(amount, code)


def parse_money(value, default=0.0):
    """Parse a user-supplied number. Returns ``(number, ok)``.

    ``ok`` is False when a value *was supplied* and is not a finite number.
    Both front doors then refuse the submission instead of billing the
    default, because the two ways this used to go wrong are both silent:

    * ``"$500.00"`` pasted into a rate raised ValueError and became ``0.00``,
      so the invoice went out for nothing with no warning at all.
    * ``"1e400"`` (a paste or a fat-fingered exponent) is a *valid* float
      literal that overflows to ``inf``. ``inf`` through the totals gives
      ``inf * 0 == nan``, so the invoice total became NaN — and because
      ``nan < 0`` is False it sailed past the negative-total guard, was
      stored, and then poisoned the History KPIs, which read ``$nan`` for
      **every** invoice in the account.

    Absence is not an error: ``None`` and ``""`` mean "leave it at the
    default", which is how a blank tax / discount / shipping box is meant to
    behave. A bool is refused rather than counted — ``int(True) == 1`` is how
    a yes/no answer gets billed as a quantity of one.

    One function so both front doors make the same call: the web form and the
    JSON API used to have separate coercion with separate holes.

    Caught by tests/test_scenarios.py::
      test_unparseable_money_is_refused_not_silently_billed_as_zero
      test_an_overflowing_rate_cannot_produce_a_nan_invoice
    """
    if value is None:
        return default, True
    if isinstance(value, bool):
        return default, False
    if isinstance(value, (int, float)):
        number = float(value)
        return (number, True) if math.isfinite(number) else (default, False)
    text = str(value).strip().replace(",", "")
    if text == "":
        return default, True
    try:
        number = float(text)
    except ValueError:
        return default, False
    return (number, True) if math.isfinite(number) else (default, False)


def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
