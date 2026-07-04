"""Local-app hardening: loopback-only Host (H2), cross-origin POST block (H3),
and a per-install random secret key (M7)."""

from __future__ import annotations

import pytest

_JOB = {"filing_status": "single", "tax_year": 2025,
        "jobs": [{"pay_frequency": "annual", "gross_pay_per_period": "50000",
                  "federal_tax_withheld_per_period": "5000"}]}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("SATC_SECRET_KEY", "test-secret")  # skip the file-write path
    from satc.app.server import create_app
    return create_app().test_client()


def test_foreign_host_is_rejected(client):
    assert client.get("/", headers={"Host": "evil.example.com"}).status_code == 400


def test_loopback_host_is_allowed(client):
    assert client.get("/", headers={"Host": "127.0.0.1:5050"}).status_code == 200


def test_cross_origin_post_is_blocked(client):
    r = client.post("/api/withholding/estimate",
                    headers={"Origin": "https://evil.example.com"}, json=_JOB)
    assert r.status_code == 403


def test_same_origin_post_is_allowed(client):
    r = client.post("/api/withholding/estimate",
                    headers={"Origin": "http://127.0.0.1:5050"}, json=_JOB)
    assert r.status_code == 200


def test_originless_post_is_allowed_for_local_tools(client):
    # The MCP proxy / curl send no Origin header — must not be treated as CSRF.
    assert client.post("/api/withholding/estimate", json=_JOB).status_code == 200


def test_secret_key_is_random_not_the_old_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SATC_SECRET_KEY", raising=False)
    from satc.app import server
    monkeypatch.setattr(server.STATE.store, "dir", tmp_path)
    app = server.create_app()
    assert app.secret_key not in (b"satc-local-dev-key", "satc-local-dev-key")
    assert (tmp_path / "flask_secret.key").exists()
