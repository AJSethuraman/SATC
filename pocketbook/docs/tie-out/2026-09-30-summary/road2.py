"""Road 2: every Summary figure worked out again from "Summary book.csv" alone, and set beside what PocketBook showed.
Imports nothing from PocketBook: the standard library only.

    cd pocketbook && python3 docs/tie-out/2026-09-30-summary/road2.py

What it takes as given, and why:
- the band labels, read off the tab ("496 - 653"). A label is a claim about which loans a band holds, so each loan is
  placed here by reading the label (a dollar value with its cents dropped, as the firm decided on 30 Sep 2026), and
  a loan that fits no label, or two, is reported;
- the analyst's one answer on Columns: FICO -9999 is Missing ("(marked missing)"). A blank is "(blank)", text that
  isn't a number is "(not a number)".
The definitions are the firm's (30 Sep 2026) and the engine's measures as the README states them: bad loans are
BAD_FLAG = 1, over the loans whose BAD_FLAG reads 0 or 1; charge-off rate is GCO_AMT over ORIG_BAL on the loans
with both; RANR the same with RANR_AMT; x book is the band's charge-off rate over the whole book's.

Writes results.csv (each cell, both numbers, TIED or DIFFERS) and prints the counts."""

import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPECIAL = ("(blank)", "(not a number)", "(marked missing)")
TOL = 1e-9


def number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def reads_in(label: str, v: float) -> bool:
    lo, hi = (float(x.replace(",", "")) for x in label.split(" - "))
    return lo <= math.floor(v) <= hi


def place(v, labels, field) -> str:
    if v is None or str(v).strip() == "":
        return "(blank)"
    x = number(v)
    if x is None:
        return "(not a number)"
    if field == "FICO" and x == -9999:
        return "(marked missing)"
    hit = [lab for lab in labels if reads_in(lab, x)]
    if len(hit) != 1:
        raise ValueError(f"{field} {v} fits {len(hit)} labels: {hit}")
    return hit[0]


def figures(rows) -> dict:
    read = [r for r in rows if r["BAD_FLAG"] in ("0", "1")]
    bad = sum(1 for r in read if r["BAD_FLAG"] == "1")
    booked = math.fsum(number(r["ORIG_BAL"]) for r in rows if number(r["ORIG_BAL"]) is not None)
    both = lambda col: [(number(r[col]), number(r["ORIG_BAL"])) for r in rows                  # noqa: E731
                        if number(r[col]) is not None and number(r["ORIG_BAL"]) is not None]
    g, k = both("GCO_AMT"), both("RANR_AMT")
    gco, gden = math.fsum(a for a, _ in g), math.fsum(b for _, b in g)
    ranr, rden = math.fsum(a for a, _ in k), math.fsum(b for _, b in k)
    return {"Loans": len(rows), "Bad loans": bad, "Bad loans %": bad / len(read) if read else None,
            "Booked $": booked, "Charged off $": gco, "Charge-off rate": gco / gden if gden else None,
            "RANR $": ranr, "RANR rate": ranr / rden if rden else None}


def view(rows, field, labels, specials, book_rate) -> dict:
    """The bands, then `specials` (the special rows the tab shows or the loans fall in), then All."""
    by = {}
    for r in rows:
        by.setdefault(place(r[field], labels, field), []).append(r)
    out = {lab: figures(by.get(lab, [])) for lab in labels + [sp for sp in SPECIAL if sp in specials or sp in by]}
    out["All"] = figures(rows)
    top = out["All"]
    for x in out.values():
        for share, of in (("% of loans", "Loans"), ("% of booked", "Booked $"), ("% of charge-offs", "Charged off $"),
                          ("% of RANR", "RANR $")):
            x[share] = x[of] / top[of] if top[of] else None
        x["× book"] = x["Charge-off rate"] / book_rate if x["Charge-off rate"] is not None else None
    return out


def main() -> None:
    loans = list(csv.DictReader(open(HERE / "Summary book.csv", encoding="utf-8")))
    shown = list(csv.DictReader(open(HERE / "shown.csv", encoding="utf-8")))
    book_rate = figures(loans)["Charge-off rate"]
    views = {}
    for s in shown:
        views.setdefault((s["band column"], s["only loans where"]), []).append(s)
    out, counts = [], {"TIED": 0, "DIFFERS": 0}
    for (field, only), cells in views.items():
        labels = list(dict.fromkeys(c["row"] for c in cells if c["row"] != "All" and c["row"] not in SPECIAL))
        rows = loans if only == "All loans" else [r for r in loans if r["ORIG_DATE"][:4] == only]
        rows_shown = list(dict.fromkeys(c["row"] for c in cells))
        want = view(rows, field, labels, rows_shown, book_rate)
        if rows_shown != list(want):                          # the bands in order, the special rows, then All
            out.append([field, only, "(row order)", "", " · ".join(rows_shown), " · ".join(want), "DIFFERS"])
            counts["DIFFERS"] += 1
        for c in cells:
            got = None if c["shown"] == "" else float(c["shown"])      # repr of a number, written by build.py
            w = want[c["row"]][c["heading"]]
            if w is None:
                same = got in (None, "")
            else:
                same = isinstance(got, (int, float)) and abs(got - w) <= TOL * max(1.0, abs(w))
            verdict = "TIED" if same else "DIFFERS"
            counts[verdict] += 1
            out.append([field, only, c["row"], c["heading"], c["shown"], "" if w is None else repr(w), verdict])
    with open(HERE / "results.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["band column", "only loans where", "row", "heading", "PocketBook", "road 2", "verdict"])
        wr.writerows(out)
    print(f"{len(views)} views, {sum(counts.values()):,} cells: {counts['TIED']:,} TIED, {counts['DIFFERS']:,} DIFFERS")


if __name__ == "__main__":
    main()
