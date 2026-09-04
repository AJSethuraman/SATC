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


def opaque_id(prefix: str) -> str:
    """A unique, URL/filename-safe id for intake records (``task-<uuid>``)."""
    import uuid

    return f"{prefix}-{uuid.uuid4()}"


# --- document identity -------------------------------------------------------
#
# A document's id is derived from its CONTENT, not its filename. Three reasons,
# all of them things that were actually wrong:
#
#   1. Correctness. document_id used to be ``path.name``, and a staged field's id
#      is ``f"{document_id}:{field_path}"``. Two files with the same basename in
#      different subfolders — ``2024/W2.pdf`` and ``2023/W2.pdf`` — produced the
#      same field ids, and StagingGate._find returns the FIRST match. A confirm
#      could land on the wrong document's field.
#   2. Privacy. The id is written into the data mart and exported to Excel, and
#      client filenames routinely carry the client's name. A hash carries none.
#   3. Idempotence (doctrine rule 4). Re-reading the same file — an original and
#      the copy ``sort_folder`` made — yields the SAME id, so re-staging is a
#      no-op rather than a duplicate.
#
# The human-readable name still exists: it lives on ``StagedDocument.display_name``
# for the local UI, and deliberately never travels into the mart or an export.

_DOC_ID_CHARS = 16


def content_document_id(data: bytes, *, prefix: str = "doc") -> str:
    """A stable id derived from a document's bytes: ``doc-a3f91c2e4b5d6e7f``.

    Same bytes always give the same id, on any machine, in any run — which is
    what makes re-reading a file idempotent instead of duplicative.
    """
    import hashlib

    return f"{prefix}-{hashlib.sha256(data).hexdigest()[:_DOC_ID_CHARS]}"


def part_document_id(parent_id: str, index: int) -> str:
    """The id of one part split out of a combined PDF.

    Derived from the parent's id so the relationship survives, and so a part is
    stable across runs even though its bytes live only in a temp directory.
    """
    return f"{parent_id}.p{int(index)}"


def content_document_id_for_path(path) -> str:
    """Hash a file on disk. Streams, so a large scan does not load into memory."""
    import hashlib
    from pathlib import Path

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"doc-{digest.hexdigest()[:_DOC_ID_CHARS]}"
