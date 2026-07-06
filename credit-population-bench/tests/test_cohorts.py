"""Seam 1 — derived cohorts: safe compilation, overlap matrix, residual, A/B."""

import math

import pandas as pd
import pytest

from popbench import cohorts, contract, mapping
from popbench.cohorts import Cohort, Rule
from popbench.engine import run_analysis


def _prep_full_demo():
    from popbench import demo
    pop = demo.demo_population_full()
    props = mapping.propose(list(pop.columns))
    cols = [mapping.ColumnMap(p.header, p.field_id,
                              contract.UNIT_FRACTION if p.needs_unit else None)
            for p in props if p.field_id]
    m = mapping.confirm(cols)
    return run_analysis(pop, m).clean   # normalized: has dpd_min


# --- overlap + residual are honest (the whole point) ------------------------

def test_cohorts_report_independently_with_overlap_and_residual():
    df = _prep_full_demo()
    A = Cohort("A", "high-balance delinquent",
               (Rule("current_balance", ">=", 20000), Rule("dpd_min", ">=", 90)))
    B = Cohort("B", "subprime auto",
               (Rule("fico_orig", "<", 660), Rule("product_type", "==", "auto")))
    C = Cohort("C", "card", (Rule("product_type", "==", "card"),))
    cmp = cohorts.evaluate(df, [A, B, C])

    by = {r.id: r for r in cmp.reports}
    assert by["A"].count == 2 and math.isclose(by["A"].balance, 145000.0)   # L-102, L-104
    assert by["B"].count == 1 and math.isclose(by["B"].balance, 25000.0)    # L-102
    assert by["C"].count == 2 and math.isclose(by["C"].balance, 13000.0)    # L-103, L-105

    # A and B overlap on L-102 ($25k); the others are disjoint.
    assert cmp.overlap_count[("A", "B")] == 1
    assert math.isclose(cmp.overlap_dollars[("A", "B")], 25000.0)
    assert cmp.overlap_count[("A", "C")] == 0 and cmp.overlap_count[("B", "C")] == 0

    # L-101 is in no cohort -> residual.
    assert cmp.residual_count == 1 and math.isclose(cmp.residual_dollars, 15000.0)
    assert cmp.population_count == 5 and math.isclose(cmp.population_dollars, 173000.0)

    # Cohorts do NOT partition: A+B+C counts (5) != population (5) only by luck;
    # the overlap is what makes summing them wrong. Prove A+B double-counts L-102.
    assert by["A"].count + by["B"].count + by["C"].count == 5
    assert cmp.overlap_count[("A", "B")] > 0   # so the naive sum over-counts


# --- OR-groups vs AND -------------------------------------------------------

def test_or_group_semantics():
    df = _prep_full_demo()
    # auto OR card (same group) -> 4 loans (all but the HELOC).
    coh = Cohort("mix", "auto or card",
                 (Rule("product_type", "==", "auto", group=1),
                  Rule("product_type", "==", "card", group=1)))
    assert int(cohorts.compile_mask(df, coh).sum()) == 4


def test_and_across_ungrouped_rules():
    df = _prep_full_demo()
    coh = Cohort("x", "auto AND delinquent",
                 (Rule("product_type", "==", "auto"), Rule("dpd_min", ">=", 90)))
    # auto = L-101,L-102; delinquent>=90 among them = L-102 only.
    assert int(cohorts.compile_mask(df, coh).sum()) == 1


# --- safety + missing-data stance ------------------------------------------

def test_unknown_operator_refused():
    df = _prep_full_demo()
    with pytest.raises(cohorts.CohortError, match="operator"):
        cohorts.compile_mask(df, Cohort("z", "bad", (Rule("fico_orig", "~=", 5),)))


def test_unmapped_field_refused():
    df = _prep_full_demo()
    with pytest.raises(cohorts.CohortError, match="unmapped"):
        cohorts.compile_mask(df, Cohort("z", "bad", (Rule("nope", "==", 1),)))


def test_comparison_on_null_field_is_hard_error():
    df = _prep_full_demo()   # ltv is null for the unsecured loans
    with pytest.raises(cohorts.CohortError, match="null"):
        cohorts.compile_mask(df, Cohort("z", "ltv", (Rule("ltv", "<", 0.9),)))
    # ...but is_null is allowed to see nulls.
    m = cohorts.compile_mask(df, Cohort("z", "no ltv", (Rule("ltv", "is_null"),)))
    assert int(m.sum()) == 4   # the four unsecured loans


# --- A/B comparison flags dollar-vs-count divergence ------------------------

def test_ab_compare_flags_divergence():
    # Group A: one huge low-score loan + one tiny high-score loan.
    # Group B: uniform. Dollar basis says A is lower; count basis says A is higher.
    df = pd.DataFrame({
        "loan_id": ["a1", "a2", "b1", "b2"],
        "current_balance": [99000.0, 1000.0, 5000.0, 5000.0],
        "fico_orig": [600.0, 800.0, 690.0, 690.0],
        "grp": ["A", "A", "B", "B"],
    })
    A = Cohort("A", "A", (Rule("grp", "==", "A"),))
    B = Cohort("B", "B", (Rule("grp", "==", "B"),))
    (row,) = [r for r in cohorts.ab_compare(df, A, B, attributes=("fico_orig",))]
    # A dollar-weighted FICO ~602 (< B's 690); A count-weighted 700 (> B's 690).
    assert row.a_dollar < row.b_dollar
    assert row.a_count > row.b_count
    assert row.diverges is True
