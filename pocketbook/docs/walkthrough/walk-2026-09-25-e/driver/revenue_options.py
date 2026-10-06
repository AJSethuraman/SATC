"""One line per workbook: the revenue line on Losses vs revenue, the planted pocket's box, and how many
pockets read earning more or less. Used for step 13's table of revenue options.

    python3.12 revenue_options.py BOOK.xlsx...
"""
import sys, collections
from openpyxl import load_workbook
for p in sys.argv[1:]:
    ws = load_workbook(p)["Losses vs revenue"]
    rows = [r for r in ws.iter_rows(min_row=4, values_only=True) if isinstance(r[3], (int, float)) and r[8]]
    c = collections.Counter(r[8] for r in rows)
    planted = [r[8] for r in rows if r[1] == "under 654" and r[2] == "Broker"]
    print(p.split('/')[-2], "|", ws["B2"].value[ws["B2"].value.find("Revenue"):][:170])
    print("   planted:", planted, "| earning more:", sum(v for k, v in c.items() if "earning more" in k),
          "earning less:", sum(v for k, v in c.items() if "earning less" in k), "| total", len(rows))
