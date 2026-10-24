"""The estimator the firm asked for on 17 October 2026, tested against the forms.

*"I want a tax estimator built that is super user friendly, easy to use, and
catches anything. Like maybe we won't have certain info and it has to make an
assumption as to maybe standard deduction instead of itemized but I want to have
one that can be updated for each year to see whether people are withholding
enough or what needs to change"* -- and, minutes later: *"also needs to be built
with checks to ensure we don't accidentally use it without updating it for the
right year"*.

EVERY EXPECTED FIGURE BELOW IS WORKED BY HAND FROM THE FORM, line by line, and
written as a literal. None is computed from the crosswalk the engine reads, for
the reason `test_the_2025_tables_are_enacted_law.py` gives: a test that derives
its answer from the table under test can only prove the table agrees with
itself. Sources, all captured 17 October 2026 from irs.gov:

* Schedule 1-A (Form 1040) 2025 -- tips, overtime, car loan interest, seniors
* 2025 Instructions for Schedule A -- the State and Local Tax Deduction Worksheet
* Schedule 8812 (Form 1040) 2025 -- the child tax credit and its refundable part
* Rev. Proc. 2024-40 sec. 2.06 and Rev. Proc. 2025-32 -- EITC, 2026 tables
* Form 1040-ES (2025) and (2026) -- due dates, the 2026 wage base
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from satc.withholding import EstimatorInput, TaxYearNotOnFile, available_years, estimate, staleness
from satc.withholding.tax_data import REQUIRED, incomplete_years, load_tax_tables, missing_parameters, required_for

D = Decimal
MID_YEAR = date(2025, 7, 1)


def _run(year=2025, wages=0, status="single", today=MID_YEAR, **top):
    data = {"filing_status": status, "tax_year": year,
            "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": wages,
                        "pay_periods_remaining": 1}}
    data.update(top)
    return estimate(EstimatorInput.from_dict(data), today=today)


# ── the year guard ────────────────────────────────────────────────────────────

def test_every_year_the_estimator_offers_is_complete():
    """A year is offered only with every parameter the engine reads in force."""
    for year in available_years():
        tables, _ = load_tax_tables(year)
        for name in required_for(year):
            p = tables._x.params.get(name)
            assert p is not None and p.status == "in_force" and p.value is not None, (year, name)


def test_a_half_finished_year_is_named_with_what_it_lacks():
    assert 2024 in incomplete_years()
    with pytest.raises(TaxYearNotOnFile) as exc:
        _run(year=2024, wages=50000)
    assert "configs/crosswalk/federal/2024.yaml" in str(exc.value)
    assert "will not substitute" in str(exc.value)


def test_staleness_speaks_once_the_calendar_passes_the_newest_year():
    assert staleness(date(2026, 10, 17)) is None
    warning = staleness(date(2027, 1, 1))
    assert warning and "2027" in warning and "2026" in warning
    assert "configs/crosswalk/federal/2027.yaml" in warning


def test_the_current_year_is_on_file():
    """THIS TEST IS MEANT TO GO RED ON 1 JANUARY when nobody has added the new
    year's table. That is the check the firm asked for: the estimator cannot be
    used for a year it has not been updated for without the suite saying so.

    To make it green: copy configs/crosswalk/federal/<last year>.yaml to the new
    year, replace every figure from that year's IRS revenue procedure and Form
    1040-ES, and run this file.
    """
    assert staleness() is None, staleness()


# ── what it was not told ──────────────────────────────────────────────────────

def test_blank_answers_become_named_assumptions_not_silent_defaults():
    r = estimate(EstimatorInput.from_dict({
        "paystub": {"pay_frequency": "biweekly", "gross_pay_per_period": 2000,
                    "federal_tax_withheld_per_period": 150}}), today=date(2026, 10, 17))
    topics = {a.topic for a in r.assumptions}
    assert {"Filing status", "Tax year", "Deduction", "Age", "Dependents",
            "Last year's tax"} <= topics
    assert r.filing_status == "single" and r.tax_year_used == 2026
    deduction = next(a for a in r.assumptions if a.topic == "Deduction")
    assert "$16,100" in deduction.assumed
    assert r.breakdown.deduction_kind == "standard"


def test_an_answer_given_is_not_listed_as_assumed():
    r = _run(wages=60000, household={"taxpayer_65_or_older": False, "children_under_17": 0,
                                     "other_dependents": 0},
             deductions={"mortgage_interest": 1000}, prior_year_tax=5000)
    topics = {a.topic for a in r.assumptions}
    assert not topics & {"Filing status", "Deduction", "Age", "Dependents", "Last year's tax"}


def test_itemizes_only_when_itemizing_is_larger():
    # 2025 single, AGI 100,000: mortgage 9,000 + SALT 7,000 = 16,000 > 15,750.
    r = _run(wages=100000, deductions={"mortgage_interest": 9000,
                                       "state_local_income_or_sales_tax": 7000})
    assert r.breakdown.deduction_kind == "itemized"
    assert r.breakdown.deduction_used == D("16000.00")
    r = _run(wages=100000, deductions={"mortgage_interest": 8000,
                                       "state_local_income_or_sales_tax": 7000})
    assert r.breakdown.deduction_kind == "standard"
    assert r.breakdown.deduction_used == D("15750.00")
    assert any(c.title == "Itemizing is close" for c in r.checks)


def test_a_misspelt_filing_status_is_refused_not_assumed():
    with pytest.raises(ValueError, match="filing_status"):
        EstimatorInput.from_dict({"filing_status": "maried", "paystub": {"pay_frequency": "annual"}})


# ── Schedule 1-A (Form 1040) 2025 ─────────────────────────────────────────────

def test_tips_phase_down_in_whole_thousands_rounded_down():
    # MFJ, MAGI 310,500. Line 7: 20,000. Line 10: 10,500. Line 11: 10.
    # Line 12: 1,000. Line 13: 19,000.
    r = _run(wages=310500, status="married_jointly", schedule_1a={"qualified_tips": 20000})
    assert r.breakdown.tips_deduction == D("19000.00")


def test_overtime_is_capped_then_phased():
    # Single, MAGI 155,999. Line 15: 12,500. Line 18: 5,999. Line 19: 5. Line 21: 12,000.
    r = _run(wages=155999, schedule_1a={"qualified_overtime": 15000})
    assert r.breakdown.overtime_deduction == D("12000.00")


def test_car_loan_interest_phases_per_started_thousand():
    # Single, MAGI 100,001. Line 27: 1. Line 28: 1 (rounded UP). Line 29: 200. Line 30: 3,800.
    assert _run(wages=100001, schedule_1a={"car_loan_interest": 4000}).breakdown.car_loan_deduction == D("3800.00")
    assert _run(wages=100000, schedule_1a={"car_loan_interest": 4000}).breakdown.car_loan_deduction == D("4000.00")


def test_car_loan_interest_is_allowed_on_a_separate_return():
    # Codex on #451 said a separate return cannot take it. The 2025 Schedule
    # 1-A says otherwise, checked against the form on 24 Oct 2026: Parts II,
    # III and V each carry "If married, you must file jointly to claim this
    # deduction"; Part IV's caution has no such sentence -- only "you, or your
    # spouse if married filing jointly, paid or accrued" the interest. Line 26
    # puts a separate return at the $100,000 start. MAGI 60,000: no phase-down.
    r = _run(wages=60000, status="married_separately", schedule_1a={"car_loan_interest": 4000})
    assert r.breakdown.car_loan_deduction == D("4000.00")


def test_senior_deduction_for_each_spouse_and_none_when_filing_separately():
    # MFJ, MAGI 160,000. Line 33: 10,000. Line 34: 600. Line 35: 5,400. Line 37: 10,800.
    r = _run(wages=160000, status="married_jointly",
             household={"taxpayer_65_or_older": True, "spouse_65_or_older": True})
    assert r.breakdown.senior_deduction == D("10800.00")
    # ...and the age boxes on the standard deduction: 31,500 + 2 x 1,600.
    assert r.breakdown.deduction_used == D("34700.00")
    r = _run(wages=60000, status="married_separately", household={"taxpayer_65_or_older": True})
    assert r.breakdown.senior_deduction == ZERO_
    assert any("separately" in c.title for c in r.checks)


ZERO_ = D("0.00")


# ── Schedule A, line 5e ───────────────────────────────────────────────────────

@pytest.mark.parametrize("status,agi,paid,expected", [
    ("single", 120000, 50000, "40000.00"),            # line 6 "No": the full cap
    ("single", 520000, 50000, "34000.00"),            # 40,000 - 30% x 20,000
    ("single", 600000, 50000, "10000.00"),            # 40,000 - 30,000 = 10,000 floor
    ("single", 900000, 50000, "10000.00"),            # never below the floor
    ("married_separately", 260000, 30000, "18500.00"),  # (40,000 - 3,000) / 2
    ("single", 120000, 8000, "8000.00"),              # under 10,000: no worksheet
])
def test_salt_worksheet(status, agi, paid, expected):
    r = _run(wages=agi, status=status, deductions={"state_local_income_or_sales_tax": paid,
                                                   "mortgage_interest": 30000})
    assert r.breakdown.itemized_computed - D("30000") == D(expected)


def test_medical_counts_only_above_seven_and_a_half_percent():
    # AGI 80,000: floor 6,000; 10,000 of expenses leaves 4,000.
    r = _run(wages=80000, deductions={"medical_expenses": 10000})
    assert r.breakdown.itemized_computed == D("4000.00")


# ── Schedule 8812 (Form 1040) 2025 ────────────────────────────────────────────

def test_child_credit_phases_out_per_started_thousand():
    # MFJ, AGI 401,500, two children. Line 8: 4,400. Line 10: 2,000. Line 11: 100. Line 12: 4,300.
    r = _run(wages=401500, status="married_jointly", household={"children_under_17": 2})
    assert r.breakdown.child_and_dependent_credit == D("4300.00")


def test_the_refundable_part_is_paid_when_the_tax_runs_out():
    # HOH, wages 20,000, two children, 2025. Taxable 20,000 - 23,625 = 0, so no
    # income tax: line 14 = 0. Line 16a: 4,400. Line 16b: 3,400. Line 17: 3,400.
    # Line 19: 17,500. Line 20: 2,625. ACTC = 2,625.
    r = _run(wages=20000, status="head_of_household", household={"children_under_17": 2})
    assert r.breakdown.child_and_dependent_credit == ZERO_
    assert r.breakdown.additional_child_tax_credit == D("2625.00")


def test_earned_income_credit_from_the_revenue_procedure_columns():
    # HOH, two children, earned = AGI = 30,000, 2025 (Rev. Proc. 2024-40 2.06):
    # max 7,152; phase-out 7,152 / (57,310 - 23,350) per dollar over 23,350.
    # 7,152 - 6,650 x 7,152 / 33,960 = 7,152 - 1,400.494 = 5,751.51
    # (first written here as 5,751.50 -- the hand arithmetic rounded 1,400.494
    # up; the engine was right and the literal was not)
    r = _run(wages=30000, status="head_of_household", household={"children_under_17": 2})
    assert r.breakdown.earned_income_credit == D("5751.51")


def test_rents_and_passive_income_count_as_investment_income_for_the_credit():
    # HOH, three children, wages 20,000, net rent 12,000, 2025. Investment
    # income 12,000 is over the 11,950 limit (Rev. Proc. 2024-40 2.06(2);
    # Pub. 596 counts passive income), so no credit. Codex review, PR #451.
    r = _run(wages=20000, status="head_of_household", household={"children_under_17": 3},
             other_income={"rental_and_passive_income": 12000})
    assert r.breakdown.earned_income_credit == ZERO_
    assert r.breakdown.total_income == D("32000.00")


def test_childless_credit_needs_somebody_aged_25_to_64():
    # Single, no children, wages 15,000, 2025. Phase-in caps at 649; phase-out
    # 649 / (19,104 - 10,620) x (15,000 - 10,620) = 335.06; credit 313.94.
    told = _run(wages=15000, household={"taxpayer_under_25": False, "children_under_17": 0})
    assert told.breakdown.earned_income_credit == D("313.94")
    assert not any("25" in a.assumed for a in told.assumptions)
    # Under 25: IRC sec. 32(c)(1)(A)(ii)(II) -- no credit. Codex review, PR #451.
    young = _run(wages=15000, household={"taxpayer_under_25": True, "children_under_17": 0})
    assert young.breakdown.earned_income_credit == ZERO_
    # Not told: assumed in range, and said so.
    blank = _run(wages=15000, household={"children_under_17": 0})
    assert blank.breakdown.earned_income_credit == D("313.94")
    assert any(a.topic == "Earned income credit" and "25" in a.assumed for a in blank.assumptions)


def test_childless_joint_return_qualifies_on_either_spouse():
    young_pair = {"taxpayer_under_25": True, "spouse_under_25": True, "children_under_17": 0}
    assert _run(wages=15000, status="married_jointly",
                household=young_pair).breakdown.earned_income_credit == ZERO_
    one_older = dict(young_pair, spouse_under_25=False)
    assert _run(wages=15000, status="married_jointly",
                household=one_older).breakdown.earned_income_credit > ZERO_


def test_no_earned_income_credit_married_filing_separately():
    r = _run(wages=15000, status="married_separately", household={"children_under_17": 1})
    assert r.breakdown.earned_income_credit == ZERO_
    # Not told they lived apart: not claimed, and said so.
    assert any(a.topic == "Earned income credit" and "lived apart" in a.assumed for a in r.assumptions)
    told_no = _run(wages=15000, status="married_separately",
                   household={"children_under_17": 1, "lived_apart_from_spouse": False})
    assert told_no.breakdown.earned_income_credit == ZERO_
    assert not any("lived apart" in a.assumed for a in told_no.assumptions)


def test_a_separated_parent_filing_separately_gets_the_credit():
    # IRC sec. 32(d)(2), Pub. 596: a separate return with a qualifying child
    # may claim it when the spouses lived apart the last six months. Codex
    # review, PR #451. MFS uses the unmarried columns. One child, wages
    # 15,000, 2025 (Rev. Proc. 2024-40 2.06): 15,000 x 4,328 / 12,730 = 5,099
    # caps at 4,328; AGI 15,000 is under the 23,350 phase-out start.
    r = _run(wages=15000, status="married_separately",
             household={"children_under_17": 1, "lived_apart_from_spouse": True})
    assert r.breakdown.earned_income_credit == D("4328.00")
    # The rule needs a child: living apart alone does not open it.
    none = _run(wages=15000, status="married_separately",
                household={"children_under_17": 0, "lived_apart_from_spouse": True})
    assert none.breakdown.earned_income_credit == ZERO_


def test_nonrefundable_credits_do_not_offset_self_employment_tax():
    # Single, SE net 30,000, one child. SE tax 30,000 x .9235 x .153 = 4,238.87.
    # Half 2,119.43; AGI 27,880.57; taxable 12,130.57 less QBI. The child credit
    # can take the income tax to zero but never touches the SE tax.
    r = _run(wages=0, other_income={"self_employment_net": 30000}, household={"children_under_17": 1})
    b = r.breakdown
    assert b.self_employment_tax == D("4238.87")
    assert b.income_tax_before_credits - b.child_and_dependent_credit == ZERO_
    assert b.total_tax_liability <= b.self_employment_tax


# ── capital losses ────────────────────────────────────────────────────────────

def test_a_net_capital_loss_counts_three_thousand_and_carries_the_rest():
    r = _run(wages=80000, other_income={"short_term_capital_gains": -5000,
                                        "long_term_capital_gains": -15000})
    assert r.breakdown.capital_gain_in_income == D("-3000.00")
    assert r.breakdown.capital_loss_carryover == D("17000.00")
    assert r.breakdown.adjusted_gross_income == D("77000.00")


def test_a_short_term_loss_offsets_long_term_gain_before_the_preferential_rate():
    # LT +10,000, ST -4,000: net capital gain 6,000 is the preferential amount.
    r = _run(wages=200000, other_income={"short_term_capital_gains": -4000,
                                         "long_term_capital_gains": 10000})
    assert r.breakdown.capital_gains_tax == D("900.00")      # 15% x 6,000


# ── payments the paystub's federal line leaves out ────────────────────────────

def test_additional_medicare_withheld_by_the_employer_is_a_payment():
    # Single, one job paying 250,000. Tax: 0.9% x 50,000 = 450. The employer
    # withholds the same 450 (IRC 3102(f)), so it must not show as owed.
    r = _run(wages=250000)
    assert r.breakdown.additional_medicare_tax == D("450.00")
    assert r.recommendation.additional_medicare_withheld == D("450.00")
    # ...and it reaches the payments. (A mutation run on 17 Oct 2026 showed the
    # two asserts above survive dropping it from the payments entirely.)
    assert r.recommendation.other_payments_total == D("450.00")
    assert r.recommendation.projected_total_payments == D("450.00")


def test_two_employers_over_the_wage_base_give_back_the_excess():
    # 2025 base 176,100. Two jobs of 120,000 each, same person:
    # withheld 2 x 7,440 = 14,880; owed 6.2% x 176,100 = 10,918.20; excess 3,961.80.
    data = {"filing_status": "single", "tax_year": 2025, "jobs": [
        {"pay_frequency": "annual", "taxable_wages_per_period": 120000, "pay_periods_remaining": 1},
        {"pay_frequency": "annual", "taxable_wages_per_period": 120000, "pay_periods_remaining": 1}]}
    r = estimate(EstimatorInput.from_dict(data), today=MID_YEAR)
    assert r.recommendation.excess_social_security_credit == D("3961.80")
    data["jobs"][1]["owner"] = "spouse"
    data["filing_status"] = "married_jointly"
    r = estimate(EstimatorInput.from_dict(data), today=MID_YEAR)
    assert r.recommendation.excess_social_security_credit == ZERO_


# ── the penalty test and what to do about it ──────────────────────────────────

def test_penalty_risk_lays_out_the_estimated_payments_still_due():
    # 2026, single, SE net 60,000, nothing paid, last year's tax 2,000 (AGI under
    # 150,000 -> 100%). Required = the smaller of 90% of this year and 2,000.
    r = _run(year=2026, other_income={"self_employment_net": 60000}, prior_year_tax=2000,
             prior_year_agi=50000, today=date(2026, 8, 1))
    rec = r.recommendation
    assert rec.required_annual_payment == D("2000.00")
    assert rec.required_annual_payment_basis == "100% of last year's tax"
    assert rec.penalty_risk
    # 15 Sep 2026 and 15 Jan 2027 are still ahead on 1 Aug 2026 (Form 1040-ES 2026).
    # A quarter (500) was due by each date, cumulatively, so April's and June's
    # are overdue and go into September: 1,500 then 500. (First written as
    # 1,000 + 1,000 -- spreading the missed quarters left the taxpayer 500
    # short from September to January. Codex review, PR #451.)
    assert rec.estimated_payments_remaining == [("2026-09-15", D("1500.00")), ("2027-01-15", D("500.00"))]
    assert any(c.level == "act" and "penalty" in c.title.lower() for c in r.checks)
    assert "penalty" in r.headline


def test_estimated_payments_already_made_count_toward_the_next_date():
    # As above, but 600 already paid. Due by 15 Sep: 3 x 500 = 1,500, less the
    # 600 = 900. Due by 15 Jan: 2,000 - 600 - 900 = 500.
    r = _run(year=2026, other_income={"self_employment_net": 60000}, prior_year_tax=2000,
             prior_year_agi=50000, today=date(2026, 8, 1), other_payments={"estimated_tax_payments": 600})
    assert r.recommendation.estimated_payments_remaining == [
        ("2026-09-15", D("900.00")), ("2027-01-15", D("500.00"))]


def test_no_penalty_when_less_than_a_thousand_is_owed():
    # 2025 single, wages 50,000: taxable 34,250; tax 1,192.50 + 12% x 22,325 =
    # 3,871.50. Withheld 3,000 is short of 90% (3,484.35), so ONLY the $1,000
    # rule (IRC 6654(e)(1)) keeps this out of the penalty: 871.50 owed.
    # (The first version withheld 3,500, which met 90% anyway, so it passed with
    # the $1,000 rule deleted -- caught by the mutation run on 17 Oct 2026.)
    r = _run(wages=50000, paystub={"pay_frequency": "annual", "taxable_wages_per_period": 50000,
                                   "federal_tax_withheld_per_period": 3000, "pay_periods_remaining": 1})
    assert r.breakdown.total_tax_liability == D("3871.50")
    assert r.recommendation.safe_harbor_shortfall == D("484.35")
    assert not r.recommendation.penalty_risk


def test_last_year_at_110_percent_above_150000():
    r = _run(wages=300000, prior_year_tax=50000, prior_year_agi=280000)
    assert r.recommendation.required_annual_payment == D("55000.00")
    assert r.recommendation.required_annual_payment_basis == "110% of last year's tax"


def test_last_years_income_not_given_is_the_110_percent_rule_and_said():
    # Pub. 505: 110% where last year's AGI was over 150,000. Blank used to
    # fall through to 100% silently. Codex review, PR #451.
    blank = _run(wages=300000, prior_year_tax=50000)
    assert blank.recommendation.required_annual_payment == D("55000.00")
    assert any(a.topic == "Last year's income" for a in blank.assumptions)
    under = _run(wages=300000, prior_year_tax=50000, prior_year_agi=100000)
    assert under.recommendation.required_annual_payment == D("50000.00")
    assert not any(a.topic == "Last year's income" for a in under.assumptions)


@pytest.mark.parametrize("status,count,ok", [
    ("single", 1, True), ("single", 2, False), ("head_of_household", 2, False),
    ("married_separately", 2, False), ("married_jointly", 2, True), ("married_jointly", 3, False)])
def test_only_the_taxpayer_and_a_joint_spouse_can_be_blind(status, count, ok):
    # Pub. 501: the blindness box is the taxpayer's, and the spouse's on a
    # joint return; a blind dependent adds nothing. Codex review, PR #451.
    if ok:
        assert _run(wages=60000, status=status, household={"blind_count": count})
    else:
        with pytest.raises(ValueError, match="legally blind"):
            _run(wages=60000, status=status, household={"blind_count": count})


def test_a_later_year_must_carry_the_deductions_the_law_started_in_2026():
    # A 2027 file without them would read them as zero and switch the
    # deductions off. Codex review, PR #451.
    import dataclasses
    later = ("charity_nonitemizer_max", "charity_itemized_floor_pct",
             "qbi_minimum_deduction", "qbi_minimum_qbi")
    assert not set(later) & set(required_for(2025))
    assert set(later) <= set(required_for(2027))
    cw = load_tax_tables(2026)[0]._x
    assert not missing_parameters(cw)
    for name in later:
        cut = dataclasses.replace(cw, tax_year=2027,
                                  params={k: v for k, v in cw.params.items() if k != name})
        assert missing_parameters(cut) == [name]


def test_the_headline_says_the_answer_first():
    r = _run(year=2026, wages=0, paystub={"pay_frequency": "biweekly", "gross_pay_per_period": 3000,
                                          "federal_tax_withheld_per_period": 100,
                                          "pay_periods_remaining": 6, "name": "Acme"},
             today=date(2026, 10, 17))
    assert r.headline.startswith("Short for 2026: about $")
    assert "per paycheck on Acme" in r.headline


# ── 2026 is its own year ──────────────────────────────────────────────────────

def test_2026_uses_2026_figures():
    # Single, wages 100,000: taxable 100,000 - 16,100 = 83,900.
    # Rev. Proc. 2025-32 Table 3: 5,800 + 22% x (83,900 - 50,400) = 5,800 + 7,370 = 13,170.
    r = _run(year=2026, wages=100000, today=date(2026, 10, 17))
    assert r.breakdown.taxable_income == D("83900.00")
    assert r.breakdown.ordinary_income_tax == D("13170.00")


def test_2026_charity_deduction_for_people_who_do_not_itemize():
    # MFJ standard 32,200 plus up to 2,000 of cash gifts (Form 1040-ES 2026).
    r = _run(year=2026, wages=90000, status="married_jointly", deductions={"charitable_cash": 3000},
             today=date(2026, 10, 17))
    assert r.breakdown.deduction_used == D("34200.00")
    r = _run(year=2025, wages=90000, status="married_jointly", deductions={"charitable_cash": 3000})
    assert r.breakdown.deduction_used == D("31500.00")


def test_the_earned_income_assumption_is_only_raised_where_the_credit_could_apply():
    # Seen on the screen on 17 Oct 2026: a $153,000 joint household was told the
    # estimator had assumed which children qualify for a credit it cannot get.
    rich = _run(wages=150000, status="married_jointly", household={"children_under_17": 2})
    assert "Earned income credit" not in {a.topic for a in rich.assumptions}
    poor = _run(wages=30000, status="head_of_household", household={"children_under_17": 2})
    assert "Earned income credit" in {a.topic for a in poor.assumptions}


def test_three_children_take_the_larger_of_the_two_refundable_child_credits():
    # Schedule 8812 Part II-B, IRC sec. 24(d)(1)(B)(ii). Codex review, PR #451.
    # HOH, wages 4,000, dividends 12,000 (over the 11,950 limit, so no EITC),
    # 2025; no income tax. Line 20: (4,000 - 2,500) x 15% = 225. Line 21:
    # 4,000 x 6.2% + 4,000 x 1.45% = 248 + 58 = 306. Line 26 takes 306.
    three = _run(wages=4000, status="head_of_household", household={"children_under_17": 3},
                 other_income={"ordinary_dividends": 12000})
    assert three.breakdown.earned_income_credit == ZERO_
    assert three.breakdown.additional_child_tax_credit == D("306.00")
    two = _run(wages=4000, status="head_of_household", household={"children_under_17": 2},
               other_income={"ordinary_dividends": 12000})
    assert two.breakdown.additional_child_tax_credit == D("225.00")
    # Line 24 subtracts the earned income credit. Without the dividends the
    # credit is 4,000 x 45% = 1,800, so line 25 is 306 - 1,800, nothing, and
    # line 20's 225 stands.
    with_eitc = _run(wages=4000, status="head_of_household", household={"children_under_17": 3})
    assert with_eitc.breakdown.earned_income_credit == D("1800.00")
    assert with_eitc.breakdown.additional_child_tax_credit == D("225.00")


def test_the_payroll_alternative_counts_half_the_self_employment_tax():
    # Codex's example: SE 20,000, dividends 12,000, three children. Sec.
    # 24(d)(2)(A)(ii) counts HALF the SE tax: 20,000 x .9235 x .153 / 2 =
    # 1,412.96, under line 20's (20,000 - 1,412.96 - 2,500) x 15% = 2,413.06.
    # So line 20 stands; the ~2,826 Codex gave counts the whole SE tax.
    r = _run(wages=0, status="head_of_household", household={"children_under_17": 3},
             other_income={"ordinary_dividends": 12000, "self_employment_net": 20000})
    assert r.breakdown.additional_child_tax_credit == D("2413.06")


@pytest.mark.parametrize("status,amount", [("married_separately", 1000), ("single", 3000)])
def test_student_loan_interest_the_law_does_not_allow_is_refused(status, amount):
    # IRC sec. 221(e)(2): none on a separate return; 221(b)(1): at most 2,500.
    # Codex review, PR #451.
    with pytest.raises(ValueError, match="Student loan interest"):
        _run(wages=60000, status=status, adjustments={"student_loan_interest": amount})


def test_student_loan_interest_within_the_limit_is_deducted():
    r = _run(wages=60000, adjustments={"student_loan_interest": 2500})
    assert r.breakdown.adjusted_gross_income == D("57500.00")
