import json, urllib.request, urllib.parse, sys, time
hist=json.load(open(sys.argv[1])); roster={b['cert']:b['short'] for b in json.load(open(sys.argv[2]))['banks']}
ALLOW={211,215,216,217,221,222,223,224}; BRANCH={712}
F='CERT,REPDTE,LNLSGR,LNCI,LNRECONS,LNREMULT,LNRENRES,LNREAG,LNAG,LS,LNDEP,LNOTHER'
def get(cert, before):
    # last filing with REPDTE < before (YYYYMMDD)
    p={'filters':'CERT:%s AND REPDTE:[19900101 TO %s]'%(cert,before),'fields':F,'sort_by':'REPDTE','sort_order':'DESC','limit':1}
    u='https://api.fdic.gov/banks/financials?'+urllib.parse.urlencode(p)
    for i in range(4):
        try:
            d=json.load(urllib.request.urlopen(u,timeout=90)); break
        except Exception as e: time.sleep(3)
    return d['data'][0]['data'] if d['data'] else None
def qstart(eff):
    y,m=int(eff[:4]),int(eff[5:7]); qm=((m-1)//3)*3+1
    return '%04d%02d01'%(y,qm)
def prevday(s):
    import datetime
    d=datetime.date(int(s[:4]),int(s[4:6]),int(s[6:8]))-datetime.timedelta(days=1); return d.strftime('%Y%m%d')
rows=[]
for acq,hs in hist.items():
    for r in hs:
        code=r['CHANGECODE']
        if code not in ALLOW and code not in BRANCH: continue
        eff=r['EFFDATE'][:10]
        if eff<'2006-01-01': continue
        tgt=str(r.get('OUT_CERT'))
        cut=prevday(qstart(eff))
        t=get(tgt,cut) if code in ALLOW else None
        a=get(acq,cut)
        rows.append(dict(acq=acq,acqname=roster[acq],eff=eff,code=code,tgt=tgt,tname=r.get('OUT_INSTNAME'),t=t,a=a))
        time.sleep(0.2)
json.dump(rows,open(sys.argv[3],'w'),indent=1)
