"""Roll-forward / proforma: carry standing data and carryforwards into next year.

Drake computes carryforwards and basis; the mart STORES and CARRIES them so the
practice always holds each client's record-level data year to year and can seed
next year without re-keying. This module produces the proforma seed for year Y+1
from the mart as of year Y:

  * open carryforwards (NOL, capital-loss, §179, passive, charitable, AMT credit,
    QBI, state/federal overpayment applied, FTC) advance to the next year unless
    consumed or expired;
  * per-owner basis / capital-account ENDING balances become next year's BEGINNING
    balances (1120-S / 1065);
  * standing client data carries by reference (client_id).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from satc.models.mart import Carryforward, DataMart, OwnerBasis
from satc.models.provenance import Provenance, SourceRef


@dataclass(slots=True)
class ProformaSeed:
    """The seed for one client's next-year return."""

    client_id: str
    to_year: int
    carryforwards: list[Carryforward] = field(default_factory=list)
    owner_basis_beginning: list[OwnerBasis] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _carryforward_open(cf: Carryforward, from_year: int, to_year: int) -> bool:
    if cf.applied_to_year is not None:
        return False  # already consumed
    if cf.tax_year_generated > from_year:
        return False  # not yet arisen as of from_year
    if cf.expires_after_year is not None and cf.expires_after_year < to_year:
        return False  # expired before the target year
    return cf.amount != 0


def roll_forward(mart: DataMart, *, from_year: int, to_year: int) -> dict[str, ProformaSeed]:
    """Build per-client proforma seeds for ``to_year`` from the mart as of ``from_year``."""
    seeds: dict[str, ProformaSeed] = {}

    def seed_for(client_id: str) -> ProformaSeed:
        return seeds.setdefault(client_id, ProformaSeed(client_id=client_id, to_year=to_year))

    cf_prov = Provenance(
        source_kind="PRIOR_YEAR_CARRYFORWARD", confidence="HIGH",
        source_ref=SourceRef(citation=f"Carried from {from_year} via data mart"),
        note="Proforma roll-forward")

    for cf in mart.carryforwards:
        if _carryforward_open(cf, from_year, to_year):
            seed = seed_for(cf.client_id)
            seed.carryforwards.append(replace(
                cf, cf_id=f"{cf.cf_id}->{to_year}", applied_to_year=None, provenance=cf_prov))

    for ob in mart.owner_basis:
        if ob.tax_year == from_year:
            seed = seed_for(ob.client_id)
            seed.owner_basis_beginning.append(OwnerBasis(
                return_key=ob.return_key, client_id=ob.client_id, owner_id=ob.owner_id,
                tax_year=to_year, beginning_balance=ob.ending_balance,
                debt_basis_beginning=ob.debt_basis_ending, ownership_pct=ob.ownership_pct,
                provenance=cf_prov))

    for seed in seeds.values():
        seed.notes.append(
            f"{len(seed.carryforwards)} carryforward(s) and "
            f"{len(seed.owner_basis_beginning)} basis/capital opening balance(s) seeded into {to_year}.")
    return seeds
