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

import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import sort_tax_docs
from sort_tax_docs import normalize_text

EXTRACTED_DATA_FILE_NAME = "Extracted_Form_Data.xlsx"
# Per-form-type CSVs with stable machine keys and typed values, for feeding a
# downstream Drake entry script. Generic keys; map them to Drake fields there.
DRAKE_EXPORT_FOLDER_NAME = "Drake_Export"
RECORD_METADATA_FIELDS = ("form_type", "source_file", "page", "needs_review")

# A monetary value. Requires a thousands separator or a decimal portion so that
# bare box numbers (for example "1") and years (for example "2024") sitting next
# to a label are not mistaken for amounts. Real forms print cents; when OCR drops
# the decimal the value is left blank and flagged rather than guessed.
# Strict money: comma-grouped (1,234[.56]) or decimal cents (1234.56). Preferred.
MONEY_PATTERN = r"\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+\.\d{2})"
# Whole-dollar fallback: a 3+ digit integer that is NOT a 4-digit year and is not part
# of a hyphenated EIN/SSN/TIN (the (?<![\d-]) / (?![\d-]) boundaries reject e.g. the
# "3456789" of an EIN "12-3456789"). Used only when no strict amount is near the label.
WHOLE_DOLLAR_PATTERN = r"(?<![\d-])(?!(?:19|20)\d{2}(?![\d-]))\d{3,}(?![\d-])"
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
    "1099_G": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("payer_tin", "Payer TIN", "ein"),
        FieldSpec("recipient_tin", "Recipient TIN", "ssn"),
        FieldSpec("box1_unemployment_compensation", "Box 1 Unemployment Compensation", "amount", "UNEMPLOYMENT COMPENSATION", primary=True),
        FieldSpec("box2_state_income_tax_refunds", "Box 2 State/Local Tax Refunds", "amount", "STATE OR LOCAL INCOME TAX REFUNDS", primary=True),
        FieldSpec("box4_federal_withholding", "Box 4 Federal Withholding", "amount", "FEDERAL INCOME TAX WITHHELD"),
    ),
    "1099_K": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("payer_tin", "Payer TIN", "ein"),
        FieldSpec("payee_tin", "Payee TIN", "ssn"),
        FieldSpec("box1a_gross_amount", "Box 1a Gross Amount", "amount", "GROSS AMOUNT OF PAYMENT CARD", primary=True),
        FieldSpec("box4_federal_withholding", "Box 4 Federal Withholding", "amount", "FEDERAL INCOME TAX WITHHELD"),
    ),
    "SSA_1099": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("beneficiary_ssn", "Beneficiary SSN", "ssn"),
        FieldSpec("box3_benefits_paid", "Box 3 Benefits Paid", "amount", "BENEFITS PAID"),
        FieldSpec("box5_net_benefits", "Box 5 Net Benefits", "amount", "NET BENEFITS", primary=True),
        FieldSpec("box6_voluntary_withholding", "Box 6 Voluntary Withholding", "amount", "VOLUNTARY FEDERAL INCOME TAX WITHHELD"),
    ),
    "1098_Mortgage": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("lender_tin", "Lender TIN", "ein"),
        FieldSpec("borrower_tin", "Borrower TIN", "ssn"),
        FieldSpec("box1_mortgage_interest", "Box 1 Mortgage Interest", "amount", "MORTGAGE INTEREST RECEIVED", primary=True),
        FieldSpec("box5_mortgage_insurance", "Box 5 Mortgage Insurance Premiums", "amount", "MORTGAGE INSURANCE PREMIUMS"),
        FieldSpec("box6_points_paid", "Box 6 Points Paid", "amount", "POINTS PAID"),
    ),
    "1098_Tuition": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("filer_tin", "Filer TIN", "ein"),
        FieldSpec("student_ssn", "Student SSN", "ssn"),
        FieldSpec("box1_payments_received", "Box 1 Payments Received", "amount", "PAYMENTS RECEIVED FOR QUALIFIED TUITION", primary=True),
        FieldSpec("box4_adjustments", "Box 4 Adjustments", "amount", "ADJUSTMENTS MADE FOR A PRIOR YEAR"),
        FieldSpec("box5_scholarships_or_grants", "Box 5 Scholarships or Grants", "amount", "SCHOLARSHIPS OR GRANTS"),
    ),
    "Brokerage_1099B": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("payer_tin", "Payer TIN", "ein"),
        FieldSpec("recipient_tin", "Recipient TIN", "ssn"),
        FieldSpec("proceeds", "Proceeds (Box 1d)", "amount", "PROCEEDS"),
        FieldSpec("cost_basis", "Cost Basis (Box 1e)", "amount", "COST BASIS"),
    ),
    "K1": (
        FieldSpec("tax_year", "Tax Year", "year"),
        FieldSpec("entity_ein", "Entity EIN", "ein"),
        FieldSpec("partner_ssn", "Partner/Shareholder SSN", "ssn"),
        FieldSpec("box1_ordinary_business_income", "Box 1 Ordinary Business Income", "amount", "ORDINARY BUSINESS INCOME", primary=True),
        FieldSpec("box2_net_rental_real_estate", "Box 2 Net Rental Real Estate", "amount", "NET RENTAL REAL ESTATE INCOME"),
        FieldSpec("box5_interest_income", "Box 5 Interest Income", "amount", "INTEREST INCOME"),
        FieldSpec("box6a_ordinary_dividends", "Box 6a Ordinary Dividends", "amount", "ORDINARY DIVIDENDS"),
        FieldSpec("box9a_net_longterm_capital_gain", "Box 9a Net Long-Term Capital Gain", "amount", "NET LONG-TERM CAPITAL GAIN"),
    ),
}

# Some forms cannot be reduced to a few fields safely. Always flag them and add a
# clear note so a human checks the detail.
ALWAYS_REVIEW_CATEGORIES = {"Brokerage_1099B"}
CATEGORY_NOTES = {
    "Brokerage_1099B": "1099-B is transactional; verify every sale against the broker statement.",
}

SUPPORTED_CATEGORIES = tuple(EXTRACTION_SPECS)


def _clean_amount(raw: str) -> str:
    """Normalize a captured amount by removing separators and currency symbols."""

    return raw.replace(",", "").replace("$", "").strip()


def _amount_after_label(text: str, label: str, window: int) -> str:
    """Return the monetary value found just after any occurrence of a label.

    Box-label words often appear first in the form title, far from the value, so
    every occurrence is checked. A strict (comma/cents) amount is preferred and wins
    over a plain whole-dollar integer anywhere, so account numbers or the tax year do
    not override a real value; the whole-dollar fallback only applies when no strict
    amount is found near the label at all.
    """

    ends = [occurrence.end() for occurrence in re.finditer(re.escape(label), text)]
    for end in ends:  # preferred pass: comma/cents amounts
        match = re.search(MONEY_PATTERN, text[end : end + window])
        if match:
            return _clean_amount(match.group(1))
    for end in ends:  # fallback pass: whole-dollar integers (e.g. 52000)
        match = re.search(WHOLE_DOLLAR_PATTERN, text[end : end + window])
        if match:
            return _clean_amount(match.group(0))
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

    key_missing = (primary_exists and not primary_found) or not any(values.values())
    needs_review = key_missing or category in ALWAYS_REVIEW_CATEGORIES

    notes = [VERIFY_NOTE]
    category_note = CATEGORY_NOTES.get(category)
    if category_note:
        notes.append(category_note)
    if key_missing:
        notes.append(MISSING_KEY_FIELD_NOTE)
    return ExtractionResult(category, values, needs_review, tuple(notes))


def _typed_value(spec: FieldSpec, raw: str):
    """Convert a raw extracted string to a typed value (float for amounts)."""

    if not raw:
        return None
    if spec.kind == "amount":
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


def _record_for(
    category: str, source_file: str, page: int | None, result: ExtractionResult
) -> dict[str, object]:
    """Build one typed record (stable machine keys) for a single extracted form."""

    record: dict[str, object] = {
        "form_type": category,
        "source_file": source_file,
        "page": page,
        "needs_review": result.needs_review,
    }
    for spec in EXTRACTION_SPECS[category]:
        record[spec.name] = _typed_value(spec, result.values.get(spec.name, ""))
    record["notes"] = " ".join(result.notes)
    return record


def drake_columns(category: str) -> list[str]:
    """Column order for the Drake CSV export of a form category."""

    specs = EXTRACTION_SPECS[category]
    return [*RECORD_METADATA_FIELDS, *(spec.name for spec in specs), "notes"]


def _excel_row(record: dict[str, object]) -> dict[str, object]:
    """Derive a human-readable spreadsheet row from a typed record."""

    category = str(record["form_type"])
    source = str(record["source_file"])
    if record["page"]:
        source = f"{source} (page {record['page']})"
    row: dict[str, object] = {"Source File": source}
    for spec in EXTRACTION_SPECS[category]:
        value = record.get(spec.name)
        row[spec.header] = "" if value is None else value
    row["Needs Review"] = "Yes" if record["needs_review"] else "No"
    row["Notes"] = record.get("notes", "")
    return row


def extracted_columns(category: str) -> list[str]:
    """Return spreadsheet column headers for a form category."""

    specs = EXTRACTION_SPECS[category]
    return ["Source File", *(spec.header for spec in specs), "Needs Review", "Notes"]


def write_extracted_data(
    records_by_category: dict[str, list[dict[str, object]]], output_folder: Path
) -> Path | None:
    """Write one Excel sheet per form type. Return the path, or None if empty."""

    if not any(records_by_category.values()):
        return None

    import pandas as pd

    path = output_folder / EXTRACTED_DATA_FILE_NAME
    with pd.ExcelWriter(path) as writer:
        for category in EXTRACTION_SPECS:
            records = records_by_category.get(category)
            if not records:
                continue
            rows = [_excel_row(record) for record in records]
            dataframe = pd.DataFrame(rows, columns=extracted_columns(category))
            dataframe.to_excel(writer, sheet_name=category, index=False)
    return path


def write_drake_csvs(
    records_by_category: dict[str, list[dict[str, object]]], output_folder: Path
) -> Path | None:
    """Write one CSV per form type with stable keys and typed values for Drake.

    Returns the export folder, or None when nothing was extracted.
    """

    if not any(records_by_category.values()):
        return None

    export_folder = output_folder / DRAKE_EXPORT_FOLDER_NAME
    export_folder.mkdir(exist_ok=True)
    for category in EXTRACTION_SPECS:
        records = records_by_category.get(category)
        if not records:
            continue
        columns = drake_columns(category)
        csv_path = export_folder / f"{category}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {column: ("" if record.get(column) is None else record[column]) for column in columns}
                )
    return export_folder


def _extract_units(file_path: Path) -> list[tuple[str, int | None, str, str]]:
    """Return (source_file, page, category, text) units for a file.

    PDFs are read page by page so a combined upload with several forms yields one
    unit per page (page is 1-based); images are read as a single unit (page None).
    """

    if file_path.suffix.lower() == ".pdf":
        pages = sort_tax_docs.extract_pdf_page_texts(file_path)
        multi_page = len(pages) > 1
        units: list[tuple[int | None, str, str]] = []
        for page_number, (text, _ocr_used) in enumerate(pages, start=1):
            category = sort_tax_docs.classify_text(text).category
            page = page_number if multi_page else None
            units.append((file_path.name, page, category, text))
        return units

    text, _ocr_used, _note, classification, _debug = (
        sort_tax_docs.extract_text_and_classification(file_path)
    )
    return [(file_path.name, None, classification.category, text)]


def run_extraction(input_folder, save_extracted_text=False, status_callback=None) -> dict:
    """Read supported files, extract fields for known forms, and write a workbook."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)
    files = list(sort_tax_docs.iter_supported_files(input_folder, output_folder))

    records_by_category: dict[str, list[dict[str, object]]] = defaultdict(list)
    review_count = 0
    for index, file_path in enumerate(files, start=1):
        if status_callback:
            status_callback(f"Extracting {index} of {len(files)}: {file_path.name}")
        try:
            units = _extract_units(file_path)
        except Exception:  # Keep going through the rest of the upload folder.
            continue
        for source_file, page, category, text in units:
            if category not in EXTRACTION_SPECS:
                continue
            result = extract_form_fields(category, text)
            records_by_category[category].append(
                _record_for(category, source_file, page, result)
            )
            if result.needs_review:
                review_count += 1

    data_path = write_extracted_data(records_by_category, output_folder)
    drake_export_folder = write_drake_csvs(records_by_category, output_folder)
    counts = {category: len(records) for category, records in records_by_category.items()}
    total_forms = sum(counts.values())
    return {
        "tool": "extract",
        "output_folder": output_folder,
        "data_path": data_path,
        "drake_export_folder": drake_export_folder,
        "records_by_category": dict(records_by_category),
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
        description="Extract key fields from W-2 and 1099 forms into a spreadsheet "
        "and per-form CSVs for a Drake entry script."
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
    if result["drake_export_folder"]:
        print(f"Drake CSV export: {result['drake_export_folder']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
