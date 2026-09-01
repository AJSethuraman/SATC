"""The tax calendar. Four dates a season, and the firm's year hangs off them.

WHAT THIS REPLACES. `registry/firm-settings.yaml` carried four materials
deadlines typed by hand, under a comment telling a PERSON to "CHECK THIS AGAINST
THE IRS CALENDAR each season before rolling it forward". They were right for
2026 and would have been wrong the first year a deadline shifted -- silently,
in a letter already sent.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
import yaml

import deadlines as taxcal
from settings import SETTINGS


# -- the assertion that outranks the rule ------------------------------------

def test_the_derived_deadlines_are_the_ones_the_firm_already_published():
    """THE ONE THAT DECIDES THE RULE. Four materials deadlines are already in
    `firm-settings.yaml` and have already been said to clients. A rule that
    computes different dates is not a better rule, it is a rule that contradicts
    a letter somebody has read.

    This is also how the rule was chosen. `docs/pricing-and-deadlines-basis.md`
    proposes "filing date minus four weeks, moved to the nearest Monday" and
    ends with "one rule to approve". Nobody approved it, and the dates on file
    are minus TWENTY-ONE DAYS unshifted. The file won.
    """
    settings = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    published = settings["materials_deadlines"]["2026"]
    assert published, "no published deadlines to check against — examined nothing"

    for return_type, said in published.items():
        want = datetime.strptime(said, "%B %d, %Y").date()
        got = taxcal.materials_deadline(return_type, 2026)
        assert got == want, (
            f"{return_type}: the software computes {got}, the firm told clients "
            f"{want}. One of them is wrong and it is not the letter.")


# -- section 6072: which month ------------------------------------------------

def test_entities_are_due_a_month_before_individuals():
    """IRC 6072 — the 15th day of the third month for partnerships and S
    corporations, the fourth for individuals and C corporations."""
    assert taxcal.filing_date("partnership_1065", 2026) == date(2027, 3, 15)
    assert taxcal.filing_date("s_corp_1120s", 2026) == date(2027, 3, 15)
    assert taxcal.filing_date("individual_1040", 2026) == date(2027, 4, 15)
    assert taxcal.filing_date("c_corp_1120", 2026) == date(2027, 4, 15)


def test_the_tax_year_is_not_the_filing_year():
    """The 2026 return is due in 2027. This repo has been bitten by that
    distinction before — `_season` means the tax year — so the argument is named
    for it and this test says so out loud."""
    assert taxcal.filing_date("individual_1040", 2026).year == 2027


def test_an_extension_is_six_months_and_keeps_the_fifteenth():
    assert taxcal.filing_date("partnership_1065", 2026, extended=True) == date(2027, 9, 15)
    assert taxcal.filing_date("individual_1040", 2026, extended=True) == date(2027, 10, 15)


def test_a_return_type_nobody_configured_refuses_rather_than_guessing():
    """A silent wrong date is worse than a missing one."""
    with pytest.raises(KeyError, match="no filing date"):
        taxcal.filing_date("form_990", 2026)


# -- section 7503: the shifts, against dates that really happened ------------

def test_the_2022_individual_deadline_was_the_eighteenth():
    """MEASURED AGAINST REALITY, not against my own arithmetic. 15 April 2022
    was a Friday and DC observed Emancipation Day that same day, so the deadline
    moved to Monday 18 April — which is what the IRS announced."""
    assert taxcal.filing_date("individual_1040", 2021) == date(2022, 4, 18)


def test_the_2017_individual_deadline_was_the_eighteenth():
    """15 April 2017 was a Saturday and Emancipation Day was observed on Monday
    the 17th, so the deadline moved to Tuesday the 18th. Two closed days in a
    row — the case a naive "add one day" gets wrong."""
    assert taxcal.filing_date("individual_1040", 2016) == date(2017, 4, 18)


def test_a_weekend_moves_an_entity_deadline_too():
    """15 March 2026 is a Sunday. Emancipation Day cannot help here — this is
    the plain weekend rule, and it applies to the March dates as much as April."""
    assert taxcal.filing_date("s_corp_1120s", 2025) == date(2026, 3, 16)


def test_emancipation_day_moves_off_a_weekend_in_both_directions():
    assert taxcal.emancipation_day(2022) == date(2022, 4, 15)   # 16th is a Saturday
    assert taxcal.emancipation_day(2017) == date(2017, 4, 17)   # 16th is a Sunday
    assert taxcal.emancipation_day(2027) == date(2027, 4, 16)   # 16th is a Friday


def test_a_year_where_nothing_shifts_shifts_nothing():
    """The failure direction nobody checks. A rule that moves dates correctly
    but moves them when it should not is just as wrong."""
    assert taxcal.filing_date("individual_1040", 2026) == date(2027, 4, 15)
    assert taxcal.filing_date("partnership_1065", 2026) == date(2027, 3, 15)


# -- the materials deadline is policy, not statute ---------------------------

def test_at_a_three_week_lead_the_deadline_is_always_a_weekday_anyway():
    """WHY THERE IS NO WEEKEND SHIFT ON THIS DATE, and it is structure rather
    than luck. Twenty-one days is exactly three weeks, so the materials deadline
    inherits the filing date's weekday — and section 7503 has already made that
    a business day. Across 2024-2040 not one lands on a weekend.

    Found by mutation testing: making this date shift off weekends changed
    nothing, and the test that claimed to cover it had picked a Monday. It also
    carried `assert got.weekday() == 0 or True`, which asserts nothing at all —
    exactly the kind of line the test audit exists to find.
    """
    for tax_year in range(2024, 2041):
        for return_type in taxcal.RETURN_TYPES:
            got = taxcal.materials_deadline(return_type, tax_year)
            assert got.weekday() < 5, f"{return_type} {tax_year} -> {got}"


def test_a_lead_that_is_not_whole_weeks_can_land_on_a_saturday_and_stays_there():
    """AND THEN THE CHOICE BECOMES VISIBLE. Change the lead off a multiple of
    seven and the deadline can fall on a weekend. It is left there: the filing
    date is statutory and the law moves it, but this is a date the FIRM asks
    for, and asking for papers by a Saturday is a thing a firm may do."""
    got = taxcal.materials_deadline("individual_1040", 2026, lead_days=19)
    assert got == date(2027, 3, 27)
    assert got.weekday() == 5, "27 March 2027 is a Saturday; it must stay one"


def test_the_lead_time_is_one_number():
    """Changing the policy must be one edit, not four dates to re-invent."""
    assert taxcal.MATERIALS_LEAD_DAYS == 21
    tighter = taxcal.materials_deadline("individual_1040", 2026, lead_days=14)
    assert tighter == date(2027, 4, 1)


# -- the season ---------------------------------------------------------------

def test_a_season_is_every_date_in_order():
    got = taxcal.season(2026)
    assert got, "a season with no dates in it examined nothing"
    assert got == sorted(got, key=lambda m: (m.when, m.return_type, m.kind))
    assert {m.kind for m in got} == {"materials", "filing", "extended"}


def test_a_missed_statutory_date_is_marked_apart_from_a_missed_firm_date():
    """Missing a filing date is a legal problem. Missing a materials deadline is
    a firm problem. A board that shows them the same way teaches the reader to
    treat both as soft."""
    got = {m.kind: m.statutory for m in taxcal.season(2026)}
    assert got == {"materials": False, "filing": True, "extended": True}


# -- the thing that compares the two answers ---------------------------------

def test_a_season_nobody_typed_is_derived_rather_than_refused():
    """THE ANNUAL CHORE, GONE. This used to raise: a season missing from
    `firm-settings.yaml` stopped every document. Now the statute answers, so a
    new year needs no edit and the first season a deadline shifts for a weekend
    or Emancipation Day, it shifts here too."""
    import settings as st

    got = st._materials_deadline("2030", "individual_1040", {})
    assert got == "March 25, 2031"     # 15 Apr 2031 is a Tuesday; minus 21 days


def test_a_typed_date_wins_over_the_rule():
    """A letter already read is not corrected by a better rule."""
    import settings as st

    said = {"individual_1040": "March 25, 2027"}
    assert st._materials_deadline("2026", "individual_1040", said) == "March 25, 2027"


def test_a_typed_date_that_disagrees_with_the_statute_is_refused():
    """THE POINT OF THE WHOLE THING, and the tenet the week produced: a claim in
    one place, behaviour in another, and now something comparing them.

    A disagreement means the file is stale or the policy moved. Resolving it
    silently — either way — is how a client gets a date nobody chose.
    """
    import settings as st

    stale = {"individual_1040": "March 18, 2027"}    # last year's, rolled wrong
    with pytest.raises(ValueError, match="does not agree with the statute"):
        st._materials_deadline("2026", "individual_1040", stale)


def test_the_refusal_shows_both_dates_and_the_arithmetic():
    """A refusal that does not say which date to fix is a puzzle, not a message."""
    import settings as st

    with pytest.raises(ValueError) as caught:
        st._materials_deadline("2026", "individual_1040",
                               {"individual_1040": "March 18, 2027"})
    said = str(caught.value)
    assert "March 18, 2027" in said and "March 25, 2027" in said
    assert "2027-04-15" in said and "21 days" in said


def test_a_date_is_written_the_way_the_firm_writes_it():
    """"March 5, 2027", never "March 05, 2027". The templates merge this
    straight onto a page a client reads."""
    import settings as st

    assert st._spoken(date(2027, 3, 5)) == "March 5, 2027"
    assert st._spoken(date(2027, 3, 25)) == "March 25, 2027"
