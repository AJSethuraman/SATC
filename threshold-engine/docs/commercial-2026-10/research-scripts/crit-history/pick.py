# Pick the XBRL instance + label linkbase for each filing from its index.json
import json, os, sys, re
def pick(D, acc):
    p = os.path.join(D, "idx", acc + ".json")
    if not os.path.exists(p): return None
    items = json.load(open(p))["directory"]["item"]
    names = {i["name"]: int(i.get("size") or 0) for i in items}
    inst = [n for n in names if n.endswith("_htm.xml")]
    if not inst:
        inst = [n for n in names if n.endswith(".xml") and not re.search(r"_(cal|def|lab|pre|ref)\.xml$", n)
                and n not in ("FilingSummary.xml",) and not n.startswith("R") and "xbrl" not in n.lower()[:0]]
        inst = [n for n in inst if not n.lower().startswith("primary_doc") and not n.lower().startswith("metadata")]
    lab = [n for n in names if n.endswith("_lab.xml")]
    return {"inst": inst, "lab": lab, "sizes": {n: names[n] for n in inst + lab}}
if __name__ == "__main__":
    D = sys.argv[1]; subs = json.load(open(os.path.join(D, "subs_all.json")))
    tot = 0
    for t, s in subs.items():
        for f in s["filings"]:
            if f["filed"] < "2009-04-01": continue
            r = pick(D, f["acc"])
            if r is None: print("NOIDX", t, f["acc"]); continue
            if len(r["inst"]) != 1: print(t, f["form"], f["period"], f["acc"], r["inst"])
            tot += sum(r["sizes"].get(n, 0) for n in r["inst"][:1])
    print("total inst bytes", tot / 1e9, "GB")
