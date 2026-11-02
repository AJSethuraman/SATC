"""What a released case becomes: a data feed where every value carries its state, and a workbook.

The feed never writes a missing value as zero: a missing value is `null` with state "missing". Fields a pack marks
personal are masked; the full value never leaves through the feed. The feed's shape is this application's own: the
receiving system's real format has not been supplied (DECISIONS D7), so treat it as a proposal.
"""
from __future__ import annotations

import csv
import io

from .methods import blank

FEED_VERSION = "workpaper-feed/0.1 (proposed; the receiving system's format is not yet known)"


def mask(v):
    s = str(v)
    return s[:1] + "•" * 4 if s else s


def feed(c):
    pack, ev = c["pack"], c["eval"]
    values = []
    for s in pack.sections:
        sec = next(x for x in ev["sections"] if x["id"] == s["id"])
        for b in s["blocks"]:
            if b["kind"] == "field":
                f = ev["fields"][b["id"]]
                state = {"empty": "missing" if b.get("req") else "blank"}.get(f["state"], f["state"])
                if sec["applies"] == "No":
                    state = "not_applicable_section"
                v = f["value"]
                values.append({"path": f"f/{b['id']}", "label": b["label"], "section": s["title"], "state": state,
                               "value": (mask(v) if b.get("personal") and not blank(v) else v), "masked": bool(b.get("personal")),
                               "reason": f.get("reason")})
            elif b["kind"] == "grid":
                t = ev["tables"][b["id"]]
                for r in t["rows"]:
                    for col in t["cols"]:
                        if col.get("compute"):
                            v = r["computed"].get(col["key"])
                        else:
                            v = r["cells"].get(col["key"])
                        if blank(v) and not r["excluded"]:
                            continue
                        values.append({"path": f"g/{b['id']}/{r['key']}/{col['key']}", "label": f"{b['label']}: {r['label']}: {col['label']}",
                                       "section": s["title"], "state": "excluded" if r["excluded"] else ("calculated" if col.get("compute") else ("zero" if v == 0 else "entered")),
                                       "value": v, "masked": False, "reason": r["reason"]})
    calcs = [{"id": k, "method": v["code"], "status": v["status"], "result": v["value"], "verdict": v["verdict"],
              "limit": v["limit"] if v["confirmed"] else None, "parts": v["parts"], "missing": v["missing"], "disclosures": v["disclosures"]}
             for k, v in ev["calcs"].items()]
    return {"format": FEED_VERSION, "case": c["id"], "tool": c["tool"], "tool_version": c["version"], "pack_fingerprint": c["fingerprint"],
            "policy_version": c["policy_version"], "status": c["status"], "preparer": c["preparer"], "approved_by": c["approved_by"],
            "sections": [{"id": s["id"], "title": s["title"], "status": s["status"]} for s in ev["sections"]],
            "values": values, "calculations": calcs,
            "exceptions": [{"calc": e["calc"], "reason": e["reason"], "note": e["note"], "by": e["by"], "acknowledged_by": (e["ack"] or {}).get("by")} for e in c["exceptions"].values()],
            "review_points": [{"id": p["id"], "section": p["section"], "text": p["text"], "raised_by": p["by"], "open": p["open"], "replies": len(p["replies"])} for p in c["points"].values()]}


def feed_csv(fd):
    """One row per value: the flat file a database load expects. Missing stays empty and says so in the state column."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["case", "tool_version", "path", "label", "state", "value", "reason"])
    for v in fd["values"]:
        w.writerow([fd["case"], fd["tool_version"], v["path"], v["label"], v["state"], "" if v["value"] is None else v["value"], v["reason"] or ""])
    for c in fd["calculations"]:
        w.writerow([fd["case"], fd["tool_version"], f"calc/{c['id']}", c["method"], c["status"], "" if c["result"] is None else c["result"], c["verdict"]])
    return buf.getvalue()


def workbook(c, path):
    """The case as the tool's workbook. Excluded rows are left out and values marked not applicable are left blank,
    because a workbook cell cannot carry a state; the About sheet lists both."""
    from .workbook import build_workbook
    data = _without_excluded(c)
    notes = [f"{p}: {'not applicable' if s['state'] == 'na' else 'excluded'} ({s.get('reason')})" for p, s in sorted(c["states"].items())]
    conf = {k: {"policy": v["limit"], "confirmed": "Yes" if v["confirmed"] else "No", "by": v.get("by"), "date": v.get("date")} for k, v in c["policy"].items()}
    pack = dict(c["pack"].data)
    pack["_notes"] = notes
    pack["_case"] = c["id"]
    return build_workbook(pack, data, conf, path, f"case {c['id']}, pack {c['fingerprint']}")


def _without_excluded(c):
    import json
    data = json.loads(json.dumps(c["data"]))
    for path, s in c["states"].items():
        if s["state"] == "na" and path.startswith("f/"):
            data.pop(path[2:], None)
        if s["state"] != "excluded":
            continue
        _, gid, rk = path.split("/")
        g = data.get(gid) or {}
        if "rows" in g and rk.isdigit() and int(rk) < len(g["rows"]):
            g["rows"][int(rk)] = {}
        elif rk in g:
            g[rk] = {}
    for g in data.values():
        if isinstance(g, dict) and "rows" in g:
            g["rows"] = [r for r in g["rows"] if r]
    return data
