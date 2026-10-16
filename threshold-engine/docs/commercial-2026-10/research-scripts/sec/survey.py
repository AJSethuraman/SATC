import sys, os, re, json, glob
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
XBRLI="{http://www.xbrl.org/2003/instance}"; XBRLDI="{http://xbrl.org/2006/xbrldi}"
LINK="{http://www.xbrl.org/2003/linkbase}"; XLINK="{http://www.w3.org/1999/xlink}"
D=sys.argv[1]; PERIOD="2026-06-30"
def labels(path):
    root=ET.parse(path).getroot(); out={}
    for lk in root.iter(LINK+"labelLink"):
        loc,lab={},{}
        for el in lk:
            t=el.get(XLINK+"type")
            if t=="locator": loc[el.get(XLINK+"label")]=el.get(XLINK+"href").split("#")[1].replace("_",":",1)
            elif t=="resource" and el.get(XLINK+"role","").endswith("/label"): lab[el.get(XLINK+"label")]=el.text
        for el in lk:
            if el.get(XLINK+"type")=="arc" and el.get(XLINK+"from") in loc and el.get(XLINK+"to") in lab:
                out[loc[el.get(XLINK+"from")]]=lab[el.get(XLINK+"to")]
    return out
CQ=re.compile(r"CreditAssessment|CreditQuality|RiskRating|Grade|Rating|Criticized|Classified",re.I)
res={}
for t in sorted(os.listdir(D)):
    fd=os.path.join(D,t)
    if not os.path.isdir(fd): continue
    inst=glob.glob(fd+"/*_htm.xml")[0]; lab=labels(glob.glob(fd+"/*_lab.xml")[0])
    nsmap={}
    for _,(p,u) in ET.iterparse(inst,events=["start-ns"]): nsmap.setdefault(u,p)
    root=ET.parse(inst).getroot()
    ctx={}
    for c in root.iter(XBRLI+"context"):
        i=c.find(".//"+XBRLI+"instant")
        if i is None or i.text.strip()!=PERIOD: continue
        dims=tuple(sorted((m.get("dimension"),m.text.strip()) for m in c.iter(XBRLDI+"explicitMember")))
        typed=[m.get("dimension") for m in c.iter(XBRLDI+"typedMember")]
        ctx[c.get("id")]=(dims,typed)
    facts=[]
    for el in root:
        cr=el.get("contextRef")
        if cr not in ctx or el.text is None: continue
        ns,loc=el.tag[1:].split("}"); q="%s:%s"%(nsmap.get(ns,ns),loc)
        if "FinancingReceivable" not in q and "Loans" not in q and "Loan" not in q: continue
        dims,typed=ctx[cr]
        try: v=float(el.text)
        except: continue
        facts.append((q,dims,typed,v))
    # CQ axes
    cqfacts=[f for f in facts if any(CQ.search(a) for a,_ in f[1])]
    axes=Counter(a for f in cqfacts for a,_ in f[1])
    cqmembers=Counter(m for f in cqfacts for a,m in f[1] if CQ.search(a))
    other=Counter((a,m) for f in cqfacts for a,m in f[1] if not CQ.search(a))
    concepts=Counter(f[0] for f in cqfacts)
    typed=Counter(x for f in cqfacts for x in f[2])
    r={"axes":dict(axes),"cq_members":{m:(lab.get(m,""),n) for m,n in cqmembers.items()},
       "other_members":{"%s|%s"%(a,m):(lab.get(m,""),n) for (a,m),n in other.items()},
       "concepts":dict(concepts),"typed":dict(typed),"n":len(cqfacts)}
    res[t]=r
    print("=====",t,len(cqfacts))
    print(" AXES:",dict(axes)); print(" TYPED:",dict(typed))
    print(" CQ MEMBERS:"); [print("   ",m,"|",lab.get(m,""),n) for m,n in cqmembers.most_common()]
    print(" OTHER AXIS MEMBERS:"); [print("   ",a.split(":")[1],"|",m,"|",lab.get(m,""),n) for (a,m),n in sorted(other.items())]
    print(" CONCEPTS:"); [print("   ",c,n) for c,n in concepts.most_common()]
json.dump(res,open(os.path.join(D,"survey.json"),"w"),indent=1)
