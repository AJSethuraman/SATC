"""Slice 3 (issue #62): the exception engine + evidence staleness + Findings.

Every rule is a live formula against the ``_config`` knob panel; the recalc
engine proves each fires (or stays clean) against hardcoded expected values
for the synthetic fixture — including a stale-evidence case, a missing-
evidence case, an approved-with-mitigant case, and the waived-status path
through the Findings aggregates (Seam 1).
"""

from datetime import date

import pytest

from credit_review import build_demo_workbook, load_program, workbook_bytes
from credit_review.config import ConfigError
from credit_review.linesheet import CLEAR_FLAG, OPEN_FLAG
from credit_review.workbook import PROGRAMS_DIR

from recalc import Recalc

LS = "LS_CI-0001"


def _rows(ws):
    return {ws.cell(r, 2).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value}


def _fnd_rows(ws):
    """Findings aggregate labels live in column A (last occurrence wins is fine —
    labels are unique except loan ids, which only appear once as aggregates)."""
    return {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1)
            if ws.cell(r, 1).value and not str(ws.cell(r, 1).value).startswith("Open")}


@pytest.fixture(scope="module")
def demo_recalc():
    wb, *_ = build_demo_workbook()
    return Recalc(workbook_bytes(wb)), _rows(wb[LS]), _fnd_rows(wb["Findings"])


# ---------------------------------------------------------------------------
# Policy exceptions vs [POL] thresholds
# ---------------------------------------------------------------------------
def test_dscr_below_floor_fires(demo_recalc):
    rc, rows, _ = demo_recalc
    assert rc.value(LS, f"C{rows['DSCR']}") == pytest.approx(400000 / 380000)
    assert rc.value(LS, f"C{rows['DSCR below policy floor']}") == OPEN_FLAG


def test_ltv_over_ceiling_fires_as_approved_with_mitigant(demo_recalc):
    rc, rows, _ = demo_recalc
    assert rc.value(LS, f"C{rows['Loan-to-value']}") \
        == pytest.approx(0.875)
    r = rows["LTV above policy ceiling"]
    assert rc.value(LS, f"C{r}") == OPEN_FLAG


def test_leverage_inside_ceiling_stays_clean(demo_recalc):
    rc, rows, _ = demo_recalc
    assert rc.value(LS, f"C{rows['Leverage']}") == pytest.approx(3400000 / 900000)
    assert rc.value(LS, f"C{rows['Leverage above policy ceiling']}") == CLEAR_FLAG


def test_dscr_clears_when_cash_flow_improves():
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    rows = _rows(ws)
    ws.cell(rows["Global cash flow"], 3, 600000)
    rc = Recalc(workbook_bytes(wb))
    assert rc.value(LS, f"C{rows['DSCR below policy floor']}") == CLEAR_FLAG


# ---------------------------------------------------------------------------
# Compliance exception
# ---------------------------------------------------------------------------
def test_flood_exception_fires_only_for_uninsured_flood_zone(demo_recalc):
    rc, rows, _ = demo_recalc
    assert rc.value(LS, f"C{rows['Flood insurance missing for flood-zone collateral']}") \
        == CLEAR_FLAG   # fixture: not in a flood zone
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    r = _rows(ws)
    ws.cell(r["Collateral in a flood zone?"], 3, "yes")
    ws.cell(r["Flood insurance current?"], 3, "no")
    rc2 = Recalc(workbook_bytes(wb))
    assert rc2.value(LS, f"C{r['Flood insurance missing for flood-zone collateral']}") \
        == OPEN_FLAG


# ---------------------------------------------------------------------------
# Evidence currency
# ---------------------------------------------------------------------------
def test_stale_bbc_raises_documentation_exception(demo_recalc):
    rc, rows, _ = demo_recalc
    # BBC as of 2026-03-31 vs review_as_of 2026-06-30 = 91 days > 45-day window.
    assert rc.value(LS, f"C{rows['Borrowing-base certificate stale or missing']}") == OPEN_FLAG


def test_current_evidence_stays_clean(demo_recalc):
    rc, rows, _ = demo_recalc
    assert rc.value(LS, f"C{rows['Financial statements stale or missing']}") == CLEAR_FLAG
    assert rc.value(LS, f"C{rows['Covenant compliance certificate stale or missing']}") \
        == CLEAR_FLAG
    assert rc.value(LS, f"C{rows['Credit approval / memo missing from file']}") == CLEAR_FLAG


def test_missing_evidence_date_raises_exception():
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    rows = _rows(ws)
    ws.cell(rows["Financial statements — as-of date"], 3).value = None   # not in the file
    rc = Recalc(workbook_bytes(wb))
    assert rc.value(LS, f"C{rows['Financial statements stale or missing']}") == OPEN_FLAG


def test_appraisal_is_condition_driven_not_clocked():
    program = load_program(PROGRAMS_DIR / "c_and_i.yaml")
    rows = [r for s in program.sections for r in s["rows"]]
    appraisal_exc = next(r for r in rows if r.get("id") == "ev_appraisal_exc")
    # No fixed day-count: the test is the reviewer's validity judgment.
    assert "[POL" not in appraisal_exc["when"] and "[ASOF]" not in appraisal_exc["when"]

    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    r = _rows(ws)
    valid = r["Collateral appraisal — still valid for current conditions? (yes/no)"]
    ws.cell(valid, 3, "no")
    rc = Recalc(workbook_bytes(wb))
    assert rc.value(LS, f"C{r['Collateral appraisal no longer valid']}") == OPEN_FLAG


# ---------------------------------------------------------------------------
# Findings register + aggregates
# ---------------------------------------------------------------------------
def _agg_value(rc, fnd_rows, label):
    return rc.value("Findings", f"B{fnd_rows[label]}")


def test_findings_register_has_one_row_per_loan_exception(demo_recalc):
    wb, program, _, loans = build_demo_workbook()
    fnd = wb["Findings"]
    rule_count = sum(1 for s in program.sections for r in s["rows"]
                     if r.get("kind") == "exception")
    register_rows = [r for r in range(1, fnd.max_row + 1)
                     if "'LS_" in str(fnd.cell(r, 6).value or "")]
    assert len(register_rows) == rule_count * len(loans) == 40
    # subtype is representable and drives severity: the mitigated LTV rule
    ltv = next(r for r in register_rows
               if "LTV above" in str(fnd.cell(r, 2).value))
    assert fnd.cell(ltv, 4).value == "approved_with_mitigant"
    assert fnd.cell(ltv, 5).value == "medium"


def test_open_counts_by_class_match_fixture(demo_recalc):
    rc, _, fnd = demo_recalc
    # Hand-tallied from the 4-loan fixture (see the fixture's comments):
    # policy: CI1 dscr+ltv, CI2 leverage, CI3 dscr+ltv+leverage, CI4 dscr+ltv+leverage.
    # documentation: CI1 bbc; CI3 fs+covenant+appraisal; CI4 bbc+credit approval.
    # compliance: CI4 flood. rating: CI2 and CI4 cross-bucket downgrades.
    assert _agg_value(rc, fnd, "policy") == 9
    assert _agg_value(rc, fnd, "documentation") == 6
    assert _agg_value(rc, fnd, "compliance") == 1
    assert _agg_value(rc, fnd, "rating") == 2


def test_open_counts_by_severity_and_loan(demo_recalc):
    rc, _, fnd = demo_recalc
    assert _agg_value(rc, fnd, "high") == 10   # 3 dscr + 3 leverage + 2 rating + flood + CA
    assert _agg_value(rc, fnd, "medium") == 7  # 3 ltv + 2 bbc + fs + appraisal
    assert _agg_value(rc, fnd, "low") == 1     # covenant cert
    assert _agg_value(rc, fnd, "CI-0001") == 3
    assert _agg_value(rc, fnd, "CI-0002") == 2
    assert _agg_value(rc, fnd, "CI-0003") == 6
    assert _agg_value(rc, fnd, "CI-0004") == 7
    assert _agg_value(rc, fnd, "TOTAL open") == 18


def test_waived_status_drops_from_open_counts():
    wb, *_ = build_demo_workbook()
    ws = wb[LS]
    rows = _rows(ws)
    ws.cell(rows["LTV above policy ceiling"], 5, "waived")
    rc = Recalc(workbook_bytes(wb))
    fnd = _fnd_rows(wb["Findings"])
    assert _agg_value(rc, fnd, "policy") == 8
    assert _agg_value(rc, fnd, "waived") == 1
    assert _agg_value(rc, fnd, "TOTAL open") == 17


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
def test_exception_rows_validate_class_and_when(tmp_path):
    import yaml
    base = yaml.safe_load((PROGRAMS_DIR / "c_and_i.yaml").read_text(encoding="utf-8"))
    base["sections"][0]["rows"].append(
        {"id": "bad", "kind": "exception", "class": "vibes", "severity": "high",
         "when": "1>0", "label": "bad"})
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    with pytest.raises(ConfigError, match="exception class"):
        load_program(p)
