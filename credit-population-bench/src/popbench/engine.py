"""The one-button flow: map -> clean -> compute -> assemble.

Ties the pure layers together into the single deterministic run the ``.xlsm``
button triggers. Kept thin: each step is its own tested module; this just
sequences them and shapes the result for the workbook.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from popbench import (bands, cleaning, cohorts as cohorts_mod, contract,
                      delinquency, metrics, rolls, strata, vintage)
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
    stratifications: list[strata.Stratification] | None = None
    cohorts: object | None = None   # cohorts_mod.CohortComparison
    charge_off: object | None = None            # vintage.GrossChargeOff
    vintage_rows: list | None = None            # list[vintage.VintageRow]
    triangle: object | None = None              # vintage.Triangle
    roll: object | None = None                  # rolls.RollMatrix


def run_analysis(raw: pd.DataFrame, mapping: Mapping,
                 attributes: list[str] | None = None,
                 status_map: dict[str, str] | None = None,
                 cohort_specs: list | None = None) -> AnalysisResult:
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

    strats = _default_stratifications(clean, mapping)
    cohort_cmp = cohorts_mod.evaluate(clean, cohort_specs) if cohort_specs else None

    # Time lenses — each produced only when its fields are present.
    charge_off = vintage_rows = triangle = roll = None
    has_loss = mapping.has("chargeoff_flag") and mapping.has("chargeoff_balance")
    if has_loss:
        charge_off = vintage.gross_charge_off_rate(clean)
    if mapping.has("orig_date"):
        vintage_rows = vintage.vintage_summary(clean, grain="year")
        if mapping.has("chargeoff_date") and mapping.has("chargeoff_balance"):
            triangle = vintage.loss_triangle(clean, grain="year")
    if mapping.has("prior_dpd_bucket") and "dpd_bucket_canon" in clean.columns:
        roll = rolls.roll_matrix(clean)

    return AnalysisResult(clean, records, pop, wa, delq, urccp, strats, cohort_cmp,
                          charge_off, vintage_rows, triangle, roll)


def _default_stratifications(clean: pd.DataFrame,
                             mapping: Mapping) -> list[strata.Stratification]:
    """A sensible default set for the demo/output: by product, and by the CFPB
    FICO band when those fields are present. Real runs drive the dimension list
    from ``_config``; the group-by API accepts any mapped field or band scheme."""
    out: list[strata.Stratification] = []
    if mapping.has("product_type"):
        out.append(strata.group_by(clean, "product_type"))
    if mapping.has("fico_orig"):
        out.append(strata.group_by(clean, "fico_orig",
                                   scheme=bands.get_preset("fico_orig", "cfpb")))
    return out


def _default_attributes(mapping: Mapping) -> list[str]:
    # Every mapped weighted-average attribute the contract knows about.
    candidates = ("fico_orig", "ltv")
    return [a for a in candidates if mapping.has(a)]


def build(raw: pd.DataFrame, mapping: Mapping,
          attributes: list[str] | None = None,
          status_map: dict[str, str] | None = None,
          cohort_specs: list | None = None) -> bytes:
    """Full run to deterministic workbook bytes."""
    result = run_analysis(raw, mapping, attributes, status_map=status_map,
                          cohort_specs=cohort_specs)
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
        stratifications=result.stratifications,
        cohort_comparison=result.cohorts,
        charge_off=result.charge_off,
        vintage_rows=result.vintage_rows,
        triangle=result.triangle,
        roll=result.roll,
    )
    return workbook_bytes(wb)
