"""The PocketBook road for the second run kind, Test new variables (scouting), on the book tests/test_scout.py uses
(its `wide` fixture): 12,000 made-up loans with income / sales cliffs (below 0.1, above 2.0), UTIL (a cliff above 0.9)
and TENURE (nothing) planted, and filler columns with nothing behind them. Nine candidates: income / sales made on
Columns, and UTIL, TENURE, F1, F2, F3, F4, REGION ticked Test it; FICO and CHANNEL held fixed; BAD_FLAG the outcome;
the cutoff at the suggested month. The walk's own scouting book shortlists one candidate, so its joint model never
draws; this one shortlists more than one, so every table on New variables has figures in it.

    python3 make_scout_book.py ../../../src "/tmp/credit/Loan files"

It writes "Scouting book.csv" into the folder and runs PocketBook on it the way the tests do (book.set_up, the
answers Control and Columns take, book.run), leaving "Scouting book - PocketBook.xlsx" beside it. This script is on
PocketBook's side of the tie-out and uses PocketBook freely; nothing on the other road imports it.
"""
import csv
import os
import random
import sys
from pathlib import Path

SRC, FOLDER = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
HOME = FOLDER.parent
os.environ["HOME"] = str(HOME)
os.environ["POCKETBOOK_MEMORY"] = str(HOME / "memory-scouting.yaml")
os.environ["GIT_CEILING_DIRECTORIES"] = str(HOME)
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC.parent / "tests"))

from openpyxl import load_workbook  # noqa: E402
from pocketbook import book, synth  # noqa: E402
from test_book import _answer  # noqa: E402
from test_book_dates import _choose, _control  # noqa: E402

NEW = "Finding and testing a new variable"
HOLD = ("FICO", "CHANNEL")
TEST = ("UTIL", "TENURE", "F1", "F2", "F3", "F4", "REGION")
SUGGESTED = "The month start nearest 70% of the loans (suggested)"


def filler(rows):
    """tests/test_scout.py's _filler, verbatim: four number columns and a category with nothing behind them."""
    rng = random.Random("scout-filler")
    for r in rows:
        f1 = rng.gauss(50, 15)
        r["F1"] = round(f1, 2)
        r["F2"] = round(0.9 * f1 + rng.gauss(0, 3), 2)
        r["F3"] = round(rng.gauss(10, 1), 3)
        r["F4"] = round(rng.uniform(0, 100), 1)
        r["REGION"] = rng.choice(["North", "South", "East", "West", "Central"])


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    x = FOLDER / "Scouting book.csv"
    rows = synth.add_shortlist(synth.make_rows(12000, 7, ratio=True), 7)
    filler(rows)
    with x.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    b = book.set_up(x).book
    _answer(b)
    _control(b, run_kind=NEW, new_variable_step="Scout first", **{"derived|1": ("income_to_sales", "INCOME", "SALES")})
    book.set_up(x)
    wb = load_workbook(b)
    names = [str(r[book.C_NAME - 1].value) for r in book.table_rows(wb["Columns"]) if r[book.C_NAME - 1].value]
    _choose(b, drop=tuple(c for c in names if c not in HOLD), run_kind="new_variable", outcome="BAD_FLAG",
            test=TEST, hold=HOLD)
    _control(b, cutoff=SUGGESTED)
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)
    ran = book.run(b)
    print("ran ok" if ran.ok else "REFUSED", *ran.lines, sep="\n  ")
    print("workbook:", b)


if __name__ == "__main__":
    main()
