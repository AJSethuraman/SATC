"""Provenance: every value in the system traces to where it came from.

A core build standard is that no figure is trusted without a source. Each value
the system stages, computes, or stores carries a :class:`Provenance` record so a
preparer can answer "where did this number come from?" — a confirmed source
document, a prior-year carryforward, Drake output, a tax-law parameter, or a
preparer's own entry.

These dataclasses map 1:1 to SQL columns/tables (no nesting that can't be
flattened), so the model ports to a database with no restructuring.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from satc.models.actor import Actor

# Where a value originated. Drives trust: SOURCE_DOC and PRIOR_YEAR_CARRYFORWARD
# are the only origins allowed to populate intake fields. DRAKE_OUTPUT is for
# reconciliation/data-mart seeding only — never to populate a workpaper input.
SourceKind = Literal[
    "SOURCE_DOC",                 # an extracted, confirmed source document (W-2, 1099, K-1...)
    "PRIOR_YEAR_CARRYFORWARD",    # carried forward from the data mart
    "DRAKE_OUTPUT",               # parsed from the Drake preparer-set PDF (reconcile/seed only)
    "PREPARER_ENTRY",             # keyed/confirmed by the preparer
    "COMPUTED",                   # a cross-check / formula derived in the workpaper
    "TAX_LAW_PARAM",              # a value from the dated tax-law crosswalk
]

# Conservative confidence on an *extracted* value. Anything below HIGH must be
# reviewed at the confirmation gate before it is trusted.
Confidence = Literal["HIGH", "MEDIUM", "LOW", "UNCERTAIN"]


@dataclass(slots=True)
class SourceRef:
    """A pointer to where a value lives — never the sensitive content itself.

    Documents are referenced by SharePoint link + ``document_id``, never embedded.
    For Drake preparer-set parsing we key off the stable *worksheet title* (not
    coordinates). For tax-law parameters we record the citation.
    """

    document_id: str | None = None        # FK into the document & communication repository
    sharepoint_link: str | None = None    # external link; the file stays in SharePoint
    page: int | None = None               # 1-based page within a source PDF
    worksheet_title: str | None = None     # e.g. "Filing Instructions", "Carryover Worksheet"
    field_label: str | None = None        # the labeled field on the document
    citation: str | None = None           # tax-law source (Rev. Proc., state code, URL)


@dataclass(slots=True)
class Provenance:
    """The full provenance attached to a single value."""

    source_kind: SourceKind
    confidence: Confidence = "HIGH"
    source_ref: SourceRef | None = None
    note: str = ""
    extractor: str = ""                   # which extractor/parser produced it
    extracted_at: datetime | None = None
    produced_by: Actor | None = None
    """WHO produced this value — and the taint follows the value, not the reader.

    A value a model produced stays model-produced through OCR correction,
    normalisation, and re-extraction: see :meth:`derive`. Defining "is this
    model output?" on the *reader that last touched it* is how a laundered
    value reaches the confirmation gate looking deterministic.
    """

    @property
    def is_model_produced(self) -> bool:
        return self.produced_by is not None and self.produced_by.is_model

    def derive(self, *, by: Actor, note: str = "",
               confidence: Confidence | None = None) -> Provenance:
        """A new provenance for a value derived from this one.

        **Sticky and transitive.** If either this value or the deriving actor is
        a model, the result is model-produced. A deterministic post-processor
        running over model output does not launder it back to clean; the only
        thing that turns a proposal into a fact is a human at the gate.
        """
        # If this value was already model-produced, the derived value keeps that
        # model as its producer no matter who derived it — deterministic
        # post-processing cannot launder model output clean. Otherwise the
        # deriving actor becomes the producer, so a model deriving from a clean
        # value taints the result.
        produced_by = self.produced_by if self.is_model_produced else by
        return Provenance(
            source_kind=self.source_kind,
            confidence=confidence or self.confidence,
            source_ref=self.source_ref,
            note=" ".join(x for x in (self.note, note) if x),
            extractor=self.extractor,
            extracted_at=self.extracted_at,
            produced_by=produced_by)

    def short_source(self) -> str:
        """A compact human label for a tie-out column (no PII)."""
        ref = self.source_ref
        if self.source_kind == "PRIOR_YEAR_CARRYFORWARD":
            return "Prior-year carryforward"
        if self.source_kind == "TAX_LAW_PARAM":
            return f"Tax law: {ref.citation}" if ref and ref.citation else "Tax law parameter"
        if self.source_kind == "DRAKE_OUTPUT":
            title = ref.worksheet_title if ref else None
            return f"Drake: {title}" if title else "Drake output"
        if self.source_kind == "COMPUTED":
            return "Computed (workpaper)"
        if self.source_kind == "PREPARER_ENTRY":
            return "Preparer entry"
        # SOURCE_DOC
        if ref and ref.document_id:
            page = f" p.{ref.page}" if ref.page else ""
            return f"Doc {ref.document_id}{page}"
        return "Source document"
