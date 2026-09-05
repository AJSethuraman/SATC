"""Extractor base helpers — conservative parsing + staged-field construction.

The cardinal rule of extraction here is *conservatism*: never guess a dollar
amount. A value that does not parse cleanly is staged as ``NEEDS_REVIEW`` with a
blank amount and a note, so the preparer must look at it. Confidence is recorded
on every field and only ``HIGH`` confidence is eligible for auto-confirmation.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from satc.ingest import shapes
from satc.models.provenance import Confidence, Provenance, SourceRef
from satc.models.staging import StagedField

_MONEY_OK = re.compile(r"^\$?\(?-?[\d,]+(\.\d{1,2})?\)?$")


def parse_money(raw: object | None) -> tuple[Decimal | None, Confidence, str]:
    """Parse a monetary token conservatively.

    Returns ``(amount_or_None, confidence, note)``. Parentheses denote negatives.
    Anything that is not unambiguously a number yields ``(None, "UNCERTAIN", ...)``
    so it routes to manual review rather than being guessed.
    """
    if raw is None:
        return None, "UNCERTAIN", "no value extracted"
    text = str(raw).strip()
    if text == "" or text.upper() in {"N/A", "NA", "-", "NONE"}:
        return None, "UNCERTAIN", f"non-numeric token {text!r}"
    cleaned = text.replace("$", "").replace(",", "").strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    if not _MONEY_OK.match(text):
        return None, "UNCERTAIN", f"unrecognized money format {text!r}"
    try:
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None, "UNCERTAIN", f"could not parse {text!r}"
    if negative:
        amount = -amount
    return amount, "HIGH", ""


def make_staged_field(
    *, field_id: str, document_id: str, client_id: str, tax_year: int,
    field_path: str, label: str, raw_value: object | None, is_money: bool,
    extractor: str, shape: str = "", page: int | None = None,
    worksheet_title: str | None = None,
    sharepoint_link: str | None = None, base_confidence: Confidence = "HIGH",
) -> StagedField:
    """Build a :class:`StagedField` with provenance, parsing money conservatively."""
    text = "" if raw_value is None else str(raw_value).strip()
    amount: Decimal | None = None
    confidence: Confidence = base_confidence
    note = ""
    status = "STAGED"

    if is_money:
        amount, money_conf, money_note = parse_money(raw_value)
        if amount is None:
            confidence = "UNCERTAIN"
            note = money_note
            status = "NEEDS_REVIEW"
        else:
            confidence = base_confidence if base_confidence != "HIGH" else money_conf

    # WHAT THE FIELD IS ALLOWED TO HOLD, which is a different question from how
    # sure the reader was. D9: reading `Box 17  State income tax  2,679.00` put
    # the string "income tax" into Box 15 - State. It was caught, but by
    # CONFIDENCE -- the read happened to come back LOW. Nothing on the row knew
    # a state field cannot hold a verb phrase, so the same read at HIGH would
    # have auto-confirmed and gone into the Drake input as `box15_state`.
    #
    # Here, because this is where every reader converges: the map extractor, the
    # vision rung, the paystub path and the form reader all build their fields
    # through this function. A check on any one of them is a check on one door.
    #
    # The value is KEPT, not blanked. The preparer has to see what the document
    # actually said to decide, and a cleared field loses the evidence that the
    # reader went wrong.
    if not shapes.fits(shape, text):
        confidence = "UNCERTAIN"
        status = "NEEDS_REVIEW"
        why = shapes.refusal(shape, text)
        note = f"{note} · {why}".lstrip(" ·") if note else why

    source_ref = SourceRef(
        document_id=document_id, sharepoint_link=sharepoint_link,
        page=page, worksheet_title=worksheet_title, field_label=label,
    )
    provenance = Provenance(
        source_kind="SOURCE_DOC", confidence=confidence, source_ref=source_ref,
        note=note, extractor=extractor, extracted_at=datetime.now(),
    )
    return StagedField(
        field_id=field_id, document_id=document_id, client_id=client_id,
        tax_year=tax_year, field_path=field_path, label=label, value_text=text,
        provenance=provenance, value_amount=amount, status=status, note=note,
        shape=shape,
    )
