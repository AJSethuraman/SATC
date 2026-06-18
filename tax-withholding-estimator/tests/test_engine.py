"""Engine tests with hand-computed expected values against 2025 tables."""

from __future__ import annotations

from decimal import Decimal

import pytest

from twe.engine import estimate
from twe.models import (
    EstimatorInput,
    OtherIncome,
    Paystub,
)


def _wages_only_single() -> EstimatorInput:
    # Biweekly, $3,000/period, full year (26 periods), $350 withheld/period.
    return EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="biweekly",
            gross_pay_per_period=Decimal("3000"),
            federal_tax_withheld_per_period=Decimal("350"),
            pay_periods_remaining=26,
        ),
    )


def test_simple_single_wages_only():
    result = estimate(_wages_only_single())
    b = result.breakdown

    assert b.projected_taxable_wages == Decimal("78000.00")
    assert b.adjusted_gross_income == Decimal("78000.00")
    assert b.deduction_used == Decimal("15000.00")
    assert b.deduction_kind == "standard"
    assert b.taxable_income == Decimal("63000.00")
    # 10% * 11925 + 12% * 36550 + 22% * 14525 = 8774.00
    assert b.ordinary_income_tax == Decimal("8774.00")
    assert b.total_tax_liability == Decimal("8774.00")
    assert b.marginal_rate == Decimal("0.22")


def test_simple_single_balance_and_recommendation():
    result = estimate(_wages_only_single())
    r = result.recommendation

    assert r.periods_per_year == 26
    assert r.periods_remaining == 26
    assert r.projected_withholding_current_rate == Decimal("9100.00")
    # 9100 withheld - 8774 owed = 326 refund.
    assert r.projected_balance == Decimal("326.00")
    # Over-withholding relative to break-even target.
    assert r.is_over_withholding is True
    # 8774 / 26 = 337.46 to break even.
    assert r.recommended_withholding_per_period == Decimal("337.46")
    assert r.additional_withholding_per_period == Decimal("0.00")


def test_underwithholding_recommends_extra():
    # Withhold only $200/period -> under-withheld, needs a 4(c) bump.
    inp = _wages_only_single()
    inp.paystub.federal_tax_withheld_per_period = Decimal("200")
    result = estimate(inp)
    r = result.recommendation

    assert r.projected_withholding_current_rate == Decimal("5200.00")
    assert r.projected_balance == Decimal("-3574.00")  # balance due
    assert r.is_over_withholding is False
    assert r.recommended_withholding_per_period == Decimal("337.46")
    # 337.46 - 200 = 137.46 extra per paycheck.
    assert r.additional_withholding_per_period == Decimal("137.46")


def test_taxable_wages_per_period_used_directly():
    # Box 1 taxable wages entered directly; gross/pretax ignored.
    inp = EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="biweekly",
            taxable_wages_per_period=Decimal("2800"),
            pay_periods_remaining=26,
        ),
    )
    # 2800 * 26 = 72,800
    assert estimate(inp).breakdown.projected_taxable_wages == Decimal("72800.00")


def test_ytd_only_infers_per_period_and_projects():
    # No this-period wage, but YTD taxable + periods remaining lets us infer.
    inp = EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="biweekly",
            ytd_taxable_wages=Decimal("40000"),   # 20 elapsed periods (26 - 6)
            pay_periods_remaining=6,
        ),
    )
    # per-period inferred = 40000 / 20 = 2000; projected = 40000 + 2000*6 = 52,000
    assert estimate(inp).breakdown.projected_taxable_wages == Decimal("52000.00")


def test_pretax_reduces_taxable_wages():
    inp = _wages_only_single()
    inp.paystub.retirement_pretax_per_period = Decimal("300")
    inp.paystub.other_pretax_per_period = Decimal("100")
    result = estimate(inp)
    # (3000 - 400) * 26 = 67,600
    assert result.breakdown.projected_taxable_wages == Decimal("67600.00")


def test_ltcg_fully_in_zero_bracket():
    inp = EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="biweekly",
            gross_pay_per_period=Decimal("1000"),
            pay_periods_remaining=26,
        ),
        other_income=OtherIncome(long_term_capital_gains=Decimal("10000")),
    )
    b = estimate(inp).breakdown
    # wages 26,000 + LTCG 10,000 = 36,000 AGI; minus 15,000 std = 21,000 TI.
    assert b.taxable_income == Decimal("21000.00")
    # Ordinary TI = 11,000 taxed at 10% = 1,100; LTCG sits in 0% bracket.
    assert b.ordinary_income_tax == Decimal("1100.00")
    assert b.capital_gains_tax == Decimal("0.00")
    assert b.total_tax_liability == Decimal("1100.00")


def test_ltcg_partly_in_fifteen_bracket():
    # Push ordinary income above the 0% cap-gains threshold so LTCG is taxed.
    inp = EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="annual",
            gross_pay_per_period=Decimal("100000"),
            pay_periods_remaining=1,
        ),
        other_income=OtherIncome(long_term_capital_gains=Decimal("20000")),
    )
    b = estimate(inp).breakdown
    # AGI 120,000 - 15,000 = 105,000 TI; preferential 20,000; ordinary 85,000.
    # Ordinary 85,000 already above 48,350 zero-rate top -> all 20,000 at 15%.
    assert b.capital_gains_tax == Decimal("3000.00")


def test_self_employment_tax():
    inp = EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(pay_frequency="annual", pay_periods_remaining=1),
        other_income=OtherIncome(self_employment_net=Decimal("20000")),
    )
    b = estimate(inp).breakdown
    # 20,000 * 0.9235 = 18,470 base; SS 0.124 + Medicare 0.029 = 0.153.
    # 18,470 * 0.153 = 2,825.91
    assert b.self_employment_tax == Decimal("2825.91")
    # Half of SE tax is an above-the-line adjustment.
    assert b.adjustments_total == Decimal("1412.96")


def test_itemized_beats_standard():
    inp = _wages_only_single()
    inp.deductions.itemized_total = Decimal("25000")
    b = estimate(inp).breakdown
    assert b.deduction_kind == "itemized"
    assert b.deduction_used == Decimal("25000.00")
    assert b.taxable_income == Decimal("53000.00")


def test_credits_reduce_liability_not_below_zero():
    inp = _wages_only_single()
    inp.credits.child_tax_credit = Decimal("100000")  # absurdly large
    b = estimate(inp).breakdown
    assert b.total_tax_liability == Decimal("0.00")


def test_target_refund_increases_required_withholding():
    inp = _wages_only_single()
    inp.target_refund = Decimal("2600")  # want a $2,600 refund
    r = estimate(inp).recommendation
    # (8774 + 2600) / 26 = 437.46
    assert r.recommended_withholding_per_period == Decimal("437.46")
    assert r.additional_withholding_per_period == Decimal("87.46")


def test_safe_harbor_uses_110_percent_for_high_income():
    inp = _wages_only_single()
    inp.prior_year_tax = Decimal("6000")
    inp.prior_year_agi = Decimal("200000")  # > 150k -> 110%
    r = estimate(inp).recommendation
    # min(90% * 8774 = 7896.60, 110% * 6000 = 6600) = 6600
    assert r.safe_harbor_target == Decimal("6600.00")


def test_mid_year_projection_uses_ytd():
    inp = EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="biweekly",
            gross_pay_per_period=Decimal("3000"),
            federal_tax_withheld_per_period=Decimal("350"),
            ytd_taxable_wages=Decimal("36000"),
            ytd_federal_tax_withheld=Decimal("4200"),
            pay_periods_remaining=14,
        ),
    )
    r = estimate(inp).recommendation
    b = estimate(inp).breakdown
    # 36,000 YTD + 3,000 * 14 = 78,000 projected wages.
    assert b.projected_taxable_wages == Decimal("78000.00")
    assert r.periods_elapsed == 12
    # 4,200 YTD + 350 * 14 = 9,100 projected withholding.
    assert r.projected_withholding_current_rate == Decimal("9100.00")
    assert r.ytd_withholding == Decimal("4200.00")


def test_periods_remaining_clamped():
    inp = _wages_only_single()
    inp.paystub.pay_periods_remaining = 999
    r = estimate(inp).recommendation
    assert r.periods_remaining == 26
    assert r.periods_elapsed == 0


def test_unknown_year_falls_back_with_note():
    inp = _wages_only_single()
    inp.tax_year = 1999
    result = estimate(inp)
    assert result.tax_year_used != 1999
    assert any("not yet bundled" in note for note in result.notes)


def _two_jobs_single() -> EstimatorInput:
    return EstimatorInput(
        filing_status="single",
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="biweekly",
            gross_pay_per_period=Decimal("3000"),
            federal_tax_withheld_per_period=Decimal("350"),
            pay_periods_remaining=26,
            name="Main job",
            adjust_withholding=True,
        ),
        additional_jobs=[Paystub(
            pay_frequency="biweekly",
            gross_pay_per_period=Decimal("2000"),
            federal_tax_withheld_per_period=Decimal("150"),
            pay_periods_remaining=26,
            name="Side job",
        )],
    )


def test_two_jobs_sum_wages_and_withholding():
    result = estimate(_two_jobs_single())
    b, r = result.breakdown, result.recommendation
    assert b.projected_taxable_wages == Decimal("130000.00")   # 3000*26 + 2000*26
    assert b.taxable_income == Decimal("115000.00")
    # 10%*11925 + 12%*36550 + 22%*54875 + 24%*11650 = 20447.00
    assert b.total_tax_liability == Decimal("20447.00")
    assert r.projected_withholding_current_rate == Decimal("13000.00")  # (350+150)*26
    assert r.projected_balance == Decimal("-7447.00")  # under-withheld


def test_two_jobs_recommendation_targets_adjusted_job():
    result = estimate(_two_jobs_single())
    r = result.recommendation
    assert r.adjusted_job_name == "Main job"
    assert r.periods_remaining == 26  # the main job's periods
    # Side job contributes 3,900 future; main must cover 20447 - 3900 = 16547 over 26.
    assert r.recommended_withholding_per_period == Decimal("636.42")
    assert r.additional_withholding_per_period == Decimal("286.42")  # 636.42 - 350
    assert r.is_over_withholding is False


def test_job_breakdown_lists_each_job():
    result = estimate(_two_jobs_single())
    jb = result.recommendation.job_breakdown
    assert [j.name for j in jb] == ["Main job", "Side job"]
    assert jb[0].projected_taxable_wages == Decimal("78000.00")
    assert jb[0].projected_withholding == Decimal("9100.00")
    assert jb[1].projected_taxable_wages == Decimal("52000.00")
    assert jb[1].projected_withholding == Decimal("3900.00")


def test_adjust_flag_defaults_to_primary_job():
    inp = _two_jobs_single()
    inp.paystub.adjust_withholding = False  # no job flagged
    result = estimate(inp)
    assert result.recommendation.adjusted_job_name == "Main job"  # primary by default


def test_jobs_list_form_in_from_dict():
    inp = EstimatorInput.from_dict({
        "filing_status": "single",
        "jobs": [
            {"pay_frequency": "biweekly", "gross_pay_per_period": 3000,
             "federal_tax_withheld_per_period": 350, "pay_periods_remaining": 26,
             "name": "A", "adjust_withholding": True},
            {"pay_frequency": "biweekly", "gross_pay_per_period": 2000,
             "federal_tax_withheld_per_period": 150, "pay_periods_remaining": 26, "name": "B"},
        ],
    })
    assert len(inp.jobs) == 2
    assert inp.adjusted_job().name == "A"
    result = estimate(inp)
    assert result.breakdown.projected_taxable_wages == Decimal("130000.00")


def test_jobs_and_paystub_conflict_raises():
    with pytest.raises(ValueError, match="not both"):
        EstimatorInput.from_dict({
            "filing_status": "single",
            "paystub": {"pay_frequency": "weekly"},
            "jobs": [{"pay_frequency": "weekly"}],
        })


@pytest.mark.parametrize("status", [
    "single", "married_jointly", "married_separately", "head_of_household",
])
def test_all_filing_statuses_run(status):
    inp = EstimatorInput(
        filing_status=status,
        tax_year=2025,
        paystub=Paystub(
            pay_frequency="monthly",
            gross_pay_per_period=Decimal("8000"),
            federal_tax_withheld_per_period=Decimal("1200"),
            pay_periods_remaining=12,
        ),
    )
    result = estimate(inp)
    assert result.breakdown.total_tax_liability >= 0
