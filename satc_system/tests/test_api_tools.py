"""SATC MCP tool implementations (the read/write functions agents call)."""

from __future__ import annotations

import json

import pytest

from satc.api import tools


@pytest.fixture()
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    from satc.app.state import AppState
    return AppState()


def test_estimate_withholding_returns_projection():
    out = tools.estimate_withholding({
        "filing_status": "single", "tax_year": 2025,
        "jobs": [{"pay_frequency": "annual", "gross_pay_per_period": "78000",
                  "federal_tax_withheld_per_period": "9000", "pay_periods_remaining": 1}],
    })
    assert "breakdown" in out and "recommendation" in out
    assert out["breakdown"]["total_tax_liability"] > 0
    assert isinstance(out["breakdown"]["total_tax_liability"], float)   # JSON-safe
    # round-trips through JSON without choking on Decimals/dates
    json.dumps(out)


def test_estimate_withholding_bad_input_is_data_not_crash():
    out = tools.estimate_withholding({"jobs": [{}]})   # missing filing_status
    assert "error" in out


def test_read_paystub_parses_text():
    out = tools.read_paystub("Gross Pay  2,500.00  30,000.00\nFederal Income Tax  300.00  3,600.00")
    assert any("Gross" in k for k in out["labeled_fields"])
    assert any("2500" in v for v in out["labeled_fields"].values())


def test_create_then_list_and_get_client_stays_deidentified(state):
    res = tools.create_person_client(state, first_name="Jordan", last_name="Lee",
                                     ssn="123-45-6789", email="j@example.com")
    cid = res["client_id"]
    assert cid in {c["client_id"] for c in tools.list_clients(state)}

    got = tools.get_client(state, cid)
    assert got["client_id"] == cid
    assert "line_items" in got and "documents" in got and "returns" in got
    # The full SSN lives in the vault and must NOT come back through the API.
    assert "123-45-6789" not in json.dumps(got)


def test_get_unknown_client_returns_error(state):
    assert "error" in tools.get_client(state, "NOPE-9999")


def test_post_confirmed_intake_targets_the_named_client(state):
    cid = tools.create_person_client(state, first_name="A", last_name="B")["client_id"]
    out = tools.post_confirmed_intake(state, client_id=cid, tax_year=2024)
    assert out["client_id"] == cid


def test_http_estimate_endpoint():
    from satc.app.server import create_app
    r = create_app().test_client().post("/api/withholding/estimate", json={
        "filing_status": "single", "tax_year": 2025,
        "jobs": [{"pay_frequency": "annual", "gross_pay_per_period": "78000",
                  "federal_tax_withheld_per_period": "9000", "pay_periods_remaining": 1}]})
    assert r.status_code == 200
    assert r.get_json()["breakdown"]["total_tax_liability"] > 0


def test_http_read_paystub_endpoint():
    from satc.app.server import create_app
    r = create_app().test_client().post("/api/withholding/read-paystub",
        json={"text": "Gross Pay 2,500.00 30,000.00\nFederal Income Tax 300.00 3,600.00"})
    assert r.status_code == 200
    assert any("Gross" in k for k in r.get_json()["labeled_fields"])
