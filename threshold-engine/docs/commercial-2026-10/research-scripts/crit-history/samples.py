import json, os, sys, re
sys.path.insert(0, os.path.dirname(__file__)); from verdict2 import keep, iscomm, GENERIC_CON, CRIT, local
D = sys.argv[1]; s = json.load(open(os.path.join(D, "summary.json"))); v = json.load(open(os.path.join(D, "verdicts2.json")))
out = {}
for t, x in s.items():
    if not x["first_any"]: continue
    per = x["first_any"][0]; e = [e for e in v[t] if e["period"] == per][0]
    r = json.load(open(os.path.join(D, "sum2", e["acc"] + ".json")))
    rows = {}
    for f in r["facts"]:
        d, q, oth, cq, val, u = f
        if d != per or not keep(f): continue
        dk = "|".join(sorted("%s=%s" % (local(a), local(m)) for a, m in oth.items()))
        lab = dk + ("" if GENERIC_CON.match(q) else " [" + local(q) + "]")
        if not iscomm(lab): continue
        rows.setdefault((local(q), dk), {}).update({local(m): val for m in cq.values()})
    def score(k):
        txt = k[0] + k[1]
        return (bool(re.search(r"CommercialAndIndustrial|CommercialFinancialAndAgricultural|CommercialLoan\b|CommercialAndIndustrialLoans|UsCommercial|CommercialDomestic|CommercialFinancingReceivable", txt)), len(rows[k]))
    best = sorted(rows, key=score, reverse=True)[:1]
    out[t] = [(per, k[0], k[1], {m: round(float(vv) / 1e6, 1) for m, vv in rows[k].items()}) for k in best]
    print(t, out[t])
json.dump(out, open(os.path.join(D, "samples.json"), "w"), indent=1)
