"""Withholding estimator screen (Flask) tests — multi-job + learned templates."""

from __future__ import annotations

import io

import pytest

from satc.app.server import create_app

STUB_A = ("Employer: Acme Corp\nPayroll by ADP\n"
          "Gross Pay            2,500.00    30,000.00\n"
          "Federal Income Tax     300.00     3,600.00\n"
          "Pay Frequency: Bi-Weekly\n")
STUB_B = ("Employer: Beta LLC\nPayroll by ADP\n"
          "Gross Pay            2,000.00    24,000.00\n"
          "Federal Income Tax     240.00     2,880.00\n"
          "Pay Frequency: Bi-Weekly\n")


@pytest.fixture()
def client():
    return create_app().test_client()


def test_estimator_form_renders(client):
    resp = client.get("/withholding")
    assert resp.status_code == 200
    assert b"Withholding estimator" in resp.data


def test_single_job_estimate_shows_projection(client):
    resp = client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "78000", "federal_tax_withheld_per_period": "9000",
    })
    assert resp.status_code == 200
    assert b"Total tax liability" in resp.data
    assert b"Download audit tape" in resp.data


def test_audit_tape_after_estimate(client):
    client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "78000", "federal_tax_withheld_per_period": "9000",
    })
    resp = client.get("/withholding/audit.xlsx")
    assert resp.status_code == 200
    assert resp.data[:2] == b"PK"   # xlsx is a zip
    assert "spreadsheetml" in resp.headers["Content-Type"]


def test_audit_tape_without_estimate_is_guarded(client):
    assert create_app().test_client().get("/withholding/audit.xlsx").status_code == 400


def test_paste_paystub_adds_a_job(client):
    resp = client.post("/withholding/from-paystub", data={"paystub_text": STUB_A})
    assert resp.status_code == 200
    assert b"Teach this layout" in resp.data       # teach panel appears
    assert b"2500.00" in resp.data                 # gross filled into the job row
    assert b"3600.00" in resp.data                 # YTD federal withheld filled


def _textlayer_pdf(lines) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Courier", 11)
    y = 760
    for line in lines:
        c.drawString(60, y, line)
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


def test_upload_pdf_adds_a_job(client):
    pdf = _textlayer_pdf(["Pay Frequency: Bi-Weekly",
                          "Gross Pay            2,500.00    30,000.00",
                          "Federal Income Tax     300.00     3,600.00"])
    resp = client.post("/withholding/from-file",
                       data={"paystub_file": (io.BytesIO(pdf), "stub.pdf")},
                       content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"2500.00" in resp.data           # pulled from the PDF text layer into a job
    assert b"text layer" in resp.data        # on-device source note


def test_upload_without_file_is_handled(client):
    resp = client.post("/withholding/from-file", data={}, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"No file was selected" in resp.data


def test_two_paystubs_one_estimate(client):
    client.post("/withholding/from-paystub", data={"paystub_text": STUB_A})
    client.post("/withholding/from-paystub", data={"paystub_text": STUB_B})
    resp = client.post("/withholding", data={
        "filing_status": "married_jointly", "tax_year": "2025", "adjust_job": "0"})
    assert resp.status_code == 200
    assert b"Total tax liability" in resp.data
    assert b"Projected withholding" in resp.data   # per-job breakdown shown (>1 job)


def test_learned_layout_autofills_next_stub(client, tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    saved = client.post("/withholding/save-layout", data={
        "paystub_src": STUB_A,
        "t_gross_cur": "2500.00", "t_gross_ytd": "30000.00",
        "t_fed_cur": "300.00", "t_fed_ytd": "3600.00", "t_freq": "biweekly"})
    assert b"will fill in automatically" in saved.data
    # A different-period stub from the same employer/layout is recognized + autofilled.
    again = ("Employer: Acme Corp\nPayroll by ADP\n"
             "Gross Pay            2,500.00    32,500.00\n"
             "Federal Income Tax     310.00     3,910.00\n"
             "Pay Frequency: Bi-Weekly\n")
    resp = client.post("/withholding/from-paystub", data={"paystub_text": again})
    assert b"Recognized" in resp.data
    assert b"3910.00" in resp.data        # YTD federal pulled via the learned anchors


def _pymupdf_available() -> bool:
    try:
        import pymupdf  # noqa: F401
        return True
    except ImportError:
        try:
            import fitz  # noqa: F401
            return True
        except ImportError:
            return False


@pytest.mark.skipif(not _pymupdf_available(), reason="PyMuPDF not installed")
def test_paystub_layout_new_opens_teach_modal(client, tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    pdf = _textlayer_pdf(["ACME CORP",
                          "Gross Pay            2,500.00    30,000.00",
                          "Federal Income Tax     300.00     3,600.00"])
    resp = client.post("/withholding/paystub/layout",
                       data={"paystub_file": (io.BytesIO(pdf), "acme.pdf")},
                       content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"Map your paystub" in resp.data        # teach modal rendered
    assert b'id="ps-teach-data" type="application/json"' in resp.data   # payload embedded


@pytest.mark.skipif(not _pymupdf_available(), reason="PyMuPDF not installed")
def test_paystub_click_teach_saves_profile_then_recognizes(client, tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    import json

    from satc.ingest.paystub_layout import extract_layout, parse_currency

    pdf = _textlayer_pdf(["ACME CORP",
                          "Gross Pay            2,500.00    30,000.00",
                          "Federal Income Tax     300.00     3,600.00"])
    words = extract_layout(pdf, "application/pdf").words

    def idx_for(value: str) -> int:
        want = parse_currency(value)
        for i, w in enumerate(words):
            if parse_currency(w.text) == want:
                return i
        raise AssertionError(f"{value} not in {[w.text for w in words]}")

    assignments = {
        "gross_pay_per_period": [idx_for("2500.00")],
        "ytd_taxable_wages": [idx_for("30000.00")],
        "federal_tax_withheld_per_period": [idx_for("300.00")],
        "ytd_federal_tax_withheld": [idx_for("3600.00")],
    }
    words_payload = [{"text": w.text, "x0": w.x0, "y0": w.y0, "x1": w.x1, "y1": w.y1} for w in words]
    saved = client.post("/withholding/paystub/teach", data={
        "words": json.dumps(words_payload),
        "assignments": json.dumps(assignments),
        "profile_name": "Acme Corp (ADP)",
        "pay_frequency": "biweekly"})
    assert saved.status_code == 200
    assert b"Saved" in saved.data
    assert b"2500.00" in saved.data        # job added from the mapped values

    # Re-upload the same layout -> recognized and auto-added, no teach modal.
    again = client.post("/withholding/paystub/layout",
                        data={"paystub_file": (io.BytesIO(pdf), "acme.pdf")},
                        content_type="multipart/form-data")
    assert again.status_code == 200
    assert b"Recognized" in again.data
    assert b'id="ps-teach-data" type="application/json"' not in again.data   # no payload -> modal closed


def test_estimator_filing_status_mapping():
    from satc.app.withholding_views import _estimator_filing_status
    assert _estimator_filing_status("MFJ") == "married_jointly"
    assert _estimator_filing_status("S") == "single"
    assert _estimator_filing_status("HOH") == "head_of_household"
    assert _estimator_filing_status("QSS") == "married_jointly"     # uses MFJ brackets
    assert _estimator_filing_status("single") == "single"           # already estimator format
    assert _estimator_filing_status("") == ""


def test_from_client_prefills_filing_status(monkeypatch):
    import types

    from satc.app.state import STATE
    fake = types.SimpleNamespace(client_id="ZZ-1", filing_status="HOH")
    monkeypatch.setattr(STATE.mart, "public_clients", [fake])
    monkeypatch.setattr(STATE, "name", lambda cid: "Test Client")

    resp = create_app().test_client().post("/withholding/from-client", data={"client_id": "ZZ-1"})
    assert resp.status_code == 200
    assert b"Prefilled filing status" in resp.data
    assert b"Head of household" in resp.data        # mapped HOH label
