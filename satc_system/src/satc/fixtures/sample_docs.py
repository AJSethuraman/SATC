"""Generate synthetic *fillable* tax-document PDFs for the Intake demo.

These are real PDFs with AcroForm fields whose names match the extraction-config
field paths, so the free :class:`~satc.ingest.readers.pdf_form.PdfFormReader` reads
them with no API key. Values are obviously synthetic; SSN/EIN use invalid ranges
and are masked downstream.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _fillable(path: Path, title: str, subtitle: str, fields: list[tuple[str, str, str]]) -> None:
    """Write a titled PDF with a labeled text field per (label, field_name, value)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFillColorRGB(0.04, 0.12, 0.23)
    c.rect(0, h - 70, w, 70, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(54, h - 42, title)
    c.setFont("Helvetica", 9)
    c.drawString(54, h - 58, subtitle)

    form = c.acroForm
    y = h - 110
    c.setFillColorRGB(0.1, 0.1, 0.1)
    for label, name, value in fields:
        c.setFont("Helvetica", 10)
        c.drawString(56, y + 3, label)
        form.textfield(name=name, value=value, x=300, y=y - 4, width=230, height=18,
                       borderWidth=1, borderColor=None, fillColor=None, fontSize=10)
        y -= 30
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(54, 40, "Synthetic document for demonstration — not a real taxpayer.")
    c.save()


def write_sample_w2(path: Path) -> None:
    _fillable(path, "Form W-2  Wage and Tax Statement", "Tax year 2024 · synthetic", [
        ("Box 1 — Wages, tips, other compensation", "w2_box1_wages", "98000.00"),
        ("Box 2 — Federal income tax withheld", "w2_box2_fed_wh", "12500.00"),
        ("Box 3 — Social Security wages", "w2_box3_ss_wages", "98000.00"),
        ("Box 15 — State", "w2_box15_state", "OH"),
        ("Box 17 — State income tax", "w2_box17_state_wh", "3200.00"),
        ("Employer name", "w2_employer_name", "Buckeye Manufacturing LLC"),
        ("Employer EIN", "w2_employer_ein", "31-0009999"),
        ("Employee SSN", "w2_employee_ssn", "400-55-1234"),
    ])


def write_sample_1099int(path: Path) -> None:
    _fillable(path, "Form 1099-INT  Interest Income", "Tax year 2024 · synthetic", [
        ("Box 1 — Interest income", "int_box1_interest", "1200.00"),
        ("Box 4 — Federal income tax withheld", "int_box4_fed_wh", "0.00"),
        ("Payer name", "int_payer_name", "Heartland Bank"),
        ("Payer TIN", "int_payer_tin", "34-0001111"),
    ])


def write_plain_pdf(path: Path, title: str) -> None:
    """A non-fillable PDF (e.g., an engagement letter) — Intake files it, not extracts it."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(54, h - 80, title)
    c.setFont("Helvetica", 10)
    c.drawString(54, h - 110, "This is a scanned/flat document with no form fields.")
    c.save()


def _draw_text_page(c, lines: list[str]) -> None:
    """Draw plain text lines on the current canvas page (no form fields)."""
    w, h = letter
    y = h - 70
    for line in lines:
        c.setFont("Helvetica-Bold" if line and line[0] == "#" else "Helvetica", 11)
        c.drawString(54, y, line.lstrip("# "))
        y -= 22


def write_text_form(path: Path, lines: list[str]) -> None:
    """A single-page *text-layer* PDF (no AcroForm) — read by the free text reader."""
    c = canvas.Canvas(str(path), pagesize=letter)
    _draw_text_page(c, lines)
    c.save()


# Canonical text-layer page bodies for the synthetic forms (label  value).
TEXT_W2 = [
    "# Form W-2  Wage and Tax Statement  2024",
    "Wages, tips, other compensation      98000.00",
    "Federal income tax withheld          12500.00",
    "Social security wages                98000.00",
    "Employer name      Buckeye Manufacturing LLC",
    "Employer EIN       31-0009999",
    "Employee SSN       400-55-1234",
]
TEXT_1099INT = [
    "# Form 1099-INT  Interest Income  2024",
    "Interest income     1200.00",
    "Payer name          Heartland Bank",
    "Payer TIN           34-0001111",
]
TEXT_ENGAGEMENT = [
    "# SATC Engagement Letter",
    "Terms of engagement for the 2024 tax year.",
]


def write_combined_pdf(path: Path, pages: list[list[str]]) -> None:
    """A multi-page PDF where each page is a different form (text layer)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for i, lines in enumerate(pages):
        if i:
            c.showPage()
        _draw_text_page(c, lines)
    c.save()


def create_sample_folder(directory: str | Path) -> Path:
    """Create a folder of synthetic client documents and return its path."""
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    write_sample_w2(d / "W2_Buckeye_Manufacturing.pdf")
    write_sample_1099int(d / "1099INT_Heartland_Bank.pdf")
    write_plain_pdf(d / "Engagement_Letter.pdf", "SATC Engagement Letter — Maplewood 2024")
    return d
