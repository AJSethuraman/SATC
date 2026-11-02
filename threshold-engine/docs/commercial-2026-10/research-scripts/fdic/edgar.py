import json, urllib.request, urllib.parse, sys, time
import os; UA={'User-Agent': os.environ['SEC_USER_AGENT']}  # SEC requires a contact; never stored
ciks={'Wells':'0000072971','PNC':'0000713676','Truist':'0000092230','USB':'0000036104','Key':'0000091576','FifthThird':'0000035527','Huntington':'0000049196','MT':'0000036270','Citizens':'0000759944','FCB':'0000798941','JPM':'0000019617','CapOne':'0000927628','Regions':'0001281761','Zions':'0000109380','BofA':'0000070858','Citi':'0000831001'}
out={}
for name,cik in ciks.items():
    hits=[]
    for start in (0,100,200):
        q={'q':'"Completion of Acquisition or Disposition of Assets"','forms':'8-K','ciks':cik,'startdt':'2006-01-01','enddt':'2026-10-15','from':start}
        u='https://efts.sec.gov/LATEST/search-index?'+urllib.parse.urlencode(q)
        d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60))
        h=d['hits']['hits']
        for x in h:
            s=x['_source']
            if '2.01' in (s.get('items') or []):
                hits.append((s.get('period_ending'),s.get('file_date'),x['_id']))
        if len(h)<100: break
        time.sleep(0.3)
    out[name]=sorted(set(hits))
    time.sleep(0.3)
json.dump(out,open(sys.argv[1],'w'),indent=1)
for k,v in out.items():
    print(k)
    for p in v: print('  ',p)
