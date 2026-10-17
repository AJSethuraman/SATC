# Summarise credit-quality-category facts in one XBRL instance (a file path). Read-only.
import re, sys, json
import xml.etree.ElementTree as ET
XBRLI = "{http://www.xbrl.org/2003/instance}"; XBRLDI = "{http://xbrl.org/2006/xbrldi}"
CQ = re.compile(r"(Pass(?![a-z])(?!Through|Thru)|SpecialMention|Substandard|Doubtful|Criticized|Criticised|Classified|Olem|OLEM|EspeciallyMentioned|Watch(?![a-z])|WatchList|Noncriticized|NonCriticized)")
EXT = re.compile(r"ExternalCreditRating|InvestmentGrade", re.I)
LOANISH = re.compile(r"Loan|Lease|Receivable|Financing|Credit|Exposure", re.I)
def local(q): return q.split(":", 1)[-1]
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
            typed = [m.get("dimension") for m in el.iter(XBRLDI + "typedMember")]
            ctx[el.get("id")] = (d, inst is not None, mem, typed); el.clear(); continue
        if tag.startswith("{") and not tag.startswith(XBRLI) and el.get("contextRef"):
            ns, loc = tag[1:].split("}")
            q = "%s:%s" % (nsmap.get(ns, ns), loc)
            if loc in ("DocumentPeriodEndDate", "DocumentFiscalYearFocus", "DocumentFiscalPeriodFocus", "DocumentType", "AmendmentFlag"):
                dei[loc] = (el.text or "").strip()
            elif el.get("unitRef") and el.text and el.text.strip():
                c = el.get("contextRef")
                facts.append((q, c, el.text.strip()))
            el.clear()
    # credit-quality axes: any axis carrying a member whose local name matches CQ
    cq_axes = set(); ext_axes = set()
    for d, isinst, mem, typed in ctx.values():
        for a, m in mem.items():
            if CQ.search(local(m)): cq_axes.add(a)
            if EXT.search(local(a)) or EXT.search(local(m)): ext_axes.add(a)
    pe = dei.get("DocumentPeriodEndDate", "")
    out = {"dei": dei, "cq_axes": sorted(cq_axes), "ext_axes": sorted(ext_axes), "dates": {}}
    per_date = {}
    for q, c, v in facts:
        if c not in ctx: continue
        d, isinst, mem, typed = ctx[c]
        cqm = {a: m for a, m in mem.items() if a in cq_axes}
        exm = {a: m for a, m in mem.items() if a in ext_axes}
        if not cqm and not exm: continue
        if not LOANISH.search(local(q)): continue
        r = per_date.setdefault(d, {"n": 0, "cq_members": {}, "ext_members": {}, "other": {}, "concepts": {}, "typed": {}, "matrix": {}})
        r["n"] += 1
        for a, m in cqm.items(): r["cq_members"].setdefault(m, set()).add(a)
        for a, m in exm.items(): r["ext_members"].setdefault(m, set()).add(a)
        for a, m in mem.items():
            if a not in cq_axes and a not in ext_axes: r["other"].setdefault(a, set()).add(m)
        for t in typed: r["typed"][t] = r["typed"].get(t, 0) + 1
        r["concepts"][q] = r["concepts"].get(q, 0) + 1
        if cqm and any(CQ.search(local(m)) for m in cqm.values()):
            k = "|".join(sorted("%s=%s" % (local(a), m) for a, m in mem.items() if a not in cq_axes))
            r["matrix"].setdefault(k, set()).update(cqm.values())
    for d, r in per_date.items():
        r["cq_members"] = {m: sorted(a) for m, a in r["cq_members"].items()}
        r["ext_members"] = {m: sorted(a) for m, a in r["ext_members"].items()}
        r["other"] = {a: sorted(ms) for a, ms in r["other"].items()}
        r["matrix"] = {k: sorted(v) for k, v in r["matrix"].items()}
    out["dates"] = per_date
    out["n_facts"] = len(facts); out["n_ctx"] = len(ctx)
    return out
if __name__ == "__main__":
    r = run(sys.argv[1]); print(json.dumps(r, indent=1)[:6000])
