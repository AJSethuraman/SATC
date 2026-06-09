"""End-to-end: synthetic corpus -> panel -> benchmarks -> adjusted ->
overlay -> backtest. The corpus is shaped exactly like CompanyFacts and is
parsed by the same code path live EDGAR data would take."""

import math

import pytest

from ccbw.overlay import BorrowerYear, overlay_borrower
from ccbw.snapshot import assemble, build_demo_inputs
from ccbw.synth import company_facts_json, make_universe


@pytest.fixture(scope="module")
def demo():
    panels, sics = build_demo_inputs(seed=20260609)
    snapshot, bt = assemble(panels, sics, data_source="SYNTHETIC_DEMO",
                            source_notes=["test"])
    return panels, snapshot, bt


class TestCorpus:
    def test_deterministic(self):
        u1 = make_universe(seed=1)
        u2 = make_universe(seed=1)
        assert [c.cik for c in u1] == [c.cik for c in u2]
        cf1 = company_facts_json(u1[0])
        cf2 = company_facts_json(u2[0])
        assert cf1 == cf2

    def test_messiness_present(self):
        u = make_universe(seed=20260609)
        tags = {c.revenue_tag for c in u}
        assert len(tags) >= 2                      # tag fragmentation
        assert any(c.restates for c in u)          # restatements
        assert any(c.missing for c in u)           # missing line items
        assert any(c.fye_month != 12 for c in u)   # off-calendar FYE
        assert any(c.decline_start for c in u)     # deterioration cohort
        assert any(c.unit_trap_fy for c in u)      # unit trap

    def test_lmm_band_deliberately_thin(self):
        u = make_universe(seed=20260609)
        lmm = [c for c in u if c.ebitda0 < 25e6]
        large = [c for c in u if c.ebitda0 >= 300e6]
        assert len(lmm) < len(large)               # survivor-size skew


class TestSnapshot:
    def test_all_segments_and_buckets_present(self, demo):
        _, snapshot, _ = demo
        assert set(snapshot["segments"]) == {
            "cni", "cre_opco", "healthcare", "agribusiness", "leveraged_abl"}
        for seg in snapshot["segments"].values():
            assert set(seg["buckets"]) == {"lmm", "cmm", "umm", "large"}
            assert seg["peer_definition"]
            assert seg["normalization_rules"]
            assert seg["cyclicality_treatment"]

    def test_core_segment_has_usable_distributions(self, demo):
        _, snapshot, _ = demo
        cell = (snapshot["segments"]["cni"]["buckets"]["umm"]
                ["metrics"]["debt_ebitda"])
        cur = cell["current"]
        assert cur and cur["n"] >= 5
        assert cur["p10"] <= cur["p50"] <= cur["p90"]
        assert cell["baseline_pre2020"] is not None      # historical anchor
        assert cell["trend"]                              # 3y trend context
        assert cell["basis"]                              # basis labeled
        assert cell["adjusted"]["current"]["p90"] > cur["p90"]

    def test_thin_lmm_carries_coverage_gaps(self, demo):
        _, snapshot, _ = demo
        gaps = []
        for seg in snapshot["segments"].values():
            b = seg["buckets"]["lmm"]
            gaps += b["coverage_gaps"]
            for m in b["metrics"].values():
                gaps += m["coverage_gaps"]
        assert gaps, "thin lmm band must surface coverage gaps"

    def test_every_metric_cell_is_basis_labeled_and_sourced(self, demo):
        _, snapshot, _ = demo
        for seg in snapshot["segments"].values():
            for b in seg["buckets"].values():
                for m in b["metrics"].values():
                    assert m["basis"]
                    assert m["sources"]
                    assert m["direction"] in ("higher_is_riskier",
                                              "lower_is_riskier")

    def test_meta_flags_synthetic_source(self, demo):
        _, snapshot, _ = demo
        assert snapshot["meta"]["data_source"] == "SYNTHETIC_DEMO"
        assert any("SYNTHETIC" in n for n in snapshot["meta"]["source_notes"])
        assert "refresh" in snapshot["meta"]

    def test_overlay_runs_against_snapshot(self, demo):
        _, snapshot, _ = demo
        ys = [BorrowerYear(fy=2023, revenue=80e6, ebitda=11e6, total_debt=50e6,
                           cash=2e6, interest_expense=4.5e6, capex=2e6),
              BorrowerYear(fy=2024, revenue=78e6, ebitda=10e6, total_debt=55e6,
                           cash=1.5e6, interest_expense=5.2e6, capex=2e6)]
        res = overlay_borrower(ys, "cni", "lmm", snapshot)
        assert "debt_ebitda" in res.metrics
        m = res.metrics["debt_ebitda"]
        assert m["flag"] in ("in_range", "watch", "departure", "severe",
                             "no_benchmark")
        if m["flag"] != "no_benchmark":
            assert m["framing"]["classification"] in (
                "stable_in_range", "normalization", "structural_departure",
                "persistent_departure", "single_period")


class TestBacktest:
    def test_backtest_produces_meaningful_stats(self, demo):
        _, snapshot, bt = demo
        s = bt["summary"]
        assert s["n_eligible_company_years"] > 100
        assert s["n_flagged"] > 5
        assert s["n_deteriorated_total"] > 3
        assert s["hit_rate"] is not None
        assert s["capture_rate"] is not None

    def test_flags_lead_deterioration(self, demo):
        # the point of the design: warnings should lead distress
        _, snapshot, bt = demo
        s = bt["summary"]
        assert s["median_lead_time_years"] is not None
        assert s["median_lead_time_years"] >= 1

    def test_caveats_disclosed(self, demo):
        _, _, bt = demo
        assert any("public-proxy" in c.lower() or "proxy" in c.lower()
                   for c in bt["summary"]["caveats"])
