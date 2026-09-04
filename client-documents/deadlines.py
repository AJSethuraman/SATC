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
from pathlib import Path

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


# ── what is next, for the line at the top of every screen ─────────────────
#
# THE DATE HALF ONLY, AND THAT IS THE FIRM'S DECISION. Claude Design's chrome
# carried "next: 15 September ... 4 clients due before it". The date is
# derived from the statute here and is safe; the COUNT is not. `board()` below
# emits `materials` and `filing` milestones and no `extended` one, so a count
# beside an extension deadline would have read zero on the very date it named
# -- a number nobody could check, at the top of every screen, which is exactly
# the shape §0 of the tenets is a list of. The count goes up when the board
# counts extensions and not before (firm, 3 September 2026).


def _plain_words() -> dict[str, str]:
    """`{return type: what the firm calls that client}`, plural.

    READ OUT OF THE INTERVIEW'S OWN OPTION LABELS rather than typed here. A
    second list of names for the same four things is a second list to keep in
    step, and this repository's own rule for that is to derive one from the
    other (S6). `test_deadlines` holds the two files together, so a label the
    firm rewords carries through and a form number either side gains without
    the other fails.
    """
    import yaml

    spec = yaml.safe_load(
        (Path(__file__).resolve().parent / "registry" / "interview.yaml")
        .read_text(encoding="utf-8")) or {}
    out: dict[str, str] = {}
    for section in spec.get("sections") or []:
        for question in section.get("questions") or []:
            if question.get("id") != "federal_form":
                continue
            for option in question.get("options") or []:
                kind = _FORM_TO_TYPE.get(str(option.get("value", "")).upper())
                label = str(option.get("label", ""))
                if kind and "\u2014" in label:
                    out[kind] = label.split("\u2014", 1)[1].strip() + "s"
    return out


def who(return_type: str) -> str:
    """The plural noun for one return type, or the key when we have no word.

    Falling back to the key is deliberate: a form number the interview stops
    offering would otherwise vanish off the chrome silently, and a reader
    seeing `s_corp_1120s` will ask, which is the outcome to want.
    """
    return _plain_words().get(return_type, return_type)


def next_dates(today: date | None = None) -> list[Milestone]:
    """Every milestone falling on the next date the firm's calendar carries.

    A LIST, BECAUSE TWO RETURN TYPES SHARE MOST DATES. 15 March is partnerships
    and S corporations; 15 April is individuals and C corporations. Naming one
    of the pair on the chrome would be true and misleading.

    Seasons overlap -- an extended 1065 for one tax year is due five months
    after the next year's papers are asked for -- so this looks across the
    three tax years that can still have a live date, rather than assuming
    which season it is.
    """
    now = today or date.today()
    soonest: list[Milestone] = []
    for year in (now.year - 2, now.year - 1, now.year):
        for milestone in season(year):
            if milestone.when < now:
                continue
            if not soonest or milestone.when < soonest[0].when:
                soonest = [milestone]
            elif milestone.when == soonest[0].when:
                soonest.append(milestone)
    return soonest


def next_line(today: date | None = None) -> tuple[date, str] | None:
    """`(the date, what falls on it)` for the chrome, or None.

    None when nothing is ahead, which happens only if the rule stops
    producing dates -- and an empty line is the right answer to that, not a
    guessed one.
    """
    ahead = next_dates(today)
    if not ahead:
        return None
    kinds = {m.what for m in ahead}
    # One date can carry two different things -- papers due in for one return
    # type and a filing deadline for another. Say both rather than picking.
    parts = []
    for what in sorted(kinds):
        names = sorted({who(m.return_type) for m in ahead if m.what == what})
        if len(names) > 1:
            names = [", ".join(names[:-1]) + " and " + names[-1]]
        parts.append(f"{what} for {names[0]}")
    return ahead[0].when, "; ".join(parts)


# ── the board: the season across the whole book ───────────────────────────
#
# EVERYTHING THIS SOFTWARE DOES WELL HAPPENS TO ONE ENGAGEMENT AT A TIME.
# Nothing looked across the book and said what season it is. That is the thing
# a person otherwise holds in their head through February, and the thing that
# makes extensions a decision rather than a scramble.

@dataclass(frozen=True)
class Due:
    """One engagement against one date."""

    ref: str
    client: str
    return_type: str
    when: date
    what: str
    kind: str
    days: int | None          # None when we cannot tell — never a zero

    @property
    def overdue(self) -> bool:
        return self.days is not None and self.days < 0

    @property
    def statutory(self) -> bool:
        return self.kind in ("filing", "extended")


# How an engagement's federal form answers map onto a filing date. The
# interview asks `federal_form`; the settings key is spelled differently, and
# the two have to meet somewhere.
_FORM_TO_TYPE = {
    "1040": "individual_1040",
    "1065": "partnership_1065",
    "1120S": "s_corp_1120s",
    "1120": "c_corp_1120",
}

# THE KEY A REAL RECORD ACTUALLY CARRIES. A composed record has no
# `FederalForm` on it: `intake.compose_record` reads the interview's
# `federal_form` answer, writes `_return_type` in the rest of the codebase's
# vocabulary ("individual", "s_corp", ...), and the form number itself only
# survives as prose inside `FederalReturns` ("Form 1040 with Schedules B and
# D"). Reading `FederalForm` here therefore placed nothing at all: every
# engagement the interview created came back unplaced, and the board said the
# season was empty. That is this file's own docstring bug wearing a new hat --
# a claim in one place, the behaviour in another, and nothing comparing them
# (S31). The comparing thing is `test_deadlines.py::test_every_return_type_the
# _interview_can_write_is_placeable`, which fails if either vocabulary grows a
# member the other does not have.
_KIND_TO_TYPE = {
    "individual": "individual_1040",
    "partnership": "partnership_1065",
    "s_corp": "s_corp_1120s",
    "c_corp": "c_corp_1120",
}


# ── what can be a tax year at all ──────────────────────────────────────────
#
# THE REFUND CLIFF IS THREE YEARS; THE FILING WINDOW IS NOT.
#
# IRC 6511(a): a claim for credit or refund must be filed within 3 years of
# filing the return, or 2 years of paying the tax, whichever is later. An
# amended return asking for money back IS such a claim, so three years is the
# real limit on a 1040-X that is worth filing.
#
# But there is NO statute of limitations on an unfiled return -- 6501's
# assessment clock starts when a return is filed, so for a year the client
# never filed it never started. The firm does that work, and the interview asks
# "Any unfiled years?" precisely because it does. A hard three-year floor here
# would refuse real engagements.
#
# THE FIRM SET THE WINDOW AT THREE, 3 September 2026, having been shown the
# distinction above and chosen anyway. So the input rule IS the refund window
# here, deliberately, and this is what that costs:
#
#   an unfiled 2019 return, prepared in 2026, is REFUSED at the question.
#
# That work still exists. It goes through `unfiled_years` -- the free-text
# question in the history section -- rather than by opening an engagement dated
# to a year this refuses. If the firm starts taking that work often enough to
# want its own engagement per year, this constant is the thing to revisit, and
# raising it is a one-line change with tests that name the consequence.
#
# One forward is the return prepared in December for the year just ending.
# Confirmed against irs.gov, after `0` put a return due 0001-04-17 at the top
# of the board.
REFUND_YEARS = 3
YEARS_BACK = REFUND_YEARS
YEARS_FORWARD = 1


def plausible_year(value, today: date | None = None) -> bool:
    """Could this be a tax year the firm would actually work on?

    Deliberately not "is this an int". `0` is an int and produced a return due
    `0001-04-17` that sorted to the TOP of the board -- soonest first -- with
    `unplaced` empty and nothing reporting a problem. A number that parses is
    not the same as a year that means anything.
    """
    try:
        year = int(str(value).strip())
    except (TypeError, ValueError):
        return False
    now = (today or date.today()).year
    return now - YEARS_BACK <= year <= now + YEARS_FORWARD


def return_type_for(record: dict) -> str | None:
    """Which filing date an engagement's record falls under, or None.

    NONE RATHER THAN A GUESS. An engagement whose form we cannot read has an
    unknown deadline, and putting it under 15 April because most returns are
    is how a 1065 misses 15 March.
    """
    kind = str(record.get("_return_type") or "").strip()
    if kind in _KIND_TO_TYPE:
        return _KIND_TO_TYPE[kind]
    form = str(record.get("FederalForm") or record.get("federal_form") or "").strip()
    form = form.replace("Form ", "").replace("form ", "").strip()
    return _FORM_TO_TYPE.get(form.upper())


def board(records: list[tuple[str, dict]], *, today: date | None = None,
          within_days: int | None = None) -> tuple[list[Due], list[str]]:
    """``(what is due, refs we could not place)``, soonest first.

    THE SECOND RETURN VALUE IS THE POINT AS MUCH AS THE FIRST. A board that
    silently drops the engagements it could not read is a board that says the
    season is quieter than it is -- which is this project's oldest bug wearing
    a new hat. Every ref that could not be placed comes back so the caller can
    print it, per S2: a check reports its denominator.
    """
    now = today or date.today()
    due: list[Due] = []
    unplaced: list[str] = []

    for ref, record in records:
        return_type = return_type_for(record)
        tax_year = record.get("TaxYear") or record.get("tax_year")
        # `plausible_year` rather than a bare `int()`: both "unreadable" and
        # "readable but impossible" have to land in `unplaced`, and only the
        # first one used to.
        tax_year = int(str(tax_year).strip()) if plausible_year(tax_year) else None
        if return_type is None or tax_year is None:
            unplaced.append(ref)
            continue

        client = str(record.get("ClientFullName") or record.get("EntityName")
                     or "(no name)")
        # A YEAR THAT PARSES IS NOT A YEAR THAT WORKS. `int()` above accepts
        # 99999 and -5 happily, and `date(year + 1, ...)` then raises
        # `ValueError: year is out of range` -- out of THIS function, taking
        # the whole board with it. Every readable engagement disappeared
        # because one record had a typo in it, which is the failure the
        # docstring above says `unplaced` exists to prevent, arriving by the
        # one route that was not guarded.
        #
        # Found 3 September 2026: `tax_year` is free text in the interview, so
        # this was one keystroke away at all times. That entry check is fixed
        # too; this stays because the board must degrade to one named
        # engagement no matter what reaches it.
        try:
            milestones = (
                Milestone(materials_deadline(return_type, tax_year),
                          "papers due in", return_type, "materials"),
                Milestone(filing_date(return_type, tax_year),
                          "return due", return_type, "filing"),
            )
        except (ValueError, OverflowError):
            unplaced.append(ref)
            continue

        for milestone in milestones:
            days = (milestone.when - now).days
            if within_days is not None and days > within_days:
                continue
            due.append(Due(ref=ref, client=client, return_type=return_type,
                           when=milestone.when, what=milestone.what,
                           kind=milestone.kind, days=days))

    due.sort(key=lambda d: (d.when, d.ref, d.kind))
    return due, unplaced
