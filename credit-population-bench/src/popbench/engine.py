"""The one-button flow: map -> clean -> compute -> assemble.

Ties the pure layers together into the single deterministic run the ``.xlsm``
button triggers. Kept thin: each step is its own tested module; this just
sequences them and shapes the result for the workbook.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from popbench import cleaning, contract, delinquency, metrics
from popbench.mapping import Mapping
from popbench.workbook import build_workbook, workbook_bytes


@dataclass(frozen=True)
class AnalysisResult:
    clean: pd.DataFrame
    cleaning: list[cleaning.CleaningRecord]
    population: dict
    wa: list[metrics.WAResult]
    delinquency: dict | None = None
    urccp: list[delinquency.ClassRow] | None = None


def run_analysis(raw: pd.DataFrame, mapping: Mapping,
                 attributes: list[str] | None = None,
                 status_map: dict[str, str] | None = None) -> AnalysisResult:
    """Validate/clean the population, then compute the metrics its mapped fields
    support: weighted averages always; delinquency rates when a delinquency
    signal is mapped; URCCP classification when a structure field is mapped too.

    Feature-gated analyses that lack their fields are simply not produced (the
    named-missing-field refusal is raised by the delinquency module when a
    caller *requests* one explicitly). Raises
    :class:`~popbench.cleaning.CleaningError` if the population isn't clean.
    """
    attributes = attributes if attributes is not None else _default_attributes(mapping)

    delq_available = any(mapping.has(f) for f in contract.DELINQUENCY_FORMS)
    required: set[str] = set()
    if delq_available:
        required.add(delinquency.delinquency_form(mapping))   # signal must be present
    if mapping.has("structure"):
        required.add("structure")

    clean, records = cleaning.validate_and_clean(
        raw, mapping, required_fields=tuple(sorted(required)))
    pop = metrics.population_totals(clean)
    wa = metrics.weighted_average_table(clean, list(attributes))

    delq = None
    urccp = None
    if delq_available:
        clean, drecs = delinquency.normalize(clean, mapping, status_map=status_map)
        records = records + drecs
        delq = delinquency.delinquency_rates(clean)
        if mapping.has("structure"):
            urccp = delinquency.classify_urccp(clean)

    return AnalysisResult(clean, records, pop, wa, delq, urccp)


def _default_attributes(mapping: Mapping) -> list[str]:
    # Every mapped weighted-average attribute the contract knows about.
    candidates = ("fico_orig", "ltv")
    return [a for a in candidates if mapping.has(a)]


def build(raw: pd.DataFrame, mapping: Mapping,
          attributes: list[str] | None = None,
          status_map: dict[str, str] | None = None) -> bytes:
    """Full run to deterministic workbook bytes."""
    result = run_analysis(raw, mapping, attributes, status_map=status_map)
    wb = build_workbook(
        raw=result.clean,
        map_rows=mapping.as_rows(),
        cleaning_rows=[(r.rule, r.column, r.rows_affected, r.detail)
                       for r in result.cleaning],
        population=result.population,
        wa_rows=[(w.attribute, w.dollar_weighted, w.count_weighted,
                  w.n, w.coverage_dollars, w.note) for w in result.wa],
        delinquency_result=result.delinquency,
        urccp_rows=result.urccp,
    )
    return workbook_bytes(wb)
