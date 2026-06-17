"""PII masking utilities (shared convention with drake-entry-assistant).

Only masked or non-sensitive values are ever written to the workbook. Full
SSN/EIN values live exclusively in the external identity vault. These helpers
produce last-4 style masks for the rare cases where a masked tail is shown for
preparer recognition (e.g. matching a W-2 to the right person).
"""

from __future__ import annotations


def _digits_only(value: object | None) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def mask_ssn(value: str | None) -> str:
    """Mask SSN-like input as ``***-**-1234``."""
    if value is None or str(value).strip() == "":
        return ""
    digits = _digits_only(value)
    if len(digits) < 4:
        return "***-**-****"
    return f"***-**-{digits[-4:]}"


def mask_ein(value: str | None) -> str:
    """Mask EIN-like input as ``**-***1234``."""
    if value is None or str(value).strip() == "":
        return ""
    digits = _digits_only(value)
    if len(digits) < 4:
        return "**-*******"
    return f"**-***{digits[-4:]}"


def last4(value: str | None) -> str:
    """Return just the last four digits (no formatting), or ``""``."""
    digits = _digits_only(value)
    return digits[-4:] if len(digits) >= 4 else ""


def mask_value(field_name: str, value: object | None) -> str:
    """Mask sensitive values by field name; otherwise stringify readably."""
    normalized = (field_name or "").lower()
    if "ssn" in normalized:
        return mask_ssn(None if value is None else str(value))
    if "ein" in normalized:
        return mask_ein(None if value is None else str(value))
    if value is None:
        return ""
    return str(value)
