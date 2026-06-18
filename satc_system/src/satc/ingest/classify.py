"""Content-based document classification — decide what a file *is* by reading it.

A filename sorter breaks the moment a client sends ``IMG_4471.pdf``. This reads the
document instead, preferring cheap and exact signals before any paid OCR:

    1. PDF form fields  — a fillable form's AcroForm field names are its
       fingerprint (``w2_box1_wages`` -> W-2). Free, exact.
    2. Embedded PDF text — most "PDFs" carry a real text layer; the form's printed
       title ("Wage and Tax Statement") names it. Free, no OCR.
    3. Filename hint     — weak; used only when the content is silent.
    4. Vision / OCR      — only true scans with no text layer reach here; needs an
       Anthropic API key and costs a little per document.

The result feeds the same intake/staging pipeline, so classification only picks
*which* extraction map to use — it never writes a value on its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from satc.config import load_classification, load_extraction_map

# Confidence ordering for any callers that want to compare.
CONF_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNCERTAIN": 0}


def _normalize(text: str) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


@dataclass(slots=True)
class DocType:
    """A known document type and the signals that identify it."""

    key: str | None                       # extraction-config key; None = filed-not-extracted
    label: str
    code: str
    filename_hints: list[str] = field(default_factory=list)
    title_markers: list[str] = field(default_factory=list)
    field_markers: set[str] = field(default_factory=set)  # normalized AcroForm field names

    @property
    def extractable(self) -> bool:
        return self.key is not None


@dataclass(slots=True)
class Classification:
    """The classifier's verdict for one file."""

    label: str
    key: str | None
    code: str
    confidence: str          # HIGH / MEDIUM / LOW / UNCERTAIN
    method: str              # "form fields" / "text" / "filename" / "vision" / "unclassified"
    evidence: str = ""

    @property
    def extractable(self) -> bool:
        return self.key is not None

    @property
    def classified(self) -> bool:
        return self.method != "unclassified"


# A neutral verdict for files nothing matched.
UNCLASSIFIED = Classification(
    label="Unclassified", key=None, code="DOC",
    confidence="UNCERTAIN", method="unclassified",
    evidence="no form fields, text, filename hint, or vision match",
)


class DocumentClassifier:
    """Classifies a file by reading it, cheapest-and-most-exact signal first."""

    def __init__(self, doc_types: list[DocType], *, has_key: bool | None = None) -> None:
        self.doc_types = doc_types
        self.has_key = (bool(os.environ.get("ANTHROPIC_API_KEY"))
                        if has_key is None else has_key)

    # -- construction -----------------------------------------------------
    @classmethod
    def from_config(cls, config_root: Path | None = None, *, has_key: bool | None = None
                    ) -> DocumentClassifier:
        registry = load_classification(config_root)
        doc_types: list[DocType] = []
        cache: dict[str, set[str]] = {}
        for entry in registry.get("doc_types", []):
            key = entry.get("key")
            markers = cls._field_markers_for(key, config_root, cache) if key else set()
            doc_types.append(DocType(
                key=key,
                label=entry["label"],
                code=entry.get("code", entry["label"]),
                filename_hints=[h.lower() for h in entry.get("filename_hints", [])],
                title_markers=[m.lower() for m in entry.get("title_markers", [])],
                field_markers=markers,
            ))
        return cls(doc_types, has_key=has_key)

    @staticmethod
    def _field_markers_for(key: str, config_root: Path | None,
                           cache: dict[str, set[str]]) -> set[str]:
        """Normalized AcroForm fingerprints from an extraction config's field paths."""
        if key in cache:
            return cache[key]
        markers: set[str] = set()
        try:
            cfg = load_extraction_map(key, config_root)
            for spec in cfg.get("fields", []):
                for candidate in (spec.get("field_path"), spec.get("pdf_field")):
                    if candidate:
                        markers.add(_normalize(candidate))
        except Exception:  # noqa: BLE001 - a missing map just means no field signal
            markers = set()
        cache[key] = markers
        return markers

    # -- classify ---------------------------------------------------------
    def classify_path(self, source: str | Path) -> Classification:
        path = Path(source)
        is_pdf = path.suffix.lower() == ".pdf"

        if is_pdf:
            by_fields = self._by_form_fields(path)
            if by_fields is not None:
                return by_fields
            by_text = self._by_text(path)
            if by_text is not None:
                return by_text

        by_name = self._by_filename(path.name)
        if by_name is not None:
            return by_name

        if self.has_key:
            by_vision = self._by_vision(path)
            if by_vision is not None:
                return by_vision

        return UNCLASSIFIED

    # -- individual signals ----------------------------------------------
    def _by_form_fields(self, path: Path) -> Classification | None:
        names = self._acroform_names(path)
        if not names:
            return None
        best, best_score = None, 0
        for dt in self.doc_types:
            if not dt.field_markers:
                continue
            score = len(names & dt.field_markers)
            if score > best_score:
                best, best_score = dt, score
        if best is not None and best_score >= 2:
            return Classification(best.label, best.key, best.code, "HIGH", "form fields",
                                  f"matched {best_score} fillable form fields")
        return None

    def _by_text(self, path: Path) -> Classification | None:
        text = self._page_text(path)
        if not text:
            return None
        low = text.lower()
        best, best_score, hit = None, 0, ""
        for dt in self.doc_types:
            for marker in dt.title_markers:
                if marker in low:
                    # First (most specific) marker per type; keep the strongest type.
                    score = sum(1 for m in dt.title_markers if m in low)
                    if score > best_score:
                        best, best_score, hit = dt, score, marker
                    break
        if best is not None:
            conf = "HIGH" if best_score >= 2 else "MEDIUM"
            return Classification(best.label, best.key, best.code, conf, "text",
                                  f"page text contains “{hit}”")
        return None

    def _by_filename(self, name: str) -> Classification | None:
        low = name.lower()
        for dt in self.doc_types:
            for hint in dt.filename_hints:
                if hint in low:
                    return Classification(dt.label, dt.key, dt.code, "LOW", "filename",
                                          f"file name contains “{hint}”")
        return None

    def _by_vision(self, path: Path) -> Classification | None:  # pragma: no cover - needs a key
        """Last resort: ask the vision model to name the form (true scans only)."""
        try:
            from satc.ingest.readers.vision import VisionDocumentReader

            labels = [dt.label for dt in self.doc_types]
            choice = VisionDocumentReader.classify_form(str(path), labels)
        except Exception:  # noqa: BLE001 - never let a model error crash sorting
            return None
        for dt in self.doc_types:
            if dt.label == choice:
                return Classification(dt.label, dt.key, dt.code, "MEDIUM", "vision",
                                      "identified by vision model")
        return None

    # -- low-level readers (guarded; never raise) ------------------------
    @staticmethod
    def _acroform_names(path: Path) -> set[str]:
        try:
            from pypdf import PdfReader

            fields = PdfReader(str(path)).get_fields() or {}
            return {_normalize(name) for name in fields}
        except Exception:  # noqa: BLE001 - not a fillable PDF / pypdf unavailable
            return set()

    @staticmethod
    def _page_text(path: Path) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            if not reader.pages:
                return ""
            return reader.pages[0].extract_text() or ""
        except Exception:  # noqa: BLE001 - image/scan with no text layer
            return ""


def load_classifier(config_root: Path | None = None, *, has_key: bool | None = None
                    ) -> DocumentClassifier:
    """Convenience builder used by intake and the sorter."""
    return DocumentClassifier.from_config(config_root, has_key=has_key)
