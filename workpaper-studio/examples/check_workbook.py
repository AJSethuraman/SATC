"""Open the example workbook the way a person would: LibreOffice recalculates every
formula, then we read the results back and compare them with independent arithmetic.
A formula that errors, or a value that disagrees, fails the check.

Run: python3 workpaper-studio/examples/check_workbook.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

OUT = Path(__file__).resolve().parent / "out"
src = OUT / "CR-2026Q3-07.xlsx"
tmp = Path(tempfile.mkdtemp())
subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(tmp), str(src)],
               check=True, capture_output=True, timeout=180)
wb = load_workbook(tmp / src.name, data_only=True)

errors = []
checked = 0
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.strip() in ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "Err:502", "Err:504"):
                errors.append(f"{ws.title}!{c.coordinate} = {c.value}")
            checked += 1

expect = {
    ("DTI", "B12"): 8000 + 1450 + 3200,                 # monthly income
    ("DTI", "B13"): (612 + 95 + 0 + 5780) / 12650,       # debt-to-income
    ("DTI", "B15"): "Above limit",
    ("Cash flow", "B4"): 96000 - 18600,
    ("Cash flow", "C4"): 41000 - 6200,
    ("Collateral", "D2"): 190000 * 0.70,
    ("Collateral", "D4"): 190000 * 0.70 + 240000 * 0.80,
    ("Facilities", "C4"): 285000 + 75000,
    ("Cover", "B11"): 9, ("Cover", "B12"): 6, ("Cover", "B13"): 2, ("Cover", "B14"): 1,
}
bad = []
for (sheet, cell), want in expect.items():
    got = wb[sheet][cell].value
    ok = (abs(got - want) < 1e-9) if isinstance(want, (int, float)) and isinstance(got, (int, float)) else got == want
    if not ok:
        bad.append(f"{sheet}!{cell}: got {got!r}, want {want!r}")

print(f"cells examined: {checked}; formula errors: {len(errors)}; expected values checked: {len(expect)}; mismatches: {len(bad)}")
for e in errors + bad:
    print("  ", e)
sys.exit(1 if errors or bad else 0)
