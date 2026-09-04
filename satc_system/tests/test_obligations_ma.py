"""Massachusetts obligations, checked against DOR's own published dates.

The strongest test available for a deadline engine: the Massachusetts
Department of Revenue *publishes* the 2026 filing-season dates explicitly, so
these assertions compare computed output against the authority's own numbers
rather than against a re-derivation of the implementation.

Source: Massachusetts DOR, "Tax Due Dates and Extensions", page updated
2026-03-23, read 2026-08-01.
https://www.mass.gov/info-details/massachusetts-dor-tax-due-dates-and-extensions
"""

from __future__ import annotations

from datetime import date

import pytest

from satc.config import ConfigError
from satc.obligations.due_dates import compute, month_period, quarter, tax_year
from satc.obligations.rules import (
    has_jurisdiction,
    rule,
    rules_for_jurisdiction,
)


# --- the jurisdiction is now sourced -----------------------------------------

def test_massachusetts_is_sourced():
    assert has_jurisdiction("MA")
    assert len(rules_for_jurisdiction("MA")) >= 8


def test_ohio_is_still_refused():
    """MA being sourced must not make OH silently answerable."""
    assert not has_jurisdiction("OH")
    with pytest.raises(ConfigError, match="will not fall back"):
        rules_for_jurisdiction("OH")


def test_every_ma_rule_cites_the_dor_page():
    for r in rules_for_jurisdiction("MA"):
        assert "MA DOR" in r.source, f"{r.key} does not cite the DOR page"


# --- income and fiduciary: DOR's published 2026 dates ------------------------

def test_form_1_matches_dors_published_april_15():
    d = compute(rule("ma_form_1"), tax_year(2025))
    assert d.due == date(2026, 4, 15)


def test_form_1_extension_matches_dors_published_october_15():
    d = compute(rule("ma_form_1"), tax_year(2025))
    assert d.extended_due == date(2026, 10, 15)


def test_form_2_fiduciary_matches_april_15():
    assert compute(rule("ma_form_2"), tax_year(2025)).due == date(2026, 4, 15)


# --- pass-through and corporate: DOR's published 2026 dates ------------------

def test_form_3_partnership_matches_dors_published_march_16():
    """DOR says March 16, 2026 — March 15 is a Sunday. The shift produces it."""
    d = compute(rule("ma_form_3"), tax_year(2025))
    assert d.statutory == date(2026, 3, 15)
    assert d.due == date(2026, 3, 16)


def test_form_3_extension_matches_dors_published_september_15():
    d = compute(rule("ma_form_3"), tax_year(2025))
    assert d.extended_due == date(2026, 9, 15)


def test_form_355s_matches_dors_published_march_16_and_september_15():
    d = compute(rule("ma_form_355s"), tax_year(2025))
    assert d.due == date(2026, 3, 16)
    assert d.extended_due == date(2026, 9, 15)


def test_form_355_matches_dors_published_april_15_and_october_15():
    d = compute(rule("ma_form_355"), tax_year(2025))
    assert d.due == date(2026, 4, 15)
    assert d.extended_due == date(2026, 10, 15)


# --- the extension rules that differ from federal ----------------------------

def test_a_federal_extension_does_not_extend_massachusetts():
    """DOR: "Filing an extension with the IRS does not count as filing an
    extension for Massachusetts." The single fact that justifies per-state config."""
    note = rule("ma_form_1").extension.note
    assert "federal extension does NOT extend" in note or \
           "does not extend the Massachusetts return" in note


def test_the_personal_extension_carries_its_80_percent_condition():
    """An extension whose condition fails was never an extension — the return
    is late. So the condition travels with the rule, not in a footnote."""
    ext = rule("ma_form_1").extension
    assert ext.available
    assert "80%" in ext.condition
    assert "no zero extensions" in ext.condition.lower()


def test_the_corporate_extension_carries_its_own_different_condition():
    """Corporate excise is the GREATER of 50% of tax or the minimum excise —
    a different test from the personal 80%."""
    ext = rule("ma_form_355").extension
    assert "50%" in ext.condition
    assert "minimum corporate excise" in ext.condition
    assert "80%" not in ext.condition


def test_the_partnership_extension_states_no_payment_condition():
    """DOR describes the partnership extension as automatic with no condition;
    inventing one would be as wrong as dropping a real one."""
    assert rule("ma_form_3").extension.available
    assert rule("ma_form_3").extension.condition == ""


# --- sales and use -----------------------------------------------------------

def test_monthly_sales_tax_is_the_30th_of_the_following_month():
    d = compute(rule("ma_st9_monthly"), month_period(2026, 3))
    assert d.statutory == date(2026, 4, 30)


def test_quarterly_sales_tax_is_the_30th_after_the_quarter():
    d = compute(rule("ma_st9_quarterly"), quarter(2026, 1))
    assert d.statutory == date(2026, 4, 30)


def test_annual_sales_tax_is_january_30():
    d = compute(rule("ma_st9_annual"), tax_year(2025))
    assert d.statutory == date(2026, 1, 30)


def test_sales_tax_cannot_be_extended():
    for key in ("ma_st9_monthly", "ma_st9_quarterly", "ma_st9_annual", "ma_meals"):
        assert not rule(key).is_extendable, key


def test_monthly_periods_key_correctly():
    """The idempotence key must distinguish months, or March overwrites February."""
    assert month_period(2026, 3).period_key == "2026-03"
    assert month_period(2026, 11).period_key == "2026-11"
    keys = {month_period(2026, m).period_key for m in range(1, 13)}
    assert len(keys) == 12


def test_an_invalid_month_is_refused():
    with pytest.raises(ConfigError):
        month_period(2026, 13)


# --- what is deliberately absent ---------------------------------------------

def test_personal_estimated_installments_are_not_encoded():
    """DOR publishes June 16, 2026 for the Form 1-ES second installment but
    June 15 for the corporate Form 355-ES — and June 15, 2026 is a MONDAY, so
    no weekend or holiday explains the difference.

    Rather than guess whether that is a DOR typo or a rule we do not
    understand, the installments are absent. This test exists so that absence
    is deliberate and documented rather than an oversight someone silently
    "fixes" with arithmetic.
    """
    keys = {r.key for r in rules_for_jurisdiction("MA")}
    assert "ma_form_1_es" not in keys
    assert "ma_form_355_es" not in keys


def test_patriots_day_2030_is_the_known_divergence():
    """Patriots' Day (third Monday in April) is a Massachusetts legal holiday
    that the federal calendar does not know about.

    In most years it lands AFTER April 15 and is irrelevant to the filing
    deadline. In 2028, 2029, 2034, 2035 and 2040 it coincides with DC
    Emancipation Day, so the federal calendar happens to produce the right
    answer anyway.

    **2030 is the one that breaks**: April 15, 2030 is itself Patriots' Day, so
    Massachusetts should move while the federal deadline does not. SATC has no
    MA holiday calendar — the DOR page states no shift rule and none was
    sourced — so it will compute April 15 and be WRONG.

    This test asserts the current, known-incomplete behaviour on purpose, so
    the day someone sources MA's shift rule this fails loudly and points at the
    fix rather than the bug hiding until 2030.
    """
    from datetime import timedelta

    from satc.obligations.calendar import holiday_name

    # April 15, 2030 is a Monday, and is the third Monday of April.
    april_15_2030 = date(2030, 4, 15)
    assert april_15_2030.weekday() == 0
    first_monday = date(2030, 4, 1) + timedelta(days=(0 - date(2030, 4, 1).weekday()) % 7)
    assert first_monday + timedelta(days=14) == april_15_2030

    # No Patriots' Day in the calendar, so nothing moves the MA deadline.
    assert holiday_name(april_15_2030) == ""
    d = compute(rule("ma_form_1"), tax_year(2029))
    assert d.statutory == april_15_2030
    assert d.due == april_15_2030          # known-wrong for MA; see docstring


def test_the_federal_calendar_covers_patriots_day_by_coincidence_in_2029():
    """April 16, 2029 is both Patriots' Day and DC Emancipation Day, so the
    federal shift produces the correct Massachusetts answer without knowing why."""
    from satc.obligations.calendar import holiday_name

    assert holiday_name(date(2029, 4, 16)) == "DC Emancipation Day"
    d = compute(rule("ma_form_1"), tax_year(2028))
    assert d.statutory == date(2029, 4, 15)     # a Sunday
    assert d.due == date(2029, 4, 17)           # past the holiday Monday
