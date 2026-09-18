"""Read the extract as it comes out of the bank's system.

CSV through the standard library, XLSX through openpyxl. Column names are
used exactly as found. Values are typed here and nowhere else, and a value
that will not type is reported as what it is (blank, non-numeric,
unparseable) rather than repaired.

Blank is a state, not dirt: a blank is counted by quarter on the capture tab.
Everything that is not blank and will not parse is dirt, and dirt refuses the
build (PRD §6.3).
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

BLANK_TOKENS = {"", "na", "n/a", "null", "none", "-"}


class Blank:
    """The single blank marker. Identity-compared."""
    def __repr__(self) -> str:   # pragma: no cover
        return "BLANK"


BLANK = Blank()


@dataclass(frozen=True)
class Bad:
    """A value that would not type. `reason` is one of the hygiene reasons."""
    reason: str
    value: Any


@dataclass
class Table:
    path: str
    sha256: str
    columns: list[str]
    rows: list[dict[str, Any]]
    kind: str            # "csv" | "xlsx"


def read_table(path: str | Path, sheet: str | None = None) -> Table:
    p = Path(path)
    data = p.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        ws = wb[sheet] if sheet else wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        header = next(it, None)
        if header is None:
            raise ValueError(f"{p}: the sheet has no header row")
        columns = [str(h).strip() if h is not None else "" for h in header]
        rows = []
        for r in it:
            if r is None or all(v is None for v in r):
                continue
            rows.append({columns[i]: (r[i] if i < len(r) else None) for i in range(len(columns))})
        wb.close()
        return Table(path=str(p), sha256=digest, columns=columns, rows=rows, kind="xlsx")
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    columns = [c.strip() for c in (reader.fieldnames or [])]
    rows = [{k.strip() if k else k: v for k, v in row.items()} for row in reader]
    return Table(path=str(p), sha256=digest, columns=columns, rows=rows, kind="csv")


def is_blank(value: Any) -> bool:
    if value is None or value is BLANK:
        return True
    if isinstance(value, str):
        return value.strip().lower() in BLANK_TOKENS
    return False


def parse_number(value: Any) -> Any:
    """A float, BLANK, or Bad('non-numeric')."""
    if is_blank(value):
        return BLANK
    if isinstance(value, bool):
        return Bad("non-numeric", value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return Bad("non-numeric", value)
    s = str(value).strip()
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").replace(" ", "")
    if s.endswith("%"):
        return Bad("non-numeric", value)
    try:
        d = Decimal(s)
    except InvalidOperation:
        return Bad("non-numeric", value)
    f = float(d)
    return -f if neg else f


def parse_date(value: Any, fmt: str | None) -> Any:
    """A date, BLANK, or Bad('unparseable date'). A typed date cell needs no
    format; text needs `fmt` (slice 2 adds detection when it is absent)."""
    if is_blank(value):
        return BLANK
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if fmt is None:
        return Bad("unparseable date", value)
    try:
        return datetime.strptime(s, fmt).date()
    except ValueError:
        return Bad("unparseable date", value)


def cell_text(value: Any) -> str:
    """The value as text for a category label. Blank -> '(blank)'."""
    if is_blank(value):
        return "(blank)"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
