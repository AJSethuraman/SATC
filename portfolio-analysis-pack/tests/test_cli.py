"""Seam 2: the command line on files. Refusals name the line to add."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from analysis_pack.cli import main


def _run(argv, capsys):
    rc = main(argv)
    out = capsys.readouterr()
    status = json.loads(out.out) if out.out.strip() else None
    return rc, status, out.err


def _copy_book(effect_book: Path, tmp_path: Path) -> Path:
    d = tmp_path / "book"
    shutil.copytree(effect_book, d)
    return d


def _edit_config(d: Path, mutate) -> Path:
    raw = yaml.safe_load((d / "config.yaml").read_text())
    mutate(raw)
    p = d / "edited.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False))
    return p


def test_validate_passes_the_synthetic_book(effect_book, capsys):
    rc, status, err = _run(["validate", str(effect_book / "config.yaml"), "--data", str(effect_book / "loans.csv"),
                            "--asof", "2026-06-30"], capsys)
    assert rc == 0 and status["ok"] and status["buildable"]
    assert "seasoned" in err


def test_a_missing_existing_control_line_is_refused_with_the_line_to_add(effect_book, tmp_path, capsys):
    d = _copy_book(effect_book, tmp_path)
    p = _edit_config(d, lambda raw: raw.pop("existing_control"))
    rc, status, err = _run(["validate", str(p), "--data", str(d / "loans.csv")], capsys)
    assert rc == 2 and status["refused"] == "config"
    assert "existing_control: none   # or the control that reacts today" in err


def test_a_missing_flag_line_is_refused(effect_book, tmp_path, capsys):
    d = _copy_book(effect_book, tmp_path)
    p = _edit_config(d, lambda raw: raw["rule"].pop("fires_when"))
    rc, status, err = _run(["validate", str(p), "--data", str(d / "loans.csv")], capsys)
    assert rc == 2 and "fires_when: {op: '>', value: 1.0}" in err


def test_a_later_column_used_as_a_control_is_refused_naming_the_column(effect_book, tmp_path, capsys):
    d = _copy_book(effect_book, tmp_path)
    def mutate(raw):
        raw["controls"].append({"name": "leak", "field": "outcome_date"})
    p = _edit_config(d, mutate)
    rc, status, err = _run(["validate", str(p), "--data", str(d / "loans.csv")], capsys)
    assert rc == 2
    assert "column `outcome_date` is declared `known: later`" in err


def test_an_undeclared_column_is_refused_with_the_fields_line(effect_book, tmp_path, capsys):
    d = _copy_book(effect_book, tmp_path)
    p = _edit_config(d, lambda raw: raw["fields"].pop("amount"))
    rc, status, err = _run(["validate", str(p), "--data", str(d / "loans.csv")], capsys)
    assert rc == 2 and "amount: {known: at_origination}" in err


def test_a_column_the_data_does_not_carry_is_refused(effect_book, tmp_path, capsys):
    d = _copy_book(effect_book, tmp_path)
    def mutate(raw):
        raw["fields"]["ghost"] = {"known": "at_origination"}
        raw["controls"].append({"name": "ghost", "field": "ghost"})
    p = _edit_config(d, mutate)
    rc, status, err = _run(["validate", str(p), "--data", str(d / "loans.csv")], capsys)
    assert rc == 2 and status["refused"] == "columns" and "ghost" in err


def test_an_unbuilt_door_is_valid_but_refused_by_build(effect_book, tmp_path, capsys):
    d = _copy_book(effect_book, tmp_path)
    p = _edit_config(d, lambda raw: raw.update({"rule_type": "threshold"}))
    rc, status, _ = _run(["validate", str(p), "--data", str(d / "loans.csv")], capsys)
    assert rc == 0 and status["buildable"] is False
    rc, status, err = _run(["build", str(p), "--data", str(d / "loans.csv"), "--asof", "2026-06-30",
                            "-o", str(d / "x.xlsx")], capsys)
    assert rc == 2 and status["refused"] == "rule_type" and "not built in this version" in err
    assert not (d / "x.xlsx").exists()


def test_build_writes_the_pack_and_reports_the_check_as_not_run_here(effect_book, tmp_path, capsys):
    out = tmp_path / "pack.xlsx"
    rc, status, err = _run(["build", str(effect_book / "config.yaml"), "--data", str(effect_book / "loans.csv"),
                            "--asof", "2026-06-30", "-o", str(out)], capsys)
    assert rc == 0 and out.exists()
    assert status["formula_check"] == "not run here"
    assert "not run here (no engine); Excel verifies on open" in err
    assert status["gradient"] == "monotonic increasing"


def test_dirt_refuses_the_build_and_writes_the_offending_rows(effect_book, tmp_path, capsys):
    d = _copy_book(effect_book, tmp_path)
    csv_path = d / "loans.csv"
    lines = csv_path.read_text().splitlines()
    header = lines[0].split(",")
    i_b = header.index("field_b")
    i_id = header.index("loan_id")
    dirty = lines[1].split(","); dirty[i_b] = "0"
    dup = lines[2].split(",")
    dup2 = list(dup)
    lines_out = [lines[0], ",".join(dirty)] + lines[2:] + [",".join(dup2)]
    csv_path.write_text("\n".join(lines_out) + "\n")
    rc, status, err = _run(["build", str(d / "config.yaml"), "--data", str(csv_path), "--asof", "2026-06-30",
                            "-o", str(d / "x.xlsx")], capsys)
    assert rc == 2 and status["refused"] == "hygiene"
    assert status["counts"] == {"zero or negative in a rule field": 1, "duplicate loan id": 1}
    report = Path(status["file"]).read_text().splitlines()
    assert report[0] == "loan_id,column,value,reason" and len(report) == 3
    assert not (d / "x.xlsx").exists()
