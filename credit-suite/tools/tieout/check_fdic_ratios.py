"""The 6,080 ratios the FDIC computes: does its arithmetic join our lines?

Eight of the eighty-seven bank fields are not lines a bank files. The FDIC
computes them from filed lines and publishes the result, so there is no row on
any form to photograph and no line to compare them with. They are delivered
labelled `computed_by = the FDIC` and, until now, checked against nothing at
all -- the lines they are computed FROM are verified, and the step that joins
those lines was taken on trust.

That is a `COULD NOT` with an obstacle named, and a named obstacle is a
hypothesis rather than a verdict. Testing it: four of the eight are plain
point-in-time ratios of two figures this feed already carries and has already
tied to the filings. Recompute each one from ITS OWN verified components and
compare with what the FDIC published.

    EQV       equity capital            / total assets
    LNATRESR  allowance for loan losses / gross loans and leases
    NCLNLSR   noncurrent loans          / gross loans and leases
    LNRESNCR  allowance for loan losses / noncurrent loans

The other four -- ROAQ, NIMY, NTLNLSQR, EEFFR -- are computed over AVERAGE
balances across a period, or over income-statement items this feed does not
carry, so their components are not here to recompute from. That is reported
rather than glossed.

**Nothing computed here is delivered.** The firm's instruction was to eliminate
ratios made by our software, and this makes none: it recomputes the FDIC's own
number solely to ask whether the FDIC's arithmetic agrees with the filed lines
underneath it, and then throws the recomputation away.

    python tools/tieout/check_fdic_ratios.py
"""
import collections
import csv
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
DATA = CS / "verified-data"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

#: ratio -> (numerator, denominator). Both must be VERIFIED in the delivered
#: file for the comparison to mean anything; an unverified component makes
#: this a check of our arithmetic against our arithmetic.
RECOMPUTABLE = {
    "EQV": ("EQ", "ASSET"),
    "LNATRESR": ("LNATRES", "LNLSGR"),
    "NCLNLSR": ("NCLNLS", "LNLSGR"),
    "LNRESNCR": ("LNATRES", "NCLNLS"),
}
#: ratio -> why its components are not in this feed.
NOT_RECOMPUTABLE = {
    "ROAQ": "net income for the quarter over AVERAGE assets; the average is "
            "not a filed line and this feed carries period-end balances",
    "NIMY": "net interest income over AVERAGE earning assets; same reason",
    "NTLNLSQR": "quarterly net charge-offs, annualised, over AVERAGE loans; "
                "same reason, and the numerator is itself a flow",
    "EEFFR": "noninterest expense over revenue; the income-statement items it "
             "needs are not among the 87 fields this feed carries",
}
#: The FDIC publishes these to four decimal places. A recomputation from two
#: figures each rounded to a thousand dollars cannot land closer than the
#: rounding of its own inputs, so the tolerance is derived from the inputs
#: rather than picked: half a thousand on each side of a division.
def tolerance(num, den):
    if not den:
        return None
    return abs(((num + 0.5) / (den - 0.5) - num / den) * 100) + 5e-5


panel = collections.defaultdict(dict)
verified = collections.defaultdict(dict)
for r in csv.DictReader((DATA / "bank-values.csv").open(encoding="utf-8")):
    key = (r["cert"], r["report_date"])
    panel[key][r["field"]] = float(r["value"])
    verified[key][r["field"]] = r["verified"] == "yes"

print("Recomputing the FDIC's own ratios from the lines this feed has already")
print("tied to the filings. Nothing computed here is delivered.\n")

totals = collections.Counter()
worst = {}
for ratio, (num_f, den_f) in sorted(RECOMPUTABLE.items()):
    agree = differ = skipped = 0
    biggest = (0.0, None)
    for key, fields in panel.items():
        theirs = fields.get(ratio)
        num, den = fields.get(num_f), fields.get(den_f)
        if theirs is None or num is None or den is None:
            skipped += 1
            continue
        if not (verified[key].get(num_f) and verified[key].get(den_f)):
            skipped += 1               # an unverified component proves nothing
            continue
        if den == 0:
            skipped += 1               # a zero denominator is not a failure
            continue
        ours = num / den * 100.0
        gap = abs(ours - theirs)
        tol = tolerance(num, den)
        if gap <= tol:
            agree += 1
        else:
            differ += 1
            if gap > biggest[0]:
                biggest = (gap, "%s %s: FDIC %s, the two verified lines give "
                                "%.4f" % (key[0], key[1], theirs, ours))
    totals["agree"] += agree
    totals["differ"] += differ
    totals["skipped"] += skipped
    worst[ratio] = biggest[1]
    print("  %-9s = %-8s / %-8s   %4d agree, %d differ, %d not comparable"
          % (ratio, num_f, den_f, agree, differ, skipped))
    if biggest[1]:
        print("        worst: %s" % biggest[1])

print("\n  %d of the 6,080 FDIC-computed values were recomputed from their own"
      % (totals["agree"] + totals["differ"]))
print("  verified components. %d agree, %d differ."
      % (totals["agree"], totals["differ"]))
print("\nNot recomputable, and why:")
for ratio, why in sorted(NOT_RECOMPUTABLE.items()):
    print("  %-9s %s" % (ratio, why))
print("\nWhat this does NOT prove: that the FDIC's definition is the one you")
print("want. It proves its arithmetic joins the lines we verified, on the")
print("four where those lines are here to join.")
raise SystemExit(1 if totals["differ"] else 0)
