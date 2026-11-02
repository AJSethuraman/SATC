import json, statistics, sys, csv, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
from threshold_engine.scale import typical_yearly_move, level_spread
D=json.load(open(sys.argv[1])); CATS=D["cats"]
def lab(d): return f"{d[:4]}Q{(int(d[4:6])-1)//3+1}"
def num(x): return None if x is None else float(x)
def series(rows, cat, kind):
    bal,dr,cr,na,p9,p3=CATS[cat]; ds=sorted(rows); out=[]
    for i,d in enumerate(ds):
        r=rows[d]
        if kind=="nco":
            if i<3: continue
            w=[rows[x] for x in ds[i-3:i+1]]
            if any(num(x.get(dr)) is None or num(x.get(cr)) is None or num(x.get(bal)) is None for x in w): continue
            avg=sum(num(x[bal]) for x in w)/4
            if avg<=0: continue
            out.append((lab(d),100*sum(num(x[dr])-num(x[cr]) for x in w)/avg))
        elif kind=="qann":  # quarterly annualized, avg of two quarter-ends, for Fed compare
            if i<1: continue
            p=rows[ds[i-1]]
            if None in (num(r.get(dr)),num(r.get(cr)),num(r.get(bal)),num(p.get(bal))): continue
            out.append((lab(d),400*(num(r[dr])-num(r[cr]))/((num(r[bal])+num(p[bal]))/2)))
        else:
            f={"na":na,"p9":p9,"p3":p3}[kind]
            if num(r.get(f)) is None or not num(r.get(bal)): continue
            out.append((lab(d),100*num(r[f])/num(r[bal])))
    return out
def stats(s, start=None):
    s=[x for x in s if start is None or x[0]>=start]
    if len(s)<9: return None
    v=[x[1] for x in s]; med=statistics.median(v); sp=level_spread(v); mv=typical_yearly_move(v)
    wi=max(range(len(v)),key=lambda i:v[i])
    return dict(n=len(v),first=s[0][0],last=s[-1][0],median=med,move=mv,spread=sp,worst=v[wi],worstq=s[wi][0],
                latest=v[-1],zmax=(v[wi]-med)/sp if sp else None)
res={}
for who,rows in [("Industry",D["industry"])]+[(k,v) for k,v in D["banks"].items()]:
    for cat in CATS:
        for kind in ("nco","na"):
            s=series(rows,cat,kind)
            res[(who,cat,kind)]=s
json.dump({"|".join(k):v for k,v in res.items()},open("series.json","w"))
# Table 1: industry and KeyBank, windows
print("who|cat|measure|window|n|first|median|move|spread|worst|worstq|latest|zmax")
for who in ("Industry","KeyBank"):
    for cat in CATS:
        for kind in ("nco","na"):
            for start in (None,"2006Q4","2014Q1"):
                st=stats(res[(who,cat,kind)],start)
                if not st: print(who,cat,kind,start,"too short",sep="|"); continue
                print("|".join(str(x) for x in [who,cat,kind,start or "all",st["n"],st["first"],round(st["median"],3),
                      None if st["move"] is None else round(st["move"],3),round(st["spread"],3),round(st["worst"],3),st["worstq"],round(st["latest"],3),
                      None if st["zmax"] is None else round(st["zmax"],1)]))
