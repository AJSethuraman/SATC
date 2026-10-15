"""The book: one file that says everything a workbook is built from.

``threshold-engine book BOOK.json OUT.xlsx`` reads it and writes one workbook:
Summary and Decide first, then Thresholds, Assess and the reference tabs, and,
when the book has a ``peers`` section, the peer tabs built into the same file.
No Excel is needed to build it; the Decide tab's slicers are written into the
file (``slicers.py``).

Every key is required and none has a default (the tool's rule: a missing
judgement is refused, not filled in). Relative paths are read from the book's
own folder, so a book and its files can be copied to another machine whole.

    {
      "workbook": {"name", "unit", "direction", "frequency", "smoothing",
                   "floor_at_zero", "moderate_halfwidth", "low_step", "high_z",
                   "on_the_line", "half_lives", "percentiles", "horizon",
                   "min_history"},
      "parts": ["Product", "Measure", "Source"],
      "series": [{"Product": ..., "Measure": ..., "Source": ..., "file": ...}]
                or "a CSV with those columns",
      "not_in_book": [{"Product": ..., "Measure": ..., "Source": ..., "why": ...}],
      "compare": ["KeyBank", "Peer group"] or null,
      "notes": ["..."],
      "peers": null or {every setting 'peers build' takes, by its keyword name}
    }

A part value of ``*`` in ``not_in_book`` stands for every value of that part.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

from .series import LABEL_RULE, label_ok

WORKBOOK_KEYS = ("name", "unit", "direction", "frequency", "smoothing", "floor_at_zero", "moderate_halfwidth",
                 "low_step", "high_z", "on_the_line", "half_lives", "percentiles", "horizon", "min_history")
TOP_KEYS = ("workbook", "parts", "series", "not_in_book", "compare", "notes", "peers")
#: 'peers build' settings, by the keyword ``peers.run.build`` takes; paths among them.
PEERS_KEYS = ("cache", "roster", "series_dir", "first", "last", "products", "mergers", "absorptions",
              "extra_acquisitions", "industry_combined", "jump", "acquisition_share", "min_book", "exempt_self",
              "pack", "min_banks", "rank_by", "last_n", "min_obs", "base_quarter", "index_min_book",
              "lagged_years", "lag_years", "normalisation_years", "mix_base_year", "delinquency")
PEERS_PATHS = ("cache", "roster", "series_dir", "mergers", "absorptions")
#: The peer tabs' titles inside the book's workbook, which has its own Data, Glossary and Run.
PEER_TAB_NAMES = {"Pack": "Peers pack", "Peers": "Peers", "Delinquency": "Peers delinquency",
                  "Balances": "Peers balances", "Lagged": "Peers lagged", "Normalisation": "Peers normalisation",
                  "Mix": "Peers mix", "Glossary": "Peers glossary", "Data": "Peers data",
                  "DelinquencyData": "Peers delinquency data", "Run": "Peers run"}


class BookError(ValueError):
    """A book that cannot be built from, with every problem found."""


def _keys(where: str, got: dict, want, problems: List[str]) -> None:
    if not isinstance(got, dict):
        problems.append("%s must be an object with the keys %s" % (where, ", ".join(want)))
        return
    for k in want:
        if k not in got:
            problems.append("%s is missing %r (every key is required; none has a default)" % (where, k))
    for k in got:
        if k not in want:
            problems.append("%s has %r, which is not a key it takes (check the spelling)" % (where, k))


def load(path) -> dict:
    """Read and check a book. Returns ``{"workbook": settings, "series":
    [(label, Path)], "decide": spec for workbook.build, "peers": settings or
    None, "folder": Path}``; raises BookError listing every problem at once."""
    path = Path(path)
    folder = path.resolve().parent
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BookError("%s is not valid JSON: %s" % (path.name, e)) from None
    problems: List[str] = []
    _keys("the book", raw, TOP_KEYS, problems)
    if problems:
        raise BookError("\n".join(problems))
    _keys("workbook", raw["workbook"], WORKBOOK_KEYS, problems)
    parts = raw["parts"]
    if not (isinstance(parts, list) and len(parts) == 3 and all(isinstance(p, str) and p.strip() for p in parts)):
        problems.append("parts must be a list of three names, for example [\"Product\", \"Measure\", \"Source\"]")
        raise BookError("\n".join(problems))

    def resolve(p) -> Path:
        q = Path(p)
        return q if q.is_absolute() else folder / q

    rows = raw["series"]
    if isinstance(rows, str):
        src = resolve(rows)
        if not src.exists():
            problems.append("series: the file %s does not exist" % src)
            rows = []
        else:
            with src.open(newline="", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
            # A CSV's file paths are read from the CSV's own folder.
            for r in rows:
                if r.get("file") and not Path(r["file"]).is_absolute():
                    r["file"] = str(src.parent / r["file"])
    if not isinstance(rows, list) or not rows:
        problems.append("series must list at least one series")
        rows = []
    series, decide_parts, seen = [], {}, set()
    for i, r in enumerate(rows, start=1):
        where = "series %d" % i
        if not isinstance(r, dict):
            problems.append("%s must be an object" % where)
            continue
        _keys(where, r, list(parts) + ["file"], problems)
        if any(k not in r for k in list(parts) + ["file"]):
            continue
        vals = tuple(str(r[p]).strip() for p in parts)
        if not all(vals):
            problems.append("%s: every part needs a value" % where)
            continue
        label = " - ".join(vals)
        if any(" - " in v for v in vals):
            problems.append("%s: a part value may not hold ' - ', which joins the parts into the label" % where)
            continue
        if not label_ok(label):
            problems.append("%s: %r can't be used: %s" % (where, label, LABEL_RULE))
            continue
        if label.casefold() in seen:
            problems.append("%s: %r is listed twice" % (where, label))
            continue
        seen.add(label.casefold())
        series.append((label, resolve(r["file"])))
        decide_parts[label] = vals
    absent = raw["not_in_book"]
    if not isinstance(absent, list):
        problems.append("not_in_book must be a list (empty to say there is nothing missing to explain)")
        absent = []
    absent_out = []
    for i, a in enumerate(absent, start=1):
        where = "not_in_book %d" % i
        _keys(where, a, list(parts) + ["why"], problems)
        if isinstance(a, dict) and all(k in a for k in list(parts) + ["why"]):
            if not str(a["why"]).strip():
                problems.append("%s: why must say why" % where)
            absent_out.append({"parts": {p: a[p] for p in parts}, "why": str(a["why"]).strip()})
    compare = raw["compare"]
    third = {v[2] for v in decide_parts.values()}
    if compare is not None:
        if not (isinstance(compare, list) and len(compare) == 2 and all(c in third for c in compare)
                and compare[0] != compare[1]):
            problems.append("compare must be null or two different values of %s that the series use (%s)"
                            % (parts[2], ", ".join(sorted(third))))
            compare = None
        else:
            compare = tuple(compare)
    notes = raw["notes"]
    if not (isinstance(notes, list) and all(isinstance(t, str) for t in notes)):
        problems.append("notes must be a list of sentences (empty for none)")
        notes = []
    peers = raw["peers"]
    if peers is not None:
        _keys("peers", peers, PEERS_KEYS, problems)
        if isinstance(peers, dict) and all(k in peers for k in PEERS_KEYS):
            peers = dict(peers)
            for k in PEERS_PATHS:
                peers[k] = resolve(peers[k])
    # A series file that is not there is only a problem if no peers build will write it.
    if peers is None:
        for label, p in series:
            if not p.exists():
                problems.append("the file for %r does not exist: %s" % (label, p))
    if problems:
        raise BookError("\n".join(problems))
    wbk = dict(raw["workbook"])
    wbk["half_lives"] = tuple(wbk["half_lives"])
    wbk["percentiles"] = tuple(wbk["percentiles"])
    return {"workbook": wbk, "series": series, "peers": peers, "folder": folder,
            "decide": {"names": list(parts), "parts": decide_parts, "absent": absent_out, "compare": compare,
                       "notes": notes}}


def build(book_path, out, say=print) -> dict:
    """Build the book's workbook at ``out``. With a peers section, the peers
    build runs first, into the same workbook, and writes the series CSVs the
    book then reads."""
    from openpyxl import Workbook

    from . import workbook as WB

    bk = load(book_path)
    out = Path(out)
    host = Workbook()
    blank = host.active
    if bk["peers"] is not None:
        from .peers import run as peers_run
        peers_run.build(None, into=host, names=PEER_TAB_NAMES, say=say, **bk["peers"])
        missing = [(lbl, p) for lbl, p in bk["series"] if not p.exists()]
        if missing:
            raise BookError("\n".join("the file for %r was not written by the peers build either: %s" % m
                                      for m in missing))

    def tidy(wb):
        if blank.title in wb.sheetnames and blank.max_row == 1 and blank["A1"].value is None:
            wb.remove(blank)
        order = ["Summary", "Decide", "Thresholds", "Assess", "Peers", "Peers delinquency", "Peers balances",
                 "Peers pack", "Peers lagged", "Peers normalisation", "Peers mix", "Synthesis", "Chart",
                 "Evidence", "Backtest", "Sources", "Glossary", "Peers glossary", "Run", "Peers run", "Data",
                 "Peers data", "Peers delinquency data"]
        known = [wb[t] for t in order if t in wb.sheetnames]
        wb._sheets = known + [ws for ws in wb._sheets if ws not in known]
        wb.active = wb.sheetnames.index("Summary")
        for ws in wb.worksheets:
            ws.sheet_view.tabSelected = ws.title == "Summary"

    info = WB.build(out, bk["series"], decide=bk["decide"], into=host, before_save=tidy, **bk["workbook"])
    from . import slicers
    d = info["decide"]
    p0, p1, p2 = bk["decide"]["names"]
    first = bk["series"][0][0]
    picks = dict(zip((p0, p1, p2), bk["decide"]["parts"][first]))
    slicers.add_table_slicers(out, "Decide", d["table"], [
        {"column": name, "caption": name, "selected": picks[name]} for name in (p0, p1, p2)])
    return info
