"""Landing a rule on a period — where a deadline actually becomes a date.

An :class:`~satc.obligations.rules.ObligationRule` says *"the 15th day of the
4th month after the tax year ends."* A :class:`Period` says *which* year. This
module puts them together and then applies IRC §7503, producing both the
statutory date and the date the act is actually due.

Both are kept, deliberately. The statutory date is what the extension runs from
and what the owner sees cited; the shifted date is the one that matters this
year. Collapsing them is how a system ends up computing an extended deadline six
months after a *shifted* date and drifting a day every year.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

from satc.config import ConfigError
from satc.obligations.calendar import shift_for_weekend_holiday, why_shifted
from satc.obligations.rules import ObligationRule

# A "half month" in the extension tables is 15 days. The only rule that uses one
# is Form 1041's 5½-month extension, which must land on September 30 for a
# calendar-year trust — the 15th day of the 4th month, plus 5 months, plus 15
# days. Verified against that case in the tests.
_HALF_MONTH_DAYS = 15


@dataclass(frozen=True, slots=True)
class Period:
    """The span an obligation is owed for, and the key that makes it unique.

    ``period_key`` is the idempotence key for the whole recurring model
    (doctrine rule 4): regenerating a period must find the same obligation, not
    mint a second one. ``"2025"`` for an annual return, ``"2026Q1"`` for a
    payroll quarter, ``"2026-03"`` for a monthly duty.
    """

    period_key: str
    start: date
    end: date

    @property
    def is_calendar_year(self) -> bool:
        return (self.start.month, self.start.day) == (1, 1) and \
               (self.end.month, self.end.day) == (12, 31)


def tax_year(year: int, *, fiscal_year_end: date | None = None) -> Period:
    """An annual period. Defaults to the calendar year.

    ``fiscal_year_end`` is what makes every other date computable — without it
    a fiscal-year entity's deadlines cannot be derived at all.
    """
    if fiscal_year_end is None:
        return Period(str(year), date(year, 1, 1), date(year, 12, 31))
    start = _add_months(fiscal_year_end, -12) + timedelta(days=1)
    return Period(str(year), start, fiscal_year_end)


def month_period(year: int, month: int) -> Period:
    """A calendar month, keyed ``2026-03``.

    The period for monthly sales-tax and withholding duties.
    """
    if not 1 <= month <= 12:
        raise ConfigError(f"Month must be 1-12, got {month}")
    return Period(f"{year}-{month:02d}", date(year, month, 1),
                  date(year, month, monthrange(year, month)[1]))


def quarter(year: int, q: int) -> Period:
    """A calendar quarter, keyed ``2026Q1``."""
    if not 1 <= q <= 4:
        raise ConfigError(f"Quarter must be 1-4, got {q}")
    start_month = 3 * (q - 1) + 1
    end_month = start_month + 2
    return Period(f"{year}Q{q}", date(year, start_month, 1),
                  date(year, end_month, monthrange(year, end_month)[1]))


@dataclass(frozen=True, slots=True)
class DueDates:
    """When an obligation is due — statutory and as-shifted, original and extended."""

    rule_key: str
    period_key: str
    statutory: date
    due: date
    shift_reason: str = ""
    extended_statutory: date | None = None
    extended_due: date | None = None
    extended_shift_reason: str = ""
    extension_form: str = ""
    installment: int | None = None
    documents_due: date | None = None
    documents_due_is_firm_policy: bool = True

    @property
    def was_shifted(self) -> bool:
        return self.due != self.statutory

    @property
    def is_extendable(self) -> bool:
        return self.extended_due is not None

    def final_due(self, *, extended: bool = False) -> date:
        """The operative deadline — extended when an extension is on file."""
        if extended and self.extended_due is not None:
            return self.extended_due
        return self.due

    def days_until(self, today: date, *, extended: bool = False) -> int:
        """Days from ``today`` to the operative deadline. Negative means overdue."""
        return (self.final_due(extended=extended) - today).days


def _clamp_day(year: int, month: int, day: int) -> date:
    """A date, with the day pulled back to the last of the month if it overruns.

    Needed for duties due on "the last day of the month following" — a rule
    written as day 31 must land on April 30, not raise.
    """
    return date(year, month, min(day, monthrange(year, month)[1]))


def _add_months(anchor: date, months: int) -> date:
    total = anchor.month + months
    year = anchor.year + (total - 1) // 12
    month = (total - 1) % 12 + 1
    return _clamp_day(year, month, anchor.day)


def _nth_month_after(anchor: date, months: int, day: int) -> date:
    """The ``day``-th day of the ``months``-th month after ``anchor``'s month.

    "The 15th day of the 4th month after the tax year ends": for a December
    year-end that is April 15 of the following year.
    """
    total = anchor.month + months
    year = anchor.year + (total - 1) // 12
    month = (total - 1) % 12 + 1
    return _clamp_day(year, month, day)


def _statutory_due(rule: ObligationRule, period: Period,
                   installment: int | None = None) -> date:
    basis = rule.basis
    due = rule.due
    day = int(due.get("day", 15))

    if basis in ("fiscal_year_end", "quarter_end"):
        return _nth_month_after(period.end, int(due["months"]), day)

    if basis == "fixed":
        # A fixed calendar date in the year AFTER the period (W-2s for 2025 are
        # furnished by January 31, 2026).
        return _clamp_day(period.end.year + 1, int(due["month"]), day)

    if basis == "installments":
        months = list(due.get("months") or [])
        if installment is None:
            raise ConfigError(
                f"Rule {rule.key!r} is an installment rule — ask for one installment "
                f"(1-{len(months)}), or call installment_due_dates()")
        if not 1 <= installment <= len(months):
            raise ConfigError(
                f"Rule {rule.key!r} has {len(months)} installments; got {installment}")
        # Installments run from the START of the period, and the last one falls
        # in the following January — hence month 13, not month 1.
        offset = int(months[installment - 1])
        year = period.start.year + (offset - 1) // 12
        month = (offset - 1) % 12 + 1
        return _clamp_day(year, month, day)

    raise ConfigError(f"Rule {rule.key!r} has an unsupported due basis: {basis!r}")


def _extended_statutory(rule: ObligationRule, statutory: date) -> date | None:
    """The extended deadline, measured from the STATUTORY original.

    Not from the shifted one. An extension is granted from the date the law
    sets; measuring from a weekend-shifted date would drift the extended
    deadline a day or two every year.
    """
    if not rule.is_extendable:
        return None
    months = rule.extension.months
    whole = int(months)
    extended = _add_months(statutory, whole)
    if months - whole:
        extended += timedelta(days=_HALF_MONTH_DAYS)
    return extended


def compute(rule: ObligationRule, period: Period, *,
            installment: int | None = None, policy=None) -> DueDates:
    """Land a rule on a period and apply the calendar.

    ``policy`` supplies the firm's own document cutoff. Pass ``None`` to use the
    installed one; the resulting ``documents_due`` is always flagged as firm
    policy so the UI never renders it like a statutory date.
    """
    from satc.obligations.policy import policy as installed_policy

    statutory = _statutory_due(rule, period, installment)
    due = shift_for_weekend_holiday(statutory)

    ext_statutory = _extended_statutory(rule, statutory)
    ext_due = shift_for_weekend_holiday(ext_statutory) if ext_statutory else None

    firm = installed_policy() if policy is None else policy
    documents_due = firm.cutoff_for(rule.key, due) if firm else None

    return DueDates(
        rule_key=rule.key,
        period_key=period.period_key if installment is None
        else f"{period.period_key}-{installment}",
        statutory=statutory, due=due, shift_reason=why_shifted(statutory),
        extended_statutory=ext_statutory, extended_due=ext_due,
        extended_shift_reason=why_shifted(ext_statutory) if ext_statutory else "",
        extension_form=rule.extension.form, installment=installment,
        documents_due=documents_due)


def installment_due_dates(rule: ObligationRule, period: Period) -> list[DueDates]:
    """Every installment of an installment rule, in order."""
    if rule.basis != "installments":
        raise ConfigError(f"Rule {rule.key!r} is not an installment rule")
    count = len(rule.due.get("months") or [])
    return [compute(rule, period, installment=i) for i in range(1, count + 1)]


def perfection_deadline(rule: ObligationRule, due: date) -> date | None:
    """The last day to retransmit a rejected e-filed return.

    **Calendar days, never shifted.** IRS Pub 1345 is explicit that the
    transmission perfection period "has never been extended regardless of
    weekends, holidays or the end of the year cutoff" — so this deliberately
    does not call the §7503 shift. Applying the shift here would tell the owner
    they have longer than they do.
    """
    if not rule.perfection_days:
        return None
    return due + timedelta(days=rule.perfection_days)
