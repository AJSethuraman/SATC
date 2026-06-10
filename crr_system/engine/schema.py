"""Shared row schema for the extraction engine.

One schema serves both row types:
  Type A - regulatory/policy thresholds (OCC bulletins, interagency guidance,
           exam manuals, internal credit policy).
  Type B - credit-memo / underwriting assertions (CAM, underwriting package,
           spreads, appraisal).

Every row carries provenance: the verbatim source span and the page/section
locator it came from. A row without a traceable origin must not be created.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional

ROW_TYPE_A = "A-Threshold"
ROW_TYPE_B = "B-Assertion"

CONFIDENCE_HIGH = "High"
CONFIDENCE_MEDIUM = "Medium"
CONFIDENCE_LOW = "Low"

STATUS_STAGED = "Staged"
STATUS_COVERAGE_GAP = "Coverage Gap"

CONFIRMATION_PENDING = "Pending"
CONFIRMATION_CONFIRMED = "Confirmed"
CONFIRMATION_REJECTED = "Rejected"


@dataclass
class SourceAnchor:
    """Location of a span inside a source document."""

    document: str            # file name / URL of the source document
    page: Optional[int]      # 1-based page number (None for unpaged text)
    section: str             # nearest heading / section label, "" if unknown
    char_start: int          # offset of span within the page text
    char_end: int

    def locator(self) -> str:
        parts = []
        if self.page is not None:
            parts.append(f"p.{self.page}")
        if self.section:
            parts.append(self.section)
        return ", ".join(parts) if parts else "(unlocated)"


@dataclass
class ExtractedRow:
    """A single staged fact awaiting reviewer confirmation."""

    row_type: str                     # ROW_TYPE_A or ROW_TYPE_B
    metric: str                       # e.g. "Total Debt / EBITDA" or "DSCR (asserted)"
    proposed_value: str               # value as extracted, normalized text
    unit: str                         # "x", "%", "$", "text", "grade", ...
    basis: str                        # definition/basis or assertion context
    source_span: str                  # verbatim text the value came from
    anchor: SourceAnchor
    confidence: str = CONFIDENCE_MEDIUM
    status: str = STATUS_STAGED
    # Type A fields ---------------------------------------------------------
    agency: str = ""                  # OCC / FDIC / FRB / Interagency / Internal
    citation: str = ""                # bulletin number, policy section, etc.
    effective_date: Optional[dt.date] = None
    rescinded_date: Optional[dt.date] = None
    # Type B fields ---------------------------------------------------------
    borrower: str = ""
    facility: str = ""
    category: str = ""                # ratio / grade / repayment / guarantor / covenant / collateral / assumption
    # Reviewer workflow (always blank at extraction time) --------------------
    confirmation: str = CONFIRMATION_PENDING
    reviewer_notes: str = ""
    independent_value: str = ""       # reviewer's independently derived value (Type B)
    notes: str = ""                   # extractor notes (ambiguity, gaps)
    row_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.source_span and self.status != STATUS_COVERAGE_GAP:
            raise ValueError(
                f"Row '{self.metric}' has no source span; rows must carry provenance."
            )
        if not self.row_id:
            digest = hashlib.sha1(
                "|".join(
                    [
                        self.row_type,
                        self.metric,
                        self.proposed_value,
                        self.agency,
                        self.borrower,
                        self.anchor.document,
                        str(self.anchor.page),
                        str(self.anchor.char_start),
                    ]
                ).encode()
            ).hexdigest()[:10].upper()
            prefix = "THR" if self.row_type == ROW_TYPE_A else "AST"
            self.row_id = f"{prefix}-{digest}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["locator"] = self.anchor.locator()
        return d
