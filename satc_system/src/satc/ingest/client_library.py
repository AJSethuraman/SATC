"""Per-client, per-year document library — where sorted documents live.

Sort can write its clean, renamed copies into a tidy library organized by client
and tax year, so each client has one folder per year:

    <library root>/Jordan & Avery Maplewood (SATC-001000)/2024/
        W-2/W-2 - Buckeye Manufacturing LLC.pdf
        1099-INT/1099-INT - Heartland Bank.pdf
        ...

That year folder is then a ready-to-read Intake folder — Sort and Intake share the
same classifier, so the sorted output feeds straight back in. The library root is
on the practice's own machine (names are fine here); override it with
``SATC_LIBRARY``. Default: ``~/SATC Clients``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(text: str) -> str:
    return _UNSAFE.sub("", str(text)).strip().strip(".") or "Client"


def library_root() -> Path:
    """Root of the client document library (``SATC_LIBRARY`` or ``~/SATC Clients``)."""
    override = os.environ.get("SATC_LIBRARY", "").strip()
    return Path(override) if override else Path.home() / "SATC Clients"


def client_folder(client_id: str, name: str = "") -> Path:
    """One client's folder, named for humans but tagged with the opaque id."""
    label = _safe(name) if name else ""
    folder = f"{label} ({client_id})" if label else client_id
    return library_root() / folder


def client_year_folder(client_id: str, tax_year: int | str, name: str = "") -> Path:
    """The client's folder for a single tax year — the Sort destination / Intake source."""
    return client_folder(client_id, name) / str(tax_year)
