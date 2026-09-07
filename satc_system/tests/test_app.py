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


def test_closing_a_request_drops_it_off_the_tracker(client):
    item = STATE.outstanding()[0]
    before = len(STATE.outstanding())
    resp = client.post(f"/documents/{item.request_id}/close")
    assert resp.status_code in (301, 302)      # redirect back
    assert not item.is_open
    assert len(STATE.outstanding()) == before - 1


def test_closing_a_request_as_not_applicable_keeps_the_reason(client):
    """A bare N/A is indistinguishable from never having asked."""
    item = STATE.outstanding()[0]
    client.post(f"/documents/{item.request_id}/close",
                data={"reason": "they closed that account in March"})
    assert item.status == "not_applicable"
    assert item.not_applicable_reason == "they closed that account in March"
