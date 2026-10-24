"""Widen a tab's print area so the render shows what Excel shows on screen past it.

    python3.12 widen.py BOOK.xlsx OUT.xlsx 'Sheet!B1:H25' [...]

The sixth walk: Control's print area stops at column F, so LibreOffice's print leaves out the new
"Last Run used" column (H). In Excel it's on screen, to the right of the 70-wide "What it means"
column and the hidden key column. This copy only moves the print area; nothing else changes."""
import sys
from openpyxl import load_workbook

src, out, areas = sys.argv[1], sys.argv[2], sys.argv[3:]
wb = load_workbook(src)
for a in areas:
    sheet, rng = a.split("!")
    wb[sheet].print_area = rng
    print(sheet, "print area ->", rng)
wb.save(out)
