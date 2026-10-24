"""The reference and data tabs on one template: Evidence, Glossary, Sources
(with Reporting changes as its last section), Run, Data, and the layout
Signals data shares with Data.

Claude Design's round 3 (docs/design/round-3/handoff/README.md, "Peer books,
Evidence, Glossary, Sources, Run, Data, Signals data"), over round 2's
reference template:

- row 1 the title, Arial 14 bold; row 2 the subtitle, Calibri 11 SLATE, over a
  thin STONE rule; a spacer;
- each section under ``quiet_section`` (Arial 11 bold over a medium INK rule);
- column headers MIST, Arial 9 bold INK, wrapped, 27 pt, a STONE rule under;
- body rows 15 pt with hairlines ``E7E2D8``; numbers right-aligned;
- filter buttons only on Product, Measure and Source (and Tab, on Glossary).

Words on these tabs are the files' and the registry's own; the writers add
headings and nothing else. A file's folder is printed once, on Run; every
other mention of a file is its name.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.filters import AutoFilter, FilterColumn
from openpyxl.worksheet.table import Table, TableStyleInfo

from . import keybank_style as K

EDGE = 1.57                                      # column A: a 16 px margin
HAIR = "E7E2D8"
F_BODY = Font(name="Calibri", size=11, color=K.INK_TEXT)
F_BOLD = Font(name="Calibri", size=11, bold=True, color=K.INK_TEXT)
F_SLATE = Font(name="Calibri", size=11, color=K.SLATE)
F_SMALL = Font(name="Calibri", size=10, color=K.INK_TEXT)
F_SMALL_BOLD = Font(name="Calibri", size=10, bold=True, color=K.INK_TEXT)
F_SMALL_SLATE = Font(name="Calibri", size=10, color=K.SLATE)
F_MONO = Font(name="Consolas", size=9, color=K.INK_TEXT)
F_HASH = Font(name="Consolas", size=9, color=K.SLATE)
F_LINK = Font(name="Calibri", size=10, color=K.KEY_RED, underline="single")
TOP = Alignment(vertical="top", wrap_text=True)
RIGHT_TOP = Alignment(vertical="top", horizontal="right")
Z_FORMAT = "+0.0;-0.0;0.0"


# ---------------------------------------------------------------- the template

def px(p: float) -> float:
    """Pixels to Excel column units, as the hand-off converts them."""
    return round((p - 5) / 7, 2)


def fit(texts, lo: int, hi: int, per: float = 7.0, pad: int = 14) -> int:
    """A column's width in pixels for its longest text, between lo and hi."""
    longest = max((len(str(t)) for t in texts if t is not None), default=0)
    return int(min(hi, max(lo, longest * per + pad)))


def lines(text, width_px: float, per: float = 7.0) -> int:
    """Lines a text wraps to in a column ``width_px`` wide (each newline one more)."""
    # Word wrap leaves part of each line empty: a tenth is allowed for it.
    chars = max(1, int(0.9 * (width_px - 8) / per))
    return sum(max(1, -(-len(part) // chars)) for part in str(text or "").split("\n"))


def widths(ws, cols: Dict[str, float]) -> None:
    ws.column_dimensions["A"].width = EDGE
    for c, p in cols.items():
        ws.column_dimensions[c].width = px(p)


def title(ws, text: str, subtitle: str, last_col: int) -> int:
    """Rows 1 to 3: the title, the subtitle over a thin STONE rule, a spacer.
    Returns the first free row."""
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = EDGE
    t = ws.cell(1, 2, text)
    t.font = Font(name="Arial", size=14, bold=True, color=K.INK)
    t.alignment = Alignment(vertical="bottom")
    s = ws.cell(2, 2, subtitle)
    s.font = Font(name="Calibri", size=11, color=K.SLATE)
    s.alignment = Alignment(vertical="center")
    for col in range(2, last_col + 1):
        ws.cell(2, col).border = Border(bottom=Side(style="thin", color=K.STONE))
    for r, h in ((1, 25.5), (2, 15), (3, 7.5)):
        ws.row_dimensions[r].height = h
    return 4


def section(ws, row: int, text: str, first: int, last: int) -> int:
    """A section head (``quiet_section``). Returns the next row."""
    return K.quiet_section(ws, row, text, last - first + 1, first_col=first)


def header(ws, row: int, names: Sequence, first: int, right=(), height: float = 27) -> int:
    """A header row: MIST, Arial 9 bold INK, wrapped, a STONE rule; the
    ``right`` positions right-aligned. A None name leaves the cell blank but
    keeps the band. Returns the next row."""
    for i, nm in enumerate(names):
        c = ws.cell(row, first + i, nm)
        c.fill = K.solid(K.MIST)
        c.font = Font(name="Arial", size=9, bold=True, color=K.INK)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right" if i in right else "left")
        c.border = Border(bottom=Side(style="thin", color=K.STONE))
    ws.row_dimensions[row].height = height
    return row + 1


def body(ws, row: int, first: int, last: int, height: float = 15) -> None:
    """A body row: a hairline under it, ``height`` points tall."""
    for col in range(first, last + 1):
        ws.cell(row, col).border = Border(bottom=Side(style="thin", color=HAIR))
    ws.row_dimensions[row].height = height


def _buttons(af: AutoFilter, n: int, keep: Sequence[int]) -> AutoFilter:
    """Filter buttons only on the ``keep`` positions (0-based) of ``n`` columns."""
    af.filterColumn = [FilterColumn(colId=i, hiddenButton=True) for i in range(n) if i not in keep]
    return af


def sheet_filter(ws, first_col: int, header_row: int, last_col: int, last_row: int, keep: Sequence[int]) -> None:
    """The sheet's filter over one table, with buttons only on ``keep``."""
    ref = "%s%d:%s%d" % (L(first_col), header_row, L(last_col), max(last_row, header_row + 1))
    ws.auto_filter = _buttons(AutoFilter(ref=ref), last_col - first_col + 1, keep)


def excel_table(ws, name: str, first_col: int, header_row: int, last_col: int, last_row: int,
                keep: Sequence[int]) -> Table:
    """An Excel table with no banding, its filter buttons only on ``keep``."""
    ref = "%s%d:%s%d" % (L(first_col), header_row, L(last_col), max(last_row, header_row + 1))
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
    t.autoFilter = _buttons(AutoFilter(ref=ref), last_col - first_col + 1, keep)
    ws.add_table(t)
    return t


def repeats_hidden(ws, first_col: int, n_cols: int, first_row: int, last_row: int) -> None:
    """A name the row above already shows turns white (the round 2 pattern),
    so every row keeps its names for the filters. Each column is hidden only
    when it and every column left of it repeat."""
    if last_row < first_row:
        return
    for k in range(n_cols):
        col = L(first_col + k)
        same = ",".join("$%s%d=$%s%d" % (L(first_col + j), first_row, L(first_col + j), first_row - 1)
                        for j in range(k + 1))
        ws.conditional_formatting.add("%s%d:%s%d" % (col, first_row, col, last_row), FormulaRule(
            formula=["AND(%s)" % same], font=Font(color=K.PAPER)))


def product_rules(ws, first_col: int, last_col: int, rows: Sequence[int]) -> None:
    """A thin INK rule over each product's first row."""
    for r in rows:
        for col in range(first_col, last_col + 1):
            c = ws.cell(r, col)
            c.border = Border(top=Side(style="thin", color=K.INK), bottom=c.border.bottom)


_WIN = re.compile(r"[A-Za-z]:\\[^\s,;\"]+")
_NIX = re.compile(r"(?<![\w.:/])/(?:[\w.-]+/){2,}[\w.-]+")           # not a web address's path


def short_paths(text: str) -> str:
    """A full local path in a note, shortened to its last two folders: the
    folder is printed once, on Run."""
    def cut(m, sep):
        p = m.group(0)
        tail = p.rstrip(".")
        parts = [x for x in tail.split(sep) if x]
        return "…" + sep + sep.join(parts[-2:]) + p[len(tail):]
    text = _WIN.sub(lambda m: cut(m, "\\"), text)
    return _NIX.sub(lambda m: cut(m, "/"), text)


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- Evidence

SPELL_HEAD = ("Spell from", "Peak quarter", "Peak", "Peak ÷ median", "Robust z", "Years per spell this bad",
              "Deepest dip (sd)", "Note")
DEPART_HEAD = ("First quarter", "Last quarter", "Worse or better", "Average distance from trend", "Robust z",
               "Rank among windows of its length", "Window (quarters)")


def evidence(ws, series: Sequence[dict], id_names: Sequence[str], quarter: Callable[[str], str]) -> dict:
    """Two Excel tables, Spells and Departures, each row naming its series by
    ``id_names`` (Product, Measure, Source in the book). ``series``: dicts with
    ``ids`` (one value per id name) and ``ev`` (evidence.evidence's result)."""
    ni = len(id_names)
    B = 2
    S0 = B + ni                                          # the first figure column
    sp_last, dp_last = S0 + len(SPELL_HEAD) - 1, S0 + len(DEPART_HEAD) - 1
    title(ws, "Evidence for each judgment",
          "Spells worse than the median and temporary departures from trend, for every series. Robust z measures "
          "how far a peak sits from the rest of the history; 3.5 or more is unusual.", sp_last)
    spells = [(s["ids"], sp) for s in series for sp in s["ev"]["spells"]]
    departs = [(s["ids"], d) for s in series for d in s["ev"]["departures"]]
    out = {}

    def block(row, name, table_name, head, items, last, write):
        row = section(ws, row, "%s · %d rows" % (name, len(items)), B, last)
        h = row
        row = header(ws, row, list(id_names) + list(head), B, right=right_of(head, ni))
        first = row
        prev = None
        starts = []
        for ids, item in items:
            for j, v in enumerate(ids):
                c = ws.cell(row, B + j, v)
                c.font = F_BOLD if j == 0 else F_BODY
                c.alignment = Alignment(vertical="top")
            height = write(row, item)
            body(ws, row, B, last, height)
            if prev is None or ids[0] != prev:
                starts.append(row)
            prev = ids[0]
            row += 1
        if not items:
            body(ws, row, B, last)
            row += 1
        product_rules(ws, B, last, starts[1:])
        repeats_hidden(ws, B, ni, first, row - 1)
        z = L(S0 + head.index("Robust z"))
        ws.conditional_formatting.add("%s%d:%s%d" % (z, first, z, row - 1), FormulaRule(
            formula=["AND(ISNUMBER($%s%d),ABS($%s%d)>=3.5)" % (z, first, z, first)], font=Font(bold=True)))
        excel_table(ws, table_name, B, h, last, row - 1, keep=range(ni))
        out[table_name] = (h, row - 1)
        return row + 1

    def right_of(head, n):
        nums = {"Peak", "Peak ÷ median", "Robust z", "Years per spell this bad", "Deepest dip (sd)",
                "Average distance from trend", "Rank among windows of its length", "Window (quarters)"}
        return [n + i for i, h in enumerate(head) if h in nums]

    note_px = 300

    def spell(row, sp):
        vals = [quarter(sp["start"]), quarter(sp["peak_date"]), sp["peak"], sp["peak_over_median"], sp["robust_z"],
                sp["return_period_years"], sp["dip"]["in_sd_of_change"] if sp["dip"] else None, sp["note"] or None]
        fmts = [None, None, "0.00", "0.00", Z_FORMAT, "0.0", "0.0", None]
        for k, (v, f) in enumerate(zip(vals, fmts)):
            c = ws.cell(row, S0 + k, v)
            c.font = F_SLATE if k < 2 else F_BODY
            if f:
                c.number_format = f
                c.alignment = RIGHT_TOP
            else:
                c.alignment = Alignment(vertical="top", wrap_text=k == 7, indent=1 if k == 7 else 0)
        return 15 * lines(sp["note"], note_px)

    def depart(row, d):
        vals = [quarter(d["first"]), quarter(d["last"]), d["direction"], d["mean_departure"], d["robust_z"],
                "1 of %d" % d["of"], d["length"]]
        fmts = [None, None, None, "0.00", Z_FORMAT, None, "0"]
        for k, (v, f) in enumerate(zip(vals, fmts)):
            c = ws.cell(row, S0 + k, v)
            c.font = F_SLATE if k < 2 else F_BODY
            c.alignment = RIGHT_TOP if f or k == 5 else Alignment(vertical="top")
            if f:
                c.number_format = f
        return 15

    r = block(4, "Spells worse than the median", "Spells", SPELL_HEAD, spells, sp_last, spell)
    block(r, "Temporary departures from trend", "Departures", DEPART_HEAD, departs, dp_last, depart)
    idw = id_widths(id_names, [s["ids"] for s in series])
    cols = {L(B + j): w for j, w in enumerate(idw)}
    for k, w in enumerate((90, 90, 120, 120, 80, 130, 110, note_px)):
        cols[L(S0 + k)] = w
    widths(ws, cols)
    ws.freeze_panes = ws.cell(1, S0).coordinate
    return out


def id_widths(id_names: Sequence[str], ids: Sequence[Sequence[str]]) -> List[int]:
    """Widths for the Product, Measure and Source columns (or Series), to
    their longest name; the first, shown bold, a little wider."""
    out = []
    for j, nm in enumerate(id_names):
        vals = [x[j] for x in ids] + [nm]
        out.append(fit(vals, 90, 420, per=7.4 if j == 0 else 7.0))
    return out


# ---------------------------------------------------------------- Glossary

GLOSSARY_HEAD = ("Tab", "Term", "What it means", "How it is calculated")
GLOSSARY_PX = (120, 240, 640, 806)
LINE_PT = 13.5                                   # Calibri 10 at 1.35


def _glossary_row(ws, r, first, vals, px_):
    """One term: the tab (when given) and the calculation SLATE, the term bold."""
    term_at = len(vals) - 3
    for k, v in enumerate(vals):
        c = ws.cell(r, first + k, v)
        c.alignment = TOP
        c.font = Font(name="Calibri", size=10, bold=k == term_at,
                      color=K.SLATE if k < term_at or k == len(vals) - 1 else K.INK_TEXT)
    n = max(lines(v, w, per=5.5) for v, w in zip(vals, px_))
    body(ws, r, first, first + len(vals) - 1, max(15, LINE_PT * n + 2))


def glossary(ws, rows: Sequence[Tuple[str, ...]], with_tab: bool = True) -> int:
    """One row per term, Calibri 10 wrapped: with ``with_tab`` (the book) a Tab
    column first, filterable, its repeats white; ``rows`` are (tab, term,
    meaning, calculation), or (term, meaning, calculation) without a tab.
    Returns the last row."""
    head = GLOSSARY_HEAD if with_tab else GLOSSARY_HEAD[1:]
    px_ = GLOSSARY_PX if with_tab else GLOSSARY_PX[1:]
    last = 1 + len(head)
    title(ws, "Glossary", "What each term means, and how the workbook calculates it."
          + (" Grouped by the tab the term first appears on." if with_tab else ""), last)
    header(ws, 4, head, 2)
    r = 5
    for vals in rows:
        _glossary_row(ws, r, 2, vals, px_)
        r += 1
    widths(ws, {L(2 + k): w for k, w in enumerate(px_)})
    if with_tab:
        repeats_hidden(ws, 2, 1, 5, r - 1)
        sheet_filter(ws, 2, 4, last, r - 1, keep=(0,))
        ws.freeze_panes = "D5"
    else:
        ws.freeze_panes = "C5"
    return r - 1


def append_terms(ws, tab: str, terms: Sequence[Tuple[str, str, str]]) -> int:
    """Add ``terms`` (term, meaning, calculation) to a Glossary written by
    ``glossary``, under ``tab``, and take them into its filter. For the peer
    terms the peers build folds into the book's Glossary. Returns the last row."""
    last = ws.max_row
    while last > 4 and ws.cell(last, 3).value is None:
        last -= 1
    r = last + 1
    for term, meaning, calc in terms:
        _glossary_row(ws, r, 2, (tab, term, meaning, calc), GLOSSARY_PX)
        r += 1
    if ws.auto_filter.ref:
        a, _ = ws.auto_filter.ref.split(":")
        ws.auto_filter.ref = "%s:%s%d" % (a, L(1 + len(GLOSSARY_HEAD)), r - 1)
    repeats_hidden(ws, 2, 1, last + 1, r - 1)
    return r - 1


# ---------------------------------------------------------------- Sources

SHOWN = {"measure": "Measure", "population": "Who is in it", "call-report": "Call Report lines",
         "numerator": "Numerator", "denominator": "Denominator", "basis": "Basis", "as-of": "As of",
         "source": "Source", "checked": "Checked", "prepared-by": "Prepared by", "prepared-on": "Prepared on",
         "note": "Note"}
_NAMED = re.compile(r"^([A-Z][^:.;,]{0,60}): (.+)$", re.S)


def _line(key: str, text: str) -> str:
    """A note line as written in the file (after its '#')."""
    return text if key == "note" else "%s: %s" % (key, text)


def sources(ws, files: Sequence[dict], id_names: Sequence[str], core: Sequence[str],
            reporting: Optional[dict] = None, change_key: str = "reporting-change",
            whens: Callable = None) -> dict:
    """Sources in three sections. ``files``: dicts with ``ids`` (a value per
    id name), ``path``, ``rows``, ``first``, ``last`` and ``notes`` (the
    file's (key, text) lines). A line identical in a tenth of the files or more (two at least) is a
    shared note, printed once and keyed S1, S2, ...; a ``change_key`` line is
    shown by its quarters (``whens``); the rest are the file's own, verbatim.
    ``reporting``: ``{"changes", "about", "source_name"}`` for the last
    section, or None. Returns where each section is."""
    ni = len(id_names)
    B = 2
    c_file, c_rows, c_first, c_last, c_shared, c_chg, c_own = (B + ni + k for k in range(7))
    last = c_own
    title(ws, "Sources", "Each series file's description lines, as written in the file. Notes shared by many files "
                         "are printed once, under Shared notes, and named in the table. A required line the file "
                         "does not give is marked.", last)
    count: Dict[str, int] = {}
    for f in files:
        for key, text in dict.fromkeys(f["notes"]):
            if key != change_key:
                count[_line(key, text)] = count.get(_line(key, text), 0) + 1
    # "Shared by many": in a tenth of the files or more, and at least two.
    many = max(2, -(-len(files) // 10))
    shared: Dict[str, str] = {}
    for f in files:
        for key, text in f["notes"]:
            ln = _line(key, text)
            if key != change_key and count[ln] >= many and ln not in shared:
                shared[ln] = "S%d" % (len(shared) + 1)
    idw = id_widths(id_names, [f["ids"] for f in files])
    px_ = dict(zip((L(B + j) for j in range(ni)), idw))
    px_.update({L(c_file): fit([f["path"].name for f in files], 160, 270, per=6.6), L(c_rows): 50,
                L(c_first): 84, L(c_last): 84, L(c_shared): 110, L(c_chg): 170, L(c_own): 480})
    widths(ws, px_)
    span_px = sum(px_[L(c)] for c in range(B + 1, last + 1)) - px_[L(B + 1)]
    out = {}

    # Shared notes
    r = section(ws, 4, "Shared notes", B, last)
    out["shared"] = r
    for ln, key in shared.items():
        text = short_paths(ln)
        m = _NAMED.match(text)
        name, rest = (m.group(1), m.group(2)) if m else (None, text)
        ws.cell(r, B, key).font = F_SMALL_SLATE
        ws.cell(r, B + 1, name).font = F_SMALL_BOLD
        c = ws.cell(r, B + 2, rest)
        c.font = F_SMALL
        for col in (B, B + 1, B + 2):
            ws.cell(r, col).alignment = TOP
        ws.merge_cells(start_row=r, start_column=B + 2, end_row=r, end_column=last)
        body(ws, r, B, last, max(15, LINE_PT * max(lines(rest, span_px, per=5.5),
                                                   lines(name, px_[L(B + 1)], per=6.0)) + 2))
        r += 1
    if not shared:
        ws.cell(r, B, "None: no line is in more than one file.").font = F_SMALL_SLATE
        body(ws, r, B, last)
        r += 1

    # Every series file
    r = section(ws, r + 1, "Every series file · %d rows" % len(files), B, last)
    h = r
    r = header(ws, r, list(id_names) + ["File", "Rows", "First", "Last", "Shared notes", "Reporting changes",
                                        "The file's own notes · lines it does not give"], B, right=(ni + 1,))
    first = r
    starts, prev = [], None
    for f in files:
        given = {k for k, _ in f["notes"]}
        missing = [SHOWN.get(k, k) for k in core if k not in given]
        own = [short_paths(_line(k, t)) for k, t in f["notes"]
               if k != change_key and _line(k, t) not in shared]
        keys = sorted(dict.fromkeys(shared[_line(k, t)] for k, t in f["notes"]
                                  if k != change_key and _line(k, t) in shared), key=lambda x: int(x[1:]))
        chg = whens(f["notes"]) if whens else []
        for j, v in enumerate(f["ids"]):
            ws.cell(r, B + j, v).font = F_SMALL_BOLD if j == 0 else F_SMALL
        vals = {c_file: f["path"].name, c_rows: f["rows"], c_first: f["first"], c_last: f["last"],
                c_shared: " ".join(keys) or None, c_chg: " · ".join(chg) or None}
        for col, v in vals.items():
            c = ws.cell(r, col, v)
            c.font = F_MONO if col == c_file else F_SMALL
        ws.cell(r, c_rows).number_format = "#,##0"
        text = " ".join(own)
        if missing:
            tail = "Not stated: %s." % ", ".join(missing)
            rich = CellRichText([TextBlock(InlineFont(rFont="Calibri", sz=10, color=K.INK_TEXT), text + " ")] if text
                                else [])
            rich.append(TextBlock(InlineFont(rFont="Calibri", sz=10, b=True, color=K.CRIMSON), tail))
            ws.cell(r, c_own).value = rich
            text = (text + " " + tail).strip()
        else:
            ws.cell(r, c_own, text or None).font = F_SMALL
        for col in range(B, last + 1):
            ws.cell(r, col).alignment = RIGHT_TOP if col == c_rows else Alignment(
                vertical="top", wrap_text=col in (c_own, c_file, c_chg, c_shared), indent=1 if col == c_first else 0)
        n = max(lines(text, px_[L(c_own)], per=5.5), lines(vals[c_chg], px_[L(c_chg)], per=5.8),
                lines(vals[c_file], px_[L(c_file)], per=6.6), lines(vals[c_shared], px_[L(c_shared)], per=5.8))
        body(ws, r, B, last, max(15, LINE_PT * n + 2))
        if prev is None or f["ids"][0] != prev:
            starts.append(r)
        prev = f["ids"][0]
        r += 1
    if not files:
        body(ws, r, B, last)
        r += 1
    product_rules(ws, B, last, starts[1:])
    repeats_hidden(ws, B, ni, first, r - 1)
    sheet_filter(ws, B, h, last, r - 1, keep=range(ni))
    out["files"] = (h, r - 1)

    if reporting is not None:
        # The registry's seven columns over the sheet's own: Call Report
        # items, What changed and Source document over the wider ones.
        if ni >= 3:
            groups = [(B, B), (B + 1, B + 1), (B + 2, B + 2), (c_file, c_file), (c_rows, c_last),
                      (c_shared, c_chg), (c_own, c_own)]
        else:
            groups = [(B, B), (c_file, c_file), (c_rows, c_rows), (c_first, c_first), (c_last, c_shared),
                      (c_chg, c_chg), (c_own, c_own)]
        out["reporting"] = reporting_section(ws, r + 1, reporting["changes"], reporting["about"], B, last, groups,
                                             reporting.get("source_name"))
    ws.freeze_panes = ws.cell(1, B + ni).coordinate
    return out


RC_HEAD = ("Change", "Took effect", "Products touched", "Measures touched", "Call Report items", "What changed",
           "Source document")


def reporting_section(ws, row: int, changes: Sequence[dict], about: str, B: int, last: int,
                      groups: Sequence[Tuple[int, int]], source_name: Optional[str] = None) -> dict:
    """The registry's table under its own heading: the registry's own words
    about itself, then one row per change, each of its seven columns over
    ``groups`` (first, last column; merged where more than one), every source
    document linked to its address, a second one on the row under. Returns
    where it is."""
    from .reporting_changes import when
    r = section(ws, row, "Reporting changes · %d rows%s" % (len(changes), ", from %s" % source_name
                                                                 if source_name else ""), B, last)
    gpx = [sum((ws.column_dimensions[L(c)].width or 8.43) * 7 + 5 for c in range(a, b + 1)) for a, b in groups]
    span_px = sum((ws.column_dimensions[L(c)].width or 8.43) * 7 + 5 for c in range(B, last + 1))
    c = ws.cell(r, B, about)
    c.font = F_SMALL_SLATE
    c.alignment = TOP
    ws.merge_cells(start_row=r, start_column=B, end_row=r, end_column=last)
    ws.row_dimensions[r].height = max(15, LINE_PT * lines(about, span_px, per=5.5) + 2)
    about_row = r
    r += 1

    def put(r_, k, v, font):
        a, b = groups[k]
        cell = ws.cell(r_, a, v)
        cell.font = font
        cell.alignment = TOP
        if b > a:
            ws.merge_cells(start_row=r_, start_column=a, end_row=r_, end_column=b)
        return cell

    h = r
    names = [None] * (last - B + 1)
    for (a, _), nm in zip(groups, RC_HEAD):
        names[a - B] = nm
    header(ws, r, names, B)
    for a, b in groups:
        if b > a:
            ws.merge_cells(start_row=r, start_column=a, end_row=r, end_column=b)
    r += 1
    first = r
    for ch in changes:
        vals = (ch["name"], when(ch), ", ".join(ch["products"]) or "None of the products",
                ", ".join(ch["measures"]) or "None", "; ".join(ch["call_report_items"]) or "None stated",
                ch["what_changed"])
        n = 1
        for k, v in enumerate(vals):
            put(r, k, v, F_SMALL_BOLD if k == 0 else F_SMALL)
            n = max(n, lines(v, gpx[k], per=5.5))
        for i, s in enumerate(ch["sources"]):
            if i:                                    # the change's next source, on the row under, no rule between
                r += 1
                for k in range(6):
                    put(r, k, None, F_SMALL)
                n = 1
            cell = put(r, 6, s["citation"], F_LINK)
            cell.hyperlink = s["url"]
            n = max(n, lines(s["citation"], gpx[6], per=5.5))
            ws.row_dimensions[r].height = max(15, LINE_PT * n + 2)
        body(ws, r, B, last, ws.row_dimensions[r].height)
        r += 1
    return {"about": about_row, "header": h, "rows": (first, r - 1), "columns": [a for a, _ in groups]}


# ---------------------------------------------------------------- Run

def run_grid(id_names: Sequence[str], ids: Sequence[Sequence[str]], files: Sequence[str]) -> dict:
    """Run's columns: the series' names, then First, Last, Rows, File and
    SHA-256, which Left out as built and the live sections reuse."""
    B = 2
    ni = len(id_names)
    cols = {"ids": list(range(B, B + ni)), "first": B + ni, "last": B + ni + 1, "rows": B + ni + 2,
            "file": B + ni + 3, "sha": B + ni + 4}
    idw = id_widths(id_names, ids)
    idw[0] = max(idw[0], 150)                    # This build's labels sit over it
    px_ = {L(c): w for c, w in zip(cols["ids"], idw)}
    px_.update({L(cols["first"]): 84, L(cols["last"]): 84, L(cols["rows"]): 56,
                L(cols["file"]): fit(files, 240, 470, per=6.6), L(cols["sha"]): 440})
    cols["px"] = px_
    cols["last_col"] = cols["sha"]
    return cols


def run_build(ws, grid: dict, rows: Sequence[Tuple[str, object]], folders: Sequence[str]) -> int:
    """Title and This build: each row's label and value, then the series
    folder once. Returns the next free row."""
    last = grid["last_col"]
    widths(ws, grid["px"])
    title(ws, "Run", "The build, each input file with its SHA-256 fingerprint, and the settings in use.", last)
    r = section(ws, 4, "This build", 2, last)
    v_col = 3
    for lbl, v in list(rows[:2]) + [("Series folder" if len(folders) < 2 else "Series folders",
                                     "; ".join(folders))] + list(rows[2:]):
        ws.cell(r, 2, lbl).font = F_SLATE
        c = ws.cell(r, v_col, v)
        c.font = F_MONO if lbl.startswith("Series folder") else F_BODY
        c.alignment = Alignment(vertical="center")
        body(ws, r, 2, last)
        r += 1
    return r


def run_files(ws, row: int, grid: dict, id_names: Sequence[str], files: Sequence[dict], heading: str) -> int:
    """The Files table: names split, the file name only, rows, first and last,
    the SHA-256 in Consolas 9 SLATE. ``files``: dicts with ``ids``, ``name``,
    ``rows``, ``first``, ``last``, ``sha``. Returns the next free row."""
    last = grid["last_col"]
    r = section(ws, row, heading, 2, last)
    names = [None] * (last - 1)
    for j, nm in enumerate(id_names):
        names[grid["ids"][j] - 2] = nm
    for key, nm in (("first", "First"), ("last", "Last"), ("rows", "Rows"), ("file", "File"), ("sha", "SHA-256")):
        names[grid[key] - 2] = nm
    h = r
    r = header(ws, r, names, 2, right=(grid["rows"] - 2,))
    first = r
    for f in files:
        for j, v in enumerate(f["ids"]):
            ws.cell(r, grid["ids"][j], v).font = F_BODY
        ws.cell(r, grid["first"], f["first"]).font = F_BODY
        ws.cell(r, grid["last"], f["last"]).font = F_BODY
        c = ws.cell(r, grid["rows"], f["rows"])
        c.font = F_BODY
        c.number_format = "#,##0"
        c = ws.cell(r, grid["file"], f["name"])
        c.font = F_MONO
        c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
        ws.cell(r, grid["sha"], f["sha"]).font = F_HASH
        body(ws, r, 2, last, 15 * lines(f["name"], grid["px"][L(grid["file"])], per=6.6))
        r += 1
    repeats_hidden(ws, grid["ids"][0], len(id_names), first, r - 1)
    sheet_filter(ws, 2, h, last, r - 1, keep=[c - 2 for c in grid["ids"]])
    return r + 1


def run_left_out(ws, row: int, grid: dict, path: Path) -> int:
    """Left out as built: the file's name, rows and SHA-256 on the Files
    columns, then one row per span it lists, From and To under First and
    Last, Why under File. Returns the next free row."""
    last = grid["last_col"]
    path = Path(path)
    with open(path, newline="", encoding="utf-8") as fh:
        data = [r_ for r_ in csv.reader(fh) if r_ and not r_[0].startswith("#")]
    head, spans = data[0], data[1:]
    r = section(ws, row, "Left out as built", 2, last)
    ws.cell(r, 2, "File").font = F_SLATE
    ws.cell(r, grid["file"], path.name).font = F_MONO
    c = ws.cell(r, grid["rows"], len(spans))
    c.font = F_BODY
    c.number_format = "#,##0"
    ws.cell(r, grid["sha"], sha(path)).font = F_HASH
    body(ws, r, 2, last)
    r += 1
    names = [None] * (last - 1)
    n_ids = len(head) - 3
    for j in range(n_ids):
        names[grid["ids"][j] - 2] = head[j]
    names[grid["first"] - 2], names[grid["last"] - 2], names[grid["file"] - 2] = "From", "To", "Why"
    r = header(ws, r, names, 2)
    first_span = r
    for sp in spans:
        for j in range(n_ids):
            ws.cell(r, grid["ids"][j], sp[j]).font = F_BODY
        ws.cell(r, grid["first"], sp[n_ids]).font = F_BODY
        ws.cell(r, grid["last"], sp[n_ids + 1]).font = F_BODY
        c = ws.cell(r, grid["file"], sp[n_ids + 2])
        c.font = F_BODY
        for col in range(2, last + 1):
            ws.cell(r, col).alignment = Alignment(vertical="top", wrap_text=col == grid["file"])
        width_ = grid["px"][L(grid["file"])] + grid["px"][L(grid["sha"])]
        ws.merge_cells(start_row=r, start_column=grid["file"], end_row=r, end_column=grid["sha"])
        body(ws, r, 2, last, 15 * lines(sp[n_ids + 2], width_, per=6.4))
        r += 1
    repeats_hidden(ws, grid["ids"][0], n_ids, first_span, r - 1)
    return r + 1


def run_columns(ws) -> dict:
    """Run's File and SHA-256 columns, read from its Files header."""
    for r in range(1, ws.max_row + 1):
        names = {ws.cell(r, c).value: c for c in range(2, ws.max_column + 1)}
        if "File" in names and "SHA-256" in names:
            return {"file": names["File"], "sha": names["SHA-256"], "last_col": names["SHA-256"]}
    raise ValueError("Run has no Files table to align with")


def run_signals(ws, sources: Sequence[Tuple[str, str, str]]) -> int:
    """The public data behind Signals, after what Run holds, on its columns:
    what each source is over the name columns, its file name under File, its
    SHA-256 under SHA-256. Returns the last row."""
    grid = run_columns(ws)
    last = grid["last_col"]
    r = section(ws, ws.max_row + 2, "Signals: the public data behind the tab", 2, last)
    names = [None] * (last - 1)
    names[0], names[grid["file"] - 2], names[grid["sha"] - 2] = "Source", "File", "SHA-256"
    r = header(ws, r, names, 2)
    for what, file, digest in sources:
        ws.cell(r, 2, what).font = F_BODY
        c = ws.cell(r, grid["file"], Path(file).name if file else None)
        c.font = F_MONO
        ws.cell(r, grid["sha"], digest or None).font = F_HASH
        body(ws, r, 2, last)
        r += 1
    return r - 1


# ---------------------------------------------------------------- Data and Signals data

def first_with_values(ws, first_row: int, last_row: int, first_col: int, last_col: int) -> Optional[int]:
    """The first row from ``first_row`` where any of the columns holds a
    number (a formula is not a value), or None."""
    for r in range(first_row, last_row + 1):
        for c in range(first_col, last_col + 1):
            v = ws.cell(r, c).value
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return r
    return None


def data_layout(ws, header_row: int, first_row: int, last_row: int, last_col: int, number_format: str,
                col_px: float = 117) -> Tuple[int, int]:
    """A data tab: the header MIST, Arial 9 bold INK, wrapped, 45 pt, a STONE
    rule; values in ``number_format``; frozen under the header after column
    A; and the quarters before the first one with a value on the sheet in a
    collapsed outline group, the calendar itself unchanged. Returns the rows
    grouped (first, last), or (0, 0) when the first quarter has a value."""
    for col in range(1, last_col + 1):
        c = ws.cell(header_row, col)
        c.fill = K.solid(K.MIST)
        c.font = Font(name="Arial", bold=True, size=9, color=K.INK)
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = Border(bottom=Side(style="thin", color=K.STONE))
        if col > 1:
            ws.column_dimensions[L(col)].width = px(col_px)
    ws.row_dimensions[header_row].height = 45
    for r in range(first_row, last_row + 1 if number_format else first_row):
        for col in range(2, last_col + 1):
            ws.cell(r, col).number_format = number_format
    ws.freeze_panes = ws.cell(header_row + 1, 2).coordinate
    hit = first_with_values(ws, first_row, last_row, 2, last_col)
    if hit is not None and hit > first_row:
        ws.row_dimensions.group(first_row, hit - 1, hidden=True)
        ws.sheet_properties.outlinePr.summaryBelow = True
        return first_row, hit - 1
    return 0, 0
