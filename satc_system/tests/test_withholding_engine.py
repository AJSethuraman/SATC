"""Withholding engine tests — hand-computed against the 2025 federal crosswalk."""

from __future__ import annotations

from decimal import Decimal

import pytest

from satc.withholding import EstimatorInput, available_years, estimate


def _estimate(**top):
    return estimate(EstimatorInput.from_dict(top))


def test_available_years_are_the_fully_published_federal_tables():
    years = available_years()
    assert 2024 in years and 2025 in years
    assert 2026 not in years          # the sunset fixture is intentionally not usable


def test_single_filer_ordinary_tax_matches_brackets():
    # $78,000 wages - $15,000 standard deduction = $63,000 taxable.
    r = _estimate(filing_status="single", tax_year=2025,
                  paystub={"pay_frequency": "annual", "taxable_wages_per_period": 78000,
                           "pay_periods_remaining": 1})
    assert r.breakdown.taxable_income == Decimal("63000.00")
    # 10%*11925 + 12%*(48475-11925) + 22%*(63000-48475) = 1192.50 + 4386 + 3195.50
    assert r.breakdown.ordinary_income_tax == Decimal("8774.00")


def test_capital_gains_stack_on_top_of_ordinary_income():
    # $20k ordinary TI + $40k LTCG: $28,350 fills the 0% band, $11,650 taxed at 15%.
    r = _estimate(filing_status="single", tax_year=2025,
                  paystub={"pay_frequency": "annual", "taxable_wages_per_period": 35000,
                           "pay_periods_remaining": 1},
                  other_income={"long_term_capital_gains": 40000})
    assert r.breakdown.ordinary_income_tax == Decimal("2161.50")
    assert r.breakdown.capital_gains_tax == Decimal("1747.50")


def test_self_employment_tax_uses_split_se_rates():
    # $10,000 net SE * 0.9235 = 9235 base; 12.4% SS + 2.9% Medicare = 1412.96.
    r = _estimate(filing_status="single", tax_year=2025,
                  paystub={"pay_frequency": "annual", "taxable_wages_per_period": 0,
                           "pay_periods_remaining": 1},
                  other_income={"self_employment_net": 10000})
    assert r.breakdown.self_employment_tax == Decimal("1412.96")


def test_niit_applies_to_investment_income_over_threshold():
    # AGI $270k (single, threshold $200k); $20k interest is below the $70k room.
    r = _estimate(filing_status="single", tax_year=2025,
                  paystub={"pay_frequency": "annual", "taxable_wages_per_period": 250000,
                           "pay_periods_remaining": 1},
                  other_income={"interest": 20000})
    assert r.breakdown.net_investment_income_tax == Decimal("760.00")  # 20000 * 3.8%


def test_year_fallback_uses_latest_published_with_a_note():
    r = _estimate(filing_status="single", tax_year=2026,
                  paystub={"pay_frequency": "annual", "taxable_wages_per_period": 50000,
                           "pay_periods_remaining": 1})
    assert r.tax_year_used == 2025
    assert any("2026" in n for n in r.notes)


def test_over_vs_under_withholding_is_household_based():
    base = {"filing_status": "single", "tax_year": 2025}
    over = _estimate(**base, paystub={"pay_frequency": "annual", "taxable_wages_per_period": 50000,
                                      "federal_tax_withheld_per_period": 8000, "pay_periods_remaining": 1})
    assert over.recommendation.is_over_withholding is True
    assert over.recommendation.projected_balance > 0          # headed for a big refund

    under = _estimate(**base, paystub={"pay_frequency": "annual", "taxable_wages_per_period": 50000,
                                       "federal_tax_withheld_per_period": 200, "pay_periods_remaining": 1})
    assert under.recommendation.is_over_withholding is False
    assert under.recommendation.additional_withholding_per_period > 0


def test_safe_harbor_target_is_min_of_current_and_prior():
    r = _estimate(filing_status="single", tax_year=2025, prior_year_tax=2000, prior_year_agi=50000,
                  paystub={"pay_frequency": "annual", "taxable_wages_per_period": 80000,
                           "pay_periods_remaining": 1})
    liability = r.breakdown.total_tax_liability
    expected = min(liability * Decimal("0.90"), Decimal("2000"))
    assert r.recommendation.safe_harbor_target == expected.quantize(Decimal("0.01"))


def test_unknown_input_key_raises():
    with pytest.raises(ValueError):
        EstimatorInput.from_dict({"filing_status": "single", "bogus_key": 1,
                                  "paystub": {"pay_frequency": "annual"}})
