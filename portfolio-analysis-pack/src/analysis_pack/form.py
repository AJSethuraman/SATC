"""The form: designation at the desk in Excel, a dropdown beside each column.

`pack setup EXTRACT` (from the bundle, `python build_pack.py --setup
EXTRACT.csv`) run once writes `question.xlsx` beside the extract: one row
per column of the extract with what it reads as and three sample values,
and a dropdown in the next cell for the column's role (loan number,
origination date, the two rule columns, how a loan went bad, a group).
A second tab holds the few answers that are not a column: the word for the
event, the as-of date, the window. The person picks in Excel, saves, and
runs the same command again; the tool reads the form, refuses anything the
loader would refuse (every problem at once, each with its cell), writes the
question file and builds the pack. Nothing is typed at a prompt and nothing
is edited by hand.

The firm, 22 September 2026, offered a pop-up window or a form in Excel:
"Actually excel version is fine." The picker (`picker.py`, `--ask`) stays
for a desk without Excel and for the tests that drive it.

What the form proposes it takes from the data and says so: a group column
left without band edges is banded at the quartiles of its own values, and
the quartiles are shown in the cell beside it before the person decides.
Nothing else is filled in for them: the event word and the as-of date are
required and refused when blank.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import from_excel
from openpyxl.worksheet.datavalidation import DataValidation

from . import workbook_style as ks
from .ingest import Bad, Table, is_blank, parse_number
from .picker import NUMERIC, _fmt, _quartile_edges, _slug, question_from_answers, answers_to_yaml

FORM_NAME = "question.xlsx"

# the roles, as the dropdown lists them
LOAN, ORIG, TOP, BOTTOM, TOP_G, BOTTOM_G, OUT_DATE, OUT_FLAG, M_TOP, M_BOTTOM, GROUP = ROLES = (
    "loan number", "origination date", "rule top", "rule bottom", "rule top + group", "rule bottom + group",
    "went bad: date", "went bad: flag", "went bad: measure top", "went bad: measure bottom", "group",
)
# a rule column is often the group that matters most (a size is usually the
# bottom of the ratio), so the two rule roles come in a "+ group" form too
ALSO_GROUP = {TOP_G: TOP, BOTTOM_G: BOTTOM}
SINGLE = (LOAN, ORIG, TOP, BOTTOM, OUT_DATE, OUT_FLAG, M_TOP, M_BOTTOM)    # each on exactly one column
OUTCOME_ROLES = (OUT_DATE, OUT_FLAG, M_TOP, M_BOTTOM)
YES_NO = ("no", "yes")
KINDS = ("ratio (top / bottom)", "difference (top - bottom)")

COLUMNS_TAB, ANSWERS_TAB, LISTS_TAB = "Columns", "Answers", "lists"
HEADER_ROW = 3                          # data from the row after, on both tabs
ROLE_COL, LATER_COL, EDGES_COL, QUARTILE_COL = 6, 7, 8, 9     # F, G, H, I on the Columns tab

# the Answers tab: key, question, what is there to start with, the note beside it
ANSWERS = (
    ("kind", "Compare the two rule columns as", KINDS[0], "ratio, or difference (top - bottom)"),
    ("fires", "The flag fires when the ratio (or difference) is above", 1, "1 for a ratio; a difference usually 0"),
    ("buckets", "Steps of the ratio for the gradient (edges, smallest first, separated by commas)", "0.5, 1, 2, 5",
     "for a difference, leave blank to take the quartiles of top - bottom from the data"),
    ("label", "The word every tab will use for the event (one word)", "", "required, e.g. event or bad"),
    ("months", "Months a loan needs on book before it counts", 24, ""),
    ("asof", "The as-of date the pack is built at", "", "required; type it as a date, e.g. 2026-06-30"),
    ("run_date", "Today's date, to stamp on the pack", "", "blank: the pack says run date not given"),
    ("existing_control", "What at the bank reacts to this contradiction today", "none", ""),
    ("flag_value", "If a loan went bad by a flag: the value that means yes", 1, ""),
    ("measure_kind", "If a loan went bad by a measure: combine its two columns as", KINDS[0], ""),
    ("measure_cut", "If a loan went bad by a measure: bad at or above (one cut)", "", "fill this or the edges below"),
    ("measure_edges", "If a loan went bad by a measure: or its band edges (smallest first)", "", ""),
)
REQUIRED = ("label", "asof")

FILL_IN = PatternFill("solid", fgColor=ks.CANVAS)       # the cells the person fills
NOTE = Font(name="Calibri", italic=True, size=10, color=ks.SLATE)


class FormError(Exception):
    """The form as saved cannot be built from; `problems` lists why, each with its cell."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


class NotFilled(Exception):
    """The form is as the tool wrote it: nothing picked yet."""


# -- writing --------------------------------------------------------------------

def _kind_shown(entry: dict) -> str:
    return "date" if (entry.get("dates") or {}).get("resolved") else entry["kind"]


def _values(table: Table, col: str) -> list[float]:
    out = []
    for r in table.rows:
        v = r.get(col)
        if is_blank(v):
            continue
        n = parse_number(v)
        if not isinstance(n, Bad):
            out.append(float(n))
    return out


def write_form(table: Table, report: list[dict], path: Path) -> Path:
    """The blank form for this extract: one row per column, dropdowns beside."""
    wb = Workbook()
    ws = wb.active
    ws.title = COLUMNS_TAB
    name = Path(table.path).name
    widths = {1: 5, 2: 28, 3: 10, 4: 9, 5: 44, 6: 26, 7: 16, 8: 34, 9: 30}
    for i, w in widths.items():
        ws.column_dimensions[get_column_letter(i)].width = w
    ks.brand_banner(ws, 1, 9, f"{name}: which column is which",
                    "Pick a role beside each column you use; leave the others blank. Then the Answers tab, save, and run the command again.")
    ks.header_row(ws, HEADER_ROW, ["#", "column", "reads as", "blank", "e.g.", "role  (pick from the list)",
                                   "known only after the loan was made?", "band edges  (a group number column; smallest first)",
                                   "its quartiles, from the data  (used when the edges are blank)"])
    n = len(report)
    for i, e in enumerate(report, start=1):
        r = HEADER_ROW + i
        blank = "n/a" if e["null_share"] is None else f"{e['null_share']:.0%}"
        samples = ", ".join(" ".join(str(s).split())[:18] for s in e["samples"][:3])
        for c, v in ((1, i), (2, e["column"]), (3, _kind_shown(e)), (4, blank), (5, samples)):
            cell = ws.cell(r, c, v)
            cell.font = ks.DATA_FONT
        ws.cell(r, 1).alignment = Alignment(horizontal="right")
        for c in (ROLE_COL, LATER_COL, EDGES_COL):
            ws.cell(r, c).fill = FILL_IN
            ws.cell(r, c).font = ks.DATA_FONT
        if e["kind"] in NUMERIC:
            q = _quartile_edges(_values(table, e["column"]))
            ws.cell(r, QUARTILE_COL, ", ".join(_fmt(x) for x in q) if q else "too few values to propose").font = NOTE
    last = HEADER_ROW + n
    lists = wb.create_sheet(LISTS_TAB)
    for i, role in enumerate(ROLES, start=1):
        lists.cell(i, 1, role)
    for i, v in enumerate(YES_NO, start=1):
        lists.cell(i, 2, v)
    for i, v in enumerate(KINDS, start=1):
        lists.cell(i, 3, v)
    lists.sheet_state = "hidden"

    def dropdown(ws_, cells: str, ref: str, prompt: str) -> None:
        dv = DataValidation(type="list", formula1=ref, allow_blank=True, showErrorMessage=True,
                            errorTitle="Pick from the list", error=prompt)
        dv.add(cells)
        ws_.add_data_validation(dv)

    dropdown(ws, f"F{HEADER_ROW + 1}:F{last}", f"={LISTS_TAB}!$A$1:$A${len(ROLES)}", "Pick a role from the list, or leave the cell blank.")
    dropdown(ws, f"G{HEADER_ROW + 1}:G{last}", f"={LISTS_TAB}!$B$1:$B$2", "yes or no")
    ws.freeze_panes = f"A{HEADER_ROW + 1}"
    ks.hide_gridlines(ws)
    _print_wide(ws)

    wa = wb.create_sheet(ANSWERS_TAB)
    for i, w in {1: 78, 2: 28, 3: 70}.items():
        wa.column_dimensions[get_column_letter(i)].width = w
    ks.brand_banner(wa, 1, 3, "The answers that are not a column",
                    "Two are required: the word for the event and the as-of date. The rest hold a usual value; change what you know better.")
    ks.header_row(wa, HEADER_ROW, ["question", "answer", "note"])
    for i, (key, question, start, note) in enumerate(ANSWERS, start=1):
        r = HEADER_ROW + i
        wa.cell(r, 1, question).font = ks.DATA_FONT
        cell = wa.cell(r, 2, start if start != "" else None)
        cell.fill = FILL_IN
        cell.font = ks.DATA_FONT
        if key in ("asof", "run_date"):
            cell.number_format = "yyyy-mm-dd"
        wa.cell(r, 3, note).font = NOTE
        if key in ("kind", "measure_kind"):
            dropdown(wa, f"B{r}", f"={LISTS_TAB}!$C$1:$C$2", "ratio or difference")
    wa.freeze_panes = f"A{HEADER_ROW + 1}"
    ks.hide_gridlines(wa)
    _print_wide(wa)
    wb.save(path)
    return path


def _print_wide(ws) -> None:
    """Printed (or rendered), the tab fits its width on a landscape page."""
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


# -- reading --------------------------------------------------------------------

def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, datetime):
        return v.date().isoformat()
    return str(v).strip()


def _number(v, where: str, problems: list[str]) -> float | None:
    n = parse_number(v)
    if isinstance(n, Bad) or n is None or is_blank(v):
        problems.append(f"{where}: {_text(v)!r} is not a number")
        return None
    return float(n)


def _edges(v, where: str, problems: list[str]) -> list[float] | None:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return [float(v)]
    parts = [p for p in re.split(r"[,\s;]+", _text(v).replace("_", "")) if p]
    try:
        edges = [float(p) for p in parts]
    except ValueError:
        problems.append(f"{where}: type numbers separated by commas, smallest first (not {_text(v)!r})")
        return None
    if not edges or any(edges[i] >= edges[i + 1] for i in range(len(edges) - 1)):
        problems.append(f"{where}: the edges must rise, smallest first, no repeats (not {_text(v)!r})")
        return None
    return edges


def _date(v, where: str, problems: list[str]) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return from_excel(v).date()
        except (ValueError, OverflowError, TypeError):
            pass
    try:
        return date.fromisoformat(_text(v))
    except ValueError:
        problems.append(f"{where}: type the date as YYYY-MM-DD or as an Excel date (not {_text(v)!r})")
        return None


def read_form(path: Path, table: Table, report: list[dict]) -> dict:
    """The answers a person saved in the form, in the picker's shape. Raises
    FormError with every problem at once, or NotFilled when nothing was picked."""
    wb = load_workbook(path, data_only=True)
    problems: list[str] = []
    if COLUMNS_TAB not in wb.sheetnames or ANSWERS_TAB not in wb.sheetnames:
        raise FormError([f"{path.name} is not the form this tool writes (no {COLUMNS_TAB} and {ANSWERS_TAB} tabs); "
                         f"delete it and run the command again for a fresh one"])
    ws, wa = wb[COLUMNS_TAB], wb[ANSWERS_TAB]
    by_name = {e["column"]: e for e in report}

    rows: list[tuple[int, str, str, str, object]] = []      # row, column, role, later, edges
    r = HEADER_ROW + 1
    while ws.cell(r, 2).value not in (None, ""):
        rows.append((r, _text(ws.cell(r, 2).value), _text(ws.cell(r, ROLE_COL).value).lower(),
                     _text(ws.cell(r, LATER_COL).value).lower(), ws.cell(r, EDGES_COL).value))
        r += 1
    named = [c for _, c, _, _, _ in rows]
    if sorted(named) != sorted(table.columns):
        extra = [c for c in named if c not in by_name]
        missing = [c for c in table.columns if c not in named]
        raise FormError([f"{path.name} was written for a different extract: "
                         + (f"it lists {', '.join(extra[:5])} which {Path(table.path).name} does not have; " if extra else "")
                         + (f"{Path(table.path).name} has {', '.join(missing[:5])} which the form does not list; " if missing else "")
                         + "delete the form and run the command again for a fresh one"])

    answers_raw: dict[str, object] = {}
    r = HEADER_ROW + 1
    questions = {q: k for k, q, _, _ in ANSWERS}
    while wa.cell(r, 1).value not in (None, ""):
        q = _text(wa.cell(r, 1).value)
        if q in questions:
            answers_raw[questions[q]] = wa.cell(r, 2).value
        r += 1
    for key, q, _, _ in ANSWERS:
        if key not in answers_raw:
            problems.append(f"{ANSWERS_TAB} tab: the row \"{q}\" is missing; delete {path.name} and run the command again for a fresh form")
    if problems:
        raise FormError(problems)

    roles: dict[str, list[tuple[str, int]]] = {}
    for row, col, role, later, edges in rows:
        if role:
            if role not in ROLES:
                problems.append(f"{COLUMNS_TAB}!F{row}: {role!r} is not a role; pick one from the list")
                continue
            if role in ALSO_GROUP:
                roles.setdefault(GROUP, []).append((col, row))
                role = ALSO_GROUP[role]
            roles.setdefault(role, []).append((col, row))
    if not roles and all(is_blank(v) for k, v in answers_raw.items() if k in REQUIRED):
        raise NotFilled()

    a: dict = {"used": {}}
    for role in SINGLE:
        picks = roles.get(role, [])
        if len(picks) > 1:
            problems.append(f"{COLUMNS_TAB} tab: \"{role}\" is on {len(picks)} columns ("
                            + ", ".join(f"{c} in F{rw}" for c, rw in picks) + "); only one can be")
    for role in (LOAN, ORIG, TOP, BOTTOM):
        if role not in roles:
            problems.append(f"{COLUMNS_TAB} tab, role column: no column is marked \"{role}\"")
    # the outcome: exactly one of the three forms
    forms = [f for f in ("date", "flag", "measure")
             if (f == "date" and OUT_DATE in roles) or (f == "flag" and OUT_FLAG in roles)
             or (f == "measure" and (M_TOP in roles or M_BOTTOM in roles))]
    if not forms:
        problems.append(f"{COLUMNS_TAB} tab, role column: nothing says how a loan went bad; mark one column "
                        f"\"{OUT_DATE}\" or \"{OUT_FLAG}\", or two columns \"{M_TOP}\" and \"{M_BOTTOM}\"")
    elif len(forms) > 1:
        problems.append(f"{COLUMNS_TAB} tab, role column: a loan goes bad one way; the form marks "
                        + " and ".join(forms) + " — keep one")
    if "measure" in forms and not (M_TOP in roles and M_BOTTOM in roles):
        problems.append(f"{COLUMNS_TAB} tab, role column: a measure needs both \"{M_TOP}\" and \"{M_BOTTOM}\"")

    def one(role: str) -> tuple[str, int] | None:
        picks = roles.get(role, [])
        return picks[0] if len(picks) == 1 else None

    def needs(role: str, kinds: tuple[str, ...] | None, what: str) -> None:
        pick = one(role)
        if pick is None:
            return
        col, row = pick
        e = by_name[col]
        if kinds is None:                                     # a date role
            if not (e["kind"] == "date-like" or e.get("dates")):
                problems.append(f"{COLUMNS_TAB}!F{row}: {col} reads as {e['kind']}, and \"{role}\" needs a date column")
        elif e["kind"] not in kinds:
            problems.append(f"{COLUMNS_TAB}!F{row}: {col} reads as {e['kind']}, and \"{role}\" needs {what}")

    needs(ORIG, None, "")
    needs(OUT_DATE, None, "")
    for role in (TOP, BOTTOM, M_TOP, M_BOTTOM, OUT_FLAG):
        needs(role, NUMERIC, "a number column")

    for role in SINGLE:
        pick = one(role)
        if pick:
            a["used"][pick[0]] = role
    for col, row in roles.get(GROUP, []):
        a["used"].setdefault(col, GROUP)
    group_rows = {row for _, row in roles.get(GROUP, [])}

    # what was known when: yes on anything but the outcome is a leak
    for row, col, role, flag, _ in rows:
        if flag in ("", "no"):
            continue
        if flag != "yes":
            problems.append(f"{COLUMNS_TAB}!G{row}: yes or no (not {flag!r})")
            continue
        if not role or role in OUTCOME_ROLES:
            continue
        problems.append(f"{COLUMNS_TAB}!G{row}: {col} is the {role}; a column known only after the loan was made cannot "
                        f"be used there, because it would leak what happened into the test. Put no there, "
                        f"or give that role to another column.")
    a["later"] = []                                           # the outcome columns are known later by construction

    # the groups, with edges for the number columns; edges beside any other column are ignored
    conf: list[dict] = []
    for row, col, role, _, edges in rows:
        if row not in group_rows:
            continue
        e = by_name[col]
        if e["kind"] in NUMERIC:
            if is_blank(edges):
                q = _quartile_edges(_values(table, col))
                if not q:
                    problems.append(f"{COLUMNS_TAB}!H{row}: {col} has too few values to propose bands from; type the edges")
                    continue
                conf.append({"name": col, "field": col, "edges": q, "proposed": True})
            else:
                got = _edges(edges, f"{COLUMNS_TAB}!H{row}", problems)
                if got:
                    conf.append({"name": col, "field": col, "edges": got})
        else:
            if not is_blank(edges):
                problems.append(f"{COLUMNS_TAB}!H{row}: {col} reads as {e['kind']} and is taken level by level; "
                                f"band edges do not apply. Clear the cell.")
                continue
            conf.append({"name": col, "field": col})
    a["confounders"] = conf

    # the answers tab
    def cell(key: str) -> str:
        return f"{ANSWERS_TAB}!B{HEADER_ROW + 1 + [k for k, *_ in ANSWERS].index(key)}"

    kind_text = _text(answers_raw["kind"]).lower()
    if kind_text.startswith("ratio") or kind_text == "":
        a["kind"] = "ratio"
    elif kind_text.startswith("difference"):
        a["kind"] = "difference"
    else:
        problems.append(f"{cell('kind')}: ratio or difference (not {kind_text!r})")
        a["kind"] = "ratio"
    fires = _number(answers_raw["fires"], cell("fires"), problems)
    a["fires_value"] = fires if fires is not None else 1.0
    if is_blank(answers_raw["buckets"]):
        if a["kind"] == "ratio":
            problems.append(f"{cell('buckets')}: the steps of the ratio are needed, e.g. 0.5, 1, 2, 5")
        else:
            top, bottom = one(TOP), one(BOTTOM)
            if top and bottom:
                pairs = [x - y for x, y in zip(_values(table, top[0]), _values(table, bottom[0]))]
                a["buckets"] = _quartile_edges(pairs) or [0.0]
                a["buckets_proposed"] = True
    else:
        a["buckets"] = _edges(answers_raw["buckets"], cell("buckets"), problems) or [1.0]
    label = _text(answers_raw["label"])
    if not label:
        problems.append(f"{cell('label')}: the word for the event is needed (one word, e.g. event)")
    a["label"] = label.split()[0] if label else "event"
    months = _number(answers_raw["months"], cell("months"), problems)
    a["window_months"] = int(months) if months is not None else 24
    if is_blank(answers_raw["asof"]):
        problems.append(f"{cell('asof')}: the as-of date is needed")
    else:
        a["asof"] = _date(answers_raw["asof"], cell("asof"), problems)
    a["run_date"] = None if is_blank(answers_raw["run_date"]) else _date(answers_raw["run_date"], cell("run_date"), problems)
    a["existing_control"] = _text(answers_raw["existing_control"]) or "none"

    if OUT_DATE in roles and one(OUT_DATE):
        a["outcome"] = {"date_field": one(OUT_DATE)[0]}
    elif OUT_FLAG in roles and one(OUT_FLAG):
        val = _number(answers_raw["flag_value"], cell("flag_value"), problems)
        a["outcome"] = {"field": one(OUT_FLAG)[0], "op": "==", "value": val if val is not None else 1.0,
                        "basis": "windowed_by_bank"}
    elif one(M_TOP) and one(M_BOTTOM):
        mk = _text(answers_raw["measure_kind"]).lower()
        out = {"measure": {"kind": "difference" if mk.startswith("difference") else "ratio",
                           "field_a": one(M_TOP)[0], "field_b": one(M_BOTTOM)[0]}, "basis": "snapshot_at_asof"}
        cut, edges = answers_raw["measure_cut"], answers_raw["measure_edges"]
        if is_blank(cut) and is_blank(edges):
            problems.append(f"{cell('measure_cut')}: a measure needs one cut (bad at or above) or band edges in the row below")
        elif not is_blank(cut) and not is_blank(edges):
            problems.append(f"{cell('measure_cut')}: one cut or band edges, not both")
        elif not is_blank(cut):
            out["op"] = ">="
            v = _number(cut, cell("measure_cut"), problems)
            out["value"] = v if v is not None else 0.0
        else:
            out["edges"] = _edges(edges, cell("measure_edges"), problems) or [0.0]
        a["outcome"] = out
    if problems:
        raise FormError(problems)
    a["loan_id"], a["origination_date"] = one(LOAN)[0], one(ORIG)[0]
    a["field_a"], a["field_b"] = one(TOP)[0], one(BOTTOM)[0]
    a["name"] = _slug(f"{a['field_a']}_vs_{a['field_b']}")
    return a


def describe(a: dict) -> list[str]:
    """What was read from the form, one line per answer, for the screen."""
    kind = "/" if a["kind"] == "ratio" else "-"
    steps = ", ".join(_fmt(x) for x in a["buckets"]) + (" (the quartiles of top - bottom, from the data)" if a.get("buckets_proposed") else "")
    out = a["outcome"]
    if "date_field" in out:
        bad = f"{out['date_field']} (the date it happened)"
    elif "field" in out:
        bad = f"{out['field']} = {_fmt(out['value'])} (a flag the bank set)"
    else:
        m = out["measure"]
        how = f"at or above {_fmt(out['value'])}" if "value" in out else "bands at " + ", ".join(_fmt(x) for x in out["edges"])
        bad = f"{m['field_a']} {'/' if m['kind'] == 'ratio' else '-'} {m['field_b']} {how}, at the as-of date"
    groups = []
    for c in a["confounders"]:
        if "edges" in c:
            groups.append(f"{c['name']} (edges " + ", ".join(_fmt(x) for x in c["edges"])
                          + (", its quartiles from the data" if c.get("proposed") else "") + ")")
        else:
            groups.append(f"{c['name']} (level by level)")
    lines = [
        f"  loan number       {a['loan_id']}",
        f"  origination date  {a['origination_date']}",
        f"  rule              {a['field_a']} {kind} {a['field_b']}, fires above {_fmt(a['fires_value'])}, steps {steps}",
        f"  went bad          {bad}",
        f"  groups            " + ("; ".join(groups) if groups else "none (step 4 will have nothing to test inside)"),
        f"  window            {a['window_months']} months; as-of {a['asof'].isoformat()}; "
        + (f"run date {a['run_date'].isoformat()}" if a.get("run_date") else "run date not given"),
        f"  reacts today      {a['existing_control']}",
    ]
    return lines


def to_yaml(a: dict, columns: list[str]) -> str:
    head = (f"# Question file written from {FORM_NAME}. Change the form in Excel and run the\n"
            f"# setup again to answer differently; nothing here needs editing by hand.\n")
    clean = {k: v for k, v in a.items() if k != "buckets_proposed"}
    clean["confounders"] = [{k: v for k, v in c.items() if k != "proposed"} for c in a["confounders"]]
    return head + answers_to_yaml(clean, columns)


__all__ = ["FORM_NAME", "ROLES", "FormError", "NotFilled", "write_form", "read_form", "describe", "to_yaml"]
