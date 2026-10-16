import json, time, urllib.request, sys, os
import os; UA = os.environ["SEC_USER_AGENT"]  # SEC requires a contact; never stored
D = sys.argv[1]
subs = json.load(open(os.path.join(D,"subs.json")))
for t, s in subs.items():
    form, period, filed, acc, prim = s["recent"][0]
    p = os.path.join(D, t, prim)
    if os.path.exists(p): continue
    time.sleep(0.25)
    u = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s" % (s["cik"], acc.replace("-",""), prim)
    open(p,"wb").write(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=180).read())
    print(t, os.path.getsize(p))
