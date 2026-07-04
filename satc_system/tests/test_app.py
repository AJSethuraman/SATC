"""Smoke tests for the prototype web app (no server needed — Flask test client)."""

from __future__ import annotations

import pytest

flask = pytest.importorskip("flask")  # app is an optional extra

from satc.app.server import create_app  # noqa: E402
from satc.app.state import STATE  # noqa: E402


@pytest.fixture()
def client():
    return create_app().test_client()


def test_core_screens_render(client):
    for path in ["/", "/intake?folder=/x", "/staging", "/documents", "/clients/SATC-001000"]:
        assert client.get(path).status_code == 200


def test_mark_document_received_updates_status_and_tracker(client):
    doc = STATE.outstanding()[0]               # a "Requested" document
    before = len(STATE.outstanding())
    resp = client.post(f"/documents/{doc.document_id}/Received")
    assert resp.status_code in (301, 302)      # redirect back
    assert doc.status == "Received"
    assert len(STATE.outstanding()) == before - 1   # dropped off the missing-docs tracker
