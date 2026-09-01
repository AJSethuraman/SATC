"""Folder intake auto-closes the loop: an arriving W-2 marks its request Received."""

from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")
pytest.importorskip("flask")

from satc.app.state import AppState  # noqa: E402
from satc.fixtures import create_sample_folder  # noqa: E402


def test_intake_reconciles_requested_documents(tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path / "data"))   # isolated store
    state = AppState()

    # A 1040 engagement for the seeded client opens its document requests.
    state.create_engagement(client_id="SATC-001000", workflow_key="personal_1040_core",
                            due_date="2026-04-15", tax_year=2024,
                            answers={"newSatcClient": "no"})
    before = sum(1 for d in state.documents()
                 if d.client_id == "SATC-001000" and d.status == "Requested")
    assert before >= 1

    # Drop a real W-2 (+1099-INT, engagement letter) into a folder and run intake.
    folder = create_sample_folder(tmp_path / "Clients" / "2024")
    summary = state.run_intake(str(folder), client_id="SATC-001000", tax_year=2024)

    # The arriving documents found the requests they belong to.
    assert summary["reconciled"] >= 1

    # AND THE CORE-INCOME REQUEST STAYS OPEN, because it names five forms and
    # two of them arrived. This assertion used to read
    #
    #     assert any("income" in d.doc_type.lower() for d in received)
    #
    # over documents whose status was "Received" -- so it asserted that a W-2
    # and a 1099-INT closed a request reading "Upload Forms W-2, 1099-INT,
    # 1099-DIV, 1099-B, 1099-G", and the client was never asked for the other
    # three. See satc.intake.service.reconcile_received.
    from satc.intake.service import outstanding_parts

    income = [d for d in state.documents()
              if d.client_id == "SATC-001000" and "income" in str(d.doc_type).lower()]
    assert income, "the core-income request should exist"
    assert all(d.status == "Requested" for d in income)
    assert outstanding_parts(income[0]), "it should still name what has not arrived"
    assert any("still waiting on" in n for n in summary["notes"])
