"""The eight dollar fields the tie-out never reached, and where they come from.

Seven of them carry the literal text "(not in tie-out map)" as their provenance:
the workbook lands a value and nothing records where it came from. My tie-out
walked straight past them, because it only checks fields the map cites -- a
check that examines what the map documents cannot discover what the map omits.

The expressions below were read off the FORM, by caption, not found by hunting
for a number that matched. Schedule RC-N line 5.c is "Other consumer loans" and
its three columns are past-due 30-89, past-due 90+, and nonaccrual; Schedule
RI-B Part I lines 1.c, 1.d, 1.e, 1.a and 5.c are the charge-off and recovery
pairs for each loan class. Then every one is checked against all twelve banks --
because a caption I read correctly for one filer is still a guess until it holds
for the rest.
"""
import json
import pathlib
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
BANKS = SB / "banks"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

Q2, Q1 = "2026-06-30", "2026-03-31"

#: Balances and past-due amounts: one filing, read directly.
LEVELS = {
    "P3CONOTH": ("RCFDK216", "RC-N 5.c col A",
                 "Other consumer loans, past due 30-89 days and still accruing"),
    "P9CONOTH": ("RCFDK217", "RC-N 5.c col B",
                 "Other consumer loans, past due 90 days or more and still accruing"),
    "NACONOTH": ("RCFDK218", "RC-N 5.c col C",
                 "Other consumer loans, nonaccrual"),
}

#: Quarterly net charge-offs: charge-offs less recoveries, year-to-date in the
#: filing, so the quarter is one filing minus the previous one.
FLOWS = {
    "NTCONOTQ": ("RIADK205-RIADK206", "RI-B I 5.c",
                 "Other consumer loans, charge-offs less recoveries"),
    "NTRERESQ": ("RIAD5411+RIADC234+RIADC235-RIAD5412-RIADC217-RIADC218",
                 "RI-B I 1.c.1 + 1.c.2.a + 1.c.2.b",
                 "1-4 family residential: revolving open-end plus closed-end "
                 "first and junior liens, charge-offs less recoveries"),
    "NTRECONQ": ("RIADC891+RIADC893-RIADC892-RIADC894", "RI-B I 1.a.1 + 1.a.2",
                 "Construction and land development, charge-offs less recoveries"),
    "NTRENREQ": ("RIADC895+RIADC897-RIADC896-RIADC898", "RI-B I 1.e.1 + 1.e.2",
                 "Nonfarm nonresidential, owner-occupied plus other, "
                 "charge-offs less recoveries"),
    "NTREMULQ": ("RIAD3588-RIAD3589", "RI-B I 1.d",
                 "Multifamily residential, charge-offs less recoveries"),
}


def evaluate(expr, facts):
    tokens, buf, sign = [], "", 1
    for ch in expr:
        if ch in "+-":
            tokens.append((sign, buf.strip()))
            sign = 1 if ch == "+" else -1
            buf = ""
        else:
            buf += ch
    tokens.append((sign, buf.strip()))
    total = 0.0
    for sgn, code in tokens:
        if not code:
            continue
        v = facts.get(code)
        if v is None:
            return None
        total += sgn * float(v)
    return total


index = json.loads((BANKS / "index.json").read_text())
rosters = {b["cert"]: b for b in json.loads((SB / "bank_rosters.json").read_text())}
landed = json.loads((SB / "bank_landed.json").read_text())

results = []
for entry in index:
    cert, name = entry["cert"], entry["name"]
    f2 = json.loads((BANKS / entry["filings"][Q2]["facts"]).read_text())
    f1 = json.loads((BANKS / entry["filings"][Q1]["facts"]).read_text())
    vals = landed[cert]
    for field, (code, where, what) in LEVELS.items():
        ours = vals.get(field)
        raw = f2.get(code)
        filed = None if raw is None else float(raw) / 1000.0
        verdict = ("COULD NOT" if (filed is None or ours is None)
                   else ("TIES" if abs(float(ours) - filed) < 0.51 else "DIFFERS"))
        results.append({"cert": cert, "name": name, "field": field,
                        "ours": ours, "filed": filed, "used": code,
                        "schedule": where, "caption": what, "verdict": verdict,
                        "how": "read straight off the filing"})
    for field, (expr, where, what) in FLOWS.items():
        ours = vals.get(field)
        v2, v1 = evaluate(expr, f2), evaluate(expr, f1)
        filed = None if (v2 is None or v1 is None) else (v2 - v1) / 1000.0
        verdict = ("COULD NOT" if (filed is None or ours is None)
                   else ("TIES" if abs(float(ours) - filed) < 0.51 else "DIFFERS"))
        results.append({"cert": cert, "name": name, "field": field,
                        "ours": ours, "filed": filed,
                        "used": "%s at %s minus the same at %s" % (expr, Q2, Q1),
                        "schedule": where, "caption": what, "verdict": verdict,
                        "how": ("the filing reports this year-to-date, so the "
                                "quarter is one filing minus the previous one"),
                        "ytd_q2": None if v2 is None else v2 / 1000.0,
                        "ytd_q1": None if v1 is None else v1 / 1000.0})

(SB / "gap_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")

from collections import Counter
print("new lines compared: %d  %s"
      % (len(results), Counter(r["verdict"] for r in results).most_common()))
print()
for field in list(LEVELS) + list(FLOWS):
    rows = [r for r in results if r["field"] == field]
    c = Counter(r["verdict"] for r in rows)
    print("%-10s %-34s %2d ties, %2d differ, %2d could not"
          % (field, rows[0]["schedule"], c.get("TIES", 0),
             c.get("DIFFERS", 0), c.get("COULD NOT", 0)))
    for r in rows:
        if r["verdict"] != "TIES":
            print("      %-24s ours=%-14s filed=%-14s"
                  % (r["name"][:24], r["ours"], r["filed"]))
