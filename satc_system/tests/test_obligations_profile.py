"""Obligation profiles: deriving what a client owes from facts about them.

The property under test is that **nobody has to remember to create work** — and
its dangerous twin, that the system does not invent work nobody owes.
"""

from __future__ import annotations

from datetime import date

import pytest

from satc.config import ConfigError
from satc.obligations.profile import (
    ObligationProfile,
    ProfileFact,
    materialise,
    merge,
    obligation_key,
)

YES = ProfileFact("yes", basis="stated_by_client", source="2026 intake interview")
NO = ProfileFact("no", basis="stated_by_client", source="2026 intake interview")


def _individual(**kw) -> ObligationProfile:
    return ObligationProfile(client_id="SATC-001000", entity_type="INDIVIDUAL", **kw)


# --- the key ------------------------------------------------------------------

def test_the_key_distinguishes_periods_not_just_years():
    """A tax year cannot express a payroll quarter, so the key uses period_key."""
    q1 = obligation_key("C", "file", "941", "US", "2026Q1")
    q2 = obligation_key("C", "file", "941", "US", "2026Q2")
    assert q1 != q2
    assert "2026Q1" in q1


def test_the_key_is_stable_across_runs():
    a = obligation_key("C", "file", "1040", "US", "2025")
    b = obligation_key("C", "file", "1040", "US", "2025")
    assert a == b


# --- deriving duties ----------------------------------------------------------

def test_an_individual_owes_a_1040():
    duties = materialise(_individual(), 2025)
    forms = {d.form for d in duties}
    assert "1040" in forms


def test_an_individual_does_not_owe_a_partnership_return():
    forms = {d.form for d in materialise(_individual(), 2025)}
    assert "1065" not in forms
    assert "1120S" not in forms


def test_no_payroll_facts_means_no_payroll_work():
    """The dangerous direction: inventing duties fills the queue with fiction."""
    forms = {d.form for d in materialise(_individual(), 2025)}
    assert "941" not in forms
    assert "W-2" not in forms


def test_payroll_facts_generate_quarterly_941s():
    profile = _individual(runs_payroll=YES,
                          payroll_form=ProfileFact("941", basis="agency_notice",
                                                   source="IRS notice CP136, 2026-01-12"))
    duties = [d for d in materialise(profile, 2026) if d.form == "941"]
    assert len(duties) == 4
    assert {d.period_key for d in duties} == {"2026Q1", "2026Q2", "2026Q3", "2026Q4"}


def test_a_944_filer_does_not_also_get_941s():
    """941 vs 944 is IRS-ASSIGNED. Generating both would be twice wrong."""
    profile = _individual(runs_payroll=YES,
                          payroll_form=ProfileFact("944", basis="agency_notice",
                                                   source="IRS notice"))
    forms = {d.form for d in materialise(profile, 2026)}
    assert "941" not in forms


def test_estimates_are_only_owed_when_a_fact_says_so():
    without = {d.form for d in materialise(_individual(), 2026)}
    assert "1040-ES" not in without

    with_estimates = materialise(_individual(pays_estimates=YES), 2026)
    installments = [d for d in with_estimates if d.form == "1040-ES"]
    assert len(installments) == 4


def test_saying_no_is_different_from_saying_nothing():
    """An explicit no must not read the same as an unanswered question."""
    said_no = _individual(runs_payroll=NO)
    assert "941" not in {d.form for d in materialise(said_no, 2026)}
    assert said_no.runs_payroll is not None
    assert not said_no.runs_payroll.is_assumed


# --- fiscal years -------------------------------------------------------------

def test_a_fiscal_year_client_gets_fiscal_dates():
    profile = ObligationProfile(client_id="C", entity_type="CCORP",
                                fiscal_year_end=date(2026, 6, 30))
    duties = [d for d in materialise(profile, 2026) if d.form == "1120"]
    assert duties
    assert duties[0].statutory_due == date(2026, 10, 15)


def test_a_calendar_year_client_needs_no_year_end_set():
    assert _individual().year_end_for(2025) == date(2025, 12, 31)


# --- jurisdictions: the refusal -----------------------------------------------

def test_an_unsourced_jurisdiction_refuses_rather_than_defaulting():
    profile = _individual(jurisdictions=("US", "OH"))
    with pytest.raises(ConfigError) as exc:
        materialise(profile, 2025)
    message = str(exc.value)
    assert "will not fall back" in message
    assert "configs/obligations/oh.yaml" in message


def test_massachusetts_is_sourced_so_it_materialises():
    profile = _individual(jurisdictions=("US", "MA"))
    duties = materialise(profile, 2025)
    assert {"US", "MA"} <= {d.jurisdiction for d in duties}
    ma_1 = next(d for d in duties if d.jurisdiction == "MA" and d.form == "1")
    assert ma_1.due == date(2026, 4, 15)


def test_the_massachusetts_extension_condition_travels_with_the_duty():
    """An extension whose condition fails was never an extension."""
    duties = materialise(_individual(jurisdictions=("MA",)), 2025)
    ma_1 = next(d for d in duties if d.form == "1")
    assert "80%" in ma_1.extension_condition


# --- assumed facts are flagged, not hidden ------------------------------------

def test_a_duty_built_on_an_assumption_says_so():
    profile = _individual(runs_payroll=ProfileFact("yes"))    # no basis given
    assert profile.assumed_facts()
    duties = [d for d in materialise(profile, 2026) if d.form == "941"]
    assert duties and duties[0].is_assumed
    assert "runs_payroll" in duties[0].from_assumed_facts


def test_a_sourced_fact_produces_an_unflagged_duty():
    profile = _individual(runs_payroll=YES,
                          payroll_form=ProfileFact("941", basis="agency_notice",
                                                   source="IRS notice"))
    duties = [d for d in materialise(profile, 2026) if d.form == "941"]
    assert duties and not duties[0].is_assumed


# --- dates and ordering -------------------------------------------------------

def test_duties_come_back_in_deadline_order():
    profile = _individual(runs_payroll=YES, pays_estimates=YES)
    duties = materialise(profile, 2026)
    assert duties == sorted(duties, key=lambda o: (o.due, o.jurisdiction, o.form))


def test_every_materialised_duty_lands_on_a_business_day():
    from satc.obligations.calendar import is_business_day

    profile = _individual(runs_payroll=YES, pays_estimates=YES,
                          jurisdictions=("US", "MA"))
    for duty in materialise(profile, 2026):
        assert is_business_day(duty.due), f"{duty.form} {duty.period_key} -> {duty.due}"


def test_the_firm_cutoff_rides_along():
    duty = next(d for d in materialise(_individual(), 2025) if d.form == "1040")
    assert duty.documents_due == date(2026, 3, 1)


def test_days_until_counts_down_from_today():
    duty = next(d for d in materialise(_individual(), 2025) if d.form == "1040")
    assert duty.days_until(date(2026, 4, 1)) == 14
    assert duty.days_until(date(2026, 5, 1)) < 0


# --- idempotence (doctrine rule 4) -------------------------------------------

def test_materialising_twice_produces_identical_keys():
    a = materialise(_individual(runs_payroll=YES), 2026)
    b = materialise(_individual(runs_payroll=YES), 2026)
    assert [x.obligation_key for x in a] == [x.obligation_key for x in b]


def test_re_merging_the_same_period_adds_nothing():
    """"Already exists as requested" is success, never a conflict."""
    duties = materialise(_individual(runs_payroll=YES), 2026)
    merged, added = merge(duties, duties)
    assert added == 0
    assert len(merged) == len(duties)


def test_merge_adds_only_genuinely_new_duties():
    base = materialise(_individual(), 2026)
    grown = materialise(_individual(runs_payroll=YES), 2026)
    merged, added = merge(base, grown)
    assert added == len(grown) - len(base)
    assert len(merged) == len(grown)


def test_merge_keeps_the_existing_instance_not_the_fresh_one():
    """An instance on file may have a job with progress against it."""
    duties = materialise(_individual(), 2026)
    keys = {d.obligation_key for d in duties}
    merged, _ = merge(duties, materialise(_individual(), 2026))
    assert {m.obligation_key for m in merged} == keys
