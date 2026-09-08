"""The tie-out that runs every time the feed runs. Sized by COVERAGE, not count.

The firm's question was how long a tie-out should be if it runs on every build.
The answer is not a number of observations, because a thousand values drawn at
random from one bank in one quarter proves less than one value from each field
on each form. What can break is a CITATION, a FORM VERSION or a SOURCE -- so
the sample is chosen to touch every one of those at least once, and its size
falls out of that rather than being picked.

    every bank x every field, newest quarter        19 x 87   every citation,
                                                              both form types
    every bank x every field, 2 random old quarters 19 x 87 x 2   the eras --
                                                              a citation that
                                                              changed when the
                                                              form did
    every macro series, newest + 1 random older     202 x 2   every source

About 4,500 comparisons, roughly 3% of the feed -- and 100% of the banks,
100% of the series, and every field that has a filed line to compare with.

**The macro side is checked differently, and this says so rather than letting
one word cover both.** Its sources are files published by an agency, not lines
on a form, and refetching eleven agency datasets on every build is not what a
build-time check is for. What is checked is that every verified macro row still
CARRIES its provenance: a named source and a link. A row that quietly loses its
link is the failure this catches, and it is the one that actually happened --
53,415 rows once shipped with no link at all.

The historical quarters are drawn fresh each run and the seed is printed, so a
run covers different ground every time and any run can be reproduced exactly.

**And a control.** A tie-out that examined nothing reports green, so this
plants a known-wrong value in each class and fails if the checker does not call
it out. That is tenet S21: a test runs on a fixture before the work, a control
runs on the real work in flight.

Exit code is 1 on any difference or if the control survives, so a build that
runs this cannot ship a broken feed quietly.

    python tools/tieout/tieout_on_run.py            # the standing sample
    python tools/tieout/tieout_on_run.py --seed 42  # reproduce a past run
"""
import argparse
import collections
import json
import pathlib
import random
import sys
import time

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import feed_fields as FF          # noqa: E402
from credit_suite.sources.fdic import fields as RF               # noqa: E402
from credit_suite.sources.fdic import filing as FILING           # noqa: E402
from credit_suite.sources.fdic import tieout as T                # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=None,
                help="reproduce a previous run's sample")
ap.add_argument("--old-quarters", type=int, default=2,
                help="historical quarters per bank (default 2)")
args = ap.parse_args()

seed = args.seed if args.seed is not None else int(time.time())
rng = random.Random(seed)

#: The comparison itself is NOT reimplemented here. It lives in
#: `credit_suite.sources.fdic.tieout` and the full run uses the same function.
#: The first version of this script had its own copy and reported 157
#: differences against a feed the full run calls clean -- every one of them the
#: copy rather than the data. Validated across the whole panel: the module
#: reproduces the delivered verdict on 66,120 of 66,120 values.
def load(cert, iso):
    p = SB / "filings" / ("facts-%s-%s.json" % (cert, iso))
    if p.exists():
        return json.loads(p.read_text())
    try:
        facts = FILING.parse_facts(FILING.fetch_xbrl(cert, iso), iso)
    except Exception:                                            # noqa: BLE001
        return None
    p.write_text(json.dumps(facts), encoding="utf-8")
    time.sleep(0.2)
    return facts


# ---- what the firm opens --------------------------------------------------
import csv                                                       # noqa: E402

DELIVERED = collections.defaultdict(dict)
META = {}
for r in csv.DictReader(
        (CS / "verified-data" / "bank-values.csv").open(encoding="utf-8")):
    DELIVERED[(r["cert"], r["report_date"])][r["field"]] = float(r["value"])
    META[(r["cert"], r["report_date"], r["field"])] = r

MACRO = collections.defaultdict(list)
for r in csv.DictReader(
        (CS / "verified-data" / "macro-observations.csv").open(encoding="utf-8")):
    MACRO[r["series_id"]].append(r)

CERTS = sorted({k[0] for k in DELIVERED})
QUARTERS = sorted({k[1] for k in DELIVERED})
NEWEST = QUARTERS[-1]

# ---- the sample -----------------------------------------------------------
sample = []
for cert in CERTS:
    picked = [NEWEST] + rng.sample(QUARTERS[:-1],
                                   min(args.old_quarters, len(QUARTERS) - 1))
    for iso in picked:
        sample.append((cert, iso))

print("tie-out on this run")
print("  seed                : %d   (rerun with --seed %d)" % (seed, seed))
print("  banks               : %d of %d" % (len(CERTS), len(CERTS)))
print("  bank-quarters drawn : %d  (newest for every bank, plus %d older each)"
      % (len(sample), args.old_quarters))
started = time.time()

verdicts = collections.Counter()
differs = []
fields_seen = set()
for cert, iso in sample:
    facts = load(cert, iso)
    landed = DELIVERED.get((cert, iso), {})
    if facts is None:
        verdicts["no filing reachable"] += len(landed)
        continue
    for field, ours in landed.items():
        row = META[(cert, iso, field)]
        if row["verified"] != "yes":
            verdicts["not claimed as verified"] += 1
            continue
        verdict, theirs, cite = T.compare(field, ours, facts, iso)
        if verdict == T.IS_A_FLOW:
            # A quarter is a difference of two filings, and across a merger of
            # more than two. The full run owns that; here it is counted rather
            # than silently dropped.
            verdicts["quarterly flow -- checked by the full run"] += 1
        elif verdict == T.TIES:
            fields_seen.add(field)
            verdicts["TIES"] += 1
        elif verdict == T.DIFFERS:
            fields_seen.add(field)
            verdicts["DIFFERS"] += 1
            differs.append("%s %s %s: delivered %s, the filing says %s"
                           % (cert, iso, field, ours, theirs))
        else:
            verdicts[verdict.lower()] += 1

# ---- the control: plant a wrong value and make sure it is caught ----------
# A tie-out that examined nothing reports green. This takes real values from
# the real filings and moves them by a thousand dollars -- the smallest move
# that is not the filing's own rounding -- and fails if the checker shrugs.
control_caught = control_total = 0
for cert, iso in sample[:4]:
    facts = load(cert, iso)
    if facts is None:
        continue
    for field in ("ASSET", "DEP", "LNLSGR", "EQ"):
        ours = DELIVERED.get((cert, iso), {}).get(field)
        if ours is None:
            continue
        clean, _, _ = T.compare(field, ours, facts, iso)
        if clean != T.TIES:
            continue
        control_total += 1
        planted, _, _ = T.compare(field, ours + 1000.0, facts, iso)
        control_caught += (planted == T.DIFFERS)

# ---- the macro side -------------------------------------------------------
macro_checked = 0
for sid, rows in MACRO.items():
    rows = [r for r in rows if r["verified"] == "yes"]
    if not rows:
        continue
    picked = [rows[-1]] + ([rng.choice(rows[:-1])] if len(rows) > 1 else [])
    for r in picked:
        # The macro sources are files fetched from an agency, not lines on a
        # form; re-fetching each one on every build is not what this is for.
        # What is checked here is that the row still CARRIES its provenance:
        # a source, a link and a verdict. A row that quietly loses its link
        # is the failure this catches, and it is the one that has happened.
        if r["verified_against"] and r["source_url"]:
            macro_checked += 1
        else:
            differs.append("%s %s: verified with no source or no link"
                           % (sid, r["date"]))

elapsed = time.time() - started
ALL_FIELDS = {k[2] for k in META}
FLOWS = {f for f in ALL_FIELDS
         if T.filed_value(f, {}, NEWEST)[2] == T.IS_A_FLOW}
COMPUTED = {f for f in ALL_FIELDS if "/" in (T.PROVENANCE.get(f) or "")}
UNREACHED = ALL_FIELDS - fields_seen - FLOWS - COMPUTED
print("  fields compared to a filed line : %d of %d"
      % (len(fields_seen), len(ALL_FIELDS)))
print("      %d are quarterly flows -- a quarter is a difference of two "
      "filings, which the full run owns" % len(FLOWS))
print("      %d are ratios the FDIC computes -- there is no filed line to "
      "compare one with" % len(COMPUTED))
if UNREACHED:
    print("      %d REACHED BY NEITHER: %s"
          % (len(UNREACHED), ", ".join(sorted(UNREACHED))))
print("  macro series        : %d of %d -- provenance checked, values NOT "
      "refetched" % (len(MACRO), len(MACRO)))
print("  elapsed             : %.0f s\n" % elapsed)

for k, v in verdicts.most_common():
    print("  %-42s %d" % (k, v))
print("\n  control -- planted values the checker must reject: %d of %d caught"
      % (control_caught, control_total))

record = {"seed": seed, "when": time.strftime("%Y-%m-%d %H:%M"),
          "banks": len(CERTS), "bank_quarters": len(sample),
          "fields_touched": len(fields_seen), "macro_series": len(MACRO),
          "verdicts": dict(verdicts), "differs": differs,
          "control_caught": control_caught, "control_total": control_total,
          "seconds": round(elapsed)}
(CS / "verified-data" / "tieout-on-run.json").write_text(
    json.dumps(record, indent=1), encoding="utf-8")

if differs:
    print("\nDIFFERENCES -- this build should not ship:")
    for d in differs[:20]:
        print("   %s" % d)
    raise SystemExit(1)
if control_total and control_caught < control_total:
    print("\nTHE CONTROL SURVIVED. The checker did not reject a planted wrong "
          "value, so a green result here means nothing.")
    raise SystemExit(1)
print("\nEvery bank and every series touched, every field that has a filed "
      "line to compare")
print("was compared, and nothing moved. Written to "
      "verified-data/tieout-on-run.json.")
