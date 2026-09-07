"""The last two citations, found by subtraction rather than by brute force.

A four-item search over 260 candidate lines is 183 million combinations per
quarter, which is not a search, it is a hang. The cheap version: take the known
components, subtract them from the FDIC's figure, and ask which single line
equals what is left. That found `PV10` in seconds after the combinatorial
version had run for ten minutes and produced nothing.

The same trick closes the older era of `UCOTHER` and the whole history of
`RSCONS`: seed with what is already established, subtract, and name the
remainder. If the remainder matches no line in every bank-quarter, it stays
underived -- the point is to stop guessing, not to always win.
"""
import json
import pathlib
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

PREFIXES = ("RCFD", "RCON", "RIAD", "RCFA", "RCOA", "RCFW", "RCFN")
new = json.loads((SB / "deep" / "bank_new_fields.json").read_text())
names = {e["cert"]: e["name"] for e in
         json.loads((SB / "banks" / "index.json").read_text())}


def by_item(f):
    out = {}
    for k, v in f.items():
        if isinstance(v, (int, float)) and k[:4] in PREFIXES:
            out.setdefault(k[4:], []).append(float(v))
    return out


def iso_of(r):
    s = str(r["REPDTE"])
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])


rows = []
for cert, rs in new.items():
    for r in rs:
        iso = iso_of(r)
        p = SB / "filings" / ("facts-%s-%s.json" % (cert, iso))
        if p.exists():
            rows.append((cert, iso, r, by_item(json.loads(p.read_text()))))
rows.sort(key=lambda t: t[1])


def remainder_item(field, seed, lo, hi):
    """The single line equal to (field - sum(seed)) in every bank-quarter."""
    keep, n, skipped = None, 0, 0
    for cert, iso, r, b in rows:
        if not (lo <= iso <= hi) or r.get(field) is None:
            continue
        if any(c not in b for c in seed):
            skipped += 1
            continue
        want = float(r[field]) * 1000.0
        short = want - sum(max(b[c], key=abs) for c in seed)
        n += 1
        if abs(short) < 0.51:
            continue                      # seed alone is exact here
        here = {k for k, vs in b.items()
                if any(abs(v - short) < 0.51 for v in vs)}
        keep = here if keep is None else (keep & here)
        if not keep:
            return None, n, skipped
    return (sorted(keep) if keep else []), n, skipped


def check(field, codes, lo, hi):
    ok = bad = miss = 0
    for cert, iso, r, b in rows:
        if not (lo <= iso <= hi) or r.get(field) is None:
            continue
        if any(c not in b for c in codes):
            miss += 1
            continue
        want = float(r[field]) * 1000.0
        got = sum(max(b[c], key=abs) for c in codes)
        ok += abs(got - want) < 0.51
        bad += abs(got - want) >= 0.51
    return ok, bad, miss


print("UCOTHER, the era before the recoding")
rem, n, skipped = remainder_item("UCOTHER", ("J457", "J458", "J459"),
                                 "2016-01-01", "2024-09-30")
print("   seed J457+J458+J459 over %d bank-quarters (%d lacked a component)"
      % (n, skipped))
print("   remainder line:", rem or "none -- the seed is already exact")
codes = ["J457", "J458", "J459"] + (rem[:1] if rem else [])
ok, bad, miss = check("UCOTHER", codes, "2016-01-01", "2024-09-30")
print("   %s  ->  holds %d, fails %d, component missing %d"
      % (" + ".join(codes), ok, bad, miss))

print("\nUCOTHER, the modern era")
ok, bad, miss = check("UCOTHER", ["J457", "PV11", "J459", "PV10"],
                      "2024-12-01", "2026-12-31")
print("   J457 + PV11 + J459 + PV10  ->  holds %d, fails %d, missing %d"
      % (ok, bad, miss))

print("\nRSCONS, seeded on K159 (the line the per-quarter search kept naming)")
for lo, hi, label in (("2016-01-01", "2022-12-31", "before the 2023 change"),
                      ("2023-01-01", "2026-12-31", "after it")):
    rem, n, skipped = remainder_item("RSCONS", ("K159",), lo, hi)
    print("   %-24s remainder %-14s over %d bank-quarters"
          % (label, ", ".join(rem or []) or "none", n))
    codes = ["K159"] + (rem[:1] if rem else [])
    ok, bad, miss = check("RSCONS", codes, lo, hi)
    print("      %-22s holds %d, fails %d, missing %d"
          % (" + ".join(codes), ok, bad, miss))
