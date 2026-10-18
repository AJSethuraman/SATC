# Fact-level dump of every monetary fact carrying a member on a credit-quality axis. Read-only.
import re, sys, json
import xml.etree.ElementTree as ET
from analyze import CQ, EXT, local, XBRLI, XBRLDI
def run(path):
    nsmap = {}; ctx = {}; facts = []; dei = {}
    for ev, el in ET.iterparse(path, events=("start-ns", "end")):
        if ev == "start-ns":
            p, u = el; nsmap.setdefault(u, p); continue
        tag = el.tag
        if tag == XBRLI + "context":
            inst = el.find(".//" + XBRLI + "instant"); end = el.find(".//" + XBRLI + "endDate")
            d = (inst.text if inst is not None else (end.text if end is not None else "")).strip()
            mem = {m.get("dimension"): m.text.strip() for m in el.iter(XBRLDI + "explicitMember")}
            ctx[el.get("id")] = (d, mem); el.clear(); continue
        if tag.startswith("{") and not tag.startswith(XBRLI) and el.get("contextRef"):
            ns, loc = tag[1:].split("}")
            q = "%s:%s" % (nsmap.get(ns, ns), loc)
            if loc in ("DocumentPeriodEndDate", "DocumentType"):
                dei[loc] = (el.text or "").strip()
            elif el.get("unitRef") and el.text and el.text.strip():
                facts.append((q, el.get("contextRef"), el.text.strip(), el.get("unitRef")))
            el.clear()
    cq_axes = set()
    for d, mem in ctx.values():
        for a, m in mem.items():
            if CQ.search(local(m)) or EXT.search(local(m)): cq_axes.add(a)
    out = []
    for q, c, v, u in facts:
        if c not in ctx: continue
        d, mem = ctx[c]
        cq = {a: m for a, m in mem.items() if a in cq_axes}
        if not cq: continue
        oth = {a: m for a, m in mem.items() if a not in cq_axes}
        out.append([d, q, oth, cq, v, u])
    return {"dei": dei, "cq_axes": sorted(cq_axes), "facts": out}
