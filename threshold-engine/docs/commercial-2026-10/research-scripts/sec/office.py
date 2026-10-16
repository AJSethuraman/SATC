import sys, os, re, glob
import xml.etree.ElementTree as ET
from collections import Counter
XBRLI="{http://www.xbrl.org/2003/instance}"; XBRLDI="{http://xbrl.org/2006/xbrldi}"
D=sys.argv[1]
for t in sorted(x for x in os.listdir(D) if os.path.isdir(os.path.join(D,x))):
    inst=glob.glob(os.path.join(D,t,"*_htm.xml"))[0]
    nsmap={}
    for _,(p,u) in ET.iterparse(inst,events=["start-ns"]): nsmap.setdefault(u,p)
    root=ET.parse(inst).getroot(); ctx={}
    for c in root.iter(XBRLI+"context"):
        i=c.find(".//"+XBRLI+"instant")
        per=i.text.strip() if i is not None else "dur"
        ctx[c.get("id")]=(per,tuple((m.get("dimension").split(":")[1],m.text.strip()) for m in c.iter(XBRLDI+"explicitMember")))
    hits=Counter()
    for el in root:
        cr=el.get("contextRef")
        if cr not in ctx: continue
        per,dims=ctx[cr]
        offm=[m for a,m in dims if re.search(r"office",m,re.I)]
        if offm:
            ns,loc=el.tag[1:].split("}")
            hits[(loc[:70],per," / ".join(m.split(":")[1] for a,m in dims))]+=1
    print("=====",t,len(hits))
    for (c,p,d),n in sorted(hits.items()):
        if p=="2026-06-30": print("   ",c,"|",d)
