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
    extractor: str, page: int | None = None, worksheet_title: str | None = None,
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
    )
