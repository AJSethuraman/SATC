"""Seam 1 (PRD §7): the in-memory builder.

Asserts against the ``openpyxl.Workbook`` object returned by
``build_engagement_workbook`` — config parse/validation, sheet presence, house
style, live formula wiring, TIN last-4 discipline, and byte-level determinism.
"""

import io
import re
import zipfile
from pathlib import Path

import pytest
import yaml

from credit_review import (
    ConfigError,
    build_demo_workbook,
    build_engagement_workbook,
    load_engagement,
    load_loans,
    load_program,
    workbook_bytes,
)
from credit_review import keybank_style as KB
from credit_review.workbook import ENGAGEMENTS_DIR, PROGRAMS_DIR

PROGRAM_PATH = PROGRAMS_DIR / "c_and_i.yaml"
ENGAGEMENT_PATH = ENGAGEMENTS_DIR / "demo_engagement.yaml"


@pytest.fixture(scope="module")
def built():
    wb, program, engagement, loans = build_demo_workbook()
    return wb, program, engagement, loans


# ---------------------------------------------------------------------------
# Config parse + validation
# ---------------------------------------------------------------------------
def test_program_parses_with_review_mode_and_framework():
    program = load_program(PROGRAM_PATH)
    assert program.lob == "c_and_i"
    assert program.review_mode == "loan_level"
    assert program.buckets == ("Pass", "Special Mention", "Substandard", "Doubtful", "Loss")
    assert program.criticized == ("Special Mention", "Substandard", "Doubtful", "Loss")
    assert program.classified == ("Substandard", "Doubtful", "Loss")
    titles = [s["title"] for s in program.sections]
    assert "Identification & exposure" in titles


def test_engagement_overlay_parses():
    engagement = load_engagement(ENGAGEMENT_PATH)
    assert engagement.client_name == "Demo Community Bank"
    assert engagement.engagement_id == "DEMO-2026-01"
    assert engagement.rating_scale_map["6"] == "Special Mention"
    assert engagement.thresholds["dscr_floor"] == pytest.approx(1.20)
    assert engagement.reviewer["independent"] is True
    loans = load_loans(engagement.loans_path)
    assert [loan.loan_id for loan in loans] == ["CI-0001", "CI-0002", "CI-0003", "CI-0004"]


def _write_yaml(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return p


def _program_dict(**overrides):
    base = yaml.safe_load(PROGRAM_PATH.read_text(encoding="utf-8"))
    base.update(overrides)
    return base


def test_program_rejects_unknown_review_mode(tmp_path):
    data = _program_dict()
    data["meta"]["review_mode"] = "vibes"
    with pytest.raises(ConfigError, match="review_mode"):
        load_program(_write_yaml(tmp_path, "bad.yaml", data))


def test_program_must_stay_client_agnostic(tmp_path):
    data = _program_dict(thresholds={"dscr_floor": 1.0})
    with pytest.raises(ConfigError, match="client-specific"):
        load_program(_write_yaml(tmp_path, "bad.yaml", data))


def test_product_conformance_is_schema_valid_but_not_buildable(tmp_path):
    data = _program_dict()
    data["meta"]["review_mode"] = "product_conformance"
    program = load_program(_write_yaml(tmp_path, "mode_b.yaml", data))  # schema carries it
    engagement = load_engagement(ENGAGEMENT_PATH)
    loans = load_loans(engagement.loans_path)
    with pytest.raises(ConfigError, match="not built yet"):
        build_engagement_workbook(program, engagement, loans)


def test_loans_reject_full_tin_fields_and_values(tmp_path):
    with pytest.raises(ConfigError, match="last-4"):
        load_loans(_write_yaml(tmp_path, "l1.yaml",
                               {"loans": [{"loan_id": "X-1", "tin": "12-3456789"}]}))
    with pytest.raises(ConfigError, match="last-4"):
        load_loans(_write_yaml(tmp_path, "l2.yaml",
                               {"loans": [{"loan_id": "X-1", "note": "SSN 123-45-6789"}]}))
    with pytest.raises(ConfigError, match="tin_last4"):
        load_loans(_write_yaml(tmp_path, "l3.yaml",
                               {"loans": [{"loan_id": "X-1", "tin_last4": "123456789"}]}))


def test_overlay_grades_must_map_into_program_buckets(tmp_path):
    program = load_program(PROGRAM_PATH)
    data = yaml.safe_load(ENGAGEMENT_PATH.read_text(encoding="utf-8"))
    data["rating_scale_map"]["6"] = "Watch"   # not a regulatory bucket
    data["loans"] = str(ENGAGEMENTS_DIR / "demo_c_and_i_loans.yaml")
    engagement = load_engagement(_write_yaml(tmp_path, "e.yaml", data))
    loans = load_loans(engagement.loans_path)
    with pytest.raises(ConfigError, match="rating_scale_map"):
        build_engagement_workbook(program, engagement, loans)


# ---------------------------------------------------------------------------
# Sheet presence + house style
# ---------------------------------------------------------------------------
def test_sheet_presence_and_order(built):
    wb, _, _, loans = built
    assert wb.sheetnames == (["Cover"] + [f"LS_{l.loan_id}" for l in loans]
                             + ["Master", "Findings", "_config"])


def test_house_style_banner_and_gridlines(built):
    wb, program, engagement, _ = built
    for name in wb.sheetnames:
        assert wb[name].sheet_view.showGridLines is False, name
    for name in ("Cover", "LS_CI-0001"):
        banner = wb[name]["A1"]
        assert banner.fill.fgColor.rgb.endswith(KB.INK), name       # ink banner band
        assert banner.font.name == "Arial" and banner.font.bold, name
        assert banner.font.color.rgb.endswith(KB.PAPER), name
        # the single red accent rule on the banner's bottom edge
        assert wb[name]["A2"].border.bottom.color.rgb.endswith(KB.KEY_RED), name
    cover = wb["Cover"]
    assert cover["A1"].value == f"Loan Review — {engagement.client_name}"
    assert program.title in wb["LS_CI-0001"]["A1"].value


def test_linesheet_inputs_are_house_styled_input_cells(built):
    wb, _, _, _ = built
    ls = wb["LS_CI-0001"]
    labels = {ls.cell(r, 2).value: ls.cell(r, 3) for r in range(1, ls.max_row + 1)
              if ls.cell(r, 2).value}
    for label in ("Borrower (legal name)", "Total commitment",
                  "Originator risk rating"):
        cell = labels[label]
        assert cell.fill.fgColor.rgb.endswith(KB.CANVAS), label     # input tint
        assert cell.border.left.style == "thin", label
    assert labels["Total commitment"].value == 2500000
    assert labels["Total commitment"].number_format.startswith("$")
    assert labels["Borrower (legal name)"].value == "Blue Heron Fabrication LLC"


def test_computed_row_ships_a_live_formula_not_a_result(built):
    wb, _, _, _ = built
    ls = wb["LS_CI-0001"]
    formulas = {ls.cell(r, 2).value: ls.cell(r, 3).value
                for r in range(1, ls.max_row + 1) if ls.cell(r, 2).value}
    unfunded = formulas["Unfunded commitment"]
    assert isinstance(unfunded, str) and unfunded.startswith("=")
    # references the commitment and outstanding cells, not a hardcoded 750000
    refs = re.findall(r"C\d+", unfunded)
    assert len(refs) == 2 and "750000" not in unfunded


def test_config_sheet_is_the_knob_panel(built):
    wb, program, engagement, _ = built
    ws = wb["_config"]
    col_a = [ws.cell(r, 1).value for r in range(1, ws.max_row + 1)]
    for band in ("[ENGAGEMENT]", "[THRESHOLDS]", "[RATING_SCALE_MAP]", "[RATING_FRAMEWORK]"):
        assert band in col_a, band
        band_cell = ws.cell(col_a.index(band) + 1, 1)
        assert band_cell.fill.fgColor.rgb.endswith(KB.ONYX)          # onyx system band
    # every overlay threshold surfaces as an editable knob
    for key, value in engagement.thresholds.items():
        r = col_a.index(key) + 1
        assert ws.cell(r, 2).value == pytest.approx(value), key
    assert "review_mode" in col_a
    assert ws.cell(col_a.index("review_mode") + 1, 2).value == program.review_mode


# ---------------------------------------------------------------------------
# PII: TIN last-4 only
# ---------------------------------------------------------------------------
def test_workbook_carries_no_full_tin(built):
    wb, _, _, _ = built
    data = workbook_bytes(wb)
    shared = b""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith(".xml"):
                shared += z.read(name)
    text = shared.decode("utf-8", errors="ignore")
    assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", text)   # no dashed SSN
    assert not re.search(r"\b\d{2}-\d{7}\b", text)         # no dashed EIN
    for last4 in ("6789", "4821", "9034", "2277"):          # the last-4s are present
        assert last4 in text


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_build_is_byte_identical():
    b1 = workbook_bytes(build_demo_workbook()[0])
    b2 = workbook_bytes(build_demo_workbook()[0])
    assert b1 == b2
