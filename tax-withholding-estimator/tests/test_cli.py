"""CLI smoke tests."""

from __future__ import annotations

import json

from twe.cli import main


def test_years_command(capsys):
    assert main(["years"]) == 0
    out = capsys.readouterr().out
    assert "2025" in out


def test_estimate_with_flags(capsys):
    code = main([
        "estimate",
        "--filing-status", "single",
        "--pay-frequency", "biweekly",
        "--gross", "3000",
        "--withheld", "350",
        "--periods-remaining", "26",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "TAX WITHHOLDING ESTIMATE" in out
    assert "TOTAL TAX LIABILITY" in out


def test_estimate_json_output(capsys):
    code = main([
        "estimate", "--json",
        "--filing-status", "single",
        "--pay-frequency", "biweekly",
        "--gross", "3000",
        "--withheld", "350",
        "--periods-remaining", "26",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tax_year_used"] == 2025
    assert payload["breakdown"]["total_tax_liability"] == "8774.00"


def test_estimate_from_input_file(tmp_path, capsys):
    scenario = {
        "filing_status": "single",
        "paystub": {
            "pay_frequency": "biweekly",
            "gross_pay_per_period": 3000,
            "federal_tax_withheld_per_period": 350,
            "pay_periods_remaining": 26,
        },
        "tax_year": 2025,
    }
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario), encoding="utf-8")

    code = main(["estimate", "--json", "--input", str(path)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["breakdown"]["total_tax_liability"] == "8774.00"


def test_sample_then_estimate_roundtrip(tmp_path, capsys):
    sample_path = tmp_path / "sample.json"
    assert main(["sample", "--output", str(sample_path)]) == 0
    capsys.readouterr()

    assert main(["estimate", "--input", str(sample_path)]) == 0
    out = capsys.readouterr().out
    assert "RECOMMENDATION" in out or "OVER-WITHHOLD" in out


def test_estimate_missing_required_flag():
    # No filing status and no input file -> failure exit code.
    assert main(["estimate", "--pay-frequency", "weekly", "--gross", "1000"]) == 1


def test_estimate_missing_input_file():
    assert main(["estimate", "--input", "/nonexistent/file.json"]) == 1
