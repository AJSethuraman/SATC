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
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from satc.config import load_classification, load_extraction_map

# Confidence ordering for any callers that want to compare.
CONF_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNCERTAIN": 0}

# Default scoring knobs for the text rung (overridable in classification.yaml).
DEFAULT_TEXT_THRESHOLD = 6      # minimum winning score to classify by text
DEFAULT_CLOSE_DELTA = 3         # winner within this of the runner-up => ambiguous (don't guess)

_DASHES = "‐‑‒–—−"
_QUOTES = "‘’ʼ`'"


def _normalize(text: str) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


def _normalize_text(text: str) -> str:
    """Lowercase, fold unicode dashes/quotes, and repair OCR-split form names.

    Scanners routinely drop the hyphen in form numbers ("1099 NEC", "W 2"); a
    keyword match would miss them otherwise. Keeps word boundaries (spaces) so
    multi-word phrases still match — unlike :func:`_normalize`.
    """
    t = str(text).lower()
    for d in _DASHES:
        t = t.replace(d, "-")
    for q in _QUOTES:
        t = t.replace(q, "")
    t = re.sub(r"\b1099\s+(nec|misc|int|div|r|b|g|k)\b", r"1099-\1", t)
    t = re.sub(r"\bw\s+2\b", "w-2", t)
    t = re.sub(r"\b1098\s+(t|e)\b", r"1098-\1", t)
    t = re.sub(r"\bssa\s+1099\b", "ssa-1099", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass(slots=True)
class DocType:
    """A known document type and the signals that identify it."""

    key: str | None                       # extraction-config key; None = filed-not-extracted
    label: str
    code: str
    filename_hints: list[str] = field(default_factory=list)
    keywords: list[tuple[str, int]] = field(default_factory=list)  # (normalized phrase, weight)
    threshold: int = 0                    # per-type override; 0 = use the classifier default
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

    def __init__(self, doc_types: list[DocType], *, has_key: bool | None = None,
                 text_threshold: int = DEFAULT_TEXT_THRESHOLD,
                 close_delta: int = DEFAULT_CLOSE_DELTA) -> None:
        self.doc_types = doc_types
        self.text_threshold = text_threshold
        self.close_delta = close_delta
        # "has_key" gates the cloud vision rung; default to the opt-in posture so a
        # stray API key in the environment never silently enables cloud calls.
        if has_key is None:
            from satc.settings import cloud_vision_enabled
            has_key = cloud_vision_enabled()
        self.has_key = has_key
        # Optional local-OCR text provider (path -> text); set by load_classifier
        # when Tesseract is available, so scans can be classified locally.
        self.ocr_text_provider: Any = None

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
                keywords=cls._parse_keywords(entry),
                threshold=int(entry.get("threshold", 0)),
                field_markers=markers,
            ))
        return cls(doc_types, has_key=has_key,
                   text_threshold=int(registry.get("text_threshold", DEFAULT_TEXT_THRESHOLD)),
                   close_delta=int(registry.get("close_delta", DEFAULT_CLOSE_DELTA)))

    @staticmethod
    def _parse_keywords(entry: dict[str, Any]) -> list[tuple[str, int]]:
        """Read weighted ``keywords`` ([phrase, weight] or {phrase: weight}).

        Falls back to legacy ``title_markers`` at a default weight so a type that
        only lists markers still classifies (each marker alone clears threshold).
        """
        out: list[tuple[str, int]] = []
        raw = entry.get("keywords")
        if isinstance(raw, dict):
            raw = list(raw.items())
        for item in raw or []:
            phrase, weight = (item[0], item[1]) if isinstance(item, (list, tuple)) else (item, DEFAULT_TEXT_THRESHOLD)
            out.append((_normalize_text(phrase), int(weight)))
        for marker in entry.get("title_markers", []):
            out.append((_normalize_text(marker), DEFAULT_TEXT_THRESHOLD))
        return out

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

        by_ocr = self._by_ocr(path)          # scans / images / text-less PDFs (local OCR)
        if by_ocr is not None:
            return by_ocr

        by_name = self._by_filename(path.name)
        if by_name is not None:
            return by_name

        if self.has_key:
            by_vision = self._by_vision(path)
            if by_vision is not None:
                return by_vision

        return UNCLASSIFIED

    def _by_ocr(self, path: Path) -> Classification | None:
        if self.ocr_text_provider is None:
            return None
        try:
            text = self.ocr_text_provider(str(path))
        except Exception:  # noqa: BLE001 - OCR unavailable / failed => fall through
            return None
        return self.classify_text(text, method="ocr")

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
        return self.classify_text(self._page_text(path), method="text")

    def classify_text(self, text: str, *, method: str = "text") -> Classification | None:
        """Weighted-keyword scoring over document text (shared by text + OCR rungs).

        Each type's keywords carry weights (strong identifiers high, generic words
        low) so no single weak word can classify alone. The winner must clear its
        threshold; if a runner-up is also strong or within ``close_delta``, the
        result is downgraded to MEDIUM — the pipeline feeds a human, so when it is
        unsure it says so rather than guessing.
        """
        if not text or not text.strip():
            return None
        norm = _normalize_text(text)
        scored: list[tuple[int, int, DocType]] = []
        for dt in self.doc_types:
            score = sum(w for phrase, w in dt.keywords if phrase and phrase in norm)
            if score > 0:
                scored.append((score, dt.threshold or self.text_threshold, dt))
        qualified = [(s, dt) for s, thr, dt in scored if s >= thr]
        if not qualified:
            return None
        qualified.sort(key=lambda x: x[0], reverse=True)
        best_score, best = qualified[0]
        # A runner-up that resolves to the *same* extraction key (e.g. the generic
        # "Schedule K-1" vs the specific 1120-S entry) agrees with the winner — it is
        # not a competing interpretation, so it never makes the result ambiguous.
        runner = next((s for s, dt in qualified[1:] if dt.key != best.key), 0)
        ambiguous = runner >= (best.threshold or self.text_threshold) or \
            (runner > 0 and best_score - runner <= self.close_delta)
        conf = "MEDIUM" if ambiguous else "HIGH"
        ev = f"text score {best_score}" + (f" (runner-up {runner})" if runner else "")
        return Classification(best.label, best.key, best.code, conf, method, ev)

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
    """Convenience builder used by intake and the sorter.

    Wires in the local-OCR text provider when Tesseract is available, so scanned
    documents can be classified on-machine (first page is enough for typing).
    """
    clf = DocumentClassifier.from_config(config_root, has_key=has_key)
    from satc.settings import ocr_enabled

    if ocr_enabled():
        from satc.ingest.ocr import ocr_document_text

        clf.ocr_text_provider = lambda p: ocr_document_text(p, 1)
    return clf
