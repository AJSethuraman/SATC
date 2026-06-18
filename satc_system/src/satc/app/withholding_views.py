"""Withholding estimator screen (Flask blueprint).

Registered by :func:`satc.app.server.create_app`. A self-contained planning tool:
enter paystub + other-income figures (or paste a paystub's text to pre-fill them),
get a full-year federal projection and a per-paycheck W-4 line 4c recommendation,
and download the branded Excel audit tape. Tax constants come from SATC's dated,
cited crosswalk via :mod:`satc.withholding`.
"""

from __future__ import annotations

import io

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


@bp.route("/withholding/from-paystub", methods=["POST"])
def from_paystub():
    """Read pasted paystub text and pre-fill the form (uncertain fields flagged)."""
    read = PaystubReader().read_text(request.form.get("paystub_text", ""))
    stub = paystub_from_fields(read.labeled_fields)
    form = {
        "filing_status": request.form.get("filing_status", "single"),
        "pay_frequency": stub.pay_frequency,
        "gross_pay_per_period": _str(stub.gross_pay_per_period),
        "federal_tax_withheld_per_period": _str(stub.federal_tax_withheld_per_period),
        "retirement_pretax_per_period": _str(stub.retirement_pretax_per_period),
        "ytd_taxable_wages": _str(stub.ytd_taxable_wages),
        "ytd_federal_tax_withheld": _str(stub.ytd_federal_tax_withheld),
        "pay_periods_remaining": "" if stub.pay_periods_remaining is None
        else str(stub.pay_periods_remaining),
    }
    if not read.labeled_fields:
        notes = ["No paystub figures could be read from that text — enter them by hand."]
    else:
        notes = [f"Read “{lbl}” — please confirm." for lbl in sorted(read.uncertain_labels)]
    return render_template("withholding.html", **_ctx(form=form, prefilled=True,
                                                      prefill_notes=notes))


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
