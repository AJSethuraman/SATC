"""Withholding estimator screen (Flask) tests."""

from __future__ import annotations

import pytest

from satc.app.server import create_app


@pytest.fixture()
def client():
    return create_app().test_client()


def test_estimator_form_renders(client):
    resp = client.get("/withholding")
    assert resp.status_code == 200
    assert b"Withholding estimator" in resp.data


def test_estimate_post_shows_projection(client):
    resp = client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "78000", "federal_tax_withheld_per_period": "9000",
    })
    assert resp.status_code == 200
    assert b"Total tax liability" in resp.data
    assert b"Download audit tape" in resp.data


def test_audit_tape_download_after_estimate(client):
    client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "78000", "federal_tax_withheld_per_period": "9000",
    })
    resp = client.get("/withholding/audit.xlsx")
    assert resp.status_code == 200
    assert resp.data[:2] == b"PK"   # xlsx is a zip
    assert "spreadsheetml" in resp.headers["Content-Type"]


def test_audit_tape_without_estimate_is_guarded(client):
    # Fresh app: no estimate has been run yet.
    fresh = create_app().test_client()
    assert fresh.get("/withholding/audit.xlsx").status_code == 400


def test_paste_paystub_prefills_form(client):
    sample = ("Pay Frequency: Bi-Weekly\n"
              "Gross Pay   2,500.00   30,000.00\n"
              "Federal Income Tax   300.00   3,600.00\n")
    resp = client.post("/withholding/from-paystub", data={"paystub_text": sample,
                                                          "filing_status": "single"})
    assert resp.status_code == 200
    assert b"Pre-filled from the paystub" in resp.data
    assert b"2500.00" in resp.data        # gross prefilled into the form value
    assert b"3600.00" in resp.data        # YTD federal withheld prefilled
