"""Local OCR (Tesseract) — turn a scan/photo into text, fully on this machine.

OCR is just another *text source*: once a scanned page is OCR'd, the same local
keyword classifier and label-anchored extractor read it — no cloud, no model
weights, nothing leaves the machine. Tesseract + Pillow do the work; PDF pages are
rasterized with poppler's ``pdftoppm`` (already used for vision rasterization).

Everything degrades gracefully: if Tesseract isn't installed, :func:`tesseract_available`
returns False and callers fall through to the next rung.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}


def tesseract_available() -> bool:
    """True if both the Tesseract binary and the pytesseract bindings are present."""
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def _ocr_image_file(path: str | Path) -> str:
    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(str(path)))


def ocr_pdf_page_text(path: str | Path, page: int = 1, *, dpi: int = 300) -> str:
    """Rasterize one PDF page with pdftoppm and OCR it to text."""
    with tempfile.TemporaryDirectory() as tmp:
        prefix = str(Path(tmp) / "pg")
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
                        str(path), prefix], check=True, capture_output=True)
        produced = sorted(Path(tmp).glob("pg*.png"))
        return _ocr_image_file(produced[0]) if produced else ""


def ocr_document_text(path: str | Path, page: int | None = None) -> str:
    """OCR a document to text. For PDFs, a single ``page`` or all pages if None."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        if page is not None:
            return ocr_pdf_page_text(p, page)
        try:
            from pypdf import PdfReader

            n = len(PdfReader(str(p)).pages)
        except Exception:  # noqa: BLE001
            n = 1
        return "\n".join(ocr_pdf_page_text(p, i) for i in range(1, n + 1))
    return _ocr_image_file(p)
