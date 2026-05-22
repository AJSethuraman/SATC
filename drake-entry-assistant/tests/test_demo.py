from __future__ import annotations

from pathlib import Path

from dea.demo import create_sample_workbook
from dea.excel_loader import load_workbook_data
from dea.validation import validate_client_batch


def test_create_sample_workbook_writes_file(tmp_path) -> None:
    out = tmp_path / "sample_intake.xlsx"
    written = create_sample_workbook(out)
    assert written == out
    assert out.exists()


def test_generated_sample_workbook_loads_and_validates(tmp_path) -> None:
    out = tmp_path / "sample_intake.xlsx"
    create_sample_workbook(out)

    loaded = load_workbook_data(out)
    issues = validate_client_batch(loaded.client_batch, loaded.source_cells)
    assert not [issue for issue in issues if issue.severity == "ERROR"]


def test_demo_module_source_has_no_contiguous_literal_identifiers() -> None:
    source = Path("src/dea/demo.py").read_text(encoding="utf-8")
    full_ssn = "".join(["123", "45", "6789"])
    full_ssn_fmt = "-".join(["123", "45", "6789"])
    full_ein_fmt = "-".join(["12", "3456789"])
    assert full_ssn not in source
    assert full_ssn_fmt not in source
    assert full_ein_fmt not in source
