"""Validation rules for normalized tax-entry data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from dea.models import ClientBatch, SourceCellRef, ValidationIssue

_ALLOWED_FILING = {"S", "MFJ", "MFS", "HOH", "QSS"}
_ALLOWED_BOX12 = {
    "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R",
    "S", "T", "V", "W", "Y", "Z", "AA", "BB", "DD", "EE", "FF", "GG", "HH",
}
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}


def _digits(text: str) -> str:
    return "".join(c for c in text if c.isdigit())


def _valid_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
        return True
    except Exception:
        return False


def _valid_zip(text: str) -> bool:
    d = _digits(text)
    return len(d) in {5, 9}


def _numeric_or_blank(raw: str) -> bool:
    if raw.strip() == "":
        return True
    try:
        Decimal(raw)
        return True
    except (InvalidOperation, ValueError):
        return False


def validate_client_batch(
    client_batch: ClientBatch,
    source_cells: dict[str, SourceCellRef] | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    refs = source_cells or {}

    def add(severity: str, client_id: str, field: str, msg: str) -> None:
        ref = refs.get(f"clients.{client_id}.{field}")
        issues.append(
            ValidationIssue(
                severity=severity,  # type: ignore[arg-type]
                client_id=client_id,
                field=field,
                message=msg,
                source_sheet=ref.sheet if ref else None,
                source_cell=ref.cell if ref else None,
            )
        )

    for client in client_batch.clients:
        cid = client.client_id
        tp = client.taxpayer

        if not tp.first_name.strip():
            add("ERROR", cid, "taxpayer.first_name", "taxpayer.first_name is required")
        if not tp.last_name.strip():
            add("ERROR", cid, "taxpayer.last_name", "taxpayer.last_name is required")
        if not tp.ssn.strip():
            add("ERROR", cid, "taxpayer.ssn", "taxpayer.ssn is required")
        elif len(_digits(tp.ssn)) != 9:
            add("ERROR", cid, "taxpayer.ssn", "taxpayer.ssn must contain exactly 9 digits")

        if not tp.dob.strip():
            add("ERROR", cid, "taxpayer.dob", "taxpayer.dob is required")
        elif not _valid_date(tp.dob):
            add("ERROR", cid, "taxpayer.dob", "taxpayer.dob must be a valid date")

        if not client.filing_status.strip():
            add("ERROR", cid, "filing_status", "filing_status is required")
        elif client.filing_status not in _ALLOWED_FILING:
            add("ERROR", cid, "filing_status", "filing_status is invalid")

        if not client.address.street.strip():
            add("ERROR", cid, "address.street", "address.street is required")
        if not client.address.city.strip():
            add("ERROR", cid, "address.city", "address.city is required")
        if not client.address.state.strip():
            add("ERROR", cid, "address.state", "address.state is required")
        elif client.address.state.upper() not in _US_STATES:
            add("ERROR", cid, "address.state", "address.state must be a valid two-letter US state code")
        if not client.address.zip.strip():
            add("ERROR", cid, "address.zip", "address.zip is required")
        elif not _valid_zip(client.address.zip):
            add("ERROR", cid, "address.zip", "address.zip must be a valid 5 digit or 9 digit ZIP")

        if client.filing_status == "MFJ":
            if client.spouse is None:
                add("ERROR", cid, "spouse", "spouse is required for MFJ")
            else:
                if not client.spouse.first_name.strip():
                    add("ERROR", cid, "spouse.first_name", "spouse.first_name is required for MFJ")
                if not client.spouse.last_name.strip():
                    add("ERROR", cid, "spouse.last_name", "spouse.last_name is required for MFJ")
                if not client.spouse.ssn.strip():
                    add("ERROR", cid, "spouse.ssn", "spouse.ssn is required for MFJ")
                if not client.spouse.dob.strip():
                    add("ERROR", cid, "spouse.dob", "spouse.dob is required for MFJ")

        if client.spouse is not None:
            if client.spouse.ssn.strip() and len(_digits(client.spouse.ssn)) != 9:
                add("ERROR", cid, "spouse.ssn", "spouse.ssn must contain exactly 9 digits")
            if client.spouse.dob.strip() and not _valid_date(client.spouse.dob):
                add("ERROR", cid, "spouse.dob", "spouse.dob must be a valid date")

        for w2 in client.w2s:
            w2f = f"w2s.{w2.w2_id}"
            if not w2.employer.ein.strip():
                add("ERROR", cid, f"{w2f}.employer.ein", "employer.ein is required")
            elif len(_digits(w2.employer.ein)) != 9:
                add("ERROR", cid, f"{w2f}.employer.ein", "employer.ein must contain exactly 9 digits")
            if not w2.employer.name.strip():
                add("ERROR", cid, f"{w2f}.employer.name", "employer.name is required")

            raws = [
                ("box_1_wages", w2.box_1_raw),
                ("box_2_federal_withholding", w2.box_2_raw),
                ("box_3_social_security_wages", w2.box_3_raw),
                ("box_4_social_security_tax", w2.box_4_raw),
                ("box_5_medicare_wages", w2.box_5_raw),
                ("box_6_medicare_tax", w2.box_6_raw),
            ]
            for fname, raw in raws:
                if not _numeric_or_blank(raw):
                    add("ERROR", cid, f"{w2f}.{fname}", f"{fname} must be numeric")

            if w2.box_2_federal_withholding > w2.box_1_wages:
                add("ERROR", cid, f"{w2f}.box_2_federal_withholding", "box_2_federal_withholding cannot exceed box_1_wages")

            for state_line in w2.state_lines:
                if state_line.state_withholding > Decimal("0") and not state_line.state.strip():
                    add("ERROR", cid, f"{w2f}.state_lines.state", "state withholding requires state code")
                if state_line.state_withholding > Decimal("0") and state_line.state_wages <= Decimal("0"):
                    add("ERROR", cid, f"{w2f}.state_lines.state_wages", "state withholding requires state wages")

            for item in w2.box_12_items:
                code = item.code.strip().upper()
                if code and code not in _ALLOWED_BOX12:
                    add("WARNING", cid, f"{w2f}.box_12_items.code", "box 12 code is unsupported for automatic handling")

    return issues
