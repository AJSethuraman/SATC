"""Turn a tool configuration into a working Excel workbook that looks like an application, not a spreadsheet.

    python3 workpaper-studio/excel/build_tool_workbook.py      # configs/*.json -> out/*.xlsx (blank tool + filled example)
    python3 workpaper-studio/excel/check_tool_workbooks.py     # LibreOffice recalculates; results are read by defined name

Design language (taken from the owner's own linesheet): a navy title band with buttons between screens, no gridlines and no
row or column headers, a grey canvas, side-by-side detail panels with labels right-aligned against tinted input boxes,
large navy section headings, each question in its own bordered box with a rating box and a large comment box, and the
supporting analysis on its own screen. Excel is only the engine. No macros: buttons are links, logic is formulas.

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
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
CONFIGS, OUT = HERE / "configs", HERE / "out"

FIRST, LAST = 2, 25            # usable grid columns B..Y, 24 narrow columns
GRID_W = 4.9
HELP_APPLIES, HELP_MISSING = 28, 29   # hidden helper columns AB, AC
FONT = "Arial"
UNLOCK = Protection(locked=False)
NUMF = {"money": '"$"#,##0;("$"#,##0);"$0"', "money2": '"$"#,##0.00;("$"#,##0.00);"$0.00"', "number": '#,##0;(#,##0);"0"', "pct": "0.0%", "date": "mm/dd/yyyy"}
ENTERED_ROWS, ENTERED_COLS = 6, 4


def F(size=9, bold=False, color="2B2F36", italic=False):
    return Font(name=FONT, size=size, bold=bold, color=color, italic=italic)


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


class Style:
    def __init__(self, brand):
        self.navy = brand
        self.band = fill(brand)
        self.button = fill("8FA6C9")
        self.canvas = fill("D9DDE2")
        self.panel = fill("ECEEF1")
        self.input = fill("F6E7E8")
        self.textbox = fill("FBFBFC")
        self.calc = fill("E3E7ED")
        self.na = fill("E2E4E7")
        self.thead = fill(brand)
        self.zebra = fill("F3F4F6")
        side = Side(style="thin", color="BCC2CA")
        self.box = Border(left=side, right=side, top=side, bottom=side)
        white = Side(style="medium", color="FFFFFF")
        self.btnbox = Border(left=white, right=white, top=white, bottom=white)
        self.rule = Border(bottom=Side(style="thin", color="AEB6C1"))


class Screen:
    """One worksheet styled as an application screen."""

    def __init__(self, book, title, name):
        self.book, self.st = book, book.st
        self.ws = book.wb.create_sheet(name)
        self.name, self.title = name, title
        self.r = 5
        self.styled = set()
        self.cur_inputs = []

    def put(self, r, c1, value=None, c2=None, h=None, font=None, align=None, fill_=None, border=None, fmt=None, unlock=False):
        ws = self.ws
        c2 = c2 or c1
        if c2 > c1 or (h and h > 1):
            ws.merge_cells(start_row=r, start_column=c1, end_row=r + (h or 1) - 1, end_column=c2)
        cell = ws.cell(r, c1, value)
        if font: cell.font = font
        if align: cell.alignment = align
        if fmt: cell.number_format = fmt
        if unlock: cell.protection = UNLOCK
        for rr in range(r, r + (h or 1)):
            for cc in range(c1, c2 + 1):
                x = ws.cell(rr, cc)
                if fill_: x.fill = fill_
                if border: x.border = border
                self.styled.add((rr, cc))
        return cell

    def label(self, r, c1, c2, text, size=8.5):
        return self.put(r, c1, text, c2, font=F(size, True, "3A4250"), align=Alignment(horizontal="right", vertical="center", wrap_text=True))

    def caps(self, r, c1, c2, text, color="4A5361"):
        return self.put(r, c1, text.upper(), c2, font=F(8, True, color), align=Alignment(horizontal="left", vertical="bottom"))

    def heading(self, r, text):
        return self.put(r, FIRST, text, 15, font=F(13, True, self.st.navy), align=Alignment(vertical="bottom"))

    def band(self, subtitle, buttons):
        ws, st = self.ws, self.st
        for c in range(1, LAST + 2):
            for r in (1, 2):
                ws.cell(r, c).fill = st.band
                self.styled.add((r, c))
        ws.row_dimensions[1].height = 34
        ws.row_dimensions[2].height = 15
        self.put(1, FIRST, self.title.upper(), 12, font=Font(name=FONT, size=18, bold=True, color="FFFFFF"), align=Alignment(vertical="center"))
        self.put(2, FIRST, subtitle, 14, font=Font(name=FONT, size=8.5, color="DCE3EE"), align=Alignment(vertical="top"))
        col = LAST - 3 * len(buttons) + 1
        for text, target in buttons:
            cell = self.put(1, col, text, col + 2, font=Font(name=FONT, size=8.5, bold=True, color="FFFFFF"),
                            align=Alignment(horizontal="center", vertical="center", wrap_text=True), fill_=st.button, border=st.btnbox)
            cell.hyperlink = f"#'{target}'!A1"
            col += 3

    def finish(self, last_row):
        ws, st = self.ws, self.st
        for r in range(1, last_row + 3):
            for c in range(1, LAST + 3):
                x = ws.cell(r, c)
                if x.fill is None or x.fill.fill_type is None:      # anything without its own fill sits on the panel
                    x.fill = st.panel if (FIRST <= c <= LAST and 3 <= r <= last_row + 1) else st.canvas
        ws.column_dimensions["A"].width = 2.5
        for c in range(FIRST, LAST + 1):
            ws.column_dimensions[L(c)].width = GRID_W
        ws.column_dimensions[L(LAST + 1)].width = 2.5
        for c in (HELP_APPLIES, HELP_MISSING):
            ws.column_dimensions[L(c)].hidden = True
        ws.sheet_view.showGridLines = False
        ws.sheet_view.showRowColHeaders = False
        ws.sheet_view.zoomScale = 110
        ws.freeze_panes = "A3"
        ws.page_setup.orientation = "portrait"
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_area = f"A1:{L(LAST + 1)}{last_row + 1}"
        ws.protection.sheet = True
        ws.protection.formatColumns = ws.protection.formatRows = ws.protection.formatCells = False


class Book:
    def __init__(self, cfg):
        self.cfg, self.tool, self.org = cfg, cfg["tool"], cfg["org"]
        self.st = Style(cfg.get("brand", "2B3A55"))
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.example = cfg.get("example", {}) if cfg.get("_fill") else {}
        self.addr, self.grid = {}, {}
        self.sections, self.record = [], []
        self.screens, self.limits, self.framework_rows = {}, {}, {}

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

    def input(self, scr, r, c1, c2, f, value, h=None):
        big = f.get("type") == "longtext"
        if f.get("type") == "date" and isinstance(value, str):
            value = datetime.date.fromisoformat(value)
        fmt = None
        if f.get("type") == "date":
            fmt = NUMF["date"]
        elif f.get("type") == "number":
            fmt = NUMF["money2" if f.get("cents") else "money"] if f.get("money") else NUMF["number"]
        cell = scr.put(r, c1, value, c2, h=h, fill_=self.st.textbox if big else self.st.input, border=self.st.box, fmt=fmt, unlock=True,
                       font=F(9), align=Alignment(vertical="top" if big else "center", wrap_text=big, horizontal="right" if f.get("type") == "number" else "left", indent=0 if big else 1))
        scr.cur_inputs.append(cell.coordinate)
        self.validate(scr, cell, f)
        return cell

    def calc(self, scr, r, c1, c2, formula, fmt=None, size=9, bold=False):
        return scr.put(r, c1, formula, c2, fill_=self.st.calc, border=self.st.box, fmt=fmt, font=F(size, bold),
                       align=Alignment(horizontal="right", vertical="center", indent=1))

    def applies(self, rule):
        if not rule:
            return '"Yes"'
        a = self.addr[rule["field"]]
        cond = "OR(" + ",".join(f'{a}="{v}"' for v in rule["values"]) + ")"
        return f'IF({a}="","Waiting",IF({cond},"Yes","No"))'

    def screen_for(self, s):
        nm = s.get("screen", "Workpaper")
        if nm not in self.screens:
            title = self.tool["name"] if nm == "Workpaper" else f'{self.tool["name"]}: {nm}'
            self.screens[nm] = Screen(self, title, nm)
        return self.screens[nm]

    def section_head(self, scr, s, compact=None):
        r = scr.r
        if compact:
            c1, c2 = compact
            scr.caps(r, c1, c2 - 3, s["title"])
            status = scr.put(r, c2 - 2, None, c2, font=F(7.5, True, "6B7685"), align=Alignment(horizontal="right", vertical="bottom"))
        else:
            scr.ws.row_dimensions[r].height = 24
            scr.heading(r, s["title"])
            scr.put(r, 16, {"required": "", "optional": "Optional", "conditional": "Only when it applies"}[s["mode"]], 19,
                    font=F(8, False, "6B7685", True), align=Alignment(horizontal="right", vertical="bottom"))
            status = scr.put(r, 20, None, LAST, font=F(9, True), align=Alignment(horizontal="right", vertical="bottom"))
            for c in range(FIRST, LAST + 1):
                scr.ws.cell(r, c).border = self.st.rule
        rule = s.get("rule") if s["mode"] == "conditional" else None
        scr.ws.cell(r, HELP_APPLIES, "=" + self.applies(rule) if rule else "Yes")
        return r, status, f"${L(HELP_APPLIES)}${r}"

    def section_close(self, scr, s, head_row, status, applies_ref, terms, start, end, compact=None):
        ws = scr.ws
        miss = "+".join(terms) if terms else "0"
        optional = s["mode"] == "optional"
        started = "+".join(f'({a}<>"")' for a in scr.cur_inputs) or "0"
        m = ws.cell(head_row, HELP_MISSING)
        m.value = (f'=IF({applies_ref}="No",0,IF(({started})=0,0,{miss}))' if optional
                   else f'=IF({applies_ref}="No",0,IF({applies_ref}="Waiting",1,{miss}))')
        opt = f'IF(({started})=0,"Optional",' if optional else "("
        status.value = (f'=IF({applies_ref}="No","Not applicable",IF({applies_ref}="Waiting","Waiting on an answer",'
                        f'{opt}IF(({miss})=0,"Complete",({miss})&" missing"))))')
        sc = status.coordinate
        ws.conditional_formatting.add(sc, FormulaRule(formula=[f'{sc}="Complete"'], font=Font(name=FONT, color="127A4C", bold=True)))
        ws.conditional_formatting.add(sc, FormulaRule(formula=[f'ISNUMBER(SEARCH("missing",{sc}))'], font=Font(name=FONT, color="9A5B00", bold=True)))
        if s["mode"] == "conditional" and end >= start:
            c1, c2 = compact or (FIRST, LAST)
            ws.conditional_formatting.add(f"{L(c1)}{start}:{L(c2)}{end}", FormulaRule(formula=[f'{applies_ref}="No"'], fill=self.st.na, font=Font(name=FONT, color="9AA3AE")))
        self.sections.append({"id": s["id"], "title": s["title"], "status": q(scr.name, sc), "missing": q(scr.name, f"{L(HELP_MISSING)}{head_row}"), "screen": scr.name})
        self.name(f"Status_{sname(s['id'])}", scr.name, sc)

    def fields_panel(self, scr, fields, c1, c2, r0):
        terms, r = [], r0
        lw = max(3, (c2 - c1 + 1) * 3 // 8)
        for f in fields:
            val = self.example.get(f["id"])
            if f.get("type") == "longtext":
                scr.caps(r, c1, c2, f["label"] + ("" if f.get("req") else " (optional)"))
                r += 1
                cell = self.input(scr, r, c1, c2, f, val, h=4)
                for rr in range(r, r + 4):
                    scr.ws.row_dimensions[rr].height = 18
                r += 4
            else:
                scr.ws.row_dimensions[r].height = 21
                scr.label(r, c1, c1 + lw - 1, f["label"] + ("" if f.get("req") else " (optional)"))
                cell = self.input(scr, r, c1 + lw, c2, f, val)
                r += 1
            ref = q(scr.name, cell.coordinate)
            self.addr[f["id"]] = ref
            self.name(f"Field_{sname(f['id'])}", scr.name, cell.coordinate)
            if f.get("req"):
                terms.append(f'({cell.coordinate}="")*1')
            self.record.append((f["label"], f'=IF({ref}="","",{ref})'))
        return terms, r

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
                if last_group is not None:
                    scr.r += 1
                ws.row_dimensions[scr.r].height = 24
                scr.heading(scr.r, qd["group"]); scr.r += 1
                last_group = qd["group"]
            r = scr.r
            ws.row_dimensions[r].height = 21; ws.row_dimensions[r + 1].height = 21
            scr.put(r, FIRST, str(qd["key"]), FIRST, font=F(8.5, True, "3A4250"), align=Alignment(vertical="top"))
            box = scr.put(r, FIRST + 1, f"=Framework!C{self.framework_rows[qd['key']]}", FIRST + 9, h=2, fill_=st.textbox, border=st.box,
                          font=F(8.5), align=Alignment(wrap_text=True, vertical="center", indent=1))
            if qd.get("info"):
                box.comment = Comment("How to test this:\n" + qd["info"], "Framework", width=330, height=150)
            v = ex.get(str(qd["key"]), {})
            scr.label(r, FIRST + 10, FIRST + 12, rating["label"])
            rc = self.input(scr, r, FIRST + 13, FIRST + 15, rating, v.get(rating["key"]))
            note = scr.put(r + 1, FIRST + 10, None, FIRST + 15, font=F(7.5, False, "9A5B00", True), align=Alignment(horizontal="right", vertical="top"))
            cm = self.input(scr, r, FIRST + 16, LAST, comment, v.get(comment["key"]), h=2) if comment else None
            if cm:
                cm.alignment = Alignment(wrap_text=True, vertical="top")
                for cc in range(FIRST + 16, LAST + 1):
                    for rr in (r, r + 1):
                        ws.cell(rr, cc).fill = st.textbox
            ws.cell(r, HELP_APPLIES, "=" + self.applies(qd.get("when")))
            apc = f"${L(HELP_APPLIES)}{r}"
            rcc, cmc = rc.coordinate, (cm.coordinate if cm else None)
            rw = comment.get("reqWhen") if comment else None
            need = (f'AND(OR({",".join(f"{rcc}=" + chr(34) + x + chr(34) for x in rw["values"])}),{cmc}="")') if rw else "FALSE"
            note.value = f'=IF({apc}="No","Not applicable",IF({apc}="Waiting","Waiting on an answer",IF({rcc}="","Rate this",IF({need},"Comment needed",""))))'
            terms += [f'({apc}="Yes")*(({rcc}="")+({need}))', f'({apc}="Waiting")*1']
            ws.conditional_formatting.add(f"{L(FIRST)}{r}:{L(LAST)}{r + 1}", FormulaRule(formula=[f'{apc}="No"'], fill=st.na, font=Font(name=FONT, color="9AA3AE")))
            for val_, col in (("Not effective", "B4372C"), ("Partially effective", "9A5B00"), ("Effective", "127A4C")):
                ws.conditional_formatting.add(rcc, FormulaRule(formula=[f'{rcc}="{val_}"'], font=Font(name=FONT, color=col, bold=True)))
            self.record.append((f'{rating["label"]}_{qd["key"]}', f'=IF({q(scr.name, f"{L(HELP_APPLIES)}{r}")}="No","Not applicable",{q(scr.name, rcc)})'))
            if cm:
                self.record.append((f'{comment["label"]}_{qd["key"]}', f'=IF({q(scr.name, cmc)}="","",{q(scr.name, cmc)})'))
            ws.row_dimensions[r + 2].height = 7
            scr.r += 3
        return terms

    def table(self, scr, g, R, C, ex, rows_from, cols_from, by):
        ws, st, terms = scr.ws, self.st, []
        scr.caps(scr.r, FIRST, LAST, g["label"]); scr.r += 1
        lab_w = 4 if rows_from == "entered" else 8
        data_c1 = FIRST + lab_w
        span = max(3, (LAST - data_c1 + 1) // max(1, len(C)))
        cols = [(data_c1 + j * span, data_c1 + (j + 1) * span - 1) for j in range(len(C))]
        hdr = scr.r
        ws.row_dimensions[hdr].height = 24
        cols_ex = list(ex.get("_cols") or [])
        for j, (c, (a, b)) in enumerate(zip(C, cols)):
            if cols_from == "entered":
                h = self.input(scr, hdr, a, b, {"type": "text"}, cols_ex[j] if j < len(cols_ex) else c["label"])
                h.font = F(8.5, True); h.alignment = Alignment(horizontal="center", vertical="center")
                scr.cur_inputs.remove(h.coordinate)
            else:
                scr.put(hdr, a, c["label"].upper(), b, font=F(7.5, True, "4A5361"), align=Alignment(horizontal="center", vertical="bottom", wrap_text=True))
        scr.r += 1
        first = scr.r
        for i, row in enumerate(R):
            r = scr.r
            ws.row_dimensions[r].height = 20
            scr.label(r, FIRST, FIRST + lab_w - 1, row["label"]).font = F(8.5, True, "3A4250", italic=bool(row.get("compute")))
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
                        A_, B_ = f"{L(a)}{first + kr.index(cc['a'])}", f"{L(a)}{first + kr.index(cc['b'])}"
                    expr = {"mul": f"{A_}*{B_}", "pctof": f"{A_}*{B_}/100", "add": f"{A_}+{B_}", "sub": f"{A_}-{B_}", "div": f'IF({B_}=0,"",{A_}/{B_})'}[cc["op"]]
                    self.calc(scr, r, a, b, f'=IF(OR({A_}="",{B_}=""),"",{expr})', (NUMF["money2"] if d.get("cents") else NUMF["money"]) if d.get("money") else NUMF["number"])
                else:
                    val = exrow.get(f"c{j}") if cols_from == "entered" else exrow.get(c["key"])
                    self.input(scr, r, a, b, d, val)
            scr.r += 1
        last = scr.r - 1
        self.grid[g["id"]] = {"cols": {c["key"]: qr(scr.name, f"{L(a)}{first}", f"{L(a)}{last}") for c, (a, b) in zip(C, cols)}}
        if rows_from == "entered":
            inputs = [L(a) for c, (a, b) in zip(C, cols) if not c.get("compute")]
            used = "((" + "+".join(f'({x}{first}:{x}{last}<>"")' for x in inputs) + ")>0)"
            req = [L(a) for c, (a, b) in zip(C, cols) if c.get("req") and not c.get("compute")]
            if req:
                terms.append(f'SUMPRODUCT({used}*((' + "+".join(f'({x}{first}:{x}{last}="")' for x in req) + ')>0))')
            mn = g["rows"].get("min", 0)
            if mn:
                terms.append(f'(SUMPRODUCT({used}*1)<{mn})*1')
            self.record.append((f'{g["label"]} (rows used)', "=SUMPRODUCT(((" + "+".join(f'({qr(scr.name, f"{x}{first}", f"{x}{last}")}<>"")' for x in inputs) + ")>0)*1)"))
        else:
            for i, row in enumerate(R):
                r = first + i
                for c, (a, b) in zip(C, cols):
                    d = row if by == "row" else c
                    if d.get("req") and not d.get("compute"):
                        x = L(a)
                        terms.append(f'(SUMPRODUCT(({x}{first}:{x}{last}<>"")*1)>0)*({x}{r}="")' if cols_from == "entered" else f'({x}{r}="")*1')
        if g.get("totals"):
            r = scr.r
            ws.row_dimensions[r].height = 20
            scr.label(r, FIRST, FIRST + lab_w - 1, "Total").font = F(8.5, True, st.navy)
            for c, (a, b) in zip(C, cols):
                if by == "col" and (c.get("type") == "number" or c.get("compute")) and not c.get("noTotal"):
                    self.calc(scr, r, a, b, f"=SUM({L(a)}{first}:{L(a)}{last})", (NUMF["money2"] if c.get("cents") else NUMF["money"]) if c.get("money") else NUMF["number"], bold=True)
            scr.r += 1
        scr.r += 1
        return terms

    def calc_block(self, scr, b):
        ws, st, m = scr.ws, self.st, b["method"]
        lim = self.limits[b["id"]]
        nm = {"dti": "Debt-to-income", "ltv": "Loan-to-value", "recon": "Reconciliation", "devrate": "Deviation rate"}[m]
        ws.row_dimensions[scr.r].height = 22
        scr.put(scr.r, FIRST, nm.upper(), FIRST + 9, font=F(10, True, st.navy), align=Alignment(vertical="bottom"))
        scr.put(scr.r, FIRST + 10, b.get("code", ""), FIRST + 15, font=F(7.5, False, "6B7685", True), align=Alignment(horizontal="right", vertical="bottom"))
        scr.r += 1
        if m == "dti":
            g = self.grid["income"]["cols"]; a, per, src = g["amount"], g["per"], g["source"]
            d, pr = self.grid["debts"]["cols"]["payment"], self.addr["proposed"]
            used = f'(({src}<>"")+({a}<>"")+({per}<>"")>0)'
            rows = [("Monthly income", f'=SUMPRODUCT(({per}="Annual")*({a})/12+({per}="Monthly")*({a}))', NUMF["money"]),
                    ("Existing monthly debt payments", f"=SUM({d})", NUMF["money"]),
                    ("Proposed monthly payment", f"=N({pr})", NUMF["money"]),
                    ("Inputs still missing", f'=SUMPRODUCT({used}*((({a}="")+({per}=""))>0))+({pr}="")+(SUMPRODUCT({used}*1)=0)', "0")]
        elif m == "devrate":
            g = self.grid[b["grid"]]["cols"]
            cr = [g[k] for k in b["attributes"]]
            any_ex, tested = "+".join(f'({c}="Exception")' for c in cr), "+".join(f'({c}<>"")' for c in cr)
            rows = [("Items tested", f"=SUMPRODUCT((({tested})>0)*1)", "0"),
                    ("Items with an exception", f"=SUMPRODUCT((({any_ex})>0)*1)", "0"),
                    ("Inputs still missing", f"=SUMPRODUCT(((({tested})>0)*(({tested})<{len(cr)}))*1)", "0")]
        else:
            g = self.grid["items"]["cols"]; t, a = g["type"], g["amount"]
            sb, gl = self.addr["stmt"], self.addr["gl"]
            rows = [("Adjusted bank", f'=N({sb})+SUMIF({t},"Deposit in transit",{a})-SUMIF({t},"Outstanding check",{a})', NUMF["money2"]),
                    ("Adjusted books", f'=N({gl})-SUMIF({t},"Bank fee not yet booked",{a})+SUMIF({t},"Interest not yet booked",{a})', NUMF["money2"]),
                    ("Inputs still missing", f'=({sb}="")+({gl}="")+SUMPRODUCT((({t}<>"")+({a}<>"")=1)*1)', "0")]
        refs = {}
        for lab, f, fmt in rows:
            r = scr.r
            ws.row_dimensions[r].height = 19
            scr.label(r, FIRST, FIRST + 7, lab)
            self.calc(scr, r, FIRST + 8, FIRST + 11, f, fmt)
            refs[lab] = f"{L(FIRST + 8)}{r}"
            scr.r += 1
        r = scr.r
        ws.row_dimensions[r].height = 28
        scr.label(r, FIRST, FIRST + 7, {"dti": "Debt-to-income", "devrate": "Deviation rate", "recon": "Difference"}[m], size=10)
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
        res = self.calc(scr, r, FIRST + 8, FIRST + 11, f, fmt, size=13, bold=True)
        rc = res.coordinate
        cmp = f"ABS({rc})<=Settings!{lim['policy']}+0.005" if m == "recon" else f"{rc}<=Settings!{lim['policy']}"
        verdict = scr.put(r, FIRST + 12, f'=IF(Settings!{lim["confirmed"]}<>"Yes","Not tested: limit not confirmed",IF(ISNUMBER({rc}),IF({cmp},"Within limit","Above limit"),"Not tested"))',
                          FIRST + 19, font=F(9, True), align=Alignment(horizontal="left", vertical="center", indent=1))
        vc = verdict.coordinate
        for t_, col in (("Above limit", "B4372C"), ("Within limit", "127A4C")):
            ws.conditional_formatting.add(vc, FormulaRule(formula=[f'{vc}="{t_}"'], font=Font(name=FONT, color=col, bold=True)))
        ws.conditional_formatting.add(vc, FormulaRule(formula=[f'LEFT({vc},10)="Not tested"'], font=Font(name=FONT, color="9A5B00", bold=True)))
        scr.put(r + 1, FIRST + 12, "Limit is on Settings, confirmed by the organization. It is not part of the method.", FIRST + 23, font=F(7.5, False, "6B7685", True))
        self.name(f"Result_{sname(b['id'])}", scr.name, rc)
        self.name(f"Verdict_{sname(b['id'])}", scr.name, vc)
        for lab, ref in refs.items():
            self.name(f"Calc_{sname(b['id'])}_{sname(lab)}", scr.name, ref)
        self.record.append((nm, f"={q(scr.name, rc)}"))
        self.record.append((nm + " against limit", f"={q(scr.name, vc)}"))
        scr.r += 3

    def compact(self, s):
        return all(b["kind"] == "field" and b.get("type") != "longtext" for b in s["blocks"]) and len(s["blocks"]) <= 4

    def layout(self):
        secs, i = self.tool["sections"], 0
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
                width = (LAST - FIRST + 1) // 3
                r0, bottoms = scr.r, []
                for k, bs in enumerate(band):
                    c1 = FIRST + k * width; c2 = c1 + width - 2
                    scr.r, scr.cur_inputs = r0, []
                    head, status, ap = self.section_head(scr, bs, compact=(c1, c2))
                    terms, end = self.fields_panel(scr, bs["blocks"], c1, c2, head + 1)
                    self.section_close(scr, bs, head, status, ap, terms, head + 1, end - 1, compact=(c1, c2))
                    bottoms.append(end)
                scr.r = max(bottoms) + 1
                i += len(band)
                continue
            scr.cur_inputs = []
            head, status, ap = self.section_head(scr, s)
            scr.r += 1
            start, terms, run = scr.r, [], []
            for b in s["blocks"] + [None]:
                if b is not None and b["kind"] == "field" and b.get("type") != "longtext":
                    run.append(b); continue
                if run:
                    t, end = self.fields_panel(scr, run, FIRST, FIRST + 11, scr.r)
                    terms += t; scr.r = end + 1; run = []
                if b is None:
                    break
                if b["kind"] == "field":
                    t, end = self.fields_panel(scr, [b], FIRST, LAST, scr.r)
                    terms += t; scr.r = end + 1
                elif b["kind"] == "grid":
                    terms += self.grid_block(scr, b)
                elif b["kind"] == "calc":
                    self.calc_block(scr, b)
            self.section_close(scr, s, head, status, ap, terms, start, scr.r - 1)
            scr.r += 1
            i += 1

    def status_strip(self):
        scr = self.screens["Workpaper"]
        st, r = self.st, 3
        scr.ws.row_dimensions[r].height = 24
        scr.label(r, FIRST + 7, FIRST + 11, "READY FOR REVIEW", size=7.5)
        ready = scr.put(r, FIRST + 12, None, FIRST + 14, fill_=st.textbox, border=st.box, font=F(10, True), align=Alignment(horizontal="center", vertical="center"))
        scr.label(r, FIRST + 15, FIRST + 17, "STILL MISSING", size=7.5)
        miss = scr.put(r, FIRST + 18, "=" + "+".join(s["missing"] for s in self.sections), FIRST + 19, fill_=st.textbox, border=st.box, font=F(10, True), align=Alignment(horizontal="center", vertical="center"))
        scr.label(r, FIRST + 20, FIRST + 21, "SECTIONS", size=7.5)
        done = "+".join(f'OR({s["status"]}="Complete",{s["status"]}="Not applicable",{s["status"]}="Optional")*1' for s in self.sections)
        scr.put(r, FIRST + 22, f'=({done})&" of {len(self.sections)}"', LAST, fill_=st.textbox, border=st.box, font=F(9, True), align=Alignment(horizontal="center", vertical="center"))
        self.ready_cell = ready
        self.name("Ready", "Workpaper", ready.coordinate)
        self.name("Missing", "Workpaper", miss.coordinate)
        for v, bg, col in (("Yes", "DFF2E7", "127A4C"), ("No", "FBEFD6", "9A5B00")):
            scr.ws.conditional_formatting.add(ready.coordinate, FormulaRule(formula=[f'{ready.coordinate}="{v}"'], fill=fill(bg), font=Font(name=FONT, color=col, bold=True)))

    def table_sheet(self, name, title, intro, heads, widths, rows, unlock_cols=(), fmts=None):
        ws, st = self.wb.create_sheet(name), self.st
        n = max(2, len(heads))
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
        c = ws.cell(1, 1, title.upper()); c.font = Font(name=FONT, size=16, bold=True, color="FFFFFF"); c.alignment = Alignment(vertical="center", indent=1)
        for j in range(1, n + 1):
            ws.cell(1, j).fill = st.band
        ws.row_dimensions[1].height = 34
        if intro:
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n)
            ws.cell(2, 1, intro).font = F(8.5, False, "4A5361", True)
        ws.row_dimensions[2].height = 22
        if any(heads):
            for j, h in enumerate(heads, start=1):
                c = ws.cell(4, j, h); c.font = Font(name=FONT, size=9, bold=True, color="FFFFFF"); c.fill = st.thead
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c.border = st.box
            ws.row_dimensions[4].height = 30
        for i, row in enumerate(rows, start=5):
            for j, v in enumerate(row, start=1):
                c = ws.cell(i, j, v); c.font = F(9, bold=(j == 1 and not any(heads)))
                c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center" if j in (1, 2) and len(heads) > 3 else "left")
                c.border = st.box
                c.fill = st.input if j in unlock_cols else (st.zebra if i % 2 else fill("FFFFFF"))
                if j in unlock_cols:
                    c.protection = UNLOCK
                if fmts and j in fmts:
                    c.number_format = fmts[j]
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[L(j)].width = w
        ws.sheet_view.showGridLines = False
        ws.freeze_panes = "A5"
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
                        self.framework_rows[qd["key"]] = 5 + len(rows)
                        rows.append([qd.get("group", ""), qd["key"], qd["label"], qd.get("info", "")])
        if rows:
            ws = self.table_sheet("Framework", f'{self.tool["name"]} framework', "The questions and how to test each. The workpaper reads its wording from here.",
                                  ["Section", "#", "Question", "How to test"], [20, 8, 52, 78], rows, unlock_cols=(3, 4))
            for i in range(len(rows)):
                ws.row_dimensions[5 + i].height = 48
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
                    self.limits[b["id"]] = {"policy": f"$D${4 + len(lrows)}", "confirmed": f"$E${4 + len(lrows)}"}
        ws = self.table_sheet("Settings", "Settings", "Limits belong to this organization, not to the method. Until a limit is confirmed here, nothing is tested against it.",
                              ["Limit", "Method", "Author recommends", "Our policy", "Confirmed?", "Confirmed by", "Date"], [36, 16, 18, 14, 12, 18, 13], lrows,
                              unlock_cols=(4, 5, 6, 7), fmts={3: "0.0%" if pct else NUMF["money2"], 4: "0.0%" if pct else NUMF["money2"], 7: NUMF["date"]})
        dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True); ws.add_data_validation(dv)
        for i in range(len(lrows)):
            dv.add(f"E{5 + i}")
        lists = self.org["lists"]
        ws = self.wb.create_sheet("Lists")
        n = max(2, len(lists))
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
        c = ws.cell(1, 1, "LISTS"); c.font = Font(name=FONT, size=16, bold=True, color="FFFFFF"); c.alignment = Alignment(vertical="center", indent=1)
        for j in range(1, n + 1):
            ws.cell(1, j).fill = st.band
        ws.row_dimensions[1].height = 34
        ws.cell(2, 1, "Every dropdown reads from these lists. Add values at the end of a list.").font = F(8.5, False, "4A5361", True)
        for j, (nm, vals) in enumerate(lists.items(), start=1):
            h = ws.cell(4, j, nm); h.font = Font(name=FONT, size=9, bold=True, color="FFFFFF"); h.fill = st.thead; h.alignment = Alignment(horizontal="center", wrap_text=True)
            for i in range(5, 15 + len(vals)):
                x = ws.cell(i, j, vals[i - 5] if i - 5 < len(vals) else None); x.font = F(9); x.border = st.box; x.protection = UNLOCK
            ws.column_dimensions[L(j)].width = max(18, len(nm) + 4)
            self.wb.defined_names[f"List_{sname(nm)}"] = DefinedName(f"List_{sname(nm)}", attr_text=f"Lists!${L(j)}$5:${L(j)}${4 + len(vals) + 10}")
        ws.sheet_view.showGridLines = False
        ws.protection.sheet = True

    def check_sheet(self):
        rows = [[s["title"], f'=IF(OR({s["status"]}="Complete",{s["status"]}="Not applicable",{s["status"]}="Optional"),"OK",{s["status"]})', None] for s in self.sections]
        rows += [[f"Limit confirmed ({lid.replace('calc_', '').upper()})", f'=IF(Settings!{ref["confirmed"]}="Yes","OK","Not confirmed")', None] for lid, ref in self.limits.items()]
        ws = self.table_sheet("Check", "Release check", "Every line must read OK before this goes for review. Each line says where to go.", ["Check", "Result", "Where to go"], [40, 30, 44], rows)
        for i, s in enumerate(self.sections, start=5):
            c = ws.cell(i, 3, f'=IF(B{i}="OK","","Go to {s["title"]}")'); c.hyperlink = f"#'{s['screen']}'!A1"; c.font = Font(name=FONT, size=9, color="1F4E99", underline="single")
        for k in range(5 + len(self.sections), 5 + len(rows)):
            c = ws.cell(k, 3, f'=IF(B{k}="OK","","Confirm it on Settings")'); c.hyperlink = "#'Settings'!A1"; c.font = Font(name=FONT, size=9, color="1F4E99", underline="single")
        n = 4 + len(rows)
        ws.cell(n + 2, 1, "Ready for review").font = Font(name=FONT, size=12, bold=True)
        ws.cell(n + 2, 2, f'=IF(COUNTIF(B5:B{n},"OK")={len(rows)},"Yes","No")').font = Font(name=FONT, size=12, bold=True)
        for rr in range(5, n + 3):
            ws.conditional_formatting.add(f"B{rr}", FormulaRule(formula=[f'OR(B{rr}="OK",B{rr}="Yes")'], font=Font(name=FONT, color="127A4C", bold=True)))
            ws.conditional_formatting.add(f"B{rr}", FormulaRule(formula=[f'AND(B{rr}<>"OK",B{rr}<>"Yes",B{rr}<>"")'], font=Font(name=FONT, color="B4372C", bold=True)))
        self.ready_cell.value = f"=Check!B{n + 2}"

    def record_sheet(self):
        heads = [h for h, _ in self.record] + ["_missing"]
        vals = [f for _, f in self.record] + ["=Missing"]
        ws = self.table_sheet("Record", "Record", "One row for the database. It builds itself from the screens. A new question in the framework becomes a new column.", heads, [16] * len(heads), [vals])
        ws.row_dimensions[4].height = 44

    def about(self):
        rows = [["Tool", self.tool["name"]], ["Pack", f'{self.cfg["pack"]["name"]} {self.cfg["pack"]["version"]}'], ["Organization", self.org["name"]],
                ["Generated from", f'configs/{self.cfg["_file"]}'],
                ["How to use", "Fill the tinted boxes. Use the buttons in the blue band to move between screens. Sections and questions that do not apply grey out by themselves and keep what you typed. When the band says Ready for review: Yes, send it."],
                ["Protection", "Sheets are protected without a password so formulas are not typed over by accident. It is not security."],
                ["Note", "Synthetic example. Methods and limits are fictional demonstrations. Example wording, not any organization's policy."]]
        self.table_sheet("About", "About this tool", "", ["", ""], [18, 110], rows)

    def build(self, path):
        self.admin()
        self.layout()
        self.status_strip()
        self.check_sheet()
        self.record_sheet()
        self.about()
        screens = list(self.screens)
        admin = ["Check", "Settings"] + (["Framework"] if "Framework" in self.wb.sheetnames else [])
        for n, scr in self.screens.items():
            buttons = [(x, x) for x in screens if x != n] + [(x, x) for x in admin]
            scr.band(f'{self.org["name"]}  ·  {self.cfg["pack"]["name"]} {self.cfg["pack"]["version"]}', buttons[:4])
            scr.finish(scr.r)
        order = screens + admin + ["Lists", "Record", "About"]
        self.wb._sheets = [self.wb[n] for n in order]
        tabs = {"Check": "127A4C", "Settings": "3A4250", "Framework": "3A4250", "Lists": "3A4250", "Record": "8A94A3", "About": "8A94A3"}
        for n in order:
            self.wb[n].sheet_properties.tabColor = tabs.get(n, self.st.navy)
        self.wb.active = 0
        self.wb.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.xlsx"):
        old.unlink()
    built = []
    for p in sorted(CONFIGS.glob("*.json")):
        cfg = json.loads(p.read_text()); cfg["_file"] = p.name
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
