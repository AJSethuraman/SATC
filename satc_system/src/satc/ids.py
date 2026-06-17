"""Stable key helpers for the SATC data model.

Every record in the working data mart is keyed by a small set of stable,
human-stable identifiers so the model ports to SQL with no restructuring:

    client_id + tax_year + return_type + jurisdiction

These helpers build and parse the composite keys used as primary/foreign keys in
the normalized tables. Keys are intentionally URL/filename safe and contain no
PII (``client_id`` is an opaque handle that resolves to a name/SSN only inside the
external identity vault).
"""

from __future__ import annotations

import re
from typing import Final

# Canonical return types handled by the practice. Stable codes (not display labels)
# so they survive renames and port cleanly to SQL enums / lookup tables.
RETURN_TYPES: Final = ("1040", "1120S", "1065", "1120")

# Jurisdictions we build first. "US" = Federal. State codes are USPS two-letter.
PRIMARY_JURISDICTIONS: Final = ("US", "OH", "MI", "MA")

_CLIENT_ID_RE: Final = re.compile(r"^[A-Z]{2,6}-\d{4,}$")
_KEY_SEP: Final = "|"


def normalize_jurisdiction(value: str) -> str:
    """Normalize a jurisdiction token to its canonical form (``US`` or USPS code)."""
    token = (value or "").strip().upper()
    if token in {"US", "FED", "FEDERAL", "IRS", ""}:
        return "US"
    return token


def validate_client_id(client_id: str) -> bool:
    """Return ``True`` if ``client_id`` matches the opaque-handle convention.

    Convention: 2-6 uppercase letters, a hyphen, then a zero-padded sequence
    (e.g. ``SATC-001000``). This is a *handle*, never a name or SSN.
    """
    return bool(_CLIENT_ID_RE.match((client_id or "").strip()))


def return_key(client_id: str, tax_year: int, return_type: str, jurisdiction: str) -> str:
    """Build the composite key for one return (one client, year, form, jurisdiction)."""
    rt = return_type.strip().upper()
    if rt not in RETURN_TYPES:
        raise ValueError(f"Unknown return_type: {return_type!r}; expected one of {RETURN_TYPES}")
    juris = normalize_jurisdiction(jurisdiction)
    return _KEY_SEP.join([client_id.strip(), str(int(tax_year)), rt, juris])


def parse_return_key(key: str) -> tuple[str, int, str, str]:
    """Inverse of :func:`return_key`."""
    parts = key.split(_KEY_SEP)
    if len(parts) != 4:
        raise ValueError(f"Malformed return key: {key!r}")
    client_id, year, rt, juris = parts
    return client_id, int(year), rt, normalize_jurisdiction(juris)


def engagement_key(client_id: str, tax_year: int) -> str:
    """Build the per-client, per-year engagement key (groups all jurisdictions/forms)."""
    return _KEY_SEP.join([client_id.strip(), str(int(tax_year))])


def line_item_key(return_key_value: str, schedule: str, line: str) -> str:
    """Build a stable key for a single line item within a return."""
    return _KEY_SEP.join([return_key_value, schedule.strip().upper(), str(line).strip()])
