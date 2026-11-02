"""Pull each FICO-disclosing bank's 10-Q and 10-K XBRL from SEC EDGAR since
2019Q4 and keep only the facts tagged with a FICO member at the filing's own
quarter-end: {cik: {date: [[concept, value, {dimension: member}], ...]}}.
The instance file is deleted once read; the facts are what is kept."""
import json, sys, time, urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

OUT = Path(sys.argv[1]); UA = sys.argv[2]
BANKS = {"91576": "KeyCorp", "70858": "Bank of America", "72971": "Wells Fargo", "713676": "PNC", "831001": "Citi",
         "19617": "JPMorgan", "1281761": "Regions", "759944": "Citizens", "49196": "Huntington", "1818874": "SoFi",
         "927628": "Capital One"}
X = "{http://www.xbrl.org/2003/instance}"; D = "{http://xbrl.org/2006/xbrldi}"


def get(url):
    for k in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception:
            time.sleep(5 * (k + 1))
    raise RuntimeError("could not fetch " + url)


def facts(raw, date):
    t = ET.fromstring(raw)
    ctx = {}
    for c in t.iter(X + "context"):
        dims = {m.get("dimension"): m.text for m in c.iter(D + "explicitMember")}
        inst = c.find(".//" + X + "instant")
        if inst is not None and inst.text == date and any("FICO" in (v or "").upper() or "FICO" in (k or "").upper()
                                                          for k, v in dims.items()):
            ctx[c.get("id")] = dims
    out = []
    for e in t:
        dims = ctx.get(e.get("contextRef"))
        if dims is None or not (e.text or "").strip():
            continue
        try:
            v = float(e.text)
        except ValueError:
            continue
        out.append([e.tag.split("}")[1], v, dims])
    return out


store = OUT / "facts.json"
data = json.loads(store.read_text()) if store.exists() else {}
for cik, name in BANKS.items():
    top = json.loads(get("https://data.sec.gov/submissions/CIK%010d.json" % int(cik)))["filings"]
    pages = [top["recent"]] + [json.loads(get("https://data.sec.gov/submissions/" + f["name"]))
                               for f in top.get("files", []) if f.get("filingTo", "9999") >= "2020-01-01"]
    rows = sorted({(subs["reportDate"][i], subs["accessionNumber"][i]) for subs in pages for i in range(len(subs["form"]))
                   if subs["form"][i] in ("10-Q", "10-K") and subs["reportDate"][i] >= "2019-12-31"})
    seen = {}
    for date, acc in rows:
        seen.setdefault(date, acc)          # the first filing for the quarter, not an amendment
    for date, acc in sorted(seen.items()):
        if date in data.get(cik, {}):
            continue
        base = "https://www.sec.gov/Archives/edgar/data/%s/%s/" % (int(cik), acc.replace("-", ""))
        names = [i["name"] for i in json.loads(get(base + "index.json"))["directory"]["item"]]
        inst = [n for n in names if n.endswith("_htm.xml")]
        if not inst:
            print(name, date, "no XBRL instance", flush=True)
            data.setdefault(cik, {})[date] = None
            continue
        f = facts(get(base + inst[0]), date)
        data.setdefault(cik, {})[date] = f
        store.write_text(json.dumps(data))
        print(name, date, len(f), "FICO facts", flush=True)
        time.sleep(1.2)
print("done")
