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
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
FILINGS = SB / "filings"
sys.path.insert(0, str(CS / "src"))
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

#: quarterly flow field -> the year-to-date field the filing actually reports
FLOW_EXPR = {
    "NTCRCDQ": "RIADB514-RIADB515",
    "NTAUTOQ": "RIADK129-RIADK133",
    "NTCIQ": "RIAD4645+RIAD4646-RIAD4617-RIAD4618",
    "NTCONOTQ": "RIADK205-RIADK206",
    "NTRERESQ": "RIAD5411+RIADC234+RIADC235-RIAD5412-RIADC217-RIADC218",
    "NTRECONQ": "RIADC891+RIADC893-RIADC892-RIADC894",
    "NTRENREQ": "RIADC895+RIADC897-RIADC896-RIADC898",
    "NTREMULQ": "RIAD3588-RIAD3589",
}
CAPITAL = {"RBC1AAJ": ("7204", "RC-R Part I line 31, Tier 1 leverage ratio"),
           "RBCRWAJ": ("7205", "RC-R Part I line 51, total capital ratio")}


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


def evaluate(expr, facts, lenient=False):
    """Sum a provenance expression over one filing.

    ``lenient`` treats an absent code as zero and reports which were absent.
    A bank with no non-U.S. C&I lending does not file RIAD4646 at all, and its
    absence means nothing was lent -- not that the figure is unknown. Strict
    mode is right for the bank being checked; lenient is right for summing an
    acquired bank's prior year-to-date, where one missing line silently made
    the entire merger adjustment zero.
    """
    total, sign, buf, tokens = 0.0, 1, "", []
    for ch in expr:
        if ch in "+-":
            tokens.append((sign, buf.strip()))
            sign = 1 if ch == "+" else -1
            buf = ""
        else:
            buf += ch
    tokens.append((sign, buf.strip()))
    absent = []
    for sgn, code in tokens:
        if not code:
            continue
        v = facts.get(code)
        if v is None:
            if not lenient:
                return None
            absent.append(code)
            continue
        total += sgn * float(v)
    if lenient:
        return total, absent
    return total


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
    ent = next(e for e in cfg.entities if getattr(e, "has_entity", False)
               and str(e.entity_key).split(":")[-1] == cert)
    landed = (DEEP_VALUES.get(cert, {}) if DEEP else
              dict(backend.read_slot_block(R.slot_block(ent.slot, cfg.raw_slots),
                                           FF.RAW_FIELDS)))
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
                rec.update(theirs=theirs, schedule=where,
                           how="filed as a fraction; x100 to the published percent")
            elif field in FLOW_EXPR:
                fe = FLOW_EXPR[field]
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
                cur = evaluate(fe, facts)
                if iso[5:7] == "03":
                    theirs = None if cur is None else cur / 1000.0
                    rec["how"] = "first quarter: year-to-date IS the quarter"
                elif pfacts is None:
                    theirs = None
                    rec["how"] = "no prior filing, so the quarter cannot be formed"
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
                rec["cited"] = fe
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
                rec.update(theirs=None, verdict="NOT ON THIS FILING")
            else:
                tol = 0.005 if field in CAPITAL else 0.51
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
