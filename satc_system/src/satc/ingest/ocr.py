"""Local OCR (Tesseract) — turn a scan/photo into text, fully on this machine.

OCR is just another *text source*: once a scanned page is OCR'd, the same local
keyword classifier and label-anchored extractor read it — no cloud, no model
weights, nothing leaves the machine. Tesseract + Pillow do the work; PDF pages are
rasterized with **pymupdf** (already bundled), so there is no external poppler
dependency.

Tesseract detection resolves the binary in this order: the ``SATC_TESSERACT``
override, then ``PATH``, then the default Windows install location (the
UB-Mannheim installer does not add itself to ``PATH``). Everything degrades
gracefully: if Tesseract can't be found, OCR functions return ``""`` and callers
fall through to the next reader rung.
"""

from __future__ import annotations

import io
import os
import shutil
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}

_WINDOWS_TESSERACT = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _tesseract_cmd() -> str | None:
    """Locate the tesseract binary (override -> PATH -> default Windows path)."""
    override = os.environ.get("SATC_TESSERACT")
    if override and Path(override).exists():
        return override
    found = shutil.which("tesseract")
    if found:
        return found
    for cand in _WINDOWS_TESSERACT:
        if Path(cand).exists():
            return cand
    return None


def _ensure_tesseract():
    """Return the pytesseract module with ``tesseract_cmd`` resolved, or None."""
    cmd = _tesseract_cmd()
    if cmd is None:
        return None
    try:
        import pytesseract
    except Exception:  # noqa: BLE001
        return None
    pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract


def tesseract_available() -> bool:
    """True if the Tesseract binary (resolved) and pytesseract bindings are present."""
    return _ensure_tesseract() is not None


def _ocr_image_file(path: str | Path) -> str:
    pt = _ensure_tesseract()
    if pt is None:
        return ""
    from PIL import Image

    return pt.image_to_string(Image.open(str(path)))


def _render_pdf_page_png(path: str | Path, page: int, dpi: int) -> bytes:
    """Rasterize a single (1-indexed) PDF page to PNG bytes with pymupdf."""
    import fitz  # pymupdf

    doc = fitz.open(str(path))
    try:
        pix = doc.load_page(page - 1).get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()


def ocr_pdf_page_text(path: str | Path, page: int = 1, *, dpi: int = 300) -> str:
    """Rasterize one PDF page (pymupdf) and OCR it — no external poppler needed."""
    pt = _ensure_tesseract()
    if pt is None:
        return ""
    from PIL import Image

    png = _render_pdf_page_png(path, page, dpi)
    return pt.image_to_string(Image.open(io.BytesIO(png)))


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
