"""The made-up loan files this tie-out adds, each built from the full tie-out's Consumer book Q3.csv (8,000 made-up
loans) with Python's csv and random modules alone -- no PocketBook -- so every planted value is known:

  Flag book.csv       Q3 plus SYS_FLAG: Y or N, blank on every 97th loan (so three values: N, Y and the blank),
                      drawn after every other value, a bad loan a little more likely to carry Y (0.60 against 0.45).
                      Split by SYS_FLAG: each value against the rest of its pocket (change 1).
  Two-flag book.csv   the same SYS_FLAG with its blanks read as N: two values, Y against N (change 1, K = 2).
  Bureau book.csv     Q3 plus SHORT_HIST, months of credit history 0 to 435, and on every 40th loan one of four bureau
                      codes -99,000,901 to -99,000,904 (none of them on 1% of the loans), as
                      tests/test_firm_answers_2026_09_29.py's _bureau_file plants them (change 4).

    python3 make_books.py "../2026-09-28/Consumer book Q3.csv" OUT_FOLDER
"""
import csv
import random
import sys
from pathlib import Path

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(open(SRC, newline="", encoding="utf-8")))
head = list(rows[0])


def write(name, cols, rs):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rs)
    print(name, len(rs))


rng = random.Random("tie-out 29 Sep 2026: SYS_FLAG")
flag = []
for i, r in enumerate(rows):
    y = rng.random() < (0.60 if r["BAD_FLAG"] == "1" else 0.45)
    flag.append("" if i % 97 == 0 else "Y" if y else "N")
write("Flag book.csv", head + ["SYS_FLAG"], [{**r, "SYS_FLAG": f} for r, f in zip(rows, flag)])
write("Two-flag book.csv", head + ["SYS_FLAG"], [{**r, "SYS_FLAG": f or "N"} for r, f in zip(rows, flag)])

# 30 Sep 2026: the Grey book -- Q3 with three loans of FICO 712 - 745 moved to a CHANNEL of their own, "Kiosk", so
# FICO x CHANNEL has a 3-loan pocket (Grids greys a pocket under the Run's fewest loans)
grey, moved = [dict(r) for r in rows], 0
for r in grey:
    f = r["FICO"]
    if f not in ("", "-9999") and 712 <= float(f) <= 745 and moved < 3:
        r["CHANNEL"] = "Kiosk"
        moved += 1
write("Grey book.csv", head, grey)

# 30 Sep 2026, build 44734da4: the Year book -- Q3 with every loan's origination date drawn again, evenly over
# 2022-01-01 to 2024-12-31 (seeded), and every 151st date blank, so ORIG_YEAR has three years and "(no date)"; for
# Filter by ORIG_YEAR with a number split at the same time, and for ORIG_YEAR as the split. The same rows as
# "Year-split book.csv", so its workbook is a second Run beside the first
from datetime import date, timedelta  # noqa: E402
rng = random.Random("tie-out 30 Sep 2026: ORIG_YEAR")
span = (date(2025, 1, 1) - date(2022, 1, 1)).days - 1
year = []
for i, r in enumerate(rows):
    made = date(2022, 1, 1) + timedelta(days=rng.randint(0, span))
    year.append({**r, "ORIG_DATE": "" if i % 151 == 5 else made.isoformat()})
# and the 61 highest FICOs blanked, so FICO's lowest band edge falls between whole numbers (653.4: the 20% point
# lands between the last 653 and the first 654). A whole-number column's label must then say the band holds 653
# ("496 - 653"), where the build before printed "496 - 652"
top = sorted((i for i, r in enumerate(year) if r["FICO"] not in ("", "-9999")),
             key=lambda i: (-float(year[i]["FICO"]), i))[:61]
for i in top:
    year[i] = {**year[i], "FICO": ""}
write("Year book.csv", head, year)
write("Year-split book.csv", head, year)

rng = random.Random(3)
hist = [-99000901 - (i // 40) % 4 if i % 40 == 0 else rng.randint(0, 435) for i in range(len(rows))]
write("Bureau book.csv", head + ["SHORT_HIST"], [{**r, "SHORT_HIST": h} for r, h in zip(rows, hist)])
