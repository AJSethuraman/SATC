"""Turn a tool configuration into a working Excel workbook in the "Paper" design.

    python3 workpaper-studio/excel/build_tool_workbook.py      # packs/*.json -> excel/out/*.xlsx (blank tool + filled example)
    python3 workpaper-studio/excel/check_tool_workbooks.py     # LibreOffice recalculates; results are read by defined name

The application exports a case through build_workbook(); the demo script above uses the same function.

The look is the Paper design's Build sheet (design/paper/Paper System.html, Build sheet): a soft stone ground, lighter paper cards, inset
paper-white fields with a sunken bevel and a small gap to the next field, flat recessed computed cells, header bars in the
tool's color family, and colour that only ever means a state. Plain cell formatting only: no shapes, images or macros.
Excel is only the engine; buttons are HYPERLINK formulas and logic is formulas.

The grid: every logical column is a wide column followed by a narrow spacer, so fields that sit side by side never touch.
Two ground-coloured gutters split the width into thirds, so cards placed side by side float apart. Everything above the
grid works in logical columns; only Screen.put and the letter helpers know the physical layout.

The configuration is the builder's "As data" (sections of fields, the one table primitive, library calculations).
Nothing about a particular tool is written in this file.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter as RAW
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONFIGS, OUT = ROOT / "packs", ROOT / "excel" / "out"

FONT = "Arial"
UNLOCK = Protection(locked=False)
NUMF = {"money": '"$"#,##0;("$"#,##0);"$0"', "money2": '"$"#,##0.00;("$"#,##0.00);"$0.00"', "number": '#,##0;(#,##0);"0"',
        "pct": "0.0%", "date": "yyyy-mm-dd"}
ENTERED_ROWS, ENTERED_COLS = 6, 4

# ---------------------------------------------------------------- palette (Build sheet: Paper)
GROUND = "E4E0D9"


def shade(h, d):
    return "".join(f"{max(0, min(255, int(h[i:i + 2], 16) + d)):02X}" for i in (0, 2, 4))


def mix(a, b, k):
    return "".join(f"{round(int(a[i:i + 2], 16) * (1 - k) + int(b[i:i + 2], 16) * k):02X}" for i in (0, 2, 4))


CARD, FIELD, RECESS, NA, RULE = shade(GROUND, 7), shade(GROUND, 19), shade(GROUND, -7), shade(GROUND, -16), shade(GROUND, -17)
EDGE_D, EDGE_L = "A29E97", shade(GROUND, 21)
INPUT_INK, INK, MUTE = "1A1A1A", "262421", "6D6A63"
OK, OK_T, WARN, WARN_T, WARN_E, BAD, BAD_T = "1F6F46", "DCEBDD", "8A5A00", "F6E3B2", "CF9A33", "A92A21", "F4D9D4"
FAMILIES = {   # one hue, dark (band, static text) and mid (header bars are dark x .28 + mid x .72)
    "navy": ("2B3A55", "3D5A8F"), "forest": ("1F4D3C", "2F7058"), "burgundy": ("5C2837", "8A3F55"), "teal": ("1C4F58", "2B7782"),
    "plum": ("3F2D5C", "6246A0"), "bronze": ("5A3F1A", "8A6226"), "graphite": ("2E3136", "5A6068")}

# ---------------------------------------------------------------- grid
FIRST, LAST = 2, 25                 # logical columns; three thirds of eight: 2-9, 10-17, 18-25
THIRDS = (9, 17)
HELP_APPLIES, HELP_MISSING = 28, 29  # hidden helper columns, logical; cards side by side each get their own pair
HELPERS = {0: (28, 29), 1: (30, 31), 2: (32, 33)}
W_WIDE, W_SPACER, W_GUTTER = 3.9, 0.5, 1.3


def _build_grid():
    phys, widths = {}, {1: W_GUTTER}
    col = 2
    for c in range(FIRST, LAST + 1):
        widths[col] = W_SPACER; col += 1           # spacer before: field gap, or card padding
        phys[c] = col; widths[col] = W_WIDE; col += 1
        if c in THIRDS:
            widths[col] = W_SPACER; col += 1       # trailing padding of the left card
            widths[col] = W_GUTTER; col += 1       # ground gutter between cards
    widths[col] = W_SPACER; col += 1               # trailing padding of the last card
    widths[col] = W_GUTTER; right = col; col += 1
    for c in range(26, 34):
        phys[c] = col; col += 1
    return phys, widths, right


PHYS, WIDTHS, RIGHT = _build_grid()
GUTTERS = {k for k, w in WIDTHS.items() if w == W_GUTTER}


def P(c):
    return PHYS[c]


def L(c):
    return RAW(PHYS[c])


def F(size=10, bold=False, color=INK, italic=False, strike=False):
    return Font(name=FONT, size=size, bold=bold, color=color, italic=italic, strike=strike)


def fill(hex_):
    return PatternFill("solid", fgColor=hex_)


def sname(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def q(sheet, coord):
    col, row = re.match(r"([A-Z]+)(\d+)", coord).groups()
    return f"'{sheet}'!${col}${row}"


def qr(sheet, c1, c2):
    a, b = re.match(r"([A-Z]+)(\d+)", c1).groups(), re.match(r"([A-Z]+)(\d+)", c2).groups()
    return f"'{sheet}'!${a[0]}${a[1]}:${b[0]}${b[1]}"


def thin(color, style="thin"):
    return Side(style=style, color=color)


class Style:
    def __init__(self, family):
        self.dark, mid = FAMILIES[family]
        self.bar = mix(self.dark, mid, 0.72)
        self.sub = mix(self.dark, "FFFFFF", 0.7)
        self.label = mix(self.dark, "FFFFFF", 0.22)
        self.inset = Border(top=thin(EDGE_D), left=thin(EDGE_D), bottom=thin(EDGE_L), right=thin(EDGE_L))
        self.missing = Border(top=thin(WARN_E), left=thin(WARN_E), bottom=thin(WARN_E), right=thin(WARN_E))
        self.nc = Border(bottom=thin("8C857A", "dashed"))
        self.rule = Border(bottom=thin(RULE))
        self.under = Border(bottom=thin(self.dark))
        self.button = mix(self.dark, "FFFFFF", 0.16)
        self.btn = Border(top=thin(mix(self.dark, "FFFFFF", 0.5)), left=thin(mix(self.dark, "FFFFFF", 0.5)),
                          bottom=thin(mix(self.dark, "000000", 0.35)), right=thin(mix(self.dark, "000000", 0.35)))


class Screen:
    """One worksheet in the Paper design."""

    def __init__(self, book, title, name):
        self.book, self.st = book, book.st
        self.ws = book.wb.create_sheet(name)
        self.name, self.title = name, title
        self.r = 7
        self.cards = []          # (r1, c1, r2, c2) in logical columns
        self.cur_inputs = []

    def put(self, r, c1, value=None, c2=None, h=None, font=None, align=None, fill_=None, border=None, fmt=None, unlock=False):
        ws = self.ws
        c2 = c2 or c1
        p1, p2 = P(c1), P(c2)
        if p2 > p1 or (h and h > 1):
            ws.merge_cells(start_row=r, start_column=p1, end_row=r + (h or 1) - 1, end_column=p2)
        cell = ws.cell(r, p1, value)
        cell.font = font or F()
        if align: cell.alignment = align
        if fmt: cell.number_format = fmt
        if unlock: cell.protection = UNLOCK
        for rr in range(r, r + (h or 1)):
            for cc in range(p1, p2 + 1):
                x = ws.cell(rr, cc)
                if fill_: x.fill = fill(fill_)
                if border: x.border = border
        return cell

    def height(self, r, pt):
        self.ws.row_dimensions[r].height = pt

    def card(self, r1, c1, r2, c2):
        self.cards.append((r1, c1, r2, c2))

    def bar(self, r, c1, c2, text, right=None):
        """Header bar of a card or section: family bar colour, white bold caps."""
        st = self.st
        self.height(r, 20)
        p1, p2 = P(c1) - 1, P(c2) + 1
        for cc in range(p1, p2 + 1):
            self.ws.cell(r, cc).fill = fill(st.bar)
        if right:
            self.put(r, c1, text.upper(), c2 - 3, font=F(10, True, "FFFFFF"), align=Alignment(horizontal="center", vertical="center"))
            self.put(r, c2 - 2, right, c2, font=F(8, False, "FFFFFF"), align=Alignment(horizontal="right", vertical="center"))
        else:
            self.put(r, c1, text.upper(), c2, font=F(10, True, "FFFFFF"), align=Alignment(horizontal="center", vertical="center"))

    def band(self, subtitle, buttons):
        ws, st = self.ws, self.st
        for c in range(1, RIGHT + 1):
            for r in (1, 2, 3, 4):
                ws.cell(r, c).fill = fill(st.dark)
        self.height(1, 5); self.height(2, 24); self.height(3, 15); self.height(4, 4)
        self.put(2, FIRST, self.title.upper(), LAST - 3 * len(buttons), font=F(14, True, "FFFFFF"), align=Alignment(vertical="center", indent=1))
        self.put(3, FIRST, subtitle, FIRST + 14, font=F(8, False, st.sub), align=Alignment(vertical="center", indent=1))
        col = LAST - 3 * len(buttons) + 1
        for text, target in buttons:
            cell = self.put(2, col, f'=HYPERLINK("#\'{target}\'!A1","{text.upper()}")', col + 2, font=F(8, True, "FFFFFF"),
                            align=Alignment(horizontal="center", vertical="center"), fill_=st.button, border=st.btn)
            col += 3

    def finish(self, last_row):
        ws, st = self.ws, self.st
        top = 5
        for r in range(top, last_row + 3):
            for c in range(1, RIGHT + 2):
                if ws.cell(r, c).fill.fill_type is None:
                    ws.cell(r, c).fill = fill(GROUND)
        for r1, c1, r2, c2 in self.cards:
            for r in range(r1, r2 + 1):
                for c in range(P(c1) - 1, P(c2) + 2):
                    x = ws.cell(r, c)
                    if x.fill.fill_type is None or x.fill.fgColor.rgb in ("00" + GROUND, "FF" + GROUND):
                        x.fill = fill(CARD)
        for r in range(1, 5):
            for c in range(1, RIGHT + 2):
                if ws.cell(r, c).fill.fill_type is None:
                    ws.cell(r, c).fill = fill(st.dark)
        for k, w in WIDTHS.items():
            ws.column_dimensions[RAW(k)].width = w
        for c in range(28, 34):
            ws.column_dimensions[L(c)].hidden = True
        ws.sheet_view.showGridLines = False
        ws.sheet_view.showRowColHeaders = False
        ws.sheet_view.zoomScale = 100
        ws.freeze_panes = "A7"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_margins.left = ws.page_margins.right = ws.page_margins.top = ws.page_margins.bottom = 0.4
        ws.print_area = f"A1:{RAW(RIGHT)}{last_row + 1}"
        ws.protection.sheet = True
        ws.protection.selectLockedCells = True
        ws.protection.formatColumns = ws.protection.formatRows = ws.protection.formatCells = False


class Book:
    def __init__(self, cfg):
        self.cfg, self.tool, self.org = cfg, cfg["tool"], cfg["org"]
        self.st = Style(cfg.get("family", "navy"))
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.example = cfg.get("example", {}) if cfg.get("_fill") else {}
        self.addr, self.grid = {}, {}
        self.sections, self.record = [], []
        self.screens, self.limits, self.framework_rows = {}, {}, {}
        self.labels = {b["id"]: b["label"] for s in self.tool["sections"] for b in s["blocks"] if b["kind"] == "field"}

    def name(self, nm, sheet, coord):
        self.wb.defined_names[nm] = DefinedName(nm, attr_text=q(sheet, coord))

    def validate(self, scr, cell, f):
        t = f.get("type")
        if t in ("list", "choice"):
            src = f"=List_{sname(f['list'])}" if t == "list" else '"' + ",".join(f["opts"]) + '"'
            dv = DataValidation(type="list", formula1=src, allow_blank=True, showErrorMessage=True, errorTitle="Pick from the list", error="Choose one of the listed answers.")
        elif t == "number":
            dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True, showErrorMessage=True,
                                errorTitle="A number", error="Enter a number, 0 or more. Leave it blank if you do not know it yet.")
        elif t == "date":
            dv = DataValidation(type="date", operator="greaterThan", formula1="1", allow_blank=True, showErrorMessage=True, errorTitle="A date", error="Enter a date.")
        else:
            return
        scr.ws.add_data_validation(dv)
        dv.add(cell.coordinate)

    def input(self, scr, r, c1, c2, f, value, h=None, align=None):
        t = f.get("type")
        if t == "date" and isinstance(value, str):
            value = datetime.date.fromisoformat(value)
        fmt = None
        if t == "date":
            fmt = NUMF["date"]
        elif t == "number":
            fmt = NUMF["money2" if f.get("cents") else "money"] if f.get("money") else NUMF["number"]
        horiz = align or ("right" if t == "number" else "left" if t == "longtext" else "center")
        cell = scr.put(r, c1, value, c2, h=h, fill_=FIELD, border=self.st.inset, fmt=fmt, unlock=True, font=F(10, color=INPUT_INK),
                       align=Alignment(vertical="top" if t == "longtext" else "center", wrap_text=t in ("longtext", "comment"),
                                       horizontal=horiz, indent=1 if horiz != "center" else 0, shrink_to_fit=t not in ("longtext", "comment")))
        scr.cur_inputs.append(cell.coordinate)
        self.validate(scr, cell, f)
        return cell

    def calc(self, scr, r, c1, c2, formula, fmt=None, size=10, bold=False):
        return scr.put(r, c1, formula, c2, fill_=RECESS, fmt=fmt, font=F(size, bold),
                       align=Alignment(horizontal="right", vertical="center", indent=1))

    def missing_cf(self, scr, coord, when):
        """Required and empty: amber fill, amber edge."""
        scr.ws.conditional_formatting.add(coord, FormulaRule(formula=[when], fill=fill(WARN_T), border=self.st.missing,
                                                             font=Font(name=FONT, color=WARN, italic=True), stopIfTrue=True))

    @staticmethod
    def slot(c1):
        """Which third a card starts in. Cards side by side share rows, so each keeps its hidden helpers in its own columns."""
        return 0 if c1 <= THIRDS[0] else 1 if c1 <= THIRDS[1] else 2

    def applies(self, rule):
        if not rule:
            return '"Yes"'
        a = self.addr[rule["field"]]
        cond = "OR(" + ",".join(f'{a}="{v}"' for v in rule["values"]) + ")"
        return f'IF({a}="","Waiting",IF({cond},"Yes","No"))'

    def rule_text(self, rule):
        return f'“{self.labels.get(rule["field"], rule["field"])}” is {" or ".join(rule["values"])}'

    def screen_for(self, s):
        nm = s.get("screen", "Workpaper")
        if nm not in self.screens:
            title = self.tool["name"] if nm == "Workpaper" else f'{self.tool["name"]}: {nm}'
            self.screens[nm] = Screen(self, title, nm)
        return self.screens[nm]

    # ------------------------------------------------------------ sections
    def section_head(self, scr, s, c1=FIRST, c2=LAST):
        r = scr.r
        scr.bar(r, c1, c2, s["title"])
        rule = s.get("rule") if s["mode"] == "conditional" else None
        ha, _ = HELPERS[self.slot(c1)]
        scr.ws.cell(r, P(ha), "=" + self.applies(rule) if rule else "Yes")
        scr.r += 1
        if rule:
            scr.height(scr.r, 15)
            scr.put(scr.r, c1, f"Shown only when {self.rule_text(rule)}", c2, font=F(9, False, MUTE, True), align=Alignment(vertical="center"))
            scr.r += 1
        elif s["mode"] == "optional":
            scr.height(scr.r, 15)
            scr.put(scr.r, c1, "Optional: complete it if it helps the review", c2, font=F(9, False, MUTE, True), align=Alignment(vertical="center"))
            scr.r += 1
        scr.req = []
        return r, f"${L(ha)}${r}"

    def section_close(self, scr, s, head_row, applies_ref, terms, start, c1=FIRST, c2=LAST):
        ws, st = scr.ws, self.st
        r = scr.r
        scr.height(r, 17)
        status = scr.put(r, c2 - 5, None, c2, font=F(10, True, MUTE), align=Alignment(horizontal="right", vertical="center", indent=1))
        miss = "+".join(terms) if terms else "0"
        optional = s["mode"] == "optional"
        started = "+".join(f'({a}<>"")' for a in scr.cur_inputs) or "0"
        _, hm = HELPERS[self.slot(c1)]
        m = ws.cell(head_row, P(hm))
        m.value = (f'=IF({applies_ref}="No",0,IF(({started})=0,0,{miss}))' if optional
                   else f'=IF({applies_ref}="No",0,IF({applies_ref}="Waiting",1,{miss}))')
        opt = f'IF(({started})=0,"Optional",' if optional else "("
        status.value = (f'=IF({applies_ref}="No","Not applicable",IF({applies_ref}="Waiting","Waiting on an answer",'
                        f'{opt}IF(({miss})=0,"Complete",({miss})&" missing"))))')
        sc = status.coordinate
        ws.conditional_formatting.add(sc, FormulaRule(formula=[f'{sc}="Complete"'], font=Font(name=FONT, color=OK, bold=True)))
        ws.conditional_formatting.add(sc, FormulaRule(formula=[f'ISNUMBER(SEARCH("missing",{sc}))'], font=Font(name=FONT, color=WARN, bold=True)))
        gate = (f'AND({applies_ref}="Yes",' if s["mode"] == "conditional" else f'AND(({started})>0,' if optional else "AND(TRUE,")
        for coord, extra in scr.req:
            self.missing_cf(scr, coord, f"{gate}{extra})")
        if s["mode"] == "conditional" and r > start:
            ws.conditional_formatting.add(f"{L(c1)}{start}:{L(c2)}{r - 1}",
                                          FormulaRule(formula=[f'{applies_ref}="No"'], fill=fill(NA), border=Border(), font=Font(name=FONT, color=MUTE, italic=True)))
        scr.card(head_row, c1, r, c2)
        self.sections.append({"id": s["id"], "title": s["title"], "status": q(scr.name, sc), "missing": q(scr.name, f"{L(hm)}{head_row}"), "screen": scr.name})
        self.name(f"Status_{sname(s['id'])}", scr.name, sc)
        scr.r = r + 1

    def fields_panel(self, scr, fields, c1, c2):
        terms = []
        longest = max([len(f["label"]) for f in fields if f.get("type") != "longtext"] or [0])
        lw = max(3, min(c2 - c1 - 2, -(-(longest * 6 + 10) // 38)))
        for f in fields:
            val = self.example.get(f["id"])
            r = scr.r
            if f.get("type") == "longtext":
                scr.height(r, 16)
                scr.put(r, c1, f["label"], c2, font=F(10, color=self.st.label), align=Alignment(vertical="center", indent=1))
                for k in range(1, 5):
                    scr.height(r + k, 16)
                cell = self.input(scr, r + 1, c1, c2, f, val, h=4)
                scr.r = r + 5
            else:
                scr.height(r, 17)
                scr.put(r, c1, f["label"], c1 + lw - 1, font=F(10, color=self.st.label),
                        align=Alignment(vertical="center", indent=1, shrink_to_fit=True))
                cell = self.input(scr, r, c1 + lw, c2, f, val)
                scr.r = r + 1
            scr.height(scr.r, 3); scr.r += 1               # spacer row: fields never touch
            ref = q(scr.name, cell.coordinate)
            self.addr[f["id"]] = ref
            self.name(f"Field_{sname(f['id'])}", scr.name, cell.coordinate)
            if f.get("req"):
                terms.append(f'({cell.coordinate}="")*1')
                scr.req.append((cell.coordinate, f'{cell.coordinate}=""'))
            self.record.append((f["label"], f'=IF({ref}="","",{ref})'))
        return terms

    def grid_block(self, scr, g):
        rows_from, cols_from, by = g["rows"]["from"], g["cols"]["from"], g.get("cellsBy", "col")
        lists, ex = self.org["lists"], self.example.get(g["id"], {})
        n_entered = max(ENTERED_ROWS, g["rows"].get("min", 0), len(ex.get("rows") or []) + 2)
        R = (g["rows"].get("items") if rows_from == "fixed" else
             [{"key": v, "label": v} for v in lists[g["rows"]["list"]]] if rows_from == "list" else
             [{"key": i, "label": f'{(g["rows"].get("addLabel") or "Row").capitalize()} {i + 1}'} for i in range(n_entered)])
        C = (g["cols"].get("items") if cols_from == "fixed" else
             [{"key": f"c{j}", "label": f'{g["cols"].get("addLabel", "Column")} {j + 1}'} for j in range(ENTERED_COLS)])
        if rows_from == "fixed" and by == "col" and any(x.get("group") or x.get("info") for x in R):
            return self.questions(scr, g, R, C, ex)
        return self.table(scr, g, R, C, ex, rows_from, cols_from, by)

    def questions(self, scr, g, R, C, ex):
        ws, st, terms = scr.ws, self.st, []
        rating, comment = C[0], (C[1] if len(C) > 1 else None)
        last_group = None
        for qd in R:
            if qd.get("group") and qd["group"] != last_group:
                scr.height(scr.r, 22)
                scr.put(scr.r, FIRST, qd["group"], FIRST + 11, font=F(11, True, st.dark), align=Alignment(vertical="bottom", indent=1))
                scr.r += 1
                last_group = qd["group"]
            r = scr.r
            scr.height(r, 40)
            when = qd.get("when")
            num = scr.put(r, FIRST, str(qd["key"]), FIRST + 1, font=F(10, True, st.dark), align=Alignment(horizontal="center", vertical="center"))
            if when:
                lab = self.labels.get(when["field"], when["field"]).rstrip("?").lower()
                num.value = f'{qd["key"]}\nif {lab}' if when["values"] == ["Yes"] else f'{qd["key"]}\nif {", ".join(when["values"]).lower()}'
                num.font = F(8, True, st.dark)
                num.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            box = scr.put(r, FIRST + 2, f"=Framework!D{self.framework_rows[qd['key']]}", FIRST + 10, border=st.rule,
                          font=F(11, False, st.dark), align=Alignment(wrap_text=True, vertical="center", indent=1))
            if qd.get("info"):
                box.comment = Comment("How to test this:\n" + qd["info"], "Framework", width=330, height=150)
            v = ex.get(str(qd["key"]), {})
            rc = self.input(scr, r, FIRST + 11, FIRST + 14, rating, v.get(rating["key"]), align="center")
            cm = self.input(scr, r, FIRST + 15, LAST, dict(comment, type="comment"), v.get(comment["key"]), align="left") if comment else None
            ws.cell(r, P(HELP_APPLIES), "=" + self.applies(when))
            apc = f"${L(HELP_APPLIES)}{r}"
            rcc, cmc = rc.coordinate, (cm.coordinate if cm else None)
            rw = comment.get("reqWhen") if comment else None
            need = (f'AND(OR({",".join(f"{rcc}=" + chr(34) + x + chr(34) for x in rw["values"])}),{cmc}="")') if rw else "FALSE"
            terms += [f'({apc}="Yes")*(({rcc}="")+({need}))', f'({apc}="Waiting")*1']
            ws.conditional_formatting.add(f"{L(FIRST)}{r}:{L(LAST)}{r}",
                                          FormulaRule(formula=[f'{apc}="No"'], fill=fill(NA), border=Border(), font=Font(name=FONT, color=MUTE, italic=True), stopIfTrue=True))
            self.missing_cf(scr, rcc, f'AND({apc}<>"No",{rcc}="")')
            if cm:
                self.missing_cf(scr, cmc, f'AND({apc}<>"No",{need})')
            for val_, col in (("Not effective", BAD), ("Partially effective", WARN), ("Effective", OK)):
                ws.conditional_formatting.add(rcc, FormulaRule(formula=[f'{rcc}="{val_}"'], font=Font(name=FONT, color=col)))
            self.record.append((f'{rating["label"]}_{qd["key"]}', f'=IF({q(scr.name, f"{L(HELP_APPLIES)}{r}")}="No","Not applicable",{q(scr.name, rcc)})'))
            if cm:
                self.record.append((f'{comment["label"]}_{qd["key"]}', f'=IF({q(scr.name, cmc)}="","",{q(scr.name, cmc)})'))
            scr.height(r + 1, 4)
            scr.r += 2
        return terms

    def table(self, scr, g, R, C, ex, rows_from, cols_from, by):
        ws, st, terms = scr.ws, self.st, []
        longest = max(len(str(x["label"])) for x in R + [{"label": "Total"}])
        lab_w = max(2, -(-(longest * 7 + 12) // 38))
        data_c1 = FIRST + lab_w
        total = LAST - data_c1 + 1
        weight = [3 if (c.get("type") == "text" and by == "col") else 2 for c in C]
        units = [max(2, total * w // sum(weight)) for w in weight]
        for j in range(total - sum(units)):
            units[j % len(units)] += 1
        cols, a = [], data_c1
        for w in units:
            cols.append((a, a + w - 1)); a += w
        if g.get("label") and not g.get("hideLabel") and g["label"].lower() != (g.get("_section") or "").lower():
            scr.height(scr.r, 6); scr.r += 1
            scr.bar(scr.r, FIRST, LAST, g["label"])
            scr.r += 1
            scr.height(scr.r, 4); scr.r += 1
        hdr = scr.r
        tight = any(len(c["label"]) * 8 + 10 > (b - a + 1) * 38 for c, (a, b) in zip(C, cols))
        scr.height(hdr, 28 if tight else 18)
        cols_ex = list(ex.get("_cols") or [])
        for j, (c, (a, b)) in enumerate(zip(C, cols)):
            if cols_from == "entered":
                h = self.input(scr, hdr, a, b, {"type": "text"}, cols_ex[j] if j < len(cols_ex) else c["label"], align="center")
                scr.cur_inputs.remove(h.coordinate)
            else:
                scr.put(hdr, a, c["label"].upper(), b, border=st.under, font=F(10, True, st.dark), align=Alignment(horizontal="center", vertical="bottom", wrap_text=True))
        scr.r += 1
        scr.height(scr.r, 3); scr.r += 1
        first = scr.r
        rows_at = []
        for i, row in enumerate(R):
            r = scr.r
            rows_at.append(r)
            scr.height(r, 17)
            scr.put(r, FIRST, row["label"], FIRST + lab_w - 1, font=F(10, False, st.dark, italic=bool(row.get("compute"))),
                    align=Alignment(vertical="center", indent=1))
            exrow = ((ex.get("rows") or [])[i] if i < len(ex.get("rows") or []) else {}) if rows_from == "entered" else (ex.get(str(row["key"])) or {})
            for j, (c, (a, b)) in enumerate(zip(C, cols)):
                d = row if by == "row" else c
                if d.get("compute"):
                    cc = d["compute"]
                    if by == "col":
                        ka = [x["key"] for x in C]
                        A_, B_ = f"{L(cols[ka.index(cc['a'])][0])}{r}", f"{L(cols[ka.index(cc['b'])][0])}{r}"
                    else:
                        kr = [x["key"] for x in R]
                        A_, B_ = f"{L(a)}{rows_at[0] + 2 * kr.index(cc['a'])}", f"{L(a)}{rows_at[0] + 2 * kr.index(cc['b'])}"
                    expr = {"mul": f"{A_}*{B_}", "pctof": f"{A_}*{B_}/100", "add": f"{A_}+{B_}", "sub": f"{A_}-{B_}", "div": f'IF({B_}=0,"",{A_}/{B_})'}[cc["op"]]
                    self.calc(scr, r, a, b, f'=IF(OR({A_}="",{B_}=""),"",{expr})', (NUMF["money2"] if d.get("cents") else NUMF["money"]) if d.get("money") else NUMF["number"])
                else:
                    val = exrow.get(f"c{j}") if cols_from == "entered" else exrow.get(c["key"])
                    self.input(scr, r, a, b, d, val)
            scr.r += 1
            scr.height(scr.r, 3); scr.r += 1
        last = rows_at[-1]
        self.grid[g["id"]] = {"cols": {c["key"]: qr(scr.name, f"{L(a)}{first}", f"{L(a)}{last}") for c, (a, b) in zip(C, cols)}}
        if rows_from == "entered":
            inputs = [L(a) for c, (a, b) in zip(C, cols) if not c.get("compute")]
            used = "((" + "+".join(f'({x}{first}:{x}{last}<>"")' for x in inputs) + ")>0)"
            req = [L(a) for c, (a, b) in zip(C, cols) if c.get("req") and not c.get("compute")]
            if req:
                terms.append(f'SUMPRODUCT({used}*((' + "+".join(f'({x}{first}:{x}{last}="")' for x in req) + ')>0))')
                for r in rows_at:
                    row_used = "OR(" + ",".join(f'{x}{r}<>""' for x in inputs) + ")"
                    for x in req:
                        scr.req.append((f"{x}{r}", f'{row_used},{x}{r}=""'))
            mn = g["rows"].get("min", 0)
            if mn:
                terms.append(f'(SUMPRODUCT({used}*1)<{mn})*1')
            self.record.append((f'{g["label"]} (rows used)', "=SUMPRODUCT(((" + "+".join(f'({qr(scr.name, f"{x}{first}", f"{x}{last}")}<>"")' for x in inputs) + ")>0)*1)"))
        else:
            for i, row in enumerate(R):
                r = rows_at[i]
                for c, (a, b) in zip(C, cols):
                    d = row if by == "row" else c
                    if d.get("req") and not d.get("compute"):
                        x = L(a)
                        if cols_from == "entered":
                            terms.append(f'(SUMPRODUCT(({x}{first}:{x}{last}<>"")*1)>0)*({x}{r}="")')
                        else:
                            terms.append(f'({x}{r}="")*1')
                            scr.req.append((f"{x}{r}", f'{x}{r}=""'))
        if g.get("totals"):
            r = scr.r
            scr.height(r, 18)
            scr.put(r, FIRST, "Total", FIRST + lab_w - 1, font=F(10, True, st.dark), align=Alignment(vertical="center", indent=1))
            inputs_all = [L(a) for c, (a, b) in zip(C, cols) if not c.get("compute")]
            used_rng = "((" + "+".join(f'({x}{first}:{x}{last}<>"")' for x in inputs_all) + ")>0)"
            for c, (a, b) in zip(C, cols):
                if by == "col" and (c.get("type") == "number" or c.get("compute")) and not c.get("noTotal"):
                    x = L(a)
                    total = f"SUM({x}{first}:{x}{last})"
                    if c.get("req") and not c.get("compute"):      # a total over a column with a required gap is not a total
                        gap = (f'SUMPRODUCT({used_rng}*({x}{first}:{x}{last}=""))>0' if rows_from == "entered"
                               else "OR(" + ",".join(f'{x}{rr}=""' for rr in rows_at) + ")")
                        total = f'IF({gap},"Not calculated",{total})'
                    cell = self.calc(scr, r, a, b, "=" + total, (NUMF["money2"] if c.get("cents") else NUMF["money"]) if c.get("money") else NUMF["number"], bold=True)
                    scr.ws.conditional_formatting.add(cell.coordinate, FormulaRule(formula=[f'NOT(ISNUMBER({cell.coordinate}))'], fill=fill(CARD), border=st.nc,
                                                                                   font=Font(name=FONT, color=MUTE, italic=True, bold=False)))
                    self.name(f"Total_{sname(g['id'])}_{sname(c['key'])}", scr.name, cell.coordinate)
            scr.r += 1
        scr.height(scr.r, 6); scr.r += 1
        return terms

    def calc_block(self, scr, b):
        ws, st, m = scr.ws, self.st, b["method"]
        lim = self.limits[b["id"]]
        nm = {"dti": "Debt-to-income", "ltv": "Loan-to-value", "recon": "Reconciliation", "devrate": "Deviation rate"}[m]
        scr.height(scr.r, 6); scr.r += 1
        scr.bar(scr.r, FIRST, LAST, nm, right=b.get("code", ""))
        scr.r += 1
        scr.height(scr.r, 4); scr.r += 1
        if m == "dti":
            bind = b["inputs"]
            g = self.grid[bind["income"]]["cols"]; a, per, src = g["amount"], g["per"], g["source"]
            dg = self.grid[bind["debts"]]["cols"]; d, cred = dg["payment"], dg["creditor"]
            pr = self.addr[bind["proposed"]]
            used = f'(({src}<>"")+({a}<>"")+({per}<>"")>0)'
            rows = [("Monthly income", f'=SUMPRODUCT(({per}="Annual")*({a})/12+({per}="Monthly")*({a}))', NUMF["money"]),
                    ("Existing monthly debt payments", f"=SUM({d})", NUMF["money"]),
                    ("Proposed monthly payment", f"=N({pr})", NUMF["money"]),
                    ("Inputs still missing", f'=SUMPRODUCT({used}*((({a}="")+({per}=""))>0))+SUMPRODUCT(((({cred}<>"")+({d}<>""))>0)*({d}=""))+({pr}="")+(SUMPRODUCT({used}*1)=0)', "0")]
        elif m == "devrate":
            g = self.grid[b["grid"]]["cols"]
            cr = [g[k] for k in b["attributes"]]
            any_ex, tested = "+".join(f'({c}="Exception")' for c in cr), "+".join(f'({c}<>"")' for c in cr)
            rows = [("Items tested", f"=SUMPRODUCT((({tested})>0)*1)", "0"),
                    ("Items with an exception", f"=SUMPRODUCT((({any_ex})>0)*1)", "0"),
                    ("Inputs still missing", f"=SUMPRODUCT(((({tested})>0)*(({tested})<{len(cr)}))*1)", "0")]
        else:
            bind = b["inputs"]
            g = self.grid[bind["items"]]["cols"]; t, a = g["type"], g["amount"]
            sb, gl = self.addr[bind["bank"]], self.addr[bind["books"]]
            rows = [("Adjusted bank", f'=N({sb})+SUMIF({t},"Deposit in transit",{a})-SUMIF({t},"Outstanding check",{a})', NUMF["money2"]),
                    ("Adjusted books", f'=N({gl})-SUMIF({t},"Bank fee not yet booked",{a})+SUMIF({t},"Interest not yet booked",{a})', NUMF["money2"]),
                    ("Inputs still missing", f'=({sb}="")+({gl}="")+SUMPRODUCT((({t}<>"")+({a}<>"")=1)*1)', "0")]
        refs = {}
        miss_at = f"{L(FIRST + 9)}{scr.r + 2 * (len(rows) - 1)}"
        for lab, f, fmt in rows:
            r = scr.r
            if lab != "Inputs still missing" and m != "devrate":     # a part-built figure is withheld, never shown as $0
                f = f'=IF({miss_at}>0,"Not calculated",{f[1:]})'
            scr.height(r, 16)
            scr.put(r, FIRST, lab, FIRST + 8, font=F(10, False, st.label), align=Alignment(horizontal="right", vertical="center", indent=1))
            cell = self.calc(scr, r, FIRST + 9, FIRST + 12, f, fmt)
            ws.conditional_formatting.add(cell.coordinate, FormulaRule(formula=[f'{cell.coordinate}="Not calculated"'], fill=fill(CARD), border=st.nc,
                                                                       font=Font(name=FONT, color=MUTE, italic=True)))
            refs[lab] = f"{L(FIRST + 9)}{r}"
            scr.r += 1
            scr.height(scr.r, 3); scr.r += 1
        r = scr.r
        scr.height(r, 22)
        scr.put(r, FIRST, {"dti": "Debt-to-income", "devrate": "Deviation rate", "recon": "Difference"}[m], FIRST + 8,
                font=F(10, True, st.dark), align=Alignment(horizontal="right", vertical="center", indent=1))
        miss = refs["Inputs still missing"]
        if m == "dti":
            f = f'=IF({miss}>0,"Not calculated",IF({refs["Monthly income"]}=0,"No result",({refs["Existing monthly debt payments"]}+{refs["Proposed monthly payment"]})/{refs["Monthly income"]}))'
            fmt = NUMF["pct"]
        elif m == "devrate":
            f = f'=IF(OR({miss}>0,{refs["Items tested"]}=0),"Not calculated",{refs["Items with an exception"]}/{refs["Items tested"]})'
            fmt = NUMF["pct"]
        else:
            f = f'=IF({miss}>0,"Not calculated",ROUND({refs["Adjusted bank"]}-{refs["Adjusted books"]},2))'
            fmt = NUMF["money2"]
        res = self.calc(scr, r, FIRST + 9, FIRST + 12, f, fmt, size=13, bold=True)
        rc = res.coordinate
        ws.conditional_formatting.add(rc, FormulaRule(formula=[f'NOT(ISNUMBER({rc}))'], fill=fill(CARD), border=st.nc,
                                                      font=Font(name=FONT, color=MUTE, italic=True, bold=False)))
        cmp = f"ABS({rc})<=Settings!{lim['policy']}+0.005" if m == "recon" else f"{rc}<=Settings!{lim['policy']}"
        verdict = scr.put(r, FIRST + 13, f'=IF(Settings!{lim["confirmed"]}<>"Yes","Not tested: limit not confirmed",IF(ISNUMBER({rc}),IF({cmp},"Within limit","Above limit"),"Not tested"))',
                          FIRST + 20, font=F(10, True, MUTE), align=Alignment(horizontal="left", vertical="center", indent=1))
        vc = verdict.coordinate
        for t_, col in (("Above limit", BAD), ("Within limit", OK)):
            ws.conditional_formatting.add(vc, FormulaRule(formula=[f'{vc}="{t_}"'], font=Font(name=FONT, color=col, bold=True)))
        ws.conditional_formatting.add(vc, FormulaRule(formula=[f'LEFT({vc},10)="Not tested"'], font=Font(name=FONT, color=MUTE, italic=True, bold=False)))
        scr.height(r + 1, 15)
        scr.put(r + 1, FIRST + 9, "The limit is on Settings, confirmed by the organization. It is not part of the method.", LAST,
                font=F(9, False, MUTE, True), align=Alignment(vertical="center", indent=1))
        self.name(f"Result_{sname(b['id'])}", scr.name, rc)
        self.name(f"Verdict_{sname(b['id'])}", scr.name, vc)
        for lab, ref in refs.items():
            self.name(f"Calc_{sname(b['id'])}_{sname(lab)}", scr.name, ref)
        self.record.append((nm, f"={q(scr.name, rc)}"))
        self.record.append((nm + " against limit", f"={q(scr.name, vc)}"))
        scr.r += 2

    def compact(self, s):
        return all(b["kind"] == "field" and b.get("type") != "longtext" for b in s["blocks"]) and len(s["blocks"]) <= 4

    def layout(self):
        secs, i = self.tool["sections"], 0
        thirds = [(FIRST, THIRDS[0]), (THIRDS[0] + 1, THIRDS[1]), (THIRDS[1] + 1, LAST)]
        while i < len(secs):
            s = secs[i]
            scr = self.screen_for(s)
            if self.compact(s):
                band = [s]
                while len(band) < 3 and i + len(band) < len(secs):
                    nx = secs[i + len(band)]
                    if nx.get("screen", "Workpaper") == s.get("screen", "Workpaper") and self.compact(nx):
                        band.append(nx)
                    else:
                        break
                r0, bottoms, built = scr.r, [], []
                for k, bs in enumerate(band):
                    c1, c2 = thirds[k]
                    scr.r, scr.cur_inputs = r0, []
                    head, ap = self.section_head(scr, bs, c1, c2)
                    scr.height(scr.r, 4); scr.r += 1
                    start = scr.r
                    terms = self.fields_panel(scr, bs["blocks"], c1, c2)
                    built.append((bs, head, ap, terms, start, c1, c2, scr.r, list(scr.cur_inputs), list(scr.req)))
                    bottoms.append(scr.r)
                foot = max(bottoms)
                for bs, head, ap, terms, start, c1, c2, end, inputs, req in built:
                    scr.r, scr.cur_inputs, scr.req = foot, inputs, req
                    self.section_close(scr, bs, head, ap, terms, start, c1, c2)
                scr.height(scr.r, 9); scr.r += 1
                i += len(band)
                continue
            scr.cur_inputs = []
            head, ap = self.section_head(scr, s)
            scr.height(scr.r, 6); scr.r += 1
            start, terms, run = scr.r, [], []
            for b in s["blocks"] + [None]:
                if b is not None and b["kind"] == "field" and b.get("type") != "longtext":
                    run.append(b); continue
                if run:
                    terms += self.fields_panel(scr, run, FIRST, FIRST + 11); run = []
                if b is None:
                    break
                if b["kind"] == "field":
                    terms += self.fields_panel(scr, [b], FIRST, LAST)
                elif b["kind"] == "grid":
                    terms += self.grid_block(scr, dict(b, hideLabel=len(s["blocks"]) == 1, _section=s["title"]))
                elif b["kind"] == "calc":
                    self.calc_block(scr, b)
            self.section_close(scr, s, head, ap, terms, start)
            scr.height(scr.r, 9); scr.r += 1
            i += 1

    def status_strip(self, scr):
        st, r = self.st, 5
        scr.height(r, 22); scr.height(6, 8)
        lab = lambda c1, c2, t: scr.put(r, c1, t, c2, font=F(8, True, st.dark), align=Alignment(vertical="center", indent=1))
        lab(FIRST, FIRST + 3, "READY FOR REVIEW")
        ready = scr.put(r, FIRST + 4, "=Ready", FIRST + 5, font=F(10, True), align=Alignment(horizontal="center", vertical="center"))
        lab(THIRDS[0] + 1, THIRDS[0] + 4, "STILL MISSING")
        scr.put(r, THIRDS[0] + 6, "=Missing", THIRDS[1], font=F(10, True), align=Alignment(horizontal="right", vertical="center", indent=1))
        lab(THIRDS[1] + 1, THIRDS[1] + 4, "SECTIONS COMPLETE")
        done = "+".join(f'OR({s["status"]}="Complete",{s["status"]}="Not applicable",{s["status"]}="Optional")*1' for s in self.sections)
        scr.put(r, THIRDS[1] + 6, f'=({done})&" of {len(self.sections)}"', LAST, font=F(10, True), align=Alignment(horizontal="right", vertical="center", indent=1))
        rc = ready.coordinate
        for v, bg, col in (("Yes", OK_T, OK), ("No", WARN_T, WARN)):
            scr.ws.conditional_formatting.add(rc, FormulaRule(formula=[f'{rc}="{v}"'], fill=fill(bg), font=Font(name=FONT, color=col, bold=True)))
        return ready

    # ------------------------------------------------------------ admin screens: same ground, band and bars
    def table_sheet(self, name, title, intro, heads, widths, rows, unlock_cols=(), fmts=None, heights=None):
        ws, st = self.wb.create_sheet(name), self.st
        n = max(2, len(heads))
        last_col = n + 2
        nrows = 6 + len(rows) + 6
        for r in range(1, nrows):
            for c in range(1, last_col + 1):
                ws.cell(r, c).fill = fill(st.dark if r <= 3 else GROUND)
        ws.row_dimensions[1].height = 5; ws.row_dimensions[2].height = 26; ws.row_dimensions[3].height = 6
        ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=n + 1)
        c = ws.cell(2, 2, title.upper()); c.font = F(14, True, "FFFFFF"); c.alignment = Alignment(vertical="center")
        ws.row_dimensions[4].height = 22
        if intro:
            ws.merge_cells(start_row=4, start_column=2, end_row=4, end_column=n + 1)
            x = ws.cell(4, 2, intro); x.font = F(9, False, MUTE, True); x.alignment = Alignment(vertical="center")
        if any(heads):
            for j, h in enumerate(heads, start=2):
                x = ws.cell(5, j, h.upper()); x.font = F(10, True, "FFFFFF"); x.fill = fill(st.bar)
                x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.row_dimensions[5].height = 22
        for i, row in enumerate(rows, start=6):
            ws.row_dimensions[i].height = (heights or 20)
            for j, v in enumerate(row, start=2):
                x = ws.cell(i, j, v)
                live = (j - 1) in unlock_cols
                x.font = F(10, bold=(j == 2 and not any(heads)), color=INPUT_INK if live else st.dark)
                x.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left", indent=1)
                x.fill = fill(FIELD if live else CARD)
                x.border = st.inset if live else st.rule
                if live:
                    x.protection = UNLOCK
                if fmts and (j - 1) in fmts:
                    x.number_format = fmts[j - 1]
        ws.column_dimensions["A"].width = 2
        for j, w in enumerate(widths, start=2):
            ws.column_dimensions[RAW(j)].width = w
        ws.column_dimensions[RAW(n + 2)].width = 2
        ws.sheet_view.showGridLines = False
        ws.sheet_view.showRowColHeaders = False
        ws.freeze_panes = "A6"
        ws.page_setup.orientation = "landscape"          # print one page wide, like the screens
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.protection.sheet = True
        ws.protection.formatColumns = ws.protection.formatRows = ws.protection.formatCells = False
        return ws

    def admin(self):
        st = self.st
        rows = []
        for s in self.tool["sections"]:
            for b in s["blocks"]:
                if b["kind"] == "grid" and b["rows"]["from"] == "fixed" and any(x.get("group") or x.get("info") for x in b["rows"]["items"]):
                    for qd in b["rows"]["items"]:
                        self.framework_rows[qd["key"]] = 6 + len(rows)
                        rows.append([qd.get("group", ""), qd["key"], qd["label"], qd.get("info", "")])
        if rows:
            self.table_sheet("Framework", f'{self.tool["name"]}: framework', "The questions and how to test each. The workpaper reads its wording from here.",
                             ["Section", "#", "Question", "How to test"], [20, 7, 52, 78], rows, unlock_cols=(3, 4), heights=46)
        lrows = []
        conf = self.cfg.get("confirmations", {}) if self.cfg.get("_fill") else {}
        pct = False
        for s in self.tool["sections"]:
            for b in s["blocks"]:
                if b["kind"] == "calc":
                    cf = conf.get(b["id"], {})
                    d = cf.get("date")
                    pct = pct or b["method"] in ("dti", "devrate", "ltv")
                    lrows.append([b["limitLabel"], b.get("code", ""), b["limit"], cf.get("policy", b["limit"]), cf.get("confirmed", "No"), cf.get("by"), datetime.date.fromisoformat(d) if d else None])
                    self.limits[b["id"]] = {"policy": f"$E${5 + len(lrows)}", "confirmed": f"$F${5 + len(lrows)}"}
        ws = self.table_sheet("Settings", "Settings", "Limits belong to this organization, not to the method. Until a limit is confirmed here, nothing is tested against it.",
                              ["Limit", "Method", "Author recommends", "Our policy", "Confirmed?", "Confirmed by", "Date"], [36, 16, 18, 14, 12, 18, 13], lrows,
                              unlock_cols=(4, 5, 6, 7), fmts={3: "0.0%" if pct else NUMF["money2"], 4: "0.0%" if pct else NUMF["money2"], 7: NUMF["date"]})
        dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True); ws.add_data_validation(dv)
        for i in range(len(lrows)):
            dv.add(f"F{6 + i}")
        lists = self.org["lists"]
        longest = max(len(v) for v in lists.values())
        grid = [[(vals[i] if i < len(vals) else None) for vals in lists.values()] for i in range(longest + 10)]
        self.table_sheet("Lists", "Lists", "Every dropdown reads from these lists. Add values at the end of a list.", list(lists),
                         [max(18, len(nm) + 4) for nm in lists], grid, unlock_cols=tuple(range(1, len(lists) + 1)))
        for j, (nm, vals) in enumerate(lists.items(), start=2):
            self.wb.defined_names[f"List_{sname(nm)}"] = DefinedName(f"List_{sname(nm)}", attr_text=f"Lists!${RAW(j)}$6:${RAW(j)}${5 + len(vals) + 10}")

    def check_sheet(self):
        rows = [[s["title"], f'=IF(OR({s["status"]}="Complete",{s["status"]}="Not applicable",{s["status"]}="Optional"),"OK",{s["status"]})', None] for s in self.sections]
        rows += [[f"Limit confirmed ({lid.replace('calc_', '').upper()})", f'=IF(Settings!{ref["confirmed"]}="Yes","OK","Not confirmed")', None] for lid, ref in self.limits.items()]
        ws = self.table_sheet("Check", "Release check", "Every line must read OK before this goes for review. Each line says where to go.", ["Check", "Result", "Where to go"], [40, 30, 44], rows)
        for i, s in enumerate(self.sections, start=6):
            ws.cell(i, 4, f'=IF(C{i}="OK","",HYPERLINK("#\'{s["screen"]}\'!A1","Go to {s["title"]}"))').font = F(10, False, self.st.dark)
        for k in range(6 + len(self.sections), 6 + len(rows)):
            ws.cell(k, 4, f'=IF(C{k}="OK","",HYPERLINK("#\'Settings\'!A1","Confirm it on Settings"))').font = F(10, False, self.st.dark)
        n = 5 + len(rows)
        ws.row_dimensions[n + 2].height = 24
        ws.cell(n + 2, 2, "Ready for review").font = F(11, True, self.st.dark)
        rd = ws.cell(n + 2, 3, f'=IF(COUNTIF(C6:C{n},"OK")={len(rows)},"Yes","No")'); rd.font = F(11, True); rd.alignment = Alignment(horizontal="center", vertical="center")
        for rr in list(range(6, n + 1)) + [n + 2]:
            ws.conditional_formatting.add(f"C{rr}", FormulaRule(formula=[f'OR(C{rr}="OK",C{rr}="Yes")'], fill=fill(OK_T), font=Font(name=FONT, color=OK, bold=True)))
            ws.conditional_formatting.add(f"C{rr}", FormulaRule(formula=[f'AND(C{rr}<>"OK",C{rr}<>"Yes",C{rr}<>"")'], fill=fill(WARN_T), font=Font(name=FONT, color=WARN, bold=True)))
        self.name("Ready", "Check", f"C{n + 2}")

    def record_sheet(self):
        heads = [h for h, _ in self.record] + ["_missing"]
        vals = [f for _, f in self.record] + ["=Missing"]
        ws = self.table_sheet("Record", "Record", "One row for the database. It builds itself from the screens. A new question in the framework becomes a new column.", heads, [16] * len(heads), [vals])
        ws.row_dimensions[5].height = 44

    def review_sheet(self):
        """What the reviewer and preparer settled: exceptions beside results, review points and answers, sign-offs.
        Only a case exported from the application has these; a blank tool has none."""
        rows = self.cfg.get("_review")
        if rows is None:
            return False
        rows = rows or [["", "", "Nothing recorded.", "", "", ""]]
        ws = self.table_sheet("Review", "Exceptions and review", "Recorded in the application. A result above its limit keeps its value; the exception explains it.",
                              ["Kind", "Item", "What was recorded", "By", "When", "Settled"], [14, 22, 70, 14, 18, 26], rows, heights=34)
        for i, row in enumerate(rows, start=6):      # tall enough for every line of what was recorded
            lines = sum(1 + len(part) // 80 for part in str(row[2]).split("\n"))
            ws.row_dimensions[i].height = max(34, 14 * lines + 8)
        return True

    def about(self):
        rows = [["Tool", self.tool["name"]], ["Pack", f'{self.cfg["pack"]["name"]} {self.cfg["pack"]["version"]}'], ["Organization", self.org["name"]],
                ["Generated from", self.cfg["_file"]],
                ["How to use", "Fill the light boxes. Amber means required and still empty. Use the buttons in the band to move between screens. Sections and questions that do not apply turn grey by themselves and keep what you typed. When Ready for review reads Yes, send it."],
                ["Protection", "Sheets are protected without a password so formulas are not typed over by accident. It is not security."],
                ["Note", "Synthetic example. Methods and limits are fictional demonstrations. Example wording, not any organization's policy."]]
        if self.cfg.get("_case"):
            rows.insert(0, ["Case", self.cfg["_case"]])
        for n in self.cfg.get("_notes") or []:
            rows.append(["Not shown", n + ". A workbook cell cannot carry this state; the data feed does."])
        self.table_sheet("About", "About this tool", "", ["", ""], [18, 110], rows, heights=32)

    def build(self, path):
        self.admin()
        self.layout()
        self.check_sheet()
        miss_terms = "+".join(s["missing"] for s in self.sections)
        work = self.screens["Workpaper"]
        self.wb.defined_names["Missing"] = DefinedName("Missing", attr_text=f"Check!$C${6 + len(self.sections) + len(self.limits) + 3}")
        chk = self.wb["Check"]
        mr = 6 + len(self.sections) + len(self.limits) + 3
        chk.row_dimensions[mr].height = 20
        chk.cell(mr, 2, "Still missing").font = F(10, False, self.st.dark)
        mc = chk.cell(mr, 3, "=" + miss_terms); mc.font = F(10, True); mc.alignment = Alignment(horizontal="center")
        for scr in self.screens.values():
            self.status_strip(scr)
        self.record_sheet()
        has_review = self.review_sheet()
        self.about()
        screens = list(self.screens)
        admin = ["Check", "Settings"] + (["Framework"] if "Framework" in self.wb.sheetnames else [])
        for n, scr in self.screens.items():
            buttons = [(x, x) for x in screens if x != n] + [(x, x) for x in admin]
            scr.band(f'{self.org["name"]}  ·  {self.cfg["pack"]["name"]} {self.cfg["pack"]["version"]}', buttons[:4])
            scr.finish(scr.r)
        order = screens + (["Review"] if has_review else []) + admin + ["Lists", "Record", "About"]
        self.wb._sheets = [self.wb[n] for n in order]
        for n in order:
            self.wb[n].sheet_properties.tabColor = self.st.dark if n in screens else (OK if n == "Check" else self.st.bar)
        self.wb.active = 0
        self.wb.save(path)


def build_workbook(pack: dict, data: dict, confirmations: dict, path, generated_from: str):
    """Write one workbook for one case: the pack's tool, filled with the case's entries, limits as the organization set them."""
    cfg = json.loads(json.dumps(pack))
    cfg.update(example=data, confirmations=confirmations, _fill=True, _file=generated_from)
    Book(cfg).build(path)
    return path


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.xlsx"):
        old.unlink()
    built = []
    for p in sorted(CONFIGS.glob("*.json")):
        cfg = json.loads(p.read_text()); cfg["_file"] = f"packs/{p.name}"
        from .access import DEFAULT, actions_of     # a demonstration has no installation: use the default people
        for name, action in {"@preparers": "enter", "@reviewers": "approve"}.items():
            cfg["org"]["lists"].setdefault(name, [x for x in DEFAULT["people"] if action in actions_of(DEFAULT, x)])
        for fill_ in (False, True):
            if fill_ and "example" not in cfg:
                continue
            cfg["_fill"] = fill_
            name = f'{cfg["tool"]["name"]} - {"example" if fill_ else "blank tool"}.xlsx'
            Book(cfg).build(OUT / name)
            built.append(name)
    print("built:", *built, sep="\n  ")


if __name__ == "__main__":
    sys.exit(main())
