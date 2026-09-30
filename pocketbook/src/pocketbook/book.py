"""The workbook: the answers for a run go in, and the results come out.

Ruling OC-22 (25 Sep 2026): nobody types a command. The launcher's two
buttons call the two functions here:

    set_up(extract)   writes or refreshes the tabs a person fills in: Start
                      here, Control, Columns (with the odd values and what is
                      remembered), Look. Answers already given are kept, and so
                      are the results of the last run.
    run(book)         reads the answers, runs the engine, and writes the results
                      into the same workbook: Pockets, Paid cost kept, Grids,
                      Split (results.py, the redesign's phase 3), or New
                      variables for a test from a pre-spec (confirm_tab.py),
                      Record (record.py: Check and the Log, phase 4), and Start
                      here's findings. It loads the workbook once and saves it
                      once.

A problem is never a traceback: it is a sentence naming the tab and cell, shown
in the launcher and on Record's Every Run. A run that can't write its results changes
nothing else (no memory, no record), so a refused run leaves no trace.
"""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import config as cfgmod
from . import control, engine, meanings, memory, perm, profile, stats
from . import checks, confirmatory, prespec             # fixes 3.15 to 3.18
from . import live                                      # OC-40: the judging settings, live in the workbook
from . import confirm_tab                               # 4b and 4e: the confirmatory test's tab
from . import choices as ch                             # the redesign: what the launcher chose
from . import results                                   # the redesign, phase 3: the result tabs
from . import record                                    # the redesign, phase 4: Check and the Log as Record
from . import scout, scout_tab                          # Goal 2 item 9: scouting, then the confirmation
from .excel_lists import load as _load                   # opens a workbook Excel saved with its dropdowns kept
from .house import MIST as READ_ONLY
from .ingest import Table, read_table

INK, CANVAS, SLATE, PAPER, NEEDS = "16130F", "F4F1EC", "57534B", "FFFFFF", "F7DEDE"
WORSE_FILL, LUCK_FILL = "F7DEDE", "FFF1D6"
GREEN, RED = "63BE7B", "F8696B"
#: the tabs a person fills in, in the redesign's order (phase 2 merged Odd values and Learned into Columns)
INPUT_TABS = ("Start here", "Control", "Columns", "Look")
#: tabs an older workbook carries that the redesign folded into others: taken off at Set up (and Materiality,
#: now the panel on Control, at Run)
FOLDED_TABS = ("Odd values", "Learned", "Materiality")
RESULT_TABS = (scout.SHEET, confirm_tab.SHEET) + results.TABS + (record.SHEET,)
#: tabs the redesign's phase 4 replaced: a Run takes them off an older workbook (the Log becomes the hidden _log)
OLD_RESULT_TABS = (confirm_tab.OLD_SHEET, record.OLD_CHECK)
LOG_FIRST = record.LOG_FIRST            # the newest line on the hidden _log (the Log tab it replaces)
LOG_NOTE = record.LOG_NOTE
HELPERS = ("_options", "_meanings", "_about")
ABOUT = "_about"
FOUND = "_found"          # what the last Run found, for Start here's tiles and top five (kept through Set up)
CONFIRM_CELL = "C3"      # "Checked every column?"
# Set up's note on Columns!D3 for columns the Yes in C3 doesn't cover yet; a Run takes it off again
NEW_COLS_NOTE = "New since the last check: {}. Check them, then set C3 to Yes again."
CONFIRM_NOTE = "Run won't start until this is Yes."
#: the firm, 29 Sep 2026: "Why would we ever want to make it appear?" The columns not picked in the launcher are
#: hidden rows, not asked about and not counted: they are kept, so picking one later needs no new answers
HIDDEN_NOTE = "Only the columns this Run uses are shown; {} not picked in the launcher are hidden."
# Columns tab (the redesign, phase 2: Columns, Odd values and Learned on one tab), one column per thing said about
# an extract column, in the spec's order, then the answers the spec has no place for, then hidden keys
(C_NAME, C_SAMPLES, C_MEANS, C_WHY, C_BLANK, C_ODD, C_TREAT, C_EDGES, C_REMEMBERED, C_FORGET, C_LOOK, C_IS, C_SHOW,
 C_PERIOD, C_DEFINE) = range(2, 17)
C_SUGG = 17              # hidden: the meaning Set up suggested, so a refusal can name what was changed
C_MADE = 18              # hidden: for a new column, what Set up made it from ("INCOME ÷ SALES")
C_QKEY = 19              # hidden: an odd value's question ("FICO|repeated_value|-9999"), or a row's key
COL_HEAD = 12            # the table's header row, under the method note
COL_FIRST = COL_HEAD + 1  # first column row on the Columns tab
TABLE_END = "table|end"  # C_QKEY on the row after the table: the new-column block follows
TREAT = ("Real", "Missing")
FORGET_YES = "Yes"
COLUMNS_HEADS = {C_NAME: "Column", C_SAMPLES: "Samples", C_MEANS: "What it is ↻", C_WHY: "Why we think so",
                 C_BLANK: "Blank", C_ODD: "Odd values", C_TREAT: "Treat as ↻", C_EDGES: "Band edges ↻",
                 C_REMEMBERED: "Remembered", C_FORGET: "Forget? ↻", C_LOOK: "Check first",
                 C_IS: "Yes means ↻", C_SHOW: "Show per pocket ↻", C_PERIOD: "Period ↻",
                 C_DEFINE: "In your words"}
COLUMNS_METHOD = [
    ("What it is", "Set up guesses each column's meaning from its name and values; the reason is beside it. Fix "
                   "any that's wrong. Confirmed meanings are remembered for the next extract."),
    ("Odd values", "Values that may be codes rather than real numbers: one value far more often than any other, or "
                   "negatives in a column that's mostly positive. Missing is treated as blank and counted."),
    ("Treat as", "Answer Real or Missing. One left blank is used as recorded."),
    ("Band edges", "Blank means Control's setting. Type edges as 620; 680; 740, or every 20. Look shows what each "
                   "would cut, live."),
    ("Remembered", "Set Forget? to Yes to drop what was learned about a column at the next Run. It then waits here "
                   "for you to confirm it again. Answers marked ↻ take effect at the next Run."),
]


SHOW_OPTIONS = ("median", "average")
PERIOD_OPTIONS = {"per year": "per_year", "per month": "per_month", "one-time": "one_time"}
#: What are you running? (Control's first row; the firm, 26 Sep 2026.) Each answer's own minimum of columns:
#: where the book bleeds needs the five core columns and never a date; testing a new variable needs only what it
#: uses: the key, the outcome, and the origination date that tells the loans kept back from the rest (the tested
#: column and the pre-spec's strata are checked against Columns below). Its booked amount, GCO and RANR are
#: optional (the firm, 26 Sep 2026: "what's the point in that if you are searching for possibly important
#: variables to the outcome?"). The follow-up, scout first or test from a pre-spec, is asked only for a new
#: variable.
RUN_KIND, STEP = "run_kind", "new_variable_step"
BLEED, NEW_VARIABLE, SCOUT, FROM_PRESPEC = "bleed", "new_variable", "scout", "prespec"
SCOUT_KEY = "_scout"
NEEDS_COLUMNS = {BLEED: cfgmod.CORE, NEW_VARIABLE: cfgmod.TESTING_CORE + ("origination_date",)}


@dataclass
class Outcome:
    ok: bool
    book: Path
    lines: list[str] = field(default_factory=list)      # what the launcher shows, in plain words
    problems: list[str] = field(default_factory=list)   # a refused Run's problems, each naming its tab and cell
    summary: dict = field(default_factory=dict)         # a finished Run's headline, for the launcher's last step


#: The product's name, and the workbook's: "loans - PocketBook.xlsx" beside "loans.csv" (the firm, 26 Sep 2026).
#: A workbook written before the name changed ends " - Origination Cube.xlsx"; picked as the extract, it is still
#: recognised as a workbook, and Set up carries its answers into the new one.
NAME = "PocketBook"
SUFFIX, OLD_SUFFIX = f" - {NAME}.xlsx", " - Origination Cube.xlsx"


def book_for(extract: str | Path) -> Path:
    """Where the workbook for an extract lives: beside it, named after it."""
    p = Path(extract)
    return p.with_name(f"{p.stem}{SUFFIX}")


def cant_read(extract: str | Path, exc: OSError, again: str = "Run") -> str:
    """The extract couldn't be read, in words that say what to do (the bank, 30 Sep 2026: Run opened a
    PermissionError traceback in Notepad while the extract was open in Excel, or OneDrive was still syncing it).
    `again` is the button to press once it's fixed."""
    p = Path(extract)
    if isinstance(exc, FileNotFoundError):
        return (f"Couldn't find {p.name}. PocketBook looked for it in {p.parent}. Put it back there, or pick it "
                f"again with Browse, then press {again} again.")
    return (f"{p.name} can't be read: it's open in Excel, or OneDrive is still syncing it. Close it in Excel "
            f"(check for a hidden Excel window), or right-click it in File Explorer and choose Always keep on this "
            f"device. Then press {again} again.")


def workbook_picked(extract: str | Path) -> str | None:
    """The refusal when the file picked as the extract is one of the cube's workbooks."""
    name = Path(extract).name
    for suffix in (SUFFIX, OLD_SUFFIX):
        if name.endswith(suffix):
            real = name[: -len(suffix)]
            return (f"{name} is the workbook, not the loan file. Pick the extract it was set up from ({real}.csv "
                    f"or {real}.xlsx).")
    return None


#: what a column is, as the launcher's Choose tests table treats it
KIND_OF = {"key": "key", "origination_date": "date", "outcome": "out", "gco": "outd", "ranr": "outd"}


@dataclass
class Column:
    name: str
    what: str           # its meaning in the Columns tab's words: "FICO score", "Category · 3 values"
    kind: str           # key, date, out (the yes/no outcome), outd (outcome dollars), num, cat, other
    yes: int | None = None   # a column that could be the outcome: how many loans read 1 (bad); None if it couldn't
    no: int = 0              # ... 0 (good)
    other: int = 0           # ... anything else, blanks included: left out of the outcome rates and counted
    values: int | None = None   # a category: how many values it holds, blanks aside


@dataclass
class Read:
    """An extract as the launcher's Set up step reads it, before any workbook is written."""
    extract: Path
    book: Path
    loans: int
    columns: list[Column]
    chosen: "ch.Choices | None" = None      # what the workbook beside it already shows, if there is one
    problem: str | None = None
    # ORIG_YEAR, offered beside the categories when a column is marked Origination date (the firm, 30 Sep 2026):
    # kind "year", or "none" (greyed, nothing to pick) when that column's dates can't be read
    year: Column | None = None


def _outcome_picked(picked: str, sugg: dict, kept: dict, cat, facts_of: dict, many: int) -> None:
    """The outcome the analyst picked and confirmed in the launcher goes on Columns as the outcome, over what was
    suggested or answered before; any other column marked the outcome is read as what it is otherwise, a
    category (the firm, 29 Sep 2026: "there's no reason for it to automatically assign something")."""
    why = "picked and confirmed in the launcher as the outcome"
    for c, sg in list(sugg.items()):
        prior = (kept["columns"].get(c) or {}).get("means")
        if c != picked and (sg.means == meanings.OUTCOME or _to_code(prior, cat) == meanings.OUTCOME):
            f = facts_of.get(c)
            other = "category" if f is None or f.distinct <= many else "unknown"
            sugg[c] = meanings.Suggestion(c, other, f"not the outcome: {picked} is ({why})", "launcher")
            if c in kept["columns"]:
                kept["columns"][c]["means"] = None
    sugg[picked] = meanings.Suggestion(picked, meanings.OUTCOME, why, "launcher")
    if picked in kept["columns"]:
        kept["columns"][picked]["means"] = cat[meanings.OUTCOME].label


def _yes_no(table, c: str, kind: str) -> tuple[int | None, int, int]:
    """(ones, zeros, anything else) for a column that could be the outcome: one marked so, or one holding 0
    and 1 on 99% of its loans or more, as the outcome's own test reads it. (None, 0, 0) for any other."""
    from . import ingest
    vals = [r.get(c) for r in table.rows]
    nums = [ingest.parse_number(v) for v in vals]
    ones, zeros = sum(1 for x in nums if x == 1.0), sum(1 for x in nums if x == 0.0)
    other = len(vals) - ones - zeros
    if kind == "out" or (ones and zeros and other <= 0.01 * len(vals)):
        return ones, zeros, other
    return None, 0, 0


def read_extract(extract: str | Path, few_values: int = 12, many_values: int = 50,
                 memory_path: str | Path | None = None) -> Read:
    """What each column is, so the launcher can offer the right choices: its
    meaning as the workbook beside it says (if one exists), else as remembered
    or suggested. Nothing is written."""
    extract = Path(extract)
    target = book_for(extract)
    if workbook_picked(extract):
        return Read(extract, extract, 0, [], problem=workbook_picked(extract))
    try:
        table = read_table(extract)
    except OSError as exc:  # open in Excel, OneDrive still syncing it, or gone (the bank, 30 Sep 2026)
        return Read(extract, target, 0, [], problem=cant_read(extract, exc, "Set up"))
    except Exception as exc:  # the file itself: shown in words, never a traceback
        return Read(extract, target, 0, [], problem=f"Couldn't read {extract.name}: {exc}")
    kept = _answers(_earlier(target))
    mem = memory.load(memory_path)
    cat = meanings.catalog()
    sugg = meanings.suggest(table, mem["columns"], few_values=few_values, many_values=many_values)
    cols = profile.classify(table, few_values, many_values)
    made_table, made, _ = _made_columns(table, cols, kept, mem)
    out = []
    for c in list(table.columns) + [m.name for m in made]:
        code = _to_code((kept["columns"].get(c) or {}).get("means"), cat) or \
            (sugg[c].means if c in sugg else "amount")
        kind = KIND_OF.get(code) or {"band": "num", "dimension": "cat"}.get(cat[code].cut, "other")
        what = cat[code].label
        n = None
        if kind == "cat":
            n = len({str(r.get(c)) for r in made_table.rows if r.get(c) not in (None, "")})
            what = f"Category · {n:,} values" if code == "category" else f"{what} · {n:,} values"
        out.append(Column(c, what, kind, *_yes_no(made_table, c, kind), values=n))
    chosen = None
    if _earlier(target).exists():
        try:
            chosen = control.read_choices(load_workbook(_earlier(target))[control.SHEET])[0]
        except Exception:
            chosen = None
    return Read(extract, target, len(table.rows), out, chosen, year=_year_row(made_table, out))


def _year_row(table: Table, columns: list[Column]) -> Column | None:
    """The launcher's Origination year row: ORIG_YEAR, the year of the column marked Origination date, as the Run
    works it out (engine.origination_years); None when no column is marked so, or the extract has its own
    ORIG_YEAR."""
    dated = next((c.name for c in columns if c.kind == "date"), None)
    if dated is None or ch.ORIG_YEAR in table.columns:
        return None
    try:
        years = engine.origination_years(table, dated)
    except engine.DataRefused as exc:
        return Column(ch.ORIG_YEAR, f"{ch.ORIG_YEAR_LABEL}: can't be read. {exc}", "none")
    n = len({y for y in years if y != ch.NO_DATE})
    none = years.count(ch.NO_DATE)
    return Column(ch.ORIG_YEAR, f"{ch.ORIG_YEAR_LABEL}, from {dated} · {n:,} values"
                  + (f" · {none:,} with no date" if none else ""), "year", values=n)


def _earlier(book: Path) -> Path:
    """The workbook to carry answers from: this one, or the one written before the name changed."""
    old = book.with_name(book.name[: -len(SUFFIX)] + OLD_SUFFIX) if book.name.endswith(SUFFIX) else book
    return old if not book.exists() and old.exists() else book


def is_open(book: str | Path) -> bool:
    """True while the workbook is open in Excel: the file is locked (Windows) or
    Excel's owner file sits beside it."""
    book = Path(book)
    return book.exists() and (not _writable(book) or book.with_name(f"~${book.name}").exists())


def open_at(book: str | Path, sheet: str, cell: str) -> bool:
    """Make the workbook open at a cell: its tab active and the cell selected.
    False when that can't be done (the workbook is open, or has no such tab);
    the caller then opens it as it is and says the cell."""
    book = Path(book)
    if not book.exists() or is_open(book):
        return False
    wb = _load(book)
    if sheet not in wb.sheetnames or wb[sheet].sheet_state != "visible":
        return False
    ws = wb[sheet]
    wb.active = wb.sheetnames.index(sheet)
    for other in wb.worksheets:
        other.sheet_view.tabSelected = other is ws
    for sel in ws.sheet_view.selection:
        sel.activeCell = cell
        sel.sqref = cell
    try:
        wb.save(book)
    except PermissionError:
        return False
    return True


def _n(k: int, word: str) -> str:
    return f"{k:,} {word}" + ("" if k == 1 else "s")


def _title(ws, text: str, sub: str, width_cols: str = "B:H") -> None:
    first, last = width_cols.split(":")
    ws.merge_cells(f"{first}1:{last}1")
    ws[f"{first}1"] = text
    ws[f"{first}1"].font = Font(name="Arial", bold=True, size=16, color=PAPER)
    for c in range(ord(first), ord(last) + 1):
        ws[f"{chr(c)}1"].fill = PatternFill("solid", fgColor=INK)
    ws.row_dimensions[1].height = 28
    ws.merge_cells(f"{first}2:{last}2")
    ws[f"{first}2"] = sub
    ws[f"{first}2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws[f"{first}2"].font = Font(name="Calibri", size=10, color=SLATE)
    ws.row_dimensions[2].height = 32
    ws.sheet_view.showGridLines = False


def _head(ws, row: int, heads: list[str], start_col: int = 2) -> None:
    for i, h in enumerate(heads):
        c = ws.cell(row=row, column=start_col + i, value=h)
        c.font = Font(name="Calibri", bold=True, color=PAPER)
        c.fill = PatternFill("solid", fgColor=INK)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[row].height = 30


def _fit(ws, landscape: bool = True) -> None:
    """Every tab prints one page wide."""
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _col(n: int) -> str:
    return get_column_letter(n)


def _order(wb) -> None:
    """Start here first, the inputs, then the results, then the hidden helpers."""
    want = list(INPUT_TABS) + list(RESULT_TABS)
    wb._sheets.sort(key=lambda ws: (want.index(ws.title) if ws.title in want else len(want)))
    wb.active = 0
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = ws.title == "Start here"


# --------------------------------------------------------------------------
# What a person has already answered, so set_up never throws it away


#: the Columns tab before the redesign's phase 2 (header on row 5, rows from 6), for carrying its answers over
OLD_COLUMNS = {"first": 6, "means": 3, "is": 5, "edges": 6, "show": 7, "period": 13, "define": 14}


def _old_columns(ws) -> bool:
    return ws.cell(row=5, column=3).value == "What it is"


def table_rows(ws):
    """The Columns tab's table rows (the new layout), each a tuple of cells, down to the row that ends it. A row
    carrying a second odd value for the column above it has no name."""
    for r in ws.iter_rows(min_row=COL_FIRST):
        key = r[C_QKEY - 1].value if len(r) >= C_QKEY else None
        if key == TABLE_END:
            return
        yield r


def _answers(book: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"control": {}, "columns": {}, "confirmed": None, "odd": {}, "last_used": {},
                           "derived": {}}
    if not book.exists():
        return out
    wb = load_workbook(book)
    if control.SHEET in wb.sheetnames:
        cws = wb[control.SHEET]
        old = cws["C4"].value == "Choose"                  # before the redesign: last Run used in H, not F
        last_col = control.KEY_COL + 1 if old else control.LAST_COL
        for r in cws.iter_rows(min_row=control.FIRST_ROW):
            key = r[control.KEY_COL - 1].value
            if isinstance(key, str) and key.startswith(f"{control.DERIVED_KEY}|"):
                slot = key.split("|")[1]
                if slot.isdigit():
                    out["derived"][int(slot)] = tuple(r[c - 1].value for c in (3, 4, 5))
                continue
            if key and not str(key).startswith("block|"):
                out["control"][key] = (r[control.CHOOSE_COL - 1].value, r[control.OWN_COL - 1].value)
                if len(r) >= last_col and r[last_col - 1].value:
                    out["last_used"][key] = r[last_col - 1].value
    if "Columns" in wb.sheetnames:
        ws = wb["Columns"]
        out["confirmed"] = ws[CONFIRM_CELL].value
        if _old_columns(ws):
            o = OLD_COLUMNS
            for r in ws.iter_rows(min_row=o["first"], values_only=True):
                if len(r) > o["show"] - 1 and r[C_NAME - 1]:
                    out["columns"][str(r[C_NAME - 1])] = {
                        "means": r[o["means"] - 1], "is": r[o["is"] - 1], "edges": r[o["edges"] - 1],
                        "show": r[o["show"] - 1], "period": r[o["period"] - 1] if len(r) >= o["period"] else None,
                        "define": r[o["define"] - 1] if len(r) >= o["define"] else None}
        else:
            for r in table_rows(ws):
                v = [c.value for c in r]
                v += [None] * (C_QKEY - len(v))
                if v[C_NAME - 1]:
                    out["columns"][str(v[C_NAME - 1])] = {
                        "means": v[C_MEANS - 1], "is": v[C_IS - 1], "edges": v[C_EDGES - 1], "show": v[C_SHOW - 1],
                        "period": v[C_PERIOD - 1], "define": v[C_DEFINE - 1]}
                key = v[C_QKEY - 1]
                if isinstance(key, str) and key.count("|") == 2 and v[C_TREAT - 1]:
                    col, rest = key.split("|", 1)
                    out["odd"][(col, rest)] = str(v[C_TREAT - 1]).strip().lower()
            for r in ws.iter_rows(min_row=COL_FIRST):          # the new columns, a half-typed row as typed
                key = r[C_QKEY - 1].value if len(r) >= C_QKEY else None
                if isinstance(key, str) and key.startswith(f"{control.DERIVED_KEY}|") and key.split("|")[1].isdigit():
                    got = tuple(r[c - 1].value for c in (2, 3, 4))
                    if any(x not in (None, "") for x in got):
                        out["derived"][int(key.split("|")[1])] = got
    if "Odd values" in wb.sheetnames:                        # before the redesign, the answers had a tab
        for r in wb["Odd values"].iter_rows(min_row=5, values_only=True):
            if len(r) > 6 and r[1]:
                out["odd"][(str(r[1]), str(r[6]))] = r[4]
    return out


def _made_columns(table, cols, kept: dict, mem: dict):
    """The new columns typed on Control (fix 3.9), made on this extract: the
    table with them added, what was made, and a note for each that couldn't be.
    An Odd values answer of missing on the top or bottom (this workbook's, or
    remembered) applies here as it will on the Run, so Look shows what the Run
    will cut."""
    notes: list[str] = []
    defs: list[cfgmod.Derived] = []
    names = set(table.columns)
    for slot, got in sorted(kept["derived"].items()):
        vals = [str(v).strip() if v not in (None, "") else "" for v in got]
        if not any(vals):
            continue
        name, top, bottom = vals
        if not all(vals):
            notes.append(f"New column {slot} under Add a column needs a name, a top and a bottom, so it isn't made yet.")
        elif name in names:
            notes.append(f"New column {slot} under Add a column: {name} is already a column, so it isn't made. Give it a "
                         f"name of its own.")
        elif top not in names or bottom not in names:
            gone = " and ".join(c for c in (top, bottom) if c not in names)
            notes.append(f"New column {slot} under Add a column: {gone} isn't a column in this extract, so {name} isn't made.")
        elif top == bottom:
            notes.append(f"New column {slot} under Add a column: {top} over itself is 1 on every loan, so {name} isn't made.")
        else:
            defs.append(cfgmod.Derived(name, top, bottom))
            names.add(name)
    if not defs:
        return table, [], notes
    made, reports = engine.derive_columns(table, defs, _odd_rules(cols, kept, mem))
    return made, reports, notes


def _odd_rules(cols, kept: dict, mem: dict) -> dict:
    """Every Treat as answer of missing on Columns (this workbook's, or remembered), as the Run's rules: what
    New columns and Look read before a Run, so neither shows a value the Run will leave out."""
    rules: dict = {}
    for c in cols:
        for q in c.questions:
            key = (q["column"], f"{q['pattern']}|{q['value'] if q['value'] is not None else ''}")
            known = memory.answer_for(mem, q["column"], q["pattern"], q["value"])
            answer = kept["odd"].get(key) or (known["answer"] if known else None)
            rule = cfgmod.Question(q["column"], q["pattern"], q["value"], q["rows"], answer).as_rule()
            if rule is not None:
                old = rules.get(q["column"], cfgmod.MissingRule())
                rules[q["column"]] = cfgmod.MissingRule(below=rule.below if rule.below is not None else old.below,
                                                        above=old.above, values=old.values + rule.values)
    return rules


def _to_code(v: Any, cat) -> str | None:
    """A meaning as the Columns tab shows it (a label) or as the code."""
    if v in cat:
        return v
    for code, m in cat.items():
        if v == m.label:
            return code
    return None


# --------------------------------------------------------------------------


@control.settings_once
def set_up(extract: str | Path, book: str | Path | None = None, memory_path: str | Path | None = None,
           today: date | None = None, choices: "ch.Choices | None" = None) -> Outcome:
    """Write the workbook beside the extract. `choices` is what the launcher's
    Choose tests step picked; without it, what the workbook already shows is kept
    (or, the first time, every column its meaning cuts, and nothing split).
    The suggested Control answers are worked out here, from pockets cut at the
    default edges, and written beside their settings (never chosen for you)."""
    extract = Path(extract)
    if workbook_picked(extract):
        # the third walk, defect 10: the workbook sits beside the extract and was picked by mistake
        return Outcome(False, extract, [workbook_picked(extract)])
    book = Path(book) if book else book_for(extract)
    try:
        table = read_table(extract)
    except OSError as exc:  # open in Excel, OneDrive still syncing it, or gone (the bank, 30 Sep 2026)
        return Outcome(False, book, [cant_read(extract, exc, "Set up")])
    except Exception as exc:  # the file itself: shown in words, never a traceback
        return Outcome(False, book, [f"Couldn't read {extract.name}: {exc}"])
    as_read = table
    kept = _answers(_earlier(book))
    mem = memory.load(memory_path)
    cat = meanings.catalog()
    method = {s.key: s.recommended().value for s in control.load_settings() if s.recommended()}
    # the category limits as answered on Control: Set up is where they apply (found checking the seventh
    # walk's blank "Last Run used" rows: Set up always used the recommended 12 and 50)
    for key in ("few_values", "many_values"):
        got = control.answer_of(key, *kept["control"].get(key, (None, None)))
        if choices is not None:
            got = getattr(choices, key)             # chosen in the launcher, before the workbook existed
        if isinstance(got, (int, float)) and not isinstance(got, bool):
            method[key] = int(got)
    few, many = int(method["few_values"]), int(method["many_values"])
    # each column's facts once, for classify, suggest, review and Look (found 26 Sep 2026: four times over)
    facts_of = meanings.facts_of(table)
    cols = profile.classify(table, few, many, facts_of)
    sugg = meanings.suggest(table, mem["columns"], few_values=few, many_values=many, known=facts_of)
    extract_cols = list(table.columns)
    # fix 3.9: the new columns typed on Control are made here, so Columns lists them and Look shows them
    number_cols = [c for c in extract_cols if facts_of[c].numeric]
    table, made, made_notes = _made_columns(table, cols, kept, mem)
    if made:
        facts_of = meanings.facts_of(table, facts_of)
        cols += profile.classify(Table(path=table.path, sha256=table.sha256, columns=[r.name for r in made],
                                       rows=table.rows, kind=table.kind), few, many, facts_of)
        for r_ in made:
            sugg[r_.name] = meanings.Suggestion(r_.name, "amount", f"made under Add a column: {r_.text()}", "control")
    if choices is not None and choices.outcome in table.columns:
        _outcome_picked(choices.outcome, sugg, kept, cat, facts_of, many)
    qs = [q for c in cols for q in c.questions]
    open_qs = [q for q in qs if not memory.answer_for(mem, q["column"], q["pattern"], q["value"])]
    looks = meanings.review(table, sugg, open_qs, cat, answer_where="under Treat as", known=facts_of)
    kind_now = choices.run_kind if choices is not None and choices.run_kind is not None else \
        control.answer_of(RUN_KIND, *kept["control"].get(RUN_KIND, (None, None)))    # the launcher's, else Control's
    if kind_now == NEW_VARIABLE:
        # a test of a new variable doesn't use the dollar columns, so their absence isn't news (the firm: "don't
        # note what it does not include, just note what it does")
        absent = tuple(f"No column was found for {cat[m].label} " for m in cfgmod.DOLLARS)
        looks = [rv for rv in looks if not (rv.kind == "cannot run" and rv.says.startswith(absent))]
    new_cols = [c for c in table.columns if kept["columns"] and c not in kept["columns"]]
    gone_cols = [c for c in kept["columns"] if c not in table.columns]

    # Refresh in place: the input tabs are rebuilt, the results of the last run stay
    # (the second walk, defect 6: Set up again deleted them).
    if book.exists():
        try:
            wb = _load(book)
        except Exception:
            wb = Workbook()
            wb.remove(wb.active)
        for t in list(wb.sheetnames):
            if t in INPUT_TABS or t in HELPERS or t in FOLDED_TABS[:2]:
                del wb[t]
        if not wb.sheetnames:
            wb.create_sheet("_placeholder")
    else:
        wb = Workbook()
        wb.remove(wb.active)
    start = wb.create_sheet("Start here")
    if "_placeholder" in wb.sheetnames:
        del wb["_placeholder"]
    control.write_control(wb, control.load_settings())
    for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
        key = r[control.KEY_COL - 1].value
        if key in kept["control"]:
            choose, own = kept["control"][key]
            r[control.CHOOSE_COL - 1].value = choose
            if own not in (None, "n/a"):
                r[control.OWN_COL - 1].value = own
    cws = wb[control.SHEET]
    if choices is not None or control.read_choices(cws)[0] is None:
        # the launcher's picks; the first time without them, every column its meaning cuts, nothing split
        choices = choices or ch.Choices(few_values=int(method["few_values"]), many_values=int(method["many_values"]))
        labels = {(s.key, o.value): o.label for s in control.load_settings() for o in s.options}
        control.write_choices(cws, choices, labels)
    control.fold_launcher_rows(cws)
    if kept["last_used"]:
        # what the last Run used stays through Set up again (the sixth walk, defect 6)
        for r in cws.iter_rows(min_row=control.FIRST_ROW):
            v = kept["last_used"].get(r[control.KEY_COL - 1].value)
            if v and _answer_row(r):
                c = cws.cell(row=r[0].row, column=control.LAST_COL, value=v)
                c.font = Font(name="Calibri", size=10, color=SLATE)

    # ---- Columns: what each column is, its odd values and what is remembered about it, on one tab
    ws = wb.create_sheet("Columns")
    odd_open, edge_noted = _columns_tab(ws, wb, table, cols, sugg, facts_of, looks, kept, mem, cat, made,
                                        made_notes, new_cols, gone_cols, qs,
                                        _in_use(choices, table, sugg, kept, cat, made))
    control.write_derived(wb, number_cols, kept["derived"], sheet="Columns", top=ws.max_row + 2,
                          first=C_NAME, key_col=C_QKEY, last=C_WHY + 1)
    _fit(ws)

    from . import look                      # fix 3.8: each number column's shape, before its edges are chosen
    shown = look.number_columns(table, cols, few, facts_of)
    edge_rows = {str(r[C_NAME - 1].value): r[0].row for r in table_rows(ws) if r[C_NAME - 1].value}
    banded = {str(r[C_NAME - 1].value) for r in table_rows(ws) if r[C_NAME - 1].value
              and (_to_code(r[C_MEANS - 1].value, cat) or "") in cat
              and cat[_to_code(r[C_MEANS - 1].value, cat)].cut == "band"}
    chosen_now = choices or control.read_choices(cws)[0]
    cut = chosen_now.cut() if chosen_now is not None else None
    # H, the firm's answer of 27 Sep 2026: only a column that can be cut into bands gets a block. GCO and RANR drew a
    # chart saying "no edges on Columns yet" ("Not sure why we even have the info? Like obviously we didn't band them")
    shown = [c for c in shown + [m.name for m in made if m.name not in shown] if c in banded]
    look.write_look(wb, table, shown, known=facts_of,
                    edge_rows=edge_rows, split=chosen_now.split if chosen_now is not None else None,
                    bands=[c for c in shown if c in banded and (cut is None or c in cut)],
                    treat_rows=_treat_rows(ws), rules=_odd_rules(cols, kept, mem))

    about = wb.create_sheet(ABOUT)
    about["A1"], about["B1"] = "extract", str(extract.resolve())
    about["A2"], about["B2"] = "sha256", as_read.sha256        # the bytes read above: the extract is read once
    about["A3"], about["B3"] = "set up", (today or date.today()).isoformat()
    about["A4"], about["B4"] = "extract name", extract.name
    about.sheet_state = "hidden"
    settings = control.load_settings()
    given = {s.key: control.answer_of(s.key, *kept["control"].get(s.key, (None, None))) for s in settings}
    _start_here(start, wb, extract, len(table.rows), len(extract_cols))
    _order(wb)
    if not _writable(book):
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Set up again."])
    worked = _suggest_at_set_up(wb, book, as_read, memory_path, testing=kind_now == NEW_VARIABLE)
    _suggestions(wb[control.SHEET], *worked, when="from this extract")
    _cutoff_words(wb[control.SHEET], as_read, wb["Columns"], cat)          # OC-51
    try:
        wb.save(book)
    except PermissionError:
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Set up again."])
    lines = [f"Set up {book.name} from {extract.name}: {len(table.rows):,} loans, {_n(len(extract_cols), 'column')}."]
    for m in made:
        why = "; ".join(f"{k:,} where {w}" for w, k in m.blank.items())
        lines.append(f"Made {m.name} = {m.text()} on Columns and Look" + (f". Blank on {why}." if why else "."))
    lines += made_notes
    if given.get(RUN_KIND) is None and (choices is None or choices.run_kind is None):
        # the firm, 26 Sep 2026: ask which we are doing, so the run checks the minimum it needs
        kinds = next(x for x in settings if x.key == RUN_KIND).options
        lines.append(f'First, in the launcher, choose what you\'re running: {kinds[0].label}, or '
                     f'{kinds[1].label}.')
    if new_cols:
        lines.append(f"New columns since the last check: {', '.join(new_cols)}. Columns!C3 needs a Yes again.")
    # E, the firm's answer of 27 Sep 2026: one count of what is left, the Run's refusal's own. The window said "7
    # columns to look at first", Start here "Columns to confirm: 10", and the refusal listed 9
    _, left, _ = read_book(book, memory_path)
    on = [t for t in ("Control", "Columns", "Look") if any(p.startswith(t) for p in left)]
    joined = ", ".join(on[:-1]) + (" and " if len(on) > 1 else "") + on[-1] if on else ""
    lines.append(f"Next: {_n(len(left), 'answer')} needed before Run" + (f", on {joined}" if on else "")
                 + ". Fill in the shaded cells, save, close, and press Run." if left
                 else "Everything is answered. Press Run.")
    return Outcome(True, book, lines, summary={"suggested": worked[0], "fallback": worked[1], "needed": len(left)})


def _answer_row(r) -> bool:
    """A Control row a person answers (Block A or B), not a band, a heading or a launcher row."""
    key = r[control.KEY_COL - 1].value
    return isinstance(key, str) and key in control.NOW_KEYS + control.RUN_KEYS


#: Meanings a person may have confirmed before they were taken out (config.REMOVED), in the words Columns used.
REMOVED_MEANINGS = {"outcome_date": "Outcome date", "as_of_date": "As-of date"}


def _odd_words(q: dict) -> str:
    """An odd value as the Columns tab says it: "-9999 on 60 loans", "Negative on 595 loans"."""
    if q["pattern"] == "negatives":
        return f"Negative on {q['rows']:,} loans"
    v = q["value"]
    return f"{int(v) if float(v).is_integer() else v:g} on {q['rows']:,} loans"


def _remembered_words(entry: dict | None) -> str:
    if not entry:
        return "No"
    if entry.get("means") in REMOVED_MEANINGS:
        # confirmed before the meaning was taken out: never suggested again, and said so here
        return f"As {REMOVED_MEANINGS[entry['means']]}: no longer used. Forget it"
    times = int(entry.get("times", 1) or 1)
    return f"Yes · {times} Run" + ("" if times == 1 else "s")


def _in_use(choices, table, sugg, kept, cat, made) -> set[str] | None:
    """The extract's columns this Run uses, as the launcher picked them: the key, the outcome, the date, and for
    the bleed the booked and dollar columns, the bands, segments and split; for a new variable what is tested and
    held fixed. Columns made under Add a column always count. None (every column) when nothing was picked."""
    if choices is None or choices.run_kind is None:
        return None
    new = choices.run_kind == NEW_VARIABLE
    out = {m.name for m in made}
    for c in table.columns:
        code = _to_code((kept["columns"].get(c) or {}).get("means"), cat) or sugg[c].means
        cut = cat[code].cut if code in cat else "none"
        if code in ("key", "outcome", "origination_date") or c == choices.outcome:
            out.add(c)
        elif new:
            if c in choices.test or c in choices.hold:
                out.add(c)
        elif code in ("booked", "gco", "ranr") or c in (choices.split, choices.filter) or \
                (c in choices.bands if choices.bands is not None else cut == "band") or \
                (c in choices.segments if choices.segments is not None else cut == "dimension"):
            out.add(c)
    return out


#: Columns' Check first: its width. It stays one line, as every row of the table does (the redesign's rule 5,
#: held by test_answer_tabs); the survey's proposal to wrap it waits for the firm (BACKLOG §6d)
LOOK_WIDTH = 60


def _samples_of(col, made) -> list[str]:
    """A column's first three samples as Columns shows them: a made ratio to four figures, not seventeen."""
    samples = col.samples[:3]
    if any(m.name == col.name for m in made):
        samples = [f"{float(v):.4g}" for v in samples]
    return [str(v) for v in samples]


def _columns_tab(ws, wb, table, cols, sugg, facts_of, looks, kept, mem, cat, made, made_notes, new_cols, gone_cols,
                 qs, used: set[str] | None = None) -> tuple[int, set[str]]:
    """Columns, as the redesign draws it (section 3): the check at C3, the method note, then one row per extract
    column (a second odd value in a column gets a row of its own under it, with no name). Returns how many odd
    values are still unanswered, and the columns whose remembered edges were filled in."""
    from . import house
    last = C_DEFINE
    # T1: the name and samples fit what the extract holds (the derived-column block's "New column name ↻" too);
    # Odd values and Show per pocket their longest text + 2
    widths = {1: 2, C_NAME: house.fit(list(table.columns) + ["New column name ↻", "Checked every column?"], floor=14,
                                      cap=32, pad=3),
              C_SAMPLES: house.fit([", ".join(_samples_of(x, made)) for x in cols], floor=20, cap=40),
              C_MEANS: 20, C_WHY: 40, C_BLANK: 7, C_ODD: 23, C_TREAT: 11,
              C_EDGES: 16, C_REMEMBERED: 13, C_FORGET: 9, C_LOOK: LOOK_WIDTH, C_IS: 12, C_SHOW: 19, C_PERIOD: 11,
              C_DEFINE: 30}
    for col, w in widths.items():
        ws.column_dimensions[_col(col)].width = w
    house.title_band(ws, "Columns", "What each column means, what looks odd in it, and what PocketBook remembers "
                                    "about it.", C_NAME, last)
    ws["B3"] = "Checked every column?"
    ws["B3"].font = Font(name="Calibri", bold=True, size=11)
    # new columns since the last check: the Yes no longer covers them (second walk, defect 4)
    ws[CONFIRM_CELL] = kept["confirmed"] if kept["confirmed"] in ("Yes", "No") and not new_cols else None
    house.needs_run(ws[CONFIRM_CELL])
    ws[CONFIRM_CELL].alignment = Alignment(horizontal="center")
    dv_yes = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True, showErrorMessage=True)
    ws.add_data_validation(dv_yes)
    dv_yes.add(ws[CONFIRM_CELL])
    ws.conditional_formatting.add(CONFIRM_CELL, house.still_needed(f'{CONFIRM_CELL}<>"Yes"'))
    notes = [rv.says for rv in looks if rv.kind == "cannot run"]
    if new_cols:
        notes.append(NEW_COLS_NOTE.format(", ".join(new_cols)))
    if gone_cols:
        notes.append(f"No longer in the extract: {', '.join(gone_cols)}.")
    notes += made_notes
    hidden_n = 0 if used is None else sum(1 for c in table.columns if c not in used)
    ws["D3"] = " ".join([CONFIRM_NOTE] + ([HIDDEN_NOTE.format(hidden_n)] if hidden_n else []) + notes)
    ws["D3"].font = Font(name="Calibri", bold=bool(notes), size=10, color=house.CRIMSON if notes else SLATE)
    ws["D3"].alignment = Alignment(vertical="center")
    ws.row_dimensions[3].height = 20
    top = house.method_note(ws, 5, C_NAME, C_WHY + 3, COLUMNS_METHOD, label_width=1)
    assert top == COL_HEAD, top                     # the table's place is fixed: refusals and tests name its cells
    house.header(ws, COL_HEAD, C_NAME, [COLUMNS_HEADS[c] for c in range(C_NAME, last + 1)], centre_from=4)
    for col in (C_WHY, C_ODD, C_LOOK, C_DEFINE):
        ws.cell(row=COL_HEAD, column=col).alignment = Alignment(horizontal="left", vertical="center")
    mm = wb.create_sheet("_meanings")
    for i, (code, m) in enumerate(cat.items(), start=1):
        mm.cell(row=i, column=1, value=m.label)
        mm.cell(row=i, column=2, value=code)
        mm.cell(row=i, column=3, value=m.says)
    mm.sheet_state = "hidden"
    dv_m = DataValidation(type="list", formula1=f"='_meanings'!$A$1:$A${len(cat)}", allow_blank=False,
                          showErrorMessage=True)
    dv_m.error = "Pick one of the meanings in the list."
    dv_show = DataValidation(type="list", formula1='"median,average"', allow_blank=True, showErrorMessage=True)
    dv_period = DataValidation(type="list", formula1=f'"{",".join(PERIOD_OPTIONS)}"', allow_blank=True,
                               showErrorMessage=True)
    dv_period.error = "Pick per year, per month or one-time, or leave it blank."
    dv_treat = DataValidation(type="list", formula1=f'"{",".join(TREAT)}"', allow_blank=True, showErrorMessage=True)
    dv_treat.error = "Pick Real or Missing, or leave it blank to use the values as recorded."
    dv_forget = DataValidation(type="list", formula1='"No,Yes"', allow_blank=True, showErrorMessage=True)
    for dv in (dv_m, dv_show, dv_period, dv_treat, dv_forget):
        ws.add_data_validation(dv)
    by_col: dict[str, list[str]] = {}
    for rv in looks:
        # an odd value is said once, in its own column beside Treat as, not again under Check first
        if rv.kind not in ("cannot run", "odd values"):
            by_col.setdefault(rv.column, []).append(rv.says)
    for c in new_cols:
        by_col.setdefault(c, []).insert(0, "New since the last check.")
    classified = {c.name: c for c in cols}
    why_len = max((len(("Remembered: " if sugg[c].source == "remembered" else "") + sugg[c].why)
                   for c in table.columns), default=20)
    ws.column_dimensions[_col(C_WHY)].width = min(max(why_len * 0.9, 24), 64)
    questions: dict[str, list[dict]] = {}
    for q in qs:
        questions.setdefault(q["column"], []).append(q)
    edge_noted: set[str] = set()
    odd_open = 0
    thin = Border(bottom=Side(style="thin", color=house.ROW_RULE))
    r = COL_FIRST
    for c in table.columns:
        sg = sugg[c]
        prior = kept["columns"].get(c, {})
        code = _to_code(prior.get("means"), cat) or sg.means
        hide = used is not None and c not in used
        tag = "Remembered: " if sg.source == "remembered" else ""
        f = facts_of.get(c) or meanings.facts(table, c)
        blank = (f.rows - f.nonblank) / f.rows if f.rows else 0
        ws.cell(row=r, column=C_NAME, value=c).font = Font(name="Calibri", bold=True, size=10)
        samples = _samples_of(classified[c], made) if c in classified else []
        ws.cell(row=r, column=C_SAMPLES, value=", ".join(samples))
        means = ws.cell(row=r, column=C_MEANS, value=cat[code].label)
        house.needs_run(means)
        dv_m.add(means)
        ws.cell(row=r, column=C_WHY, value=tag + sg.why)
        ws.cell(row=r, column=C_BLANK, value=blank).number_format = "0%"
        # remembered edges only fill a column this workbook hasn't seen: what's on this workbook's
        # Columns tab, a cleared cell included, wins (the fifth walk: another copy's "every 2000"
        # came in, and clearing the cell didn't undo it)
        remembered_edges = (mem["columns"].get(c) or {}).get("edges") \
            if c not in kept["columns"] and cat[code].cut == "band" else None
        edges = ws.cell(row=r, column=C_EDGES, value=prior.get("edges") if prior else remembered_edges)
        if remembered_edges:
            by_col.setdefault(c, []).append(f"Band edges remembered from before: {remembered_edges}.")
            edge_noted.add(c)
        edges.number_format = "@"            # kept as typed: Excel would read 620,680,740 as one number
        if cat[code].cut == "band" or edges.value:
            house.needs_run(edges)
        entry = mem["columns"].get(c)
        ws.cell(row=r, column=C_REMEMBERED, value=_remembered_words(entry))
        forget = ws.cell(row=r, column=C_FORGET, value="No" if entry else None)
        dv_forget.add(forget)                   # every row: a Run remembers a column, and it can be forgotten
        if entry:
            house.needs_run(forget)
        ws.cell(row=r, column=C_LOOK, value=" ".join(by_col.get(c, [])) or None)  # after the edges note
        ws.cell(row=r, column=C_IS, value=prior.get("is") if prior else sg.is_value)
        ws.cell(row=r, column=C_SHOW, value=prior.get("show"))
        dv_show.add(ws.cell(row=r, column=C_SHOW))
        ws.cell(row=r, column=C_PERIOD, value=prior.get("period"))
        dv_period.add(ws.cell(row=r, column=C_PERIOD))
        ws.cell(row=r, column=C_DEFINE, value=prior.get("define"))
        ws.cell(row=r, column=C_SUGG, value=sg.means)
        ws.cell(row=r, column=C_MADE, value=next((m.text() for m in made if m.name == c), None))
        asked = [] if hide else questions.get(c, [])      # a column not in use: nothing asked, nothing counted
        for k, q in enumerate(asked or [None]):
            row = r + k
            if q is not None:
                key = f"{q['pattern']}|{q['value'] if q['value'] is not None else ''}"
                known = memory.answer_for(mem, q["column"], q["pattern"], q["value"])
                answer = kept["odd"].get((c, key)) or (known["answer"] if known else None)
                ws.cell(row=row, column=C_ODD, value=("and " if k else "") + _odd_words(q))
                treat = ws.cell(row=row, column=C_TREAT, value=str(answer).capitalize() if answer else None)
                house.needs_run(treat)
                dv_treat.add(treat)
                ws.cell(row=row, column=C_QKEY, value=f"{c}|{key}")
                odd_open += not answer
            for col in range(C_NAME, last + 1):
                cell = ws.cell(row=row, column=col)
                if cell.border.left.style is None:
                    cell.border = thin
                cell.alignment = Alignment(vertical="center", horizontal="center" if col in (
                    C_BLANK, C_MEANS, C_TREAT, C_EDGES, C_REMEMBERED, C_FORGET, C_IS, C_SHOW, C_PERIOD) else "left")
                if col != C_NAME:
                    cell.font = Font(name="Calibri", size=10, bold=cell.font.b,
                                     color=SLATE if col in (C_SAMPLES, C_WHY, C_LOOK) else house.INK_TEXT)
            ws.row_dimensions[row].height = 18
            ws.row_dimensions[row].hidden = hide
        r += max(1, len(asked))
    ws.cell(row=r, column=C_QKEY, value=TABLE_END)
    treat = _col(C_TREAT)
    key = _col(C_QKEY)
    ws.conditional_formatting.add(f"{treat}{COL_FIRST}:{treat}{r - 1}", house.still_needed(
        f'AND(${key}{COL_FIRST}<>"",${treat}{COL_FIRST}="")'))
    look = _col(C_LOOK)
    ws.conditional_formatting.add(f"{look}{COL_FIRST}:{look}{r - 1}", house.still_needed(f'{look}{COL_FIRST}<>""'))
    for col in (C_SUGG, C_MADE, C_QKEY):
        ws.column_dimensions[_col(col)].hidden = True
    ws.freeze_panes = f"C{COL_FIRST}"
    return odd_open, edge_noted


def _treat_rows(ws) -> dict[str, tuple[int, str]]:
    """Each column's first odd value by the row its Treat as answer sits on: {column: (row, what)}."""
    out: dict[str, tuple[int, str]] = {}
    for r in table_rows(ws):
        key = r[C_QKEY - 1].value if len(r) >= C_QKEY else None
        if isinstance(key, str) and key.count("|") == 2:
            col = key.split("|")[0]
            out.setdefault(col, (r[0].row, key.split("|", 1)[1]))
    return out


#: Start here's count of what is left before Run: the launcher and the Run's refusal say the same number
NEEDED = "Answers needed before Run"


def _start_here(ws, wb, extract, rows: int, ncols: int, found=None) -> None:
    """Start here, as the redesign draws it (section 1): where things stand, as formulas over Control and
    Columns; the pending banner; what the last Run found (from _found, kept through Set up) with its five
    largest pockets; and the tabs in their three groups."""
    from . import house
    # P1, P2: B and C fit the largest pockets' bands and segments the last Run found, and the heading over them;
    # D to F their headings ("× its comparison", "Dollars above share") + 2
    tops = [r for r in wb[FOUND].iter_rows(values_only=True) if r and r[0] == "top"] if FOUND in wb.sheetnames \
        else []
    b_w = house.fit(["Largest, worse and material"] + [r[TOP_BAND - 1] for r in tops], floor=22, cap=32)
    # a segment can carry the borderline flag ("ASSET_CLASS 4 · borderline (p 0.036)", the evening tie-out, 30 Sep)
    c_w = house.fit([r[TOP_SEG - 1] for r in tops] + [f"{r[TOP_SEG - 1]} · {stats.borderline_words(0.048, 0.95)}"
                                                     for r in tops if r[TOP_SEG - 1]], floor=16, cap=44, pad=3)
    for col, w in zip("ABCDEFGHI", (2, b_w, c_w, 12, 18, 21, 16, 16, 22)):
        ws.column_dimensions[col].width = w
    stamp = _found_value(wb, "stamp")
    sub = f"{Path(extract).name} · {rows:,} loans · {ncols} columns" + (
        f" · last Run {stamp}" if stamp else "")
    house.title_band(ws, NAME, sub, 2, 9)
    r = house.method_note(ws, 3, 2, 9, [
        ("Where things stand", "What is left before Run, counted live from Control and Columns as you fill them "
                               "in."),
        ("What the last Run found", "Pockets worse and material at Control's lines, and the five largest."
         if _found_value(wb, "kind") != confirm_tab.FOUND_KIND else
         "Each group of the tested column on the holdout, against the reference group. Significant? follows the "
         "confidence on Control; the rest is as of the last Run."),
        ("The tabs", "Red tabs you fill in; black tabs hold results; grey tabs are the record."),
    ])
    _heading(ws, r, "Where things stand")
    cols = wb["Columns"] if "Columns" in wb.sheetnames else None
    end = next((c.row for c in cols[_col(C_QKEY)] if c.value == TABLE_END), COL_FIRST + 1) - 1 if cols \
        else COL_FIRST
    keys, treat = f"Columns!${_col(C_QKEY)}${COL_FIRST}:${_col(C_QKEY)}${end}", \
        f"Columns!${_col(C_TREAT)}${COL_FIRST}:${_col(C_TREAT)}${end}"
    # the count the Run's refusal gives (E, the firm, 27 Sep 2026): each blank answer on Control, what is being run
    # when the launcher hasn't said, and Checked every column; "Columns to confirm" counted every column instead
    kind_row = control.row_of(wb[control.SHEET], RUN_KIND) if control.SHEET in wb.sheetnames else None
    kind_blank = f'+IF({control.SHEET}!$C${kind_row}="",1,0)' if kind_row else ""
    tiles = [(NEEDED, f'=IFERROR(SUM(answers_needed),0){kind_blank}'
                      f'+IF(Columns!{CONFIRM_CELL.replace("C", "$C$")}="Yes",0,1)', "Control and Columns"),
             ("Odd values to answer", f'=COUNTIFS({keys},"?*",{treat},"")', "Columns · Treat as"),
             ("Changes waiting for a Run", f'=IFERROR(COUNTIF(Status,"{house.WAITING}"),0)',
              "Control · Status")]
    for i, (label, f, where) in enumerate(tiles):
        first = 2 + 2 * i
        house.tile(ws, r + 1, first, first + 1, label, f, top=house.STONE)
        foot = ws.cell(row=r + 3, column=first, value=where)
        foot.font = Font(name="Calibri", size=9, color=SLATE)
        foot.alignment = Alignment(indent=1)
    value_row = r + 2
    from openpyxl.formatting.rule import FormulaRule
    for i in range(len(tiles)):
        # a count above nought is crimson, and its tile's rule turns red
        c, d = _col(2 + 2 * i), _col(3 + 2 * i)
        ws.conditional_formatting.add(f"{c}{value_row}", FormulaRule(
            formula=[f"${c}${value_row}>0"], font=Font(name="Arial", bold=True, size=12, color=house.CRIMSON)))
        ws.conditional_formatting.add(f"{c}{r + 1}:{d}{r + 1}", FormulaRule(
            formula=[f"${c}${value_row}>0"], border=Border(top=Side(style="thick", color=house.KEY_RED))))
    # the pending banner: shown only while an answer under Needs a Run, or a choice in the launcher, differs from
    # what the last Run used
    b = r + 5
    ws.merge_cells(start_row=b, start_column=2, end_row=b, end_column=9)
    words = "&".join(f"INDEX(waiting_words,{k})" for k in range(1, control.waiting_rows(wb) + 1))
    n = f'COUNTIF(Status,"{house.WAITING}")'
    ws.cell(row=b, column=2, value=(
        f'=IFERROR(IF({n}=0,"","↻ "&{n}&IF({n}=1," change is"," changes are")&" waiting for a Run. "&'
        f'LEFT({words},LEN({words})-2)&". The result tabs still show the last Run. Save, close, and press Run in '
        f'the launcher."),"")'))
    ws.cell(row=b, column=2).font = Font(name="Calibri", size=10, bold=True, color=house.CRIMSON)
    ws.cell(row=b, column=2).alignment = Alignment(vertical="center", indent=1, wrap_text=True)
    ws.row_dimensions[b].height = 42            # three lines: a change or two in the launcher and on Control
    ws.conditional_formatting.add(f"B{b}:I{b}", FormulaRule(
        formula=[f'$B${b}<>""'], fill=PatternFill("solid", fgColor=house.ALERT_FG, bgColor=house.ALERT_FG)))
    r = b + 2
    r = _found_block(ws, wb, r)
    _tab_groups(ws, wb, r + 1)
    ws.freeze_panes = "A2"
    _fit(ws)


def _heading(ws, row: int, text: str) -> None:
    c = ws.cell(row=row, column=2, value=text.upper())
    c.font = Font(name="Arial", bold=True, size=9, color=SLATE)


def _found_value(wb, key: str):
    if FOUND not in wb.sheetnames:
        return None
    for a, b in wb[FOUND].iter_rows(min_row=1, max_col=2, values_only=True):
        if a == key:
            return b
    return None


#: Start here's list of the largest pockets, worse and material: how many rows it shows
TOP_ROWS = 5
#: the hidden column on Start here holding which _found row each of those rows shows
TOP_HELPER = 11


def _found_block(ws, wb, r: int) -> int:
    """What the last Run found: the tiles and the five largest pockets that are worse and material now. The words
    are the Run's; the tiles, the dollars and which pockets are listed are formulas over _pockets, so they follow
    Control. The list is picked as Pockets' Show dropdown picks (results._write_list): _found carries every pocket
    the Run found losing more than its share, largest dollars first, each with its live Worse? and Material? and a
    running count of those that are both, and row k is the first whose count reaches k (the firm, 27 Sep 2026, on
    rows that no longer read worse under that heading: "I don't understand this like at all like meaning it's
    slop")."""
    from . import house
    _heading(ws, r, "What the last Run found")
    if _found_value(wb, "kind") == confirm_tab.FOUND_KIND:
        return confirm_tab.found_block(ws, wb, r, lambda k: _found_value(wb, k))
    if FOUND not in wb.sheetnames or not _found_value(wb, "measure"):
        c = ws.cell(row=r + 1, column=2, value="Nothing yet: answer Control and Columns, then press Run in the "
                                               "launcher.")
        c.font = Font(name="Calibri", size=10, color=SLATE)
        return r + 3
    m, title = _found_value(wb, "measure"), _found_value(wb, "measure_title")
    crit = f'pk_kind,"grids",pk_measure,"{m}",pk_flag,"{engine.WORSE}",pk_material,"yes"'
    dollar = m != "outcome_loans"
    # Borderline (the firm, 29 Sep 2026): how many of them turn on a shuffled p-value that near the bar
    bl = f'COUNTIFS({crit},pk_wborder,"?*")'
    tiles = [(f"Pockets worse and material, {title}",
              f'=IFERROR(COUNTIFS({crit})&" of {_found_value(wb, "pockets"):,}"&IF({bl}>0," · "&{bl}&" borderline",'
              f'""),"")'),
             (f"{'Dollars' if dollar else 'Bad loans'} above their share, in those",
              f'=IFERROR(SUMIFS(pk_dollars,{crit}),"")')]
    profit = _found_value(wb, "profit")
    if profit:
        pc = f'pk_kind,"grids",pk_measure,"{profit}",pk_flag,"{engine.WORSE}",pk_material,"yes"'
        tiles.append(("Pockets keeping less, worse and material",
                      f'=IFERROR(COUNTIFS({pc})&" short $"&TEXT(SUMIFS(pk_dollars,{pc}),"#,##0"),"")'))
    else:
        tiles.append(("Last Run", _found_value(wb, "stamp")))
    for i, (label, f) in enumerate(tiles):
        house.tile(ws, r + 1, 2 + 2 * i, 3 + 2 * i, label, f)
    ws.cell(row=r + 2, column=4).number_format = '"$"#,##0' if dollar else "#,##0.0"
    t = r + 4
    heads = ["Largest, worse and material", "Segment", "Loans", "× its comparison",
             f"{'Dollars' if dollar else 'Bad loans'} above share"]
    house.header(ws, t, 2, heads, centre_from=2)
    rows = [c.row for c in wb[FOUND]["A"] if c.value == "top"]
    if not rows:
        ws.cell(row=t + 1, column=2, value="Nothing lost more than its share at the last Run.").font = \
            Font(name="Calibri", size=10, color=SLATE)
    else:
        a, z = rows[0], rows[-1]
        F = lambda c: f"'{FOUND}'!${_col(c)}${a}:${_col(c)}${z}"                    # noqa: E731
        for k in range(1, TOP_ROWS + 1):
            rr = t + k
            idx = f"${_col(TOP_HELPER)}{rr}"
            ws.cell(row=rr, column=TOP_HELPER, value=f'=IFERROR(MATCH({k},{F(TOP_CUM)},0),"")')
            got = lambda c: f"INDEX({F(c)},{idx})"                                 # noqa: E731
            P = lambda c: f"INDEX('{live.POCKETS}'!${live.col(c)}:${live.col(c)},{got(TOP_PROW)})"   # noqa: E731
            none = '"No pocket is worse and material."' if k == 1 else '""'
            # the pocket, and " · borderline (p 0.048)" when its Worse? is (the firm, 29 Sep 2026), as Record's
            # "Worst for" line says it: no Worse? column, since every row listed is worse (tenet T2)
            wb_ = P(live.P_WBTXT)
            seg = live.said_formula(got(TOP_SEG), wb_)
            vals = [f'=IF({idx}="",{none},{got(TOP_BAND)})', f'=IF({idx}="","",{seg})',
                    f'=IF({idx}="","",{got(TOP_LOANS)})',
                    f'=IF({idx}="","",IF({P(live.P_GAP)}="","",{P(live.P_GAP)}))',
                    f'=IF({idx}="","",IF({P(live.P_DOLLARS)}="","",{P(live.P_DOLLARS)}))']
            for j, v in enumerate(vals):
                c = ws.cell(row=rr, column=2 + j, value=v)
                c.font = Font(name="Calibri", size=10, color=house.INK_TEXT)
                c.alignment = Alignment(horizontal="left" if j < 2 else "center", vertical="center")
                c.border = Border(bottom=Side(style="thin", color=house.ROW_RULE))
            ws.cell(row=rr, column=4).number_format = "#,##0"
            ws.cell(row=rr, column=5).number_format = '0.00"×"'
            ws.cell(row=rr, column=6).number_format = '"$"#,##0' if dollar else "#,##0.0"
            ws.row_dimensions[rr].height = 18
        ws.column_dimensions[_col(TOP_HELPER)].hidden = True
    last = t + (TOP_ROWS if rows else 1)
    link = ws.cell(row=last + 1, column=2, value="Every pocket, every measure: the Pockets tab.")
    link.hyperlink = f"#'{results.POCKETS}'!A1"
    link.font = Font(name="Calibri", size=10, color=house.KEY_RED, underline="single")
    return last + 3


#: the tabs in their three groups, each with what it holds
TAB_GROUPS = [
    ("You answer", "KEY_RED", [("Control", "the professional calls"), ("Columns", "meanings, odd values, memory"),
                               ("Look", "each number column's shape")]),
    ("Results", "INK", [(results.POCKETS, "every pocket, worse first"), (results.PCK, "paid against cost"),
                        (results.GRIDS, "one grid at a time, and how common"),
                        (results.SUMMARY, "one band column's plain figures"), (results.SPLIT, "each pocket split"),
                        (scout.SHEET, "the candidates ranked, on development loans"),
                        (confirm_tab.SHEET, "the shortlist, confirmed")]),
    ("Record", "STONE", [(record.SHEET, "what ran, the tie-outs, every Run")]),
]


def _tab_groups(ws, wb, r: int) -> None:
    """The tabs, in three groups under a 4 px rule in each group's tab colour, each tab a link."""
    from . import house
    _heading(ws, r, "The tabs")
    spans = [(2, 3), (4, 6), (7, 9)]
    for (title, colour, tabs), (first, last) in zip(TAB_GROUPS, spans):
        for col in range(first, last + 1):
            ws.cell(row=r + 1, column=col).border = Border(top=Side(style="thick", color=getattr(house, colour)))
        ws.cell(row=r + 1, column=first, value=title).font = Font(name="Arial", bold=True, size=10)
        k = r + 2
        for tab, what in tabs:
            if tab not in wb.sheetnames and title == "Results":
                continue
            c = ws.cell(row=k, column=first, value=f"{tab}: {what}")
            c.hyperlink = f"#'{tab}'!A1"
            c.font = Font(name="Calibri", size=10, color=house.INK_TEXT)
            k += 1
        if title == "Results" and k == r + 2:
            ws.cell(row=k, column=first, value="Written by each Run.").font = Font(name="Calibri", size=10,
                                                                                    color=SLATE)


# --------------------------------------------------------------------------


def read_book(book: Path, memory_path=None, wb=None) -> tuple[dict | None, list[str], dict]:
    """The cube file a workbook describes, as a dict, and every problem in it
    named by tab and cell. Nothing is run. `wb`: the workbook already open (a
    Run loads it once)."""
    problems: list[str] = []
    wb = wb if wb is not None else _load(book)
    missing_tabs = [t for t in ("Control", "Columns", ABOUT) if t not in wb.sheetnames]
    if missing_tabs:
        return None, [f"This workbook is missing its {', '.join(missing_tabs)} tab. Press Set up again."], {}
    about = {wb[ABOUT][f"A{i}"].value: wb[ABOUT][f"B{i}"].value for i in range(1, 5)}
    if _old_columns(wb["Columns"]) or "Odd values" in wb.sheetnames:
        # set up before the redesign put the odd values and the new columns on Columns: its cells are elsewhere
        return None, ["Columns: this workbook was set up before Columns held the odd values. Press Set up again: "
                      "every answer is kept."], about
    try:
        use = control.read_control(wb)
    except control.ControlError as exc:
        problems += exc.problems
        use = {}
    cat = meanings.catalog()
    ws = wb["Columns"]
    if ws[CONFIRM_CELL].value != "Yes":
        note = str(ws["D3"].value or "")
        gone = note[note.index("Forgotten"):] if "Forgotten" in note else ""
        problems.append(f"Columns!{CONFIRM_CELL}: set Checked every column to Yes once you've checked each "
                        f"column's meaning." + (f" {gone}" if gone else ""))
    columns, edges, skip, show, split, filt = {}, {}, set(), {}, [], None
    chosen, choice_cells = control.read_choices(wb[control.SHEET])
    if chosen is None:
        problems.append("Control: this workbook was set up before the launcher chose what to cut. Press Set up "
                        "again.")
    made_rows: dict[str, tuple[int, str]] = {}         # a new column -> (its row, what it was made from)
    row_of_col: dict[str, int] = {}
    widths: dict[str, float] = {}
    typed: dict[str, str] = {}
    edge_cells: dict[str, str] = {}
    questions = []
    for r in table_rows(ws):
        qkey = r[C_QKEY - 1].value if len(r) >= C_QKEY else None
        if isinstance(qkey, str) and qkey.count("|") == 2:
            # an odd value and its Treat as answer (the redesign, phase 2: the Odd values tab is on Columns)
            qcol, pattern, value = qkey.split("|")
            said = r[C_TREAT - 1].value
            answer = str(said).strip().lower() if said not in (None, "") else None
            if answer is not None and answer not in ("real", "missing"):
                problems.append(f"Columns!{_col(C_TREAT)}{r[0].row}: Treat as takes Real or Missing, or blank.")
                answer = None
            words = str(r[C_ODD - 1].value or "")
            rows = int(re.sub(r"[^0-9]", "", words.rsplit(" on ", 1)[-1]) or 0) if " on " in words else 0
            questions.append({"column": qcol, "pattern": pattern, "value": float(value) if value else None,
                              "rows": rows, "answer": answer})
        name = r[C_NAME - 1].value
        if not name:
            continue
        name = str(name)
        row = r[C_NAME - 1].row
        code = _to_code(r[C_MEANS - 1].value, cat)
        if not code:
            problems.append(f'Columns!{_col(C_MEANS)}{row}: "{name}" has no meaning from the list. Pick one.')
            continue
        is_value = r[C_IS - 1].value
        entry: dict[str, Any] = {"means": code}
        if is_value not in (None, ""):
            entry["is"] = is_value
        mark = r[C_MADE - 1].value if len(r) >= C_MADE else None
        if mark:
            made_rows[name] = (row, str(mark))
        per = r[C_PERIOD - 1].value if len(r) >= C_PERIOD else None
        if per not in (None, ""):
            where = f"Columns!{_col(C_PERIOD)}{row}"
            if str(per).strip() not in PERIOD_OPTIONS:
                problems.append(f'{where}: the period is per year, per month or one-time. Pick one, or clear it.')
            elif mark:
                problems.append(f'{where}: "{name}" is one column over another, so it has no period of its own. '
                                f'Say the periods of the two it divides. Clear the cell.')
            elif code not in cfgmod.AMOUNT_MEANINGS:
                problems.append(f'{where}: "{name}" is marked {cat[code].label}, not an amount, so it has no period. '
                                f'Clear the cell, or change what it is.')
            else:
                entry["period"] = PERIOD_OPTIONS[str(per).strip()]
        said = r[C_DEFINE - 1].value if len(r) >= C_DEFINE else None
        if said not in (None, "") and str(said).strip():
            entry["definition"] = " ".join(str(said).split())
        columns[name] = entry if len(entry) > 1 else code
        row_of_col[name] = row
        e = r[C_EDGES - 1].value
        if e not in (None, ""):
            where = f"Columns!{_col(C_EDGES)}{row}"
            typed[name] = str(e).strip()
            edge_cells[name] = where
            if isinstance(e, (int, float)) and not isinstance(e, bool) and abs(e) >= 100000 and float(e).is_integer():
                # the second walk, defect 2: Excel read 620,680,740 as the number 620680740
                problems.append(f'{where}: the band edges for "{name}" read as the single number {e:,.0f}. '
                                f'Excel dropped the commas. Type them with semicolons: 620; 680; 740.')
            elif str(e).strip().lower().startswith("every"):
                # a band width: "every 20" cuts at every 20 points across the column's values
                # (the firm, 25 Sep 2026: "20 point bands look very different")
                try:
                    w = float(str(e).strip().lower().removeprefix("every").split()[0].replace(",", ""))
                    if w <= 0:
                        raise ValueError
                    widths[name] = w
                except (ValueError, IndexError):
                    problems.append(f'{where}: "{e}" should read like every 20: the word every, then how wide '
                                    f'each band is.')
            else:
                try:
                    pts = [float(x) for x in str(e).replace(";", ",").split(",") if x.strip()]
                    if not pts or any(b <= a for a, b in zip(pts, pts[1:])):
                        raise ValueError
                    edges[name] = pts
                except ValueError:
                    problems.append(f'{where}: the band edges for "{name}" must be rising numbers, like '
                                    f'620; 680; 740.')
        sh = r[C_SHOW - 1].value
        if sh:
            if sh not in SHOW_OPTIONS:
                problems.append(f'Columns!{_col(C_SHOW)}{row}: Show per pocket takes median or average.')
            elif cat[code].cut == "none" or code in ("category", "term"):
                problems.append(f'Columns!{_col(C_SHOW)}{row}: "{name}" isn\'t a number column, so it has no '
                                f'{sh} to show. Clear the cell, or change what it is.')
            else:
                show[name] = sh
    if chosen is not None:
        split, skip, filt = _cuts_chosen(chosen, choice_cells, columns, row_of_col, cat, problems)
    derived = _read_made(wb, columns, made_rows, problems)
    held_to = _what_is_run(wb, book, use, columns, cat, problems, tuple(d["name"] for d in derived))
    scouting = bool(held_to and held_to.get(SCOUT_KEY))       # Goal 2 item 9: find first, then confirm
    if scouting:
        held_to = None
    if problems:
        return None, problems, about
    if split:
        # a column that splits the pockets isn't also cut: its own band split by itself says nothing
        skip.add(split[0][0])
    raw_bands, raw_dims = [], []
    names: set[str] = set()

    def uniq(n):
        base, i = n, 2
        while n in names:
            n, i = f"{base}_{i}", i + 1
        names.add(n)
        return n

    for c, v in columns.items():
        m = v if isinstance(v, str) else v["means"]
        if c in skip:
            continue
        if cat[m].cut == "band":
            b = {"name": uniq(profile._slug(c)), "field": c}
            b.update({"edges": edges[c]} if c in edges else {"count": int(use["band_count"]),
                                                              "cut": use["band_cut"]})
            few = use.get("few_values")
            if "count" in b and isinstance(few, (int, float)) and not isinstance(few, bool):
                # too repeated to cut and this few values: one band per value (the firm, 30 Sep 2026)
                b["few_values"] = int(few)
            raw_bands.append(b)
        elif cat[m].cut == "dimension":
            raw_dims.append({"name": uniq(profile._slug(c)), "field": c})
    if held_to:
        # 4b: the pockets are the pre-spec's strata, cut as the grids cut them, so each must be cut on Columns
        cut_by = {b["field"] for b in raw_bands} | {d["field"] for d in raw_dims}
        for s in held_to["spec"].strata:
            if s in cut_by:
                continue
            why = ("no column on Columns has that name" if s not in columns
                   else f"{s} splits the pockets, so it isn't cut on its own" if split and split[0][0] == s
                   else "the launcher doesn't cut by it. Tick it under Choose tests (a band or a segment), then "
                        "press Next")
            problems.append(f"{held_to['cell']}: the pre-spec cuts the pockets by {s}, and {why}. Or fix the "
                            f"pre-spec.")
        if problems:
            return None, problems, about
    measures = [{"name": "loans", "mode": "count"}]
    for c, how in show.items():
        measures.append({"name": f"{how} {c}", "mode": "median", "value": c, "show": how})
    raw = {
        "name": profile._slug(Path(about.get("extract") or book.stem).stem),
        "schema_version": cfgmod.SCHEMA_VERSION,
        "columns_confirmed": True,
        "columns": columns,
        "bands": raw_bands,
        "dimensions": raw_dims,
        "measures": measures,
        # a test of a new variable isn't asked the bleed's settings (settings.yaml only_when): it builds no pocket,
        # so what stands in for them here decides nothing, and Record's Settings leaves them off
        "benchmark": {"min_units": _num_or(use.get("min_loans", 30), 30, int),
                      "min_events": int(use.get("min_events", 10)),
                      "worse_at": _num_or(use["worse_at"], 1.25, float),
                      "better_at": _num_or(use.get("better_at", 0.8), 0.8, float),
                      "confidence": float(use["confidence"]), "power": float(use.get("power", 0.8)),
                      "compare_to": use.get("compare_to", "peers"), "many_tests": use.get("many_tests", "bh"),
                      "materiality": use["materiality"], "revenue_line": use.get("revenue_line")},
        "questions": questions or [],
    }
    if use.get(RUN_KIND) == NEW_VARIABLE:
        raw["run_kind"] = NEW_VARIABLE              # its dollar columns are optional (cfgmod.RUN_KINDS)
    if split:
        name, code = split[0]
        raw["split"] = {"field": name, "how": "each_value" if cat[code].cut == "dimension" else "own_median"}
    if filt:
        raw["filter_by"] = filt                     # Grids' Only loans where (the firm, 30 Sep 2026)
    if derived:
        raw["derived"] = derived                    # fix 3.9
    about = dict(about)
    about["_widths"] = {c: w for c, w in widths.items() if c not in skip}
    about["_typed_edges"] = typed
    about["_edge_cells"] = edge_cells
    about["_suggest"] = {k for k in ("min_loans", "worse_at", "better_at") if use.get(k) in ("calc", "luck")}
    about["_use"] = dict(use)
    about["_prespec"] = held_to
    about["_scout"] = chosen if scouting else None
    return raw, [], about


def _cuts_chosen(chosen, cells: dict, columns: dict, row_of_col: dict, cat, problems: list[str]):
    """The split, the columns left uncut and the Grids' filter column, from what the launcher chose. A
    column is cut when the launcher ticked it (or, with nothing narrowed, when
    its meaning cuts it), as a band or a segment by its meaning on Columns. ORIG_YEAR, the year of the column
    marked Origination date, can split and filter though it isn't a column of the extract."""
    split: list[tuple[str, str]] = []
    dated = next((c for c, v in columns.items() if (v if isinstance(v, str) else v["means"]) == "origination_date"),
                 None)

    def no_year(cell: str, what: str) -> None:
        problems.append(f"{cell}: {what} by {ch.ORIG_YEAR}, the year each loan was made, and no column on Columns "
                        f"is marked {cat['origination_date'].label}. Mark the column that holds it, or choose again "
                        f"in the launcher.")
    for key in ("bands", "segments"):
        for name in getattr(chosen, key) or ():
            if name not in columns:
                problems.append(f"{cells[key]}: {name} isn't a column in this extract. Choose again in the launcher.")
    cut = chosen.cut()
    skip = {c for c in columns if cut is not None and c not in cut}
    if chosen.split == ch.ORIG_YEAR and ch.ORIG_YEAR not in columns:
        if dated:
            split.append((ch.ORIG_YEAR, "category"))            # one value per year, each against the rest
        else:
            no_year(cells["split"], "the launcher splits the pockets")
    elif chosen.split:
        name = chosen.split
        code = columns.get(name)
        code = code if code is None or isinstance(code, str) else code["means"]
        if code is None:
            problems.append(f"{cells['split']}: {name} isn't a column in this extract. Choose again in the launcher.")
        elif cat[code].cut in ("band", "dimension"):
            split.append((name, code))
        else:
            # the third walk, defect 7: GCO split by itself read 93.83x; the key "had too few loans"
            problems.append(f'{cells["split"]}: "{name}" is marked {cat[code].label} on Columns '
                            f'(Columns!{_col(C_MEANS)}{row_of_col[name]}), which can\'t split the pockets. Only a '
                            f"score, ratio, amount (the booked amount too) or category can. Choose another in the "
                            f"launcher, or fix what it is.")
    filt = None
    if chosen.filter and chosen.run_kind != ch.NEW_VARIABLE:
        name = chosen.filter
        code = columns.get(name)
        code = code if code is None or isinstance(code, str) else code["means"]
        where = cells.get("filter", "Control")
        if name == ch.ORIG_YEAR and code is None:
            if dated:
                filt = name
            else:
                no_year(where, "the launcher filters the Grids")
        elif code is None:
            problems.append(f"{where}: {name} isn't a column in this extract. Choose again in the launcher.")
        elif cat[code].cut == "dimension":
            filt = name
        else:
            problems.append(f'{where}: "{name}" is marked {cat[code].label} on Columns '
                            f'(Columns!{_col(C_MEANS)}{row_of_col[name]}), and only a category (or '
                            f'{ch.ORIG_YEAR_LABEL}) can filter the Grids. Choose another in the launcher, or fix '
                            f'what it is.')
    if chosen.run_kind == ch.NEW_VARIABLE and chosen.outcome:
        code = columns.get(chosen.outcome)
        code = code if code is None or isinstance(code, str) else code["means"]
        if code != "outcome":
            where = (f"Columns!{_col(C_MEANS)}{row_of_col[chosen.outcome]}" if chosen.outcome in row_of_col
                     else "Columns")
            problems.append(f"{cells['outcome']}: the launcher tests against {chosen.outcome}, and {where} doesn't "
                            f"mark it {cat['outcome'].label}. Mark it so, or choose the outcome again in the "
                            f"launcher.")
    return split, skip, filt


def _what_is_run(wb, book: Path, use: dict, columns: dict, cat, problems: list[str], made: tuple = ()) -> dict | None:
    """What are you running? Each answer's own minimum, refused by name: the
    columns it needs (NEEDS_COLUMNS), and for a new variable the follow-up. The
    pre-spec is read only for a test from a pre-spec (fix 3.15), and refused
    under the bleed analysis, which isn't a test of a new variable. A blank
    answer was refused already, by control.read_control."""
    kind, step = use.get(RUN_KIND), use.get(STEP)
    ws = wb[control.SHEET]
    kind_cell = f"{control.SHEET}!C{control.row_of(ws, RUN_KIND)}"
    labels = {o.value: o.label for s in control.load_settings() if s.key in (RUN_KIND, STEP) for o in s.options}
    text, cell = control.read_prespec(ws)
    means = {c: (v if isinstance(v, str) else v["means"]) for c, v in columns.items()}
    for m in NEEDS_COLUMNS.get(kind, cfgmod.CORE if kind is None else ()):
        hits = [c for c, code in means.items() if code == m]
        if len(hits) != 1:
            who = labels.get(kind, "Every run")
            problems.append(f"Columns: {who} needs one column marked {cat[m].label}, and "
                            + (f"none is." if not hits else f"{len(hits)} are: {', '.join(hits)}. Keep one."))
    if kind == BLEED:
        if text is not None:
            problems.append(f'{cell}: {labels[BLEED]} isn\'t a test of a new variable, so it isn\'t held to a '
                            f'pre-spec. Clear the cell, or change "What are you running?" ({kind_cell}).')
        return None
    if kind == NEW_VARIABLE and step == SCOUT:
        # Goal 2 item 9: find on the development loans, write the pre-spec, confirm it on the rest (scout.py). The
        # scouting itself runs once the engine has read the loans (run); here, only what it needs is checked
        step_cell = f"{control.SHEET}!C{control.row_of(ws, STEP)}"
        why = scout.missing()
        if why:
            problems.append(f"{step_cell}: {why}")
            return None
        chosen, cells = control.read_choices(ws)
        if chosen is not None:
            for c in list(chosen.test) + list(chosen.hold):
                if c not in columns:
                    problems.append(f"{cells.get('test', step_cell)}: {c} isn't a column in this extract. Choose "
                                    f"again in the launcher.")
            if not chosen.test and not made:
                problems.append(f"{cells.get('test', step_cell)}: tick at least one column Test it in the launcher, "
                                f"for scouting to rank.")
            if not chosen.outcome:
                problems.append(f"{cells.get('outcome', step_cell)}: pick the outcome in the launcher.")
        return {SCOUT_KEY: True}
    if kind == NEW_VARIABLE and step == FROM_PRESPEC and text is None:
        problems.append(f'{cell}: "{labels[FROM_PRESPEC]}" needs the pre-spec file named here.')
        return None
    held_to = confirmatory.read(wb, book, problems)          # fix 3.15
    for c in (held_to["spec"].columns if held_to else ()):
        if c not in columns:
            problems.append(f"{cell}: the pre-spec tests {c}, and no column on Columns has that name. Make it under "
                            f"Add a column on Columns and press Set up again, or fix the pre-spec.")
    return held_to


def what_was_run(used: dict) -> str | None:
    """The answer, in the tab's words: "Where the book bleeds", or "Finding and
    testing a new variable: test from a pre-spec"."""
    labels = {(s.key, o.value): o.label for s in control.load_settings() if s.key in (RUN_KIND, STEP)
              for o in s.options}
    kind = labels.get((RUN_KIND, used.get(RUN_KIND)))
    if kind is None:
        return None
    step = labels.get((STEP, used.get(STEP))) if used.get(RUN_KIND) == NEW_VARIABLE else None
    return f"{kind}: {step[0].lower() + step[1:]}" if step else kind


def _ran_words(res) -> str:
    """" What was run: Where the book bleeds.", for the first line of a run's Log entry and the launcher."""
    ran = what_was_run(getattr(res, "control_used", None) or {})
    return f" What was run: {ran}." if ran else ""


def _read_made(wb, columns: dict, made_rows: dict, problems: list[str]) -> list[dict]:
    """The new columns under "Add a column", each checked against the table above it: a new column must have
    been made by Set up from exactly what the block says now, or the Columns and Look tabs describe something
    else (fix 3.9: "if a derived column is defined but the workbook hasn't been set up since, Run says to press
    Set up again")."""
    defs, bad = control.read_derived(wb["Columns"], first=C_NAME, key_col=C_QKEY)
    problems += bad
    out = []
    for d in defs:
        where = f"Columns!{_col(C_NAME)}{d['row']}"
        made = made_rows.get(d["name"])
        now = f"{d['top']} ÷ {d['bottom']}"
        if d["name"] in columns and made is None:
            problems.append(f'{where}: "{d["name"]}" is already a column in the extract. Give the new column a name '
                            f'of its own.')
        elif made is None:
            problems.append(f'{where}: the new column "{d["name"]}" isn\'t in the table yet. Press Set up again, '
                            f'then check it on Columns and Look.')
        elif made[1] != now:
            problems.append(f'{where}: "{d["name"]}" was made as {made[1]} and the row now says {now}. Press Set up '
                            f'again, so Columns and Look show it as it is now.')
        else:
            out.append({"name": d["name"], "top": d["top"], "bottom": d["bottom"]})
    named = {d["name"] for d in defs}
    for name, (row, _) in made_rows.items():
        if name not in named:
            problems.append(f'Columns!{_col(C_NAME)}{row}: "{name}" was a new column, and "Add a column" doesn\'t '
                            f'have it now. Press Set up again.')
    return out


def _num_or(v, provisional, kind):
    """A Control answer as a number; a suggestion ("calc", "luck") runs first on a
    provisional number and is then worked out from the book (see _suggested)."""
    return provisional if v in ("calc", "luck") else kind(v)


def _band_widths(raw: dict, widths: dict[str, float], cfg, table, cells: dict[str, str] | None = None) -> list[str]:
    """Turn "every 20" into edges over the column's own values (missing codes
    left out). Refuses a width that would make more than 50 bands."""
    out = []
    cells = cells or {}
    for b in raw["bands"]:
        w = widths.get(b["field"])
        if not w:
            continue
        rule = cfg.missing.get(b["field"])
        vals = [v for v in (engine.classify_number(r.get(b["field"]), rule)[0] for r in table.rows) if v is not None]
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        first = math.floor(lo / w) * w + w
        pts = []
        x = first
        while x <= hi and len(pts) < 60:
            pts.append(round(x, 10))
            x += w
        if len(pts) + 1 > 50:
            total = int((hi - first) // w) + 2
            out.append(f'{cells.get(b["field"], "Columns")}: every {engine._fmt(w)} on "{b["field"]}" would make '
                       f'{total:,} bands ({engine._fmt(lo)} to {engine._fmt(hi)}). Use a wider band, so there '
                       f'are 50 bands or fewer.')
            continue
        b.pop("count", None)
        b.pop("cut", None)
        b.pop("few_values", None)
        b["edges"] = pts or [round(first, 10)]
    return out


def _suggested(res, which: set[str]) -> dict[str, float]:
    """The suggested Control answers, worked out from a first pass over the book
    (the firm, 25 Sep 2026: suggestions "where there's a calculation").
    min_loans: enough loans to expect 5 with the outcome at the book's rate, the
    textbook floor for a test of a rate (n x p of 5 or more). The fifth walk found
    10 hid a 99-loan pocket with 50 bad loans.
    worse_at / better_at: the smallest outcome gap a typical pocket can call
    significant (the median over pockets big enough to test), and one over it."""
    out: dict[str, float] = {}
    fallback: set[str] = set()
    rate = res.total.rates["outcome_loans"].rate if "outcome_loans" in res.total.rates else None
    if "min_loans" in which:
        out["min_loans"] = max(2, math.ceil(5 / rate)) if rate else 30
        if not rate:
            fallback.add("min_loans")
    if which & {"worse_at", "better_at"}:
        floor = out.get("min_loans", res.config.benchmark.min_units)
        got = luck_gap(res, "outcome_loans", floor)
        if got is None:
            fallback.update(which & {"worse_at", "better_at"})
        g = max(got or 1.25, 1.05)
        if "worse_at" in which:
            out["worse_at"] = g
        if "better_at" in which:
            out["better_at"] = round(1 / g, 2)
    res.suggest_fallback = fallback
    return out


SUGGEST_KEYS = ("min_loans", "worse_at", "better_at")
SUGGEST_COL = control.SUGGEST_COL             # I on Control: worked out from the loans
#: the answers a first pass at Set up runs with where Control has none yet: never written to the workbook
PROVISIONAL = {"min_events": "10 losses", "materiality": "No floor", "compare_to": "The rest of its band",
               "confidence": "95%", "revenue_line": "Each pocket's own test (suggested)"}


def _suggest_values(res, which: set[str]) -> tuple[dict[str, float], set[str]]:
    """_suggested without touching `res`: the values, and those with nothing to work them out from."""
    had = getattr(res, "suggest_fallback", None)
    out = _suggested(res, which)
    fallback = res.suggest_fallback
    if had is None:
        del res.suggest_fallback
    else:
        res.suggest_fallback = had
    return out, fallback


def _suggest_at_set_up(wb, book: Path, table, memory_path, testing: bool = False
                       ) -> tuple[dict[str, float], set[str]]:
    """The suggested Control answers, before anyone has answered anything (the
    firm, 26 Sep 2026: "configure what you can, and then do the workbook config
    items so that there are suggestions to be made"). The pockets are cut as
    the launcher chose, at the default edges, and the first pass is the one Run
    makes: the workbook with the suggested options picked and any other blank
    call given a stand-in, read by read_book, run without the shuffle test.
    The stand-ins go into the open workbook and every one is put back before
    this returns (found 26 Sep 2026: a saved copy cost two saves and two loads
    of the whole workbook). Nothing here stays in the workbook but the values.

    A test of a new variable (`testing`) builds no pocket, so its one suggestion, worse at, comes from the
    confirmation's own groups instead (`test_gap`): the pre-spec's column cut into its groups on the loans they
    were found on. No bleed grid is built for it (found 27 Sep 2026: this first pass cut every column as a bleed
    would, the grids a new variable never shows)."""
    changed: list[tuple[Any, Any]] = []

    def put(cell, v) -> None:
        changed.append((cell, cell.value))
        cell.value = v

    try:
        ws = wb[control.SHEET]
        labels = {s.key: s for s in control.load_settings()}
        for r in ws.iter_rows(min_row=control.FIRST_ROW):
            key = r[control.KEY_COL - 1].value
            if key in SUGGEST_KEYS:
                put(r[control.CHOOSE_COL - 1], next(o.label for o in labels[key].options
                                                    if o.value in ("calc", "luck")))
                put(r[control.OWN_COL - 1], None)
            elif key in PROVISIONAL and control.answer_of(key, r[control.CHOOSE_COL - 1].value,
                                                          r[control.OWN_COL - 1].value) is None:
                put(r[control.CHOOSE_COL - 1], PROVISIONAL[key])
            elif key == RUN_KIND and not testing:
                put(r[control.CHOOSE_COL - 1], next(o.label for o in labels[key].options if o.value == BLEED))
            elif key == control.PRESPEC_KEY and not testing:
                put(r[control.CHOOSE_COL - 1], None)
        put(wb["Columns"][CONFIRM_CELL], "Yes")
        raw, problems, about = read_book(book, memory_path, wb=wb)
        if problems:
            return {}, set()
        cfg = cfgmod.parse(raw)
        if _band_widths(raw, about.get("_widths") or {}, cfg, table, about.get("_edge_cells")):
            return {}, set()
        if about.get("_widths"):
            cfg = cfgmod.parse(raw)
        first = cfgmod.Config(**{**cfg.__dict__, "benchmark": cfgmod.Benchmark(
            **{**cfg.benchmark.__dict__, "shuffles": 0})})
        if testing:
            got = about.get("_prespec")
            if not got:
                return {}, set()
            res = engine.run(first, table)
            ps = got["spec"]
            named = prespec.named(ps, ranges={c: confirmatory.column_range(res, c) for c in ps.columns})
            gap = test_gap(confirmatory.run_tests(res, named), cfg.benchmark.confidence)
            return ({"worse_at": gap}, set()) if gap is not None else ({}, set())
        return _suggest_values(engine.run(first, table), set(SUGGEST_KEYS))
    except Exception:
        # a book the first pass can't cut yet (no outcome marked, say): the Run works them out instead
        return {}, set()
    finally:
        for cell, v in reversed(changed):
            cell.value = v


def test_gap(t, confidence: float) -> float | None:
    """A test of a new variable's suggested worse line: the smallest odds ratio a group of typical size could call
    significant against the reference group, on the loans the groups were found on (development). For each group
    other than the reference, exp(z x the standard error of its log odds ratio, sqrt(1 / (n p q) + 1 / (n_ref p
    q))), at the development loans' bad rate p and the confidence's z; the median of those, as a pocket's is for
    the bleed (`luck_gap`). `t` is one test, or a shortlist's (one per input): the median is then over every
    candidate's groups, each against its own reference. It reads how many loans each group holds and the overall bad
    rate, never which group went bad. None when there is nothing to work it out from."""
    z = stats.z_for_confidence(confidence)
    gaps = []
    for x in (t if isinstance(t, (list, tuple)) else [t]):
        d = getattr(x, "development", None)
        if x is None or x.problem or d is None or not d.n:
            continue
        p = d.n_bad / d.n
        nref = d.loans[x.ref]
        if not 0 < p < 1 or not nref:
            continue
        pq = p * (1 - p)
        gaps += [math.exp(z * math.sqrt(1 / (n * pq) + 1 / (nref * pq))) for k, n in enumerate(d.loans)
                 if k != x.ref and n]
    return round(statistics.median(gaps), 2) if gaps else None


def _suggest_from_the_test(res, picked: set[str]) -> None:
    """A test of a new variable's suggestion, worked out once its test has run (checks.attach): worse at from the
    confirmation's own groups (`test_gap`). When the answer on Control is the suggestion, the run uses it: the
    New variables tab's worse line reads it. Nothing else on the tab depends on it."""
    t = getattr(getattr(res, "prespec", None), "tests", None)
    b = res.config.benchmark
    gap = test_gap(t, b.confidence) if t and b is not None else None
    fallback = set() if gap is not None else {"worse_at"}
    value = max(gap if gap is not None else 1.25, 1.05)
    res.suggest_all = ({"worse_at": value}, fallback)
    res.suggested = {"worse_at": value} if "worse_at" in picked else {}
    res.suggest_fallback = fallback & set(res.suggested)
    if res.suggested and b is not None:
        better = b.better_at if b.better_at < value else round(1 / value, 2)
        res.config = cfgmod.Config(**{**res.config.__dict__, "benchmark": cfgmod.Benchmark(
            **{**b.__dict__, "worse_at": value, "better_at": better})})


def _suggestion_words(key: str, v: float, fallback: bool, when: str) -> str:
    said = f"{v:,.0f}" if key == "min_loans" else f"{v:.2f}x"
    if fallback:
        return f"usual value: {said} (nothing in this extract to work it out from)"
    return f"suggested: {said}, {when}"


def _suggestions(ws, values: dict[str, float], fallback: set[str], when: str) -> None:
    """The worked-out value beside each suggested setting, so it is seen before
    it is chosen. The answer cell is left alone (ruling OC-13)."""
    for r in ws.iter_rows(min_row=control.FIRST_ROW):
        key = r[control.KEY_COL - 1].value
        if key not in SUGGEST_KEYS:
            continue
        v = values.get(key)
        if v is None and ws.row_dimensions[r[0].row].hidden:
            ws.cell(row=r[0].row, column=SUGGEST_COL).value = None      # not asked for this run (only_when)
            continue
        c = ws.cell(row=r[0].row, column=SUGGEST_COL,
                    value=_suggestion_words(key, v, key in fallback, when) if v is not None
                    else "Worked out when you press Run")
        c.font = Font(name="Calibri", size=10, bold=v is not None and key not in fallback,
                      color=INK if v is not None else SLATE)
        c.alignment = Alignment(horizontal="left", vertical="center")
        if key in control.NOW_KEYS:
            # the number itself, hidden, for Comes to before the first Run (G)
            ws.cell(row=r[0].row, column=control.WORKED_COL).value = v


def _writable(book: Path) -> bool:
    """False when another program (Excel) holds the file. Checked before
    anything is changed, so a refused run leaves no trace (second walk, defect 8)."""
    try:
        with open(book, "r+b"):
            return True
    except PermissionError:
        return False
    except OSError:
        return True


def _refused(wb, book: Path, lines: list[str], outcome: Outcome) -> Outcome:
    """A refused Run: its lines on the Log, the workbook saved once, and the refusal handed back."""
    _log(wb, lines)
    _save(wb, book)
    return outcome


def _save(wb, book: Path) -> bool:
    try:
        wb.save(book)
    except PermissionError:
        return False
    return True


@control.settings_once
def run(book: str | Path, extract: str | Path | None = None, memory_path: str | Path | None = None) -> Outcome:
    """Run from the workbook. `extract` is the file picked in the launcher; it
    wins over the path remembered at set up, so a workbook copied to another
    folder runs that folder's extract (second walk, defect 1).

    The workbook is loaded once and saved once (found 26 Sep 2026: a Run loaded
    it eight times and saved it three): every reader and writer below is handed
    the open workbook."""
    book = Path(book)
    if not book.exists():
        return Outcome(False, book, [f"Couldn't find {book.name}. Press Set up first."])
    if not _writable(book):
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Run again."])
    try:
        wb = _load(book)
    except Exception as exc:  # the file itself: in words, never a traceback
        return Outcome(False, book, [f"Couldn't open {book.name}: {exc}. Press Set up again."])
    raw, problems, about = read_book(book, memory_path, wb=wb)
    if raw is not None:
        try:
            cfg = cfgmod.parse(raw)
        except cfgmod.ConfigError as exc:
            problems = [_plain(p) + _changed_away(wb, p) for p in exc.problems]
    if problems:
        return _refused(wb, book, ["Couldn't run. Fix these, save, close, and press Run again:"] + problems,
                        Outcome(False, book, ["Couldn't run yet. Fix these in the workbook, save, close, and press "
                                              "Run again:"] + [f"  - {p}" for p in problems], problems=list(problems)))
    notes = []
    if extract is not None:
        src = Path(extract)
    else:
        src = Path(about["extract"])
        if not src.exists() and about.get("extract name"):
            beside = book.with_name(str(about["extract name"]))
            if beside.exists():
                src = beside
    try:
        # read once, and its fingerprint taken from the same bytes (the bank, 30 Sep 2026: the fingerprint's own
        # read raised PermissionError with the extract open in Excel, and a traceback opened in Notepad)
        table = read_table(src)
    except OSError as exc:
        return Outcome(False, book, [cant_read(src, exc, "Run")])
    if about.get("sha256") and table.sha256 != about["sha256"]:
        notes.append(f"{src.name} has changed since Set up. If columns were added or renamed, press Set up first.")
    far = _band_widths(raw, about.get("_widths") or {}, cfg, table, about.get("_edge_cells"))
    if about.get("_widths") and not far:
        cfg = cfgmod.parse(raw)
    far += _edges_outside(wb, raw, cfg, table)
    if far:
        return _refused(wb, book, ["Couldn't run. Fix these, save, close, and press Run again:"] + far,
                        Outcome(False, book, ["Couldn't run yet. Fix these in the workbook, save, close, and press "
                                              "Run again:"] + [f"  - {p}" for p in far], problems=list(far)))
    suggested: dict[str, float] = {}
    testing = cfg.run_kind == NEW_VARIABLE
    try:
        if about.get("_suggest") and not testing:
            # a suggested answer is worked out from a first pass, then the run is done again with it. The
            # first pass needs rates and pocket sizes only, so it runs no shuffle test
            first = cfg if cfg.benchmark is None else cfgmod.Config(**{
                **cfg.__dict__, "benchmark": cfgmod.Benchmark(**{**cfg.benchmark.__dict__, "shuffles": 0})})
            res = engine.run(first, table)
            suggested = _suggested(res, about["_suggest"])
            bm = raw["benchmark"]
            bm["min_units"] = int(suggested.get("min_loans", bm["min_units"]))
            bm["worse_at"] = float(suggested.get("worse_at", bm["worse_at"]))
            bm["better_at"] = float(suggested.get("better_at", bm["better_at"]))
            if bm["better_at"] >= bm["worse_at"]:
                bm["better_at"] = round(1 / bm["worse_at"], 2)
            fallback = getattr(res, "suggest_fallback", set())
            cfg = cfgmod.parse(raw)
            res = engine.run(cfg, table)
            res.suggest_fallback = fallback
        else:
            res = engine.run(cfg, table)
        res.suggested = suggested
        res.control_used = about.get("_use") or {}
        if not testing:
            # every suggestion, refreshed for Control whether or not it was picked; a picked one is what was used
            values, fb = _suggest_values(res, set(SUGGEST_KEYS))
            fb = (fb - set(suggested)) | (getattr(res, "suggest_fallback", set()) & set(suggested))
            res.suggest_all = ({**values, **suggested}, fb)
    except (engine.ColumnsMissing, engine.NothingToCut) as exc:
        msg = re.sub(r"used by dimension \w+", "a segment", re.sub(r"used by band \w+", "a band", str(exc)))
        msg = msg.replace("`", '"')
        if isinstance(exc, engine.ColumnsMissing):
            # the third walk, defect 15: a renamed column needs Set up, and the message didn't say so
            msg += ". If a column was renamed or dropped, press Set up again."
        return _refused(wb, book, ["Couldn't run:", msg], Outcome(False, book, [f"Couldn't run: {msg}"]))
    except perm.NumpyMissing as exc:
        return _refused(wb, book, ["Couldn't run:", str(exc)], Outcome(False, book, [f"Couldn't run: {exc}"]))
    waits = _scout(res, about, book)            # Goal 2 item 9: find on the development loans, write the pre-spec
    if isinstance(waits, Outcome):
        return _refused(wb, book, waits.lines, waits)
    about["_wb"] = wb
    checks.attach(book, about, res)             # fixes 3.12, 3.15: the pre-spec's state and the edges on Columns
    if testing:
        _suggest_from_the_test(res, about.get("_suggest") or set())
    forgotten = _forget(wb, memory_path)
    dropped = {g.split(" ", 1)[1] for g in forgotten if g.startswith("column ")}
    if dropped:
        # a Forget means "don't carry this over"; this run does not re-teach it (second walk, defect 5)
        cfg = cfgmod.Config(**{**cfg.__dict__, "columns": {k: v for k, v in cfg.columns.items() if k not in dropped}})
    memory.remember(cfg, memory_path)
    typed = about.get("_typed_edges") or {}
    cat = meanings.catalog()
    bands_only = {c for c, v in (cfg.columns or {}).items() if cat.get(v[0]) and cat[v[0]].cut == "band"}
    memory.remember_edges({c: typed.get(c) for c in bands_only if c not in dropped}, memory_path)
    _write_results(wb, book, res, memory_path, src, dropped, len(table.columns))
    from . import look                  # fix 3.8: the Look tab's scatters, only when the split or the bands moved
    split_col, band_cols = res.config.split and res.config.split[0], [b.field for b in res.config.bands]
    if look.answers_moved(wb, res.config.missing):
        # a Treat as answer changed since Look was drawn (at the bank, 29 Sep 2026: a -99,000,901 answered missing
        # still set Look's smallest and mean): the blocks are drawn again from what the Run reads
        look.write_look(wb, res.table or table, look.drawn_columns(wb), split=split_col, bands=band_cols,
                        edge_rows={str(r[C_NAME - 1].value): r[0].row for r in table_rows(wb["Columns"])
                                   if r[C_NAME - 1].value},
                        treat_rows=_treat_rows(wb["Columns"]), rules=res.config.missing, keep_inputs=True)
    else:
        look.refresh(wb, res.table or table, split_col, band_cols, rules=res.config.missing)
    summary = _headline(res, wb)
    _log(wb, [_ran_on(res, src) + _ran_words(res)]
         + scout_tab.log_lines(res)             # Goal 2 item 9: what scouting wrote, before any held-back result
         + [f"Confirmation waits: {w}" for w in res.scout_waits]
         + confirmatory.log_lines(res)          # fix 3.15: held to a pre-spec, and whether it touched the holdout
         + scout_tab.held_back_lines(res)       # OC-51: the tree's out-of-time check read the held-back loans too
         + [f"Warning: {_plain_warning(w)}" for w in res.warnings], redraw=False)
    _record(wb, res, src, f"{book.stem} - what ran.yaml")     # Check and the Log, this Run's entry included
    _order(wb)
    if not _save(wb, book):
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Run again."])
    audit = book.with_name(f"{book.stem} - what ran.yaml")
    head = "# Exactly what the last Run used.\n"
    if per_pocket(res):
        head += "# revenue_line: each pocket's own test (profit counts only when its gap is significant)\n"
    if what_was_run(res.control_used):
        head += f"# What was run: {what_was_run(res.control_used)}\n"
    head += _dates_head(res)
    head += "".join(f"# {x}\n" for x in scout_tab.log_lines(res))
    head += confirmatory.what_ran(res)
    head += "".join(f"# {x}\n" for x in scout_tab.held_back_lines(res))
    if isinstance(raw.get("benchmark"), dict) and cfg.benchmark is not None:
        raw["benchmark"].setdefault("shuffles", cfg.benchmark.shuffles)
    audit.write_text(head + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    lines = notes + [_ran_on(res, src) + _ran_words(res)]
    each = getattr(res, "value_bands", {})
    lines += [engine.EACH_VALUE_SAYS.format(b.field) + "." for b in res.config.bands if b.name in each]
    lines += _top_lines(res)
    lines += scout_tab.launcher_lines(res)
    lines += confirmatory.launcher_lines(res)
    lines += scout_tab.held_back_lines(res)
    # the same rows the tab shades blue (its flag), and pockets counted once (the seventh walk, defect 7:
    # "58 pockets" was 58 rows from 23 pockets)
    blue = [(gi, key) for gi, g in enumerate(res.grids) for key, c in g.inner() for m in res.measures
            if m.is_rate and c.rates[m.name].material and c.rates[m.name].flag in (engine.THIN, engine.FEW)]
    small = len(set(blue))
    if small:
        rows_said = "" if len(blue) == small else f" ({len(blue)} rows: a pocket has a row for each measure)"
        lines.append(f"{_n(small, 'pocket')} {'is' if small == 1 else 'are'} material but too small to test: "
                     f"Worse? reads Too few losses and Material? Yes on Pockets{rows_said}, to look at by hand.")
    sug = getattr(res, "suggested", None) or {}
    if sug:
        said = {"min_loans": "fewest loans {:,}", "worse_at": "worse at {:.2f}x", "better_at": "better at {:.2f}x"}
        fb = getattr(res, "suggest_fallback", set())
        worked = [said[k].format(v) for k, v in sug.items() if k not in fb]
        usual = [said[k].format(v) for k, v in sug.items() if k in fb]
        if worked:
            lines.append("Worked out from this book: " + "; ".join(worked) + ".")
        if usual:
            lines.append("Nothing in this book to work these out from, so the usual values were used: "
                         + "; ".join(usual) + ".")
    if cfg.split and bleed_tabs(res):
        sf, how = cfg.split
        lines.append(f"Split by {sf}" + (f" (the year in {cfg.origination_date})" if sf == ch.ORIG_YEAR else "")
                     + ": " + ("each pocket halved at its own median. See the Split tab, and Pockets "
                                           f"split by {sf}." if how == "own_median" else
                                           f"each pocket split by each value. See the Split tab, and Pockets split "
                                           f"by {sf}.")
                     + f" {sf} isn't cut on its own while it splits.")
    if cfg.filter_by and bleed_tabs(res) and res.filter_values:
        lines.append(f"Grids filter by {filter_words(res)}: {filter_counts(res)}. Pick one in Grids' Only loans "
                     f"where.")
    if dropped:
        lines.append(f"Forgot {', '.join(sorted(dropped))}, as marked on Columns. Check "
                     f"{'it' if len(dropped) == 1 else 'them'} and set C3 to Yes before the next Run.")
    tested = getattr(getattr(res, "prespec", None), "tests", None) or []
    lines.append(f"Open {book.name}: start with "
                 + (f"{confirm_tab.SHEET}." if tested and all(x.problem is None for x in tested)
                    else "Pockets." if bleed_tabs(res) else f"{scout.SHEET}." if res.scout is not None
                    else f"{record.SHEET}."))
    summary["first"] = first_lines(lines)
    if res.scout_waits:
        # found and written, not yet confirmed: the pre-spec asks for an answer first (OC-13)
        lines += ["The held-back loans weren't tested yet. The pre-spec scouting wrote waits for:"] + \
            [f"  - {w}" for w in res.scout_waits]
        return Outcome(False, book, lines, problems=list(res.scout_waits), summary=summary)
    return Outcome(True, book, lines, summary=summary)


def first_lines(lines: list[str]) -> list[str]:
    """The Run's first two lines, for the launcher's finished screen (J, the firm, 27 Sep 2026): where to start
    reading, then the first of a pre-spec changed after a held-back run, the pockets too small to test, what splits
    the pockets, and what the Run ran on. The rest of what the Run said is on Record."""
    start = [x for x in lines if x.startswith("Open ") and ": start with " in x]
    return (start + [x for x in lines if x.startswith(confirmatory.CHANGED)]
            + [x for x in lines if " material but too small to test" in x]
            + [x for x in lines if x.startswith("Split by ")] + [x for x in lines if x.startswith("Ran on ")])[:2]


def _scout(res, about: dict, book: Path):
    """Goal 2 item 9, the find half of "Find on 70%, confirm on the rest": scout the development loans
    (scout.run), write the pre-spec beside the workbook (scout.write, before any held-back loan is tested), and hand
    it to the confirmation as a saved one would be (confirmatory.state reads about["_prespec"]). Returns what the
    confirmation waits for, in words (a pre-spec still to answer, such as its strata), [] when nothing; or a refused
    Outcome when scikit-learn is missing."""
    res.scout, res.scout_waits = None, []
    chosen = about.get("_scout")
    if chosen is None:
        return []
    try:
        sc = scout.run(res, chosen, cutoff=cutoff_of(res, about.get("_use") or {}))
    except scout.ScoutMissing as exc:
        return Outcome(False, book, ["Couldn't run:", str(exc)], problems=[str(exc)])
    res.scout = sc
    if sc.problem:
        return []
    path = scout.write(sc, book)
    if path is None:
        return []
    try:
        about["_prespec"] = {"spec": prespec.load(path), "path": path, "cell": path.name, "scouted": True}
    except prespec.PreSpecError as exc:
        res.scout_waits = [f"{path.name}: {confirmatory._plain(x.removeprefix(f'{path}: '))}. Then press Run again."
                           for x in exc.problems]
        return res.scout_waits
    # OC-51: the pre-spec is on disk and read, so the held-back loans may now be read: the tree's out-of-time check
    try:
        scout.out_of_time(res, sc)
    except Exception as exc:                    # noqa: BLE001 - said on New variables and Record, never a failed Run
        sc.oot = scout.OutOfTime(held_back=sc.holdout, problem=f"it couldn't be worked out ({exc})")
    return res.scout_waits


def cutoff_of(res, use: dict):
    """The cutoff the Run uses (OC-51): the date typed on Control, or for the suggestion the month start nearest 70%
    of the loans, worked out from this extract's dates as Set up showed it. None when there is none to use."""
    got = use.get("cutoff")
    if isinstance(got, date):
        return got
    if got in scout.CUTOFF_SHARES:
        dates, _ = confirmatory.origination_dates(res)
        return scout.suggest_cutoff(dates or [], scout.CUTOFF_SHARES[got])
    return None


def _cutoff_words(ws, table, cols_ws, cat) -> None:
    """The suggested cutoff beside its setting on Control (OC-51, OC-13: shown, never chosen): the month start
    nearest 70% of the loans, and how many loans fall each side of it."""
    r = control.row_of(ws, "cutoff")
    if r is None:
        return
    col = next((str(x[C_NAME - 1].value) for x in table_rows(cols_ws) if x[C_NAME - 1].value
                and _to_code(x[C_MEANS - 1].value, cat) == "origination_date"), None)
    said = "Worked out once a column is marked Origination date on Columns"
    if col and col in table.columns:
        try:
            read = engine._date_reader(table, col, "when each loan was made")
            dates = [d for d in (read(x.get(col)) for x in table.rows) if isinstance(d, date)]
        except engine.NothingToCut:
            dates = []
        got = scout.suggest_cutoff(dates)
        if got is not None:
            before = sum(1 for d in dates if d < got)
            said = f"suggested: {got.isoformat()} ({before:,} loans before, {len(dates) - before:,} after)"
    c = ws.cell(row=r, column=SUGGEST_COL, value=said)
    c.font = Font(name="Calibri", size=10, bold=said.startswith("suggested"), color=INK)
    c.alignment = Alignment(horizontal="left", vertical="center")


def _forget(wb, memory_path) -> list[str]:
    """What the analyst marked Forget? Yes on Columns, dropped from memory now (the redesign, phase 2: Learned is
    on Columns). An older workbook's Learned tab is read the same way as before."""
    if "Learned" in wb.sheetnames:
        return memory.apply_review(wb["Learned"], memory_path)[1]
    names = [str(r[C_NAME - 1].value) for r in table_rows(wb["Columns"])
             if r[C_NAME - 1].value and len(r) >= C_FORGET and str(r[C_FORGET - 1].value or "").strip() == FORGET_YES]
    return memory.forget(names, memory_path)[1] if names else []


def _headline(res, wb) -> dict:
    """What the launcher's last step shows: how many pockets read worse and
    material on charge-offs (the loss share of loans without them), what they
    lost above their share, the tie-outs, and every odd value still unanswered."""
    rates = [m for m in res.measures if m.is_rate]
    m = next((x for x in rates if x.name == "gco_rate"), rates[0] if rates else None)
    worse, pockets, borderline = [], 0, 0
    for g in res.grids if m is not None else ():
        for _, c in g.inner():
            pockets += 1
            s = c.rates[m.name]
            if s.flag == engine.WORSE and s.material is not False and s.dollars and s.dollars > 0:
                worse.append(s.dollars)
                borderline += s.worse_borderline is not None
    open_qs = []
    if "Columns" in wb.sheetnames:
        name = None
        for r in table_rows(wb["Columns"]):
            name = r[C_NAME - 1].value or name
            key = r[C_QKEY - 1].value if len(r) >= C_QKEY else None
            if isinstance(key, str) and key.count("|") == 2 and not r[C_TREAT - 1].value:
                cell = f"{_col(C_TREAT)}{r[0].row}"
                open_qs.append({"sheet": "Columns", "cell": cell,
                                "says": f"{key.split('|')[0]}: {r[C_ODD - 1].value}, used as recorded. Answer it "
                                        f"on Columns, row {r[0].row} (Treat as), and press Run again if they mean "
                                        f"missing."})
    if not bleed_tabs(res):
        return {**confirmatory.headline(res), "open": open_qs}      # the confirmation's tiles (OC-42)
    return {"measure": m.title if m is not None else None, "gco": m is not None and m.name == "gco_rate",
            "worse": len(worse), "pockets": pockets, "dollars": sum(worse), "tie_outs": res.tie_outs,
            "borderline": borderline, "open": open_qs}


def _edges_outside(wb, raw: dict, cfg, table) -> list[str]:
    """Own band edges that sit outside the column's values make an empty band,
    or one band holding everything (the second walk, defect 2: an edge of
    620,680,740 put every FICO in one band). Each is named by its cell."""
    rows = {}
    for r in table_rows(wb["Columns"]):
        if r[C_NAME - 1].value:
            rows[str(r[C_NAME - 1].value)] = r[0].row
    out = []
    for b in raw["bands"]:
        if "edges" not in b:
            continue
        c = b["field"]
        rule = cfg.missing.get(c)
        vals = [v for v in (engine.classify_number(row.get(c), rule)[0] for row in table.rows) if v is not None]
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        bad = [e for e in b["edges"] if not lo < e <= hi]
        if bad:
            out.append(f'Columns!{_col(C_EDGES)}{rows.get(c, "")}: {c} runs from {engine._fmt(lo)} to '
                       f'{engine._fmt(hi)}, so an edge at {", ".join(engine._fmt(x) for x in bad)} would leave a '
                       f'band empty. Type edges inside that range, with semicolons: 620; 680; 740.')
    return out


PLAIN = {
    "`dimensions:` needs at least one entry": "Nothing is left to cut across: mark at least one column as a "
                                             "category (or term) on the Columns tab, and tick it under Segment by "
                                             "in the launcher.",
    "`bands:` needs at least one entry": "Nothing is left to cut into bands: mark at least one number column as "
                                        "a score, ratio or amount on the Columns tab, and tick it under Cut into "
                                        "bands in the launcher.",
}


def _changed_away(wb, problem: str) -> str:
    """When nothing is left to cut, name the columns that were suggested as
    one and aren't cut now (the second walk, defect 15: the message didn't say
    which change caused it)."""
    kind = {"`dimensions:` needs at least one entry": "dimension",
            "`bands:` needs at least one entry": "band"}.get(problem)
    if not kind:
        return ""
    cat = meanings.catalog()
    out = []
    chosen, cells = control.read_choices(wb[control.SHEET])
    cut = chosen.cut() if chosen else None
    for r in table_rows(wb["Columns"]):
        name, sugg = r[C_NAME - 1].value, r[C_SUGG - 1].value if len(r) >= C_SUGG else None
        if not name or sugg not in cat or cat[sugg].cut != kind:
            continue
        now = _to_code(r[C_MEANS - 1].value, cat)
        if now != sugg:
            out.append(f"{name} (Columns!{_col(C_MEANS)}{r[0].row}, now {cat[now].label if now else 'blank'})")
        elif chosen and chosen.split == name:
            out.append(f"{name} ({cells['split']}: it splits the pockets, so it isn't a "
                       f"{'segment' if kind == 'dimension' else 'band'} of its own)")
        elif cut is not None and name not in cut:
            out.append(f"{name} (not ticked in the launcher, {cells['bands' if kind == 'band' else 'segments']})")
    return f" Changed from what was suggested: {'; '.join(out)}." if out else ""


def _plain(problem: str) -> str:
    """A cube-file problem, in workbook terms: nobody at the desk sees the cube file."""
    if problem in PLAIN:
        return PLAIN[problem]
    cat = meanings.catalog()
    for code, m in cat.items():
        problem = problem.replace(f"that means {code};", f"marked {m.label};")
    return (problem.replace("`columns:` needs exactly one column", "Columns: exactly one column must be")
            .replace("`columns:`", "the Columns tab").replace("`", '"'))


def filter_words(res) -> str:
    """The Grids' filter column as Record and the Run name it: ORIG_YEAR says where its years come from."""
    f = res.config.filter_by
    return f"{f} (the year in {res.config.origination_date})" if f == ch.ORIG_YEAR else str(f)


def filter_counts(res) -> str:
    """Each value the Grids can be filtered to, with its loans: "2022 (1,012 loans), 2023 (998 loans)"."""
    g = res.grids[0] if res.grids else None
    out = []
    for v in res.filter_values:
        n = g.filtered[v].cells[(engine.ALL, engine.ALL)].rows if g is not None and v in g.filtered else None
        out.append(v if n is None else f"{v} ({_n(n, 'loan')})")
    return ", ".join(out)


def _names(res) -> dict[str, str]:
    """Grid band/dimension names back to the extract's own column names."""
    out = {b.name: b.field for b in res.config.bands}
    out.update({d.name: d.field for d in res.config.dimensions})
    if res.config.split:
        sfield = res.config.split[0]
        out.update({f"{d.name} / {sfield}": f"{d.field} / {sfield}" for d in res.config.dimensions})
    return out


def _ran_on(res, src: Path) -> str:
    """The first line of a Run's Log entry and the launcher's. It no longer counts the tie-outs: a Run whose grids
    don't add up stops and writes nothing, so "N tie-out checks agree" could only ever read fine (tenet T2). Record's
    Tie-out checks row keeps the count, once."""
    return f"Ran on {res.rows:,} loans from {src.name}."


def _top_lines(res) -> list[str]:
    names = _names(res)
    out = []
    if not bleed_tabs(res):
        return out                              # no pocket was built to be worst (OC-42)
    for m in res.measures:
        if not m.is_rate:
            continue
        best = None
        for g in res.grids:
            for (b, d), c in g.inner():
                s = c.rates[m.name]
                # the dollars of the comparison that decides the flag (the firm, 26 Sep 2026)
                if s.dollars and s.dollars > 0 and s.flag == engine.WORSE and s.material is not False:
                    if best is None or s.dollars > best[0]:
                        best = (s.dollars, live.flagged(f"{names[g.band]} {b} / {names[g.dimension]} {d}",
                                                        s.worse_borderline))
        tested = any(c.rates[m.name].reading_topline not in (engine.THIN, engine.FEW, None)
                     for g in res.grids for _, c in g.inner())
        if best:
            out.append(f"Worst for {m.title}: {best[1]}.")
        elif not tested:
            least = res.config.benchmark.min_events if res.config.benchmark else 0
            out.append(f"No pocket had enough losses to test {m.title} (fewest losses: {least:,}).")
        else:
            out.append(f"Nothing is worse for {m.title} at these settings.")
    return out


# --------------------------------------------------------------------------
# Results


def _log(wb, lines: list[str], redraw: bool = True) -> None:
    """The Run's lines at the top of the Log (Record's Every Run, kept on the hidden _log), in the open workbook
    (the Run saves it once). A refusal draws Every Run again at once; a Run writes Record afterwards."""
    record.add(wb, lines)
    if redraw:
        record.refresh_runs(wb)
    _order(wb)


def _write_results(wb, book: Path, res, memory_path, src: Path, forgotten: set[str] | None = None,
                   ncols: int | None = None) -> None:
    for t in RESULT_TABS[:-1] + ("Materiality", "Learned"):
        if t in wb.sheetnames:
            del wb[t]
    for t in results.OLD_TABS + OLD_RESULT_TABS + results.HIDDEN + (results.CHART,):   # the redesign replaced
        if t in wb.sheetnames:
            del wb[t]
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if bleed_tabs(res):
        _write_bleed(wb, res, stamp)
    scout_tab.write(wb, res, stamp)             # Goal 2 item 9: only when this Run scouted (Scouting)
    confirm_tab.write(wb, res, stamp)           # 4b and 4e: only when testing from a pre-spec (New variables)
    live.ensure(wb, res)                        # the names Control's materiality panel reads, with no tab of its own
    _write_rest(wb, book, res, memory_path, src, forgotten, ncols, stamp)


def bleed_tabs(res) -> bool:
    """Whether this Run writes the bleed analysis's tabs. A test of a new variable builds none (OC-42), and the
    ones an earlier bleed Run left are taken off at the top of _write_results with every other result tab."""
    return getattr(res, "bleed", True)


def _write_bleed(wb, res, stamp: str) -> None:
    """The bleed analysis's tabs, the redesign's phase 3: Pockets, Paid cost kept, Grids (with how common each
    group is, fix 3.12) and Split (results.py)."""
    results.write(wb, res, stamp)


#: on Columns, beside a column the last Run gave one band per value (the firm, 30 Sep 2026). A suggestion only: what
#: the column is stays as answered and remembered
FEW_VALUES_WHY = " Few values ({} to {}): Category may read better."
_FEW_VALUES_RE = re.compile(r" ?Few values \([^)]*\): Category may read better\.")


def _few_values_words(cols, res) -> None:
    """"Why we think so" on Columns: the suggestion for each column this Run gave one band per value, and none
    beside a column it didn't (an earlier Run's taken off, so typed edges clear it at the next Run)."""
    each = {b.field: getattr(res, "value_bands", {}).get(b.name) for b in res.config.bands}
    for row in table_rows(cols):
        name = row[C_NAME - 1].value
        if not name:
            continue
        cell = row[C_WHY - 1]
        why = _FEW_VALUES_RE.sub("", str(cell.value or ""))
        vals = each.get(str(name))
        if vals:
            why = why.rstrip()
            why = why + "." if why and why[-1] not in ".!?" else why
            why += FEW_VALUES_WHY.format(engine.value_text(vals[0]), engine.value_text(vals[-1]))
        if why != str(cell.value or ""):
            cell.value = why.strip()


def _write_rest(wb, book: Path, res, memory_path, src: Path, forgotten, ncols, stamp: str) -> None:
    if control.SHEET in wb.sheetnames:
        _last_run_used(wb, res)
        control.fold_launcher_rows(wb[control.SHEET])     # the rows this kind of run asks, and only those
        if getattr(res, "suggest_all", None):
            _suggestions(wb[control.SHEET], *res.suggest_all, when="from this extract at the last Run")
    if "Columns" in wb.sheetnames:
        cols = wb["Columns"]
        # a Run needs C3 = Yes, so the new columns have been checked and the ask is spent (the final check, F9)
        head, tail = (re.escape(x) for x in NEW_COLS_NOTE.split("{}"))
        cols["D3"] = re.sub(head + ".*?" + tail + r"\s*", "", str(cols["D3"].value or ""), flags=re.S).strip() \
            or CONFIRM_NOTE
        if forgotten:
            # a Forget holds until a person confirms the column again (the third walk, defect 9:
            # the next Run re-learned it from Columns, which still said Yes)
            cols[CONFIRM_CELL] = None
            cols["D3"] = (f"{CONFIRM_NOTE} Forgotten: {', '.join(sorted(forgotten))}. Check what "
                          f"{'it is' if len(forgotten) == 1 else 'they are'}, then set C3 to Yes again.")
            cols["D3"].font = Font(name="Calibri", bold=True, size=10, color=WARN_TEXT)
        # what is remembered now, after this Run: a column it confirmed can be forgotten at the next one
        mem = memory.load(memory_path)["columns"]
        from . import house
        for row in table_rows(cols):
            name = row[C_NAME - 1].value
            if name and name not in (forgotten or ()) and name in mem:
                row[C_REMEMBERED - 1].value = _remembered_words(mem[name])
                if row[C_FORGET - 1].value in (None, ""):
                    row[C_FORGET - 1].value = "No"
                    house.needs_run(row[C_FORGET - 1])
                    row[C_FORGET - 1].alignment = Alignment(horizontal="center", vertical="center")
        for row in table_rows(cols):
            if row[C_NAME - 1].value and row[C_NAME - 1].value in (forgotten or ()):
                row[C_LOOK - 1].value = "Forgotten at the last Run: confirm what it is."
                row[C_REMEMBERED - 1].value = "No"
                row[C_FORGET - 1].value = None
                why = str(row[C_WHY - 1].value or "")
                if why.startswith("Remembered"):
                    row[C_WHY - 1].value = "Forgotten at the last Run; it was remembered before."
        _few_values_words(cols, res)
    _write_found(wb, res, stamp)
    if "Start here" in wb.sheetnames:
        # the second walk, defect 9, and the third walk, defect 15: the counts went stale after a run
        at = wb.sheetnames.index("Start here")
        del wb["Start here"]
        _start_here(wb.create_sheet("Start here", at), wb, src, res.rows,
                    ncols if ncols is not None else len(res.config.columns or {}))
    _order(wb)


#: _found's "top" rows: the word, band, segment, loans, the _pockets row, then 1 when Worse? and Material? both read
#: Yes now, and the running count of those, which Start here's rows MATCH (as Pockets' rows MATCH _list's)
TOP_BAND, TOP_SEG, TOP_LOANS, TOP_PROW, TOP_SHOWN, TOP_CUM = range(2, 8)


def _write_found(wb, res, stamp: str) -> None:
    """What the last Run found, kept on a hidden sheet so Start here can be written again at Set up: the measure
    its tiles count, the pockets, and every pocket losing more than its share on that measure against either
    comparison, largest dollars first as of this Run, each with the _pockets row its live verdicts are read from."""
    if FOUND in wb.sheetnames:
        del wb[FOUND]
    ws = wb.create_sheet(FOUND)
    ws.sheet_state = "hidden"
    ws.append(["stamp", stamp])
    if not bleed_tabs(res):
        return confirm_tab.write_found(ws, res)     # no pocket was built: what the confirmation found (OC-42)
    rates = [m for m in res.measures if m.is_rate]
    m = next((x for x in rates if x.name == "gco_rate"), rates[0] if rates else None)
    if m is None or res.config.benchmark is None:
        return
    lv = live.ensure(wb, res)
    names = _names(res)
    plain = {"gco_rate": "charge-offs", "outcome_loans": "bad loans", "outcome_dollars": "bad dollars"}
    ws.append(["measure", m.name])
    ws.append(["measure_title", plain.get(m.name, m.title)])
    ws.append(["pockets", sum(1 for g in res.grids for _ in g.inner())])
    if "ranr_rate" in {x.name for x in rates}:
        ws.append(["profit", "ranr_rate"])
    top = []
    for g in res.grids:
        for (b, d), c in g.inner():
            s = c.rates[m.name]
            other = s.excess_band if not s.by_band else s.excess_rest
            deciding = s.dollars is not None and s.dollars > 0
            if not (deciding or (other is not None and other > 0)):
                continue
            prow = lv.row(g, b, d, m.name)
            if prow is None:
                continue
            # a segment that is only a number reads with its column's name: "ASSET_CLASS 4", as the spec does
            seg = f"{names[g.dimension]} {d}" if str(d).replace(".", "").isdigit() else str(d)
            top.append(((0 if deciding else 1, -(s.dollars if deciding else other)), f"{names[g.band]} {b}", seg,
                        s.units, prow))
    P = lambda c, row: f"'{live.POCKETS}'!${live.col(c)}${row}"          # noqa: E731
    for _, band, seg, loans, prow in sorted(top, key=lambda t: t[0]):
        r = ws.max_row + 1
        ws.append(["top", band, seg, loans, prow])
        ws.cell(row=r, column=TOP_SHOWN, value=f'=IF(AND({P(live.P_WORSE, prow)}="{live.YES}",'
                                               f'{P(live.P_MAT, prow)}="{live.YES}"),1,0)')
        first = ws.cell(row=r - 1, column=1).value != "top"
        ws.cell(row=r, column=TOP_CUM, value=f"={_col(TOP_SHOWN)}{r}" if first else
                f"={_col(TOP_CUM)}{r - 1}+{_col(TOP_SHOWN)}{r}")


def _last_run_used(wb, res) -> None:
    """Beside every Control answer, what the last Run used, with a suggested
    option's worked-out number (the fifth walk: a suggestion showed no number
    anywhere on Control). The answer cells as the Run read them go on _used,
    for Status to compare with."""
    ws = wb[control.SHEET]
    col = control.LAST_COL
    said = _used_words(res)
    if control.USED_SHEET in wb.sheetnames:
        del wb[control.USED_SHEET]
    held = wb.create_sheet(control.USED_SHEET)
    held.sheet_state = "hidden"
    held.append(["key", "answer as the cells held it", "in words"])
    settings = {s.key: s for s in control.load_settings()}
    for row in ws.iter_rows(min_row=control.FIRST_ROW):
        key = row[control.KEY_COL - 1].value
        s = settings.get(key)
        if s is None or s.in_launcher:
            continue
        own, choose = row[control.OWN_COL - 1].value, row[control.CHOOSE_COL - 1].value
        answer = own if own not in (None, "", "n/a") else choose
        picked = control._matching(s, choose) if answer is choose and choose not in (None, "") else []
        held.append([key, answer, picked[0].label if picked else answer])
        words = said.get(key)
        c = ws.cell(row=row[0].row, column=col, value=words)
        c.value = words                     # cleared when not asked: ws.cell(value=None) leaves the old one
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.font = Font(name="Calibri", size=10, color=SLATE)
    # and each choice made in the launcher, as the Run read it, so Next changing one shows as waiting (A)
    for r in control.launcher_rows_of(ws):
        own = ws.cell(row=r, column=control.OWN_COL).value
        choose = ws.cell(row=r, column=control.CHOOSE_COL).value
        answer = own if own not in (None, "", "n/a") else choose
        held.append([ws.cell(row=r, column=control.KEY_COL).value, answer, answer])


def _used_words(res) -> dict[str, str]:
    """What the last Run used for each Control setting, in words, as Control's Last Run used and Record's Settings
    say it: a suggested value marked worked out, or the usual value when nothing could be worked out. A setting the
    run didn't ask (the profit line, or a bleed's lines on a test of a new variable) used nothing: it has none."""
    by_q = dict(control.describe(_settings_of(res.config)))
    sug = getattr(res, "suggested", None) or {}
    used = getattr(res, "control_used", None) or {}
    fb = getattr(res, "suggest_fallback", set())
    out = {}
    for s in control.load_settings():
        if s.in_launcher:
            continue
        key = s.key
        words = by_q.get(s.question)
        if words is None and key in ("band_count", "band_cut") and key in used:
            words = dict(control.describe({key: used[key]})).get(s.question)
        if key == "revenue_line" and profit_line(res):
            words = profit_words(res)
        elif key in fb:
            words = f"{words} (the usual value: nothing in this book to work it out from)"
        elif key in sug:
            words = f"{words} (worked out from this book)"
        if key == "cutoff":
            sc = getattr(res, "scout", None)
            got = getattr(sc, "cutoff", None)
            words = None if got is None else got.isoformat() + (" (worked out from this book)"
                                                                 if used.get("cutoff") in scout.CUTOFF_SHARES
                                                                 else "")
        if not control.asked(s, used):
            words = None                    # not asked for this run, so nothing was used
        if words is not None:
            out[key] = words
    return out


def _unit(m) -> str:
    if m.mode == "flagwt" and m.per == engine.EACH_LOAN:
        return "loans"
    if m.mode == "flagwt":
        return f"{m.per} dollars"
    return f"{m.numerator()} dollars"


def _amount(v: float, m) -> str:
    """A line in its unit. Loans to one decimal: a line of 2.3 shown as 2 put a
    pocket whose excess also showed as 2 either side of it (second walk, defect 7)."""
    return f"{v:,.1f} loans" if _unit(m) == "loans" else f"{v:,.0f} {_unit(m)}"


def _plain_warning(w: str) -> str:
    """An engine warning in workbook terms: nobody at the desk sees the cube file."""
    return (w.replace("(real, or missing) in `questions:`", "Real or Missing under Treat as on Columns")
            .replace("`", '"'))


P_FMT = '[<0.0001]"under 0.01%";[<0.01]0.00%;0.0%'
#: a difference in percentage points of booked dollars, signed: "+0.35 pts", "-1.20 pts" (NEXT-GOAL 3.2)
PTS_FMT = '+0.00" pts";-0.00" pts";0.00" pts"'


def _shown(v: float | None, m) -> float | None:
    """A comparison as the workbook prints it: a multiple, or for profit the
    difference in points (the engine keeps it in the rate's units: 0.0035 is
    +0.35 points)."""
    if v is None:
        return None
    return round(v * 100, 9) + 0.0 if m.in_points else v        # + 0.0: no "-0.00 pts" from a rounding hair


def _gap_fmt(m) -> str:
    return PTS_FMT if m.in_points else '0.00"x"'


def which_test(s, peers: bool = True) -> str:
    """The test behind a pocket's p-value, in a few words (docs/statistics.md):
    the z test at or above fewest loans, the exact test below it, and for a
    dollar rate the shuffle count made literal (B2): how many of the shuffles
    made a gap at least as big against the comparison that decides the flag,
    before the allowance for many tests (NEXT-GOAL 3.6)."""
    if s.test == engine.EXACT_TEST:
        return "exact test"
    if s.test == engine.Z_TEST:
        return "z test"
    if s.test == engine.SHUFFLE_TEST and s.shuffles:
        hits = s.hits_band if peers and not s.alone else s.hits_book
        return f"shuffled: {hits:,} of {s.shuffles:,}" if hits is not None else f"{s.shuffles:,} shuffles"
    return ""


WARN_TEXT = "960019"

#: Together, the two sides of Paid, cost, kept read at once (NEXT-GOAL 3.4; five verdicts since the redesign)
TOGETHER, together_of = results.TOGETHER, results.together_of


def profit_line(res):
    """The profit line the run used (engine.profit_line), with the materiality
    line in GCO dollars for the dollar option."""
    b = res.config.benchmark
    return engine.profit_line(b, res.materiality_line.get("gco_rate")) if b is not None else None


def _has_profit(res) -> bool:
    """Whether the run has a profit rate. A test of a new variable may run without RANR (Goal 2 item 2), and then
    no tab says anything about profit."""
    return any(m.name in cfgmod.PROFIT for m in res.measures)


def _has_dollar_rates(res) -> bool:
    """Whether the run has any rate in dollars, so a shuffle test to describe; not without the dollar columns."""
    return any(m.is_rate and m.name != "outcome_loans" for m in res.measures)


def per_pocket(res) -> bool:
    """Profit is read by each pocket's own test (the suggested option, OC-31)."""
    line = profit_line(res)
    return bool(line and line.kind == "test")


def profit_words(res) -> str:
    """When profit counts as more or less, in a few words."""
    line = profit_line(res)
    if line is None:
        return ""
    if line.kind == "points":
        return f"{line.value * 100:.2f} points either way"
    if line.kind == "dollars":
        return f"a gap of {line.value:,.0f} dollars either way (the materiality line)"
    return "each pocket's own test"


DECIDES_BAND = ("The rest of its band decides each pocket's flag, its dollars and whether it is material. A pocket "
                "alone in its band is compared with the rest of the book.")
DECIDES_BOOK = ("The rest of the book decides each pocket's flag, its dollars and whether it is material: every "
                "other loan in the book, for the gap and the dollars alike.")


def decides(res) -> str:
    """Check's one line on which comparison decides (the firm, 26 Sep 2026: one
    comparison decides the verdict, the dollars and materiality): a formula that
    follows "judged against" on Control (OC-40)."""
    return f"=IF(judged_band,{live.q(DECIDES_BAND)},{live.q(DECIDES_BOOK)})"


def reads(res) -> str:
    """How a profit or contribution reading is worded: the gap itself, never a
    verdict word (the firm, 26 Sep 2026: "yes I prefer it to be literal"), with
    this run's own pockets as the examples, never made-up numbers."""
    b = res.config.benchmark
    against = "its band" if b is not None and b.compare_to == "peers" else "the book"
    line = profit_line(res)
    names = _names(res)
    # the examples: the pocket with the most dollars at stake of each kind, so a blank or marked-missing
    # pocket isn't what the reader meets first
    best: dict[bool, tuple] = {}
    for g in res.grids:
        for (bl, dl), c in g.inner():
            s = c.rates.get("ranr_rate")
            if s is None or s.dollars is None or s.flag not in (engine.WORSE, engine.BETTER, engine.IN_LINE,
                                                                  engine.UNSURE_WORSE, engine.UNSURE_BETTER):
                continue
            kind = s.flag in (engine.WORSE, engine.BETTER)
            if kind not in best or abs(s.dollars) > best[kind][0]:
                where = f"{names[g.band]} {bl} / {names[g.dimension]} {dl}"
                best[kind] = (abs(s.dollars), f"{where}: \"{engine.said(s, line)}\"")
    past, inside = (best[k][1] if k in best else None for k in (True, False))
    out = (f"As the gap: how many points of booked dollars a pocket is short of or ahead of {against}, and the "
           f"dollars that comes to" + (f". In this run, {past}." if past else "."))
    if line is None or line.kind == "test":
        out += " A gap its own test doesn't call significant gives the gap and says not significant"
    else:
        out += (" A gap inside the line gives the line and the gap; one past it that isn't significant ends "
                "\"(not significant)\"")
    return out + (f". In this run, {inside}." if inside else ".")


def luck_gap(res, mname: str, floor: float) -> float | None:
    """The smallest gap a pocket of typical size can call significant: for each
    pocket at or above fewest loans, the multiple its test would call
    significant at the Control confidence (A3 for the share of loans), and the
    median of those. The catch rate is left out on purpose (the fourth walk,
    defect 4: at 80% caught it was the gap a pocket can find, 1.25x, not the
    gap that just clears the bar, about 1.17x)."""
    b = res.config.benchmark
    ln = res.loans_needed.get(mname)
    if b is None or ln is None:
        return None
    gaps = []
    for g in res.grids:
        for _, c in g.inner():
            s = c.rates[mname]
            if s.units >= floor:
                x = stats.smallest_gap_for(ln, s.units, b.confidence, 0.5)
                if x:
                    gaps.append(x)
    return round(statistics.median(gaps), 2) if gaps else None


def _partner(res) -> tuple[str, float] | None:
    """The band column the split column moves with most, and the correlation."""
    field_ = res.config.split[0]
    got = {f: r for f, r in res.split_moves_with.items() if f != field_}
    return max(got.items(), key=lambda t: abs(t[1])) if got else None


def _holds_partner(res, g) -> bool | None:
    p = _partner(res)
    if p is None:
        return None
    names = _names(res)
    return p[0] in (names[g.band], names[g.dimension])


def _three_way_note(res, g) -> tuple[str, float]:
    """One short cell per split pocket on Pockets, and the order: grids that hold the
    split's partner fixed first (the fifth walk: the same 35-word sentence on
    every row was read past)."""
    p = _partner(res)
    held = _holds_partner(res, g)
    if p is None or held is None:
        return "", 0.0
    return ("yes" if held else f"no: may be mostly {p[0]}, so not red"), (0.0 if held else 1.0)


def _holds_fixed(res, g) -> tuple[str, float]:
    """What a grid does and doesn't hold fixed, in words, and a sort key: the
    split column's strongest tie to a band column this grid doesn't hold fixed.
    The third walk, defect 2: in a loan-size grid the high-debt half is also the
    low-score half, and a book with no debt effect read 1.7x. The number is shown
    and the reader decides (ruling OC-27); nothing is hidden or dropped."""
    names = _names(res)
    field_ = res.config.split[0]
    held = {names[g.band], names[g.dimension]}
    loose = {f: r for f, r in res.split_moves_with.items() if f not in held and f != field_}
    fixed = {f: r for f, r in res.split_moves_with.items() if f in held and f != field_}
    words = []
    if fixed:
        f, r = max(fixed.items(), key=lambda t: abs(t[1]))
        words.append(f"This grid holds {f} fixed ({field_}'s correlation with it: {r:+.2f}).")
    if loose:
        f, r = max(loose.items(), key=lambda t: abs(t[1]))
        words.append(f"It doesn't hold {f} fixed ({field_}'s correlation with it: {r:+.2f}).")
        return " ".join(words), abs(r)
    return " ".join(words) or "", 0.0


def _same_size(m, pooled: dict, conf: float) -> str:
    """The Split tab's "Same size in every pocket?" for one measure. Cochran's Q
    (A8) runs on the yes/no outcome only, so anything else says it wasn't tested
    and why; "yes/no outcome only" there read as an answer (the final check, F9)."""
    steady = pooled.get("steady_p")
    if steady is not None:
        # A8: a Q that isn't significant is "no evidence the pockets disagree", never "proof they agree". Its
        # p-value against the bar on Control, so it follows a change of confidence (OC-40)
        return f'=IF({live.sig(live.num(steady))},"no: bigger in some pockets","no sign they differ")'
    if not engine.yes_no(m):
        return "not tested: dollar rate"
    return "not tested: too few pockets" if pooled.get("pockets", 0) < 2 else "not tested: couldn't be worked out"


def _p(v) -> str:
    if v is None:
        return "(not available)"
    return "under 0.01%" if v < 0.0001 else f"{v:.2%}" if v < 0.01 else f"{v:.1%}"


def _total_words(m, res=None) -> str:
    """What a materiality share is a share of (the third walk, defect 16).
    Profit's line is drawn from GCO, so its share is of the book's GCO."""
    if m.name in cfgmod.PROFIT and res is not None:
        gco = next((x for x in res.measures if x.name == "gco_rate"), None)
        if gco is not None:
            return f"total {gco.value}"
    if m.mode == "flagwt" and m.per == engine.EACH_LOAN:
        return "loans with the outcome"
    if m.mode == "flagwt":
        return f"{m.per} on loans with the outcome"
    return f"total {m.value}"


def _amount_f(ref: str, m) -> str:
    """_amount as a formula over the cell `ref`: a line in its unit."""
    if _unit(m) == "loans":
        return f'TEXT({ref},"#,##0.0")&" loans"'
    return f'TEXT({ref},"#,##0")&{live.q(" " + _unit(m))}'


def _typical_gap(res, m) -> float | None:
    """The median, over every pocket, of the smallest gap it could show (a
    difference, for profit): what a pocket of typical size can see."""
    got = [c.rates[m.name].smallest_gap for g in res.grids for _, c in g.inner()
           if c.rates[m.name].smallest_gap is not None]
    return statistics.median(got) if got else None


def _record(wb, res, src: Path, record_name: str = "") -> None:
    """Record (the redesign, section 10): Check's lines and the Log on one tab, the Log's newest entry included
    (so a Run writes it after the Log has this Run's lines)."""
    record.write(wb, _record_rows(wb, res, src, record_name))


def measure_name(m) -> str:
    """A measure as the result tabs name it (results.PLAIN), or its own title when they don't."""
    return results.PLAIN.get(m.name, m.title)


def _record_rows(wb, res, src: Path, record_name: str = "") -> dict[str, list]:
    """Every line Check carried, each in the Record section it belongs in (record.section_of), and Settings: one
    row per Control setting the run asked."""
    record_ = record_name
    rows = [("Extract", src.name), ("Loans run", f"{res.rows:,}"),
            ("Record of this run", f"{record_}, beside this workbook: every setting the run used, kept for the "
                                   f"file. It is replaced by the next Run."),
            ("Tie-out checks", f"{res.tie_outs:,}: every grid adds up to the book")]
    ran = what_was_run(getattr(res, "control_used", None) or {})
    if ran:
        rows.insert(2, ("What was run", ran))
    # each measure by the name the result tabs give it: the walk of 27 Sep 2026 read "Outcome, share of loans" here
    # beside "Bad loans" on Pockets, Grids and Split, for the same measure
    title = measure_name
    lv = live.ensure(wb, res)
    # a test of a new variable may run without the dollar columns: then no profit and no dollar rate is on Record
    profit, dollar_rates = _has_profit(res), _has_dollar_rates(res)
    if res.config.benchmark is not None:
        # the lines in use now, beside what the last Run used (OC-40), are Record's Settings section
        for m in res.measures:
            if not m.is_rate:
                continue
            n = sum(1 for g in res.grids for _ in g.inner())
            worse = live.count_formula(m.name, [(live.P_FLAG, f'"{engine.WORSE}"')])
            material = live.count_formula(m.name, [(live.P_FLAG, f'"{engine.WORSE}"'), (live.P_MATERIAL, '"yes"')])
            rows.append((f"Worse now: {title(m)}", f'={worse}&" of {n:,} pockets on the grids read worse; "&'
                                                   f'{material}&" of them are material."'))
        for m in res.measures:
            if not m.is_rate or engine.yes_no(m) or not res.config.benchmark.shuffles:
                continue            # only a shuffled p-value can be borderline (docs/statistics.md B2a)
            n = sum(1 for g in res.grids for _ in g.inner())
            said = live.count_formula(m.name, [(live.P_BTXT, '"?*"')])
            worse = live.count_formula(m.name, [(live.P_WBTXT, '"?*"')])
            rows.append((f"Borderline now: {title(m)}", f'={said}&" of {n:,} pockets on the grids have a borderline '
                                                        f'verdict ("&{worse}&" on Worse?)."'))
    rows += _origination_rows(res) + _column_rows(res)
    for m in res.measures:
        lo = res.left_out.get(m.name)
        if lo:
            rows.append((f"Left out of {title(m)}", "; ".join(f"{k:,} x {col} {why}" for (col, why), k in lo.items())))
    names = _names(res)
    for name, e in res.band_edges.items():
        rows.append((f"Band edges used: {names.get(name, name)}",
                     f"{'; '.join(engine._fmt(x) for x in e)}  ({_n(len(e) + 1, 'band')})"))
    b = res.config.benchmark
    for mname, ln in res.loans_needed.items():
        m = next(x for x in res.measures if x.name == mname)
        if m.in_points:
            # profit is a gap in points: what a pocket of typical size can see, not a multiple (NEXT-GOAL 3.2)
            typ = _typical_gap(res, m)
            rows.append((f"Smallest gap a typical pocket could show: {title(m)}",
                         f"{typ * 100:.2f} points either way (the median over the pockets; caught "
                         f"{b.power:.0%} of the time at {b.confidence:.0%} sure)" if typ
                         else "can't be sized: no pocket has the loans to show one"))
            continue
        rows.append((f"Loans needed for a {ln.gap:g}x gap: {title(m)}",
                     f"about {ln.loans:,}" if ln.loans else "can't be sized (the book's rate is zero)"
                     if not ln.rate else "more than this book has: not even half of it could show that gap"))
    for m in res.measures:
        if m.is_rate and b is not None:
            # the line in use now (OC-40)
            v = lv.line_cell[m.name]
            said = (f'"a shortfall of "&{_amount_f(v, m)}&": the same dollar line as GCO (Control\'s materiality '
                    f'answer)"' if m.name in cfgmod.PROFIT else _amount_f(v, m))
            rows.append((f"Materiality line: {title(m)}",
                         f'=IF({v}="","no line: the dollar line on Control is a GCO amount",{said})'))
    if res.config.split:
        sf, how = res.config.split
        named = f"{sf} (the year in {res.config.origination_date})" if sf == ch.ORIG_YEAR else sf
        rows.append(("Split", f"{named}, " + ("each pocket halved at its own median" if how == "own_median"
                                          else "each pocket split by each value, and each value set against the "
                                               "rest of its pocket") + f". {sf} isn't cut on its own while it "
                                                                        f"splits. Split pockets: "
                                                                        f"{sum(1 for g in res.three_way for _ in g.inner()):,}."))
        for f, r in sorted(res.split_moves_with.items(), key=lambda t: -abs(t[1])):
            if f != sf:
                rows.append((f"How closely {sf} moves with {f}", f"correlation {r:+.2f}"))
    if res.config.filter_by and res.filter_values:
        rows.append(("Grids filter", f"{filter_words(res)}: {filter_counts(res)}. Grids' Only loans where builds "
                                     f"each grid again on one value's loans, set against the whole book. Picked "
                                     f"in the launcher (Filter by), apart from the split."))
    sug = getattr(res, "suggested", None) or {}
    if sug:
        rate = res.total.rates["outcome_loans"].rate
        words = []
        fb = getattr(res, "suggest_fallback", set())
        if "min_loans" in sug and "min_loans" not in fb:
            words.append(f"fewest loans {sug['min_loans']:,} (enough to expect 5 with the outcome at the book's "
                         f"rate of {rate:.2%})" if rate else f"fewest loans {sug['min_loans']:,}")
        # a value that fell back is named as Control names it and never called worked out (the seventh
        # walk, defect 6: "1.25x (the outcome gap ...)" beside "the usual value was used")
        lines_ = [k for k in ("worse_at", "better_at") if k in sug and k not in fb]
        for k in lines_:
            words.append(f"{'worse' if k == 'worse_at' else 'better'} at {sug[k]:.2f}x")
        if lines_:
            words[-1] += (" (the smallest outcome gap a pocket of typical size can call significant)" if bleed_tabs(res)
                          else " (the smallest odds ratio a group of typical size can call significant against the "
                               "reference group, on the loans the groups were found on)")
        if fb:
            named = {"min_loans": "fewest loans", "worse_at": "how much worse", "better_at": "how much better"}
            words.append("nothing could be worked out (no rate, or no pocket big enough), so the usual value "
                         "was used for " + " and ".join(
                             f"{named.get(k, k)} ({sug[k]:.2f}x)" if isinstance(sug.get(k), float)
                             else f"{named.get(k, k)} ({sug[k]:,})" for k in sorted(fb) if k in sug))
        rows.append(("Worked out from this book" if not fb else "Suggested values", "; ".join(words)))
    # how many pockets were tested at all, so a reviewer reading Check alone sees an empty run for what it is
    # (the seventh walk, defect 6)
    if "outcome_loans" in res.total.rates and b is not None:
        cells = [c for g in res.grids for _, c in g.inner()]
        tested = sum(1 for c in cells if c.rates["outcome_loans"].reading_topline not in (engine.THIN, engine.FEW))
        rows.append(("Pockets tested", f"{tested:,} of {len(cells):,}" if tested else
                     f"none of {len(cells):,}: every pocket has fewer loans with the outcome than fewest losses "
                     f"({b.min_events:,})"))
    if b is not None:
        # which test gave each p-value (docs/statistics.md; OC-36 asks Check to name the split's)
        rows.append(("Tests", f"Outcome, share of loans: the z test, pooled, for a pocket of {b.min_units:,} loans "
                              f"or more, and the exact test (Fisher's) below that."
                              + (f" Every dollar rate: the loans are shuffled {b.shuffles:,} times, within the band "
                                 f"for the rest of its band, and its p-value is how often a shuffle made a gap as "
                                 f"big." if dollar_rates else "")
                              + (" Profit and contribution are compared as a gap in points, never a multiple."
                                 if profit else "")
                              + (" A split by a category: each value against the rest of its pocket, as the "
                                 "halves are compared; and whether the values differ at all, every value at once, "
                                 "by the K-group Mantel-Haenszel test (general association, on one fewer degrees "
                                 "of freedom than there are values), bad loans only."
                                 if res.config.split and res.config.split[1] == "each_value" else "")
                              + f" The split's odds: "
                              f"Cochran-Mantel-Haenszel, which asks whether an odds ratio this far from 1 could "
                              f"come from shuffling loans within their pockets. It has no continuity correction: "
                              f"nothing is taken off the gap between actual and expected before it is squared."))
        # the words the tabs use, defined once (docs/statistics.md, conventions; NEXT-GOAL 3.1)
        rows.append(("p-value", live.text("The chance of a gap at least this big if there were no real difference, "
                                          "after the allowance for many tests. Below ",
                                          ('TEXT(significance_bar,"0%")',), " is significant, at ",
                                          ('TEXT(confidence,"0%")',), " sure. Two-sided: a gap either way counts.")))
        if dollar_rates:
            rows.append(("Borderline", live.text(
                "A verdict is borderline when the p-value that decides it came from shuffling and sits within "
                f"{stats.BORDERLINE_SE:g} of its own standard errors of the ", ('TEXT(significance_bar,"0%")',),
                " bar, either side, so another run of the shuffles could read it the other way. The standard error "
                "is the square root of p (1 - p) / shuffles, times what the allowance for many tests multiplied "
                "the p-value by. The tabs add \"borderline (p 0.048)\" to the verdict; its colour, order and "
                "counts stay the verdict's. The z test and the exact test give the same p-value on every run, so "
                "they are never borderline.")))
        rows.append(("Standard error", live.text("How far a rate worked out from this many loans typically lands "
                                                 "from its true value. A gap of ",
                                                 ('TEXT(NORMSINV(1-(1-confidence)/2),"0.00")',),
                                                 " standard errors is the ", ('TEXT(confidence,"0%")',), " line.")))
    if b is not None and b.many_tests != "none":
        rows.append(("The allowance for many tests covers",
                     "each grid and measure on its own, one comparison at a time"))
    if "contribution_rate" in res.total.rates:
        # the definition the tabs rest on (OC-35): the losses inside RANR are GCO
        rows.append(("Contribution before losses", "RANR + GCO, per booked dollar. This assumes RANR has gross "
                                                   "charge-offs taken out. If RANR nets recoveries instead, "
                                                   "contribution is overstated by the recoveries."))
    if b is not None:
        rows.append(("Decides each pocket", decides(res)))
    if b is not None and profit:
        said = (f"='{live.LIVE_SHEET}'!$E${live.L_PKIND}&IF(profit_kind=\"test\",\": only a gap that is "
                f"significant at \"&TEXT(confidence,\"0%\"),\"\")")
        if b.revenue_line is None:
            said += '&" (none was chosen, so each pocket\'s own test)"'
        rows.append(("Profit counts as more or less", said))
        rows.append(("How profit reads", reads(res) + " The examples are as of the last Run."))
    # what the data left out, beside what each measure left out (the engine's warnings are about the extract)
    rows += [("Warning", _plain_warning(w), record.LEFT) for w in res.warnings]
    if not bleed_tabs(res):
        rows = _without_bleed(rows, None)
    rows += checks.rows(res)                    # fixes 3.15 to 3.18: pre-spec, pocket budget, families, products
    out: dict[str, list] = {}
    before = None
    for k, v, *where in rows:
        sec = where[0] if where else record.section_of(str(k), before)
        out.setdefault(sec, []).append((k, v))
        before = sec
    out[record.SETTINGS] = _settings_rows(wb, res)
    return out


def _settings_rows(wb, res) -> list[tuple]:
    """Record's Settings: every Control setting this run asked, as (the question, in use now, what the last Run
    used, 1 while the two differ). A Changes-now setting reads its words on _live, now and at the Run; a Needs-a-Run
    one reads Control's answer now and the answer the Run used, and differs while Control's Status says it waits
    for a Run. A workbook with no Control (a test's) has the Run's words only."""
    used = getattr(res, "control_used", None) or {}
    words = _used_words(res)
    settings = [s for s in control.load_settings() if not s.in_launcher]
    live_row = {"worse_at": live.L_WORSE, "better_at": live.L_BETTER, "confidence": live.L_CONF,
                "materiality": live.L_MKIND, "compare_to": live.L_BAND, "revenue_line": live.L_PKIND}
    lv = live.ensure(wb, res)
    if control.SHEET not in wb.sheetnames:
        return [(s.question, words.get(s.key), words.get(s.key), None) for s in settings
                if words.get(s.key) is not None]
    ws, out = wb[control.SHEET], []
    L = f"'{live.LIVE_SHEET}'"
    on_control = live._control_rows(wb, res)
    for s in settings:
        r = control.row_of(ws, s.key)
        if r is None or not control.asked(s, used):
            continue
        if s.key in live_row and s.key in on_control:
            x = live_row[s.key]
            out.append((s.question, f"={L}!$E${x}", lv.last.get(x), f"=IF({L}!$E${x}<>{L}!$F${x},1,0)"))
            continue
        C, D, K = (f"{control.SHEET}!${_col(c)}${r}" for c in (control.CHOOSE_COL, control.OWN_COL, control.KEY_COL))
        now = (f'=IF(AND({D}<>"",{D}<>"n/a"),{D},IFERROR(INDEX({control.OPTIONS_SHEET}!$G:$G,MATCH({K}&"|"&{C},'
               f'{control.OPTIONS_SHEET}!$A:$A,0)),{C}&""))')
        status = f"{control.SHEET}!${_col(control.STATUS_COL)}${r}"
        out.append((s.question, now, words.get(s.key), f'=IF({status}="{control.WAITING}",1,0)'))
    return out


#: Check's one line on a test of a new variable, in place of the tie-outs (OC-42)
NO_BLEED = ("Bleed tabs", "None: testing a new variable runs only the confirmatory test. Any left by an earlier "
                          "Run were taken off.")
#: Check's lines about the bleed analysis's pockets, grids and tests, left off when it wasn't built
BLEED_ROWS = ("Worse now: ", "Loans needed for ", "Smallest gap ", "Materiality line: ", "Split", "Grids filter",
              "How closely ",
              "Pockets tested", "Tests", "The allowance for many tests", "Decides each pocket")


def _without_bleed(rows: list, live_end: int | None) -> list:
    """Check's rows for a test of a new variable (OC-42): the tie-outs row becomes NO_BLEED, and the bleed's own
    lines after the live block (whose rows are counted by position, so it is kept as it is) are left off."""
    at = next(i for i, r in enumerate(rows) if r[0] == "Tie-out checks")
    rows = rows[:at] + [NO_BLEED] + rows[at + 1:]
    keep = live_end if live_end is not None else at + 1
    return rows[:keep] + [r for r in rows[keep:] if not str(r[0]).startswith(BLEED_ROWS)]


def _origination_rows(res) -> list[tuple[str, str]]:
    """One line on Check when a column is marked Origination date: the range of
    dates among the loans run, and how many have no readable date. A fact only:
    nothing is left out for its dates, so a wrong extract shows here."""
    d = res.dates
    if d is None:
        return []
    if d.problem:
        return [("Origination dates", f"Couldn't be read: {_plain_warning(d.problem)}")]
    none = f"{d.unreadable:,} without a readable date"
    if d.first is None:
        return [("Origination dates", f"none readable in {d.column} ({_n(d.loans, 'loan')}; {none})")]
    return [("Origination dates", f"{d.first.isoformat()} to {d.last.isoformat()} ({_n(d.loans, 'loan')}; {none})")]


def _dates_head(res) -> str:
    """What the new columns did, as comments at the top of what ran."""
    out = ""
    for m in res.derived:
        blank = sum(m.blank.values())
        out += f"# new column {m.name} = {m.text()}: made on {m.made:,} loans, blank on {blank:,}\n"
    return out


def _column_rows(res) -> list[tuple[str, str]]:
    """Check's lines for the new columns (fix 3.9) and what each amount is said
    to be over and to measure (fixes 3.10, 3.11)."""
    rows = []
    for m in res.derived:
        blank = sum(m.blank.values())
        why = "; ".join(f"{k:,} where {w}" for w, k in m.blank.items())
        rows.append((f"New column: {m.name}", f"{m.text()} on each loan. Made on {m.made:,}"
                     + (f"; blank on {blank:,} ({why})." if blank else "; blank on none.")))
    cfg = res.config
    for c in list(dict.fromkeys(list(cfg.periods) + list(cfg.definitions))):
        said = [cfgmod.PERIOD_WORDS[cfg.periods[c]]] if c in cfg.periods else []
        said += [cfg.definitions[c]] if c in cfg.definitions else []
        rows.append((f"What {c} is", "; ".join(said)))
    return rows


def _settings_of(cfg) -> dict:
    b = cfg.benchmark
    if b is None:
        return {}
    mat = {"none": "none", "share": f"{b.materiality[1] * 100:g}% of losses"}.get(
        b.materiality[0], f"${b.materiality[1]:,.0f} of GCO")
    return {"min_loans": b.min_units, "min_events": b.min_events, "worse_at": b.worse_at, "better_at": b.better_at,
            "confidence": b.confidence, "power": b.power, "compare_to": b.compare_to, "many_tests": b.many_tests,
            "materiality": mat,
            # not asked for a test of a new variable (the redesign, phase 2), so Check doesn't echo it then
            **({"revenue_line": b.revenue_line} if b.revenue_line is not None else {})}
