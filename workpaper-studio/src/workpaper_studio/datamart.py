"""The data mart: every released case's answers, results, exceptions, review points and actions, in one database
built for looking across cases rather than inside one.

The owner, 2 Nov 2026: "The feed has to return all answers - the point is to easily see results and it also allows
for checks on the outside stuff is done in addition to route cause analysis", and on the data mart: "it does not need
to work exactly like work it should work better if possible".

So, better than a copied master table:
  * one long table of answers, every one with its state (entered, zero, missing, not applicable, excluded, waiting)
    and where it came from (master database, corrected, entered), so an empty value always says why;
  * the master-table shape is a VIEW over it, generated from the tool's own pack: one row per case, one column per
    field, question and result. A new question is a new column with no development, and the view can never drift
    from the answers because it is not a copy of them;
  * results, exceptions, review points and every action in their own tables, for the outside checks and the
    root-cause questions ("which questions fail most, and what do the comments say?");
  * de-identified: it is built from the feed, where personal fields are already masked;
  * append-only: a case is published once, at release, and the database refuses to change or remove a row.
"""
from __future__ import annotations

import json
import re
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (case_id TEXT PRIMARY KEY, line_id TEXT, tool TEXT, tool_version TEXT, pack_fingerprint TEXT,
    policy_version TEXT, status TEXT, preparer TEXT, approved_by TEXT, released_by TEXT, released_at TEXT);
CREATE TABLE IF NOT EXISTS answers (case_id TEXT, path TEXT, section TEXT, question TEXT, question_group TEXT, label TEXT, state TEXT,
    value_text TEXT, value_num REAL, reason TEXT, source TEXT, changed_from_master INTEGER, master_value TEXT, PRIMARY KEY (case_id, path));
CREATE TABLE IF NOT EXISTS results (case_id TEXT, calc_id TEXT, method TEXT, status TEXT, value REAL, verdict TEXT, limit_value REAL,
    inputs_missing INTEGER, PRIMARY KEY (case_id, calc_id));
CREATE TABLE IF NOT EXISTS exceptions (case_id TEXT, calc_id TEXT, reason TEXT, note TEXT, recorded_by TEXT, acknowledged_by TEXT);
CREATE TABLE IF NOT EXISTS review_points (case_id TEXT, point_id TEXT, section TEXT, text TEXT, raised_by TEXT, still_open INTEGER, replies INTEGER);
CREATE TABLE IF NOT EXISTS actions (case_id TEXT, seq INTEGER, at TEXT, actor TEXT, kind TEXT, path TEXT, detail TEXT, PRIMARY KEY (case_id, seq));
"""
TABLES = ["cases", "answers", "results", "exceptions", "review_points", "actions"]


def connect(path):
    db = sqlite3.connect(str(path), check_same_thread=False)
    db.executescript(SCHEMA)
    for t in TABLES:
        for op in ("UPDATE", "DELETE"):
            db.execute(f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
                       f"BEGIN SELECT RAISE(ABORT, 'the data mart is append-only: a released case is never changed'); END")
    db.commit()
    return db


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def publish(path, c, feed):
    """Write one released case. Called once, at release, from the same feed the released files are written from."""
    db = connect(path)
    with db:
        db.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?)", (feed["case"], feed.get("line_id"), feed["tool"], feed["tool_version"],
                   feed["pack_fingerprint"], str(feed["policy_version"]), feed["status"], feed["preparer"], feed["approved_by"],
                   feed.get("released_by"), feed.get("released_at")))
        for v in feed["values"]:
            val = v["value"]
            num = float(val) if isinstance(val, (int, float)) and not isinstance(val, bool) else None
            db.execute("INSERT INTO answers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (feed["case"], v["path"], v["section"], v.get("question"), v.get("group"),
                       v["label"], v["state"], None if val is None else str(val), num, v.get("reason"), v.get("source"),
                       int(bool(v.get("changed_from_master"))), None if v.get("master_value") is None else str(v["master_value"])))
        for r in feed["calculations"]:
            db.execute("INSERT INTO results VALUES (?,?,?,?,?,?,?,?)", (feed["case"], r["id"], r["method"], r["status"], r["result"], r["verdict"],
                       r["limit"], (r["parts"] or {}).get("Inputs still missing")))
        for e in feed["exceptions"]:
            db.execute("INSERT INTO exceptions VALUES (?,?,?,?,?,?)", (feed["case"], e["calc"], e["reason"], e["note"], e["by"], e["acknowledged_by"]))
        for p in feed["review_points"]:
            db.execute("INSERT INTO review_points VALUES (?,?,?,?,?,?,?)", (feed["case"], p["id"], p["section"], p["text"], p["raised_by"], int(p["open"]), p["replies"]))
        personal = {f"f/{b['id']}" for _, b in c["pack"].blocks() if b["kind"] == "field" and b.get("personal")}
        for e in c["events"]:
            detail = {k: v for k, v in e.items() if k not in ("seq", "at", "actor", "kind", "path")}
            if e.get("path") in personal:          # the log's own old and new values for a personal field stay out
                detail = {k: v for k, v in detail.items() if k not in ("old", "new")}
            db.execute("INSERT INTO actions VALUES (?,?,?,?,?,?,?)", (feed["case"], e["seq"], e["at"], e["actor"], e["kind"], e.get("path"),
                       json.dumps(detail, sort_keys=True, default=str)))
        name = wide_view(db, c["pack"], feed["tool_version"])
    db.close()
    return name


def wide_view(db, pack, version, rows_shown=6):
    """One row per case and one column per field, question and result: the master-table shape, generated from the pack."""
    name = f"wide_{slug(pack.name)}_v{slug(version)}"
    cols, used = ["c.case_id AS case_id", "c.line_id AS line_id", "c.status AS status", "c.preparer AS preparer",
                  "c.approved_by AS approved_by", "c.released_at AS released_at"], set()

    def col(label, expr):
        nm = slug(label)[:60] or "col"
        while nm in used:
            nm += "_"
        used.add(nm)
        cols.append(f'{expr} AS "{nm}"')

    pick = "MAX(CASE WHEN a.path = '{p}' THEN COALESCE(a.value_text, '[' || a.state || ']') END)"
    for s in pack.sections:
        for b in s["blocks"]:
            if b["kind"] == "field":
                col(b["label"], pick.format(p=f"f/{b['id']}"))
            elif b["kind"] == "grid" and b["rows"]["from"] == "fixed" and any(x.get("group") or x.get("info") for x in b["rows"]["items"]):
                rating, comment = b["cols"]["items"][0], (b["cols"]["items"][1] if len(b["cols"]["items"]) > 1 else None)
                for q in b["rows"]["items"]:
                    col(f'q{q["key"]}_{rating["key"]}', pick.format(p=f"g/{b['id']}/{q['key']}/{rating['key']}"))
                    if comment:
                        col(f'q{q["key"]}_{comment["key"]}', pick.format(p=f"g/{b['id']}/{q['key']}/{comment['key']}"))
            elif b["kind"] == "grid":
                # a table becomes fixed columns, as in the work version's feed: entered rows 1..n, or each fixed row
                ckeys = [c_["key"] for c_ in b["cols"].get("items") or []] or [f"c{j}" for j in range(4)]
                if b["rows"]["from"] == "entered":
                    rkeys = [(str(i), f"{i + 1}") for i in range(rows_shown)]
                elif b["rows"]["from"] == "list":
                    rkeys = [(v, v) for v in pack.data["org"]["lists"][b["rows"]["list"]]]
                else:
                    rkeys = [(str(it["key"]), str(it["key"])) for it in b["rows"]["items"]]
                for rk, rl in rkeys:
                    for ck in ckeys:
                        col(f'{b["id"]}_{rl}_{ck}', pick.format(p=f"g/{b['id']}/{rk}/{ck}"))
            elif b["kind"] == "calc":
                col(f'{b["id"]} result', f"(SELECT r.value FROM results r WHERE r.case_id = c.case_id AND r.calc_id = '{b['id']}')")
                col(f'{b["id"]} verdict', f"(SELECT r.verdict FROM results r WHERE r.case_id = c.case_id AND r.calc_id = '{b['id']}')")
    db.execute(f'DROP VIEW IF EXISTS "{name}"')
    db.execute(f'CREATE VIEW "{name}" AS SELECT {", ".join(cols)} FROM cases c LEFT JOIN answers a ON a.case_id = c.case_id '
               f"WHERE c.tool = ? AND c.tool_version = ? GROUP BY c.case_id".replace("?", "'{}'").format(pack.name.replace("'", "''"), version.replace("'", "''")))
    return name


def views(db):
    return [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]


def rows(db, sql, args=()):
    cur = db.execute(sql, args)
    names = [d[0] for d in cur.description]
    return names, cur.fetchall()
