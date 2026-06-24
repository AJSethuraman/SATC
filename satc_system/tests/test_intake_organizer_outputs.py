"""Tests for the organizer PDF and the split (subject, body) email parts."""

from __future__ import annotations

from satc.intake.outputs import (
    build_organizer_email,
    build_request_email,
    generate_client_request_email,
    generate_intake_organizer_pdf,
    organizer_questions,
)
from satc.intake.workflows import NEW_CLIENT_GATE, build_engagement, load_workflow


def _engagement():
    wf = load_workflow("personal_1040_core")
    return build_engagement(
        wf, client_id="SATC-001000", due_date="2026-04-15",
        answers={"newSatcClient": "yes", "marketplaceInsurance": "yes"}, tax_year=2025)


def test_build_request_email_splits_subject_and_body():
    subject, body = build_request_email(_engagement(), client_name="Jordan Rivera")
    assert subject == "Requested items for Jordan Rivera - Personal 1040 core"
    assert "Subject:" not in body
    assert body.startswith("Hello Jordan Rivera,")
    # The combined helper still embeds the Subject line (back-compat with callers).
    combined = generate_client_request_email(_engagement(), client_name="Jordan Rivera")
    assert combined == f"Subject: {subject}\n\n{body}"


def test_organizer_questions_exclude_the_new_returning_gate():
    wf = load_workflow("personal_1040_core")
    ids = [q.id for q in organizer_questions(wf)]
    assert NEW_CLIENT_GATE not in ids
    assert "marketplaceInsurance" in ids


def test_generate_intake_organizer_pdf_returns_pdf_bytes():
    wf = load_workflow("personal_1040_core")
    pdf = generate_intake_organizer_pdf(wf, client_name="Jordan Rivera", tax_year=2025)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_returning_organizer_with_prefill_still_renders():
    wf = load_workflow("personal_1040_core")
    pdf = generate_intake_organizer_pdf(
        wf, client_name="Jordan Rivera", tax_year=2025, returning=True,
        prefill={"movedStates": "yes"}, filing_status="Married filing jointly")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_build_organizer_email_new_vs_returning():
    wf = load_workflow("personal_1040_core")
    s_new, b_new = build_organizer_email(client_name="Jordan", workflow=wf, tax_year=2025, returning=False)
    s_ret, b_ret = build_organizer_email(client_name="Jordan", workflow=wf, tax_year=2025, returning=True)
    assert "organizer" in s_new.lower()
    assert "Welcome" in b_new                 # new clients get a welcome
    assert "again" in b_ret.lower()           # returning clients get a "good to work with you again"
