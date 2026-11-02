import json, sys, os
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__)); from sec import get
D = sys.argv[1]; subs = json.load(open(os.path.join(D, "subs_all.json")))
os.makedirs(os.path.join(D, "idx"), exist_ok=True)
jobs = []
for t, s in subs.items():
    for f in s["filings"]:
        if f["filed"] >= "2009-04-01":
            jobs.append((t, s["cik"], f["acc"]))
def one(j):
    t, cik, acc = j
    p = os.path.join(D, "idx", acc + ".json")
    if os.path.exists(p): return
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s/" % (cik, acc.replace("-", ""))
    try:
        open(p, "wb").write(get(base + "index.json"))
    except Exception as e:
        print("ERR", t, acc, e)
with ThreadPoolExecutor(4) as ex: list(ex.map(one, jobs))
print(len(jobs))
