"""The catalog: every series traceable to the research, and nothing rated."""
import pathlib

from threshold_engine.macro.catalog import (BY_KEY, CARE, CARE_DERIVED, CARE_NOT_READ, CORE, DERIVED, DERIVED_BY_KEY,
                                            FRED_PD, HIGHER, HOUSEHOLD_DEBT, LOWER, NOT_YET, PICK, READ, SERIES,
                                            STATES)

REPORT = (pathlib.Path(__file__).resolve().parents[1] / "docs" / "macro" / "reports"
          / "Macro risk indicators for lending.md")


def test_keys_are_unique():
    assert len(BY_KEY) == len(SERIES)


def test_every_series_names_its_publisher_licence_and_start():
    for s in SERIES:
        assert s.publisher and s.licence and s.starts and s.unit, s.key
        assert s.group in ("consumer", "commercial", "both"), s.key
        assert s.frequency in ("daily", "weekly", "monthly", "quarterly"), s.key


def test_every_series_cites_a_section_the_report_really_has():
    text = REPORT.read_text("utf-8").replace("–", "-")
    for s in SERIES + DERIVED:
        assert "## " + s.report in text, (s.key, s.report)


def test_a_direction_of_stress_is_only_ever_what_the_research_says_and_nothing_is_left_to_a_setting():
    # The research's direction is a recorded fact, shown as one. No note still says the firm sets it: nothing
    # does any more (22 Oct 2026).
    for s in SERIES + DERIVED:
        assert s.stress in (HIGHER, LOWER, None), s.key
        assert "firm sets" not in s.note and "the firm" not in s.note, s.key


def test_all_fifty_states_and_dc():
    assert len(STATES) == 51 and len(set(STATES)) == 51
    assert all(("unemployment_" + st.lower()) in BY_KEY for st in STATES)


def test_every_series_read_says_how_its_change_is_counted_and_whether_its_level_is_read():
    for s in READ:
        assert s.change_in in ("points", "percent"), s.key
        if s.position:      # its place in its history is not read: says why, and is a level that grows
            assert "says nothing" in s.position and s.change_in == "percent", s.key


def test_a_derived_reading_is_built_from_two_series_the_catalog_pulls():
    for d in DERIVED:
        assert len(d.inputs) == 2 and all(k in BY_KEY for k in d.inputs), d.key
        assert d.key not in BY_KEY and d.how, d.key
    inputs = [s for s in SERIES if not s.read_alone]
    assert {s.key for s in inputs} == {"income_per_person", "treasury_10y", "wages_eci_nsa", "cpi_nsa"}
    assert len(READ) == len(SERIES) - len(inputs) + len(DERIVED)


def test_the_usable_with_care_group_says_why_each_needs_care_and_is_kept_apart_from_the_core():
    assert CARE and all(s.care and s.stress is None and s.read_alone for s in CARE + CARE_DERIVED)
    assert not {s.key for s in CARE + CARE_DERIVED} & {i.key for i in CORE}
    assert [s for s in SERIES if s.care] == CARE and READ == CORE + PICK + CARE + CARE_DERIVED


def test_every_other_delinquency_measure_is_read_for_the_dashboard_and_leads_found_only():
    # The firm, 23 Oct 2026: "i want to bring in all measures - like 30+, 30+ non accrual, 30-89, 90+, 90+ non
    # accrual, etc", shown only in the Dashboard's pick list and on Leads found ("Pick list + screen").
    assert len(PICK) == 40 and all(s.source == "fdic" and s.pick_only and s.read_alone for s in PICK)
    assert not {s.key for s in PICK} & {i.key for i in CORE}
    assert {s.source_id.split("_delinquency-")[1] for s in PICK} == {
        "30-89_quarter-end", "90-plus-accruing_quarter-end", "nonaccrual_quarter-end",
        "90-plus-incl-nonaccrual_quarter-end", "30-plus-accruing_quarter-end"}


def test_the_licensed_part_of_the_group_is_named_with_its_reason():
    named = dict(CARE_NOT_READ)
    for what in ("University of Michigan consumer sentiment", "Atlanta Fed home ownership affordability"):
        assert named[what].startswith("licensed")
    assert not any("Michigan" in s.publisher for s in CARE)
    # A licence that asks for wording gets it carried with the series.
    sce = next(s for s in CARE if s.source == "nyfed_sce")
    assert sce.credit.startswith("Source: Survey of Consumer Expectations") and "FRBNY disclaims" in sce.credit


def test_the_prime_rate_is_read_daily_from_fred_in_points():
    # The firm, 22 Oct 2026: "how do we not have the prime interest rate". FRED's page, read that day: DPRIME,
    # Board of Governors H.15, daily from 1955-08-04, Public Domain: Citation Requested.
    p = BY_KEY["prime_rate"]
    assert (p.source, p.source_id, p.frequency, p.starts, p.change_in) == ("fred", "DPRIME", "daily", "1955-08-04",
                                                                          "points")
    assert p.licence.endswith("Public Domain: Citation Requested") and not p.position and not p.care
    assert p in CORE


def test_household_debt_is_every_type_the_ny_fed_reports_with_its_attribution():
    # The firm, 22 Oct 2026: "household as a graph ... split between as it is literally reported". The NY Fed's
    # terms of use (6/9/2023), read that day, name the attribution: "New York Fed Consumer Credit Panel / Equifax".
    assert [c for _, c, _ in HOUSEHOLD_DEBT] == ["Mortgage", "HE Revolving", "Auto Loan", "Credit Card",
                                                 "Student Loan", "Other", "Total"]
    for key, column, _ in HOUSEHOLD_DEBT:
        s = BY_KEY[key]
        assert (s.source, s.source_id, s.frequency, s.unit) == ("nyfed_hhdc", column, "quarterly",
                                                                 "trillions of dollars")
        assert s.credit.startswith("Source: New York Fed Consumer Credit Panel / Equifax.")
        assert "not the NY Fed's" in s.credit           # the terms ask modified content to be labelled as such
        assert s.position and s in CORE                  # balances grow: read on their change only


def test_nothing_still_waits_on_the_ny_feds_terms():
    # Its terms of use were read on 22 Oct 2026 and allow business use; a reason saying they are unconfirmed
    # would now be false.
    for _, why in NOT_YET + CARE_NOT_READ:
        assert "not confirmed (report, gaps)" not in why and "reuse terms are not confirmed" not in why


def test_the_atlanta_fed_wage_tracker_is_read_from_fred_under_freds_tag():
    # The firm, 22 Oct 2026: "Also do we note use the Atlanta fed wage growth data?" FRED's page, read that day:
    # FRBATLWGT3MMAUMHWGO, Federal Reserve Bank of Atlanta, monthly from 1997, Public Domain: Citation Requested.
    # It was left out on 21 Oct under the Atlanta Fed's own site terms; read from FRED, FRED's tag is the one that
    # applies, as for every other FRED series.
    t = BY_KEY["wage_tracker"]
    assert (t.source, t.source_id, t.frequency, t.starts, t.licence) == ("fred", "FRBATLWGT3MMAUMHWGO", "monthly",
                                                                         "1997-01", FRED_PD)
    assert t.change_in == "points" and not t.position and t in CARE        # a growth rate: its level is read
    assert t.breaks[0][0] == "2025-10"                                     # no household survey that month
    assert "Atlanta Fed wage growth tracker" not in dict(CARE_NOT_READ)


def test_new_bankruptcies_are_usable_with_care_from_the_household_debt_file_with_the_2005_law_marked():
    # The firm, 23 Oct 2026, "build it": the NY Fed's count, its full history, the 2005 law a break, no quarter
    # left out (leaving quarters out would take them out of every series).
    b = BY_KEY["new_bankruptcies"]
    assert b in CARE and b not in CORE
    assert (b.source, b.source_id, b.frequency, b.starts) == ("nyfed_hhdc", "Page 17 Data: bankruptcy", "quarterly",
                                                              "2003Q1")
    assert b.change_in == "percent" and not b.position              # a count: its level is read, its change in %
    assert b.licence == BY_KEY["household_total"].licence and b.credit == BY_KEY["household_total"].credit
    assert b.breaks[0][0] == "2005-10" and "17 October 2005" in b.breaks[0][1] and "109-8" in b.breaks[0][1]
    assert "Bankruptcy filings (US Courts)" in dict(CARE_NOT_READ)  # court filings: still no reader


def test_wages_after_inflation_are_usable_with_care_and_read_on_their_change():
    d = DERIVED_BY_KEY["real_wages_eci"]
    assert d.inputs == ("wages_eci_nsa", "cpi_nsa") and d in CARE_DERIVED and d not in CORE
    assert [BY_KEY[k].source_id for k in d.inputs] == ["CIU2020000000000I", "CPIAUCNS"]
    assert d.change_in == "percent" and "says nothing" in d.position and "0.851%" in d.note
    # private industry only, as its input is: shortened to fit its column, the title had lost it (Codex on #471)
    assert "private" in BY_KEY["wages_eci_nsa"].title and "private" in d.title


def test_each_bank_series_starts_in_its_first_quarter_in_the_build():
    # The 23 Oct 2026 build, every filer from 2006 Q1: a net charge-off rate is the past four quarters, so all banks'
    # start in 2006 Q4 and their 30+ in 2006 Q1 (Codex on #472: three loss series said 2006 Q1).
    for s in SERIES:
        if s.source == "fdic" and s.source_id.split("_")[1] == "industry":
            assert s.starts == ("2006Q4" if s.source_id.endswith("_net") else "2006Q1"), s.key
