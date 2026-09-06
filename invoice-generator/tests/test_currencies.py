"""Unit tests for the ISO 4217 currency table.

These are the guards on the one thing this table exists to get right: the
number of decimal places a currency actually has. ``helpers.format_money``
hard-codes two, and two is wrong for the yen (which has none) and for the
Kuwaiti dinar (which has three) — the same assumption that makes
``stripe_utils`` charge ``int(round(amount * 100))`` for every currency alike.
A wrong ``decimals`` here is not a formatting blemish; it is a 100x overcharge
on a JPY invoice and a 10x undercharge on a KWD one.

Run with: ``python -m pytest tests/test_currencies.py`` from the project root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import currencies  # noqa: E402
import helpers  # noqa: E402
from currencies import (  # noqa: E402
    CURRENCIES,
    CURRENCY_CHOICES,
    decimals_for,
    format_amount,
    get_currency,
    symbol_for,
)

# ISO 4217 currencies with no minor unit. Anything formatted with a decimal
# point in one of these is quoting an amount that cannot exist.
ZERO_DECIMAL = [
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG",
    "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
]

# The seven currencies subdivided into thousandths (fils, millimes, dirham).
THREE_DECIMAL = ["BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"]


# ---------------------------------------------------------------------------
# Shape of the table
# ---------------------------------------------------------------------------
def test_at_least_150_currencies_are_present():
    assert len(CURRENCIES) >= 150


def test_every_entry_has_all_four_keys():
    for code, entry in CURRENCIES.items():
        assert set(entry) == {"code", "name", "symbol", "decimals"}, code


def test_every_code_is_three_uppercase_letters_and_keys_its_own_entry():
    for code, entry in CURRENCIES.items():
        assert len(code) == 3 and code.isupper() and code.isalpha(), code
        # The dict key and the entry's own code must not drift apart: a lookup
        # that returns an entry describing a *different* currency is exactly
        # the silent substitution get_currency refuses to do.
        assert entry["code"] == code


def test_every_entry_has_a_name_and_a_symbol():
    for code, entry in CURRENCIES.items():
        assert entry["name"].strip(), code
        # Never blank: an amount with no symbol does not say what it is
        # denominated in. Where there is no glyph the symbol is the code.
        assert entry["symbol"].strip(), code


def test_decimals_are_only_ever_zero_two_or_three():
    for code, entry in CURRENCIES.items():
        assert entry["decimals"] in (0, 2, 3), (code, entry["decimals"])


def test_no_duplicate_codes():
    codes = [row[0] for row in currencies._TABLE]
    assert len(codes) == len(set(codes))
    # ...and nothing was lost building the dict from the table.
    assert len(codes) == len(CURRENCIES)


# ---------------------------------------------------------------------------
# Minor units — the reason this module exists
# ---------------------------------------------------------------------------
def test_zero_decimal_currencies_are_marked_zero():
    for code in ZERO_DECIMAL:
        assert decimals_for(code) == 0, code


def test_zero_decimal_currencies_format_with_no_decimal_point():
    for code in ZERO_DECIMAL:
        assert "." not in format_amount(1500, code), code
    assert format_amount(1500, "JPY") == "¥1,500"
    assert format_amount(1500, "KRW") == "₩1,500"
    assert format_amount(1500, "VND") == "₫1,500"
    assert format_amount(1500, "CLP") == "$1,500"
    assert format_amount(1500, "ISK") == "kr1,500"


def test_three_decimal_currencies_are_marked_three():
    for code in THREE_DECIMAL:
        assert decimals_for(code) == 3, code


def test_three_decimal_currencies_format_with_exactly_three():
    for code in THREE_DECIMAL:
        assert format_amount(1500, code).split(".")[-1] == "000", code
    assert format_amount(1500, "BHD") == "BD1,500.000"
    assert format_amount(1500, "KWD") == "KD1,500.000"
    assert format_amount(1500, "OMR") == "OMR1,500.000"
    assert format_amount(1500, "TND") == "DT1,500.000"


def test_a_three_decimal_amount_keeps_its_third_digit():
    # KWD 1.500 is 1,500 fils. Truncated to two places it becomes KWD 1.50 —
    # a tenth of the invoice.
    assert format_amount(1.5, "KWD") == "KD1.500"
    assert format_amount(1.234, "KWD") == "KD1.234"


def test_hungarian_forint_keeps_the_iso_value_not_the_stripe_one():
    # HUF is 2 in ISO 4217 and 0 at Stripe. This table follows ISO; a
    # processor's quirk belongs in the code that talks to that processor.
    assert decimals_for("HUF") == 2
    assert format_amount(1500, "HUF") == "Ft1,500.00"


# ---------------------------------------------------------------------------
# Lookups refuse to guess
# ---------------------------------------------------------------------------
def test_get_currency_returns_none_for_an_unknown_code():
    assert get_currency("ZZZ") is None
    assert get_currency("") is None
    assert get_currency(None) is None


def test_get_currency_does_not_fall_back_to_usd():
    # The failure this guards: an unknown code silently answered with the US
    # dollar bills the wrong money with the wrong symbol and says nothing.
    assert get_currency("ZZZ") != get_currency("USD")
    assert get_currency("QQQ") is None


def test_get_currency_is_case_insensitive_and_returns_a_copy():
    assert get_currency("usd")["code"] == "USD"
    entry = get_currency("USD")
    entry["symbol"] = "TAMPERED"
    assert CURRENCIES["USD"]["symbol"] == "$"
    assert symbol_for("USD") == "$"


def test_symbol_for_unknown_code_is_the_code_itself():
    assert symbol_for("ZZZ") == "ZZZ"
    assert symbol_for("zzz") == "ZZZ"
    assert symbol_for(None) == ""


def test_decimals_for_unknown_code_defaults_to_two():
    assert decimals_for("ZZZ") == 2
    assert decimals_for(None) == 2
    assert format_amount(1500, "ZZZ") == "ZZZ1,500.00"


# ---------------------------------------------------------------------------
# format_amount is display code: it must never raise
# ---------------------------------------------------------------------------
def test_format_amount_handles_none_zero_negative_and_huge_without_raising():
    assert format_amount(None, "USD") == "$0.00"
    assert format_amount(0, "USD") == "$0.00"
    assert format_amount(-1234.5, "USD") == "-$1,234.50"
    assert format_amount(1e15, "USD") == "$1,000,000,000,000,000.00"
    # Whatever these produce, they produce a string rather than a 500 on a
    # page the client is looking at.
    for value in (None, 0, -1, 1e308, float("inf"), float("nan"), "", "abc",
                  "1500", True, [], object()):
        for code in ("USD", "JPY", "KWD", "ZZZ", None):
            assert isinstance(format_amount(value, code), str)


def test_non_finite_amounts_format_as_zero_not_as_nan():
    # A NaN total once rendered "$nan" for every invoice in the account.
    assert format_amount(float("nan"), "USD") == "$0.00"
    assert format_amount(float("inf"), "USD") == "$0.00"


def test_a_bool_is_not_an_amount():
    assert format_amount(True, "USD") == "$0.00"


def test_negative_zero_does_not_render_a_minus_sign():
    assert format_amount(-0.001, "USD") == "$0.00"
    assert format_amount(-0.4, "JPY") == "¥0"


# ---------------------------------------------------------------------------
# Compatibility with what helpers.py already ships
# ---------------------------------------------------------------------------
def test_every_helpers_currency_exists_in_the_new_table():
    missing = [c for c in helpers.CURRENCY_SYMBOLS if c not in CURRENCIES]
    assert missing == []


def test_helpers_symbols_are_reproduced_character_for_character():
    # If this fails, a page that switches from helpers.currency_symbol to
    # symbol_for silently changes what clients see on existing invoices.
    for code, symbol in helpers.CURRENCY_SYMBOLS.items():
        assert symbol_for(code) == symbol, code


def test_two_decimal_formatting_still_matches_helpers_format_money():
    for code in helpers.CURRENCY_SYMBOLS:
        if decimals_for(code) == 2:
            assert format_amount(1250, code) == helpers.format_money(1250, code)


# ---------------------------------------------------------------------------
# The dropdown
# ---------------------------------------------------------------------------
def test_currency_choices_covers_every_currency_exactly_once():
    codes = [code for code, _ in CURRENCY_CHOICES]
    assert len(codes) == len(CURRENCIES)
    assert set(codes) == set(CURRENCIES)


def test_currency_choices_puts_the_common_currencies_first():
    codes = [code for code, _ in CURRENCY_CHOICES]
    assert codes[:9] == [
        "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "INR", "CHF", "CNY",
    ]
    assert codes[9:] == sorted(codes[9:])


def test_currency_choices_labels_read_like_a_dropdown():
    labels = dict(CURRENCY_CHOICES)
    assert labels["USD"] == "USD — US Dollar ($)"
    assert labels["JPY"] == "JPY — Japanese Yen (¥)"
    # CHF's stored symbol carries a trailing space for formatting; the label
    # must not show it.
    assert labels["CHF"] == "CHF — Swiss Franc (CHF)"
