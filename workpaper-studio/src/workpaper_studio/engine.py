"""The engine: one pack, one case's entries, one policy set in; every status, result and verdict out.

This is the only place the application decides anything. The screens display what it returns, the release check
reads it, the feed and the workbook carry it. The generated workbook has its own formulas for people who stay in
Excel, and tests/test_workbook_parity.py proves they agree with this file on the same case.

Case data has the same shape as a pack's `example`: fields by id; tables by id with `rows` (entered rows), `_cols`
(entered columns) or row keys (fixed and list rows). Value states other than entered live beside the data, keyed by
path: "f/<field>" (not applicable, with a reason) and "g/<table>/<row>" (row excluded, with a reason).
"""
from __future__ import annotations

import datetime
import re

from .methods import METHODS, blank

OK_STATUSES = ("Complete", "Not applicable", "Optional")
ENTERED_COLS = 4


class EntryError(ValueError):
    """An entry the engine will not store, with the reason in the words the preparer will read."""


# ------------------------------------------------------------------ parsing entries
def parse(defn: dict, text, lists: dict):
    """Turn what someone typed into the stored value. Blank stays blank: it is never turned into zero."""
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    t = text.strip()
    if t == "":
        return None
    kind = defn.get("type", "text")
    if kind == "number":
        s = t.replace("$", "").replace(",", "").replace(" ", "")
        neg = s.startswith("(") and s.endswith(")")
        s = s.strip("()")
        if s.endswith("%"):
            s = s[:-1]
        try:
            v = float(s)
        except ValueError:
            raise EntryError(f"“{t}” is not a number. Enter digits only, for example 1450 or 1,450.00.") from None
        v = -v if neg else v
        if v < 0:
            raise EntryError("Enter 0 or more. A negative amount belongs in a different line.")
        return int(v) if v == int(v) and "." not in s else v
    if kind == "date":
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.datetime.strptime(t, fmt).date().isoformat()
            except ValueError:
                pass
        raise EntryError(f"“{t}” is not a date. Use the form 2026-10-31.")
    if kind in ("list", "choice"):
        opts = defn.get("opts") if kind == "choice" else lists.get(defn.get("list"), [])
        for o in opts:
            if o.lower() == t.lower():
                return o
        raise EntryError(f"“{t}” is not one of the choices: {', '.join(opts)}.")
    return t


# ------------------------------------------------------------------ formatting results
def fmt_value(v, defn=None, pct=False):
    if v is None or v == "":
        return ""
    if pct:
        return f"{v * 100:.1f}%"
    if defn and defn.get("type") == "number":
        if defn.get("money"):
            return f"${v:,.2f}" if defn.get("cents") else f"${v:,.0f}"
        return f"{v:,.0f}" if float(v) == int(v) else f"{v:,}"
    return str(v)


# ------------------------------------------------------------------ the evaluation
class Case:
    def __init__(self, pack, data, states=None, policy=None):
        self.pack, self.data = pack, data or {}
        self.states = states or {}
        self.policy = policy or {}
        self.lists = pack.data["org"].get("lists", {})
        self.fieldmap = {b["id"]: b for _, b in pack.blocks() if b["kind"] == "field"}

    # facts ---------------------------------------------------------
    def value(self, fid):
        return self.data.get(fid)

    def na(self, path):
        st = self.states.get(path)
        return st if st and st.get("state") == "na" else None

    def excluded(self, path):
        st = self.states.get(path)
        return st if st and st.get("state") == "excluded" else None

    def field_fact(self, fid):
        n = self.na(f"f/{fid}")
        if n:
            return {"state": "na", "value": None, "reason": n.get("reason")}
        return {"state": "entered", "value": self.value(fid)}

    def applies(self, rule):
        if not rule:
            return "Yes"
        v = self.value(rule["field"])
        if blank(v):
            return "Waiting"
        return "Yes" if v in rule["values"] else "No"

    # tables --------------------------------------------------------
    def table(self, g):
        """Rows of a table as the engine sees them: label, cells, computed cells, excluded or not."""
        gid, by = g["id"], g.get("cellsBy", "col")
        d = self.data.get(gid) or {}
        rows_from, cols_from = g["rows"]["from"], g["cols"]["from"]
        if cols_from == "fixed":
            C = g["cols"]["items"]
        else:
            names = list(d.get("_cols") or [])
            n = max(ENTERED_COLS, len(names), *[len([k for k in (d.get(str(it["key"])) or {})]) for it in g["rows"].get("items") or [{"key": "_"}]])
            C = [{"key": f"c{j}", "label": names[j] if j < len(names) and names[j] else f'{g["cols"].get("addLabel", "Column")} {j + 1}'} for j in range(n)]
        if rows_from == "fixed":
            R = [dict(it, _key=str(it["key"])) for it in g["rows"]["items"]]
            raw = [d.get(str(it["key"])) or {} for it in g["rows"]["items"]]
        elif rows_from == "list":
            R = [{"key": v, "label": v, "_key": v} for v in self.lists[g["rows"]["list"]]]
            raw = [d.get(v) or {} for v in self.lists[g["rows"]["list"]]]
        else:
            raw = list(d.get("rows") or [])
            lab = (g["rows"].get("addLabel") or "Row").capitalize()
            R = [{"key": i, "label": f"{lab} {i + 1}", "_key": str(i)} for i in range(len(raw))]
        out = []
        for row, cells in zip(R, raw):
            ex = self.excluded(f"g/{gid}/{row['_key']}")
            r = {"key": row["_key"], "label": row.get("label") or row["_key"], "def": row, "cells": dict(cells),
                 "excluded": bool(ex), "reason": (ex or {}).get("reason"), "computed": {}}
            out.append(r)
        # computed cells: by column (every row) or by row (every column)
        for r in out:
            for c in C:
                d_ = r["def"] if by == "row" else c
                cp = d_.get("compute")
                if not cp:
                    continue
                if by == "col":
                    a, b = r["cells"].get(cp["a"]), r["cells"].get(cp["b"])
                else:
                    src = {x["key"]: x for x in out}
                    a, b = src[cp["a"]]["cells"].get(c["key"]), src[cp["b"]]["cells"].get(c["key"])
                r["computed"][c["key"]] = _op(cp["op"], a, b)
        return C, out

    def table_used(self, g, C, rows):
        inputs = [c["key"] for c in C if not c.get("compute")]
        return [r for r in rows if not r["excluded"] and any(not blank(r["cells"].get(k)) for k in inputs)]

    # sections ------------------------------------------------------
    def evaluate(self):
        res = {"fields": {}, "sections": [], "tables": {}, "questions": {}, "calcs": {}}
        for s in self.pack.sections:
            ap = self.applies(s.get("rule") if s["mode"] == "conditional" else None)
            items, started = [], False
            for b in s["blocks"]:
                if b["kind"] == "field":
                    f = self.field_fact(b["id"])
                    v = f["value"]
                    if f["state"] == "na":
                        state = "na"
                    elif blank(v):
                        state = "missing" if b.get("req") else "empty"
                    else:
                        state = "zero" if b.get("type") == "number" and float(v) == 0 else "entered"
                    started = started or not blank(v) or f["state"] == "na"
                    res["fields"][b["id"]] = {"value": v, "state": state, "reason": f.get("reason"), "display": fmt_value(v, b)}
                    if state == "missing":
                        items.append({"label": b["label"], "path": f"f/{b['id']}"})
                elif b["kind"] == "grid":
                    st, its = self.grid_status(b)
                    started = started or st
                    items += its
            for b in s["blocks"]:
                if b["kind"] == "calc":
                    res["calcs"][b["id"]] = self.calc(b)
            if ap == "No":
                miss_items = []
            elif s["mode"] == "optional" and not started:
                miss_items = []
            elif ap == "Waiting":
                rf = s["rule"]["field"]
                miss_items = [{"label": f'Answer “{self.fieldmap[rf]["label"]}” first', "path": f"f/{rf}"}]
            else:
                miss_items = items
            n = len(miss_items)
            if ap == "No":
                status = "Not applicable"
            elif ap == "Waiting":
                status = "Waiting on an answer"
            elif s["mode"] == "optional" and not started:
                status = "Optional"
            else:
                status = "Complete" if n == 0 else f"{n} missing"
            res["sections"].append({"id": s["id"], "title": s["title"], "mode": s["mode"], "screen": s.get("screen", "Workpaper"),
                                    "applies": ap, "status": status, "missing": n, "items": miss_items, "started": started})
        for b in (b for _, b in self.pack.blocks() if b["kind"] == "grid"):
            res["tables"][b["id"]] = self._table_view(b)
        res["missing"] = sum(s["missing"] for s in res["sections"])
        res["sections_done"] = sum(s["status"] in OK_STATUSES for s in res["sections"])
        res["sections_total"] = len(res["sections"])
        res["limits_ok"] = all(c["confirmed"] for c in res["calcs"].values())
        res["ready"] = res["sections_done"] == res["sections_total"] and res["limits_ok"]
        return res

    def grid_status(self, g):
        """(started, missing items) for one table, counted the way the workbook counts them."""
        C, rows = self.table(g)
        items, started = [], False
        rows_from, cols_from, by = g["rows"]["from"], g["cols"]["from"], g.get("cellsBy", "col")
        if rows_from == "fixed" and by == "col" and any(x.get("group") or x.get("info") for x in g["rows"]["items"]):
            rating, comment = C[0], (C[1] if len(C) > 1 else None)
            qs = {}
            for r in rows:
                ap = self.applies(r["def"].get("when"))
                rv, cv = r["cells"].get(rating["key"]), (r["cells"].get(comment["key"]) if comment else None)
                started = started or not blank(rv) or not blank(cv)
                rw = comment.get("reqWhen") if comment else None
                need = bool(rw) and rv in rw["values"] and blank(cv)
                qs[r["key"]] = {"applies": ap, "rating": rv, "comment": cv, "rating_missing": ap != "No" and blank(rv), "need_comment": ap != "No" and need}
                lab = f'Question {r["key"]}'
                if ap == "Yes" and blank(rv):
                    items.append({"label": f"{lab}: rate it", "path": f"g/{g['id']}/{r['key']}/{rating['key']}"})
                elif ap == "Yes" and need:
                    items.append({"label": f"{lab}: a comment is needed for this rating", "path": f"g/{g['id']}/{r['key']}/{comment['key']}"})
                elif ap == "Waiting":
                    items.append({"label": f'{lab}: answer “{self.fieldmap[r["def"]["when"]["field"]]["label"]}” first', "path": f"f/{r['def']['when']['field']}"})
            self._questions = getattr(self, "_questions", {})
            self._questions[g["id"]] = qs
            return started, items
        inputs = [c for c in C if not c.get("compute")]
        for r in rows:
            if any(not blank(r["cells"].get(c["key"])) for c in inputs) or r["excluded"]:
                started = True
        if rows_from == "entered":
            req = [c for c in inputs if c.get("req")]
            for r in self.table_used(g, C, rows):
                lack = [c["label"] for c in req if blank(r["cells"].get(c["key"]))]
                if lack:
                    items.append({"label": f'{g["label"]}, {r["label"]}: {", ".join(lack)}', "path": f"g/{g['id']}/{r['key']}/{[c for c in req if blank(r['cells'].get(c['key']))][0]['key']}"})
            mn = g["rows"].get("min", 0)
            if mn and len(self.table_used(g, C, rows)) < mn:
                items.append({"label": f'{g["label"]}: at least {mn} {g["rows"].get("addLabel", "row")}' + ("" if mn == 1 else "s"), "path": f"g/{g['id']}/0/{inputs[0]['key']}"})
        else:
            for r in rows:
                if r["excluded"]:
                    continue
                for c in C:
                    d_ = r["def"] if by == "row" else c
                    if not d_.get("req") or d_.get("compute"):
                        continue
                    if cols_from == "entered":
                        col_used = any(not blank(x["cells"].get(c["key"])) for x in rows)
                        if col_used and blank(r["cells"].get(c["key"])):
                            items.append({"label": f'{g["label"]}, {c["label"]}: {r["label"]}', "path": f"g/{g['id']}/{r['key']}/{c['key']}"})
                    elif blank(r["cells"].get(c["key"])):
                        items.append({"label": f'{g["label"]}, {r["label"]}: {c["label"]}', "path": f"g/{g['id']}/{r['key']}/{c['key']}"})
        return started, items

    def _table_view(self, g):
        C, rows = self.table(g)
        totals = {}
        if g.get("totals") and g.get("cellsBy", "col") == "col":
            live = self.table_used(g, C, rows) if g["rows"]["from"] == "entered" else [r for r in rows if not r["excluded"]]
            for c in C:
                if (c.get("type") == "number" or c.get("compute")) and not c.get("noTotal"):
                    if c.get("req") and not c.get("compute") and any(blank(r["cells"].get(c["key"])) for r in live):
                        totals[c["key"]] = None      # a required gap: the total is withheld, never shown as a smaller number
                        continue
                    vals = [(r["computed"].get(c["key"]) if c.get("compute") else r["cells"].get(c["key"])) for r in rows if not r["excluded"]]
                    totals[c["key"]] = sum(v for v in vals if isinstance(v, (int, float)))
        return {"cols": C, "rows": rows, "totals": totals, "questions": getattr(self, "_questions", {}).get(g["id"])}

    # calculations --------------------------------------------------
    def calc(self, b):
        m = METHODS[b["method"]]
        x = self.method_inputs(b)
        r = m.run(x)
        pol = self.policy.get(b["id"]) or {}
        confirmed = bool(pol.get("confirmed"))
        limit = pol.get("limit", b["limit"])
        pct = b["method"] in ("dti", "devrate")
        if not confirmed:
            verdict = "Not tested: limit not confirmed"
        elif r.status == "calculated":
            ok = abs(r.value) <= limit + 0.005 if b["method"] == "recon" else r.value <= limit
            verdict = "Within limit" if ok else "Above limit"
        else:
            verdict = "Not tested"
        display = {"calculated": None, "not_calculated": "Not calculated", "no_result": "No result"}[r.status]
        if display is None:
            display = f"{r.value * 100:.1f}%" if pct else f"${r.value:,.2f}"
        return {"id": b["id"], "method": b["method"], "name": m.name, "code": b.get("code") or f"{m.code} {m.version}",
                "status": r.status, "value": r.value, "display": display, "parts": r.parts, "missing": r.missing,
                "disclosures": r.disclosures, "verdict": verdict, "confirmed": confirmed, "limit": limit,
                "limit_display": f"{limit * 100:.1f}%" if pct else f"${limit:,.2f}", "limit_label": b["limitLabel"],
                "pct": pct, "policy": pol}

    def method_inputs(self, b):
        def rows(gid):
            g = self.pack.grid(gid)
            _, rs = self.table(g)
            return [dict(r["cells"], label=r["label"], excluded=r["excluded"], reason=r["reason"]) for r in rs]
        if b["method"] == "dti":
            i = b["inputs"]
            return {"income": rows(i["income"]), "debts": rows(i["debts"]), "proposed": self.field_fact(i["proposed"])}
        if b["method"] == "recon":
            i = b["inputs"]
            return {"items": rows(i["items"]), "bank": self.field_fact(i["bank"]), "books": self.field_fact(i["books"])}
        if b["method"] == "devrate":
            return {"rows": [dict(label=r["label"], attrs=[r.get(a) for a in b["attributes"]], excluded=r["excluded"], reason=r["reason"]) for r in rows(b["grid"])]}
        raise KeyError(b["method"])


def _op(op, a, b):
    if blank(a) or blank(b):
        return None
    a, b = float(a), float(b)
    if op == "mul":
        return a * b
    if op == "pctof":
        return a * b / 100
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    return None if b == 0 else a / b


def evaluate(pack, data, states=None, policy=None):
    return Case(pack, data, states, policy).evaluate()


# ------------------------------------------------------------------ paths
PATH = re.compile(r"^(f)/([^/]+)$|^(g)/([^/]+)/([^/]+)/([^/]+)$|^(g)/([^/]+)/([^/]+)$")


def defn_for(pack, path):
    """The definition that governs one entry path, so the entry is parsed by the type its column or field declares."""
    m = PATH.match(path)
    if not m:
        raise EntryError(f"Unknown entry {path!r}.")
    if m.group(1):
        return pack.field(m.group(2))
    if m.group(3):
        g = pack.grid(m.group(4))
        rk, ck = m.group(5), m.group(6)
        if rk == "_cols":
            return {"type": "text"}
        if g.get("cellsBy", "col") == "row":
            return next(it for it in g["rows"]["items"] if str(it["key"]) == rk)
        return next(it for it in g["cols"]["items"] if it["key"] == ck)
    return None


def set_value(pack, data: dict, path: str, value):
    """Write one parsed value into case data at a path. Returns the previous value."""
    m = PATH.match(path)
    if m.group(1):
        old = data.get(m.group(2))
        if value is None:
            data.pop(m.group(2), None)
        else:
            data[m.group(2)] = value
        return old
    gid, rk, ck = m.group(4), m.group(5), m.group(6)
    g = pack.grid(gid)
    d = data.setdefault(gid, {})
    if rk == "_cols":
        cols = d.setdefault("_cols", [])
        j = int(ck[1:]) if ck.startswith("c") else int(ck)
        while len(cols) <= j:
            cols.append("")
        old, cols[j] = cols[j], value or ""
        return old or None
    if g["rows"]["from"] == "entered":
        rows = d.setdefault("rows", [])
        i = int(rk)
        while len(rows) <= i:
            rows.append({})
        old = rows[i].get(ck)
        if value is None:
            rows[i].pop(ck, None)
        else:
            rows[i][ck] = value
        while rows and not rows[-1]:
            rows.pop()
        return old
    row = d.setdefault(rk, {})
    old = row.get(ck)
    if value is None:
        row.pop(ck, None)
    else:
        row[ck] = value
    return old


def get_value(pack, data, path):
    m = PATH.match(path)
    if m.group(1):
        return data.get(m.group(2))
    gid, rk, ck = m.group(4), m.group(5), m.group(6)
    d = data.get(gid) or {}
    if rk == "_cols":
        cols = d.get("_cols") or []
        j = int(ck[1:])
        return cols[j] if j < len(cols) else None
    if pack.grid(gid)["rows"]["from"] == "entered":
        rows = d.get("rows") or []
        i = int(rk)
        return rows[i].get(ck) if i < len(rows) else None
    return (d.get(rk) or {}).get(ck)
