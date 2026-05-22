from __future__ import annotations

import json

from openpyxl import load_workbook

from dea.cli import main
from dea.demo import create_sample_workbook


def _id_from_parts(*parts: str) -> str:
    return "".join(parts)


def _make_valid_workbook(tmp_path):
    workbook_path = tmp_path / "sample.xlsx"
    create_sample_workbook(workbook_path)
    return workbook_path


def _make_invalid_workbook(tmp_path):
    workbook_path = _make_valid_workbook(tmp_path)
    wb = load_workbook(workbook_path)
    clients = wb["Clients"]
    clients["F2"] = "12"
    wb.save(workbook_path)
    return workbook_path


def test_validate_exits_0_for_valid_and_writes_report(tmp_path, capsys) -> None:
    workbook = _make_valid_workbook(tmp_path)
    out_dir = tmp_path / "out"
    code = main([
        "validate",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--output-dir",
        str(out_dir),
    ])
    captured = capsys.readouterr()

    assert code == 0
    assert (out_dir / "validation_report.xlsx").exists()
    assert "errors=0" in captured.out


def test_validate_exits_1_for_invalid_and_writes_report(tmp_path, capsys) -> None:
    workbook = _make_invalid_workbook(tmp_path)
    out_dir = tmp_path / "out"
    code = main([
        "validate",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--output-dir",
        str(out_dir),
    ])
    captured = capsys.readouterr()

    assert code == 1
    assert (out_dir / "validation_report.xlsx").exists()
    assert "errors=" in captured.out


def test_dry_run_writes_masked_action_plan_and_planned_log(tmp_path, capsys) -> None:
    workbook = _make_valid_workbook(tmp_path)
    out_dir = tmp_path / "out"
    raw_ssn = _id_from_parts("123", "45", "6789")
    raw_ein = _id_from_parts("12", "345", "6789")

    code = main([
        "dry-run",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--config-dir",
        "configs/drake/2025",
        "--output-dir",
        str(out_dir),
    ])
    captured = capsys.readouterr()

    assert code == 0
    action_plan_path = out_dir / "action_plan.json"
    assert action_plan_path.exists()
    assert (out_dir / "planned_entry_log.csv").exists()
    assert (out_dir / "planned_entry_log.xlsx").exists()

    payload = action_plan_path.read_text(encoding="utf-8")
    assert raw_ssn not in payload
    assert raw_ein not in payload
    assert "***-**-6789" in payload
    assert "**-***6789" in payload
    assert raw_ssn not in captured.out
    assert raw_ein not in captured.out

    data = json.loads(payload)
    assert "plans" in data


def test_dry_run_stops_on_validation_error(tmp_path) -> None:
    workbook = _make_invalid_workbook(tmp_path)
    out_dir = tmp_path / "out"

    code = main([
        "dry-run",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--config-dir",
        "configs/drake/2025",
        "--output-dir",
        str(out_dir),
    ])

    assert code == 1
    assert (out_dir / "validation_report.xlsx").exists()
    assert not (out_dir / "action_plan.json").exists()


def test_run_fake_writes_entry_logs_and_succeeds(tmp_path) -> None:
    workbook = _make_valid_workbook(tmp_path)
    out_dir = tmp_path / "out"

    code = main([
        "run-fake",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--config-dir",
        "configs/drake/2025",
        "--output-dir",
        str(out_dir),
    ])

    assert code == 0
    assert (out_dir / "validation_report.xlsx").exists()
    assert (out_dir / "entry_log.csv").exists()
    assert (out_dir / "entry_log.xlsx").exists()


def test_run_fake_stops_on_validation_error(tmp_path) -> None:
    workbook = _make_invalid_workbook(tmp_path)
    out_dir = tmp_path / "out"

    code = main([
        "run-fake",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--config-dir",
        "configs/drake/2025",
        "--output-dir",
        str(out_dir),
    ])

    assert code == 1
    assert (out_dir / "validation_report.xlsx").exists()


def test_run_live_without_flag_refuses_execution(tmp_path, capsys) -> None:
    workbook = _make_valid_workbook(tmp_path)
    out_dir = tmp_path / "out"

    code = main([
        "run-live",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--config-dir",
        "configs/drake/2025",
        "--output-dir",
        str(out_dir),
    ])
    captured = capsys.readouterr()

    assert code == 1
    assert "blocked" in captured.out


def test_run_live_with_flag_still_refuses_not_implemented(tmp_path, capsys) -> None:
    workbook = _make_valid_workbook(tmp_path)
    out_dir = tmp_path / "out"

    code = main([
        "run-live",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--config-dir",
        "configs/drake/2025",
        "--output-dir",
        str(out_dir),
        "--live-drake",
    ])
    captured = capsys.readouterr()

    assert code == 1
    assert "not implemented" in captured.out.lower()


def test_cli_output_does_not_contain_full_identifiers(tmp_path, capsys) -> None:
    workbook = _make_valid_workbook(tmp_path)
    out_dir = tmp_path / "out"
    raw_ssn = _id_from_parts("123", "45", "6789")
    raw_ein = _id_from_parts("12", "345", "6789")

    _ = main([
        "run-fake",
        "--input",
        str(workbook),
        "--tax-year",
        "2025",
        "--config-dir",
        "configs/drake/2025",
        "--output-dir",
        str(out_dir),
    ])
    captured = capsys.readouterr()

    assert raw_ssn not in captured.out
    assert raw_ein not in captured.out
