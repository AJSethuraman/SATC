"""Build a normalized annual financial panel from parsed facts.

One row per company per fiscal-year label. Every value carries provenance
(CIK, accession, tag, period, form, filed date) and every derivation
(total debt, EBITDA) records its components and any gaps. Values are USD
raw units throughout -- EDGAR XBRL is not reported in thousands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .parse import Fact, annual_period_ends, dedupe_facts, extract_facts, select_annual
from .tags import CONCEPTS


@dataclass
class PanelValue:
    value: float
    provenance: list[dict]      # one entry per contributing fact
    notes: list[str] = field(default_factory=list)


@dataclass
class PanelRow:
    cik: int
    entity: str
    sic: Optional[int]
    fy: int                     # fiscal-year label (see parse.fiscal_year_label)
    fye: Optional[str]          # actual period end date, ISO
    values: dict[str, PanelValue] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)

    def get(self, key: str) -> Optional[float]:
        pv = self.values.get(key)
        return pv.value if pv else None

    def as_plain_dict(self) -> dict:
        d = {k: v.value for k, v in self.values.items()}
        d.update({"cik": self.cik, "fy": self.fy})
        return d


def _pv_from_fact(f: Fact, notes: Optional[list[str]] = None) -> PanelValue:
    return PanelValue(value=f.val, provenance=[f.provenance()], notes=notes or [])


def derive_total_debt(row: PanelRow) -> None:
    """Total debt = noncurrent LTD + current debt, assembled from whatever
    components the filer tagged, without double counting.

    Preference order for the current piece: DebtCurrent (already the total)
    else current-portion LTD + short-term borrowings. If only the combined
    LongTermDebt tag exists, use it and flag the basis ambiguity (it may or
    may not include the current portion depending on the filer).
    """
    notes: list[str] = []
    prov: list[dict] = []

    ltd_nc = row.values.get("lt_debt_noncurrent")
    ltd_combined = row.values.get("lt_debt_combined")
    debt_cur_total = row.values.get("debt_current_total")
    ltd_cur = row.values.get("lt_debt_current")
    stb = row.values.get("short_term_borrowings")

    if debt_cur_total is not None:
        current = debt_cur_total.value
        prov += debt_cur_total.provenance
    else:
        current = 0.0
        if ltd_cur is not None:
            current += ltd_cur.value
            prov += ltd_cur.provenance
        if stb is not None:
            current += stb.value
            prov += stb.provenance
        if ltd_cur is None and stb is None:
            notes.append("no current-debt tags found; current portion assumed 0")

    if ltd_nc is not None:
        total = ltd_nc.value + current
        prov = ltd_nc.provenance + prov
    elif ltd_combined is not None:
        total = ltd_combined.value + (current if debt_cur_total is None else current)
        prov = ltd_combined.provenance + prov
        notes.append(
            "built from combined LongTermDebt tag; filer practice varies on "
            "whether it includes the current portion -- possible double count "
            "or understatement; comparability note applies"
        )
    elif current > 0:
        total = current
        notes.append("no long-term debt tags found; total debt = current debt only")
    else:
        row.gaps.append("total_debt: no debt tags found (cannot distinguish "
                        "debt-free from untagged)")
        return

    row.values["total_debt"] = PanelValue(value=total, provenance=prov, notes=notes)


def derive_ebitda(row: PanelRow) -> None:
    """EBITDA = operating income + D&A. Standard, addback-free normalization;
    the basis difference vs. sponsor-adjusted private EBITDA is a documented
    comparability note at the benchmark level."""
    oi = row.values.get("operating_income")
    da = row.values.get("depreciation_amortization")
    if oi is None:
        row.gaps.append("ebitda: operating income missing; EBITDA not computed")
        return
    notes: list[str] = []
    prov = list(oi.provenance)
    if da is None:
        row.gaps.append("ebitda: D&A missing; EBITDA approximated by operating "
                        "income only (understated)")
        notes.append("D&A unavailable: EBITDA = operating income (understated)")
        val = oi.value
    else:
        val = oi.value + da.value
        prov += da.provenance
    row.values["ebitda"] = PanelValue(value=val, provenance=prov, notes=notes)


def build_company_panel(
    companyfacts: dict,
    sic: Optional[int] = None,
    min_fy: int = 2010,
) -> list[PanelRow]:
    """CompanyFacts JSON -> one PanelRow per fiscal year.

    XBRL was phased in 2009-2011, so history before ~2010 is unreliable;
    rows earlier than ``min_fy`` are dropped.
    """
    facts = dedupe_facts(extract_facts(companyfacts))
    if not facts:
        return []
    fye_by_label = annual_period_ends(facts)

    cik = int(companyfacts["cik"])
    entity = companyfacts.get("entityName", "")

    per_concept: dict[str, dict[int, Fact]] = {}
    concept_notes: dict[str, list[str]] = {}
    for concept in CONCEPTS:
        sel, notes = select_annual(facts, concept, fiscal_year_ends=fye_by_label)
        per_concept[concept] = sel
        concept_notes[concept] = notes

    all_years = sorted({fy for sel in per_concept.values() for fy in sel
                        if fy >= min_fy})
    rows: list[PanelRow] = []
    for fy in all_years:
        row = PanelRow(
            cik=cik, entity=entity, sic=sic, fy=fy,
            fye=fye_by_label[fy].isoformat() if fy in fye_by_label else None,
        )
        for concept, sel in per_concept.items():
            f = sel.get(fy)
            if f is not None:
                row.values[concept] = _pv_from_fact(f, list(concept_notes[concept]))
            elif CONCEPTS[concept].core:
                row.gaps.append(f"{concept}: no usable annual fact for FY{fy}")
        derive_total_debt(row)
        derive_ebitda(row)
        rows.append(row)
    # Drop years with no income statement at all (instant-only stub years,
    # typically the comparative balance-sheet column of the first filing).
    rows = [r for r in rows if r.get("revenue") is not None
            or r.get("operating_income") is not None]
    return rows
