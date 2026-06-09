"""Stage 5: failure models, deterioration events, backtest mechanics."""

import math

from ccbw.panel import PanelRow, PanelValue
from ccbw.validate import (Z_DISTRESS, altman_z_private, beaver_cfo_tl,
                           deterioration_event, ohlson_o, ohlson_probability)


def _row(fy=2020, **vals):
    r = PanelRow(cik=1, entity="T", sic=3559, fy=fy, fye=f"{fy}-12-31")
    for k, v in vals.items():
        r.values[k] = PanelValue(value=v, provenance=[])
    return r


HEALTHY = dict(total_assets=170e6, total_liabilities=96e6,
               current_assets=56e6, current_liabilities=27e6,
               retained_earnings=40e6, operating_income=14e6,
               revenue=120e6, equity=74e6, net_income=7e6,
               operating_cash_flow=10e6, ebitda=18.4e6,
               interest_expense=3.2e6)


class TestAltman:
    def test_hand_computed_z(self):
        z = altman_z_private(_row(**HEALTHY))
        ta, tl = 170e6, 96e6
        expected = (0.717 * (56e6 - 27e6) / ta + 0.847 * 40e6 / ta
                    + 3.107 * 14e6 / ta + 0.420 * 74e6 / tl
                    + 0.998 * 120e6 / ta)
        assert math.isclose(z, expected)
        assert z > Z_DISTRESS

    def test_distressed_company_in_distress_zone(self):
        z = altman_z_private(_row(
            total_assets=100e6, total_liabilities=110e6,
            current_assets=20e6, current_liabilities=45e6,
            retained_earnings=-30e6, operating_income=-5e6,
            revenue=60e6, equity=-10e6))
        assert z < Z_DISTRESS

    def test_missing_inputs_none_not_garbage(self):
        assert altman_z_private(_row(total_assets=100e6)) is None

    def test_tl_derived_from_equity_when_absent(self):
        vals = dict(HEALTHY)
        del vals["total_liabilities"]
        assert altman_z_private(_row(**vals)) is not None


class TestOhlsonBeaver:
    def test_ohlson_healthy_below_decision_boundary(self):
        # Levels are comparative, not calibrated PDs (the GNP-deflator size
        # term is substituted -- see validate.py); assert the healthy name
        # sits below the 0.5 logit boundary, not an absolute PD.
        o = ohlson_o(_row(**HEALTHY))
        assert o is not None
        assert ohlson_probability(o) < 0.5

    def test_ohlson_distressed_higher_than_healthy(self):
        bad = ohlson_o(_row(
            total_assets=100e6, total_liabilities=115e6,
            current_assets=20e6, current_liabilities=45e6,
            net_income=-12e6, operating_cash_flow=-4e6))
        good = ohlson_o(_row(**HEALTHY))
        assert bad > good
        assert ohlson_probability(bad) > 0.5

    def test_beaver_ratio(self):
        assert math.isclose(beaver_cfo_tl(_row(**HEALTHY)), 10e6 / 96e6)


class TestDeteriorationEvent:
    def _path(self, ebitdas, interests):
        rows = []
        for i, (e, ie) in enumerate(zip(ebitdas, interests)):
            rows.append(_row(fy=2019 + i, ebitda=e, interest_expense=ie,
                             total_assets=100e6, equity=20e6))
        return rows

    def test_coverage_collapse_detected_with_lead_time(self):
        # EBITDA 20->14->8->4 vs interest 5: the 40%-decline trigger fires
        # first (FY2021: 8 <= 0.6*20); coverage < 1.0x follows in FY2022.
        rows = self._path([20e6, 14e6, 8e6, 4e6], [5e6, 5e6, 5e6, 5e6])
        ev = deterioration_event(rows, flag_fy=2019, horizon=3)
        assert ev is not None
        assert ev["fy"] == 2021
        assert ev["lead_time"] == 2
        assert any("EBITDA decline" in r for r in ev["reasons"])

    def test_pure_coverage_breach_detected(self):
        rows = self._path([20e6, 16e6, 14e6, 13e6], [5e6, 5e6, 15e6, 15e6])
        ev = deterioration_event(rows, flag_fy=2019, horizon=3)
        assert ev is not None
        assert ev["fy"] == 2021
        assert any("coverage < 1.0x" in r for r in ev["reasons"])

    def test_ebitda_collapse_40pct(self):
        rows = self._path([20e6, 18e6, 11e6, 10e6], [1e6] * 4)
        ev = deterioration_event(rows, flag_fy=2019, horizon=3)
        assert ev is not None
        assert ev["lead_time"] == 2          # 11 < 0.6*20 at FY2021
        assert any("EBITDA decline" in r for r in ev["reasons"])

    def test_stable_company_no_event(self):
        rows = self._path([20e6, 21e6, 22e6, 23e6], [5e6] * 4)
        assert deterioration_event(rows, flag_fy=2019, horizon=3) is None

    def test_negative_equity_event(self):
        rows = [_row(fy=2019, ebitda=10e6, equity=5e6),
                _row(fy=2020, ebitda=9e6, equity=-2e6)]
        ev = deterioration_event(rows, flag_fy=2019, horizon=3)
        assert ev and "negative book equity" in ev["reasons"]
