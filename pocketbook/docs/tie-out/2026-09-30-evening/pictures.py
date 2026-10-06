"""Make this tie-out's pictures (the 29 Sep tie-out's pictures.py, pointed at the evening's changes).

    python3 pictures.py OUT        # OUT: where run-it-all.sh left the in-between files

Each command is RUN here, and its real output drawn as a terminal window with the command above it -- nothing typed
in by hand. The figure is then ringed in red, found by searching the output for its text, so a ring cannot land on
a number that is not there.
"""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve()
MONO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
MONO_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 15)
SANS_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
RED = (220, 20, 20)
CW, LH = 9, 21


def run(cmd):
    env = {**os.environ, "OUT": str(OUT)}
    return subprocess.run(["bash", "-c", cmd], cwd=HERE, capture_output=True, text=True, check=True, env=env).stdout


def terminal(name, title, steps, rings):
    lines = []
    for cmd, out in steps:
        full = "$ " + cmd
        while len(full) > 118:
            lines.append((full[:118], "cmd"))
            full = "  " + full[118:]
        lines.append((full, "cmd"))
        lines += [(x, "out") for x in out.rstrip("\n").split("\n")]
        lines.append(("", "out"))
    width = max(len(t) for t, _ in lines) * CW + 40
    top = 44
    img = Image.new("RGB", (width, top + len(lines) * LH + 16), (250, 250, 247))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 34], fill=(40, 42, 46))
    d.text((14, 8), title, font=SANS_B, fill=(255, 255, 255))
    for i, (t, kind) in enumerate(lines):
        y = top + i * LH
        if kind == "cmd":
            d.rectangle([0, y - 2, width, y + LH - 3], fill=(234, 236, 240))
        d.text((20, y), t, font=MONO_B if kind == "cmd" else MONO, fill=(20, 20, 20))
    for text, nth in rings:
        hits = [(i, j) for i, (t, kind) in enumerate(lines) if kind == "out"
                for j in range(len(t)) if t.startswith(text, j)]
        for i, at in hits[nth - 1:nth]:
            x0, y0 = 20 + at * CW - 6, top + i * LH - 4
            x1, y1 = 20 + (at + len(text)) * CW + 6, top + (i + 1) * LH - 2
            d.rounded_rectangle([x0, y0, x1, y1], radius=8, outline=RED, width=4)
            break
        else:
            raise SystemExit(f"{name}: {text!r} (occurrence {nth}) is not in the output, so it cannot be ringed")
    img.save(HERE / name)
    print("wrote", name)


def main():
    c1 = ("awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} $h[\"CHANNEL\"]==\"Kiosk\"{n++; print \"Kiosk loan:\", "
          "$h[\"LOAN_NBR\"], \"FICO\", $h[\"FICO\"], \"ORIG_BAL\", $h[\"ORIG_BAL\"]} END{print \"Kiosk loans:\", n}' "
          "\"Grey book.csv\"")
    c1b = ("grep -E 'ORIG_BAL x CHANNEL · Earned before losses( · book · All · Kiosk)?,' OUT/roster-grey.csv "
           "| cut -d, -f2,5-9")
    terminal("source-1-grey.png",
             "Change 1  ·  Grey book  ·  the 3-loan Kiosk pocket: grey, and left out of the heat's bound",
             [(c1, run(c1)), (c1b.replace("OUT/", "work44/"), run(c1b.replace("OUT/", "$OUT/")))],
             [("Kiosk loans: 3", 1), ("-11.514423453", 1), ("True,True", 1), ("2.888908416,2.88890841606", 1)])
    c2 = ("awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} {f=$h[\"FICO\"]; b=$h[\"BAD_FLAG\"]} b==\"0\"||b==\"1\""
          "{N++; B+=b} f!=\"\"&&f!=-9999&&f>=496&&f<654&&$h[\"CHANNEL\"]==\"Branch\"&&$h[\"SYS_FLAG\"]==\"Y\"&&"
          "(b==\"0\"||b==\"1\"){n++; k+=b} END{printf \"whole book: %d loans, %d bad, %.4f%%\\n496 - 653 / Branch, "
          "SYS_FLAG Y only: %d loans, %d bad, %.4f%%, x the whole book %.6f\\n\", N, B, 100*B/N, n, k, 100*k/n, "
          "(k/n)/(B/N)}' \"Flag book.csv\"")
    c2b = ("grep -E 'FICO x CHANNEL \\| where Y · Bad loans( · (rate|book) · 496 - 653 · Branch)?,' OUT/roster-flag.csv"
           " | cut -d, -f2,5-9")
    terminal("source-2-filter.png",
             "Changes 2 and 3  ·  Flag book  ·  Only loans where SYS_FLAG is Y: vs the book is still the whole book's",
             [(c2, run(c2)), (c2b.replace("OUT/", "work44/"), run(c2b.replace("OUT/", "$OUT/")))],
             [("7.7385%", 1), ("x the whole book 1.566358", 1), ("(book: 7.74%)", 1), ("1.56635825133", 1)])
    c3 = ("awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i; next} {f=$h[\"FICO\"]; o=$h[\"ORIG_BAL\"]} o!=\"\"{N++; S+=o} "
          "f!=\"\"&&f!=-9999&&f>=496&&f<654&&$h[\"CHANNEL\"]==\"Branch\"{r++; if(o!=\"\"){n++; s+=o; print o > "
          "\"/dev/stderr\"}} END{printf \"whole book: %d loans with a booked amount, average %.4f\\n496 - 653 / "
          "Branch: %d loans, %d with a booked amount, average %.4f, x the book %.6f\\n\", N, S/N, r, n, s/n, "
          "(s/n)/(S/N)}' \"../2026-09-28/Consumer book Q3.csv\" 2>$OUT/sizes.txt; sort -n $OUT/sizes.txt "
          "| awk '{v[NR]=$1} END{print \"median:\", (NR%2 ? v[(NR+1)/2] : (v[NR/2]+v[NR/2+1])/2)}'")
    c3b = ("grep -E 'FICO x CHANNEL · (Loan size( · (rate|book) · 496 - 653 · Branch)?|496 - 653 · Branch),' "
           "OUT/roster-q3.csv | grep -E 'grid-head|Loan size · rate|Loan size · book|size-median' | cut -d, -f2,5-9")
    terminal("source-3-size.png",
             "Change 4  ·  Consumer book Q3  ·  Loan size in FICO 496 - 653 / Branch",
             [(c3.replace("$OUT", "work44"), run(c3)), (c3b.replace("OUT/", "work44/"), run(c3b.replace("OUT/", "$OUT/")))],
             [("average 32549.2167", 1), ("median: 31733", 1), ("$32,263", 1), ("32549.2167131", 1)])
    c4 = ("python3 -c \"import csv, numpy as np; v = [float(r['FICO']) for r in csv.DictReader(open('Bureau book.csv')) "
          "if r['FICO'] not in ('', '-9999')]; print(len(v), 'loans', np.percentile(v, [10, 25, 50, 75, 90]))\"")
    c4b = "grep -E 'bureau,look,.*FICO · [0-9]+th percentile' OUT/roster-bureau.csv | cut -d, -f4-9"
    terminal("source-4-look.png",
             "Change 5  ·  Bureau book  ·  FICO's P10 to P90, the answered-missing -9999 left out",
             [(c4, run(c4)), (c4b.replace("OUT/", "work44/"), run(c4b.replace("OUT/", "$OUT/")))],
             [("[629. 663. 699. 736. 772.]", 1), ("the median · 3\",699,699", 1), ("P90) · 3,772,772,0,TIED", 1)])
    c5 = "python3 explain_border.py OUT q3 | head -3 | cut -c1-200"
    terminal("source-5-border.png",
             "Change 6  ·  Consumer book Q3  ·  borderline, pocket by pocket, on every pocket of _pockets",
             [(c5.replace("OUT", "work44"), run(c5.replace("OUT", "$OUT")))],
             [("1195 of 1195 TIED", 1), ("TIED-WITHIN-SAMPLING", 1)])
    c6 = ("python3 -c \"import csv; [print(r['tab'], r['column'], r['verdict'], '|', r['worst'][:118]) for r in "
          "csv.DictReader(open('OUT/widths-q3.csv')) if (r['tab'], r['column']) in {('Split', 'J'), "
          "('Start here', 'C'), ('Look', 'B'), ('Pockets', 'K'), ('Paid, cost, kept', 'K')}]\"")
    terminal("source-6-widths.png",
             "Change 7  ·  Consumer book Q3  ·  three columns a value doesn't fit",
             [(c6.replace("OUT/", "work44/"), run(c6.replace("OUT/", "$OUT/")))],
             [("borderline (p 0.054)", 1), ("ASSET_CLASS 4 · borderline (p 0.036)", 1),
              ("50th percentile (P50), the median", 1)])
    c7 = ("awk -F, 'NR>1 && $2!=\"\" && $2!=-9999 {n++; if ($2<=653) lo++; if ($2==653) at++; if ($2<=652) old++} "
          "END {printf \"FICO read: %d loans; 653 or under: %d, of them at 653: %d; 652 or under: %d\\n\", n, lo, at, "
          "old}' \"Year book.csv\"")
    c7b = "grep -E '^year,band-label,.*FICO · (496|654)' OUT/roster-year.csv | cut -d, -f5-9"
    terminal("source-7-label.png",
             "Change 9  ·  Year book  ·  FICO's lowest edge is 653.4: the band holds 653, and says so",
             [(c7, run(c7)), (c7b.replace("OUT/", "work44/"), run(c7b.replace("OUT/", "$OUT/")))],
             [("653 or under: 1556", 1), ("at 653: 40", 1), ("FICO · 496 - 653,1556,1556", 1)])
    c8 = ("awk -F, 'NR>1 {y = ($10==\"\") ? \"(no date)\" : substr($10,1,4); n[y]++} END {for (k in n) print k, n[k]}' "
          "\"Year book.csv\" | sort")
    c8b = ("python3 -c \"import csv; [print(r['ours'][:104], '|', r['source'], '|', r['verdict']) for r in "
           "csv.DictReader(open('OUT/roster-year.csv')) if 'Grids filter' in r['figure']]\"")
    terminal("source-8-year.png",
             "Change 3  ·  Year book  ·  Filter by ORIG_YEAR: the year in ORIG_DATE, and (no date)",
             [(c8, run(c8)), (c8b.replace("OUT/", "work44/"), run(c8b.replace("OUT/", "$OUT/")))],
             [("(no date) 53", 1), ("2022 2687", 1), ("2022; 2687; 2023; 2641; 2024; 2619; 53", 1), ("TIED", 1)])


if __name__ == "__main__":
    main()
