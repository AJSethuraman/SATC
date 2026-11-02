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
out={}
urls=[]
for cert in sys.argv[3:]:
    rows={}
    for i in range(0,len(F),100):
        chunk=F[i:i+100]
        url,p=get({"filters":"CERT:%s"%cert,"fields":"CERT,REPDTE,"+",".join(chunk),"sort_by":"REPDTE","sort_order":"ASC","limit":"1000","format":"json"})
        urls.append(url)
        for r in p["data"]:
            d=r["data"]; rows.setdefault(d["REPDTE"],{}).update(d)
    out[cert]=rows
json.dump({"urls":urls,"data":out},open(sys.argv[2],"w"))
print({c:len(v) for c,v in out.items()})
