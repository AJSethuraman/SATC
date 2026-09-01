"""The tax calendar — filing dates, and the date a client's papers must be in.

WHY THIS EXISTS. The firm's whole year hangs off four dates a season and none of
them was in the software. `registry/firm-settings.yaml` carried four materials
deadlines TYPED BY HAND, under a comment reading *"CHECK THIS AGAINST THE IRS
CALENDAR each season before rolling it forward"* -- an instruction to a person to
remember something a calendar can compute. `docs/pricing-and-deadlines-basis.md`
worked the statute out in full and ended with a rule "to approve", and nobody
approved it.

So the dates were right for 2026 and would have been wrong the first year a
deadline shifted, silently, in a letter a client had already been sent.

WHAT THE RULE ACTUALLY IS, measured rather than taken from the proposal. The
basis document proposes *filing date minus four weeks, moved to the nearest
Monday*. The four dates actually on file are exactly **filing date minus 21
days**, unshifted:

    individual_1040    15 Apr 2027 -> 25 Mar 2027   (21 days, a Thursday)
    c_corp_1120        15 Apr 2027 -> 25 Mar 2027
    s_corp_1120s       15 Mar 2027 -> 22 Feb 2027   (21 days, a Monday)
    partnership_1065   15 Mar 2027 -> 22 Feb 2027

Three weeks is what the firm has been telling clients, so three weeks is what
this computes, and `tests/test_calendar.py` holds it to reproducing those four
dates exactly. Changing the policy is one number below; changing what a client
was already told is not a code change.

SOURCES, because tax parameters are never guessed here:
  * **IRC section 6072** -- partnerships and S corporations file by the 15th day
    of the third month after the tax year ends; individuals and C corporations
    by the 15th day of the fourth month. For a calendar-year filer: 15 March and
    15 April of the following year.
  * **IRC section 7503** -- a due date falling on a Saturday, Sunday or legal
    holiday moves to the next day that is none of those.
  * **DC Emancipation Day, 16 April.** A District of Columbia holiday, and it
    moves the FEDERAL individual deadline because section 7503 counts a legal
    holiday in the District. When the 16th falls on a Saturday it is observed on
    Friday the 15th; on a Sunday, Monday the 17th. Either way 15 April is no
    longer available and the deadline moves on. This is why the 2017 deadline
    was 18 April and the 2022 deadline was 18 April.

NAMED `deadlines` AND NOT `calendar` ON PURPOSE. A module called `calendar.py`
here shadows the standard library's, and the standard library's is what
`datetime.strptime` reaches for -- so every date the whole package parsed broke
the moment the file existed. This repo already carries one of these:
`requests.py` shadows the HTTP library, which is why nothing here may import it.
One was an accident nobody planned to repeat.

THE RULE AS IT STANDS TODAY, APPLIED TO ANY YEAR. Emancipation Day did not
affect federal filing deadlines until the mid-2000s, so asking this module about
a 1990s season gets today's rule rather than that year's history. It is built to
compute the season ahead, not to audit one long past; a date needed for an old
year should come from the return, not from here.

NOT MODELLED, and named so nobody assumes it is: Patriots' Day, which moves the
deadline for Maine and Massachusetts filers only; fiscal-year filers, who are
not a calendar-year 15 March / 15 April case; and disaster postponements, which
the IRS announces per area and no rule can derive.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# HOW LONG BEFORE THE FILING DATE the firm wants the client's papers. Policy,
# not statute -- the one number to change. See the module docstring for why it
# is 21 and not the 28 the basis document proposed.
MATERIALS_LEAD_DAYS = 21

# Which month the return is due in, by IRC 6072. The day is always the 15th.
_DUE_MONTH = {
    "partnership_1065": 3,
    "s_corp_1120s": 3,
    "individual_1040": 4,
    "c_corp_1120": 4,
}

# An extension is six months, so the month rolls and the 15th holds.
_EXTENSION_MONTHS = 6

RETURN_TYPES = tuple(_DUE_MONTH)


def _fixed_federal_holidays(year: int) -> set[date]:
    """The fixed-date federal holidays that can land on or beside 15 March/April.

    Deliberately NOT the whole federal calendar. Only a holiday that can fall on
    or immediately after one of our four dates can move one, and listing the
    rest would be code nobody can check. New Year's Day and Independence Day are
    here because the observed-shift logic is the same and a reader looking for
    them should find them rather than wonder.
    """
    fixed = {date(year, 1, 1), date(year, 7, 4), date(year, 12, 25)}
    observed: set[date] = set()
    for day in fixed:
        observed.add(day)
        if day.weekday() == 5:            # Saturday -> observed Friday
            observed.add(day - timedelta(days=1))
        elif day.weekday() == 6:          # Sunday -> observed Monday
            observed.add(day + timedelta(days=1))
    return observed


def emancipation_day(year: int) -> date:
    """When DC observes Emancipation Day. 16 April, shifted off a weekend."""
    day = date(year, 4, 16)
    if day.weekday() == 5:                # Saturday -> observed Friday the 15th
        return day - timedelta(days=1)
    if day.weekday() == 6:                # Sunday -> observed Monday the 17th
        return day + timedelta(days=1)
    return day


def is_closed(day: date) -> bool:
    """Is this a day a return cannot be due on, under section 7503?"""
    if day.weekday() >= 5:                # Saturday or Sunday
        return True
    if day == emancipation_day(day.year):
        return True
    return day in _fixed_federal_holidays(day.year)


def next_business_day(day: date) -> date:
    """The first day that is not a weekend or a legal holiday, section 7503.

    Loops rather than adding one day, because two closed days can sit together:
    a Saturday 15 April with Emancipation Day observed on the Friday before it
    pushes past the weekend AND past Monday the 17th.
    """
    while is_closed(day):
        day += timedelta(days=1)
    return day


def filing_date(return_type: str, tax_year: int, *, extended: bool = False) -> date:
    """When a calendar-year return for ``tax_year`` is due, section 7503 applied.

    ``tax_year`` is the YEAR THE RETURN IS FOR, not the year it is filed. The
    2026 return is due in 2027. This repo has been bitten by that distinction
    before -- `_season` means the tax year -- so the argument is named for it.
    """
    if return_type not in _DUE_MONTH:
        raise KeyError(
            f"no filing date for {return_type!r}; known types are "
            + ", ".join(sorted(_DUE_MONTH))
        )
    month = _DUE_MONTH[return_type] + (_EXTENSION_MONTHS if extended else 0)
    return next_business_day(date(tax_year + 1, month, 15))


def materials_deadline(return_type: str, tax_year: int, *,
                       lead_days: int = MATERIALS_LEAD_DAYS) -> date:
    """When the client's papers must be in hand. Policy, off the filing date.

    NOT moved off a weekend. The filing date is a statutory deadline and the law
    moves it; this is a date the firm asks for, and asking for papers by a
    Saturday is a thing a firm may perfectly well do. Moving it would also break
    the four dates already sent to clients.
    """
    return filing_date(return_type, tax_year) - timedelta(days=lead_days)


@dataclass(frozen=True)
class Milestone:
    """One dated thing in a season, and what it is."""

    when: date
    what: str
    return_type: str
    kind: str          # "materials" | "filing" | "extended"

    @property
    def statutory(self) -> bool:
        """Whether missing it is a legal problem or a firm problem."""
        return self.kind in ("filing", "extended")


def season(tax_year: int) -> list[Milestone]:
    """Every date in one tax year's season, earliest first."""
    out: list[Milestone] = []
    for rt in RETURN_TYPES:
        out.append(Milestone(materials_deadline(rt, tax_year),
                             "papers due in", rt, "materials"))
        out.append(Milestone(filing_date(rt, tax_year), "return due", rt, "filing"))
        out.append(Milestone(filing_date(rt, tax_year, extended=True),
                             "extended return due", rt, "extended"))
    return sorted(out, key=lambda m: (m.when, m.return_type, m.kind))
