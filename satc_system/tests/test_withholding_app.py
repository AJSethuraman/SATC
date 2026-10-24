"""Withholding estimator screen (Flask) tests — multi-job + learned templates."""

from __future__ import annotations

import io
import re

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
    assert _estimator_filing_status("QSS") == "qualifying_surviving_spouse"
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


def test_the_age_and_rent_fields_reach_the_estimate(client):
    """Codex review, PR #451: the under-25 and rental fields are on the form,
    so walk them through it. Single, wages 15,000, 2025, no children: 313.94
    of earned income credit at 25 or older; none under 25; none with 12,000
    of rent, which is over the 11,950 investment-income limit."""
    def post(**extra):
        return client.post("/withholding", data={
            "filing_status": "single", "tax_year": "2025",
            "j0_name": "Case", "j0_pay_frequency": "annual",
            "j0_gross_pay_per_period": "15000", "j0_federal_tax_withheld_per_period": "0",
            "j0_retirement_pretax_per_period": "0", "j0_pay_periods_remaining": "1",
            "children_under_17": "0", **extra}).get_data(as_text=True)
    row = re.compile(r"Earned income credit</td>\s*<td class=\"num\">\(\$314\)")  # whole dollars
    assert row.search(post(taxpayer_under_25="no"))
    assert not row.search(post(taxpayer_under_25="yes"))
    assert not row.search(post(taxpayer_under_25="no", rental_and_passive_income="12000"))
    assert 'name="rental_and_passive_income"' in post()
    assert 'name="spouse_under_25"' in post()


def test_the_screen_asks_whether_a_separate_filer_lived_apart(client):
    """Codex on #451: the credit a separated parent can claim on a separate
    return needs a question on the screen, not only in the engine."""
    base = {"filing_status": "married_separately", "tax_year": "2025", "adjust_job": "0",
            "pay_frequency": "annual", "pay_periods_remaining": "1",
            "gross_pay_per_period": "15000", "federal_tax_withheld_per_period": "0",
            "children_under_17": "1"}
    assert b'name="lived_apart_from_spouse"' in client.get("/withholding").data
    apart = client.post("/withholding", data=dict(base, lived_apart_from_spouse="yes")).data
    assert b"4,328" in apart, apart.decode("utf-8", "replace")[:2000]
    blank = client.post("/withholding", data=dict(base, lived_apart_from_spouse="")).data
    assert b"4,328" not in blank and b"lived apart" in blank


def _text(page: bytes) -> bytes:
    """The page as a reader sees it: tags dropped, whitespace collapsed."""
    return re.sub(rb"\s+", b" ", re.sub(rb"<[^>]+>", b" ", page))


def test_the_screen_asks_whose_business_it_is(client):
    """Codex on #451: on a joint return only the owner's wages use up the
    Social Security wage base on Schedule SE, so the screen has to ask whose
    business it is. Spouse's job 180,000, business 100,000 (engine test has the
    working): taxpayer's $14,130, spouse's $2,678, as the screen rounds."""
    base = {"filing_status": "married_jointly", "tax_year": "2025", "adjust_job": "0",
            "pay_frequency": "annual", "pay_periods_remaining": "1", "owner": "spouse",
            "gross_pay_per_period": "180000", "federal_tax_withheld_per_period": "0",
            "self_employment_net": "100000"}
    assert b'name="self_employment_owner"' in client.get("/withholding").data
    mine = client.post("/withholding", data=dict(base, self_employment_owner="you")).data
    assert b"Self-employment tax $14,130" in _text(mine), mine.decode("utf-8", "replace")[:2000]
    theirs = client.post("/withholding", data=dict(base, self_employment_owner="spouse")).data
    assert b"Self-employment tax $2,678" in _text(theirs)


def test_the_screen_asks_whether_a_separate_filers_spouse_files_nothing(client):
    """Codex on #451: Pub. 501 lets a separate return count the spouse's age
    box when the spouse has no income and files nothing: 15,750 + 1,600."""
    base = {"filing_status": "married_separately", "tax_year": "2025", "adjust_job": "0",
            "pay_frequency": "annual", "pay_periods_remaining": "1",
            "gross_pay_per_period": "60000", "federal_tax_withheld_per_period": "5000",
            "spouse_65_or_older": "yes"}
    assert b'name="spouse_no_income_not_filing"' in client.get("/withholding").data
    told = client.post("/withholding", data=dict(base, spouse_no_income_not_filing="yes")).data
    assert b"17,350" in told, told.decode("utf-8", "replace")[:2000]
    blank = client.post("/withholding", data=base).data
    assert b"17,350" not in blank and b"Spouse&#39;s age" in blank


def test_two_blind_people_on_a_single_return_are_refused_on_screen(client):
    resp = client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "60000", "federal_tax_withheld_per_period": "5000",
        "blind_count": "2"})
    assert resp.status_code == 200
    assert b"legally blind" in resp.data and b"Total tax liability" not in resp.data


def test_the_screen_takes_refundable_credits_and_the_2210_prior_year_tax(client):
    """Codex on #451: the refundable part of the education credit had nowhere
    to go, and last year's tax was asked for as line 24 without the refundable
    credits taken off. Then, Codex again: it was labelled Form 2210 line 8,
    which already carries the 110% the engine adds, so it must be asked for
    BEFORE the 110%."""
    page = client.get("/withholding").data
    assert b'name="refundable_credits"' in page and b"before any 110%" in page
    assert b"Form 2210 line 8" not in page
    resp = client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "12000", "federal_tax_withheld_per_period": "0",
        "refundable_credits": "1000"})
    assert resp.status_code == 200 and b"Total tax liability" in resp.data
    assert b"Refundable credits entered" in resp.data and b"1,000" in resp.data


def test_the_screen_offers_a_surviving_spouse_and_business_tips(client):
    """Codex on #451: a surviving spouse was run as a joint return, and tips
    from a business had nowhere to go apart from employee tips."""
    page = client.get("/withholding").data
    assert b'value="qualifying_surviving_spouse"' in page
    assert b'name="qualified_tips_business"' in page
    resp = client.post("/withholding", data={
        "filing_status": "qualifying_surviving_spouse", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "100000", "federal_tax_withheld_per_period": "0",
        "qualified_overtime": "20000"})
    # Single-filer overtime cap, joint brackets: see the engine test.
    assert b"$12,500" in _text(resp.data) and b"$6,243" in _text(resp.data)
    # The result header names the status (Codex: it rendered blank).
    assert "Tax year 2025 · Qualifying surviving spouse".encode() in _text(resp.data)


def test_spouse_pay_on_a_separate_return_is_refused_on_screen(client):
    resp = client.post("/withholding", data={
        "filing_status": "married_separately", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1", "owner": "spouse",
        "gross_pay_per_period": "100000", "federal_tax_withheld_per_period": "0"})
    assert resp.status_code == 200
    assert b"carries only your own pay" in resp.data and b"Total tax liability" not in resp.data


def test_the_screen_takes_qbi_inside_rents_and_credits_after_the_child_credit(client):
    page = client.get("/withholding").data
    assert b'name="qbi_from_rental_and_k1"' in page and b'name="credits_after_child_credit"' in page
    resp = client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "100000", "federal_tax_withheld_per_period": "0",
        "rental_and_passive_income": "100000", "qbi_from_rental_and_k1": "100000"})
    assert b"QBI deduction $20,000" in _text(resp.data), _text(resp.data)[:3000]
    # A later credit is posted and used: 2,071.50 of income tax less 2,000.
    later = client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025", "adjust_job": "0",
        "pay_frequency": "annual", "pay_periods_remaining": "1",
        "gross_pay_per_period": "35000", "federal_tax_withheld_per_period": "0",
        "credits_after_child_credit": "2000"})
    assert b"Other credits ($2,000) Total tax liability $72" in _text(later.data)
