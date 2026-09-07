"""Check all 9,120 new bank values against the line each one cites.

Same standard as the ten-year run: the FDIC's published number on one side, the
bank's own filed Call Report on the other, and a verdict per value. Nothing is
adjusted and nothing is computed into the feed -- the arithmetic here happens on
the SOURCE side, adding or differencing the filed lines to see what the FDIC
did.

Three kinds of field, and they are labelled differently because they are
different claims:

  * a filed line, compared straight;
  * a line whose code CHANGED inside the window, compared against whichever
    citation was in force that quarter;
  * a quarterly flow, which no single filing carries -- the year-to-date less
    the previous quarter's, and NOT COMPARABLE where the quarter spans a merger,
    because across one the difference of two year-to-date totals mixes two banks.
"""
import collections
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import feed_fields as FF          # noqa: E402

PREFIXES = ("RCFD", "RCON", "RIAD", "RCFA", "RCOA", "RCFW", "RCFN")
new = json.loads((SB / "deep" / "bank_new_fields.json").read_text())
names = {e["cert"]: e["name"] for e in
         json.loads((SB / "banks" / "index.json").read_text())}
mergers = json.loads((SB / "merger_records_deep.json").read_text())
MERGER_Q = {(m["survivor"], m["quarter"]) for m in mergers}


def by_item(f):
    out = {}
    for k, v in f.items():
        if isinstance(v, (int, float)) and k[:4] in PREFIXES:
            out.setdefault(k[4:], []).append(float(v))
    return out


def facts(cert, iso):
    """(by-item view, raw code view) for one filing, or (None, None)."""
    p = SB / "filings" / ("facts-%s-%s.json" % (cert, iso))
    if not p.exists():
        return None, None
    raw = json.loads(p.read_text())
    return by_item(raw), raw


def iso_of(r):
    s = str(r["REPDTE"])
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])


def prev_quarter(iso):
    y, m = int(iso[:4]), int(iso[5:7])
    py, pm = {3: (y - 1, 12), 6: (y, 3), 9: (y, 6), 12: (y, 9)}[m]
    return "%04d-%02d-%02d" % (py, pm, {3: 31, 6: 30, 9: 30, 12: 31}[pm])


def evaluate(expr, b, raw=None):
    """Sum an expression over one filing, or None if a line is absent.

    An item written bare (`3815`) matches under whichever prefix the bank
    filed it. An item written WITH its prefix (`RCONJ454`) means that line
    and no other.
    """
    raw = raw if raw is not None else {}
    total, sign, buf, terms = 0.0, 1, "", []
    for ch in expr:
        if ch in "+-":
            terms.append((sign, buf.strip()))
            sign = 1 if ch == "+" else -1
            buf = ""
        else:
            buf += ch
    terms.append((sign, buf.strip()))
    for sgn, code in terms:
        if not code:
            continue
        if code[:4] in PREFIXES:
            # A citation that names its prefix means that prefix and no other.
            # `LNNDEPD` is the domestic line; the consolidated one is larger at
            # every bank with foreign offices, and taking "whichever is bigger"
            # reported 55 of 480 as differences.
            vals = raw.get(code)
            if vals is None:
                return None
            total += sgn * float(vals)
            continue
        vals = b.get(code)
        if not vals:
            return None
        total += sgn * max(vals, key=abs)
    return total


rows = []
for cert, rs in sorted(new.items(), key=lambda kv: names[kv[0]]):
    for r in rs:
        iso = iso_of(r)
        b, raw = facts(cert, iso)
        for field in FF.FEED_FIELDS:
            ours = r.get(field)
            if ours is None:
                continue
            expr = FF.citation_for(field, iso)
            rec = {"cert": cert, "bank": names[cert], "repdte": iso,
                   "field": field, "ours": ours, "cited": expr,
                   "schedule": next(x[1] for x in FF.FEED_ROWS if x[0] == field)}
            if b is None:
                rec.update(theirs=None, verdict="NO FILING FETCHED", how="")
                rows.append(rec)
                continue

            if field in FF.FEED_FLOW_FIELDS:
                base = expr.split(" (")[0]
                if (cert, iso) in MERGER_Q:
                    rec.update(theirs=None,
                               verdict="NOT COMPARABLE (SPANS A MERGER)",
                               how="this quarter spans a merger, so the "
                                   "difference of two year-to-date totals "
                                   "mixes two banks")
                    rows.append(rec)
                    continue
                cur = evaluate(base, b, raw)
                if iso[5:7] == "03":
                    theirs = None if cur is None else cur / 1000.0
                    rec["how"] = "first quarter: the year-to-date IS the quarter"
                else:
                    pb, praw = facts(cert, prev_quarter(iso))
                    pri = evaluate(base, pb, praw) if pb else None
                    theirs = (None if cur is None or pri is None
                              else (cur - pri) / 1000.0)
                    rec["how"] = ("this filing's year-to-date less the previous "
                                  "quarter's")
                rec["cited"] = base
            elif field in FF.TWO_COLUMN_FIELDS:
                # An advanced-approaches bank files this under two frameworks.
                # The column is chosen from the RATIOS -- the lower one binds --
                # BEFORE the amount is looked at, so this comparison can fail.
                # Choosing by which amount matched would tie by construction.
                col = FF.binding_column(field, raw)
                n_filed = sum(1 for amt, rat in FF.TWO_COLUMN_FIELDS[field]
                              if raw.get(amt) is not None
                              and raw.get(rat) is not None)
                theirs = float(raw[col]) / 1000.0 if col else None
                rec["cited"] = col or expr
                rec["how"] = ("filed under %d framework(s); this is the one "
                              "that binds, chosen on its capital ratio"
                              % n_filed) if col else "no framework filed"
            else:
                got = evaluate(expr.split(" (")[0], b, raw)
                theirs = None if got is None else got / 1000.0
                rec["how"] = ("read straight off the filing"
                              if "+" not in expr and "-" not in expr
                              else "the filed lines the FDIC adds, summed")
                rec["cited"] = expr.split(" (")[0]


            if theirs is None:
                rec.update(theirs=None, verdict="NOT ON THIS FILING")
            else:
                rec.update(theirs=theirs,
                           verdict=("TIES" if abs(float(ours) - theirs) < 0.51
                                    else "DIFFERS"))
            rows.append(rec)
    print("  %-26s done" % names[cert][:26], flush=True)

(SB / "bank_new_rows.json").write_text(json.dumps(rows), encoding="utf-8")
c = collections.Counter(r["verdict"] for r in rows)
print("\nnew bank values examined : %d" % len(rows))
for k, v in c.most_common():
    print("   %-34s %5d" % (k, v))

diffs = [r for r in rows if r["verdict"] == "DIFFERS"]
if diffs:
    print("\nDIFFERS by field:")
    for f, n in collections.Counter(r["field"] for r in diffs).most_common():
        print("   %-10s %4d" % (f, n))
    print("\n  first five:")
    for r in diffs[:5]:
        print("   %-22s %s %-10s ours %14s  filed %14s"
              % (r["bank"][:22], r["repdte"], r["field"], r["ours"], r["theirs"]))
else:
    print("\nno differences")

absent = [r for r in rows if r["verdict"] == "NOT ON THIS FILING"]
if absent:
    print("\nNOT ON THIS FILING by field:")
    for f, n in collections.Counter(r["field"] for r in absent).most_common():
        qs = sorted({r["repdte"] for r in absent if r["field"] == f})
        print("   %-10s %4d  %s .. %s" % (f, n, qs[0], qs[-1]))
