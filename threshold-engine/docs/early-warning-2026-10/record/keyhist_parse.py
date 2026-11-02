import re, sys, json, collections
from pathlib import Path
from xml.etree import ElementTree as ET
X = "{http://www.xbrl.org/2003/instance}"; D = "{http://xbrl.org/2006/xbrldi}"
out = {}
for f in sorted(Path(sys.argv[1]).glob("20*.xml")):
    date = f.stem
    t = ET.parse(f).getroot()
    ctx = {}
    for c in t.iter(X + "context"):
        dims = {m.get("dimension"): m.text for m in c.iter(D + "explicitMember")}
        inst = c.find(".//" + X + "instant")
        if inst is not None and inst.text == date and any("FICO" in (v or "").upper() for v in dims.values()):
            ctx[c.get("id")] = dims
    g = collections.defaultdict(lambda: collections.defaultdict(dict))
    for e in t:
        dims = ctx.get(e.get("contextRef"))
        if dims is None or not (e.text or "").strip():
            continue
        concept = e.tag.split("}")[1]
        band_dim = next(k for k, v in dims.items() if "FICO" in v.upper())
        band = dims[band_dim].split(":")[1]
        cls = " / ".join(v.split(":")[1].replace("Member", "") for k, v in sorted(dims.items()) if k != band_dim)
        g[cls][band][concept] = float(e.text)
    rec = {}
    for cls, bands in g.items():
        def amt(cs):
            for tot in ("FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss",
                        "FinancingReceivableRecordedInvestment", "LoansAndLeasesReceivableGrossCarryingAmount",
                        "NotesReceivableGross", "LoansReceivableGrossCarryingAmount", "LoansAndLeasesReceivableNetOfDeferredIncome"):
                if tot in cs:
                    return cs[tot], tot
            vs = {k: v for k, v in cs.items() if "Originated" in k or "Revolving" in k}
            return (sum(vs.values()), "sum of vintages") if vs else (None, ",".join(cs))
        rec[cls] = {b: amt(cs) for b, cs in bands.items()}
    out[date] = rec
json.dump(out, open(Path(sys.argv[1]) / "fico.json", "w"), indent=1)
for d in ("2018-06-30", "2019-12-31", "2020-03-31", "2022-12-31", "2026-06-30"):
    print("==", d)
    for cls, bands in out.get(d, {}).items():
        print("   ", cls, {b: (round(v / 1e6) if v else v, how[:30]) for b, (v, how) in bands.items()})
