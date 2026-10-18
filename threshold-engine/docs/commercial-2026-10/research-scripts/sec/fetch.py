import json, time, urllib.request, sys, os
import os; UA = os.environ["SEC_USER_AGENT"]  # SEC requires a contact; never stored
D = sys.argv[1]
subs = json.load(open(os.path.join(D,"subs.json")))
def get(u):
    time.sleep(0.2)
    r = urllib.request.Request(u, headers={"User-Agent": UA})
    return urllib.request.urlopen(r, timeout=120).read()
for t, s in subs.items():
    form, period, filed, acc, prim = s["recent"][0]
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s/" % (s["cik"], acc.replace("-",""))
    names = [x["name"] for x in json.loads(get(base+"index.json"))["directory"]["item"]]
    want = [n for n in names if n.endswith("_htm.xml") or n.endswith("_lab.xml") or n.endswith("_pre.xml") or n == "FilingSummary.xml"]
    fd = os.path.join(D, t); os.makedirs(fd, exist_ok=True)
    for n in want:
        p = os.path.join(fd, n)
        if not os.path.exists(p):
            open(p,"wb").write(get(base+n))
    print(t, acc, want)
