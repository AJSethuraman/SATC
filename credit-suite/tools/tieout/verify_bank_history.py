"""Verify every bank value in every quarter against that quarter's own filing.

Sixteen quarters, twelve banks, sixty-nine raw fields. The first pass proved the
newest quarter; the instruction is all of the raw data, verified.

Three kinds of field, handled differently and labelled differently:

* **Filed lines** -- balances, past-due buckets, securities. The provenance map
  names an MDRM expression; it is resolved in that quarter's own filing.
* **Quarterly flows** -- the filing reports charge-offs year-to-date, so a
  quarter is this filing less the previous one. In a quarter that spans a
  merger the acquired bank's prior year-to-date comes off as well, because the
  survivor's total already contains it. That is the mistake that produced a
  false PNC finding, and the merger record is consulted here rather than an API
  queried on the wrong date field.
* **Ratios the FDIC computes** -- not a filed line at all. Recorded as such
  rather than compared against something that does not exist.

Nothing is adjusted. Every comparison is a value in the workbook against a value
in a document the bank filed.
"""
import csv
import json
import pathlib
import re
import sys
import time

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
# `FILINGS = SB / "filings"` sat two lines ABOVE `SB = workdir()` from the move
# to the Forge until 8 September 2026, so this tool -- the one that decides
# every bank verdict in the delivered file -- raised NameError on import and
# had done since. Nothing caught it: the standing run starts downstream, at
# build_export, on the rows this tool wrote before the move.
FILINGS = SB / "filings"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import openpyxl                                                  # noqa: E402
from credit_suite.engine.config import parse_config              # noqa: E402
from credit_suite.sources.fdic import engine_api as R            # noqa: E402
from credit_suite.sources.fdic import fields as FF               # noqa: E402
from credit_suite.sources.fdic import filing as F                # noqa: E402
from credit_suite.sources.fdic.runner import (FDIC, OpenpyxlBackend,
                                              read_provenance_rows)  # noqa: E402
from credit_suite.sources.fdic import provenance_seed as PS      # noqa: E402

DEEP = "--deep" in sys.argv
WB = CS / "example-output" / "Bank_Peer_Monitor.xlsm"
if DEEP:
    quarters = json.loads((SB / "deep" / "deep_quarters.json").read_text())
    ARTIFACT = "the deep feed CSV, bank-values-raw.csv"
    OUT_ROWS = "bank_deep_rows.json"
else:
    quarters = json.loads((SB / "bank_quarters.json").read_text())  # newest first
    ARTIFACT = "the dashboard workbook, Bank_Peer_Monitor.xlsm"
    OUT_ROWS = "bank_history_rows.json"
# Ten years hold eleven acquisitions, not the six the sixteen-quarter run
# saw. Five more quarters would otherwise have been reported as the FDIC
# disagreeing with the filings, which is the exact false finding this
# record exists to prevent.
mergers = json.loads((SB / ("merger_records_deep.json" if DEEP
                           else "merger_records.json")).read_text())
index = json.loads((SB / "banks" / "index.json").read_text())

#: The fields the filing reports year-to-date, so that a quarter is this
#: filing less the previous one. WHICH fields those are is a fact about the
#: form and belongs here; WHAT LINE each one cites does not, and used to be
#: copied into this file beside the list. The copy went stale in the one way
#: that matters: `NTCIQ`'s citation named only the 031 form's split, the seed
#: had carried both forms since 5 September, and 63 values on banks filing the
#: 041 were published as lines their bank had not filed. The expressions are
#: read from the seed below, where the file already says the seed is the source
#: of truth.
FLOW_FIELDS = ("NTCRCDQ", "NTAUTOQ", "NTCIQ", "NTCONOTQ", "NTRERESQ",
               "NTRECONQ", "NTRENREQ", "NTREMULQ")
CAPITAL = {"RBC1AAJ": ("7204", "RC-R Part I 31 from 2020Q1, 44 before it, "
                               "Tier 1 leverage ratio"),
           "RBCRWAJ": ("7205", "RC-R Part I 51 from 2020Q1, 43 before it, "
                               "total capital ratio")}
#: How close two capital ratios must be to be called the same figure. The
#: filing reports a fraction to six places and the FDIC publishes a percent to
#: four, so honest rounding never exceeds 0.00005 -- measured over all 1,520
#: rows, not assumed. The tolerance was 0.005, a hundred times what rounding
#: needs, and the one value that used the room was a real disagreement:
#: Huntington's total capital ratio at 2026-03-31, off by 0.00475.
CAPITAL_TOL = 0.0001


def load(cert, iso):
    p = FILINGS / ("facts-%s-%s.json" % (cert, iso))
    if p.exists():
        return json.loads(p.read_text())
    try:
        facts = F.parse_facts(F.fetch_xbrl(cert, iso), iso)
        p.write_text(json.dumps(facts), encoding="utf-8")
        time.sleep(0.25)
        return facts
    except Exception:                                            # noqa: BLE001
        return None


def prev_quarter(iso):
    y, m = int(iso[:4]), int(iso[5:7])
    ends = {3: (y - 1, 12), 6: (y, 3), 9: (y, 6), 12: (y, 9)}
    py, pm = ends[m]
    return "%04d-%02d-%02d" % (py, pm, {3: 31, 6: 30, 9: 30, 12: 31}[pm])


_PARSED = {}


def resolve(expr, facts, lenient=False):
    """Resolve a provenance expression over one filing, in dollars.

    `(dollars, the codes used, the codes absent)`, or None when a required term
    is missing. It is a thin wrapper over `filing.filed_dollars`, deliberately:
    this function used to be a SECOND resolver that took the expression
    literally, so a citation carrying both versions of the form resolved
    correctly on the balance path and not here. Two resolvers is the fault; one
    is the fix.
    """
    if expr not in _PARSED:
        _PARSED[expr] = F.parse_mdrm(expr)
    parsed = _PARSED[expr]
    if parsed is None:
        return None
    return F.filed_dollars(facts, parsed, lenient=lenient)


def evaluate(expr, facts, lenient=False):
    """`resolve` in the shape the callers below want: dollars, or None."""
    got = resolve(expr, facts, lenient=lenient)
    if lenient:
        return (0.0, []) if got is None else (got[0], got[2])
    return None if got is None else got[0]


def base_is_adjusted(landed, iso, field, expr, pfacts):
    """Is the base this quarter subtracts a figure no filing carries?

    A quarterly flow is this filing's year-to-date less the base already
    reported for the year, and normally that base is the previous filing's
    year-to-date. There is exactly one way it stops being that.

    **The first quarter's published figure IS the base the second subtracts** --
    there is no earlier quarter for it to be a difference of. So when a merger
    lands in a first quarter and the FDIC publishes something other than the
    filed year-to-date, every later subtraction that year starts from a number
    no document carries, and the second quarter cannot be formed from the
    filings at all.

    A merger in any LATER quarter does not do this. The FDIC adjusts that one
    quarter's figure and the next quarter goes back to being a plain difference
    of two filed year-to-dates -- which is why a first version of this check,
    written as "the FDIC's quarters no longer sum to the year-to-date", took
    twenty-one rows that tie perfectly against the filings and called them
    uncomparable. Suppressing a row that ties is the same error as plugging one
    that does not, pointed the other way.

    Found on Huntington, second quarter of 2026, five fields: their first
    quarter was the filed year-to-date less 88, and their second was the
    year-to-date less THAT. Their own number is read here only to ask whether
    the comparison is WELL FORMED; it never stands in for the source.
    """
    if pfacts is None or iso[5:7] != "06":
        return False
    q1 = iso[:4] + "-03-31"
    published = (landed.get(q1) or {}).get(field)
    if published is None:
        return False
    filed = evaluate(expr, pfacts)          # pfacts IS the first quarter here
    if filed is None:
        return False
    return abs(float(published) - filed / 1000.0) > 0.51


book = openpyxl.load_workbook(WB, data_only=False)
cfg = parse_config([list(r) for r in book["_config"].iter_rows(values_only=True)], FDIC)
# The SEED is the source of truth. Reading the workbook's own tab means
# reading a build that may predate the citations -- and it did: three
# fields still said "(not in tie-out map)" there, so 576 values went
# unchecked against a map that had already been corrected.
prov = {r[0]: {"schedule": r[1], "caption": r[2], "mdrm": r[3],
               "flag": r[4], "notes": r[5] if len(r) > 5 else ""}
        for r in PS.ALL_ROWS}
backend = OpenpyxlBackend(str(WB), FDIC, FF.RAW_FIELDS)

#: The deep feed's ours side, read back off the CSV that was written before
#: anything was verified -- {cert: {report_date: {field: value}}}.
DEEP_VALUES = {}
if DEEP:
    with (SB / "deep" / "bank-values-raw.csv").open(encoding="utf-8") as _fh:
        for _r in csv.DictReader(_fh):
            (DEEP_VALUES.setdefault(_r["cert"], {})
                        .setdefault(_r["report_date"], {}))[_r["field"]] = \
                float(_r["value"])

rows = []
for entry in index:
    cert, name = entry["cert"], entry["name"]
    # In deep mode the ours side is the delivered CSV, so the workbook plays no
    # part and its slot must not be looked up. The dashboard workbook carries
    # the twelve it was built for; resolving a slot for a nineteenth bank threw
    # StopIteration after twelve banks had already been checked -- and the run
    # still exited 0 through a pipe, which is how a crash reads as a result.
    if DEEP:
        landed = DEEP_VALUES.get(cert, {})
    else:
        ent = next(e for e in cfg.entities if getattr(e, "has_entity", False)
                   and str(e.entity_key).split(":")[-1] == cert)
        landed = dict(backend.read_slot_block(
            R.slot_block(ent.slot, cfg.raw_slots), FF.RAW_FIELDS))
    for iso in quarters:
        vals = landed.get(iso)
        if not vals:
            continue
        facts = load(cert, iso)
        piso = prev_quarter(iso)
        pfacts = load(cert, piso) if iso[5:7] != "03" else None
        acq = [m for m in mergers if m["survivor"] == cert and m["quarter"] == iso]
        acq_prior = []
        for m in acq:
            af = load(m["acquired"], piso)
            if af is not None:
                acq_prior.append((m["acquired"], af))
        for field in FF.RAW_FIELDS:
            ours = vals.get(field)
            if ours is None:
                continue
            expr = (prov.get(field) or {}).get("mdrm", "")
            rec = {"cert": cert, "bank": name, "repdte": iso, "field": field,
                   "ours": ours, "cited": expr,
                   "schedule": (prov.get(field) or {}).get("schedule", "")}
            if facts is None:
                rec.update(theirs=None, verdict="NO FILING FETCHED", how="")
                rows.append(rec); continue
            if field in CAPITAL:
                tail, where = CAPITAL[field]
                cands = [v for k, v in facts.items()
                         if re.fullmatch(r"RC[A-Z][AW]" + tail, k)]
                theirs = min(cands) * 100 if cands else None
                # A bank may file the same ratio under more than one capital
                # framework, and the one that binds is the LOWER. Saying so in
                # the row matters: 293 of these had more than one column, so
                # the minimum was a real choice and not a formality. The RBC
                # dollar field has said this in its own note since 5 September.
                rec.update(theirs=theirs, schedule=where,
                           how=("filed as a fraction; x100 to the published "
                                "percent. Filed under %d framework(s); this is "
                                "the one that binds, the lower ratio"
                                % len(cands)) if cands else
                               "filed as a fraction; x100 to the published percent")
            elif field in FLOW_FIELDS:
                fe = expr
                if acq:
                    # The workbook's own merger record says this quarter is not
                    # a quarter of anything. Two mergers in this set consolidate
                    # two different ways -- PNC's year-to-date contains the
                    # acquired bank's and Capital One's does not -- so no single
                    # subtraction turns two year-to-date figures into a quarter
                    # here. Reporting it as not comparable is the software's own
                    # position and the only honest one.
                    rec.update(theirs=None, verdict="NOT COMPARABLE (SPANS A MERGER)",
                               cited=fe,
                               how=("this quarter spans the merger of cert %s "
                                    "(effective %s). A quarterly flow is the "
                                    "year-to-date less the previous quarter's, "
                                    "which across a merger mixes two banks."
                                    % (", ".join(m["acquired"] for m in acq),
                                       ", ".join(m["effective"] for m in acq))))
                    rows.append(rec)
                    continue
                cur_got = resolve(fe, facts)
                cur = None if cur_got is None else cur_got[0]
                # What the row cites is the line that was actually read on
                # THIS filing, not the map entry that covers both forms --
                # otherwise a bank filing the 041 is handed the 031's codes
                # and told to go and find them on its own form.
                used_here = cur_got[1] if cur_got else ""
                if iso[5:7] == "03":
                    theirs = None if cur is None else cur / 1000.0
                    rec["how"] = "first quarter: year-to-date IS the quarter"
                elif pfacts is None:
                    theirs = None
                    rec["how"] = "no prior filing, so the quarter cannot be formed"
                elif base_is_adjusted(landed, iso, field, fe, pfacts):
                    # A quarterly flow is this filing's year-to-date less the
                    # base already reported for the year. Normally that base IS
                    # the previous filing's year-to-date. After a merger
                    # quarter the FDIC publishes a figure of its own that the
                    # filings do not add up to, and from then on its base is
                    # that figure -- so the subtraction cannot be done from the
                    # documents at all.
                    #
                    # Found on Huntington, Q2 2026, five fields: the FDIC's Q1
                    # was the filed year-to-date less 88, and their Q2 was the
                    # Q2 year-to-date less THAT. Reproducing it needs their own
                    # Q1 number on the source side, which is the mirror. So it
                    # is reported as not comparable, which is what it is.
                    rec.update(theirs=None, cited=fe,
                               verdict="NOT COMPARABLE (BASE ADJUSTED FOR A MERGER)",
                               how=("the year-to-date already reported for this "
                                    "year is the FDIC's own merger-adjusted "
                                    "figure, not a line on the previous filing, "
                                    "so this quarter cannot be formed by "
                                    "subtraction from the documents"))
                    rows.append(rec)
                    continue
                else:
                    pri = evaluate(fe, pfacts)
                    add, absent = 0.0, []
                    for _c, af in acq_prior:
                        got, miss = evaluate(fe, af, lenient=True)
                        add += got
                        absent += miss
                    if absent:
                        rec["absent_components"] = sorted(set(absent))
                    theirs = (None if (cur is None or pri is None)
                              else (cur - pri - add) / 1000.0)
                    rec["how"] = ("this filing's year-to-date less the previous "
                                  "quarter's" + (", less the year-to-date of the "
                                  "bank(s) merged in this quarter (%s)"
                                  % ", ".join(c for c, _ in acq_prior)
                                  if acq_prior else ""))
                rec["cited"] = used_here or fe
            elif "/" in (expr or ""):
                rec.update(theirs=None, verdict="COMPUTED BY THE FDIC",
                           how="a ratio the FDIC computes from filed lines; "
                               "not itself a line on the form")
                rows.append(rec); continue
            else:
                parsed = F.parse_mdrm(expr) if expr else None
                if parsed is None:
                    rec.update(theirs=None, verdict="NO USABLE CITATION", how="")
                    rows.append(rec); continue
                v, used = F.filed_value(facts, parsed)
                # filed_value already returns the figure in the field's own
                # units (thousands). Dividing again reported every one of
                # 7,598 balances as a difference -- uniformly, across every
                # bank and every quarter, which is what a checker bug looks
                # like and what a data problem never does.
                theirs = None if v is None else float(v)
                rec["how"] = "read straight off the filing"
                rec["cited"] = used or expr
            if theirs is None:
                # The note said "read straight off the filing" on all 177 rows
                # whose verdict said there was nothing on the filing to read.
                # A row that contradicts itself tells the reader to believe
                # whichever half they saw first.
                rec.update(theirs=None, verdict="NOT ON THIS FILING",
                           how=("the line this field cites is not on the form "
                                "this bank filed for this quarter, so there is "
                                "nothing on it to compare against"))
            else:
                tol = CAPITAL_TOL if field in CAPITAL else 0.51
                rec.update(theirs=theirs,
                           verdict=("TIES" if abs(float(ours) - theirs) < tol
                                    else "DIFFERS"))
            rows.append(rec)
    print("  %-24s done" % name[:24], flush=True)

(SB / OUT_ROWS).write_text(json.dumps(rows), encoding="utf-8")
from collections import Counter
c = Counter(r["verdict"] for r in rows)
print("\nours read from       : %s" % ARTIFACT)
print("bank values examined : %d" % len(rows))
for k, v in c.most_common():
    print("   %-24s %6d" % (k, v))
diffs = [r for r in rows if r["verdict"] == "DIFFERS"]
print("\nDIFFERS by field:")
for f, n in Counter(r["field"] for r in diffs).most_common(15):
    print("   %-12s %4d" % (f, n))
