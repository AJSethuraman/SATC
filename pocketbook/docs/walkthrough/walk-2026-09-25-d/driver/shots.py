"""Make every picture in the procedure and the defects file from what the walk captured.

    WALK=<scratch> python3 shots.py

Workbook pages come from the PDFs render.sh printed ($WALK/r/<name>.pdf); window
pictures from drive.py ($WALK/shots/*.png). Each picture is a crop of the page
with a red ring round what the step is about, and where the thing to read is
small, a zoomed crop underneath taken from a sharper render of the same page.

Changed from the third walk: rings are placed by finding the row's own words on
the printed page (pdftotext -bbox), not by guessed fractions, so a row that moves
between builds is still ringed. Boxes are fractions of the whole page:
(x1, y1, x2, y2).
"""
import os
import re
import subprocess
from functools import lru_cache
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
        subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(n), "-l", str(n), "-png", "-singlefile",
                        str(W / "r" / f"{pdf}.pdf"), str(CACHE / f"{pdf}-{n}-{dpi}")], check=True)
    return Image.open(p).convert("RGB")


@lru_cache(None)
def words(pdf: str, n: int):
    x = subprocess.run(["pdftotext", "-bbox", "-f", str(n), "-l", str(n), str(W / "r" / f"{pdf}.pdf"), "-"],
                       capture_output=True, text=True, check=True).stdout
    pw, ph = map(float, re.search(r'<page width="([\d.]+)" height="([\d.]+)"', x).groups())
    out = []
    for m in re.finditer(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)<', x):
        a, b, c, d = map(float, m.groups()[:4])
        out.append((a / pw, b / ph, c / pw, d / ph, m.group(5).replace("&amp;", "&")))
    return out


def find(pdf: str, n: int, text: str, nth: int = 0, x2: float | None = None, x1: float | None = None):
    """The box round `text` (several words, in order, on one printed line) on page n; x1/x2 widen it.
    pdftotext lists a spreadsheet page column by column, so words are first regrouped into lines."""
    lines: dict[int, list] = {}
    for w in words(pdf, n):
        lines.setdefault(round(w[1] * 2000), []).append(w)
    want, hits = text.split(), []
    for y in sorted(lines):
        ws = sorted(lines[y], key=lambda w: w[0])
        for i in range(len(ws) - len(want) + 1):
            seq = ws[i:i + len(want)]
            if [s[4] for s in seq] == want:
                hits.append((seq[0][0], min(s[1] for s in seq), seq[-1][2], max(s[3] for s in seq)))
    if len(hits) <= nth:
        raise SystemExit(f"not found on {pdf} p{n}: {text!r}")
    a, b, c, d = hits[nth]
    return (x1 if x1 is not None else a, b + 0.001, x2 if x2 is not None else c, d - 0.001)


def compose(main, rings, crop, zoom_src, zoom):
    Wd, H = main.size
    d = ImageDraw.Draw(main)
    for x1, y1, x2, y2 in rings:
        d.rounded_rectangle((x1 * Wd - 4, y1 * H - 3, x2 * Wd + 4, y2 * H + 3), radius=6, outline=RED, width=3)
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
    """A workbook page at 100 dpi (or `dpi`); the zoom comes from a 220 dpi render with the rings drawn on it."""
    hi = compose(page(pdf, n, 220), rings, None, None, None) if zoom else None
    img = compose(page(pdf, n, dpi), rings, crop, hi, zoom)
    img.save(OUT / f"{name}.png")


def win(name, shot, rings=(), zoom=None):
    img = compose(Image.open(W / "shots" / f"{shot}.png").convert("RGB"), rings, None, None, zoom)
    img.save(OUT / f"{name}.png")


BOX = (0.01, 0.32, 0.96, 0.99)          # the message box in the window
SETUP_BTN, RUN_BTN, BROWSE = (0.02, 0.23, 0.33, 0.30), (0.34, 0.23, 0.53, 0.30), (0.81, 0.14, 0.95, 0.21)
F = find

# ---- the route
win("step-01-window-opened", "s01-1-opened", [BROWSE])
win("step-02a-pick-the-extract", "s01-2-file-dialog-typed", [(0.17, 0.65, 0.83, 0.72)])
win("step-02b-extract-picked", "s01-2-picked", [(0.12, 0.14, 0.80, 0.21)])
win("step-03-after-set-up", "s01-3-after-set-up", [SETUP_BTN, (0.02, 0.34, 0.95, 0.50)])
sheet("step-04-start-here", "setup1", 1, (0.05, 0.08, 0.95, 0.46), [F("setup1", 1, "Calls still to make on Control", x2=0.45)])
rev = F("setup1", 2, "How far revenue must move before it", x2=0.915)
sheet("step-05-control-blank", "setup1", 2, (0.05, 0.08, 0.95, 0.66), [(rev[0], rev[1], rev[2], rev[3] + 0.014)],
      zoom=(0.06, rev[1] - 0.03, 0.93, rev[3] + 0.03))
sheet("step-06-columns", "setup1", 3, (0.05, 0.08, 0.95, 0.46), [F("setup1", 3, "Split", x1=0.41, x2=0.46)],
      zoom=(0.06, 0.13, 0.62, 0.43))
sheet("step-07-odd-values", "setup1", 4, (0.05, 0.08, 0.95, 0.30))
sheet("step-07b-learned-empty", "setup1", 5, (0.05, 0.08, 0.95, 0.30))
win("step-08-run-before-answering", "s08-1-after-run", [RUN_BTN, BOX])
win("step-08b-scrolled", "s08-2-scrolled", [(0.02, 0.76, 0.96, 0.95)])
rev = F("run1", 2, "How far revenue must move before it", x2=0.915)
sheet("step-09-control-answered", "run1", 2, (0.05, 0.08, 0.95, 0.66), [(rev[0], rev[1], rev[2], rev[3] + 0.014)],
      zoom=(0.06, rev[1] - 0.03, 0.93, rev[3] + 0.03))
sheet("step-10a-columns-confirmed", "run1", 3, (0.05, 0.08, 0.95, 0.46), [F("run1", 3, "Checked every column?", x2=0.24)])
sheet("step-10b-odd-values-answered", "run1", 4, (0.05, 0.08, 0.95, 0.30))
win("step-11-after-run", "s11-1-after-run", [RUN_BTN, (0.02, 0.34, 0.95, 0.60)])
top = F("run1", 6, "Outcome, share of loans FICO under 654", x2=0.95)
sheet("step-12-where-it-bleeds", "run1", 6, (0.05, 0.10, 0.95, 0.50), [top], zoom=(0.05, 0.13, 0.95, 0.22))
pl = F("run1", 9, "under 654 Broker", x2=0.69)
sheet("step-13-losses-vs-revenue", "run1", 9, (0.05, 0.10, 0.95, 0.60), [pl, F("run1", 9, "Revenue counts as more", x1=0.07, x2=0.69)],
      zoom=(0.07, 0.12, 0.70, 0.37))
sheet("step-13b-chart", "run1", 9, (0.69, 0.16, 0.91, 0.36), dpi=220)
sheet("step-13c-revenue-5-percent", "rev5", 9, (0.05, 0.10, 0.95, 0.40), [F("rev5", 9, "Revenue counts as more", x1=0.07, x2=0.69)],
      zoom=(0.07, 0.12, 0.91, 0.37))
win("step-13d-revenue-95-refused", "wrong-rev-95-1-after-run", [BOX])
win("step-13e-revenue-095-refused", "wrong-rev-own095-1-after-run", [BOX])
sheet("step-14-grids", "run1", 12, (0.05, 0.10, 0.95, 0.45), [F("run1", 12, "(marked missing)", nth=1, x2=0.60)],
      zoom=(0.05, 0.12, 0.70, 0.27))
rr = F("run1", 12, "FICO x CHANNEL: RANR per booked dollar")
sheet("step-14b-grids-ranr", "run1", 12, (0.05, rr[1] - 0.01, 0.95, rr[1] + 0.13), dpi=170)
sheet("step-15-materiality", "run1", 15, (0.05, 0.08, 0.95, 0.60), [F("run1", 15, "1.0% 5.7", x1=0.07, x2=0.78)])
sheet("step-16-check", "run1", 20, (0.05, 0.08, 0.95, 0.78), [F("run1", 20, "Revenue counts as more or less at", x2=0.93)])
sheet("step-17-log", "run1", 21, (0.05, 0.05, 0.95, 0.45))
sheet("step-17b-start-here-after-run", "run1", 1, (0.05, 0.08, 0.95, 0.46), [F("run1", 1, "Things to look at first on Columns", x2=0.45)])
sheet("step-18-split-set", "splitrev", 3, (0.05, 0.08, 0.95, 0.46), [F("splitrev", 3, "REV_DEBT", x2=0.46)],
      zoom=(0.06, 0.13, 0.62, 0.43))
win("step-18b-after-split-run", "s18-1-after-run", [RUN_BTN, (0.02, 0.50, 0.95, 0.62)])
s1 = F("splitrev", 12, "The high-REV_DEBT half was worse in 14", x2=0.87)
sheet("step-18c-split-tab", "splitrev", 12, (0.05, 0.06, 0.95, 0.55), [(s1[0], s1[1], s1[2], s1[3] + 0.04)],
      zoom=(0.05, 0.10, 0.60, 0.25))
o = F("splitrev", 13, "ORIG_BAL x CHANNEL: Outcome, share of loans", x2=0.87)
sheet("step-18d-split-orig-bal", "splitrev", 13, (0.05, o[1] - 0.01, 0.95, min(o[1] + 0.16, 0.99)),
      [(o[0], o[3] + 0.002, o[2], o[3] + 0.045)], dpi=170)
sheet("step-18e-three-way", "splitrev", 16, (0.02, 0.10, 0.98, 0.27), [F("splitrev", 16, "Outcome, share of loans FICO under 654", x2=0.97)],
      dpi=200)
win("step-19-after-category-split", "s19-1-after-run", [(0.02, 0.575, 0.95, 0.66)])
sheet("step-19b-three-way-category", "splitac", 14, (0.02, 0.10, 0.98, 0.27), [F("splitac", 14, "Outcome, share of loans FICO under 654", x2=0.97)],
      dpi=200)
av = F("show", 12, "FICO x CHANNEL: average ORIG_BAL per pocket")
sheet("step-20-show-per-pocket", "show", 12, (0.07, av[1] - 0.01, 0.30, av[1] + 0.25), dpi=200)
win("step-21-own-edges-run", "s21-1-after-run", [(0.02, 0.37, 0.95, 0.49)])
sheet("step-21b-own-edges-losses-vs-revenue", "edges", 9, (0.05, 0.10, 0.95, 0.40), [F("edges", 9, "under 620 Broker", x2=0.69)],
      zoom=(0.07, 0.12, 0.91, 0.37))
win("step-22-set-up-again", "s22-1-after-set-up", [SETUP_BTN, (0.02, 0.34, 0.95, 0.50)])
sheet("step-22b-start-here-after-set-up-again", "setup2", 1, (0.05, 0.08, 0.95, 0.46), [F("setup2", 1, "Calls still to make on Control", x2=0.95)])
sheet("step-23-learned-forget-marked", "forgetm", 5, (0.05, 0.05, 0.95, 0.40), [F("forgetm", 5, "Forget column CHANNEL", x2=0.95)])
win("step-23b-after-forget-run", "s23-1-after-run", [(0.02, 0.60, 0.95, 0.70)])
win("step-23c-second-run-refused", "s23b-1-after-run", [BOX])
sheet("step-23d-columns-after-forget", "forget2", 3, (0.05, 0.08, 0.95, 0.46),
      [F("forget2", 3, "Forgotten on Learned: CHANNEL.", x1=0.07, x2=0.75), F("forget2", 3, "CHANNEL Category", x2=0.95)],
      zoom=(0.05, 0.12, 0.95, 0.27))

# ---- wrong turns (window)
for n in ("split-gco", "split-key", "split-outcome", "split-booked", "two-splits", "own-materiality",
          "split-only-segment", "avg-on-category", "edges-commas-number", "edges-outside", "w2-15-range-95",
          "extract-renamed-col", "extract-fewer-rows", "copied-folder", "noplant-split"):
    win(f"wrong-{n}", f"wrong-{n}-1-after-run", [BOX])
win("wrong-extract-renamed-col-set-up", "wrong-extract-renamed-col-b-1-after-set-up", [BOX])
win("wrong-open-run", "wrong-open-1-after-run", [BOX])
win("wrong-open-set-up", "wrong-open-2-after-set-up", [BOX])
win("wrong-picked-workbook", "wrong-picked-workbook-1-after-set-up", [BOX])
win("wrong-picked-workbook-run", "wrong-picked-workbook-2-after-run", [BOX])
win("wrong-new-columns-set-up", "wrong-new-columns-1-after-set-up", [BOX])
sheet("wrong-new-columns-tab", "w-new-columns", 3, (0.05, 0.08, 0.95, 0.52), [F("w-new-columns", 3, "CURR_STATUS", x2=0.95)])
sheet("wrong-own-materiality-check", "w-own-materiality", 20, (0.05, 0.08, 0.95, 0.85),
      [F("w-own-materiality", 20, "Smallest excess loss worth reporting", x2=0.93)])
print("ok")

# ---- pictures for the defects file
t = F("w-noplant", 16, "ORIG_BAL 49,158 and over CHANNEL / REV_DEBT Broker / REV_DEBT high half", x2=0.95)
sheet("defect-1-no-effect-book-three-way", "w-noplant", 16, (0.02, 0.10, 0.98, t[3] + 0.03), [t], dpi=200)
o = F("w-noplant", 13, "ORIG_BAL x CHANNEL: Outcome, share of loans", x2=0.87)
sheet("defect-1b-no-effect-book-split-sentence", "w-noplant", 13, (0.05, o[1] - 0.01, 0.95, o[1] + 0.07),
      [(o[0], o[3] + 0.002, o[2], o[3] + 0.045)], dpi=200)
rows = [F("run1", 9, "under 654 Online", x2=0.69), F("run1", 9, "under 654 Branch", x2=0.69),
        F("run1", 9, "746 and over Branch", x2=0.69)]
sheet("defect-2-box-against-dollars", "run1", 9, (0.07, 0.16, 0.69, 0.37), rows, dpi=220)
sheet("defect-2b-chart-names-losing-less", "run1", 9, (0.69, 0.16, 0.91, 0.36), [(0.788, 0.247, 0.845, 0.268)], dpi=220)
rows = [F("run1", 9, "(marked missing) Broker", x2=0.69), F("run1", 9, "(marked missing) Online", x2=0.69)]
sheet("defect-3-untested-pockets-boxed", "run1", 9, (0.07, 0.16, 0.69, 0.37), rows, dpi=220)
sheet("defect-4-line-moves-with-the-split", "splitac", 8, (0.07, 0.12, 0.69, 0.37),
      [F("splitac", 8, "Revenue counts as more", x1=0.07, x2=0.69), F("splitac", 8, "(marked missing) Broker", x2=0.69)], dpi=220)
print("ok, defects")
