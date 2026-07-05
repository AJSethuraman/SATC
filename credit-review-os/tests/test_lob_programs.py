"""LOB build-out (BACKLOG §5, cash-flow-out order): owner-occupied CRE,
construction/ADC, and agricultural programs — each pure config + crosswalk on
the unchanged engine. One parametrized harness: build the LOB's synthetic
demo, verify the crosswalk is fully cited, and recalc-verify that the clean
credit stays clean and the stressed credit trips exactly its expected
findings.
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

# (program, engagement, lob-specific crosswalk element,
#  clean sheet, stressed sheet, stressed bucket,
#  exception labels expected OPEN on the stressed loan and CLEAR on the clean)
CASES = [
    pytest.param(
        "owner_occ_cre.yaml", "demo_oocre_engagement.yaml", "owner_occupied_repayment",
        "LS_OOC-0001", "LS_OOC-0002", "Substandard",
        ["Rating disagreement (independent validation)",
         "DSCR below policy floor",
         "LTV above policy ceiling (approved with mitigant)",
         "Flood insurance missing for flood-zone collateral",
         "Occupant business financial statements stale or missing",
         "Covenant compliance certificate stale or missing",
         "Collateral appraisal no longer valid"],
        id="owner_occ_cre"),
    pytest.param(
        "construction_adc.yaml", "demo_adc_engagement.yaml", "adc_cost_to_complete",
        "LS_ADC-0001", "LS_ADC-0002", "Substandard",
        ["Rating disagreement (independent validation)",
         "Loan-to-cost above policy ceiling",
         "Interest reserve depleted (or not evidenced)",
         "As-completed LTV above policy ceiling (approved with mitigant)",
         "Project budget / cost review missing from file",
         "Draw inspection report stale or missing",
         "As-completed appraisal no longer valid"],
        id="construction_adc"),
    pytest.param(
        "agricultural.yaml", "demo_ag_engagement.yaml", "agricultural_repayment",
        "LS_AG-0001", "LS_AG-0002", "Substandard",
        ["Rating disagreement (independent validation)",
         "DSCR below policy floor",
         "Operating carryover debt outstanding",
         "LTV above policy ceiling (approved with mitigant)",
         "Required crop/livestock insurance not in force",
         "Financial statements / tax returns stale or missing",
         "Chattel / equipment inspection stale or missing"],
        id="agricultural"),
]


@pytest.fixture(scope="module")
def built_lobs():
    cache = {}
    for case in CASES:
        program_file, engagement_file = case.values[0], case.values[1]
        program = load_program(PROGRAMS_DIR / program_file)
        engagement = load_engagement(ENGAGEMENTS_DIR / engagement_file)
        loans = load_loans(engagement.loans_path)
        wb = build_engagement_workbook(program, engagement, loans)
        cache[program_file] = (wb, Recalc(workbook_bytes(wb)), program)
    return cache


def _rows(ws):
    return {ws.cell(r, 2).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value}


@pytest.mark.parametrize(
    "program_file,engagement_file,lob_element,clean_ls,stressed_ls,stressed_bucket,labels",
    CASES)
def test_lob_crosswalk_fully_cited(built_lobs, program_file, engagement_file,
                                   lob_element, clean_ls, stressed_ls,
                                   stressed_bucket, labels):
    _, _, program = built_lobs[program_file]
    elements = {e["element"] for e in program.crosswalk}
    assert REQUIRED_ELEMENTS <= elements
    assert lob_element in elements
    for entry in program.crosswalk:
        assert entry["requirement"].strip() and entry["source"].strip(), entry["element"]


@pytest.mark.parametrize(
    "program_file,engagement_file,lob_element,clean_ls,stressed_ls,stressed_bucket,labels",
    CASES)
def test_lob_clean_credit_stays_clean(built_lobs, program_file, engagement_file,
                                      lob_element, clean_ls, stressed_ls,
                                      stressed_bucket, labels):
    wb, rc, _ = built_lobs[program_file]
    rows = _rows(wb[clean_ls])
    for label in labels:
        if label.startswith("Rating disagreement"):
            continue   # clean fixtures leave the reviewer rating blank -> flag blank
        assert rc.value(clean_ls, f"C{rows[label]}") == CLEAR_FLAG, (clean_ls, label)
    assert rc.value("Master", "H4") == "Pass"          # clean loan, originator grade
    assert bool(rc.value("Master", "I4")) is False


@pytest.mark.parametrize(
    "program_file,engagement_file,lob_element,clean_ls,stressed_ls,stressed_bucket,labels",
    CASES)
def test_lob_stressed_credit_trips_expected_findings(built_lobs, program_file,
                                                     engagement_file, lob_element,
                                                     clean_ls, stressed_ls,
                                                     stressed_bucket, labels):
    wb, rc, _ = built_lobs[program_file]
    rows = _rows(wb[stressed_ls])
    for label in labels:
        assert rc.value(stressed_ls, f"C{rows[label]}") == OPEN_FLAG, (stressed_ls, label)
    assert rc.value("Master", "H5") == stressed_bucket
    assert bool(rc.value("Master", "J5")) is True      # classified
