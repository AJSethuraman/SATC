"""Open every generated workbook in LibreOffice (which recalculates all formulas), then read results by
defined name and compare them with independent arithmetic. A formula error or a wrong value fails.
Reading by name means the checks do not care where the design puts things.

    python3 workpaper-studio/excel/check_tool_workbooks.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

OUT = Path(__file__).resolve().parent / "out"
ERR = {"#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "Err:502", "Err:504", "Err:508", "Err:511", "Err:522"}
tmp = Path(tempfile.mkdtemp())
fails, checks = [], 0


def recalc(p):
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(tmp), str(p)], check=True, capture_output=True, timeout=240)
    return load_workbook(p, data_only=False), load_workbook(tmp / p.name, data_only=True)


def by_name(wf, wv, nm):
    dn = wf.defined_names[nm]
    sheet, coord = next(iter(dn.destinations))
    return wv[sheet][coord.replace("$", "")].value


def eq(label, got, want):
    global checks
    checks += 1
    ok = abs(got - want) < 1e-6 if isinstance(want, float) and isinstance(got, (int, float)) else got == want
    if not ok:
        fails.append(f"{label}: got {got!r}, want {want!r}")


for p in sorted(OUT.glob("*.xlsx")):
    wf, wv = recalc(p)
    V = lambda nm: by_name(wf, wv, nm)
    errs = [f"{ws.title}!{c.coordinate}={c.value}" for ws in wv.worksheets for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.strip() in ERR]
    checks += 1
    if errs:
        fails.append(f"{p.name}: formula errors {errs[:6]}")
    n = p.name
    if n == "Credit file review - example.xlsx":
        eq(n + " DTI", V("Result_calc_dti"), (612 + 95 + 0 + 5780) / (8000 + 1450 + 3200))
        eq(n + " monthly income", V("Calc_calc_dti_Monthly_income"), 12650)
        eq(n + " verdict", V("Verdict_calc_dti"), "Above limit")
        eq(n + " test questions", V("Status_s3"), "1 missing")
        eq(n + " supporting", V("Status_s4"), "Complete")
        eq(n + " conclusion", V("Status_s5"), "1 missing")
        eq(n + " tester panel", V("Status_tester"), "Complete")
        eq(n + " ready", V("Ready"), "No")
        eq(n + " missing", V("Missing"), 2)
    if n == "Credit file review - blank tool.xlsx":
        eq(n + " DTI", V("Result_calc_dti"), "Not calculated")
        eq(n + " part-built income withheld", V("Calc_calc_dti_Monthly_income"), "Not calculated")
        eq(n + " supporting", V("Status_s4"), "Optional")
        eq(n + " verdict", V("Verdict_calc_dti"), "Not tested: limit not confirmed")
        eq(n + " ready", V("Ready"), "No")
    if n == "Control test - example.xlsx":
        eq(n + " deviation", V("Result_calc_dev"), 2 / 25)
        eq(n + " tested", V("Calc_calc_dev_Items_tested"), 25)
        eq(n + " verdict", V("Verdict_calc_dev"), "Above limit")
        eq(n + " exceptions", V("Status_s3"), "Complete")
        eq(n + " ready", V("Ready"), "Yes")
    if n == "Bank reconciliation - example.xlsx":
        eq(n + " adjusted bank", V("Calc_calc_rec_Adjusted_bank"), 185600.55 + 12400 - (18950 + 4310.20 + 1280))
        eq(n + " difference", V("Result_calc_rec"), 0.0)
        eq(n + " verdict", V("Verdict_calc_rec"), "Within limit")
        eq(n + " intercompany", V("Status_s3"), "Not applicable")
        eq(n + " ready", V("Ready"), "Yes")

print(f"workbooks: {len(list(OUT.glob('*.xlsx')))} · checks: {checks} · failures: {len(fails)}")
for f in fails:
    print("  ", f)
sys.exit(1 if fails else 0)
