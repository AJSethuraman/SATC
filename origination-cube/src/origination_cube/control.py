"""The control center: every setting of a run on one Excel tab.

Each setting has a dropdown of options and a cell for your own value. Two
more cells are Excel formulas: the value in use, and what the chosen option
means. The options and their explanations come from `settings.yaml` and
nowhere else, so the tab, the run and the docs cannot drift apart.

Reading back does not depend on Excel having recalculated. Python reads the
dropdown and the override cells directly: your own value wins when it is
filled in. A setting with neither is refused and named. The recommended
option is pre-selected so the tab opens ready to run, and it is printed with
every other setting in use on the output, so nothing is chosen silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

SHEET = "Control"
OPTIONS_SHEET = "_options"
RECOMMENDED = " (recommended)"
FIRST_ROW = 5
KEY_COL, CHOOSE_COL, OWN_COL = 8, 3, 4            # H, C, D

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

    def recommended(self) -> Option:
        return next(o for o in self.options if o.recommended)


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
                               override=s.get("override"), options=opts, group=g["title"]))
    return out


# --------------------------------------------------------------------------


def write_control(wb: Workbook, settings: list[Setting]) -> None:
    ws = wb.create_sheet(SHEET, 0) if SHEET not in wb.sheetnames else wb[SHEET]
    opt = wb.create_sheet(OPTIONS_SHEET)
    opt.append(["lookup", "setting", "option", "value", "what it means", "your own value accepts"])
    ranges: dict[str, tuple[int, int]] = {}
    for s in settings:
        first = opt.max_row + 1
        for o in s.options:
            opt.append([f"{s.key}|{o.shown}", s.key, o.shown, o.value, o.explains, s.override or ""])
        ranges[s.key] = (first, opt.max_row)
    opt.sheet_state = "hidden"

    thin = Side(style="thin", color=MIST)
    ws.sheet_view.showGridLines = False
    widths = {"A": 2, "B": 34, "C": 44, "D": 16, "E": 14, "F": 62, "G": 13, "H": 12}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.merge_cells("B1:G1")
    ws["B1"] = "Control center"
    ws["B1"].font = Font(name="Arial", bold=True, size=16, color=PAPER)
    for c in "BCDEFG":
        ws[f"{c}1"].fill = PatternFill("solid", fgColor=INK)
    ws.row_dimensions[1].height = 28
    ws.merge_cells("B2:G2")
    ws["B2"] = ("Pick an option in column C, or type your own value in column D. Column E is what the run "
                "will use; column F says what that choice does. Live settings recalculate at once; "
                "re-run settings need the script run again.")
    ws["B2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws["B2"].font = Font(name="Calibri", size=10, color=SLATE)
    ws.row_dimensions[2].height = 30
    heads = ["Setting", "Choose", "Your own value", "In use", "What it means", "Takes effect", "key"]
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
        choose = ws.cell(row=r, column=CHOOSE_COL, value=s.recommended().shown)
        dv = DataValidation(type="list", formula1=f"='{OPTIONS_SHEET}'!$C${first}:$C${last}", allow_blank=True,
                            showDropDown=False)
        dv.error = "Pick one of the listed options, or type your own value in column D."
        ws.add_data_validation(dv)
        dv.add(choose)
        own = ws.cell(row=r, column=OWN_COL)
        if s.override is None:
            own.value = "n/a"
            own.font = Font(name="Calibri", italic=True, color=SLATE)
            own.fill = PatternFill("solid", fgColor=MIST)
        else:
            own.fill = PatternFill("solid", fgColor="FFF8E1")
        C, D, H = f"C{r}", f"D{r}", f"$H{r}"
        own_set = f'AND({D}<>"",{D}<>"n/a")'
        lookup = f"MATCH({H}&\"|\"&{C},{OPTIONS_SHEET}!$A:$A,0)"
        ws.cell(row=r, column=5, value=(f'=IF({own_set},{D},IF({C}="","PICK ONE",'
                                        f'INDEX({OPTIONS_SHEET}!$D:$D,{lookup})))'))
        note = f"Your own value, in place of the options ({s.override})." if s.override else ""
        ws.cell(row=r, column=6, value=(f'=IF({own_set},"{note}",IF({C}="","Nothing chosen: the run will refuse '
                                        f'this setting.",INDEX({OPTIONS_SHEET}!$E:$E,{lookup})))'))
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
            else:
                found[key] = own
            continue
        if chosen in (None, ""):
            problems.append(f"{where}: `{s.question}` has nothing chosen and no value of your own")
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
