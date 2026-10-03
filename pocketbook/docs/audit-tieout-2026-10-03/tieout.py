"""Independent recomputation of PocketBook's bleed-test figures, from the loan file's text alone.

This script imports nothing from PocketBook and reads none of its workbooks. It uses the Python standard library
only: csv, decimal and fractions for the arithmetic, hashlib for the file fingerprint, random for the shuffle test,
plus json, math and sys for input and output.

    python tieout.py LOANS_CSV OUT_JSON [--shuffles 10000] [--seed 20261003]

What it takes as given (the Run's settings, as the audit workbook's Run stamp lists them; they are inputs, not
figures, so they are typed here rather than read):

    columns        LOAN_NBR (loan), ORIG_BAL (booked), GCO_AMT (GCO), RANR_AMT (RANR), BAD_FLAG (bad = 1),
                   FICO (band column), CHANNEL (segment column)
    band edges     653, 686, 713, 746 (a loan is in the band whose lower edge it is at or above)
    missing rule   FICO = -9999 is "marked missing"
    comparison     each pocket is judged against the rest of its band; a pocket alone in its band against the book
    fewest losses  10 (a pocket with fewer loans with a non-zero GCO is not shuffled)
    the audit's    seeded from SHA-256 over the text "origination-cube shuffle test, 25 Sep 2026", the text "the
    random pick    audit workbook's pocket, selected at random" and the file's SHA-256 hex, joined by the unit
                   separator (0x1F); the first 8 bytes read as a little-endian integer. The tested pockets, keyed
                   "FICO x CHANNEL|band|segment" and sorted as text, numbered from 0; the pick is seed mod their
                   number (as the Run stamp sheet states it)
    allowance      Benjamini-Hochberg, across the grid's tested pockets
    shuffles       10,000

Everything else is computed here. Dollar sums are exact (Decimal read from the text, summed as Fractions); rates and
multiples are exact Fractions until they are written out as floats. The shuffle test uses floats, as any
implementation must, and its own random-number stream, not PocketBook's seed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import sys
from decimal import Decimal, InvalidOperation
from fractions import Fraction

EDGES = (653, 686, 713, 746)
GRID = "FICO x CHANNEL"
PICK_BASE = "origination-cube shuffle test, 25 Sep 2026"
PICK_NAME = "the audit workbook's pocket, selected at random"
MISSING_FICO = Decimal("-9999")
MIN_EVENTS = 10
TIE = 1e-9

BLANK, NOT_NUMBER, MARKED = "(blank)", "(not a number)", "(marked missing)"


def number(text: str):
    """A cell as a number, or the reason it has none."""
    t = text.strip()
    if t == "":
        return BLANK
    try:
        d = Decimal(t)
    except InvalidOperation:
        return NOT_NUMBER
    if not d.is_finite():
        return NOT_NUMBER
    return d


def is_num(v) -> bool:
    return isinstance(v, Decimal)


def band_labels(values: list[Decimal]) -> list[str]:
    """Each band's name: from its lower edge (the lowest score seen, for the first) to one below the next edge (the
    highest score seen, for the last). Every score in this file is a whole number."""
    lows = [min(values)] + [Decimal(e) for e in EDGES]
    highs = [Decimal(e - 1) for e in EDGES] + [max(values)]
    return [f"{int(lo)} - {int(hi)}" for lo, hi in zip(lows, highs)]


def band_of(v, labels) -> str:
    if not is_num(v):
        return v
    for i, e in enumerate(EDGES):
        if v < e:
            return labels[i]
    return labels[-1]


def ratio(a, b):
    return Fraction(a) / Fraction(b) if b else None


def fl(x):
    return None if x is None else float(x)


def load(path: str):
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    loans = []
    for r in rows:
        fico = number(r["FICO"])
        if is_num(fico) and fico == MISSING_FICO:
            fico = MARKED
        bad = number(r["BAD_FLAG"])
        if is_num(bad) and bad not in (0, 1):
            bad = "(not 0 or 1)"
        loans.append({"booked": number(r["ORIG_BAL"]), "gco": number(r["GCO_AMT"]), "ranr": number(r["RANR_AMT"]),
                      "bad": bad, "fico": fico, "seg": r["CHANNEL"].strip() or BLANK})
    labels = band_labels([x["fico"] for x in loans if is_num(x["fico"])])
    for x in loans:
        x["band"] = band_of(x["fico"], labels)
    return sha, loans, labels


def totals(rows):
    """Every sum a pocket's figures are built from, for one set of loans."""
    t = {"loans": len(rows), "bad": 0, "bad_n": 0, "gco_bk": Fraction(0), "gco": Fraction(0), "gco_n": 0,
         "ranr_bk": Fraction(0), "ranr": Fraction(0), "both_bk": Fraction(0), "both": Fraction(0),
         "avg_n": 0, "avg_bk": Fraction(0), "events": 0}
    for x in rows:
        b, g, r = x["booked"], x["gco"], x["ranr"]
        if is_num(x["bad"]):
            t["bad_n"] += 1
            t["bad"] += int(x["bad"])
        if is_num(b):
            t["avg_n"] += 1
            t["avg_bk"] += Fraction(b)
            if is_num(g):
                t["gco_bk"] += Fraction(b)
                t["gco"] += Fraction(g)
                t["gco_n"] += 1
                if g != 0:
                    t["events"] += 1
            if is_num(r):
                t["ranr_bk"] += Fraction(b)
                t["ranr"] += Fraction(r)
            if is_num(g) and is_num(r):
                t["both_bk"] += Fraction(b)
                t["both"] += Fraction(g) + Fraction(r)
    return t


def figures(P, B, BD):
    """One pocket's figures. P: the pocket's sums; B: the whole book's; BD: the pocket's band's (None if the
    pocket is alone in its band, which is then judged against the book)."""
    f = {}
    f["loans"], f["bad"], f["bad_n"] = P["loans"], P["bad"], P["bad_n"]
    f["bad_rate"] = ratio(P["bad"], P["bad_n"])
    f["gco_bk"], f["gco"] = P["gco_bk"], P["gco"]
    f["gco_rate"] = ratio(P["gco"], P["gco_bk"])
    f["ranr_bk"], f["ranr"] = P["ranr_bk"], P["ranr"]
    f["ranr_rate"] = ratio(P["ranr"], P["ranr_bk"])
    f["book_gco_bk"], f["book_gco"] = B["gco_bk"], B["gco"]
    f["book_rate"] = ratio(B["gco"], B["gco_bk"])
    f["rest_gco_bk"], f["rest_gco"] = B["gco_bk"] - P["gco_bk"], B["gco"] - P["gco"]
    f["rest_rate"] = ratio(f["rest_gco"], f["rest_gco_bk"])
    f["x_book"] = f["gco_rate"] / f["book_rate"] if f["gco_rate"] is not None and f["book_rate"] else None
    f["x_rest"] = f["gco_rate"] / f["rest_rate"] if f["gco_rate"] is not None and f["rest_rate"] else None
    f["gco_gap"] = (f["gco_rate"] - f["rest_rate"]) * 100 if None not in (f["gco_rate"], f["rest_rate"]) else None
    f["excess_rest"] = P["gco"] - f["rest_rate"] * P["gco_bk"] if f["rest_rate"] is not None else None
    f["ranr_rest_rate"] = ratio(B["ranr"] - P["ranr"], B["ranr_bk"] - P["ranr_bk"])
    f["ranr_gap"] = ((f["ranr_rate"] - f["ranr_rest_rate"]) * 100
                     if None not in (f["ranr_rate"], f["ranr_rest_rate"]) else None)
    by_band = BD is not None and BD["gco_bk"] - P["gco_bk"] != 0
    if BD is not None:
        # what a reviewer gets by following the "By hand" note for this line literally: every booked dollar in the
        # band (In this band = 1, booked column summed), less the pocket's booked in the GCO rate
        f["band_bk_by_hand"] = BD["avg_bk"] - P["gco_bk"]
        f["band_gco_bk"], f["band_gco"] = BD["gco_bk"] - P["gco_bk"], BD["gco"] - P["gco"]
        f["band_rate"] = ratio(f["band_gco"], f["band_gco_bk"])
        f["x_band"] = f["gco_rate"] / f["band_rate"] if f["gco_rate"] is not None and f["band_rate"] else None
        f["excess_band"] = P["gco"] - f["band_rate"] * P["gco_bk"] if f["band_rate"] is not None else None
        # what the main workbook's RANR vs GCOs tab shows against the rest of the band
        f["ranr_band_rate"] = ratio(BD["ranr"] - P["ranr"], BD["ranr_bk"] - P["ranr_bk"])
        f["ranr_band_gap"] = ((f["ranr_rate"] - f["ranr_band_rate"]) * 100
                              if None not in (f["ranr_rate"], f["ranr_band_rate"]) else None)
        f["ranr_band_dollars"] = (f["ranr_rate"] - f["ranr_band_rate"]) * P["ranr_bk"] if f["ranr_band_gap"] is not None else None
        f["both_rate"] = ratio(P["both"], P["both_bk"])
        f["both_band_rate"] = ratio(BD["both"] - P["both"], BD["both_bk"] - P["both_bk"])
        f["both_band_gap"] = ((f["both_rate"] - f["both_band_rate"]) * 100
                              if None not in (f["both_rate"], f["both_band_rate"]) else None)
        f["both_band_dollars"] = (f["both_rate"] - f["both_band_rate"]) * P["both_bk"] if f["both_band_gap"] is not None else None
        # the rows added after the tie-out (3 Oct 2026), under the audit workbook's own names
        f["band_ranr_bk"], f["band_ranr"] = BD["ranr_bk"] - P["ranr_bk"], BD["ranr"] - P["ranr"]
        f["band_ranr_rate"], f["ranr_gap_band"] = f["ranr_band_rate"], f["ranr_band_gap"]
        f["ranr_usd_band"] = (P["ranr"] - f["ranr_band_rate"] * P["ranr_bk"]
                              if f["ranr_band_rate"] is not None else None)
        f["band_ctb_bk"], f["band_ctb"] = BD["both_bk"] - P["both_bk"], BD["both"] - P["both"]
        f["band_ctb_rate"], f["ctb_gap_band"] = f["both_band_rate"], f["both_band_gap"]
        f["ctb_usd_band"] = (P["both"] - f["both_band_rate"] * P["both_bk"]
                             if f["both_band_rate"] is not None else None)
    f["ctb_bk"], f["ctb"] = P["both_bk"], P["both"]
    f["ctb_rate"] = ratio(P["both"], P["both_bk"])
    f["book_all_bk"], f["book_nogco_bk"] = B["avg_bk"], B["avg_bk"] - B["gco_bk"]
    f["book_ranr_bk"], f["book_ranr"] = B["ranr_bk"], B["ranr"]
    f["book_ctb_bk"], f["book_ctb"] = B["both_bk"], B["both"]
    f["ranr_usd_rest"] = (P["ranr"] - f["ranr_rest_rate"] * P["ranr_bk"]
                          if f["ranr_rest_rate"] is not None else None)
    f["ctb_rest_rate"] = ratio(B["both"] - P["both"], B["both_bk"] - P["both_bk"])
    f["ctb_gap"] = ((f["ctb_rate"] - f["ctb_rest_rate"]) * 100
                    if None not in (f["ctb_rate"], f["ctb_rest_rate"]) else None)
    f["ctb_usd_rest"] = (P["both"] - f["ctb_rest_rate"] * P["both_bk"]
                         if f["ctb_rest_rate"] is not None else None)
    f["by_band"] = by_band
    f["dollars"] = f.get("excess_band") if by_band else f["excess_rest"]
    f["avg_n"], f["avg_bk"] = P["avg_n"], P["avg_bk"]
    f["avg"] = ratio(P["avg_bk"], P["avg_n"])
    f["book_avg"] = ratio(B["avg_bk"], B["avg_n"])
    f["book_avg_every_loan"] = ratio(B["avg_bk"], B["loans"])     # "the same over every loan", read literally
    f["avg_x"] = f["avg"] / f["book_avg"] if f["avg"] is not None and f["book_avg"] else None
    f["events"] = P["events"]
    # the two-proportion z-test on bad loans, the audit's textbook cross-check
    x1, n1, x2, n2 = P["bad"], P["bad_n"], B["bad"] - P["bad"], B["bad_n"] - P["bad_n"]
    pp = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2)) if n1 and n2 else 0
    f["z"] = (x1 / n1 - x2 / n2) / se if se else None
    f["z_p"] = math.erfc(abs(f["z"]) / math.sqrt(2)) if f["z"] is not None else None
    return f


def shuffle_test(loans, keys, shuffles: int, seed: int):
    """The shuffle test on the GCO rate, each pocket against the rest of its band, from scratch.

    Within each band, only the loans in the GCO rate (a number in both ORIG_BAL and GCO_AMT) take part. The real gap
    g = pocket GCOs / pocket booked - rest-of-band GCOs / rest-of-band booked. Each shuffle deals the band's loans
    into a random order and gives each segment as many of them as it really has; a shuffled gap counts when it is
    at least as far from 0 as the real one, either way, less an allowance of 1e-9 times the larger of |g| and the
    band's sum of |GCO| over its booked; a shuffled gap that cannot be worked out counts too. p = (count + 1) /
    (shuffles + 1)."""
    rng = random.Random(seed)
    out = {}
    plan = []
    for band in sorted({k[0] for k in keys}):
        members = [x for x in loans if x["band"] == band and is_num(x["booked"]) and is_num(x["gco"])]
        z = [complex(float(x["gco"]), float(x["booked"])) for x in members]
        segs = sorted({x["seg"] for x in members})
        sizes = [sum(1 for x in members if x["seg"] == s) for s in segs]
        gy, gx = sum(c.real for c in z), sum(c.imag for c in z)
        ay = sum(abs(c.real) for c in z)
        tests = []
        a = 0
        for s, k in zip(segs, sizes):
            if (band, s) in keys and k < len(z):
                py = sum(float(x["gco"]) for x in members if x["seg"] == s)
                px = sum(float(x["booked"]) for x in members if x["seg"] == s)
                g = py / px - (gy - py) / (gx - px)
                thr = abs(g) - TIE * max(abs(g), abs(ay / gx))
                tests.append([s, a, a + k, g, thr, 0])
            a += k
        if tests:
            plan.append((band, z, gy, gx, tests))
    for _ in range(shuffles):
        for band, z, gy, gx, tests in plan:
            order = list(range(len(z)))
            rng.shuffle(order)
            for t in tests:
                s = sum(map(z.__getitem__, order[t[1]:t[2]]))
                try:
                    g = s.real / s.imag - (gy - s.real) / (gx - s.imag)
                    hit = not (abs(g) < t[4])
                except ZeroDivisionError:
                    hit = True
                t[5] += hit
    for band, z, gy, gx, tests in plan:
        for s, a, b, g, thr, hits in tests:
            out[(band, s)] = {"gap": g, "line": thr, "hits": hits, "p": (hits + 1) / (shuffles + 1)}
    return out


def bh(ps: dict) -> dict:
    """Benjamini-Hochberg step-up: sort the m p-values small to large; the i-th becomes p(i) x m / i, then each is
    replaced by the smallest such value at its own rank or above, capped at 1."""
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 1.0
    for rank in range(m, 0, -1):
        k, p = items[rank - 1]
        running = min(running, p * m / rank)
        out[k] = min(1.0, running)
    return out


def main(argv):
    src, dst = argv[0], argv[1]
    shuffles = int(argv[argv.index("--shuffles") + 1]) if "--shuffles" in argv else 10_000
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 20261003
    sha, loans, labels = load(src)
    B = totals(loans)
    keys = sorted({(x["band"], x["seg"]) for x in loans})
    pockets = {}
    for k in keys:
        rows = [x for x in loans if (x["band"], x["seg"]) == k]
        band_rows = [x for x in loans if x["band"] == k[0]]
        pockets[k] = figures(totals(rows), B, totals(band_rows))
    tested = [k for k in keys if pockets[k]["events"] >= MIN_EVENTS and pockets[k]["by_band"]]
    # the audit's random pick, from the tested pockets: every pocket with enough losses to test (each has a
    # comparison: the rest of its band, or for a pocket alone in its band the rest of the book)
    population = sorted(f"{GRID}|{k[0]}|{k[1]}" for k in keys if pockets[k]["events"] >= MIN_EVENTS)
    pseed = int.from_bytes(hashlib.sha256("\x1f".join((PICK_BASE, PICK_NAME, sha)).encode("utf-8")).digest()[:8],
                           "little")
    chosen = population[pseed % len(population)]
    pick = {"seed": pseed, "population": len(population), "index": pseed % len(population), "key": chosen,
            "band": chosen.split("|")[1], "seg": chosen.split("|")[2], "keys": population}
    shuf = shuffle_test(loans, set(tested), shuffles, seed) if shuffles else {}
    adj = bh({k: v["p"] for k, v in shuf.items()})
    for k, v in shuf.items():
        v["p_adj"] = adj[k]
    # the verdicts as the Pockets tab defines them: worse at 1.25 times the rest or more with an adjusted p-value
    # under 5%; material when the dollars above share reach 1% of the book's GCOs
    line = B["gco"] / 100
    for k, f in pockets.items():
        x = f["x_band"] if f["by_band"] else f["x_rest"]
        p = shuf[k]["p_adj"] if k in shuf else None
        big = x is not None and x >= Fraction(5, 4)
        f["worse"] = "Yes" if big and p is not None and p < 0.05 else "Not sure" if big and p is not None else "No"
        f["material"] = "Yes" if f["dollars"] is not None and f["dollars"] >= line else "No"

    def rows_lost(col, why):
        return sum(1 for x in loans if x[col] == why)
    rows_io = {
        "rows_read": len(loans),
        "bad_not01": rows_lost("bad", "(not 0 or 1)"), "bad_in": B["bad_n"],
        "gco_not_number": rows_lost("gco", NOT_NUMBER), "gco_booked_blank": rows_lost("booked", BLANK),
        "gco_in": B["gco_n"],
        "ranr_booked_blank": sum(1 for x in loans if x["booked"] == BLANK and is_num(x["ranr"])),
        "ranr_in": sum(1 for x in loans if is_num(x["booked"]) and is_num(x["ranr"])),
        "fico_blank": rows_lost("band", BLANK), "fico_marked": rows_lost("band", MARKED),
        "band_counts": {lab: sum(1 for x in loans if x["band"] == lab) for lab in labels + [BLANK, MARKED]},
    }

    def js(v):
        if isinstance(v, Fraction):
            return float(v)
        return v
    book = {"loans": B["loans"], "booked_all": B["avg_bk"], "booked_n": B["avg_n"], "gco_bk": B["gco_bk"],
            "gco": B["gco"], "ranr_bk": B["ranr_bk"], "ranr": B["ranr"],
            "ranr_all": sum(Fraction(x["ranr"]) for x in loans if is_num(x["ranr"])),
            "gco_all": sum(Fraction(x["gco"]) for x in loans if is_num(x["gco"])),
            "materiality": B["gco"] / 100}
    out = {"sha256": sha, "book": {a: js(b) for a, b in book.items()}, "labels": labels, "rows": rows_io, "bands": [x["band"] for x in loans],
           "pockets": [{"band": k[0], "seg": k[1], **{a: js(b) for a, b in f.items()},
                        **({"shuffle": shuf[k]} if k in shuf else {})} for k, f in pockets.items()],
           "shuffles": shuffles, "seed": seed, "pick": pick}
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"SHA-256 {sha}; {len(loans):,} loans; {len(keys)} pockets; {len(shuf)} shuffled; the audit's pick "
          f"{chosen}, number {pick['index']} of {pick['population']} (seed {pick['seed']})")


if __name__ == "__main__":
    main(sys.argv[1:])
