"""Prove the cause of the Case-Shiller residual instead of widening a threshold.

Seven of 43 month-comparisons missed the release's printed value by 0.005 to
0.0074 percentage points. No series missed twice, and the signs were random --
so it is noise, not a data difference. But "it is noise" is a description.

The hypothesis is arithmetic and testable: S&P publishes index LEVELS rounded
to two decimals, and computes the printed percent change from those rounded
levels. FRED redistributes the levels at full precision. So our change is the
true one and S&P's is the change of two rounded numbers, then itself rounded.

If that is what happens, then re-running our own division with both cells
rounded to two decimals first should reproduce S&P's printed figure EXACTLY,
on every line -- including the seven that missed. If it does not, the
hypothesis is wrong and the difference is unexplained, which is what would
then get written down.
"""
import json
import pathlib
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

JUNE = {r["series"]: r for r in
        json.loads((SB / "fred_caseshiller_results.json").read_text())
        if r.get("ours_new") is not None}
MAY = {r["series"]: r for r in json.loads((SB / "cs_second_month.json").read_text())}
ours = json.loads((SB / "fred_ours.json").read_text())

BACK = {"DEXRSA": 0}
tests = []
for sid, r in sorted(JUNE.items()):
    tests.append((sid, "June/May", r["ours_new"], r["ours_old"], r["theirs"]))
for sid, r in sorted(MAY.items()):
    obs = ours[sid]["observations"]
    b = BACK.get(sid, 1)
    tests.append((sid, "May/April", obs[b]["value"], obs[b + 1]["value"], r["theirs"]))

rows = []
for sid, window, new, old, printed in tests:
    raw = round((new / old - 1.0) * 100.0, 4)
    rounded = round((round(new, 2) / round(old, 2) - 1.0) * 100.0, 2)
    rows.append({"series": sid, "window": window,
                 "level_new": new, "level_old": old,
                 "level_new_2dp": round(new, 2), "level_old_2dp": round(old, 2),
                 "printed": printed,
                 "raw_change": raw, "raw_miss": round(raw - printed, 4),
                 "rounded_change": rounded,
                 "hypothesis_holds": abs(rounded - printed) < 1e-9})

(SB / "cs_rounding_cause.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")

held = sum(r["hypothesis_holds"] for r in rows)
missed_raw = [r for r in rows if abs(r["raw_miss"]) > 0.005]
print("comparisons tested                            : %d" % len(rows))
print("missed the printed value at full precision    : %d" % len(missed_raw))
print("reproduced EXACTLY once both levels are")
print("  rounded to the two decimals S&P publishes   : %d of %d" % (held, len(rows)))
print()
print("The lines that missed at full precision, re-checked under the hypothesis:")
print("%-11s %-10s %10s %10s %9s %9s  %s"
      % ("series", "window", "level new", "level old", "printed", "rounded", "holds"))
for r in sorted(missed_raw, key=lambda x: -abs(x["raw_miss"])):
    print("%-11s %-10s %10.2f %10.2f %9.2f %9.2f  %s"
          % (r["series"], r["window"], r["level_new_2dp"], r["level_old_2dp"],
             r["printed"], r["rounded_change"],
             "yes" if r["hypothesis_holds"] else "NO"))
if held == len(rows):
    print("\nEvery comparison reproduces the release exactly. The residual is")
    print("S&P computing its printed change from its own two-decimal levels;")
    print("it is not a difference between the workbook's data and S&P's.")
else:
    bad = [r for r in rows if not r["hypothesis_holds"]]
    print("\n%d comparisons do NOT reproduce: %s"
          % (len(bad), sorted({b["series"] for b in bad})))
