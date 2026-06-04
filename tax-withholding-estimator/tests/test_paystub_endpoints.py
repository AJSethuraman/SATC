"""Integration tests for the paystub import HTTP endpoints.

Skipped automatically when PyMuPDF (the optional [paystub] extra) is absent.
"""

from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

import pytest

pymupdf = pytest.importorskip("pymupdf")

from twe.server import _Handler


@pytest.fixture()
def server(tmp_path, monkeypatch):
    # Keep saved profiles inside the temp dir.
    monkeypatch.setenv("TWE_PROFILE_DIR", str(tmp_path))
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()
    srv.server_close()


def _paystub_pdf_b64() -> str:
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=300)
    page.insert_text((40, 40), "ACME PAYROLL SERVICES", fontsize=11)
    page.insert_text((40, 110), "Gross Pay          3,200.00      38,400.00", fontsize=10)
    page.insert_text((40, 140), "Federal Income Tax   410.00       4,920.00", fontsize=10)
    page.insert_text((40, 220), "Pay Date: 06/30/2025", fontsize=10)
    return base64.b64encode(doc.tobytes()).decode("ascii")


def _post(base: str, path: str, obj: dict):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(obj).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_layout_extract_and_automatch(server):
    pdf = _paystub_pdf_b64()

    status, layout = _post(server, "/api/paystub/layout", {"data": pdf, "media_type": "application/pdf"})
    assert status == 200
    assert len(layout["words"]) > 0
    assert len(layout["targets"]) == 7
    assert layout["matched"] is None  # nothing learned yet

    words = layout["words"]

    def idx(text: str) -> int:
        return next(i for i, w in enumerate(words) if w["text"] == text)

    status, extracted = _post(server, "/api/paystub/extract", {
        "words": words,
        "assignments": {
            "gross_pay_per_period": [idx("3,200.00")],
            "federal_tax_withheld_per_period": [idx("410.00")],
            "ytd_taxable_wages": [idx("38,400.00")],
            "last_pay_date": [idx("06/30/2025")],
        },
        "name": "Acme ADP",
        "pay_frequency": "biweekly",
        "match_keywords": ["ACME PAYROLL"],
        "save": True,
    })
    assert status == 200
    assert extracted["saved"] is True
    assert extracted["extracted"]["gross_pay_per_period"] == "3200.00"
    assert extracted["extracted"]["ytd_taxable_wages"] == "38400.00"
    assert extracted["extracted"]["last_pay_date"] == "2025-06-30"
    assert extracted["extracted"]["pay_frequency"] == "biweekly"

    # Re-uploading the same layout should now auto-match the saved profile.
    status, layout2 = _post(server, "/api/paystub/layout", {"data": pdf, "media_type": "application/pdf"})
    assert status == 200
    assert layout2["matched"] is not None
    assert layout2["matched"]["name"] == "Acme ADP"
    assert layout2["matched"]["extracted"]["federal_tax_withheld_per_period"] == "410.00"


def test_extract_without_save(server):
    pdf = _paystub_pdf_b64()
    _, layout = _post(server, "/api/paystub/layout", {"data": pdf, "media_type": "application/pdf"})
    words = layout["words"]
    idx = next(i for i, w in enumerate(words) if w["text"] == "410.00")

    status, result = _post(server, "/api/paystub/extract", {
        "words": words,
        "assignments": {"federal_tax_withheld_per_period": [idx]},
        "name": "Temp",
        "save": False,
    })
    assert status == 200
    assert result["saved"] is False
    assert result["extracted"]["federal_tax_withheld_per_period"] == "410.00"


def test_layout_bad_base64_returns_400(server):
    status, body = _post(server, "/api/paystub/layout", {"data": "not-valid-pdf-data", "media_type": "application/pdf"})
    assert status == 400
    assert "error" in body


def _get(base: str, path: str):
    with urllib.request.urlopen(base + path) as resp:
        return resp.status, json.loads(resp.read())


def _seed_profile(server: str, name: str) -> None:
    _, layout = _post(server, "/api/paystub/layout", {"data": _paystub_pdf_b64(), "media_type": "application/pdf"})
    words = layout["words"]
    gi = next(i for i, w in enumerate(words) if w["text"] == "3,200.00")
    _post(server, "/api/paystub/extract", {
        "words": words,
        "assignments": {"gross_pay_per_period": [gi]},
        "name": name,
        "pay_frequency": "biweekly",
        "save": True,
    })


def test_list_rename_delete_profiles(server):
    _seed_profile(server, "Acme ADP")
    _seed_profile(server, "Beta Gusto")

    status, body = _get(server, "/api/paystub/profiles")
    assert status == 200
    names = {p["name"] for p in body["profiles"]}
    assert names == {"Acme ADP", "Beta Gusto"}
    acme = next(p for p in body["profiles"] if p["name"] == "Acme ADP")
    assert acme["field_count"] == 1
    assert acme["fields"][0]["field"] == "gross_pay_per_period"
    assert acme["fields"][0]["label"]  # human label present

    status, _ = _post(server, "/api/paystub/profile/rename", {"old": "Acme ADP", "new": "Acme Payroll"})
    assert status == 200
    names = {p["name"] for p in _get(server, "/api/paystub/profiles")[1]["profiles"]}
    assert names == {"Acme Payroll", "Beta Gusto"}

    status, body = _post(server, "/api/paystub/profile/delete", {"name": "Beta Gusto"})
    assert status == 200 and body["ok"] is True
    names = {p["name"] for p in _get(server, "/api/paystub/profiles")[1]["profiles"]}
    assert names == {"Acme Payroll"}


def test_rename_missing_profile_returns_404(server):
    status, body = _post(server, "/api/paystub/profile/rename", {"old": "ghost", "new": "x"})
    assert status == 404
    assert "error" in body
