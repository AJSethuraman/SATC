#!/usr/bin/env python3
"""Prototype local tax document sorter.

This script uses simple keyword rules plus local text extraction/OCR to copy (or move)
obvious tax documents into category folders and write an inventory workbook.
"""

from __future__ import annotations

import argparse
import io
import json
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
    "1099_G": "12_1099_G",
    "1099_K": "13_1099_K",
    "SSA_1099": "14_SSA_1099",
    "NeedsReview": "99_Needs_Review",
}


@dataclass(frozen=True)
class ScoringRule:
    """A weighted keyword rule used by the conservative classifier."""

    category: str
    keyword: str
    weight: int


@dataclass(frozen=True)
class ClassificationResult:
    """Classification details recorded in the inventory."""

    category: str
    confidence: str
    matched_keyword: str
    matched_keywords: tuple[str, ...] = ()
    winning_score: int = 0
    runner_up_category: str = ""
    runner_up_score: int = 0
    category_scores: dict[str, int] | None = None
    notes: tuple[str, ...] = ()
    multiple_categories_detected: bool = False


# Strong official identifiers carry enough weight to classify. Generic words are
# intentionally absent or low-weight so they cannot classify by themselves.
SCORING_RULES: tuple[ScoringRule, ...] = (
    ScoringRule("W2", "FORM W-2", 8),
    ScoringRule("W2", "WAGE AND TAX STATEMENT", 8),
    ScoringRule("1099_NEC", "FORM 1099-NEC", 10),
    ScoringRule("1099_NEC", "1099-NEC", 9),
    ScoringRule("1099_NEC", "NONEMPLOYEE COMPENSATION", 8),
    ScoringRule("1099_MISC", "FORM 1099-MISC", 10),
    ScoringRule("1099_MISC", "1099-MISC", 9),
    ScoringRule("1099_MISC", "MISCELLANEOUS INFORMATION", 2),
    ScoringRule("Brokerage_1099B", "CONSOLIDATED 1099", 10),
    ScoringRule("Brokerage_1099B", "PROCEEDS FROM BROKER AND BARTER EXCHANGE", 10),
    ScoringRule("Brokerage_1099B", "FORM 1099-B", 10),
    ScoringRule("Brokerage_1099B", "1099-B", 9),
    ScoringRule("Brokerage_1099B", "PROCEEDS FROM BROKER", 8),
    ScoringRule("Brokerage_1099B", "COST BASIS", 5),
    ScoringRule("Brokerage_1099B", "REALIZED GAIN", 5),
    ScoringRule("Brokerage_1099B", "REALIZED LOSS", 5),
    ScoringRule("Brokerage_1099B", "BROKERAGE LLC", 5),
    ScoringRule("Brokerage_1099B", "BROKERAGE", 4),
    ScoringRule("Brokerage_1099B", "TAX INFORMATION STATEMENT", 4),
    ScoringRule("1099_INT_DIV", "FORM 1099-INT", 9),
    ScoringRule("1099_INT_DIV", "1099-INT", 8),
    ScoringRule("1099_INT_DIV", "FORM 1099-DIV", 9),
    ScoringRule("1099_INT_DIV", "1099-DIV", 8),
    ScoringRule("1099_R", "FORM 1099-R", 10),
    ScoringRule("1099_R", "1099-R", 9),
    ScoringRule("1099_R", "DISTRIBUTIONS FROM PENSIONS", 8),
    ScoringRule("1099_R", "RETIREMENT OR PROFIT-SHARING PLANS", 8),
    ScoringRule("1098_Mortgage", "FORM 1098 MORTGAGE INTEREST STATEMENT", 10),
    ScoringRule("1098_Mortgage", "MORTGAGE INTEREST STATEMENT", 9),
    ScoringRule("1098_Mortgage", "MORTGAGE INTEREST RECEIVED", 8),
    ScoringRule("1098_Tuition", "FORM 1098-T", 10),
    ScoringRule("1098_Tuition", "1098-T", 9),
    ScoringRule("1098_Tuition", "TUITION STATEMENT", 8),
    ScoringRule("1095_A", "FORM 1095-A", 10),
    ScoringRule("1095_A", "1095-A", 9),
    ScoringRule("1095_A", "HEALTH INSURANCE MARKETPLACE STATEMENT", 8),
    ScoringRule("K1", "SCHEDULE K-1", 9),
    ScoringRule("K1", "PARTNER'S SHARE OF INCOME", 8),
    ScoringRule("K1", "SHAREHOLDER'S SHARE OF INCOME", 8),
    ScoringRule("K1", "BENEFICIARY'S SHARE OF INCOME", 8),
    ScoringRule("ID", "DRIVER LICENSE", 8),
    ScoringRule("ID", "DRIVER'S LICENSE", 8),
    ScoringRule("ID", "IDENTIFICATION CARD", 8),
    ScoringRule("ID", "STATE ID", 8),
    ScoringRule("1099_G", "FORM 1099-G", 10),
    ScoringRule("1099_G", "1099-G", 9),
    ScoringRule("1099_G", "CERTAIN GOVERNMENT PAYMENTS", 8),
    ScoringRule("1099_G", "UNEMPLOYMENT COMPENSATION", 5),
    ScoringRule("1099_K", "FORM 1099-K", 10),
    ScoringRule("1099_K", "1099-K", 9),
    ScoringRule("1099_K", "PAYMENT CARD AND THIRD PARTY NETWORK TRANSACTIONS", 8),
    ScoringRule("SSA_1099", "FORM SSA-1099", 10),
    ScoringRule("SSA_1099", "SSA-1099", 9),
    ScoringRule("SSA_1099", "SOCIAL SECURITY BENEFIT STATEMENT", 8),
)

BROKERAGE_INDICATORS = (
    "WEALTHFRONT BROKERAGE",
    "FIDELITY",
    "SCHWAB",
    "VANGUARD",
    "ROBINHOOD",
    "E*TRADE",
    "MORGAN STANLEY",
    "MERRILL",
    "TD AMERITRADE",
    "INTERACTIVE BROKERS",
    "COINBASE",
    "PUBLIC INVESTING",
)

W2_STRUCTURAL_INDICATORS = (
    "EMPLOYEE'S SOCIAL SECURITY NUMBER",
    "EMPLOYER IDENTIFICATION NUMBER",
    "EMPLOYER'S NAME, ADDRESS, AND ZIP CODE",
    "WAGES, TIPS, OTHER COMPENSATION",
    "FEDERAL INCOME TAX WITHHELD",
    "SOCIAL SECURITY WAGES",
    "MEDICARE WAGES AND TIPS",
    "CONTROL NUMBER",
    "SOCIAL SECURITY TAX WITHHELD",
    "MEDICARE TAX WITHHELD",
    "ALLOCATED TIPS",
    "DEPENDENT CARE BENEFITS",
    "NONQUALIFIED PLANS",
)
W2_STRUCTURAL_MIN_MATCHES = 4
W2_STRUCTURAL_SCORE = 8

CATEGORY_THRESHOLDS = {
    "W2": 8,
    "1099_NEC": 8,
    "1099_MISC": 9,
    "1099_INT_DIV": 8,
    "1099_R": 8,
    "1098_Mortgage": 8,
    "1098_Tuition": 8,
    "1095_A": 8,
    "K1": 8,
    "Brokerage_1099B": 8,
    "ID": 8,
    "1099_G": 8,
    "1099_K": 8,
    "SSA_1099": 8,
}
REVIEW_SCORE_THRESHOLD = 4
CLOSE_SCORE_DELTA = 3
MIN_RELIABLE_TEXT_CHARS = 8
CLASSIFICATION_CONFIDENCE_RANK = {"Low": 0, "Medium": 1, "High": 2}
DEBUG_TEXT_FOLDER_NAME = "_extracted_text_debug"


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
    parser.add_argument(
        "--save-extracted-text",
        action="store_true",
        help="Save selectable/OCR/combined text and scores for troubleshooting.",
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



def setup_debug_text_folder(output_folder: Path, save_extracted_text: bool) -> Path | None:
    """Create the optional extracted-text debug folder."""

    if not save_extracted_text:
        return None
    debug_folder = output_folder / DEBUG_TEXT_FOLDER_NAME
    debug_folder.mkdir(exist_ok=True)
    return debug_folder


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


def preprocess_image_for_ocr(image):
    """Apply simple local Pillow preprocessing before Tesseract OCR."""

    from PIL import ImageEnhance, ImageFilter, ImageOps

    grayscale = ImageOps.grayscale(image)
    contrasted = ImageOps.autocontrast(grayscale)
    contrasted = ImageEnhance.Contrast(contrasted).enhance(1.8)
    sharpened = ImageEnhance.Sharpness(contrasted).enhance(1.5)
    return sharpened.filter(ImageFilter.SHARPEN)


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
            # Decode via PNG so grayscale/CMYK pages are handled correctly instead
            # of assuming a fixed RGB channel layout from the raw samples buffer.
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            text_parts.append(pytesseract.image_to_string(preprocess_image_for_ocr(image)))
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
            text_parts.append(pytesseract.image_to_string(preprocess_image_for_ocr(frame)))
    return "\n".join(text_parts).strip()


def normalize_text(text: str) -> str:
    """Normalize OCR/text while preserving official hyphenated form names."""

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "−": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.upper()

    # OCR sometimes drops hyphens in form names. Reinsert them for matching.
    text = re.sub(r"\b1099\s+(NEC|MISC|INT|DIV|R|B|G|K)\b", r"1099-\1", text)
    text = re.sub(r"\bFORM\s+1099\s+(NEC|MISC|INT|DIV|R|B|G|K)\b", r"FORM 1099-\1", text)
    text = re.sub(r"\b1098\s+T\b", "1098-T", text)
    text = re.sub(r"\bFORM\s+1098\s+T\b", "FORM 1098-T", text)
    text = re.sub(r"\bSSA\s+1099\b", "SSA-1099", text)
    text = re.sub(r"\bFORM\s+SSA\s+1099\b", "FORM SSA-1099", text)
    text = re.sub(r"\bW\s+2\b", "W-2", text)
    text = re.sub(r"\bFORM\s+W\s+2\b", "FORM W-2", text)
    return re.sub(r"\s+", " ", text).strip()


def text_contains_classification_keyword(text: str) -> bool:
    """Return True when text contains any configured classification keyword."""

    normalized_text = normalize_text(text)
    return any(normalize_text(rule.keyword) in normalized_text for rule in SCORING_RULES)


def extract_text(file_path: Path) -> tuple[str, bool, str]:
    """Extract text from a supported file for compatibility with older callers."""

    text, ocr_used, note, _result, _debug_parts = extract_text_and_classification(file_path)
    return text, ocr_used, note


def is_successful_pdf_classification(result: ClassificationResult) -> bool:
    """Return True when selectable PDF text is strong enough to skip OCR."""

    return (
        result.category != "NeedsReview"
        and result.confidence == "High"
        and bool(result.matched_keywords)
    )


def better_classification(
    first: ClassificationResult, second: ClassificationResult
) -> ClassificationResult:
    """Choose the better classification result using conservative tie-breakers."""

    first_specific = first.category != "NeedsReview"
    second_specific = second.category != "NeedsReview"
    if first_specific != second_specific:
        return first if first_specific else second

    first_confidence = CLASSIFICATION_CONFIDENCE_RANK.get(first.confidence, 0)
    second_confidence = CLASSIFICATION_CONFIDENCE_RANK.get(second.confidence, 0)
    if first_confidence != second_confidence:
        return first if first_confidence > second_confidence else second

    if first.winning_score != second.winning_score:
        return first if first.winning_score > second.winning_score else second

    return first


def classification_debug_summary(result: ClassificationResult) -> str:
    """Return JSON classification details for debug text files."""

    return json.dumps(
        {
            "category": result.category,
            "confidence": result.confidence,
            "winning_score": result.winning_score,
            "runner_up_category": result.runner_up_category,
            "runner_up_score": result.runner_up_score,
            "matched_keywords": list(result.matched_keywords),
            "category_scores": result.category_scores or {},
            "notes": list(result.notes),
        },
        indent=2,
        sort_keys=True,
    )


def extract_text_and_classification(
    file_path: Path,
) -> tuple[str, bool, str, ClassificationResult, dict[str, str]]:
    """Extract text and classify it, OCRing PDFs when selectable text is inconclusive."""

    suffix = file_path.suffix.lower()
    debug_parts = {"selectable_text": "", "ocr_text": "", "combined_text": ""}

    if suffix == ".pdf":
        selectable_text = extract_pdf_selectable_text(file_path)
        debug_parts["selectable_text"] = selectable_text
        selectable_result = classify_text(selectable_text)
        debug_parts["selectable_classification"] = classification_debug_summary(selectable_result)
        if is_successful_pdf_classification(selectable_result):
            debug_parts["combined_text"] = selectable_text
            debug_parts["final_classification"] = classification_debug_summary(selectable_result)
            return (
                selectable_text,
                False,
                "Selectable PDF text classified successfully; OCR skipped.",
                selectable_result,
                debug_parts,
            )

        ocr_text = ocr_pdf(file_path)
        combined_text = "\n".join(part for part in (selectable_text, ocr_text) if part.strip())
        debug_parts["ocr_text"] = ocr_text
        debug_parts["combined_text"] = combined_text
        combined_result = classify_text(combined_text)
        result = better_classification(selectable_result, combined_result)
        debug_parts["combined_classification"] = classification_debug_summary(combined_result)
        debug_parts["final_classification"] = classification_debug_summary(result)
        return (
            combined_text or selectable_text or ocr_text,
            True,
            "Selectable PDF text was inconclusive; OCR used and combined with selectable text.",
            result,
            debug_parts,
        )

    ocr_text = ocr_image(file_path)
    debug_parts["ocr_text"] = ocr_text
    debug_parts["combined_text"] = ocr_text
    result = classify_text(ocr_text)
    debug_parts["final_classification"] = classification_debug_summary(result)
    return ocr_text, True, "Image OCR used.", result, debug_parts


def score_categories(text: str) -> tuple[dict[str, int], dict[str, list[str]], list[str]]:
    """Score every category and apply conservative anti-misclassification rules."""

    normalized_text = normalize_text(text)
    scores = {category: 0 for category in CATEGORY_FOLDERS if category != "NeedsReview"}
    matched_keywords = {category: [] for category in scores}
    notes: list[str] = []

    for rule in SCORING_RULES:
        if normalize_text(rule.keyword) in normalized_text:
            scores[rule.category] += rule.weight
            matched_keywords[rule.category].append(rule.keyword)

    for indicator in BROKERAGE_INDICATORS:
        if normalize_text(indicator) in normalized_text:
            scores["Brokerage_1099B"] += 4
            matched_keywords["Brokerage_1099B"].append(indicator)

    w2_structural_matches = [
        indicator
        for indicator in W2_STRUCTURAL_INDICATORS
        if normalize_text(indicator) in normalized_text
    ]
    if len(w2_structural_matches) >= W2_STRUCTURAL_MIN_MATCHES:
        scores["W2"] += W2_STRUCTURAL_SCORE
        matched_keywords["W2"].extend(w2_structural_matches)

    has_1099_nec = "1099-NEC" in normalized_text or "NONEMPLOYEE COMPENSATION" in normalized_text
    has_1099_misc = "1099-MISC" in normalized_text
    has_brokerage_indicator = any(
        keyword in normalized_text
        for keyword in ("CONSOLIDATED 1099", "1099-B", "BROKERAGE", "TAX INFORMATION STATEMENT")
    )
    has_1098_tuition = "1098-T" in normalized_text or "TUITION STATEMENT" in normalized_text

    if has_1099_nec:
        scores["W2"] = 0
        notes.append("1099-NEC indicator present; prevented W2 misclassification.")
    if has_1099_misc:
        scores["W2"] = 0
    if has_brokerage_indicator:
        scores["W2"] = 0
        if not has_1099_misc:
            scores["1099_MISC"] = 0
        notes.append("Brokerage indicators present; prevented W2/1099_MISC misclassification.")
    if has_1098_tuition:
        scores["W2"] = 0
        scores["1098_Mortgage"] = 0
        notes.append("1098-T indicator present; prevented mortgage 1098 misclassification.")

    if scores["Brokerage_1099B"] >= CATEGORY_THRESHOLDS["Brokerage_1099B"]:
        scores["1099_INT_DIV"] = min(scores["1099_INT_DIV"], scores["Brokerage_1099B"] - 1)

    return scores, matched_keywords, notes


def classify_text(text: str) -> ClassificationResult:
    """Classify text with conservative scoring. If unsure, do not guess."""

    normalized_text = normalize_text(text)
    scores, matched_by_category, notes = score_categories(normalized_text)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    winning_category, winning_score = ranked[0]
    runner_up_category, runner_up_score = ranked[1] if len(ranked) > 1 else ("", 0)
    if runner_up_score == 0:
        runner_up_category = ""
    categories_for_review = [
        category for category, score in scores.items() if score >= REVIEW_SCORE_THRESHOLD
    ]

    if len(normalized_text) < MIN_RELIABLE_TEXT_CHARS:
        notes.append("Low confidence; sent to NeedsReview.")
        return ClassificationResult(
            "NeedsReview",
            "Low",
            "",
            winning_score=0,
            runner_up_category=runner_up_category,
            runner_up_score=runner_up_score,
            category_scores=scores,
            notes=tuple(notes),
        )

    threshold = CATEGORY_THRESHOLDS[winning_category]
    if winning_score < threshold:
        if len(categories_for_review) > 1:
            notes.append(MULTIPLE_MATCH_NOTE)
        notes.append("Low confidence; sent to NeedsReview.")
        return ClassificationResult(
            "NeedsReview",
            "Low",
            "",
            matched_keywords=tuple(matched_by_category.get(winning_category, ())),
            winning_score=winning_score,
            runner_up_category=runner_up_category,
            runner_up_score=runner_up_score,
            category_scores=scores,
            notes=tuple(notes),
            multiple_categories_detected=len(categories_for_review) > 1,
        )

    multiple_categories_detected = len(categories_for_review) > 1
    if multiple_categories_detected:
        notes.append(MULTIPLE_MATCH_NOTE)

    close_runner_up = runner_up_score > 0 and winning_score - runner_up_score <= CLOSE_SCORE_DELTA
    confidence = "Medium" if multiple_categories_detected or close_runner_up else "High"
    matched_keywords = tuple(matched_by_category.get(winning_category, ()))

    return ClassificationResult(
        winning_category,
        confidence,
        "; ".join(matched_keywords),
        matched_keywords=matched_keywords,
        winning_score=winning_score,
        runner_up_category=runner_up_category,
        runner_up_score=runner_up_score,
        category_scores=scores,
        notes=tuple(notes),
        multiple_categories_detected=multiple_categories_detected,
    )


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



def write_extracted_text_debug(
    debug_folder: Path, file_path: Path, debug_parts: dict[str, str]
) -> Path:
    """Save extracted text and classification details for troubleshooting."""

    debug_filename = f"{safe_filename_part(file_path.stem)}_extracted_text.txt"
    debug_path = unique_destination_path(debug_folder, debug_filename)
    sections = [
        ("Original File", str(file_path)),
        ("Selectable Text", debug_parts.get("selectable_text", "")),
        ("OCR Text", debug_parts.get("ocr_text", "")),
        ("Combined Text", debug_parts.get("combined_text", "")),
        ("Selectable Classification", debug_parts.get("selectable_classification", "")),
        ("Combined Classification", debug_parts.get("combined_classification", "")),
        ("Final Classification", debug_parts.get("final_classification", "")),
    ]
    content = []
    for title, value in sections:
        content.append(f"===== {title} =====")
        content.append(value or "")
        content.append("")
    debug_path.write_text("\n".join(content), encoding="utf-8")
    return debug_path


def process_file(
    file_path: Path, output_folder: Path, move: bool, debug_folder: Path | None = None
) -> dict[str, object]:
    """Process one document and return an inventory row."""

    notes: list[str] = []
    ocr_used = False
    result = ClassificationResult("NeedsReview", "Low", "")
    destination_path: Path | None = None

    try:
        logging.info("Processing %s", file_path)
        text, ocr_used, extraction_note, result, debug_parts = extract_text_and_classification(
            file_path
        )
        notes.append(extraction_note)
        if not text.strip():
            notes.append("No readable text found.")
        notes.extend(note for note in result.notes if note not in notes)
        if debug_folder is not None:
            debug_path = write_extracted_text_debug(debug_folder, file_path, debug_parts)
            notes.append(f"Extracted text debug file: {debug_path}")

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
        "Winning Score": result.winning_score,
        "Runner Up Category": result.runner_up_category,
        "Runner Up Score": result.runner_up_score,
        "Matched Keywords": "; ".join(result.matched_keywords) or result.matched_keyword,
        "Category Scores": json.dumps(result.category_scores or {}, sort_keys=True),
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
        "Winning Score",
        "Runner Up Category",
        "Runner Up Score",
        "Matched Keywords",
        "Category Scores",
        "OCR Used",
        "Notes",
    ]
    import pandas as pd

    dataframe = pd.DataFrame(rows, columns=columns)
    dataframe.to_excel(inventory_path, index=False)
    return inventory_path


def run_sort(
    input_folder: Path,
    move: bool = False,
    save_extracted_text: bool = False,
    status_callback=None,
) -> dict[str, object]:
    """Sort one folder and return output paths plus the inventory rows.

    Shared by the CLI, the desktop app, and the tools registry so the run loop
    lives in exactly one place.
    """

    output_folder = setup_output_folders(input_folder)
    debug_folder = setup_debug_text_folder(output_folder, save_extracted_text)
    setup_logging(output_folder)
    logging.info("Starting tax document sort for %s", input_folder)
    logging.info("Default safety mode: %s", "MOVE" if move else "COPY")

    files = list(iter_supported_files(input_folder, output_folder))
    rows: list[dict[str, object]] = []
    for index, file_path in enumerate(files, start=1):
        if status_callback:
            status_callback(f"Processing {index} of {len(files)}: {file_path.name}")
        rows.append(process_file(file_path, output_folder, move, debug_folder))

    inventory_path = write_inventory(rows, output_folder)
    logging.info("Inventory written to %s", inventory_path)
    logging.info("Finished. Processed %s supported file(s).", len(rows))
    return {
        "tool": "sort",
        "output_folder": output_folder,
        "inventory_path": inventory_path,
        "log_path": output_folder / LOG_FILE_NAME,
        "debug_folder": debug_folder,
        "rows": rows,
        "total_files": len(rows),
        "summary": f"Sorted {len(rows)} supported file(s).",
    }


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

    result = run_sort(
        input_folder, move=args.move, save_extracted_text=args.save_extracted_text
    )
    print(f"Finished. Processed {result['total_files']} supported file(s).")
    print(f"Output folder: {result['output_folder']}")
    print(f"Inventory: {result['inventory_path']}")
    print(f"Log: {result['log_path']}")
    if result["debug_folder"] is not None:
        print(f"Extracted text debug folder: {result['debug_folder']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
