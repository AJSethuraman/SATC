#!/usr/bin/env python3
"""Sanity-check extracted form data before it is entered or filed.

Reads the per-form CSVs the extractor wrote to Drake_Export/ and flags likely
problems: rows the extractor already flagged for manual entry, a form with no
primary amount read, federal withholding that exceeds W-2 wages, and possible
duplicate forms. Findings go to Diagnostics/diagnostics.csv. This is assistive
review, not tax advice. Standard-library only.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import extract_form_data
import generate_documents
import sort_tax_docs

DIAGNOSTICS_FOLDER_NAME = "Diagnostics"
SUMMARY_FILENAME = "diagnostics.csv"
SEV_WARN, SEV_INFO = "warning", "info"


def _num(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _truthy(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


def check_rows(category: str, rows: list[dict]) -> list[dict]:
    """Apply checks to the rows of one form-type CSV; return finding dicts."""

    specs = extract_form_data.EXTRACTION_SPECS.get(category, ())
    primary_fields = [s.name for s in specs if getattr(s, "primary", False)]
    all_fields = [s.name for s in specs]
    findings: list[dict] = []
    fingerprints: Counter = Counter()

    def add(row: dict, issue: str, severity: str) -> None:
        findings.append({
            "form": category,
            "source_file": row.get("source_file", ""),
            "page": row.get("page", ""),
            "issue": issue,
            "severity": severity,
        })

    for row in rows:
        if _truthy(row.get("needs_review")):
            add(row, "Flagged during extraction; verify and enter manually.", SEV_INFO)

        # Blank (unread), not merely zero: a legitimate 0.00 should not be flagged.
        if primary_fields and all(str(row.get(f, "")).strip() == "" for f in primary_fields):
            add(row, "No primary amount was read for this form.", SEV_WARN)

        if category == "W2":
            wages = _num(row.get("box1_wages"))
            withholding = _num(row.get("box2_federal_withholding"))
            if wages is not None and withholding is not None and withholding > wages:
                add(row, f"Federal withholding ({withholding:,.2f}) exceeds wages ({wages:,.2f}).", SEV_WARN)

        # Match on every extracted field so two distinct people who merely share one
        # amount (e.g. identical wages) are not flagged; a true duplicate matches on all.
        key = tuple(str(row.get(f, "")) for f in (all_fields or ["source_file"]))
        fingerprints[key] += 1
        if fingerprints[key] == 2:
            add(row, "Possible duplicate (an identical form was seen more than once).", SEV_WARN)

    return findings


def run_diagnostics(input_folder, status_callback=None) -> dict:
    """Scan Drake_Export CSVs for likely data problems."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "diagnostics",
        "output_folder": output_folder,
        "diagnostics_folder": None,
        "report_path": None,
        "finding_count": 0,
        "warning_count": 0,
        "warnings": [],
    }

    drake_folder = output_folder / extract_form_data.DRAKE_EXPORT_FOLDER_NAME
    if not drake_folder.is_dir() or not any(drake_folder.glob("*.csv")):
        return {**base_result, "summary": "No extracted data found (run Extract Form Data first); nothing to check."}

    findings: list[dict] = []
    for csv_path in sorted(drake_folder.glob("*.csv")):
        if status_callback:
            status_callback(f"Checking {csv_path.name}")
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        findings.extend(check_rows(csv_path.stem, rows))

    diagnostics_folder = output_folder / DIAGNOSTICS_FOLDER_NAME
    diagnostics_folder.mkdir(exist_ok=True)
    report_path = diagnostics_folder / SUMMARY_FILENAME
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["form", "source_file", "page", "issue", "severity"])
        writer.writeheader()
        writer.writerows(findings)

    warning_count = sum(1 for f in findings if f["severity"] == SEV_WARN)
    return {
        **base_result,
        "diagnostics_folder": diagnostics_folder,
        "report_path": report_path,
        "finding_count": len(findings),
        "warning_count": warning_count,
        "summary": (
            f"Reviewed extracted data: {warning_count} warning(s), "
            f"{len(findings) - warning_count} note(s)."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sanity-check extracted form data.")
    parser.add_argument("input_folder", help="Folder containing Drake_Export output.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_diagnostics(folder, status_callback=print)
    print(result["summary"])
    if result["report_path"]:
        print(f"Diagnostics report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
