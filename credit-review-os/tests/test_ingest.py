"""Slice 5 (issue #64): de-identified Data Mart + re-ingest round-trip (Seam 2).

Build the demo -> programmatically key reviewer assessments -> save ->
``ingest_workbook`` -> assert the mart is de-identified (no name, no loan
number, no full TIN) and the portfolio findings match the workbook's own
Findings/Master aggregates.
"""

import json

import pytest

from credit_review import build_demo_workbook, ingest_workbook, workbook_bytes
from credit_review.mart import MART_COLUMNS

SYNTHETIC_NAMES = ("Blue Heron", "Cedar Creek", "Harbor Point", "Sunview")
LOAN_NUMBERS = ("40017-3", "51230-8", "61022-1", "70415-9")


@pytest.fixture(scope="module")
def filled_workbook_path(tmp_path_factory):
    """The demo engagement with the reviewer's remaining assessment keyed."""
    wb, *_ = build_demo_workbook()
    ls = wb["LS_CI-0001"]
    rows = {ls.cell(r, 2).value: r for r in range(1, ls.max_row + 1) if ls.cell(r, 2).value}
    ls.cell(rows["Reviewer risk rating (independent)"], 3, "4")   # concur: Pass
    path = tmp_path_factory.mktemp("ingest") / "filled.xlsx"
    path.write_bytes(workbook_bytes(wb))
    return path


@pytest.fixture(scope="module")
def round_trip(filled_workbook_path):
    return ingest_workbook(filled_workbook_path)


def test_mart_sheet_is_deidentified_flat_grid():
    wb, _, engagement, loans = build_demo_workbook()
    ws = wb["Data Mart"]
    headers = [ws.cell(1, c).value for c in range(1, len(MART_COLUMNS) + 1)]
    assert headers == MART_COLUMNS
    ids = [ws.cell(r, 1).value for r in range(2, 2 + len(loans))]
    assert ids == [f"{engagement.engagement_id}-L{i:02d}" for i in range(1, 5)]
    # no borrower/loan-number/TIN column, and data cells are formulas into Master
    text = " ".join(str(ws.cell(r, c).value) for r in range(1, ws.max_row + 1)
                    for c in range(1, ws.max_column + 1))
    for name in SYNTHETIC_NAMES:
        assert name not in text
    for number in LOAN_NUMBERS:
        assert number not in text
    assert "=Master!" in text


def test_ingest_returns_deidentified_mart(round_trip):
    mart, _ = round_trip
    assert mart.engagement_id == "DEMO-2026-01"
    assert mart.lob == "c_and_i"
    assert [r["mart_id"] for r in mart.rows] == [f"DEMO-2026-01-L{i:02d}" for i in range(1, 5)]
    dumped = json.dumps(mart.rows)
    for name in SYNTHETIC_NAMES:
        assert name not in dumped
    for number in LOAN_NUMBERS:
        assert number not in dumped
    for last4 in ("6789", "4821", "9034", "2277"):
        assert last4 not in dumped.replace('"committed"', "")   # no TIN, even last-4


def test_ingest_mart_reflects_keyed_assessments(round_trip):
    mart, _ = round_trip
    by_id = {r["mart_id"]: r for r in mart.rows}
    assert by_id["DEMO-2026-01-L01"]["rev_grade"] == "4"          # keyed in the fill step
    assert by_id["DEMO-2026-01-L01"]["bucket"] == "Pass"
    assert by_id["DEMO-2026-01-L02"]["bucket"] == "Special Mention"
    assert by_id["DEMO-2026-01-L03"]["classified"] is True
    assert by_id["DEMO-2026-01-L04"]["bucket"] == "Doubtful"
    assert by_id["DEMO-2026-01-L04"]["outstanding"] == 800000


def test_portfolio_findings_match_workbook_aggregates(round_trip):
    _, findings = round_trip
    # Same hand-tallied expectations the Findings sheet recalc tests assert —
    # the re-ingest pass must agree with the workbook's own aggregates.
    assert findings.open_by_class == {"policy": 9, "documentation": 6,
                                      "compliance": 1, "rating": 2}
    assert findings.open_by_severity == {"high": 10, "medium": 7, "low": 1}
    assert findings.fired_by_status == {"open": 18}
    assert findings.total_open == 18
    assert findings.open_by_loan == {"DEMO-2026-01-L01": 3, "DEMO-2026-01-L02": 2,
                                     "DEMO-2026-01-L03": 6, "DEMO-2026-01-L04": 7}
    assert findings.criticized_dollars == 4300000
    assert findings.criticized_count == 3
    assert findings.classified_dollars == 3400000
    assert findings.classified_count == 2


def test_findings_records_are_deidentified(round_trip):
    _, findings = round_trip
    dumped = json.dumps(findings.records)
    for name in SYNTHETIC_NAMES:
        assert name not in dumped
    assert all(r["mart_id"].startswith("DEMO-2026-01-L") for r in findings.records)


def test_waiver_flows_through_reingest(filled_workbook_path, tmp_path):
    wb, *_ = build_demo_workbook()
    ls = wb["LS_CI-0001"]
    rows = {ls.cell(r, 2).value: r for r in range(1, ls.max_row + 1) if ls.cell(r, 2).value}
    ls.cell(rows["LTV above policy ceiling (approved with mitigant)"], 5, "waived")
    path = tmp_path / "waived.xlsx"
    path.write_bytes(workbook_bytes(wb))
    _, findings = ingest_workbook(path)
    assert findings.open_by_class["policy"] == 8
    assert findings.fired_by_status == {"open": 17, "waived": 1}
    assert findings.total_open == 17
