"""The re-run after the fixes (3 Oct 2026): tieout.py's independent figures against the fixed audit workbook and the
main workbook, both as LibreOffice calculates them, and each of the first run's findings checked again.

    python compare_rerun.py RUN_DIR INDEP_JSON OUT_JSON

compare.py, beside it, is the first run's reader and stays as it was: it reads the audit workbook as merged at
f20118b9 (the top flagged pocket, 37 rows). This one reads the workbook after the fixes: the pocket selected at
random, every gap RANR vs GCOs shows, each booked total named by its population, and part D of Shuffle test. It
imports nothing from pocketbook; it borrows compare.py's helpers (LibreOffice through tests/recalc.py, the
dropdowns, the tolerance) and tieout.py's Benjamini-Hochberg.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from compare import calc_main, picks, recalc, set_and_calc, ties  # noqa: E402
from tieout import bh  # noqa: E402

#: One pocket's Step column -> the figure's name in tieout.json (and on _pocketbook)
STEPS = {
    "Loans": "loans", "Bad loans": "bad", "Loans with an outcome": "bad_n", "Bad loan rate": "bad_rate",
    "Booked, loans with a GCO": "gco_bk", "GCOs": "gco", "GCO rate": "gco_rate",
    "Booked, loans with a RANR": "ranr_bk", "RANR": "ranr", "RANR rate": "ranr_rate",
    "Booked, loans with a GCO and a RANR": "ctb_bk", "RANR + GCOs": "ctb", "RANR + GCOs rate": "ctb_rate",
    "Booked, whole book, every loan with a booked amount": "book_all_bk",
    "Booked, whole book, loans with a GCO": "book_gco_bk", "Booked, whole book, loans with no GCO amount":
        "book_nogco_bk", "GCOs, whole book": "book_gco", "GCO rate, whole book": "book_rate",
    "Booked, whole book, loans with a RANR": "book_ranr_bk", "RANR, whole book": "book_ranr",
    "Booked, whole book, loans with a GCO and a RANR": "book_ctb_bk", "RANR + GCOs, whole book": "book_ctb",
    "Booked, rest of the book, loans with a GCO": "rest_gco_bk", "GCOs, rest of the book": "rest_gco",
    "GCO rate, rest of the book": "rest_rate", "× book": "x_book", "× rest of the book": "x_rest",
    "GCO gap in points, against the book": "gco_gap", "Dollars above share, against the book": "excess_rest",
    "RANR rate, rest of the book": "ranr_rest_rate", "RANR gap in points, against the book": "ranr_gap",
    "RANR dollars, against the book": "ranr_usd_rest", "RANR + GCOs rate, rest of the book": "ctb_rest_rate",
    "RANR + GCOs gap in points, against the book": "ctb_gap", "RANR + GCOs dollars, against the book":
        "ctb_usd_rest",
    "Booked, rest of its band, loans with a GCO": "band_gco_bk", "GCOs, rest of its band": "band_gco",
    "GCO rate, rest of its band": "band_rate", "× rest of its band": "x_band",
    "Dollars above share, against its band": "excess_band", "Dollars above share, as shown": "dollars",
    "Booked, rest of its band, loans with a RANR": "band_ranr_bk", "RANR, rest of its band": "band_ranr",
    "RANR rate, rest of its band": "band_ranr_rate", "RANR gap in points, against its band": "ranr_gap_band",
    "RANR dollars, against its band": "ranr_usd_band",
    "Booked, rest of its band, loans with a GCO and a RANR": "band_ctb_bk", "RANR + GCOs, rest of its band":
        "band_ctb", "RANR + GCOs rate, rest of its band": "band_ctb_rate",
    "RANR + GCOs gap in points, against its band": "ctb_gap_band",
    "RANR + GCOs dollars, against its band": "ctb_usd_band",
    "Loans with a booked amount": "avg_n", "Booked, every loan with a booked amount": "avg_bk", "Avg line": "avg",
    "Avg line, whole book": "book_avg", "Line × book": "avg_x", "Loans with a loss": "events",
    "Shuffles with a gap at least as large, in either direction": "hits", "p-value": "raw",
    "p-value after the allowance for many tests": "p"}
SHUFFLE_KEYS = {"hits", "raw", "p"}


def table(ws) -> list[dict]:
    """One pocket's figure rows (a row with a Ties? cell), each with the independent figure's name."""
    head = next(r for r in range(1, 40) if ws.cell(row=r, column=2).value == "Step")
    out = []
    for r in range(head + 1, ws.max_row + 1):
        step, tie = ws.cell(row=r, column=2).value, ws.cell(row=r, column=7).value
        if tie is None:
            continue
        out.append({"step": step, "key": STEPS.get(step), "words": ws.cell(row=r, column=3).value,
                    "written": ws.cell(row=r, column=4).value, "excel": ws.cell(row=r, column=5).value,
                    "pb": ws.cell(row=r, column=6).value, "ties": tie, "hand": ws.cell(row=r, column=8).value})
    return out


def indep(p: dict, key: str):
    if key in SHUFFLE_KEYS:
        s = p.get("shuffle")
        return None if not s else {"hits": s["hits"], "raw": s["p"], "p": s["p_adj"]}[key]
    return p.get(key)


def row_of(ws, label: str, col: int = 2, after: int = 0) -> int:
    for r in range(after + 1, ws.max_row + 1):
        if ws.cell(row=r, column=col).value == label:
            return r
    raise KeyError(label)


def three_way(rows: list[dict], p: dict, B: int) -> None:
    """Each row's verdict: the three agree within 1E-9 (counts exactly); a shuffle figure, within Monte Carlo
    error of the independent shuffles, and exactly between Excel and PocketBook."""
    for x in rows:
        x["indep"] = indep(p, x["key"]) if x["key"] else None
        if x["key"] is None:
            x["ok"] = False
        elif x["key"] in SHUFFLE_KEYS:
            if x["indep"] is None and x["excel"] in ("", None) and x["pb"] in ("", None, "none"):
                x["ok"] = True                   # not tested: no p-value on any side
                continue
            if x["excel"] in ("", None) or isinstance(x["excel"], str):
                x["ok"] = "listed" if x["key"] == "hits" else False
                continue
            a, b = x["indep"], x["pb"]
            if x["key"] == "hits":
                a, b = (a + 1) / (B + 1), (b + 1) / (B + 1)
            pbar = (a + b) / 2
            se = math.sqrt(2 * pbar * (1 - pbar) / B)
            x["ok"] = ("mc" if abs(a - b) <= 3 * se or a == b else False) if ties(x["excel"], x["pb"]) else False
        else:
            x["ok"] = ties(x["indep"], x["excel"]) and ties(x["indep"], x["pb"]) and ties(x["excel"], x["pb"])


def main(run: Path, indep_path: Path, out_path: Path) -> None:
    ind = json.loads(indep_path.read_text())
    pockets = {(p["band"], p["seg"]): p for p in ind["pockets"]}
    B = ind["shuffles"]
    audit = run / "loans - PocketBook - audit.xlsx"
    main_book = run / "loans - PocketBook.xlsx"
    work = run / "compare-rerun"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    res = {"sha": ind["sha256"]}
    calc = recalc(audit, work / "audit-default")
    res["sheets"] = {}
    for name in ("Rows in and out", "Bands", "One pocket", "Shuffle test"):
        ws = calc[name]
        res["sheets"][name] = {
            "ticks": sum(1 for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value[:1] == "✓"),
            "crosses": sum(1 for row in ws.iter_rows() for c in row if c.value == "✗")}

    # ---- finding 7 (new): the pocket the workbook opens on, drawn at random, and the independent draw
    one = calc["One pocket"]
    at = picks(one)
    picked = [one[at["GRID"]].value, one[at["BAND"]].value, one[at["SEGMENT"]].value]
    stamp = calc["Run stamp"]
    said = {stamp.cell(row=r, column=2).value: stamp.cell(row=r, column=3).value for r in range(1, stamp.max_row + 1)}
    P = ind["pick"]
    res["pick"] = {"indep": P, "audit": picked, "stamp_seed": said.get("Pick seed"),
                   "stamp_pocket": said.get("Pocket selected"), "stamp_population": said.get("Population drawn from"),
                   "stamp_sha": said.get("Its SHA-256 fingerprint"),
                   "one_pocket_top": one.cell(row=3, column=3).value}
    res["pick"]["ok"] = (picked == ["FICO x CHANNEL", P["band"], P["seg"]] and said.get("Pick seed") == str(P["seed"])
                         and str(said.get("Population drawn from", "")).startswith(f"{P['population']:,} pockets")
                         and said.get("Its SHA-256 fingerprint") == ind["sha256"]
                         and said.get("Pocket selected", "") in str(one.cell(row=3, column=3).value))
    key = (P["band"], P["seg"])
    d = pockets[key]

    # ---- One pocket, the random pocket: every row, three ways
    rows = table(one)
    three_way(rows, d, B)
    res["random"] = {"pocket": list(key), "rows": rows}

    # ---- Shuffle test, part B: the random pocket's listed shuffles
    sh = calc["Shuffle test"]
    b0 = next(r for r in range(1, sh.max_row + 1) if str(sh.cell(row=r, column=2).value).startswith("B. "))
    partb = {}
    for label in ("Actual gap", "The line", "Shuffles that count", "Shuffles", "p-value"):
        r = row_of(sh, label, after=b0)
        partb[label] = {"excel": sh.cell(row=r, column=4).value, "pb": sh.cell(row=r, column=5).value,
                        "ties": sh.cell(row=r, column=6).value}
    first = next(r for r in range(1, sh.max_row + 1)
                 if str(sh.cell(row=r, column=2).value).startswith("Every shuffled gap for the pocket")) + 2
    draws = [sh.cell(row=r, column=3).value for r in range(first, first + B)]
    nums = [x for x in draws if isinstance(x, (int, float))]
    line = d["shuffle"]["line"] if d.get("shuffle") else None
    partb["listed"] = len([x for x in draws if x is not None])
    partb["count_from_list_indep_line"] = (sum(1 for x in nums if not abs(x) < line) + len(draws) - len(nums)
                                           if line is not None else None)
    partb["indep"] = d.get("shuffle")
    res["partb"] = partb

    # ---- finding 5: part D, the allowance for many tests, from the visible table
    head = row_of(sh, "Pocket (band, segment)", col=3)
    D = []
    for r in range(head + 1, sh.max_row + 1):
        if not isinstance(sh.cell(row=r, column=2).value, int):
            break
        band, seg = sh.cell(row=r, column=3).value.rsplit(", ", 1)
        D.append({"band": band, "seg": seg, "count": sh.cell(row=r, column=4).value,
                  "p": sh.cell(row=r, column=5).value, "rank": sh.cell(row=r, column=6).value,
                  "term": sh.cell(row=r, column=7).value, "adj_excel": sh.cell(row=r, column=8).value,
                  "adj_pb": sh.cell(row=r, column=9).value, "ties": sh.cell(row=r, column=10).value,
                  "selected": sh.cell(row=r, column=11).value == "◀ selected pocket"})
    adj = bh({(x["band"], x["seg"]): x["p"] for x in D})
    for x in D:
        x["bh_of_listed_p"] = adj[(x["band"], x["seg"])]
        s = pockets[(x["band"], x["seg"])].get("shuffle")
        x["indep_hits"], x["indep_p"], x["indep_adj"] = (s["hits"], s["p"], s["p_adj"]) if s else (None,) * 3
        x["ok"] = (x["ties"] == "✓" and abs(x["adj_excel"] - x["bh_of_listed_p"]) <= 1e-12
                   and abs(x["adj_pb"] - x["bh_of_listed_p"]) <= 1e-12)
        pbar = (x["p"] + x["indep_p"]) / 2
        se = math.sqrt(2 * pbar * (1 - pbar) / B)
        x["mc"] = abs(x["p"] - x["indep_p"]) <= 3 * se or x["p"] == x["indep_p"]
    m_row = row_of(sh, "Pockets tested on this comparison")
    sel_row = row_of(sh, "The selected pocket's adjusted p-value")
    res["partd"] = {"rows": D, "tests": [sh.cell(row=m_row, column=c).value for c in (4, 5, 6)],
                    "selected": [sh.cell(row=sel_row, column=c).value for c in (4, 5, 6)],
                    "rule": sh.cell(row=head - 2, column=2).value}

    # ---- finding 1: "Booked, rest of its band" by hand, on the band holding the GCO of "#N/A" (713 - 745)
    f1 = {}
    for band, seg, tag in (("713 - 745", "Online", "p713"), ("(blank)", "Broker", "pblank")):
        c = set_and_calc(audit, work / tag, "One pocket", {"GRID": "FICO x CHANNEL", "BAND": band, "SEGMENT": seg})
        t = table(c["One pocket"])
        three_way(t, pockets[(band, seg)], B)
        f1[f"{band}|{seg}"] = t
    res["others"] = f1
    p713 = pockets[("713 - 745", "Online")]
    r = next(x for x in f1["713 - 745|Online"] if x["key"] == "band_gco_bk")
    res["finding1"] = {"hand": r["hand"], "excel": r["excel"], "indep_following_new_words": p713["band_gco_bk"],
                       "indep_following_old_words": p713["band_bk_by_hand"]}

    # ---- finding 2: Avg line, whole book
    r = next(x for x in rows if x["key"] == "book_avg")
    res["finding2"] = {"words": r["words"], "excel": r["excel"], "indep": d["book_avg"],
                       "every_loan_reading": d["book_avg_every_loan"]}

    # ---- findings 3 and 4: the main workbook's RANR vs GCOs row for the random pocket, and its whole book
    rg = calc_main(main_book, work)["RANR vs GCOs"]
    hr = next(r for r in range(1, 60) if rg.cell(row=r, column=2).value == "Band")
    main_row, whole = None, None
    for r in range(hr + 1, rg.max_row + 1):
        if rg.cell(row=r, column=2).value == key[0] and rg.cell(row=r, column=3).value == key[1]:
            main_row = [rg.cell(row=r, column=c).value for c in range(4, 20)]
        if rg.cell(row=r, column=2).value == "Whole book":
            whole = [rg.cell(row=r, column=c).value for c in range(4, 11)]
    by_band = d["by_band"]
    keys = ["loans", "ranr_bk", "gco", "ranr", "ranr_rate", "avg", "avg_x",
            "ctb_gap_band" if by_band else "ctb_gap", "ctb_usd_band" if by_band else "ctb_usd_rest",
            "band_ctb_rate" if by_band else "ctb_rest_rate", "x_band" if by_band else "x_rest",
            "excess_band" if by_band else "excess_rest", "band_rate" if by_band else "rest_rate",
            "ranr_gap_band" if by_band else "ranr_gap", "ranr_usd_band" if by_band else "ranr_usd_rest",
            "band_ranr_rate" if by_band else "ranr_rest_rate"]
    heads = ["Loans", "Booked", "GCOs", "RANR", "RANR ÷ Booked", "Avg line", "Line × book",
             "RANR + GCOs: Gap pts", "RANR + GCOs: Dollars", "RANR + GCOs: Rest", "GCOs: × rest", "GCOs: Dollars",
             "GCOs: Rest", "RANR: Gap pts", "RANR: Dollars", "RANR: Rest"]
    excel = {x["key"]: x["excel"] for x in rows}
    main_cmp = []
    for h, k, v in zip(heads, keys, main_row):
        a = d[k]
        main_cmp.append({"col": h, "key": k, "indep": a, "audit": excel.get(k), "main": v,
                         "audit_row": next((x["step"] for x in rows if x["key"] == k), None),
                         "ok": ties(a, v) and ties(excel.get(k), v)})
    res["main"] = main_cmp
    bk = ind["book"]
    res["whole_book"] = [
        {"what": "Booked", "main": whole[1], "audit_row": "Booked, whole book, loans with a RANR",
         "audit": excel["book_ranr_bk"], "indep": d["book_ranr_bk"]},
        {"what": "GCOs", "main": whole[2], "audit_row": "GCOs, whole book", "audit": excel["book_gco"],
         "indep": bk["gco"]},
        {"what": "RANR", "main": whole[3], "audit_row": "RANR, whole book", "audit": excel["book_ranr"],
         "indep": bk["ranr"]}]
    for x in res["whole_book"]:
        x["ok"] = ties(x["indep"], x["main"]) and ties(x["audit"], x["main"])
    res["booked_labels"] = [x["step"] for x in rows if x["step"].startswith("Booked")]
    res["finding4"] = {k: excel[k] for k in ("book_all_bk", "book_gco_bk", "book_nogco_bk", "book_ranr_bk",
                                             "book_ctb_bk")}
    res["finding4"]["indep_nogco"] = d["book_nogco_bk"]
    out_path.write_text(json.dumps(res, default=str, indent=1))
    print("written", out_path)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
