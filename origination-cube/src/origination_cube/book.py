"""The workbook: the answers for a run go in, and the results come out.

Ruling OC-22 (25 Sep 2026): nobody types a command. The launcher's two
buttons call the two functions here:

    set_up(extract)   writes or refreshes the input tabs: Start here, Control,
                      Columns, Odd values, Learned. Answers already given are
                      kept, and so are the results of the last run.
    run(book)         reads the answers, runs the cube, and writes the results
                      into the same workbook: Where it bleeds, Losses vs revenue,
                      Grids, Split, Materiality, Check, Log.

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
from . import control, engine, meanings, memory, profile, stats
from .ingest import read_table

INK, CANVAS, SLATE, PAPER, NEEDS = "16130F", "F4F1EC", "57534B", "FFFFFF", "FCE4C4"
WORSE_FILL, LUCK_FILL = "F7DEDE", "FFF1D6"
GREEN, RED = "63BE7B", "F8696B"
INPUT_TABS = ("Start here", "Control", "Columns", "Odd values", "Learned")
RESULT_TABS = ("Where it bleeds", "Losses vs revenue", "Grids", "Split", "Three-way", "Materiality", "Check", "Log")
LOG_FIRST = 4            # the newest line on the Log tab
HELPERS = ("_options", "_meanings", "_about")
ABOUT = "_about"
CHART_DATA = "_chart"     # the Losses vs revenue charts' own numbers, hidden
COL_FIRST = 6            # first column row on the Columns tab
CONFIRM_CELL = "C3"      # "Checked every column?"
# Columns tab, one column per thing a person says about an extract column
C_NAME, C_MEANS, C_CUT, C_IS, C_EDGES, C_SHOW, C_SPLIT, C_LOOK, C_WHY, C_BLANK, C_SAMPLES = range(2, 13)
C_SUGG = 13              # hidden: the meaning Set up suggested, so a refusal can name what was changed
SHOW_OPTIONS = ("median", "average")


@dataclass
class Outcome:
    ok: bool
    book: Path
    lines: list[str] = field(default_factory=list)      # what the launcher shows, in plain words


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


def _answers(book: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"control": {}, "columns": {}, "confirmed": None, "odd": {}, "last_used": {}}
    if not book.exists():
        return out
    wb = load_workbook(book)
    if control.SHEET in wb.sheetnames:
        for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
            key = r[control.KEY_COL - 1].value
            if key:
                out["control"][key] = (r[control.CHOOSE_COL - 1].value, r[control.OWN_COL - 1].value)
                if len(r) > control.KEY_COL and r[control.KEY_COL].value:
                    out["last_used"][key] = r[control.KEY_COL].value
    if "Columns" in wb.sheetnames:
        ws = wb["Columns"]
        out["confirmed"] = ws[CONFIRM_CELL].value
        for r in ws.iter_rows(min_row=COL_FIRST, values_only=True):
            if len(r) > C_SPLIT - 1 and r[C_NAME - 1]:
                out["columns"][str(r[C_NAME - 1])] = {
                    "means": r[C_MEANS - 1], "cut": r[C_CUT - 1], "is": r[C_IS - 1], "edges": r[C_EDGES - 1],
                    "show": r[C_SHOW - 1], "split": r[C_SPLIT - 1]}
    if "Odd values" in wb.sheetnames:
        for r in wb["Odd values"].iter_rows(min_row=5, values_only=True):
            if len(r) > 6 and r[1]:
                out["odd"][(str(r[1]), str(r[6]))] = r[4]
    return out


def _to_code(v: Any, cat) -> str | None:
    """A meaning as the Columns tab shows it (a label) or as the code."""
    if v in cat:
        return v
    for code, m in cat.items():
        if v == m.label:
            return code
    return None


# --------------------------------------------------------------------------


def set_up(extract: str | Path, book: str | Path | None = None, memory_path: str | Path | None = None,
           today: date | None = None) -> Outcome:
    extract = Path(extract)
    if extract.name.endswith(" - Origination Cube.xlsx"):
        # the third walk, defect 10: the workbook sits beside the extract and was picked by mistake
        real = extract.name[: -len(" - Origination Cube.xlsx")]
        return Outcome(False, extract, [f"{extract.name} is the workbook, not the loan file. Pick the extract "
                                        f"it was set up from ({real}.csv or {real}.xlsx)."])
    book = Path(book) if book else extract.with_name(f"{extract.stem} - Origination Cube.xlsx")
    try:
        table = read_table(extract)
    except Exception as exc:  # the file itself: shown in words, never a traceback
        return Outcome(False, book, [f"Couldn't read {extract.name}: {exc}"])
    kept = _answers(book)
    mem = memory.load(memory_path)
    sugg = meanings.suggest(table, mem["columns"])
    cat = meanings.catalog()
    method = {s.key: s.recommended().value for s in control.load_settings() if s.recommended()}
    cols = profile.classify(table, int(method["few_values"]), int(method["many_values"]))
    qs = [q for c in cols for q in c.questions]
    open_qs = [q for q in qs if not memory.answer_for(mem, q["column"], q["pattern"], q["value"])]
    looks = meanings.review(table, sugg, open_qs, cat, answer_where="on the Odd values tab")
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
            if t in INPUT_TABS or t in HELPERS:
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
    if kept["last_used"]:
        # what the last Run used stays through Set up again (the sixth walk, defect 6)
        cws = wb[control.SHEET]
        col = control.KEY_COL + 1
        h = cws.cell(row=control.FIRST_ROW - 1, column=col, value="Last Run used")
        h.font = Font(name="Calibri", bold=True, color=PAPER)
        h.fill = PatternFill("solid", fgColor=INK)
        cws.column_dimensions[_col(col)].width = 26
        for r in cws.iter_rows(min_row=control.FIRST_ROW):
            v = kept["last_used"].get(r[control.KEY_COL - 1].value)
            if v:
                c = cws.cell(row=r[0].row, column=col, value=v)
                c.font = Font(name="Calibri", color=SLATE)
                c.alignment = Alignment(wrap_text=True, vertical="top")
        cws.print_area = f"B1:{_col(col)}{cws.max_row}"

    # ---- Columns
    ws = wb.create_sheet("Columns")
    _title(ws, "Columns", "Fix any meaning that's wrong, and set Cut by it to No for anything you don't want in "
                          "the grids. Shaded rows have a reason under Look first. Set C3 to Yes when done; "
                          "confirmed meanings carry over to the next extract.", "B:L")
    ws["B3"] = "Checked every column?"
    ws["B3"].font = Font(name="Calibri", bold=True)
    # new columns since the last check: the Yes no longer covers them (second walk, defect 4)
    ws[CONFIRM_CELL] = kept["confirmed"] if kept["confirmed"] in ("Yes", "No") and not new_cols else None
    dv_yes = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True, showErrorMessage=True)
    ws.add_data_validation(dv_yes)
    dv_yes.add(ws[CONFIRM_CELL])
    ws.conditional_formatting.add(CONFIRM_CELL, FormulaRule(formula=[f'{CONFIRM_CELL}<>"Yes"'],
                                                            fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))
    notes = [rv.says for rv in looks if rv.kind == "cannot run"]
    if new_cols:
        notes.append(f"New since the last check: {', '.join(new_cols)}. Check them, then set C3 to Yes again.")
    if gone_cols:
        notes.append(f"No longer in the extract: {', '.join(gone_cols)}.")
    ws["D3"] = " ".join(notes) or None
    ws["D3"].font = Font(name="Calibri", bold=True, color="960019")
    ws["D3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("D3:L3")
    ws.row_dimensions[3].height = 30 if notes else 16
    _head(ws, 5, ["Column", "What it is", "Cut by it?", "Yes means (outcome only)",
                  "Band edges (620; 680 or every 20)",
                  "Show per pocket", "Split pockets by it?", "Look first", "Why this was suggested", "Blank",
                  "Samples"])
    ws.row_dimensions[5].height = 44
    mm = wb.create_sheet("_meanings")
    for i, (code, m) in enumerate(cat.items(), start=1):
        mm.cell(row=i, column=1, value=m.label)
        mm.cell(row=i, column=2, value=code)
        mm.cell(row=i, column=3, value=m.says)
    mm.sheet_state = "hidden"
    dv_m = DataValidation(type="list", formula1=f"='_meanings'!$A$1:$A${len(cat)}", allow_blank=False,
                          showErrorMessage=True)
    dv_m.error = "Pick one of the meanings in the list."
    dv_cut = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True, showErrorMessage=True)
    dv_show = DataValidation(type="list", formula1='"median,average"', allow_blank=True, showErrorMessage=True)
    dv_split = DataValidation(type="list", formula1='"Yes"', allow_blank=True, showErrorMessage=True)
    dv_split.error = "Type Yes, or leave it blank. Only one column can split the pockets."
    for dv in (dv_m, dv_cut, dv_show, dv_split):
        ws.add_data_validation(dv)
    by_col: dict[str, list[str]] = {}
    for rv in looks:
        if rv.kind != "cannot run":
            by_col.setdefault(rv.column, []).append(rv.says)
    for c in new_cols:
        by_col.setdefault(c, []).insert(0, "New since the last check.")
    classified = {c.name: c for c in cols}
    edge_noted: set[str] = set()
    r = COL_FIRST
    for c in table.columns:
        sg = sugg[c]
        prior = kept["columns"].get(c, {})
        code = _to_code(prior.get("means"), cat) or sg.means
        tag = "Remembered: " if sg.source == "remembered" else ""
        f = meanings.facts(table, c)
        blank = (f.rows - f.nonblank) / f.rows if f.rows else 0
        ws.cell(row=r, column=C_NAME, value=c).font = Font(name="Calibri", bold=True)
        ws.cell(row=r, column=C_MEANS, value=cat[code].label)
        dv_m.add(ws.cell(row=r, column=C_MEANS))
        cuttable = cat[code].cut != "none"
        ws.cell(row=r, column=C_CUT, value=(prior.get("cut") or "Yes") if cuttable else None)
        dv_cut.add(ws.cell(row=r, column=C_CUT))
        ws.cell(row=r, column=C_IS, value=prior.get("is") if prior else sg.is_value)
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
        ws.cell(row=r, column=C_SHOW, value=prior.get("show"))
        dv_show.add(ws.cell(row=r, column=C_SHOW))
        ws.cell(row=r, column=C_SPLIT, value=prior.get("split"))
        dv_split.add(ws.cell(row=r, column=C_SPLIT))
        ws.cell(row=r, column=C_LOOK, value=" ".join(by_col.get(c, [])) or None)  # after the edges note
        ws.cell(row=r, column=C_WHY, value=tag + sg.why)
        ws.cell(row=r, column=C_BLANK, value=blank).number_format = "0%"
        ws.cell(row=r, column=C_SAMPLES, value=", ".join(classified[c].samples[:3]) if c in classified else "")
        ws.cell(row=r, column=C_SUGG, value=sg.means)
        for col in range(C_NAME, C_SAMPLES + 1):
            ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top", indent=1 if col in (
                C_BLANK, C_SAMPLES) else 0, horizontal="center" if col == C_BLANK else None)
        r += 1
    look = _col(C_LOOK)
    ws.conditional_formatting.add(f"{look}{COL_FIRST}:{look}{r}", FormulaRule(
        formula=[f'{look}{COL_FIRST}<>""'], fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))
    for col, w in zip("ABCDEFGHIJKL", (2, 22, 20, 9, 13, 16, 11, 11, 44, 40, 8, 30)):
        ws.column_dimensions[col].width = w
    ws.column_dimensions[_col(C_SUGG)].hidden = True
    ws.freeze_panes = f"C{COL_FIRST}"
    _fit(ws)

    # ---- Odd values
    wo = wb.create_sheet("Odd values")
    _title(wo, "Odd values", "Values that might be codes rather than real numbers. Answer real or missing (missing "
                             "is treated as blank and counted). Unanswered ones are used as is.", "B:G")
    _head(wo, 4, ["Column", "What looks odd", "Rows", "Answer", "Note"])
    dv_a = DataValidation(type="list", formula1='"real,missing"', allow_blank=True, showErrorMessage=True)
    wo.add_data_validation(dv_a)
    r = 5
    odd_open = 0
    for q in qs:
        key = (q["column"], f"{q['pattern']}|{q['value'] if q['value'] is not None else ''}")
        known = memory.answer_for(mem, q["column"], q["pattern"], q["value"])
        answer = kept["odd"].get(key) or (known["answer"] if known else None)
        what = ("negative values in a column that is mostly positive" if q["pattern"] == "negatives"
                else f"the value {q['value']:g} repeated far more than any other")
        wo.cell(row=r, column=2, value=q["column"])
        wo.cell(row=r, column=3, value=what)
        wo.cell(row=r, column=4, value=q["rows"]).number_format = "#,##0"
        wo.cell(row=r, column=5, value=answer)
        odd_open += not answer
        dv_a.add(wo.cell(row=r, column=5))
        wo.cell(row=r, column=6, value=f"Remembered: answered {known['answer']} on {known.get('last')}"
                if known else None)
        wo.cell(row=r, column=7, value=key[1])          # hidden: how the answer is matched
        r += 1
    if r == 5:
        wo.cell(row=5, column=2, value="Nothing odd found.")
    else:
        wo.conditional_formatting.add(f"E5:E{r - 1}", FormulaRule(
            formula=['E5=""'], fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))
    for col, w in zip("ABCDEFG", (2, 22, 50, 10, 12, 44, 10)):
        wo.column_dimensions[col].width = w
    wo.column_dimensions["G"].hidden = True
    _fit(wo)

    _learned_tab(wb, memory_path)

    about = wb.create_sheet(ABOUT)
    about["A1"], about["B1"] = "extract", str(extract.resolve())
    about["A2"], about["B2"] = "sha256", hashlib.sha256(extract.read_bytes()).hexdigest()
    about["A3"], about["B3"] = "set up", (today or date.today()).isoformat()
    about["A4"], about["B4"] = "extract name", extract.name
    about.sheet_state = "hidden"
    unanswered = sum(1 for s in control.load_settings() if s.judgment
                     and not any(v not in (None, "n/a") for v in kept["control"].get(s.key, (None, None))))
    last = None
    if "Log" in wb.sheetnames:
        lg = wb["Log"]
        top = LOG_FIRST if lg["A1"].value == "Log" else 1
        if lg.cell(row=top, column=1).value:
            last = f"{lg.cell(row=top, column=1).value}: {lg.cell(row=top, column=2).value}"
    _start_here(start, extract, len(table.rows), len(table.columns), looks, len(qs), unanswered, last)
    _order(wb)
    try:
        wb.save(book)
    except PermissionError:
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Set up again."])
    lines = [f"Set up {book.name} from {extract.name}: {len(table.rows):,} loans, {_n(len(table.columns), 'column')}."]
    if new_cols:
        lines.append(f"New columns since the last check: {', '.join(new_cols)}. Columns!C3 needs a Yes again.")
    nlook = len({rv.column for rv in looks if rv.kind != "cannot run"} | set(new_cols) | edge_noted)
    if nlook:
        lines.append(f"{_n(nlook, 'column')} to look at first, on the Columns tab.")
    left = []
    if unanswered:
        left.append("Control")
    if ws[CONFIRM_CELL].value != "Yes":
        left.append("Columns")
    if odd_open:
        left.append("Odd values")
    # the second walk, defect 15: this line said the same thing with nothing left to fill
    joined = ", ".join(left[:-1]) + (" and " if len(left) > 1 else "") + left[-1] if left else ""
    lines.append(f"Next: fill in the shaded cells on {joined}, save, close, and press Run." if left
                 else "Everything is answered. Press Run the cube.")
    return Outcome(True, book, lines)


def _learned_tab(wb, memory_path) -> None:
    if "Learned" in wb.sheetnames:
        del wb["Learned"]
    ws = wb.create_sheet("Learned")
    _title(ws, "Learned", "Meanings and answers carried over from past runs. Set a row to Forget to drop it on the "
                          "next Run, and the column waits on Columns for you to confirm it again.", "A:G")
    heads = ["Keep?", "Kind", "Column", "What it learned", "First confirmed", "Last confirmed", "Times", "id"]
    for i, h in enumerate(heads, start=1):
        c = ws.cell(row=3, column=i, value=h)
        c.font = Font(name="Calibri", bold=True, color=PAPER)
        c.fill = PatternFill("solid", fgColor=INK)
    dv = DataValidation(type="list", formula1=f'"{memory.KEEP},{memory.FORGET}"', allow_blank=False)
    ws.add_data_validation(dv)
    rows = memory.rows(memory.load(memory_path))
    cat = meanings.catalog()
    for rw in rows:
        learned = rw["learned"]
        if rw["kind"] == "column":
            code = learned.split(" ")[0]
            learned = learned.replace(code, cat[code].label, 1) if code in cat else learned
        ws.append([memory.KEEP, rw["kind"], rw["column"], learned, rw["first"], rw["last"], rw["times"], rw["id"]])
        dv.add(ws.cell(row=ws.max_row, column=1))
    if not rows:
        ws.cell(row=4, column=3, value="Nothing learned yet.")
    for col, w in zip("ABCDEFGH", (9, 9, 22, 44, 15, 15, 7, 30)):
        ws.column_dimensions[col].width = w
    ws.column_dimensions["H"].hidden = True
    _fit(ws)


def _start_here(ws, extract, rows, ncols, looks, nq, unanswered, last_run) -> None:
    for rng in list(ws.merged_cells.ranges):
        ws.unmerge_cells(str(rng))
    for row in ws.iter_rows():
        for c in row:
            c.value = None
    _title(ws, "Origination Cube", f"Set up from {Path(extract).name}: {rows:,} loans, {ncols} columns.", "B:D")
    steps = [
        ("1", "Control", "Fill in the shaded cells: materiality, minimum loans, how much worse counts."),
        ("2", "Columns", "Check each column's meaning and whether to cut by it. Set C3 to Yes when done."),
        ("3", "Odd values", "Answer real or missing. Unanswered ones are used as is."),
        ("4", "Launcher", "Save and close this workbook, then press Run the cube."),
    ]
    _head(ws, 4, ["Step", "Where", "What to do"])
    for i, (n, where, what) in enumerate(steps, start=5):
        ws.cell(row=i, column=2, value=n)
        ws.cell(row=i, column=3, value=where).font = Font(name="Calibri", bold=True)
        ws.cell(row=i, column=4, value=what).alignment = Alignment(wrap_text=True, vertical="top")
    ws["B11"] = "Where things stand"
    ws["B11"].font = Font(name="Calibri", bold=True, size=12)
    _status(ws, unanswered, len(looks), nq, last_run)
    for col, w in zip("ABCD", (2, 7, 38, 90)):
        ws.column_dimensions[col].width = w
    _fit(ws)


def _status(ws, unanswered, nlooks, nq, last_run) -> None:
    status = [("Calls still to make on Control", unanswered), ("Things to look at first on Columns", nlooks),
              ("Odd values found", nq), ("Last run", last_run or "not run yet")]
    for i, (k, v) in enumerate(status, start=12):
        ws.cell(row=i, column=3, value=k)
        ws.cell(row=i, column=4, value=v).alignment = Alignment(horizontal="left")


# --------------------------------------------------------------------------


def read_book(book: Path, memory_path=None) -> tuple[dict | None, list[str], dict]:
    """The cube file a workbook describes, as a dict, and every problem in it
    named by tab and cell. Nothing is run."""
    problems: list[str] = []
    wb = load_workbook(book)
    missing_tabs = [t for t in ("Control", "Columns", "Odd values", ABOUT) if t not in wb.sheetnames]
    if missing_tabs:
        return None, [f"This workbook is missing its {', '.join(missing_tabs)} tab. Press Set up again."], {}
    about = {wb[ABOUT][f"A{i}"].value: wb[ABOUT][f"B{i}"].value for i in range(1, 5)}
    try:
        use = control.read_control(book)
    except control.ControlError as exc:
        problems += exc.problems
        use = {}
    cat = meanings.catalog()
    ws = wb["Columns"]
    if ws[CONFIRM_CELL].value != "Yes":
        note = str(ws["D3"].value or "")
        problems.append(f"Columns!{CONFIRM_CELL}: set Checked every column to Yes once you've checked each "
                        f"column's meaning." + (f" {note}" if note.startswith("Forgotten") else ""))
    columns, edges, skip, show, split = {}, {}, set(), {}, []
    widths: dict[str, float] = {}
    typed: dict[str, str] = {}
    edge_cells: dict[str, str] = {}
    for r in ws.iter_rows(min_row=COL_FIRST):
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
        columns[name] = {"means": code, "is": is_value} if is_value not in (None, "") else code
        if r[C_CUT - 1].value == "No":
            skip.add(name)
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
        if r[C_SPLIT - 1].value == "Yes":
            if cat[code].cut in ("band", "dimension"):
                split.append((name, code, row))
            else:
                # the third walk, defect 7: GCO split by itself read 93.83x; the key "had too few loans"
                problems.append(f'Columns!{_col(C_SPLIT)}{row}: "{name}" is marked {cat[code].label}, which '
                                f"can't split the pockets. Only a score, ratio, amount (the booked amount too) or "
                                f"category can.")
    if len(split) > 1:
        cells = " and ".join(f"Columns!{_col(C_SPLIT)}{row}" for _, _, row in split)
        problems.append(f"{cells}: only one column can split the pockets. Clear all but one.")
    questions = []
    for r in wb["Odd values"].iter_rows(min_row=5, values_only=True):
        if len(r) < 7 or not r[1] or not r[6]:
            continue
        pattern, _, value = str(r[6]).partition("|")
        questions.append({"column": r[1], "pattern": pattern, "value": float(value) if value else None,
                          "rows": r[3] or 0, "answer": r[4] or None})
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
        "min_age_months": int(use["min_age_months"]),
        "benchmark": {"min_units": _num_or(use["min_loans"], 30, int), "min_events": int(use["min_events"]),
                      "worse_at": _num_or(use["worse_at"], 1.25, float),
                      "better_at": _num_or(use["better_at"], 0.8, float),
                      "confidence": float(use["confidence"]), "power": float(use["power"]),
                      "compare_to": use["compare_to"], "many_tests": use["many_tests"],
                      "materiality": use["materiality"], "revenue_line": use["revenue_line"]},
        "questions": questions or [],
    }
    if split:
        name, code, _ = split[0]
        raw["split"] = {"field": name, "how": "each_value" if cat[code].cut == "dimension" else "own_median"}
    about = dict(about)
    about["_widths"] = {c: w for c, w in widths.items() if c not in skip}
    about["_typed_edges"] = typed
    about["_edge_cells"] = edge_cells
    about["_suggest"] = {k for k in ("min_loans", "worse_at", "better_at") if use.get(k) in ("calc", "luck")}
    return raw, [], about


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
    worse_at / better_at: the smallest outcome gap a typical pocket can tell from
    luck (the median over pockets big enough to test), and one over it."""
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


def run(book: str | Path, extract: str | Path | None = None, memory_path: str | Path | None = None) -> Outcome:
    """Run from the workbook. `extract` is the file picked in the launcher; it
    wins over the path remembered at set up, so a workbook copied to another
    folder runs that folder's extract (second walk, defect 1)."""
    book = Path(book)
    if not book.exists():
        return Outcome(False, book, [f"Couldn't find {book.name}. Press Set up first."])
    if not _writable(book):
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Run again."])
    raw, problems, about = read_book(book, memory_path)
    if raw is not None:
        try:
            cfg = cfgmod.parse(raw)
        except cfgmod.ConfigError as exc:
            problems = [_plain(p) + _changed_away(book, p) for p in exc.problems]
    if problems:
        _log(book, ["Couldn't run. Fix these, save, close, and press Run again:"] + problems)
        return Outcome(False, book, ["Couldn't run yet. Fix these in the workbook, save, close, and press Run "
                                     "again:"] + [f"  - {p}" for p in problems])
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
    far += _edges_outside(book, raw, cfg, table)
    if far:
        _log(book, ["Couldn't run. Fix these, save, close, and press Run again:"] + far)
        return Outcome(False, book, ["Couldn't run yet. Fix these in the workbook, save, close, and press Run "
                                     "again:"] + [f"  - {p}" for p in far])
    suggested: dict[str, float] = {}
    try:
        res = engine.run(cfg, table)
        if about.get("_suggest"):
            # a suggested answer is worked out from a first pass, then the run is done again with it
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
        res.suggested = suggested
    except (engine.ColumnsMissing, engine.NothingToCut) as exc:
        msg = re.sub(r"used by dimension \w+", "a segment", re.sub(r"used by band \w+", "a band", str(exc)))
        msg = msg.replace("`", '"')
        if isinstance(exc, engine.ColumnsMissing):
            # the third walk, defect 15: a renamed column needs Set up, and the message didn't say so
            msg += ". If a column was renamed or dropped, press Set up again."
        _log(book, ["Couldn't run:", msg])
        return Outcome(False, book, [f"Couldn't run: {msg}"])
    forgotten = memory.apply_review(book, memory_path)[1]
    dropped = {g.split(" ", 1)[1] for g in forgotten if g.startswith("column ")}
    if dropped:
        # a Forget means "don't carry this over"; this run does not re-teach it (second walk, defect 5)
        cfg = cfgmod.Config(**{**cfg.__dict__, "columns": {k: v for k, v in cfg.columns.items() if k not in dropped}})
    memory.remember(cfg, memory_path)
    typed = about.get("_typed_edges") or {}
    cat = meanings.catalog()
    bands_only = {c for c, v in (cfg.columns or {}).items() if cat.get(v[0]) and cat[v[0]].cut == "band"}
    memory.remember_edges({c: typed.get(c) for c in bands_only if c not in dropped}, memory_path)
    try:
        _write_results(book, res, memory_path, src, dropped)
    except PermissionError:
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Run again."])
    audit = book.with_name(f"{book.stem} - what ran.yaml")
    head = "# Exactly what the last Run used.\n"
    if per_pocket(res):
        head += "# revenue_line: each pocket's own luck range (its own test)\n"
    audit.write_text(head + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    lines = notes + [f"Ran on {res.rows:,} loans from {src.name}; {res.tie_outs:,} tie-out checks agree."]
    lines += _top_lines(res)
    small = sum(1 for g in res.grids for _, c in g.inner() for m in res.measures if m.is_rate
                and c.rates[m.name].material and c.rates[m.name].reading_topline in (engine.THIN, engine.FEW))
    if small:
        lines.append(f"{_n(small, 'pocket')} {'is' if small == 1 else 'are'} material but too small to test: "
                     f"shaded blue on Where it bleeds, to look at by hand.")
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
        lines.append(f"Forgot {', '.join(sorted(dropped))}, as marked on Learned. Check "
                     f"{'it' if len(dropped) == 1 else 'them'} on Columns and set C3 to Yes before the next Run.")
    lines.append(f"Open {book.name}: start with Where it bleeds.")
    return Outcome(True, book, lines)


def _edges_outside(book: Path, raw: dict, cfg, table) -> list[str]:
    """Own band edges that sit outside the column's values make an empty band,
    or one band holding everything (the second walk, defect 2: an edge of
    620,680,740 put every FICO in one band). Each is named by its cell."""
    rows = {}
    for r in load_workbook(book)["Columns"].iter_rows(min_row=COL_FIRST):
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
                                             "category (or term) on the Columns tab, with Cut by it set to Yes.",
    "`bands:` needs at least one entry": "Nothing is left to cut into bands: mark at least one number column as "
                                        "a score, ratio or amount on the Columns tab, with Cut by it set to Yes.",
}


def _changed_away(book: Path, problem: str) -> str:
    """When nothing is left to cut, name the columns that were suggested as
    one and aren't cut now (the second walk, defect 15: the message didn't say
    which change caused it)."""
    kind = {"`dimensions:` needs at least one entry": "dimension",
            "`bands:` needs at least one entry": "band"}.get(problem)
    if not kind:
        return ""
    cat = meanings.catalog()
    out = []
    for r in load_workbook(book)["Columns"].iter_rows(min_row=COL_FIRST):
        name, sugg = r[C_NAME - 1].value, r[C_SUGG - 1].value if len(r) >= C_SUGG else None
        if not name or sugg not in cat or cat[sugg].cut != kind:
            continue
        now = _to_code(r[C_MEANS - 1].value, cat)
        if now != sugg:
            out.append(f"{name} (Columns!{_col(C_MEANS)}{r[0].row}, now {cat[now].label if now else 'blank'})")
        elif r[C_SPLIT - 1].value == "Yes":
            out.append(f"{name} (Columns!{_col(C_SPLIT)}{r[0].row}: it splits the pockets, so it isn't a "
                       f"{'segment' if kind == 'dimension' else 'band'} of its own)")
        elif r[C_CUT - 1].value == "No":
            out.append(f"{name} (Columns!{_col(C_CUT)}{r[0].row}, Cut by it? No)")
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
                if s.excess and s.excess > 0 and s.flag == engine.WORSE and s.material is not False:
                    if best is None or s.excess > best[0]:
                        best = (s.excess, f"{names[g.band]} {b} / {names[g.dimension]} {d}")
        tested = any(c.rates[m.name].reading_topline not in (engine.THIN, engine.FEW, None)
                     for g in res.grids for _, c in g.inner())
        if best:
            out.append(f"Worst for {m.title}: {best[1]}.")
        elif not tested:
            floor = res.config.benchmark.min_units if res.config.benchmark else 0
            out.append(f"No pocket had enough loans or losses to test {m.title} (fewest loans: {floor:,}).")
        else:
            out.append(f"Nothing is worse for {m.title} at these settings.")
    return out


# --------------------------------------------------------------------------
# Results


def _log(book: Path, lines: list[str]) -> None:
    try:
        wb = load_workbook(book)
    except Exception:
        return
    ws = wb["Log"] if "Log" in wb.sheetnames else wb.create_sheet("Log")
    if ws["A1"].value != "Log":
        # a heading like every other tab, and the newest run first under it (second walk, defect 16)
        if ws.max_row > 1 or ws["A1"].value:
            ws.insert_rows(1, amount=LOG_FIRST - 1)
        _title(ws, "Log", "Every Run and every refusal, newest first.", "A:B")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.insert_rows(LOG_FIRST, amount=len(lines) + 1)
    for i, line in enumerate(lines):
        ws.cell(row=LOG_FIRST + i, column=1, value=stamp if i == 0 else None).alignment = Alignment(vertical="top")
        ws.cell(row=LOG_FIRST + i, column=2, value=line).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 17
    ws.column_dimensions["B"].width = 100
    _fit(ws, landscape=False)
    if "Start here" in wb.sheetnames:
        wb["Start here"]["D15"] = (f"{stamp}: couldn't run; see the Log tab" if "Couldn't" in lines[0]
                                   else f"{stamp}: {lines[0]}")
    _order(wb)
    try:
        wb.save(book)
    except PermissionError:
        pass


def _write_results(book: Path, res, memory_path, src: Path, forgotten: set[str] | None = None) -> None:
    wb = load_workbook(book)
    for t in RESULT_TABS[:-1]:
        if t in wb.sheetnames:
            del wb[t]
    _learned_tab(wb, memory_path)
    _bleeds(wb.create_sheet("Where it bleeds"), res)
    _losses_vs_revenue(wb.create_sheet("Losses vs revenue"), res)
    _grids(wb.create_sheet("Grids"), res)
    if res.config.split:
        _split_tab(wb.create_sheet("Split"), res)
        note = (lambda g: _three_way_note(res, g)) if res.config.split[1] == "own_median" else None
        pt = _partner(res)
        sf = res.config.split[0]
        after = (f" {sf} moves with {pt[0]} (correlation {pt[1]:+.2f}). Rows whose grid doesn't hold {pt[0]} fixed "
                 f"(the last column says no) come after the rest, and part of their gap may be {pt[0]}."
                 if note and pt else "")
        _bleeds(wb.create_sheet("Three-way"), res, res.three_way, "Three-way",
                f"Pockets split by {sf}, each tested like any other pocket,", note, after)
    _materiality_tab(wb.create_sheet("Materiality"), res)
    _check(wb.create_sheet("Check"), res, src, f"{book.stem} - what ran.yaml")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if control.SHEET in wb.sheetnames:
        _last_run_used(wb[control.SHEET], res)
    if forgotten and "Columns" in wb.sheetnames:
        # a Forget holds until a person confirms the column again (the third walk, defect 9:
        # the next Run re-learned it from Columns, which still said Yes)
        cols = wb["Columns"]
        cols[CONFIRM_CELL] = None
        cols["D3"] = (f"Forgotten on Learned: {', '.join(sorted(forgotten))}. Check what "
                      f"{'it is' if len(forgotten) == 1 else 'they are'}, then set C3 to Yes again.")
        for row in cols.iter_rows(min_row=COL_FIRST):
            if row[C_NAME - 1].value in forgotten:
                row[C_LOOK - 1].value = "Forgotten on Learned: confirm what it is."
                why = str(row[C_WHY - 1].value or "")
                if why.startswith("Remembered"):
                    row[C_WHY - 1].value = "Forgotten on Learned; it was remembered before."
    if "Start here" in wb.sheetnames:
        # the second walk, defect 9, and the third walk, defect 15: the counts went stale after a run
        sh = wb["Start here"]
        # a run only happens with every column confirmed, so what's left to look at is what a Forget marked
        looks = len(forgotten or ())
        _status(sh, 0, looks, sh["D14"].value, stamp)
        sh["B2"] = f"Last run on {res.rows:,} loans from {src.name}."
    _order(wb)
    wb.save(book)
    _log(book, [f"Ran on {res.rows:,} loans from {src.name}; {res.tie_outs:,} tie-out checks agree."] +
         [f"Warning: {_plain_warning(w)}" for w in res.warnings])


def _last_run_used(ws, res) -> None:
    """Beside every Control answer, what the last Run used, with a suggested
    option's worked-out number (the fifth walk: a suggestion showed no number
    anywhere on Control)."""
    col = control.KEY_COL + 1
    h = ws.cell(row=control.FIRST_ROW - 1, column=col, value="Last Run used")
    h.font = Font(name="Calibri", bold=True, color=PAPER)
    h.fill = PatternFill("solid", fgColor=INK)
    h.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions[_col(col)].width = 26
    ws.print_area = f"B1:{_col(col)}{ws.max_row}"          # on the page (the sixth walk, defect 6)
    by_q = dict(control.describe(_settings_of(res.config)))
    sug = getattr(res, "suggested", None) or {}
    rl = revenue_lines(res)
    for row in ws.iter_rows(min_row=control.FIRST_ROW):
        key = row[control.KEY_COL - 1].value
        s = next((x for x in control.load_settings() if x.key == key), None)
        if s is None:
            continue
        words = by_q.get(s.question)
        fb = getattr(res, "suggest_fallback", set())
        if key == "revenue_line" and rl:
            words = "each pocket's own luck range" if per_pocket(res) else f"{rl[1]:.2f}x and {rl[0]:.2f}x"
        elif key in fb:
            words = f"{words} (the usual value: nothing in this book to work it out from)"
        elif key in sug:
            words = f"{words} (worked out from this book)"
        c = ws.cell(row=row[0].row, column=col, value=words)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = Font(name="Calibri", color=SLATE)


def _unit(m) -> str:
    if m.mode == "flagwt" and m.per == engine.EACH_LOAN:
        return "loans"
    if m.mode == "flagwt":
        return f"{m.per} dollars"
    return f"{m.value} dollars"


def _amount(v: float, m) -> str:
    """A line in its unit. Loans to one decimal: a line of 2.3 shown as 2 put a
    pocket whose excess also showed as 2 either side of it (second walk, defect 7)."""
    return f"{v:,.1f} loans" if _unit(m) == "loans" else f"{v:,.0f} {_unit(m)}"


def _plain_warning(w: str) -> str:
    """An engine warning in workbook terms: nobody at the desk sees the cube file."""
    return (w.replace("(real, or missing) in `questions:`", "real or missing on the Odd values tab")
            .replace("`", '"'))


def _bleeds(ws, res, grids=None, title: str = "Where it bleeds", lead: str = "Pockets", note_of=None,
            after: str = "") -> None:
    """Every pocket losing more than its share, largest first. The Three-way tab
    is the same list over the three-way pockets, with what each grid holds fixed
    beside every row, and the grids that hold it fixed first (`note_of` gives the
    words and the order; the fourth walk, defect 1)."""
    grids = res.grids if grids is None else grids
    b = res.config.benchmark
    judged = "the rest of its band" if b and b.compare_to == "peers" else "the rest of the book"
    names = _names(res)
    _title(ws, title, f"{lead} losing more than their share (RANR: earning less), largest first. The "
                      f"flag compares each pocket with {judged}. Red: worse. Amber: worse, but could be "
                      f"luck. Blue: material, but too few loans or losses to test, so worth a look by hand. "
                      f"\"Luck alone\" is how often a gap this big turns up with no real "
                      f"difference behind it, after the allowance for testing many pockets within each grid "
                      f"(see Check).{after}", "B:S" if note_of else "B:R")
    heads = ["Measure", "Band column", "Band", "Segment column", "Segment", "Loans", "Rate", "Book rate", "Excess",
             "Excess is in", "Material", "Vs rest of book", "Luck alone", "Vs rest of band", "Luck alone",
             f"Flag (vs {judged})", "Smallest gap it could show"] + (
                [f"Holds {_partner(res)[0]} fixed?" if _partner(res) else "Holds fixed?"] if note_of else [])
    _head(ws, 4, heads)
    r = 5
    untested = (engine.THIN, engine.FEW)
    for m in res.measures:
        if not m.is_rate:
            continue
        found = []
        for g in grids:
            for (bl, dl), c in g.inner():
                s = c.rates[m.name]
                if s.excess is not None and s.excess > 0:
                    found.append((s.excess, g, bl, dl, s))
        order = (lambda t: (note_of(t[1])[1], -t[0])) if note_of else (lambda t: -t[0])
        for ex, g, bl, dl, s in sorted(found, key=order):
            tested = s.reading_topline not in untested
            gap = s.smallest_gap if m.higher_is == "worse" else (1 / s.smallest_gap if s.smallest_gap else None)
            vals = [m.title, names[g.band], bl, names[g.dimension], dl, s.units, s.rate,
                    res.total.rates[m.name].rate, ex, _unit(m),
                    {True: "yes", False: "below the line", None: ""}[s.material], s.vs_rest,
                    s.p_book if tested else None, s.vs_band, s.p_band if tested else None, s.flag or "", gap]
            if note_of:
                vals.append(note_of(g)[0])
            for i, v in enumerate(vals, start=2):
                ws.cell(row=r, column=i, value=v)
            # loans to one decimal, like the line they're held against (the third walk, defect 13)
            ex_fmt = "#,##0.0" if _unit(m) == "loans" else "#,##0"
            for col, fmt in ((8, "0.00%"), (9, "0.00%"), (10, ex_fmt), (13, '0.00"x"'), (14, P_FMT),
                             (15, '0.00"x"'), (16, P_FMT)):
                ws.cell(row=r, column=col).number_format = fmt
            ws.cell(row=r, column=18).number_format = ('0.00"x or more"' if m.higher_is == "worse"
                                                       else '0.00"x or less"')
            r += 1
    if r == 5:
        ws.cell(row=5, column=2, value="Nothing is losing more than its share at these settings.")
    # material but too small to test: shown, not hidden (the firm, 25 Sep 2026: "this is a materiality thing")
    for formula, fill in (('$Q5="worse"', WORSE_FILL), ('$Q5="worse, but could be luck"', LUCK_FILL),
                          ('AND($L5="yes",LEFT($Q5,7)="too few")', SMALL_FILL)):
        ws.conditional_formatting.add(f"B5:R{max(r, 6)}", FormulaRule(formula=[formula], fill=PatternFill(
            "solid", fgColor=fill, bgColor=fill)))
    seg_w = 26 if grids is not res.grids else 13
    for col, w in zip("ABCDEFGHIJKLMNOPQR", (2, 28, 12, 22, 16 if seg_w == 13 else 26, seg_w, 8, 8, 8, 12, 16, 14,
                                             11, 11, 11, 11, 22, 15)):
        ws.column_dimensions[col].width = w
    if note_of:
        ws.column_dimensions["S"].width = 30
        ws.row_dimensions[2].height = 58
        for row in ws.iter_rows(min_row=5, min_col=19, max_col=19):
            row[0].alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B5"
    _fit(ws)


P_FMT = '[<0.0001]"under 0.01%";[<0.01]0.00%;0.0%'
LUCK = "How often luck alone gives a gap this big"

# Nine boxes, worst first. Each side reads more, about the same, or less, by the
# lines on Control (ruling OC-26; the third walk, defect 1: by 1.00x alone, the
# three worst bleeders read "earning more" on revenue their own flags called noise).
# The tab no longer prints the box (the firm: "i can just visually see that"); it
# still orders the rows and picks the pockets the chart names.
BOXES = ("Losing more, earning less", "Losing more, earning the same", "Losing the same, earning less",
         "Losing more, earning more", "Losing less, earning less", "About the same on both",
         "Losing the same, earning more", "Losing less, earning the same", "Losing less, earning more")
NOT_TESTED = "Not tested: too few loans or losses"
SMALL_FILL = "DDEBF7"      # material, but too few loans or losses to test: look at it by hand
WARN_TEXT = "960019"


def box_of(gco: str, ranr: str) -> str:
    """gco and ranr are each "more", "same" or "less"."""
    g = {"more": "Losing more", "same": "Losing the same", "less": "Losing less"}[gco]
    r = {"more": "earning more", "same": "earning the same", "less": "earning less"}[ranr]
    return "About the same on both" if gco == ranr == "same" else f"{g}, {r}"


def revenue_lines(res) -> tuple[float, float, str] | None:
    """The two multiples revenue must pass to count as less or more, and where
    they came from, in words."""
    b = res.config.benchmark
    if b is None:
        return None
    rl = b.revenue_line
    if rl is None or rl == "losses":
        return 1 / b.worse_at, 1 / b.better_at, "the same lines as for losses"
    if rl == "luck":
        # each pocket's own: past what luck alone can move THAT pocket, by its own test (the firm, 25 Sep
        # 2026, after the sixth walk: one number for every pocket let a 176-loan pocket cross on noise)
        return 1.0, 1.0, f"past what luck alone can move that pocket (its own test, at {b.confidence:.0%} sure)"
    return 1 - rl, 1 + rl, f"{rl:.0%} either way"


def per_pocket(res) -> bool:
    b = res.config.benchmark
    return bool(b and b.revenue_line == "luck")


def luck_gap(res, mname: str, floor: float) -> float | None:
    """The gap luck alone can make in a pocket of typical size: for each pocket
    big enough to test, the multiple its test would call real at the Control
    confidence, and the median of those. The catch rate is left out on purpose
    (the fourth walk, defect 4: at 80% caught it was the gap a pocket can find,
    1.25x, not what luck alone moves, about 1.17x)."""
    b = res.config.benchmark
    ln = res.loans_needed.get(mname)
    if b is None or ln is None:
        return None
    gaps = []
    for g in res.grids:
        for _, c in g.inner():
            s = c.rates[mname]
            if s.units >= floor:
                x = stats.smallest_gap(s.units, ln.rate, ln.s_d, ln.x_bar, b.confidence, 0.5)
                if x:
                    gaps.append(x)
    return round(statistics.median(gaps), 2) if gaps else None


def _over(s, parent) -> float:
    """A pocket's numerator over what it would be at the rate of the rest of its
    comparison (the parent less the pocket)."""
    rest_num, rest_den = parent.num - s.num, parent.den - s.den
    if not rest_den:
        return 0.0
    return s.num - rest_num / rest_den * s.den


def _side(idx, lo: float, hi: float) -> str | None:
    if idx is None:
        return None
    return "more" if idx >= hi else "less" if idx <= lo else "same"


RED_CELL, GREEN_CELL = "F2C4C4", "CFE8C4"
# the tab's columns, one side after the other (the firm, 25 Sep 2026: "instead of just listing GCO vs
# Comparison, find a clean way to display the comparable metrics")
LVR_G, LVR_R = 5, 10                 # first column of the GCO side and of the RANR side
LVR_SIDE = ("This pocket", "{rest}", "Multiple", "Reading", "Over the rest ($)")


def _rest_rate(s, parent) -> float | None:
    den = parent.den - s.den
    return (parent.num - s.num) / den if den else None


def _losses_vs_revenue(ws, res) -> None:
    """GCO and RANR side by side, per pocket. The firm: 'GCO is high but profit
    is high - do we care? maybe.' Each side shows the pocket's rate, the rate of
    the rest it's compared with, the multiple, a reading and the dollars, so the
    numbers behind a reading are on the row. A reading says more, about the same
    or less by the lines on Control; red and green show which side is worse or
    better, and the pair shows the trade-off without naming it (the firm, 25 Sep
    2026: "i don't think that which box is a relevant thing to need, i can just
    visually see that"). Nothing is netted: RANR already includes credit losses
    (OC-29). The dollars use the same comparison as the reading (the third walk,
    defect 5)."""
    names = _names(res)
    b = res.config.benchmark
    if b is None or "gco_rate" not in {m.name for m in res.measures}:
        _title(ws, "Losses vs revenue", "Needs the Control settings.", "B:N")
        return
    peers = b.compare_to == "peers"
    rest = "Rest of band" if peers else "Rest of book"
    judged = "the rest of its band" if peers else "the rest of the book"
    rlo, rhi, rwhy = revenue_lines(res)
    own = per_pocket(res)
    rev_words = (f"Revenue counts as more or less only when it's {rwhy}." if own else
                 f"Revenue counts as more at {rhi:.2f}x or above and less at {rlo:.2f}x or below ({rwhy}).")
    _title(ws, "Losses vs revenue", f"Each pocket's losses (GCO) and revenue (RANR) beside {judged}. "
                                    f"GCO counts as more at {b.worse_at:.2f}x or above and less at "
                                    f"{b.better_at:.2f}x or below. {rev_words} Both are set on Control. Red is "
                                    f"worse, green is better; a gap its own test says could be luck is marked and "
                                    f"left plain. RANR already includes credit losses, so nothing is netted.", "B:N")
    ws.row_dimensions[2].height = 44
    side_heads = [h.format(rest=rest) for h in LVR_SIDE]
    floor = b.min_units
    # the charts' own numbers (the Control lines, the named pockets) live on a hidden sheet:
    # hidden cells on this tab aren't drawn by every spreadsheet program
    wb = ws.parent
    if CHART_DATA in wb.sheetnames:
        del wb[CHART_DATA]
    hs = wb.create_sheet(CHART_DATA)
    hs.sheet_state = "hidden"
    top = 4
    for gi, g in enumerate(res.grids):
        rows = []
        for (bl, dl), c in g.inner():
            gs, rs = c.rates["gco_rate"], c.rates["ranr_rate"]
            gidx, ridx = (gs.vs_band, rs.vs_band) if peers else (gs.vs_rest, rs.vs_rest)
            if gs.units < floor or gidx is None or ridx is None:
                continue
            # the lines on Control decide each side; a side whose own test says the gap could be luck
            # keeps its reading and says so (the firm, 25 Sep 2026, after the fifth walk found a luck
            # gate made the lines decide nothing)
            real = lambda p: p is not None and p < 1 - b.confidence      # noqa: E731
            gp, rp = (gs.p_band, rs.p_band) if peers else (gs.p_book, rs.p_book)
            gside = _side(gidx, b.better_at, b.worse_at)
            # the suggested revenue option is each pocket's own luck range: a side only moves when its test
            # says so, and there's nothing left to mark
            rside = (_side(ridx, rlo, rhi) if real(rp) else "same") if own else _side(ridx, rlo, rhi)
            maybe = [w for w, side, p in (("loss", gside, gp), ("revenue", rside, rp))
                     if side != "same" and not real(p)]
            gflag = gs.reading_band if peers else gs.reading_topline
            rflag = rs.reading_band if peers else rs.reading_topline
            # untested on either side: no box and no colour (the fourth walk, defect 3)
            untested = {gflag, rflag} & {engine.THIN, engine.FEW}
            box = NOT_TESTED if untested else box_of(gside, rside)
            luck = {w: w in maybe and box != NOT_TESTED for w in ("loss", "revenue")}

            def words(flag, side, w, more, less):
                if flag in (engine.THIN, engine.FEW):
                    return flag
                return {"more": more, "less": less, "same": "about the same"}[side] + (
                    " (could be luck)" if luck[w] else "")

            # dollars against the same comparison as the reading (the fourth walk, defect 2)
            parent = g.cells[(bl, engine.ALL)] if peers else res.total
            pg, pr = parent.rates["gco_rate"], parent.rates["ranr_rate"]
            rows.append({"band": bl, "seg": dl, "loans": gs.units, "box": box, "gidx": gidx, "ridx": ridx,
                         "gside": None if untested or luck["loss"] else gside,
                         "rside": None if untested or luck["revenue"] else rside,
                         "cells": [bl, dl, gs.units,
                                   gs.rate, _rest_rate(gs, pg), gidx,
                                   words(gflag, gside, "loss", "losing more", "losing less"), _over(gs, pg),
                                   rs.rate, _rest_rate(rs, pr), ridx,
                                   words(rflag, rside, "revenue", "earning more", "earning less"), _over(rs, pr)]})
        rows.sort(key=lambda x: (x["box"] == NOT_TESTED, -(x["cells"][7] or 0)))
        ws.cell(row=top, column=2, value=f"{names[g.band]} x {names[g.dimension]}").font = Font(
            name="Calibri", bold=True, size=12)
        # two header rows: which side, then what each column holds
        _head(ws, top + 1, ["", "", "", "Losses: GCO per booked dollar", "", "", "", "",
                            "Revenue: RANR per booked dollar", "", "", "", ""])
        for a, z in ((LVR_G, LVR_G + 4), (LVR_R, LVR_R + 4)):
            ws.merge_cells(start_row=top + 1, start_column=a, end_row=top + 1, end_column=z)
            ws.cell(row=top + 1, column=a).alignment = Alignment(horizontal="center")
        ws.row_dimensions[top + 1].height = 16
        _head(ws, top + 2, ["Band", "Segment", "Loans"] + side_heads + side_heads)
        r = top + 3
        first = r
        for row in rows:
            for i, v in enumerate(row["cells"], start=2):
                ws.cell(row=r, column=i, value=v)
            for a in (LVR_G, LVR_R):
                ws.cell(row=r, column=a).number_format = ws.cell(row=r, column=a + 1).number_format = "0.00%"
                ws.cell(row=r, column=a + 2).number_format = '0.00"x"'
                ws.cell(row=r, column=a + 4).number_format = "#,##0"
                ws.cell(row=r, column=a + 3).alignment = Alignment(indent=1)     # clear of the multiple
            # red and green by side, worse and better; a luck-marked side isn't shaded like a finding
            # (the sixth walk, defect 2)
            for a, side, bad in ((LVR_G, row["gside"], "more"), (LVR_R, row["rside"], "less")):
                if side in ("more", "less"):
                    fill = PatternFill("solid", fgColor=RED_CELL if side == bad else GREEN_CELL)
                    for col in (a + 2, a + 3):
                        ws.cell(row=r, column=col).fill = fill
            ws.cell(row=r, column=LVR_R).border = Border(left=Side(style="thin", color=SLATE))
            r += 1
        ws.cell(row=top + 2, column=LVR_R).border = Border(left=Side(style="thin", color=PAPER))
        if not rows:
            ws.cell(row=r, column=2, value="No pocket has enough loans to place.")
            r += 1
        if any(x["box"] != NOT_TESTED for x in rows):
            _revenue_chart(ws, hs, rows, first, r - 1, f"{names[g.band]} x {names[g.dimension]}", b,
                           None if own else rlo, None if own else rhi, 1 + gi * 3, top)
        top = max(r, top + 24) + 2
    for col, w in zip("ABCDEFGHIJKLMNO", (2, 16, 16, 7, 10, 11, 9, 20, 13, 10, 11, 9, 20, 13, 2)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "B4"
    _fit(ws)


def _revenue_chart(ws, hs, rows, first: int, last: int, title: str, b, rlo: float | None, rhi: float | None,
                   hcol: int, anchor_row: int) -> None:
    """One chart per grid (the third walk, defect 11: one chart for every grid
    counted the same loans six times). GCO on a scale of tens, so one pocket at
    8x doesn't squash the rest and 1.00x sits on a tick; the four lines from
    Control mark the boxes; the three biggest bleeders are named."""
    chart = ScatterChart()
    chart.title = title
    chart.style = 13
    chart.x_axis.title = "GCO multiple (right: losing more)"
    chart.y_axis.title = "RANR multiple (up: earning more)"
    last = first + sum(1 for x in rows if x["box"] != NOT_TESTED) - 1      # untested pockets sort last and stay off
    pts = Series(Reference(ws, min_col=LVR_R + 2, min_row=first, max_row=last),
                 Reference(ws, min_col=LVR_G + 2, min_row=first, max_row=last), title="Pockets")
    pts.marker.symbol = "circle"
    pts.marker.size = 6
    pts.marker.graphicalProperties.solidFill = "2F5597"
    pts.marker.graphicalProperties.line.solidFill = "2F5597"
    pts.graphicalProperties.line.noFill = True
    chart.series.append(pts)
    boxed = [x for x in rows if x["box"] != NOT_TESTED]
    xs, ys = [x["gidx"] for x in boxed if x["gidx"] > 0], [x["ridx"] for x in boxed]
    x_lo = 10 ** math.floor(math.log10(min(xs + [b.better_at])))
    x_hi = 10 ** math.ceil(math.log10(max(xs + [b.worse_at])))
    # whole tenths, so 1.00x is a tick (the fourth walk, defect 7)
    y_lo = math.floor((min(ys + ([rlo] if rlo else [1.0])) - 0.02) * 10) / 10
    y_hi = math.ceil((max(ys + ([rhi] if rhi else [1.0])) + 0.02) * 10) / 10
    # the four lines, in hidden helper columns: x, y pairs
    r = 1
    lines = [((b.worse_at, y_lo), (b.worse_at, y_hi)), ((b.better_at, y_lo), (b.better_at, y_hi))]
    if rlo and rhi:
        lines += [((x_lo, rhi), (x_hi, rhi)), ((x_lo, rlo), (x_hi, rlo))]
    for (x1, y1), (x2, y2) in lines:
        for k, (xv, yv) in enumerate(((x1, y1), (x2, y2))):
            hs.cell(row=r + k, column=hcol, value=xv)
            hs.cell(row=r + k, column=hcol + 1, value=yv)
        line = Series(Reference(hs, min_col=hcol + 1, min_row=r, max_row=r + 1),
                      Reference(hs, min_col=hcol, min_row=r, max_row=r + 1), title="line")
        line.marker.symbol = "none"
        line.graphicalProperties.line.solidFill = "7F7F7F"
        line.graphicalProperties.line.dashStyle = "dash"
        chart.series.append(line)
        r += 2
    # the three biggest bleeders, named on the chart
    from openpyxl.chart.label import DataLabelList
    named = [k for k, x in enumerate(rows) if x["box"].startswith("Losing more")][:3]
    for n_, k in enumerate(named):
        row = rows[k]
        rr = first + k
        name = f"{row['band']} / {row['seg']}"
        one = Series(Reference(ws, min_col=LVR_R + 2, min_row=rr, max_row=rr),
                     Reference(ws, min_col=LVR_G + 2, min_row=rr, max_row=rr), title=name)
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
    chart.y_axis.majorUnit = 0.1
    chart.x_axis.number_format = chart.y_axis.number_format = '0.00"x"'
    chart.x_axis.delete = chart.y_axis.delete = False
    chart.width, chart.height = 15, 10
    ws.add_chart(chart, f"P{anchor_row}")


def _heat(ws, rng: str, m) -> None:
    lo, hi = (GREEN, RED) if m.higher_is == "worse" else (RED, GREEN)
    ws.conditional_formatting.add(rng, ColorScaleRule(start_type="num", start_value=0.5, start_color=lo,
                                                      mid_type="num", mid_value=1, mid_color="FFFFFF",
                                                      end_type="num", end_value=2, end_color=hi))


def _block(ws, top: int, c0: int, label: str, rows_: list[str], cols: list[str], value, fmt: str, heat_m=None,
           skip_margins: bool = False) -> None:
    ws.cell(row=top, column=c0, value=label).font = Font(name="Calibri", bold=True, color=PAPER)
    ws.cell(row=top, column=c0).fill = PatternFill("solid", fgColor=INK)
    for j, d in enumerate(cols, start=c0 + 1):
        h = ws.cell(row=top, column=j, value=d)
        h.font = Font(name="Calibri", bold=True, color=PAPER)
        h.fill = PatternFill("solid", fgColor=INK)
        h.alignment = Alignment(wrap_text=True, horizontal="center")
    rr = top + 1
    for bl in rows_:
        ws.cell(row=rr, column=c0, value=bl)
        for j, d in enumerate(cols, start=c0 + 1):
            if skip_margins and (bl == engine.ALL or d == engine.ALL):
                continue
            v = value(bl, d)
            if v is not None:
                ws.cell(row=rr, column=j, value=v).number_format = fmt
        rr += 1
    if heat_m is not None:
        _heat(ws, f"{_col(c0 + 1)}{top + 1}:{_col(c0 + len(cols))}{rr - 1}", heat_m)


def _grids(ws, res) -> None:
    """Every band crossed with every dimension, as heat maps: the rate, the rate
    against the book, and the rate against the rest of the same band (its peers).
    Red is worse, green better; for RANR, where more is better, the other way.
    A column shown per pocket (median or average) gets its own block. A split
    by a category repeats the grid once per value, side by side."""
    names = _names(res)
    _title(ws, "Grids", "Each grid three ways: the rate, the rate against the book, and the rate against the rest "
                        "of the same band. Red is worse, green is better. For RANR more is better, so low is red.",
           "B:Z")
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
                   lambda bl, d: cell(bl, d, lambda s: s.vs_topline if s.reading_topline not in untested
                                      else None), '0.00"x"', m)
            _block(ws, top, 2 + 2 * width, "Vs the rest of its band", rows_, g.dim_labels,
                   lambda bl, d: cell(bl, d, lambda s: s.vs_band if s.reading_band not in untested else None),
                   '0.00"x"', m, skip_margins=True)
            r = top + len(rows_) + 1
            ws.cell(row=r, column=2 + width, value="Blank: fewer loans or losses than the minimum on Control, so "
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
                        return engine.index_of(c.rates[m.name].rate, top_rate)

                    _block(ws, r, c0, f"{res.config.split[0]} = {lab}", g.band_labels, g.dim_labels, val,
                           '0.00"x"', m)
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
    return ("yes" if held else f"no: part of this may be {p[0]}"), (0.0 if held else 1.0)


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
    # said once, here, instead of repeated under every grid (asked for on 25 Sep 2026)
    how_rows = [
        ("What it does", f"Inside each pocket (one band, one segment) the loans are sorted by {field_} and cut at "
                         f"that pocket's own median. The high half is compared with the low half, so the band and "
                         f"segment are the same on both sides. {field_} isn't cut into bands of its own while it "
                         f"splits."),
        ("High half vs low", "The high half's rate divided by the low half's. 2.00x means the high half goes bad, "
                             "or loses, twice as often. For RANR, above 1.00x means the high half earns more."),
        ("Luck alone", f"How often a gap this big turns up by chance when there's no real difference. The test "
                       f"weighs the gap against how much each half's rate wobbles at its size. The pocket figures "
                       f"(the heat maps) are after the allowance for many tests ({allowance}), across the pockets "
                       f"of one grid and one measure; a pocket whose gap could be luck shows its multiple in "
                       f"brackets, unshaded. The summary's figure is one pooled test per grid and measure, with "
                       f"no allowance. Blank: a half has fewer loans or losses than the minimums on Control "
                       f"({b.min_units if b else 0:,} loans, {b.min_events if b else 0:,} losses)."),
        ("Pooled across pockets", f"The high halves' actual total against what it would be at their low halves' "
                                  f"rates, added over every pocket, with its range at {conf:.0%} sure. For the "
                                  f"yes/no outcome only, the odds are pooled too (Mantel-Haenszel: a standard way to "
                                  f"combine pockets without mixing their loans), and Cochran's Q checks whether the "
                                  f"gap is about the same size in every pocket."),
        ("What it assumes", f"A grid holds fixed only its band and segment. Anything {field_} moves with that the "
                            f"grid doesn't hold fixed can show up here as a {field_} effect, so each grid gives the "
                            f"correlation, and grids that hold fixed what {field_} moves with most come first. "
                            f"A correlation runs from -1 to 1: 0 means unrelated, and the further from 0, the "
                            f"more of a gap may belong to the other column. "
                            f"Inside a band the score still varies a little, so a little can remain even there. "
                            f"Loans are treated as independent of each other."),
    ]
    ws.cell(row=4, column=2, value="How this tab works").font = Font(name="Calibri", bold=True, size=12)
    r = 5
    for k, v in how_rows:
        ws.cell(row=r, column=2, value=k).font = Font(name="Calibri", bold=True)
        ws.cell(row=r, column=2).alignment = Alignment(vertical="top")
        c = ws.cell(row=r, column=3, value=v)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=2 + 2 * width - 1)
        ws.row_dimensions[r].height = 44
        r += 1
    r += 1
    heads = ["Measure", "Pockets tested", "High half worse in", "High vs low, pooled", f"Range ({conf:.0%})",
             "Luck alone", "As odds", "Same size in every pocket?"]
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
        rr = r + 3
        rates = [m for m in res.measures if m.is_rate]
        for m in rates:
            p = g.split_pooled.get(m.name, {})
            steady = p.get("steady_p")
            vals = [m.title, p.get("pockets", 0),
                    f"{p['high_worse']} of {p['pockets']}" if p.get("pockets") else "none big enough",
                    p.get("ratio"), (f"{p['ratio_lo']:.2f}x to {p['ratio_hi']:.2f}x" if p.get("ratio_hi") else ""),
                    p.get("ratio_p"), p.get("odds"),
                    ("yes/no outcome only" if steady is None else
                     "yes" if steady >= 1 - conf else "no: bigger in some pockets")]
            for i, v in enumerate(vals, start=2):
                ws.cell(row=rr, column=i, value=v).alignment = Alignment(horizontal="left" if i == 2 else "center")
            ws.cell(row=rr, column=5).number_format = '0.00"x"'
            ws.cell(row=rr, column=7).number_format = P_FMT
            ws.cell(row=rr, column=8).number_format = '0.00"x"'
            rr += 1
        r = rr + 1
        for m in rates:
            def cmp_(bl, d, k, m=m, g=g):
                got = g.split_compare.get((bl, d), {}).get(m.name)
                return got[k] if got else None

            def shown(bl, d, m=m, g=g):
                # a gap that could be luck: in brackets and unshaded (the sixth walk, defect 9)
                got = g.split_compare.get((bl, d), {}).get(m.name)
                if not got or got[0] is None:
                    return None
                return got[0] if got[1] is not None and got[1] < 1 - conf else f"({got[0]:.2f}x)"

            _block(ws, r, 2, m.title, g.band_labels, g.dim_labels, shown,
                   '0.00"x"', m)
            _block(ws, r, 2 + width, "Luck alone", g.band_labels, g.dim_labels, lambda bl, d: cmp_(bl, d, 1),
                   P_FMT)
            r += len(g.band_labels) + 2
        r += 1
    ws.column_dimensions["A"].width = 2
    for j in range(2, 2 + 3 * width):
        ws.column_dimensions[_col(j)].width = 12
    for k in range(3):
        ws.column_dimensions[_col(2 + k * width)].width = 30
    _fit(ws)


def _pooled_sentence(p: dict, field_: str, m, conf: float) -> str:
    """The rate ratio leads, because it's the figure a consultant will quote; the
    odds are the test's own number and follow it (the third walk, defect 6)."""
    if not p or not p.get("pockets"):
        return "No pocket has enough loans in both halves to compare."
    parts = [f"The high-{field_} half was worse in {p['high_worse']} of the {_n(p['pockets'], 'pocket')} big "
             f"enough to test."]
    if p.get("ratio"):
        if m.mode == "flagwt" and m.per == engine.EACH_LOAN:
            what = f"has the outcome {p['ratio']:.2f} times as often as the low half"
        elif m.higher_is == "worse":
            what = f"loses {p['ratio']:.2f}x what it would at the low half's rate"
        else:
            what = f"earns {p['ratio']:.2f}x what it would at the low half's rate"
        rng = (f" ({conf:.0%} range {p['ratio_lo']:.2f} to {p['ratio_hi']:.2f})" if p.get("ratio_hi") else "")
        luck = (f" Luck alone gives a gap this big {_p(p['ratio_p'])} of the time." if p.get("ratio_p") is not None
                else "")
        parts.append(f"Holding the pocket fixed, the high half {what}{rng}.{luck}")
    if p.get("odds"):
        parts.append(f"As odds, {p['odds']:.2f}x ({p['odds_lo']:.2f} to {p['odds_hi']:.2f}).")
        if p.get("steady_p") is not None:
            steady = ("about the same size in every pocket" if p["steady_p"] >= 1 - conf
                      else "bigger in some pockets than others: see which below")
            parts.append(f"The gap is {steady}.")
    return " ".join(parts)


def _p(v) -> str:
    if v is None:
        return "(not available)"
    return "under 0.01%" if v < 0.0001 else f"{v:.2%}" if v < 0.01 else f"{v:.1%}"


def _total_words(m) -> str:
    """What a materiality share is a share of (the third walk, defect 16)."""
    if m.mode == "flagwt" and m.per == engine.EACH_LOAN:
        return "loans with the outcome"
    if m.mode == "flagwt":
        return f"{m.per} on loans with the outcome"
    return f"total {m.value}"


def _materiality_tab(ws, res) -> None:
    """The evidence for the materiality call, per grid and measure: what each
    level would keep (the second walk, defect 7: the call was made blind)."""
    names = _names(res)
    line = res.materiality_line
    _title(ws, "Materiality", "What each materiality level would keep: how many pockets, and how much of the "
                              "grid's excess they hold. The level itself is set on Control.", "B:F")
    r = 4
    for g in res.grids:
        for m in res.measures:
            if not m.is_rate:
                continue
            ws.cell(row=r, column=2, value=f"{names[g.band]} x {names[g.dimension]}: {m.title}").font = Font(
                name="Calibri", bold=True)
            now = line.get(m.name)
            if now:
                in_use = f"In use: {_amount(now, m)}"
            elif m.name in line:
                in_use = "In use: no line"
            else:
                in_use = "In use: no line (the dollar line on Control is GCO only)"
            ws.cell(row=r, column=6, value=in_use)
            _head(ws, r + 1, [f"Share of the book's {_total_words(m)}", f"Excess at or over ({_unit(m)})",
                              "Pockets kept", "Share of the grid's excess"])
            rr = r + 2
            for row in engine.materiality(g, m, res.total):
                for i, v in enumerate((row.share_of_losses, row.threshold, row.pockets, row.captured), start=2):
                    ws.cell(row=rr, column=i, value=v)
                ws.cell(row=rr, column=2).number_format = "0.0%"
                ws.cell(row=rr, column=3).number_format = "#,##0.0" if _unit(m) == "loans" else "#,##0"
                ws.cell(row=rr, column=5).number_format = "0%"
                rr += 1
            r = rr + 1
    for col, w in zip("ABCDEF", (2, 26, 30, 14, 24, 40)):
        ws.column_dimensions[col].width = w
    _fit(ws)


def _check(ws, res, src: Path, record: str = "") -> None:
    _title(ws, "Check", "Settings used, tie-outs, and what was left out.", "B:C")
    rows = [("Extract", src.name), ("Loans run", f"{res.rows:,}"),
            ("Record of this run", f"{record}, beside this workbook: every setting the run used, kept for the "
                                   f"file. It is replaced by the next Run."),
            ("Tie-out checks", f"{res.tie_outs:,} of {res.tie_outs:,} agree: every grid adds up to the book")]
    if res.aged_out:
        rows.append(("Left out for loan age", f"{res.aged_out:,}"))
    for m in res.measures:
        lo = res.left_out.get(m.name)
        if lo:
            rows.append((f"Left out of {m.title}", "; ".join(f"{k:,} x {col} {why}" for (col, why), k in lo.items())))
    names = _names(res)
    for name, e in res.band_edges.items():
        rows.append((f"Band edges used: {names.get(name, name)}",
                     f"{'; '.join(engine._fmt(x) for x in e)}  ({_n(len(e) + 1, 'band')})"))
    for mname, ln in res.loans_needed.items():
        m = next(x for x in res.measures if x.name == mname)
        rows.append((f"Loans needed for a {ln.gap:g}x gap: {m.title}",
                     f"about {ln.loans:,}" if ln.loans else "can't be sized (the book's rate is zero)"))
    for m in res.measures:
        if m.is_rate and res.config.benchmark is not None:
            v = res.materiality_line.get(m.name)
            rows.append((f"Materiality line: {m.title}", _amount(v, m) if v is not None
                         else "no line: the dollar line on Control is a GCO amount"))
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
        if "min_loans" in sug:
            words.append(f"fewest loans {sug['min_loans']:,} (enough to expect 5 with the outcome at the book's "
                         f"rate of {rate:.2%})" if rate else f"fewest loans {sug['min_loans']:,}")
        if "worse_at" in sug:
            words.append(f"worse at {sug['worse_at']:.2f}x")
        if "better_at" in sug:
            words.append(f"better at {sug['better_at']:.2f}x")
        if "worse_at" in sug or "better_at" in sug:
            words[-1] += " (the outcome gap luck alone can make in a pocket of typical size)"
        fb = getattr(res, "suggest_fallback", set())
        if fb:
            words.append("where nothing could be worked out (no rate, or no pocket big enough), the usual value "
                         "was used instead: " + ", ".join(sorted(fb)))
        rows.append(("Worked out from this book" if not fb else "Suggested values", "; ".join(words)))
    b = res.config.benchmark
    if b is not None and b.many_tests != "none":
        rows.append(("The allowance for many tests covers",
                     "each grid and measure on its own, one comparison at a time (the firm's call, 25 Sep 2026)"))
    rl = revenue_lines(res)
    if rl and per_pocket(res):
        rows.append(("Revenue counts as more or less", f"when it's {rl[2]}"))
    elif rl:
        rows.append(("Revenue counts as more or less at", f"{rl[1]:.2f}x and {rl[0]:.2f}x ({rl[2]})"))
    for q, words in control.describe(_settings_of(res.config)):
        rows.append((q, words))
    for w in res.warnings:
        rows.append(("Warning", _plain_warning(w)))
    for i, (k, v) in enumerate(rows, start=4):
        ws.cell(row=i, column=2, value=k).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=i, column=2).font = Font(name="Calibri", bold=True)
        ws.cell(row=i, column=3, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 100
    _fit(ws)


def _settings_of(cfg) -> dict:
    b = cfg.benchmark
    if b is None:
        return {}
    mat = {"none": "none", "share": f"{b.materiality[1] * 100:g}% of losses"}.get(
        b.materiality[0], f"${b.materiality[1]:,.0f} of GCO")
    return {"min_loans": b.min_units, "min_events": b.min_events, "worse_at": b.worse_at, "better_at": b.better_at,
            "confidence": b.confidence, "power": b.power, "compare_to": b.compare_to, "many_tests": b.many_tests,
            "materiality": mat, "min_age_months": cfg.min_age_months, "revenue_line": b.revenue_line}
