"""Withholding estimator screen (Flask blueprint).

A household planning tool: add one or more **jobs** (each from a paystub — uploaded,
pasted, or typed), get a full-year federal projection across all of them, and a
per-paycheck W-4 (line 4c) recommendation on the job you choose to tune. Paystub
reading runs on-device and *learns*: once you teach an employer's layout, later
stubs from that employer fill in automatically. Tax constants come from SATC's
dated, cited crosswalk.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

from flask import Blueprint, render_template, request, send_file, session

from satc.app.state import STATE
from satc.ingest.paystub_layout import (
    TARGET_FIELDS,
    Layout,
    PaystubError,
    Profile,
    Word,
    apply_profile,
    build_rules,
    extract_layout,
)
from satc.ingest.paystub_profiles import match_profile, save_profile
from satc.ingest.paystub_templates import TemplateLibrary, learn, read_with_templates
from satc.ingest.readers.base import ReadResult
from satc.ingest.readers.paystub import (
    LABEL_EMPLOYER,
    LABEL_FED_WH_CURRENT,
    LABEL_FED_WH_YTD,
    LABEL_GROSS_CURRENT,
    LABEL_GROSS_YTD,
    LABEL_PAY_FREQUENCY,
    LABEL_RETIREMENT_CURRENT,
)
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

# Stored client filing-status codes (Drake-style) -> estimator codes.
_DRAKE_TO_ESTIMATOR_STATUS = {
    "S": "single", "MFJ": "married_jointly", "MFS": "married_separately",
    "HOH": "head_of_household", "QSS": "married_jointly",
}
_ESTIMATOR_STATUSES = {value for value, _ in FILING_STATUSES}


def _estimator_filing_status(stored: str) -> str:
    """Map a client's stored filing status to an estimator code (or '' if none)."""
    s = (stored or "").strip()
    if s in _ESTIMATOR_STATUSES:
        return s
    return _DRAKE_TO_ESTIMATOR_STATUS.get(s.upper(), "")

_JOBS_KEY = "wh_jobs"          # list[dict] of per-job paystub fields, per session
_HH_KEY = "wh_household"       # household-level fields (filing status, other income, ...)

_JOB_KEYS = ("name", "pay_frequency", "gross_pay_per_period",
             "federal_tax_withheld_per_period", "retirement_pretax_per_period",
             "ytd_taxable_wages", "ytd_federal_tax_withheld", "pay_periods_remaining")

_BLANK_JOB = {"pay_frequency": "biweekly", **{k: "" for k in _JOB_KEYS if k != "pay_frequency"}}

_HH_KEYS = ("filing_status", "tax_year", "interest", "ordinary_dividends",
            "qualified_dividends", "long_term_capital_gains", "short_term_capital_gains",
            "self_employment_net", "itemized_total", "extra_standard_deductions",
            "child_tax_credit", "other_nonrefundable_credits", "estimated_tax_payments",
            "target_refund", "prior_year_tax", "prior_year_agi")

_OTHER_INCOME_KEYS = ("interest", "ordinary_dividends", "qualified_dividends",
                      "long_term_capital_gains", "short_term_capital_gains", "self_employment_net")


def _clean_num(raw) -> str | None:
    """A money/number field -> cleaned string, or None when blank."""
    if raw is None:
        return None
    s = str(raw).replace(",", "").replace("$", "").strip()
    return s or None


def _str(value) -> str:
    if value is None or value == 0:
        return ""
    return f"{value}"


# --- session-backed job list -------------------------------------------------

def _jobs() -> list[dict]:
    return session.get(_JOBS_KEY, [])


def _set_jobs(jobs: list[dict]) -> None:
    session[_JOBS_KEY] = jobs
    session.modified = True


def _household() -> dict:
    return session.get(_HH_KEY, {})


def _collect_job_rows(form) -> list[dict] | None:
    """Parse edited job rows (``j{i}_*``) from a submitted form, newest order.

    Returns None when the form carries no job fields (so we don't wipe state on
    forms that aren't the main one). Falls back to flat single-job fields for
    backward compatibility.
    """
    idxs = sorted({int(m.group(1)) for k in form.keys() for m in [re.match(r"j(\d+)_", k)] if m})
    if idxs:
        return [{key: (form.get(f"j{i}_{key}") or "") for key in _JOB_KEYS} for i in idxs]
    if any(form.get(k) for k in ("gross_pay_per_period", "federal_tax_withheld_per_period")):
        return [{key: (form.get(key) or "") for key in _JOB_KEYS}]
    return None


def _sync(form) -> None:
    """Persist edited job rows + household fields from a main-form submission."""
    rows = _collect_job_rows(form)
    if rows is not None:
        _set_jobs(rows)
    hh = {k: form.get(k) for k in _HH_KEYS if form.get(k) is not None}
    hh["adjust_job"] = form.get("adjust_job", "0")
    session[_HH_KEY] = hh
    session.modified = True


def _job_from_read(read) -> dict:
    """Turn a paystub read into a job row (per-period + YTD figures)."""
    stub = paystub_from_fields(read.labeled_fields)
    return {
        "name": read.labeled_fields.get(LABEL_EMPLOYER, ""),
        "pay_frequency": stub.pay_frequency,
        "gross_pay_per_period": _str(stub.gross_pay_per_period),
        "federal_tax_withheld_per_period": _str(stub.federal_tax_withheld_per_period),
        "retirement_pretax_per_period": _str(stub.retirement_pretax_per_period),
        "ytd_taxable_wages": _str(stub.ytd_taxable_wages),
        "ytd_federal_tax_withheld": _str(stub.ytd_federal_tax_withheld),
        "pay_periods_remaining": "" if stub.pay_periods_remaining is None else str(stub.pay_periods_remaining),
    }


# --- estimate assembly -------------------------------------------------------

def _estimator_input(jobs: list[dict], hh: dict) -> EstimatorInput:
    adjust = int(_clean_num(hh.get("adjust_job")) or 0)
    job_inputs: list[dict] = []
    for i, job in enumerate(jobs):
        paystub: dict = {"pay_frequency": job.get("pay_frequency") or "biweekly"}
        for key in ("gross_pay_per_period", "federal_tax_withheld_per_period",
                    "retirement_pretax_per_period", "ytd_taxable_wages", "ytd_federal_tax_withheld"):
            val = _clean_num(job.get(key))
            if val is not None:
                paystub[key] = val
        remaining = _clean_num(job.get("pay_periods_remaining"))
        if remaining is not None:
            paystub["pay_periods_remaining"] = int(float(remaining))
        if (job.get("name") or "").strip():
            paystub["name"] = job["name"].strip()
        if i == adjust:
            paystub["adjust_withholding"] = True
        job_inputs.append(paystub)
    if not job_inputs:
        job_inputs = [{"pay_frequency": "biweekly"}]

    data: dict = {"filing_status": hh.get("filing_status", "single"), "jobs": job_inputs}
    year = _clean_num(hh.get("tax_year"))
    if year is not None:
        data["tax_year"] = int(float(year))

    other_income = {k: _clean_num(hh.get(k)) for k in _OTHER_INCOME_KEYS}
    other_income = {k: v for k, v in other_income.items() if v is not None}
    if other_income:
        data["other_income"] = other_income

    deductions: dict = {}
    itemized = _clean_num(hh.get("itemized_total"))
    if itemized is not None:
        deductions["itemized_total"] = itemized
    extra = _clean_num(hh.get("extra_standard_deductions"))
    if extra is not None:
        deductions["extra_standard_deductions"] = int(float(extra))
    if deductions:
        data["deductions"] = deductions

    credits = {k: _clean_num(hh.get(k)) for k in ("child_tax_credit", "other_nonrefundable_credits")}
    credits = {k: v for k, v in credits.items() if v is not None}
    if credits:
        data["credits"] = credits

    est = _clean_num(hh.get("estimated_tax_payments"))
    if est is not None:
        data["other_payments"] = {"estimated_tax_payments": est}

    for key in ("target_refund", "prior_year_tax", "prior_year_agi"):
        val = _clean_num(hh.get(key))
        if val is not None:
            data[key] = val
    return EstimatorInput.from_dict(data)


# --- rendering ---------------------------------------------------------------

def _teach_ctx(read, source_text: str) -> dict:
    lf = read.labeled_fields
    return {
        "source": source_text,
        "hint": lf.get(LABEL_EMPLOYER) or "this employer",
        "values": {
            "gross_cur": lf.get(LABEL_GROSS_CURRENT, ""),
            "gross_ytd": lf.get(LABEL_GROSS_YTD, ""),
            "fed_cur": lf.get(LABEL_FED_WH_CURRENT, ""),
            "fed_ytd": lf.get(LABEL_FED_WH_YTD, ""),
            "retire_cur": lf.get(LABEL_RETIREMENT_CURRENT, ""),
            "freq": lf.get(LABEL_PAY_FREQUENCY, ""),
        },
    }


def _render(*, result=None, teach=None, teach_layout=None, notes=None):
    hh = _household()
    return render_template(
        "withholding.html",
        title="Withholding",
        filing_statuses=FILING_STATUSES,
        frequencies=PAY_FREQUENCIES,
        years=available_years(),
        clients=STATE.client_choices(),
        jobs=_jobs(),
        hh=hh,
        adjust_job=int(_clean_num(hh.get("adjust_job")) or 0),
        result=result,
        teach=teach,
        teach_layout=teach_layout,
        prefill_notes=notes or [],
    )


# --- click-to-teach paystub reading -----------------------------------------

def _words_payload(words: list) -> list[dict]:
    return [{"text": w.text, "x0": w.x0, "y0": w.y0, "x1": w.x1, "y1": w.y1} for w in words]


def _labeled_from_fields(fields: dict, *, name: str = "", freq: str = "") -> dict:
    """Map click-to-teach output (job-field keys) to the canonical reader labels,
    so it flows through the same paystub_from_fields derivation as everything else."""
    m = {
        LABEL_GROSS_CURRENT: fields.get("gross_pay_per_period", ""),
        LABEL_FED_WH_CURRENT: fields.get("federal_tax_withheld_per_period", ""),
        LABEL_RETIREMENT_CURRENT: fields.get("retirement_pretax_per_period", ""),
        LABEL_GROSS_YTD: fields.get("ytd_taxable_wages", ""),
        LABEL_FED_WH_YTD: fields.get("ytd_federal_tax_withheld", ""),
    }
    chosen_freq = fields.get("pay_frequency") or freq
    if chosen_freq:
        m[LABEL_PAY_FREQUENCY] = chosen_freq
    if name:
        m[LABEL_EMPLOYER] = name
    return {k: v for k, v in m.items() if v}


def _match_keywords(words: list) -> list[str]:
    """Distinctive header tokens (employer/provider) so future stubs match."""
    seen: list[str] = []
    for w in sorted(words, key=lambda w: (w.y0, w.x0)):
        if w.y0 > 0.22:
            continue
        tok = re.sub(r"[^a-z]", "", w.text.lower())
        if len(tok) >= 4 and tok not in seen:
            seen.append(tok)
    return seen[:8]


def _add_job_from_fields(fields: dict, *, name: str, freq: str) -> None:
    labeled = _labeled_from_fields(fields, name=name, freq=freq)
    jobs = _jobs()
    jobs.append(_job_from_read(ReadResult(labeled_fields=labeled)))
    _set_jobs(jobs)


@bp.route("/withholding/paystub/layout", methods=["POST"])
def paystub_layout():
    """Read an uploaded paystub by rendering it + word boxes; auto-apply a known
    layout, else hand the page to the click-to-teach modal."""
    _sync(request.form)
    upload = request.files.get("paystub_file")
    if upload is None or not (upload.filename or "").strip():
        return _render(notes=["Choose a paystub file first, or paste its text."])
    data = upload.read()
    media = upload.mimetype or ""
    if not media and (upload.filename or "").lower().endswith(".pdf"):
        media = "application/pdf"
    try:
        layout = extract_layout(data, media)
    except PaystubError as exc:
        return _render(notes=[f"Couldn’t read that file: {exc}", "You can paste the paystub text instead."])

    profile = match_profile(layout)
    if profile is not None:
        _add_job_from_fields(apply_profile(layout, profile),
                             name=profile.name, freq=profile.pay_frequency or "")
        return _render(notes=[f"Recognized “{profile.name}” — read the paystub and added the job."])

    suggested = " ".join(w.text for w in sorted(layout.words, key=lambda w: (w.y0, w.x0))[:4])[:48]
    teach_layout = {
        "image": layout.image_png_b64,
        "words": _words_payload(layout.words),
        "targets": [{"key": k, "label": lbl} for k, lbl, _ in TARGET_FIELDS],
        "frequencies": PAY_FREQUENCIES,
        "suggested_name": suggested,
    }
    return _render(teach_layout=teach_layout,
                   notes=["New layout — click each figure on the paystub to map it (once per employer)."])


@bp.route("/withholding/paystub/teach", methods=["POST"])
def paystub_teach():
    """Turn the clicked words into a saved profile and add the job."""
    try:
        words_raw = json.loads(request.form.get("words", "[]"))
        assignments = json.loads(request.form.get("assignments", "{}"))
    except (ValueError, TypeError):
        return _render(notes=["Couldn’t read the mapping — please try again."])
    words = [Word(text=str(w.get("text", "")), x0=float(w["x0"]), y0=float(w["y0"]),
                  x1=float(w["x1"]), y1=float(w["y1"])) for w in words_raw if "x0" in w]
    assignments = {k: [int(i) for i in v] for k, v in assignments.items() if v}
    if not words or not assignments:
        return _render(notes=["Nothing was mapped — pick a field, then click its number on the paystub."])

    name = (request.form.get("profile_name") or "").strip() or "Saved paystub"
    freq = (request.form.get("pay_frequency") or "").strip().lower() or None
    profile = Profile(name=name, pay_frequency=freq,
                      rules=build_rules(words, assignments), match_keywords=_match_keywords(words))
    save_profile(profile)
    fields = apply_profile(Layout(image_png_b64="", img_width=0, img_height=0, words=words), profile)
    _add_job_from_fields(fields, name=name, freq=freq or "")
    return _render(notes=[f"Saved “{name}” and added the job — future stubs from this layout fill in automatically."])


# --- routes ------------------------------------------------------------------

@bp.route("/withholding", methods=["GET", "POST"])
def withholding():
    if request.method == "GET":
        return _render()
    _sync(request.form)
    try:
        result = estimate(_estimator_input(_jobs(), _household()))
    except Exception as exc:  # noqa: BLE001 - surface bad input as a message, not a 500
        return _render(notes=[f"Couldn’t run the estimate: {exc}"])
    return _render(result=result)


@bp.route("/withholding/add-job", methods=["POST"])
def add_job():
    _sync(request.form)
    jobs = _jobs()
    jobs.append(dict(_BLANK_JOB))
    _set_jobs(jobs)
    return _render()


@bp.route("/withholding/remove-job", methods=["POST"])
def remove_job():
    _sync(request.form)
    idx = int(_clean_num(request.form.get("remove_index")) or -1)
    jobs = _jobs()
    if 0 <= idx < len(jobs):
        jobs.pop(idx)
        _set_jobs(jobs)
    return _render()


@bp.route("/withholding/clear-jobs", methods=["POST"])
def clear_jobs():
    session.pop(_JOBS_KEY, None)
    session.modified = True
    return _render()


def _read_paystub_file(upload) -> tuple[str, str]:
    """Pull text from an uploaded paystub, local-first; returns ``(text, source note)``."""
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
                    "for local OCR, or paste the paystub text.")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _add_job_from_text(text: str, source_note: str | None):
    read, template = read_with_templates(text)
    jobs = _jobs()
    jobs.append(_job_from_read(read))
    _set_jobs(jobs)
    notes = [source_note] if source_note else []
    if template is not None:
        notes.append(f"Recognized {template.label_hint} — read from a saved layout.")
    return _render(notes=notes, teach=_teach_ctx(read, text))


@bp.route("/withholding/from-file", methods=["POST"])
def from_file():
    _sync(request.form)
    upload = request.files.get("paystub_file")
    if upload is None or not (upload.filename or "").strip():
        return _render(notes=["No file was selected — choose a paystub PDF or image, or paste the text."])
    text, note = _read_paystub_file(upload)
    return _add_job_from_text(text, note)


@bp.route("/withholding/from-paystub", methods=["POST"])
def from_paystub():
    _sync(request.form)
    return _add_job_from_text(request.form.get("paystub_text", ""), None)


@bp.route("/withholding/from-client", methods=["POST"])
def from_client():
    """Prefill stable household info (filing status) from an existing client.

    Per-paycheck figures still come from a paystub; prior-year dollar amounts are
    deliberately not seeded (a prior wage is a poor proxy for this year).
    """
    _sync(request.form)
    cid = (request.form.get("client_id") or "").strip()
    if not cid:
        return _render(notes=["Pick a client first."])
    pc = next((p for p in STATE.mart.public_clients if p.client_id == cid), None)
    if pc is None:
        return _render(notes=[f"Client “{cid}” not found."])

    notes = [f"Loaded {STATE.name(cid)}."]
    fs = _estimator_filing_status(getattr(pc, "filing_status", "") or "")
    if fs:
        hh = _household()
        hh["filing_status"] = fs
        session[_HH_KEY] = hh
        session.modified = True
        notes.append(f"Prefilled filing status: {dict(FILING_STATUSES)[fs]}. "
                     "Add a current paystub for the per-paycheck figures.")
    else:
        notes.append("No stored filing status to prefill — set it below.")
    return _render(notes=notes)


@bp.route("/withholding/save-layout", methods=["POST"])
def save_layout():
    src = request.form.get("paystub_src", "")
    confirmed = {
        LABEL_GROSS_CURRENT: request.form.get("t_gross_cur", ""),
        LABEL_GROSS_YTD: request.form.get("t_gross_ytd", ""),
        LABEL_FED_WH_CURRENT: request.form.get("t_fed_cur", ""),
        LABEL_FED_WH_YTD: request.form.get("t_fed_ytd", ""),
        LABEL_RETIREMENT_CURRENT: request.form.get("t_retire_cur", ""),
        LABEL_PAY_FREQUENCY: request.form.get("t_freq", ""),
    }
    confirmed = {k: v for k, v in confirmed.items() if v and v.strip()}
    if not src.strip() or not confirmed:
        return _render(notes=["Nothing to learn yet — read a paystub, then save its layout."])
    template = learn(src, confirmed)
    TemplateLibrary().save(template)
    return _render(notes=[f"Saved — future {template.label_hint} paystubs will fill in automatically."])


@bp.route("/withholding/audit.xlsx")
def audit_tape():
    """Download the audit tape for the current jobs/household."""
    jobs = _jobs()
    if not jobs:
        return ("Run an estimate first, then download its audit tape.", 400)
    inp = _estimator_input(jobs, _household())
    wb = build_audit_tape(estimate(inp), inp)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="SATC_Withholding_Estimate.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
