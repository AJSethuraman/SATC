"""The house money format.

Every money string in this app comes from ``helpers.format_money``. The
conventions it implements are not preference -- they are the ones in
``satc-handoff/03-COLLATERAL/SATC Figures and Tables.html``, which says in terms
that they apply to the Jinja templates here as much as to the site. Its
reference table is reproduced as a test below, because the whole point of the
conventions is that every figure in the system agrees, and a second formatter
appearing anywhere is the failure this guards against.

Run with: ``python -m pytest`` from the project root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import format_money  # noqa: E402


def test_two_decimals_always():
    # $300, not $300.00, is the tell the spec names first
    assert format_money(300) == "$300.00"
    assert format_money(0) == "$0.00"


def test_thousands_separated_above_999():
    assert format_money(1137.5) == "$1,137.50"
    assert format_money(999) == "$999.00"


def test_negatives_take_parentheses_never_a_minus():
    # the accounting convention, and the one that survives a photocopier
    assert format_money(-1500) == "($1,500.00)"
    assert "-" not in format_money(-1500)
    assert "−" not in format_money(-1500)


def test_credits_drop_the_symbol():
    # the parentheses already carry the meaning
    assert format_money(-1500, symbol=False) == "(1,500.00)"


def test_statement_rows_can_drop_the_symbol():
    assert format_money(2450, symbol=False) == "2,450.00"


def test_nil_is_an_em_dash_and_zero_is_not():
    # "nothing to report" and "came out to zero" are different facts
    assert format_money(None) == "—"
    assert format_money(0) == "$0.00"


def test_currency_symbol_follows_the_code():
    assert format_money(10, "EUR") == "€10.00"
    assert format_money(-10, "EUR") == "(€10.00)"


def test_garbage_does_not_raise():
    # a template must never blow up mid-render over a bad value
    assert format_money("not a number") == "$0.00"


def test_the_reference_table_renders_exactly():
    """The 'Correct' column of SATC Figures and Tables, line for line."""
    assert format_money(2450.00) == "$2,450.00"
    assert format_money(1137.50) == "$1,137.50"
    assert format_money(300.00) == "$300.00"
    assert format_money(3887.50) == "$3,887.50"
    assert format_money(-1500.00, symbol=False) == "(1,500.00)"
    assert format_money(-116.63, symbol=False) == "(116.63)"
    assert format_money(2270.87) == "$2,270.87"
