import sys,json,urllib.request,urllib.parse
q=sys.argv[2]; fields=sys.argv[3]
rows=[];off=0
while True:
    url="https://api.fdic.gov/banks/financials?"+urllib.parse.urlencode({"filters":"REPDTE:%s"%q,"fields":"CERT,REPDTE,NAMEFULL,CALLFORM,"+fields,"sort_by":"CERT","sort_order":"ASC","limit":"10000","offset":str(off),"format":"json"})
    p=json.loads(urllib.request.urlopen(url,timeout=300).read().decode())
    got=[r["data"] for r in p["data"]]; rows+=got
    if len(got)<10000: break
    off+=10000
json.dump({"url":url,"rows":rows},open(sys.argv[1],"w")); print(q,len(rows))
