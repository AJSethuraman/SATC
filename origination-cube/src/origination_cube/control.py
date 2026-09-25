"""The control center: every setting of a run on one Excel tab.

Each setting has a dropdown of options and a cell for your own value. Two
more cells are Excel formulas: the value in use, and what the chosen option
means. The options and their explanations come from `settings.yaml` and
nowhere else, so the tab, the run and the docs cannot drift apart.

Reading back does not depend on Excel having recalculated. Python reads the
dropdown and the override cells directly: your own value wins when it is
filled in. A setting with neither is refused and named.

Two kinds of setting (settings.yaml says which). A judgment setting - is it
material, is it enough loans, how much worse counts - opens blank and the
run refuses until someone answers it: the tool never decides what matters.
A method setting - how bands are cut, which multiple-test allowance - opens
on its recommended option, which is printed on every output.

The tab does not label which is which. The firm, 25 Sep 2026: "i don't want
things to be labeled 'your judgment' that is very AI coded ... conditionally
format the workbook to indicate where we must enter things and provide
instructions that don't sound robotic." So a cell that still needs an answer
is shaded by conditional formatting, and the shading goes away once it is
answered; the instructions at the top are written the way the firm talks.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

SHEET = "Control"
OPTIONS_SHEET = "_options"
RECOMMENDED = " (recommended)"
FIRST_ROW = 5
KEY_COL, CHOOSE_COL, OWN_COL = 8, 3, 4            # H, C, D
NEEDS = "FCE4C4"          # the shade on a cell that still needs an answer
INSTRUCTIONS = (
    "Fill in the shaded cells before running. Those are the calls we make on every job: "
    "what's material, how many loans is enough to matter, and how much worse than its peers a pocket has to be. "
    "Everything else starts on a reasonable setting, so change it only if the population calls for it. "
    "Pick from the list, or type your own number in the next column and that wins. "
    "If a row says re-run, run the script again after changing it."
)

INK, CANVAS, MIST, SLATE, PAPER, KEY_RED = "16130F", "F4F1EC", "E4DFD5", "57534B", "FFFFFF", "CC0000"


class ControlError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass(frozen=True)
class Option:
    value: Any
    label: str
    explains: str
    recommended: bool = False

    @property
    def shown(self) -> str:
        return self.label + (RECOMMENDED if self.recommended else "")


@dataclass(frozen=True)
class Setting:
    key: str
    question: str
    takes_effect: str
    override: str | None
    options: tuple[Option, ...]
    group: str
    judgment: bool = False
    valid: dict | None = None        # {min, max, whole}: what a typed value may be
    def recommended(self) -> Option | None:
        return next((o for o in self.options if o.recommended), None)


def load_settings(path: str | Path | None = None) -> list[Setting]:
    text = (Path(path).read_text(encoding="utf-8") if path
            else resources.files("origination_cube").joinpath("settings.yaml").read_text(encoding="utf-8"))
    raw = yaml.safe_load(text)
    out = []
    for g in raw["groups"]:
        for s in g["settings"]:
            opts = tuple(Option(value=o["value"], label=str(o["label"]), explains=" ".join(str(o["explains"]).split()),
                                recommended=bool(o.get("recommended", False))) for o in s["options"])
            out.append(Setting(key=s["key"], question=s["question"], takes_effect=s["takes_effect"],
                               override=s.get("override"), options=opts, group=g["title"],
                               judgment=bool(s.get("judgment", False)), valid=s.get("valid")))
    return out


# --------------------------------------------------------------------------


def write_control(wb: Workbook, settings: list[Setting]) -> None:
    ws = wb.create_sheet(SHEET, 0) if SHEET not in wb.sheetnames else wb[SHEET]
    opt = wb.create_sheet(OPTIONS_SHEET)
    opt.append(["lookup", "setting", "option", "value", "what it means", "your own value accepts", "plain"])
    ranges: dict[str, tuple[int, int]] = {}
    for s in settings:
        first = opt.max_row + 1
        for o in s.options:
            opt.append([f"{s.key}|{o.shown}", s.key, o.shown, o.value, o.explains, s.override or "", o.label])
        ranges[s.key] = (first, opt.max_row)
    opt.sheet_state = "hidden"

    thin = Side(style="thin", color=MIST)
    ws.sheet_view.showGridLines = False
    widths = {"A": 2, "B": 34, "C": 44, "D": 19, "E": 22, "F": 62, "G": 13, "H": 12}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.merge_cells("B1:G1")
    ws["B1"] = "Control center"
    ws["B1"].font = Font(name="Arial", bold=True, size=16, color=PAPER)
    for c in "BCDEFG":
        ws[f"{c}1"].fill = PatternFill("solid", fgColor=INK)
    ws.row_dimensions[1].height = 28
    ws.merge_cells("B2:G2")
    ws["B2"] = INSTRUCTIONS
    ws["B2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws["B2"].font = Font(name="Calibri", size=10, color=SLATE)
    ws.row_dimensions[2].height = 44
    ws["B3"] = "Shaded = still needs an answer"
    ws["B3"].fill = PatternFill("solid", fgColor=NEEDS)
    ws["B3"].font = Font(name="Calibri", size=9, color=INK)
    heads = ["Setting", "Choose", "Or enter your own", "In use", "What it means", "Takes effect", "key"]
    for i, h in enumerate(heads):
        c = ws.cell(row=4, column=2 + i, value=h)
        c.font = Font(name="Calibri", bold=True, color=PAPER)
        c.fill = PatternFill("solid", fgColor=INK)
    ws.freeze_panes = "C5"

    r = FIRST_ROW
    group = None
    for s in settings:
        if s.group != group:
            group = s.group
            ws.cell(row=r, column=2, value=group).font = Font(name="Calibri", bold=True, color=INK)
            for col in range(2, 9):
                ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=CANVAS)
            r += 1
        first, last = ranges[s.key]
        ws.cell(row=r, column=2, value=s.question)
        rec = s.recommended()
        choose = ws.cell(row=r, column=CHOOSE_COL, value=None if s.judgment or rec is None else rec.shown)
        dv = DataValidation(type="list", formula1=f"='{OPTIONS_SHEET}'!$C${first}:$C${last}", allow_blank=True,
                            showDropDown=False, showErrorMessage=True)
        dv.errorTitle = "Pick from the list"
        dv.error = "Pick one of the listed options. To use your own number, type it in the next column."
        ws.add_data_validation(dv)
        dv.add(choose)
        own = ws.cell(row=r, column=OWN_COL)
        if s.override is not None and s.valid:
            v = s.valid
            dvo = DataValidation(type="whole" if v.get("whole") else "decimal", operator="between",
                                 formula1=str(v["min"]), formula2=str(v["max"]), allow_blank=True,
                                 showErrorMessage=True)
            dvo.errorTitle = "Out of range"
            dvo.error = f"Enter {s.override}, from {v['min']:g} to {v['max']:g}."
            ws.add_data_validation(dvo)
            dvo.add(own)
        if s.override is None:
            own.value = "n/a"
            own.font = Font(name="Calibri", italic=True, color=SLATE)
            own.fill = PatternFill("solid", fgColor=MIST)
        C, D, H = f"C{r}", f"D{r}", f"$H{r}"
        # shaded while unanswered, on any row: a method setting someone clears needs an answer too.
        # A row with no own-value cell shades only its dropdown (the grey n/a cell is not an answer).
        ws.conditional_formatting.add(
            f"C{r}:D{r}" if s.override is not None else f"C{r}",
            FormulaRule(formula=[f'AND($C{r}="",OR($D{r}="",$D{r}="n/a"))'],
                        fill=PatternFill("solid", fgColor=NEEDS, bgColor=NEEDS)))
        own_set = f'AND({D}<>"",{D}<>"n/a")'
        lookup = f"MATCH({H}&\"|\"&{C},{OPTIONS_SHEET}!$A:$A,0)"
        ws.cell(row=r, column=5, value=(f'=IF({own_set},{D},IF({C}="","",'
                                        f'IFERROR(INDEX({OPTIONS_SHEET}!$G:$G,{lookup}),"not an option")))'))
        note = f"Your own value, in place of the options ({s.override})." if s.override else ""
        ws.cell(row=r, column=6, value=(f'=IF({own_set},"{note}",IF({C}="","Needs an answer before we run. '
                                        f'Pick one, or enter your own.",'
                                        f'IFERROR(INDEX({OPTIONS_SHEET}!$E:$E,{lookup}),"That isn\'t one of the '
                                        f'options. Pick from the list, or put your number in the next column.")))'))
        ws.cell(row=r, column=7, value=s.takes_effect)
        k = ws.cell(row=r, column=KEY_COL, value=s.key)
        k.font = Font(name="Consolas", size=8, color=SLATE)
        for col in range(2, 9):
            cell = ws.cell(row=r, column=col)
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if col != OWN_COL and col != KEY_COL and cell.font.color is None:
                cell.font = Font(name="Calibri", size=10, color=INK)
        ws.cell(row=r, column=5).font = Font(name="Calibri", bold=True, color=INK)
        r += 1
    ws.column_dimensions["H"].hidden = True
    ws.print_area = f"B1:G{r - 1}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def build_control_book(out: str | Path, settings: list[Setting] | None = None) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    write_control(wb, settings or load_settings())
    p = Path(out)
    wb.save(p)
    return p


# --------------------------------------------------------------------------


def read_control(path: str | Path, settings: list[Setting] | None = None) -> dict[str, Any]:
    """The settings in use, read from the cells a person edits. Refuses, all
    at once, any setting left with nothing chosen, an unknown option, or an
    own value the setting cannot take."""
    settings = settings or load_settings()
    by_key = {s.key: s for s in settings}
    ws = load_workbook(path)[SHEET]
    found: dict[str, Any] = {}
    seen: set[str] = set()
    problems: list[str] = []
    for row in ws.iter_rows(min_row=FIRST_ROW):
        key = row[KEY_COL - 1].value
        if key not in by_key:
            continue
        s = by_key[key]
        seen.add(key)
        chosen, own = row[CHOOSE_COL - 1].value, row[OWN_COL - 1].value
        where = f"{SHEET}!C{row[0].row}"
        if own not in (None, "", "n/a"):
            if s.override is None:
                problems.append(f"{where}: `{s.question}` takes one of the listed options only")
            elif not isinstance(own, (int, float)) or isinstance(own, bool):
                problems.append(f"{SHEET}!D{row[0].row}: `{s.question}` needs {s.override}; got {own!r}")
            elif s.valid and not (s.valid["min"] <= own <= s.valid["max"]) or \
                    (s.valid and s.valid.get("whole") and not float(own).is_integer()):
                v = s.valid
                problems.append(f"{SHEET}!D{row[0].row}: `{s.question}` needs {s.override}, from {v['min']:g} to "
                                f"{v['max']:g}; got {own!r}")
            else:
                found[key] = int(own) if (s.valid or {}).get("whole") else own
            continue
        if chosen in (None, ""):
            problems.append(f"{where}: `{s.question}` needs an answer. Pick one, or enter your own in column D")
            continue
        match = [o for o in s.options if o.shown == str(chosen).strip()]
        if not match:
            problems.append(f"{where}: {chosen!r} is not an option for `{s.question}`")
            continue
        found[key] = match[0].value
    for k in by_key:
        if k not in seen:
            problems.append(f"setting `{k}` is not on the {SHEET} tab")
    if problems:
        raise ControlError(problems)
    return found


def describe(found: dict[str, Any], settings: list[Setting] | None = None) -> list[tuple[str, str]]:
    """The settings in use as a person reads them: the question and the chosen
    option's words, or the typed value (walkthrough defect 13 echoed codes)."""
    out = []
    for s in settings or load_settings():
        if s.key not in found:
            continue
        v = found[s.key]
        o = next((o for o in s.options if o.value == v), None)
        out.append((s.question, o.label if o else f"{v:g}" if isinstance(v, float) else str(v)))
    return out
