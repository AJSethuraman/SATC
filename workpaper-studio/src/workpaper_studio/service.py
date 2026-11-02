"""Workpaper Studio's record and rules: who may do what, and everything that was done.

Everything a person does is an event, appended to one table that the database refuses to update or delete. A case
is rebuilt by replaying its events; nothing else holds its state. Published packs and policy versions are stored
by value and are just as immutable, so a case reopens under exactly the tool and limits it was made with.

Roles come from the signed-in person, never from the request (DESIGN-PRINCIPLES §6). The rules live here, not in
the screens, so a refusal holds whatever route asks:

* entries: a preparer, on a case that is in progress or returned. A reviewer cannot change an entry.
* review: a reviewer who did not prepare the case. Points are raised, answered, cleared; never edited away.
* exceptions: recorded by the preparer beside an above-limit result, acknowledged by the reviewer. The result stays.
* approval: needs nothing missing, no open point, and every above-limit result carrying an acknowledged exception.
* release: only after approval, and only when the release check is all OK.
* packs and limits: a designer proposes a pack and a different person approves it; an admin confirms limits.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sqlite3
from pathlib import Path

from . import engine
from .pack import Pack, from_data, load_dir

ROLES = ("preparer", "reviewer", "designer", "approver", "admin")
DEMO_USERS = {
    "A. Rivera": ["preparer"],
    "J. Moss": ["preparer"],
    "D. Patel": ["reviewer"],
    "K. Owens": ["reviewer", "approver"],
    "M. Okafor": ["designer", "admin"],
}
EDITABLE = ("In progress", "Returned")

SCHEMA = """
CREATE TABLE IF NOT EXISTS packs (fingerprint TEXT PRIMARY KEY, tool TEXT, version TEXT, file TEXT, body TEXT,
    proposed_by TEXT, proposed_at TEXT);
CREATE TABLE IF NOT EXISTS pack_approvals (fingerprint TEXT PRIMARY KEY, approved_by TEXT, approved_at TEXT);
CREATE TABLE IF NOT EXISTS policy (version INTEGER PRIMARY KEY, at TEXT, by TEXT, body TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS events (case_id TEXT, seq INTEGER, at TEXT, actor TEXT, kind TEXT, body TEXT,
    PRIMARY KEY (case_id, seq));
CREATE TABLE IF NOT EXISTS outputs (case_id TEXT, name TEXT, sha256 TEXT, at TEXT, PRIMARY KEY (case_id, name));
"""
FREEZE = ["events", "packs", "pack_approvals", "policy", "outputs"]


class Refused(PermissionError):
    """A rule said no. The message says why and, where there is one, who can."""


def now():
    return datetime.datetime.now().replace(microsecond=0).isoformat(sep=" ")


class Studio:
    def __init__(self, db_path, packs_dir, users=None, out_dir=None):
        self.db_path = str(db_path)
        self.packs_dir = Path(packs_dir)
        self.users = {k: list(v) for k, v in (users or DEMO_USERS).items()}
        self.out_dir = Path(out_dir or Path(db_path).parent / "outputs")
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.db.executescript(SCHEMA)
        for t in FREEZE:
            for op in ("UPDATE", "DELETE"):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
                                f"BEGIN SELECT RAISE(ABORT, '{t} are append-only: nothing is changed or removed'); END")
        self.db.commit()

    # ------------------------------------------------------------ people
    def roles(self, user):
        if user not in self.users:
            raise Refused(f"{user!r} is not a person in this installation.")
        return set(self.users[user])

    def need(self, user, role, doing):
        if role not in self.roles(user):
            who = [u for u, r in self.users.items() if role in r]
            raise Refused(f"Only a {role} can {doing}. {', '.join(who) or 'Nobody'} can.")

    # ------------------------------------------------------------ packs
    def pack_files(self):
        return load_dir(self.packs_dir)

    def propose(self, user, file_name):
        self.need(user, "designer", "propose a tool for publishing")
        good, bad = self.pack_files()
        for e in bad:
            if e.file == file_name:
                raise Refused(f"This pack cannot be proposed until it loads: {e}")
        p = next((p for p in good if p.file == file_name), None)
        if p is None:
            raise Refused(f"There is no pack called {file_name}.")
        if self.db.execute("SELECT 1 FROM packs WHERE fingerprint=?", (p.fingerprint,)).fetchone():
            return p.fingerprint
        self.db.execute("INSERT INTO packs VALUES (?,?,?,?,?,?,?)", (p.fingerprint, p.name, p.version, p.file,
                                                                    json.dumps(p.data, sort_keys=True), user, now()))
        self.db.commit()
        return p.fingerprint

    def approve_pack(self, user, fp):
        self.need(user, "approver", "approve a tool")
        row = self.db.execute("SELECT proposed_by FROM packs WHERE fingerprint=?", (fp,)).fetchone()
        if not row:
            raise Refused("That version has not been proposed.")
        if row[0] == user:
            who = [u for u, r in self.users.items() if "approver" in r and u != user]
            raise Refused(f"You proposed this version, so you cannot approve it. {', '.join(who) or 'Another approver'} can.")
        if self.db.execute("SELECT 1 FROM pack_approvals WHERE fingerprint=?", (fp,)).fetchone():
            return
        self.db.execute("INSERT INTO pack_approvals VALUES (?,?,?)", (fp, user, now()))
        self.db.commit()

    def stored_pack(self, fp) -> Pack:
        row = self.db.execute("SELECT body, file FROM packs WHERE fingerprint=?", (fp,)).fetchone()
        if not row:
            raise KeyError(fp)
        return from_data(json.loads(row[0]), row[1])

    def versions(self):
        rows = self.db.execute("SELECT p.fingerprint, p.tool, p.version, p.file, p.proposed_by, p.proposed_at, a.approved_by, a.approved_at "
                               "FROM packs p LEFT JOIN pack_approvals a USING (fingerprint) ORDER BY p.proposed_at").fetchall()
        keys = ("fingerprint", "tool", "version", "file", "proposed_by", "proposed_at", "approved_by", "approved_at")
        return [dict(zip(keys, r)) for r in rows]

    def published(self):
        """The newest approved version of each tool: what a new case is made with."""
        out = {}
        for v in self.versions():
            if v["approved_by"]:
                out[v["tool"]] = v
        return out

    # ------------------------------------------------------------ limits
    def policy(self, version=None):
        if version is None:
            row = self.db.execute("SELECT version, body FROM policy ORDER BY version DESC LIMIT 1").fetchone()
        else:
            row = self.db.execute("SELECT version, body FROM policy WHERE version=?", (version,)).fetchone()
        return (row[0], json.loads(row[1])) if row else (0, {})

    def policy_history(self):
        return [dict(zip(("version", "at", "by", "note"), r)) for r in self.db.execute("SELECT version, at, by, note FROM policy ORDER BY version DESC")]

    def confirm_limit(self, user, tool, calc_id, limit, confirmed=True):
        self.need(user, "admin", "set the organization's limits")
        v, body = self.policy()
        body = json.loads(json.dumps(body))
        body.setdefault(tool, {})[calc_id] = {"limit": float(limit), "confirmed": bool(confirmed), "by": user, "date": datetime.date.today().isoformat()}
        self.db.execute("INSERT INTO policy VALUES (?,?,?,?,?)", (v + 1, now(), user, json.dumps(body, sort_keys=True),
                                                                f"{tool}: {calc_id} {'confirmed at' if confirmed else 'unconfirmed,'} {limit}"))
        self.db.commit()
        return v + 1

    # ------------------------------------------------------------ events
    def append(self, case_id, actor, kind, **body):
        seq = (self.db.execute("SELECT MAX(seq) FROM events WHERE case_id=?", (case_id,)).fetchone()[0] or 0) + 1
        self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (case_id, seq, now(), actor, kind, json.dumps(body, sort_keys=True)))
        self.db.commit()
        return seq

    def events(self, case_id):
        return [{"seq": s, "at": a, "actor": u, "kind": k, **json.loads(b)} for s, a, u, k, b in
                self.db.execute("SELECT seq, at, actor, kind, body FROM events WHERE case_id=? ORDER BY seq", (case_id,))]

    def case_ids(self):
        return [r[0] for r in self.db.execute("SELECT case_id FROM events WHERE kind='created' ORDER BY at DESC, case_id DESC")]

    # ------------------------------------------------------------ cases
    def new_case(self, user, tool):
        self.need(user, "preparer", "start a case")
        v = self.published().get(tool)
        if not v:
            raise Refused(f"{tool} has no approved version yet, so a case cannot be started with it.")
        prefix = "".join(w[0] for w in tool.split()[:3]).upper()
        n = 1 + sum(1 for c in self.case_ids() if c.startswith(prefix + "-"))
        cid = f"{prefix}-{n:04d}"
        pv, _ = self.policy()
        self.append(cid, user, "created", tool=tool, fingerprint=v["fingerprint"], version=v["version"], policy_version=pv)
        return cid

    def case(self, cid):
        """Rebuild a case from its events. This is the only way a case is read."""
        evs = self.events(cid)
        if not evs:
            raise KeyError(cid)
        c = {"id": cid, "data": {}, "states": {}, "status": "In progress", "points": {}, "exceptions": {}, "events": evs,
             "preparer": evs[0]["actor"], "created_at": evs[0]["at"], "reviewer": None, "approved_by": None}
        first = evs[0]
        c.update(tool=first["tool"], fingerprint=first["fingerprint"], version=first["version"], policy_version=first["policy_version"])
        pack = self.stored_pack(first["fingerprint"])
        c["pack"] = pack
        for e in evs[1:]:
            k = e["kind"]
            if k == "set":
                engine.set_value(pack, c["data"], e["path"], e["new"])
            elif k == "mark":
                if e.get("state"):
                    c["states"][e["path"]] = {"state": e["state"], "reason": e.get("reason")}
                else:
                    c["states"].pop(e["path"], None)
            elif k == "submitted":
                c["status"] = "In review"
            elif k == "returned":
                c["status"] = "Returned"
            elif k == "approved":
                c["status"], c["approved_by"] = "Approved", e["actor"]
            elif k == "released":
                c["status"] = "Released"
            elif k == "point_raised":
                c["points"][e["id"]] = {"id": e["id"], "section": e["section"], "text": e["text"], "by": e["actor"], "at": e["at"], "replies": [], "open": True}
                c["reviewer"] = e["actor"]
            elif k == "point_replied":
                c["points"][e["id"]]["replies"].append({"by": e["actor"], "at": e["at"], "text": e["text"]})
            elif k == "point_cleared":
                c["points"][e["id"]]["open"] = False
                c["points"][e["id"]]["cleared_by"] = e["actor"]
            elif k == "exception_recorded":
                c["exceptions"][e["id"]] = {"id": e["id"], "calc": e["calc"], "reason": e["reason"], "note": e["note"], "by": e["actor"], "at": e["at"], "ack": None}
            elif k == "exception_acknowledged":
                c["exceptions"][e["id"]]["ack"] = {"by": e["actor"], "at": e["at"]}
        _, body = self.policy(c["policy_version"])
        c["policy"] = body.get(c["tool"], {})
        c["eval"] = engine.evaluate(pack, c["data"], c["states"], c["policy"])
        c["subject"] = self._subject(pack, c["data"])
        return c

    @staticmethod
    def _subject(pack, data):
        for _, b in pack.blocks():
            if b["kind"] == "field" and b.get("type") == "text" and data.get(b["id"]):
                v = str(data[b["id"]])
                return (v[0] + "•" * 4) if b.get("personal") else v
        return ""

    def _editable(self, user, c):
        self.need(user, "preparer", "change an entry")
        if c["status"] not in EDITABLE:
            raise Refused(f"This case is {c['status'].lower()}, so its entries are locked." +
                          (" The reviewer can return it if something needs to change." if c["status"] == "In review" else ""))

    def set(self, user, cid, path, text):
        c = self.case(cid)
        self._editable(user, c)
        defn = engine.defn_for(c["pack"], path)
        value = engine.parse(defn, text, c["pack"].data["org"].get("lists", {}))
        old = engine.get_value(c["pack"], c["data"], path)
        if old == value:
            return c
        self.append(cid, user, "set", path=path, old=old, new=value)
        return self.case(cid)

    def mark(self, user, cid, path, state, reason=""):
        c = self.case(cid)
        self._editable(user, c)
        if state not in ("na", "excluded", None):
            raise Refused("A value can be marked not applicable or excluded, or cleared.")
        if state and not (reason or "").strip():
            raise Refused("Say why. A value marked " + ("not applicable" if state == "na" else "excluded") + " needs a reason.")
        if state == "na" and not path.startswith("f/"):
            raise Refused("Only a field can be marked not applicable. Exclude a table row instead.")
        if state == "excluded" and path.count("/") != 2:
            raise Refused("Only a whole table row can be excluded.")
        self.append(cid, user, "mark", path=path, state=state, reason=(reason or "").strip() or None)
        return self.case(cid)

    # ------------------------------------------------------------ review
    def submit(self, user, cid):
        c = self.case(cid)
        self._editable(user, c)
        ev = c["eval"]
        if ev["missing"]:
            raise Refused(f"{ev['missing']} item(s) are still missing. The release check lists each one.")
        if not ev["limits_ok"]:
            raise Refused("A limit this tool tests against has not been confirmed by the organization. An admin confirms it on Settings.")
        self.append(cid, user, "submitted")
        return self.case(cid)

    def _reviewer(self, user, c, doing):
        self.need(user, "reviewer", doing)
        if user == c["preparer"]:
            others = [u for u, r in self.users.items() if "reviewer" in r and u != user]
            raise Refused(f"You prepared this case, so you cannot review it. {', '.join(others)} can.")

    def raise_point(self, user, cid, section, text):
        c = self.case(cid)
        self._reviewer(user, c, "raise a review point")
        if c["status"] != "In review":
            raise Refused("Review points are raised while a case is in review.")
        if not text.strip():
            raise Refused("Write the point.")
        pid = f"P{len(c['points']) + 1}"
        self.append(cid, user, "point_raised", id=pid, section=section, text=text.strip())
        return self.case(cid)

    def reply_point(self, user, cid, pid, text):
        c = self.case(cid)
        self.need(user, "preparer", "answer a review point")
        if pid not in c["points"] or not text.strip():
            raise Refused("Write the answer to an existing point.")
        self.append(cid, user, "point_replied", id=pid, text=text.strip())
        return self.case(cid)

    def clear_point(self, user, cid, pid):
        c = self.case(cid)
        self._reviewer(user, c, "clear a review point")
        if pid not in c["points"]:
            raise Refused("There is no such point.")
        self.append(cid, user, "point_cleared", id=pid)
        return self.case(cid)

    def return_case(self, user, cid):
        c = self.case(cid)
        self._reviewer(user, c, "return a case")
        if c["status"] != "In review":
            raise Refused("Only a case in review can be returned.")
        self.append(cid, user, "returned")
        return self.case(cid)

    def record_exception(self, user, cid, calc_id, reason, note):
        c = self.case(cid)
        self.need(user, "preparer", "record an exception")
        if c["status"] in ("Approved", "Released"):
            raise Refused("This case is approved; exceptions are recorded before approval.")
        calc = c["eval"]["calcs"].get(calc_id)
        if not calc or calc["verdict"] != "Above limit":
            raise Refused("An exception is recorded beside a result that is above its limit, and this one is not.")
        if reason not in c["pack"].data["org"]["lists"].get("Exception reasons", []):
            raise Refused("Choose a reason from the organization's list.")
        if not note.strip():
            raise Refused("Explain the exception in the note.")
        eid = f"E{len(c['exceptions']) + 1}"
        self.append(cid, user, "exception_recorded", id=eid, calc=calc_id, reason=reason, note=note.strip())
        return self.case(cid)

    def acknowledge(self, user, cid, eid):
        c = self.case(cid)
        self._reviewer(user, c, "acknowledge an exception")
        if eid not in c["exceptions"]:
            raise Refused("There is no such exception.")
        self.append(cid, user, "exception_acknowledged", id=eid)
        return self.case(cid)

    def approve(self, user, cid):
        c = self.case(cid)
        self._reviewer(user, c, "approve a case")
        blockers = [x for x in self.release_check(c) if not x["ok"] and x["stage"] == "approve"]
        if c["status"] != "In review":
            raise Refused("Only a case in review can be approved.")
        if blockers:
            raise Refused("Not yet: " + "; ".join(f'{b["check"]} ({b["detail"]})' for b in blockers))
        self.append(cid, user, "approved")
        return self.case(cid)

    # ------------------------------------------------------------ release
    def release_check(self, c):
        ev, out = c["eval"], []
        for s in ev["sections"]:
            ok = s["status"] in engine.OK_STATUSES
            out.append({"check": s["title"], "ok": ok, "detail": "OK" if ok else s["status"] + ": " + "; ".join(i["label"] for i in s["items"]),
                        "link": s["items"][0]["path"] if s["items"] else None, "stage": "approve"})
        for cid_, calc in ev["calcs"].items():
            out.append({"check": f"{calc['limit_label']} confirmed", "ok": calc["confirmed"], "stage": "approve", "link": None,
                        "detail": "OK" if calc["confirmed"] else "Not confirmed. An admin confirms it on Settings."})
            if calc["verdict"] == "Above limit":
                exs = [e for e in c["exceptions"].values() if e["calc"] == cid_]
                acked = [e for e in exs if e["ack"]]
                ok = bool(acked)
                out.append({"check": f"{calc['name']} above limit: exception", "ok": ok, "stage": "approve", "link": f"calc/{cid_}",
                            "detail": "OK, acknowledged by " + acked[0]["ack"]["by"] if ok else ("Recorded, waiting for the reviewer" if exs else "Record an exception, or correct the entries")})
        open_pts = [p for p in c["points"].values() if p["open"]]
        out.append({"check": "Review points", "ok": not open_pts, "stage": "approve", "link": f"point/{open_pts[0]['id']}" if open_pts else None,
                    "detail": "OK" if not open_pts else f"{len(open_pts)} open"})
        out.append({"check": "Approved by a reviewer", "ok": c["status"] in ("Approved", "Released"), "stage": "release", "link": None,
                    "detail": f"OK, {c['approved_by']}" if c["approved_by"] else "Not yet"})
        return out

    def release(self, user, cid):
        c = self.case(cid)
        if not (self.roles(user) & {"reviewer", "admin"}):
            raise Refused("Only a reviewer or an admin can release a case.")
        if c["status"] == "Released":
            raise Refused("This case has already been released.")
        bad = [x for x in self.release_check(c) if not x["ok"]]
        if bad:
            raise Refused("The release check is not clear: " + "; ".join(f"{b['check']} ({b['detail']})" for b in bad))
        folder = self.out_dir / cid
        folder.mkdir(parents=True, exist_ok=True)
        files = self.write_outputs(c, folder)
        for name, digest in files.items():
            self.db.execute("INSERT INTO outputs VALUES (?,?,?,?)", (cid, name, digest, now()))
        self.db.commit()
        self.append(cid, user, "released", outputs=files)
        return self.case(cid)

    def released_outputs(self, cid):
        return [dict(zip(("name", "sha256", "at"), r)) for r in self.db.execute("SELECT name, sha256, at FROM outputs WHERE case_id=?", (cid,))]

    def write_outputs(self, c, folder):
        from . import outputs
        folder = Path(folder)
        files = {}
        feed = outputs.feed(c)
        (folder / f"{c['id']}.feed.json").write_text(json.dumps(feed, indent=1, sort_keys=True))
        (folder / f"{c['id']}.feed.csv").write_text(outputs.feed_csv(feed))
        try:
            outputs.workbook(c, folder / f"{c['id']}.xlsx")
        except ImportError:
            pass
        for p in sorted(folder.iterdir()):
            files[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        return files
