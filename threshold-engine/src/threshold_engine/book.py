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
      "peers": null or {every setting 'peers build' takes, by its keyword name},
      "internal": null or {"file": the bank's internal file (docs/INTERNAL-IMPORT.md),
                           "source": the source its series go under, e.g. "KeyBank internal",
                           "segments": true to add each segment as a series as well,
                           "measures": {internal measure: the book's measure it is},
                           "call_report_source": the source holding the bank's Call Report series}
    }

With an internal section, run on site only: the file is checked as the
``internal check`` command checks it; each product's composite (and, when
asked, each segment) is written beside the workbook as a series for every
measure the book maps; and the file's rows fill the Internal data tab. A
measure the book does not map stays on the Internal tab: whether an internal
30+ includes nonaccrual loans is the book's to say, and is never assumed.

A part value of ``*`` in ``not_in_book`` stands for every value of that part.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .series import LABEL_RULE, label_ok

WORKBOOK_KEYS = ("name", "unit", "direction", "frequency", "smoothing", "floor_at_zero", "moderate_halfwidth",
                 "low_step", "high_z", "on_the_line", "half_lives", "percentiles", "horizon", "min_history")
TOP_KEYS = ("workbook", "parts", "series", "not_in_book", "compare", "notes", "peers", "internal")
#: The internal section: the file (docs/INTERNAL-IMPORT.md) and the judgments made about it.
INTERNAL_KEYS = ("file", "source", "segments", "measures", "call_report_source")
#: 'peers build' settings, by the keyword ``peers.run.build`` takes; paths among them.
PEERS_KEYS = ("cache", "roster", "series_dir", "first", "last", "products", "mergers", "absorptions",
              "extra_acquisitions", "industry_combined", "jump", "acquisition_share", "min_book", "exempt_self",
              "pack", "min_banks", "rank_by", "last_n", "min_obs", "base_quarter", "index_min_book",
              "lagged_years", "lag_years", "normalisation_years", "mix_base_year", "delinquency")
PEERS_PATHS = ("cache", "roster", "series_dir", "mergers", "absorptions")
#: The peer tabs' titles inside the book's workbook, which has its own Data, Glossary and Run.
#: One dashboard (Peers) and its hidden Workings since 14 Oct 2026; before, one tab per view. Since
#: 15 Oct 2026 the peer glossary and run record are sections of the book's own Glossary and Run.
PEER_TAB_NAMES = {"Peers": "Peers", "Workings": "Peers workings", "Glossary": "Glossary",
                  "Data": "Peers data", "DelinquencyData": "Peers delinquency data", "Run": "Run"}


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
    internal = _internal(raw["internal"], resolve, decide_parts, problems)
    if problems:
        raise BookError("\n".join(problems))
    wbk = dict(raw["workbook"])
    wbk["half_lives"] = tuple(wbk["half_lives"])
    wbk["percentiles"] = tuple(wbk["percentiles"])
    return {"workbook": wbk, "series": series, "peers": peers, "folder": folder, "internal": internal,
            "decide": {"names": list(parts), "parts": decide_parts, "absent": absent_out, "compare": compare,
                       "notes": notes}}


def _internal(spec, resolve, decide_parts, problems) -> Optional[dict]:
    """The book's internal section, checked: None, or the file read by
    ``internal.read`` (every one of its problems listed here) and the
    choices, each stated. Which workbook measure an internal measure is, is a
    judgment the book states; one it does not state stays on the Internal
    tab only."""
    if spec is None:
        return None
    _keys("internal", spec, INTERNAL_KEYS, problems)
    if not isinstance(spec, dict) or any(k not in spec for k in INTERNAL_KEYS):
        return None
    from . import internal as I
    products = {v[0] for v in decide_parts.values()}
    measures = {v[1] for v in decide_parts.values()}
    sources = {v[2] for v in decide_parts.values()}
    out = {"file": resolve(spec["file"]), "source": spec["source"], "segments": spec["segments"],
           "measures": spec["measures"], "call_report_source": spec["call_report_source"], "data": None}
    src = spec["source"]
    if not (isinstance(src, str) and src.strip() and label_ok(src) and " - " not in src):
        problems.append("internal: source must name the internal series' source, for example \"KeyBank "
                        "internal\" (%s, and no ' - ')" % LABEL_RULE)
    elif src in sources:
        problems.append("internal: source %r is already a source of the book's series; name the internal one "
                        "differently" % src)
    if not isinstance(spec["segments"], bool):
        problems.append("internal: segments must be true (each segment also becomes a series) or false")
    ms = spec["measures"]
    if not isinstance(ms, dict):
        problems.append("internal: measures must be an object from an internal measure (%s) to the workbook "
                        "measure it is; {} puts none on the views" % ", ".join(I.MEASURES))
    else:
        for k, v in ms.items():
            if k not in I.MEASURES:
                problems.append("internal: measures has %r, which is not an internal measure (%s)"
                                % (k, ", ".join(I.MEASURES)))
            elif v not in measures:
                problems.append("internal: measures maps %s to %r, which is not a measure of the book's series "
                                "(%s)" % (k, v, ", ".join(sorted(measures))))
        if len(set(ms.values())) != len(ms):
            problems.append("internal: measures maps two internal measures to one workbook measure")
    if spec["call_report_source"] not in sources:
        problems.append("internal: call_report_source must be the source holding the bank's Call Report series, "
                        "one of %s" % ", ".join(sorted(sources)))
    if not out["file"].exists():
        problems.append("internal: the file %s does not exist" % out["file"])
        return out
    try:
        out["data"] = I.read(out["file"])
    except I.Refused as e:
        problems.extend("internal file: " + p for p in e.problems)
        return out
    if spec["segments"] is True:
        for p, seg in out["data"].keys():
            if seg != I.ALL and not (label_ok(seg) and " - " not in seg):
                problems.append("internal: segment %r of %s can't name a source (%s, and no ' - ')"
                                % (seg, p, LABEL_RULE))
    if not any(p in products for p, _ in out["data"].keys()):
        problems.append("internal: the file's products (%s) are none of the book's (%s)"
                        % (", ".join(sorted({p for p, _ in out["data"].keys()})), ", ".join(sorted(products))))
    return out


def internal_series(bk: dict, out_dir: Path) -> List[Tuple[str, Path, Tuple[str, str, str]]]:
    """Write the book's internal series to ``out_dir`` and return ``[(label,
    path, parts)]``: the composite of every product the book has, for every
    measure the book maps, under the internal source; and each segment too,
    under "SOURCE: SEGMENT", when the book says so. By the public method
    (``internal.composite_series`` and ``internal.series``), each from its
    latest unbroken run, with notes saying what it is."""
    from . import internal as I
    from .peers.books import write_series
    from .peers.run import series_note, slug, unbroken_tail
    spec = bk["internal"]
    data = spec["data"]
    products = {v[0] for v in bk["decide"]["parts"].values()}
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for p in dict.fromkeys(pr for pr, _ in data.keys()):
        if p not in products:
            continue
        segs = [s for pr, s in data.keys() if pr == p and s != I.ALL] if spec["segments"] else []
        for key, measure in spec["measures"].items():
            m = I.MEASURES[key]
            for seg in [None] + segs:
                if seg is None:
                    pairs = I.composite_series(data, p, key)
                    src, what = spec["source"], ("the composite: %s" % (
                        "the All rows" if I.composite_segment(data, p) == I.ALL else "every segment summed"))
                else:
                    pairs = I.series(data, p, seg, key)
                    src, what = "%s: %s" % (spec["source"], seg), "segment %s: %s" % (seg, data.segments[seg])
                tail, before, after = unbroken_tail(pairs)
                if not tail:
                    continue
                path = out_dir / ("internal_%s_%s_%s.csv" % (slug(p), slug(seg or "composite"), key))
                note = ["measure: %s. %s, %s, internal" % (m.title, p, what), "numerator: %s" % m.numerator,
                        "denominator: %s" % m.denominator,
                        "basis: %s. The file's own basis: %s" % (m.basis, data.notes["basis"]),
                        "as-of: %s" % data.notes["as-of"], "source: %s" % data.notes["source"],
                        "entity: %s" % data.notes["entity"],
                        "Written by 'book' from %s. Internal data: run on site, never committed."
                        % Path(data.path).name]
                write_series(tail, path, series_note(note, tail, before, after))
                made.append(("%s - %s - %s" % (p, measure, src), path, (p, measure, src)))
    return made


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
    peer_tabs = None
    if bk["peers"] is not None:
        from .peers import run as peers_run
        peer_tabs = peers_run.build(None, into=host, names=PEER_TAB_NAMES, say=say, **bk["peers"])["info"]["sheets"]
        missing = [(lbl, p) for lbl, p in bk["series"] if not p.exists()]
        if missing:
            raise BookError("\n".join("the file for %r was not written by the peers build either: %s" % m
                                      for m in missing))

    def tidy(wb):
        if blank.title in wb.sheetnames and blank.max_row == 1 and blank["A1"].value is None:
            wb.remove(blank)
        order = ["Decide", "Summary", "Peers", "Thresholds", "Internal", "Synthesis", "Evidence", "Backtest",
                 "Glossary", "Sources", "Run", "Data", "Peers data", "Peers delinquency data", "Internal data",
                 "SynthesisData", "Assess", "Chart", "Peers workings"]
        known = [wb[t] for t in order if t in wb.sheetnames]
        wb._sheets = known + [ws for ws in wb._sheets if ws not in known]
        wb.active = wb.sheetnames.index("Summary")
        for ws in wb.worksheets:
            ws.sheet_view.tabSelected = ws.title == "Summary"

    series, decide = list(bk["series"]), dict(bk["decide"])
    if bk["internal"] is not None:
        # The bank's own figures, on site: their series sit beside the
        # workbook, never in the repository, and the rows fill Internal data.
        from .peers import roster as R
        spec = bk["internal"]
        made = internal_series(bk, out.parent / (out.stem + " internal series"))
        taken = {lbl.casefold() for lbl, _ in series}
        for lbl, path, parts_ in made:
            if lbl.casefold() in taken:
                raise BookError("internal: the series %r is already in the book" % lbl)
            series.append((lbl, path))
        decide["parts"] = dict(decide["parts"], **{lbl: parts_ for lbl, _, parts_ in made})
        tab_keys = ("net-charge-off-rate", "gross-charge-off-rate", "dpd-30-plus-quarter-end",
                    "dpd-60-plus-quarter-end", "dpd-90-plus-quarter-end")
        decide["internal"] = {
            "rows": list(spec["data"].rows), "source": spec["source"],
            "measures": {k: spec["measures"][k] for k in tab_keys if k in spec["measures"]},
            "call_report": spec["call_report_source"],
            "peers_self": R.self_bank(R.load(bk["peers"]["roster"]))["short"] if bk["peers"] else None}
        say("internal: %d rows from %s; %d series added under %s"
            % (len(spec["data"].rows), Path(spec["data"].path).name, len(made), spec["source"]))

    info = WB.build(out, series, decide=decide, into=host, before_save=tidy, **bk["workbook"])
    if peer_tabs:
        # The peer charts draw a missing quarter as a gap, which is set on the saved file.
        from .peers.peers_workbook import na_as_gap
        na_as_gap(out, peer_tabs)
    return info
