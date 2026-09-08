"""Date the code changes, and find the sums, quarter by quarter.

Three of the seven unresolved fields are quarterly figures the FDIC differences
out of a year-to-date line -- no single filing carries them, which is the same
construction every existing `*Q` field uses and is stated rather than chased.

The other four resolve in the newest quarters and not the oldest, which means
the citation is real and has a before and an after. A provenance row that names
only the current code is right today and silently wrong about six years of
history, so this finds the quarter each one changed in and what it changed from.

The search runs PER QUARTER, over singles and over two- and three-item sums, so
a field the FDIC publishes as the total of several filed lines resolves the same
way `UCCOMRES` did.
"""
import itertools
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

FIELDS = ["UCOTHER", "RSCONS"]
PREFIXES = ("RCFD", "RCON", "RIAD", "RCFA", "RCOA", "RCFW", "RCFN")

new = json.loads((SB / "deep" / "bank_new_fields.json").read_text())
names = {e["cert"]: e["name"] for e in
         json.loads((SB / "banks" / "index.json").read_text())}


def item(code):
    return code[4:] if code[:4] in PREFIXES else code


def by_item(f):
    out = {}
    for k, v in f.items():
        if isinstance(v, (int, float)) and k[:4] in PREFIXES:
            out.setdefault(item(k), []).append(float(v))
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

quarters = sorted({i for _c, i, _r, _b in rows})


def resolve(field, quarter):
    """The item or item-sum equal to the field, across all banks that quarter."""
    have = [(c, b, float(r[field]) * 1000.0) for c, i, r, b in rows
            if i == quarter and r.get(field) is not None]
    if not have:
        return None

    # singles first: cheapest, and the commonest answer
    c0, b0, want0 = have[0]
    keep = {i for i, vs in b0.items() if any(abs(v - want0) < 0.51 for v in vs)}
    for _c, b, want in have[1:]:
        keep &= {i for i in keep
                 if any(abs(v - want) < 0.51 for v in b.get(i, ()))}
        if not keep:
            break
    if keep:
        return sorted(keep)

    # then sums of two, then of three
    cand = {i: max(vs, key=abs) for i, vs in b0.items()
            if 0 < abs(max(vs, key=abs)) <= abs(want0) + 1}
    keys = sorted(cand, key=lambda i: -abs(cand[i]))[:260]
    # Four, not three. The FDIC's commercial commitment total turned out to be
    # J457 + PV11 + J459 + PV10, and a three-item search reported the modern
    # form as underivable while a three-item CITATION would have been short by
    # up to $1.4bn at the banks with foreign offices -- and exact at the four
    # without them, which is how a wrong citation survives a spot check.
    for size in (2, 3, 4):
        for combo in itertools.combinations(keys, size):
            if abs(sum(cand[i] for i in combo) - want0) >= 0.51:
                continue
            ok = True
            for _c, b, want in have[1:]:
                if any(i not in b for i in combo):
                    ok = False
                    break
                if abs(sum(max(b[i], key=abs) for i in combo) - want) >= 0.51:
                    ok = False
                    break
            if ok:
                return sorted(combo)
    return None


for field in FIELDS:
    print("=== %s" % field)
    runs, prev = [], object()
    for q in quarters:
        got = resolve(field, q)
        key = tuple(got) if got else None
        if key != prev:
            runs.append([q, q, got])
            prev = key
        else:
            runs[-1][1] = q
    for start, end, got in runs:
        label = " + ".join(got) if got else "NOT DERIVED"
        span = start if start == end else "%s .. %s" % (start, end)
        print("   %-26s %s" % (span, label))
    print()

print("A run boundary is the quarter the form changed. A row citing only the")
print("current code is right today and wrong about everything before it.")
