"""Pull industry sums (aggregation) and per-bank rows for commercial categories."""
import json, urllib.request, urllib.parse, time, sys
OUT = sys.argv[1]
CATS = {  # name: (balance, quarterly gross, quarterly recov, nonaccrual, pd90, pd30)
 "C&I": ("LNCI","DRCIQ","CRCIQ","NACI","P9CI","P3CI"),
 "Construction": ("LNRECONS","DRRECONQ","CRRECONQ","NARECONS","P9RECONS","P3RECONS"),
 "Multifamily": ("LNREMULT","DRREMULQ","CRREMULQ","NAREMULT","P9REMULT","P3REMULT"),
 "Nonfarm nonres": ("LNRENRES","DRRENRSQ","CRRENRSQ","NARENRES","P9RENRES","P3RENRES"),
 "Farmland": ("LNREAG","DRREAGQ","CRREAGQ","NAREAG","P9REAG","P3REAG"),
 "Leases": ("LS","DRLSQ","CRLSQ","NALS","P9LS","P3LS"),
}
FIELDS = sorted({f for v in CATS.values() for f in v})
def get(params):
    url = "https://api.fdic.gov/banks/financials?" + urllib.parse.urlencode(params)
    for a in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as r: return json.loads(r.read())
        except Exception as e:
            time.sleep(5*(a+1)); err=e
    raise err
def qends(y0,y1):
    for y in range(y0,y1+1):
        for md in ("0331","0630","0930","1231"):
            d=f"{y}{md}"
            if d<="20260630": yield d
ind={}
for d in qends(1991,2026):
    j=get({"filters":f"REPDTE:{d}","agg_by":"REPDTE","agg_sum_fields":",".join(FIELDS),"agg_limit":1,"limit":1})
    row=j["data"][0]["data"]; ind[d]={f:row.get("sum_"+f) for f in FIELDS}; ind[d]["count"]=row["count"]
banks={}
peers=json.load(open(sys.argv[2]))["banks"]
for b in peers:
    j=get({"filters":f"CERT:{b['cert']} AND REPDTE:[20050101 TO 20260630]","fields":"CERT,REPDTE,"+",".join(FIELDS),"limit":10000,"sort_by":"REPDTE","sort_order":"ASC"})
    banks[b["short"]]={r["data"]["REPDTE"]:r["data"] for r in j["data"]}
json.dump({"cats":CATS,"industry":ind,"banks":banks},open(OUT,"w"))
print(len(ind), {k:len(v) for k,v in banks.items()})
