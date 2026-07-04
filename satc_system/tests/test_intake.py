"""End-to-end Intake: read real generated PDFs through the app's reader pipeline."""

from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")
pytest.importorskip("flask")

from satc.app.state import AppState  # noqa: E402
from satc.fixtures import create_sample_folder  # noqa: E402


def test_intake_reads_real_fillable_pdfs(tmp_path):
    folder = create_sample_folder(tmp_path / "Clients" / "Maplewood" / "2024")
    summary = AppState().run_intake(str(folder))

    # The W-2 and 1099-INT are read; the engagement letter is filed, not extracted.
    assert summary["files_read"] == 2
    assert any("Engagement" in n for n in summary["notes"])


def test_intake_extracts_real_values_and_masks_tins(tmp_path):
    folder = create_sample_folder(tmp_path / "docs")
    state = AppState()
    state.run_intake(str(folder))
    by_path = {f.field_path: f for f in state.gate.all_fields()}

    # Real values pulled from the actual PDF form fields.
    assert by_path["w2.box1_wages"].effective_text() == "98000.00"
    assert by_path["int.box1_interest"].effective_text() == "1200.00"
    # The PDF held the full SSN/EIN; staging shows only masked last-4.
    assert by_path["w2.employee_ssn"].effective_text() == "***-**-1234"
    assert by_path["w2.employer_ein"].effective_text() == "**-***9999"
    assert "400551234" not in by_path["w2.employee_ssn"].effective_text()
