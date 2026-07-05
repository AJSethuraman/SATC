"""Roadmap follow-ups: portability proofs.

1. **Second demo bank** (PRD success metric): a new client bank is a thin
   overlay — different internal scale (1-10) and tighter thresholds — on the
   unchanged C&I program. Zero code changes: these tests only load configs
   and build.
2. **First LOB extension**: the income-producing CRE program is config +
   crosswalk on the unchanged engine — NOI-based DSCR, occupancy, appraised-
   value LTV, rent-roll staleness.
"""

import pytest

from credit_review import (
    build_engagement_workbook,
    load_engagement,
    load_loans,
    load_program,
    workbook_bytes,
)
from credit_review.linesheet import CLEAR_FLAG, OPEN_FLAG
from credit_review.workbook import ENGAGEMENTS_DIR, PROGRAMS_DIR

from recalc import Recalc
from test_methodology import REQUIRED_ELEMENTS


def _build(program_name, engagement_name):
    program = load_program(PROGRAMS_DIR / program_name)
    engagement = load_engagement(ENGAGEMENTS_DIR / engagement_name)
    loans = load_loans(engagement.loans_path)
    return build_engagement_workbook(program, engagement, loans), program, engagement, loans


def _rows(ws):
    return {ws.cell(r, 2).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value}


# ---------------------------------------------------------------------------
# Second demo bank: same program, thin overlay, different scale + thresholds
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def bank2():
    wb, *rest = _build("c_and_i.yaml", "demo_bank2_engagement.yaml")
    return wb, Recalc(workbook_bytes(wb))


def test_bank2_builds_from_overlay_alone(bank2):
    wb, _ = bank2
    assert wb.sheetnames == ["Cover", "LS_SSB-0001", "LS_SSB-0002", "Master",
                             "Data Mart", "Findings", "_methodology", "_config",
                             "_readme", "_map"]


def test_bank2_ten_grade_scale_maps_buckets(bank2):
    _, rc = bank2
    # grade 7 = Special Mention on this bank's 1-10 scale (it was Substandard
    # on Demo Community Bank's 1-9 scale) — the map is pure overlay config
    assert rc.value("Master", "H4") == "Special Mention"   # SSB-0001, reviewer 7
    assert rc.value("Master", "H5") == "Substandard"       # SSB-0002, 8
    assert bool(rc.value("Master", "I4")) is True          # criticized
    assert bool(rc.value("Master", "J4")) is False         # not classified


def test_bank2_rating_finding_fires_on_its_own_scale(bank2):
    wb, rc = bank2
    rows = _rows(wb["LS_SSB-0001"])
    r = rows["Rating disagreement"]
    assert rc.value("LS_SSB-0001", f"C{r}") == OPEN_FLAG   # 6 (Pass) vs 7 (SM)


def test_bank2_tighter_thresholds_flip_outcomes(bank2):
    wb, rc = bank2
    ls1 = _rows(wb["LS_SSB-0001"])
    # DSCR 1.22 breaches this bank's 1.25 floor (would pass 1.20)
    assert rc.value("LS_SSB-0001", f"C{ls1['DSCR']}") == pytest.approx(1.22)
    assert rc.value("LS_SSB-0001", f"C{ls1['DSCR below policy floor']}") == OPEN_FLAG
    # LTV 77.8% breaches the 75% ceiling (would pass 80%)
    r = ls1["LTV above policy ceiling"]
    assert rc.value("LS_SSB-0001", f"C{r}") == OPEN_FLAG
    # BBC 41 days old breaches the 30-day window (would pass 45)
    assert rc.value("LS_SSB-0001",
                    f"C{ls1['Borrowing-base certificate stale or missing']}") == OPEN_FLAG
    ls2 = _rows(wb["LS_SSB-0002"])
    # leverage 3.95x breaches the 3.5x ceiling (would pass 4.0x)
    assert rc.value("LS_SSB-0002", f"C{ls2['Leverage above policy ceiling']}") == OPEN_FLAG


def test_bank2_asset_quality(bank2):
    wb, rc = bank2
    fnd = wb["Findings"]
    labels = {fnd.cell(r, 1).value: r for r in range(1, fnd.max_row + 1)
              if fnd.cell(r, 1).value}
    assert rc.value("Findings", f"B{labels['Criticized $ (outstanding)']}") == 1900000
    assert rc.value("Findings", f"B{labels['Classified $ (outstanding)']}") == 1200000


# ---------------------------------------------------------------------------
# First LOB extension: income-producing CRE (config + crosswalk only)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cre():
    wb, program, engagement, loans = _build("cre_income_producing.yaml",
                                            "demo_cre_engagement.yaml")
    return wb, Recalc(workbook_bytes(wb)), program


def test_cre_program_builds_on_the_same_engine(cre):
    wb, _, program = cre
    assert program.lob == "cre_income_producing"
    assert program.review_mode == "loan_level"
    assert "LS_CRE-0001" in wb.sheetnames and "LS_CRE-0002" in wb.sheetnames


def test_cre_crosswalk_covers_required_elements_plus_collateral(cre):
    _, _, program = cre
    elements = {e["element"] for e in program.crosswalk}
    assert REQUIRED_ELEMENTS <= elements
    assert "collateral_valuation" in elements


def test_cre_stabilized_credit_is_clean(cre):
    wb, rc, _ = cre
    rows = _rows(wb["LS_CRE-0001"])
    assert rc.value("LS_CRE-0001", f"C{rows['DSCR']}") \
        == pytest.approx(520000 / 390000)
    for label in ("DSCR below policy floor", "Occupancy below policy floor",
                  "LTV above policy ceiling",
                  "Rent roll stale or missing", "Collateral appraisal no longer valid"):
        assert rc.value("LS_CRE-0001", f"C{rows[label]}") == CLEAR_FLAG, label


def test_cre_stressed_office_credit_trips_the_program(cre):
    wb, rc, _ = cre
    rows = _rows(wb["LS_CRE-0002"])
    expected_open = ("Rating disagreement",
                     "DSCR below policy floor",
                     "Occupancy below policy floor",
                     "LTV above policy ceiling",
                     "Rent roll stale or missing",
                     "Collateral appraisal no longer valid")
    for label in expected_open:
        assert rc.value("LS_CRE-0002", f"C{rows[label]}") == OPEN_FLAG, label
    # Substandard via the reviewer's downgrade; classified in the roll-up
    assert rc.value("Master", "H5") == "Substandard"
    assert bool(rc.value("Master", "J5")) is True
