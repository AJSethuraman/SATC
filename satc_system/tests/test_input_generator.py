"""Integration test: the Drake input generator produces a workbook that the
existing drake-entry-assistant (DEA) loads and validates without errors.

This proves the coordination seam — SATC emits intake in DEA's exact
``Clients`` / ``W2s`` shape, so DEA drives the Drake keying.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from satc.drake.input_generator import generate_drake_intake_workbook
from satc.fixtures import synthetic_drake_intake

# Make the sibling drake-entry-assistant package importable.
_DEA_SRC = Path(__file__).resolve().parents[2] / "drake-entry-assistant" / "src"
if _DEA_SRC.exists():
    sys.path.insert(0, str(_DEA_SRC))

dea_available = _DEA_SRC.exists()


def test_generated_intake_has_dea_shape(tmp_path):
    out = generate_drake_intake_workbook(tmp_path / "intake.xlsx", synthetic_drake_intake())
    from openpyxl import load_workbook
    wb = load_workbook(out)
    assert wb.sheetnames == ["Clients", "W2s"]
    assert wb["Clients"].max_row == 2          # header + 1 client
    assert wb["W2s"].max_row == 3              # header + 2 W-2s


@pytest.mark.skipif(not dea_available, reason="drake-entry-assistant not present")
def test_dea_loads_and_validates_generated_intake(tmp_path):
    out = generate_drake_intake_workbook(tmp_path / "intake.xlsx", synthetic_drake_intake())

    from dea.excel_loader import load_workbook_data
    from dea.validation import validate_client_batch

    loaded = load_workbook_data(out)
    batch = loaded.client_batch
    assert len(batch.clients) == 1
    client = batch.clients[0]
    assert client.client_id == "SATC-001000"
    assert len(client.w2s) == 2
    assert sum(w.box_1_wages for w in client.w2s) == 145000

    # DEA's own validation must find no ERROR-level problems with our intake.
    issues = validate_client_batch(batch, loaded.source_cells)
    errors = [i for i in issues if i.severity == "ERROR"]
    assert errors == [], f"DEA reported errors on generated intake: {errors}"
