"""Derived cohorts — structured rules, compiled safely, honestly reconciled.

A cohort is a named set of **structured rule rows** (``field | op | value``),
never free text — so there is no ``eval``/``query`` and nothing arbitrary to
execute. Rules with the same ``group`` are OR-ed into one clause; distinct
groups (and ungrouped rules) are AND-ed. Rules compile to pandas boolean masks
through a fixed operator whitelist.

Because cohorts are arbitrary predicates they **overlap** and leave **gaps** —
unlike a group-by partition. This module therefore reports each cohort
**independently**, and always alongside a **pairwise overlap matrix** ($ and
count) and an **"in no cohort" residual**, so double-counting and gaps are
visible instead of silently summed.

Missing-data stance (PRD Q7): a rule that compares a field with null values is a
**hard error** — cohorts run on a clean population. Only the explicit
``is_null``/``not_null`` operators may see nulls.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field as dc_field
from functools import reduce

import pandas as pd

from popbench import metrics

# Operator whitelist — the only things a rule can do. No eval, ever.
_COMPARISON_OPS = {
    "<": lambda s, v: s < v,
    "<=": lambda s, v: s <= v,
    ">": lambda s, v: s > v,
    ">=": lambda s, v: s >= v,
    "==": lambda s, v: s == v,
    "!=": lambda s, v: s != v,
    "in": lambda s, v: s.isin(list(v)),
    "not_in": lambda s, v: ~s.isin(list(v)),
    "between": lambda s, v: s.between(v[0], v[1]),
}
_NULL_OPS = {
    "is_null": lambda s, v: s.isna(),
    "not_null": lambda s, v: s.notna(),
}
OPS = tuple(_COMPARISON_OPS) + tuple(_NULL_OPS)


class CohortError(ValueError):
    """A cohort references an unknown field/op, or compares a field with nulls."""


@dataclass(frozen=True)
class Rule:
    field: str
    op: str
    value: object = None
    group: object = None      # rules sharing a group are OR-ed


@dataclass(frozen=True)
class Cohort:
    id: str
    label: str
    rules: tuple[Rule, ...] = dc_field(default_factory=tuple)


def _rule_mask(df: pd.DataFrame, rule: Rule) -> pd.Series:
    if rule.field not in df.columns:
        raise CohortError(f"rule references unmapped field {rule.field!r}")
    if rule.op not in OPS:
        raise CohortError(f"unknown operator {rule.op!r}; allowed: {OPS}")
    col = df[rule.field]
    if rule.op in _NULL_OPS:
        return _NULL_OPS[rule.op](col, rule.value)
    if col.isna().any():
        n = int(col.isna().sum())
        raise CohortError(
            f"field {rule.field!r} has {n} null value(s); a cohort comparison "
            f"needs a clean field — filter/map it upstream (or use is_null)")
    return _COMPARISON_OPS[rule.op](col, rule.value)


def compile_mask(df: pd.DataFrame, cohort: Cohort) -> pd.Series:
    """Boolean membership mask for ``cohort`` over ``df``. AND of clauses, where
    same-group rules OR into one clause."""
    and_masks: list[pd.Series] = []
    groups: dict[object, list[pd.Series]] = defaultdict(list)
    for rule in cohort.rules:
        m = _rule_mask(df, rule)
        if rule.group is None:
            and_masks.append(m)
        else:
            groups[rule.group].append(m)
    for masks in groups.values():
        and_masks.append(reduce(lambda a, b: a | b, masks))
    if not and_masks:
        return pd.Series(True, index=df.index)
    return reduce(lambda a, b: a & b, and_masks)


@dataclass(frozen=True)
class CohortReport:
    id: str
    label: str
    count: int
    balance: float
    wa: list[metrics.WAResult]


@dataclass(frozen=True)
class CohortComparison:
    reports: list[CohortReport]
    overlap_count: dict[tuple[str, str], int]      # pairwise (id_a,id_b) -> n
    overlap_dollars: dict[tuple[str, str], float]
    residual_count: int                             # loans in NO cohort
    residual_dollars: float
    population_count: int
    population_dollars: float


def evaluate(df: pd.DataFrame, cohorts: list[Cohort],
             weight: str = "current_balance",
             attributes=("fico_orig", "dti", "rate", "ltv")) -> CohortComparison:
    """Report each cohort independently, plus the overlap matrix and residual."""
    attrs = [a for a in attributes if a in df.columns]
    masks = {c.id: compile_mask(df, c) for c in cohorts}

    reports = []
    for c in cohorts:
        m = masks[c.id]
        sub = df[m]
        reports.append(CohortReport(
            c.id, c.label, int(m.sum()),
            float(sub[weight].astype("float64").sum()),
            metrics.weighted_average_table(sub, attrs, weight)))

    overlap_n: dict[tuple[str, str], int] = {}
    overlap_d: dict[tuple[str, str], float] = {}
    ids = [c.id for c in cohorts]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            inter = masks[a] & masks[b]
            overlap_n[(a, b)] = int(inter.sum())
            overlap_d[(a, b)] = float(df.loc[inter, weight].astype("float64").sum())

    any_mask = reduce(lambda x, y: x | y, masks.values()) if masks \
        else pd.Series(False, index=df.index)
    residual = ~any_mask
    return CohortComparison(
        reports, overlap_n, overlap_d,
        int(residual.sum()), float(df.loc[residual, weight].astype("float64").sum()),
        int(len(df)), float(df[weight].astype("float64").sum()))


# --- A/B subgroup comparison ------------------------------------------------

@dataclass(frozen=True)
class ABAttr:
    attribute: str
    a_dollar: float | None
    a_count: float | None
    b_dollar: float | None
    b_count: float | None
    diverges: bool          # dollar vs count basis disagree on A-vs-B direction


def ab_compare(df: pd.DataFrame, cohort_a: Cohort, cohort_b: Cohort,
               attributes=("fico_orig", "dti", "rate", "ltv"),
               weight: str = "current_balance") -> list[ABAttr]:
    """Compare two subgroups on both weightings, flagging where the dollar and
    count bases disagree on which group is higher (the reason both ship)."""
    ma, mb = compile_mask(df, cohort_a), compile_mask(df, cohort_b)
    a, b = df[ma], df[mb]
    out = []
    for attr in attributes:
        if attr not in df.columns:
            continue
        wa_a = metrics.weighted_average(a, attr, weight)
        wa_b = metrics.weighted_average(b, attr, weight)
        diverges = False
        if None not in (wa_a.dollar_weighted, wa_b.dollar_weighted,
                        wa_a.count_weighted, wa_b.count_weighted):
            dollar_dir = wa_a.dollar_weighted - wa_b.dollar_weighted
            count_dir = wa_a.count_weighted - wa_b.count_weighted
            diverges = (dollar_dir > 0) != (count_dir > 0) and dollar_dir != 0 and count_dir != 0
        out.append(ABAttr(attr, wa_a.dollar_weighted, wa_a.count_weighted,
                          wa_b.dollar_weighted, wa_b.count_weighted, diverges))
    return out
