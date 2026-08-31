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
    # Was this read produced WITHOUT a model? Form fields, a text-layer regex and
    # Tesseract are deterministic: the same document gives the same answer twice.
    # A vision model is not, however sure it sounds.
    #
    # DEFAULT FALSE ON PURPOSE. A reader written next year that never thinks
    # about this is treated as a model -- forgetting is safe rather than
    # dangerous, which is the only way round a default like this can go.
    deterministic: bool = False

    def confidence_map(self) -> dict[str, Confidence]:
        """Per-label base confidence, and the gate auto-confirms only HIGH.

        A NON-DETERMINISTIC READ IS NEVER HIGH, whatever it says about itself.

        The firm, 31 Aug 2026: *"I really want it deterministic first."* This is
        the half of that which lives below the ladder. `VisionDocumentReader`
        asked the model to name its own uncertain fields and trusted the rest --
        so a field the model did not flag arrived HIGH and `auto_confirm_high`
        wrote a model's reading of a wage box into the workpaper with nobody
        looking at it.

        A model's self-assessment is not evidence. It is the same faculty that
        produced the answer, asked whether it is happy with it. Determinism is a
        property of the READER; it is not a judgement the output gets to make
        about itself.
        """
        if not self.deterministic:
            return {label: "LOW" for label in self.labeled_fields}
        return {label: ("LOW" if label in self.uncertain_labels else "HIGH")
                for label in self.labeled_fields}


class DocumentReader(Protocol):
    """A reader turns a source document into a :class:`ReadResult`."""

    def read(self, source: str) -> ReadResult:  # pragma: no cover - protocol
        ...
