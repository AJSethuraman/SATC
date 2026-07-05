"""Group-by stratification — a partition of the population, per-cell metrics.

Group the clean population by a mapped dimension (product, structure, channel,
a delinquency bucket) or by a band derived from a numeric field (FICO/DTI/LTV
via a :class:`~popbench.bands.BandScheme`). Each cell reports its count,
balance, and the full weighted-average set on both bases. Because a group-by is
a genuine partition, the cells reconcile to the population total — the tool
asserts that (unlike derived cohorts, which overlap; that is Slice 5).

A cardinality guard refuses a group-by on a dimension with too many distinct
values (e.g. an id-like ad-hoc tail column) rather than emitting thousands of
one-loan cells.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from popbench import bands, contract, metrics

# Attributes reported per cell (those present in the frame are used).
WA_ATTRIBUTES = ("fico_orig", "fico_refresh", "dti", "rate", "ltv", "orig_amount")
DEFAULT_MAX_CARDINALITY = 50
_DERIVED_COLS = {"dpd_bucket_canon", "dpd_min"}


def slice_dimensions(df: pd.DataFrame) -> list[str]:
    """Columns usable as a group-by dimension: canonical optional-slice fields
    (product, channel, state, structure) plus any ad-hoc tail column — excluding
    weights, attributes, derived columns, and internal helpers."""
    dims: list[str] = []
    for c in df.columns:
        if c.startswith("__") or c in _DERIVED_COLS:
            continue
        f = contract._BY_ID.get(c)
        if f is None:                       # ad-hoc tail column
            dims.append(c)
        elif f.role == contract.OPTIONAL_SLICE:
            dims.append(c)
    return dims


class CardinalityError(ValueError):
    """A group-by dimension has more distinct values than the guard allows."""


@dataclass(frozen=True)
class Cell:
    value: str
    count: int
    balance: float
    wa: list[metrics.WAResult]


@dataclass(frozen=True)
class Stratification:
    dimension: str            # the column or band-scheme name grouped on
    cells: list[Cell]
    total_count: int
    total_balance: float
    reconciles: bool          # cells sum back to the population


def _attrs_present(df: pd.DataFrame) -> list[str]:
    return [a for a in WA_ATTRIBUTES if a in df.columns]


def group_by(df: pd.DataFrame, dimension: str,
             scheme: bands.BandScheme | None = None,
             weight: str = "current_balance",
             max_cardinality: int = DEFAULT_MAX_CARDINALITY) -> Stratification:
    """Partition ``df`` by ``dimension`` (or by ``scheme`` applied to its field).

    LTV self-suppresses where a cell has no secured exposure (its LTV rows are
    null), which falls out of the weighted-average's null handling.
    """
    work = df.copy()
    if scheme is not None:
        col = f"__band__{scheme.field}"
        work[col] = scheme.assign(work[scheme.field])
        group_col, label = col, scheme.name
    else:
        if dimension not in work.columns:
            raise KeyError(f"group-by dimension {dimension!r} is not a mapped column")
        group_col, label = dimension, dimension

    nun = int(work[group_col].nunique(dropna=True))
    if nun > max_cardinality:
        raise CardinalityError(
            f"dimension {label!r} has {nun} distinct values (> {max_cardinality}); "
            f"band it or raise the cap — refusing to emit {nun} cells")

    attrs = _attrs_present(work)
    cells: list[Cell] = []
    # observed=True keeps only non-empty categorical bands; sort for determinism.
    grouped = work.groupby(group_col, observed=True, dropna=False)
    for value, grp in grouped:
        disp = "(unbanded)" if (value is None or (isinstance(value, float) and math.isnan(value))) else str(value)
        cells.append(Cell(
            disp, int(len(grp)),
            float(grp[weight].astype("float64").sum()),
            metrics.weighted_average_table(grp, attrs, weight)))
    cells.sort(key=lambda c: c.value)

    tot_n = int(len(work))
    tot_bal = float(work[weight].astype("float64").sum())
    recon = (sum(c.count for c in cells) == tot_n
             and math.isclose(sum(c.balance for c in cells), tot_bal, rel_tol=1e-9))
    return Stratification(label, cells, tot_n, tot_bal, recon)
