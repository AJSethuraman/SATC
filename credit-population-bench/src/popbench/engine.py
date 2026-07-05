"""The one-button flow: map -> clean -> compute -> assemble.

Ties the pure layers together into the single deterministic run the ``.xlsm``
button triggers. Kept thin: each step is its own tested module; this just
sequences them and shapes the result for the workbook.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from popbench import cleaning, metrics
from popbench.mapping import Mapping
from popbench.workbook import build_workbook, workbook_bytes


@dataclass(frozen=True)
class AnalysisResult:
    clean: pd.DataFrame
    cleaning: list[cleaning.CleaningRecord]
    population: dict
    wa: list[metrics.WAResult]


def run_analysis(raw: pd.DataFrame, mapping: Mapping,
                 attributes: list[str] | None = None) -> AnalysisResult:
    """Validate/clean the population, then compute headline metrics.

    ``attributes`` are the WA attributes to report (default: every feature-gated
    attribute the mapping actually carries). Raises
    :class:`~popbench.cleaning.CleaningError` if the population isn't clean.
    """
    attributes = attributes if attributes is not None else _default_attributes(mapping)
    required = tuple(a for a in attributes if mapping.has(a))
    clean, records = cleaning.validate_and_clean(raw, mapping, required_fields=())
    pop = metrics.population_totals(clean)
    wa = metrics.weighted_average_table(clean, list(attributes))
    return AnalysisResult(clean, records, pop, wa)


def _default_attributes(mapping: Mapping) -> list[str]:
    # Slice 1: FICO is the demonstrated attribute; later slices widen this.
    return [a for a in ("fico_orig",) if mapping.has(a)]


def build(raw: pd.DataFrame, mapping: Mapping,
          attributes: list[str] | None = None) -> bytes:
    """Full run to deterministic workbook bytes."""
    result = run_analysis(raw, mapping, attributes)
    wb = build_workbook(
        raw=result.clean,
        map_rows=mapping.as_rows(),
        cleaning_rows=[(r.rule, r.column, r.rows_affected, r.detail)
                       for r in result.cleaning],
        population=result.population,
        wa_rows=[(w.attribute, w.dollar_weighted, w.count_weighted,
                  w.n, w.coverage_dollars, w.note) for w in result.wa],
    )
    return workbook_bytes(wb)
