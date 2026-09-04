"""Local OCR document reader — Tesseract text into the shared text extractor.

A scan is read entirely on-machine: OCR the image to text, then run that text
through the same :class:`~satc.ingest.readers.text_anchor.TextAnchorReader` used
for digital text-layer PDFs. OCR output is noisy, so every value it produces is
flagged for review and never auto-confirms — the preparer confirms each one.
"""

from __future__ import annotations

from typing import Any, Callable

from satc.ingest.readers.base import ReadResult
from satc.ingest.readers.text_anchor import TextAnchorReader


class TesseractOcrReader:
    """Reads a scan/photo by OCR'ing it locally, then anchoring values in the text."""

    def __init__(self, config: dict[str, Any], *, page: int | None = None,
                 text_provider: Callable[[str], str] | None = None) -> None:
        self.config = config
        self.page = page
        self._text_provider = text_provider   # injectable for tests (no Tesseract needed)

    def _ocr(self, source: str) -> str:
        """The form's own pages, OCR'd -- not the IRS's instructions about it.

        THE SAME $200,000 ARRIVES THIS WAY. The text-layer reader was fixed to
        skip guidance pages; this one OCR'd every page and anchored over the
        concatenation, so a SCANNED eleven-page W-2 still put
        `medicare wages and tips ... above $200,000` in front of the anchor.
        It is less dangerous than the text path -- every OCR field is flagged
        for review below and none of them auto-confirm -- but a preparer being
        shown $200,000 of wages on a blank form and having to disbelieve it is
        not a working document reader.

        A scan has no text layer to test, so the pages are OCR'd first and
        judged on what comes out. That costs nothing extra: this rung was
        already reading every page.
        """
        if self._text_provider is not None:
            return self._text_provider(source)
        from pathlib import Path

        from satc.ingest.ocr import ocr_document_text, ocr_pdf_page_text
        from satc.ingest.pages import is_guidance

        path = Path(source)
        if self.page is not None or path.suffix.lower() != ".pdf":
            return ocr_document_text(source, self.page)

        try:
            from pypdf import PdfReader

            count = len(PdfReader(str(path)).pages)
        except Exception:      # noqa: BLE001 - unreadable page count => read it whole
            return ocr_document_text(source, None)

        texts = []
        for number in range(1, count + 1):
            try:
                texts.append(ocr_pdf_page_text(path, number))
            except Exception:  # noqa: BLE001 - one bad page is not the document
                continue
        form = [t for t in texts if not is_guidance(t)]
        return "\n".join(form or texts)

    def read(self, source: str) -> ReadResult:
        result = TextAnchorReader(self.config).read_text(self._ocr(str(source)))
        # Tesseract is deterministic -- no model, same page gives the same text
        # twice -- but noisy, so every field is still flagged for review. The two
        # are different statements and both are wanted: `deterministic` says it
        # can be reproduced, `uncertain_labels` says it should be checked.
        result.deterministic = True
        result.uncertain_labels = set(result.labeled_fields)   # OCR is noisy: review all
        result.backend = "TesseractOcrReader"
        return result
