import json, os, sys, datetime
D = sys.argv[1]
v = json.load(open(os.path.join(D, "verdicts2.json")))
def qtrs(a, b):
    out = []; y, m = int(a[:4]), int(a[5:7])
    while (y, m) <= (int(b[:4]), int(b[5:7])):
        out.append("%d-%02d" % (y, m)); m += 3
        if m > 12: m -= 12; y += 1
    return out
BYCLASS = {"DIM", "CONCEPT", "RATING"}
res = {}
for t, es in v.items():
    byq = {e["period"][:7]: e for e in es}
    allq = qtrs("2009-03", "2026-06")
    missing = [q for q in allq if q not in byq and (t != "CFG" or q >= "2014-09")]
    first_any = next((e for e in es if e.get("verdict") in BYCLASS), None)
    first_dim = next((e for e in es if e.get("verdict") == "DIM"), None)
    first_crit = next((e for e in es if e.get("verdict") in ("DIM", "CONCEPT")), None)
    win = qtrs(first_any["period"][:7], "2026-06") if first_any else []
    tagged = [q for q in win if q in byq and byq[q].get("verdict") in BYCLASS]
    crit = [q for q in win if q in byq and byq[q].get("verdict") in ("DIM", "CONCEPT")]
    dim = [q for q in win if q in byq and byq[q].get("verdict") == "DIM"]
    gaps = [q for q in win if q not in tagged]
    early = {}
    for e in es:
        for d, vv in (e.get("comparatives") or {}).items():
            if vv in BYCLASS and d < (first_any["period"] if first_any else "9999"):
                early.setdefault(d, []).append("%s %s (%s)" % (e["form"], e["period"], vv))
    pre = {q: (byq[q].get("verdict") or byq[q]["status"]) for q in qtrs("2009-03", "2010-12") if q in byq}
    res[t] = dict(first_any=first_any and (first_any["period"], first_any["verdict"], first_any["url"]),
                  first_crit=first_crit and (first_crit["period"], first_crit["verdict"], first_crit["url"]),
                  first_dim=first_dim and (first_dim["period"], first_dim["url"]),
                  window=len(win), tagged=len(tagged), crit=len(crit), dim=len(dim), gaps=gaps, missing=missing,
                  early=early, pre2011=pre, last=(es[-1]["period"], es[-1].get("verdict"), es[-1].get("url")))
    print(t, json.dumps(res[t], indent=None)[:1500]); print()
json.dump(res, open(os.path.join(D, "summary.json"), "w"), indent=1)
