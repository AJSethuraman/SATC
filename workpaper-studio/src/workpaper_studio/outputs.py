"""What a released case becomes: a data feed where every value carries its state, and a workbook.

The feed never writes a missing value as zero: a missing value is `null` with state "missing". Fields a pack marks
personal are masked; the full value never leaves through the feed. The feed's shape is this application's own: the
receiving system's real format has not been supplied (DECISIONS D7), so treat it as a proposal.
"""
from __future__ import annotations

import csv
import json
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
            elif b["kind"] == "grid" and ev["tables"][b["id"]]["questions"] is not None:
                # every question is returned, answered or not, with why: the point is to see every result
                t = ev["tables"][b["id"]]
                rating, comment = t["cols"][0], (t["cols"][1] if len(t["cols"]) > 1 else None)
                for r in t["rows"]:
                    q = t["questions"][r["key"]]
                    na = q["applies"] == "No" or sec["applies"] == "No"
                    for col, v in ((rating, q["rating"]), (comment, q["comment"])):
                        if col is None:
                            continue
                        st = ("not_applicable" if na else "waiting" if q["applies"] == "Waiting" else
                              "entered" if not blank(v) else ("missing" if col is rating or q["need_comment"] else "blank"))
                        values.append({"path": f"g/{b['id']}/{r['key']}/{col['key']}", "label": f"{r['key']} {r['def'].get('label', '')} · {col['label']}",
                                       "section": s["title"], "question": r["key"], "group": r["def"].get("group"), "state": st,
                                       "value": None if na else v, "masked": False, "reason": "condition not met" if q["applies"] == "No" else None})
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
                        values.append({"path": f"g/{b['id']}/{r['key']}/{col['key']}", "label": f"{b['label']} · {r['label']} · {col['label']}",
                                       "section": s["title"], "state": "excluded" if r["excluded"] else ("calculated" if col.get("compute") else ("zero" if v == 0 else "entered")),
                                       "value": v, "masked": False, "reason": r["reason"]})
    for v in values:   # where each value came from: the master database, unchanged or corrected, or entered here
        m = c.get("master", {})
        if v["path"] in m:
            changed = v["value"] != (mask(m[v["path"]]) if v["masked"] else m[v["path"]])
            v.update(source="master", changed_from_master=changed, master_value=(mask(m[v["path"]]) if v["masked"] else m[v["path"]]) if changed else None)
        else:
            v.update(source="entered" if v["state"] not in ("calculated",) else "calculated", changed_from_master=False, master_value=None)
    calcs = [{"id": k, "method": v["code"], "status": v["status"], "result": v["value"], "verdict": v["verdict"],
              "limit": v["limit"] if v["confirmed"] else None, "parts": v["parts"], "missing": v["missing"], "disclosures": v["disclosures"]}
             for k, v in ev["calcs"].items()]
    return {"format": FEED_VERSION, "case": c["id"], "line_id": c.get("line_id"), "tool": c["tool"], "tool_version": c["version"], "pack_fingerprint": c["fingerprint"],
            "policy_version": c["policy_version"], "status": c["status"], "preparer": c["preparer"], "approved_by": c["approved_by"],
            "released_by": c.get("released_by"), "released_at": c.get("released_at"),
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


def wide_csv(c, fd):
    """Every answer of one case in one row, columns in the pack's order: the shape the master table loads.
    Built through the data mart's own view, so the file and the mart cannot disagree."""
    import sqlite3
    import tempfile
    from pathlib import Path
    from . import datamart
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "one.db"
        name = datamart.publish(p, c, fd)
        db = sqlite3.connect(str(p))
        names, rows = datamart.rows(db, f'SELECT * FROM "{name}"')
        db.close()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(names)
    w.writerows(rows)
    return buf.getvalue()


def workbook(c, path):
    """The case as the tool's workbook. Excluded rows are left out and values marked not applicable are left blank,
    because a workbook cell cannot carry a state; the About sheet lists both."""
    from .workbook import build_workbook
    data = _without_excluded(c)
    notes = [f"{p}: {'not applicable' if s['state'] == 'na' else 'excluded'} ({s.get('reason')})" for p, s in sorted(c["states"].items())]
    conf = {k: {"policy": v["limit"], "confirmed": "Yes" if v["confirmed"] else "No", "by": v.get("by"), "date": v.get("date")} for k, v in c["policy"].items()}
    pack = json.loads(json.dumps(c["pack"].data))
    pack["org"]["lists"] = c.get("lists") or pack["org"]["lists"]
    pack["_notes"] = notes
    pack["_case"] = c["id"]
    pack["_review"] = review_rows(c)
    for _, b in c["pack"].blocks():         # personal values leave masked, in the workbook as in the feed
        if b["kind"] == "field" and b.get("personal") and not blank(data.get(b["id"])):
            data[b["id"]] = mask(data[b["id"]])
    return build_workbook(pack, data, conf, path, f"case {c['id']}, pack {c['fingerprint']}")


def review_rows(c):
    titles = {x["id"]: x["title"] for x in c["pack"].sections}
    rows = []
    for e in c["exceptions"].values():
        calc = c["eval"]["calcs"].get(e["calc"], {})
        rows.append(["Exception", f'{calc.get("name", e["calc"])}: {calc.get("display", "")} ({calc.get("verdict", "")})', f'{e["reason"]}. {e["note"]}',
                     e["by"], e["at"], f'Acknowledged by {e["ack"]["by"]}, {e["ack"]["at"]}' if e["ack"] else "Not acknowledged"])
    for p in c["points"].values():
        text = p["text"] + "".join(f'\nAnswer ({r["by"]}): {r["text"]}' for r in p["replies"])
        rows.append(["Review point", f'{p["id"]}, {titles.get(p["section"], p["section"])}', text, p["by"], p["at"],
                     f'Cleared by {p.get("cleared_by")}' if not p["open"] else "Open"])
    for e in c["events"]:
        if e["kind"] in ("submitted", "returned", "approved", "released"):
            rows.append(["Sign-off", e["kind"].capitalize(), "", e["actor"], e["at"], ""])
    return rows


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
