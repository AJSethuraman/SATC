"""Two figures the proposal quotes that stress_stats.py does not print: past due
against nonaccrual (medians, 2006Q4 on), and how many banks' CRE net charge-off
medians since 2014Q1 are at or below zero. Run where pull.json and series.json are."""
import json, statistics
D = json.load(open("pull.json")); I = D["industry"]; C = D["cats"]; B = D["banks"]
S = json.load(open("series.json"))
for cat in ("C&I", "Nonfarm nonres", "Multifamily", "Construction"):
    bal, dr, cr, na, p9, p3 = C[cat]
    for who, R in (("Industry", I), ("KeyBank", B["KeyBank"])):
        r = {k: [100 * float(R[d][f]) / float(R[d][bal]) for d in sorted(R)
                 if d >= "20061231" and R[d].get(f) is not None and R[d].get(bal)]
             for k, f in (("nonaccrual", na), ("90+", p9), ("30-89", p3))}
        print(cat, who, "median, max:", {k: (round(statistics.median(v), 3), round(max(v), 2)) for k, v in r.items()})
for cat in ("Multifamily", "Construction", "Nonfarm nonres"):
    meds = {n: statistics.median([v for q, v in S[f"{n}|{cat}|nco"] if q >= "2014Q1"]) for n in B}
    print(cat, "TTM net charge-off median since 2014Q1, of", len(meds), "banks: below 0:", sum(m < 0 for m in meds.values()),
          "equal 0:", sum(m == 0 for m in meds.values()), "KeyBank:", meds["KeyBank"])
s = S["KeyBank|Multifamily|nonaccrual" if "KeyBank|Multifamily|nonaccrual" in S else "KeyBank|Multifamily|na"]
print("KeyBank multifamily nonaccrual quarters at or above 3.9%:", [(q, round(v, 2)) for q, v in s if v >= 3.9])
