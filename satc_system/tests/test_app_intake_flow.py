"""Flow tests: the branched interview, filing status, and the email/organizer routes.

Runs against the Flask test client and the module-level ``STATE`` (an isolated
temp store, per conftest). On non-Windows CI the Outlook COM path is unavailable,
so the email routes exercise the graceful mailto/text fallback.
"""

from __future__ import annotations

import pytest

flask = pytest.importorskip("flask")  # app is an optional extra

from satc.app.server import create_app  # noqa: E402
from satc.app.state import STATE  # noqa: E402


@pytest.fixture()
def client():
    return create_app().test_client()


def _make_client(email: str = "taxpayer@example.com") -> str:
    return STATE.create_person_client(first_name="Pat", last_name="Lee",
                                      ssn="123-45-6789", email=email)


def test_create_client_lands_on_intake_chooser(client):
    cid = _make_client()
    body = client.get(f"/clients/{cid}/start").get_data(as_text=True)
    assert "Scan their documents" in body
    assert "Interview them yourself" in body
    assert "Send the client a form" in body


def test_new_client_interview_hides_the_gate_question(client):
    cid = _make_client()
    body = client.get(f"/intake/new?client={cid}&workflow=personal_1040_core").get_data(as_text=True)
    # No history -> defaults to NEW; the gate question is promoted out of the table.
    assert "New SAT-C client?" not in body
    assert "Filing status" in body


def test_returning_interview_prefills_and_shows_history(client):
    cid = _make_client()
    STATE.create_engagement(client_id=cid, workflow_key="personal_1040_core",
                            due_date="2025-04-15", tax_year=2024,
                            answers={"newSatcClient": "yes", "movedStates": "yes"})
    body = client.get(
        f"/intake/new?client={cid}&workflow=personal_1040_core&mode=returning").get_data(as_text=True)
    assert "what changed" in body.lower()
    assert "last year" in body.lower()


def test_interview_post_persists_filing_status_and_sets_gate(client):
    cid = _make_client()
    resp = client.post("/intake/new", data={
        "client": cid, "workflow_key": "personal_1040_core", "mode": "new",
        "due_date": "2026-04-15", "tax_year": "2025",
        "filing_status": "Married filing jointly"})
    assert resp.status_code in (301, 302)
    assert STATE.filing_status(cid) == "Married filing jointly"
    eng = STATE.prior_engagement(cid, "personal_1040_core")
    assert eng is not None and eng.intake_answers.get("newSatcClient") == "yes"


def test_engagement_email_outlook_falls_back_to_text(client):
    cid = _make_client()
    eng = STATE.create_engagement(client_id=cid, workflow_key="personal_1040_core",
                                  due_date="2026-04-15", tax_year=2025,
                                  answers={"newSatcClient": "no"})
    body = client.post(f"/engagements/{eng.engagement_id}/email/outlook").get_data(as_text=True)
    assert "mailto:" in body          # universal fallback link
    assert "Requested items" in body  # the generated subject/body is shown


def test_organizer_picker_action_and_pdf(client):
    cid = _make_client()
    assert "Choose a workflow" in client.get(f"/intake/organizer?client={cid}").get_data(as_text=True)
    action = client.get(f"/intake/organizer?client={cid}&workflow=personal_1040_core").get_data(as_text=True)
    assert "organizer" in action.lower()
    pdf = client.get(f"/intake/organizer.pdf?client={cid}&workflow=personal_1040_core")
    assert pdf.status_code == 200
    assert pdf.data[:4] == b"%PDF"


def test_organizer_email_attaches_and_falls_back(client):
    cid = _make_client()
    body = client.post("/intake/organizer/email", data={
        "client": cid, "workflow_key": "personal_1040_core", "mode": "new",
        "tax_year": "2025"}).get_data(as_text=True)
    assert "mailto:" in body
    assert "organizer" in body.lower()
