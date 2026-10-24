"""Road 2: the same figures from the loan file, importing nothing from PocketBook (the csv and math modules only).

From Road 1 it takes only what the analyst reads off the tab to know where a loan goes and which pockets are
listed: the grid names, each band's label ("496 - 652", both ends in the band) and the list of pockets shown.
Every number is worked out here from Kiosk book.csv. Writes work/road2.csv.

The reading rules, as a person would apply them to the file:
- a loan counts towards RANR, and its booked amount towards Booked, when both ORIG_BAL and RANR_AMT read as numbers;
- a loan counts towards GCO when GCO_AMT and ORIG_BAL read as numbers ("#N/A" and a blank don't);
- Loans counts every loan in the pocket; RANR rate is RANR / Booked;
- a FICO of -9999 (below -1000) is "(marked missing)", a blank FICO "(blank)";
- RANR and RANR rate are red when RANR is below zero; Booked and GCO are never red;
- the line beside the Grid dropdown counts the pockets listed whose RANR is below zero, and adds up what they lost.
"""
import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"


def num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def band_of(fico, labels):
    if fico in ("", None):
        return "(blank)"
    v = float(fico)
    if v < -1000:
        return "(marked missing)"
    for lab in labels:
        lo, _, hi = lab.partition(" - ")
        if hi and float(lo) <= v <= float(hi):
            return lab
    raise KeyError(fico)


def sums(loans):
    booked = math.fsum(num(r["ORIG_BAL"]) for r in loans if num(r["ORIG_BAL"]) is not None
                       and num(r["RANR_AMT"]) is not None)
    ranr = math.fsum(num(r["RANR_AMT"]) for r in loans if num(r["ORIG_BAL"]) is not None
                     and num(r["RANR_AMT"]) is not None)
    gco = math.fsum(num(r["GCO_AMT"]) for r in loans if num(r["ORIG_BAL"]) is not None
                    and num(r["GCO_AMT"]) is not None)
    return {"loans": len(loans), "booked": booked, "gco": gco, "ranr": ranr,
            "ranr_rate": ranr / booked if booked else None}


def line(neg):
    if not neg:
        return "No pocket listed lost money outright: every one's RANR is zero or more."
    n, lost = len(neg), -math.fsum(neg)
    return f"{n} pocket{'s' if n != 1 else ''} lost money outright, totalling ${lost:,.0f}: RANR below zero, in red."


def main() -> None:
    loans = list(csv.DictReader((HERE / "Kiosk book.csv").open(encoding="utf-8")))
    road1 = list(csv.DictReader((WORK / "road1.csv").open(encoding="utf-8")))
    grids = list(dict.fromkeys(r["grid"] for r in road1))
    out = []
    for grid in grids:
        seg_col = grid.split(" x ")[1]
        listed = list(dict.fromkeys((r["band"], r["segment"]) for r in road1 if r["grid"] == grid
                                    and r["kind"] == "pocket"))
        labels = {b for b, _ in listed if " - " in b}
        cells: dict = {}
        for r in loans:
            cells.setdefault((band_of(r["FICO"], labels), r[seg_col]), []).append(r)
        for key in listed:
            s = sums(cells.get(key, []))
            for k, v in s.items():
                out.append((grid, "pocket", *key, k, v))
            neg = s["ranr"] < 0
            out += [(grid, "pocket", *key, "ranr red", neg), (grid, "pocket", *key, "ranr_rate red", neg),
                    (grid, "pocket", *key, "booked red", False), (grid, "pocket", *key, "gco red", False)]
        negs = [sums(cells.get(k, []))["ranr"] for k in listed]
        negs = [v for v in negs if v < 0]
        out += [(grid, "line", "", "", "count line", line(negs)), (grid, "line", "", "", "count line red",
                                                                  bool(negs))]
        shown = [r for k in listed for r in cells.get(k, [])]
        rest = [r for k, v in cells.items() if k not in listed for r in v]
        totals = [("Pockets listed", sums(shown))] + ([("Not listed", sums(rest))] if rest else []) + \
                 [("Whole book", sums(loans))]
        for label, s in totals:
            for k, v in s.items():
                out.append((grid, "total", label, "", k, v))
            neg = s["ranr"] < 0
            out += [(grid, "total", label, "", "ranr red", neg), (grid, "total", label, "", "ranr_rate red", neg),
                    (grid, "total", label, "", "booked red", False), (grid, "total", label, "", "gco red", False)]
    with (WORK / "road2.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["grid", "kind", "band", "segment", "figure", "value"])
        w.writerows(out)
    print(f"{len(grids)} grids, {len(out)} figures worked out -> {WORK / 'road2.csv'}")


if __name__ == "__main__":
    main()
