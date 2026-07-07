"""Integration: compose.py assembles the calc modules into one ValuationResult.

Offline (no market): intrinsic DCF + quality + forensics must still compute;
price-derived pieces (EV, multiples, MoS, reverse) are absent, never crash.
"""

from datetime import date

from conftest import mk_series
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.valuation.compose import compute_valuation, net_claims_senior_to_equity

D = date


class _Co:
    """Stand-in for a Company row (compose only reads a few attributes)."""

    def __init__(self, bucket="industrials", sic="3559"):
        self.id = 1
        self.name = "SynthCo"
        self.industry_bucket = bucket
        self.sic = sic


def healthy_industrial() -> dict:
    return {
        "revenue": mk_series("revenue", [(D(2022, 12, 31), 1000.0), (D(2023, 12, 31), 1100.0), (D(2024, 12, 31), 1210.0)]),
        "cost_of_revenue": mk_series("cost_of_revenue", [(D(2022, 12, 31), 600.0), (D(2023, 12, 31), 650.0), (D(2024, 12, 31), 700.0)]),
        "operating_income": mk_series("operating_income", [(D(2022, 12, 31), 200.0), (D(2023, 12, 31), 230.0), (D(2024, 12, 31), 270.0)]),
        "net_income": mk_series("net_income", [(D(2022, 12, 31), 150.0), (D(2023, 12, 31), 170.0), (D(2024, 12, 31), 200.0)]),
        "operating_cash_flow": mk_series("operating_cash_flow", [(D(2022, 12, 31), 210.0), (D(2023, 12, 31), 240.0), (D(2024, 12, 31), 280.0)]),
        "capex": mk_series("capex", [(D(2022, 12, 31), 50.0), (D(2023, 12, 31), 55.0), (D(2024, 12, 31), 60.0)]),
        "total_assets": mk_series("total_assets", [(D(2022, 12, 31), 1500.0), (D(2023, 12, 31), 1600.0), (D(2024, 12, 31), 1700.0)]),
        "equity": mk_series("equity", [(D(2022, 12, 31), 800.0), (D(2023, 12, 31), 900.0), (D(2024, 12, 31), 1000.0)]),
        "total_liabilities": mk_series("total_liabilities", [(D(2024, 12, 31), 700.0)]),
        "current_assets": mk_series("current_assets", [(D(2023, 12, 31), 500.0), (D(2024, 12, 31), 560.0)]),
        "current_liabilities": mk_series("current_liabilities", [(D(2023, 12, 31), 300.0), (D(2024, 12, 31), 320.0)]),
        "long_term_debt": mk_series("long_term_debt", [(D(2023, 12, 31), 300.0), (D(2024, 12, 31), 300.0)]),
        "cash": mk_series("cash", [(D(2024, 12, 31), 150.0)]),
        "retained_earnings": mk_series("retained_earnings", [(D(2024, 12, 31), 600.0)]),
        "ppe_net": mk_series("ppe_net", [(D(2023, 12, 31), 400.0), (D(2024, 12, 31), 420.0)]),
        "depreciation_amortization": mk_series("depreciation_amortization", [(D(2023, 12, 31), 40.0), (D(2024, 12, 31), 45.0)]),
        "sga_expense": mk_series("sga_expense", [(D(2023, 12, 31), 120.0), (D(2024, 12, 31), 130.0)]),
        "accounts_receivable": mk_series("accounts_receivable", [(D(2023, 12, 31), 90.0), (D(2024, 12, 31), 100.0)]),
        "shares_outstanding": mk_series("shares_outstanding", [(D(2024, 12, 31), 100.0)], unit="shares"),
        "diluted_shares": mk_series("diluted_shares", [(D(2023, 12, 31), 100.0), (D(2024, 12, 31), 100.0)], unit="shares"),
    }


def test_net_claims_senior_sums_debt_not_derived():
    # 300 debt + 0 preferred + 0 minority - 150 cash = 150 (NOT -150).
    assert net_claims_senior_to_equity(healthy_industrial()) == 150.0


def test_compose_offline_computes_intrinsic_and_forensics():
    series = healthy_industrial()
    derived = compute_derived_metrics(series)
    val = compute_valuation(None, _Co(), "SYN", series, derived, market=None)

    # Intrinsic DCF computes without a price.
    assert val.dcf.status == "OK"
    assert val.dcf.method == "dcf"
    assert val.dcf.fair_value_per_share is not None and val.dcf.fair_value_per_share > 0

    # Price-derived pieces absent, not crashing.
    assert val.price is None
    assert val.margin_of_safety is None
    assert val.multiples == {}
    assert val.reverse is None

    # Quality + forensics present.
    assert val.metric_set == "industrial"
    assert val.quality.factors["piotroski_f"].value == 9.0
    assert val.quality.factors["altman_z"].detail["zone"] == "safe"
    assert val.beneish is not None and val.beneish.m_score is not None
    assert val.beneish.flag is False  # healthy company
    assert val.stress.flag_count == 0
    assert val.engine_version


def test_compose_bank_routes_to_financial():
    series = healthy_industrial()
    derived = compute_derived_metrics(series)
    val = compute_valuation(None, _Co(bucket="banking", sic="6022"), "BNK", series, derived, market=None)
    assert val.dcf.method == "ddm+justified_pb"
    assert val.metric_set == "financial"
    # Industrial factors must not be applied to a bank.
    assert val.quality.factors["piotroski_f"].status == "NOT_APPLICABLE"


def test_compose_flags_stressed_company():
    series = healthy_industrial()
    # Wreck it: negative OCF with positive NI, receivables exploding.
    series["operating_cash_flow"] = mk_series("operating_cash_flow", [(D(2023, 12, 31), 240.0), (D(2024, 12, 31), 50.0)])
    series["accounts_receivable"] = mk_series("accounts_receivable", [(D(2023, 12, 31), 90.0), (D(2024, 12, 31), 300.0)])
    derived = compute_derived_metrics(series)
    val = compute_valuation(None, _Co(), "SYN", series, derived, market=None)
    keys = {k for k, _, _ in val.stress.stress_flags}
    assert "ocf_ni_divergence" in keys
    assert "receivables_outgrowing_sales" in keys
    assert val.stress.flag_count >= 2
