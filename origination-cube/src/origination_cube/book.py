"""The workbook: where every decision about a run is made, and where the results land.

Ruling OC-22 (25 Sep 2026). The firm: "my preference is this is either in a GUI
or something the workbook can help with it because i don't want this to be a
technical exercise for users to run nor me to debug." So nobody types a
command. Two buttons in the launcher call the two functions here:

    set_up(extract)   reads the extract and writes the workbook: Start here,
                      Control, Columns, Odd values, Learned. Run it again on
                      the same workbook and every answer already given is kept.
    run(book)         reads the answers from the workbook, runs the cube, and
                      writes the results back into it: Where it bleeds, Grids,
                      Check, Log. Beside it, cube.yaml records exactly what ran.

A problem is never a traceback. Everything that stops a run is a sentence
naming the tab and cell to fix, shown in the launcher and written to the Log
and Start here tabs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from . import config as cfgmod
from . import control, engine, meanings, memory, profile
from .ingest import read_table

INK, CANVAS, SLATE, PAPER, NEEDS = "16130F", "F4F1EC", "57534B", "FFFFFF", "FCE4C4"
WORSE_FILL, LUCK_FILL = "F7DEDE", "FFF1D6"
INPUT_TABS = ("Start here", "Control", "Columns", "Odd values", "Learned")
RESULT_TABS = ("Where it bleeds", "Grids", "Check", "Log")
ABOUT = "_about"
COL_FIRST = 6            # first column row on the Columns tab
CONFIRM_CELL = "C3"      # "Checked every column?"


@dataclass
class Outcome:
    ok: bool
    book: Path
    lines: list[str] = field(default_factory=list)      # what the launcher shows, in plain words


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


def _shade_blank(ws, rng: str, first_cell: str) -> None:
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'{first_cell}=""'],
                                                   fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))


# --------------------------------------------------------------------------
# Reading what a person has already answered, so set_up never throws it away


def _answers(book: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"control": {}, "columns": {}, "confirmed": None, "odd": {}}
    if not book.exists():
        return out
    wb = load_workbook(book)
    if control.SHEET in wb.sheetnames:
        ws = wb[control.SHEET]
        for r in ws.iter_rows(min_row=control.FIRST_ROW):
            key = r[control.KEY_COL - 1].value
            if key:
                out["control"][key] = (r[control.CHOOSE_COL - 1].value, r[control.OWN_COL - 1].value)
    if "Columns" in wb.sheetnames:
        ws = wb["Columns"]
        out["confirmed"] = ws[CONFIRM_CELL].value
        for r in ws.iter_rows(min_row=COL_FIRST, values_only=True):
            if r[1]:
                out["columns"][str(r[1])] = {"means": r[2], "is": r[3], "edges": r[4]}
    if "Odd values" in wb.sheetnames:
        for r in wb["Odd values"].iter_rows(min_row=5, values_only=True):
            if r[1]:
                out["odd"][(str(r[1]), str(r[6]))] = r[4]
    return out


# --------------------------------------------------------------------------


def set_up(extract: str | Path, book: str | Path | None = None, memory_path: str | Path | None = None,
           today: date | None = None) -> Outcome:
    extract = Path(extract)
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
    looks = meanings.review(table, sugg, open_qs, cat)

    wb = Workbook()
    wb.remove(wb.active)
    start = wb.create_sheet("Start here")
    control.write_control(wb, control.load_settings())
    ws_c = wb[control.SHEET]
    for r in ws_c.iter_rows(min_row=control.FIRST_ROW):
        key = r[control.KEY_COL - 1].value
        if key in kept["control"]:
            choose, own = kept["control"][key]
            r[control.CHOOSE_COL - 1].value = choose
            if own not in (None, "n/a"):
                r[control.OWN_COL - 1].value = own

    # ---- Columns
    ws = wb.create_sheet("Columns")
    _title(ws, "Columns", "What each column is. Anything shaded in the Look first column is worth a second look "
                          "before you run; the reason is beside it. Change a column's meaning from the list if "
                          "it's wrong. Then set Checked every column to Yes: nothing runs until you do, and what "
                          "you confirm is remembered for next time.", "B:I")
    ws["B3"] = "Checked every column?"
    ws["B3"].font = Font(name="Calibri", bold=True)
    ws[CONFIRM_CELL] = kept["confirmed"] if kept["confirmed"] in ("Yes", "No") else None
    dv_yes = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True, showErrorMessage=True)
    ws.add_data_validation(dv_yes)
    dv_yes.add(ws[CONFIRM_CELL])
    ws.conditional_formatting.add(CONFIRM_CELL, FormulaRule(formula=[f'{CONFIRM_CELL}<>"Yes"'],
                                                            fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))
    blocking = [rv for rv in looks if rv.kind == "cannot run"]
    ws["D3"] = (" ".join(rv.says for rv in blocking)) if blocking else ""
    ws["D3"].font = Font(name="Calibri", bold=True, color="960019")
    _head(ws, 5, ["Column", "What it is", "Yes means (outcome only)", "Band edges (optional)", "Look first",
                  "Why this was suggested", "Blank", "Samples"])
    mm = wb.create_sheet("_meanings")
    for i, m in enumerate(cat, start=1):
        mm.cell(row=i, column=1, value=m)
        mm.cell(row=i, column=2, value=cat[m].says)
    mm.sheet_state = "hidden"
    dv_m = DataValidation(type="list", formula1=f"='_meanings'!$A$1:$A${len(cat)}", allow_blank=False,
                          showErrorMessage=True)
    dv_m.error = "Pick one of the meanings in the list."
    ws.add_data_validation(dv_m)
    by_col: dict[str, list[str]] = {}
    for rv in looks:
        if rv.kind != "cannot run":
            by_col.setdefault(rv.column, []).append(rv.says)
    classified = {c.name: c for c in cols}
    r = COL_FIRST
    for c in table.columns:
        sg = sugg[c]
        prior = kept["columns"].get(c, {})
        means = prior.get("means") if prior.get("means") in cat else sg.means
        tag = "Remembered: " if sg.source == "remembered" else ""
        f = meanings.facts(table, c)
        blank = (f.rows - f.nonblank) / f.rows if f.rows else 0
        ws.cell(row=r, column=2, value=c).font = Font(name="Calibri", bold=True)
        ws.cell(row=r, column=3, value=means)
        dv_m.add(ws.cell(row=r, column=3))
        ws.cell(row=r, column=4, value=prior.get("is") if prior else sg.is_value)
        ws.cell(row=r, column=5, value=prior.get("edges"))
        ws.cell(row=r, column=6, value=" ".join(by_col.get(c, [])) or None)
        ws.cell(row=r, column=7, value=tag + sg.why)
        ws.cell(row=r, column=8, value=blank).number_format = "0%"
        ws.cell(row=r, column=9, value=", ".join(classified[c].samples[:3]) if c in classified else "")
        for col in range(2, 10):
            ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top")
        r += 1
    ws.conditional_formatting.add(f"F{COL_FIRST}:F{r}", FormulaRule(
        formula=[f'F{COL_FIRST}<>""'], fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))
    for col, w in zip("ABCDEFGHI", (2, 22, 18, 14, 16, 48, 44, 7, 30)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = f"C{COL_FIRST}"
    _fit(ws)

    # ---- Odd values
    wo = wb.create_sheet("Odd values")
    _title(wo, "Odd values", "Things in the data that could be a code rather than a real value. None of them stops "
                             "a run: until you answer, the values are used as they are. Answer real, or missing "
                             "(treated as blank and counted). Your answers are remembered.", "B:G")
    _head(wo, 4, ["Column", "What looks odd", "Rows", "Answer", "Note"])
    dv_a = DataValidation(type="list", formula1='"real,missing"', allow_blank=True, showErrorMessage=True)
    wo.add_data_validation(dv_a)
    r = 5
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
        dv_a.add(wo.cell(row=r, column=5))
        wo.cell(row=r, column=6, value=f"Remembered: you answered {known['answer']} on {known.get('last')}"
                if known else None)
        wo.cell(row=r, column=7, value=key[1])          # hidden: how the answer is matched
        r += 1
    if r == 5:
        wo.cell(row=5, column=2, value="Nothing odd found.")
    else:
        _shade_blank(wo, f"E5:E{r - 1}", "E5")
    for col, w in zip("ABCDEFG", (2, 22, 50, 10, 12, 44, 10)):
        wo.column_dimensions[col].width = w
    wo.column_dimensions["G"].hidden = True
    _fit(wo)

    # ---- Learned
    _learned_tab(wb, memory_path)

    # ---- about, then Start here last so it can count everything above
    about = wb.create_sheet(ABOUT)
    about["A1"], about["B1"] = "extract", str(extract.resolve())
    about["A2"], about["B2"] = "sha256", hashlib.sha256(extract.read_bytes()).hexdigest()
    about["A3"], about["B3"] = "set up", (today or date.today()).isoformat()
    about.sheet_state = "hidden"
    unanswered = sum(1 for s in control.load_settings() if s.judgment
                     and not any(kept["control"].get(s.key, (None, None))))
    _start_here(start, extract, len(table.rows), len(table.columns), looks, len(qs), unanswered, None)
    _order(wb)
    try:
        wb.save(book)
    except PermissionError:
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Set up again."])
    lines = [f"Set up {book.name} from {extract.name}: {len(table.rows):,} loans, {len(table.columns)} columns."]
    if looks:
        lines.append(f"{len(looks)} thing(s) to look at first, on the Columns tab.")
    lines.append("Next: fill in the shaded cells on Control and Columns, save, close, and press Run.")
    return Outcome(True, book, lines)


def _order(wb) -> None:
    """Start here first, the inputs, then the results, then the hidden helpers."""
    want = list(INPUT_TABS) + list(RESULT_TABS)
    wb._sheets.sort(key=lambda ws: (want.index(ws.title) if ws.title in want else len(want)))
    wb.active = 0
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = ws.title == "Start here"


def _learned_tab(wb, memory_path) -> None:
    ws = wb.create_sheet("Learned")
    ws["A1"] = ("Everything the cube has learned from files you confirmed. Set a row to Forget if it shouldn't "
                "have been learned; it's dropped the next time you press Run.")
    ws["A1"].font = Font(italic=True, size=10)
    heads = ["Keep?", "Kind", "Column", "What it learned", "First confirmed", "Last confirmed", "Times", "id"]
    for i, h in enumerate(heads, start=1):
        c = ws.cell(row=3, column=i, value=h)
        c.font = Font(bold=True, color=PAPER)
        c.fill = PatternFill("solid", fgColor=INK)
    dv = DataValidation(type="list", formula1=f'"{memory.KEEP},{memory.FORGET}"', allow_blank=False)
    ws.add_data_validation(dv)
    rows = memory.rows(memory.load(memory_path))
    for rw in rows:
        ws.append([memory.KEEP, rw["kind"], rw["column"], rw["learned"], rw["first"], rw["last"], rw["times"],
                   rw["id"]])
        dv.add(ws.cell(row=ws.max_row, column=1))
    if not rows:
        ws.cell(row=4, column=3, value="Nothing learned yet.")
    for col, w in zip("ABCDEFGH", (9, 9, 22, 44, 15, 15, 7, 30)):
        ws.column_dimensions[col].width = w
    ws.column_dimensions["H"].hidden = True
    ws["A1"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A1:G1")
    ws.row_dimensions[1].height = 30
    _fit(ws)


def _start_here(ws, extract, rows, ncols, looks, nq, unanswered, last_run) -> None:
    for rng in list(ws.merged_cells.ranges):
        ws.unmerge_cells(str(rng))
    for row in ws.iter_rows():
        for c in row:
            c.value = None
    _title(ws, "Origination Cube", f"Where does the book bleed? Set up from {Path(extract).name}: {rows:,} loans, "
                                   f"{ncols} columns.", "B:D")
    ws.unmerge_cells("B2:D2")
    steps = [
        ("1", "Control", "Fill in the shaded cells. Those are our calls: what's material, how many loans is "
                         "enough, how much worse counts as worse."),
        ("2", "Columns", "Check what each column is; anything shaded has a reason beside it. Fix any that's "
                         "wrong from the list, then set Checked every column to Yes."),
        ("3", "Odd values", "Answer what you can: real, or missing. Anything unanswered is used as it is."),
        ("4", "Launcher", "Save, close this workbook, and press Run the cube. Results land in the tabs on the "
                          "right."),
    ]
    ws["B4"], ws["C4"], ws["D4"] = "Step", "Where", "What to do"
    for c in ("B4", "C4", "D4"):
        ws[c].font = Font(bold=True, color=PAPER)
        ws[c].fill = PatternFill("solid", fgColor=INK)
    for i, (n, where, what) in enumerate(steps, start=5):
        ws.cell(row=i, column=2, value=n)
        ws.cell(row=i, column=3, value=where).font = Font(bold=True)
        ws.cell(row=i, column=4, value=what).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 30
    ws["B11"] = "Where things stand"
    ws["B11"].font = Font(bold=True, size=12)
    status = [
        ("Calls still to make on Control", unanswered),
        ("Things to look at first on Columns", len(looks)),
        ("Odd values found", nq),
        ("Last run", last_run or "not run yet"),
    ]
    for i, (k, v) in enumerate(status, start=12):
        ws.cell(row=i, column=3, value=k)
        ws.cell(row=i, column=4, value=v).alignment = Alignment(horizontal="left")
    for col, w in zip("ABCD", (2, 7, 38, 90)):
        ws.column_dimensions[col].width = w
    ws.merge_cells("B2:D2")
    _fit(ws)


def _fit(ws, landscape: bool = True) -> None:
    """Every tab prints one page wide (the walk found Start here split across two)."""
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


# --------------------------------------------------------------------------


def read_book(book: Path, memory_path=None) -> tuple[dict | None, list[str], dict]:
    """The cube file a workbook describes, as a dict, and every problem in it
    named by tab and cell. Nothing is run."""
    problems: list[str] = []
    wb = load_workbook(book)
    missing_tabs = [t for t in ("Control", "Columns", "Odd values", ABOUT) if t not in wb.sheetnames]
    if missing_tabs:
        return None, [f"This workbook is missing its {', '.join(missing_tabs)} tab(s). Press Set up again."], {}
    about = {wb[ABOUT][f"A{i}"].value: wb[ABOUT][f"B{i}"].value for i in range(1, 4)}
    try:
        use = control.read_control(book)
    except control.ControlError as exc:
        problems += exc.problems
        use = {}
    ws = wb["Columns"]
    confirmed = ws[CONFIRM_CELL].value == "Yes"
    if not confirmed:
        problems.append(f"Columns!{CONFIRM_CELL}: set Checked every column to Yes once you've checked what each "
                        f"column is.")
    columns, edges = {}, {}
    for r in ws.iter_rows(min_row=COL_FIRST):
        name = r[1].value
        if not name:
            continue
        means, is_value, e = r[2].value, r[3].value, r[4].value
        if not means:
            problems.append(f"Columns!C{r[1].row}: `{name}` has no meaning. Pick one from the list.")
            continue
        columns[str(name)] = {"means": means, "is": is_value} if is_value not in (None, "") else means
        if e not in (None, ""):
            try:
                pts = [float(x) for x in str(e).replace(";", ",").split(",") if x.strip()]
                if not pts or any(b <= a for a, b in zip(pts, pts[1:])):
                    raise ValueError
                edges[str(name)] = pts
            except ValueError:
                problems.append(f"Columns!E{r[1].row}: band edges for `{name}` must be rising numbers "
                                f"separated by commas, like 620, 680, 740.")
    questions = []
    wo = wb["Odd values"]
    for r in wo.iter_rows(min_row=5, values_only=True):
        if not r[1] or not r[6]:
            continue
        pattern, _, value = str(r[6]).partition("|")
        questions.append({"column": r[1], "pattern": pattern, "value": float(value) if value else None,
                          "rows": r[3] or 0, "answer": r[4] or None})
    if problems:
        return None, problems, about
    cat = meanings.catalog()
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
        if m not in cat:
            continue
        if cat[m].cut == "band":
            b = {"name": uniq(profile._slug(c)), "field": c}
            b.update({"edges": edges[c]} if c in edges else {"count": int(use["band_count"]),
                                                              "cut": use["band_cut"]})
            raw_bands.append(b)
        elif cat[m].cut == "dimension":
            raw_dims.append({"name": uniq(profile._slug(c)), "field": c})
    raw = {
        "name": profile._slug(Path(about.get("extract") or book.stem).stem),
        "schema_version": cfgmod.SCHEMA_VERSION,
        "columns_confirmed": True,
        "columns": columns,
        "bands": raw_bands,
        "dimensions": raw_dims,
        "measures": [{"name": "loans", "mode": "count"}],
        "min_age_months": int(use["min_age_months"]),
        "benchmark": {"min_units": int(use["min_loans"]), "min_events": int(use["min_events"]),
                      "worse_at": float(use["worse_at"]), "better_at": float(use["better_at"]),
                      "confidence": float(use["confidence"]), "power": float(use["power"]),
                      "compare_to": use["compare_to"], "many_tests": use["many_tests"],
                      "materiality": use["materiality"]},
        "questions": questions or [],
    }
    return raw, [], about


def run(book: str | Path, memory_path: str | Path | None = None) -> Outcome:
    book = Path(book)
    if not book.exists():
        return Outcome(False, book, [f"Couldn't find {book.name}. Press Set up first."])
    raw, problems, about = read_book(book, memory_path)
    if raw is not None:
        try:
            cfg = cfgmod.parse(raw)
        except cfgmod.ConfigError as exc:
            problems = [_plain(p) for p in exc.problems]
    if problems:
        _log(book, ["Couldn't run. Fix these, save, close, and press Run again:"] + problems)
        return Outcome(False, book, ["Couldn't run yet. Fix these in the workbook, save, close, and press Run "
                                     "again:"] + [f"  - {p}" for p in problems])
    extract = Path(about["extract"])
    if not extract.exists():
        return Outcome(False, book, [f"The extract this workbook was set up from is gone: {extract}. "
                                     f"Put it back, or press Set up with the new one."])
    table = read_table(extract)
    if hashlib.sha256(extract.read_bytes()).hexdigest() != about.get("sha256"):
        note = [f"Note: {extract.name} has changed since set up. Its columns were read again at set up only; "
                f"press Set up if columns were added or renamed."]
    else:
        note = []
    try:
        res = engine.run(cfg, table)
    except (engine.ColumnsMissing, engine.NothingToCut) as exc:
        _log(book, ["Couldn't run:", str(exc)])
        return Outcome(False, book, [f"Couldn't run: {exc}"])
    memory.apply_review(book, memory_path)
    mpath, n = memory.remember(cfg, memory_path)
    audit = book.with_name(f"{book.stem} - what ran.yaml")
    audit.write_text("# Exactly what the last Run used, for the record.\n"
                     + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    try:
        _write_results(book, res, memory_path)
    except PermissionError:
        return Outcome(False, book, [f"{book.name} is open in Excel. Close it, then press Run again."])
    top = _top_lines(res)
    return Outcome(True, book, note + [f"Ran on {res.rows:,} loans; {res.tie_outs:,} tie-out checks agree."]
                   + top + [f"Remembered {n} confirmed answers for next time.", f"Open {book.name}: the results "
                                                                                   f"are on Where it bleeds."])


PLAIN = {
    "`dimensions:` needs at least one entry": "Nothing is left to cut across: mark at least one column as a "
                                             "category (or term) on the Columns tab.",
    "`bands:` needs at least one entry": "Nothing is left to cut into bands: mark at least one number column as "
                                        "fico, score, dti, ltv, rate or amount on the Columns tab.",
}


def _plain(problem: str) -> str:
    """A cube-file problem, in workbook terms: nobody at the desk sees the cube file."""
    if problem in PLAIN:
        return PLAIN[problem]
    return (problem.replace("`columns:` needs exactly one column that means", "Columns: exactly one column must be")
            .replace("`columns:`", "the Columns tab").replace("`", '"'))


def _top_lines(res) -> list[str]:
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
                        best = (s.excess, f"{g.band} {b} / {g.dimension} {d}")
        if best:
            out.append(f"Worst for {m.title}: {best[1]}.")
    return out


# --------------------------------------------------------------------------
# Results


def _log(book: Path, lines: list[str]) -> None:
    try:
        wb = load_workbook(book)
    except Exception:
        return
    ws = wb["Log"] if "Log" in wb.sheetnames else wb.create_sheet("Log")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.insert_rows(1, amount=len(lines) + 1)
    for i, line in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=stamp if i == 1 else None)
        ws.cell(row=i, column=2, value=line)
    ws.column_dimensions["A"].width = 17
    ws.column_dimensions["B"].width = 140
    if "Start here" in wb.sheetnames:
        wb["Start here"]["D15"] = f"{stamp}: couldn't run; see the Log tab" if "Couldn't" in lines[0] else stamp
    _order(wb)
    try:
        wb.save(book)
    except PermissionError:
        pass


def _write_results(book: Path, res, memory_path) -> None:
    wb = load_workbook(book)
    for t in ("Where it bleeds", "Grids", "Check", "Learned"):
        if t in wb.sheetnames:
            del wb[t]
    _learned_tab(wb, memory_path)
    _bleeds(wb.create_sheet("Where it bleeds"), res)
    _grids(wb.create_sheet("Grids"), res)
    _check(wb.create_sheet("Check"), res)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "Start here" in wb.sheetnames:
        wb["Start here"]["D15"] = f"{stamp}: {res.rows:,} loans, {res.tie_outs:,} tie-out checks agree"
    _order(wb)
    wb.save(book)
    _log(book, [f"Ran on {res.rows:,} loans; {res.tie_outs:,} tie-out checks agree."] +
         [f"Warning: {w}" for w in res.warnings])


def _bleeds(ws, res) -> None:
    b = res.config.benchmark
    judged = "the rest of its band" if b and b.compare_to == "peers" else "the rest of the book"
    _title(ws, "Where it bleeds", f"Every pocket losing more than its share (or, for RANR, earning less), largest "
                                  f"first within each measure. The flag is judged against {judged}. Shaded red: "
                                  f"worse. Shaded amber: worse, but could be luck.", "B:Q")
    heads = ["Measure", "Band", "Pocket", "Dimension", "Pocket", "Loans", "Rate", "Book rate", "Excess",
             "Material", "vs rest of book", "p", "vs rest of band", "p", "Flag", "Smallest gap it could show"]
    _head(ws, 4, heads)
    r = 5
    for m in res.measures:
        if not m.is_rate:
            continue
        found = []
        for g in res.grids:
            for (bl, dl), c in g.inner():
                s = c.rates[m.name]
                if s.excess is not None and s.excess > 0:
                    found.append((s.excess, g, bl, dl, s))
        for ex, g, bl, dl, s in sorted(found, key=lambda t: -t[0]):
            vals = [m.title, g.band, bl, g.dimension, dl, s.units, s.rate, res.total.rates[m.name].rate, ex,
                    {True: "yes", False: "below the line", None: ""}[s.material], s.vs_rest, s.p_book, s.vs_band,
                    s.p_band, s.flag or "", s.smallest_gap]
            for i, v in enumerate(vals, start=2):
                ws.cell(row=r, column=i, value=v)
            for col, fmt in ((8, "0.00%"), (9, "0.00%"), (10, "#,##0"), (12, '0.00"x"'), (13, "0.0000"),
                             (14, '0.00"x"'), (15, "0.0000"), (17, '0.00"x"')):
                ws.cell(row=r, column=col).number_format = fmt
            r += 1
    if r == 5:
        ws.cell(row=5, column=2, value="Nothing is losing more than its share at these settings.")
    ws.conditional_formatting.add(f"B5:Q{max(r, 6)}", FormulaRule(formula=['$P5="worse"'],
                                                                  fill=PatternFill("solid", fgColor=WORSE_FILL,
                                                                                   bgColor=WORSE_FILL)))
    ws.conditional_formatting.add(f"B5:Q{max(r, 6)}", FormulaRule(formula=['$P5="worse, but could be luck"'],
                                                                  fill=PatternFill("solid", fgColor=LUCK_FILL,
                                                                                   bgColor=LUCK_FILL)))
    for col, w in zip("ABCDEFGHIJKLMNOPQ", (2, 30, 10, 22, 11, 11, 8, 8, 10, 13, 15, 13, 9, 13, 9, 24, 13)):
        ws.column_dimensions[col].width = w
    ws.row_dimensions[4].height = 30
    ws.freeze_panes = "B5"
    _fit(ws)


def _grids(ws, res) -> None:
    _title(ws, "Grids", "Every band crossed with every dimension, one block per measure: each pocket's rate, then "
                        "its rate over the book's.", "B:J")
    r = 4
    for g in res.grids:
        for m in res.measures:
            if not m.is_rate:
                continue
            ws.cell(row=r, column=2, value=f"{g.band} x {g.dimension}: {m.title}   ({m.label()})").font = Font(
                bold=True)
            r += 1
            cols = g.dim_labels + [engine.ALL]
            ws.cell(row=r, column=2, value="Rate")
            for j, d in enumerate(cols, start=3):
                ws.cell(row=r, column=j, value=d).font = Font(bold=True)
            r += 1
            for bl in g.band_labels + [engine.ALL]:
                ws.cell(row=r, column=2, value=bl)
                for j, d in enumerate(cols, start=3):
                    c = g.cells.get((bl, d))
                    if c is not None and c.rates[m.name].rate is not None:
                        ws.cell(row=r, column=j, value=c.rates[m.name].rate).number_format = "0.00%"
                r += 1
            ws.cell(row=r, column=2, value="Over the book's rate").font = Font(italic=True)
            r += 1
            for bl in g.band_labels + [engine.ALL]:
                ws.cell(row=r, column=2, value=bl)
                for j, d in enumerate(cols, start=3):
                    c = g.cells.get((bl, d))
                    if c is not None and c.rates[m.name].vs_topline is not None:
                        ws.cell(row=r, column=j, value=c.rates[m.name].vs_topline).number_format = '0.00"x"'
                r += 1
            r += 1
    ws.column_dimensions["B"].width = 26
    for j in range(3, 12):
        ws.column_dimensions[chr(ord("A") + j - 1)].width = 13
    _fit(ws)


def _check(ws, res) -> None:
    _title(ws, "Check", "What the run checked and used, for the record.", "B:D")
    rows = [("Loans run", f"{res.rows:,}"), ("Tie-out checks", f"{res.tie_outs:,} of {res.tie_outs:,} agree: "
                                                                f"every grid adds up to the book")]
    if res.aged_out:
        rows.append(("Left out for loan age", f"{res.aged_out:,}"))
    for m in res.measures:
        lo = res.left_out.get(m.name)
        if lo:
            rows.append((f"Left out of {m.title}", "; ".join(f"{k:,} x {col} {why}" for (col, why), k in lo.items())))
    for name, e in res.band_edges.items():
        rows.append((f"Band edges used: {name}", ", ".join(engine._fmt(x) for x in e)))
    for ln in res.loans_needed.values():
        rows.append(("What this book can show", ln.sentence()))
    for m, v in res.materiality_line.items():
        rows.append((f"Materiality line: {m}", f"{v:,.0f}"))
    for q, words in control.describe({**_settings_of(res.config)}):
        rows.append((f"Setting: {q}", words))
    for w in res.warnings:
        rows.append(("Warning", w))
    for i, (k, v) in enumerate(rows, start=4):
        ws.cell(row=i, column=2, value=k).font = Font(bold=True)
        ws.cell(row=i, column=3, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 120
    _fit(ws)


def _settings_of(cfg) -> dict:
    b = cfg.benchmark
    if b is None:
        return {}
    mat = {"none": "none", "share": f"{b.materiality[1] * 100:g}% of losses"}.get(b.materiality[0], b.materiality[1])
    return {"min_loans": b.min_units, "min_events": b.min_events, "worse_at": b.worse_at, "better_at": b.better_at,
            "confidence": b.confidence, "power": b.power, "compare_to": b.compare_to, "many_tests": b.many_tests,
            "materiality": mat, "min_age_months": cfg.min_age_months}
