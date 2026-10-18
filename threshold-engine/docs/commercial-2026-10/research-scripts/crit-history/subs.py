import json, sys, os
sys.path.insert(0, os.path.dirname(__file__)); from sec import get, CIKS
D = sys.argv[1]; out = {}
for t, cik in CIKS.items():
    sub = json.loads(get("https://data.sec.gov/submissions/CIK%010d.json" % cik))
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        blocks.append(json.loads(get("https://data.sec.gov/submissions/" + f["name"])))
    rows = []
    for b in blocks:
        for i, fm in enumerate(b["form"]):
            if fm in ("10-K", "10-Q", "10-K/A", "10-Q/A", "10-KT"):
                rows.append(dict(form=fm, period=b["reportDate"][i], filed=b["filingDate"][i], acc=b["accessionNumber"][i],
                                 prim=b["primaryDocument"][i], xbrl=b.get("isXBRL", [None]*len(b["form"]))[i],
                                 ixbrl=b.get("isInlineXBRL", [None]*len(b["form"]))[i]))
    rows.sort(key=lambda r: r["filed"])
    out[t] = {"cik": cik, "name": sub["name"], "former": sub.get("formerNames"), "filings": rows}
    print(t, cik, sub["name"], len(rows), rows[0]["filed"] if rows else None)
json.dump(out, open(os.path.join(D, "subs_all.json"), "w"), indent=1)
