"""Staging / confirmation gate records.

The ingestion pipeline never writes extracted values straight into the workpaper.
Every extracted field lands here first as a :class:`StagedField` carrying its
provenance and confidence. The preparer confirms (or corrects) each one at the
confirmation gate; only ``CONFIRMED`` values are promoted into the line sheets and
the data mart. This is the human-in-the-loop control the whole system is built
around.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from satc.models.provenance import Provenance

StagingStatus = Literal["STAGED", "NEEDS_REVIEW", "CONFIRMED", "REJECTED"]

# Document types the repository / extractors recognize.
DocType = Literal[
    "W-2", "1099-INT", "1099-DIV", "1099-B", "1099-R", "1099-NEC", "1099-MISC",
    "1099-G", "SSA-1099", "1098", "1098-T", "1098-E", "K-1-1120S", "K-1-1065",
    "PRIOR-YEAR-1040", "PRIOR-YEAR-1120S", "PRIOR-YEAR-1065", "PRIOR-YEAR-1120",
    "ORGANIZER", "OTHER",
]


@dataclass(slots=True)
class StagedField:
    """One extracted field awaiting preparer confirmation.

    ``value_text`` always holds the verbatim extracted token; ``value_amount`` is
    set only when the field is monetary and parsed cleanly. The gate never
    *guesses* an amount — an unparseable money field stays ``NEEDS_REVIEW`` with a
    blank ``value_amount`` and a note.
    """

    field_id: str
    document_id: str
    client_id: str
    tax_year: int
    field_path: str               # canonical destination, e.g. "w2.box1_wages"
    label: str
    value_text: str
    provenance: Provenance
    value_amount: Decimal | None = None
    status: StagingStatus = "STAGED"
    note: str = ""
    confirmed_value_text: str = ""
    confirmed_value_amount: Decimal | None = None
    confirmed_by: str = ""
    confirmed_at: datetime | None = None

    @property
    def is_trusted(self) -> bool:
        return self.status == "CONFIRMED"

    def effective_text(self) -> str:
        return self.confirmed_value_text if self.is_trusted and self.confirmed_value_text else self.value_text

    def effective_amount(self) -> Decimal | None:
        if self.is_trusted and self.confirmed_value_amount is not None:
            return self.confirmed_value_amount
        return self.value_amount


@dataclass(slots=True)
class StagedDocument:
    """All staged fields extracted from one source document.

    ``source_path`` is the original file the values were read from, retained so the
    preparer can compare the staged values against the real document at review time.
    """

    document_id: str
    client_id: str
    tax_year: int
    doc_type: DocType | str
    fields: list[StagedField] = field(default_factory=list)
    extracted_at: datetime | None = None
    source_path: str = ""
    source_note: str = ""        # e.g. "part 2 of a combined PDF"

    def needs_review(self) -> list[StagedField]:
        return [f for f in self.fields if f.status in ("STAGED", "NEEDS_REVIEW")]

    def confirmed(self) -> list[StagedField]:
        return [f for f in self.fields if f.status == "CONFIRMED"]
