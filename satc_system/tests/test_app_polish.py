"""Route tests for the wired-up buttons + staging edits (no more dead links)."""

from __future__ import annotations

import pytest

flask = pytest.importorskip("flask")

from satc.app.server import create_app  # noqa: E402
from satc.app.state import STATE  # noqa: E402


@pytest.fixture()
def client():
    return create_app().test_client()


def test_sample_banner_shows_while_sample_data_present(client):
    assert STATE.has_sample_data()
    assert "sample data" in client.get("/").get_data(as_text=True).lower()


def test_generate_drake_entry_renders_a_real_worksheet(client):
    body = client.get("/clients/SATC-001000/drake").get_data(as_text=True)
    assert "Drake entry worksheet" in body


def test_draft_delivery_email_falls_back_with_text(client):
    body = client.post("/clients/SATC-001000/delivery-email").get_data(as_text=True)
    assert "mailto:" in body
    assert "tax return is ready" in body.lower()


def test_staging_edit_unaccept_delete(client):
    fid = STATE.gate.all_fields()[0].field_id
    client.post(f"/staging/{fid}/edit", data={"value": "145030"})
    assert STATE.gate._find(fid).effective_text() == "145030"
    client.post(f"/staging/{fid}/unconfirm")
    assert STATE.gate._find(fid).status in ("STAGED", "NEEDS_REVIEW")
    client.post(f"/staging/{fid}/delete")
    assert STATE.gate._find(fid) is None


def test_discard_client_removes_a_just_added_client(client):
    cid = STATE.create_person_client(first_name="Tmp", last_name="Discard", ssn="999-88-7777")
    assert STATE.public_client(cid) is not None
    resp = client.post(f"/clients/{cid}/discard")
    assert resp.status_code in (301, 302)
    assert STATE.public_client(cid) is None


def test_no_placeholder_href_hash_in_client_page(client):
    # The client page must not ship dead "#" buttons anymore.
    body = client.get("/clients/SATC-001000").get_data(as_text=True)
    assert 'href="#"' not in body


def test_intake_retains_source_and_route_is_allowlisted(tmp_path, client):
    """Compare-to-source: a read keeps its file, and /source serves only those."""
    from satc.app.state import STATE, AppState
    from satc.fixtures import create_sample_folder

    fresh = AppState()
    fresh.run_intake(str(create_sample_folder(tmp_path / "2024")))
    sourced = [d for d in fresh.gate.documents if d.source_path]
    assert sourced, "each read document should retain its source file path"

    STATE.intake_sources = set(fresh.intake_sources)
    assert client.get("/source", query_string={"path": sourced[0].source_path}).status_code == 200
    # Anything outside the allow-list is refused (no arbitrary file reads).
    assert client.get("/source", query_string={"path": "/etc/passwd"}).status_code == 404
