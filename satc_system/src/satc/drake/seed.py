"""Seed the data mart from a parsed Drake preparer set (no re-keying).

The Comparison page populates the client's record-level line items; the Carryover
page populates next-year carryforwards. Returns the new records so the caller can
route them through the staging/confirmation gate before committing to the mart.
"""

from __future__ import annotations

from decimal import Decimal

from satc.drake.preparer_set_parser import PreparerSet
from satc.ids import line_item_key, return_key
from satc.models.mart import Carryforward, DataMart, LineItem
from satc.models.provenance import Provenance, SourceRef


def seed_records(ps: PreparerSet, *, return_type: str = "1040", jurisdiction: str = "US"
                 ) -> tuple[list[LineItem], list[Carryforward]]:
    """Build (line_items, carryforwards) from the comparison + carryover pages."""
    rk = return_key(ps.client_id, ps.tax_year, return_type, jurisdiction)
    prov_cmp = Provenance(source_kind="DRAKE_OUTPUT",
                          source_ref=SourceRef(worksheet_title="Tax Return Comparison"))
    prov_cf = Provenance(source_kind="DRAKE_OUTPUT",
                         source_ref=SourceRef(worksheet_title="Carryover Worksheet"))

    line_items: list[LineItem] = []
    current = next((c for c in ps.comparison if c.year == ps.tax_year), None)
    if current:
        for key, amount in current.values.items():
            line_items.append(LineItem(
                line_item_key=line_item_key(rk, "1040", key), return_key=rk,
                schedule="1040", line_code=key, label=key.replace("_", " ").title(),
                amount=Decimal(str(amount)), provenance=prov_cmp))

    carryforwards: list[Carryforward] = []
    for item in ps.carryovers:
        carryforwards.append(Carryforward(
            cf_id=f"CF-{ps.client_id}-{item.kind}-{ps.tax_year}", client_id=ps.client_id,
            return_type=return_type, jurisdiction=jurisdiction, kind=item.kind,
            tax_year_generated=ps.tax_year, amount=Decimal(str(item.amount)), provenance=prov_cf))
    return line_items, carryforwards


def seed_data_mart(mart: DataMart, ps: PreparerSet, *, return_type: str = "1040") -> int:
    """Apply the seed to the mart, de-duplicating by key. Returns records added."""
    line_items, carryforwards = seed_records(ps, return_type=return_type)
    existing_li = {li.line_item_key for li in mart.line_items}
    existing_cf = {cf.cf_id for cf in mart.carryforwards}
    added = 0
    for li in line_items:
        if li.line_item_key not in existing_li:
            mart.line_items.append(li)
            added += 1
    for cf in carryforwards:
        if cf.cf_id not in existing_cf:
            mart.carryforwards.append(cf)
            added += 1
    return added
