import sys,json,urllib.request,urllib.parse,time
sys.path.insert(0,sys.argv[1]); import fields
F=fields.all_fields()
BASE="https://api.fdic.gov/banks/financials"
def get(params):
    url=BASE+"?"+urllib.parse.urlencode(params)
    for a in range(4):
        try:
            with urllib.request.urlopen(url,timeout=300) as r: return url,json.loads(r.read().decode())
        except Exception as e:
            time.sleep(5*(a+1)); err=e
    raise err
res={};urls=[]
for q in sys.argv[3:]:
    rows={}
    for i in range(0,len(F),100):
        chunk=F[i:i+100]; off=0; stated=None
        while True:
            url,p=get({"filters":"REPDTE:%s"%q,"fields":"CERT,REPDTE,"+",".join(chunk),"sort_by":"CERT","sort_order":"ASC","limit":"10000","offset":str(off),"format":"json"})
            urls.append(url); stated=p["meta"]["total"]
            got=[r["data"] for r in p["data"]]
            for d in got: rows.setdefault(d["CERT"],{}).update(d)
            if len(got)<10000: break
            off+=10000
        assert len(rows)==stated,(q,len(rows),stated)
    agg={}
    for f in F:
        vals=[r[f] for r in rows.values() if f in r and r[f] is not None]
        agg[f]={"sum":sum(vals) if vals else None,"n":len(vals),"nz":sum(1 for v in vals if v)}
    res[q]={"filers":len(rows),"agg":agg}
    print(q,len(rows),flush=True)
json.dump({"urls":urls,"res":res},open(sys.argv[2],"w"))
