"""Make every picture in the procedure and the defects file from what the walk captured.

    WALK=<scratch> python3 shots.py

Workbook pages come from the PDFs render.sh printed ($WALK/r/<name>.pdf); window
pictures from drive.py ($WALK/shots/*.png). Each picture is a crop of the page
with a red ring round what the step is about, and where the thing to read is
small, a zoomed crop underneath taken from a sharper render of the same page.
Rings are placed by finding the row's own words on the printed page
(pdftotext -bbox). Boxes are fractions of the whole page: (x1, y1, x2, y2).

Fifth walk (commit 5ef61df): the window is 720x560, so the window boxes were
measured again from its screenshots.
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
        out.append((a / pw, b / ph, c / pw, d / ph, m.group(5).replace("&amp;", "&").replace("&apos;", "'")
                    .replace("&quot;", '"')))
    return out


def find(pdf: str, n: int, text: str, nth: int = 0, x2: float | None = None, x1: float | None = None):
    """The box round `text` (several words, in order, on one printed line) on page n; x1/x2 widen it."""
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


BOX = (0.02, 0.245, 0.96, 0.97)          # the message box in the window
SETUP_BTN, RUN_BTN, BROWSE = (0.02, 0.17, 0.29, 0.225), (0.30, 0.17, 0.475, 0.225), (0.825, 0.10, 0.96, 0.155)
EXTRACT = (0.105, 0.10, 0.825, 0.155)
F = find


def line_box(y1, y2):
    """Lines of the window's message box, by pixel rows of the 560-high window."""
    return (0.02, y1 / 560, 0.96, y2 / 560)


# ---- the route
win("step-01-window-opened", "s01-1-opened", [BROWSE])
win("step-02a-pick-the-extract", "s01-2-file-dialog-typed", [(0.12, 0.615, 1.0, 0.665)])
win("step-02b-extract-picked", "s01-2-picked", [EXTRACT])
win("step-03-after-set-up", "s01-3-after-set-up", [SETUP_BTN, line_box(140, 208)])
sheet("step-04-start-here", "setup1", 1, (0.05, 0.08, 0.95, 0.46), [F("setup1", 1, "Calls still to make on Control", x2=0.45)])
ml = F("setup1", 2, "Fewest loans in a pocket before it is", x2=0.93)
sheet("step-05-control-blank", "setup1", 2, (0.05, 0.08, 0.95, 0.66), [(ml[0], ml[1], ml[2], ml[3] + 0.014)],
      zoom=(0.06, ml[1] - 0.03, 0.93, ml[3] + 0.10))
be = F("setup1", 3, "Band edges (620;", x2=0.44)
sheet("step-06-columns", "setup1", 3, (0.05, 0.08, 0.95, 0.46), [(be[0], be[1], be[2], be[3] + 0.028)],
      zoom=(0.06, 0.13, 0.62, 0.43))
sheet("step-07-odd-values", "setup1", 4, (0.05, 0.08, 0.95, 0.30))
sheet("step-07b-learned-empty", "setup1", 5, (0.05, 0.08, 0.95, 0.30))
win("step-08-run-before-answering", "s08-1-after-run", [RUN_BTN, line_box(140, 480)])
r13 = F("run1", 2, "Fewest loans in a pocket before it is", x2=0.93)
r19 = F("run1", 2, "How much worse than its comparison a", x2=0.93)
r21 = F("run1", 2, "How far revenue must move before it", x2=0.93)
sheet("step-09-control-answered", "run1", 2, (0.05, 0.08, 0.95, 0.66),
      [(r13[0], r13[1], r13[2], r13[3] + 0.014), (r19[0], r19[1], r19[2], r21[3] + 0.014)],
      zoom=(0.06, r13[1] - 0.01, 0.93, r21[3] + 0.03))
sheet("step-10a-columns-confirmed", "run1", 3, (0.05, 0.08, 0.95, 0.46), [F("run1", 3, "Checked every column? Yes", x2=0.30)])
sheet("step-10b-odd-values-answered", "run1", 4, (0.05, 0.08, 0.95, 0.30))
win("step-11-after-run", "s11-1-after-run", [RUN_BTN, line_box(140, 240)])
top = F("run1", 6, "Outcome, share of loans FICO under 654", x2=0.95)
sheet("step-12-where-it-bleeds", "run1", 6, (0.05, 0.10, 0.95, 0.50), [top], zoom=(0.05, 0.13, 0.95, 0.22))
pl = F("run1", 9, "under 654 Broker", x2=0.69)
sub = F("run1", 9, "Each pocket's GCO and RANR", x2=0.69)
sheet("step-13-losses-vs-revenue", "run1", 9, (0.05, 0.10, 0.95, 0.60), [pl, (sub[0], sub[1], sub[2], sub[3] + 0.03)],
      zoom=(0.07, 0.12, 0.70, 0.37))
sheet("step-13b-chart", "run1", 9, (0.69, 0.44, 0.91, 0.64), dpi=220)
sheet("step-13c-revenue-5-percent", "rev5", 9, (0.05, 0.10, 0.95, 0.40),
      [F("rev5", 9, "654 to under 686 Online", x2=0.69), F("rev5", 9, "Each pocket's GCO and RANR", x2=0.69)],
      zoom=(0.07, 0.12, 0.70, 0.37))
win("step-13d-revenue-95-refused", "wrong-rev-95-1-after-run", [line_box(140, 210)])
win("step-13e-revenue-095-refused", "wrong-rev-own095-1-after-run", [line_box(140, 210)])
sheet("step-14-grids", "run1", 12, (0.05, 0.10, 0.95, 0.45), [F("run1", 12, "(marked missing)", nth=1, x2=0.60)],
      zoom=(0.05, 0.12, 0.70, 0.27))
sheet("step-15-materiality", "run1", 15, (0.05, 0.08, 0.95, 0.60), [F("run1", 15, "1.0% 5.7", x1=0.07, x2=0.78)])
wk = F("run1", 20, "Worked out from this book", x2=0.93)
rv = F("run1", 20, "Revenue counts as more or less at", x2=0.93)
sheet("step-16-check", "run1", 20, (0.05, 0.08, 0.95, 0.78), [(wk[0], wk[1], wk[2], wk[3] + 0.014),
                                                              (rv[0], rv[1], rv[2], rv[3] + 0.014)],
      zoom=(0.10, wk[1] - 0.01, 0.93, rv[3] + 0.03))
sheet("step-17-log", "run1", 21, (0.05, 0.05, 0.95, 0.45))
sheet("step-17b-start-here-after-run", "run1", 1, (0.05, 0.08, 0.95, 0.46), [F("run1", 1, "Things to look at first on Columns", x2=0.45)])
sheet("step-18-split-set", "splitrev", 3, (0.05, 0.08, 0.95, 0.46), [F("splitrev", 3, "REV_DEBT Amount or number", x2=0.50)],
      zoom=(0.06, 0.13, 0.62, 0.43))
win("step-18b-after-split-run", "s18-1-after-run", [line_box(140, 262)])
s1 = F("splitrev", 12, "This grid holds FICO fixed", x2=0.87)
sheet("step-18c-split-tab", "splitrev", 12, (0.05, 0.06, 0.95, 0.55), [(s1[0], s1[1], s1[2], s1[3] + 0.03)],
      zoom=(0.05, 0.10, 0.85, 0.25))
o = F("splitrev", 13, "ORIG_BAL x CHANNEL: Outcome, share of loans", x2=0.87)
sheet("step-18d-split-orig-bal", "splitrev", 13, (0.05, o[1] - 0.01, 0.95, min(o[1] + 0.16, 0.99)),
      [(o[0], o[3] + 0.002, o[2], o[3] + 0.045)], dpi=170)
t1 = F("splitrev", 16, "Outcome, share of loans FICO under 654", x2=0.97)
sheet("step-18e-three-way", "splitrev", 16, (0.02, 0.10, 0.98, 0.30), [t1], dpi=200)
hf = F("splitrev", 16, "What this grid holds fixed")
sheet("step-18f-three-way-holds-fixed", "splitrev", 16, (0.66, 0.10, 0.93, 0.30), [(hf[0], hf[1], 0.93, hf[3])], dpi=220)
win("step-19-after-category-split", "s19-1-after-run", [line_box(225, 262)])
sheet("step-19b-three-way-category", "splitac", 14, (0.02, 0.10, 0.98, 0.27),
      [F("splitac", 14, "Outcome, share of loans FICO under 654", x2=0.97)], dpi=200)
av = F("show", 12, "FICO x CHANNEL: average ORIG_BAL per pocket")
sheet("step-20-show-per-pocket", "show", 12, (0.07, av[1] - 0.01, 0.30, av[1] + 0.25), dpi=200)
win("step-21-own-edges-run", "s21-1-after-run", [line_box(157, 210)])
sheet("step-21b-own-edges-losses-vs-revenue", "edges", 9, (0.05, 0.10, 0.95, 0.40), [F("edges", 9, "under 620 Broker", x2=0.69)],
      zoom=(0.07, 0.12, 0.91, 0.37))
sheet("step-21c-every-20-typed", "every20main", 3, (0.05, 0.08, 0.95, 0.46), [F("every20main", 3, "every 20")],
      zoom=(0.06, 0.13, 0.62, 0.43))
win("step-21d-every-20-run", "s21c-1-after-run", [line_box(157, 210)])
e20 = F("every20main", 25, "Band edges used: FICO", x2=0.93)
sheet("step-21e-every-20-check", "every20main", 25, (0.05, 0.08, 0.95, 0.40), [(e20[0], e20[1], e20[2], e20[3] + 0.005)],
      zoom=(0.10, e20[1] - 0.01, 0.93, e20[3] + 0.03))
win("step-22-set-up-again", "s22-1-after-set-up", [SETUP_BTN, line_box(140, 192)])
sheet("step-22b-start-here-after-set-up-again", "setup2", 1, (0.05, 0.08, 0.95, 0.46), [F("setup2", 1, "Calls still to make on Control", x2=0.95)])
sheet("step-22c-columns-after-set-up-again", "setup2", 3, (0.05, 0.08, 0.95, 0.46),
      [F("setup2", 3, "every 2000"), F("setup2", 3, "620; 680")], zoom=(0.06, 0.13, 0.62, 0.43))
sheet("step-23-learned-forget-marked", "forgetm", 5, (0.05, 0.05, 0.95, 0.40), [F("forgetm", 5, "Forget column CHANNEL", x2=0.95)])
win("step-23b-after-forget-run", "s23-1-after-run", [line_box(225, 262)])
win("step-23c-second-run-refused", "s23b-1-after-run", [line_box(140, 210)])
sheet("step-23d-columns-after-forget", "forget2", 3, (0.05, 0.08, 0.95, 0.46),
      [F("forget2", 3, "Forgotten on Learned: CHANNEL.", x1=0.07, x2=0.75), F("forget2", 3, "CHANNEL Category", x2=0.95)],
      zoom=(0.05, 0.12, 0.95, 0.27))
win("step-24-next-extract-set-up", "s24-2-after-set-up", [EXTRACT, line_box(140, 192)])
sheet("step-24b-next-extract-columns", "q4setup", 3, (0.05, 0.08, 0.95, 0.46), [F("q4setup", 3, "every 20")],
      zoom=(0.06, 0.13, 0.62, 0.43))

# ---- wrong turns (window)
for n in ("split-gco", "split-key", "split-outcome", "split-booked", "two-splits", "own-materiality",
          "split-only-segment", "avg-on-category", "edges-commas-number", "edges-outside", "w2-15-range-95",
          "extract-renamed-col", "extract-fewer-rows", "copied-folder", "noplant-split", "every1", "every0",
          "everytwenty", "every05", "every-on-category", "min-huge"):
    win(f"wrong-{n}", f"wrong-{n}-1-after-run", [BOX])
win("wrong-extract-renamed-col-set-up", "wrong-extract-renamed-col-b-1-after-set-up", [BOX])
win("wrong-open-run", "wrong-open-1-after-run", [BOX])
win("wrong-open-set-up", "wrong-open-2-after-set-up", [BOX])
win("wrong-picked-workbook", "wrong-picked-workbook-1-after-set-up", [BOX])
win("wrong-picked-workbook-run", "wrong-picked-workbook-2-after-run", [BOX])
win("wrong-new-columns-set-up", "wrong-new-columns-1-after-set-up", [BOX])
sheet("wrong-new-columns-tab", "w-new-columns", 3, (0.05, 0.08, 0.95, 0.52), [F("w-new-columns", 3, "CURR_STATUS", x2=0.95)])
wm = F("w-min-huge", 20, "Worked out from this book", x2=0.93)
sheet("wrong-min-huge-check", "w-min-huge", 20, (0.05, 0.08, 0.95, 0.80), [(wm[0], wm[1], wm[2], wm[3] + 0.005),
                                                                           F("w-min-huge", 20, "How much worse than its comparison a pocket must be", x2=0.93)],
      zoom=(0.10, wm[1] - 0.01, 0.93, wm[3] + 0.08))
print("ok")

# ---- pictures for the defects file
r = F("every20main", 6, "Outcome, share of loans FICO 600 to under 620", x2=0.95)
sheet("defect-1-every-20-planted-pocket-untested", "every20main", 6, (0.05, 0.10, 0.95, r[3] + 0.06), [r],
      zoom=(0.05, r[1] - 0.012, 0.95, r[3] + 0.012), dpi=130)
t = F("splitac", 14, "Outcome, share of loans FICO under 654", x2=0.97)
sheet("defect-1b-category-split-untested", "splitac", 14, (0.02, 0.10, 0.98, 0.20), [t], dpi=200)
sheet("defect-2-set-up-again-changes-bands", "setup2", 3, (0.05, 0.08, 0.95, 0.46),
      [F("setup2", 3, "every 2000"), F("setup2", 3, "620; 680"), F("setup2", 3, "every 20")], dpi=130)
rd = F("forget2", 31, "Band edges used: REV_DEBT", x2=0.93)
sheet("defect-2b-rev-debt-now-25-bands", "forget2", 31, (0.05, rd[1] - 0.03, 0.95, rd[3] + 0.04),
      [(rd[0], rd[1], rd[2], rd[3] + 0.003)], dpi=160)
sheet("defect-3-revenue-5-percent-same-boxes", "rev5", 9, (0.07, 0.12, 0.69, 0.37),
      [F("rev5", 9, "Pockets per box:", x2=0.69), F("rev5", 9, "654 to under 686 Online", x2=0.69)], dpi=220)
sheet("defect-3b-chart-dots-past-the-lines", "run1", 9, (0.07, 0.44, 0.91, 0.64),
      [F("run1", 9, "654 to under 686 4", x2=0.69), F("run1", 9, "712 to under 746 4", x2=0.69),
       F("run1", 9, "746 and over 2", x2=0.69)], dpi=200)
n1 = F("w-noplant", 17, "ORIG_BAL 49,158 and over CHANNEL / REV_DEBT Broker / REV_DEBT high half", x2=0.97)
sheet("defect-4-no-effect-book-three-way", "w-noplant", 17, (0.02, n1[1] - 0.045, 0.98, n1[3] + 0.03),
      [(n1[0], n1[1] - 0.03, n1[2], n1[3] + 0.002)], dpi=200)
o = F("w-noplant", 13, "ORIG_BAL x CHANNEL: Outcome, share of loans", x2=0.87)
sheet("defect-4b-no-effect-book-split-sentence", "w-noplant", 13, (0.05, o[1] - 0.01, 0.95, o[1] + 0.07),
      [(o[0], o[3] + 0.002, o[2], o[3] + 0.045)], dpi=200)
sheet("defect-5-same-box-at-1-76x", "run1", 9, (0.07, 0.44, 0.69, 0.64),
      [F("run1", 9, "712 to under 746 4", x2=0.69), F("run1", 9, "654 to under 686 4", x2=0.69)], dpi=220)
print("ok, defects")
