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


# ── the board ────────────────────────────────────────────────────────────────
#
# EVERYTHING ELSE IN THIS SOFTWARE ACTS ON ONE ENGAGEMENT. Nothing looked across
# all of them and said what season it is — the thing a person otherwise holds in
# their head through February.

def _rec(name, form=None, year=2026):
    out = {"ClientFullName": name, "TaxYear": year}
    if form:
        out["FederalForm"] = form
    return out


def test_the_board_puts_each_engagement_under_its_own_filing_date():
    """A 1065 is due 15 March and a 1040 is due 15 April. Sorting the book by
    one date because most returns use it is how the entity work gets missed."""
    due, _ = taxcal.board(
        [("2026-0001", _rec("Riverbend Partners", "1065")),
         ("2026-0002", _rec("Marcus Ellwood", "1040"))],
        today=date(2027, 2, 18))
    filings = {d.ref: d.when for d in due if d.kind == "filing"}
    assert filings == {"2026-0001": date(2027, 3, 15),
                       "2026-0002": date(2027, 4, 15)}


def test_an_engagement_with_no_form_is_named_rather_than_dropped():
    """THE POINT OF THE SECOND RETURN VALUE. A board that silently omits what it
    could not read says the season is quieter than it is — this project's oldest
    bug wearing a new hat. An unreadable engagement has an UNKNOWN deadline."""
    due, unplaced = taxcal.board(
        [("2026-0001", _rec("Marcus Ellwood", "1040")),
         ("2026-0009", {"ClientFullName": "Half-Finished Sitting"})],
        today=date(2027, 2, 18))
    assert unplaced == ["2026-0009"]
    assert all(d.ref == "2026-0001" for d in due)


def test_a_form_the_calendar_does_not_know_is_not_assumed_to_be_a_1040():
    """FOUND BY MUTATION TESTING, and the test above did not catch it. That one
    uses a record with no year either, so it lands in `unplaced` for the wrong
    reason and a form defaulting to `individual_1040` slipped straight past it.

    A 990 or a 706 under 15 April is a wrong deadline stated confidently, which
    is worse than an unknown one stated plainly.
    """
    due, unplaced = taxcal.board(
        [("2026-0007", _rec("A Foundation", "990"))], today=date(2027, 2, 18))
    assert unplaced == ["2026-0007"]
    assert due == []
    assert taxcal.return_type_for({"FederalForm": "990"}) is None


def test_an_unreadable_year_is_not_guessed_either():
    """A form with no tax year cannot be placed. Assuming the current one is a
    guess about a deadline, which is the one kind of guess this must not make."""
    _, unplaced = taxcal.board(
        [("2026-0004", {"ClientFullName": "No Year", "FederalForm": "1040"})],
        today=date(2027, 2, 18))
    assert unplaced == ["2026-0004"]


def test_a_form_spelled_the_interview_way_is_read_too():
    """The interview answers `federal_form`; the record carries `FederalForm`.
    A board that reads only one of them shows half the book."""
    due, unplaced = taxcal.board(
        [("2026-0002", {"ClientFullName": "M E", "federal_form": "1040",
                        "tax_year": 2026})],
        today=date(2027, 2, 18))
    assert not unplaced and due


def test_a_date_already_past_is_overdue_not_hidden():
    """Sorting it off the bottom of the list is the same as not saying it."""
    due, _ = taxcal.board([("2026-0001", _rec("Riverbend Partners", "1065"))],
                          today=date(2027, 3, 20))
    past = [d for d in due if d.overdue]
    assert len(past) == 2, "both the papers date and the filing date are behind us"
    assert all(d.days < 0 for d in past)


def test_a_window_hides_the_far_future_and_not_the_past():
    """`--within 40` is "what do I need to think about", and something already
    overdue is exactly that. Filtering it out with the far future would be the
    wrong half."""
    due, _ = taxcal.board([("2026-0001", _rec("Riverbend Partners", "1065")),
                           ("2026-0002", _rec("Marcus Ellwood", "1040"))],
                          today=date(2027, 3, 20), within_days=10)
    assert any(d.overdue for d in due), "the overdue rows were filtered away"
    assert not any(d.when == date(2027, 4, 15) for d in due)


def test_a_statutory_date_is_distinguishable_from_a_firm_one():
    """Missing a filing date is a legal problem; missing a papers date is a firm
    problem. A board that shows them identically teaches the reader to treat
    both as soft, and it is the statutory one that cannot be soft."""
    due, _ = taxcal.board([("2026-0002", _rec("Marcus Ellwood", "1040"))],
                          today=date(2027, 2, 18))
    kinds = {d.kind: d.statutory for d in due}
    assert kinds == {"materials": False, "filing": True}


def test_a_record_the_interview_actually_composed_lands_on_the_board():
    """THE TEST THAT WAS MISSING. Every test above builds its own record with a
    `FederalForm` key on it. No record in this system has ever had that key: the
    interview writes `_return_type`, and the form number survives only as prose
    inside `FederalReturns`. So the board placed nothing at all in real use --
    `season` read one engagement, said "nothing due", and listed it as unplaced
    for want of "no federal form or no tax year" that were both plainly
    answered. A hand-built fixture cannot catch that. This one goes through
    `intake.compose_record`, which is what the running system calls."""
    import intake
    record = intake.compose_record({
        "federal_form": "1040", "tax_year": "2026",
        "client_full_name": "Marcus Ellwood", "filing_status": "single",
    })
    assert taxcal.return_type_for(record) == "individual_1040", (
        "a record the interview composed could not be read back")
    due, unplaced = taxcal.board([("2026-0001", record)], today=date(2027, 2, 15))
    assert unplaced == [], "the interview's own record came back unplaceable"
    assert [d.when for d in due] == [date(2027, 3, 25), date(2027, 4, 15)]


def test_every_return_type_the_interview_can_write_is_placeable():
    """THE THIRD THING (S31). Two vocabularies name the same four returns: the
    interview's `_return_type` ("individual") and the settings key
    ("individual_1040"). Nothing compared them, which is how one could be read
    for the other for as long as it was. Adding a fifth form to either side
    now fails here rather than silently dropping that client off the board."""
    import intake
    assert set(intake.RETURN_TYPE.values()) == set(taxcal._KIND_TO_TYPE), (
        "a return type the interview can write has no filing date")
    assert set(taxcal._KIND_TO_TYPE.values()) == set(taxcal.RETURN_TYPES), (
        "a filing date exists that no interview answer reaches")
    for form, kind in intake.RETURN_TYPE.items():
        composed = {"_return_type": kind}
        assert taxcal.return_type_for(composed) == taxcal._FORM_TO_TYPE[form], (
            f"{form} and {kind} disagree about which date they are under")


def test_a_year_that_parses_but_cannot_be_a_year_does_not_take_the_board_down():
    """F3. `int("99999")` succeeds; `date(100000, 4, 15)` does not.

    The ValueError escaped `board()` entirely, so ONE engagement with a typo in
    its year made the whole calendar raise — and every readable engagement
    disappeared with it. That is precisely the failure this function's docstring
    says `unplaced` exists to prevent, arriving by the one route that was not
    guarded.

    `0` is here too and is the nastier one: it does not raise. It produced
    `papers due 0001-03-27` and `return due 0001-04-17`, which sorted to the TOP
    of the board — soonest first — with `unplaced` empty and nothing reporting a
    problem.
    """
    good = ("2026-0001", _rec("Marcus Ellwood", "1040"))
    for typo in ("99999", "-5", "0", "x"):
        bad = ("2026-0002", {"ClientFullName": "Typo", "FederalForm": "1040",
                             "TaxYear": typo})
        due, unplaced = taxcal.board([good, bad], today=date(2026, 2, 18))
        assert unplaced == ["2026-0002"], f"{typo!r} should be named, not dropped"
        assert due, f"{typo!r} took the whole board down"
        assert all(d.ref == "2026-0001" for d in due)


def test_the_year_window_is_the_typo_guard_and_not_the_refund_window():
    """IRC 6511(a) caps a REFUND claim at three years. Filing is not capped.

    Recorded as a test because the two numbers are easy to conflate, and
    conflating them would refuse an unfiled-year engagement the firm does take.
    """
    assert taxcal.REFUND_YEARS == 3
    assert taxcal.YEARS_BACK > taxcal.REFUND_YEARS

    today = date(2026, 6, 1)
    assert taxcal.plausible_year(2026, today)
    assert taxcal.plausible_year(2027, today), "a return prepared in December"
    assert taxcal.plausible_year(2019, today), "the oldest unfiled year we accept"
    assert not taxcal.plausible_year(2018, today)
    assert not taxcal.plausible_year(2028, today)
    for nonsense in ("x", "", None, "0", "-5", "99999", 0, -5):
        assert not taxcal.plausible_year(nonsense, today), f"{nonsense!r}"
