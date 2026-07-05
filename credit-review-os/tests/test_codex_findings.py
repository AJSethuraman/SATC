"""Regressions for the two Codex review findings on PR #71.

P1-1: `credit-review ingest` must not leave decrypted borrower data readable
on disk — plaintext is confined to a 0700 private directory that is removed.

P1-2: YAML native scalars in loan values (``rating_originator: 4`` as int,
``flood_zone_collateral: yes`` as bool) must still drive the text-comparing
formulas — the builder normalizes by row kind instead of silently blanking a
VLOOKUP or never firing a ``="yes"`` check.
"""

import os
import stat

import pytest
import yaml

from credit_review import build_engagement_workbook, workbook_bytes
from credit_review.cli import main
from credit_review.config import Loan, load_engagement, load_program
from credit_review.linesheet import OPEN_FLAG
from credit_review.workbook import ENGAGEMENTS_DIR, PROGRAMS_DIR

from recalc import Recalc


def test_yaml_native_scalars_still_drive_text_formulas():
    program = load_program(PROGRAMS_DIR / "c_and_i.yaml")
    engagement = load_engagement(ENGAGEMENTS_DIR / "demo_engagement.yaml")
    # As a user would write them unquoted: ints and YAML booleans.
    loan = Loan(loan_id="Y-0001", values={
        "borrower_name": "Blue Heron Fabrication LLC",
        "loan_number": "40017-3",
        "tin_last4": "6789",
        "total_commitment": 1000000,
        "outstanding": 900000,
        "rating_originator": 4,                # int, not "4"
        "rating_reviewer": 7,                  # int -> Substandard
        "flood_zone_collateral": True,         # YAML `yes` -> bool
        "flood_insurance_current": False,      # YAML `no` -> bool
        "cash_flow": 500000, "debt_service": 300000,
        "collateral_value": 2000000, "total_debt": 100000, "ebitda": 500000,
    })
    wb = build_engagement_workbook(program, engagement, [loan])
    ws = wb["LS_Y-0001"]
    rows = {ws.cell(r, 2).value: r for r in range(1, ws.max_row + 1)
            if ws.cell(r, 2).value}
    # normalized to text in the cells
    assert ws.cell(rows["Originator risk rating"], 3).value == "4"
    assert ws.cell(rows["Improved real estate collateral in a flood zone? (yes/no)"],
                   3).value == "yes"
    rc = Recalc(workbook_bytes(wb))
    # the rating map resolves (int grade would have blanked the VLOOKUP)...
    assert rc.value("Master", "H4") == "Substandard"
    # ...the cross-bucket disagreement fires...
    r = rows["Rating disagreement (independent validation)"]
    assert rc.value("LS_Y-0001", f"C{r}") == OPEN_FLAG
    # ...and the flood compliance check fires (bool would never equal "yes").
    r = rows["Flood insurance missing for flood-zone collateral"]
    assert rc.value("LS_Y-0001", f"C{r}") == OPEN_FLAG


def test_ingest_confines_decrypted_plaintext_to_private_dir(tmp_path, capsys,
                                                            monkeypatch):
    out = tmp_path / "demo.xlsx.enc"
    report = tmp_path / "findings.json"
    assert main(["--key-dir", str(tmp_path), "build",
                 str(ENGAGEMENTS_DIR / "demo_engagement.yaml"),
                 "-o", str(out)]) == 0

    seen = {}
    import credit_review.cli as cli_module
    real_ingest = cli_module.ingest_workbook

    def spying_ingest(path):
        st = os.stat(path)
        seen["file_mode"] = stat.S_IMODE(st.st_mode)
        seen["dir_mode"] = stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode)
        seen["path"] = str(path)
        return real_ingest(path)

    monkeypatch.setattr(cli_module, "ingest_workbook", spying_ingest)
    assert main(["--key-dir", str(tmp_path), "ingest", str(out),
                 "--json", str(report)]) == 0
    assert seen["file_mode"] == 0o600      # plaintext unreadable to others
    assert seen["dir_mode"] == 0o700
    assert not os.path.exists(seen["path"])            # nothing lingers
    assert not os.path.exists(os.path.dirname(seen["path"]))
