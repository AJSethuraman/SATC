"""Make the tie-out's pictures.

    python3 pictures.py

Source pictures (the extract's side): each command below is RUN, here, on "Consumer book Q3.csv", and its real
output is drawn as a terminal window with the command above it -- nothing typed in by hand. The figure is then
ringed in red, found by searching the output for its text, so a ring cannot land on a number that is not there.

Workbook pictures (PocketBook's side): LibreOffice Calc screenshots of the workbook as the analyst opens it (in
raw/, taken under a virtual display, the file recalculated on load), cut to the rows that matter, ringed, and
given an identity band naming the file, the tab and the cell.
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CSV = "Consumer book Q3.csv"
MONO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
MONO_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 15)
SANS_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
SANS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
RED = (220, 20, 20)
CW, LH = 9, 21            # DejaVu Sans Mono 15px: character width and line height

FILTER = """NR>1 && $2!="" && $2!=-9999 && $2<654"""


def run(cmd):
    return subprocess.run(["bash", "-c", cmd], cwd=HERE, capture_output=True, text=True, check=True).stdout


def terminal(name, title, steps, rings):
    """steps: [(command, output)]; rings: [(text to find in an output line, occurrence)]."""
    lines = []           # (text, kind)
    for cmd, out in steps:
        full = "$ " + cmd
        while len(full) > 112:                  # a long command wraps, as a terminal would
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
    """crop: (x0, y0, x1, y1) in the screenshot, or several stacked top to bottom (a wide sheet's dropdowns over
    the block that matters, with a grey rule between); rings: boxes in the screenshot's pixels."""
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
    rows = f"awk -F, '{FILTER} && $3==\"Broker\"' \"{CSV}\""
    sums = (f"awk -F, '{FILTER} {{s=($3==\"Broker\")?\"Broker\":\"others\"; n[s]++; "
            f"if($5==0||$5==1){{t[s]++; b[s]+=$5}}; g[s]+=$6; k[s]+=$4}} "
            f"END{{for(s in n) printf \"%-7s loans %5d  flag 0/1 %5d  bad %4d  GCO_AMT %13.2f  ORIG_BAL %14.2f\\n\", "
            f"s, n[s], t[s], b[s], g[s], k[s]}}' \"{CSV}\" | sort")
    steps = [
        (f"wc -l \"{CSV}\"", run(f"wc -l \"{CSV}\"")),
        (f"head -1 \"{CSV}\"", run(f"head -1 \"{CSV}\"")),
        (rows + " | head -5", run(rows + " | head -5")),
        (rows + " | wc -l", run(rows + " | wc -l")),
        (f"awk -F, '{FILTER} {{print $2}}' \"{CSV}\" | sort -n | sed -n '1p;$p'",
         run(f"awk -F, '{FILTER} {{print $2}}' \"{CSV}\" | sort -n | sed -n '1p;$p'")),
        (sums, run(sums)),
    ]
    terminal("source-1-extract-fico-under-654.png",
             "The extract, read with awk  ·  Consumer book Q3.csv  ·  8,000 loans + 1 header row  ·  10 columns",
             steps, [("8001 Consumer book Q3.csv", 1), ("523", 2), ("loans   523", 1), ("bad  128", 1),
                     ("GCO_AMT    2414523.69", 1), ("ORIG_BAL    17041067.38", 1),
                     ("GCO_AMT    1820522.82", 1), ("ORIG_BAL    33706885.06", 1), ("bad  106", 1)])

    out = run(f"./by-hand.awk \"{CSV}\"")
    fig2 = out[out.index("FIGURE 2"):]
    terminal("source-2-grid-by-hand.png",
             "The extract, read with awk  ·  Consumer book Q3.csv  ·  the FICO x CHANNEL grid by hand",
             [(f"./by-hand.awk \"{CSV}\"   # the Figure 2 part of its output", fig2)],
             [("1556", 1), ("8000", 1), ("258068446.03", 1), ("17041067.38", 1)])

    fig1 = out[:out.index("FIGURE 2")]
    terminal("source-3-figure-1-by-hand.png",
             "The extract, read with awk  ·  Consumer book Q3.csv  ·  Figure 1 worked through",
             [(f"./by-hand.awk \"{CSV}\"   # the Figure 1 part of its output", fig1)],
             [("2.6233556379", 1), ("1494128.5842", 1), ("0.0540104141", 2), ("74.281008", 1)])

    pv = run(f"python3 pvalue.py \"{CSV}\"")
    terminal("source-4-pvalue.png",
             "The extract, read with Python's csv module, scipy and statsmodels  ·  Consumer book Q3.csv",
             [(f"python3 pvalue.py \"{CSV}\"", pv)],
             [("2.032066e-12", 1), ("2.438479e-12", 1), ("9.550925e-02", 1)])

    book = "Consumer book Q3 - PocketBook.xlsx"
    workbook("wb-1-start-here.png", "start-here.png", (0, 120, 940, 700),
             [(80, 590, 938, 620), (298, 130, 800, 158)],
             f"{book}  ·  tab Start here  ·  row 20  ·  LibreOffice Calc, recalculated on open")
    workbook("wb-2-pockets-chargeoffs.png", "pockets-chargeoffs.png", (0, 555, 1540, 810),
             [(84, 720, 1418, 748), (130, 650, 372, 682)],
             f"{book}  ·  tab Pockets  ·  MEASURE (C18) set to Charge-offs  ·  row 21")
    workbook("wb-3-pockets-badloans.png", "pockets-badloans.png", (0, 555, 1790, 1090),
             [(1550, 718, 1674, 748), (84, 718, 1550, 748), (84, 1057, 2140, 1082)],
             f"{book}  ·  tab Pockets  ·  MEASURE Bad loans (as it opens)  ·  row 21, p-value in L21; row 37")
    workbook("wb-4-grids-loans.png", "grids-loans.png", ((0, 395, 1000, 450), (1160, 695, 2140, 925)),
             [(1278, 700, 2140, 918)],
             f"{book}  ·  tab Grids  ·  GRID FICO x CHANNEL  ·  the Loans block, M27:Q35")
    workbook("wb-5-grids-booked.png", "grids-booked.png", (0, 395, 1045, 1015),
             [(393, 569, 609, 994)],
             f"{book}  ·  tab Grids  ·  booked dollars by pocket, D44:E63")
    workbook("wb-6-record.png", "record.png", (0, 290, 1325, 1010),
             [(407, 883, 1323, 912)],
             f"{book}  ·  tab Record  ·  Does it add up, C25")


if __name__ == "__main__":
    main()
