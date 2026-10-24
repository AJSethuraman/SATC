"""Make every picture in the procedure and the defects file from what the walk captured.

    WALK=<scratch> python3 shots.py

Workbook pages come from the PDFs render.sh printed ($WALK/r/<name>.pdf); window
pictures from drive.py ($WALK/shots/*.png). Each picture is a crop of the page
with a red ring round what the step is about, and where the thing to read is
small, a zoomed crop underneath taken from a sharper render of the same page.
Boxes are fractions of the whole page: (x1, y1, x2, y2).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W = Path(os.environ["WALK"])
OUT = Path(__file__).resolve().parents[1]
CACHE = W / "pages"
CACHE.mkdir(exist_ok=True)
RED = (204, 0, 0)


def page(pdf: str, n: int, dpi: int) -> Image.Image:
    p = CACHE / f"{pdf}-{n}-{dpi}.png"
    if not p.exists():
        stem = CACHE / f"{pdf}-{n}-{dpi}"
        subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(n), "-l", str(n), "-png", "-singlefile",
                        str(W / "r" / f"{pdf}.pdf"), str(stem)], check=True)
    return Image.open(p).convert("RGB")


def compose(main: Image.Image, rings, crop, zoom_src: Image.Image | None, zoom) -> Image.Image:
    Wd, H = main.size
    d = ImageDraw.Draw(main)
    for x1, y1, x2, y2 in rings:
        d.rounded_rectangle((x1 * Wd - 4, y1 * H - 4, x2 * Wd + 4, y2 * H + 4), radius=8, outline=RED, width=3)
    if crop:
        main = main.crop((int(crop[0] * Wd), int(crop[1] * H), int(crop[2] * Wd), int(crop[3] * H)))
    parts = [main]
    if zoom:
        src = zoom_src or main
        Wh, Hh = src.size
        z = src.crop((int(zoom[0] * Wh), int(zoom[1] * Hh), int(zoom[2] * Wh), int(zoom[3] * Hh)))
        scale = min(main.width / z.width, 2.5)
        parts.append(z.resize((int(z.width * scale), int(z.height * scale)), Image.LANCZOS))
    out = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts) + 12 * (len(parts) - 1)),
                    "white")
    y = 0
    for i, p in enumerate(parts):
        out.paste(p, (0, y))
        if i:
            ImageDraw.Draw(out).rectangle((0, y - 1, p.width - 1, y + p.height - 1), outline=RED, width=2)
        y += p.height + 12
    return out


def sheet(name, pdf, n, crop, rings=(), zoom=None, dpi=100):
    """A workbook page: the page at 100 dpi (or `dpi`), zoom from 200 dpi."""
    img = compose(page(pdf, n, dpi), rings, crop, page(pdf, n, 200) if zoom else None, zoom)
    img.save(OUT / f"{name}.png")


def win(name, shot, rings=(), zoom=None):
    """A window picture from drive.py, ringed."""
    img = compose(Image.open(W / "shots" / f"{shot}.png").convert("RGB"), rings, None, None, zoom)
    img.save(OUT / f"{name}.png")


BOX = (0.01, 0.32, 0.96, 0.99)          # the message box in the window
SETUP_BTN, RUN_BTN, BROWSE = (0.02, 0.23, 0.33, 0.30), (0.34, 0.23, 0.53, 0.30), (0.81, 0.14, 0.95, 0.21)

# ---- the route
win("step-01-window-opened", "s01-1-opened", [BROWSE])
win("step-02a-pick-the-extract", "s01-2-file-dialog-typed", [(0.17, 0.65, 0.83, 0.72)])
win("step-02b-extract-picked", "s01-2-picked", [(0.12, 0.14, 0.80, 0.21)])
win("step-03-after-set-up", "s01-3-after-set-up", [SETUP_BTN, (0.02, 0.34, 0.95, 0.50)])
sheet("step-04-start-here", "setup1", 1, (0.05, 0.08, 0.95, 0.46), [(0.07, 0.34, 0.45, 0.43)])
sheet("step-05-control-blank", "setup1", 2, (0.05, 0.08, 0.95, 0.62), [(0.215, 0.20, 0.41, 0.55)])
sheet("step-06-columns", "setup1", 3, (0.05, 0.08, 0.95, 0.46), [(0.15, 0.155, 0.24, 0.17), (0.37, 0.175, 0.46, 0.215)],
      zoom=(0.06, 0.13, 0.50, 0.43))
sheet("step-07-odd-values", "setup1", 4, (0.05, 0.08, 0.95, 0.30), [(0.575, 0.237, 0.66, 0.262)])
sheet("step-07b-learned-empty", "setup1", 5, (0.05, 0.08, 0.95, 0.30))
win("step-08-run-before-answering", "s08-1-after-run", [RUN_BTN, BOX])
win("step-08b-scrolled", "s08-2-scrolled", [(0.02, 0.87, 0.96, 0.95)])
sheet("step-09-control-answered", "run1", 2, (0.05, 0.08, 0.95, 0.62), [(0.215, 0.20, 0.41, 0.55)])
sheet("step-10a-columns-confirmed", "run1", 3, (0.05, 0.08, 0.95, 0.46), [(0.07, 0.155, 0.24, 0.17)])
sheet("step-10b-odd-values-answered", "run1", 4, (0.05, 0.08, 0.95, 0.30), [(0.575, 0.237, 0.66, 0.262)])
win("step-11-after-run", "s11-1-after-run", [RUN_BTN, (0.02, 0.34, 0.95, 0.60)])
sheet("step-12-where-it-bleeds", "run1", 6, (0.05, 0.10, 0.95, 0.50), [(0.07, 0.189, 0.93, 0.196)],
      zoom=(0.07, 0.16, 0.93, 0.24))
sheet("step-13-losses-vs-revenue", "run1", 9, (0.05, 0.10, 0.95, 0.60), [(0.07, 0.3415, 0.69, 0.3485), (0.69, 0.16, 0.81, 0.21)],
      zoom=(0.07, 0.16, 0.69, 0.40))
sheet("step-13b-chart", "run1", 9, (0.69, 0.16, 0.89, 0.49), dpi=220)
sheet("step-14-grids", "run1", 11, (0.05, 0.10, 0.95, 0.55), [(0.32, 0.188, 0.58, 0.195)], zoom=(0.07, 0.15, 0.76, 0.26))
sheet("step-14b-grids-ranr", "run1", 11, (0.05, 0.44, 0.95, 0.56), zoom=(0.07, 0.455, 0.76, 0.55))
sheet("step-15-materiality", "run1", 14, (0.05, 0.08, 0.95, 0.60), [(0.07, 0.25, 0.78, 0.335)])
sheet("step-16-check", "run1", 19, (0.05, 0.08, 0.95, 0.75))
sheet("step-17-log", "run1", 20, (0.05, 0.05, 0.95, 0.45))
sheet("step-17b-start-here-after-run", "run1", 1, (0.05, 0.08, 0.95, 0.46), [(0.07, 0.34, 0.95, 0.43)])
sheet("step-18-split-set", "splitrev", 3, (0.05, 0.08, 0.95, 0.46), [(0.41, 0.395, 0.46, 0.415)], zoom=(0.06, 0.13, 0.62, 0.43))
win("step-18b-after-split-run", "s18-1-after-run", [RUN_BTN, (0.02, 0.34, 0.95, 0.55)])
sheet("step-18c-split-tab", "splitrev", 11, (0.05, 0.10, 0.95, 0.55), [(0.07, 0.19, 0.84, 0.22)], zoom=(0.07, 0.17, 0.70, 0.34))
sheet("step-18d-split-orig-bal", "splitrev", 12, (0.05, 0.06, 0.95, 0.95), [(0.07, 0.765, 0.87, 0.815), (0.07, 0.121, 0.87, 0.141)])
win("step-19-after-category-split", "s19-1-after-run")
sheet("step-19b-category-split-grids", "splitac", 9, (0.05, 0.10, 0.95, 0.46), [(0.07, 0.26, 0.70, 0.43)], zoom=(0.07, 0.26, 0.70, 0.43))
sheet("step-19c-split-tab-category", "splitac", 13, (0.05, 0.08, 0.95, 0.25))
sheet("step-20-show-per-pocket", "show", 11, (0.07, 0.555, 0.30, 0.74), dpi=200)
win("step-21-own-edges-run", "s21-1-after-run", [(0.02, 0.37, 0.95, 0.49)])
win("step-22-set-up-again", "s22-1-after-set-up", [SETUP_BTN, (0.02, 0.34, 0.95, 0.50)])
sheet("step-22b-start-here-after-set-up-again", "setup2", 1, (0.05, 0.08, 0.95, 0.46), [(0.07, 0.34, 0.95, 0.43)])
sheet("step-23-learned-forget-marked", "forgetm", 5, (0.05, 0.08, 0.95, 0.40), [(0.07, 0.255, 0.95, 0.268)])
win("step-23b-after-forget-run", "s23-1-after-run", [(0.02, 0.575, 0.95, 0.605)])
sheet("step-23c-learned-after-second-run", "forget2", 5, (0.05, 0.08, 0.95, 0.40), [(0.07, 0.255, 0.95, 0.268)])

# ---- wrong turns (window)
for n in ("two-splits", "split-only-segment", "avg-on-category", "edges-outside", "edges-commas-number",
          "extract-renamed-col", "extract-fewer-rows", "copied-folder", "split-gco",
          "split-key", "own-materiality", "w2-15-range-95"):
    win(f"wrong-{n}", f"wrong-{n}-1-after-run", [BOX])
win("wrong-open-run", "wrong-open-1-after-run", [BOX])
win("wrong-open-set-up", "wrong-open-2-after-set-up", [BOX])
win("wrong-picked-workbook", "wrong-picked-workbook-1-after-set-up", [(0.02, 0.34, 0.95, 0.46)])
win("wrong-new-columns-set-up", "wrong-new-columns-1-after-set-up", [(0.02, 0.38, 0.95, 0.46)])
sheet("wrong-new-columns-tab", "w-new-columns", 3, (0.05, 0.08, 0.95, 0.52), [(0.07, 0.15, 0.95, 0.18)])
sheet("wrong-edges-commas-text-check", "w-edges-commas-text", 19, (0.05, 0.08, 0.95, 0.40), [(0.07, 0.330, 0.60, 0.345)])
sheet("wrong-own-materiality-check", "w-own-materiality", 19, (0.05, 0.08, 0.95, 0.80))
sheet("wrong-split-gco-tab", "w-split-gco", 14, (0.05, 0.08, 0.95, 0.40), [(0.07, 0.19, 0.84, 0.22)])
print("ok")

# ---- pictures for the defects file
sheet("defect-1-worst-pockets-in-earning-more", "run1", 9, (0.07, 0.16, 0.69, 0.378), [(0.07, 0.3455, 0.69, 0.3695)], dpi=200)
sheet("defect-2-split-finds-debt-that-isnt-there", "w-noplant", 13, (0.05, 0.595, 0.95, 0.88),
      [(0.075, 0.615, 0.84, 0.648)], dpi=150)
print("ok, defects")
