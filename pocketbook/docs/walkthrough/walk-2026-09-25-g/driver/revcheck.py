"""Losses vs revenue, read back row by row (seventh walk, commit a5a8aa2).

    python3.12 revcheck.py PLANTED_BAND BOOK.xlsx...     (PLANTED_BAND: "under 654", "under 620", "600 to under 620")

For each workbook: the subtitle's revenue words; per grid, the count line against the rows under it; and
these checks, each of which should print 0:
  - a luck-marked box that is shaded, or counted in "Pockets per box"
  - a plain box off "About the same" / "Not tested" that is NOT shaded (the three greens and reds and ambers)
  - a RANR reading that disagrees with the box's revenue side
  - a Which box cell whose text sits top-aligned while the row's numbers sit at the bottom (only matters when
    the row grows to two lines; counted, not judged)
and the planted pocket's row in every grid it appears in."""
import re, sys, collections
from openpyxl import load_workbook

BOXES = ("Losing more, earning less", "Losing more, earning the same", "Losing the same, earning less",
         "Losing more, earning more", "Losing less, earning less", "About the same on both",
         "Losing the same, earning more", "Losing less, earning the same", "Losing less, earning more")
band = sys.argv[1]
for p in sys.argv[2:]:
    ws = load_workbook(p)["Losses vs revenue"]
    sub = ws["B2"].value
    rv = re.search(r"(Revenue counts as [^.]*\.)", sub)
    print(f"== {p.split('/')[-2]}/{p.split('/')[-1][:12]}  {rv.group(1) if rv else sub[:200]}")
    grid, cnt, rows = None, None, collections.defaultdict(list)
    for r in ws.iter_rows(min_row=4):
        v = [c.value for c in r]
        if v[1] and v[2] is None and v[3] is None and " x " in str(v[1]):
            grid = v[1]; continue
        if v[1] and str(v[1]).startswith("Pockets per box"):
            cnt = v[1]; rows[grid].append(("COUNT", cnt)); continue
        if not isinstance(v[3], (int, float)) or not v[8]:
            continue
        fill = r[1].fill.fgColor.rgb if r[1].fill and r[1].fill.fill_type == "solid" else None
        rows[grid].append((v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8], fill,
                           r[8].alignment.vertical, r[1].alignment.vertical))
    bad = collections.Counter()
    for g, rs in rows.items():
        count_line = [x[1] for x in rs if x[0] == "COUNT"][0]
        data = [x for x in rs if x[0] != "COUNT"]
        body = count_line.split("Pockets per box: ", 1)[1]
        parts = [q for chunk in body.split(". ") for q in chunk.split("; ")]
        said = {q.rsplit(": ", 1)[0].strip(): int(q.rsplit(": ", 1)[1]) for q in parts if ": " in q}
        luck = sum(1 for x in data if x[7].endswith("could be luck)"))
        plain = collections.Counter(x[7] for x in data if not x[7].endswith("could be luck)"))
        for k, n in plain.items():
            if said.get(k) != n:
                bad[f"count line says {k}: {said.get(k)}, rows {n}"] += 1
        if luck and said.get("Marked could be luck, not counted above") != luck:
            bad["count of luck-marked disagrees"] += 1
        for x in data:
            box, fill, reading = x[7], x[8], x[6]
            if box.endswith("could be luck)") and fill:
                bad["luck-marked but shaded"] += 1
            if box in BOXES and box != "About the same on both" and not fill:
                bad["plain box off 'the same' but unshaded"] += 1
            base = box.split(" (")[0]
            rside = base.split(", ")[1] if ", " in base else "earning the same"
            if box.startswith("Not tested"):
                continue
            want = {"earning more": "earning more", "earning less": "earning less", "earning the same": "about the same",
                    "the same on both": "about the same"}.get(rside, rside)
            if not str(reading).startswith(want):
                bad[f"RANR reading '{reading}' vs box '{box}'"] += 1
            if x[9] == "top" and x[10] != "top" and box.endswith("could be luck)"):
                bad["box text top-aligned, row bottom-aligned (luck-marked rows)"] += 1
        pl = [x for x in data if x[0] == band and x[1] == "Broker"]
        if pl:
            x = pl[0]
            print(f"   {g}: planted {band} / Broker {x[2]} loans, GCO {x[3]:.2f}x {x[4]}, RANR {x[5]:.2f}x '{x[6]}' -> "
                  f"{x[7]!r} shaded {x[8]}")
        print(f"   {g}: {count_line}")
    for k, n in bad.items():
        print(f"   CHECK {n:3}  {k}")
