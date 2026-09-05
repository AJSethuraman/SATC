"""Is the Case-Shiller gap a June accident or a standing bias?

Five of twenty-two lines missed the release's printed rounding by 0.005 to
0.0074 percentage points. That is small, and small is not an explanation. The
release prints a SECOND month's change in the same table -- May / April -- so
the same arithmetic on the month before is a free discriminator:

  * if the five miss again, something systematic separates our levels from
    S&P's, and the June result is not a one-off
  * if the five tie, the June figures are the odd ones, which points at the
    revision window S&P declares on the facing page

Either answer is worth more than widening the tolerance until the red goes away.
"""
import json
import pathlib
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

#: Table 3, 'May / April Change (%)', column 'SA'.
MAY_APRIL = {
    "ATXRSA": 0.00, "BOXRSA": 0.55, "CRXRSA": -0.24, "CHXRSA": 0.54,
    "CEXRSA": -0.13, "DAXRSA": 0.06, "DNXRSA": -0.33, "DEXRSA": 0.15,
    "LVXRSA": -0.55, "LXXRSA": 0.28, "MIXRSA": 0.09, "MNXRSA": -0.10,
    "NYXRSA": 0.50, "PHXRSA": -0.22, "POXRSA": -0.21, "SDXRSA": -0.53,
    "SFXRSA": 0.21, "SEXRSA": -0.27, "TPXRSA": -0.22, "WDXRSA": 0.13,
    "CSUSHPISA": 0.02,
}
#: Detroit's May/April is its LATEST pair, so it sits one step earlier.
BACK = {"DEXRSA": 0}

ours = json.loads((SB / "fred_ours.json").read_text())
june = {r["series"]: r for r in
        json.loads((SB / "fred_caseshiller_results.json").read_text())}

rows = []
for sid, published in sorted(MAY_APRIL.items()):
    obs = ours[sid]["observations"]
    back = BACK.get(sid, 1)
    new, old = obs[back], obs[back + 1]
    computed = (new["value"] / old["value"] - 1.0) * 100.0
    rows.append({
        "series": sid,
        "june_diff": june[sid].get("diff"),
        "june_verdict": june[sid]["verdict"],
        "may_dates": "%s / %s" % (new["date"], old["date"]),
        "ours": round(computed, 4), "theirs": published,
        "diff": round(computed - published, 4),
        "verdict": "TIED" if abs(computed - published) <= 0.005 else "DIFFERS",
    })

(SB / "cs_second_month.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
from collections import Counter
print("May/April, same arithmetic, same release: %d compared  %s"
      % (len(rows), Counter(r["verdict"] for r in rows).most_common()))
print()
print("%-11s %-9s %9s   %-9s %9s   %s" %
      ("series", "June", "June diff", "May/Apr", "M/A diff", "dates"))
for r in sorted(rows, key=lambda x: -abs(x["diff"])):
    print("%-11s %-9s %9s   %-9s %9s   %s"
          % (r["series"], r["june_verdict"], r["june_diff"],
             r["verdict"], r["diff"], r["may_dates"]))

june_bad = {r["series"] for r in rows if r["june_verdict"] == "DIFFERS"}
may_bad = {r["series"] for r in rows if r["verdict"] == "DIFFERS"}
print("\nmissed in June : %s" % sorted(june_bad))
print("missed in May  : %s" % sorted(may_bad))
print("missed in both : %s" % sorted(june_bad & may_bad))
print("\nlargest absolute miss across both months: %.4f percentage points"
      % max([abs(r["diff"]) for r in rows]
            + [abs(r["june_diff"]) for r in rows if r["june_diff"] is not None]))
