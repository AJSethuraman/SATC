"""Obligation rules and the due dates they compute.

Correctness-critical. Every date below is hand-checked against the statute or
the form instructions, not round-tripped through the implementation. The cases
chosen are the ones that actually go wrong in practice:

  * a 1041 extends 5½ months (September 30), not 6 (October 15);
  * the extension runs from the STATUTORY date, not the weekend-shifted one;
  * the perfection period is calendar days and is never shifted;
  * estimated installments run from the START of the year and the fourth lands
    the following January.
"""

from __future__ import annotations

from datetime import date

import pytest

from satc.config import ConfigError
from satc.obligations.due_dates import (
    Period,
    compute,
    installment_due_dates,
    perfection_deadline,
    quarter,
    tax_year,
)
from satc.obligations.rules import load_rules, rule, rules, rules_for_entity


# --- the config on disk ------------------------------------------------------

def test_rules_load():
    keys = {r.key for r in rules()}
    assert {"form_1040", "form_1065", "form_1120s", "form_1041", "form_990"} <= keys


def test_every_rule_cites_a_source():
    """CLAUDE.md: a tax parameter without a citation is a bug."""
    for r in rules():
        assert r.source, f"{r.key} cites no source"


def test_a_rule_without_a_source_is_refused(tmp_path):
    (tmp_path / "obligations").mkdir()
    (tmp_path / "obligations" / "bad.yaml").write_text(
        "rules:\n  - key: x\n    kind: file\n    form: X\n"
        "    due: {basis: fiscal_year_end, months: 4, day: 15}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="cites no source"):
        load_rules(tmp_path)


def test_a_rule_claiming_extendable_must_say_how_long(tmp_path):
    (tmp_path / "obligations").mkdir()
    (tmp_path / "obligations" / "bad.yaml").write_text(
        "rules:\n  - key: x\n    kind: file\n    form: X\n    source: somewhere\n"
        "    due: {basis: fiscal_year_end, months: 4, day: 15}\n"
        "    extension: {available: true, form: '7004'}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="no length"):
        load_rules(tmp_path)


def test_entity_filtering():
    individual = {r.key for r in rules_for_entity("INDIVIDUAL")}
    assert "form_1040" in individual
    assert "form_1120s" not in individual
    # An empty entity_types means "depends what they do", not "nobody".
    assert "form_941" in individual


# --- the ordinary case -------------------------------------------------------

def test_calendar_year_1040_is_the_15th_day_of_the_4th_month():
    d = compute(rule("form_1040"), tax_year(2025))
    assert d.statutory == date(2026, 4, 15)
    assert d.due == date(2026, 4, 15)         # a Wednesday — no shift
    assert not d.was_shifted


def test_calendar_year_1065_is_the_15th_day_of_the_3rd_month():
    d = compute(rule("form_1065"), tax_year(2026))
    assert d.statutory == date(2027, 3, 15)


def test_a_june_30_fiscal_year_1120_is_due_october_15():
    """The 4th month after a June 30 year-end."""
    d = compute(rule("form_1120"), tax_year(2026, fiscal_year_end=date(2026, 6, 30)))
    assert d.statutory == date(2026, 10, 15)


def test_a_fiscal_period_starts_the_day_after_the_prior_year_end():
    period = tax_year(2026, fiscal_year_end=date(2026, 6, 30))
    assert period.start == date(2025, 7, 1)
    assert period.end == date(2026, 6, 30)
    assert not period.is_calendar_year


# --- the shift, applied to real deadlines ------------------------------------

def test_a_sunday_due_date_moves_to_monday():
    """March 15, 2026 is a Sunday — the 1065/1120-S deadline moves."""
    d = compute(rule("form_1120s"), tax_year(2025))
    assert d.statutory == date(2026, 3, 15)
    assert d.due == date(2026, 3, 16)
    assert d.was_shifted
    assert "weekend" in d.shift_reason


def test_the_april_deadline_is_pushed_by_dc_emancipation_day():
    """TY2027: April 15, 2028 is a Saturday and the DC holiday is observed Monday."""
    d = compute(rule("form_1040"), tax_year(2027))
    assert d.statutory == date(2028, 4, 15)
    assert d.due == date(2028, 4, 18)
    assert "DC Emancipation Day" in d.shift_reason


# --- extensions --------------------------------------------------------------

def test_a_1040_extends_six_months_to_october():
    d = compute(rule("form_1040"), tax_year(2025))
    assert d.extended_statutory == date(2026, 10, 15)
    assert d.extension_form == "4868"


def test_a_1041_extends_five_and_a_half_months_to_september_30():
    """NOT October 15. Form 7004 gives a 5½-month period for Form 1041.

    Getting this wrong hands a beneficiary's extended 1040 a 15-day K-1 window
    instead of the 30 days everyone assumes.
    """
    d = compute(rule("form_1041"), tax_year(2025))
    assert d.statutory == date(2026, 4, 15)
    assert d.extended_statutory == date(2026, 9, 30)
    assert d.extended_due == date(2026, 9, 30)      # a Wednesday


def test_the_extension_runs_from_the_statutory_date_not_the_shifted_one():
    """TY2027: the original shifts to April 18 but the extension is 6 months
    from April 15 — October 15, 2028, itself a Sunday, so October 16."""
    d = compute(rule("form_1040"), tax_year(2027))
    assert d.due == date(2028, 4, 18)               # shifted
    assert d.extended_statutory == date(2028, 10, 15)
    assert date(2028, 10, 15).weekday() == 6        # Sunday
    assert d.extended_due == date(2028, 10, 16)


def test_the_k1_window_is_the_thing_the_extension_dates_are_for():
    """An extended 1065 lands Sept 15; the 1040 consuming its K-1 is due Oct 15."""
    entity = compute(rule("form_1065"), tax_year(2025))
    individual = compute(rule("form_1040"), tax_year(2025))
    assert entity.extended_statutory == date(2026, 9, 15)
    assert individual.extended_statutory == date(2026, 10, 15)
    assert (individual.extended_due - entity.extended_due).days == 30


def test_an_extended_1041_leaves_only_fifteen_days():
    """The case that surprises people — half the window of a 1065."""
    trust = compute(rule("form_1041"), tax_year(2025))
    individual = compute(rule("form_1040"), tax_year(2025))
    assert (individual.extended_due - trust.extended_due).days == 15


def test_990n_cannot_be_extended():
    """A real answer, not a missing one — the UI must refuse to offer relief."""
    d = compute(rule("form_990n"), tax_year(2025))
    assert not d.is_extendable
    assert d.extended_due is None
    assert not rule("form_990n").is_extendable


def test_w2_furnishing_cannot_be_extended():
    """Form 8809 explicitly excludes W-2 and 1099-NEC."""
    assert not rule("w2_furnish").is_extendable
    assert not rule("form_1099nec").is_extendable


# --- fixed-date and quarterly duties -----------------------------------------

def test_w2s_are_furnished_by_january_31_of_the_following_year():
    d = compute(rule("w2_furnish"), tax_year(2025))
    assert d.statutory == date(2026, 1, 31)


def test_a_january_31_date_shifts_off_a_weekend():
    """TY2026: January 31, 2027 is a Sunday."""
    d = compute(rule("form_1099nec"), tax_year(2026))
    assert d.statutory == date(2027, 1, 31)
    assert date(2027, 1, 31).weekday() == 6
    assert d.due == date(2027, 2, 1)


def test_941_is_due_the_last_day_of_the_month_after_the_quarter():
    """April 30, not April 31 — the day clamps to the month's length."""
    d = compute(rule("form_941"), quarter(2026, 1))
    assert d.statutory == date(2026, 4, 30)
    d3 = compute(rule("form_941"), quarter(2026, 3))
    assert d3.statutory == date(2026, 10, 31)


def test_quarter_periods_key_and_span_correctly():
    q = quarter(2026, 2)
    assert q.period_key == "2026Q2"
    assert q.start == date(2026, 4, 1)
    assert q.end == date(2026, 6, 30)


def test_an_invalid_quarter_is_refused():
    with pytest.raises(ConfigError):
        quarter(2026, 5)


# --- estimated installments --------------------------------------------------

def test_individual_estimates_run_from_the_start_of_the_year():
    """Four installments for TY2026: Apr 15, Jun 15, Sep 15 — then Jan 15, 2027."""
    dues = installment_due_dates(rule("estimate_1040"), tax_year(2026))
    assert [d.statutory for d in dues] == [
        date(2026, 4, 15), date(2026, 6, 15), date(2026, 9, 15), date(2027, 1, 15)]


def test_each_installment_gets_its_own_period_key():
    """The idempotence key must distinguish them or Q2 overwrites Q1."""
    dues = installment_due_dates(rule("estimate_1040"), tax_year(2026))
    keys = [d.period_key for d in dues]
    assert keys == ["2026-1", "2026-2", "2026-3", "2026-4"]
    assert len(set(keys)) == 4


def test_asking_an_installment_rule_for_one_date_is_an_error_that_says_what_to_do():
    """Doctrine rule 3: a refusal names the right next step."""
    with pytest.raises(ConfigError, match="installment_due_dates"):
        compute(rule("estimate_1040"), tax_year(2026))


def test_an_out_of_range_installment_is_refused():
    with pytest.raises(ConfigError, match="4 installments"):
        compute(rule("estimate_1040"), tax_year(2026), installment=5)


# --- the perfection period ---------------------------------------------------

def test_the_1040_perfection_period_is_five_days():
    """Drake KB 13325. A blog claiming 10 days for 1040 is wrong — 10 is for
    business returns, and building it into an October workflow files late."""
    assert rule("form_1040").perfection_days == 5
    assert rule("form_1065").perfection_days == 10


def test_the_perfection_deadline_is_never_shifted_for_weekends():
    """Pub 1345: the period "has never been extended regardless of weekends,
    holidays or the end of the year cutoff"."""
    # April 15, 2026 + 5 calendar days = April 20 (a Monday), but the point is
    # the arithmetic is raw. Pick a case that lands on a weekend:
    deadline = perfection_deadline(rule("form_1065"), date(2026, 3, 16))
    assert deadline == date(2026, 3, 26)
    saturday = perfection_deadline(rule("form_1040"), date(2026, 4, 13))
    assert saturday == date(2026, 4, 18)
    assert saturday.weekday() == 5          # left on a Saturday, deliberately


def test_a_rule_with_no_perfection_period_returns_none():
    assert perfection_deadline(rule("w2_furnish"), date(2026, 1, 31)) is None


# --- the queue arithmetic ----------------------------------------------------

def test_days_until_counts_down_and_goes_negative_when_overdue():
    d = compute(rule("form_1040"), tax_year(2025))       # due 2026-04-15
    assert d.days_until(date(2026, 4, 1)) == 14
    assert d.days_until(date(2026, 4, 15)) == 0
    assert d.days_until(date(2026, 4, 20)) == -5


def test_an_extension_on_file_moves_the_operative_deadline():
    d = compute(rule("form_1040"), tax_year(2025))
    assert d.final_due() == date(2026, 4, 15)
    assert d.final_due(extended=True) == date(2026, 10, 15)
    assert d.days_until(date(2026, 4, 20), extended=True) == 178


# --- invariants --------------------------------------------------------------

def test_no_computed_deadline_ever_lands_on_a_weekend_or_holiday():
    from satc.obligations.calendar import is_business_day

    for r in rules():
        if r.basis == "installments":
            dues = installment_due_dates(r, tax_year(2026))
        else:
            period = quarter(2026, 1) if r.basis == "quarter_end" else tax_year(2026)
            dues = [compute(r, period)]
        for d in dues:
            assert is_business_day(d.due), f"{r.key} due {d.due} is not a business day"
            if d.extended_due:
                assert is_business_day(d.extended_due), f"{r.key} extended {d.extended_due}"


def test_an_extended_deadline_is_always_later_than_the_original():
    for r in rules():
        if r.basis == "installments" or not r.is_extendable:
            continue
        period = quarter(2026, 1) if r.basis == "quarter_end" else tax_year(2026)
        d = compute(r, period)
        assert d.extended_due > d.due, r.key
