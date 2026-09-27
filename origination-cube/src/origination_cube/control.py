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
import functools
import math
import threading
from typing import Any

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

SHEET = "Control"
OPTIONS_SHEET = "_options"
USED_SHEET = "_used"      # what the last Run used, cell for cell, so Status can compare (the redesign, phase 2)
RECOMMENDED = " (recommended)"
FIRST_ROW = 5
KEY_COL, CHOOSE_COL, OWN_COL = 7, 3, 4            # G (hidden), C, D
#: the redesign's columns (docs/redesign-2026-09-26/README.md, section 2): Setting B, Your answer C, Or your own D,
#: Comes to E, Last Run used F, the key G (hidden), Status H, and I the value worked out from the loans
COMES_COL, LAST_COL, STATUS_COL, SUGGEST_COL = 5, 6, 8, 9
NEED_COL, PEND_COL = 10, 11                        # hidden: 1 while an answer is needed; a waiting change in words
PANEL_COL = 13                                     # M: "What each materiality level keeps"
LAST_VISIBLE = SUGGEST_COL
WAITING, SAME = "\u21bb Waiting for a Run", "Same as last Run"
#: the two blocks a person answers, in the spec's order; the launcher's block follows them
NOW_KEYS = ("worse_at", "better_at", "revenue_line", "confidence", "materiality", "compare_to")
RUN_KEYS = ("min_loans", "min_events", "band_count", "band_cut", "power", "many_tests")
BLOCK_NOW, BLOCK_RUN, BLOCK_LAUNCHER = "block|now", "block|run", "block|launcher"
NEEDS = "F7DEDE"          # ALERT_FG: the shade on a cell that still needs an answer
METHOD = [
    ("Changes now", "The result tabs read these answers with formulas. Change one and every reading, dollar figure, "
                    "colour and verdict follows at once. The order of rows stays as the last Run left it."),
    ("Needs a Run", "These decide which pockets exist and which test each one gets, so they take effect when you "
                    "press Run again. Status says when an answer differs from what the last Run used."),
    ("Your answer", "Pick from the list, or type a number under Or your own: a number there wins. A shaded answer "
                    "still needs one. Comes to shows what the answer amounts to now."),
    ("Worked out", "Fewest loans, worse at and better at each have a value worked out from this extract, shown "
                   "beside the setting. It is never picked for you."),
    ("Chosen in the launcher", "What you're running and how the pockets are cut. Change them in the launcher's "
                               "Choose tests, then press Next. They are shown here so a reviewer sees them."),
    ("Materiality levels", "For each level: its dollar line, how many pockets have charge-offs above their share "
                           "that reach it, and their part of all such dollars. It follows your answer live."),
]

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
    only_when: dict | None = None    # {key: value}: asked only when another setting has that answer
    in_launcher: bool = False        # chosen in the launcher; Control shows it read-only (the redesign)

    def recommended(self) -> Option | None:
        return next((o for o in self.options if o.recommended), None)


#: The new-columns block under the settings (fix 3.9): a heading, a note, a header and this many rows.
#: Rows an older Control tab carries whose settings were taken out: the loan age filter, the outcome window and
#: the as-of date (the firm, 26 Sep 2026: every loan in the extract is run). Refused by cell until Set up again.
REMOVED_ROWS = ("min_age_months", "window_months", "as_of")
DERIVED_KEY = "derived"
DERIVED_ROWS = 3
DERIVED_NOTE = ("Shows here and on Look, and in Choose tests, once you press Set up again. Blank where the bottom "
                "is zero or blank.")


_ONCE = threading.local()


def settings_once(fn):
    """Read settings.yaml once for the whole of `fn` (book.set_up, book.run).
    Found 26 Sep 2026: one Run parsed it up to 45 times, once inside a loop over
    Control's rows. The copy is dropped when `fn` is entered and when it returns,
    so an edit to the file between two presses of the button is always read."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        outer = getattr(_ONCE, "cache", None)
        _ONCE.cache = {}
        try:
            return fn(*args, **kwargs)
        finally:
            _ONCE.cache = outer if outer is None else {}
    return wrapper


def load_settings(path: str | Path | None = None) -> list[Setting]:
    cache = getattr(_ONCE, "cache", None)
    if cache is None:
        return _read_settings(path)
    key = str(path) if path else None
    if key not in cache:
        cache[key] = _read_settings(path)
    return list(cache[key])


def _read_settings(path: str | Path | None = None) -> list[Setting]:
    text =(Path(path).read_text(encoding="utf-8") if path
            else resources.files("origination_cube").joinpath("settings.yaml").read_text(encoding="utf-8"))
    raw = yaml.safe_load(text)
    out = []
    for g in raw["groups"]:
        for s in g["settings"]:
            opts = tuple(Option(value=o["value"], label=str(o["label"]), explains=" ".join(str(o["explains"]).split()),
                                recommended=bool(o.get("recommended", False))) for o in s["options"])
            out.append(Setting(key=s["key"], question=s["question"], takes_effect=s["takes_effect"],
                               override=s.get("override"), options=opts, group=g["title"],
                               judgment=bool(s.get("judgment", False)), valid=s.get("valid"),
                               only_when=s.get("only_when"), in_launcher=s.get("asked_in") == "launcher"))
    return out


# --------------------------------------------------------------------------


def _by_value(key: str, v: Any) -> str:
    """An option's value as Excel writes a number joined to text: 0.95, 30, 1.25."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return ""
    t = f"{float(v):.10f}".rstrip("0").rstrip(".")
    return f"{key}|{t}"


def write_control(wb: Workbook, settings: list[Setting]) -> None:
    """The Control tab as the redesign draws it (docs/redesign-2026-09-26/README.md, section 2): the method note,
    the legend, Block A (changes now), Block B (needs a Run, with Status), Block C (chosen in the launcher,
    read-only), and on the right what each materiality level keeps. Every row is found by its key in column G,
    so reading back doesn't depend on where a row sits."""
    from . import house
    from openpyxl.utils import get_column_letter
    from openpyxl.workbook.defined_name import DefinedName
    ws = wb.create_sheet(SHEET, 0) if SHEET not in wb.sheetnames else wb[SHEET]
    opt = wb.create_sheet(OPTIONS_SHEET)
    opt.append(["lookup", "setting", "option", "value", "what it means", "your own value accepts", "plain",
                "lookup by value"])
    ranges: dict[str, tuple[int, int]] = {}
    for s in settings:
        first = opt.max_row + 1
        for o in s.options:
            # a number is kept (the lookup by value uses it); a word such as a suggestion's code isn't shown anywhere
            value = o.value if isinstance(o.value, (int, float)) and not isinstance(o.value, bool) else None
            opt.append([f"{s.key}|{o.shown}", s.key, o.shown, value, o.explains, s.override or "", o.label,
                        _by_value(s.key, o.value)])
        ranges[s.key] = (first, opt.max_row)
    opt.sheet_state = "hidden"
    if USED_SHEET not in wb.sheetnames:
        used = wb.create_sheet(USED_SHEET)          # filled by each Run (book._last_run_used)
        used.append(["key", "answer as the cells held it", "in words"])
        used.sheet_state = "hidden"

    # each column fits its longest value and its header (the spec's rule 5: no wrapping in the rows)
    fit_b = max(len(s.question) for s in settings) * 0.95 + 2
    fit_c = max(len(o.shown) for s in settings for o in s.options) * 0.95 + 3
    widths = {"A": 2, "B": min(fit_b, 80), "C": min(fit_c, 66), "D": 12, "E": 14, "F": 44, "G": 12, "H": 22,
              "I": 50, "J": 4, "K": 4, "L": 3, "M": 12, "N": 14, "O": 10, "P": 11}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    house.title_band(ws, "Control", "The professional calls. The top block changes results now; the second waits "
                                    "for a Run.", 2, PANEL_COL + 3)
    r = house.method_note(ws, 3, 2, LAST_VISIBLE, METHOD)
    # the legend: the three input styles, drawn as they appear
    for col, (text, style) in zip((2, 3, 6), (("Changes now", house.changes_now), ("Needs a Run", house.needs_run),
                                               ("Still needs an answer", None))):
        c = ws.cell(row=r, column=col, value=text)
        if style:
            style(c)
        else:
            c.fill = house.fill(house.ALERT_FG)
            c.font = Font(name="Calibri", bold=True, size=10, color=house.INK_TEXT)
        c.alignment = Alignment(horizontal="center", vertical="center")
    legend_row = r
    ws.cell(row=legend_row, column=KEY_COL, value="legend")
    r += 2

    by_key = {s.key: s for s in settings}
    now = [by_key[k] for k in NOW_KEYS if k in by_key]
    run = [by_key[k] for k in RUN_KEYS if k in by_key]
    rest = [s for s in settings if not s.in_launcher and s.key not in NOW_KEYS + RUN_KEYS]
    run += [s for s in rest if s.takes_effect != "live"]
    now += [s for s in rest if s.takes_effect == "live"]
    # where each row lands, worked out first: a setting asked only after another's answer names that row
    row_of: dict[str, int] = {}
    a_top = r
    for i, s in enumerate(now):
        row_of[s.key] = a_top + 2 + i
    b_top = a_top + 2 + len(now) + 1
    for i, s in enumerate(run):
        row_of[s.key] = b_top + 2 + i
    c_top = b_top + 2 + len(run) + 1
    launcher_rows = _launcher_order(by_key)
    for i, (key, _) in enumerate(launcher_rows):
        if key in by_key:
            row_of[key] = c_top + 1 + i

    house.section(ws, a_top, 2, LAST_VISIBLE, "Changes now · the result tabs follow as you change these")
    ws.cell(row=a_top, column=KEY_COL, value=BLOCK_NOW)
    house.sub_header(ws, a_top + 1, 2, ["Setting", "Your answer", "Or your own", "Comes to", "Last Run used", None,
                                        None, "Worked out from the loans"], centre_from=1)
    ws.cell(row=a_top + 1, column=KEY_COL, value=None)
    house.section(ws, b_top, 2, LAST_VISIBLE, "↻ Needs a Run · takes effect when you press Run again",
                  hex_=house.SLATE, rule=house.STONE)
    ws.cell(row=b_top, column=KEY_COL, value=BLOCK_RUN)
    house.sub_header(ws, b_top + 1, 2, ["Setting", "Your answer ↻", "Or your own", None, "Last Run used", None,
                                        "Status", "Worked out from the loans"], centre_from=1)
    thin = Side(style="thin", color=house.ROW_RULE)
    status_rows = []
    for s in now + run:
        r = row_of[s.key]
        live_now = s in now
        first, last = ranges[s.key]
        ws.cell(row=r, column=2, value=s.question)
        # what each option means, on the setting's name rather than beside the row (tenet T1): hover to read it
        from openpyxl.comments import Comment
        note = Comment("\n".join(f"{o.label}: {o.explains}" for o in s.options), "PocketBook")
        note.width, note.height = 420, 60 + 44 * len(s.options)
        ws.cell(row=r, column=2).comment = note
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
            dvo.error = f"Enter {_range_words(s)}."
            ws.add_data_validation(dvo)
            dvo.add(own)
        style = house.changes_now if live_now else house.needs_run
        style(choose)
        if s.override is None:
            own.value = "n/a"
            own.font = Font(name="Calibri", italic=True, size=10, color=house.STONE)
        else:
            style(own)
        C, D, K = f"$C${r}", f"$D${r}", f"${get_column_letter(KEY_COL)}${r}"
        asked, _ = _asked_formula(s, settings, row_of)
        answered_blank = f'AND({asked},$C{r}="",OR($D{r}="",$D{r}="n/a"))'
        ws.conditional_formatting.add(f"C{r}:D{r}" if s.override is not None else f"C{r}",
                                      house.still_needed(answered_blank))
        ws.cell(row=r, column=NEED_COL, value=f"=IF({answered_blank},1,0)")
        own_set = f'AND({D}<>"",{D}<>"n/a")'
        lookup = (f"IFERROR(MATCH({K}&\"|\"&{C},{OPTIONS_SHEET}!$A:$A,0),"
                  f"MATCH({K}&\"|\"&IFERROR(VALUE({C}),{C}),{OPTIONS_SHEET}!$H:$H,0))")
        plain = f'IFERROR(INDEX({OPTIONS_SHEET}!$G:$G,{lookup}),"not an option")'
        if live_now:
            shown = _comes_to(s.key, plain)
            ws.cell(row=r, column=COMES_COL, value=(f'=IF(NOT({asked}),"",IF({own_set},{D},IF({C}="","",'
                                                    f'IF(ISNA({lookup}),"not an option",{shown}))))'))
        else:
            # Status (the spec's formula): the answer now against the one the last Run used, kept on _used
            answer = f"IF({own_set},{D},{C})"
            last = f"INDEX({USED_SHEET}!$B:$B,MATCH({K},{USED_SHEET}!$A:$A,0))"
            last_words = f"INDEX({USED_SHEET}!$C:$C,MATCH({K},{USED_SHEET}!$A:$A,0))"
            ws.cell(row=r, column=STATUS_COL, value=(f'=IF(NOT({asked}),"",IFERROR(IF({answer}&""={last}&"",'
                                                     f'"{SAME}","{WAITING}"),""))'))
            ws.cell(row=r, column=PEND_COL, value=(f'=IF($H{r}="{WAITING}",$B{r}&": "&{last_words}&" → "&'
                                                   f'{answer}&" (Control C{r}); ","")'))
            status_rows.append(r)
        k = ws.cell(row=r, column=KEY_COL, value=s.key)
        k.font = Font(name="Consolas", size=8, color=SLATE)
        ws.cell(row=r, column=2).font = Font(name="Calibri", size=10, color=house.INK_TEXT)
        for col in (2, COMES_COL, LAST_COL, STATUS_COL, SUGGEST_COL):
            cell = ws.cell(row=r, column=col)
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical="center", horizontal="left" if col == 2 else "center")
        ws.cell(row=r, column=COMES_COL).font = Font(name="Calibri", bold=True, size=10, color=house.INK_TEXT)
        ws.cell(row=r, column=CHOOSE_COL).alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.cell(row=r, column=OWN_COL).alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[r].height = 18
    if status_rows:
        rng = f"$H${status_rows[0]}:$H${status_rows[-1]}"
        wb.defined_names["Status"] = DefinedName("Status", attr_text=f"{SHEET}!{rng}")
        wb.defined_names["waiting_words"] = DefinedName(
            "waiting_words", attr_text=f"{SHEET}!$K${status_rows[0]}:$K${status_rows[-1]}")
        from openpyxl.formatting.rule import FormulaRule
        ws.conditional_formatting.add(rng.replace("$", ""), FormulaRule(
            formula=[f'$H{status_rows[0]}="{WAITING}"'], font=Font(bold=True, color=house.CRIMSON),
            fill=PatternFill("solid", fgColor=house.ALERT_FG, bgColor=house.ALERT_FG)))
    need = [row_of[s.key] for s in now + run]
    wb.defined_names["answers_needed"] = DefinedName(
        "answers_needed", attr_text=f"{SHEET}!$J${min(need)}:$J${max(need)}")
    _write_launcher_block(ws, settings, row_of, c_top, launcher_rows)
    _materiality_panel(ws, settings, a_top)
    for col in ("G", "J", "K"):
        ws.column_dimensions[col].hidden = True
    ws.freeze_panes = "C2"
    ws.print_area = f"B1:P{ws.max_row}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _comes_to(key: str, plain: str) -> str:
    """What an answer in Block A comes to: the dollar line for materiality and the multiple a suggested line was
    worked out as, read from the names the last Run defined; the answer's own words otherwise (and before any
    Run, when the names don't exist yet)."""
    if key == "materiality":
        return (f'IFERROR(IF(materiality_kind="none","No floor",IF(materiality_gco>0,"$"&TEXT(materiality_gco,'
                f'"#,##0"),{plain})),{plain})')
    if key in ("worse_at", "better_at"):
        return f'IFERROR(TEXT({key},"0.00")&"×",{plain})'
    return '""'                 # the answer says it already: nothing to add


def _materiality_panel(ws, settings: list[Setting], top: int) -> None:
    """What each materiality level keeps, beside Block A (it absorbs the Materiality tab): for each share on
    Control's list, the dollar line, the pockets whose charge-offs above their share reach it, and their part of
    all such dollars. Live: formulas over the names each Run defines (book_gco, pk_kind, pk_measure, pk_dollars);
    before the first Run they show nothing."""
    from . import house
    first, last = PANEL_COL, PANEL_COL + 3
    s = next((x for x in settings if x.key == "materiality"), None)
    if s is None:
        return
    for col in range(first, last + 1):
        c = ws.cell(row=top, column=col)
        c.fill = house.fill(house.CANVAS)
        c.border = Border(top=Side(style="thick", color=house.KEY_RED))
    ws.cell(row=top, column=first, value="What each materiality level keeps").font = Font(
        name="Arial", bold=True, size=10, color=house.INK_TEXT)
    house.sub_header(ws, top + 1, first, ["Level", "Dollars", "Pockets", "Of excess"], centre_from=1)
    levels = [(o.label.split(" ")[0], float(str(o.value).split("%")[0]) / 100) for o in s.options
              if isinstance(o.value, str) and o.value.endswith("of losses")]
    crit = 'pk_kind,"grids",pk_measure,"gco_rate"'
    r = top + 2
    for label, share in levels:
        line = f"({share!r}*book_gco)"
        ws.cell(row=r, column=first, value=(f'=IFERROR("{label}"&IF(AND(materiality_kind="share",'
                                            f'ABS(materiality_share-{share!r})<1E-9)," ◂",""),"{label}")'))
        ws.cell(row=r, column=first + 1, value=f'=IFERROR({line},"")').number_format = '"$"#,##0'
        ws.cell(row=r, column=first + 2, value=(f'=IFERROR(COUNTIFS({crit},pk_dollars,">="&{line},'
                                                f'pk_dollars,">0"),"")'))
        all_ = f'SUMIFS(pk_dollars,{crit},pk_dollars,">0")'
        ws.cell(row=r, column=first + 3, value=(f'=IFERROR(IF({all_}=0,0,SUMIFS(pk_dollars,{crit},pk_dollars,'
                                                f'">="&{line},pk_dollars,">0")/{all_}),"")')).number_format = "0%"
        for col in range(first, last + 1):
            c = ws.cell(row=r, column=col)
            c.alignment = Alignment(horizontal="left" if col == first else "center", vertical="center")
            c.font = Font(name="Calibri", size=10, color=house.INK_TEXT)
            c.border = Border(bottom=Side(style="thin", color=house.ROW_RULE))
        r += 1
    from openpyxl.formatting.rule import FormulaRule
    ws.conditional_formatting.add(
        f"{_letter(first)}{top + 2}:{_letter(last)}{r - 1}",
        FormulaRule(formula=[f'RIGHT(${_letter(first)}{top + 2},1)="◂"'], font=Font(bold=True),
                    fill=PatternFill("solid", fgColor=house.CANVAS, bgColor=house.CANVAS)))
    for i, words in enumerate(("Charge-offs, every grid, against what each pocket is judged against.",
                               "A profit shortfall is held to the same dollar line.")):
        note = ws.cell(row=r + i, column=first, value=words)
        note.font = Font(name="Calibri", size=9, color=SLATE)


def _letter(col: int) -> str:
    from openpyxl.utils import get_column_letter
    return get_column_letter(col)


def _asked_formula(s: Setting, settings: list[Setting], row_of: dict[str, int]) -> tuple[str, str]:
    """An Excel condition that is TRUE while the setting is asked, and what its
    explanation says while it isn't: 'Only asked when "What are you running?" is
    Finding and testing a new variable.' TRUE for every setting asked always."""
    if not s.only_when:
        return "TRUE", ""
    conds, words = [], []
    for key, value in s.only_when.items():
        other = next(x for x in settings if x.key == key)
        opt = next(o for o in other.options if o.value == value)
        conds.append(f'$C${row_of[key]}="{opt.shown}"')
        words.append(f'""{other.question}"" is {opt.label}')
    return (conds[0] if len(conds) == 1 else f"AND({','.join(conds)})"), f"Only asked when {' and '.join(words)}."


def asked(s: Setting, answers: dict[str, Any]) -> bool:
    """Whether a setting is asked, given the answers read so far (only_when)."""
    return all(answers.get(k) == v for k, v in (s.only_when or {}).items())


def build_control_book(out: str | Path, settings: list[Setting] | None = None) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    write_control(wb, settings or load_settings())
    p = Path(out)
    wb.save(p)
    return p


# --------------------------------------------------------------------------
# Chosen in the launcher (the redesign, 26 Sep 2026): what runs is picked in the
# launcher before the workbook is written, and shown here read-only. The rows
# keep their keys, so the run reads a setting among them (What are you running?,
# the two column limits) exactly as before, and the choices (bands, segments,
# split, the pre-spec file) from the rows keyed "launcher|...".

LAUNCHER_HEAD = "Chosen in the launcher"
LAUNCHER_NOTE = "To change these, go back to Choose tests in the launcher and press Next."


def _launcher_order(by_key: dict) -> list[tuple[str, str | None]]:
    """Block C's rows, in order: (key, label for a row that isn't a setting)."""
    from . import choices as ch
    order = [("run_kind", None), ("new_variable_step", None)] + [(k, lab) for k, lab in ch.ROWS] + \
            [(PRESPEC_KEY, "Saved shortlist (pre-spec file)"), ("few_values", None), ("many_values", None)]
    return [(k, lab) for k, lab in order if k not in by_key or by_key[k].in_launcher]


def _write_launcher_block(ws, settings: list[Setting], row_of: dict[str, int], top: int,
                          order: list[tuple[str, str | None]]) -> int:
    """Block C, chosen in the launcher and shown read-only; returns the first row after it."""
    from . import choices as ch
    from . import house
    house.section(ws, top, 2, LAST_VISIBLE, f"{LAUNCHER_HEAD} · read-only here", hex_=house.MIST, rule=None,
                  color=house.INK_TEXT)
    ws.cell(row=top, column=4, value=LAUNCHER_NOTE).font = Font(name="Calibri", size=9, italic=True,
                                                                 color=house.SLATE)
    ws.cell(row=top, column=KEY_COL, value=f"{ch.KEY}|head")
    by_key = {s.key: s for s in settings}
    thin = Side(style="thin", color=house.ROW_RULE)
    r = top + 1
    for key, label in order:
        s = by_key.get(key)
        ws.cell(row=r, column=2, value=s.question if s is not None else label)
        ws.cell(row=r, column=KEY_COL, value=key if s is not None or key == PRESPEC_KEY else f"{ch.KEY}|{key}")
        if s is not None:
            row_of[key] = r
            rec = s.recommended()
            ws.cell(row=r, column=CHOOSE_COL, value=rec.label if rec is not None else None)
        for col in range(2, LAST_VISIBLE + 1):
            if col == KEY_COL:
                continue
            cell = ws.cell(row=r, column=col)
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical="center")
            cell.font = Font(name="Calibri", size=10, color=house.SLATE if col == 2 else house.INK_TEXT,
                             bold=col == CHOOSE_COL)
        ws.cell(row=r, column=KEY_COL).font = Font(name="Consolas", size=8, color=SLATE)
        ws.row_dimensions[r].height = 18
        r += 1
    return r + 1


def write_choices(ws, got, labels: dict[tuple[str, str], str]) -> None:
    """The launcher's choices into the block. `labels` maps (setting key, option
    value) to the option's label, so a setting reads back like one picked on the tab."""
    from . import choices as ch
    step = None
    if got.run_kind == ch.NEW_VARIABLE:
        step = "prespec" if got.shortlist else "scout"
    values = {"few_values": labels.get(("few_values", got.few_values), got.few_values),
              "many_values": labels.get(("many_values", got.many_values), got.many_values),
              **{f"{ch.KEY}|{k}": v for k, v in got.rows().items()}}
    if got.run_kind is not None:
        # what runs, and for a new variable whether a saved shortlist is confirmed; None leaves all three as they are
        values["run_kind"] = labels[("run_kind", got.run_kind)]
        values["new_variable_step"] = labels[("new_variable_step", step)] if step else None
        values[PRESPEC_KEY] = got.shortlist if got.run_kind == ch.NEW_VARIABLE else None
    for r in ws.iter_rows(min_row=FIRST_ROW):
        key = r[KEY_COL - 1].value
        if key in values:
            r[CHOOSE_COL - 1].value = values[key]
            if key in ("few_values", "many_values") and answer_of(key, None, r[OWN_COL - 1].value) != \
                    getattr(got, key):
                r[OWN_COL - 1].value = None
    fold_launcher_rows(ws)


def fold_launcher_rows(ws) -> None:
    """Show only the block's rows for what is being run: the new-variable rows fold away for the bleed."""
    from . import choices as ch
    only_new = {"new_variable_step", PRESPEC_KEY} | {f"{ch.KEY}|{k}" for k in ("outcome", "test", "hold",
                                                                                "find_share")}
    kind_row = row_of(ws, "run_kind")
    s = next(x for x in load_settings() if x.key == "run_kind")
    got = _matching(s, ws.cell(row=kind_row, column=CHOOSE_COL).value) if kind_row else []
    new = bool(got) and got[0].value == ch.NEW_VARIABLE
    # a setting asked only for one kind of run is hidden for the other (the redesign, phase 4: a new-variable run
    # is asked only what it uses); with no kind chosen yet every setting shows
    kind = got[0].value if got else None
    by_kind = {x.key for x in load_settings() if x.only_when and set(x.only_when) == {"run_kind"}
               and kind is not None and not asked(x, {"run_kind": kind})}
    for r in ws.iter_rows(min_row=FIRST_ROW):
        key = r[KEY_COL - 1].value
        if key in only_new:
            ws.row_dimensions[r[0].row].hidden = not new
        elif isinstance(key, str) and any(x.key == key and x.only_when and set(x.only_when) == {"run_kind"}
                                          for x in load_settings()):
            ws.row_dimensions[r[0].row].hidden = key in by_kind


def read_choices(ws):
    """The block's choices as a Choices, and the cell each row sits in (for a refusal)."""
    from . import choices as ch
    got, cells = {}, {}
    run_kind = shortlist = None
    limits = {"few_values": 12, "many_values": 50}
    for r in ws.iter_rows(min_row=FIRST_ROW):
        key = r[KEY_COL - 1].value
        if not isinstance(key, str):
            continue
        v = r[CHOOSE_COL - 1].value
        if key.startswith(f"{ch.KEY}|") and key.split("|")[1] in dict(ch.ROWS):
            got[key.split("|")[1]] = str(v).strip() if v not in (None, "") else None
            cells[key.split("|")[1]] = f"{SHEET}!C{r[0].row}"
        elif key == "run_kind":
            s = next(x for x in load_settings() if x.key == key)
            hit = _matching(s, v) if v not in (None, "") else []
            run_kind = hit[0].value if hit else None
            cells[key] = f"{SHEET}!C{r[0].row}"
        elif key == PRESPEC_KEY:
            shortlist = str(v).strip() if v not in (None, "") else None
            cells[key] = f"{SHEET}!C{r[0].row}"
        elif key in limits:
            n = answer_of(key, v, r[OWN_COL - 1].value)
            if isinstance(n, (int, float)) and not isinstance(n, bool):
                limits[key] = int(n)
    if got.get("bands") is None and got.get("segments") is None:
        return None, cells              # nothing written yet, or a workbook set up before the launcher chose
    return ch.Choices.from_rows(got, run_kind=run_kind, shortlist=shortlist, **limits), cells


# --------------------------------------------------------------------------


def read_control(path, settings: list[Setting] | None = None) -> dict[str, Any]:
    """The settings in use, read from the cells a person edits. Refuses, all
    at once, any setting left with nothing chosen, an unknown option, or an
    own value the setting cannot take. `path` is the workbook's file, or the
    workbook already open (a Run loads it once)."""
    settings = settings or load_settings()
    by_key = {s.key: s for s in settings}
    ws = (path if isinstance(path, Workbook) else load_workbook(path))[SHEET]
    found: dict[str, Any] = {}
    seen: set[str] = set()
    problems: list[str] = []
    later: list[tuple[Any, Setting]] = []
    for row in ws.iter_rows(min_row=FIRST_ROW):
        key = row[KEY_COL - 1].value
        if key in REMOVED_ROWS:
            # a workbook set up before the row was taken out: its answer would read as used and isn't
            problems.append(f'{SHEET}!C{row[0].row}: "{row[1].value}" is no longer used: every loan in the extract '
                            f'is run. Press Set up again to take the row off.')
            continue
        if key not in by_key:
            continue
        s = by_key[key]
        seen.add(key)
        if s.only_when:
            later.append((row, s))          # read once the answer it hangs on is known
            continue
        _take(row, s, found, problems)
    for row, s in later:
        if asked(s, found):
            _take(row, s, found, problems)
    for k in by_key:
        if k not in seen:
            problems.append(f'The {SHEET} tab is missing the setting "{by_key[k].question}". Press Set up again.')
    if problems:
        raise ControlError(problems)
    return found


def _take(row, s: Setting, found: dict[str, Any], problems: list[str]) -> None:
    """One setting's answer into `found`, or its problem, named by cell."""
    key = s.key
    chosen, own = row[CHOOSE_COL - 1].value, row[OWN_COL - 1].value
    where = f"{SHEET}!C{row[0].row}"
    if own not in (None, "", "n/a"):
        if s.override is None:
            problems.append(f'{where}: "{s.question}" takes one of the listed options only.')
        elif not isinstance(own, (int, float)) or isinstance(own, bool):
            problems.append(f'{SHEET}!D{row[0].row}: "{s.question}" needs {s.override}; got {own!r}.')
        elif s.valid and not (s.valid["min"] <= own <= s.valid["max"]) or \
                (s.valid and s.valid.get("whole") and not float(own).is_integer()):
            problems.append(f'{SHEET}!D{row[0].row}: "{s.question}" needs {_range_words(s)}; got {own!r}.'
                            + _percent_hint(s, own))
        else:
            found[key] = int(own) if (s.valid or {}).get("whole") else own
        return
    if chosen in (None, ""):
        if s.in_launcher:
            problems.append(f'{where}: "{s.question}" is chosen in the launcher. {LAUNCHER_NOTE}')
            return
        how = "Pick one from the list." if s.override is None else "Pick one, or enter your own in column D."
        problems.append(f'{where}: "{s.question}" needs an answer. {how}')
        return
    match = _matching(s, chosen)
    if not match:
        problems.append(f'{where}: {chosen!r} is not an option for "{s.question}".')
        return
    found[key] = match[0].value


def describe(found: dict[str, Any], settings: list[Setting] | None = None) -> list[tuple[str, str]]:
    """The settings in use as a person reads them: the question and the chosen
    option's words, or the typed value (walkthrough defect 13 echoed codes)."""
    out = []
    for s in settings or load_settings():
        if s.key not in found:
            continue
        v = found[s.key]
        o = next((o for o in s.options if o.value == v), None)
        label = o.label.replace(" (suggested)", "") if o else None
        out.append((s.question, label if o else f"{v:g}" if isinstance(v, float) else str(v)))
    return out


def _as_number(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(",", "")
    try:
        return float(t[:-1]) / 100 if t.endswith("%") else float(t)
    except ValueError:
        return None


def _matching(s: Setting, chosen: Any) -> list[Option]:
    """The option a Choose cell means, however Excel stored it. A pick from the
    list is its label; but Excel can turn a label that looks like a number into
    that number ("95%" becomes 0.95), so a number that equals an option's value
    means that option too (the second walkthrough, defect 3)."""
    text = str(chosen).strip()
    hit = [o for o in s.options if text in (o.shown, o.label)]
    if hit:
        return hit
    n = _as_number(chosen)
    if n is None:
        return []
    return [o for o in s.options if isinstance(o.value, (int, float)) and not isinstance(o.value, bool)
            and abs(float(o.value) - n) < 1e-9]


def answer_of(key: str, choose: Any, own: Any) -> Any:
    """One setting's answer from its two cells, or None when there isn't a usable
    one: a valid own value first, then the option picked. For Set up, which reads
    Control before the Run's full check does."""
    s = next((x for x in load_settings() if x.key == key), None)
    if s is None:
        return None
    n = _as_number(own) if own not in (None, "", "n/a") else None
    v = s.valid or {}
    if n is not None and v.get("min", -math.inf) <= n <= v.get("max", math.inf):
        return int(n) if v.get("integer") or float(n).is_integer() else n
    hit = _matching(s, choose) if choose not in (None, "") else []
    return hit[0].value if hit else None


def _range_words(s: Setting) -> str:
    """What the own-value cell takes, with its range said once (second walk,
    defect 15: "a share between 0.5 and 0.999, from 0.5 to 0.999")."""
    v = s.valid or {}
    if "min" not in v:
        return s.override
    return f"{s.override}, from {v['min']:g} to {v['max']:g}"


def _percent_hint(s: Setting, own: Any) -> str:
    """95 typed where 0.95 is meant: say so."""
    v = s.valid or {}
    if v.get("max", 2) < 1 and isinstance(own, (int, float)) and v["max"] < own <= 1:
        return f" The most it takes is {v['max']:g}."
    if v.get("max", 2) < 1 and isinstance(own, (int, float)) and 1 < own <= 100:
        if v.get("min", 0) <= own / 100 <= v["max"]:
            return f" For {own:g}%, type {own / 100:g}."
        return f" Type a share between {v['min']:g} and {v['max']:g}: for 15%, type 0.15."
    return ""


def row_of(ws, key: str) -> int | None:
    """The row a setting (or a new-column slot) sits on, by its key."""
    for r in ws.iter_rows(min_row=FIRST_ROW):
        if r[KEY_COL - 1].value == key:
            return r[0].row
    return None


# --------------------------------------------------------------------------
# New columns (fix 3.9): "Add a column: one divided by another". Each row names a
# column made by dividing one of the extract's columns by another. Since the
# redesign (phase 2) the block sits on Columns, under the table; before it, on
# Control. Set up writes it with the extract's number columns in the dropdowns
# and puts every answer back; the run reads it and refuses a half-filled row by
# cell. The name, top and bottom are three cells side by side from `first`, and
# `key_col` holds each row's key.

NUMBER_LIST_COL = 10              # J on the hidden options tab: the dropdowns' column names
DERIVED_HEAD = "Add a column: one divided by another"


def write_derived(wb: Workbook, number_columns: list[str], kept: dict[int, tuple] | None = None,
                  sheet: str = "Columns", top: int | None = None, first: int = 2, key_col: int = KEY_COL,
                  last: int = 6) -> int:
    """The block from row `top` (under the last used row when not given). `kept` maps a slot (1 to
    DERIVED_ROWS) to the (name, top, bottom) already typed there. Returns the row under it."""
    from . import house
    ws, opt = wb[sheet], wb[OPTIONS_SHEET]
    kept = kept or {}
    opt.cell(row=1, column=NUMBER_LIST_COL, value="number columns")
    for i, c in enumerate(number_columns, start=2):
        opt.cell(row=i, column=NUMBER_LIST_COL, value=c)
    r = top if top is not None else ws.max_row + 2
    house.section(ws, r, first, last, DERIVED_HEAD)
    ws.cell(row=r, column=key_col, value=f"{DERIVED_KEY}|head")
    note = ws.cell(row=r + 1, column=first, value=DERIVED_NOTE)
    note.font = Font(name="Calibri", size=9, color=SLATE)
    ws.cell(row=r + 1, column=key_col, value=f"{DERIVED_KEY}|note")
    house.sub_header(ws, r + 2, first, ["New column name ↻", "Top (divided)", "Bottom (divided by)",
                                        "What it makes"], centre_from=4)
    ws.cell(row=r + 2, column=key_col, value=f"{DERIVED_KEY}|cols")
    dv = None
    if number_columns:
        dv = DataValidation(type="list", formula1=f"='{OPTIONS_SHEET}'!$J$2:$J${len(number_columns) + 1}",
                            allow_blank=True, showErrorMessage=True)
        dv.errorTitle = "Pick a column"
        dv.error = "Pick one of the extract's number columns from the list."
        ws.add_data_validation(dv)
    thin = Side(style="thin", color=house.ROW_RULE)
    L = [_letter(first + i) for i in range(3)]
    for slot in range(1, DERIVED_ROWS + 1):
        row = r + 2 + slot
        for i, v in enumerate(kept.get(slot, (None, None, None))):
            c = ws.cell(row=row, column=first + i, value=v)
            house.needs_run(c)
            c.alignment = Alignment(vertical="center")
            if i and dv is not None:
                dv.add(c)
        made = ws.cell(row=row, column=first + 3, value=(
            f'=IF(COUNTA({L[0]}{row}:{L[2]}{row})=0,"",IF(COUNTA({L[0]}{row}:{L[2]}{row})<3,'
            f'"Needs a name, a top and a bottom.",{L[0]}{row}&" = "&{L[1]}{row}&" ÷ "&{L[2]}{row}&'
            f'" on each loan."))'))
        made.font = Font(name="Calibri", size=10, color=SLATE)
        ws.cell(row=row, column=key_col, value=f"{DERIVED_KEY}|{slot}")
        for col in range(first + 3, last + 1):
            ws.cell(row=row, column=col).border = Border(bottom=thin)
        ws.row_dimensions[row].height = 18
        # a half-filled row is shaded where it still needs something; an empty one is left alone
        ws.conditional_formatting.add(f"{L[0]}{row}:{L[2]}{row}", house.still_needed(
            f'AND({L[0]}{row}="",COUNTA(${L[0]}{row}:${L[2]}{row})>0)'))
    return r + 3 + DERIVED_ROWS


def read_derived(ws, first: int = 2, key_col: int = KEY_COL) -> tuple[list[dict], list[str]]:
    """Each filled new-column row as {slot, row, name, top, bottom}, and a
    problem for each half-filled one, named by cell."""
    out, problems = [], []
    for r in ws.iter_rows(min_row=FIRST_ROW):
        if len(r) < key_col:
            continue
        key = r[key_col - 1].value
        if not (isinstance(key, str) and key.startswith(f"{DERIVED_KEY}|") and key.split("|")[1].isdigit()):
            continue
        row = r[0].row
        vals = [r[c - 1].value for c in (first, first + 1, first + 2)]
        vals = [str(v).strip() if v not in (None, "") and str(v).strip() else None for v in vals]
        if not any(vals):
            continue
        if not all(vals):
            lacking = [w for w, v in zip(("a name", "a top", "a bottom"), vals) if not v]
            col = _letter(first + [v is None for v in vals].index(True))
            problems.append(f"{ws.title}!{col}{row}: new column {key.split('|')[1]} needs "
                            f"{' and '.join(lacking)}. Fill it in, or clear the row.")
            continue
        out.append({"slot": int(key.split("|")[1]), "row": row, "name": vals[0], "top": vals[1], "bottom": vals[2]})
    return out, problems


# --------------------------------------------------------------------------
# The pre-spec file (fix 3.15): one cell, for a confirmatory run only. Since the
# redesign it is picked in the launcher ("Or confirm a saved shortlist") and
# shown in the "Chosen in the launcher" block. Blank is the answer for Where the
# book bleeds. The run reads the file only for "Test from a pre-spec", refuses
# one it cannot use or one named for the bleed analysis, naming this cell
# (book.read_book).

PRESPEC_KEY = "prespec"

def read_prespec(ws) -> tuple[str | None, str]:
    """What the pre-spec cell says, without the quotes Windows puts round a
    copied path, or None when it is blank or the tab has no such cell (a
    workbook set up before there was one); and the cell, for a refusal."""
    row = row_of(ws, PRESPEC_KEY)
    if row is None:
        return None, f"{SHEET}!C"
    v = ws.cell(row=row, column=CHOOSE_COL).value
    text = str(v).strip().strip('"').strip("'").strip() if v not in (None, "") else ""
    return (text or None), f"{SHEET}!C{row}"
