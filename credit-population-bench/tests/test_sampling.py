"""Seam 1 — segment risk ranking, coverage ($ and count), OCC doc."""

import math

from popbench import contract, mapping, sampling
from popbench.engine import run_analysis


def _prep():
    from popbench import demo
    pop = demo.demo_population_full()
    props = mapping.propose(list(pop.columns))
    cols = [mapping.ColumnMap(p.header, p.field_id,
                              contract.UNIT_FRACTION if p.needs_unit else None)
            for p in props if p.field_id]
    m = mapping.confirm(cols)
    return run_analysis(pop, m).clean


def test_rank_flags_high_risk_segments():
    df = _prep()
    ranked = sampling.rank_segments(df, "product_type")
    by = {r.value: r for r in ranked}
    # HELOC is 100% >=90 DPD -> ranks first and is flagged.
    assert ranked[0].value == "heloc"
    assert math.isclose(by["heloc"].risk_dollar_rate, 1.0)
    assert all(by[v].flagged for v in ("auto", "card", "heloc"))
    assert math.isclose(by["auto"].risk_dollar_rate, 25000.0 / 40000.0)


def test_coverage_by_segment_both_bases():
    df = _prep()
    cov = {c.value: c for c in sampling.coverage_by_segment(
        df, {"L-102", "L-103", "L-104"}, "product_type")}
    # auto: selected L-102 of {L-101,L-102} -> 1/2 count, 25k/40k dollars
    assert cov["auto"].sel_count == 1
    assert math.isclose(cov["auto"].count_coverage, 0.5)
    assert math.isclose(cov["auto"].dollar_coverage, 25000.0 / 40000.0)
    # heloc: fully covered
    assert math.isclose(cov["heloc"].dollar_coverage, 1.0)


def test_occ_doc_has_required_sections_and_label():
    df = _prep()
    doc = sampling.build_doc(df, {"L-102", "L-103", "L-104"}, "product_type")
    assert doc.population_count == 5 and math.isclose(doc.population_dollars, 173000.0)
    assert doc.sample_count == 3 and math.isclose(doc.sample_dollars, 153000.0)
    assert math.isclose(doc.overall_count_coverage, 0.6)
    assert math.isclose(doc.overall_dollar_coverage, 153000.0 / 173000.0)
    assert doc.areas_of_focus                      # flagged high-risk segments
    assert "stratified" in doc.selection_rationale
    assert "NON-EXTRAPOLABLE" in doc.non_extrapolable
    assert set(doc.selected_loan_ids) == {"L-102", "L-103", "L-104"}


def test_empty_selection_is_zero_coverage_not_crash():
    df = _prep()
    doc = sampling.build_doc(df, set(), "product_type")
    assert doc.sample_count == 0
    assert math.isclose(doc.overall_dollar_coverage, 0.0)
