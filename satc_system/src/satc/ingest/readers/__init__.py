"""Document readers: raw document -> labeled fields (front end of extraction).

Pluggable backends feed the same MapExtractor + confirmation gate:
  * PdfFormReader      — free, exact, for fillable PDFs
  * VisionDocumentReader — Claude vision, for scans/photos/any layout
"""

from __future__ import annotations

from satc.ingest.readers.base import DocumentReader, ReadResult
from satc.ingest.readers.ocr import TesseractOcrReader
from satc.ingest.readers.ollama import OllamaVisionReader
from satc.ingest.readers.pdf_form import PdfFormReader
from satc.ingest.readers.text_anchor import TextAnchorReader
from satc.ingest.readers.vision import VisionDocumentReader

__all__ = ["DocumentReader", "ReadResult", "PdfFormReader", "TextAnchorReader",
           "TesseractOcrReader", "OllamaVisionReader", "VisionDocumentReader"]
