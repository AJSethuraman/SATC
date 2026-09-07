"""Why seven fields have no single citation across ten years.

The all-480 derivation found twelve of nineteen. A field fails that test for
three quite different reasons, and calling all three "not derived" would hide
the interesting one:

  * it is a QUARTERLY figure the FDIC differences out of a year-to-date filed
    line, so no single filing carries it -- true of every `*Q` field already in
    the feed, and stated rather than treated as a gap;
  * the FORM CHANGED inside the ten years, so the citation is real but has a
    before and an after -- the scan already found one of these, where RC-L
    1.e.(2) moved from `J458` to `PV11` and an old crosswalk would silently
    lose fifteen billion dollars;
  * nothing found it, which is the only one that is actually a gap.

So this derives over the newest eight quarters and the oldest eight separately.
A field that resolves in both to the SAME item was a checker problem. One that
resolves to DIFFERENT items dates the recoding. One that resolves in neither is
the real unknown.
"""
import json
import pathlib
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

UNRESOLVED = ["DRRENRSQ", "CRRENRSQ", "NTRELOCQ", "INTAN", "UCOTHER",
              "RSLNLTOT", "RSCONS"]
PREFIXES = ("RCFD", "RCON", "RIAD", "RCFA", "RCOA", "RCFW", "RCFN")

new = json.loads((SB / "deep" / "bank_new_fields.json").read_text())


def item(code):
    return code[4:] if code[:4] in PREFIXES else code


def by_item(f):
    out = {}
    for k, v in f.items():
        if isinstance(v, (int, float)):
            out.setdefault(item(k), []).append(float(v))
    return out


def iso_of(r):
    s = str(r["REPDTE"])
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])


pairs = []
for cert, rows in new.items():
    for row in rows:
        iso = iso_of(row)
        p = SB / "filings" / ("facts-%s-%s.json" % (cert, iso))
        if p.exists():
            pairs.append((cert, iso, row, json.loads(p.read_text())))

quarters = sorted({i for _c, i, _r, _f in pairs})
NEW_ERA = set(quarters[-8:])
OLD_ERA = set(quarters[:8])
print("newest era : %s .. %s" % (quarters[-8], quarters[-1]))
print("oldest era : %s .. %s" % (quarters[0], quarters[7]))
print()


def singles_over(field, era):
    have = [(c, i, r, f) for c, i, r, f in pairs
            if i in era and r.get(field) is not None]
    if not have:
        return None, 0
    _c, _i, row0, f0 = have[0]
    want0 = float(row0[field]) * 1000.0
    keep = {item(k) for k, v in f0.items() if isinstance(v, (int, float))
            and abs(float(v) - want0) < 0.51}
    for _c, _i, row, f in have[1:]:
        want = float(row[field]) * 1000.0
        by = by_item(f)
        keep &= {i for i in keep
                 if any(abs(v - want) < 0.51 for v in by.get(i, ()))}
        if not keep:
            break
    return sorted(keep), len(have)


out = {}
for field in UNRESOLVED:
    new_codes, n_new = singles_over(field, NEW_ERA)
    old_codes, n_old = singles_over(field, OLD_ERA)
    if new_codes and old_codes and set(new_codes) & set(old_codes):
        verdict = "SAME BOTH ERAS"
    elif new_codes and old_codes:
        verdict = "CODE CHANGED"
    elif new_codes or old_codes:
        verdict = "ONE ERA ONLY"
    else:
        verdict = "NEITHER ERA"
    out[field] = {"verdict": verdict, "new": new_codes, "old": old_codes}
    print("  %-10s %-16s newest %-22s oldest %-22s"
          % (field, verdict,
             ", ".join(new_codes or []) or "--",
             ", ".join(old_codes or []) or "--"))

(SB / "era_citations.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print()
print("NEITHER ERA on a quarterly field is expected -- the FDIC differences it")
print("out of a year-to-date line, so no single filing carries the number.")
