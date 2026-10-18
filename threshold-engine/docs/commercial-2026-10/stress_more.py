import json, csv, statistics, os
FRED=os.path.join(os.path.dirname(os.path.abspath(__file__)),"fred")
D=json.load(open("pull.json")); C=D["cats"]; I=D["industry"]; B=D["banks"]
k=B["KeyBank"]["20260630"]
print("KeyBank 2026Q2 multifamily: bal",k["LNREMULT"],"NA",k["NAREMULT"],"P9",k["P9REMULT"],"DRQ",k["DRREMULQ"],"CRQ",k["CRREMULQ"])
for d in ("20250630","20250930","20251231","20260331"): print(d, B["KeyBank"][d]["LNREMULT"], B["KeyBank"][d]["NAREMULT"], B["KeyBank"][d]["DRREMULQ"])
# Fed compare: industry quarterly annualized NCO vs Fed NSA all banks
def fed(id):
    return {r["observation_date"]:float(r[id]) for r in csv.DictReader(open(os.path.join(FRED,f"{id}.csv"))) if r[id] not in ("",".")}
import os
ds=sorted(I)
def qann(cats):
    out={}
    for i in range(1,len(ds)):
        d,p=ds[i],ds[i-1]
        try:
            net=sum(float(I[d][C[c][1]])-float(I[d][C[c][2]]) for c in cats)
            bal=sum((float(I[d][C[c][0]])+float(I[p][C[c][0]]))/2 for c in cats)
        except TypeError: continue
        out[f"{d[:4]}-{int(d[4:6])-2:02d}-01"]=400*net/bal
    return out
for cats,fid in ((["C&I"],"CORBLACBN"),(["Construction","Multifamily","Nonfarm nonres"],"CORCREXFACBN"),(["Leases"],"CORLFRACBN"),(["Farmland"],"CORFLACBN")):
    if not os.path.exists(os.path.join(FRED,f"{fid}.csv")): print("no",fid); continue
    f=fed(fid); o=qann(cats); both=[x for x in o if x in f]
    diffs=[abs(round(o[x],2)-f[x]) for x in both]
    print(fid,len(both),"quarters; max abs diff",round(max(diffs),3),"; within 0.01:",sum(d<=0.0100001 for d in diffs),
          "; worst at",max(both,key=lambda x:abs(round(o[x],2)-f[x])))
# concentration of peer C&I, CRE at 2026Q2
big=["JPMorgan","Wells Fargo","Bank of America","Citi","Capital One"]
for cat,f in (("C&I","LNCI"),("CRE nonfarm","LNRENRES"),("Multifamily","LNREMULT"),("Construction","LNRECONS")):
    peers={n:float(v["20260630"][f] or 0) for n,v in B.items() if n!="KeyBank"}
    tot=sum(peers.values()); bigs=sum(peers[n] for n in big)
    print(cat,"peer total $bn",round(tot/1e6,1),"big5 share",round(100*bigs/tot,1),"%; industry share of peers",round(100*tot/float(I["20260630"][f]),1))
print("--- since 2006")
for cats,fid in ((["C&I"],"CORBLACBN"),(["Construction","Multifamily","Nonfarm nonres"],"CORCREXFACBN")):
    f=fed(fid); o=qann(cats); both=[x for x in o if x in f and x>="2006"]
    d=[o[x]-f[x] for x in both]
    print(fid,len(both),"mean",round(statistics.mean(d),3),"max abs",round(max(map(abs,d)),3))
# per-peer zmax C&I and nonfarm NCO since 2006Q4 and 2014Q1
import sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","src"))
from threshold_engine.scale import level_spread
S=json.load(open("series.json"))
for cat in ("C&I","Nonfarm nonres","Multifamily","Construction"):
  for start in ("2006Q4","2014Q1"):
    rows=[]
    for n in B:
        s=[v for q,v in S[f"{n}|{cat}|nco"] if q>=start]
        if len(s)<9: rows.append((n,None)); continue
        med=statistics.median(s); sp=level_spread(s)
        rows.append((n, round(statistics.median(s),3), round((max(s)-med)/sp,1) if sp else None, round(max(s),2)))
    print(cat,start,rows)
