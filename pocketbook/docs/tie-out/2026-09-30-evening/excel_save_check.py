"""Change 5, on PocketBook's side (it uses PocketBook and its tests' helper freely): the dropdowns are kept after a
workbook is saved the way Excel saves it, and run again.

    python3 excel_save_check.py "Consumer book Q3 - PocketBook.xlsx" "../2026-09-28/Consumer book Q3.csv" WORK/excel

1. A copy of the Run's workbook, beside a copy of its loan file. Every dropdown is listed: its sheet, its cells and
   its list formula (openpyxl), and LibreOffice calculates the copy so each list's items can be read.
2. The copy is rewritten the way Excel saves it -- tests/test_firm_answers_2026_09_29.py's _as_excel_saves_it moves
   every dropdown whose list sits on another sheet into Excel's 2010 extension block -- and what openpyxl alone
   still sees is counted (the bug: it drops that block).
3. PocketBook runs the rewritten workbook again (book.run, 10,000 shuffles, as any Run). Then every dropdown is
   listed again, the copy calculated again, and each list's items read again.

Tied, per dropdown: the same sheet, the same cells, the same formula, and the same items in its list. And, as a
bonus, every number the Run writes on _views (every figure the result tabs show) the same before and after, since the
shuffles are seeded.
"""
import json
import shutil
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[2] / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(HERE.parents[2] / "tests"))

import os  # noqa: E402

import re  # noqa: E402

from openpyxl import load_workbook  # noqa: E402
from openpyxl.utils import range_boundaries  # noqa: E402

import recalc  # noqa: E402
from pocketbook import book, excel_lists  # noqa: E402
from test_firm_answers_2026_09_29 import _as_excel_saves_it  # noqa: E402

def lists(path, loader=load_workbook):
    wb = loader(path)
    return sorted((ws.title, str(d.sqref), (d.formula1 or "").lstrip("="), d.type or "", d.operator or "",
                   (d.formula2 or "").lstrip("="))
                  for ws in wb for d in ws.data_validations.dataValidation)


def items(calc, sheet, formula):
    """A list formula's items, read from the calculated workbook: a typed list, a range on any sheet, a name, or
    OFFSET(start, 0, 0, MAX(1, count), 1)."""
    f = formula.strip()
    if re.fullmatch(r"-?[\d.]+", f):
        return [f"a number rule: {f}"]          # not a list: a typed number's bound, compared as written
    if f.startswith('"'):
        return [s for s in f.strip('"').split(",")]
    m = re.fullmatch(r"OFFSET\(\$?([A-Z]+)\$?(\d+),0,0,MAX\(1,\$?([A-Z]+)\$?(\d+)\),1\)", f)
    if m:
        ws = calc[sheet]
        n = max(1, int(ws[f"{m.group(3)}{m.group(4)}"].value or 0))
        return [ws[f"{m.group(1)}{int(m.group(2)) + k}"].value for k in range(n)]
    if f in calc.defined_names:
        dests = list(calc.defined_names[f].destinations)
        if len(dests) == 1:
            sheet, f = dests[0][0], dests[0][1]
    m = re.fullmatch(r"(?:'?([^'!]+)'?!)?(\$?[A-Z]+\$?\d+(?::\$?[A-Z]+\$?\d+)?)", f)
    if m:
        ws = calc[m.group(1) or sheet]
        c0, r0, c1, r1 = range_boundaries(m.group(2).replace("$", ""))
        return [ws.cell(r, c).value for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
    return None


def views_numbers(calc):
    ws = calc["_views"]
    return {ws.cell(r, 1).value: [ws.cell(r, c).value for c in range(2, ws.max_column + 1)]
            for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value}


def main():
    book_in, csv_in, work = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["POCKETBOOK_MEMORY"] = str(work / "memory.yaml")

    x = work / csv_in.name
    b = work / book_in.name
    shutil.copy(csv_in, x)
    shutil.copy(book_in, b)


    before = lists(b)
    calc_b = load_workbook(recalc.recalc_file(b, work / "before"), data_only=True)
    items_b = {k: items(calc_b, k[0], k[2]) for k in before}
    views_b = views_numbers(calc_b)
    moved = _as_excel_saves_it(b)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        openpyxl_sees = len(lists(b))
    in_block = sum(len(v) for v in excel_lists.extended(b).values())
    ran = book.run(b, extract=x)
    print("ran", ran.ok, *ran.lines[:2], sep="\n  ")
    after = lists(b)
    calc_a = load_workbook(recalc.recalc_file(b, work / "after"), data_only=True)
    items_a = {k: items(calc_a, k[0], k[2]) for k in after}
    views_a = views_numbers(calc_a)
    out = {"before": len(before), "moved to Excel's block": moved, "openpyxl alone sees after the save": openpyxl_sees,
           "in Excel's block": in_block, "ran again": ran.ok, "after": len(after),
           "dropdowns": [{"sheet": k[0], "cells": k[1], "formula": k[2], "type": k[3], "operator": k[4],
                          "formula2": k[5], "items before": items_b[k],
                          "there after": k in set(after), "items after": items_a.get(k)} for k in before],
           "new after": [list(k) for k in after if k not in set(before)],
           "views rows": len(views_b), "views rows differing": sorted(
               k for k in set(views_b) | set(views_a) if views_b.get(k) != views_a.get(k) and not str(k).startswith("R|"))}
    (work / "dropdowns.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k not in ("dropdowns",)}, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
