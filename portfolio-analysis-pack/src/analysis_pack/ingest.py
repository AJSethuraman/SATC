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


DATE_PATTERNS = ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%y", "%Y%m%d", "%d-%b-%Y", "%b %d, %Y",
                 "%Y-%m-%dT%H:%M:%S")


def parse_date(value: Any, fmt: str | None) -> Any:
    """A date, BLANK, or Bad('unparseable date'). A typed date cell needs no
    format; text needs `fmt`, which the caller resolved (declared or detected)."""
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


@dataclass(frozen=True)
class DateDetection:
    """What the eight common patterns make of one column's text values."""
    column: str
    total: int                          # non-blank values looked at
    typed: int                          # values that were already dates (XLSX cells)
    fits: dict[str, int]                # pattern -> how many values it parses
    resolved: str | None                # the one pattern fitting every value, if exactly one
    ambiguous: tuple[str, ...]          # patterns that all fit every value, when more than one
    sample: str | None                  # a value to show both readings of

    def readings(self) -> list[tuple[str, str]]:
        """The ambiguous sample read each way, as (pattern, plain date)."""
        out = []
        if self.sample is None:
            return out
        for pat in self.ambiguous:
            try:
                d = datetime.strptime(self.sample, pat).date()
                out.append((pat, d.strftime("%d %B %Y")))
            except ValueError:            # pragma: no cover - only ambiguous patterns are listed
                pass
        return out


def detect_date_format(column: str, values: list[Any]) -> DateDetection:
    """Try every pattern over every non-blank text value. One pattern fitting
    them all is a fact and is used; several fitting them all is ambiguous and
    the caller refuses; none fitting them all leaves the best pattern's
    failures as unparseable."""
    texts = []
    typed = 0
    for v in values:
        if is_blank(v):
            continue
        if isinstance(v, (datetime, date)):
            typed += 1
            continue
        texts.append(str(v).strip())
    fits: dict[str, int] = {}
    for pat in DATE_PATTERNS:
        n = 0
        for s in texts:
            try:
                datetime.strptime(s, pat)
                n += 1
            except ValueError:
                pass
        fits[pat] = n
    full = tuple(pat for pat in DATE_PATTERNS if texts and fits[pat] == len(texts))
    resolved = full[0] if len(full) == 1 else None
    ambiguous = full if len(full) > 1 else ()
    return DateDetection(column=column, total=len(texts) + typed, typed=typed, fits=fits,
                         resolved=resolved, ambiguous=ambiguous, sample=texts[0] if texts else None)


def best_pattern(det: DateDetection) -> str | None:
    """When no pattern fits every value: the one that fits most, so the rest
    can be named as unparseable. None when nothing fits anything."""
    if not det.fits or max(det.fits.values()) == 0:
        return None
    return max(DATE_PATTERNS, key=lambda pat: det.fits[pat])


def inspect_columns(table: "Table") -> list[dict[str, Any]]:
    """Per column: inferred type, null share, distinct count, five samples, and
    the date detection where the column looks like dates. Never applies
    anything; it reports."""
    out = []
    n = len(table.rows)
    for col in table.columns:
        values = [r.get(col) for r in table.rows]
        nonblank = [v for v in values if not is_blank(v)]
        numeric = sum(1 for v in nonblank if not isinstance(parse_number(v), Bad))
        integers = sum(1 for v in nonblank if not isinstance(parse_number(v), Bad)
                       and float(parse_number(v)).is_integer())
        det = detect_date_format(col, values)
        date_like = det.typed + max(det.fits.values(), default=0)
        distinct = len(set(cell_text(v) for v in nonblank))
        if not nonblank:
            kind = "empty"
        elif det.typed == len(nonblank) or (date_like >= 0.9 * len(nonblank) and numeric < len(nonblank)):
            kind = "date-like"
        elif numeric == len(nonblank):
            kind = "integer" if integers == len(nonblank) else "decimal"
        elif numeric == 0:
            kind = "text"
        else:
            kind = "mixed"
        samples = []
        for v in nonblank:
            s = cell_text(v)
            if s not in samples:
                samples.append(s)
            if len(samples) == 5:
                break
        entry = {"column": col, "kind": kind, "null_share": round((n - len(nonblank)) / n, 4) if n else None,
                 "distinct": distinct, "samples": samples}
        if kind == "date-like":
            entry["dates"] = {"typed": det.typed, "fits": {k: v for k, v in det.fits.items() if v},
                              "resolved": det.resolved, "ambiguous": list(det.ambiguous),
                              "readings": det.readings()}
        out.append(entry)
    return out


def cell_text(value: Any) -> str:
    """The value as text for a category label. Blank -> '(blank)'."""
    if is_blank(value):
        return "(blank)"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
