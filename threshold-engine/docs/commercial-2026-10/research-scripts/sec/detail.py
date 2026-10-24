import sys, os, re, json, glob
import xml.etree.ElementTree as ET
from collections import defaultdict
XBRLI="{http://www.xbrl.org/2003/instance}"; XBRLDI="{http://xbrl.org/2006/xbrldi}"
D=sys.argv[1]; T=sys.argv[2:] or sorted(x for x in os.listdir(D) if os.path.isdir(os.path.join(D,x)))
PERIOD="2026-06-30"
CQ=re.compile(r"InternalCreditAssessment|ExternalCreditRatingByGrouping",re.I)
VINT=re.compile(r"Originated|Revolving")
for t in T:
    fd=os.path.join(D,t); inst=glob.glob(fd+"/*_htm.xml")[0]
    nsmap={}
    for _,(p,u) in ET.iterparse(inst,events=["start-ns"]): nsmap.setdefault(u,p)
    root=ET.parse(inst).getroot(); ctx={}
    for c in root.iter(XBRLI+"context"):
        i=c.find(".//"+XBRLI+"instant")
        if i is None or i.text.strip()!=PERIOD: continue
        ctx[c.get("id")]=tuple(sorted((m.get("dimension").split(":")[1],m.text.strip()) for m in c.iter(XBRLDI+"explicitMember")))
    tab=defaultdict(dict); vint=defaultdict(set)
    for el in root:
        cr=el.get("contextRef")
        if cr not in ctx or el.text is None: continue
        ns,loc=el.tag[1:].split("}"); q="%s:%s"%(nsmap.get(ns,ns),loc)
        dims=ctx[cr]
        if not any(CQ.search(a) for a,_ in dims): continue
        g=[m for a,m in dims if CQ.search(a)][0]
        rest=tuple("%s"%(m.split(":")[1].replace("Member","")) for a,m in dims if not CQ.search(a))
        if VINT.search(q):
            vint[rest].add(g.split(":")[1].replace("Member",""))
        elif "FinancingReceivable" in q and "AllowanceForCreditLossExcl" not in q:
            try: tab[(q.split(":")[1][:60],rest)][g.split(":")[1].replace("Member","")]=round(float(el.text)/1e6)
            except: pass
    print("=====",t)
    for (q,rest),row in sorted(tab.items()):
        print("  %-60s %s\n      %s"%(q," / ".join(rest),row))
    print("  VINTAGE (concept facts with grade dims at %s):"%PERIOD)
    for rest,gs in sorted(vint.items()): print("     %s -> %s"%(" / ".join(rest),sorted(gs)))
