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


def _is_tin_field(field_name: str, kind: str) -> bool:
    """True when a field path's final segment names an SSN/EIN.

    Anchored on the trailing path segment (``taxpayer.ssn`` -> ``ssn``) rather
    than a substring of the whole path, so an unrelated field like
    ``business_ssname`` is not mistaken for an SSN and redacted/mangled.
    """
    segment = field_name.rsplit(".", 1)[-1].lower()
    return segment == kind or segment.endswith("_" + kind)


def mask_value(field_name: str, value: object | None) -> str:
    """Mask sensitive values by field name, otherwise stringify readably."""
    if _is_tin_field(field_name, "ssn"):
        return mask_ssn(None if value is None else str(value))
    if _is_tin_field(field_name, "ein"):
        return mask_ein(None if value is None else str(value))

    if value is None:
        return ""
    return str(value)
