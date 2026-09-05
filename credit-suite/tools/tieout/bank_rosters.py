"""A structured roster per bank: the workbook's cells against the filed report.

The ours side is read out of `Bank_Peer_Monitor.xlsm` -- the cells a person
opens -- through exactly the path the runner's own tie-out uses, so this is not
a second implementation that could agree with itself. The filed side comes from
each bank's own XBRL as the FFIEC serves it: the document the bank signed, not
the FDIC's republication of it.

Five lines per bank come back "skipped with a stated reason". Two of those
reasons dissolve on one push, and both were closed by hand for KeyBank earlier:

  * the two capital ratios are said to have no single filed line to compare a
    percentage with -- except the filing publishes them itself, as percentages,
    on Schedule RC-R
  * the three quarterly flows are said to be year-to-date in the filing, which
    is true; a quarter is then the difference of two filings, which is the
    subtraction the objection had just finished describing

So all five are closed for every bank, rather than shipping twelve documents
that each stop five lines short of the end.
"""
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
BANKS = SB / "banks"
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import openpyxl                                                  # noqa: E402
from credit_suite.engine.config import parse_config              # noqa: E402
from credit_suite.sources.fdic import engine_api as R            # noqa: E402
from credit_suite.sources.fdic import fields                     # noqa: E402
from credit_suite.sources.fdic import filing as F                # noqa: E402
from credit_suite.sources.fdic.runner import (FDIC, OpenpyxlBackend,
                                              read_provenance_rows,
                                              facsimile_url)     # noqa: E402

WB = CS / "example-output" / "Bank_Peer_Monitor.xlsm"
Q2, Q1 = "2026-06-30", "2026-03-31"

#: The three quarterly flows the runner skips. The filing reports charge-offs
#: and recoveries YEAR-TO-DATE, so the second quarter alone is the Q2 figure
#: minus the Q1 figure -- no calendar-year boundary sits between them.
FLOWS = {
    "NTCRCDQ": ("RIADB514-RIADB515", "credit card net charge-offs",
                "RI-B Part I line 5.a: charge-offs less recoveries, credit cards"),
    "NTAUTOQ": ("RIADK129-RIADK133", "auto loan net charge-offs",
                "RI-B Part I line 5.c: charge-offs less recoveries, auto loans"),
    # C&I on form 031 is split by borrower: line 4.a to U.S. addressees and
    # 4.b to non-U.S. addressees. The FDIC's figure is both, which is also how
    # the workbook's C&I BALANCE is built (RCFD1763+RCFD1764). Using 4.a alone
    # understated ten of twelve banks -- by 9% at JPMorgan and 57% at Goldman.
    "NTCIQ":   ("RIAD4645+RIAD4646-RIAD4617-RIAD4618", "C&I net charge-offs",
                "RI-B Part I line 4.a and 4.b: charge-offs less recoveries, "
                "C&I loans to U.S. and non-U.S. addressees"),
}
#: The two capital ratios, filed as PERCENTAGES on Schedule RC-R Part I. The
#: bank files them; nothing here recomputes them. They are absent from the
#: parsed XBRL, so they are read off the facsimile -- which is the document the
#: regulator serves and the one a reviewer would open anyway.
#:
#: The code prefix is RCFA on form 031 (consolidated, foreign offices) and RCOA
#: on 041. Matching the caption and accepting either prefix means the same rule
#: works for a filer of either form, rather than working for the twelve banks
#: that happen to be in this workbook.
RATIOS = {
    "RBC1AAJ": (r"31\. Leverage ratio", "7204", "Tier 1 leverage ratio",
                "RC-R Part I, line 31"),
    "RBCRWAJ": (r"5\d\. Total capital ratio", "7205", "Total capital ratio",
                "RC-R Part I, line 51"),
}


#: Read off each facsimile by bank_ratios.py, which runs under the venv that
#: has PyMuPDF. Kept as a separate step rather than importing a PDF library
#: into the workbook path.
RATIO_READS = json.loads((SB / "bank_ratios.json").read_text())


def evaluate(expr, facts):
    """Sum/difference of MDRM codes, as the provenance map writes them."""
    total, ok, used = 0.0, True, []
    term, sign = "", 1
    tokens, buf = [], ""
    for ch in expr:
        if ch in "+-":
            tokens.append((sign, buf.strip()))
            sign = 1 if ch == "+" else -1
            buf = ""
        else:
            buf += ch
    tokens.append((sign, buf.strip()))
    for sgn, code in tokens:
        if not code:
            continue
        used.append(code)
        v = facts.get(code)
        if v is None:
            ok = False
            continue
        total += sgn * float(v)
    return (total if ok else None), used


book = openpyxl.load_workbook(WB, data_only=False)
rows = [list(r) for r in book["_config"].iter_rows(values_only=True)]
cfg = parse_config(rows, FDIC)
prov = read_provenance_rows(book)
index = json.loads((BANKS / "index.json").read_text())
backend = OpenpyxlBackend(str(WB), FDIC, fields.RAW_FIELDS)

expressions = {f: prov[f]["mdrm"] for f in fields.RAW_FIELDS
               if f in prov and prov[f]["mdrm"]}
print("provenance expressions for raw fields: %d of %d"
      % (len(expressions), len(fields.RAW_FIELDS)))

out = []
for entry in index:
    cert, name, slot = entry["cert"], entry["name"], entry["slot"]
    entity = next(e for e in cfg.entities
                  if getattr(e, "has_entity", False)
                  and str(e.entity_key).split(":")[-1] == str(cert))
    block = R.slot_block(entity.slot, cfg.raw_slots)
    quarters = backend.read_slot_block(block, fields.RAW_FIELDS)
    iso, landed = quarters[0]
    assert iso == Q2, (cert, iso)

    facts2 = json.loads((BANKS / entry["filings"][Q2]["facts"]).read_text())
    facts1 = json.loads((BANKS / entry["filings"][Q1]["facts"]).read_text())

    tie_rows = F.tie(facts2, landed, expressions, units=fields.FIELD_UNITS)
    lines = []
    for r in tie_rows:
        lines.append({
            "field": r.field,
            "ours": r.landed_thousands,
            "filed": r.filed_thousands,
            "used": r.used or "",
            "verdict": r.verdict,
            "note": r.note or "",
            "schedule": (prov.get(r.field) or {}).get("schedule", ""),
            "caption": (prov.get(r.field) or {}).get("caption", ""),
            "how": "read straight off the filing",
        })

    # ---- close the three quarterly flows, by differencing two filings -------
    for field, (expr, what, where) in FLOWS.items():
        ours = landed.get(field)
        v2, used = evaluate(expr, facts2)
        v1, _ = evaluate(expr, facts1)
        filed = None if (v2 is None or v1 is None) else (v2 - v1) / 1000.0
        verdict = "COULD NOT"
        if filed is not None and ours is not None:
            verdict = "TIES" if abs(float(ours) - filed) < 0.51 else "DIFFERS"
        lines.append({
            "field": field, "ours": ours, "filed": filed,
            "used": "%s at %s minus the same at %s" % (expr, Q2, Q1),
            "verdict": verdict, "note": "",
            "schedule": where, "caption": what,
            "how": ("the filing reports this year-to-date, so the quarter is "
                    "one filing minus the previous one"),
            "ytd_q2": None if v2 is None else v2 / 1000.0,
            "ytd_q1": None if v1 is None else v1 / 1000.0,
        })

    # ---- close the two capital ratios, read off the filed page -------------
    for field, (caption_rx, tail, what, where) in RATIOS.items():
        ours = landed.get(field)
        got = RATIO_READS.get(cert, {}).get(field, {})
        filed, code, pno = got.get("value"), got.get("code"), got.get("page")
        verdict = "COULD NOT"
        if filed is not None and ours is not None:
            verdict = "TIES" if abs(float(ours) - filed) < 0.005 else "DIFFERS"
        elif filed is None and ours is None:
            verdict = "TIES"
        lines.append({
            "field": field, "ours": ours, "filed": filed,
            "used": code or "not found on the filing",
            "verdict": verdict, "note": "",
            "schedule": where, "caption": what, "filing_page": pno,
            "how": ("the bank files this ratio itself, as a percentage on the "
                    "facsimile -- it is not recomputed here"),
            "is_percent": True,
        })

    counted = [l for l in lines if not l["note"]]
    ties = sum(1 for l in counted if l["verdict"] == "TIES")
    print("%-26s cert %-6s %3d lines  %3d tie  %3d differ  %3d could not  "
          "(%d skipped as ratios)"
          % (name, cert, len(counted), ties,
             sum(1 for l in counted if l["verdict"].startswith("DIFFERS")),
             sum(1 for l in counted if l["verdict"] == "COULD NOT"),
             len(lines) - len(counted)))

    out.append({"cert": cert, "name": name, "slot": slot, "repdte": iso,
                "block_first_row": block.first_data_row,
                "block_last_row": block.last_data_row,
                "facsimile": facsimile_url(cert, iso),
                "facsimile_prior": facsimile_url(cert, Q1),
                "lines": lines})

(SB / "bank_rosters.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
tot = sum(len([l for l in b["lines"] if not l["note"]]) for b in out)
tied = sum(sum(1 for l in b["lines"] if not l["note"] and l["verdict"] == "TIES")
           for b in out)
print("\n%d banks, %d lines compared, %d tie" % (len(out), tot, tied))
