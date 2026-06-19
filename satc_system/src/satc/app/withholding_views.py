"""Withholding estimator screen (Flask blueprint).

Registered by :func:`satc.app.server.create_app`. A self-contained planning tool:
enter paystub + other-income figures (or paste a paystub's text to pre-fill them),
get a full-year federal projection and a per-paycheck W-4 line 4c recommendation,
and download the branded Excel audit tape. Tax constants come from SATC's dated,
cited crosswalk via :mod:`satc.withholding`.
"""

from __future__ import annotations

import io
from pathlib import Path

from flask import Blueprint, render_template, request, send_file, session

from satc.ingest.readers.paystub import PaystubReader
from satc.withholding import EstimatorInput, available_years, estimate, paystub_from_fields
from satc.withholding.audit_tape import build_audit_tape

bp = Blueprint("withholding", __name__)

FILING_STATUSES = [
    ("single", "Single"),
    ("married_jointly", "Married filing jointly"),
    ("married_separately", "Married filing separately"),
    ("head_of_household", "Head of household"),
]
PAY_FREQUENCIES = ["weekly", "biweekly", "semimonthly", "monthly", "annual"]
_SESSION_KEY = "withholding_form"   # last estimate's inputs, per browser session


def _num(form, key: str):
    """A money/number field -> cleaned string, or None when blank."""
    raw = (form.get(key) or "").replace(",", "").replace("$", "").strip()
    return raw or None


def _form_to_input(form) -> EstimatorInput:
    """Build an EstimatorInput from posted form fields (blanks dropped)."""
    paystub: dict = {"pay_frequency": form.get("pay_frequency", "biweekly")}
    for key in ("gross_pay_per_period", "federal_tax_withheld_per_period",
                "retirement_pretax_per_period", "ytd_taxable_wages",
                "ytd_federal_tax_withheld"):
        val = _num(form, key)
        if val is not None:
            paystub[key] = val
    remaining = _num(form, "pay_periods_remaining")
    if remaining is not None:
        paystub["pay_periods_remaining"] = int(float(remaining))

    other_income = {k: _num(form, k) for k in (
        "interest", "ordinary_dividends", "qualified_dividends",
        "long_term_capital_gains", "short_term_capital_gains", "self_employment_net")}
    other_income = {k: v for k, v in other_income.items() if v is not None}

    deductions: dict = {}
    itemized = _num(form, "itemized_total")
    if itemized is not None:
        deductions["itemized_total"] = itemized
    extra = _num(form, "extra_standard_deductions")
    if extra is not None:
        deductions["extra_standard_deductions"] = int(float(extra))

    credits = {k: _num(form, k) for k in ("child_tax_credit", "other_nonrefundable_credits")}
    credits = {k: v for k, v in credits.items() if v is not None}

    other_payments = {}
    est = _num(form, "estimated_tax_payments")
    if est is not None:
        other_payments["estimated_tax_payments"] = est

    data: dict = {
        "filing_status": form.get("filing_status", "single"),
        "paystub": paystub,
        "other_income": other_income,
        "deductions": deductions,
        "credits": credits,
        "other_payments": other_payments,
    }
    year = _num(form, "tax_year")
    if year is not None:
        data["tax_year"] = int(float(year))
    for key in ("target_refund", "prior_year_tax", "prior_year_agi"):
        val = _num(form, key)
        if val is not None:
            data[key] = val
    return EstimatorInput.from_dict(data)


def _ctx(**extra) -> dict:
    return {"title": "Withholding", "filing_statuses": FILING_STATUSES,
            "frequencies": PAY_FREQUENCIES, "years": available_years(),
            "form": {}, "result": None, "prefilled": False, "prefill_notes": [], **extra}


@bp.route("/withholding", methods=["GET", "POST"])
def withholding():
    if request.method == "GET":
        return render_template("withholding.html", **_ctx())
    form = request.form.to_dict()
    result = estimate(_form_to_input(form))
    session[_SESSION_KEY] = form          # so the audit tape can re-run it
    return render_template("withholding.html", **_ctx(form=form, result=result))


def _prefill_render(read, filing_status: str, *, lead_notes: list[str] | None = None):
    """Render the screen pre-filled from a paystub read (uploaded file or pasted text).

    Same conservative behavior either way: uncertain fields are flagged and the
    preparer confirms every figure before it counts.
    """
    stub = paystub_from_fields(read.labeled_fields)
    form = {
        "filing_status": filing_status,
        "pay_frequency": stub.pay_frequency,
        "gross_pay_per_period": _str(stub.gross_pay_per_period),
        "federal_tax_withheld_per_period": _str(stub.federal_tax_withheld_per_period),
        "retirement_pretax_per_period": _str(stub.retirement_pretax_per_period),
        "ytd_taxable_wages": _str(stub.ytd_taxable_wages),
        "ytd_federal_tax_withheld": _str(stub.ytd_federal_tax_withheld),
        "pay_periods_remaining": "" if stub.pay_periods_remaining is None
        else str(stub.pay_periods_remaining),
    }
    notes = list(lead_notes or [])
    if not read.labeled_fields:
        notes.append("No paystub figures could be read — enter them by hand.")
    else:
        notes += [f"Read “{lbl}” — please confirm." for lbl in sorted(read.uncertain_labels)]
    return render_template("withholding.html", **_ctx(form=form, prefilled=True,
                                                      prefill_notes=notes))


def _read_paystub_file(upload) -> tuple[str, str]:
    """Pull text from an uploaded paystub, local-first; returns ``(text, source note)``.

    Reuses the same on-device reader ladder as the rest of SATC: text-layer PDFs
    are read with pypdf, and scans/images fall back to local OCR (Tesseract) when
    available. The cloud is never used here — nothing leaves the machine.
    """
    import os
    import tempfile

    from werkzeug.utils import secure_filename

    from satc import settings
    from satc.ingest.readers.paystub import _page_text

    name = upload.filename or "paystub"
    suffix = Path(secure_filename(name)).suffix.lower()
    fd, tmp = tempfile.mkstemp(suffix=suffix or ".pdf")
    try:
        with os.fdopen(fd, "wb") as handle:
            upload.save(handle)

        text = _page_text(tmp) if suffix == ".pdf" else ""
        if text.strip():
            return text, f"Read “{name}” from its PDF text layer — on this machine."

        if settings.ocr_enabled():
            from satc.ingest.ocr import ocr_document_text
            text = ocr_document_text(tmp)
            if text.strip():
                return text, f"Read “{name}” with local OCR — on this machine."

        return "", (f"Couldn’t pull text from “{name}”. If it’s a scan, install Tesseract "
                    "for local OCR, or paste the paystub text below.")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


@bp.route("/withholding/from-paystub", methods=["POST"])
def from_paystub():
    """Read pasted paystub text and pre-fill the form (uncertain fields flagged)."""
    read = PaystubReader().read_text(request.form.get("paystub_text", ""))
    return _prefill_render(read, request.form.get("filing_status", "single"))


@bp.route("/withholding/from-file", methods=["POST"])
def from_file():
    """Read an uploaded paystub (PDF or image) on-device and pre-fill the form."""
    upload = request.files.get("paystub_file")
    if upload is None or not (upload.filename or "").strip():
        return render_template("withholding.html", **_ctx(
            prefilled=True,
            prefill_notes=["No file was selected — choose a paystub PDF or image, or paste the text below."]))
    text, note = _read_paystub_file(upload)
    return _prefill_render(PaystubReader().read_text(text),
                           request.form.get("filing_status", "single"),
                           lead_notes=[note] if note else None)


@bp.route("/withholding/audit.xlsx")
def audit_tape():
    """Download the audit tape for the most recent estimate."""
    form = session.get(_SESSION_KEY)
    if not form:
        return ("Run an estimate first, then download its audit tape.", 400)
    inp = _form_to_input(form)
    wb = build_audit_tape(estimate(inp), inp)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="SATC_Withholding_Estimate.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _str(value) -> str:
    if value is None or value == 0:
        return ""
    return f"{value}"
