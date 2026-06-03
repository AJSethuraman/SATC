#!/usr/bin/env python3
"""Pure load/serialize logic for the in-app Clients editor.

Separated from the Qt dialog so the data handling is testable without a GUI. The
editor shows a friendly subset of fields as a table; this module converts between
client records and table rows and, crucially, **preserves any fields the table does
not show** (line_items, totals, signed flags, custom fields) when saving, so editing
a client in the GUI never silently drops their other data.

Standard library only.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

# (column label, clients.json key, kind). "list" fields are shown comma-separated.
FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Name", "client_name", "text"),
    ("Email", "email", "text"),
    ("Phone", "phone", "text"),
    ("Tax Year", "tax_year", "text"),
    ("Filing Status", "filing_status", "text"),
    ("Expected Documents", "expected_documents", "list"),
    ("Services", "services", "list"),
)
COLUMN_LABELS = tuple(label for label, _, _ in FIELDS)
BACKUP_FILENAME = "clients.backup.json"


def join_list(value) -> str:
    """Render a list field as a comma-separated string for display."""

    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("service") or item.get("description") or ""))
            else:
                parts.append(str(item))
        return ", ".join(p for p in parts if p)
    return "" if value is None else str(value)


def parse_list(text: str) -> list[str]:
    """Parse a comma-separated string into a clean list of values."""

    return [part.strip() for part in str(text).split(",") if part.strip()]


def client_to_row(client: dict) -> list[str]:
    """One client -> the cell strings for each editor column, in column order."""

    row = []
    for _, key, kind in FIELDS:
        value = client.get(key)
        row.append(join_list(value) if kind == "list" else ("" if value is None else str(value)))
    return row


def row_to_client(cells: list[str], original: dict | None = None) -> dict:
    """Editor cells (+ the original record) -> a client dict, preserving hidden fields."""

    client = dict(original or {})
    for index, (_, key, kind) in enumerate(FIELDS):
        text = cells[index] if index < len(cells) else ""
        if kind == "list":
            parsed = parse_list(text)
            if parsed:
                client[key] = parsed
            else:
                client.pop(key, None)
        else:
            text = str(text).strip()
            if text:
                client[key] = text
            else:
                client.pop(key, None)
    return client


def load_clients(folder) -> list[dict]:
    """Load existing client records from clients.json (or clients.csv), else []."""

    folder = Path(folder)
    json_path = folder / "clients.json"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return []
    csv_path = folder / "clients.csv"
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    return []


def save_clients(folder, clients: list[dict]) -> Path:
    """Write clients.json, backing up any existing file first."""

    folder = Path(folder)
    path = folder / "clients.json"
    if path.exists():
        shutil.copy2(path, folder / BACKUP_FILENAME)
    path.write_text(json.dumps(clients, indent=2), encoding="utf-8")
    return path
