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


def test_a_filename_only_verdict_does_not_close_a_request_through_intake(
        tmp_path, monkeypatch):
    """THE OTHER FRONT DOOR. `collect` has the same test; this is the one that
    runs when the firm points intake at a folder.

    The gate here read `if c.classified and not c.multi` -- any rung naming the
    document at all. The FILENAME rung names things it has not read, so a
    Schedule C called `2025 Schedule C 1040.pdf` came back `Prior-year 1040` at
    LOW and closed the client's open prior-year request. See
    `satc.ingest.classify.Classification.may_close_a_request`.
    """
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path / "data"))
    state = AppState()
    state.create_engagement(client_id="SATC-001000",
                            workflow_key="personal_1040_core",
                            due_date="2026-04-15", tax_year=2024,
                            answers={"newSatcClient": "yes"})

    prior = [d for d in state.documents()
             if d.client_id == "SATC-001000"
             and "prior" in str(d.doc_type).lower()]
    assert prior, "the prior-year request should exist"

    # A folder holding ONE document whose text names no form at all, so the
    # filename is the only thing left to go on.
    folder = tmp_path / "drop"
    folder.mkdir()
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    doc.new_page().insert_textbox(
        pymupdf.Rect(36, 36, 560, 740),
        "Profit or Loss From Business. Gross receipts or sales.", fontsize=10)
    doc.save(str(folder / "2025 Schedule C 1040.pdf"))
    doc.close()

    state.run_intake(str(folder), client_id="SATC-001000", tax_year=2024)

    still = [d for d in state.documents()
             if d.document_id == prior[0].document_id]
    assert still[0].status == "Requested", (
        "a LOW filename guess closed the prior-year request")
