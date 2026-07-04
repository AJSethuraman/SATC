"""Free label-anchored text extractor for text-layer PDFs that aren't fillable.

Many "PDFs" are not AcroForm-fillable but carry a real text layer (consolidated
1099s, software-printed forms, some payroll W-2s). Rather than pay the vision
path, this finds each field's printed label in the text and reads the value next
to it:

  * money  — prefer a strict comma/cents dollar amount; fall back to a whole-dollar
    integer that is **not** a 4-digit year and **not** part of an EIN/SSN.
  * tin    — an exact ``NN-NNNNNNN`` (EIN) or ``NNN-NN-NNNN`` (SSN) pattern.
  * text   — the rest of the label's line (employer/payer name, state).

It is heuristic, so anything not matched by a strict money/TIN pattern is flagged
uncertain (staged LOW) and never auto-confirms — the preparer still confirms. The
output is plain labeled fields, so it flows through the same MapExtractor +
confirmation gate as every other reader (and SSN/EIN are masked there).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from satc.ingest.readers.base import ReadResult

# Strict money: 1,234 or 1,234.56 or 1234.56 (comma groups or cents required).
MONEY = re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+\.\d{2})")
# Whole-dollar fallback: 3+ digits that are not a 19xx/20xx year and not glued to a dash.
WHOLE_DOLLAR = re.compile(r"(?<![\d-])(?!(?:19|20)\d{2}(?![\d-]))\d{3,}(?![\d-])")
EIN = re.compile(r"\b\d{2}-\d{7}\b")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_BOX_PREFIX = re.compile(r"^box\s*\w+\s*[-–—]\s*", re.IGNORECASE)


def _clean_amount(text: str) -> str:
    return text.replace(",", "").replace("$", "").strip()


def _anchors(spec: dict[str, Any]) -> list[str]:
    """Searchable label phrases for a field, most distinctive (longest) first."""
    label = str(spec.get("label", ""))
    cands = {label.lower(), _BOX_PREFIX.sub("", label).lower().strip()}
    cands.update(a.lower() for a in spec.get("aliases", []))
    return sorted((c for c in cands if c), key=len, reverse=True)


def _anchor_ends(low: str, anchor: str):
    """Yield end-offsets where ``anchor`` occurs in ``low``.

    A short single word (e.g. "state") must match a whole word, so it never fires
    inside a longer one ("State" vs "Statement"). A multi-word or longer phrase
    (e.g. the truncated label "...other comp" that prefixes "compensation") keeps
    plain substring matching.
    """
    if " " in anchor or "," in anchor or len(anchor) > 6:
        start = 0
        while (i := low.find(anchor, start)) >= 0:
            yield i + len(anchor)
            start = i + 1
    else:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(anchor) + r"(?![a-z0-9])", low):
            yield m.end()


class TextAnchorReader:
    """Reads box values from a PDF's text layer by anchoring on each field label."""

    def __init__(self, config: dict[str, Any], *, page: int | None = None, window: int = 64) -> None:
        self.doc_type = config.get("doc_type", "document")
        self.field_specs = config.get("fields", [])
        self.page = page
        self.window = window

    def read(self, source: str) -> ReadResult:
        return self.read_text(self._page_text(Path(source)))

    def read_text(self, text: str) -> ReadResult:
        """Core extraction over already-read text (unit-testable, no PDF)."""
        low = (text or "").lower()
        labeled: dict[str, str] = {}
        uncertain: set[str] = set()
        for spec in self.field_specs:
            value, confident = self._extract(spec, text, low)
            if not value:
                continue
            label = spec.get("label", spec["field_path"])
            labeled[label] = value
            if not confident:
                uncertain.add(label)
        return ReadResult(labeled_fields=labeled, uncertain_labels=uncertain,
                          backend="TextAnchorReader")

    def _extract(self, spec: dict[str, Any], text: str, low: str) -> tuple[str, bool]:
        kind = "money" if spec.get("money") else ("tin" if spec.get("sensitive") else "text")
        for anchor in _anchors(spec):
            for end in _anchor_ends(low, anchor):
                seg = text[end: end + self.window]
                if kind == "tin":
                    m = EIN.search(seg) or SSN.search(seg)
                    if m:
                        return m.group(0), True
                elif kind == "money":
                    m = MONEY.search(seg)
                    if m:
                        return _clean_amount(m.group(1)), True
                    m = WHOLE_DOLLAR.search(seg)
                    if m:
                        return _clean_amount(m.group(0)), False    # fallback => review
                else:  # free text — the remainder of the label's line
                    line = seg.splitlines()[0] if seg.strip() else ""
                    value = re.split(r"\s{2,}|\t", line.strip(" :-\t"))[0].strip()
                    if value:
                        return value, False
        return "", False

    def _page_text(self, path: Path) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = reader.pages if self.page is None else [reader.pages[self.page - 1]]
            return "\n".join((p.extract_text() or "") for p in pages)
        except Exception:  # noqa: BLE001 - no text layer / unreadable => empty
            return ""
