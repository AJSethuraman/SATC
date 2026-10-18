import json, time, urllib.request, sys, os
import os; UA = os.environ["SEC_USER_AGENT"]  # SEC requires a contact; never stored
D = sys.argv[1]
CIKS = {"KEY":91576,"CFG":759944,"PNC":713676,"TFC":92230,"FITB":35527,"HBAN":49196,"MTB":36270,"RF":1281761,
"ZION":109380,"FCNCA":798941,"USB":36104,"JPM":19617,"WFC":72971,"BAC":70858,"C":831001,"COF":927628}
def get(u):
    time.sleep(0.2)
    r = urllib.request.Request(u, headers={"User-Agent": UA})
    return urllib.request.urlopen(r, timeout=60).read()
out = {}
for t, cik in CIKS.items():
    sub = json.loads(get("https://data.sec.gov/submissions/CIK%010d.json" % cik))
    rec = sub["filings"]["recent"]
    qs = [i for i,f in enumerate(rec["form"]) if f in ("10-Q","10-Q/A","10-K")]
    latest = [ (rec["form"][i], rec["reportDate"][i], rec["filingDate"][i], rec["accessionNumber"][i], rec["primaryDocument"][i]) for i in qs[:3]]
    out[t] = {"cik": cik, "name": sub["name"], "sic": sub.get("sic"), "recent": latest}
    print(t, cik, sub["name"], sub.get("sic"), latest[:2])
json.dump(out, open(os.path.join(D, "subs.json"), "w"), indent=1)
