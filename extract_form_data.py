#!/usr/bin/env python3
"""Local, rule-based extraction of key fields from common tax forms.

This is the second tool in the suite. Like the sorter, it is fully local:
no AI, no machine learning, no cloud services, and no paid APIs. Field values
are pulled from selectable PDF text and local Tesseract OCR using label-anchored
regular expressions.

Extraction is best-effort and assistive. Every value should be verified against
the source document, and anything the rules cannot read is left blank and the
row is flagged so a human enters it manually.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import sort_tax_docs
from sort_tax_docs import normalize_text

EXTRACTED_DATA_FILE_NAME = "Extracted_Form_Data.xlsx"

# A monetary value. Requires a thousands separator or a decimal portion so that
# bare box numbers (for example "1") and years (for example "2024") sitting next
# to a label are not mistaken for amounts. Real forms print cents; when OCR drops
# the decimal the value is left blank and flagged rather than guessed.
MONEY_PATTERN = r"\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+\.\d{2})"
EIN_PATTERN = r"\b\d{2}-\d{7}\b"
SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
YEAR_PATTERN = r"\b20\d{2}\b"

VERIFY_NOTE = "Best-effort local extraction; verify all values against the source document."
MISSING_KEY_FIELD_NOTE = "Key field(s) could not be read; manual entry required."


@dataclass(frozen=True)
class FieldSpec:
    """One extractable field on a form."""

    name: str
    header: str
    kind: str  # "amount", "year", "ein", "ssn", or "code"
    label: str = ""
    window: int = 48
    primary: bool = False


@dataclass(frozen=True)
class ExtractionResult:
    """Extracted values for a single document."""

    category: str
    values: dict[str, str]
    needs_review: bool
    notes: tuple[str, ...] = ()


# Field order here also defines the spreadsheet column order for each form.
EXTRACTION_SPECS: dict[str, tuple[FieldSpec, ...]] = {
    "W2": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("employer_ein", "Employer EIN (Box b)", "ein"),
        FieldSpec("employee_ssn", "Employee SSN (Box a)", "ssn"),
        FieldSpec("box1_wages", "Box 1 Wages", "amount", "WAGES, TIPS, OTHER COMPENSATION", primary=True),
        FieldSpec("box2_federal_withholding", "Box 2 Federal Withholding", "amount", "FEDERAL INCOME TAX WITHHELD"),
        FieldSpec("box3_social_security_wages", "Box 3 Social Security Wages", "amount", "SOCIAL SECURITY WAGES"),
        FieldSpec("box4_social_security_tax", "Box 4 Social Security Tax", "amount", "SOCIAL SECURITY TAX WITHHELD"),
        FieldSpec("box5_medicare_wages", "Box 5 Medicare Wages", "amount", "MEDICARE WAGES AND TIPS"),
        FieldSpec("box6_medicare_tax", "Box 6 Medicare Tax", "amount", "MEDICARE TAX WITHHELD"),
    ),
    "1099_NEC": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("payer_tin", "Payer TIN", "ein"),
        FieldSpec("recipient_tin", "Recipient TIN", "ssn"),
        FieldSpec("box1_nonemployee_compensation", "Box 1 Nonemployee Compensation", "amount", "NONEMPLOYEE COMPENSATION", primary=True),
        FieldSpec("box4_federal_withholding", "Box 4 Federal Withholding", "amount", "FEDERAL INCOME TAX WITHHELD"),
    ),
    "1099_INT_DIV": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("payer_tin", "Payer TIN", "ein"),
        FieldSpec("recipient_tin", "Recipient TIN", "ssn"),
        FieldSpec("interest_income", "Interest Income (1099-INT Box 1)", "amount", "INTEREST INCOME", primary=True),
        FieldSpec("ordinary_dividends", "Ordinary Dividends (1099-DIV Box 1a)", "amount", "ORDINARY DIVIDENDS", primary=True),
        FieldSpec("qualified_dividends", "Qualified Dividends (1099-DIV Box 1b)", "amount", "QUALIFIED DIVIDENDS"),
        FieldSpec("total_capital_gain", "Total Capital Gain (1099-DIV Box 2a)", "amount", "TOTAL CAPITAL GAIN"),
        FieldSpec("federal_withholding", "Federal Withholding", "amount", "FEDERAL INCOME TAX WITHHELD"),
    ),
    "1099_R": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("payer_tin", "Payer TIN", "ein"),
        FieldSpec("recipient_tin", "Recipient TIN", "ssn"),
        FieldSpec("box1_gross_distribution", "Box 1 Gross Distribution", "amount", "GROSS DISTRIBUTION", primary=True),
        FieldSpec("box2a_taxable_amount", "Box 2a Taxable Amount", "amount", "TAXABLE AMOUNT"),
        FieldSpec("box4_federal_withholding", "Box 4 Federal Withholding", "amount", "FEDERAL INCOME TAX WITHHELD"),
        FieldSpec("box7_distribution_code", "Box 7 Distribution Code", "code", "DISTRIBUTION CODE", window=20),
    ),
}

SUPPORTED_CATEGORIES = tuple(EXTRACTION_SPECS)


def _clean_amount(raw: str) -> str:
    """Normalize a captured amount by removing separators and currency symbols."""

    return raw.replace(",", "").replace("$", "").strip()


def _amount_after_label(text: str, label: str, window: int) -> str:
    """Return the first monetary value found just after any occurrence of a label.

    Box-label words often appear first in the form title, far from the value, so
    every occurrence is checked and the first one with a nearby amount wins.
    """

    for occurrence in re.finditer(re.escape(label), text):
        segment = text[occurrence.end() : occurrence.end() + window]
        match = re.search(MONEY_PATTERN, segment)
        if match:
            return _clean_amount(match.group(1))
    return ""


def _code_after_label(text: str, label: str, window: int) -> str:
    """Return a short alphanumeric code that appears just after a label."""

    index = text.find(label)
    if index == -1:
        return ""
    start = index + len(label)
    segment = text[start : start + window]
    match = re.search(r"\b([0-9A-Z]{1,2})\b", segment)
    return match.group(1) if match else ""


def _first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def _extract_one(spec: FieldSpec, normalized_text: str) -> str:
    """Extract a single field value from already-normalized text."""

    if spec.kind == "amount":
        return _amount_after_label(normalized_text, spec.label, spec.window)
    if spec.kind == "code":
        return _code_after_label(normalized_text, spec.label, spec.window)
    if spec.kind == "year":
        return _first_match(YEAR_PATTERN, normalized_text)
    if spec.kind == "ein":
        return _first_match(EIN_PATTERN, normalized_text)
    if spec.kind == "ssn":
        return _first_match(SSN_PATTERN, normalized_text)
    return ""


def extract_form_fields(category: str, text: str) -> ExtractionResult:
    """Extract known fields for a form category from raw extracted/OCR text."""

    specs = EXTRACTION_SPECS.get(category, ())
    normalized_text = normalize_text(text)

    values: dict[str, str] = {}
    primary_exists = False
    primary_found = False
    for spec in specs:
        value = _extract_one(spec, normalized_text)
        values[spec.name] = value
        if spec.primary:
            primary_exists = True
            primary_found = primary_found or bool(value)

    needs_review = (primary_exists and not primary_found) or not any(values.values())
    notes = [VERIFY_NOTE]
    if needs_review:
        notes.append(MISSING_KEY_FIELD_NOTE)
    return ExtractionResult(category, values, needs_review, tuple(notes))


def extracted_columns(category: str) -> list[str]:
    """Return spreadsheet column headers for a form category."""

    specs = EXTRACTION_SPECS[category]
    return ["Source File", *(spec.header for spec in specs), "Needs Review", "Notes"]


def _row_for(category: str, source_name: str, result: ExtractionResult) -> dict[str, object]:
    specs = EXTRACTION_SPECS[category]
    row: dict[str, object] = {"Source File": source_name}
    for spec in specs:
        row[spec.header] = result.values.get(spec.name, "")
    row["Needs Review"] = "Yes" if result.needs_review else "No"
    row["Notes"] = " ".join(result.notes)
    return row


def write_extracted_data(
    rows_by_category: dict[str, list[dict[str, object]]], output_folder: Path
) -> Path | None:
    """Write one sheet per form type. Return the path, or None when nothing extracted."""

    if not any(rows_by_category.values()):
        return None

    import pandas as pd

    path = output_folder / EXTRACTED_DATA_FILE_NAME
    with pd.ExcelWriter(path) as writer:
        for category in EXTRACTION_SPECS:
            rows = rows_by_category.get(category)
            if not rows:
                continue
            dataframe = pd.DataFrame(rows, columns=extracted_columns(category))
            dataframe.to_excel(writer, sheet_name=category, index=False)
    return path


def run_extraction(input_folder, save_extracted_text=False, status_callback=None) -> dict:
    """Read supported files, extract fields for known forms, and write a workbook."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)
    files = list(sort_tax_docs.iter_supported_files(input_folder, output_folder))

    rows_by_category: dict[str, list[dict[str, object]]] = defaultdict(list)
    review_count = 0
    for index, file_path in enumerate(files, start=1):
        if status_callback:
            status_callback(f"Extracting {index} of {len(files)}: {file_path.name}")
        try:
            text, _ocr_used, _note, classification, _debug = (
                sort_tax_docs.extract_text_and_classification(file_path)
            )
        except Exception:  # Keep going through the rest of the upload folder.
            continue
        category = classification.category
        if category not in EXTRACTION_SPECS:
            continue
        result = extract_form_fields(category, text)
        rows_by_category[category].append(_row_for(category, file_path.name, result))
        if result.needs_review:
            review_count += 1

    data_path = write_extracted_data(rows_by_category, output_folder)
    counts = {category: len(rows) for category, rows in rows_by_category.items()}
    total_forms = sum(counts.values())
    return {
        "tool": "extract",
        "output_folder": output_folder,
        "data_path": data_path,
        "counts_by_category": counts,
        "total_forms": total_forms,
        "review_count": review_count,
        "summary": (
            f"Extracted {total_forms} form(s) across {len(counts)} type(s); "
            f"{review_count} flagged for manual entry."
            if total_forms
            else "No W-2 or 1099 forms were recognized for extraction."
        ),
    }


def main() -> int:
    """Run extraction from the command line for one folder."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Extract key fields from W-2 and 1099 forms into a spreadsheet."
    )
    parser.add_argument("input_folder", help="Folder containing uploaded tax documents.")
    parser.add_argument(
        "--save-extracted-text",
        action="store_true",
        help="Reserved for parity with the sorter; extraction always reads text locally.",
    )
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1
    if not sort_tax_docs.check_dependencies():
        return 1

    result = run_extraction(folder, status_callback=lambda message: print(message))
    print(result["summary"])
    if result["data_path"]:
        print(f"Extracted data: {result['data_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
