"""Tests for the SQLite store of record (durability + vault/mart separation)."""

from __future__ import annotations

from openpyxl import load_workbook

from satc.fixtures import synthetic_identities
from satc.persistence import SATCStore, export_mart_to_excel


def test_status_change_survives_a_restart(tmp_path):
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    doc = next(d for d in store.load_mart().documents if d.status == "Requested")
    store.set_document_status(doc.document_id, "Received")
    store.close()

    # Reopen the same directory — a fresh process would see exactly this.
    store2 = SATCStore(tmp_path)
    reloaded = {d.document_id: d.status for d in store2.load_mart().documents}
    assert reloaded[doc.document_id] == "Received"


def test_pii_lives_only_in_the_vault_file_not_the_mart(tmp_path):
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    store.close()

    mart_bytes = (tmp_path / "satc_mart.db").read_bytes().decode("latin-1")
    vault_bytes = (tmp_path / "satc_vault.db").read_bytes().decode("latin-1")
    for rec in synthetic_identities():
        # The legal name and full TIN must NOT appear in the mart database…
        assert rec.legal_name not in mart_bytes
        assert rec.tin.replace("-", "") not in mart_bytes.replace("-", "")
        # …but they DO live in the vault database.
        assert rec.legal_name in vault_bytes


def test_export_produces_an_excel_mirror(tmp_path):
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    out = export_mart_to_excel(store, tmp_path / "export.xlsx")
    assert out.exists()
    wb = load_workbook(out)
    assert "Data Mart" in wb.sheetnames
    assert "Dashboards" in wb.sheetnames


def test_loaded_mart_matches_fixture_shape(tmp_path):
    store = SATCStore(tmp_path)
    store.seed_if_empty()
    mart = store.load_mart()
    assert len(mart.returns) == 6
    assert len(mart.documents) == 10
    assert any(c.kind == "NOL" for c in mart.carryforwards)
