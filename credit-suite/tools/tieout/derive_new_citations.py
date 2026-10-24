"""Find the filed line behind each new field, rather than assuming it.

Nineteen fields are being added to the feed. Each needs a citation -- the MDRM
code on the Call Report that carries the number -- and a citation is exactly the
kind of thing that can be plausible, documented, and wrong. This session already
found one: LNLSGR cited RC-C Part I line 12 for years, and the FDIC has always
used RC 4.a + 4.b instead. The values agreed 471 times out of 480 and the
citation was still wrong.

So the codes are derived from evidence. For every candidate field, in every
cached filing, this searches the bank's own XBRL for a code whose value equals
the FDIC's -- and for pairs and triples whose SUM equals it, because the FDIC
publishes several of these as the total of two or three filed lines.

A code only survives if it matches in EVERY bank-quarter where both sides have a
value. One coincidence cannot survive 480 of them; a real citation has to.
Anything that does not survive is reported as underived rather than guessed at.
"""
import collections
import itertools
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

FIELDS = ["UCCRCD", "UCLOC", "DRRENRSQ", "CRRENRSQ", "NTRELOCQ", "RBC", "ORE",
          "INTAN", "UCCOMRES", "UCCOMREU", "UCOTHER", "LNNDEPD",
          "RSLNLTOT", "RSLNREFM", "RSCI", "RSCONS", "RSMULT", "RSOTHER",
          "NARSNRES"]

new = json.loads((SB / "deep" / "bank_new_fields.json").read_text())
index = {e["cert"]: e["name"] for e in
         json.loads((SB / "banks" / "index.json").read_text())}


#: An MDRM code is a prefix plus a four-character item. The prefix names the
#: schedule and the reporting basis; the item names the line.
PREFIXES = ("RCFD", "RCON", "RIAD", "RCFA", "RCOA", "RCFW", "RCFN")


def item(code):
    return code[4:] if code[:4] in PREFIXES else code


def by_item(f):
    """{item: [values under any prefix]} for one filing."""
    out = {}
    for k, v in f.items():
        if isinstance(v, (int, float)):
            out.setdefault(item(k), []).append(float(v))
    return out


def facts(cert, iso):
    p = SB / "filings" / ("facts-%s-%s.json" % (cert, iso))
    return json.loads(p.read_text()) if p.exists() else None


def iso_of(repdte):
    s = str(repdte)
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])


#: Every (cert, quarter) with both a filing on disk and a value from the FDIC.
pairs = []
for cert, rows in new.items():
    for row in rows:
        iso = iso_of(row["REPDTE"])
        f = facts(cert, iso)
        if f is not None:
            pairs.append((cert, iso, row, f))
print("bank-quarters with both a filing and an FDIC row: %d" % len(pairs))
print("deriving over all of them -- a coincidence does not survive %d\n"
      % len(pairs))

results = {}
for field in FIELDS:
    have = [(c, i, r, f) for c, i, r, f in pairs if r.get(field) is not None]
    if not have:
        results[field] = {"verdict": "NO FDIC VALUE", "n": 0}
        continue

    # ---- singles: one ITEM equal to the field, in every quarter -----------
    # Matched on the four-character MDRM item, not the whole code. The prefix
    # says which schedule a bank reports on -- RCFD consolidated for an 031
    # filer, RCON domestic for an 041 one -- so requiring the same string
    # everywhere requires twelve banks to file the same form. They do not, and
    # the provenance map has always written this as "RCON2170 (RCFD2170 031)".
    cert0, iso0, row0, f0 = have[0]
    want0 = float(row0[field]) * 1000.0
    singles = {item(k) for k, v in f0.items() if isinstance(v, (int, float))
               and abs(float(v) - want0) < 0.51}
    for cert, iso, row, f in have[1:]:
        want = float(row[field]) * 1000.0
        by = by_item(f)
        singles &= {i for i in singles
                    if any(abs(v - want) < 0.51 for v in by.get(i, ()))}
        if not singles:
            break

    if singles:
        results[field] = {"verdict": "SINGLE", "codes": sorted(singles),
                          "n": len(have)}
        continue

    # ---- sums: two or three codes adding to the field ---------------------
    # Restricted to codes near the right order of magnitude, or the search is
    # quadratic over two thousand codes for no gain.
    def candidates(f, want):
        """Items in the right order of magnitude, one entry per item."""
        seen = {}
        for k, v in f.items():
            if not isinstance(v, (int, float)) or k[:4] not in PREFIXES:
                continue
            if not (0 < abs(float(v)) <= abs(want) + 1):
                continue
            seen.setdefault(item(k), float(v))
        return seen

    combo = None
    for size in (2, 3):
        cands = candidates(f0, want0)
        keys = sorted(cands, key=lambda i: -abs(cands[i]))[:420]
        found = None
        for combo_try in itertools.combinations(keys, size):
            if abs(sum(cands[i] for i in combo_try) - want0) >= 0.51:
                continue
            # must hold in every other bank-quarter, on the item rather than
            # the code -- and a bank may report an item under either prefix.
            ok = True
            for cert, iso, row, f in have[1:]:
                want = float(row[field]) * 1000.0
                by = by_item(f)
                if any(i not in by for i in combo_try):
                    ok = False
                    break
                # one value per item; where a filing carries both prefixes
                # they agree, and where they do not the wider one is filed
                got = sum(max(by[i], key=abs) for i in combo_try)
                if abs(got - want) >= 0.51:
                    ok = False
                    break
            if ok:
                found = combo_try
                break
        if found:
            combo = found
            break

    if combo:
        results[field] = {"verdict": "SUM", "codes": sorted(combo), "n": len(have)}
    else:
        results[field] = {"verdict": "NOT DERIVED", "n": len(have)}

for field in FIELDS:
    r = results[field]
    codes = " + ".join(r.get("codes", [])) or "--"
    print("  %-10s %-12s %-52s over %d bank-quarters"
          % (field, r["verdict"], codes[:52], r["n"]))

(SB / "new_field_citations.json").write_text(json.dumps(results, indent=1),
                                             encoding="utf-8")
counts = collections.Counter(r["verdict"] for r in results.values())
print("\n%s" % dict(counts))
print("\nA NOT DERIVED field is one whose filed line this could not establish.")
print("It gets no citation rather than a plausible one.")
