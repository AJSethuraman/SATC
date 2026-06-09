"""Stage 3: borrower overlay -- grading, percentiles, departure framing."""

import math

from ccbw.metrics import HIGHER_RISK, LOWER_RISK
from ccbw.overlay import (BorrowerYear, borrower_ratios, departure_framing,
                          grade, interp_percentile, overlay_borrower)

DIST = {"n": 20, "p10": 1.0, "p25": 2.0, "p50": 3.0, "p75": 4.0, "p90": 5.0}


class TestGrade:
    def test_higher_risk_boundaries(self):
        assert grade(3.0, DIST, HIGHER_RISK) == "in_range"
        assert grade(4.1, DIST, HIGHER_RISK) == "watch"
        assert grade(5.1, DIST, HIGHER_RISK) == "departure"
        # severe: beyond p90 + 0.25*IQR = 5.5
        assert grade(5.6, DIST, HIGHER_RISK) == "severe"

    def test_lower_risk_boundaries(self):
        assert grade(3.0, DIST, LOWER_RISK) == "in_range"
        assert grade(1.9, DIST, LOWER_RISK) == "watch"
        assert grade(0.9, DIST, LOWER_RISK) == "departure"
        assert grade(0.4, DIST, LOWER_RISK) == "severe"

    def test_nan_is_severe(self):
        assert grade(float("nan"), DIST, HIGHER_RISK) == "severe"


class TestPercentile:
    def test_median_maps_to_50(self):
        assert math.isclose(interp_percentile(3.0, DIST), 50.0)

    def test_interpolation_between_knots(self):
        assert math.isclose(interp_percentile(3.5, DIST), 62.5)

    def test_clamped_in_tails(self):
        assert interp_percentile(100.0, DIST) == 98.0
        assert interp_percentile(-100.0, DIST) == 2.0


class TestFraming:
    def test_single_period_cannot_classify(self):
        f = departure_framing("debt_ebitda", {2024: 6.0}, 3.0, HIGHER_RISK)
        assert f["classification"] == "single_period"

    def test_normalization_gap_closing(self):
        f = departure_framing("debt_ebitda", {2022: 6.0, 2024: 4.5}, 3.0,
                              HIGHER_RISK)
        assert f["classification"] == "normalization"
        assert "toward the peer baseline" in f["narrative"]

    def test_structural_departure_gap_widening(self):
        f = departure_framing("debt_ebitda", {2022: 4.5, 2024: 6.0}, 3.0,
                              HIGHER_RISK)
        assert f["classification"] == "structural_departure"
        assert "away from the peer baseline" in f["narrative"]

    def test_persistent_departure_static_gap(self):
        f = departure_framing("debt_ebitda", {2022: 6.0, 2024: 6.1}, 3.0,
                              HIGHER_RISK)
        assert f["classification"] == "persistent_departure"


class TestBorrowerRatios:
    def test_core_ratios(self):
        ys = [BorrowerYear(fy=2024, revenue=80e6, ebitda=12e6, total_debt=54e6,
                           cash=3e6, interest_expense=4.8e6)]
        r = borrower_ratios(ys, "cni")[2024]
        assert math.isclose(r["debt_ebitda"], 4.5)
        assert math.isclose(r["net_debt_ebitda"], 4.25)
        assert math.isclose(r["interest_coverage"], 2.5)
        assert math.isclose(r["ebitda_margin"], 15.0)

    def test_negative_ebitda_nan(self):
        ys = [BorrowerYear(fy=2024, ebitda=-1e6, total_debt=10e6)]
        r = borrower_ratios(ys, "cni")[2024]
        assert math.isnan(r["debt_ebitda"])

    def test_segment_suppression_applies_to_borrower_too(self):
        ys = [BorrowerYear(fy=2024, revenue=80e6, ebitda=40e6, cogs=30e6,
                           receivables=10e6, inventory=5e6, payables=4e6)]
        r = borrower_ratios(ys, "cre_opco")[2024]
        assert "dso" not in r and "ccc" not in r


def _mini_adjusted():
    cell = {
        "label": "Total Debt / EBITDA", "unit": "x", "direction": HIGHER_RISK,
        "basis": "fy basis", "primary": True,
        "current": dict(DIST), "baseline_pre2020": dict(DIST), "trend": [],
        "coverage_gaps": ["thin"], "sources": ["agg"],
        "adjusted": {"current": {"n": 20, "p10": 1, "p25": 1.6, "p50": 3.0,
                                 "p75": 4.4, "p90": 6.0},
                     "baseline_pre2020": dict(DIST)},
        "adjustment_note": "note",
    }
    return {"segments": {"cni": {"buckets": {"cmm": {
        "label": "core", "n_companies": 9, "coverage_gaps": [],
        "metrics": {"debt_ebitda": cell}}}}}}


class TestOverlay:
    def test_flags_against_adjusted_by_default(self):
        ys = [BorrowerYear(fy=2023, ebitda=10e6, total_debt=40e6),
              BorrowerYear(fy=2024, ebitda=10e6, total_debt=50e6)]
        res = overlay_borrower(ys, "cni", "cmm", _mini_adjusted())
        m = res.metrics["debt_ebitda"]
        assert m["flag"] == "watch"        # 5.0 vs adjusted p75 4.4 / p90 6.0
        assert m["raw_dist"] == DIST       # raw still attached side-by-side
        assert m["framing"]["classification"] == "structural_departure"
        assert "mechanism" in m and "Leverage" in m["mechanism"]

    def test_raw_view_grades_harder_here(self):
        ys = [BorrowerYear(fy=2024, ebitda=10e6, total_debt=52e6)]
        res = overlay_borrower(ys, "cni", "cmm", _mini_adjusted(), view="raw")
        assert res.metrics["debt_ebitda"]["flag"] == "departure"  # 5.2 > raw p90

    def test_missing_primary_metric_reported_as_gap(self):
        ys = [BorrowerYear(fy=2024, ebitda=10e6, total_debt=30e6)]  # no interest
        res = overlay_borrower(ys, "cni", "cmm", _mini_adjusted())
        assert any("EBITDA / Interest" in g for g in res.coverage_gaps)
