import sys,json,urllib.request,urllib.parse,time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,sys.argv[1]); import fields
F=fields.all_fields()
def q(filt,order):
    url="https://api.fdic.gov/banks/financials?"+urllib.parse.urlencode({"filters":filt,"fields":"CERT,REPDTE","sort_by":"REPDTE","sort_order":order,"limit":"1","format":"json"})
    for a in range(4):
        try:
            p=json.loads(urllib.request.urlopen(url,timeout=120).read().decode()); break
        except Exception as e:
            time.sleep(3*(a+1)); p=None
    d=p["data"]
    return url,(d[0]["data"]["REPDTE"] if d else None),p["meta"]["total"]
def one(f):
    u1,first,n=q("%s:[* TO *]"%f,"ASC")
    u2,firstnz,_=q("(%s:[1 TO *] OR %s:[* TO -1])"%(f,f),"ASC")
    u3,last,_=q("%s:[* TO *]"%f,"DESC")
    return f,{"first":first,"firstnz":firstnz,"last":last,"rows":n,"url_first":u1,"url_firstnz":u2}
with ThreadPoolExecutor(6) as ex: res=dict(ex.map(one,F))
json.dump(res,open(sys.argv[2],"w"),indent=0)
for f in F: print(f,res[f]["first"],res[f]["firstnz"],res[f]["last"],res[f]["rows"])
