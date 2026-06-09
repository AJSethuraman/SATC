"""End-to-end pipeline test on synthetic data, incl. determinism check."""

import os

from satc_edgar.aggregate import parse_tiers
from satc_edgar.pipeline import run_for_sic, write_outputs
from tests.fixtures import make_companyfacts


class FakeClient:
    """Stands in for EdgarClient; serves synthetic companyfacts, no network."""

    def __init__(self, facts_by_cik, sic_desc):
        self._facts = facts_by_cik
        self._sic_desc = sic_desc

    def get_companyfacts(self, cik):
        return self._facts.get(int(cik))

    def get_submissions(self, cik):
        return {"sicDescription": self._sic_desc, "sic": "5140", "name": f"Co{cik}"}


def _build_companies(n, base_cik, revenue, **kw):
    companies = []
    facts = {}
    for i in range(n):
        cik = base_cik + i
        facts[cik] = make_companyfacts(
            cik, f"Co{cik}", [2018, 2019, 2020, 2021, 2022], revenue=revenue, **kw
        )
        companies.append((cik, f"Co{cik}", f"T{cik}"))
    return companies, facts


def _run(tmp_path):
    # Two tiers populated: 250M-1B (thin) and 1B-5B (healthy sample).
    small, f1 = _build_companies(3, 1000, revenue=500e6, growth=1.05)
    mid, f2 = _build_companies(11, 2000, revenue=2000e6, growth=1.08)
    facts = {**f1, **f2}
    companies = small + mid
    client = FakeClient(facts, "GROCERIES GENERAL LINE")
    tiers = parse_tiers("0-250M,250M-1B,1B-5B,5B+")
    run = run_for_sic(client, "5140", companies, tiers, years=5, min_sample=10, log=lambda m: None)
    out_base = os.path.join(tmp_path, "food_dist")
    csv_path, md_path = write_outputs([run], out_base, 5, "2026-06-09", 10, lambda m: None)
    return run, csv_path, md_path


def test_pipeline_produces_outputs(tmp_path):
    run, csv_path, md_path = _run(tmp_path)
    assert os.path.exists(csv_path) and os.path.exists(md_path)
    q = run.quality
    assert q["attempted"] == 14
    assert q["usable"] == 14
    assert q["company_years"] == 14 * 5

    by_tier = q["usable_by_tier"]
    assert by_tier["250M-1B"] == 3
    assert by_tier["1B-5B"] == 11

    # Low-confidence flag on the thin tier only.
    flags = {tr.tier.label: tr.low_confidence for tr in run.tier_results}
    assert flags["250M-1B"] is True
    assert flags["1B-5B"] is False

    md = open(md_path).read()
    assert "LOW CONFIDENCE" in md
    assert "Standing caveats" in md
    assert "Survivorship" in md or "SURVIVORSHIP" in md
    assert "Cross-tier size trend" in md
    assert "data vintage" in md.lower()


def test_deterministic_byte_identical(tmp_path):
    d1 = os.path.join(tmp_path, "run1")
    d2 = os.path.join(tmp_path, "run2")
    os.makedirs(d1)
    os.makedirs(d2)
    _, c1, m1 = _run(d1)
    _, c2, m2 = _run(d2)
    assert open(c1, "rb").read() == open(c2, "rb").read()
    assert open(m1, "rb").read() == open(m2, "rb").read()
