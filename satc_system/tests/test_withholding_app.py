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


def _textlayer_paystub_pdf() -> bytes:
    """A real text-layer PDF carrying paystub lines (so pypdf can read it)."""
    import io as _io

    from reportlab.pdfgen import canvas

    buf = _io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Courier", 11)
    y = 760
    for line in ("Pay Frequency: Bi-Weekly",
                 "Gross Pay            2,500.00    30,000.00",
                 "Federal Income Tax     300.00     3,600.00"):
        c.drawString(60, y, line)
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


def test_upload_textlayer_pdf_prefills_form(client):
    import io as _io

    resp = client.post(
        "/withholding/from-file",
        data={"filing_status": "single",
              "paystub_file": (_io.BytesIO(_textlayer_paystub_pdf()), "stub.pdf")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert b"Pre-filled from the paystub" in resp.data
    assert b"2500.00" in resp.data           # gross pulled from the PDF text layer
    assert b"3600.00" in resp.data           # YTD federal withheld pulled too
    assert b"text layer" in resp.data        # local, on-device source note


def test_upload_without_file_is_handled(client):
    resp = client.post("/withholding/from-file", data={"filing_status": "single"},
                       content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"No file was selected" in resp.data
