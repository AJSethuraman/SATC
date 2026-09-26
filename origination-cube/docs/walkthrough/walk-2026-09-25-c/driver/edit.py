"""Stand-in for typing in Excel: set cells and save.  python3 edit.py BOOK 'Sheet!A1=value' ...
A value that reads as a number is typed as a number, as Excel would; '' clears the cell."""
import sys
from openpyxl import load_workbook

book, edits = sys.argv[1], sys.argv[2:]
wb = load_workbook(book)
for e in edits:
    ref, _, val = e.partition("=")
    sheet, cell = ref.split("!")
    v = val
    if val == "":
        v = None
    else:
        try:
            v = int(val)
        except ValueError:
            try:
                v = float(val)
            except ValueError:
                pass
    wb[sheet][cell].value = v
    print(f"{sheet}!{cell} <- {v!r}")
wb.save(book)
