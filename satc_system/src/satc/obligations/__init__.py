"""OBLIGATIONS — the practice's clock.

A tax practice is a deadline engine. Everything a staff accountant does is
downstream of *what is due, what is late, and what is blocked* — so this is the
piece the rest of the practice model hangs off.

An **obligation** is one taxpayer owing one jurisdiction one duty for one
period: file a 1040 for 2025, deposit payroll tax for March, furnish a K-1 to a
partner. Obligations are derived from facts about the client and dated rule
config; work is derived from obligations. Nobody should ever have to *remember*
to create work.

The rule this area exists to enforce: **a due date is computed, never stored.**
It is a rule ("the 15th day of the 4th month after the tax year ends") landed on
a calendar that shifts it off weekends and legal holidays (IRC §7503). April 15
was a Tuesday in 2025 and lands on a Saturday in 2028 — a date frozen from last
year is a return filed late.

Pieces, each testable alone:

===================================  =========================================
:mod:`satc.obligations.calendar`     legal holidays + the §7503 shift
===================================  =========================================
"""

from __future__ import annotations

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

__all__ = [
    "Holiday",
    "holiday_name",
    "holidays_in",
    "is_business_day",
    "is_legal_holiday",
    "load_holidays",
    "next_business_day",
    "shift_for_weekend_holiday",
    "why_shifted",
]
