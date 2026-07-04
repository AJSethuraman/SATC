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
        if self._text_provider is not None:
            return self._text_provider(source)
        from satc.ingest.ocr import ocr_document_text

        return ocr_document_text(source, self.page)

    def read(self, source: str) -> ReadResult:
        result = TextAnchorReader(self.config).read_text(self._ocr(str(source)))
        result.uncertain_labels = set(result.labeled_fields)   # OCR is noisy: review all
        result.backend = "TesseractOcrReader"
        return result
