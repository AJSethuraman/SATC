"""Slice 7 (issue #66): the no-PII-leak guard (PRD Seam 3).

Byte-level and object-level assertions that PII never escapes its boundary:
no full TIN pattern anywhere, borrower names and loan numbers only in the
engagement workbook's own tabs (never the de-identified mart, findings
export, or metadata), every committed fixture synthetic, and the builder
masks a TIN-shaped value even when the loaders are bypassed.
"""

import io
import json
import re
import zipfile
from pathlib import Path

import pytest

from credit_review import (
    Loan,
    build_demo_workbook,
    ingest_workbook,
    load_engagement,
    load_loans,
    load_program,
    workbook_bytes,
)
from credit_review.workbook import ENGAGEMENTS_DIR, PROGRAMS_DIR, build_engagement_workbook

# The only borrower identities allowed to exist anywhere in this repository.
SYNTHETIC_NAMES = ("Blue Heron Fabrication LLC", "Cedar Creek Outfitters Inc",
                   "Harbor Point Logistics LLC", "Sunview Orchards LP")
LOAN_NUMBERS = ("40017-3", "51230-8", "61022-1", "70415-9")

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")
NINE_DIGIT_RE = re.compile(r"\b\d{9}\b")

# Sheets where borrower identity is allowed (the bank's own data, returned to
# the bank) vs the de-identified surfaces.
DEIDENTIFIED_SHEETS = ("Data Mart", "Findings", "_methodology", "_config", "_map")


def _workbook_xml_text(data: bytes) -> str:
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith(".xml"):
                out.append(z.read(name).decode("utf-8", errors="ignore"))
    return "\n".join(out)


def test_saved_workbook_carries_no_full_tin_pattern():
    wb, *_ = build_demo_workbook()
    text = _workbook_xml_text(workbook_bytes(wb))
    assert not SSN_RE.search(text)
    assert not EIN_RE.search(text)
    assert not NINE_DIGIT_RE.search(text)


def test_names_and_loan_numbers_stay_out_of_deidentified_sheets():
    wb, *_ = build_demo_workbook()
    for sheet in DEIDENTIFIED_SHEETS:
        cells = " | ".join(str(c.value) for row in wb[sheet].iter_rows()
                           for c in row if c.value is not None)
        for name in SYNTHETIC_NAMES:
            assert name not in cells, sheet
        for number in LOAN_NUMBERS:
            assert number not in cells, sheet


def test_ingest_exports_are_clean():
    wb, *_ = build_demo_workbook()
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(workbook_bytes(wb))
        mart, findings = ingest_workbook(path)
    finally:
        os.unlink(path)
    dumped = json.dumps(mart.rows) + json.dumps(findings.records) \
        + json.dumps(findings.open_by_loan)
    for name in SYNTHETIC_NAMES:
        assert name not in dumped
    for number in LOAN_NUMBERS:
        assert number not in dumped
    assert not SSN_RE.search(dumped) and not EIN_RE.search(dumped) \
        and not NINE_DIGIT_RE.search(dumped)


def test_builder_masks_tin_even_when_loaders_are_bypassed():
    program = load_program(PROGRAMS_DIR / "c_and_i.yaml")
    engagement = load_engagement(ENGAGEMENTS_DIR / "demo_engagement.yaml")
    sneaky = Loan(loan_id="X-0001", values={
        "borrower_name": "Blue Heron Fabrication LLC",
        "tin_last4": "123-45-6789",      # a full TIN forced past the loader
        "rating_originator": "4"})
    wb = build_engagement_workbook(program, engagement, [sneaky])
    ls = wb["LS_X-0001"]
    rows = {ls.cell(r, 2).value: r for r in range(1, ls.max_row + 1) if ls.cell(r, 2).value}
    assert ls.cell(rows["TIN (last 4 only)"], 3).value == "6789"
    text = _workbook_xml_text(workbook_bytes(wb))
    assert not SSN_RE.search(text) and not NINE_DIGIT_RE.search(text)


def test_committed_fixtures_are_synthetic_only():
    # every engagement fixture in the repo: TINs last-4 only, no full-TIN
    # shapes anywhere, and borrower names only from the synthetic set
    for path in Path(ENGAGEMENTS_DIR).glob("*.yaml"):
        raw = path.read_text(encoding="utf-8")
        assert not SSN_RE.search(raw), path.name
        assert not EIN_RE.search(raw), path.name
        assert not NINE_DIGIT_RE.search(raw), path.name
    loans = load_loans(ENGAGEMENTS_DIR / "demo_c_and_i_loans.yaml")
    for loan in loans:
        name = loan.values.get("borrower_name", "")
        assert name in SYNTHETIC_NAMES, name
        tin = str(loan.values.get("tin_last4", ""))
        assert re.fullmatch(r"\d{4}", tin), tin
