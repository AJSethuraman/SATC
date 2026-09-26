"""Where it bleeds (and Three-way), read back for the blue rows: material but too small to test.

    python3.12 bluecheck.py BOOK.xlsx [TAB]

Blue comes from a conditional format: Material (column L) is "yes" and the flag (column Q) starts "too few".
Prints the rows that would be blue, the rows that are material and untested by any other wording, the
window's claim (from the Log tab's last run), and whether the count agrees."""
import re, sys, collections
from openpyxl import load_workbook
wb = load_workbook(sys.argv[1])
tab = sys.argv[2] if len(sys.argv) > 2 else "Where it bleeds"
ws = wb[tab]
print(ws["B2"].value[:400])
print("conditional formats:", [(str(r.sqref), [x.formula for x in r.rules]) for r in ws.conditional_formatting])
hdr = [c.value for c in ws[4]]
blue, flags, material = [], collections.Counter(), collections.Counter()
for r in ws.iter_rows(min_row=5, values_only=True):
    if not r[1]:
        continue
    d = dict(zip(hdr, r))
    fl = r[16]
    flags[fl] += 1
    material[(r[11], "too few" in str(fl))] += 1
    if r[11] == "yes" and str(fl)[:7] == "too few":
        blue.append(r)
print("flags:", dict(flags))
print("material x untested:", dict(material))
print(len(blue), "blue rows")
for r in blue[:40]:
    print("  ", r[1], "|", r[3], "/", r[5], "|", r[6], "loans | rate", round(r[7], 4) if isinstance(r[7], float) else r[7],
          "| excess", round(r[9], 1) if isinstance(r[9], float) else r[9], r[10], "| material", r[11], "|", r[16])
if "Log" in wb.sheetnames:
    for row in wb["Log"].iter_rows(values_only=True):
        for v in row:
            if v and "too small to test" in str(v):
                print("LOG:", v)
