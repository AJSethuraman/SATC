import json, urllib.request, urllib.parse, sys, time
import os; UA={'User-Agent': os.environ['SEC_USER_AGENT']}  # SEC requires a contact; never stored
for line in sys.stdin:
    if not line.strip(): continue
    label,cik,q,start,end,forms=line.rstrip('\n').split('|')
    p={'q':q,'startdt':start,'enddt':end}
    if cik: p['ciks']=cik
    if forms: p['forms']=forms
    u='https://efts.sec.gov/LATEST/search-index?'+urllib.parse.urlencode(p)
    d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60))
    print('==',label,d['hits']['total']['value'])
    for x in d['hits']['hits'][:6]:
        s=x['_source']; print('  ',s.get('file_date'),s.get('period_ending'),s.get('form'),s.get('items'),x['_id'],s.get('display_names',[''])[0][:40])
    time.sleep(0.4)
