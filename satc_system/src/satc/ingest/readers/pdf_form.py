"""PDF fillable-form reader (free, exact) for genuine AcroForm documents.

Many broker/payroll 1099s and some W-2s are fillable PDFs whose field values can
be read exactly — no OCR, no model, no cost. This reader pulls those values and
maps each AcroForm field name to a config label (by exact ``pdf_field`` match or by
normalized label/alias). Anything it can't confidently map is left for the vision
backend or manual entry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from satc.ingest.readers.base import ReadResult


def _normalize(text: str) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


class PdfFormReader:
    """Reads fillable-PDF form fields into labeled values."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.doc_type = config.get("doc_type", "document")
        self.field_specs = config.get("fields", [])
        # Map every recognizable key (explicit pdf_field, label, aliases, field_path)
        # to the spec's display label.
        self._index: dict[str, str] = {}
        for spec in self.field_specs:
            label = spec.get("label", spec["field_path"])
            keys = [spec.get("pdf_field", ""), label, spec["field_path"], *spec.get("aliases", [])]
            for key in keys:
                if key:
                    self._index[_normalize(key)] = label

    def read_fields(self, form_fields: dict[str, Any]) -> ReadResult:
        """Map a ``{pdf_field_name: value}`` dict to labeled fields (testable core)."""
        labeled: dict[str, str] = {}
        for raw_name, value in form_fields.items():
            label = self._index.get(_normalize(raw_name))
            if label is None or value is None or str(value).strip() == "":
                continue
            labeled[label] = str(value).strip()
        return ReadResult(labeled_fields=labeled, backend="PdfFormReader")

    def read(self, source: str) -> ReadResult:
        from pypdf import PdfReader  # imported lazily

        reader = PdfReader(str(Path(source)))
        fields = reader.get_fields() or {}
        form_fields = {name: (f.get("/V") if hasattr(f, "get") else f) for name, f in fields.items()}
        return self.read_fields(form_fields)
