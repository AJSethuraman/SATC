"""The workbook: the answers for a run go in, and the results come out.

Ruling OC-22 (25 Sep 2026): nobody types a command. The launcher's two
buttons call the two functions here:

    set_up(extract)   writes or refreshes the tabs a person fills in: Start
                      here, Control, Columns (with the odd values and what is
                      remembered), Look. Answers already given are kept, and so
                      are the results of the last run.
    run(book)         reads the answers, runs the engine, and writes the results
                      into the same workbook: Where it bleeds, Losses vs revenue,
                      Grids, Split, Check, Log, and Start here's findings. It
                      loads the workbook once and saves it once.

A problem is never a traceback: it is a sentence naming the tab and cell, shown
in the launcher and on the Log tab. A run that can't write its results changes
nothing else (no memory, no record), so a refused run leaves no trace.
"""

from __future__ import annotations

import hashlib
import math
import re
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import config as cfgmod
from . import control, engine, meanings, memory, perm, profile, stats
from . import checks, confirmatory, prevalence          # fixes 3.12 and 3.15 to 3.18
from . import live                                      # OC-40: the judging settings, live in the workbook
from . import confirm_tab                               # 4b and 4e: the confirmatory test's tab
from . import choices as ch                             # the redesign: what the launcher chose
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
RESULT_TABS = ("Confirmatory test", "Where it bleeds", "Losses vs revenue", "Grids", "Split", "Prevalence", "Three-way",
               "Check", "Log")
LOG_FIRST = 4            # the newest line on the Log tab
LOG_NOTE = ("Every Run and every refusal, newest first. Each entry is what that Run used: a line changed on "
            "Control afterwards shows on the result tabs, not here.")
HELPERS = ("_options", "_meanings", "_about")
ABOUT = "_about"
FOUND = "_found"          # what the last Run found, for Start here's tiles and top five (kept through Set up)
CHART_DATA = "_chart"     # the Losses vs revenue charts' own numbers, hidden
CONFIRM_CELL = "C3"      # "Checked every column?"
# Set up's note on Columns!D3 for columns the Yes in C3 doesn't cover yet; a Run takes it off again
NEW_COLS_NOTE = "New since the last check: {}. Check them, then set C3 to Yes again."
CONFIRM_NOTE = "Run won't start until this is Yes."
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


@dataclass
class Read:
    """An extract as the launcher's Set up step reads it, before any workbook is written."""
    extract: Path
    book: Path
    loans: int
    columns: list[Column]
    chosen: "ch.Choices | None" = None      # what the workbook beside it already shows, if there is one
    problem: str | None = None


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
        if kind == "cat":
            n = len({str(r.get(c)) for r in made_table.rows if r.get(c) not in (None, "")})
            what = f"Category · {n:,} values" if code == "category" else f"{what} · {n:,} values"
        out.append(Column(c, what, kind))
    chosen = None
    if _earlier(target).exists():
        try:
            chosen = control.read_choices(load_workbook(_earlier(target))[control.SHEET])[0]
        except Exception:
            chosen = None
    return Read(extract, target, len(table.rows), out, chosen)


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
    wb = load_workbook(book)
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
    made, reports = engine.derive_columns(table, defs, rules)
    return made, reports, notes


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
            wb = load_workbook(book)
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
                                        made_notes, new_cols, gone_cols, qs)
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
    look.write_look(wb, table, shown + [m.name for m in made if m.name not in shown], known=facts_of,
                    edge_rows=edge_rows, split=chosen_now.split if chosen_now is not None else None,
                    bands=[c for c in shown if c in banded and (cut is None or c in cut)],
                    treat_rows=_treat_rows(ws))

    about = wb.create_sheet(ABOUT)
    about["A1"], about["B1"] = "extract", str(extract.resolve())
    about["A2"], about["B2"] = "sha256", hashlib.sha256(extract.read_bytes()).hexdigest()
    about["A3"], about["B3"] = "set up", (today or date.today()).isoformat()
    about["A4"], about["B4"] = "extract name", extract.name
    about.sheet_state = "hidden"
    settings = control.load_settings()
    given = {s.key: control.answer_of(s.key, *kept["control"].get(s.key, (None, None))) for s in settings}
    unanswered = sum(1 for s in settings if s.judgment and not s.in_launcher and control.asked(s, given)
                     and not any(v not in (None, "n/a") for v in kept["control"].get(s.key, (None, None))))
    _start_here(start, wb, extract, len(table.rows), len(extract_cols))
    _order(wb)
    if not _writable(book):
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Set up again."])
    worked = _suggest_at_set_up(wb, book, as_read, memory_path)
    _suggestions(wb[control.SHEET], *worked, when="from this extract")
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
    nlook = len({rv.column for rv in looks if rv.kind != "cannot run"} | set(new_cols) | edge_noted)
    if nlook:
        lines.append(f"{_n(nlook, 'column')} to look at first, on the Columns tab.")
    left = []
    if unanswered:
        left.append("Control")
    if ws[CONFIRM_CELL].value != "Yes" or odd_open:
        left.append("Columns")
    # the second walk, defect 15: this line said the same thing with nothing left to fill
    joined = ", ".join(left[:-1]) + (" and " if len(left) > 1 else "") + left[-1] if left else ""
    lines.append(f"Next: fill in the shaded cells on {joined}, save, close, and press Run." if left
                 else "Everything is answered. Press Run.")
    return Outcome(True, book, lines, summary={"suggested": worked[0], "fallback": worked[1]})


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


def _columns_tab(ws, wb, table, cols, sugg, facts_of, looks, kept, mem, cat, made, made_notes, new_cols, gone_cols,
                 qs) -> tuple[int, set[str]]:
    """Columns, as the redesign draws it (section 3): the check at C3, the method note, then one row per extract
    column (a second odd value in a column gets a row of its own under it, with no name). Returns how many odd
    values are still unanswered, and the columns whose remembered edges were filled in."""
    from . import house
    last = C_DEFINE
    widths = {1: 2, C_NAME: 22, C_SAMPLES: 26, C_MEANS: 20, C_WHY: 40, C_BLANK: 7, C_ODD: 20, C_TREAT: 11,
              C_EDGES: 16, C_REMEMBERED: 13, C_FORGET: 9, C_LOOK: 60, C_IS: 12, C_SHOW: 15, C_PERIOD: 11,
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
    ws["D3"] = " ".join([CONFIRM_NOTE] + notes)
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
        tag = "Remembered: " if sg.source == "remembered" else ""
        f = facts_of.get(c) or meanings.facts(table, c)
        blank = (f.rows - f.nonblank) / f.rows if f.rows else 0
        ws.cell(row=r, column=C_NAME, value=c).font = Font(name="Calibri", bold=True, size=10)
        samples = classified[c].samples[:3] if c in classified else []
        if any(m.name == c for m in made):
            samples = [f"{float(v):.4g}" for v in samples]      # a ratio to four figures, not seventeen
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
        for k, q in enumerate(questions.get(c, []) or [None]):
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
        r += max(1, len(questions.get(c, [])))
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


def _start_here(ws, wb, extract, rows: int, ncols: int, found=None) -> None:
    """Start here, as the redesign draws it (section 1): where things stand, as formulas over Control and
    Columns; the pending banner; what the last Run found (from _found, kept through Set up) with its five
    largest pockets; and the tabs in their three groups."""
    from . import house
    for col, w in zip("ABCDEFGHI", (2, 22, 16, 16, 16, 16, 16, 16, 22)):
        ws.column_dimensions[col].width = w
    stamp = _found_value(wb, "stamp")
    sub = f"{Path(extract).name} · {rows:,} loans · {ncols} columns" + (
        f" · last Run {stamp}" if stamp else "")
    house.title_band(ws, NAME, sub, 2, 9)
    r = house.method_note(ws, 3, 2, 9, [
        ("Where things stand", "What is left before Run, counted live from Control and Columns as you fill them "
                               "in."),
        ("What the last Run found", "Pockets that read worse and are material, and the five largest. Worse? and "
                                    "Material? follow Control; the order and the rest are as of the last Run."),
        ("The tabs", "Red tabs you fill in; black tabs hold results; grey tabs are the record."),
    ])
    _heading(ws, r, "Where things stand")
    cols = wb["Columns"] if "Columns" in wb.sheetnames else None
    end = next((c.row for c in cols[_col(C_QKEY)] if c.value == TABLE_END), COL_FIRST + 1) - 1 if cols \
        else COL_FIRST
    names = f"Columns!$B${COL_FIRST}:$B${end}"
    keys, treat = f"Columns!${_col(C_QKEY)}${COL_FIRST}:${_col(C_QKEY)}${end}", \
        f"Columns!${_col(C_TREAT)}${COL_FIRST}:${_col(C_TREAT)}${end}"
    tiles = [("Answers still needed", "=IFERROR(SUM(answers_needed),0)", "Control"),
             ("Columns to confirm", f'=IF(Columns!{CONFIRM_CELL.replace("C", "$C$")}="Yes",0,COUNTA({names}))',
              "Columns"),
             ("Odd values to answer", f'=COUNTIFS({keys},"?*",{treat},"")', "Columns · Treat as"),
             ("Changes waiting for a Run", f'=IFERROR(COUNTIF(Status,"{house.WAITING}"),0)',
              "Control · Needs a Run")]
    for i, (label, f, where) in enumerate(tiles):
        first = 2 + 2 * i
        house.tile(ws, r + 1, first, first + 1, label, f, top=house.STONE)
        foot = ws.cell(row=r + 3, column=first, value=where)
        foot.font = Font(name="Calibri", size=9, color=SLATE)
        foot.alignment = Alignment(indent=1)
    value_row = r + 2
    from openpyxl.formatting.rule import FormulaRule
    for i in range(4):
        # a count above nought is crimson, and its tile's rule turns red
        c, d = _col(2 + 2 * i), _col(3 + 2 * i)
        ws.conditional_formatting.add(f"{c}{value_row}", FormulaRule(
            formula=[f"${c}${value_row}>0"], font=Font(name="Arial", bold=True, size=12, color=house.CRIMSON)))
        ws.conditional_formatting.add(f"{c}{r + 1}:{d}{r + 1}", FormulaRule(
            formula=[f"${c}${value_row}>0"], border=Border(top=Side(style="thick", color=house.KEY_RED))))
    # the pending banner: shown only while an answer under Needs a Run differs from what the last Run used
    b = r + 5
    ws.merge_cells(start_row=b, start_column=2, end_row=b, end_column=9)
    words = "&".join(f"INDEX(waiting_words,{k})" for k in range(1, len(control.RUN_KEYS) + 1))
    n = f'COUNTIF(Status,"{house.WAITING}")'
    ws.cell(row=b, column=2, value=(
        f'=IFERROR(IF({n}=0,"","↻ "&{n}&IF({n}=1," change is"," changes are")&" waiting for a Run. "&'
        f'LEFT({words},LEN({words})-2)&". The result tabs still show the last Run. Save, close, and press Run in '
        f'the launcher."),"")'))
    ws.cell(row=b, column=2).font = Font(name="Calibri", size=10, bold=True, color=house.CRIMSON)
    ws.cell(row=b, column=2).alignment = Alignment(vertical="center", indent=1, wrap_text=True)
    ws.row_dimensions[b].height = 30
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


def _found_block(ws, wb, r: int) -> int:
    """What the last Run found: four tiles and the five largest pockets, worse and material. The words are the
    Run's; Worse?, Material?, the dollars and the counts are formulas over _pockets, so they follow Control."""
    from . import house
    _heading(ws, r, "What the last Run found")
    if FOUND not in wb.sheetnames or not _found_value(wb, "measure"):
        c = ws.cell(row=r + 1, column=2, value="Nothing yet: answer Control and Columns, then press Run in the "
                                               "launcher.")
        c.font = Font(name="Calibri", size=10, color=SLATE)
        return r + 3
    m, title = _found_value(wb, "measure"), _found_value(wb, "measure_title")
    crit = f'pk_kind,"grids",pk_measure,"{m}",pk_flag,"{engine.WORSE}",pk_material,"yes"'
    dollar = m != "outcome_loans"
    tiles = [(f"Pockets worse and material, {title}",
              f'=IFERROR(COUNTIFS({crit})&" of {_found_value(wb, "pockets"):,}","")'),
             (f"{'Dollars' if dollar else 'Bad loans'} above their share, in those",
              f'=IFERROR(SUMIFS(pk_dollars,{crit}),"")')]
    profit = _found_value(wb, "profit")
    if profit:
        pc = f'pk_kind,"grids",pk_measure,"{profit}",pk_flag,"{engine.WORSE}",pk_material,"yes"'
        tiles.append(("Pockets keeping less, worse and material",
                      f'=IFERROR(COUNTIFS({pc})&" short $"&TEXT(SUMIFS(pk_dollars,{pc}),"#,##0"),"")'))
    else:
        tiles.append(("Last Run", _found_value(wb, "stamp")))
    tiles.append(("Tie-out checks", _found_value(wb, "tie_outs")))
    for i, (label, f) in enumerate(tiles):
        house.tile(ws, r + 1, 2 + 2 * i, 3 + 2 * i, label, f)
    ws.cell(row=r + 2, column=4).number_format = '"$"#,##0' if dollar else "#,##0.0"
    if _found_value(wb, "tie_outs") and str(_found_value(wb, "tie_outs")).split(" of ")[0] == \
            str(_found_value(wb, "tie_outs")).split(" of ")[-1].split(" ")[0]:
        ws.cell(row=r + 2, column=8).font = Font(name="Arial", bold=True, size=12, color=house.POSITIVE)
    t = r + 4
    heads = ["Largest, worse and material", "Segment", "Loans", "× its comparison",
             f"{'Dollars' if dollar else 'Bad loans'} above share", "Worse?", "Material?"]
    house.header(ws, t, 2, heads + [None], centre_from=2)
    top = [row for row in wb[FOUND].iter_rows(min_row=1, values_only=True) if row[0] == "top"]
    for i, (_, band, seg, loans, prow) in enumerate(top[:5], start=1):
        rr = t + i
        P = lambda c: f"'{live.POCKETS}'!${live.col(c)}${prow}"         # noqa: E731
        vals = [band, seg, loans, f"=IF({P(live.P_GAP)}=\"\",\"\",{P(live.P_GAP)})",
                f"=IF({P(live.P_DOLLARS)}=\"\",\"\",{P(live.P_DOLLARS)})",
                f'=IF({P(live.P_FLAG)}="{engine.WORSE}","Yes",IF(LEFT({P(live.P_FLAG)},5)="worse","Not sure","No"))',
                f'=IF({P(live.P_MATERIAL)}="yes","Yes","No")']
        for j, v in enumerate(vals):
            c = ws.cell(row=rr, column=2 + j, value=v)
            c.font = Font(name="Calibri", size=10, color=house.INK_TEXT)
            c.alignment = Alignment(horizontal="left" if j < 2 else "center", vertical="center")
            c.border = Border(bottom=Side(style="thin", color=house.ROW_RULE))
        ws.cell(row=rr, column=4).number_format = "#,##0"
        ws.cell(row=rr, column=5).number_format = '0.00"×"'
        ws.cell(row=rr, column=6).number_format = '"$"#,##0' if dollar else "#,##0.0"
        ws.row_dimensions[rr].height = 18
    if not top:
        ws.cell(row=t + 1, column=2, value="No pocket read worse and material at the last Run's lines.").font = \
            Font(name="Calibri", size=10, color=SLATE)
    from openpyxl.formatting.rule import FormulaRule
    last = t + max(1, len(top[:5]))
    ws.conditional_formatting.add(f"G{t + 1}:G{last}", FormulaRule(
        formula=[f'G{t + 1}="Yes"'], font=Font(bold=True, color=house.CRIMSON),
        fill=PatternFill("solid", fgColor=house.ALERT_FG, bgColor=house.ALERT_FG)))
    ws.conditional_formatting.add(f"G{t + 1}:G{last}", FormulaRule(
        formula=[f'G{t + 1}="Not sure"'], fill=PatternFill("solid", fgColor=house.CANVAS, bgColor=house.CANVAS)))
    ws.conditional_formatting.add(f"H{t + 1}:H{last}", FormulaRule(
        formula=[f'H{t + 1}="Yes"'], font=Font(bold=True),
        fill=PatternFill("solid", fgColor=house.MIST, bgColor=house.MIST)))
    link = ws.cell(row=last + 1, column=2, value="Every pocket, every measure: the Where it bleeds tab.")
    link.hyperlink = "#'Where it bleeds'!A1"
    link.font = Font(name="Calibri", size=10, color=house.KEY_RED, underline="single")
    return last + 3


#: the tabs in their three groups, each with what it holds
TAB_GROUPS = [
    ("You answer", "KEY_RED", [("Control", "the professional calls"), ("Columns", "meanings, odd values, memory"),
                               ("Look", "each number column's shape")]),
    ("Results", "INK", [("Where it bleeds", "every pocket, largest first"), ("Losses vs revenue", "paid against cost"),
                        ("Grids", "every rate, band by segment"), ("Split", "each pocket halved"),
                        ("Three-way", "the halves, tested"), ("Prevalence", "how common each value is"),
                        ("Confirmatory test", "a saved shortlist, confirmed")]),
    ("Record", "STONE", [("Check", "what ran, and the tie-outs"), ("Log", "every Run, newest first")]),
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
    wb = wb if wb is not None else load_workbook(book)
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
    columns, edges, skip, show, split = {}, {}, set(), {}, []
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
        split, skip = _cuts_chosen(chosen, choice_cells, columns, row_of_col, cat, problems)
    derived = _read_made(wb, columns, made_rows, problems)
    held_to = _what_is_run(wb, book, use, columns, cat, problems)    # the pre-spec named on Control, if any
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
        "benchmark": {"min_units": _num_or(use["min_loans"], 30, int), "min_events": int(use["min_events"]),
                      "worse_at": _num_or(use["worse_at"], 1.25, float),
                      "better_at": _num_or(use["better_at"], 0.8, float),
                      "confidence": float(use["confidence"]), "power": float(use["power"]),
                      "compare_to": use["compare_to"], "many_tests": use["many_tests"],
                      "materiality": use["materiality"], "revenue_line": use.get("revenue_line")},
        "questions": questions or [],
    }
    if use.get(RUN_KIND) == NEW_VARIABLE:
        raw["run_kind"] = NEW_VARIABLE              # its dollar columns are optional (cfgmod.RUN_KINDS)
    if split:
        name, code = split[0]
        raw["split"] = {"field": name, "how": "each_value" if cat[code].cut == "dimension" else "own_median"}
    if derived:
        raw["derived"] = derived                    # fix 3.9
    about = dict(about)
    about["_widths"] = {c: w for c, w in widths.items() if c not in skip}
    about["_typed_edges"] = typed
    about["_edge_cells"] = edge_cells
    about["_suggest"] = {k for k in ("min_loans", "worse_at", "better_at") if use.get(k) in ("calc", "luck")}
    about["_use"] = dict(use)
    about["_prespec"] = held_to
    return raw, [], about


def _cuts_chosen(chosen, cells: dict, columns: dict, row_of_col: dict, cat, problems: list[str]):
    """The split, and the columns left uncut, from what the launcher chose. A
    column is cut when the launcher ticked it (or, with nothing narrowed, when
    its meaning cuts it), as a band or a segment by its meaning on Columns."""
    split: list[tuple[str, str]] = []
    for key in ("bands", "segments"):
        for name in getattr(chosen, key) or ():
            if name not in columns:
                problems.append(f"{cells[key]}: {name} isn't a column in this extract. Choose again in the launcher.")
    cut = chosen.cut()
    skip = {c for c in columns if cut is not None and c not in cut}
    if chosen.split:
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
    if chosen.run_kind == ch.NEW_VARIABLE and chosen.outcome:
        code = columns.get(chosen.outcome)
        code = code if code is None or isinstance(code, str) else code["means"]
        if code != "outcome":
            where = (f"Columns!{_col(C_MEANS)}{row_of_col[chosen.outcome]}" if chosen.outcome in row_of_col
                     else "Columns")
            problems.append(f"{cells['outcome']}: the launcher tests against {chosen.outcome}, and {where} doesn't "
                            f"mark it {cat['outcome'].label}. Mark it so, or choose the outcome again in the "
                            f"launcher.")
    return split, skip


def _what_is_run(wb, book: Path, use: dict, columns: dict, cat, problems: list[str]) -> dict | None:
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
        # say what it does (the firm: "don't note what it does not include just note what it does")
        problems.append(f'{control.SHEET}!C{control.row_of(ws, STEP)}: PocketBook confirms a saved shortlist of '
                        f'new variables. Pick the shortlist in the launcher (Choose tests, Or confirm a saved '
                        f'shortlist), or run {labels[BLEED]}.')
        return None
    if kind == NEW_VARIABLE and step == FROM_PRESPEC and text is None:
        problems.append(f'{cell}: "{labels[FROM_PRESPEC]}" needs the pre-spec file named here.')
        return None
    held_to = confirmatory.read(wb, book, problems)          # fix 3.15
    if held_to and held_to["spec"].column not in columns:
        problems.append(f"{cell}: the pre-spec tests {held_to['spec'].column}, and no column on Columns has that "
                        f"name. Make it under Add a column on Columns and press Set up again, or fix the pre-spec.")
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


def _suggest_at_set_up(wb, book: Path, table, memory_path) -> tuple[dict[str, float], set[str]]:
    """The suggested Control answers, before anyone has answered anything (the
    firm, 26 Sep 2026: "configure what you can, and then do the workbook config
    items so that there are suggestions to be made"). The pockets are cut as
    the launcher chose, at the default edges, and the first pass is the one Run
    makes: the workbook with the suggested options picked and any other blank
    call given a stand-in, read by read_book, run without the shuffle test.
    The stand-ins go into the open workbook and every one is put back before
    this returns (found 26 Sep 2026: a saved copy cost two saves and two loads
    of the whole workbook). Nothing here stays in the workbook but the values."""
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
            elif key == RUN_KIND:
                put(r[control.CHOOSE_COL - 1], next(o.label for o in labels[key].options if o.value == BLEED))
            elif key == control.PRESPEC_KEY:
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
        return _suggest_values(engine.run(first, table), set(SUGGEST_KEYS))
    except Exception:
        # a book the first pass can't cut yet (no outcome marked, say): the Run works them out instead
        return {}, set()
    finally:
        for cell, v in reversed(changed):
            cell.value = v


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
        c = ws.cell(row=r[0].row, column=SUGGEST_COL,
                    value=_suggestion_words(key, v, key in fallback, when) if v is not None
                    else "Worked out when you press Run")
        c.font = Font(name="Calibri", size=10, bold=v is not None and key not in fallback,
                      color=INK if v is not None else SLATE)
        c.alignment = Alignment(horizontal="left", vertical="center")


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
        wb = load_workbook(book)
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
    if not src.exists():
        return Outcome(False, book, [f"Couldn't find the extract {src.name}. Put it beside the workbook, or pick "
                                     f"it in the window."])
    if about.get("sha256") and hashlib.sha256(src.read_bytes()).hexdigest() != about["sha256"]:
        notes.append(f"{src.name} has changed since Set up. If columns were added or renamed, press Set up first.")
    table = read_table(src)
    far = _band_widths(raw, about.get("_widths") or {}, cfg, table, about.get("_edge_cells"))
    if about.get("_widths") and not far:
        cfg = cfgmod.parse(raw)
    far += _edges_outside(wb, raw, cfg, table)
    if far:
        return _refused(wb, book, ["Couldn't run. Fix these, save, close, and press Run again:"] + far,
                        Outcome(False, book, ["Couldn't run yet. Fix these in the workbook, save, close, and press "
                                              "Run again:"] + [f"  - {p}" for p in far], problems=list(far)))
    suggested: dict[str, float] = {}
    try:
        if about.get("_suggest"):
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
    about["_wb"] = wb
    checks.attach(book, about, res)             # fixes 3.12, 3.15: the pre-spec's state and the edges on Columns
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
    look.refresh(wb, res.table or table, res.config.split and res.config.split[0],
                 [b.field for b in res.config.bands])
    summary = _headline(res, wb)
    _log(wb, [f"Ran on {res.rows:,} loans from {src.name}; {res.tie_outs:,} tie-out checks agree." + _ran_words(res)]
         + confirmatory.log_lines(res)          # fix 3.15: held to a pre-spec, and whether it touched the holdout
         + [f"Warning: {_plain_warning(w)}" for w in res.warnings])
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
    head += confirmatory.what_ran(res)
    if isinstance(raw.get("benchmark"), dict) and cfg.benchmark is not None:
        raw["benchmark"].setdefault("shuffles", cfg.benchmark.shuffles)
    audit.write_text(head + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    lines = notes + [f"Ran on {res.rows:,} loans from {src.name}; {res.tie_outs:,} tie-out checks agree."
                     + _ran_words(res)]
    lines += _top_lines(res)
    lines += confirmatory.launcher_lines(res)
    # the same rows the tab shades blue (its flag), and pockets counted once (the seventh walk, defect 7:
    # "58 pockets" was 58 rows from 23 pockets)
    blue = [(gi, key) for gi, g in enumerate(res.grids) for key, c in g.inner() for m in res.measures
            if m.is_rate and c.rates[m.name].material and c.rates[m.name].flag in (engine.THIN, engine.FEW)]
    small = len(set(blue))
    if small:
        rows_said = "" if len(blue) == small else f" ({len(blue)} rows: a pocket has a row for each measure)"
        lines.append(f"{_n(small, 'pocket')} {'is' if small == 1 else 'are'} material but too small to test: "
                     f"shaded blue on Where it bleeds{rows_said}, to look at by hand.")
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
    if cfg.split:
        sf, how = cfg.split
        lines.append(f"Split by {sf}: " + ("each pocket halved at its own median. See the Split and Three-way tabs."
                                           if how == "own_median" else "one layer per value. See the Three-way tab.")
                     + f" {sf} isn't cut on its own while it splits.")
    if dropped:
        lines.append(f"Forgot {', '.join(sorted(dropped))}, as marked on Columns. Check "
                     f"{'it' if len(dropped) == 1 else 'them'} and set C3 to Yes before the next Run.")
    tested = getattr(getattr(res, "prespec", None), "test", None)
    lines.append(f"Open {book.name}: start with "
                 + ("Confirmatory test." if tested is not None and tested.problem is None else "Where it bleeds."))
    return Outcome(True, book, lines, summary=summary)


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
    worse, pockets = [], 0
    for g in res.grids if m is not None else ():
        for _, c in g.inner():
            pockets += 1
            s = c.rates[m.name]
            if s.flag == engine.WORSE and s.material is not False and s.dollars and s.dollars > 0:
                worse.append(s.dollars)
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
    return {"measure": m.title if m is not None else None, "gco": m is not None and m.name == "gco_rate",
            "worse": len(worse), "pockets": pockets, "dollars": sum(worse), "tie_outs": res.tie_outs,
            "open": open_qs}


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


def _names(res) -> dict[str, str]:
    """Grid band/dimension names back to the extract's own column names."""
    out = {b.name: b.field for b in res.config.bands}
    out.update({d.name: d.field for d in res.config.dimensions})
    if res.config.split:
        sfield = res.config.split[0]
        out.update({f"{d.name} / {sfield}": f"{d.field} / {sfield}" for d in res.config.dimensions})
    return out


def _top_lines(res) -> list[str]:
    names = _names(res)
    out = []
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
                        best = (s.dollars, f"{names[g.band]} {b} / {names[g.dimension]} {d}")
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


def _log(wb, lines: list[str]) -> None:
    """The Run's lines at the top of the Log tab, in the open workbook (the Run saves it once)."""
    ws = wb["Log"] if "Log" in wb.sheetnames else wb.create_sheet("Log")
    if ws["A1"].value != "Log":
        # a heading like every other tab, and the newest run first under it (second walk, defect 16)
        if ws.max_row > 1 or ws["A1"].value:
            ws.insert_rows(1, amount=LOG_FIRST - 1)
        _title(ws, "Log", LOG_NOTE, "A:B")
    # a record of what each Run used: it doesn't follow a line changed on Control afterwards (OC-40)
    ws["A2"] = LOG_NOTE
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.insert_rows(LOG_FIRST, amount=len(lines) + 1)
    for i, line in enumerate(lines):
        ws.cell(row=LOG_FIRST + i, column=1, value=stamp if i == 0 else None).alignment = Alignment(vertical="top")
        ws.cell(row=LOG_FIRST + i, column=2, value=line).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 17
    ws.column_dimensions["B"].width = 100
    _fit(ws, landscape=False)
    _order(wb)


def _write_results(wb, book: Path, res, memory_path, src: Path, forgotten: set[str] | None = None,
                   ncols: int | None = None) -> None:
    for t in RESULT_TABS[:-1] + ("Materiality", "Learned"):
        if t in wb.sheetnames:
            del wb[t]
    _bleeds(wb.create_sheet("Where it bleeds"), res)
    have = {m.name for m in res.measures}
    if res.config.benchmark is None or {"gco_rate", "ranr_rate", "contribution_rate"} <= have:
        # a test of a new variable run without GCO and RANR has nothing to put on it, so there is no tab
        _losses_vs_revenue(wb.create_sheet("Losses vs revenue"), res)
    _grids(wb.create_sheet("Grids"), res)
    if res.config.split:
        _split_tab(wb.create_sheet("Split"), res)
        note = (lambda g: _three_way_note(res, g)) if res.config.split[1] == "own_median" else None
        pt = _partner(res)
        sf = res.config.split[0]
        after = (f" {sf} moves with {pt[0]} (correlation {pt[1]:+.2f}). Rows whose grid doesn't hold {pt[0]} fixed "
                 f"(the last column says no) come after the rest, and aren't shaded red: part of their gap may be {pt[0]}."
                 if note and pt else "")
        _bleeds(wb.create_sheet("Three-way"), res, res.three_way, "Three-way",
                f"Pockets split by {sf}, each tested like any other pocket,", note, after)
    prevalence.write(wb, res)                   # fix 3.12: only with a split or a new column
    confirm_tab.write(wb, res)                  # 4b and 4e: only when testing from a pre-spec
    live.ensure(wb, res)                        # the names Control's materiality panel reads, with no tab of its own
    _check(wb.create_sheet("Check"), res, src, f"{book.stem} - what ran.yaml")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if control.SHEET in wb.sheetnames:
        _last_run_used(wb, res)
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
    _write_found(wb, res, stamp)
    if "Start here" in wb.sheetnames:
        # the second walk, defect 9, and the third walk, defect 15: the counts went stale after a run
        at = wb.sheetnames.index("Start here")
        del wb["Start here"]
        _start_here(wb.create_sheet("Start here", at), wb, src, res.rows,
                    ncols if ncols is not None else len(res.config.columns or {}))
    _order(wb)


def _write_found(wb, res, stamp: str) -> None:
    """What the last Run found, kept on a hidden sheet so Start here can be written again at Set up: the measure
    its tiles count, the pockets, the tie-outs, and the five largest pockets worse and material with the _pockets
    row each one's live verdicts read."""
    if FOUND in wb.sheetnames:
        del wb[FOUND]
    ws = wb.create_sheet(FOUND)
    ws.sheet_state = "hidden"
    ws.append(["stamp", stamp])
    ws.append(["tie_outs", f"{res.tie_outs:,} of {res.tie_outs:,} agree"])
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
            if s.flag == engine.WORSE and s.material is not False and s.dollars and s.dollars > 0:
                # a segment that is only a number reads with its column's name: "ASSET_CLASS 4", as the spec does
                seg = f"{names[g.dimension]} {d}" if str(d).replace(".", "").isdigit() else str(d)
                top.append((s.dollars, f"{names[g.band]} {b}", seg, s.units, lv.row(g, b, d, m.name)))
    for dollars, band, seg, loans, prow in sorted(top, key=lambda t: -t[0])[:5]:
        if prow is not None:
            ws.append(["top", band, seg, loans, prow])


def _last_run_used(wb, res) -> None:
    """Beside every Control answer, what the last Run used, with a suggested
    option's worked-out number (the fifth walk: a suggestion showed no number
    anywhere on Control). The answer cells as the Run read them go on _used,
    for Status to compare with."""
    ws = wb[control.SHEET]
    col = control.LAST_COL
    by_q = dict(control.describe(_settings_of(res.config)))
    sug = getattr(res, "suggested", None) or {}
    used = getattr(res, "control_used", None) or {}
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
        words = by_q.get(s.question)
        fb = getattr(res, "suggest_fallback", set())
        if words is None and key in ("band_count", "band_cut") and key in used:
            words = dict(control.describe({key: used[key]})).get(s.question)
        if key == "revenue_line" and profit_line(res):
            words = profit_words(res)
        elif key in fb:
            words = f"{words} (the usual value: nothing in this book to work it out from)"
        elif key in sug:
            words = f"{words} (worked out from this book)"
        if key == "revenue_line" and not control.asked(s, used):
            words = None                    # not asked for this run, so nothing was used
        c = ws.cell(row=row[0].row, column=col, value=words)
        c.value = words                     # cleared when not asked: ws.cell(value=None) leaves the old one
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.font = Font(name="Calibri", size=10, color=SLATE)


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


def _in_use(ws, note: str, last_col: str, height: float = 44) -> None:
    """Row 3 of a result tab: the lines its readings are using now, as a formula pointing at Control, and what
    on the tab stays as of the last Run (OC-40)."""
    ws.merge_cells(f"B3:{last_col}3")
    c = ws["B3"]
    c.value = live.text((live.IN_USE,), " " + note if note else "")
    c.alignment = Alignment(wrap_text=True, vertical="top")
    c.font = Font(name="Calibri", size=10, bold=True, color=INK)
    ws.row_dimensions[3].height = height


#: what stays as of the last Run on the pocket lists, said on each (OC-40: no SORT or FILTER in the bank's Excel)
SORTED_NOTE = ("Sorted as of the last Run: changing a line on Control updates the readings, dollars and colours "
               "here, not the order. The smallest gap each pocket could show is as of the last Run.")
JUDGED = ('IF(judged_band,"the rest of its band","the rest of the book")',)


def _bleeds(ws, res, grids=None, title: str = "Where it bleeds", lead: str = "Pockets", note_of=None,
            after: str = "") -> None:
    """Every pocket losing more than its share, largest first. The Three-way tab
    is the same list over the three-way pockets, with what each grid holds fixed
    beside every row, and the grids that hold it fixed first (`note_of` gives the
    words and the order; the fourth walk, defect 1).

    One comparison decides the flag, the dollars, materiality and the order (the
    firm, 26 Sep 2026): the one Control's "judged against" picks. Its dollars come
    first; the other comparison's are beside them for reference. A pocket alone in
    its band has no excess over its band, so it is ranked by the book's.

    Live (OC-40): the flag, both dollar columns, Material, the Test column and the
    headings that name the comparison are formulas over the hidden _pockets sheet,
    so a line changed on Control shows here at once. The rows and their order are
    the last Run's. So that a change of "judged against" finds every pocket it
    could flag, the pockets losing more than their share against the other
    comparison only are listed after the rest, under their own heading."""
    grids = res.grids if grids is None else grids
    lv = live.ensure(ws.parent, res)
    kind = "three-way" if grids is not res.grids else "grids"
    b = res.config.benchmark
    peers = bool(b and b.compare_to == "peers")
    names = _names(res)
    # a test of a new variable may run without RANR, or without any dollar rate (Goal 2 item 2): the note then
    # says nothing about profit or shuffles
    profit, dollar_rates = _has_profit(res), _has_dollar_rates(res)
    _title(ws, title, "", "B:U" if note_of else "B:T")
    ws["B2"] = live.text(
        f"{lead} losing more than their share{' (profit: falling short of it)' if profit else ''}, largest first. "
        f"Each pocket is compared with ", JUDGED, ": that decides the flag, the excess, whether it is material and "
        f"the order. ",
        ('IF(judged_band,"Excess over the book","Excess over its band")',),
        f" is beside it for reference."
        + (" Profit is a gap in points, judged by the profit line on Control." if profit else "")
        + " Red: worse. Amber: worse, not significant. Blue: material, but too few losses to test, so look by hand. "
        "p-value: the chance of a gap this big with no real difference, after the allowance for many tests (see "
        "Check). Test: which test ran" + ("; for a dollar rate, how many shuffles made a gap as big against "
                                          if dollar_rates else "."),
        *((JUDGED, ".") if dollar_rates else ()), after)
    ws.row_dimensions[2].height = 58
    _in_use(ws, SORTED_NOTE, "U" if note_of else "T")
    first_h = ('IF(judged_band,"Excess over its band","Excess over the book")',)
    other_h = ('IF(judged_band,"Excess over the book","Excess over its band")',)
    heads = ["Measure", "Band column", "Band", "Segment column", "Segment", "Loans", "Rate", "Book rate",
             live.text(first_h), live.text(other_h), "Excess is in", "Material", "Vs rest of book", "p-value",
             "Vs rest of band", "p-value", live.text("Flag (vs ", JUDGED, ")"), "Smallest gap it could show"] + (
                [f"Holds {_partner(res)[0]} fixed?" if _partner(res) else "Holds fixed?"] if note_of else []) + [
                "Test"]
    _head(ws, 4, heads)
    ws.row_dimensions[4].height = 44           # "Excess over the book" on two lines
    untested = (engine.THIN, engine.FEW)
    main, others = [], []
    for m in res.measures:
        if not m.is_rate:
            continue
        found, elsewhere = [], []
        for g in grids:
            for (bl, dl), c in g.inner():
                s = c.rates[m.name]
                if s.dollars is not None and s.dollars > 0:
                    found.append((s.dollars, g, bl, dl, s))
                else:
                    # losing more against the comparison that doesn't decide now: a change on Control can flag it
                    other = s.excess if peers else s.excess_band
                    if other is not None and other > 0:
                        elsewhere.append((other, g, bl, dl, s))
        order = (lambda t: (note_of(t[1])[1], -t[0])) if note_of else (lambda t: -t[0])
        main += [(m, *t[1:]) for t in sorted(found, key=order)]
        others += [(m, *t[1:]) for t in sorted(elsewhere, key=order)]

    def write(r, m, g, bl, dl, s):
        tested = s.reading_topline not in untested
        if m.in_points:
            # a shortfall of at least this many points: profit's bleed is the downward gap
            gap = -s.smallest_gap * 100 if s.smallest_gap else None
        else:
            gap = s.smallest_gap if m.higher_is == "worse" else (1 / s.smallest_gap if s.smallest_gap else None)
        at = lambda c: lv.ref(kind, g, bl, dl, m.name, c)           # noqa: E731
        first = f'=IF(judged_band,IF({at(live.P_EX_BAND)}="","",{at(live.P_EX_BAND)}),{at(live.P_EX_BOOK)})'
        other = f'=IF(judged_band,{at(live.P_EX_BOOK)},IF({at(live.P_EX_BAND)}="","",{at(live.P_EX_BAND)}))'
        vals = [m.title, names[g.band], bl, names[g.dimension], dl, s.units, s.rate,
                res.total.rates[m.name].rate, first, other, _unit(m), f"={at(live.P_MATERIAL)}",
                _shown(s.vs_rest, m), s.p_book if tested else None, _shown(s.vs_band, m),
                s.p_band if tested else None, f"={at(live.P_SAID)}", gap]
        if note_of:
            vals.append(note_of(g)[0])
        vals.append(f"={at(live.P_TEST)}")
        for i, v in enumerate(vals, start=2):
            ws.cell(row=r, column=i, value=v)
        ws.cell(row=r, column=len(vals) + 1).alignment = Alignment(horizontal="left", indent=1)   # clear of the gap
        # loans to one decimal, like the line they're held against (the third walk, defect 13)
        ex_fmt = "#,##0.0" if _unit(m) == "loans" else "#,##0"
        for col, fmt in ((8, "0.00%"), (9, "0.00%"), (10, ex_fmt), (11, ex_fmt), (14, _gap_fmt(m)), (15, P_FMT),
                         (16, _gap_fmt(m)), (17, P_FMT)):
            ws.cell(row=r, column=col).number_format = fmt
        ws.cell(row=r, column=19).number_format = ('0.00" pts or less"' if m.in_points else
                                                   '0.00"x or more"' if m.higher_is == "worse"
                                                   else '0.00"x or less"')
        # words that follow a right-aligned number start clear of it ("10.9%worse", "80.4loans" on the render,
        # 26 Sep 2026)
        # (an indent only shows in LibreOffice on a cell aligned left: the render of 26 Sep 2026 still ran
        # them together)
        for col in (12, 18, 20):
            ws.cell(row=r, column=col).alignment = Alignment(horizontal="left", indent=1)

    r = 5
    for t in main:
        write(r, *t)
        r += 1
    if not main:
        ws.cell(row=5, column=2, value="Nothing is losing more than its share at the last Run's settings.")
        r = 6
    if others:
        r += 1
        other_words = "the rest of the book" if peers else "the rest of its band"
        h = ws.cell(row=r, column=2, value=(
            f"Losing more than their share against {other_words} only, at the last Run's settings. Listed so "
            f"that changing what a pocket is judged against, on Control, finds them here."))
        h.font = Font(name="Calibri", bold=True, color=INK)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=21 if note_of else 20)
        h.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 30
        r += 1
        for t in others:
            write(r, *t)
            r += 1
    # material but too small to test: shown, not hidden (the firm, 25 Sep 2026: "this is a materiality thing")
    # on Three-way, no red on a row whose grid doesn't hold the split's partner fixed: its gap may be
    # mostly that column (the firm, 25 Sep 2026, after the seventh walk). A real effect of the split
    # column still shows red in the grids that do hold it fixed. Profit's flag is literal ("short of its band
    # by 0.80 points ($16,000)"): a shortfall is worse, and one that ends "(not significant)" is amber
    short, unsure = 'LEFT($R5,8)="short of"', 'RIGHT($R5,17)="(not significant)"'
    worse = f'OR($R5="worse",AND({short},NOT({unsure})))'
    red = f'AND({worse},LEFT($T5,3)<>"no:")' if note_of else worse
    for formula, fill in ((red, WORSE_FILL), (f'OR($R5="{engine.UNSURE_WORSE}",AND({short},{unsure}))', LUCK_FILL),
                          ('AND($M5="yes",LEFT($R5,7)="too few")', SMALL_FILL)):
        ws.conditional_formatting.add(f"B5:S{max(r, 6)}", FormulaRule(formula=[formula], fill=PatternFill(
            "solid", fgColor=fill, bgColor=fill)))
    seg_w = 26 if grids is not res.grids else 13
    # the measure's name on one line: "Contribution before losses per booked dollar" (the render, 26 Sep 2026);
    # and profit's flag: "short of its band by 0.80 points ($16,000) (not significant)"
    for col, w in zip("ABCDEFGHIJKLMNOPQRS", (2, 42, 12, 22, 16 if seg_w == 13 else 26, seg_w, 8, 8, 8, 12, 12, 30,
                                              14, 11, 11, 11, 11, 56, 17)):
        ws.column_dimensions[col].width = w
    ws.column_dimensions["U" if note_of else "T"].width = 22
    if note_of:
        ws.column_dimensions["T"].width = 30
        ws.row_dimensions[2].height = 86
        for row in ws.iter_rows(min_row=5, min_col=20, max_col=20):
            row[0].alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B5"
    _fit(ws)


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


NOT_TESTED = "Not tested: too few losses"
#: a pocket with no other pocket in its band, judged against the book instead (the firm, 26 Sep 2026)
ALONE = "alone in its band: compared with the book"
SMALL_FILL = "DDEBF7"      # material, but too few losses to test: look at it by hand
WARN_TEXT = "960019"

# GCO's side and RANR's read together (NEXT-GOAL 3.4), only for these three pairs; blank otherwise. Each side
# is the one shown in colour: tested, and significant
TOGETHER = {("more", "more"): "priced for it", ("more", "less"): "net drain", ("less", "less"): "safe but idle"}


def together_of(gco: str | None, ranr: str | None) -> str:
    """gco and ranr are each "more", "same", "less", or None when a side is
    untested or not significant: losing more and keeping more is priced for
    it; losing more and keeping less, a net drain; losing less and keeping
    less, safe but idle."""
    return TOGETHER.get((gco, ranr), "")


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
                "alone in its band is compared with the book. The excess over the book is shown beside it for "
                "reference.")
DECIDES_BOOK = ("The rest of the book decides each pocket's flag, its dollars and whether it is material. The "
                "excess over its band is shown beside it for reference.")


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


def _side(idx, lo: float, hi: float) -> str | None:
    if idx is None:
        return None
    return "more" if idx >= hi else "less" if idx <= lo else "same"


RED_CELL, GREEN_CELL = "F2C4C4", "CFE8C4"
# the tab's columns, one side after the other (the firm, 25 Sep 2026: "instead of just listing GCO vs
# Comparison, find a clean way to display the comparable metrics"), and since NEXT-GOAL 3.4 three sides:
# what they paid us, what they cost us, what we kept
LVR_C, LVR_G, LVR_R, LVR_T = 5, 11, 17, 23       # first column of each side, and Together
# the dollars of the comparison that decides come first, the other's beside them (the firm, 26 Sep 2026)
LVR_SIDE = ("This pocket", "{rest}", "Gap", "Reading", "{first} ($)", "{other} ($)")
# (measure, heading, first column, word for more, word for less, the side that is worse). Contribution and
# profit say their gap literally instead (engine.literal; the firm, 26 Sep 2026: "yes I prefer it to be literal")
LVR_SIDES = (("contribution_rate", "What they paid us: contribution before losses", LVR_C, None, None, "less"),
             ("gco_rate", "What they cost us: GCO", LVR_G, "losing more", "losing less", "more"),
             ("ranr_rate", "What we kept: profit after losses (RANR)", LVR_R, None, None, "less"))
PROFIT_SIDE = {engine.WORSE: "less", engine.UNSURE_WORSE: "less", engine.BETTER: "more", engine.UNSURE_BETTER: "more"}


def _rest_rate(s, parent) -> float | None:
    den = parent.den - s.den
    return (parent.num - s.num) / den if den else None


#: Losses vs revenue's hidden columns, far right of the charts: each row's untested mark and each side's flag,
#: which the red and green rules read (OC-40: the colours follow Control)
LVR_HIDDEN = 60
CHART_POINTS = 100        # on the hidden _chart sheet: each grid's points as of the last Run, x then y


def _losses_vs_revenue(ws, res) -> None:
    """What they paid us, what they cost us and what we kept, per pocket
    (NEXT-GOAL 3.4). The firm: 'GCO is high but profit is high - do we care?
    maybe.' Each side shows the pocket's rate, the rate of the rest it's
    compared with, the gap, a reading and the dollars, so the numbers behind a
    reading are on the row. GCO reads by the loss lines on Control (a
    multiple); contribution and profit by the profit line (points), as the
    engine read them, so this tab and Where it bleeds can't disagree (OC-32).
    Red and green show which side is worse or better (the firm, 25 Sep 2026:
    "i can just visually see that"). Nothing is netted: RANR already has GCO
    taken out (OC-29, OC-35), so contribution adds it back. The dollars use the
    same comparison as the reading (the third walk, defect 5), the engine's, so
    materiality and Where it bleeds agree (the firm, 26 Sep 2026); the other
    comparison's dollars sit beside them. Contribution and profit read
    literally: "short of its band by 0.80 points ($16,000)".

    Live (OC-40): the rest's rate, the gap, the readings, both dollar columns,
    Together and Compared with are formulas over the hidden _pockets sheet, and
    red and green are rules over each side's flag, so a line changed on Control
    shows here at once. The rows, their order and the charts are the last Run's."""
    names = _names(res)
    b = res.config.benchmark
    if b is None or not {"gco_rate", "ranr_rate", "contribution_rate"} <= {m.name for m in res.measures}:
        _title(ws, "Losses vs revenue", "Needs the Control settings.", "B:T")
        return
    lv = live.ensure(ws.parent, res)
    peers = b.compare_to == "peers"
    _title(ws, "Losses vs revenue", "", "B:X")
    ws["B2"] = live.text(
        "Each pocket beside ", JUDGED,
        ": what they paid us (contribution before losses), what they cost us (GCO) and what we kept (profit after "
        "losses, RANR). RANR already has GCO taken out, so contribution is RANR + GCO. GCO counts as more at ",
        ('TEXT(worse_at,"0.00")',), "x or above and less at ", ('TEXT(better_at,"0.00")',),
        "x or below. Contribution and profit read as their gap: points short of or ahead of ", JUDGED,
        ", and the dollars that comes to. A gap counts ",
        ('IF(profit_kind="test","only when the pocket\'s own test calls the gap significant",IF(profit_kind="points",'
         '"at "&TEXT(profit_line*100,"0.00")&" points either way","when the gap reaches "&TEXT(profit_line,'
         '"#,##0")&" dollars (the materiality line)"))',),
        ". ", ('IF(judged_band,"Over its band","Over the book")',), ": the dollars over ", JUDGED, "; ",
        ('IF(judged_band,"over the book","over its band")',),
        " is beside it for reference. Red is worse, green is better; a gap that is not significant is marked and "
        "left plain. Together: losing more and keeping more is priced for it; losing more and keeping less, a net "
        "drain; losing less and keeping less, safe but idle.")
    ws.row_dimensions[2].height = 72
    _in_use(ws, "Rows sorted as of the last Run, and the charts are as of the last Run too: changing a line on "
                "Control updates the readings, dollars and colours here, not the order or the charts.", "X")
    side_heads = [live.text(('IF(judged_band,"Rest of band","Rest of book")',)) if h == "{rest}" else
                  live.text(('IF(judged_band,"Over its band ($)","Over the book ($)")',)) if h == "{first} ($)" else
                  live.text(('IF(judged_band,"Over the book ($)","Over its band ($)")',)) if h == "{other} ($)"
                  else h for h in LVR_SIDE]
    # the charts' own numbers (the Control lines, the named pockets, the points) live on a hidden sheet:
    # hidden cells on this tab aren't drawn by every spreadsheet program
    wb = ws.parent
    if CHART_DATA in wb.sheetnames:
        del wb[CHART_DATA]
    hs = wb.create_sheet(CHART_DATA)
    hs.sheet_state = "hidden"
    real = lambda p: stats.significant(p, b.confidence)      # noqa: E731
    untested_words = (engine.THIN, engine.FEW)
    top = 4
    ms = {m.name: m for m in res.measures}
    for gi, g in enumerate(res.grids):
        rows = []
        mates = {}
        for (bl, _), _c in g.inner():
            mates[bl] = mates.get(bl, 0) + 1
        for (bl, dl), c in g.inner():
            ss = {k: c.rates[k] for k, *_ in LVR_SIDES}
            alone = peers and ss["gco_rate"].alone
            band = peers and not alone
            gaps = {k: s.vs_band if band else s.vs_rest for k, s in ss.items()}
            # every pocket with all three comparisons, whatever its size: below fewest loans a dollar rate
            # is still shuffled (docs/statistics.md B2), and only fewest losses leaves a side untested. With
            # "judged against" live, a pocket complete against either comparison is kept (OC-40)
            other = {k: s.vs_rest if band or mates[bl] == 1 else s.vs_band for k, s in ss.items()}
            if any(v is None for v in gaps.values()) and any(v is None for v in other.values()):
                continue
            flags = {k: s.reading_band if band else s.reading_topline for k, s in ss.items()}
            ps = {k: s.p_band if band else s.p_book for k, s in ss.items()}
            sides = {k: PROFIT_SIDE.get(f, "same") for k, f in flags.items()}
            sides["gco_rate"] = _side(gaps["gco_rate"], b.better_at, b.worse_at)
            unsure = {k: f in (engine.UNSURE_WORSE, engine.UNSURE_BETTER) for k, f in flags.items()}
            unsure["gco_rate"] = (sides["gco_rate"] != "same" and not real(ps["gco_rate"])
                                  and flags["gco_rate"] not in untested_words)
            # untested on any side: no colour and no Together (the fourth walk, defect 3). Fewest losses is a
            # Run setting, so this is fixed until the next Run
            untested = bool(set(flags.values()) & set(untested_words))
            shown = {k: None if untested or unsure[k] else sides[k] for k in sides}
            rows.append({"band": bl, "seg": dl, "untested": untested,
                         "gidx": gaps["gco_rate"], "ridx": None if gaps["ranr_rate"] is None else gaps["ranr_rate"] * 100,
                         "shown": shown, "g_over": ss["gco_rate"].dollars, "units": ss["gco_rate"].units,
                         "rates": {k: s.rate for k, s in ss.items()}})
        rows.sort(key=lambda x: (x["untested"], -(x["g_over"] or 0)))
        ws.cell(row=top, column=2, value=f"{names[g.band]} x {names[g.dimension]}").font = Font(
            name="Calibri", bold=True, size=12)
        # two header rows: which side, then what each column holds
        _head(ws, top + 1, ["", "", ""] + [x for _, h, *_ in LVR_SIDES for x in (h, "", "", "", "", "")] + ["", ""])
        for _, _, a, *_ in LVR_SIDES:
            ws.merge_cells(start_row=top + 1, start_column=a, end_row=top + 1, end_column=a + 5)
            ws.cell(row=top + 1, column=a).alignment = Alignment(horizontal="center")
        ws.row_dimensions[top + 1].height = 16
        _head(ws, top + 2, ["Band", "Segment", "Loans"] + side_heads * 3 + ["Together", "Compared with"])
        r = top + 3
        first = r
        for row in rows:
            at = lambda k, c: lv.ref("grids", g, row["band"], row["seg"], k, c)        # noqa: E731
            cells = [row["band"], row["seg"], row["units"]]
            for k, _, a, more, less, _ in LVR_SIDES:
                neg = "-" if ms[k].higher_is == "better" else ""
                sr = lambda c: f'IF({at(k, c)}="","",{neg}{at(k, c)})'                  # noqa: E731
                gap = at(k, live.P_GAP)
                if more is None:
                    word = f"={at(k, live.P_SAID)}"      # literal: the gap, in points and dollars
                else:
                    z = at(k, live.P_FLAG)
                    word = (f'=IF({z}="{engine.WORSE}","{more}",IF({z}="{engine.UNSURE_WORSE}","{more} (not '
                            f'significant)",IF({z}="{engine.BETTER}","{less}",IF({z}="{engine.UNSURE_BETTER}",'
                            f'"{less} (not significant)",IF({z}="{engine.IN_LINE}","about the same",{z})))))')
                cells += [row["rates"][k], f"={at(k, live.P_REST)}",
                          f'=IF({gap}="","",{gap}*100)' if ms[k].in_points else f"={gap}", word,
                          f"=IF(judged_band,{sr(live.P_EX_BAND)},{sr(live.P_EX_BOOK)})",
                          f"=IF(judged_band,{sr(live.P_EX_BOOK)},{sr(live.P_EX_BAND)})"]
            gz, rz = at("gco_rate", live.P_FLAG), at("ranr_rate", live.P_FLAG)
            u = f"${_col(LVR_HIDDEN)}{r}"
            together = (f'=IF({u},"",IF(AND({gz}="{engine.WORSE}",{rz}="{engine.BETTER}"),"{TOGETHER[("more", "more")]}",'
                        f'IF(AND({gz}="{engine.WORSE}",{rz}="{engine.WORSE}"),"{TOGETHER[("more", "less")]}",'
                        f'IF(AND({gz}="{engine.BETTER}",{rz}="{engine.WORSE}"),"{TOGETHER[("less", "less")]}",""))))')
            # a lone pocket's note sits in its own column: Together only ever reads the pair (the firm, 26 Sep 2026)
            cells += [together, f'=IF(AND(judged_band,{at("gco_rate", live.P_ALONE)}),"{ALONE}","")']
            for i, v in enumerate(cells, start=2):
                # a two-line reading makes a tall row: its numbers sit level with the words
                ws.cell(row=r, column=i, value=v).alignment = Alignment(vertical="center")
            ws.cell(row=r, column=LVR_HIDDEN, value=row["untested"])
            for j, (k, *_x) in enumerate(LVR_SIDES, start=1):
                ws.cell(row=r, column=LVR_HIDDEN + j, value=f"={at(k, live.P_FLAG)}")
            # the words after a number start clear of it; an indent only shows on a cell aligned left
            ws.cell(row=r, column=LVR_T).alignment = Alignment(horizontal="left", indent=1, vertical="center")
            for k, _, a, _, _, bad in LVR_SIDES:
                ws.cell(row=r, column=a).number_format = ws.cell(row=r, column=a + 1).number_format = "0.00%"
                ws.cell(row=r, column=a + 2).number_format = '0.00"x"' if k == "gco_rate" else PTS_FMT
                ws.cell(row=r, column=a + 4).number_format = ws.cell(row=r, column=a + 5).number_format = "#,##0"
                # clear of the gap, and a literal reading on two lines rather than cut off
                ws.cell(row=r, column=a + 3).alignment = Alignment(horizontal="left", indent=1, wrap_text=True,
                                                                   vertical="center")
                ws.cell(row=r, column=a).border = Border(left=Side(style="thin", color=SLATE))
            ws.cell(row=r, column=LVR_T).border = Border(left=Side(style="thin", color=SLATE))
            ws.cell(row=r, column=LVR_T).font = Font(name="Calibri", bold=True)
            r += 1
        if rows:
            # red and green by side, worse and better, from the flag the lines on Control give; a side that isn't
            # significant isn't shaded like a finding (the sixth walk, defect 2), and nothing on an untested row
            u = f"${_col(LVR_HIDDEN)}{first}"
            for j, (k, _, a, *_x) in enumerate(LVR_SIDES, start=1):
                f = f"${_col(LVR_HIDDEN + j)}{first}"
                rng = f"{_col(a + 2)}{first}:{_col(a + 3)}{r - 1}"
                for word, fill in ((engine.WORSE, RED_CELL), (engine.BETTER, GREEN_CELL)):
                    ws.conditional_formatting.add(rng, FormulaRule(
                        formula=[f'AND(NOT({u}),{f}="{word}")'], fill=PatternFill("solid", fgColor=fill,
                                                                                   bgColor=fill)))
        if not rows:
            ws.cell(row=r, column=2, value="No pocket has enough loans to place.")
            r += 1
        if any(not x["untested"] and x["gidx"] is not None and x["ridx"] is not None for x in rows):
            _revenue_chart(ws, hs, rows, first, f"{names[g.band]} x {names[g.dimension]} (as of the last Run)", b,
                           profit_line(res), 1 + gi * 3, top, CHART_POINTS + gi * 3)
        top = max(r, top + 24) + 2
    # a reading fits "losing more (not significant)" on one line (the seventh walk, defects 4 and 5); a literal
    # one, "short of its band by 0.80 points ($16,000) (not significant)", on two
    widths = [2, 15, 12, 7] + [9, 9, 10, 44, 12, 12] * 3 + [14, 36, 2]
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[_col(j)].width = w
    for j in range(LVR_HIDDEN, LVR_HIDDEN + 4):
        ws.column_dimensions[_col(j)].hidden = True
    ws.cell(row=3, column=LVR_HIDDEN, value="For the colour rules: untested (fewest losses, a Run setting), then "
                                            "each side's flag")
    ws.freeze_panes = "B4"
    _fit(ws)


def _nice_step(span: float) -> float:
    """A round tick step giving about eight ticks over `span`."""
    for step in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50):
        if span / step <= 8:
            return step
    return 100.0


def _revenue_chart(ws, hs, rows, first: int, title: str, b, line, hcol: int, anchor_row: int, pcol: int) -> None:
    """One chart per grid (the third walk, defect 11: one chart for every grid
    counted the same loans six times). GCO's multiple across, on a scale of
    tens, so one pocket at 8x doesn't squash the rest and 1.00x sits on a tick;
    profit's gap in points up. The lines from Control mark the sides (0 when
    profit is read by each pocket's own test), and the three biggest bleeders
    are named. All as of the last Run (OC-40): the points are copied to the
    hidden _chart sheet, so the chart doesn't move with a line changed on
    Control, and its title says so."""
    chart = ScatterChart()
    chart.title = title
    chart.style = 13
    chart.x_axis.title = "GCO multiple (right: losing more)"
    chart.y_axis.title = "Profit gap in points (up: ahead)"
    boxed = [x for x in rows if not x["untested"] and x["gidx"] is not None and x["ridx"] is not None]
    for k, x in enumerate(boxed, start=1):
        hs.cell(row=k, column=pcol, value=x["gidx"])
        hs.cell(row=k, column=pcol + 1, value=x["ridx"])
    last = len(boxed)
    pts = Series(Reference(hs, min_col=pcol + 1, min_row=1, max_row=last),
                 Reference(hs, min_col=pcol, min_row=1, max_row=last), title="Pockets")
    pts.marker.symbol = "circle"
    pts.marker.size = 6
    pts.marker.graphicalProperties.solidFill = "2F5597"
    pts.marker.graphicalProperties.line.solidFill = "2F5597"
    pts.graphicalProperties.line.noFill = True
    chart.series.append(pts)
    xs, ys = [x["gidx"] for x in boxed if x["gidx"] > 0], [x["ridx"] for x in boxed]
    x_lo = 10 ** math.floor(math.log10(min(xs + [b.better_at])))
    x_hi = 10 ** math.ceil(math.log10(max(xs + [b.worse_at])))
    band = line.value * 100 if line is not None and line.kind == "points" else None
    lo_y, hi_y = min(ys + ([-band] if band else [0.0])), max(ys + ([band] if band else [0.0]))
    step = _nice_step((hi_y - lo_y) or 1.0)
    y_lo, y_hi = math.floor(lo_y / step) * step - step, math.ceil(hi_y / step) * step + step
    # the lines, in hidden helper columns: x, y pairs
    r = 1
    lines = [((b.worse_at, y_lo), (b.worse_at, y_hi)), ((b.better_at, y_lo), (b.better_at, y_hi))]
    lines += [((x_lo, band), (x_hi, band)), ((x_lo, -band), (x_hi, -band))] if band else [((x_lo, 0), (x_hi, 0))]
    for (x1, y1), (x2, y2) in lines:
        for k, (xv, yv) in enumerate(((x1, y1), (x2, y2))):
            hs.cell(row=r + k, column=hcol, value=xv)
            hs.cell(row=r + k, column=hcol + 1, value=yv)
        ln = Series(Reference(hs, min_col=hcol + 1, min_row=r, max_row=r + 1),
                    Reference(hs, min_col=hcol, min_row=r, max_row=r + 1), title="line")
        ln.marker.symbol = "none"
        ln.graphicalProperties.line.solidFill = "7F7F7F"
        ln.graphicalProperties.line.dashStyle = "dash"
        chart.series.append(ln)
        r += 2
    # the three biggest bleeders, named on the chart
    from openpyxl.chart.label import DataLabelList
    # only pockets whose loss side is a finding: not one whose test says it isn't significant (the seventh walk)
    named = [k for k, x in enumerate(boxed) if x["shown"]["gco_rate"] == "more"][:3]
    for n_, k in enumerate(named):
        row = boxed[k]
        name = f"{row['band']} / {row['seg']}"
        one = Series(Reference(hs, min_col=pcol + 1, min_row=k + 1, max_row=k + 1),
                     Reference(hs, min_col=pcol, min_row=k + 1, max_row=k + 1), title=name)
        one.marker.symbol = "circle"
        one.marker.size = 8
        one.marker.graphicalProperties.solidFill = "C00000"
        one.marker.graphicalProperties.line.solidFill = "C00000"
        one.graphicalProperties.line.noFill = True
        one.dLbls = DataLabelList()
        one.dLbls.showSerName = True
        for flag in ("showVal", "showCatName", "showLegendKey", "showPercent", "showBubbleSize"):
            setattr(one.dLbls, flag, False)
        one.dLbls.position = ("r", "t", "b")[n_]
        chart.series.append(one)
        r += 1
    chart.legend = None
    chart.x_axis.scaling.logBase = 10
    chart.x_axis.scaling.min, chart.x_axis.scaling.max = x_lo, x_hi
    chart.y_axis.scaling.min, chart.y_axis.scaling.max = y_lo, y_hi
    chart.y_axis.majorUnit = step
    chart.x_axis.number_format = '0.00"x"'
    chart.y_axis.number_format = '+0.0" pts";-0.0" pts";0" pts"'
    chart.x_axis.delete = chart.y_axis.delete = False
    chart.x_axis.crosses = "min"           # the multiples along the bottom, not across a profit of 0 (the render)
    chart.width, chart.height = 15, 10
    ws.add_chart(chart, f"{_col(LVR_T + 3)}{anchor_row}")


def _heat(ws, rng: str, m, bound: float | None = None) -> None:
    """A heat map: a multiple on a doubling scale, white at 1.00x; for profit a
    difference in points, white at 0, red below (keeps less) and green above,
    even either way to the biggest gap shown (NEXT-GOAL 3.2)."""
    if m.in_points:
        top = max(bound or 0.0, 0.01)
        ws.conditional_formatting.add(rng, ColorScaleRule(start_type="num", start_value=-top, start_color=RED,
                                                          mid_type="num", mid_value=0, mid_color="FFFFFF",
                                                          end_type="num", end_value=top, end_color=GREEN))
        return
    lo, hi = (GREEN, RED) if m.higher_is == "worse" else (RED, GREEN)
    ws.conditional_formatting.add(rng, ColorScaleRule(start_type="num", start_value=0.5, start_color=lo,
                                                      mid_type="num", mid_value=1, mid_color="FFFFFF",
                                                      end_type="num", end_value=2, end_color=hi))


def _block(ws, top: int, c0: int, label: str, rows_: list[str], cols: list[str], value, fmt: str, heat_m=None,
           skip_margins: bool = False, bound: float | None = None) -> None:
    ws.cell(row=top, column=c0, value=label).font = Font(name="Calibri", bold=True, color=PAPER)
    ws.cell(row=top, column=c0).fill = PatternFill("solid", fgColor=INK)
    for j, d in enumerate(cols, start=c0 + 1):
        h = ws.cell(row=top, column=j, value=d)
        h.font = Font(name="Calibri", bold=True, color=PAPER)
        h.fill = PatternFill("solid", fgColor=INK)
        h.alignment = Alignment(wrap_text=True, horizontal="center")
    rr = top + 1
    shown: list[float] = []
    for bl in rows_:
        ws.cell(row=rr, column=c0, value=bl)
        for j, d in enumerate(cols, start=c0 + 1):
            if skip_margins and (bl == engine.ALL or d == engine.ALL):
                continue
            v = value(bl, d)
            if v is not None:
                ws.cell(row=rr, column=j, value=v).number_format = fmt
                if isinstance(v, (int, float)):
                    shown.append(abs(v))
        rr += 1
    if heat_m is not None:
        _heat(ws, f"{_col(c0 + 1)}{top + 1}:{_col(c0 + len(cols))}{rr - 1}", heat_m,
              bound if bound is not None else max(shown, default=0.0))


def _grids(ws, res) -> None:
    """Every band crossed with every dimension, as heat maps: the rate, the rate
    against the book, and the rate against the rest of the same band (its peers).
    Red is worse, green better; for profit, a gap in points where more is
    better, below zero is red. A column shown per pocket (median or average)
    gets its own block. A split by a category repeats the grid once per value,
    side by side."""
    names = _names(res)
    _title(ws, "Grids", "Each grid three ways: the rate, the rate against the book, and the rate against the rest "
                        "of the same band. Red is worse, green is better."
                        + (" Profit and contribution are compared as a gap in points, and less is red."
                           if _has_profit(res) else ""), "B:Z")
    _in_use(ws, "Nothing on this tab moves with them: the colours are the gaps themselves, and a blank is a pocket "
                "with fewer losses than fewest losses, which takes effect on the next Run.", "Z", 30)
    width = max((len(x.dim_labels) + 3 for x in res.grids), default=6)
    shows = [m for m in res.measures if m.mode == "median"]
    r = 4
    for g in res.grids:
        rows_ = g.band_labels + [engine.ALL]
        cols_all = g.dim_labels + [engine.ALL]
        for m in res.measures:
            if not m.is_rate:
                continue
            note = "  (more is better)" if m.higher_is == "better" else ""
            ws.cell(row=r, column=2, value=f"{names[g.band]} x {names[g.dimension]}: {m.title}{note}").font = Font(
                name="Calibri", bold=True, size=12)
            ws.cell(row=r + 1, column=2, value=m.words()).font = Font(name="Calibri", italic=True, size=9,
                                                                      color=SLATE)
            top = r + 2

            def cell(bl, d, f, m=m, g=g):
                c = g.cells.get((bl, d))
                return f(c.rates[m.name]) if c is not None else None

            untested = (engine.THIN, engine.FEW)
            # the heat maps leave out what the minimums on Control say not to judge (the third
            # walk, defect 4: a 1-loan row and an untested 54-loan pocket were the strongest colours)
            _block(ws, top, 2, "Rate", rows_, cols_all, lambda bl, d: cell(bl, d, lambda s: s.rate), "0.00%")
            _block(ws, top, 2 + width, "Vs the book", rows_, cols_all,
                   lambda bl, d: cell(bl, d, lambda s: _shown(s.vs_topline, m) if s.reading_topline not in untested
                                      else None), _gap_fmt(m), m)
            _block(ws, top, 2 + 2 * width, "Vs the rest of its band", rows_, g.dim_labels,
                   lambda bl, d: cell(bl, d, lambda s: _shown(s.vs_band, m) if s.reading_band not in untested
                                      else None), _gap_fmt(m), m, skip_margins=True)
            r = top + len(rows_) + 1
            ws.cell(row=r, column=2 + width, value="Blank: fewer losses than the minimum on Control, so "
                                                   "not compared.").font = Font(name="Calibri", italic=True,
                                                                                size=9, color=SLATE)
            r += 1
            if res.config.split and res.config.split[1] == "each_value" and g.split_labels:
                ws.cell(row=r, column=2, value=f"...split by {res.config.split[0]}: the rate against the book, "
                                               f"one grid per value").font = Font(name="Calibri", italic=True)
                r += 1
                top_rate = res.total.rates[m.name].rate
                for k, lab in enumerate(g.split_labels):
                    if k and k % 3 == 0:
                        r += len(rows_) + 1
                    c0 = 2 + (k % 3) * width

                    def val(bl, d, lab=lab, m=m, g=g):
                        c = g.split_cells.get((bl, d, lab))
                        if c is None or c.rates[m.name].units < res.min_units.get(m.name, 0):
                            return None
                        return _shown(engine.gap_of(c.rates[m.name].rate, top_rate, m.in_points), m)

                    _block(ws, r, c0, f"{res.config.split[0]} = {lab}", g.band_labels, g.dim_labels, val,
                           _gap_fmt(m), m)
                r += len(rows_) + 2
        for sm in shows:
            fig = "Average" if sm.show == "average" else "Median"
            ws.cell(row=r, column=2, value=f"{names[g.band]} x {names[g.dimension]}: {fig.lower()} {sm.value} per "
                                           f"pocket").font = Font(name="Calibri", bold=True, size=12)

            def shown(bl, d, sm=sm, g=g):
                c = g.cells.get((bl, d))
                if c is None:
                    return None
                return c.medians[sm.name].mean if sm.show == "average" else c.medians[sm.name].median

            ws.cell(row=r + 1, column=2, value=f"Beside the rates, for reading them: not tested, and {'an' if fig == 'Average' else 'a'} {fig.lower()} "
                                               f"doesn't add up across pockets.").font = Font(
                name="Calibri", italic=True, size=9, color=SLATE)
            got = [v for v in (shown(bl, d) for bl in rows_ for d in cols_all) if v is not None]
            # whole numbers for amounts, two places for small figures such as a ratio
            # (the third walk, defect 14: #,##0.## printed 32,583.3 beside 32,967.)
            fmt = "#,##0" if got and max(abs(v) for v in got) >= 100 else "#,##0.00"
            _block(ws, r + 2, 2, fig, rows_, cols_all, shown, fmt)
            r += len(rows_) + 4
    ws.column_dimensions["A"].width = 2
    for j in range(2, 2 + 3 * width):
        ws.column_dimensions[_col(j)].width = 11
    for k in range(3):
        ws.column_dimensions[_col(2 + k * width)].width = 24
    _fit(ws)


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
    """One short cell per Three-way row, and the order: grids that hold the
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


def _split_tab(ws, res) -> None:
    """The third layer in words and heat maps. For a number column split at each
    pocket's own median: in every pocket, the high half against the low half,
    and one pooled answer across the pockets. Grids that hold fixed what the
    split column moves with come first."""
    field_, how = res.config.split
    names = _names(res)
    if how == "each_value":
        _title(ws, "Split", f"Every pocket split by each value of {field_}. The grids are on the Grids tab, one "
                            f"per value, and every three-way pocket is tested and ranked on the Three-way tab. "
                            f"{field_} isn't a segment of its own while it splits.", "B:H")
        return
    _title(ws, "Split", f"Every pocket split in two at its own median {field_}. How the tab works comes first; "
                        f"then each grid: what it holds fixed, a summary, and the pockets as heat maps.", "B:P")
    width = max((len(x.dim_labels) + 3 for x in res.grids), default=6)
    b = res.config.benchmark
    conf = b.confidence if b else 0.95
    allowance = {"bh": "Benjamini-Hochberg", "bonferroni": "Bonferroni", "none": "none"}.get(
        b.many_tests if b else "none", "none")
    # a test of a new variable may run without RANR, or without any dollar rate (Goal 2 item 2): then the note
    # says nothing about profit or shuffles
    profit, dollar_rates = _has_profit(res), _has_dollar_rates(res)
    # said once, here, instead of repeated under every grid (asked for on 25 Sep 2026)
    how_rows = [
        ("What it does", f"Inside each pocket (one band, one segment) the loans are sorted by {field_} and cut at "
                         f"that pocket's own median. The high half is compared with the low half, so the band and "
                         f"segment are the same on both sides. {field_} isn't cut into bands of its own while it "
                         f"splits."),
        ("High half vs low", "The high half's rate divided by the low half's: 2.00x means the high half goes bad"
                             + (", or loses," if dollar_rates else "") + " twice as often."
                             + (" Profit and contribution are a gap in points instead: +0.30 pts means the high half "
                                "keeps 0.30 points more per booked dollar." if profit else "")),
        ("p-value", live.text("The chance of a gap at least this big if the two halves were no different. Below ",
                              ('TEXT(significance_bar,"0%")',), " is significant. "
                              f"For the yes/no outcome's share of loans the test measures "
                    f"the gap in standard errors (how far a rate from this many loans typically lands from its "
                    f"true value)"
                    + (f"; for a dollar rate the loans are dealt into the two halves at random inside "
                       f"their pocket, {b.shuffles if b else 0:,} times, and the p-value is how often that made a gap "
                       f"as big" if dollar_rates else "")
                    + f". The pocket figures (the heat maps) are after the allowance for many tests "
                    f"({allowance}), across the pockets of one grid and one measure; a gap that is not "
                    f"significant is shown in brackets, unshaded. The summary's figure is one pooled test per "
                    f"grid and measure, with no allowance. Blank: a half has fewer loans or losses than the "
                    f"minimums on Control ({b.min_units if b else 0:,} loans, {b.min_events if b else 0:,} "
                    f"losses).")),
        ("Pooled across pockets", live.text(f"The high halves' actual total against what it would be at their "
                                            f"low halves' rates, added over every pocket, with its range at ",
                                            ('TEXT(confidence,"0%")',), " sure. "
                                  + ("For profit and contribution the difference is taken over the high halves' "
                                     "booked dollars, in points. " if profit else "")
                                  + f"For the yes/no outcome only, the odds are pooled too "
                                  f"(Mantel-Haenszel: a standard way to combine pockets without mixing their "
                                  f"loans), with their p-value (Cochran-Mantel-Haenszel), and Cochran's Q checks "
                                  f"whether the gap is about the same size in every pocket.")),
        ("What it assumes", f"A grid holds fixed only its band and segment. Anything {field_} moves with that the "
                            f"grid doesn't hold fixed can show up here as a {field_} effect, so each grid gives the "
                            f"correlation, and grids that hold fixed what {field_} moves with most come first. "
                            f"A correlation runs from -1 to 1: 0 means unrelated, and the further from 0, the "
                            f"more of a gap may belong to the other column. "
                            f"Inside a band the score still varies a little, so a little can remain even there. "
                            f"Loans are treated as independent of each other."),
    ]
    live.ensure(ws.parent, res)
    _in_use(ws, "The pooled range, the brackets on the heat maps (not significant) and \"Same size in every "
                "pocket?\" follow the confidence level on Control. The order of the grids is as of the last Run.",
            _col(2 + 2 * width - 1), 30)
    ws.cell(row=4, column=2, value="How this tab works").font = Font(name="Calibri", bold=True, size=12)
    r = 5
    for k, v in how_rows:
        ws.cell(row=r, column=2, value=k).font = Font(name="Calibri", bold=True)
        ws.cell(row=r, column=2).alignment = Alignment(vertical="top")
        c = ws.cell(row=r, column=3, value=v)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=2 + 2 * width - 1)
        ws.row_dimensions[r].height = 58 if k == "p-value" else 44
        r += 1
    r += 1
    heads = ["Measure", "Pockets tested", "High half worse in", "High vs low, pooled",
             live.text("Range (", ('TEXT(confidence,"0%")',), ")"),
             "p-value", "As odds", "p-value, as odds", "Same size in every pocket?"]
    pt = _partner(res)
    said_break = False
    for g in sorted(res.grids, key=lambda x: _holds_fixed(res, x)[1]):
        if pt and _holds_partner(res, g) is False and not said_break:
            # the fifth walk: a no-effect book still read 1.62x "under 0.01%" in these grids
            brk = ws.cell(row=r, column=2, value=f"Grids that don't hold {pt[0]} fixed. {field_} moves with {pt[0]} "
                                                 f"(correlation {pt[1]:+.2f}), so part of every gap below may be "
                                                 f"{pt[0]}, not {field_}.")
            brk.font = Font(name="Calibri", bold=True, size=12, color=WARN_TEXT)
            brk.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=2 + 2 * width - 1)
            ws.row_dimensions[r].height = 34
            r += 2
            said_break = True
        ws.cell(row=r, column=2, value=f"{names[g.band]} x {names[g.dimension]}").font = Font(
            name="Calibri", bold=True, size=12)
        fw = ws.cell(row=r + 1, column=2, value=_holds_fixed(res, g)[0])
        fw.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r + 1, start_column=2, end_row=r + 1, end_column=2 + 2 * width - 1)
        ws.row_dimensions[r + 1].height = 30
        _head(ws, r + 2, heads)
        ws.row_dimensions[r + 2].height = 44            # "Same size in every pocket?" on three lines
        rr = r + 3
        rates = [m for m in res.measures if m.is_rate]
        for m in rates:
            p = g.split_pooled.get(m.name, {})
            # the range at the confidence on Control (OC-40): the run's half-width at its own confidence,
            # divided by that confidence's z, is the standard error, and the live z scales it back up
            z_run = stats.z_for_confidence(conf)
            z = "NORMSINV(1-(1-confidence)/2)"
            if m.in_points:
                # profit: (O - E) over the high halves' booked dollars, in points (NEXT-GOAL 3.2)
                pooled = _shown(p.get("gap"), m)
                rng = ""
                if p.get("gap_hi") is not None:
                    g0, se = p["gap"] * 100, (p["gap_hi"] - p["gap"]) * 100 / z_run
                    rng = (f'=TEXT({live.num(g0)}-{z}*{live.num(se)},"+0.00;-0.00")&" to "&'
                           f'TEXT({live.num(g0)}+{z}*{live.num(se)},"+0.00;-0.00")&" pts"')
            else:
                pooled = p.get("ratio")
                rng = ""
                if p.get("ratio_hi"):
                    se = (p["ratio_hi"] - p["ratio"]) / z_run
                    rng = (f'=TEXT(MAX({live.num(p["ratio"])}-{z}*{live.num(se)},0),"0.00")&"x to "&'
                           f'TEXT({live.num(p["ratio"])}+{z}*{live.num(se)},"0.00")&"x"')
            vals = [m.title, p.get("pockets", 0),
                    f"{p['high_worse']} of {p['pockets']}" if p.get("pockets") else "none big enough",
                    pooled, rng, p.get("ratio_p"), p.get("odds"), p.get("odds_p"), _same_size(m, p, conf)]
            for i, v in enumerate(vals, start=2):
                # the last answer wraps in its own column: spilling left, the p-value beside it cut it off
                ws.cell(row=rr, column=i, value=v).alignment = Alignment(
                    horizontal="left" if i == 2 else "center", vertical="top", wrap_text=i == len(vals) + 1)
            ws.cell(row=rr, column=5).number_format = _gap_fmt(m)
            ws.cell(row=rr, column=7).number_format = P_FMT
            ws.cell(row=rr, column=8).number_format = '0.00"x"'
            ws.cell(row=rr, column=9).number_format = P_FMT
            rr += 1
        r = rr + 1
        for m in rates:
            def cmp_(bl, d, k, m=m, g=g):
                got = g.split_compare.get((bl, d), {}).get(m.name)
                return got[k] if got else None

            pcell = {(bl, d): f"{_col(2 + width + 1 + j)}{r + 1 + i}" for i, bl in enumerate(g.band_labels)
                     for j, d in enumerate(g.dim_labels)}

            def shown(bl, d, m=m, g=g, pcell=pcell):
                # a gap that is not significant: in brackets and unshaded (the sixth walk, defect 9). Which is
                # which follows the confidence on Control: the p-value beside it, against the one bar (OC-40)
                got = g.split_compare.get((bl, d), {}).get(m.name)
                if not got or got[0] is None:
                    return None
                v = _shown(got[0], m)
                words = (f'"("&TEXT({live.num(v)},"+0.00;-0.00")&" pts)"' if m.in_points
                         else f'"("&TEXT({live.num(v)},"0.00")&"x)"')
                return f"=IF({live.sig(pcell[(bl, d)])},{live.num(v)},{words})"

            got_all = [abs(_shown(x[m.name][0], m)) for x in g.split_compare.values()
                       if m.name in x and x[m.name][0] is not None]
            _block(ws, r, 2, m.title, g.band_labels, g.dim_labels, shown, _gap_fmt(m), m,
                   bound=max(got_all, default=0.0))
            _block(ws, r, 2 + width, "p-value", g.band_labels, g.dim_labels, lambda bl, d: cmp_(bl, d, 1),
                   P_FMT)
            r += len(g.band_labels) + 2
        r += 1
    ws.column_dimensions["A"].width = 2
    for j in range(2, 2 + 3 * width):
        ws.column_dimensions[_col(j)].width = 12
    ws.column_dimensions["F"].width = 18         # the range: "-3.65 to -1.92 pts" (the render, 26 Sep 2026)
    for k in range(3):
        ws.column_dimensions[_col(2 + k * width)].width = 44     # a measure's whole name on one line
    _fit(ws)


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


def _check(ws, res, src: Path, record: str = "") -> None:
    _title(ws, "Check", "Settings used, tie-outs, and what was left out.", "B:C")
    rows = [("Extract", src.name), ("Loans run", f"{res.rows:,}"),
            ("Record of this run", f"{record}, beside this workbook: every setting the run used, kept for the "
                                   f"file. It is replaced by the next Run."),
            ("Tie-out checks", f"{res.tie_outs:,} of {res.tie_outs:,} agree: every grid adds up to the book")]
    ran = what_was_run(getattr(res, "control_used", None) or {})
    if ran:
        rows.insert(2, ("What was run", ran))
    lv = live.ensure(ws.parent, res)
    # a test of a new variable may run without the dollar columns: then no profit and no dollar rate is on Check
    profit, dollar_rates = _has_profit(res), _has_dollar_rates(res)
    first_live = None
    if res.config.benchmark is not None:
        # the lines in use now, beside what the last Run used (OC-40): a line changed on Control since the Run
        # is shaded, and the Log keeps the record
        rows.append(("In use now, from Control", "The lines the result tabs are reading now. Beside each, what "
                                                 "the last Run used; a line changed since then is shaded.",
                     "The last Run used"))
        first_live = len(rows) + 4
        for label, r in (("The loss line: worse at", live.L_WORSE), ("The loss line: better at", live.L_BETTER),
                         ("The profit line", live.L_PKIND), ("Confidence", live.L_CONF),
                         ("Materiality", live.L_MKIND), ("Judged against", live.L_BAND)):
            if r == live.L_PKIND and not profit:
                continue
            rows.append((label, f"='{live.LIVE_SHEET}'!$E${r}", lv.last.get(r)))
        last_live = len(rows) + 3
        for m in res.measures:
            if not m.is_rate:
                continue
            n = sum(1 for g in res.grids for _ in g.inner())
            worse = live.count_formula(m.name, [(live.P_FLAG, f'"{engine.WORSE}"')])
            material = live.count_formula(m.name, [(live.P_FLAG, f'"{engine.WORSE}"'), (live.P_MATERIAL, '"yes"')])
            rows.append((f"Worse now: {m.title}", f'={worse}&" of {n:,} pockets on the grids read worse; "&'
                                                   f'{material}&" of them are material."'))
    rows += _origination_rows(res) + _column_rows(res)
    for m in res.measures:
        lo = res.left_out.get(m.name)
        if lo:
            rows.append((f"Left out of {m.title}", "; ".join(f"{k:,} x {col} {why}" for (col, why), k in lo.items())))
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
            rows.append((f"Smallest gap a typical pocket could show: {m.title}",
                         f"{typ * 100:.2f} points either way (the median over the pockets; caught "
                         f"{b.power:.0%} of the time at {b.confidence:.0%} sure)" if typ
                         else "can't be sized: no pocket has the loans to show one"))
            continue
        rows.append((f"Loans needed for a {ln.gap:g}x gap: {m.title}",
                     f"about {ln.loans:,}" if ln.loans else "can't be sized (the book's rate is zero)"
                     if not ln.rate else "more than this book has: not even half of it could show that gap"))
    for m in res.measures:
        if m.is_rate and b is not None:
            # the line in use now (OC-40)
            v = lv.line_cell[m.name]
            said = (f'"a shortfall of "&{_amount_f(v, m)}&": the same dollar line as GCO (Control\'s materiality '
                    f'answer)"' if m.name in cfgmod.PROFIT else _amount_f(v, m))
            rows.append((f"Materiality line: {m.title}",
                         f'=IF({v}="","no line: the dollar line on Control is a GCO amount",{said})'))
    if res.config.split:
        sf, how = res.config.split
        rows.append(("Split", f"{sf}, " + ("each pocket halved at its own median" if how == "own_median"
                                          else "one layer per value") + f". {sf} isn't cut on its own while it "
                                                                        f"splits. Three-way pockets: "
                                                                        f"{sum(1 for g in res.three_way for _ in g.inner()):,}."))
        for f, r in sorted(res.split_moves_with.items(), key=lambda t: -abs(t[1])):
            if f != sf:
                rows.append((f"How closely {sf} moves with {f}", f"correlation {r:+.2f}"))
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
            words[-1] += " (the smallest outcome gap a pocket of typical size can call significant)"
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
                                 f"for the rest of its band; the Test column says how many shuffles made a gap as "
                                 f"big." if dollar_rates else "")
                              + (" Profit and contribution are compared as a gap in points, never a multiple."
                                 if profit else "")
                              + f" The split's odds: "
                              f"Cochran-Mantel-Haenszel, which asks whether an odds ratio this far from 1 could "
                              f"come from shuffling loans within their pockets. It has no continuity correction: "
                              f"nothing is taken off the gap between actual and expected before it is squared."))
        # the words the tabs use, defined once (docs/statistics.md, conventions; NEXT-GOAL 3.1)
        rows.append(("p-value", live.text("The chance of a gap at least this big if there were no real difference, "
                                          "after the allowance for many tests. Below ",
                                          ('TEXT(significance_bar,"0%")',), " is significant, at ",
                                          ('TEXT(confidence,"0%")',), " sure. Two-sided: a gap either way counts.")))
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
    rows.append(("What the last Run used", "Every setting, as the Log records it. Changing Control afterwards "
                                           "doesn't change these."))
    for q, words in control.describe(_settings_of(res.config)):
        rows.append((q, words))
    for w in res.warnings:
        rows.append(("Warning", _plain_warning(w)))
    rows += checks.rows(res)                    # fixes 3.15 to 3.18: pre-spec, pocket budget, families, products
    for i, (k, v, *d) in enumerate(rows, start=4):
        ws.cell(row=i, column=2, value=k).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=i, column=2).font = Font(name="Calibri", bold=True)
        ws.cell(row=i, column=3, value=v).alignment = Alignment(wrap_text=True, vertical="top")
        if d:
            ws.cell(row=i, column=4, value=d[0]).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=i, column=4).font = Font(name="Calibri", color=SLATE)
    if first_live:
        ws.cell(row=first_live - 1, column=4).font = Font(name="Calibri", bold=True)
        ws.conditional_formatting.add(f"C{first_live}:C{last_live}", FormulaRule(
            formula=[f"$C{first_live}<>$D{first_live}"], fill=PatternFill("solid", fgColor=LUCK_FILL,
                                                                           bgColor=LUCK_FILL)))
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 100
    ws.column_dimensions["D"].width = 40
    _fit(ws)


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
