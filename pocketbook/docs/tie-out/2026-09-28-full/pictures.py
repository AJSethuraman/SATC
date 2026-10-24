"""Make the tie-out's pictures (the first tie-out's pictures.py, pointed at this one's figures).

    python3 pictures.py OUT        # OUT: where run-it-all.sh left the expected figures

Source pictures (the loan file's side): each command is RUN here, on the extracts, and its real output drawn as a
terminal window with the command above it -- nothing typed in by hand. The figure is then ringed in red, found by
searching the output for its text, so a ring cannot land on a number that is not there.

Workbook pictures (PocketBook's side): LibreOffice Calc screenshots of the workbooks as the analyst opens them
(raw/, from workbook_shots.py under a virtual display, recalculated on load), cut to the rows that matter, ringed,
and given an identity band naming the file, the tab and the cell.
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
SANS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
RED = (220, 20, 20)
CW, LH = 9, 21


def run(cmd, shown=None):
    env = {**os.environ, "OUT": str(OUT)}
    return subprocess.run(["bash", "-c", cmd], cwd=HERE, capture_output=True, text=True, check=True, env=env).stdout


def terminal(name, title, steps, rings):
    lines = []
    for cmd, out in steps:
        full = "$ " + cmd
        while len(full) > 112:
            lines.append((full[:112], "cmd"))
            full = "  " + full[112:]
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
        seen = 0
        for i, (t, kind) in enumerate(lines):
            at = t.find(text)
            if at < 0 or kind != "out":
                continue
            seen += 1
            if seen != nth:
                continue
            x0, y0 = 20 + at * CW - 6, top + i * LH - 4
            x1, y1 = 20 + (at + len(text)) * CW + 6, top + (i + 1) * LH - 2
            d.rounded_rectangle([x0, y0, x1, y1], radius=8, outline=RED, width=4)
            break
        else:
            raise SystemExit(f"{name}: {text!r} (occurrence {nth}) is not in the output, so it cannot be ringed")
    img.save(HERE / name)
    print("wrote", name)


def workbook(name, raw, crop, rings, band):
    shot = Image.open(HERE / "raw" / raw).convert("RGB")
    d = ImageDraw.Draw(shot)
    for box in rings:
        d.rounded_rectangle(box, radius=6, outline=RED, width=5)
    crops = crop if isinstance(crop[0], tuple) else [crop]
    parts = [shot.crop(c) for c in crops]
    cut = Image.new("RGB", (max(x.width for x in parts), sum(x.height for x in parts) + 6 * (len(parts) - 1)),
                    (160, 160, 160))
    y = 0
    for x in parts:
        cut.paste(x, (0, y))
        y += x.height + 6
    out = Image.new("RGB", (cut.width, cut.height + 40), (255, 255, 255))
    dd = ImageDraw.Draw(out)
    dd.rectangle([0, 0, cut.width, 40], fill=(40, 42, 46))
    dd.text((12, 10), band, font=SANS, fill=(255, 255, 255))
    out.paste(cut, (0, 40))
    out.save(HERE / name)
    print("wrote", name)


def main():
    q3, sb = "../2026-09-28/Consumer book Q3.csv", "Scouting book.csv"
    # 1 · one pocket of the bleed run, worked out from the loan file; its shuffled p sits just over 5%
    c1 = 'python3 explain.py "$OUT/expected-bleed.json" "Two-way" "Kept after losses" "FICO 496 - 653" "4"'
    c2 = (f"awk -F, 'NR>1 && $2!=\"\" && $2!=-9999 && $2<654 && $4!=\"\" {{s=($8==4)?\"class 4\":\"rest of band\"; "
          f"q[s]+=$7; b[s]+=$4}} END{{for(s in q) printf \"%-13s RANR_AMT %13.2f  ORIG_BAL %14.2f  kept %.6f\\n\", "
          f"s, q[s], b[s], q[s]/b[s]}}' \"{q3}\" | sort")
    terminal("source-1-kept-pocket.png",
             "The loan file, by hand  ·  Consumer book Q3.csv  ·  FICO under 654, ASSET_CLASS 4, Kept after losses",
             [(c2, run(c2)), (c1.replace('"$OUT/', '"OUT/'), run(c1))],
             [("0.152786", 1), ("0.202114", 1), ("0.050395", 1), ("No", 1), ("606041.420522", 1)])

    # 2 · the second run kind: conditional logistic regression and the tests, from the file
    c3 = 'python3 by_hand_scout.py "Scouting book.csv" "$OUT/expected-scout.json" "$OUT/figures-scout.json" | tail -8'
    terminal("source-2-conditional-logit.png",
             "The loan file, by hand  ·  Scouting book.csv  ·  12,000 loans  ·  each candidate on its own",
             [(c3.replace('"$OUT/', '"OUT/'), run(c3))],
             [("OR [2.321672]", 1), ("gen 44.444214", 1), ("block 40.761071", 1), ("OR [1.961432 2.638629]", 1)])

    # 3 · the forest grown again from the file with the settings the Scouting tab states
    terminal("source-3-forest.png",
             "The loan file, by hand  ·  Scouting book.csv  ·  the forest grown again (scikit-learn, 200 trees, "
             "leaves of 40, seed 7)",
             [('python3 forest_scout.py "Scouting book.csv" "OUT/expected-forest.json" "OUT/figures-scout.json"',
               (OUT / "forest.log").read_text())],
             [("AUC built 0.628", 1), ("held 0.691767", 1), ("unseen 0.597", 1), ("held 0.676074", 1)])

    # 4 · the Look chart's bars for UTIL: counted from the file, and the arithmetic that moves them
    c4 = ("python3 -c \"import csv,math; v=[float(r['UTIL']) for r in csv.DictReader(open('Scouting book.csv'))]; "
          "hi=math.ceil(1.1999/0.1)*0.1; print('top of the chart:', repr(hi)); w=hi/200; "
          "print('slice for UTIL 0.24:', int(0.24/w), 'and at exactly 1.2:', int(0.24/(1.2/200))); "
          "print('loans from 0.18 to under 0.24:', sum(0.18<=x<0.24 for x in v)); "
          "print('loans at exactly 0.24:', sum(x==0.24 for x in v))\"")
    terminal("source-4-look-bars.png",
             "The loan file, by hand  ·  Scouting book.csv  ·  UTIL, the Look chart's fourth bar",
             [(c4, run(c4))],
             [("1.2000000000000002", 1), ("slice for UTIL 0.24: 39", 1), ("under 0.24: 538", 1),
              ("exactly 0.24: 5", 1)])

    workbook("wb-1-start-here.png", "start-here.png", (0, 480, 1100, 700),
             [(776, 518, 1090, 548)],
             "Consumer book Q3 - PocketBook.xlsx  ·  tab Start here  ·  F17  ·  LibreOffice Calc, recalculated on open")
    workbook("wb-2-pockets-kept.png", "pockets-kept.png", (0, 730, 1940, 900),
             [(84, 856, 1938, 876), (1553, 855, 1670, 877)],
             "Consumer book Q3 - PocketBook.xlsx  ·  tab Pockets  ·  MEASURE Kept after losses  ·  row 23, p-value L23")
    workbook("wb-3-new-variables.png", "new-variables.png", (0, 125, 1940, 606),
             [(1178, 534, 1413, 558), (1178, 558, 1413, 582), (1178, 582, 1413, 606)],
             "Scouting book - PocketBook.xlsx  ·  tab New variables  ·  rows 45 to 47, FICO and CHANNEL held fixed")
    workbook("wb-4-look-util.png", "look-util.png", (0, 200, 1400, 540),
             [(915, 295, 948, 512)],
             "Scouting book - PocketBook.xlsx  ·  tab Look  ·  UTIL  ·  the fourth bar, 0.18 to 0.24")


if __name__ == "__main__":
    main()
