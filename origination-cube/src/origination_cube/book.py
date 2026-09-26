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
from . import control, engine, meanings, memory, perm, profile, stats
from . import checks, confirmatory, prevalence          # fixes 3.12 and 3.15 to 3.18
from .ingest import Table, read_table

INK, CANVAS, SLATE, PAPER, NEEDS = "16130F", "F4F1EC", "57534B", "FFFFFF", "FCE4C4"
WORSE_FILL, LUCK_FILL = "F7DEDE", "FFF1D6"
GREEN, RED = "63BE7B", "F8696B"
INPUT_TABS = ("Start here", "Control", "Columns", "Look", "Odd values", "Learned")
RESULT_TABS = ("Where it bleeds", "Losses vs revenue", "Grids", "Split", "Prevalence", "Three-way", "Materiality",
               "Check", "Log")
LOG_FIRST = 4            # the newest line on the Log tab
HELPERS = ("_options", "_meanings", "_about")
ABOUT = "_about"
CHART_DATA = "_chart"     # the Losses vs revenue charts' own numbers, hidden
COL_FIRST = 6            # first column row on the Columns tab
CONFIRM_CELL = "C3"      # "Checked every column?"
# Columns tab, one column per thing a person says about an extract column
C_NAME, C_MEANS, C_CUT, C_IS, C_EDGES, C_SHOW, C_SPLIT, C_LOOK, C_WHY, C_BLANK, C_SAMPLES = range(2, 13)
# fixes 3.10 and 3.11: what an amount is over, and what it measures in the person's words. At the end, so no
# column a person already knows moves
C_PERIOD, C_DEFINE = 13, 14
C_SUGG = 15              # hidden: the meaning Set up suggested, so a refusal can name what was changed
C_MADE = 16              # hidden: for a new column made on Control, what Set up made it from ("INCOME ÷ SALES")
SHOW_OPTIONS = ("median", "average")
PERIOD_OPTIONS = {"per year": "per_year", "per month": "per_month", "one-time": "one_time"}


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
    out: dict[str, Any] = {"control": {}, "columns": {}, "confirmed": None, "odd": {}, "last_used": {},
                           "derived": {}}
    if not book.exists():
        return out
    wb = load_workbook(book)
    if control.SHEET in wb.sheetnames:
        for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
            key = r[control.KEY_COL - 1].value
            if isinstance(key, str) and key.startswith(f"{control.DERIVED_KEY}|"):
                slot = key.split("|")[1]
                if slot.isdigit():
                    out["derived"][int(slot)] = tuple(r[c - 1].value for c in (3, 4, 5))
                continue
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
                    "show": r[C_SHOW - 1], "split": r[C_SPLIT - 1],
                    "period": r[C_PERIOD - 1] if len(r) >= C_PERIOD else None,
                    "define": r[C_DEFINE - 1] if len(r) >= C_DEFINE else None}
    if "Odd values" in wb.sheetnames:
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
            notes.append(f"New column {slot} on Control needs a name, a top and a bottom, so it isn't made yet.")
        elif name in names:
            notes.append(f"New column {slot} on Control: {name} is already a column, so it isn't made. Give it a "
                         f"name of its own.")
        elif top not in names or bottom not in names:
            gone = " and ".join(c for c in (top, bottom) if c not in names)
            notes.append(f"New column {slot} on Control: {gone} isn't a column in this extract, so {name} isn't made.")
        elif top == bottom:
            notes.append(f"New column {slot} on Control: {top} over itself is 1 on every loan, so {name} isn't made.")
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


def _needed(s, kept: dict, codes: set[str]) -> bool:
    """Whether a Control setting needs an answer for this workbook as it stands:
    always, or - for one asked only sometimes - when its condition holds."""
    if not s.needed_when:
        return True
    if s.needed_when == "outcome_date":
        return "outcome_date" in codes
    in_use = any((control.answer_of(k, *kept["control"].get(k, (None, None))) or 0) > 0
                 for k in ("min_age_months", "window_months"))
    return in_use and "as_of_date" not in codes


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
    cat = meanings.catalog()
    method = {s.key: s.recommended().value for s in control.load_settings() if s.recommended()}
    # the category limits as answered on Control: Set up is where they apply (found checking the seventh
    # walk's blank "Last Run used" rows: Set up always used the recommended 12 and 50)
    for key in ("few_values", "many_values"):
        got = control.answer_of(key, *kept["control"].get(key, (None, None)))
        if isinstance(got, (int, float)) and not isinstance(got, bool):
            method[key] = int(got)
    few, many = int(method["few_values"]), int(method["many_values"])
    cols = profile.classify(table, few, many)
    sugg = meanings.suggest(table, mem["columns"], few_values=few, many_values=many)
    extract_cols = list(table.columns)
    # fix 3.9: the new columns typed on Control are made here, so Columns lists them and Look shows them
    facts_of = {c: meanings.facts(table, c) for c in extract_cols}
    number_cols = [c for c in extract_cols if facts_of[c].numeric]
    table, made, made_notes = _made_columns(table, cols, kept, mem)
    if made:
        cols += profile.classify(Table(path=table.path, sha256=table.sha256, columns=[r.name for r in made],
                                       rows=table.rows, kind=table.kind), few, many)
        for r_ in made:
            sugg[r_.name] = meanings.Suggestion(r_.name, "amount", f"made on Control: {r_.text()}", "control")
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
    control.write_control(wb, control.load_settings(), with_columns=True)
    for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
        key = r[control.KEY_COL - 1].value
        if key in kept["control"]:
            choose, own = kept["control"][key]
            r[control.CHOOSE_COL - 1].value = choose
            if own not in (None, "n/a"):
                r[control.OWN_COL - 1].value = own
    control.write_derived(wb, number_cols, kept["derived"])
    control.write_prespec(wb, kept["control"].get(control.PRESPEC_KEY, (None, None))[0])     # fix 3.15
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
        for r in cws.iter_rows(min_row=control.FIRST_ROW):
            key = r[control.KEY_COL - 1].value
            if key in ("few_values", "many_values"):
                c = cws.cell(row=r[0].row, column=col, value=f"{method[key]} values (applied at Set up)")
                c.font = Font(name="Calibri", color=SLATE)

    # ---- Columns
    ws = wb.create_sheet("Columns")
    _title(ws, "Columns", "Fix any meaning that's wrong, and set Cut by it to No for anything you don't want in "
                          "the grids. Shaded rows have a reason under Look first. Set C3 to Yes when done; "
                          "confirmed meanings carry over to the next extract.", "B:N")
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
    notes += made_notes
    ws["D3"] = " ".join(notes) or None
    ws["D3"].font = Font(name="Calibri", bold=True, color="960019")
    ws["D3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("D3:N3")
    ws.row_dimensions[3].height = 30 if notes else 16
    _head(ws, 5, ["Column", "What it is", "Cut by it?", "Yes means (outcome only)",
                  "Band edges (620; 680 or every 20)",
                  "Show per pocket", "Split pockets by it?", "Look first", "Why this was suggested", "Blank",
                  "Samples", "Period (amounts only)", "What it measures, in your words"])
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
    dv_period = DataValidation(type="list", formula1=f'"{",".join(PERIOD_OPTIONS)}"', allow_blank=True,
                               showErrorMessage=True)
    dv_period.error = "Pick per year, per month or one-time, or leave it blank."
    for dv in (dv_m, dv_cut, dv_show, dv_split, dv_period):
        ws.add_data_validation(dv)
    by_col: dict[str, list[str]] = {}
    for rv in looks:
        if rv.kind != "cannot run":
            by_col.setdefault(rv.column, []).append(rv.says)
    for c in new_cols:
        by_col.setdefault(c, []).insert(0, "New since the last check.")
    classified = {c.name: c for c in cols}
    edge_noted: set[str] = set()
    codes_now: set[str] = set()
    r = COL_FIRST
    for c in table.columns:
        sg = sugg[c]
        prior = kept["columns"].get(c, {})
        code = _to_code(prior.get("means"), cat) or sg.means
        tag = "Remembered: " if sg.source == "remembered" else ""
        f = facts_of.get(c) or meanings.facts(table, c)
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
        samples = classified[c].samples[:3] if c in classified else []
        if any(m.name == c for m in made):
            samples = [f"{float(v):.4g}" for v in samples]      # a ratio to four figures, not seventeen
        ws.cell(row=r, column=C_SAMPLES, value=", ".join(samples))
        ws.cell(row=r, column=C_SUGG, value=sg.means)
        ws.cell(row=r, column=C_PERIOD, value=prior.get("period"))
        dv_period.add(ws.cell(row=r, column=C_PERIOD))
        ws.cell(row=r, column=C_DEFINE, value=prior.get("define"))
        ws.cell(row=r, column=C_MADE, value=next((m.text() for m in made if m.name == c), None))
        codes_now.add(code)
        for col in range(C_NAME, C_DEFINE + 1):
            ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top", indent=1 if col in (
                C_BLANK, C_SAMPLES) else 0, horizontal="center" if col == C_BLANK else None)
        r += 1
    look = _col(C_LOOK)
    ws.conditional_formatting.add(f"{look}{COL_FIRST}:{look}{r}", FormulaRule(
        formula=[f'{look}{COL_FIRST}<>""'], fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))
    for col, w in zip("ABCDEFGHIJKLMN", (2, 22, 20, 9, 13, 16, 11, 11, 44, 40, 8, 30, 12, 34)):
        ws.column_dimensions[col].width = w
    ws.column_dimensions[_col(C_SUGG)].hidden = True
    ws.column_dimensions[_col(C_MADE)].hidden = True
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

    from . import look                      # fix 3.8: each number column's shape, before its edges are chosen
    shown = look.number_columns(table, cols, few)
    look.write_look(wb, table, shown + [m.name for m in made if m.name not in shown])
    _learned_tab(wb, memory_path)

    about = wb.create_sheet(ABOUT)
    about["A1"], about["B1"] = "extract", str(extract.resolve())
    about["A2"], about["B2"] = "sha256", hashlib.sha256(extract.read_bytes()).hexdigest()
    about["A3"], about["B3"] = "set up", (today or date.today()).isoformat()
    about["A4"], about["B4"] = "extract name", extract.name
    about.sheet_state = "hidden"
    unanswered = sum(1 for s in control.load_settings() if s.judgment and _needed(s, kept, codes_now)
                     and not any(v not in (None, "n/a") for v in kept["control"].get(s.key, (None, None))))
    last = None
    if "Log" in wb.sheetnames:
        lg = wb["Log"]
        top = LOG_FIRST if lg["A1"].value == "Log" else 1
        if lg.cell(row=top, column=1).value:
            last = f"{lg.cell(row=top, column=1).value}: {lg.cell(row=top, column=2).value}"
    _start_here(start, extract, len(table.rows), len(extract_cols), looks, len(qs), unanswered, last)
    _order(wb)
    try:
        wb.save(book)
    except PermissionError:
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Set up again."])
    lines = [f"Set up {book.name} from {extract.name}: {len(table.rows):,} loans, {_n(len(extract_cols), 'column')}."]
    for m in made:
        why = "; ".join(f"{k:,} where {w}" for w, k in m.blank.items())
        lines.append(f"Made {m.name} = {m.text()} on Columns and Look" + (f". Blank on {why}." if why else "."))
    lines += made_notes
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
            code = re.split(r"[ ;]", learned)[0]          # "fico; band edges every 20" (the seventh walk)
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
    made_rows: dict[str, tuple[int, str]] = {}         # a new column made on Control -> (its row, what it was made from)
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
    derived = _read_made(wb, columns, made_rows, problems)
    dates = _read_dates(wb, use, columns, problems) if use else {}
    questions = []
    for r in wb["Odd values"].iter_rows(min_row=5, values_only=True):
        if len(r) < 7 or not r[1] or not r[6]:
            continue
        pattern, _, value = str(r[6]).partition("|")
        questions.append({"column": r[1], "pattern": pattern, "value": float(value) if value else None,
                          "rows": r[3] or 0, "answer": r[4] or None})
    held_to = confirmatory.read(wb, book, problems)          # fix 3.15: the pre-spec named on Control, if any
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
    raw.update(dates)                               # fixes 3.13, 3.14: the window and the as-of date
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


def _read_made(wb, columns: dict, made_rows: dict, problems: list[str]) -> list[dict]:
    """The new columns on Control, each checked against Columns: a new column
    must have been made by Set up from exactly what Control says now, or the
    Columns and Look tabs describe something else (fix 3.9: "if a derived
    column is defined but the workbook hasn't been set up since, Run says to
    press Set up again")."""
    defs, bad = control.read_derived(wb[control.SHEET])
    problems += bad
    out = []
    for d in defs:
        where = f"{control.SHEET}!C{d['row']}"
        made = made_rows.get(d["name"])
        now = f"{d['top']} ÷ {d['bottom']}"
        if d["name"] in columns and made is None:
            problems.append(f'{where}: "{d["name"]}" is already a column in the extract. Give the new column a name '
                            f'of its own.')
        elif made is None:
            problems.append(f'{where}: the new column "{d["name"]}" isn\'t on Columns yet. Press Set up again, then '
                            f'check it on Columns and Look.')
        elif made[1] != now:
            problems.append(f'{where}: "{d["name"]}" was made as {made[1]} and Control now says {now}. Press Set up '
                            f'again, so Columns and Look show it as it is now.')
        else:
            out.append({"name": d["name"], "top": d["top"], "bottom": d["bottom"]})
    named = {d["name"] for d in defs}
    for name, (row, _) in made_rows.items():
        if name not in named:
            problems.append(f'Columns!{_col(C_NAME)}{row}: "{name}" was a new column made on Control, and Control '
                            f'doesn\'t have it now. Press Set up again.')
    return out


def _read_dates(wb, use: dict, columns: dict, problems: list[str]) -> dict:
    """The outcome window and the as-of date from Control, checked against the
    dates marked on Columns (fixes 3.13, 3.14). Each is asked for only when it
    matters, and then refused by cell until it is answered: the window when a
    column is marked Outcome date, the as-of date when a loan age filter or a
    window is in use and no column is marked As-of date. The as-of date is never
    worked out unless someone picked "the latest date in the extract"."""
    ws = wb[control.SHEET]
    cat = meanings.catalog()
    marked = {m: [c for c, v in columns.items() if (v if isinstance(v, str) else v["means"]) == m]
              for m in cfgmod.DATE_ROLES}

    def cell(key: str) -> str:
        return f"{control.SHEET}!C{control.row_of(ws, key) or ''}"

    out: dict[str, Any] = {}
    age = int(use.get("min_age_months") or 0)
    window = use.get("window_months")
    if window is None and marked["outcome_date"]:
        problems.append(f"{cell('window_months')}: {marked['outcome_date'][0]} is marked Outcome date on Columns, so "
                        f"say what bad means: No window, or bad within so many months of being made.")
    window = int(window or 0)
    if marked["outcome_date"] or window:
        out["window_months"] = window
    if window and not marked["outcome_date"]:
        problems.append(f"{cell('window_months')}: an outcome window of {window} months needs the date each loan went "
                        f"bad. Mark that column {cat['outcome_date'].label} on Columns, or pick No window.")
    if window and not marked["origination_date"]:
        problems.append(f"{cell('window_months')}: an outcome window of {window} months needs the date each loan was "
                        f"made. Mark that column {cat['origination_date'].label} on Columns.")
    if window and age:
        problems.append(f"{cell('min_age_months')} and {cell('window_months')}: use the loan age filter or the outcome "
                        f"window, not both. The window already leaves out loans under {window} months on book, so "
                        f"set the loan age filter to Every loan.")
    as_of = use.get("as_of")
    what = f"an outcome window of {window} months" if window else f"a loan age filter of {age} months"
    if marked["as_of_date"] and as_of not in (None, "column"):
        problems.append(f"{cell('as_of')}: the as-of date is on Control and {marked['as_of_date'][0]} is marked "
                        f"As-of date on Columns. Keep one: pick the As-of date column here, or mark it Not used.")
    elif (window or age) and not marked["as_of_date"]:
        if as_of is None:
            problems.append(f"{cell('as_of')}: {what} needs the date the data was taken. Pick the latest date in the "
                            f"extract, or type the date.")
        elif as_of == "column":
            problems.append(f"{cell('as_of')}: no column on Columns is marked As-of date. Mark it, pick the latest "
                            f"date in the extract, or type the date.")
        else:
            out["as_of"] = as_of                       # "latest", or the date typed
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
    except (engine.ColumnsMissing, engine.NothingToCut) as exc:
        msg = re.sub(r"used by dimension \w+", "a segment", re.sub(r"used by band \w+", "a band", str(exc)))
        msg = msg.replace("`", '"')
        if isinstance(exc, engine.ColumnsMissing):
            # the third walk, defect 15: a renamed column needs Set up, and the message didn't say so
            msg += ". If a column was renamed or dropped, press Set up again."
        _log(book, ["Couldn't run:", msg])
        return Outcome(False, book, [f"Couldn't run: {msg}"])
    except perm.NumpyMissing as exc:
        _log(book, ["Couldn't run:", str(exc)])
        return Outcome(False, book, [f"Couldn't run: {exc}"])
    checks.attach(book, about, res)             # fixes 3.12, 3.15: the pre-spec's state and the edges on Columns
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
        from . import look                  # fix 3.8: the Look tab again, with the split's scatters
        look.refresh(book, res.table or table, res.config.split and res.config.split[0],
                     [b.field for b in res.config.bands])
    except PermissionError:
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Run again."])
    audit = book.with_name(f"{book.stem} - what ran.yaml")
    head = "# Exactly what the last Run used.\n"
    if per_pocket(res):
        head += "# revenue_line: each pocket's own test (profit counts only when its gap is significant)\n"
    head += _dates_head(res)
    head += confirmatory.what_ran(res)
    if isinstance(raw.get("benchmark"), dict) and cfg.benchmark is not None:
        raw["benchmark"].setdefault("shuffles", cfg.benchmark.shuffles)
    audit.write_text(head + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    lines = notes + [f"Ran on {res.rows:,} loans from {src.name}; {res.tie_outs:,} tie-out checks agree."]
    lines += _top_lines(res)
    lines += _date_lines(res)
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
            least = res.config.benchmark.min_events if res.config.benchmark else 0
            out.append(f"No pocket had enough losses to test {m.title} (fewest losses: {least:,}).")
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
                 f"(the last column says no) come after the rest, and aren't shaded red: part of their gap may be {pt[0]}."
                 if note and pt else "")
        _bleeds(wb.create_sheet("Three-way"), res, res.three_way, "Three-way",
                f"Pockets split by {sf}, each tested like any other pocket,", note, after)
    prevalence.write(wb, res)                   # fix 3.12: only with a split or a new column
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
         confirmatory.log_lines(res) +          # fix 3.15: held to a pre-spec, and whether it touched the holdout
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
    by_q = dict(control.describe({**_settings_of(res.config), **_date_settings(res.config)}))
    sug = getattr(res, "suggested", None) or {}
    used = getattr(res, "control_used", None) or {}
    for row in ws.iter_rows(min_row=control.FIRST_ROW):
        key = row[control.KEY_COL - 1].value
        s = next((x for x in control.load_settings() if x.key == key), None)
        if s is None:
            continue
        words = by_q.get(s.question)
        fb = getattr(res, "suggest_fallback", set())
        if words is None and key in ("band_count", "band_cut") and key in used:
            words = dict(control.describe({key: used[key]})).get(s.question)
        if key in ("few_values", "many_values"):
            continue                        # applied at Set up, and said there
        if key == "revenue_line" and profit_line(res):
            words = profit_words(res)
        elif key in fb:
            words = f"{words} (the usual value: nothing in this book to work it out from)"
        elif key in sug:
            words = f"{words} (worked out from this book)"
        if key == "as_of" and res.dates is not None:
            words = f"{res.dates.as_of.isoformat()}: {res.dates.as_of_from}"
        c = ws.cell(row=row[0].row, column=col, value=words)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = Font(name="Calibri", color=SLATE)


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
    peers = bool(b and b.compare_to == "peers")
    judged = "the rest of its band" if peers else "the rest of the book"
    names = _names(res)
    _title(ws, title, f"{lead} losing more than their share (profit: keeping less), largest first. The flag compares "
                      f"each pocket with {judged}. Profit is a gap in points, judged by the profit line on Control. "
                      f"Red: worse. Amber: worse, not significant. Blue: material, but too few losses to test, so "
                      f"look by hand. p-value: the chance of a gap this big with no real difference, after the "
                      f"allowance for many tests (see Check). Test: which test ran; for a dollar rate, how many "
                      f"shuffles made a gap as big against {judged}.{after}", "B:T" if note_of else "B:S")
    ws.row_dimensions[2].height = 44
    heads = ["Measure", "Band column", "Band", "Segment column", "Segment", "Loans", "Rate", "Book rate", "Excess",
             "Excess is in", "Material", "Vs rest of book", "p-value", "Vs rest of band", "p-value",
             f"Flag (vs {judged})", "Smallest gap it could show"] + (
                [f"Holds {_partner(res)[0]} fixed?" if _partner(res) else "Holds fixed?"] if note_of else []) + [
                "Test"]
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
            if m.in_points:
                # a shortfall of at least this many points: profit's bleed is the downward gap
                gap = -s.smallest_gap * 100 if s.smallest_gap else None
            else:
                gap = s.smallest_gap if m.higher_is == "worse" else (1 / s.smallest_gap if s.smallest_gap else None)
            vals = [m.title, names[g.band], bl, names[g.dimension], dl, s.units, s.rate,
                    res.total.rates[m.name].rate, ex, _unit(m),
                    {True: "yes", False: "below the line", None: ""}[s.material], _shown(s.vs_rest, m),
                    s.p_book if tested else None, _shown(s.vs_band, m), s.p_band if tested else None, s.flag or "",
                    gap]
            if note_of:
                vals.append(note_of(g)[0])
            vals.append(which_test(s, peers) if tested else "")
            for i, v in enumerate(vals, start=2):
                ws.cell(row=r, column=i, value=v)
            ws.cell(row=r, column=len(vals) + 1).alignment = Alignment(horizontal="left", indent=1)   # clear of the gap
            # loans to one decimal, like the line they're held against (the third walk, defect 13)
            ex_fmt = "#,##0.0" if _unit(m) == "loans" else "#,##0"
            for col, fmt in ((8, "0.00%"), (9, "0.00%"), (10, ex_fmt), (13, _gap_fmt(m)), (14, P_FMT),
                             (15, _gap_fmt(m)), (16, P_FMT)):
                ws.cell(row=r, column=col).number_format = fmt
            ws.cell(row=r, column=18).number_format = ('0.00" pts or less"' if m.in_points else
                                                       '0.00"x or more"' if m.higher_is == "worse"
                                                       else '0.00"x or less"')
            # words that follow a right-aligned number start clear of it ("10.9%worse", "80.4loans" on the render,
            # 26 Sep 2026)
            for col in (11, 17, 19):
                ws.cell(row=r, column=col).alignment = Alignment(indent=1)
            r += 1
    if r == 5:
        ws.cell(row=5, column=2, value="Nothing is losing more than its share at these settings.")
    # material but too small to test: shown, not hidden (the firm, 25 Sep 2026: "this is a materiality thing")
    # on Three-way, no red on a row whose grid doesn't hold the split's partner fixed: its gap may be
    # mostly that column (the firm, 25 Sep 2026, after the seventh walk). A real effect of the split
    # column still shows red in the grids that do hold it fixed
    red = 'AND($Q5="worse",LEFT($S5,3)<>"no:")' if note_of else '$Q5="worse"'
    for formula, fill in ((red, WORSE_FILL), (f'$Q5="{engine.UNSURE_WORSE}"', LUCK_FILL),
                          ('AND($L5="yes",LEFT($Q5,7)="too few")', SMALL_FILL)):
        ws.conditional_formatting.add(f"B5:R{max(r, 6)}", FormulaRule(formula=[formula], fill=PatternFill(
            "solid", fgColor=fill, bgColor=fill)))
    seg_w = 26 if grids is not res.grids else 13
    # the measure's name on one line: "Contribution before losses per booked dollar" (the render, 26 Sep 2026)
    for col, w in zip("ABCDEFGHIJKLMNOPQR", (2, 42, 12, 22, 16 if seg_w == 13 else 26, seg_w, 8, 8, 8, 12, 16, 14,
                                             11, 11, 11, 11, 22, 17)):
        ws.column_dimensions[col].width = w
    ws.column_dimensions["T" if note_of else "S"].width = 22
    if note_of:
        ws.column_dimensions["S"].width = 30
        ws.row_dimensions[2].height = 72
        for row in ws.iter_rows(min_row=5, min_col=19, max_col=19):
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
        hits = s.hits_band if peers else s.hits_book
        return f"shuffled: {hits:,} of {s.shuffles:,}" if hits is not None else f"{s.shuffles:,} shuffles"
    return ""


NOT_TESTED = "Not tested: too few losses"
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
# Comparison, find a clean way to display the comparable metrics"), and since NEXT-GOAL 3.4 three sides:
# what they paid us, what they cost us, what we kept
LVR_C, LVR_G, LVR_R, LVR_T = 5, 10, 15, 20       # first column of each side, and Together
LVR_SIDE = ("This pocket", "{rest}", "Gap", "Reading", "Over the rest ($)")
# (measure, heading, first column, word for more, word for less, the side that is worse)
LVR_SIDES = (("contribution_rate", "What they paid us: contribution before losses", LVR_C, "pays more", "pays less",
              "less"),
             ("gco_rate", "What they cost us: GCO", LVR_G, "losing more", "losing less", "more"),
             ("ranr_rate", "What we kept: profit after losses (RANR)", LVR_R, "keeps more", "keeps less", "less"))
PROFIT_SIDE = {engine.WORSE: "less", engine.UNSURE_WORSE: "less", engine.BETTER: "more", engine.UNSURE_BETTER: "more"}


def _rest_rate(s, parent) -> float | None:
    den = parent.den - s.den
    return (parent.num - s.num) / den if den else None


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
    same comparison as the reading (the third walk, defect 5)."""
    names = _names(res)
    b = res.config.benchmark
    if b is None or not {"gco_rate", "ranr_rate", "contribution_rate"} <= {m.name for m in res.measures}:
        _title(ws, "Losses vs revenue", "Needs the Control settings.", "B:T")
        return
    peers = b.compare_to == "peers"
    rest = "Rest of band" if peers else "Rest of book"
    judged = "the rest of its band" if peers else "the rest of the book"
    line = profit_line(res)
    when = {"test": "only when the pocket's own test calls the gap significant",
            "points": f"at {line.value * 100:.2f} points either way",
            "dollars": f"when the gap reaches {line.value:,.0f} dollars (the materiality line)"}[line.kind]
    _title(ws, "Losses vs revenue", f"Each pocket beside {judged}: what they paid us (contribution before losses), "
                                    f"what they cost us (GCO) and what we kept (profit after losses, RANR). "
                                    f"RANR already has GCO taken out, so contribution is RANR + GCO. "
                                    f"GCO counts as more at {b.worse_at:.2f}x or above and less at "
                                    f"{b.better_at:.2f}x or below. Contribution and profit are gaps in points, and "
                                    f"count {when}. Red is worse, green is better; a gap that is not significant is "
                                    f"marked and left plain. Together: losing more and keeping more is priced for "
                                    f"it; losing more and keeping less, a net drain; losing less and keeping less, "
                                    f"safe but idle.", "B:T")
    ws.row_dimensions[2].height = 58
    side_heads = [h.format(rest=rest) for h in LVR_SIDE]
    # the charts' own numbers (the Control lines, the named pockets) live on a hidden sheet:
    # hidden cells on this tab aren't drawn by every spreadsheet program
    wb = ws.parent
    if CHART_DATA in wb.sheetnames:
        del wb[CHART_DATA]
    hs = wb.create_sheet(CHART_DATA)
    hs.sheet_state = "hidden"
    real = lambda p: p is not None and p < 1 - b.confidence      # noqa: E731
    untested_words = (engine.THIN, engine.FEW)
    top = 4
    ms = {m.name: m for m in res.measures}
    for gi, g in enumerate(res.grids):
        rows = []
        for (bl, dl), c in g.inner():
            ss = {k: c.rates[k] for k, *_ in LVR_SIDES}
            gaps = {k: s.vs_band if peers else s.vs_rest for k, s in ss.items()}
            # every pocket with all three comparisons, whatever its size: below fewest loans a dollar rate
            # is still shuffled (docs/statistics.md B2), and only fewest losses leaves a side untested
            if any(v is None for v in gaps.values()):
                continue
            flags = {k: s.reading_band if peers else s.reading_topline for k, s in ss.items()}
            ps = {k: s.p_band if peers else s.p_book for k, s in ss.items()}
            # GCO by the lines on Control; a side whose own test says the gap isn't significant keeps its
            # reading and says so (the firm, 25 Sep 2026, after the fifth walk)
            sides = {k: PROFIT_SIDE.get(f, "same") for k, f in flags.items()}
            sides["gco_rate"] = _side(gaps["gco_rate"], b.better_at, b.worse_at)
            unsure = {k: f in (engine.UNSURE_WORSE, engine.UNSURE_BETTER) for k, f in flags.items()}
            unsure["gco_rate"] = (sides["gco_rate"] != "same" and not real(ps["gco_rate"])
                                  and flags["gco_rate"] not in untested_words)
            # untested on any side: no colour and no Together (the fourth walk, defect 3)
            untested = bool(set(flags.values()) & set(untested_words))
            shown = {k: None if untested or unsure[k] else sides[k] for k in sides}
            # dollars against the same comparison as the reading (the fourth walk, defect 2)
            parent = g.cells[(bl, engine.ALL)] if peers else res.total
            over = {k: _over(s, parent.rates[k]) for k, s in ss.items()}
            cells = [bl, dl, ss["gco_rate"].units]
            for k, _, _, more, less, _ in LVR_SIDES:
                s = ss[k]
                word = flags[k] if flags[k] in untested_words else (
                    {"more": more, "less": less, "same": "about the same"}[sides[k]]
                    + (" (not significant)" if unsure[k] else ""))
                cells += [s.rate, _rest_rate(s, parent.rates[k]), _shown(gaps[k], ms[k]), word, over[k]]
            together = "" if untested else together_of(shown["gco_rate"], shown["ranr_rate"])
            rows.append({"band": bl, "seg": dl, "untested": untested, "gidx": gaps["gco_rate"],
                         "ridx": gaps["ranr_rate"] * 100, "shown": shown, "cells": cells + [together or None],
                         "g_over": over["gco_rate"]})
        rows.sort(key=lambda x: (x["untested"], -(x["g_over"] or 0)))
        ws.cell(row=top, column=2, value=f"{names[g.band]} x {names[g.dimension]}").font = Font(
            name="Calibri", bold=True, size=12)
        # two header rows: which side, then what each column holds
        _head(ws, top + 1, ["", "", ""] + [x for _, h, *_ in LVR_SIDES for x in (h, "", "", "", "")] + [""])
        for _, _, a, *_ in LVR_SIDES:
            ws.merge_cells(start_row=top + 1, start_column=a, end_row=top + 1, end_column=a + 4)
            ws.cell(row=top + 1, column=a).alignment = Alignment(horizontal="center")
        ws.row_dimensions[top + 1].height = 16
        _head(ws, top + 2, ["Band", "Segment", "Loans"] + side_heads * 3 + ["Together"])
        r = top + 3
        first = r
        for row in rows:
            for i, v in enumerate(row["cells"], start=2):
                ws.cell(row=r, column=i, value=v)
            for k, _, a, _, _, bad in LVR_SIDES:
                ws.cell(row=r, column=a).number_format = ws.cell(row=r, column=a + 1).number_format = "0.00%"
                ws.cell(row=r, column=a + 2).number_format = '0.00"x"' if k == "gco_rate" else PTS_FMT
                ws.cell(row=r, column=a + 4).number_format = "#,##0"
                ws.cell(row=r, column=a + 3).alignment = Alignment(indent=1)     # clear of the gap
                ws.cell(row=r, column=a).border = Border(left=Side(style="thin", color=SLATE))
                # red and green by side, worse and better; a side that isn't significant isn't shaded like
                # a finding (the sixth walk, defect 2)
                side = row["shown"][k]
                if side in ("more", "less"):
                    fill = PatternFill("solid", fgColor=RED_CELL if side == bad else GREEN_CELL)
                    for col in (a + 2, a + 3):
                        ws.cell(row=r, column=col).fill = fill
            ws.cell(row=r, column=LVR_T).border = Border(left=Side(style="thin", color=SLATE))
            ws.cell(row=r, column=LVR_T).font = Font(name="Calibri", bold=True)
            r += 1
        if not rows:
            ws.cell(row=r, column=2, value="No pocket has enough loans to place.")
            r += 1
        if any(not x["untested"] for x in rows):
            _revenue_chart(ws, hs, rows, first, f"{names[g.band]} x {names[g.dimension]}", b, line,
                           1 + gi * 3, top)
        top = max(r, top + 24) + 2
    # the readings fit "keeps more (not significant)" on one line (the seventh walk, defects 4 and 5)
    widths = [2, 15, 12, 7] + [9, 9, 10, 28, 12] * 3 + [14, 2]
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[_col(j)].width = w
    ws.freeze_panes = "B4"
    _fit(ws)


def _nice_step(span: float) -> float:
    """A round tick step giving about eight ticks over `span`."""
    for step in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50):
        if span / step <= 8:
            return step
    return 100.0


def _revenue_chart(ws, hs, rows, first: int, title: str, b, line, hcol: int, anchor_row: int) -> None:
    """One chart per grid (the third walk, defect 11: one chart for every grid
    counted the same loans six times). GCO's multiple across, on a scale of
    tens, so one pocket at 8x doesn't squash the rest and 1.00x sits on a tick;
    profit's gap in points up. The lines from Control mark the sides (0 when
    profit is read by each pocket's own test), and the three biggest bleeders
    are named."""
    chart = ScatterChart()
    chart.title = title
    chart.style = 13
    chart.x_axis.title = "GCO multiple (right: losing more)"
    chart.y_axis.title = "Profit gap in points (up: keeps more)"
    boxed = [x for x in rows if not x["untested"]]
    last = first + len(boxed) - 1          # untested pockets sort last and stay off
    pts = Series(Reference(ws, min_col=LVR_R + 2, min_row=first, max_row=last),
                 Reference(ws, min_col=LVR_G + 2, min_row=first, max_row=last), title="Pockets")
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
    named = [k for k, x in enumerate(rows) if x["shown"]["gco_rate"] == "more"][:3]
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
    chart.y_axis.majorUnit = step
    chart.x_axis.number_format = '0.00"x"'
    chart.y_axis.number_format = '+0.0" pts";-0.0" pts";0" pts"'
    chart.x_axis.delete = chart.y_axis.delete = False
    chart.x_axis.crosses = "min"           # the multiples along the bottom, not across a profit of 0 (the render)
    chart.width, chart.height = 15, 10
    ws.add_chart(chart, f"{_col(LVR_T + 2)}{anchor_row}")


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
           skip_margins: bool = False) -> None:
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
        _heat(ws, f"{_col(c0 + 1)}{top + 1}:{_col(c0 + len(cols))}{rr - 1}", heat_m, max(shown, default=0.0))


def _grids(ws, res) -> None:
    """Every band crossed with every dimension, as heat maps: the rate, the rate
    against the book, and the rate against the rest of the same band (its peers).
    Red is worse, green better; for profit, a gap in points where more is
    better, below zero is red. A column shown per pocket (median or average)
    gets its own block. A split by a category repeats the grid once per value,
    side by side."""
    names = _names(res)
    _title(ws, "Grids", "Each grid three ways: the rate, the rate against the book, and the rate against the rest "
                        "of the same band. Red is worse, green is better. Profit and contribution are compared as a "
                        "gap in points, and less is red.", "B:Z")
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
        ("High half vs low", "The high half's rate divided by the low half's: 2.00x means the high half goes bad, "
                             "or loses, twice as often. Profit and contribution are a gap in points instead: "
                             "+0.30 pts means the high half keeps 0.30 points more per booked dollar."),
        ("p-value", f"The chance of a gap at least this big if the two halves were no different. Below "
                    f"{1 - conf:.0%} is significant. For the yes/no outcome's share of loans the test measures "
                    f"the gap in standard errors (how far a rate from this many loans typically lands from its "
                    f"true value); for a dollar rate the loans are dealt into the two halves at random inside "
                    f"their pocket, {b.shuffles if b else 0:,} times, and the p-value is how often that made a gap "
                    f"as big. The pocket figures (the heat maps) are after the allowance for many tests "
                    f"({allowance}), across the pockets of one grid and one measure; a gap that is not "
                    f"significant is shown in brackets, unshaded. The summary's figure is one pooled test per "
                    f"grid and measure, with no allowance. Blank: a half has fewer loans or losses than the "
                    f"minimums on Control ({b.min_units if b else 0:,} loans, {b.min_events if b else 0:,} "
                    f"losses)."),
        ("Pooled across pockets", f"The high halves' actual total against what it would be at their low halves' "
                                  f"rates, added over every pocket, with its range at {conf:.0%} sure. For profit "
                                  f"and contribution the difference is taken over the high halves' booked dollars, "
                                  f"in points. For the yes/no outcome only, the odds are pooled too "
                                  f"(Mantel-Haenszel: a standard way to combine pockets without mixing their "
                                  f"loans), with their p-value (Cochran-Mantel-Haenszel), and Cochran's Q checks "
                                  f"whether the gap is about the same size in every pocket."),
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
        ws.row_dimensions[r].height = 58 if k == "p-value" else 44
        r += 1
    r += 1
    heads = ["Measure", "Pockets tested", "High half worse in", "High vs low, pooled", f"Range ({conf:.0%})",
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
            steady = p.get("steady_p")
            if m.in_points:
                # profit: (O - E) over the high halves' booked dollars, in points (NEXT-GOAL 3.2)
                pooled = _shown(p.get("gap"), m)
                rng = (f"{p['gap_lo'] * 100:+.2f} to {p['gap_hi'] * 100:+.2f} pts" if p.get("gap_hi") is not None
                       else "")
            else:
                pooled = p.get("ratio")
                rng = f"{p['ratio_lo']:.2f}x to {p['ratio_hi']:.2f}x" if p.get("ratio_hi") else ""
            vals = [m.title, p.get("pockets", 0),
                    f"{p['high_worse']} of {p['pockets']}" if p.get("pockets") else "none big enough",
                    pooled, rng, p.get("ratio_p"), p.get("odds"), p.get("odds_p"),
                    ("yes/no outcome only" if steady is None else
                     "yes" if steady >= 1 - conf else "no: bigger in some pockets")]
            for i, v in enumerate(vals, start=2):
                ws.cell(row=rr, column=i, value=v).alignment = Alignment(horizontal="left" if i == 2 else "center")
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

            def shown(bl, d, m=m, g=g):
                # a gap that is not significant: in brackets and unshaded (the sixth walk, defect 9)
                got = g.split_compare.get((bl, d), {}).get(m.name)
                if not got or got[0] is None:
                    return None
                v = _shown(got[0], m)
                if got[1] is not None and got[1] < 1 - conf:
                    return v
                return f"({v:+.2f} pts)" if m.in_points else f"({v:.2f}x)"

            _block(ws, r, 2, m.title, g.band_labels, g.dim_labels, shown, _gap_fmt(m), m)
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


def _materiality_tab(ws, res) -> None:
    """The evidence for the materiality call, per grid and measure: what each
    level would keep (the second walk, defect 7: the call was made blind)."""
    names = _names(res)
    line = res.materiality_line
    _title(ws, "Materiality", "What each materiality level would keep: how many pockets, and how much of the "
                              "grid's excess they hold. The level itself is set on Control. A profit shortfall is "
                              "held to the same dollar line as GCO.", "B:F")
    r = 4
    for g in res.grids:
        for m in res.measures:
            if not m.is_rate:
                continue
            ws.cell(row=r, column=2, value=f"{names[g.band]} x {names[g.dimension]}: {m.title}").font = Font(
                name="Calibri", bold=True)
            now = line.get(m.name)
            if now:
                in_use = f"In use: {_amount(now, m)}" + (" (the GCO line)" if m.name in cfgmod.PROFIT else "")
            elif m.name in line:
                in_use = "In use: no line"
            else:
                in_use = "In use: no line (the dollar line on Control is GCO only)"
            ws.cell(row=r, column=6, value=in_use)
            _head(ws, r + 1, [f"Share of the book's {_total_words(m, res)}", f"Excess at or over ({_unit(m)})",
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
    if res.aged_out and not (res.dates and res.dates.window):
        rows.append(("Left out for loan age", f"{res.aged_out:,}"))
    rows += _date_rows(res) + _column_rows(res)
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
            v = res.materiality_line.get(m.name)
            if v is not None and m.name in cfgmod.PROFIT:
                words = f"a shortfall of {_amount(v, m)}: the same dollar line as GCO (Control's materiality answer)"
            else:
                words = _amount(v, m) if v is not None else "no line: the dollar line on Control is a GCO amount"
            rows.append((f"Materiality line: {m.title}", words))
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
                              f"or more, and the exact test (Fisher's) below that. Every dollar rate: the loans are "
                              f"shuffled {b.shuffles:,} times, within the band for the rest of its band; the Test "
                              f"column says how many shuffles made a gap as big. Profit and contribution are "
                              f"compared as a gap in points, never a multiple. The split's odds: "
                              f"Cochran-Mantel-Haenszel, with no continuity correction."))
        # the words the tabs use, defined once (docs/statistics.md, conventions; NEXT-GOAL 3.1)
        rows.append(("p-value", f"The chance of a gap at least this big if there were no real difference, after "
                                f"the allowance for many tests. Below {1 - b.confidence:.0%} is significant, at "
                                f"{b.confidence:.0%} sure. Two-sided: a gap either way counts."))
        rows.append(("Standard error", f"How far a rate worked out from this many loans typically lands from its "
                                       f"true value. A gap of {stats.z_for_confidence(b.confidence):.2f} standard "
                                       f"errors is the {b.confidence:.0%} line."))
    if b is not None and b.many_tests != "none":
        rows.append(("The allowance for many tests covers",
                     "each grid and measure on its own, one comparison at a time (the firm's call, 25 Sep 2026)"))
    if "contribution_rate" in res.total.rates:
        # the definition the tabs rest on (OC-35): the losses inside RANR are GCO
        rows.append(("Contribution before losses", "RANR + GCO, per booked dollar. This assumes RANR has gross "
                                                   "charge-offs taken out (OC-35). If RANR nets recoveries instead, "
                                                   "contribution is overstated by the recoveries."))
    if b is not None:
        said = profit_words(res)
        if per_pocket(res):
            said += f": only a gap that is significant at {b.confidence:.0%}"
        if b.revenue_line is None:
            said += " (the cube file doesn't name one, so this one)"
        rows.append(("Profit counts as more or less", said))
    for q, words in control.describe({**_settings_of(res.config), **_date_settings(res.config)}):
        rows.append((q, words))
    for w in res.warnings:
        rows.append(("Warning", _plain_warning(w)))
    rows += checks.rows(res)                    # fixes 3.15 to 3.18: pre-spec, pocket budget, families, products
    for i, (k, v) in enumerate(rows, start=4):
        ws.cell(row=i, column=2, value=k).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=i, column=2).font = Font(name="Calibri", bold=True)
        ws.cell(row=i, column=3, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 100
    _fit(ws)


def _date_settings(cfg) -> dict:
    """The window and the as-of date as Control names them, when the run used them."""
    out: dict[str, Any] = {}
    if cfg.window_months or cfg.outcome_date:
        out["window_months"] = cfg.window_months
    if (cfg.min_age_months or cfg.window_months) and cfg.as_of is not None:
        out["as_of"] = cfg.as_of if cfg.as_of == cfgmod.AS_OF_LATEST or isinstance(cfg.as_of, date) else "column"
    return out


def _share(k: float, of: float) -> str:
    return f"{k / of:.0%}" if of else "none"


def _date_rows(res) -> list[tuple[str, str]]:
    """Check's lines for the dates (fixes 3.13, 3.14): the as-of date and where
    it came from, the origination range tested, every loan left out by why, and
    how much of the loss the window catches."""
    d = res.dates
    if d is None:
        return []
    rows = [("As-of date", f"{d.as_of.isoformat()}: {d.as_of_from}")]
    rows.append(("Origination range tested", f"{d.first.isoformat()} to {d.last.isoformat()} ({_n(d.kept, 'loan')})"
                 if d.first else "none: no loan is left"))
    if not d.window:
        return rows
    n = d.window
    rows.insert(0, ("Outcome window", f"Bad means it went bad in its first {n} months on book. Only the yes/no "
                                      f"outcome is windowed: GCO and RANR dollars are as the extract has them."))
    for why, k in d.left_out.items():
        rows.append((f"Left out: {why}", f"{k:,}"))
    rows.append((f"Bad after month {n}, so good here", f"{d.bad_after_window:,}"))
    if d.seasoned_bad:
        mtb = sorted(d.seasoned_months_to_bad)
        rows.append((f"How much of the loss {n} months catches",
                     f"Loans {d.seasoned_at} months on book or more: {d.seasoned_loans:,}. By month {n}, "
                     f"{_share(d.seasoned_bad_by, d.seasoned_bad)} of their bad loans had gone bad "
                     f"({d.seasoned_bad_by:,} of {d.seasoned_bad:,}), with "
                     f"{_share(d.seasoned_gco_by, d.seasoned_gco)} of their GCO dollars. "
                     f"Median months to bad: {statistics.median(mtb):g}."))
    else:
        rows.append((f"How much of the loss {n} months catches",
                     f"Can't say: no loan {d.seasoned_at} months on book or more went bad"
                     + ("." if d.seasoned_loans else f" (none is {d.seasoned_at} months on book).")))
    return rows


def _date_lines(res) -> list[str]:
    """The window in one line for the launcher."""
    d = res.dates
    if d is None or not d.window:
        return []
    young = d.left_out.get(engine.YOUNG.format(n=d.window), 0)
    other = d.excluded - young
    return [f"Outcome window {d.window} months: loans made {d.first.isoformat() if d.first else '-'} to "
            f"{d.last.isoformat() if d.last else '-'}; {young:,} under {d.window} months on book left out"
            + (f", and {other:,} more with a date problem (see Check)." if other else ".")]


def _dates_head(res) -> str:
    """What the dates and new columns did, as comments at the top of what ran."""
    out = ""
    d = res.dates
    if d is not None:
        out += f"# as-of date used: {d.as_of.isoformat()} ({d.as_of_from})\n"
        if d.window:
            out += (f"# outcome window: bad in the first {d.window} months on book; origination range tested "
                    f"{d.first} to {d.last}; {d.excluded:,} loans left out; {d.bad_after_window:,} bad after "
                    f"month {d.window}, counted good\n")
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
            "materiality": mat, "min_age_months": cfg.min_age_months, "revenue_line": b.revenue_line}
