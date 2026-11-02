"""Tool packs: a tool's whole configuration as one data file, checked before anything uses it.

A pack that is wrong refuses to load and says which file, where in it, and what to change (DESIGN-PRINCIPLES §5, §10).
The checks are structural (unknown keys, wrong kinds), referential (every field, list, column and method a pack names
must exist) and logical (a section may not be switched on by a field inside itself).

A pack's fingerprint covers the tool, its lists and its methods. The `example` and `confirmations` blocks are
demonstration data and do not change it.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .methods import METHODS

FIELD_TYPES = {"text", "longtext", "number", "date", "list", "choice"}
MODES = {"required", "optional", "conditional"}
OPS = {"mul", "pctof", "add", "sub", "div"}

KEYS = {
    "pack": {"pack", "family", "org", "tool", "confirmations", "example"},
    "pack.pack": {"name", "version"},
    "org": {"name", "lists"},
    "tool": {"name", "sections"},
    "section": {"id", "title", "mode", "blocks", "rule", "screen"},
    "rule": {"field", "values"},
    "field": {"kind", "id", "label", "type", "req", "list", "opts", "money", "cents", "personal", "info"},
    "grid": {"kind", "id", "label", "cellsBy", "totals", "tally", "rows", "cols"},
    "calc": {"kind", "id", "method", "code", "limit", "limitLabel", "grid", "attributes", "inputs"},
    "axis": {"from", "items", "min", "addLabel", "list"},
    "item": {"key", "label", "type", "req", "list", "opts", "money", "cents", "noTotal", "compute", "group", "info", "when", "reqWhen", "personal"},
    "compute": {"op", "a", "b"},
    "when": {"field", "values"},
    "reqWhen": {"key", "values"},
}


class PackError(ValueError):
    def __init__(self, file, where, message, line=None):
        self.file, self.where, self.message, self.line = file, where, message, line
        at = f"{file}, near line {line}" if line else file
        super().__init__(f"{at}, at {where}: {message}")


@dataclass(frozen=True)
class Pack:
    data: dict
    file: str
    fingerprint: str

    @property
    def name(self):
        return self.data["tool"]["name"]

    @property
    def version(self):
        return self.data["pack"]["version"]

    @property
    def sections(self):
        return self.data["tool"]["sections"]

    def blocks(self):
        for s in self.sections:
            for b in s["blocks"]:
                yield s, b

    def field(self, fid):
        for _, b in self.blocks():
            if b["kind"] == "field" and b["id"] == fid:
                return b
        raise KeyError(fid)

    def grid(self, gid):
        for _, b in self.blocks():
            if b["kind"] == "grid" and b["id"] == gid:
                return b
        raise KeyError(gid)

    def calcs(self):
        return [(s, b) for s, b in self.blocks() if b["kind"] == "calc"]


def fingerprint(data: dict) -> str:
    core = {k: v for k, v in data.items() if k not in ("example", "confirmations")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def _line_of(text, where):
    """Best-effort line for a path like tool.sections[3].blocks[1].rule.field: the last key named, after the nearest id."""
    if not text:
        return None
    keys = re.findall(r"\.([A-Za-z_]+)", "." + where)
    if not keys:
        return None
    ids = re.findall(r"\[(\d+)\]", where)
    pos = 0
    # walk forward through each array index so the search starts near the right block
    for part in re.finditer(r"([A-Za-z_]+)(?:\[(\d+)\])?", where):
        key, idx = part.group(1), part.group(2)
        m = re.compile(r'"%s"\s*:' % re.escape(key)).search(text, pos)
        if not m:
            break
        pos = m.end()
        if idx is not None:
            for _ in range(int(idx) + 1):
                m2 = re.compile(r'\{\s*"').search(text, pos)
                if not m2:
                    break
                pos = m2.start() + 1
    del ids
    return text.count("\n", 0, pos) + 1


def check(data: dict, file="pack", text=None):
    """Raise PackError on the first thing wrong with a pack. Returns the data unchanged when it is sound."""
    def fail(where, msg):
        raise PackError(file, where, msg, _line_of(text, where))

    def keys(obj, kind, where):
        if not isinstance(obj, dict):
            fail(where, f"expected an object, found {type(obj).__name__}")
        extra = set(obj) - KEYS[kind]
        if extra:
            fail(f"{where}.{sorted(extra)[0]}", f"'{sorted(extra)[0]}' is not something a {kind} can have. Allowed: {', '.join(sorted(KEYS[kind]))}")

    keys(data, "pack", "")
    for k in ("pack", "org", "tool"):
        if k not in data:
            fail(k, f"a pack needs '{k}'")
    keys(data["pack"], "pack.pack", "pack")
    keys(data["org"], "org", "org")
    keys(data["tool"], "tool", "tool")
    lists = data["org"].get("lists", {})
    if not isinstance(lists, dict):
        fail("org.lists", "lists must be an object of name -> values")
    sections = data["tool"].get("sections")
    if not sections:
        fail("tool.sections", "a tool needs at least one section")

    ids, sids, fields, field_section, grids = set(), set(), {}, {}, {}
    for i, s in enumerate(sections):
        sw = f"tool.sections[{i}]"
        keys(s, "section", sw)
        for k in ("id", "title", "mode", "blocks"):
            if k not in s:
                fail(sw, f"a section needs '{k}'")
        if s["id"] in sids:
            fail(f"{sw}.id", f"section id '{s['id']}' is used twice")
        sids.add(s["id"])
        if s["mode"] not in MODES:
            fail(f"{sw}.mode", f"mode must be one of {', '.join(sorted(MODES))}")
        if s["mode"] == "conditional" and "rule" not in s:
            fail(sw, "a conditional section needs a rule saying when it applies")
        for j, b in enumerate(s["blocks"]):
            bw = f"{sw}.blocks[{j}]"
            kind = b.get("kind") if isinstance(b, dict) else None
            if kind not in ("field", "grid", "calc"):
                fail(f"{bw}.kind", "kind must be field, grid or calc")
            keys(b, kind, bw)
            if "id" not in b:
                fail(bw, "every block needs an id")
            if b["id"] in ids:
                fail(f"{bw}.id", f"id '{b['id']}' is used twice")
            ids.add(b["id"])
            if kind == "field":
                _check_typed(b, bw, lists, fail)
                fields[b["id"]] = b
                field_section[b["id"]] = s["id"]
            elif kind == "grid":
                grids[b["id"]] = b
                for ax in ("rows", "cols"):
                    aw = f"{bw}.{ax}"
                    keys(b.get(ax), "axis", aw)
                    frm = b[ax].get("from")
                    if frm not in ("fixed", "entered", "list"):
                        fail(f"{aw}.from", "from must be fixed, entered or list")
                    if frm == "list" and b[ax].get("list") not in lists:
                        fail(f"{aw}.list", f"there is no list called '{b[ax].get('list')}'")
                    if frm == "fixed":
                        seen = set()
                        for k2, it in enumerate(b[ax].get("items") or []):
                            iw = f"{aw}.items[{k2}]"
                            keys(it, "item", iw)
                            if it.get("key") in seen:
                                fail(f"{iw}.key", f"key '{it.get('key')}' is used twice")
                            seen.add(it.get("key"))
                            if "type" in it:
                                _check_typed(it, iw, lists, fail)
                if b.get("cellsBy", "col") not in ("col", "row"):
                    fail(f"{bw}.cellsBy", "cellsBy must be col or row")
    # references, now every id is known
    for i, s in enumerate(sections):
        sw = f"tool.sections[{i}]"
        if s.get("rule"):
            keys(s["rule"], "rule", f"{sw}.rule")
            f = s["rule"].get("field")
            if f not in fields:
                fail(f"{sw}.rule.field", f"'{f}' is not a field in this tool")
            if field_section[f] == s["id"]:
                fail(f"{sw}.rule.field", f"'{f}' is inside this section, so the section could never be switched on (a cycle)")
        for j, b in enumerate(s["blocks"]):
            bw = f"{sw}.blocks[{j}]"
            if b["kind"] == "grid":
                fixed = {ax: [it["key"] for it in (b[ax].get("items") or [])] for ax in ("rows", "cols")}
                for ax in ("rows", "cols"):
                    for k2, it in enumerate(b[ax].get("items") or []):
                        iw = f"{bw}.{ax}.items[{k2}]"
                        if it.get("compute"):
                            keys(it["compute"], "compute", f"{iw}.compute")
                            if it["compute"].get("op") not in OPS:
                                fail(f"{iw}.compute.op", f"op must be one of {', '.join(sorted(OPS))}")
                            for side in ("a", "b"):
                                if it["compute"].get(side) not in fixed[ax]:
                                    fail(f"{iw}.compute.{side}", f"'{it['compute'].get(side)}' is not a {ax[:-1]} of this table")
                        if it.get("when"):
                            keys(it["when"], "when", f"{iw}.when")
                            if it["when"].get("field") not in fields:
                                fail(f"{iw}.when.field", f"'{it['when'].get('field')}' is not a field in this tool")
                        if it.get("reqWhen"):
                            keys(it["reqWhen"], "reqWhen", f"{iw}.reqWhen")
                            if it["reqWhen"].get("key") not in fixed[ax]:
                                fail(f"{iw}.reqWhen.key", f"'{it['reqWhen'].get('key')}' is not a column of this table")
            if b["kind"] == "calc":
                m = METHODS.get(b.get("method"))
                if not m:
                    fail(f"{bw}.method", f"'{b.get('method')}' is not in the method library. Available: {', '.join(sorted(METHODS))}")
                if "limit" not in b or "limitLabel" not in b:
                    fail(bw, "a calculation needs a recommended limit and a limitLabel")
                for e in m.bind_errors(b, fields, grids):
                    fail(f"{bw}.{e[0]}", e[1])
    return data


def _check_typed(b, where, lists, fail):
    t = b.get("type")
    if t not in FIELD_TYPES:
        fail(f"{where}.type", f"type must be one of {', '.join(sorted(FIELD_TYPES))}")
    if t == "list" and b.get("list") not in lists:
        fail(f"{where}.list", f"there is no list called '{b.get('list')}'")
    if t == "choice" and not b.get("opts"):
        fail(f"{where}.opts", "a choice needs its options")


def load(path) -> Pack:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise PackError(path.name, f"character {e.pos}", f"not valid JSON: {e.msg}", e.lineno) from None
    check(data, path.name, text)
    return Pack(data, path.name, fingerprint(data))


def from_data(data: dict, file="stored pack") -> Pack:
    check(data, file)
    return Pack(data, file, fingerprint(data))


def load_dir(folder):
    """Every pack in a folder: the sound ones, and the refusals with their reasons."""
    good, bad = [], []
    for p in sorted(Path(folder).glob("*.json")):
        try:
            good.append(load(p))
        except PackError as e:
            bad.append(e)
    return good, bad
