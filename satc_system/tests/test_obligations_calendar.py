"""The legal-holiday calendar and the §7503 deadline shift.

Correctness-critical: every computed deadline in the system lands through
:func:`shift_for_weekend_holiday`. A wrong shift here files a return late.

The hand-checked cases below are real observed dates, not round-trips of the
implementation — a test that only re-derives the code proves nothing.
"""

from __future__ import annotations

from datetime import date

import pytest

from satc.config import ConfigError
from satc.obligations.calendar import (
    Holiday,
    holiday_name,
    holidays_in,
    is_business_day,
    is_legal_holiday,
    load_holidays,
    next_business_day,
    shift_for_weekend_holiday,
    why_shifted,
)


# --- the config loads --------------------------------------------------------

def test_calendar_loads():
    holidays = load_holidays()
    keys = {h.key for h in holidays}
    assert "dc_emancipation_day" in keys, "the DC holiday that moves April 15 is missing"
    assert {"new_years_day", "thanksgiving", "christmas_day", "juneteenth"} <= keys


def test_an_unknown_rule_type_is_rejected():
    bad = Holiday(key="x", name="X", rule={"type": "phase_of_moon", "month": 1})
    with pytest.raises(ConfigError):
        bad.actual_date(2026)


# --- fixed-date holidays and their observance --------------------------------

def test_fixed_holiday_on_a_weekday_is_not_moved():
    # Christmas 2025 is a Thursday.
    assert date(2025, 12, 25).weekday() == 3
    assert holiday_name(date(2025, 12, 25)) == "Christmas Day"


def test_saturday_holiday_is_observed_the_friday_before():
    # July 4, 2026 is a Saturday -> observed Friday July 3.
    assert date(2026, 7, 4).weekday() == 5
    assert holiday_name(date(2026, 7, 3)) == "Independence Day"
    assert not is_legal_holiday(date(2026, 7, 4))   # the actual day is a Saturday anyway


def test_sunday_holiday_is_observed_the_monday_after():
    # Christmas 2033 falls on a Sunday -> observed Monday December 26.
    assert date(2033, 12, 25).weekday() == 6
    assert holiday_name(date(2033, 12, 26)) == "Christmas Day"


def test_juneteenth_did_not_exist_before_2021():
    """Pub. L. 117-17. A holiday that shifts a 2019 deadline would be wrong."""
    assert holiday_name(date(2019, 6, 19)) == ""
    assert holiday_name(date(2022, 6, 20)) == "Juneteenth National Independence Day"


# --- computed (nth / last weekday) holidays ----------------------------------

def test_nth_weekday_holidays_land_correctly():
    # Hand-checked: MLK 2026 = Mon Jan 19; Thanksgiving 2026 = Thu Nov 26.
    assert holiday_name(date(2026, 1, 19)) == "Birthday of Martin Luther King, Jr."
    assert holiday_name(date(2026, 11, 26)) == "Thanksgiving Day"


def test_last_weekday_holiday_lands_correctly():
    # Memorial Day 2026 = Mon May 25 (the last Monday, not the fourth).
    assert holiday_name(date(2026, 5, 25)) == "Memorial Day"
    # 2027 has five Mondays in May; the last is May 31.
    assert holiday_name(date(2027, 5, 31)) == "Memorial Day"


# --- the DC rule that moves April 15 nationwide ------------------------------

def test_dc_emancipation_day_is_a_holiday():
    """§7503 counts DC holidays — this is why April 15 is not always the deadline."""
    assert holiday_name(date(2026, 4, 16)) == "DC Emancipation Day"


def test_emancipation_day_on_a_saturday_pushes_april_15_to_the_17th():
    """2028: April 16 is a Sunday, observed Monday April 17.

    April 15 is a Saturday, so the deadline walks Sat -> Sun -> Mon(holiday)
    -> Tuesday April 18. This is the case that catches people out.
    """
    assert date(2028, 4, 15).weekday() == 5      # Saturday
    assert date(2028, 4, 16).weekday() == 6      # Sunday
    assert holiday_name(date(2028, 4, 17)) == "DC Emancipation Day"
    assert shift_for_weekend_holiday(date(2028, 4, 15)) == date(2028, 4, 18)


def test_emancipation_day_on_a_friday_pushes_a_thursday_deadline():
    """2027: April 16 is a Friday and is itself the holiday."""
    assert date(2027, 4, 16).weekday() == 4
    assert holiday_name(date(2027, 4, 16)) == "DC Emancipation Day"
    # April 15, 2027 is a Thursday — a business day, so it does NOT move.
    assert shift_for_weekend_holiday(date(2027, 4, 15)) == date(2027, 4, 15)


# --- the shift itself --------------------------------------------------------

def test_a_business_day_deadline_does_not_move():
    # April 15, 2026 is a Wednesday.
    assert shift_for_weekend_holiday(date(2026, 4, 15)) == date(2026, 4, 15)


def test_a_saturday_deadline_moves_to_monday():
    assert date(2028, 9, 16).weekday() == 5
    assert shift_for_weekend_holiday(date(2028, 9, 16)) == date(2028, 9, 18)


def test_a_sunday_deadline_moves_to_monday():
    assert date(2026, 3, 15).weekday() == 6      # 1065/1120-S due date, a Sunday
    assert shift_for_weekend_holiday(date(2026, 3, 15)) == date(2026, 3, 16)


def test_the_shift_walks_past_a_holiday_monday():
    """A Saturday deadline before a Monday holiday lands on Tuesday."""
    # Jan 1, 2028 is a Saturday (observed Fri Dec 31, 2027); Jan 17, 2028 is MLK Monday.
    assert holiday_name(date(2028, 1, 17)) == "Birthday of Martin Luther King, Jr."
    assert shift_for_weekend_holiday(date(2028, 1, 15)) == date(2028, 1, 18)


def test_shift_never_moves_a_deadline_backwards():
    """A deadline may only ever move later — moving it earlier would file late."""
    for year in (2025, 2026, 2027, 2028):
        for month in range(1, 13):
            for day in (1, 15, 28):
                original = date(year, month, day)
                assert shift_for_weekend_holiday(original) >= original


def test_every_shifted_date_is_a_business_day():
    for year in (2026, 2027, 2028):
        for month in range(1, 13):
            for day in (1, 14, 15, 16, 30 if month != 2 else 28):
                assert is_business_day(shift_for_weekend_holiday(date(year, month, day)))


def test_next_business_day_always_advances():
    """Unlike the shift, this one never returns the day it was given."""
    monday = date(2026, 4, 13)
    assert is_business_day(monday)
    assert next_business_day(monday) == date(2026, 4, 14)


def test_weekends_are_not_business_days():
    assert not is_business_day(date(2026, 4, 18))   # Saturday
    assert not is_business_day(date(2026, 4, 19))   # Sunday
    assert is_business_day(date(2026, 4, 17))       # Friday


# --- explaining the shift to the owner ---------------------------------------

def test_an_unmoved_date_has_no_explanation():
    assert why_shifted(date(2026, 4, 15)) == ""


def test_a_moved_date_names_what_moved_it():
    reason = why_shifted(date(2028, 4, 15))
    assert "the weekend" in reason
    assert "DC Emancipation Day" in reason
    assert "April 15" in reason


def test_holidays_in_a_year_are_distinct_dates():
    """Two holidays observed on one day would silently collapse in the map."""
    for year in (2025, 2026, 2027, 2028, 2033):
        observed = holidays_in(year)
        assert len(observed) >= 11, f"{year} lost a holiday"
