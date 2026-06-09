"""Stage 3: adjustment engine -- widening, shifts, survivorship tail."""

import math

from ccbw.adjust import (DEFAULT_PARAMS, BucketAdjustment, adjust_distribution,
                         adjustment_note, apply_adjustments)
from ccbw.metrics import HIGHER_RISK, LOWER_RISK

DIST = {"n": 20, "p10": 1.0, "p25": 2.0, "p50": 3.0, "p75": 4.0, "p90": 5.0}


class TestAdjustDistribution:
    def test_dispersion_widening_around_median(self):
        p = BucketAdjustment(1.5, 0.0, 0.0, 0.0)
        out = adjust_distribution(DIST, HIGHER_RISK, "x", p)
        assert math.isclose(out["p50"], 3.0)
        assert math.isclose(out["p25"], 3.0 + (2.0 - 3.0) * 1.5)  # 1.5
        assert math.isclose(out["p75"], 4.5)

    def test_survivorship_extends_risky_tail_only_higher_risk(self):
        p = BucketAdjustment(1.0, 0.0, 0.0, 0.20)
        out = adjust_distribution(DIST, HIGHER_RISK, "x", p)
        # IQR = 2.0 -> p90 extended by 0.4; p10 untouched
        assert math.isclose(out["p90"], 5.4)
        assert math.isclose(out["p10"], 1.0)

    def test_survivorship_extends_low_tail_for_lower_risk(self):
        p = BucketAdjustment(1.0, 0.0, 0.0, 0.20)
        out = adjust_distribution(DIST, LOWER_RISK, "x", p)
        assert math.isclose(out["p10"], 0.6)
        assert math.isclose(out["p90"], 5.0)

    def test_margin_haircut_applies_to_percent_lower_risk(self):
        p = BucketAdjustment(1.0, 2.0, -0.5, 0.0)
        out = adjust_distribution(DIST, LOWER_RISK, "%", p)
        assert math.isclose(out["p50"], 1.0)   # 3.0 - 2.0pp
        # coverage shift must NOT also apply to % metrics
        assert math.isclose(out["p75"], 2.0)

    def test_coverage_shift_applies_to_x_lower_risk(self):
        p = BucketAdjustment(1.0, 2.0, -0.5, 0.0)
        out = adjust_distribution(DIST, LOWER_RISK, "x", p)
        assert math.isclose(out["p50"], 2.5)

    def test_no_negative_safe_tail_for_leverage(self):
        p = BucketAdjustment(3.0, 0.0, 0.0, 0.0)
        out = adjust_distribution(DIST, HIGHER_RISK, "x", p)
        assert out["p10"] == 0.0   # widened through zero -> clamped

    def test_identity_params_change_nothing(self):
        p = DEFAULT_PARAMS["large"]
        out = adjust_distribution(DIST, HIGHER_RISK, "x", p)
        for k in ("p10", "p25", "p50", "p75", "p90"):
            assert math.isclose(out[k], DIST[k])


class TestApplyAdjustments:
    def _mini_benchmarks(self):
        m = {
            "label": "Total Debt / EBITDA", "unit": "x",
            "direction": HIGHER_RISK, "basis": "b", "primary": True,
            "current": dict(DIST), "baseline_pre2020": dict(DIST),
            "trend": [{"fy": 2024, "p50": 3.0, "p25": 2.0, "p75": 4.0, "n": 20}],
            "coverage_gaps": [], "sources": [],
        }
        return {"current_fy": 2024, "segments": {
            "cni": {"label": "C&I", "buckets": {
                k: {"label": k, "n_companies": 5, "coverage_gaps": [],
                    "metrics": {"debt_ebitda": dict(m, current=dict(DIST),
                                                    baseline_pre2020=dict(DIST))}}
                for k in DEFAULT_PARAMS
            }}}}

    def test_raw_untouched_adjusted_added_side_by_side(self):
        out = apply_adjustments(self._mini_benchmarks())
        cell = out["segments"]["cni"]["buckets"]["lmm"]["metrics"]["debt_ebitda"]
        assert cell["current"] == DIST                      # raw preserved
        adj = cell["adjusted"]["current"]
        assert adj["p90"] > DIST["p90"]                     # widened + tail
        assert "adjustment_note" in cell
        assert "tunable" in cell["adjustment_note"]

    def test_smaller_buckets_adjusted_harder(self):
        out = apply_adjustments(self._mini_benchmarks())
        def p90(b):
            return (out["segments"]["cni"]["buckets"][b]["metrics"]
                    ["debt_ebitda"]["adjusted"]["current"]["p90"])
        assert p90("lmm") > p90("cmm") > p90("umm") > p90("large")
        assert math.isclose(p90("large"), DIST["p90"])

    def test_params_published_in_output(self):
        out = apply_adjustments(self._mini_benchmarks())
        assert out["adjustment_params"]["lmm"]["dispersion_widening"] == 1.40
        assert out["adjustment_params"]["lmm"]["rationale"]


def test_adjustment_note_describes_all_transformations():
    note = adjustment_note(HIGHER_RISK, "x", DEFAULT_PARAMS["lmm"])
    assert "x1.40" in note
    assert "survivorship" in note
    assert "p90" in note
