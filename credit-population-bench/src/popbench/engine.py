"""The one-button flow: map -> clean -> compute -> assemble.

Ties the pure layers together into the single deterministic run the ``.xlsm``
button triggers. Kept thin: each step is its own tested module; this just
sequences them and shapes the result for the workbook.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from popbench import (bands, cleaning, cohorts as cohorts_mod, contract,
                      delinquency, metrics, rolls, sampling, strata, vintage)
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
    sampling_doc: object | None = None          # sampling.SamplingDoc


def run_analysis(raw: pd.DataFrame, mapping: Mapping,
                 attributes: list[str] | None = None,
                 status_map: dict[str, str] | None = None,
                 cohort_specs: list | None = None,
                 sample_selection=None,
                 sample_dimension: str = "product_type") -> AnalysisResult:
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

    sampling_doc = None
    if sample_selection is not None and sample_dimension in clean.columns:
        sampling_doc = sampling.build_doc(clean, sample_selection, sample_dimension)

    return AnalysisResult(clean, records, pop, wa, delq, urccp, strats, cohort_cmp,
                          charge_off, vintage_rows, triangle, roll, sampling_doc)


def _default_stratifications(clean: pd.DataFrame,
                             mapping: Mapping) -> list[strata.Stratification]:
    """A sensible default set for the demo/output: by product, and by the CFPB
    FICO band when those fields are present. Real runs drive the dimension list
    from ``_config``; the group-by API accepts any mapped field or band scheme."""
    out: list[strata.Stratification] = []
    for dim in ("product_type", "channel", "state"):
        if mapping.has(dim):
            try:
                out.append(strata.group_by(clean, dim))
            except strata.CardinalityError:
                pass   # too many distinct values to auto-stratify; still cohortable
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
          cohort_specs: list | None = None,
          sample_selection=None,
          sample_dimension: str = "product_type") -> bytes:
    """Full run to deterministic workbook bytes.

    ``sample_selection`` is the reviewer's judgmental pick. When None, the
    workbook seeds the Selection tab with the tool's high-risk flags (>=90 DPD)
    as a starting suggestion the reviewer adjusts in Excel; the button reads that
    column back (see :func:`popbench.roundtrip.run_workbook`)."""
    result = run_analysis(raw, mapping, attributes, status_map=status_map,
                          cohort_specs=cohort_specs,
                          sample_selection=sample_selection,
                          sample_dimension=sample_dimension)

    # Seed a default judgmental selection (high-risk) if the reviewer hasn't
    # marked one yet, so the shipped workbook is operable, not empty.
    selection = set(sample_selection) if sample_selection is not None else set()
    sampling_doc = result.sampling_doc
    can_sample = "dpd_min" in result.clean.columns and sample_dimension in result.clean.columns
    if sampling_doc is None and can_sample:
        selection = set(result.clean.loc[result.clean["dpd_min"] >= 90, "loan_id"])
        sampling_doc = sampling.build_doc(result.clean, selection, sample_dimension)

    # Only emit the editable tabs when they apply: Selection when a sample can be
    # computed, _cohorts when cohorts are defined.
    selection_rows = (_selection_rows(result.clean, selection, sample_dimension)
                      if sampling_doc is not None else None)
    cohort_rows = _cohort_rows(cohort_specs) if cohort_specs else None

    wb = build_workbook(
        raw=raw,                         # Raw_Input = the file as loaded (round-trips)
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
        sampling_doc=sampling_doc,
        selection_rows=selection_rows,
        cohort_rows=cohort_rows,
    )
    return workbook_bytes(wb)


def _selection_rows(clean: pd.DataFrame, selection: set, dimension: str):
    """One editable row per loan for the Selection tab: loan_id + SELECT (Y/N,
    seeded) + guide columns (segment, DPD bucket, balance, risk flag)."""
    has_dpd = "dpd_min" in clean.columns
    rows = []
    for _, row in clean.iterrows():
        lid = row["loan_id"]
        seg = row[dimension] if dimension in clean.columns else ""
        bucket = row["dpd_bucket_canon"] if "dpd_bucket_canon" in clean.columns else None
        rows.append((
            lid, "Y" if lid in selection else "",
            "" if (seg is None or seg != seg) else str(seg),
            delinquency.BUCKET_LABEL.get(bucket, "") if bucket else "",
            float(row["current_balance"]),
            "HIGH-RISK" if (has_dpd and row["dpd_min"] >= 90) else ""))
    return rows


def _cohort_rows(cohort_specs):
    """Flatten cohorts to editable ``_cohorts`` rows (id, label, group, field,
    op, value) so the definitions travel in the workbook and round-trip."""
    rows = []
    for c in (cohort_specs or []):
        for rule in c.rules:
            rows.append((c.id, c.label, "" if rule.group is None else str(rule.group),
                         rule.field, rule.op, "" if rule.value is None else rule.value))
    return rows
