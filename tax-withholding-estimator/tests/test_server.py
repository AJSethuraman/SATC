"""Tests for the local HTTP server."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

from twe.server import _HTML, _Handler


def _start_server() -> tuple[HTTPServer, str]:
    """Start a server on a random free port; return (server, base_url)."""

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://127.0.0.1:{port}"


def _stop(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()


def test_html_constant_non_empty():
    assert len(_HTML) > 500
    assert "<!DOCTYPE html>" in _HTML
    assert "/api/estimate" in _HTML


def test_get_root_returns_html():
    server, base = _start_server()
    try:
        with urllib.request.urlopen(base + "/") as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type", "")
            assert "text/html" in ct
            body = resp.read().decode("utf-8")
            assert "Tax Withholding Estimator" in body
    finally:
        _stop(server)


def test_post_estimate_valid_payload():
    server, base = _start_server()
    payload = {
        "filing_status": "single",
        "tax_year": 2025,
        "paystub": {
            "pay_frequency": "biweekly",
            "gross_pay_per_period": 3000,
            "federal_tax_withheld_per_period": 350,
            "pay_periods_remaining": 26,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/estimate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            result = json.loads(resp.read())
        assert result["tax_year_used"] == 2025
        assert result["breakdown"]["total_tax_liability"] == "8774.00"
        assert "recommendation" in result
    finally:
        _stop(server)


def test_post_estimate_bad_payload_returns_400():
    server, base = _start_server()
    # bogus_key should trigger the unknown-keys validator in EstimatorInput.from_dict
    data = json.dumps({
        "filing_status": "single",
        "paystub": {"pay_frequency": "weekly"},
        "bogus_key": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/estimate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as _:
            assert False, "expected 400"
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
        body = json.loads(exc.read())
        assert "error" in body
    finally:
        _stop(server)


def test_get_unknown_path_returns_404():
    server, base = _start_server()
    try:
        with urllib.request.urlopen(base + "/does-not-exist") as _:
            assert False, "expected 404"
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    finally:
        _stop(server)
