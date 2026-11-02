import json, os, sys
D = sys.argv[1]; v = json.load(open(os.path.join(D, "verdicts2.json")))
sys.path.insert(0, os.path.dirname(__file__))
def disp(ls):
    if not ls: return "?"
    std = next((t for r, t in ls if r == "label"), "")
    other = sorted(set(t.strip() for r, t in ls if r not in ("label", "documentation") and t and t.strip() != std))
    return std.replace(" [Member]", "") + (" {" + " / ".join(other) + "}" if other else "")
for t, es in v.items():
    print("#####", t); prev = None
    for e in es:
        p = os.path.join(D, "labs", "%s.json" % e.get("acc", "x"))
        if not os.path.exists(p): continue
        L = json.load(open(p))
        if "err" in L: print("  ", e["period"], "ERR", L["err"]); continue
        cur = tuple("%s=%s" % (c.split(":")[1].replace("Member", ""), disp(L["labels"].get(c))) for c in e.get("ccats", []))
        if cur != prev: print("  ", e["period"], e["form"], e["verdict"], "|", "; ".join(cur))
        prev = cur
