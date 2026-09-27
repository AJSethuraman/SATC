"""One line per workbook: the lines on Losses vs revenue, the planted pocket's box, and how many
pockets read losing more / earning more / earning less, split into plain and "(... could be luck)".
Used for step 13's table of revenue options and GCO lines.

    python3.12 revenue_options.py PLANTED_BAND BOOK.xlsx...      (PLANTED_BAND: "under 654" or "under 620")

Sixth walk (commit fec5f71): OC-30 lets the lines decide the boxes and marks a luck gap in brackets,
so a box can carry "(loss gap could be luck)", "(revenue gap could be luck)" or "(both gaps could be luck)".
"""
import re, sys
from openpyxl import load_workbook
band = sys.argv[1]
for p in sys.argv[2:]:
    ws = load_workbook(p)["Losses vs revenue"]
    sub = ws["B2"].value
    rows = [r for r in ws.iter_rows(min_row=4, values_only=True) if isinstance(r[3], (int, float)) and r[8]]
    boxed = [r for r in rows if not r[8].startswith("Not tested")]
    luck_r = lambda b: "revenue gap could be luck" in b or "both gaps" in b      # noqa: E731
    luck_g = lambda b: "loss gap could be luck" in b or "both gaps" in b         # noqa: E731
    cnt = {}
    for word in ("Losing more", "earning more", "earning less"):
        hit = [r[8] for r in boxed if word in r[8]]
        lk = luck_g if word.startswith("Losing") else luck_r
        cnt[word] = (sum(1 for b in hit if not lk(b)), sum(1 for b in hit if lk(b)))
    planted = [r[8] for r in rows if r[1] == band and r[2] == "Broker"]
    gl = re.search(r"GCO counts as more at ([\d.]+)x or above and less at ([\d.]+)x", sub).groups()
    rl = re.search(r"Revenue counts as more at ([\d.]+)x or above and less at ([\d.]+)x", sub).groups()
    print(f"{p.split('/')[-2]:12} GCO {gl[0]}/{gl[1]}  revenue {rl[0]}/{rl[1]} | boxed {len(boxed)} | "
          + " | ".join(f"{k}: {a} plain + {b} luck" for k, (a, b) in cnt.items()))
    print(f"{'':12} planted {band} / Broker: {planted}")
