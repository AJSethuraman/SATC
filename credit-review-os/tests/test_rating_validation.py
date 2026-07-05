"""Slice 2 (issue #61): independent rating validation as a live formula.

The disagreement test must be a live `_config` lookup — MAP() resolves each
entered grade to its regulatory bucket via VLOOKUP against the rating-scale
map, and the rating finding fires only when the two grades map to *different
buckets*. Verified with the `formulas` recalc engine against hardcoded
expected values (Seam 1).
"""

import pytest

from credit_review import build_demo_workbook, workbook_bytes
from credit_review.linesheet import CLEAR_FLAG, OPEN_FLAG

from recalc import Recalc

LS = "LS_CI-0001"


def _cells(ws):
    """label -> row lookup for a linesheet."""
    return {ws.cell(r, 2).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value}


def _flag_after_review(reviewer_grade):
    """Build the demo, key the reviewer's independent rating, recalc, return the flag."""
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    rows = _cells(ws)
    ws.cell(rows["Reviewer rating"], 3, reviewer_grade)
    flag_row = rows["Rating disagreement"]
    return Recalc(workbook_bytes(wb)).value(LS, f"C{flag_row}"), flag_row


def test_rating_cells_resolve_via_config_lookup_not_precomputed():
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    rows = _cells(ws)
    flag = ws.cell(rows["Rating disagreement"], 3).value
    # Live formula wired to the _config rating-scale map — never a boolean.
    assert isinstance(flag, str) and flag.startswith("=")
    assert flag.count("VLOOKUP") == 2 and "_config!" in flag


def test_disagreement_across_buckets_raises_rating_finding():
    # Originator grade 4 -> Pass; reviewer 7 -> Substandard: different buckets.
    flag, _ = _flag_after_review("7")
    assert flag == OPEN_FLAG


def test_same_bucket_raises_no_finding_even_for_different_grade():
    # Originator 4 -> Pass; reviewer 5 -> also Pass: no finding.
    flag, _ = _flag_after_review("5")
    assert flag == CLEAR_FLAG


def test_agreement_raises_no_finding():
    flag, _ = _flag_after_review("4")
    assert flag == CLEAR_FLAG


def test_blank_reviewer_rating_leaves_flag_blank():
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    flag_row = _cells(ws)["Rating disagreement"]
    value = Recalc(workbook_bytes(wb)).value(LS, f"C{flag_row}")
    assert value in ("", None)


def test_exception_row_carries_tracking_fields():
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    r = _cells(ws)["Rating disagreement"]
    assert ws.cell(r, 4).value == "rating / high"       # class / severity
    assert ws.cell(r, 5).value == "open"                # status default
    for col in (5, 6, 7, 8):                             # status/owner/due/cleared inputs
        assert ws.cell(r, col).fill.fgColor.rgb.endswith("F4F1EC"), col
