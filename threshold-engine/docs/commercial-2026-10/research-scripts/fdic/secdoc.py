import urllib.request, re, html, sys, time
import os; UA={'User-Agent': os.environ['SEC_USER_AGENT']}  # SEC requires a contact; never stored
for line in sys.stdin:
    if not line.strip(): continue
    label,cik,aid,pat=line.rstrip('\n').split('|',3)
    acc,fn=aid.split(':')
    u='https://www.sec.gov/Archives/edgar/data/%d/%s/%s'%(int(cik),acc.replace('-',''),fn)
    t=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read().decode('utf-8','replace')
    t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
    print('==',label,u)
    for m in list(re.finditer(pat,t,flags=re.I))[:3]:
        print('   ...',t[max(0,m.start()-250):m.end()+250])
    time.sleep(0.4)
