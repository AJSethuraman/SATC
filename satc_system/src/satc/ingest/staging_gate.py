"""The staging / confirmation gate.

Extracted fields land here and are not trusted until confirmed. The gate:
  * auto-confirms only HIGH-confidence fields (everything else waits for review);
  * lets the preparer confirm/correct or reject individual fields;
  * exposes only CONFIRMED values to downstream consumers (line sheets, data mart).

It also maps confirmed canonical ``field_path`` values onto a line sheet's input
ids (with aggregation, e.g. summing every W-2 box 1 into the single ``wages``
line) so a confirmed intake flows into the workpaper without re-keying.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Literal

from satc.models.staging import StagedDocument, StagedField

Agg = Literal["sum", "first", "max"]


@dataclass
class LineMapping:
    """How one or more confirmed field paths feed a single line-sheet input id."""

    line_id: str
    paths: list[str]
    agg: Agg = "sum"
    kind: Literal["money", "text"] = "money"


@dataclass
class StagingGate:
    """Holds staged documents and governs promotion to confirmed."""

    documents: list[StagedDocument] = field(default_factory=list)

    def add(self, doc: StagedDocument) -> StagingGate:
        self.documents.append(doc)
        return self

    def all_fields(self) -> list[StagedField]:
        return [f for doc in self.documents for f in doc.fields]

    def _find(self, field_id: str) -> StagedField | None:
        for f in self.all_fields():
            if f.field_id == field_id:
                return f
        return None

    # -- gate operations ---------------------------------------------------
    def auto_confirm_high(self, by: str = "auto") -> int:
        """Confirm only HIGH-confidence, cleanly-parsed fields. Returns count."""
        n = 0
        for f in self.all_fields():
            if f.status == "STAGED" and f.provenance.confidence == "HIGH":
                f.status = "CONFIRMED"
                f.confirmed_value_text = f.value_text
                f.confirmed_value_amount = f.value_amount
                f.confirmed_by = by
                f.confirmed_at = datetime.now()
                n += 1
        return n

    def confirm(self, field_id: str, *, value_text: str | None = None,
                value_amount: Decimal | None = None, by: str = "preparer") -> bool:
        f = self._find(field_id)
        if f is None:
            return False
        f.status = "CONFIRMED"
        f.confirmed_value_text = value_text if value_text is not None else f.value_text
        f.confirmed_value_amount = value_amount if value_amount is not None else f.value_amount
        f.confirmed_by = by
        f.confirmed_at = datetime.now()
        return True

    def reject(self, field_id: str, *, by: str = "preparer", note: str = "") -> bool:
        f = self._find(field_id)
        if f is None:
            return False
        f.status = "REJECTED"
        f.confirmed_by = by
        if note:
            f.note = note
        return True

    # -- views -------------------------------------------------------------
    def needs_review(self) -> list[StagedField]:
        return [f for f in self.all_fields() if f.status in ("STAGED", "NEEDS_REVIEW")]

    def confirmed(self) -> list[StagedField]:
        return [f for f in self.all_fields() if f.status == "CONFIRMED"]

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {"STAGED": 0, "NEEDS_REVIEW": 0, "CONFIRMED": 0, "REJECTED": 0}
        for f in self.all_fields():
            out[f.status] = out.get(f.status, 0) + 1
        return out

    def confirmed_by_path(self) -> dict[str, list[StagedField]]:
        out: dict[str, list[StagedField]] = {}
        for f in self.confirmed():
            out.setdefault(f.field_path, []).append(f)
        return out

    # -- mapping to a line sheet ------------------------------------------
    def to_line_values(self, mappings: Iterable[LineMapping]) -> dict[str, object]:
        """Project confirmed fields onto line-sheet input ids (with aggregation)."""
        by_path = self.confirmed_by_path()
        values: dict[str, object] = {}
        for m in mappings:
            fields = [f for p in m.paths for f in by_path.get(p, [])]
            if not fields:
                continue
            if m.kind == "text":
                values[m.line_id] = fields[0].effective_text()
                continue
            amounts = [f.effective_amount() for f in fields if f.effective_amount() is not None]
            if not amounts:
                continue
            if m.agg == "first":
                values[m.line_id] = float(amounts[0])
            elif m.agg == "max":
                values[m.line_id] = float(max(amounts))
            else:  # sum
                values[m.line_id] = float(sum(amounts))
        return values


# Canonical mapping: confirmed document fields -> 1040 line-sheet input ids.
MAPPING_1040: list[LineMapping] = [
    LineMapping("wages", ["w2.box1_wages"], "sum"),
    LineMapping("fed_wh_w2", ["w2.box2_fed_wh"], "sum"),
    LineMapping("ss_wages", ["w2.box3_ss_wages"], "sum"),
    LineMapping("state_wh", ["w2.box17_state_wh"], "sum"),
    LineMapping("interest", ["int.box1_interest"], "sum"),
    LineMapping("dividends_ord", ["div.box1a_ordinary"], "sum"),
    LineMapping("dividends_qual", ["div.box1b_qualified"], "sum"),
    LineMapping("k1_ordinary", ["k1s.box1_ordinary", "k1p.box1_ordinary"], "sum"),
    LineMapping("k1_rental_other", ["k1s.box2_rental", "k1p.box2_rental"], "sum"),
    LineMapping("prior_year_tax", ["prior.total_tax"], "first"),
    LineMapping("prior_year_agi", ["prior.agi"], "first"),
    LineMapping("filing_status", ["prior.filing_status"], "first", kind="text"),
]
