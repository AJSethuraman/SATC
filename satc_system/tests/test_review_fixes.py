"""Regression tests for the review-fix pass (privacy gate, redirect, clients index)."""

from __future__ import annotations

import satc.app.state as state_mod
from satc.app.server import create_app
from satc.app.state import STATE


def test_sort_folder_does_not_enable_cloud_on_key_alone(tmp_path, monkeypatch):
    # A bare API key must NOT enable cloud: only SATC_ALLOW_CLOUD opts in.
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("SATC_ALLOW_CLOUD", raising=False)

    captured: dict = {}
    real_load = state_mod.load_classifier

    def fake_load_classifier(*, has_key):
        captured["has_key"] = has_key
        return real_load(has_key=False)   # real local classifier

    monkeypatch.setattr(state_mod, "load_classifier", fake_load_classifier)

    src = tmp_path / "incoming"
    src.mkdir()
    state_mod.AppState().sort_folder(str(src))
    assert captured["has_key"] is False        # key alone -> cloud stays off


def test_staging_post_redirects_to_actual_client(monkeypatch):
    # The redirect must follow the client that was actually posted, not the sample.
    monkeypatch.setattr(STATE, "post_confirmed",
                        lambda: {"client_id": "SATC-009999", "return_key": "x",
                                 "posted": 0, "lines": []})
    resp = create_app().test_client().post("/staging/post")
    assert resp.status_code in (301, 302, 303)
    assert "SATC-009999" in resp.headers["Location"]
    assert "SATC-001000" not in resp.headers["Location"]


def test_clients_index_route_renders():
    resp = create_app().test_client().get("/clients")
    assert resp.status_code == 200
    assert b"Clients" in resp.data
