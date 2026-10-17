# Fetch label linkbases for instances where a bank's commercial category members change; map member -> standard label.
import json, os, sys, re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__)); from sec import get; from pick import pick
LINK="{http://www.xbrl.org/2003/linkbase}"; XLINK="{http://www.w3.org/1999/xlink}"
D = sys.argv[1]; v = json.load(open(os.path.join(D, "verdicts2.json")))
os.makedirs(os.path.join(D, "labs"), exist_ok=True); os.makedirs(os.path.join(D, "labdl"), exist_ok=True)
sel = []
for t, es in v.items():
    prev = None
    for i, e in enumerate(es):
        c = tuple(e.get("ccats", []))
        extra = len(sys.argv) > 2 and e.get("verdict") not in (None, "NONE") and (e["period"][5:7] == "12" or e["period"] in sys.argv[2].split(","))
        if e.get("verdict") and (c != prev or i == len(es) - 1 or extra): sel.append((t, e))
        if e.get("verdict"): prev = c
def parse(path):
    root = ET.parse(path).getroot(); out = {}
    for lk in root.iter(LINK + "labelLink"):
        loc, lab = {}, {}
        for el in lk:
            ty = el.get(XLINK + "type")
            if ty == "locator": loc[el.get(XLINK + "label")] = el.get(XLINK + "href").split("#")[1]
            elif ty == "resource": lab.setdefault(el.get(XLINK + "label"), []).append((el.get(XLINK + "role", "").split("/")[-1], el.text))
        for el in lk:
            if el.get(XLINK + "type") == "arc" and el.get(XLINK + "from") in loc and el.get(XLINK + "to") in lab:
                out.setdefault(loc[el.get(XLINK + "from")], []).extend(lab[el.get(XLINK + "to")])
    return out
def one(x):
    t, e = x
    outp = os.path.join(D, "labs", e["acc"] + ".json")
    if os.path.exists(outp): return
    r = pick(D, e["acc"]); labs = r["lab"] if r else []
    if not labs: json.dump({"err": "no _lab.xml in filing index"}, open(outp, "w")); return
    base = e["url"].rsplit("/", 1)[0] + "/"
    tmp = os.path.join(D, "labdl", e["acc"] + ".xml")
    try:
        open(tmp, "wb").write(get(base + labs[0]))
        m = parse(tmp)
        want = set(e.get("ccats", []))
        for k in list(e.get("dimrows", {})) + list(e.get("ratrows", {})):
            for p in k.split("|"):
                if "=" in p: want.add(p.split("=")[1].split(" ")[0])
        res = {}
        for w in want:
            pre, _, loc = w.partition(":")
            for key in (pre + "_" + loc, w):
                if key in m: res[w] = m[key]; break
        json.dump({"lab_url": base + labs[0], "labels": res}, open(outp, "w"), indent=0)
        print("ok", t, e["period"], len(res), flush=True)
    except Exception as ex:
        json.dump({"err": repr(ex)}, open(outp, "w")); print("ERR", t, e["period"], ex, flush=True)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
print(len(sel))
with ThreadPoolExecutor(3) as ex: list(ex.map(one, sel))
