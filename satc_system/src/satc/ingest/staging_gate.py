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

from satc.models.actor import INTAKE, Actor, ActorRefused, require_human
from satc.models.provenance import Provenance
from satc.models.staging import StagedDocument, StagedField

Agg = Literal["sum", "first", "max"]


@dataclass
class LineMapping:
    """How one or more confirmed field paths feed a single line-sheet input id.

    The optional ``schedule``/``line_code``/``label`` give the same value its home
    in the data mart's normalized ``line_items`` table, so one table drives both the
    workpaper projection and the persisted facts. A blank ``line_code`` means the
    line feeds the workpaper only and is not posted to the mart.
    """

    line_id: str
    paths: list[str]
    agg: Agg = "sum"
    kind: Literal["money", "text"] = "money"
    schedule: str = "1040"
    line_code: str = ""
    label: str = ""


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
    def auto_confirm_high(self, by: Actor) -> int:
        """Confirm HIGH-confidence, cleanly-parsed, NON-model fields. Returns count.

        ``by`` is required and has no default — a defaulted actor is the exact
        shape this whole model exists to remove, and leaving one here would be
        the last place a caller could be believed by omission.

        Two gates, not one. Confidence says the read was clean; provenance says
        what produced it. A model-produced value is never auto-confirmed at any
        confidence — an 8B model that is confidently wrong is the failure mode
        this exists to stop, and confidence is exactly the signal it fakes best.
        """
        # A system actor MAY run this sweep — deterministic code can be read,
        # tested, and proven wrong. A model may not, at any confidence.
        if by.is_model:
            raise ActorRefused(
                f"{by.handle} may not auto-confirm staged values. Deterministic "
                f"intake runs this sweep; a model's route to the mart is to "
                f"propose values that the owner accepts at the gate.")
        n = 0
        for f in self.all_fields():
            if f.status != "STAGED" or f.provenance.confidence != "HIGH":
                continue
            if f.provenance.is_model_produced:
                # Left STAGED on purpose: it still reaches the owner's review
                # queue, it just cannot skip it.
                continue
            f.status = "CONFIRMED"
            f.confirmed_value_text = f.value_text
            f.confirmed_value_amount = f.value_amount
            f.confirmed_by = by
            f.confirmed_at = datetime.now()
            n += 1
        return n

    def confirm(self, field_id: str, actor: Actor, *, value_text: str | None = None,
                value_amount: Decimal | None = None) -> bool:
        """Turn a proposal into a fact. Humans only.

        ``actor`` is positional and required — there is no default, because a
        default here is what let any caller assert it was the preparer.
        """
        require_human(actor, "confirm a staged value")
        f = self._find(field_id)
        if f is None:
            return False
        f.status = "CONFIRMED"
        f.confirmed_value_text = value_text if value_text is not None else f.value_text
        f.confirmed_value_amount = value_amount if value_amount is not None else f.value_amount
        f.confirmed_by = actor
        f.confirmed_at = datetime.now()
        return True

    def reject(self, field_id: str, actor: Actor, *, note: str = "") -> bool:
        """Reject a staged value. Humans only — rejecting is a judgment too."""
        require_human(actor, "reject a staged value")
        f = self._find(field_id)
        if f is None:
            return False
        f.status = "REJECTED"
        f.confirmed_by = actor
        if note:
            f.note = note
        return True

    def unconfirm(self, field_id: str) -> bool:
        """Un-accept a field: drop it back to review and clear the confirmation."""
        f = self._find(field_id)
        if f is None:
            return False
        f.status = "STAGED" if f.provenance.confidence == "HIGH" else "NEEDS_REVIEW"
        f.confirmed_value_text = ""
        f.confirmed_value_amount = None
        f.confirmed_by = None
        f.confirmed_at = None
        return True

    def delete_field(self, field_id: str) -> bool:
        """Remove a staged field entirely (e.g. a stray/duplicate read)."""
        for doc in self.documents:
            for i, f in enumerate(doc.fields):
                if f.field_id == field_id:
                    del doc.fields[i]
                    return True
        return False

    def edit(self, field_id: str, actor: Actor, *, value_text: str | None = None,
             value_amount: Decimal | None = None) -> bool:
        """Hand-correct a value and confirm it — the preparer's word overrides the read.

        Humans only, and for the same reason as :meth:`confirm`: this both sets a
        value AND accepts it, so it is the most powerful operation on the gate.
        A hand-corrected value becomes human-produced — the owner typed it, so
        whatever produced the original read no longer taints it.
        """
        require_human(actor, "hand-correct a staged value")
        f = self._find(field_id)
        if f is None:
            return False
        if value_text is not None:
            f.confirmed_value_text = value_text
        f.confirmed_value_amount = value_amount
        f.status = "CONFIRMED"
        f.confirmed_by = actor
        f.confirmed_at = datetime.now()
        # The owner typed this value, so it is now theirs — a hand-correction is
        # the one operation that legitimately clears a model taint, because a
        # human read the document and decided.
        f.provenance = Provenance(
            source_kind="PREPARER_ENTRY", confidence="HIGH",
            source_ref=f.provenance.source_ref,
            note=f.provenance.note, extractor=f.provenance.extractor,
            extracted_at=f.provenance.extracted_at, produced_by=actor)
        if "hand-corrected" not in (f.note or ""):
            f.note = (f.note + " · hand-corrected").lstrip(" ·")
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

    def to_line_items(self, return_key_value: str, mappings: Iterable[LineMapping],
                      *, extractor: str = "intake (confirmed)") -> list:
        """Project confirmed fields onto data-mart ``LineItem`` records.

        Only mappings carrying a ``line_code`` are posted (the rest feed the
        workpaper only). Each posted value keeps SOURCE_DOC provenance pointing back
        at the documents it came from, so the mart never holds an unsourced figure.
        """
        from satc.ids import line_item_key
        from satc.models.mart import LineItem
        from satc.models.provenance import Provenance, SourceRef

        by_path = self.confirmed_by_path()
        items: list = []
        for m in mappings:
            if not m.line_code:
                continue
            fields = [f for p in m.paths for f in by_path.get(p, [])]
            if not fields:
                continue
            doc_ids = sorted({f.document_id for f in fields if getattr(f, "document_id", "")})
            citation = "Intake (confirmed): " + ", ".join(doc_ids) if doc_ids else "Intake (confirmed)"
            prov = Provenance(source_kind="SOURCE_DOC", confidence="HIGH",
                              source_ref=SourceRef(document_id=doc_ids[0] if doc_ids else None,
                                                   citation=citation),
                              extractor=extractor)
            li_key = line_item_key(return_key_value, m.schedule, m.line_code)
            if m.kind == "text":
                items.append(LineItem(line_item_key=li_key, return_key=return_key_value,
                                      schedule=m.schedule, line_code=m.line_code,
                                      label=m.label or m.line_id, amount=None,
                                      text_value=fields[0].effective_text(), provenance=prov))
                continue
            amounts = [f.effective_amount() for f in fields if f.effective_amount() is not None]
            if not amounts:
                continue
            total = amounts[0] if m.agg == "first" else (max(amounts) if m.agg == "max" else sum(amounts))
            items.append(LineItem(line_item_key=li_key, return_key=return_key_value,
                                  schedule=m.schedule, line_code=m.line_code,
                                  label=m.label or m.line_id, amount=total, provenance=prov))
        return items


# Canonical mapping: confirmed document fields -> 1040 line-sheet input ids, and
# (where a line_code is set) -> the data mart's normalized line_items.
MAPPING_1040: list[LineMapping] = [
    LineMapping("wages", ["w2.box1_wages"], "sum",
                schedule="1040", line_code="1a", label="Wages (W-2 box 1)"),
    LineMapping("fed_wh_w2", ["w2.box2_fed_wh"], "sum",
                schedule="1040", line_code="25a", label="Federal tax withheld (W-2)"),
    LineMapping("ss_wages", ["w2.box3_ss_wages"], "sum"),  # workpaper only
    LineMapping("state_wh", ["w2.box17_state_wh"], "sum",
                schedule="SCH_A", line_code="5a", label="State income tax withheld"),
    LineMapping("interest", ["int.box1_interest"], "sum",
                schedule="1040", line_code="2b", label="Taxable interest"),
    LineMapping("dividends_ord", ["div.box1a_ordinary"], "sum",
                schedule="1040", line_code="3b", label="Ordinary dividends"),
    LineMapping("dividends_qual", ["div.box1b_qualified"], "sum",
                schedule="1040", line_code="3a", label="Qualified dividends"),
    LineMapping("k1_ordinary", ["k1s.box1_ordinary", "k1p.box1_ordinary"], "sum",
                schedule="SCH_E", line_code="K1_ORD", label="K-1 ordinary business income"),
    LineMapping("k1_rental_other", ["k1s.box2_rental", "k1p.box2_rental"], "sum",
                schedule="SCH_E", line_code="K1_RENTAL", label="K-1 net rental real estate"),
    LineMapping("prior_year_tax", ["prior.total_tax"], "first"),    # reference (workpaper)
    LineMapping("prior_year_agi", ["prior.agi"], "first"),          # reference (workpaper)
    LineMapping("filing_status", ["prior.filing_status"], "first", kind="text"),
]
