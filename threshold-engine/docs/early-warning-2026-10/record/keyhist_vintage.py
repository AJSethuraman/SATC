import re, sys, json, collections
from pathlib import Path
from xml.etree import ElementTree as ET
X = "{http://www.xbrl.org/2003/instance}"; D = "{http://xbrl.org/2006/xbrldi}"
YEARS = {"YearOneOriginatedCurrentFiscalYear": 0, "YearTwoOriginatedFiscalYearBeforeCurrentFiscalYear": 1,
         "YearThreeOriginatedTwoYearsBeforeCurrentFiscalYear": 2, "YearFourOriginatedThreeYearsBeforeCurrentFiscalYear": 3,
         "YearFiveOriginatedFourYearsBeforeCurrentFiscalYear": 4, "OriginatedFiveOrMoreYearsBeforeCurrentFiscalYear": "prior", "OriginatedMoreThanFiveYearsBeforeCurrentFiscalYear": "prior",
         "Revolving": "revolving", "RevolvingConvertedToTermLoan": "converted"}
out = {}
for f in sorted(Path(sys.argv[1]).glob("20*.xml")):
    date = f.stem
    if date < "2020-03-31":
        continue
    t = ET.parse(f).getroot()
    ctx = {}
    for c in t.iter(X + "context"):
        dims = {m.get("dimension"): m.text for m in c.iter(D + "explicitMember")}
        inst = c.find(".//" + X + "instant")
        if inst is not None and inst.text == date and any("FICO" in (v or "").upper() for v in dims.values()):
            ctx[c.get("id")] = dims
    rec = collections.defaultdict(lambda: collections.defaultdict(float))
    for e in t:
        dims = ctx.get(e.get("contextRef"))
        if dims is None or not (e.text or "").strip():
            continue
        concept = e.tag.split("}")[1]
        key = None
        for suffix, k in YEARS.items():
            if concept.endswith(suffix) and "WriteOff" not in concept:
                key = k
        if key is None:
            continue
        band = next(v for v in dims.values() if "FICO" in v.upper()).split(":")[1].lower()
        band = "u660" if "lessthan660" in band else "660_749" if "660to749" in band else "750" if "750" in band else "none"
        cls = [v.split(":")[1] for v in dims.values() if "FICO" not in v.upper()][-1].replace("Member", "")
        vint = (int(date[:4]) - key) if isinstance(key, int) else key
        rec["%s|%s" % (cls, vint)][band] += float(e.text)
    out[date] = {k: dict(v) for k, v in rec.items()}
json.dump(out, open(Path(sys.argv[1]) / "vintage.json", "w"))
# print: home equity & other consumer by vintage at a few dates
for cls in ("HomeEquityLoan", "CreditCardReceivables", "OtherConsumerLoans", "ConsumerDirectLoans", "RealEstateResidentialMortgage"):
    print("==", cls)
    for date in ("2021-12-31", "2023-12-31", "2025-12-31", "2026-06-30"):
        row = []
        for k, b in sorted(out.get(date, {}).items()):
            c, v = k.split("|")
            if c != cls:
                continue
            sc = sum(x for kk, x in b.items() if kk != "none")
            if sc > 50e6:
                row.append("%s: $%.1fbn %.1f%%" % (v, sc / 1e9, 100 * b.get("u660", 0) / sc))
        if row:
            print("  ", date, " | ".join(row))
