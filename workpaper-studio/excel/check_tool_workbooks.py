"""Open every generated workbook in LibreOffice (which recalculates all formulas), then check the
results against independent arithmetic. A formula error or a wrong value fails.

    python3 workpaper-studio/excel/check_tool_workbooks.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

OUT = Path(__file__).resolve().parent / "out"
ERR = {"#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "Err:502", "Err:504", "Err:508", "Err:511"}
tmp = Path(tempfile.mkdtemp())
fails, checks = [], 0


def recalc(p):
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(tmp), str(p)], check=True, capture_output=True, timeout=240)
    return load_workbook(tmp / p.name, data_only=True)


def by_label(ws, label, col=4):
    for row in ws.iter_rows(min_col=3, max_col=3):
        c = row[0]
        if isinstance(c.value, str) and c.value.strip() == label:
            return ws.cell(c.row, col).value
    raise KeyError(label)


def section_status(ws, title):
    for row in ws.iter_rows(min_col=3, max_col=3):
        c = row[0]
        if c.value == title and ws.cell(c.row, 2).value is not None:
            return ws.cell(c.row, 9).value
    raise KeyError(title)


def eq(name, got, want):
    global checks
    checks += 1
    ok = abs(got - want) < 1e-6 if isinstance(want, float) and isinstance(got, (int, float)) else got == want
    if not ok:
        fails.append(f"{name}: got {got!r}, want {want!r}")


for p in sorted(OUT.glob("*.xlsx")):
    wb = recalc(p)
    errs = [f"{ws.title}!{c.coordinate}={c.value}" for ws in wb.worksheets for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.strip() in ERR]
    checks += 1
    if errs:
        fails.append(f"{p.name}: formula errors {errs[:5]}")
    ws, ck = wb["Workpaper"], wb["Check"]
    n = p.name
    if n == "Credit file review - example.xlsx":
        eq(n + " DTI", by_label(ws, "Debt-to-income"), (612 + 95 + 0 + 5780) / (8000 + 1450 + 3200))
        eq(n + " DTI against limit", by_label(ws, "Against the limit"), "Above limit")
        eq(n + " monthly income", by_label(ws, "Monthly income"), 12650.0)
        eq(n + " cash left J. Hale", by_label(ws, "Left after debt payments"), 77400.0)
        eq(n + " cash left M. Hale", by_label(ws, "Left after debt payments", 5), 34800.0)
        eq(n + " test questions", section_status(ws, "Test questions"), "1 missing")       # 6.01 not rated yet
        eq(n + " conclusion", section_status(ws, "Conclusion"), "1 missing")               # summary not written yet
        eq(n + " ready", ws["J1"].value, "No")
    if n == "Credit file review - blank tool.xlsx":
        eq(n + " DTI", by_label(ws, "Debt-to-income"), "Not calculated")
        eq(n + " supporting optional", section_status(ws, "Supporting analysis"), "Optional")
        eq(n + " ready", ws["J1"].value, "No")
        eq(n + " limit not confirmed", by_label(ws, "Against the limit"), "Not tested: limit not confirmed")
    if n == "Control test - example.xlsx":
        eq(n + " deviation", by_label(ws, "Deviation rate"), 2 / 25)
        eq(n + " tested", by_label(ws, "Items tested"), 25)
        eq(n + " against", by_label(ws, "Against the limit"), "Above limit")
        eq(n + " exceptions section", section_status(ws, "Exceptions"), "Complete")
        eq(n + " ready", ws["J1"].value, "Yes")
    if n == "Bank reconciliation - example.xlsx":
        eq(n + " adjusted bank", by_label(ws, "Adjusted bank"), 185600.55 + 12400 - (18950 + 4310.20 + 1280))
        eq(n + " difference", by_label(ws, "Difference"), 0.0)
        eq(n + " against", by_label(ws, "Against the limit"), "Within limit")
        eq(n + " intercompany", section_status(ws, "Intercompany"), "Not applicable")
        eq(n + " ready", ws["J1"].value, "Yes")

print(f"workbooks: {len(list(OUT.glob('*.xlsx')))} · checks: {checks} · failures: {len(fails)}")
for f in fails:
    print("  ", f)
sys.exit(1 if fails else 0)
