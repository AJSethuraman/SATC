import sys, os, glob, json
import xml.etree.ElementTree as ET
LINK="{http://www.xbrl.org/2003/linkbase}"; XLINK="{http://www.w3.org/1999/xlink}"
D=sys.argv[1]; sv=json.load(open(os.path.join(D,"survey.json")))
for t,r in sorted(sv.items()):
    mem=set(r["cq_members"]) | {k.split("|")[1] for k in r["other_members"] if "Class" in k or "Segment" in k}
    root=ET.parse(glob.glob(os.path.join(D,t,"*_lab.xml"))[0]).getroot(); out={}
    for lk in root.iter(LINK+"labelLink"):
        loc,lab={},{}
        for el in lk:
            ty=el.get(XLINK+"type")
            if ty=="locator": loc[el.get(XLINK+"label")]=el.get(XLINK+"href").split("#")[1].replace("_",":",1)
            elif ty=="resource": lab.setdefault(el.get(XLINK+"label"),[]).append((el.get(XLINK+"role").split("/")[-1],el.text))
        for el in lk:
            if el.get(XLINK+"type")=="arc" and loc.get(el.get(XLINK+"from")) in mem:
                out.setdefault(loc[el.get(XLINK+"from")],[]).extend(lab.get(el.get(XLINK+"to"),[]))
    print("=====",t)
    for m in sorted(mem):
        ls=[x for r_,x in out.get(m,[]) if r_ in ("terseLabel","label","verboseLabel")]
        print("  ",m.split(":")[1],"->"," || ".join(dict.fromkeys(ls)))
