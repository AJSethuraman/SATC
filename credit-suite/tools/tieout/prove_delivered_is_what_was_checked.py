"""The hop nobody executed: is the delivered file the file that was verified?

Every verifier compares an OURS value against a filed document. None of them
reads the delivered file. They read what the delivered file was built from:

    verify_bank_history      deep/bank-values-raw.csv        an intermediate CSV
    verify_new_bank_fields   deep/bank_new_fields.json       the API response
    verify_fred_history      deep/macro-observations-raw.csv an intermediate CSV
    verify_new_macro         deep/macro_new.json             the API response

`verified-data/bank-values.csv` and `macro-observations.csv` are written
afterwards, by `build_export.py`, from a third file again. So the chain the
firm relies on has a last hop in it that was DESCRIBED and never executed:
`deep_feed_values.py` says in its own docstring that a finisher "asserts, row
by row, that not one value moved". No such finisher exists. Nothing in this
repository compares the delivered numbers with the numbers that were checked.

That is the tie-out skill's own worst case -- an intermediate on the `ours`
side -- and it is worth being exact about what it does and does not mean. It
does not mean the numbers are wrong; every hop is a plain copy through Python
dicts. It means nobody had measured whether they are the same, and "should be"
is not a verdict.

This measures it. Every delivered value, matched to the value the verifier
actually held, compared as a number.

    python tools/tieout/prove_delivered_is_what_was_checked.py
"""
import csv
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
DATA = CS / "verified-data"
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import feed_fields as FF          # noqa: E402
from credit_suite.sources.fdic import fields as RF               # noqa: E402


def iso(repdte):
    s = str(repdte)
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])


# ---- what the verifiers actually held ------------------------------------
checked = {}

with (SB / "deep" / "bank-values-raw.csv").open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        checked[(r["cert"], r["report_date"], r["field"])] = (
            float(r["value"]), "deep/bank-values-raw.csv")

for cert, rows in json.loads(
        (SB / "deep" / "bank_new_fields.json").read_text()).items():
    for row in rows:
        for field in FF.FEED_FIELDS:
            v = row.get(field)
            if v is not None:
                checked[(cert, iso(row["REPDTE"]), field)] = (
                    float(v), "deep/bank_new_fields.json (the API response)")

macro_checked = {}
with (SB / "deep" / "macro-observations-raw.csv").open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        macro_checked[(r["series_id"], r["date"])] = (
            float(r["value"]), "deep/macro-observations-raw.csv")

_mn = SB / "deep" / "macro_new.json"
if _mn.exists():
    for sid, obs in json.loads(_mn.read_text()).items():
        for o in obs:
            try:
                macro_checked[(sid, o["date"])] = (
                    float(o["value"]), "deep/macro_new.json (the API response)")
            except (TypeError, ValueError):
                pass

# ---- what the firm opens --------------------------------------------------
TOL = 0.0                       # a copy is a copy; nothing here may round


def compare(delivered_file, key_cols, held, label):
    same = moved = missing = 0
    examples, sources = [], {}
    with (DATA / delivered_file).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = tuple(r[c] for c in key_cols)
            got = held.get(key)
            if got is None:
                missing += 1
                if len(examples) < 5:
                    examples.append("%s -- not present in what was checked"
                                    % (key,))
                continue
            val, src = got
            sources[src] = sources.get(src, 0) + 1
            if abs(float(r["value"]) - val) <= TOL:
                same += 1
            else:
                moved += 1
                if len(examples) < 5:
                    examples.append("%s: delivered %s, checked %s"
                                    % (key, r["value"], val))
    print("%s" % label)
    print("   delivered rows compared : %d" % (same + moved + missing))
    print("   identical to the value that was verified : %d" % same)
    print("   MOVED between the check and the file     : %d" % moved)
    print("   in the file but never checked at all     : %d" % missing)
    for src, cnt in sorted(sources.items(), key=lambda kv: -kv[1]):
        print("      %-46s %d" % (src, cnt))
    for e in examples:
        print("      %s" % e)
    print()
    return moved, missing


print("Comparing the DELIVERED files against the values the verifiers held.")
print("Tolerance is zero: every hop between them is a plain copy, so any")
print("difference at all is a finding.\n")

m1, x1 = compare("bank-values.csv", ("cert", "report_date", "field"),
                 checked, "BANK -- verified-data/bank-values.csv")
m2, x2 = compare("macro-observations.csv", ("series_id", "date"),
                 macro_checked, "MACRO -- verified-data/macro-observations.csv")

print("=" * 70)
if m1 + m2 + x1 + x2 == 0:
    print("The delivered files carry exactly the numbers that were checked.")
    print("This hop had never been executed before; now it has.")
else:
    print("FINDING: %d value(s) moved and %d were never checked."
          % (m1 + m2, x1 + x2))
print("\nWhat this does NOT prove: that the intermediate agreed with the")
print("filing. That is the verifiers' job and it is reported separately.")
print("This closes the last hop only -- the one from what was verified to")
print("what the firm opens.")
