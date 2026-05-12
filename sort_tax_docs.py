#!/usr/bin/env python3
"""Prototype local tax document sorter.

This script uses simple keyword rules plus local text extraction/OCR to copy (or move)
obvious tax documents into category folders and write an inventory workbook.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
OUTPUT_FOLDER_NAME = "Organized_Tax_Documents"
LOG_FILE_NAME = "processing_log.txt"
INVENTORY_FILE_NAME = "Document_Inventory.xlsx"
MIN_SELECTABLE_TEXT_CHARS = 50
MULTIPLE_MATCH_NOTE = "Multiple possible document types detected; manual review recommended."

COMMON_TESSERACT_PATHS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)

CATEGORY_FOLDERS = {
    "W2": "01_W2",
    "1099_NEC": "02_1099_NEC",
    "1099_MISC": "03_1099_MISC",
    "1099_INT_DIV": "04_1099_INT_DIV",
    "1099_R": "05_1099_R",
    "1098_Mortgage": "06_1098_Mortgage",
    "1095_A": "07_1095_A",
    "K1": "08_K1",
    "Brokerage_1099B": "09_Brokerage_1099B",
    "ID": "10_ID",
    "1098_Tuition": "11_1098_Tuition",
    "NeedsReview": "99_Needs_Review",
}

CONFIDENCE_RANK = {"Low": 0, "Medium": 1, "High": 2}


@dataclass(frozen=True)
class KeywordRule:
    """A single keyword rule used for classification."""

    category: str
    keyword: str
    confidence: str


@dataclass(frozen=True)
class ClassificationResult:
    """Classification details recorded in the inventory."""

    category: str
    confidence: str
    matched_keyword: str
    multiple_categories_detected: bool = False


# Exact form identifiers are high confidence. Supporting descriptive phrases are
# medium confidence. Rule order matters for priority. Brokerage rules are before
# 1099-INT/DIV so consolidated brokerage statements are not misfiled.
RULES: tuple[KeywordRule, ...] = (
    KeywordRule("W2", "Form W-2", "High"),
    KeywordRule("W2", "Wage and Tax Statement", "Medium"),
    KeywordRule("1099_NEC", "1099-NEC", "High"),
    KeywordRule("1099_NEC", "Nonemployee Compensation", "Medium"),
    KeywordRule("1099_MISC", "1099-MISC", "High"),
    KeywordRule("Brokerage_1099B", "Consolidated 1099", "High"),
    KeywordRule("Brokerage_1099B", "1099-B", "High"),
    KeywordRule("Brokerage_1099B", "Proceeds From Broker", "Medium"),
    KeywordRule("Brokerage_1099B", "Cost Basis", "Medium"),
    KeywordRule("1099_INT_DIV", "1099-INT", "High"),
    KeywordRule("1099_INT_DIV", "1099-DIV", "High"),
    KeywordRule("1099_R", "1099-R", "High"),
    KeywordRule("1099_R", "Distributions From Pensions", "Medium"),
    KeywordRule("1098_Mortgage", "Form 1098 Mortgage Interest Statement", "High"),
    KeywordRule("1098_Mortgage", "Mortgage Interest Statement", "High"),
    KeywordRule("1098_Mortgage", "Mortgage Interest", "Medium"),
    KeywordRule("1098_Mortgage", "Lender", "Medium"),
    KeywordRule("1098_Tuition", "1098-T", "High"),
    KeywordRule("1098_Tuition", "Tuition Statement", "Medium"),
    KeywordRule("1095_A", "1095-A", "High"),
    KeywordRule("1095_A", "Health Insurance Marketplace Statement", "Medium"),
    KeywordRule("K1", "Schedule K-1", "High"),
    KeywordRule("ID", "Driver License", "High"),
    KeywordRule("ID", "Driver's License", "High"),
    KeywordRule("ID", "State ID", "High"),
    KeywordRule("ID", "Identification Card", "Medium"),
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Sort obvious tax documents into categorized folders using local extraction/OCR."
    )
    parser.add_argument("input_folder", nargs="?", help="Folder containing uploaded tax documents.")
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying them. Originals are never deleted separately.",
    )
    parser.add_argument(
        "--check-dependencies",
        action="store_true",
        help="Check Python packages and Tesseract OCR without processing files.",
    )
    parser.add_argument(
        "--install-dependencies",
        action="store_true",
        help="Run the setup helper to install Python packages and Tesseract when possible.",
    )
    parser.add_argument(
        "--skip-system-install",
        action="store_true",
        help="With --install-dependencies, install Python packages only and skip Tesseract.",
    )
    return parser.parse_args()


def find_tesseract_executable() -> str | None:
    """Find Tesseract on PATH or in common Windows install locations."""

    path_match = shutil.which("tesseract")
    if path_match:
        return path_match

    for candidate in COMMON_TESSERACT_PATHS:
        if candidate.exists():
            return str(candidate)
    return None


def configure_pytesseract() -> bool:
    """Configure pytesseract with a discovered Tesseract executable."""

    executable = find_tesseract_executable()
    if not executable:
        return False

    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = executable
    return True


def check_dependencies(verbose: bool = True) -> bool:
    """Check required Python packages and the Tesseract executable."""

    missing: list[str] = []
    import_checks = {
        "fitz": "PyMuPDF",
        "pandas": "pandas",
        "pytesseract": "pytesseract",
        "PIL": "Pillow",
        "openpyxl": "openpyxl",
    }
    for module_name, package_name in import_checks.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)

    tesseract_path = find_tesseract_executable()
    if tesseract_path is None:
        missing.append("Tesseract OCR application")

    if not missing:
        if verbose:
            print("All required Python packages and Tesseract OCR appear to be installed.")
            print(f"Tesseract executable: {tesseract_path}")
        return True

    if verbose:
        print("Missing dependencies:")
        for item in missing:
            print(f"  - {item}")
        print("\nRun this setup helper, then try again:")
        print(f"  {sys.executable} setup_tax_doc_sorter.py")
    return False


def install_dependencies(skip_system: bool = False) -> bool:
    """Run the setup helper from this same folder."""

    setup_script = Path(__file__).with_name("setup_tax_doc_sorter.py")
    if not setup_script.exists():
        print(f"Could not find setup helper: {setup_script}")
        return False

    command = [sys.executable, str(setup_script)]
    if skip_system:
        command.append("--skip-system")
    return subprocess.run(command, check=False).returncode == 0


def setup_output_folders(input_folder: Path) -> Path:
    """Create the output folder and all category folders."""

    output_folder = input_folder / OUTPUT_FOLDER_NAME
    output_folder.mkdir(exist_ok=True)
    for folder_name in CATEGORY_FOLDERS.values():
        (output_folder / folder_name).mkdir(exist_ok=True)
    return output_folder


def setup_logging(output_folder: Path) -> None:
    """Write logs to a plain text file and to the console."""

    log_path = output_folder / LOG_FILE_NAME
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )


def iter_supported_files(input_folder: Path, output_folder: Path) -> Iterable[Path]:
    """Yield supported files below input_folder, excluding generated output."""

    for path in input_folder.rglob("*"):
        if not path.is_file():
            continue
        if output_folder in path.parents:
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def extract_pdf_selectable_text(file_path: Path) -> str:
    """Extract selectable text from a PDF using PyMuPDF."""

    import fitz  # PyMuPDF

    text_parts: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            text_parts.append(page.get_text("text"))
    return "\n".join(text_parts).strip()


def ocr_pdf(file_path: Path) -> str:
    """OCR a scanned PDF by rendering each page to an image locally."""

    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image

    configure_pytesseract()
    text_parts: list[str] = []
    with fitz.open(file_path) as document:
        for page_number, page in enumerate(document, start=1):
            logging.debug("OCR PDF page %s of %s", page_number, file_path.name)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            text_parts.append(pytesseract.image_to_string(image))
    return "\n".join(text_parts).strip()


def ocr_image(file_path: Path) -> str:
    """OCR an image file. Multi-page TIFF files are handled page by page."""

    import pytesseract
    from PIL import Image, ImageSequence

    configure_pytesseract()
    text_parts: list[str] = []
    with Image.open(file_path) as image:
        for page_number, frame in enumerate(ImageSequence.Iterator(image), start=1):
            logging.debug("OCR image page %s of %s", page_number, file_path.name)
            text_parts.append(pytesseract.image_to_string(frame.convert("RGB")))
    return "\n".join(text_parts).strip()


def extract_text(file_path: Path) -> tuple[str, bool, str]:
    """Extract text from a supported file.

    Returns a tuple of (text, ocr_used, notes). PDFs are tried with selectable
    text extraction first; OCR is used only when little/no text is found.
    """

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        selectable_text = extract_pdf_selectable_text(file_path)
        if len(selectable_text.strip()) >= MIN_SELECTABLE_TEXT_CHARS:
            return selectable_text, False, "Selectable PDF text extracted."
        ocr_text = ocr_pdf(file_path)
        note = "PDF had little/no selectable text; OCR used."
        if selectable_text.strip():
            note += " Limited selectable text was also present."
        return ocr_text or selectable_text, True, note

    return ocr_image(file_path), True, "Image OCR used."


def normalize_text(text: str) -> str:
    """Normalize text to make keyword matching less brittle."""

    text = text.upper().replace("’", "'")
    return re.sub(r"\s+", " ", text)


def classify_text(text: str) -> ClassificationResult:
    """Classify text using simple keyword rules. If unsure, do not guess."""

    normalized_text = normalize_text(text)
    best_match_by_category: dict[str, KeywordRule] = {}

    for rule in RULES:
        if normalize_text(rule.keyword) not in normalized_text:
            continue

        existing = best_match_by_category.get(rule.category)
        if existing is None or CONFIDENCE_RANK[rule.confidence] > CONFIDENCE_RANK[existing.confidence]:
            best_match_by_category[rule.category] = rule

    if not best_match_by_category:
        return ClassificationResult("NeedsReview", "Low", "")

    # Keep the highest-confidence match. Ties preserve RULES priority order.
    for rule in RULES:
        category_match = best_match_by_category.get(rule.category)
        if category_match != rule:
            continue
        if all(
            CONFIDENCE_RANK[category_match.confidence] >= CONFIDENCE_RANK[other.confidence]
            for other in best_match_by_category.values()
        ):
            return ClassificationResult(
                category_match.category,
                category_match.confidence,
                category_match.keyword,
                multiple_categories_detected=len(best_match_by_category) > 1,
            )

    return ClassificationResult("NeedsReview", "Low", "")


def safe_filename_part(name: str) -> str:
    """Keep filenames readable while removing characters unsafe on common systems."""

    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
    return cleaned or "unnamed"


def unique_destination_path(destination_folder: Path, filename: str) -> Path:
    """Return a destination path that does not overwrite an existing file."""

    candidate = destination_folder / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        candidate = destination_folder / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def build_new_filename(category: str, original_name: str) -> str:
    """Build the DetectedType_OriginalFileName output filename."""

    return f"{category}_{safe_filename_part(original_name)}"


def copy_or_move_file(source: Path, destination: Path, move: bool) -> None:
    """Copy by default, or move when explicitly requested."""

    if move:
        shutil.move(str(source), str(destination))
    else:
        shutil.copy2(source, destination)


def process_file(file_path: Path, output_folder: Path, move: bool) -> dict[str, object]:
    """Process one document and return an inventory row."""

    notes: list[str] = []
    ocr_used = False
    result = ClassificationResult("NeedsReview", "Low", "")
    destination_path: Path | None = None

    try:
        logging.info("Processing %s", file_path)
        text, ocr_used, extraction_note = extract_text(file_path)
        notes.append(extraction_note)
        if not text.strip():
            notes.append("No readable text found.")
        result = classify_text(text)
        if result.multiple_categories_detected:
            notes.append(MULTIPLE_MATCH_NOTE)

        category_folder = output_folder / CATEGORY_FOLDERS[result.category]
        new_filename = build_new_filename(result.category, file_path.name)
        destination_path = unique_destination_path(category_folder, new_filename)
        copy_or_move_file(file_path, destination_path, move)
        logging.info(
            "%s %s -> %s (%s, %s)",
            "Moved" if move else "Copied",
            file_path.name,
            destination_path,
            result.category,
            result.confidence,
        )
    except Exception as exc:  # Keep processing other client-upload files.
        logging.exception("Error processing %s", file_path)
        notes.append(f"ERROR: {exc}")

    return {
        "Original File Name": file_path.name,
        "New File Name": destination_path.name if destination_path else "",
        "Original Path": str(file_path),
        "New Path": str(destination_path) if destination_path else "",
        "Detected Category": result.category,
        "Confidence": result.confidence,
        "Matched Keyword": result.matched_keyword,
        "OCR Used": "Yes" if ocr_used else "No",
        "Notes": " ".join(notes),
    }


def write_inventory(rows: list[dict[str, object]], output_folder: Path) -> Path:
    """Create the Excel inventory workbook."""

    inventory_path = output_folder / INVENTORY_FILE_NAME
    columns = [
        "Original File Name",
        "New File Name",
        "Original Path",
        "New Path",
        "Detected Category",
        "Confidence",
        "Matched Keyword",
        "OCR Used",
        "Notes",
    ]
    import pandas as pd

    dataframe = pd.DataFrame(rows, columns=columns)
    dataframe.to_excel(inventory_path, index=False)
    return inventory_path


def main() -> int:
    """Run the tax document sorter."""

    args = parse_args()
    if args.install_dependencies:
        if not install_dependencies(skip_system=args.skip_system_install):
            return 1
        if not args.input_folder:
            return 0

    if args.check_dependencies:
        return 0 if check_dependencies() else 1
    if not args.input_folder:
        print("Input folder is required unless using --check-dependencies.")
        print(f"Run setup first if needed: {sys.executable} setup_tax_doc_sorter.py")
        return 1

    if not check_dependencies():
        return 1

    input_folder = Path(args.input_folder).expanduser().resolve()
    if not input_folder.exists() or not input_folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {input_folder}")
        return 1

    output_folder = setup_output_folders(input_folder)
    setup_logging(output_folder)
    logging.info("Starting tax document sort for %s", input_folder)
    logging.info("Default safety mode: %s", "MOVE" if args.move else "COPY")

    rows: list[dict[str, object]] = []
    for file_path in iter_supported_files(input_folder, output_folder):
        rows.append(process_file(file_path, output_folder, args.move))

    inventory_path = write_inventory(rows, output_folder)
    logging.info("Inventory written to %s", inventory_path)
    logging.info("Finished. Processed %s supported file(s).", len(rows))
    print(f"Finished. Processed {len(rows)} supported file(s).")
    print(f"Output folder: {output_folder}")
    print(f"Inventory: {inventory_path}")
    print(f"Log: {output_folder / LOG_FILE_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
