"""Turn a tool configuration into a working Excel workbook.

    python3 workpaper-studio/excel/build_tool_workbook.py            # builds every config in configs/
    python3 workpaper-studio/excel/check_tool_workbooks.py           # LibreOffice recalculates; values are checked

The configuration is the same shape the builder shows under "As data": sections of fields,
tables (the one table primitive: rows and columns each fixed, entered or from a list) and
calculations from the library. Nothing about a particular tool is written in this file.
An optional "example" block fills a copy with synthetic entries so the workbook can be seen working.

No macros: everything is formulas, dropdowns, conditional formatting and sheet protection, so the
file opens anywhere and nothing runs that a reviewer cannot read.
"""
from __future__ import annotations

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
CONFIGS = HERE / "configs"
OUT = HERE / "out"

# ---------------------------------------------------------------- house style (overridable per organization)
def palette(brand):
    return {
        "brand": PatternFill("solid", fgColor=brand),
        "sect": PatternFill("solid", fgColor="E9EDF2"),
        "input": PatternFill("solid", fgColor="FFF8E6"),
        "calc": PatternFill("solid", fgColor="EEF2F7"),
        "na": PatternFill("solid", fgColor="EDEDED"),
        "head": PatternFill("solid", fgColor="F4F6F8"),
    }

WHITE = Font(color="FFFFFF", bold=True, size=16)
WHITE_S = Font(color="FFFFFF", size=10)
BOLD = Font(bold=True)
MUTED = Font(color="6B7685", size=9)
HAIR = Side(style="thin", color="D5DBE3")
BOX = Border(left=HAIR, right=HAIR, top=HAIR, bottom=HAIR)
UNDER = Border(bottom=Side(style="thin", color="AEB8C5"))
WRAP = Alignment(wrap_text=True, vertical="top")
MID = Alignment(vertical="center")
UNLOCK = Protection(locked=False)
FMT = {"number": '#,##0;(#,##0);"0"', "money": '"$"#,##0.00;("$"#,##0.00);"$0.00"', "pct": "0.0%", "date": "yyyy-mm-dd"}

COL_NO, COL_LABEL, COL_A = 2, 3, 4          # B number, C label/question, D.. inputs
WIDTHS = {1: 2, 2: 7, 3: 46, 4: 17, 5: 17, 6: 17, 7: 17, 8: 17, 9: 30, 10: 9}
ENTERED_ROWS = 8                             # blank rows offered for "entered" tables
ENTERED_COLS = 4                             # blank columns offered when the person filling it in adds columns


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


class Builder:
    cur_inputs = []

    def __init__(self, cfg):
        self.cfg = cfg
        self.tool = cfg["tool"]
        self.org = cfg["org"]
        self.P = palette(cfg.get("brand", "1F4E79"))
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "Workpaper"
        self.addr = {}          # field id -> absolute address on Workpaper
        self.grid = {}          # grid id -> geometry for calculations
        self.section_status = []  # (title, status cell)
        self.record = []        # (header, formula) for the Record sheet
        self.missing_total = []
        self.r = 1
        self.example = cfg.get("example", {}) if cfg.get("_fill") else {}

    # ---------------------------------------------------------- helpers
    def cell(self, row, col, value=None, **kw):
        c = self.ws.cell(row=row, column=col, value=value)
        for k, v in kw.items():
            setattr(c, k, v)
        return c

    def input_cell(self, row, col, f, value=None):
        c = self.cell(row, col, value)
        c.fill = self.P["input"]; c.border = BOX; c.protection = UNLOCK; c.alignment = MID
        self.cur_inputs.append(c.coordinate)
        t = f.get("type")
        if t in ("number",):
            c.number_format = FMT["money"] if f.get("money") else FMT["number"]
        if t == "date":
            c.number_format = FMT["date"]
        if t == "longtext":
            c.alignment = WRAP
        if t in ("list", "choice"):
            src = f"=List_{safe_name(f['list'])}" if t == "list" else '"' + ",".join(f["opts"]) + '"'
            dv = DataValidation(type="list", formula1=src, allow_blank=True, showErrorMessage=True,
                                errorTitle="Pick from the list", error="Choose one of the listed answers.")
            self.ws.add_data_validation(dv); dv.add(c.coordinate)
        if t == "number":
            dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True,
                                showErrorMessage=True, errorTitle="A number", error="Enter a number, 0 or more. Leave it blank if you do not know it yet.")
            self.ws.add_data_validation(dv); dv.add(c.coordinate)
        if t == "date":
            dv = DataValidation(type="date", operator="greaterThan", formula1="1", allow_blank=True, showErrorMessage=True,
                                errorTitle="A date", error="Enter a date.")
            self.ws.add_data_validation(dv); dv.add(c.coordinate)
        return c

    def calc_cell(self, row, col, formula, fmt=None):
        c = self.cell(row, col, formula)
        c.fill = self.P["calc"]; c.border = BOX
        if fmt:
            c.number_format = fmt
        return c

    def cond_expr(self, rule):
        """Excel expression that is TRUE when a rule holds. Blank answer -> handled by caller."""
        a = self.addr[rule["field"]]
        return "OR(" + ",".join(f'{a}="{v}"' for v in rule["values"]) + ")"

    def applies_formula(self, rule):
        if not rule:
            return '"Yes"'
        a = self.addr[rule["field"]]
        return f'IF({a}="","Waiting",IF({self.cond_expr(rule)},"Yes","No"))'

    # ---------------------------------------------------------- top band
    def title(self):
        ws = self.ws
        for c in range(1, 11):
            ws.cell(1, c).fill = self.P["brand"]; ws.cell(2, c).fill = self.P["brand"]
        ws.row_dimensions[1].height = 30
        self.cell(1, 2, self.tool["name"].upper(), font=WHITE, alignment=MID)
        self.cell(2, 2, f'{self.org["name"]} · {self.cfg["pack"]["name"]} {self.cfg["pack"]["version"]}', font=WHITE_S)
        self.cell(1, 9, "Ready for review", font=WHITE_S, alignment=Alignment(horizontal="right", vertical="center"))
        self.ready_cell = self.cell(1, 10, None, font=Font(bold=True, size=12), alignment=Alignment(horizontal="center", vertical="center"))
        self.cell(3, 2, "Yellow cells are yours. Grey cells are worked out. Nothing in grey can be typed over.", font=MUTED)
        self.r = 5

    # ---------------------------------------------------------- sections
    def section(self, s, index):
        ws, r = self.ws, self.r
        for c in range(2, 11):
            ws.cell(r, c).fill = self.P["sect"]; ws.cell(r, c).border = UNDER
        self.cell(r, 2, f"{index}", font=BOLD)
        self.cell(r, 3, s["title"], font=Font(bold=True, size=12))
        mode = {"required": "Always", "optional": "Optional", "conditional": "Only when it applies"}[s["mode"]]
        self.cell(r, 4, mode, font=MUTED)
        status = self.cell(r, 9, None, font=BOLD)
        applies = self.cell(r, 11, None, font=MUTED)
        head_row = r
        self.r += 1
        rule = s.get("rule") if s["mode"] == "conditional" else None
        applies.value = "=" + self.applies_formula(rule) if rule else "Yes"
        applies_ref = f"$K${head_row}"
        terms = []
        self.cur_inputs = []
        start = self.r
        for b in s["blocks"]:
            if b["kind"] == "field":
                terms += self.field(b)
            elif b["kind"] == "grid":
                terms += self.grid_block(b, s)
            elif b["kind"] == "calc":
                self.calc(b)
            self.r += 0
        end = self.r - 1
        miss = "+".join(terms) if terms else "0"
        optional = s["mode"] == "optional"
        started = "+".join(f'({a}<>"")' for a in self.cur_inputs) or "0"
        opt = f'IF(({started})=0,"Optional",' if optional else "("
        status.value = (f'=IF({applies_ref}="No","Not applicable",IF({applies_ref}="Waiting","Waiting on an answer",'
                        f'{opt}IF(({miss})=0,"Complete",({miss})&" missing"))))')
        self.section_status.append((s["title"], f"Workpaper!$I${head_row}", f"Workpaper!$K${head_row}", optional))
        # grey the whole section when it does not apply; it keeps what was typed
        if rule and end >= start:
            rng = f"B{start}:J{end}"
            ws.conditional_formatting.add(rng, FormulaRule(formula=[f'{applies_ref}="No"'], fill=self.P["na"], font=Font(color="9AA3AE")))
        ws.conditional_formatting.add(f"I{head_row}", FormulaRule(formula=[f'I{head_row}="Complete"'], font=Font(color="127A4C", bold=True)))
        ws.conditional_formatting.add(f"I{head_row}", FormulaRule(formula=[f'ISNUMBER(SEARCH("missing",I{head_row}))'], font=Font(color="8A5A00", bold=True)))
        if optional:
            self.missing_total.append(f'IF({applies_ref}="No",0,{miss})*0')
        else:
            self.missing_total.append(f'IF({applies_ref}="No",0,IF({applies_ref}="Waiting",1,{miss}))')
        self.r += 1

    def field(self, f):
        r = self.r
        self.cell(r, 3, f["label"] + ("" if f.get("req") else "  (optional)"), alignment=MID)
        val = self.example.get(f["id"])
        if f.get("type") == "date" and isinstance(val, str):
            import datetime; val = datetime.date.fromisoformat(val)
        c = self.input_cell(r, 4, f, val)
        if f.get("type") == "longtext":
            self.ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=8)
            self.ws.row_dimensions[r].height = 60
        else:
            self.ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=5)
        self.addr[f["id"]] = f"$D${r}"
        hint = self.cell(r, 9, None, font=MUTED)
        if f.get("req"):
            hint.value = f'=IF(D{r}="","Required","")'
        self.record.append((f["label"], f"=IF(Workpaper!D{r}=\"\",\"\",Workpaper!D{r})"))
        self.r += 1
        return [f'(D{r}="")*1'] if f.get("req") else []

    # ---------------------------------------------------------- the table primitive
    def grid_block(self, g, s):
        ws = self.ws
        rows_from, cols_from = g["rows"]["from"], g["cols"]["from"]
        by = g.get("cellsBy", "col")
        lists = self.org["lists"]
        R = (g["rows"].get("items") if rows_from == "fixed" else
             [{"key": v, "label": v} for v in lists[g["rows"]["list"]]] if rows_from == "list" else
             [{"key": i, "label": str(i + 1)} for i in range(max(ENTERED_ROWS, g["rows"].get("min", 0), len((self.example.get(g["id"]) or {}).get("rows") or []) + 2))])
        C = (g["cols"].get("items") if cols_from == "fixed" else
             [{"key": f"c{j}", "label": f'{g["cols"].get("addLabel", "Column")} {j + 1}'} for j in range(ENTERED_COLS)])
        questions = rows_from == "fixed" and by == "col" and any(x.get("group") or x.get("info") for x in R)
        self.cell(self.r, 3, g["label"], font=Font(bold=True, color="465263")); self.r += 1
        top = self.r
        terms = []
        ex = self.example.get(g["id"], {})

        if questions:
            # header
            self.cell(self.r, 2, "#", font=BOLD, fill=self.P["head"])
            self.cell(self.r, 3, "Question", font=BOLD, fill=self.P["head"])
            for j, c in enumerate(C):
                self.cell(self.r, 4 + (0 if j == 0 else 1), c["label"], font=BOLD, fill=self.P["head"])
            for cc in (6, 7, 8):
                self.cell(self.r, cc, None, fill=self.P["head"])
            self.cell(self.r, 9, "Note", font=BOLD, fill=self.P["head"])
            self.r += 1
            rating, comment = C[0], (C[1] if len(C) > 1 else None)
            first = self.r
            last_group = None
            for i, q in enumerate(R):
                if q.get("group") and q["group"] != last_group:
                    self.cell(self.r, 3, q["group"], font=Font(bold=True, italic=True, color="465263"))
                    last_group = q["group"]; self.r += 1
                r = self.r
                self.cell(r, 2, q["key"], alignment=Alignment(vertical="top"))
                fw_row = self.framework_rows[q["key"]]
                c = self.cell(r, 3, f"=Framework!C{fw_row}", alignment=WRAP)
                if q.get("info"):
                    c.comment = Comment("How to test this:\n" + q["info"], "Framework", width=320, height=140)
                v = ex.get(str(q["key"]), {})
                rc = self.input_cell(r, 4, rating, v.get(rating["key"]))
                if comment:
                    cm = self.input_cell(r, 5, comment, v.get(comment["key"]))
                    ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=8)
                    cm.alignment = WRAP
                ws.row_dimensions[r].height = 32
                ap = self.cell(r, 11, "=" + self.applies_formula(q.get("when")), font=MUTED)
                rw = comment.get("reqWhen") if comment else None
                need = (f'AND(OR({",".join(f"D{r}=" + chr(34) + x + chr(34) for x in rw["values"])}),E{r}="")') if rw else "FALSE"
                self.cell(r, 9, f'=IF(K{r}="No","Not applicable",IF(K{r}="Waiting","Waiting on an answer",IF(D{r}="","Rate this",IF({need},"Comment needed",""))))', font=MUTED)
                terms.append(f'(K{r}="Yes")*((D{r}="")+({need}))')
                terms.append(f'(K{r}="Waiting")*1')
                ws.conditional_formatting.add(f"B{r}:I{r}", FormulaRule(formula=[f'$K{r}="No"'], fill=self.P["na"], font=Font(color="9AA3AE")))
                ws.conditional_formatting.add(f"D{r}", FormulaRule(formula=[f'D{r}="Not effective"'], font=Font(color="B4372C", bold=True)))
                ws.conditional_formatting.add(f"D{r}", FormulaRule(formula=[f'D{r}="Partially effective"'], font=Font(color="8A5A00", bold=True)))
                ws.conditional_formatting.add(f"D{r}", FormulaRule(formula=[f'D{r}="Effective"'], font=Font(color="127A4C", bold=True)))
                self.record.append((f'{rating["label"]}_{q["key"]}', f'=IF(Workpaper!K{r}="No","Not applicable",Workpaper!D{r})'))
                if comment:
                    self.record.append((f'{comment["label"]}_{q["key"]}', f'=IF(Workpaper!E{r}="","",Workpaper!E{r})'))
                self.r += 1
            self.grid[g["id"]] = {"ratings": f"D{first}:D{self.r - 1}", "applies": f"K{first}:K{self.r - 1}"}
            # tally
            self.cell(self.r, 3, "Rated so far", font=MUTED, alignment=Alignment(horizontal="right"))
            rg, ap = f"D{first}:D{self.r - 1}", f"K{first}:K{self.r - 1}"
            self.calc_cell(self.r, 4, f'=COUNTIFS({ap},"Yes",{rg},"<>")&" of "&COUNTIF({ap},"Yes")')
            for k, lab in enumerate(lists[rating["list"]][:3]):
                self.calc_cell(self.r, 5 + k, f'="{lab.split()[0]} "&COUNTIF({rg},"{lab}")')
            self.r += 2
            return terms

        # ---- table layout: header row
        self.cell(self.r, 2, "#" if rows_from == "entered" else "", font=BOLD, fill=self.P["head"])
        self.cell(self.r, 3, "" if rows_from == "entered" else "", font=BOLD, fill=self.P["head"])
        col0 = 3 if rows_from == "entered" else 4     # entered rows use C as the first column
        hdr = self.r
        for j, c in enumerate(C):
            h = self.cell(self.r, col0 + j, c["label"], font=BOLD, fill=self.P["head"], alignment=Alignment(wrap_text=True))
            if cols_from == "entered":
                h.fill = self.P["input"]; h.protection = UNLOCK; h.border = BOX
                cols_ex = list(ex.get("_cols") or []); lab = cols_ex[j] if j < len(cols_ex) else None
                h.value = lab or c["label"]
        self.r += 1
        first = self.r
        geo = {"cols": {}, "first": first}
        for i, row in enumerate(R):
            r = self.r
            if rows_from == "entered":
                self.cell(r, 2, i + 1, font=MUTED)
            else:
                lab = row["label"]
                self.cell(r, 3, lab, font=Font(italic=bool(row.get("compute"))))
            exrow = (ex.get("rows") or [])[i] if rows_from == "entered" and i < len(ex.get("rows") or []) else (ex.get(str(row["key"])) or {})
            for j, c in enumerate(C):
                col = col0 + j
                d = row if by == "row" else c
                key = c["key"]
                if d.get("compute"):
                    cc = d["compute"]
                    if by == "col":
                        ka, kb = cc["a"], cc["b"]
                        ca = col0 + [x["key"] for x in C].index(ka); cb = col0 + [x["key"] for x in C].index(kb)
                        A_, B_ = f"{L(ca)}{r}", f"{L(cb)}{r}"
                    else:
                        ra = first + [x["key"] for x in R].index(cc["a"]); rb = first + [x["key"] for x in R].index(cc["b"])
                        A_, B_ = f"{L(col)}{ra}", f"{L(col)}{rb}"
                    expr = {"mul": f"{A_}*{B_}", "pctof": f"{A_}*{B_}/100", "add": f"{A_}+{B_}", "sub": f"{A_}-{B_}", "div": f"IF({B_}=0,\"\",{A_}/{B_})"}[cc["op"]]
                    blank = f'OR({A_}="",{B_}="")'
                    self.calc_cell(r, col, f'=IF({blank},"",{expr})', FMT["money"] if d.get("money") else FMT["number"])
                else:
                    val = exrow.get(key) if isinstance(exrow, dict) else None
                    if cols_from == "entered" and isinstance(exrow, dict):
                        val = exrow.get(f"c{j}")
                    if d.get("type") == "date" and isinstance(val, str):
                        import datetime; val = datetime.date.fromisoformat(val)
                    self.input_cell(r, col, d, val)
                geo["cols"].setdefault(key, f"{L(col)}{first}:{L(col)}{first + len(R) - 1}")
            self.r += 1
        last = self.r - 1
        geo["last"] = last
        geo["colnames"] = {c["key"]: L(col0 + j) for j, c in enumerate(C)}
        self.grid[g["id"]] = geo
        # completeness
        if rows_from == "entered":
            used = "(" + "+".join(f'({L(col0 + j)}{first}:{L(col0 + j)}{last}<>"")' for j, c in enumerate(C) if not c.get("compute")) + ">0)"
            reqcols = [L(col0 + j) for j, c in enumerate(C) if c.get("req") and not c.get("compute")]
            if reqcols:
                terms.append(f'SUMPRODUCT({used}*((' + "+".join(f'({x}{first}:{x}{last}="")' for x in reqcols) + ')>0))')
            mn = g["rows"].get("min", 0)
            if mn:
                terms.append(f'(SUMPRODUCT({used}*1)<{mn})*1')
            self.cell(first, 9, f'=IF(SUMPRODUCT({used}*1)<{mn},"Add at least {mn}","")' if mn else None, font=MUTED)
        else:
            for i, row in enumerate(R):
                r = first + i
                for j, c in enumerate(C):
                    d = row if by == "row" else c
                    if d.get("req") and not d.get("compute"):
                        if cols_from == "entered":
                            cl = L(col0 + j)   # a person's column counts once anything is typed in it
                            terms.append(f'(SUMPRODUCT(({cl}{first}:{cl}{first + len(R) - 1}<>"")*1)>0)*({cl}{r}="")')
                        else:
                            terms.append(f'({L(col0 + j)}{r}="")*1')
        # totals
        if g.get("totals"):
            self.cell(self.r, 3, "Total", font=BOLD)
            for j, c in enumerate(C):
                d = c
                if by == "col" and (d.get("type") == "number" or d.get("compute")) and not d.get("noTotal"):
                    self.calc_cell(self.r, col0 + j, f"=SUM({L(col0 + j)}{first}:{L(col0 + j)}{last})", FMT["money"] if d.get("money") else FMT["number"]).font = BOLD
            self.r += 1
        if rows_from == "entered":
            self.cell(self.r, 3, f"{len(R)} rows offered. Need more? Insert rows inside the table; the formulas follow.", font=MUTED)
            self.r += 1
        self.record.append((f'{g["label"]} (rows used)', f'=SUMPRODUCT(((' + "+".join(f'(Workpaper!{L(col0 + j)}{first}:{L(col0 + j)}{last}<>"")' for j, c in enumerate(C) if not c.get("compute")) + ')>0)*1)' if rows_from == "entered" else f'={len(R)}'))
        self.r += 1
        return terms

    # ---------------------------------------------------------- calculations (from the library)
    def calc(self, b):
        m = b["method"]
        ws, r0 = self.ws, self.r
        lim = self.limits[b["id"]]
        name = {"dti": "Debt-to-income", "ltv": "Loan-to-value", "recon": "Reconciliation difference", "devrate": "Deviation rate"}[m]
        self.cell(r0, 3, f"{name}  ·  {b.get('code', m.upper() + '-DEMO 1.0')}", font=Font(bold=True, color="1F4E79"))
        self.r += 1
        rows = []
        if m == "dti":
            g = self.grid["income"]; a, per, src = g["cols"]["amount"], g["cols"]["per"], g["cols"]["source"]
            d = self.grid["debts"]["cols"]["payment"]
            pr = self.addr["proposed"]
            amt_c, per_c = g["colnames"]["amount"], g["colnames"]["per"]
            f1, f2 = g["first"], g["last"]
            used = f'(({src}<>"")+({a}<>"")+({per}<>"")>0)'
            missing = f'SUMPRODUCT({used}*((({a}="")+({per}=""))>0))+({pr}="")+(SUMPRODUCT({used}*1)=0)'
            rows = [("Monthly income", f'=SUMPRODUCT(({per}="Annual")*({a})/12+({per}="Monthly")*({a}))', FMT["money"]),
                    ("Existing monthly debt payments", f"=SUM({d})", FMT["money"]),
                    ("Proposed monthly payment", f"={pr}", FMT["money"]),
                    ("Inputs still missing", f"={missing}", "0"),
                    ("Debt-to-income", None, FMT["pct"])]
        elif m == "devrate":
            g = self.grid[b["grid"]]
            attrs = [g["cols"][k] for k in b["attributes"]]
            fr, la = g["first"], g["last"]
            cols = [g["colnames"][k] for k in b["attributes"]]
            any_ex = "+".join(f'({c}{fr}:{c}{la}="Exception")' for c in cols)
            tested = "+".join(f'({c}{fr}:{c}{la}<>"")' for c in cols)
            rows = [("Items tested", f"=SUMPRODUCT((({tested})>0)*1)", "0"),
                    ("Items with an exception", f"=SUMPRODUCT((({any_ex})>0)*1)", "0"),
                    ("Inputs still missing", f'=SUMPRODUCT(((({tested})>0)*(({tested})<{len(cols)}))*1)', "0"),
                    ("Deviation rate", None, FMT["pct"])]
        elif m == "recon":
            g = self.grid["items"]; t, a = g["cols"]["type"], g["cols"]["amount"]
            sb, gl = self.addr["stmt"], self.addr["gl"]
            rows = [("Adjusted bank", f'={sb}+SUMIF({t},"Deposit in transit",{a})-SUMIF({t},"Outstanding check",{a})', FMT["money"]),
                    ("Adjusted books", f'={gl}-SUMIF({t},"Bank fee not yet booked",{a})+SUMIF({t},"Interest not yet booked",{a})', FMT["money"]),
                    ("Inputs still missing", f'=({sb}="")+({gl}="")+SUMPRODUCT((({t}<>"")+({a}<>"")=1)*1)', "0"),
                    ("Difference", None, FMT["money"])]
        refs = {}
        for lab, f, fmt in rows:
            r = self.r
            self.cell(r, 3, lab, alignment=Alignment(horizontal="right"), font=BOLD if f is None else None)
            refs[lab] = f"D{r}"
            if f is not None:
                self.calc_cell(r, 4, f, fmt)
            self.r += 1
        res_row = self.r - 1
        miss = refs["Inputs still missing"]
        if m == "dti":
            inc, debt, prop = refs["Monthly income"], refs["Existing monthly debt payments"], refs["Proposed monthly payment"]
            self.calc_cell(res_row, 4, f'=IF({miss}>0,"Not calculated",IF({inc}=0,"No result",({debt}+{prop})/{inc}))', FMT["pct"])
        elif m == "devrate":
            self.calc_cell(res_row, 4, f'=IF(OR({miss}>0,{refs["Items tested"]}=0),"Not calculated",{refs["Items with an exception"]}/{refs["Items tested"]})', FMT["pct"])
        elif m == "recon":
            self.calc_cell(res_row, 4, f'=IF({miss}>0,"Not calculated",ROUND({refs["Adjusted bank"]}-{refs["Adjusted books"]},2))', FMT["money"])
        ws.cell(res_row, 4).font = Font(bold=True, size=12)
        # the test against the limit the organization confirmed
        r = self.r
        self.cell(r, 3, "Against the limit", alignment=Alignment(horizontal="right"))
        res = f"D{res_row}"
        cmp = f"ABS({res})<=Settings!{lim['policy']}+0.005" if m == "recon" else f"{res}<=Settings!{lim['policy']}"
        self.calc_cell(r, 4, f'=IF(Settings!{lim["confirmed"]}<>"Yes","Not tested: limit not confirmed",IF(ISNUMBER({res}),IF({cmp},"Within limit","Above limit"),"Not tested"))')
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=6)
        ws.conditional_formatting.add(f"D{r}", FormulaRule(formula=[f'D{r}="Above limit"'], font=Font(color="B4372C", bold=True)))
        ws.conditional_formatting.add(f"D{r}", FormulaRule(formula=[f'D{r}="Within limit"'], font=Font(color="127A4C", bold=True)))
        ws.conditional_formatting.add(f"D{r}", FormulaRule(formula=[f'LEFT(D{r},10)="Not tested"'], font=Font(color="8A5A00", bold=True)))
        self.cell(r, 9, f"Limit lives on Settings, not in the method.", font=MUTED)
        self.record.append((name, f'=Workpaper!{res}'))
        self.record.append((name + " against limit", f"=Workpaper!D{r}"))
        self.r += 2

    # ---------------------------------------------------------- other sheets
    def lists_sheet(self):
        ls = self.wb.create_sheet("Lists")
        ls["A1"] = "Lists"; ls["A1"].font = Font(bold=True, size=13)
        ls["A2"] = "Organization lists. Every dropdown reads from here. Add a value at the end of a list; retired values can be struck through but stay."
        ls["A2"].font = MUTED
        for j, (name, vals) in enumerate(self.org["lists"].items(), start=1):
            ls.cell(4, j, name).font = BOLD; ls.cell(4, j).fill = self.P["head"]
            for i, v in enumerate(vals, start=5):
                ls.cell(i, j, v).protection = UNLOCK
            ls.column_dimensions[L(j)].width = max(16, len(name) + 4)
            ref = f"Lists!${L(j)}$5:${L(j)}${4 + len(vals) + 10}"
            self.wb.defined_names[f"List_{safe_name(name)}"] = DefinedName(f"List_{safe_name(name)}", attr_text=ref)

    def framework_sheet(self):
        fw = self.wb.create_sheet("Framework")
        fw["A1"] = "Framework"; fw["A1"].font = Font(bold=True, size=13)
        fw["A2"] = "The questions and how to test each. The workpaper reads its question wording from this sheet."; fw["A2"].font = MUTED
        heads = ["Section", "#", "Question", "How to test"]
        for j, h in enumerate(heads, start=1):
            c = fw.cell(4, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = self.P["brand"]
        self.framework_rows = {}
        r = 5
        for s in self.tool["sections"]:
            for b in s["blocks"]:
                if b["kind"] == "grid" and b["rows"]["from"] == "fixed" and any(x.get("group") or x.get("info") for x in b["rows"]["items"]):
                    for q in b["rows"]["items"]:
                        for j, v in enumerate([q.get("group", ""), q["key"], q["label"], q.get("info", "")], start=1):
                            c = fw.cell(r, j, v); c.alignment = WRAP; c.border = BOX
                            if j in (3, 4):
                                c.protection = UNLOCK
                        self.framework_rows[q["key"]] = r
                        r += 1
        for j, w in enumerate([18, 7, 52, 70], start=1):
            fw.column_dimensions[L(j)].width = w
        fw.freeze_panes = "A5"
        return fw

    def settings_sheet(self):
        st = self.wb.create_sheet("Settings")
        st["A1"] = "Settings"; st["A1"].font = Font(bold=True, size=13)
        st["A2"] = "Limits are this organization's, not the method's. Until a limit is confirmed, nothing is tested against it."; st["A2"].font = MUTED
        heads = ["Limit", "Method", "The author recommends", "Our policy", "Confirmed?", "Confirmed by", "Date"]
        for j, h in enumerate(heads, start=1):
            c = st.cell(4, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = self.P["brand"]
        self.limits = {}
        r = 5
        conf = self.cfg.get("confirmations", {}) if self.cfg.get("_fill") else {}
        dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True); st.add_data_validation(dv)
        for s in self.tool["sections"]:
            for b in s["blocks"]:
                if b["kind"] != "calc":
                    continue
                pct = b["method"] in ("dti", "ltv", "devrate")
                fmt = "0.0%" if pct else FMT["money"]
                st.cell(r, 1, b["limitLabel"]); st.cell(r, 2, b.get("code", ""))
                st.cell(r, 3, b["limit"]).number_format = fmt
                cf = conf.get(b["id"], {})
                pol = st.cell(r, 4, cf.get("policy", b["limit"])); pol.number_format = fmt; pol.fill = self.P["input"]; pol.protection = UNLOCK; pol.border = BOX
                c5 = st.cell(r, 5, cf.get("confirmed", "No")); c5.fill = self.P["input"]; c5.protection = UNLOCK; c5.border = BOX; dv.add(c5.coordinate)
                for k, key in ((6, "by"), (7, "date")):
                    c = st.cell(r, k, cf.get(key)); c.fill = self.P["input"]; c.protection = UNLOCK; c.border = BOX
                self.limits[b["id"]] = {"policy": f"$D${r}", "confirmed": f"$E${r}"}
                r += 1
        for j, w in enumerate([34, 16, 22, 14, 12, 16, 12], start=1):
            st.column_dimensions[L(j)].width = w
        return st

    def check_sheet(self):
        ck = self.wb.create_sheet("Check", 1)
        ck["A1"] = "Release check"; ck["A1"].font = Font(bold=True, size=13)
        ck["A2"] = "Every line must read OK before this goes for review. Each line says what to do."; ck["A2"].font = MUTED
        for j, h in enumerate(["Check", "Result", "What to do"], start=1):
            c = ck.cell(4, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = self.P["brand"]
        r = 5
        oks = []
        for title, status, applies, optional in self.section_status:
            ck.cell(r, 1, f"Section: {title}")
            ck.cell(r, 2, f'=IF(OR({status}="Complete",{status}="Not applicable"),"OK",{status})')
            ck.cell(r, 3, f'=IF(B{r}="OK","","Go to “{title}” on the Workpaper")' if not optional else f'=IF(B{r}="OK","","Optional. Finish it or clear it.")')
            if not optional:
                oks.append(f'B{r}="OK"')
            r += 1
        for lid, ref in self.limits.items():
            ck.cell(r, 1, "Limit confirmed: " + lid.replace("calc_", "").upper())
            ck.cell(r, 2, f'=IF(Settings!{ref["confirmed"]}="Yes","OK","Not confirmed")')
            ck.cell(r, 3, f'=IF(B{r}="OK","","Confirm it on Settings")')
            oks.append(f'B{r}="OK"'); r += 1
        ck.cell(r + 1, 1, "Ready for review").font = Font(bold=True, size=12)
        ck.cell(r + 1, 2, f'=IF(AND({",".join(oks)}),"Yes","No")').font = Font(bold=True, size=12)
        self.ready_cell.value = f"=Check!B{r + 1}"
        for rr in range(5, r + 2):
            ck.conditional_formatting.add(f"B{rr}", FormulaRule(formula=[f'OR(B{rr}="OK",B{rr}="Yes")'], font=Font(color="127A4C", bold=True)))
            ck.conditional_formatting.add(f"B{rr}", FormulaRule(formula=[f'AND(B{rr}<>"OK",B{rr}<>"Yes",B{rr}<>"")'], font=Font(color="B4372C", bold=True)))
        self.ws.conditional_formatting.add("J1", FormulaRule(formula=['J1="Yes"'], fill=PatternFill("solid", fgColor="E3F4EC"), font=Font(color="127A4C", bold=True)))
        self.ws.conditional_formatting.add("J1", FormulaRule(formula=['J1="No"'], fill=PatternFill("solid", fgColor="FDF1D6"), font=Font(color="8A5A00", bold=True)))
        for j, w in enumerate([40, 26, 44], start=1):
            ck.column_dimensions[L(j)].width = w

    def record_sheet(self):
        rc = self.wb.create_sheet("Record")
        rc["A1"] = "Record"; rc["A1"].font = Font(bold=True, size=13)
        rc["A2"] = "One row for the database. It builds itself from the Workpaper. Adding a question to the Framework adds a column."; rc["A2"].font = MUTED
        for j, (h, f) in enumerate(self.record, start=1):
            c = rc.cell(4, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = self.P["brand"]; c.alignment = Alignment(wrap_text=True, vertical="top")
            rc.cell(5, j, f)
            rc.column_dimensions[L(j)].width = 18
        rc.cell(4, len(self.record) + 1, "_missing").font = Font(bold=True, color="FFFFFF")
        rc.cell(4, len(self.record) + 1).fill = self.P["brand"]
        rc.cell(5, len(self.record) + 1, "=Workpaper!$J$3")
        rc.freeze_panes = "A5"

    def about_sheet(self):
        ab = self.wb.create_sheet("About")
        rows = [("Tool", self.tool["name"]), ("Pack", f'{self.cfg["pack"]["name"]} {self.cfg["pack"]["version"]}'),
                ("Organization", self.org["name"]), ("Generated from", f'configs/{self.cfg["_file"]} (the builder\'s "As data")'),
                ("How to use", "Fill the yellow cells on Workpaper. Sections and questions that do not apply grey out by themselves and keep what you typed. When Check says Ready for review, send it."),
                ("Protection", "Sheets are protected without a password, so formulas are not typed over by accident. It is not security."),
                ("Note", "Synthetic example. Methods and limits are fictional demonstrations. Example wording, not any organization's policy.")]
        for i, (k, v) in enumerate(rows, start=1):
            ab.cell(i, 1, k).font = BOLD; c = ab.cell(i, 2, v); c.alignment = WRAP
        ab.column_dimensions["A"].width = 18; ab.column_dimensions["B"].width = 100

    # ---------------------------------------------------------- build
    def build(self, path):
        self.framework_sheet()
        self.settings_sheet()
        self.lists_sheet()
        self.title()
        for i, s in enumerate(self.tool["sections"], start=1):
            self.section(s, i)
        self.cell(3, 9, "Still missing", font=MUTED, alignment=Alignment(horizontal="right"))
        self.cell(3, 10, "=" + ("+".join(self.missing_total) if self.missing_total else "0"), font=BOLD, alignment=Alignment(horizontal="center"))
        self.check_sheet()
        self.record_sheet()
        self.about_sheet()
        ws = self.ws
        for c, w in WIDTHS.items():
            ws.column_dimensions[L(c)].width = w
        ws.column_dimensions["K"].hidden = True   # helper: whether each section or question applies
        ws.freeze_panes = "A4"
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = "1:2"
        order = ["Workpaper", "Check", "Settings", "Framework", "Lists", "Record", "About"]
        self.wb._sheets = [self.wb[n] for n in order]
        for name in ("Workpaper", "Check", "Settings", "Framework", "Lists", "Record"):
            self.wb[name].protection.sheet = True
            self.wb[name].protection.formatCells = False
            self.wb[name].protection.formatColumns = False
            self.wb[name].protection.formatRows = False
            self.wb[name].protection.insertRows = False
        self.wb.active = 0
        self.wb.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    built = []
    for p in sorted(CONFIGS.glob("*.json")):
        cfg = json.loads(p.read_text())
        cfg["_file"] = p.name
        stem = cfg["tool"]["name"]
        for fill in (False, True):
            if fill and "example" not in cfg:
                continue
            cfg["_fill"] = fill
            name = f'{stem} - {"example" if fill else "blank tool"}.xlsx'
            Builder(cfg).build(OUT / name)
            built.append(name)
    print("built:", *built, sep="\n  ")


if __name__ == "__main__":
    sys.exit(main())
