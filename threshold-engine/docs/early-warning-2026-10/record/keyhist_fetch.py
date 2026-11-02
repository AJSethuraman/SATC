import json, sys, time, urllib.request
from pathlib import Path
out = Path(sys.argv[1]); ua = sys.argv[2]
rows = json.load(open(out / "filings.json"))
def get(url):
    for k in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            time.sleep(5 * (k + 1))
    raise RuntimeError("could not fetch " + url)
for date, form, acc, doc in rows:
    dest = out / ("%s.xml" % date)
    if dest.exists():
        continue
    base = "https://www.sec.gov/Archives/edgar/data/91576/%s/" % acc.replace("-", "")
    idx = json.loads(get(base + "index.json"))
    names = [i["name"] for i in idx["directory"]["item"]]
    inst = [n for n in names if n.endswith("_htm.xml")] or [n for n in names if n.endswith(".xml") and not any(s in n for s in ("_cal", "_def", "_lab", "_pre", "FilingSummary", "R"))]
    inst = [n for n in inst if not n.startswith("R")]
    if not inst:
        print(date, form, "NO INSTANCE", names[:12]); continue
    dest.write_bytes(get(base + inst[0]))
    print(date, form, inst[0], dest.stat().st_size)
    time.sleep(1.5)
