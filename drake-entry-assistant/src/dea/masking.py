"""PII masking utilities.

Helpers in this module provide conservative masking for sensitive identifiers so
logs and reports do not expose full SSNs/EINs.
"""

from __future__ import annotations


def _digits_only(value: object | None) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def mask_ssn(value: str | None) -> str:
    """Mask SSN-like input as ``***-**-1234`` style output."""
    if value is None or str(value).strip() == "":
        return ""

    digits = _digits_only(value)
    if len(digits) < 4:
        return "***-**-****"
    return f"***-**-{digits[-4:]}"


def mask_ein(value: str | None) -> str:
    """Mask EIN-like input as ``**-***1234`` style output."""
    if value is None or str(value).strip() == "":
        return ""

    digits = _digits_only(value)
    if len(digits) < 4:
        return "**-*******"
    return f"**-***{digits[-4:]}"


def mask_value(field_name: str, value: object | None) -> str:
    """Mask sensitive values by field name, otherwise stringify readably."""
    normalized_field = field_name.lower()

    if "ssn" in normalized_field:
        return mask_ssn(None if value is None else str(value))
    if "ein" in normalized_field:
        return mask_ein(None if value is None else str(value))

    if value is None:
        return ""
    return str(value)
