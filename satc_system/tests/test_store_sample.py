"""Sample-data lifecycle: seed once, delete a client everywhere, stay cleared."""

from __future__ import annotations

from satc.fixtures import synthetic_identities
from satc.intake.service import create_engagement, create_person_client
from satc.persistence import SATCStore


def _sample_ids() -> set[str]:
    return {rec.client_id for rec in synthetic_identities()}


def test_seed_runs_once_and_stays_cleared(tmp_path):
    store = SATCStore(tmp_path)
    assert store.seed_if_empty() is True            # first run seeds
    present = {pc.client_id for pc in store.load_mart().public_clients}
    assert _sample_ids() & present

    for cid in _sample_ids():                        # clear the sample clients
        store.delete_client(cid)

    # Re-opening the same store must NOT re-seed (the marker persists).
    store2 = SATCStore(tmp_path)
    assert store2.seed_if_empty() is False
    present2 = {pc.client_id for pc in store2.load_mart().public_clients}
    assert not (_sample_ids() & present2)


def test_delete_client_removes_it_from_vault_and_mart(tmp_path):
    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Z", last_name="Q", ssn="111-22-3333")
    create_engagement(store, client_id=cid, workflow_key="personal_1040_core",
                      due_date="2026-04-15", tax_year=2025, answers={"newSatcClient": "yes"})

    store.delete_client(cid)

    assert cid not in store.names()                                  # vault gone
    assert all(pc.client_id != cid for pc in store.load_mart().public_clients)
    assert all(e.client_id != cid for e in store.load_intake_engagements())
    assert all(d.client_id != cid for d in store.load_mart().documents)
