"""The three-way comparison: tieout.py's independent figures, the audit workbook as LibreOffice calculates it, and the
main workbook's tabs as LibreOffice calculates them.

    python compare.py RUN_DIR INDEP_JSON OUT_JSON

RUN_DIR holds what make_scenario.py wrote: loans.csv, "loans - PocketBook.xlsx" and "loans - PocketBook -
audit.xlsx". This script reads the workbooks; it does not import pocketbook. It calculates them with
pocketbook/tests/recalc.py, which drives LibreOffice headless with "recalculate on load: always".

Tolerance: two figures tie when |a - b| <= 1e-9 x max(1, |b|). Counts must match exactly. The shuffle test is
compared within Monte Carlo error instead (see shuffle_rows).
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tests"))
from recalc import recalc  # noqa: E402  (LibreOffice headless; imports nothing from pocketbook)

sys.path.insert(0, str(HERE))
from tieout import bh  # noqa: E402  (the same Benjamini-Hochberg the independent side uses)

TOL = 1e-9
DEFAULT = ("494 - 652", "Broker")

#: One pocket's "Step" column -> the figure's name in tieout.json and on _pocketbook
STEPS = {
    "Loans": "loans", "Bad loans": "bad", "Loans with an outcome": "bad_n", "Bad loan rate": "bad_rate",
    "Booked, loans with a GCO": "gco_bk", "GCOs": "gco", "GCO rate": "gco_rate",
    "Booked, loans with a RANR": "ranr_bk", "RANR": "ranr", "RANR rate": "ranr_rate",
    "Booked, whole book": "book_gco_bk", "GCOs, whole book": "book_gco", "GCO rate, whole book": "book_rate",
    "Booked, rest of the book": "rest_gco_bk", "GCOs, rest of the book": "rest_gco",
    "GCO rate, rest of the book": "rest_rate", "× book": "x_book", "× rest of the book": "x_rest",
    "Gap in points": "gco_gap", "Dollars above share, against the book": "excess_rest",
    "RANR rate, rest of the book": "ranr_rest_rate", "RANR gap in points": "ranr_gap",
    "Booked, rest of its band": "band_gco_bk", "GCOs, rest of its band": "band_gco",
    "GCO rate, rest of its band": "band_rate", "× rest of its band": "x_band",
    "Dollars above share, against its band": "excess_band", "Dollars above share, as shown": "dollars",
    "Loans with a booked amount": "avg_n", "Booked, every loan with a booked amount": "avg_bk", "Avg line": "avg",
    "Avg line, whole book": "book_avg", "Line × book": "avg_x", "Loans with a loss": "events",
    "Shuffles with a gap as big, either way": "hits", "p-value": "raw",
    "p-value after the allowance for many tests": "p"}
SHUFFLE_KEYS = {"hits", "raw", "p"}


def ties(a, b) -> bool:
    if a is None or b is None or a == "" or b == "" or a == "none" or b == "none":
        return (a in (None, "", "none")) and (b in (None, "", "none"))
    return abs(float(a) - float(b)) <= TOL * max(1.0, abs(float(b)))


def rel(a, b):
    try:
        return abs(float(a) - float(b)) / max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return None


def one_pocket_table(ws) -> list[dict]:
    head = next(r for r in range(1, 40) if ws.cell(row=r, column=2).value == "Step")
    out = []
    for r in range(head + 1, ws.max_row + 1):
        step, tie = ws.cell(row=r, column=2).value, ws.cell(row=r, column=7).value
        if step in STEPS and tie is not None:
            out.append({"step": step, "key": STEPS[step], "words": ws.cell(row=r, column=3).value,
                        "written": ws.cell(row=r, column=4).value, "excel": ws.cell(row=r, column=5).value,
                        "pb": ws.cell(row=r, column=6).value, "ties": tie, "hand": ws.cell(row=r, column=8).value})
    return out


def picks(ws) -> dict:
    out = {}
    for row in ws.iter_rows(max_row=20, max_col=6):
        for c in row:
            if c.value in ("GRID", "BAND", "SEGMENT"):
                out[c.value] = f"{c.column_letter}{c.row + 1}"
    return out


def under_label(ws, label):
    for row in ws.iter_rows(max_row=80):
        for c in row:
            if c.value == label:
                return ws.cell(row=c.row + 1, column=c.column)
    raise KeyError(label)


def set_and_calc(path: Path, out: Path, sheet: str, values: dict):
    """A copy of a workbook with dropdowns set, as LibreOffice calculates it (as tests/tabs.py does)."""
    out.mkdir(parents=True, exist_ok=True)
    p = out / path.name
    wb = load_workbook(path)
    ws = wb[sheet]
    for label, v in values.items():
        if label in ("GRID", "BAND", "SEGMENT"):
            ws[picks(ws)[label]] = v
        else:
            under_label(ws, label).value = v
    wb.save(p)
    return recalc(p, out / "rc")


def main(run: Path, indep_path: Path, out_path: Path) -> None:
    ind = json.loads(indep_path.read_text())
    pockets = {(p["band"], p["seg"]): p for p in ind["pockets"]}
    audit = run / "loans - PocketBook - audit.xlsx"
    main_book = run / "loans - PocketBook.xlsx"
    work = run / "compare"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    res = {}

    # ---- the audit workbook, calculated as it opens (the default pocket)
    calc = recalc(audit, work / "audit-default")
    res["sheets_have_cross"] = {}
    for name in ("Rows in and out", "Bands", "One pocket", "Shuffle test"):
        crosses = sum(1 for row in calc[name].iter_rows() for c in row if c.value == "✗")
        ticks = sum(1 for row in calc[name].iter_rows() for c in row if isinstance(c.value, str)
                    and c.value.startswith("✓"))
        res["sheets_have_cross"][name] = {"ticks": ticks, "crosses": crosses}

    stamp = calc["Run stamp"]
    res["sha"] = {"indep": ind["sha256"], "audit": stamp["C5"].value}
    res["rows_read_stamp"] = stamp["C6"].value

    # Rows in and out
    ws = calc["Rows in and out"]
    rio = []
    for r in range(1, ws.max_row + 1):
        lab = ws.cell(row=r, column=2).value
        if isinstance(lab, str) and ws.cell(row=r, column=5).value in ("✓", "✗"):
            rio.append({"line": lab, "excel": ws.cell(row=r, column=3).value, "pb": ws.cell(row=r, column=4).value})
    R = ind["rows"]
    # the lines in the order the sheet lists them, each with the independent count
    seq = [R["rows_read"],
           R["bad_not01"], R["rows_read"] - R["bad_in"], R["bad_in"],
           R["gco_not_number"], R["gco_booked_blank"], R["rows_read"] - R["gco_in"], R["gco_in"],
           R["ranr_booked_blank"], R["rows_read"] - R["ranr_in"], R["ranr_in"],
           R["fico_blank"], R["fico_marked"]]
    assert len(seq) == len(rio), [x["line"] for x in rio]
    for x, v in zip(rio, seq):
        x["indep"] = v
        x["ok"] = x["indep"] == x["excel"] == x["pb"]
    res["rows_in_out"] = rio

    # Bands
    ws = calc["Bands"]
    bands = []
    for r in range(1, ws.max_row + 1):
        lab = ws.cell(row=r, column=2).value
        if ws.cell(row=r, column=7).value in ("✓", "✗") and lab in R["band_counts"]:
            bands.append({"band": lab, "from": ws.cell(row=r, column=3).value, "to": ws.cell(row=r, column=4).value,
                          "excel": ws.cell(row=r, column=5).value, "pb": ws.cell(row=r, column=6).value,
                          "indep": R["band_counts"][lab]})
        elif isinstance(lab, str) and lab.startswith("Loans whose band"):
            res["band_mismatch_cell"] = {"excel": ws.cell(row=r, column=5).value, "pb": ws.cell(row=r, column=6).value}
    for b in bands:
        b["ok"] = b["excel"] == b["pb"] == b["indep"]
    res["bands"] = bands

    # Loans: every loan's band, three ways
    ws = load_workbook(calc_path(work / "audit-default", audit), read_only=True, data_only=True)["Loans"]
    it = ws.iter_rows(values_only=True)
    head = list(next(it))
    ci, cp = head.index("FICO band"), head.index("FICO band, PocketBook's")
    mine = ind["bands"]
    n = diff_excel = diff_pb = diff_ep = 0
    for i, row in enumerate(it):
        if row[0] is None:
            continue
        e, p = row[ci], row[cp]
        diff_excel += e != mine[i]
        diff_pb += p != mine[i]
        diff_ep += e != p
        n += 1
    res["loan_bands"] = {"loans": n, "indep_vs_excel": diff_excel, "indep_vs_pb": diff_pb, "excel_vs_pb": diff_ep}

    # One pocket, the default
    res["default"] = {"rows": one_pocket_table(calc["One pocket"]), "pick": DEFAULT}
    for x in res["default"]["rows"]:
        x["indep"] = indep_value(pockets[DEFAULT], x["key"])

    # Shuffle test sheet
    ws = calc["Shuffle test"]
    sh = {}
    for r in range(50, 80):
        lab = ws.cell(row=r, column=2).value
        if lab in ("Real gap", "The line", "Shuffles that count", "Shuffles", "p-value") and r > 52:
            sh[lab] = {"excel": ws.cell(row=r, column=4).value, "pb": ws.cell(row=r, column=5).value}
        if lab == "Every shuffled gap for the default pocket (10,000)":
            first = r + 2
    draws = []
    for r in range(first, first + 10_000):
        draws.append(ws.cell(row=r, column=3).value)
    mine_sh = pockets[DEFAULT]["shuffle"]
    line = mine_sh["line"]
    nums = [d for d in draws if isinstance(d, (int, float))]
    sh["listed"] = len(draws)
    sh["listed_numbers"] = len(nums)
    sh["count_from_list_my_line"] = sum(1 for d in nums if not abs(d) < line) + (len(draws) - len(nums))
    sh["max_abs_listed"] = max(abs(d) for d in nums)
    sh["indep_gap"], sh["indep_line"] = mine_sh["gap"], line
    ex = {}
    for r in range(25, 51):
        lab = ws.cell(row=r, column=2).value
        if lab in ("Real gap", "Count", "p-value"):
            ex[lab] = {"excel": ws.cell(row=r, column=4).value, "pb": ws.cell(row=r, column=5).value,
                       "ties": ws.cell(row=r, column=6).value}
    ex_ties = [ws.cell(row=r, column=11).value for r in range(28, 48)]
    sh["example"] = ex
    sh["example_rows_tied"] = sum(1 for t in ex_ties if t == "✓")
    z = {}
    for r in range(66, 76):
        lab = ws.cell(row=r, column=2).value
        if lab in ("z", "Two-sided p-value"):
            z[lab] = {"excel": ws.cell(row=r, column=4).value, "pb": ws.cell(row=r, column=5).value}
    z["z"]["indep"], z["Two-sided p-value"]["indep"] = pockets[DEFAULT]["z"], pockets[DEFAULT]["z_p"]
    sh["z"] = z
    res["shuffle_sheet"] = sh

    # ---- _pocketbook: PocketBook's stored figures for every pocket, as written
    wsr = load_workbook(audit, read_only=True)["_pocketbook"]
    rows = list(wsr.iter_rows(values_only=True))
    heads = rows[0]
    stored = {(r[2], r[3]): dict(zip(heads, r)) for r in rows[1:]}
    sweep_keys = ["loans", "bad", "bad_n", "bad_rate", "gco_bk", "gco", "gco_rate", "ranr_bk", "ranr", "ranr_rate",
                  "book_gco_bk", "book_gco", "book_rate", "rest_gco_bk", "rest_gco", "rest_rate", "x_book", "x_rest",
                  "gco_gap", "excess_rest", "ranr_rest_rate", "ranr_gap", "band_gco_bk", "band_gco", "band_rate",
                  "x_band", "excess_band", "by_band", "dollars", "avg_n", "avg_bk", "avg", "book_avg", "avg_x",
                  "events", "z", "z_p"]
    sweep = []
    for k, pb in stored.items():
        mine_p = pockets.get(k)
        bad = []
        worst = 0.0
        for key in sweep_keys:
            a, b = indep_value(mine_p, key) if mine_p else None, pb.get(key)
            if key == "by_band":
                okk = bool(a) == bool(b)
            elif key in ("z", "z_p"):
                okk = (a is None and b == "none") or (a is not None and b != "none" and
                                                        abs(a - b) <= 1e-9 * max(1e-300, abs(b)) + 1e-12)
            else:
                okk = ties(a, b)
                d = rel(a, b)
                if d is not None and d > worst:
                    worst = d
            if not okk:
                bad.append((key, a, b))
        sweep.append({"band": k[0], "seg": k[1], "figures": len(sweep_keys), "bad": bad, "worst_rel": worst,
                      "loans": pb["loans"], "gco_rate": pb["gco_rate"], "x_band": pb["x_band"],
                      "dollars": pb["dollars"]})
    res["sweep"] = sweep
    res["sweep_pockets_indep"] = len(pockets)

    # shuffle test, every tested pocket: independent p against PocketBook's, within Monte Carlo error
    B = ind["shuffles"]
    shr = []
    for k, pb in stored.items():
        mine_p = pockets.get(k, {}).get("shuffle")
        if not isinstance(pb["raw_band"], float) or mine_p is None:
            continue
        p1, p2 = pb["raw_band"], mine_p["p"]
        pbar = (p1 + p2) / 2
        se = math.sqrt(2 * pbar * (1 - pbar) / B)
        shr.append({"band": k[0], "seg": k[1], "pb_hits": pb["hits_band"], "pb_p": p1, "indep_hits": mine_p["hits"],
                    "indep_p": p2, "se_diff": se, "z": (p2 - p1) / se if se else 0.0,
                    "pb_adj": pb["adj_band"], "indep_adj": mine_p["p_adj"], "gap_pb": None})
    # Benjamini-Hochberg on PocketBook's own raw p-values, against PocketBook's adjusted ones: exact
    raw = {(x["band"], x["seg"]): x["pb_p"] for x in shr}
    adj = bh(raw)
    for x in shr:
        x["bh_of_pb_raw"] = adj[(x["band"], x["seg"])]
        x["bh_exact"] = abs(x["bh_of_pb_raw"] - x["pb_adj"]) <= 1e-15
    res["shuffle_all"] = shr

    # ---- two more pockets, and one edge case, picked on the audit's dropdowns and recalculated
    others = {}
    for band, seg, tag in (("686 - 712", "Online", "p2"), ("713 - 745", "Online", "p3"),
                           ("(marked missing)", "Broker", "p4"), ("(blank)", "Broker", "p5")):
        c = set_and_calc(audit, work / tag, "One pocket", {"GRID": "FICO x CHANNEL", "BAND": band, "SEGMENT": seg})
        t = one_pocket_table(c["One pocket"])
        for x in t:
            x["indep"] = indep_value(pockets[(band, seg)], x["key"])
        others[f"{band}|{seg}"] = t
    res["others"] = others

    # ---- the main workbook, as an analyst reads it
    mainc = {}
    pk = set_and_calc(main_book, work / "main-pockets", "Pockets", {"MEASURE": "GCOs ($)"})["Pockets"]
    hr = next(r for r in range(1, 60) if pk.cell(row=r, column=2).value == "#")
    heads = {pk.cell(row=hr, column=c).value: c for c in range(1, 22)}
    for r in range(hr + 1, pk.max_row + 1):
        if pk.cell(row=r, column=3).value == f"FICO {DEFAULT[0]}" and pk.cell(row=r, column=4).value == DEFAULT[1]:
            mainc["Pockets"] = {h: pk.cell(row=r, column=c).value for h, c in heads.items() if h}
            mainc["Pockets_row"] = r
    rg = calc_main(main_book, work)["RANR vs GCOs"]
    hr = next(r for r in range(1, 60) if rg.cell(row=r, column=2).value == "Band")
    cols = [rg.cell(row=hr, column=c).value for c in range(1, 21)]
    for r in range(hr + 1, rg.max_row + 1):
        if rg.cell(row=r, column=2).value == DEFAULT[0] and rg.cell(row=r, column=3).value == DEFAULT[1]:
            mainc["RANR vs GCOs"] = [(cols[c - 1], rg.cell(row=r, column=c).value) for c in range(4, 21)]
            mainc["RANR_row"] = r
        if rg.cell(row=r, column=2).value == "Whole book":
            mainc["RANR whole book"] = [(cols[c - 1], rg.cell(row=r, column=c).value) for c in range(4, 11)]
    gr = set_and_calc(main_book, work / "main-grids", "Grids", {"MEASURE": "GCOs ($)"})["Grids"]
    blocks = [r for r in range(1, gr.max_row + 1)
              if gr.cell(row=r, column=2).value == "FICO" and gr.cell(row=r, column=3).value == "Branch"]
    segcol = next(c for c in range(3, 8) if gr.cell(row=blocks[0], column=c).value == DEFAULT[1])
    g = {}
    for name, top in zip(("rate", "vs the book", "vs rest of band", "loans"), blocks):
        title = gr.cell(row=top - 1, column=2).value
        for r in range(top + 1, top + 12):
            if gr.cell(row=r, column=2).value == DEFAULT[0]:
                g[name] = {"title": title, "value": gr.cell(row=r, column=segcol).value}
    mainc["Grids"] = g
    res["main"] = mainc
    # every main-workbook figure for the default pocket, against the independent figure
    d = pockets[DEFAULT]
    bk = ind["book"]
    P = mainc["Pockets"]
    RG = mainc["RANR vs GCOs"]
    RB = dict(mainc["RANR whole book"])
    G = mainc["Grids"]
    rows = [
        ("Pockets", "Loans", d["loans"], P["Loans"]),
        ("Pockets", "This pocket", d["gco_rate"], P["This pocket"]),
        ("Pockets", "Rest of band", d["band_rate"], P["Rest of band"]),
        ("Pockets", "× rest of band", d["x_band"], P["× rest of band"]),
        ("Pockets", "Dollars above share", d["dollars"], P["Dollars above share"]),
        ("Pockets", "p-value", d["shuffle"]["p_adj"], P["p-value"]),
        ("Pockets", "Worse?", d["worse"], P["Worse?"]),
        ("Pockets", "Material?", d["material"], P["Material?"]),
    ]
    rg_map = ["loans", "ranr_bk", "gco", "ranr", "ranr_rate", "avg", "avg_x", "both_band_gap",
              "both_band_dollars", "both_band_rate", "x_band", "excess_band", "band_rate", "ranr_band_gap",
              "ranr_band_dollars", "ranr_band_rate"]
    group = ["", "", "", "", "", "", "", "RANR + GCOs ", "RANR + GCOs ", "RANR + GCOs ", "GCOs ", "GCOs ", "GCOs ",
             "RANR ", "RANR ", "RANR "]
    for (col, v), key, g in zip(RG, rg_map, group):
        rows.append(("RANR vs GCOs", g + col, d[key], v))
    rows += [
        ("RANR vs GCOs", "Whole book: Loans", bk["loans"], RB["Loans"]),
        ("RANR vs GCOs", "Whole book: Booked", bk["booked_all"], RB["Booked"]),
        ("RANR vs GCOs", "Whole book: GCOs", bk["gco"], RB["GCOs"]),
        ("RANR vs GCOs", "Whole book: RANR", bk["ranr"], RB["RANR"]),
        ("RANR vs GCOs", "Whole book: RANR ÷ Booked", bk["ranr"] / bk["ranr_bk"], RB["RANR ÷ Booked"]),
        ("RANR vs GCOs", "Whole book: Avg line", d["book_avg"], RB["Avg line"]),
        ("Grids", "Rate · GCOs ÷ Booked", d["gco_rate"], G["rate"]["value"]),
        ("Grids", "vs the book", d["x_book"], G["vs the book"]["value"]),
        ("Grids", "vs rest of band", d["x_band"], G["vs rest of band"]["value"]),
        ("Grids", "Loans", d["loans"], G["loans"]["value"]),
    ]
    out = []
    for tab, col, a, b in rows:
        if isinstance(a, str) or isinstance(b, str):
            ok = a == b
        elif col == "p-value":
            ok = None                     # a shuffle p-value: compared within Monte Carlo error, below
        else:
            ok = ties(a, b)
        out.append({"tab": tab, "col": col, "indep": a, "main": b, "ok": ok})
    res["main_rows"] = out
    out_path.write_text(json.dumps(res, default=str, indent=1))
    print("written", out_path)


_main_calc = {}


def calc_main(path: Path, work: Path):
    if "wb" not in _main_calc:
        _main_calc["wb"] = recalc(path, work / "main-default")
    return _main_calc["wb"]


def calc_path(d: Path, audit: Path) -> Path:
    hits = list(d.glob("*.xlsx"))
    return hits[0]


def indep_value(p, key):
    if p is None:
        return None
    if key in ("hits", "raw", "p"):
        s = p.get("shuffle")
        if not s:
            return None
        return {"hits": s["hits"], "raw": s["p"], "p": s["p_adj"]}[key]
    return p.get(key)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
