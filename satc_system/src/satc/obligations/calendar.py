"""The legal-holiday calendar and the §7503 shift.

The atom under every computed deadline. A tax due date is a *rule* ("the 15th
day of the 4th month after the tax year ends"), and the calendar decides where
that rule actually lands: IRC §7503 moves an act falling on a Saturday, Sunday,
or legal holiday to the next day that is none of those.

This is why a stored due date is always a latent bug. April 15 was a Tuesday in
2025, a Wednesday in 2026, and lands on a Saturday in 2028 — the deadline moves
with it. Nothing here caches a date across years.

The rule practitioners miss: §7503 counts a legal holiday **in the District of
Columbia**, so DC Emancipation Day (April 16) moves the April deadline for
every filer in the country, not just DC ones.

Holidays are config (``configs/calendar/holidays.yaml``), not code — adding one,
or dating one from the year it took effect, is a YAML edit.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from satc.config import CONFIG_ROOT, ConfigError, read_yaml

_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

SATURDAY = 5
SUNDAY = 6


@dataclass(frozen=True, slots=True)
class Holiday:
    """One legal holiday, as a rule that resolves to a date in a given year."""

    key: str
    name: str
    rule: dict
    observed: bool = True
    effective_from_year: int | None = None
    jurisdiction_note: str = ""

    def applies_in(self, year: int) -> bool:
        return self.effective_from_year is None or year >= self.effective_from_year

    def actual_date(self, year: int) -> date:
        """The date the holiday falls on, before any observance shift."""
        kind = self.rule.get("type")
        month = int(self.rule["month"])
        if kind == "fixed":
            return date(year, month, int(self.rule["day"]))
        if kind == "nth_weekday":
            return _nth_weekday(year, month, self.rule["weekday"], int(self.rule["n"]))
        if kind == "last_weekday":
            return _last_weekday(year, month, self.rule["weekday"])
        raise ConfigError(f"Holiday {self.key!r} has an unknown rule type: {kind!r}")

    def observed_date(self, year: int) -> date:
        """The date it is *observed* — what actually shifts a deadline.

        Per 5 U.S.C. §6103(b): a fixed-date holiday on a Saturday is observed
        the preceding Friday, on a Sunday the following Monday. Holidays defined
        as an nth weekday never need this.
        """
        actual = self.actual_date(year)
        if not self.observed:
            return actual
        if actual.weekday() == SATURDAY:
            return actual - timedelta(days=1)
        if actual.weekday() == SUNDAY:
            return actual + timedelta(days=1)
        return actual


def _weekday_index(name) -> int:
    key = str(name).strip().lower()[:3]
    if key not in _WEEKDAYS:
        raise ConfigError(f"Unknown weekday in holiday config: {name!r}")
    return _WEEKDAYS[key]


def _nth_weekday(year: int, month: int, weekday, n: int) -> date:
    """The nth given weekday of a month (n=1 is the first)."""
    target = _weekday_index(weekday)
    first = date(year, month, 1)
    offset = (target - first.weekday()) % 7
    day = 1 + offset + (n - 1) * 7
    days_in_month = monthrange(year, month)[1]
    if day > days_in_month:
        raise ConfigError(f"No {n}th weekday {weekday} in {year}-{month:02d}")
    return date(year, month, day)


def _last_weekday(year: int, month: int, weekday) -> date:
    """The last given weekday of a month."""
    target = _weekday_index(weekday)
    last = date(year, month, monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - target) % 7)


def load_holidays(config_root: Path | None = None) -> tuple[Holiday, ...]:
    """Read ``configs/calendar/holidays.yaml``."""
    path = (config_root or CONFIG_ROOT) / "calendar" / "holidays.yaml"
    if not path.exists():
        raise ConfigError(f"Holiday calendar not found: {path}")
    data = read_yaml(path)
    if not isinstance(data, dict) or not data.get("holidays"):
        raise ConfigError(f"Holiday calendar declares no holidays: {path}")
    out = []
    for entry in data["holidays"]:
        rule = entry.get("rule")
        if not isinstance(rule, dict):
            raise ConfigError(f"Holiday {entry.get('key')!r} has no rule")
        out.append(Holiday(
            key=str(entry["key"]), name=str(entry.get("name", entry["key"])),
            rule=rule, observed=bool(entry.get("observed", True)),
            effective_from_year=entry.get("effective_from_year"),
            jurisdiction_note=str(entry.get("jurisdiction_note", ""))))
    return tuple(out)


@lru_cache(maxsize=1)
def _holidays() -> tuple[Holiday, ...]:
    return load_holidays()


@lru_cache(maxsize=32)
def holidays_in(year: int) -> dict[date, str]:
    """Every observed legal holiday in a year, mapped to its name."""
    return {h.observed_date(year): h.name for h in _holidays() if h.applies_in(year)}


def is_legal_holiday(day: date) -> bool:
    return day in holidays_in(day.year)


def holiday_name(day: date) -> str:
    """The holiday's name, or ``""`` if the day isn't one."""
    return holidays_in(day.year).get(day, "")


def is_business_day(day: date) -> bool:
    """A day on which an act can be timely performed — not a weekend, not a holiday."""
    return day.weekday() < SATURDAY and not is_legal_holiday(day)


def next_business_day(day: date) -> date:
    """The next day that is neither a weekend nor a legal holiday.

    Always moves forward at least one day — use :func:`shift_for_weekend_holiday`
    when a day that is already a business day should stay put.
    """
    nxt = day + timedelta(days=1)
    while not is_business_day(nxt):
        nxt += timedelta(days=1)
    return nxt


def shift_for_weekend_holiday(day: date) -> date:
    """Apply IRC §7503: move a deadline off a weekend or legal holiday.

    A day that is already a business day is returned unchanged. This is the only
    function a due-date computation should call — it encodes the statute, and
    calling it is what keeps the shift out of every rule.
    """
    while not is_business_day(day):
        day += timedelta(days=1)
    return day


def why_shifted(original: date) -> str:
    """A plain-language reason a date moved, for showing next to a deadline.

    Returns ``""`` when nothing moved. The owner should never see a date jump
    without being told which holiday did it.
    """
    shifted = shift_for_weekend_holiday(original)
    if shifted == original:
        return ""
    reasons: list[str] = []
    cursor = original
    while cursor < shifted:
        name = holiday_name(cursor)
        if name:
            reasons.append(name)
        elif cursor.weekday() >= SATURDAY:
            reasons.append("the weekend")
        cursor += timedelta(days=1)
    seen: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.append(r)
    # Built by hand: "%-d" is a glibc extension and "%#d" is Windows-only.
    return f"{original:%B} {original.day} falls on {' and '.join(seen)}" if seen else ""
