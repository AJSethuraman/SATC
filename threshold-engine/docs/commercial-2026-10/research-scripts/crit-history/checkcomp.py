# Re-fetch an instance and report, for credit-quality facts at a given date, whether contexts are instants, with sample values.
import sys, os, re
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__)); from sec import get; from analyze import CQ, local
XBRLI = "{http://www.xbrl.org/2003/instance}"; XBRLDI = "{http://xbrl.org/2006/xbrldi}"
url, date, tmp = sys.argv[1], sys.argv[2], sys.argv[3]
open(tmp, "wb").write(get(url))
ctx = {}; out = []; nsmap = {}
for ev, el in ET.iterparse(tmp, events=("start-ns", "end")):
    if ev == "start-ns": nsmap.setdefault(el[1], el[0]); continue
    if el.tag == XBRLI + "context":
        i = el.find(".//" + XBRLI + "instant"); s = el.find(".//" + XBRLI + "startDate"); e = el.find(".//" + XBRLI + "endDate")
        ctx[el.get("id")] = (("I", i.text.strip()) if i is not None else ("D", s.text.strip() + ".." + e.text.strip()), {m.get("dimension"): m.text.strip() for m in el.iter(XBRLDI + "explicitMember")})
    elif el.get("contextRef") in ctx and el.get("unitRef"):
        (k, d), mem = ctx[el.get("contextRef")]
        if d.endswith(date) and any((CQ.search(local(m)) or re.search(r"ExternalCreditRating|InvestmentGrade", m)) for m in mem.values()) and re.search(r"Commercial|Industrial|Wholesale|RealEstate|Realestate|Construction", " ".join(mem.values()) + el.tag):
            ns, loc = el.tag[1:].split("}")
            out.append((k, d, nsmap.get(ns, ns) + ":" + loc, {local(a): local(m) for a, m in mem.items()}, el.text))
os.remove(tmp)
kinds = {}
for o in out: kinds[o[0]] = kinds.get(o[0], 0) + 1
print(url, date, "facts:", len(out), "context kinds:", kinds)
for o in out[:int(sys.argv[4]) if len(sys.argv) > 4 else 6]: print("  ", o)
