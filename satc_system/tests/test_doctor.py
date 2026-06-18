"""Readiness check, the Setup screen, and launch ergonomics."""

from __future__ import annotations

import pytest

from satc.cli import main as cli_main
from satc.doctor import format_report, run_checks


def test_run_checks_covers_the_essentials():
    names = {c.name for c in run_checks()}
    assert {"Python", "Data store", "Local OCR (Tesseract)",
            "Local vision (Ollama)", "Cloud vision"} <= names


def test_cloud_is_reported_off_by_default(monkeypatch):
    monkeypatch.delenv("SATC_ALLOW_CLOUD", raising=False)
    cloud = next(c for c in run_checks() if c.name == "Cloud vision")
    assert cloud.status == "ok"
    assert "never leave" in cloud.detail.lower()


def test_format_report_is_plain_language():
    text = format_report()
    assert "SATC readiness" in text
    assert "Cloud vision" in text


def test_doctor_cli_returns_zero(capsys):
    assert cli_main(["doctor"]) == 0
    assert "readiness" in capsys.readouterr().out


def test_setup_screen_renders():
    pytest.importorskip("flask")
    from satc.app.server import create_app
    client = create_app().test_client()
    r = client.get("/setup")
    assert r.status_code == 200
    assert b"readiness" in r.data.lower()


def test_pick_port_returns_a_usable_port():
    from satc.app.server import _pick_port
    port = _pick_port(5050)
    assert isinstance(port, int) and 0 < port < 65536
