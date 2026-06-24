"""Document readers — the front end that turns a raw document into labeled fields.

A reader's only job is to get from a raw artifact (a fillable PDF, a scan, a phone
photo) to ``{source_label: value}`` pairs. Those pairs then flow through the
existing :class:`~satc.ingest.MapExtractor` and the staging/confirmation gate, so
every reader shares the same conservative, human-confirmed downstream path.

Two backends are provided:
  * :class:`~satc.ingest.readers.pdf_form.PdfFormReader` — free, exact, for
    genuine fillable PDFs (many broker/payroll 1099s and W-2s).
  * :class:`~satc.ingest.readers.vision.VisionDocumentReader` — Claude vision, for
    scans/photos/any layout (needs an Anthropic API key; small per-document cost).

A reader may also flag fields it is unsure about; those are staged at lower
confidence so they never auto-confirm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from satc.models.provenance import Confidence


@dataclass(slots=True)
class ReadResult:
    """What a reader produces: labeled values + the fields it was unsure about."""

    labeled_fields: dict[str, str] = field(default_factory=dict)
    uncertain_labels: set[str] = field(default_factory=set)
    backend: str = ""

    def confidence_map(self) -> dict[str, Confidence]:
        """Per-label base confidence: LOW for anything the reader flagged uncertain."""
        return {label: ("LOW" if label in self.uncertain_labels else "HIGH")
                for label in self.labeled_fields}


class DocumentReader(Protocol):
    """A reader turns a source document into a :class:`ReadResult`."""

    def read(self, source: str) -> ReadResult:  # pragma: no cover - protocol
        ...
