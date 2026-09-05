"""Fold the eight recovered fields into each bank's roster, and state the
denominator honestly.

Before: 53 of 69 raw fields per bank, reported as if it were all of them.
After: 61 compared, 8 FDIC-computed ratios named as out of scope rather than
left out silently, and one field the FDIC does not publish recorded as blank
with its citation.
"""
import json
import pathlib
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

banks = json.loads((SB / "bank_rosters.json").read_text())
gap = json.loads((SB / "gap_results.json").read_text())
by_cert = {}
for g in gap:
    by_cert.setdefault(g["cert"], []).append(g)

#: The eight FDIC-COMPUTED ratios. They are arithmetic over lines this tie-out
#: proves, and they are named here so "not checked" is a statement rather than
#: an omission.
COMPUTED_RATIOS = ["NCLNLSR", "NTLNLSQR", "LNATRESR", "LNRESNCR",
                   "EQV", "ROAQ", "NIMY", "EEFFR"]

for bank in banks:
    cert = bank["cert"]
    existing = {l["field"] for l in bank["lines"]}
    added = 0
    for g in by_cert.get(cert, []):
        if g["field"] in existing:
            continue
        line = {k: g[k] for k in ("field", "ours", "filed", "used", "verdict",
                                  "schedule", "caption", "how")}
        line["note"] = ""
        for extra in ("ytd_q2", "ytd_q1"):
            if extra in g:
                line[extra] = g[extra]
        if g["field"] == "NTRENREQ":
            line["verdict"] = "NOT PUBLISHED"
            line["how"] = ("the FDIC publishes no quarterly variant of this "
                           "field -- its API returns the year-to-date and "
                           "nothing else -- so the column is blank for every "
                           "bank. The citation records where the number would "
                           "come from; the filing carries the components and "
                           "they were read.")
        bank["lines"].append(line)
        added += 1
    bank["computed_ratios_out_of_scope"] = COMPUTED_RATIOS
    bank["raw_fields_total"] = 69
    counted = [l for l in bank["lines"]
               if not l["note"] and l["verdict"] != "NOT PUBLISHED"]
    bank["compared"] = len(counted)
    bank["tied"] = sum(1 for l in counted if l["verdict"] == "TIES")
    print("%-26s +%d lines -> %d compared, %d tie, %d differ"
          % (bank["name"][:26], added, bank["compared"], bank["tied"],
             bank["compared"] - bank["tied"]))

(SB / "bank_rosters.json").write_text(json.dumps(banks, indent=1), encoding="utf-8")
tot = sum(b["compared"] for b in banks)
tied = sum(b["tied"] for b in banks)
print("\n%d banks: %d lines compared, %d tie, %d differ" % (len(banks), tot, tied, tot - tied))
print("per bank: 69 raw fields = %d compared + 8 computed ratios (out of scope)"
      " + 1 the FDIC does not publish" % banks[0]["compared"])
