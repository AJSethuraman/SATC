"""Change 7 of 30 Sep 2026, column widths: no figure, a fit. Every value a reader can see, on every visible tab of
every view, as LibreOffice displays it (its own number format: "23.02%", "2.90×", "under 0.01%", "$1,869,963"),
against the width of its column, by the survey's rule (docs/column-widths-survey-2026-09-29.md, "How to read a
width"): a width is about one character of Calibri 10 or Arial bold 9, so a cell needs its characters + 2, and a
left label with an indent + 3. And the Grids rule G1/G2/G5: the four blocks' data columns one width, both label
columns one width.

    python3 widths_check.py OUT.csv LABEL VIEWS-FOLDER [LABEL VIEWS-FOLDER ...]
    python3 widths_check.py OUT.csv LABEL:single WORKBOOK-AS-WRITTEN CALCULATED-WORKBOOK

A VIEWS-FOLDER is views.py's: set/ (as written: widths, merges, alignment, formulas) and calculated/ (LibreOffice's
values). Each calculated view is exported by LibreOffice to one CSV per sheet "as shown" (the survey's own method),
into VIEWS-FOLDER/shown/.

The rules applied, in order (none of them is PocketBook's code; each is Excel's or LibreOffice's display behaviour):
  - hidden sheets, hidden columns and hidden rows are not seen, so not checked;
  - a merged range is checked at its first cell against the widths of all its columns together;
  - a number never runs into its neighbour (it shows ####): it must fit its own width, characters + 2;
  - text that doesn't wrap runs on into empty neighbours (right of a left-aligned cell; both sides of a centred
    one), which is how a heading or a note is meant to sit; a neighbour holding a formula, even one showing
    nothing, stops it, as it does in Excel;
  - wrapped text must fit its row's height: its lines, broken at a space or after a hyphen as Excel does, at about
    1.3 x the font size in points a line.
Writes one row per (run, tab, column): TIED when everything shown in it fits, DIFFERS with the worst cell, both
lengths and the width; then the Grids blocks' widths.
"""
import csv
import json
import os
import math
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tests"))
import recalc  # noqa: E402  (only its path to soffice)

CSV_FILTER = 'csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,true,false,false,-1'
DEFAULT_WIDTH = 8.43


def export(files, outdir):
    """Every sheet of every file to CSV as shown, in three LibreOffice processes."""
    outdir.mkdir(parents=True, exist_ok=True)
    todo = [f for f in files if not (outdir / f"{Path(f).stem}-Start here.csv").exists()]
    procs = []
    for k in range(3):
        batch = todo[k::3]
        if not batch:
            continue
        prof = Path(tempfile.mkdtemp(prefix="tieout-csv-"))
        procs.append(subprocess.Popen([recalc.SOFFICE, f"-env:UserInstallation={prof.as_uri()}", "--headless",
                                       "--convert-to", CSV_FILTER, "--outdir", str(outdir), *batch],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for p in procs:
        p.wait(timeout=5000)


def pieces(text):
    """Excel's break points: after a space (the space goes) or after a hyphen (it stays)."""
    out, cur = [], ""
    for ch in text:
        if ch == " ":
            out.append((cur, True))
            cur = ""
        elif ch == "-":
            out.append((cur + "-", False))
            cur = ""
        else:
            cur += ch
    out.append((cur, False))
    return [(p, s) for p, s in out if p]


def lines_in(text, chars):
    chars = max(1, int(chars))
    total = 0
    for para in str(text).split("\n"):
        lines, cur = 0, 0
        for p, _ in pieces(para) or [("", False)]:
            add = len(p) + (1 if cur else 0)
            if cur and cur + add <= chars:
                cur += add
                continue
            lines += 1 + (max(len(p), 1) - 1) // chars
            cur = len(p) - (max(len(p), 1) - 1) // chars * chars
        total += max(lines, 1)
    return total


class Layout:
    """A sheet as written: its widths, hidden columns and rows, merges, alignments and which cells hold anything."""
    def __init__(self, ws):
        self.width, self.hid_c = {}, set()
        for d in ws.column_dimensions.values():
            lo, hi = d.min or 0, d.max or 0
            for c in range(lo, hi + 1):
                if d.width:
                    self.width[c] = d.width
                if d.hidden:
                    self.hid_c.add(c)
        self.hid_r = {r for r, d in ws.row_dimensions.items() if d.hidden}
        self.height = {r: d.height for r, d in ws.row_dimensions.items() if d.height}
        self.merge_first, self.merge_in = {}, set()
        for m in ws.merged_cells.ranges:
            self.merge_first[(m.min_row, m.min_col)] = (m.max_row, m.max_col)
            for r in range(m.min_row, m.max_row + 1):
                for c in range(m.min_col, m.max_col + 1):
                    if (r, c) != (m.min_row, m.min_col):
                        self.merge_in.add((r, c))
        self.filled = set()
        self.align, self.font = {}, {}
        for row in ws.iter_rows():
            for c in row:
                if c.value not in (None, ""):
                    self.filled.add((c.row, c.column))
                if c.has_style:
                    self.align[(c.row, c.column)] = (c.alignment.horizontal, bool(c.alignment.wrap_text),
                                                     c.alignment.indent or 0)
                    self.font[(c.row, c.column)] = (c.font.name or "Calibri", c.font.sz or 11)

    def w(self, c):
        return 0 if c in self.hid_c else self.width.get(c, DEFAULT_WIDTH)


def empty_run(L, shown, r, c, step):
    """The widths of the empty cells next to (r, c), one way, until a cell holds anything."""
    tot, k = 0.0, c + step
    while k >= 1 and k <= c + 60 * (1 if step > 0 else -1) and k >= c - 60:
        if (r, k) in L.filled or (r, k) in L.merge_in or (r, k) in L.merge_first or shown.get((r, k)):
            break
        tot += L.w(k)
        k += step
    return tot


def per_char(font):
    """Width units a character takes (the survey: Calibri 10 and Arial bold 9 both about 1 unit), scaled by size."""
    name, size = font
    return size / 9 if name.startswith("Arial") else size / 10


def kind_of(t, is_num):
    """What a cell shows: a number, prose (a sentence of six words or more), or a label or heading."""
    if is_num:
        return "value"
    return "prose" if t.count(" ") >= 6 else "label"


def check_sheet(L, rows, numeric, sheet, where, out):
    shown = {}
    for i, row in enumerate(rows, start=1):
        for j, t in enumerate(row, start=1):
            if t != "":
                shown[(i, j)] = t
    for (r, c), t in shown.items():
        if c in L.hid_c or r in L.hid_r or (r, c) in L.merge_in:
            continue
        if (r, c) not in L.filled and (r, c) not in L.merge_first:
            continue                     # LibreOffice shows nothing of its own there
        h, wrap, indent = L.align.get((r, c), (None, False, 0))
        merged = (r, c) in L.merge_first
        avail = sum(L.w(k) for k in range(c, L.merge_first[(r, c)][1] + 1)) if merged else L.w(c)
        pad = 3 if indent else 2
        pc = per_char(L.font.get((r, c), ("Calibri", 11)))
        is_num = (r, c) in numeric
        kind = kind_of(t, is_num)
        need = len(t) * pc + pad
        if wrap and not is_num:
            size = L.font.get((r, c), ("Calibri", 11))[1]
            r2 = L.merge_first.get((r, c), (r, c))[0]
            height = sum(L.height.get(k, 15) for k in range(r, r2 + 1))
            lines = lines_in(t, (avail - pad) / pc)
            ok = lines == 1 or lines * size * 1.3 <= height + 0.5
            kind = "wrapped " + kind
            why = (f"wraps to {lines} lines of {(avail - pad) / pc:.0f} characters; the row is {height:g} pt, "
                   f"{lines * size * 1.3:.0f} needed")
        else:
            room = avail
            if not is_num and not merged:        # a merged cell never runs past its merge; a number never runs on
                if h in (None, "general", "left"):
                    room += empty_run(L, shown, r, c, 1)
                elif h == "center":
                    room += 2 * min(empty_run(L, shown, r, c, 1), empty_run(L, shown, r, c, -1))
                elif h == "right":
                    room += empty_run(L, shown, r, c, -1)
            ok = need <= room + 1e-9
            if not ok and len(t) * pc <= room:
                kind += ", the padding only"
            why = (f"{len(t)} characters x {pc:.2g} + {pad} = {need:.1f} in {avail:g}"
                   + (f" (+{room - avail:g} empty beside it)" if room > avail else ""))
        key = (sheet, get_column_letter(c))
        out[key]["cells"] += 1
        if not ok:
            out[key]["bad"].append({"where": f"{sheet}!{get_column_letter(c)}{r} [{where}]", "text": t,
                                    "why": why, "number": is_num, "kind": kind})


def numeric_cells(ws):
    out = set()
    for i, row in enumerate(ws.iter_rows(min_row=1, min_col=1, values_only=True), start=1):
        for j, v in enumerate(row, start=1):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.add((i, j))
    return out


def grids_blocks(ws_set, L):
    """G1, G2, G5: the four blocks' data columns one width, the two label columns one width."""
    head = {}
    for row in ws_set.iter_rows(min_row=10, max_row=30):
        for c in row:
            if isinstance(c.value, str):
                if c.value.startswith('="Rate · "') or c.value.startswith("Rate ·"):
                    head.setdefault("rate", (c.row, c.column))
                elif "vs the book" in c.value:
                    head.setdefault("book", (c.row, c.column))
                elif c.value == "vs rest of band":
                    head.setdefault("band", (c.row, c.column))
                elif c.value == "Loans" and "band" in head and c.row == head["band"][0]:
                    head.setdefault("loans", (c.row, c.column))
    left, right = head["rate"][1], head["book"][1]
    nc = right - left - 2
    data = {c: L.w(c) for c in list(range(left + 1, left + nc + 1)) + list(range(right + 1, right + nc + 1))}
    return {"blocks": head, "left": left, "right": right, "segments": nc, "data widths": sorted(set(data.values())),
            "label widths": [L.w(left), L.w(right)], "gap": L.w(right - 1),
            "same data width": len(set(data.values())) == 1, "same label width": L.w(left) == L.w(right),
            "band/loans under rate/book": head["band"][1] == left and head["loans"][1] == right}


def main():
    out_csv = Path(sys.argv[1])
    args = sys.argv[2:]
    results, blocks = [], []
    while args:
        label, a = args[0], args[1]
        if label.endswith(":single"):
            label, calc = label[:-7], args[2]
            pairs = [(Path(a), Path(calc), label)]
            args = args[3:]
        else:
            d = Path(a)
            plan = json.loads((d / "plan.json").read_text())
            pairs = [(d / "set" / p["file"], d / "calculated" / p["file"], p["file"][:-5]) for p in plan][:int(os.environ.get("LIMIT", "100000"))]
            args = args[2:]
        shown_dir = pairs[0][1].parent.parent / f"shown-{label}"
        export([str(c) for _, c, _ in pairs], shown_dir)
        per = defaultdict(lambda: {"cells": 0, "bad": []})
        layouts = {}
        # widths, merges, alignments and formulas are the Run's, the same in every view (only the dropdowns'
        # answers differ, and they hold something either way): read once
        wb_set = load_workbook(pairs[0][0])
        sheets = [ws for ws in wb_set.worksheets if ws.sheet_state == "visible"]
        layouts = {ws.title: Layout(ws) for ws in sheets}
        for ws in sheets:
            if ws.title == "Grids":
                blocks.append({"run": label, **grids_blocks(ws, layouts["Grids"])})
        for set_f, calc_f, view in pairs:
            wb_val = load_workbook(calc_f, data_only=True, read_only=True)
            for ws in sheets:
                L = layouts[ws.title]
                f = shown_dir / f"{calc_f.stem}-{ws.title}.csv"
                if not f.exists():
                    per[(ws.title, "*")]["bad"].append({"where": f"{ws.title} [{view}]", "text": "",
                                                        "why": "no CSV", "number": False})
                    continue
                rows = list(csv.reader(open(f, newline="", encoding="utf-8")))
                check_sheet(L, rows, numeric_cells(wb_val[ws.title]), ws.title, view, per)
            wb_val.close()
        for (sheet, colname), v in sorted(per.items()):
            worst = max(v["bad"], key=lambda b: len(b["text"])) if v["bad"] else None
            results.append({"run": label, "tab": sheet, "column": colname, "cells checked": v["cells"],
                            "verdict": "DIFFERS" if v["bad"] else "TIED", "cells that don't fit": len(v["bad"]),
                            "what doesn't fit": "; ".join(sorted({b["kind"] for b in v["bad"]})),
                            "worst": "" if not worst else f'{worst["where"]}: "{worst["text"]}" -- {worst["why"]}',
                            "all": json.dumps(sorted({(b["text"], b["why"]) for b in v["bad"]})[:12])})
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    json.dump(blocks, open(out_csv.with_suffix(".blocks.json"), "w"), indent=1)
    tally = defaultdict(int)
    for r in results:
        tally[(r["run"], r["verdict"])] += 1
    print(dict(tally))
    for b in blocks:
        print(b["run"], "Grids blocks:", {k: b[k] for k in ("data widths", "label widths", "same data width",
                                                             "same label width", "band/loans under rate/book")})


if __name__ == "__main__":
    main()
