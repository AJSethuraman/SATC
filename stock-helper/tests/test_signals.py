"""Signal rules and industry applicability."""

from datetime import date

from conftest import mk_series
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.signals.engine import assess_data_confidence, evaluate_signals

D = date


def industrial_series():
    return {
        "revenue": mk_series("revenue", [
            (D(2022, 12, 31), 100.0), (D(2023, 12, 31), 110.0), (D(2024, 12, 31), 121.0),
        ]),
        "cost_of_revenue": mk_series("cost_of_revenue", [
            (D(2022, 12, 31), 60.0), (D(2023, 12, 31), 64.0), (D(2024, 12, 31), 68.0),
        ]),
        "operating_income": mk_series("operating_income", [
            (D(2022, 12, 31), 20.0), (D(2023, 12, 31), 24.0), (D(2024, 12, 31), 29.0),
        ]),
        "diluted_shares": mk_series("diluted_shares", [
            (D(2023, 12, 31), 1000.0), (D(2024, 12, 31), 950.0),
        ], unit="shares"),
    }


def industrial_derived():
    return compute_derived_metrics(industrial_series())


def bank_series():
    return {
        "deposits": mk_series("deposits", [
            (D(2022, 12, 31), 140_000.0), (D(2023, 12, 31), 145_000.0), (D(2024, 12, 31), 150_000.0),
        ]),
        "credit_loss_allowance": mk_series("credit_loss_allowance", [
            (D(2023, 12, 31), 1_500.0), (D(2024, 12, 31), 2_000.0),
        ]),
        "diluted_shares": mk_series("diluted_shares", [
            (D(2023, 12, 31), 900.0), (D(2024, 12, 31), 940.0),
        ], unit="shares"),
        "net_interest_income": mk_series("net_interest_income", [
            (D(2023, 12, 31), 4_000.0), (D(2024, 12, 31), 4_400.0),
        ]),
        "total_assets": mk_series("total_assets", [
            (D(2022, 12, 31), 180_000.0), (D(2023, 12, 31), 190_000.0), (D(2024, 12, 31), 200_000.0),
        ]),
        "nonperforming_loans": mk_series("nonperforming_loans", [
            (D(2023, 12, 31), 700.0), (D(2024, 12, 31), 900.0),
        ]),
    }


def bank_derived():
    return compute_derived_metrics(bank_series())


def by_key(results):
    return {r.definition.key: r.outcome for r in results}


def test_industrial_scorecard():
    outcomes = by_key(evaluate_signals("technology", industrial_derived()))

    growth = outcomes["revenue_growth_yoy"]
    assert growth.status == "OK"
    assert growth.direction == "improving"
    assert abs(growth.numeric_value - 0.10) < 1e-9
    assert growth.evidence, "every OK signal must carry evidence"
    assert growth.caveat

    assert outcomes["operating_margin_trend"].status == "OK"
    assert outcomes["operating_margin_trend"].direction == "improving"

    dilution = outcomes["share_dilution"]
    assert dilution.status == "OK"
    assert dilution.direction == "improving"  # shrinking share count

    # Bank-only signals must be n/a, not bogus numbers.
    assert outcomes["deposits_trend"].status == "NOT_APPLICABLE"
    assert outcomes["nim_proxy_trend"].status == "NOT_APPLICABLE"

    # Metrics that were not provided are honestly unavailable.
    assert outcomes["fcf_trend"].status == "UNAVAILABLE"
    assert "free_cash_flow" in outcomes["fcf_trend"].interpretation


def test_bank_scorecard():
    outcomes = by_key(evaluate_signals("banking", bank_derived()))

    # Industrial ratios must never be forced onto a bank.
    for key in ("gross_margin_trend", "current_ratio", "interest_coverage",
                "debt_to_assets", "accrual_proxy", "revenue_growth_yoy"):
        assert outcomes[key].status == "NOT_APPLICABLE", key

    deposits = outcomes["deposits_trend"]
    assert deposits.status == "OK"
    assert deposits.direction == "improving"

    allowance = outcomes["credit_loss_allowance"]
    assert allowance.status == "OK"
    assert allowance.direction == "deteriorating"  # +33% YoY reserve build
    assert "CECL" in allowance.caveat

    dilution = outcomes["share_dilution"]
    assert dilution.status == "OK"
    assert dilution.direction == "deteriorating"  # +4.4% share count

    # Bank metric library (Phase 4 slice): NIM proxy computed from NII / avg assets.
    nim = outcomes["nim_proxy_trend"]
    assert nim.status == "OK"
    assert "proxy" in nim.caveat.lower()

    npl = outcomes["npl_trend"]
    assert npl.status == "OK"
    assert npl.direction == "deteriorating"  # nonaccruals rising is bad

    # Charge-offs tag absent → honestly unavailable with the table-parsing hint.
    assert outcomes["charge_offs_trend"].status == "UNAVAILABLE"

    # CET1 remains a declared placeholder.
    assert outcomes["cet1_placeholder"].status == "PLACEHOLDER"


def test_insufficient_history():
    series = {"revenue": mk_series("revenue", [(D(2024, 12, 31), 100.0)])}
    outcomes = by_key(evaluate_signals("technology", compute_derived_metrics(series)))
    assert outcomes["revenue_growth_yoy"].status == "INSUFFICIENT_DATA"


def test_empty_company_does_not_crash():
    outcomes = by_key(evaluate_signals("other", {}))
    assert all(
        o.status in ("UNAVAILABLE", "PLACEHOLDER", "NOT_APPLICABLE") for o in outcomes.values()
    )


def test_data_confidence_industrial_vs_bank():
    industrial = assess_data_confidence("technology", industrial_series(), D(2024, 11, 1))
    assert industrial.metrics_mapped == 4  # revenue, cogs, op income, diluted shares
    assert industrial.annual_periods == 3
    assert industrial.level == "low"  # 4/18 coverage is honestly low

    bank = assess_data_confidence("banking", bank_series(), None)
    # Banks are not penalized for missing cost_of_revenue / current ratio inputs,
    # and bank-only metrics count toward their coverage.
    assert bank.metrics_mapped == 6
    assert bank.level in ("low", "medium", "high")

    # Industrials are not penalized for missing bank-only metrics.
    assert industrial.metrics_total < bank.metrics_total + 5
