"""The public-data rehearsal's answer key: the known-effect rates, worked out with plain Python, without PocketBook.

    python tools/rehearsal_answer_key.py DATA_FOLDER [--review]

DATA_FOLDER is the rehearsal's data folder (`extracts/` and `raw/` inside it; the report names it). What it reads, said
plainly because the report once called this key "independent" without saying of what:

- sections 1-3 read the EXTRACTS that tools/public_extract.py wrote, so they are independent of PocketBook but NOT of
  the converter. A reviewer's key read from the raw files, without the converter, agreed with every figure checked
  (29 Sep 2026);
- section 4, and every section --review adds, reads the RAW SBA FOIA file, and only the columns it names (no name,
  address or bank is read);
- --review adds what the review of 29 Sep 2026 found: each outcome's share of whole-year terms, loans left out as
  EXEMPT in the holdout's 240-month group, disbursed against approved by revolver and outcome, and how many FY2009
  loans carry InitialInterestRate.

Its output was saved as `extracts/answer-key.txt` (sections 1-4). Aggregates only: no loan-level row is printed.
Standard library only.
"""

from __future__ import annotations

import csv
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

NAT, FOIA, LC = "sba-national.csv", "sba-foia-fy2000-2009.csv", "lendingclub-36m-2008-2011.csv"
RAW_FOIA = "FOIA_7a_FY2000_FY2009_asof_260630.csv"


def num(text: str | None) -> float | None:
    s = (text or "").strip().replace("$", "").replace(",", "")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def rows(path: Path, cols: tuple[str, ...]):
    """Only the named columns of each row."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            yield {c: r[c] for c in cols}


def show(title: str, tally: dict, order: tuple[str, ...] | None = None) -> str:
    """'title k=rate%(n=N) ...', highest rate first, or in `order`; a blank key reads (blank)."""
    items = sorted(((k or "(blank)", b / n * 100, n) for k, (n, b) in tally.items()),
                   key=(lambda t: order.index(t[0])) if order else (lambda t: -t[1]))
    return title + " " + "  ".join(f"{k}={r:.2f}%(n={n:,})" for k, r, n in items)


def book(path: Path, outcome: str, cats: tuple[str, ...], size: str) -> list[str]:
    tallies = {c: defaultdict(lambda: [0, 0]) for c in cats}
    n = bad = 0
    sizes = {0: [], 1: []}
    for r in rows(path, (outcome, size) + cats):
        y = int(r[outcome])
        n += 1
        bad += y
        for c in cats:
            t = tallies[c][r[c]]
            t[0] += 1
            t[1] += y
        v = num(r[size])
        if v is not None:
            sizes[y].append(v)
    out = [f"== {path.name}: {n:,} loans, {bad:,} bad, {bad / n:.4%}"]
    out += [show(c, tallies[c]) for c in cats]
    out.append(f"median {size}: bad {statistics.median(sizes[1]):,.1f}  good {statistics.median(sizes[0]):,.1f}")
    return out


def term_band(t: float, edges: list[tuple[str, float, float]]) -> str:
    return next(name for name, lo, hi in edges if lo <= t < hi)


def nat_term_by_recession(path: Path) -> list[str]:
    edges = [("0-59", 0, 60), ("60-83", 60, 84), ("84-179", 84, 180), ("180+", 180, 1e9)]
    t = {e[0]: defaultdict(lambda: [0, 0]) for e in edges}
    for r in rows(path, ("CHGOFF_FLAG", "Term", "RECESSION")):
        c = t[term_band(float(r["Term"]), edges)][r["RECESSION"]]
        c[0] += 1
        c[1] += int(r["CHGOFF_FLAG"])
    return ["== sba-national: charge-off rate by Term band x RECESSION (independent of PocketBook)"] + \
        [show(name, t[name], ("Y", "N", "(blank)")) for name, *_ in edges]


def foia_term_groups(path: Path) -> list[str]:
    """The pre-spec's TermInMonths groups, on its development and holdout approvals."""
    edges = [("0-59", 0, 60), ("60-83", 60, 84), ("84-119", 84, 120), ("120-239", 120, 240), ("240+", 240, 1e9)]
    sets = {"dev FY2000-05": ("1999-10-01", "2005-09-30"), "holdout FY2006-09": ("2005-10-01", "2009-09-30")}
    t = {s: {e[0]: [0, 0, 0.0, 0.0] for e in edges} for s in sets}      # loans, bad, GCO, booked
    for r in rows(path, ("CHGOFF_FLAG", "TermInMonths", "ApprovalDate", "GrossChargeOffAmount", "GrossApproval")):
        term = num(r["TermInMonths"])
        which = next((s for s, (a, b) in sets.items() if a <= r["ApprovalDate"] <= b), None)
        if term is None or which is None:
            continue
        c = t[which][term_band(term, edges)]
        c[0] += 1
        c[1] += int(r["CHGOFF_FLAG"])
        c[2] += num(r["GrossChargeOffAmount"]) or 0.0
        c[3] += num(r["GrossApproval"]) or 0.0
    out = ["== sba-foia: charge-off rate by term group, development vs holdout approvals (independent of PocketBook)"]
    for s in sets:
        out.append(s + " " + "  ".join(f"{g}={b / n:.2%}(n={n:,}, GCO/booked {gco / bk:.2%})"
                                       for g, (n, b, gco, bk) in t[s].items()))
    return out


def months(a: str, b: str) -> int:
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7])


def foia_charge_off_timing(raw: Path) -> list[str]:
    both = equal = near = after = 0
    rev = Counter()
    for r in rows(raw, ("LoanStatus", "TermInMonths", "FirstDisbursementDate", "ChargeOffDate", "RevolverStatus")):
        if r["LoanStatus"].strip() != "CHGOFF":
            continue
        term, fd, co = num(r["TermInMonths"]), r["FirstDisbursementDate"].strip(), r["ChargeOffDate"].strip()
        if term is None or not fd or not co:
            continue
        both += 1
        m = months(fd, co)
        equal += m == term
        near += abs(m - term) <= 3
        after += m > term
        rev[(r["RevolverStatus"].strip(), "<60" if term < 60 else ">=60")] += 1
    return [f"== sba-foia CHGOFF loans with both dates: {both:,}; term equal to months from first disbursement to "
            f"charge-off: {equal:,} ({equal / both:.1%}); within 3 months: {near:,} ({near / both:.1%}); charged off "
            f"after the term ended: {after:,} ({after / both:.1%})",
            f"   CHGOFF loans by RevolverStatus and term: {dict(rev)}"]


def review(ext: Path, raw: Path) -> list[str]:
    out = ["== review, 29 Sep 2026: share of terms that are whole years (a multiple of 12), by outcome"]
    for name, col in ((NAT, "Term"), (FOIA, "TermInMonths")):
        t = defaultdict(lambda: [0, 0])
        at84 = Counter()
        for r in rows(ext / name, ("CHGOFF_FLAG", col)):
            v = num(r[col])
            if v is None:
                continue
            c = t[r["CHGOFF_FLAG"]]
            c[0] += 1
            c[1] += v % 12 == 0
            at84[r["CHGOFF_FLAG"]] += v == 84
        out.append(f"{name}: " + "  ".join(f"outcome {k}: {w / n:.1%} of {n:,}" for k, (n, w) in sorted(t.items()))
                   + f"  |  at exactly 84 months: {at84['0']:,} paid, {at84['1']:,} charged off")
    held = Counter()
    fy09 = Counter()
    for r in rows(raw, ("LoanStatus", "TermInMonths", "ApprovalDate", "ApprovalFY", "InitialInterestRate")):
        term, st = num(r["TermInMonths"]), r["LoanStatus"].strip()
        if r["ApprovalFY"].strip() == "2009":
            fy09["rows"] += 1
            fy09["with a rate"] += bool(r["InitialInterestRate"].strip())
        if term is not None and term >= 240 and "2005-10-01" <= r["ApprovalDate"].strip() <= "2009-09-30":
            held[st] += 1
    kept = held["P I F"] + held["CHGOFF"]
    out.append(f"== review: holdout FY2006-09, term 240+: {kept:,} kept ({held['CHGOFF']:,} charged off, "
               f"{held['CHGOFF'] / kept:.2%}); {held['EXEMPT']:,} EXEMPT left out (disbursed, still open); if every "
               f"EXEMPT loan performed: {held['CHGOFF'] / (kept + held['EXEMPT']):.2%}")
    out.append(f"== review: FY2009 rows {fy09['rows']:,}, with InitialInterestRate {fy09['with a rate']:,}")
    t = defaultdict(lambda: [0, 0])
    for r in rows(ext / NAT, ("CHGOFF_FLAG", "RevLineCr", "DisbursementGross", "GrAppv")):
        d, a = num(r["DisbursementGross"]), num(r["GrAppv"])
        c = t[(r["RevLineCr"] or "(blank)", r["CHGOFF_FLAG"])]
        c[0] += 1
        c[1] += d is not None and a is not None and d > a
    out.append("== review: sba-national, disbursed above approved, by RevLineCr and outcome: " + "  ".join(
        f"{k[0]}/{k[1]}={b / n:.1%}(n={n:,})" for k, (n, b) in sorted(t.items()) if k[0] in ("Y", "N")))
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    d = Path(argv[0])
    ext, raw = d / "extracts", d / "raw" / RAW_FOIA
    missing = [p for p in (ext / NAT, ext / FOIA, ext / LC, raw) if not p.exists()]
    if missing:
        print(f"REFUSED: {', '.join(map(str, missing))} isn't there; the data folder can be purged (the report "
              f"says where it came from)", file=sys.stderr)
        return 2
    out = book(ext / NAT, "CHGOFF_FLAG", ("NAICS2", "REAL_ESTATE", "RECESSION", "NewExist"), "DisbursementGross")
    out += book(ext / FOIA, "CHGOFF_FLAG", ("NAICS2", "REAL_ESTATE", "RECESSION", "BusinessAge", "ApprovalFY"),
                "GrossApproval")
    out += book(ext / LC, "BAD", ("grade", "purpose", "home_ownership", "emp_length"), "funded_amnt")
    out += nat_term_by_recession(ext / NAT)
    out += foia_term_groups(ext / FOIA)
    out += foia_charge_off_timing(raw)
    if "--review" in argv:
        out += review(ext, raw)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
