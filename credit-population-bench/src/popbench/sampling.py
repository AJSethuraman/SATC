"""Judgmental-sampling support — rank, flag, cover, document.

The tool does **not** draw the sample. It ranks and flags the highest-risk
cells, computes coverage per segment on both a dollar and a count basis, and —
from the loans the *reviewer* marks as selected — auto-generates the
documentation the OCC "Sampling Methodologies" booklet requires (population,
areas of focus, sample size, selection rationale, results), **explicitly and
unremovably labeled non-extrapolable**. The reviewer marks selection by loan
number; that is also the file-pull key for linesheet review.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from popbench import bands, strata

# The label is fixed text, not a parameter — a judgmental sample is never
# statistically extrapolable to the population (OCC Bulletin 2020-56).
NON_EXTRAPOLABLE = ("NON-EXTRAPOLABLE: results of this judgmental sample cannot "
                    "be statistically projected to the population (OCC Sampling "
                    "Methodologies, Bulletin 2020-56).")


@dataclass(frozen=True)
class SegmentRisk:
    value: str
    count: int
    balance: float
    risk_count: int          # loans at/above the risk DPD threshold
    risk_balance: float
    risk_dollar_rate: float  # risk_balance / segment balance
    flagged: bool            # a high-risk cell (>= flag cut on dollar risk)


def rank_segments(df: pd.DataFrame, dimension: str,
                  scheme: bands.BandScheme | None = None,
                  risk_threshold_dpd: int = 90, flag_cut: float = 0.0,
                  weight: str = "current_balance") -> list[SegmentRisk]:
    """Rank a group-by's cells by their dollar risk (>= DPD threshold), flagging
    cells whose risk dollar-rate exceeds ``flag_cut`` (default: any risk)."""
    strat = strata.group_by(df, dimension, scheme=scheme, weight=weight)
    work = df.copy()
    if scheme is not None:
        col = f"__band__{scheme.field}"
        work[col] = scheme.assign(work[scheme.field])
        group_col = col
    else:
        group_col = dimension
    has_dpd = "dpd_min" in work.columns

    out: list[SegmentRisk] = []
    for cell in strat.cells:
        grp = work[work[group_col].astype("string") == cell.value] if scheme is None \
            else work[work[group_col].astype("object").astype("string") == cell.value]
        if has_dpd:
            rmask = grp["dpd_min"] >= risk_threshold_dpd
            rc = int(rmask.sum())
            rb = float(grp.loc[rmask, weight].astype("float64").sum())
        else:
            rc, rb = 0, 0.0
        rate = (rb / cell.balance) if cell.balance else 0.0
        out.append(SegmentRisk(cell.value, cell.count, cell.balance,
                               rc, rb, rate, rate > flag_cut))
    out.sort(key=lambda s: (-s.risk_dollar_rate, -s.risk_balance, s.value))
    return out


@dataclass(frozen=True)
class SegmentCoverage:
    value: str
    seg_count: int
    seg_balance: float
    sel_count: int
    sel_balance: float
    count_coverage: float    # sel_count / seg_count
    dollar_coverage: float   # sel_balance / seg_balance
    flagged: bool


def coverage_by_segment(df: pd.DataFrame, selected_ids, dimension: str,
                        scheme: bands.BandScheme | None = None,
                        risk_threshold_dpd: int = 90,
                        weight: str = "current_balance") -> list[SegmentCoverage]:
    """Per-segment penetration of the reviewer's selection, on both bases."""
    selected = set(selected_ids)
    risk = {r.value: r for r in rank_segments(df, dimension, scheme,
                                              risk_threshold_dpd, weight=weight)}
    work = df.copy()
    if scheme is not None:
        col = f"__band__{scheme.field}"
        work[col] = scheme.assign(work[scheme.field]).astype("object").astype("string")
        group_col = col
    else:
        group_col = dimension
        work[group_col] = work[group_col].astype("string")
    work["__sel__"] = work["loan_id"].isin(selected)

    out: list[SegmentCoverage] = []
    for value, grp in work.groupby(group_col, observed=True, dropna=False):
        val = str(value)
        seg_c, seg_b = int(len(grp)), float(grp[weight].astype("float64").sum())
        sel = grp[grp["__sel__"]]
        sel_c, sel_b = int(len(sel)), float(sel[weight].astype("float64").sum())
        out.append(SegmentCoverage(
            val, seg_c, seg_b, sel_c, sel_b,
            (sel_c / seg_c) if seg_c else 0.0,
            (sel_b / seg_b) if seg_b else 0.0,
            risk.get(val).flagged if val in risk else False))
    out.sort(key=lambda c: c.value)
    return out


@dataclass(frozen=True)
class SamplingDoc:
    population_count: int
    population_dollars: float
    areas_of_focus: list[str]
    sample_count: int
    sample_dollars: float
    overall_count_coverage: float
    overall_dollar_coverage: float
    selection_rationale: str
    coverage: list[SegmentCoverage]
    results: str
    non_extrapolable: str = NON_EXTRAPOLABLE
    selected_loan_ids: list[str] = field(default_factory=list)


def build_doc(df: pd.DataFrame, selected_ids, dimension: str,
              scheme: bands.BandScheme | None = None,
              risk_threshold_dpd: int = 90,
              results: str = "(reviewer to record exceptions found)",
              weight: str = "current_balance") -> SamplingDoc:
    """Assemble the OCC-required documentation from the reviewer's selection."""
    # sorted() -> deterministic order regardless of the caller passing a set
    # (byte-identical builds must not depend on set-iteration/hash-seed order).
    selected = sorted(str(x) for x in selected_ids)
    ranked = rank_segments(df, dimension, scheme, risk_threshold_dpd, weight=weight)
    cov = coverage_by_segment(df, selected, dimension, scheme, risk_threshold_dpd, weight)

    areas = [f"{r.value} (risk ${r.risk_balance:,.0f}, "
             f"{r.risk_dollar_rate:.0%} of segment)"
             for r in ranked if r.flagged]
    sel_mask = df["loan_id"].isin(set(selected))
    sample_c = int(sel_mask.sum())
    sample_b = float(df.loc[sel_mask, weight].astype("float64").sum())
    pop_c = int(len(df))
    pop_b = float(df[weight].astype("float64").sum())

    rationale = (
        f"Population stratified by {dimension!r}; high-risk cells "
        f"(>= {risk_threshold_dpd} DPD exposure) prioritized. The reviewer "
        f"selected {sample_c} loan(s) by loan number, concentrating coverage in "
        f"the flagged segment(s). Per-segment penetration is documented below.")

    return SamplingDoc(
        pop_c, pop_b, areas, sample_c, sample_b,
        (sample_c / pop_c) if pop_c else 0.0,
        (sample_b / pop_b) if pop_b else 0.0,
        rationale, cov, results, NON_EXTRAPOLABLE, selected)
