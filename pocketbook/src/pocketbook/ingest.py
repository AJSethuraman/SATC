"""Read the extract as it comes out of the bank's system.

Copied from portfolio-analysis-pack/src/analysis_pack/ingest.py on 25 Sep 2026:
shared modules are copied per project, not imported, so each project stays
self-contained. Keep the two in step by hand when either changes.

CSV through the standard library, XLSX through openpyxl. Column names are
used exactly as found. A value that will not type is reported as what it is
(blank, non-numeric) rather than repaired. What happens to it next is the
engine's business: here it is left out of a rate and counted (ruling OC-1).
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
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
        from .excel_lists import hushed            # openpyxl's warnings about Excel's extension blocks (30 Sep 2026)
        with hushed():
            return _read_xlsx(p, sheet, digest, data)
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    columns = [c.strip() for c in (reader.fieldnames or [])]
    _refuse_duplicates(p, columns)
    rows = [{k.strip() if k else k: v for k, v in row.items()} for row in reader]
    return Table(path=str(p), sha256=digest, columns=columns, rows=rows, kind="csv")


def _read_xlsx(p: Path, sheet: str | None, digest: str, data: bytes) -> Table:
    import openpyxl
    # from the bytes already read, never the file again (the bank, 30 Sep 2026: the extract sits in a OneDrive
    # folder, where every read of the file is another trip through the sync client and the virus scanner)
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = next(it, None)
    if header is None:
        raise ValueError(f"{p}: the sheet has no header row")
    columns = [str(h).strip() if h is not None else "" for h in header]
    _refuse_duplicates(p, columns)
    rows = []
    for r in it:
        if r is None or all(v is None for v in r):
            continue
        rows.append({columns[i]: (r[i] if i < len(r) else None) for i in range(len(columns))})
    wb.close()
    return Table(path=str(p), sha256=digest, columns=columns, rows=rows, kind="xlsx")


def _refuse_duplicates(p: Path, columns: list[str]) -> None:
    """Two columns with one name (once spaces are trimmed) would be read as one: each row keeps only the last,
    and every tab would use it under the first one's name. Refused, naming them (Codex on #394, 28 Sep 2026).
    Unnamed columns are left alone: nothing can be picked by a name it hasn't got."""
    seen, twice = set(), []
    for c in columns:
        if c and c in seen and c not in twice:
            twice.append(c)
        seen.add(c)
    if twice:
        raise ValueError(f"{p.name} has two columns called {', '.join(twice)}. Rename one so each column has "
                         f"its own name, then pick the file again")


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
    if isinstance(value, (int, float, Decimal)):
        return _finite(float(value), value)
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
    f = _finite(float(d), value)
    return -f if neg and not isinstance(f, Bad) else f


def _finite(f: float, value: Any) -> Any:
    """NaN, Infinity or a number too big for a float (1e9999) is not an amount: read as non-numeric, never
    counted into a band or a sum (Codex on #394, 28 Sep 2026)."""
    return f if math.isfinite(f) else Bad("non-numeric", value)


DATE_PATTERNS = ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%y", "%Y%m%d", "%d-%b-%Y", "%b %d, %Y",
                 "%Y-%m-%dT%H:%M:%S")

# A cheap shape check per pattern, asked before strptime. Found 26 Sep 2026: Set up spent 84% of its time
# trying all eight patterns with strptime on every value, plain numbers included (12.8 million calls at 4,000
# loans by 80 columns). Each gate is deliberately LOOSER than the regex strptime builds for its pattern, so it
# never turns away a value strptime would read, and strptime still decides every value a gate lets through:
# the counts are exactly what they were. What the gates have to allow, from Python's own _strptime:
#   %d is "5", "05" or " 5" (one space-padded digit), so every two-digit field here takes " ?\d{1,2}";
#   %b is the locale's month abbreviations, so it takes any text at all;
#   a space in a pattern matches any run of whitespace, and letters match either case ("t" for "T");
#   %Y%m%d reads "2024111", "202411 5" and "20241 5": four digits, one or two, then a space-padded day;
#   \d is any Unicode digit in both, and strptime's int() reads them.
_N = r" ?\d{1,2}"
_DATE_GATES = {pat: re.compile(rx, re.IGNORECASE | re.DOTALL).fullmatch for pat, rx in {
    "%m/%d/%Y": rf"{_N}/{_N}/\d{{4}}",
    "%Y-%m-%d": rf"\d{{4}}-{_N}-{_N}",
    "%d/%m/%Y": rf"{_N}/{_N}/\d{{4}}",
    "%m/%d/%y": rf"{_N}/{_N}/\d{{2}}",
    "%Y%m%d": r"\d{4}\d{1,2} ?\d{1,2}",
    "%d-%b-%Y": rf"{_N}-.+-\d{{4}}",
    "%b %d, %Y": rf".+\s+{_N},\s+\d{{4}}",
    "%Y-%m-%dT%H:%M:%S": rf"\d{{4}}-{_N}-{_N}T{_N}:{_N}:{_N}",
}.items()}


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
        gate = _DATE_GATES[pat]
        n = 0
        for s in texts:
            if gate(s) is None:               # cannot be this pattern, so strptime is never asked
                continue
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
        # an all-digit column of eight-character values reads as %Y%m%d dates
        # too (the way a mainframe writes a date); say so, since the build will
        # read it that way if the question file names it as a date column
        # (adversarial finding 10, 19 Sep 2026)
        digits_as_dates = (kind == "integer" and det.fits.get("%Y%m%d", 0) == len(nonblank)
                           and all(len(cell_text(v)) == 8 for v in nonblank))
        if kind == "date-like" or digits_as_dates:
            entry["dates"] = {"typed": det.typed, "fits": {k: v for k, v in det.fits.items() if v},
                              "resolved": det.resolved, "ambiguous": list(det.ambiguous),
                              "readings": det.readings(), "also_integer": digits_as_dates}
        out.append(entry)
    return out


def cell_text(value: Any) -> str:
    """The value as text for a category label. Blank -> '(blank)'."""
    if is_blank(value):
        return "(blank)"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
