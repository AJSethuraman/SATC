"""Stage 2: metric computation, basis labels, segment specials."""

import math

from ccbw.metrics import METRICS, compute_measurements
from ccbw.panel import PanelRow, PanelValue


def _row(fy=2020, **vals):
    r = PanelRow(cik=1, entity="T", sic=3559, fy=fy, fye=f"{fy}-12-31")
    for k, v in vals.items():
        r.values[k] = PanelValue(value=v, provenance=[{"tag": k, "accn": "x"}])
    return r


BASE = dict(revenue=100e6, ebitda=16e6, total_debt=48e6, cash=10e6,
            interest_expense=3.2e6, capex=3e6, cogs=72e6,
            receivables=17e6, inventory=20e6, payables=10e6,
            current_assets=56e6, current_liabilities=27e6,
            total_assets=170e6)


class TestRatios:
    def test_hand_computed_values(self):
        m = compute_measurements(_row(**BASE))
        assert math.isclose(m["debt_ebitda"].value, 3.0)
        assert math.isclose(m["net_debt_ebitda"].value, 38e6 / 16e6)
        assert math.isclose(m["interest_coverage"].value, 5.0)
        assert math.isclose(m["fcc_proxy"].value, 13e6 / 3.2e6)
        assert math.isclose(m["ebitda_margin"].value, 16.0)
        assert math.isclose(m["gross_margin"].value, 28.0)
        assert math.isclose(m["dso"].value, 17e6 / 100e6 * 365)
        assert math.isclose(m["dio"].value, 20e6 / 72e6 * 365)
        assert math.isclose(m["dpo"].value, 10e6 / 72e6 * 365)
        assert math.isclose(m["ccc"].value,
                            m["dso"].value + m["dio"].value - m["dpo"].value)
        assert math.isclose(m["current_ratio"].value, 56 / 27)
        assert math.isclose(m["debt_assets"].value, 48 / 170 * 100)

    def test_every_measurement_is_basis_labeled(self):
        m = compute_measurements(_row(**BASE))
        for meas in m.values():
            assert meas.basis, meas.metric
            assert meas.unit in ("x", "%", "days", "USD")

    def test_negative_ebitda_leverage_is_nan_flagged(self):
        vals = dict(BASE, ebitda=-2e6)
        m = compute_measurements(_row(**vals))
        assert math.isnan(m["debt_ebitda"].value)
        assert any("not meaningful" in g for g in m["debt_ebitda"].gaps)

    def test_zero_interest_no_coverage(self):
        vals = dict(BASE, interest_expense=0.0)
        m = compute_measurements(_row(**vals))
        assert "interest_coverage" not in m

    def test_provenance_carried_through(self):
        m = compute_measurements(_row(**BASE))
        tags = {p["tag"] for p in m["debt_ebitda"].provenance}
        assert tags == {"total_debt", "ebitda"}


class TestSegmentSpecials:
    def test_cre_suppresses_trade_cycle_metrics(self):
        m = compute_measurements(_row(**BASE), segment="cre_opco")
        for k in ("dso", "dio", "dpo", "ccc", "gross_margin"):
            assert k not in m
        assert "debt_assets" in m

    def test_healthcare_rent_adjusted_leverage(self):
        vals = dict(BASE, rent_expense=4e6)
        m = compute_measurements(_row(**vals), segment="healthcare")
        # (48 + 8*4) / (16 + 4) = 80/20 = 4.0
        assert math.isclose(m["rent_adj_leverage"].value, 4.0)

    def test_healthcare_missing_rent_is_gap(self):
        row = _row(**BASE)
        compute_measurements(row, segment="healthcare")
        assert any("rent_adj_leverage" in g for g in row.gaps)

    def test_agribusiness_through_cycle_leverage(self):
        rows = [_row(fy=2018, **dict(BASE, ebitda=10e6)),
                _row(fy=2019, **dict(BASE, ebitda=22e6))]
        cur = _row(fy=2020, **BASE)  # ebitda 16e6 -> avg = 16e6
        m = compute_measurements(cur, history=rows, segment="agribusiness")
        assert math.isclose(m["debt_ebitda_3y"].value, 3.0)

    def test_revenue_growth_needs_adjacent_year(self):
        prior = _row(fy=2018, **BASE)
        cur = _row(fy=2020, **dict(BASE, revenue=110e6))
        m = compute_measurements(cur, history=[prior])
        assert "rev_growth" not in m  # 2-year gap: not a YoY figure

    def test_ebitda_volatility_needs_three_growth_obs(self):
        hist = [_row(fy=fy, **dict(BASE, ebitda=e))
                for fy, e in [(2016, 10e6), (2017, 12e6), (2018, 9e6)]]
        cur = _row(fy=2019, **dict(BASE, ebitda=15e6))
        m = compute_measurements(cur, history=hist)
        assert "ebitda_volatility" in m
        assert m["ebitda_volatility"].value > 0


def test_metric_specs_have_direction_and_basis():
    for k, spec in METRICS.items():
        assert spec.direction in ("higher_is_riskier", "lower_is_riskier"), k
        assert spec.basis and spec.unit, k
