"""Slice 4 (issue #63): Master roll-up + criticized/classified asset quality.

Every Master cell is a formula referencing the loan's linesheet (or the
``_config`` lookup blocks); the asset-quality summary on Findings computes the
criticized (SM+SS+D+L) and classified (SS+D+L) boundaries by formula from the
roll-up. Recalc-verified against hand-tallied expected values for the 4-loan
synthetic fixture (Seam 1).
"""

import pytest

from credit_review import build_demo_workbook, workbook_bytes

from recalc import Recalc

# Fixture geometry: register starts under the banner + header (row 4).
LOAN_ROWS = {"CI-0001": 4, "CI-0002": 5, "CI-0003": 6, "CI-0004": 7}


@pytest.fixture(scope="module")
def built():
    wb, *rest = build_demo_workbook()
    return wb, Recalc(workbook_bytes(wb))


def test_master_rows_are_formulas_not_recomputation(built):
    wb, _ = built
    ws = wb["Master"]
    for loan_id, r in LOAN_ROWS.items():
        assert ws.cell(r, 1).value == loan_id
        # borrower, loan #, exposure, ratings, bucket, flags, open-exception
        # count: every one a live formula, never a copied value
        for col in range(2, 12):
            v = ws.cell(r, col).value
            assert isinstance(v, str) and v.startswith("="), (loan_id, col, v)


def test_master_buckets_and_flags(built):
    _, rc = built
    expected = {
        "CI-0001": ("Pass", False, False),            # reviewer blank -> originator's 4
        "CI-0002": ("Special Mention", True, False),  # criticized, not classified
        "CI-0003": ("Substandard", True, True),
        "CI-0004": ("Doubtful", True, True),          # reviewer 8 governs over originator 7
    }
    for loan_id, (bucket, crit, classified) in expected.items():
        r = LOAN_ROWS[loan_id]
        assert rc.value("Master", f"H{r}") == bucket, loan_id
        assert bool(rc.value("Master", f"I{r}")) is crit, loan_id
        assert bool(rc.value("Master", f"J{r}")) is classified, loan_id


def test_master_exposure_and_open_exceptions(built):
    _, rc = built
    expected = {
        "CI-0001": (2500000, 1750000, 3),
        "CI-0002": (1200000, 900000, 2),
        "CI-0003": (3000000, 2600000, 6),
        "CI-0004": (800000, 800000, 7),
    }
    for loan_id, (committed, outstanding, open_exc) in expected.items():
        r = LOAN_ROWS[loan_id]
        assert rc.value("Master", f"D{r}") == committed
        assert rc.value("Master", f"E{r}") == outstanding
        assert rc.value("Master", f"K{r}") == open_exc


def test_asset_quality_summary(built):
    wb, rc = built
    fnd = wb["Findings"]
    labels = {fnd.cell(r, 1).value: r for r in range(1, fnd.max_row + 1)
              if fnd.cell(r, 1).value}
    # Criticized includes Special Mention; classified does not.
    assert rc.value("Findings", f"B{labels['Criticized $ (outstanding)']}") == 4300000
    assert rc.value("Findings", f"B{labels['Criticized count']}") == 3
    assert rc.value("Findings", f"B{labels['Classified $ (outstanding)']}") == 3400000
    assert rc.value("Findings", f"B{labels['Classified count']}") == 2


def test_reviewer_downgrade_moves_the_rollup():
    # Key a reviewer downgrade on the Pass loan; its bucket, flags, and the
    # portfolio totals all move -- proving the roll-up is live, not copied.
    wb, *_ = build_demo_workbook()
    ls = wb["LS_CI-0001"]
    rows = {ls.cell(r, 2).value: r for r in range(1, ls.max_row + 1) if ls.cell(r, 2).value}
    ls.cell(rows["Reviewer risk rating (independent)"], 3, "7")
    rc = Recalc(workbook_bytes(wb))
    assert rc.value("Master", "H4") == "Substandard"
    assert bool(rc.value("Master", "J4")) is True
    fnd = wb["Findings"]
    labels = {fnd.cell(r, 1).value: r for r in range(1, fnd.max_row + 1)
              if fnd.cell(r, 1).value}
    assert rc.value("Findings", f"B{labels['Classified $ (outstanding)']}") \
        == 3400000 + 1750000
