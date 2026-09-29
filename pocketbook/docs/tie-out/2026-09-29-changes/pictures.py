"""Make this tie-out's pictures (the full tie-out's pictures.py, pointed at the changes).

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
    c1 = 'python3 explain_new.py split "$OUT" two "FICO x CHANNEL · SYS_FLAG Y vs N"'
    c1b = 'python3 cmh_check.py "Two-flag book.csv"'
    terminal("source-1-split.png",
             "Change 1  ·  Two-flag book.csv  ·  FICO x CHANNEL, SYS_FLAG Y against N, Bad loans",
             [(c1.replace('"$OUT"', "OUT"), run(c1)), (c1b, run(c1b))],
             [("1.66736e-10", 1), ("1.66736e-10", 2), ("5.56501e-11", 1), ("5.56501e-11", 2), ("Q 46.137288", 1),
              ("chi2 46.137288", 1)])
    c2 = ('python3 explain_new.py panel "$OUT" flag "FICO x CHANNEL / SYS_FLAG" "Bad loans" "(blank)" "Broker · Y"')
    c2b = ('python3 explain_new.py panel "$OUT" q3 "FICO x CHANNEL" "Kept after losses" "496 - 653" "Branch"')
    terminal("source-2-panel.png",
             "Change 2  ·  What one cell says  ·  a pocket alone in its band, and a gap in points",
             [(c2.replace('"$OUT"', "OUT"), run(c2)), (c2b.replace('"$OUT"', "OUT"), run(c2b))],
             [("Blank: alone in its band. Nothing else in (blank) to compare with.", 2),
              ("Kept 3.97 points more", 2)])
    c3 = 'python3 explain_new.py dots "$OUT" q3 "FICO x CHANNEL" | head -6'
    terminal("source-3-dots.png",
             "Change 3  ·  Paid, cost, kept  ·  Consumer book Q3  ·  FICO x CHANNEL, the chart's first rows",
             [(c3.replace('"$OUT"', "OUT"), run(c3))],
             [("red, 1", 1), ("green, 3", 1), ("Priced for it", 1)])
    c4 = ("awk -F, 'NR>1 {v=$11; if (v<0) {c[v]++; n++} else {k++; s+=v; if (k==1||v<lo) lo=v; if (v>hi) hi=v}} "
          "END {for (x in c) printf \"code %d on %d loans\\n\", x, c[x]; printf \"answered missing %d; left: %d loans, "
          "smallest %d, largest %d, mean %.6f\\n\", n, k, lo, hi, s/k}' \"Bureau book.csv\" | sort")
    terminal("source-4-look.png",
             "Change 4  ·  Bureau book.csv  ·  SHORT_HIST with its bureau codes answered missing",
             [(c4, run(c4))],
             [("answered missing 200", 1), ("mean 216.205128", 1), ("smallest 0", 1)])
    c5 = "cat OUT/diagnose.txt"
    terminal("source-5-family.png",
             "The one DIFFERS  ·  Flag book  ·  FICO x ASSET_CLASS / SYS_FLAG, Earned before losses, against the band",
             [(c5, (OUT / "diagnose.txt").read_text())],
             [("(0.9641, 0.9929)", 1), ("(0.9534, 0.9819)", 1)])
    c6 = "cat results/long-shuffle-pocketbook.txt results/long-shuffle-road2.txt | cut -c1-110"
    terminal("source-6-long-shuffle.png",
             "The one DIFFERS again  ·  the same pocket, 200,000 shuffles a time, five seeds on each road",
             [(c6, run(c6))],
             [("p 0.96015", 1), ("p 0.95994", 1), ("p 0.95992", 1), ("p 0.96071", 1)])


if __name__ == "__main__":
    main()
