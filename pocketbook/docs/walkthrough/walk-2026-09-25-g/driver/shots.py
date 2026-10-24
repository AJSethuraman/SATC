"""Make every picture in the procedure and the defects file from what the walk captured.

    WALK=<scratch> python3 shots.py

Workbook pages come from the PDFs render.sh printed ($WALK/r/<name>.pdf); window
pictures from drive.py ($WALK/shots/*.png). Each picture is a crop of the page
with a red ring round what the step is about, and where the thing to read is
small, a zoomed crop underneath taken from a sharper render of the same page.
Rings are placed by finding the row's own words on the printed page
(pdftotext -bbox). Boxes are fractions of the whole page: (x1, y1, x2, y2).

Seventh walk (commit a5a8aa2): the same 720x560 window as the fifth and sixth. Control prints its Last Run used column now, so no widened copy is needed. Pages are found by
the tab's first printed line (pg), since which page a tab lands on moves with the bands.
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


def line_box(first, last=None):
    """Lines of the window's message box, counted from 1 (each about 17 pixels of the 560-high window)."""
    last = last or first
    return (0.02, (140 + 17 * (first - 1)) / 560, 0.96, (140 + 17 * last + 2) / 560)


@lru_cache(None)
def pg(pdf: str, first: str, nth: int = 0) -> int:
    """The page whose first printed line starts with `first`."""
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(W / "r" / f"{pdf}.pdf")],
                                                         capture_output=True, text=True).stdout).group(1))
    hits = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(W / "r" / f"{pdf}.pdf"), "-"],
                           capture_output=True, text=True).stdout.strip().splitlines()
        if t and t[0].startswith(first):
            hits.append(i)
    return hits[nth]


def row(pdf, first, text, nth=0, x1=None, x2=0.95):
    p = pg(pdf, first)
    return p, F(pdf, p, text, nth=nth, x1=x1, x2=x2)


def pgt(pdf: str, text: str, start: int = 1) -> int:
    """The first page from `start` on which `text` is printed on one line."""
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(W / "r" / f"{pdf}.pdf")],
                                                         capture_output=True, text=True).stdout).group(1))
    for i in range(start, n + 1):
        try:
            F(pdf, i, text)
            return i
        except SystemExit:
            pass
    raise SystemExit(f"{text!r} not on any page of {pdf}")


# ---- the route (seventh walk)
import sys
ONLY = set(sys.argv[1:])          # name prefixes to make; none = all


def want(name):
    return not ONLY or any(name.startswith(o) for o in ONLY)


def S_(name, *a, **k):
    if want(name):
        sheet(name, *a, **k)


def W_(name, *a, **k):
    if want(name):
        win(name, *a, **k)


W_("step-01-window-opened", "s01-1-opened", [BROWSE])
W_("step-02-extract-picked", "s02-1-picked", [EXTRACT])
W_("step-03-after-set-up", "s02-2-after-set-up", [SETUP_BTN, line_box(1, 4)])
S_("step-04-start-here", "setup1", 1, (0.05, 0.08, 0.95, 0.46), [F("setup1", 1, "Calls still to make on Control", x2=0.45)])
if want("step-05"):
    ml = F("setup1", 2, "How far revenue must move before it", x2=0.93)
    sheet("step-05-control-blank", "setup1", 2, (0.05, 0.08, 0.95, 0.66), [(ml[0], ml[1], ml[2], ml[3] + 0.014)])
if want("step-06"):
    be = F("setup1", 3, "Band edges (620;", x2=0.44)
    sheet("step-06-columns", "setup1", 3, (0.05, 0.08, 0.95, 0.46), [(be[0], be[1], be[2], be[3] + 0.028)],
          zoom=(0.06, 0.13, 0.62, 0.43))
S_("step-07-odd-values", "setup1", 4, (0.05, 0.08, 0.95, 0.30))
S_("step-07b-learned-empty", "setup1", 5, (0.05, 0.08, 0.95, 0.30))
W_("step-08-run-before-answering", "s08-1-after-run", [RUN_BTN, line_box(1, 12)])
if want("step-09"):
    lr = F("run1", 2, "Last Run used")
    r21 = F("run1", 2, "How far revenue must move before it", x2=0.99)
    r13 = F("run1", 2, "Fewest loans in a pocket before it is", x2=0.99)
    r19 = F("run1", 2, "How much worse than its comparison a", x2=0.99)
    sheet("step-09-control-answered", "run1", 2, (0.05, 0.10, 0.99, 0.60),
          [(lr[0] - 0.003, lr[1], 0.99, lr[3]), (r13[0], r13[1], r13[2], r13[3] + 0.014),
           (r19[0], r19[1], r19[2], r21[3] + 0.014)],
          zoom=(0.06, r19[1] - 0.01, 0.99, r21[3] + 0.03))
S_("step-10a-columns-confirmed", "run1", 3, (0.05, 0.08, 0.95, 0.46), [F("run1", 3, "Checked every column? Yes", x2=0.30)])
S_("step-10b-odd-values-answered", "run1", 4, (0.05, 0.08, 0.95, 0.30))
W_("step-11-after-run", "s11-1-after-run", [RUN_BTN, line_box(6)])
if want("step-12"):
    top = F("run1", 6, "Outcome, share of loans FICO under 654", x2=0.95)
    sheet("step-12-where-it-bleeds", "run1", 6, (0.05, 0.10, 0.95, 0.50), [top], zoom=(0.05, 0.13, 0.95, 0.22))
if want("step-13"):
    pl = F("run1", 9, "under 654 Broker", x2=0.69)
    sub = F("run1", 9, "Each pocket's GCO and RANR", x2=0.69)
    sheet("step-13-losses-vs-revenue", "run1", 9, (0.05, 0.10, 0.95, 0.40),
          [pl, (sub[0], sub[1], sub[2], sub[3] + 0.03)], zoom=(0.07, 0.12, 0.70, 0.37))
    fa = F("run1", 9, "FICO x ASSET_CLASS")
    sheet("step-13b-luck-marks", "run1", 9, (0.07, fa[1] - 0.005, 0.70, fa[1] + 0.20),
          [F("run1", 9, "Pockets per box: Losing more, earning the same: 1; About the same on both: 11.", x2=0.69),
           F("run1", 9, "654 to under 686 4", x2=0.69)], dpi=200)
    sheet("step-13c-chart", "run1", 9, (0.69, fa[1] - 0.01, 0.91, fa[1] + 0.21), dpi=220)
    rp = pgt("run1", "6,559 to under 9,837 Broker", 9)
    rd = F("run1", rp, "6,559 to under 9,837 Broker", x2=0.69)
    sheet("step-13d-earning-less", "run1", rp, (0.07, max(rd[1] - 0.10, 0.05), 0.70, rd[3] + 0.12), [rd], dpi=160)
    p5 = pg("w-rev5", "Losses vs revenue")
    sheet("step-13e-revenue-5-percent", "w-rev5", p5, (0.05, 0.10, 0.95, 0.40),
          [F("w-rev5", p5, "Each pocket's GCO and RANR", x2=0.69), F("w-rev5", p5, "Pockets per box:", x2=0.69)],
          zoom=(0.07, 0.12, 0.70, 0.37))
W_("step-13f-revenue-95-refused", "wrong-rev-95-1-after-run", [line_box(1, 4)])
W_("step-13g-revenue-095-refused", "wrong-rev-own095-1-after-run", [line_box(1, 4)])
S_("step-14-grids", "run1", 12, (0.05, 0.10, 0.95, 0.45), zoom=(0.05, 0.12, 0.70, 0.27))
S_("step-15-materiality", "run1", 15, (0.05, 0.08, 0.95, 0.60), [F("run1", 15, "1.0% 5.7", x1=0.07, x2=0.78)])
if want("step-16"):
    wk = F("run1", 20, "Worked out from this book", x2=0.93)
    rv = F("run1", 20, "Revenue counts as more or less", x2=0.93)
    sheet("step-16-check", "run1", 20, (0.05, 0.08, 0.95, 0.78), [(wk[0], wk[1], wk[2], wk[3] + 0.014),
                                                                  (rv[0], rv[1], rv[2], rv[3])],
          zoom=(0.10, wk[1] - 0.01, 0.93, rv[3] + 0.02))
S_("step-17-log", "run1", 21, (0.05, 0.05, 0.95, 0.45))
S_("step-17b-start-here-after-run", "run1", 1, (0.05, 0.08, 0.95, 0.46), [F("run1", 1, "Last run", x2=0.95)])
S_("step-18-split-set", "splitrev", 3, (0.05, 0.08, 0.95, 0.46), [F("splitrev", 3, "REV_DEBT Amount or number", x2=0.50)],
   zoom=(0.06, 0.13, 0.62, 0.43))
W_("step-18b-after-split-run", "s18-1-after-run", [line_box(7, 8)])
if want("step-18c") or want("step-18d") or want("step-18e") or want("step-18f") or want("step-18g"):
    h = F("splitrev", 12, "How this tab works")
    sheet("step-18c-split-how-it-works", "splitrev", 12, (0.05, 0.10, 0.95, 0.43),
          [(0.07, F("splitrev", 12, "Luck alone How often")[1], 0.93, F("splitrev", 12, "Pooled across pockets")[1] - 0.004),
           (0.07, F("splitrev", 12, "What it assumes")[1], 0.93, F("splitrev", 12, "What it assumes")[3] + 0.035)], dpi=150)
    fx = F("splitrev", 12, "FICO x CHANNEL")
    sheet("step-18d-split-fico-grid", "splitrev", 12, (0.05, fx[1] - 0.01, 0.95, fx[1] + 0.40),
          [(0.07, fx[3] + 0.002, 0.93, fx[3] + 0.02), (0.07, fx[1] + 0.11, 0.30, fx[1] + 0.20)], dpi=150)
    wp = pgt("splitrev", "Grids that don't hold FICO fixed.", 12)
    wn = F("splitrev", wp, "Grids that don't hold FICO fixed.", x2=0.60)
    sheet("step-18e-split-warning", "splitrev", wp, (0.05, wn[1] - 0.02, 0.95, wn[1] + 0.13), [wn], dpi=160)
    t1 = F("splitrev", 15, "Outcome, share of loans FICO under 654", x2=0.99)
    sheet("step-18f-three-way", "splitrev", 15, (0.02, 0.10, 0.99, 0.26), [t1], dpi=200)
    nb = F("splitrev", 15, "Outcome, share of loans ORIG_BAL", x2=0.99)
    sheet("step-18g-three-way-holds-fixed", "splitrev", 15, (0.55, nb[1] - 0.05, 1.0, nb[1] + 0.06),
          [(0.55, nb[1], 0.999, nb[3])], dpi=240)
W_("step-19-after-category-split", "s19-1-after-run", [line_box(7, 8)])
if want("step-19b"):
    tp = pg("splitac", "Three-way")
    sheet("step-19b-three-way-category", "splitac", tp, (0.02, 0.10, 0.98, 0.25),
          [F("splitac", tp, "Outcome, share of loans FICO under 654 CHANNEL", x2=0.97)], dpi=200)
if want("step-20"):
    sp = pgt("show", "average ORIG_BAL per pocket", 12)
    av = F("show", sp, "average ORIG_BAL per pocket")
    sheet("step-20-show-per-pocket", "show", sp, (0.05, av[1] - 0.01, 0.60, av[1] + 0.25), dpi=170)
W_("step-21-own-edges-run", "s21-1-after-run", [line_box(2, 4)])
if want("step-21b"):
    pe = pg("edges", "Losses vs revenue")
    sheet("step-21b-own-edges-losses-vs-revenue", "edges", pe, (0.05, 0.10, 0.95, 0.36),
          [F("edges", pe, "under 620 Broker", x2=0.69)], zoom=(0.07, 0.15, 0.70, 0.22))
S_("step-21c-every-20-typed", "every20main", 3, (0.05, 0.08, 0.95, 0.46), [F("every20main", 3, "every 20")],
   zoom=(0.06, 0.13, 0.62, 0.43))
W_("step-21d-every-20-run", "s21c-1-after-run", [line_box(2, 7)])
if want("step-21e"):
    e6 = F("every20main", 6, "Outcome, share of loans FICO 600 to under 620", x2=0.95)
    e7 = F("every20main", 6, "Outcome, share of loans FICO 580 to under 600", x2=0.95)
    sheet("step-21e-every-20-where-it-bleeds", "every20main", 6, (0.05, 0.10, 0.95, e7[3] + 0.03), [e6, e7],
          zoom=(0.05, e6[1] - 0.012, 0.95, e7[3] + 0.012), dpi=130)
if want("step-21f"):
    pe20 = pg("every20main", "Losses vs revenue")
    sheet("step-21f-every-20-losses-vs-revenue", "every20main", pe20, (0.05, 0.10, 0.95, 0.40),
          [F("every20main", pe20, "600 to under 620 Broker", x2=0.69)], zoom=(0.07, 0.15, 0.70, 0.22))
W_("step-22-set-up-again", "s22-1-after-set-up", [SETUP_BTN, line_box(1, 3)])
if want("step-22b"):
    lr2 = F("setup2", 2, "Last Run used")
    sheet("step-22b-control-after-set-up-again", "setup2", 2, (0.05, 0.10, 0.99, 0.60), [(lr2[0] - 0.003, lr2[1], 0.99, 0.58)])
S_("step-23-learned-forget-marked", "forgetm", 5, (0.05, 0.05, 0.95, 0.40), [F("forgetm", 5, "Forget column CHANNEL", x2=0.95)])
W_("step-23b-after-forget-run", "s23-1-after-run", [line_box(7, 8)])
W_("step-23c-second-run-refused", "s23b-1-after-run", [line_box(1, 4)])
W_("step-24-next-extract-set-up", "s24-2-after-set-up", [EXTRACT, line_box(1, 3)])
S_("step-24b-next-extract-columns", "q4setup", 3, (0.05, 0.08, 0.95, 0.46),
   [F("q4setup", 3, "FICO FICO score Yes every 20", x2=0.95)], zoom=(0.05, 0.16, 0.75, 0.27))
W_("step-25-third-extract-set-up", "s25-1-after-set-up", [line_box(1, 3)])

# ---- blue rows: a high fewest-loans floor
W_("step-21g-high-floor-run", "wrong-min450-1-after-run", [line_box(6, 7)])
if want("step-21h"):
    b1 = F("w-min450", 6, "Outcome, share of loans FICO under 654 ASSET_CLASS 4", x2=0.95)
    sheet("step-21h-high-floor-blue-rows", "w-min450", 6, (0.05, 0.10, 0.95, 0.40), [b1], zoom=(0.05, 0.13, 0.95, 0.24), dpi=130)

# ---- wrong turns (window)
for n in ("split-gco", "split-key", "split-outcome", "split-booked", "two-splits", "own-materiality",
          "split-only-segment", "avg-on-category", "edges-commas-number", "edges-outside", "w2-15-range-95",
          "extract-renamed-col", "extract-fewer-rows", "copied-folder", "noplant-split", "every1", "every0",
          "everytwenty", "every05", "everyneg", "every-on-category", "every2000", "min-huge", "lowdef", "min450"):
    W_(f"wrong-{n}", f"wrong-{n}-1-after-run", [BOX])
W_("wrong-extract-renamed-col-set-up", "wrong-extract-renamed-col-b-1-after-set-up", [BOX])
W_("wrong-open-run", "wrong-open-1-after-run", [BOX])
W_("wrong-open-set-up", "wrong-open-2-after-set-up", [BOX])
W_("wrong-picked-workbook", "wrong-picked-workbook-1-after-set-up", [BOX])
W_("wrong-picked-workbook-run", "wrong-picked-workbook-2-after-run", [BOX])
W_("wrong-new-columns-set-up", "wrong-new-columns-1-after-set-up", [BOX])
print("ok")

# ---- pictures for the defects file
if want("defect-1"):
    pe5 = pg("w-edges-5", "Losses vs revenue")
    sheet("defect-1-lob-edges-5-percent", "w-edges-5", pe5, (0.06, 0.10, 0.93, 0.42),
          [F("w-edges-5", pe5, "under 620 Broker", x2=0.69), F("w-edges-5", pe5, "Pockets per box:", x2=0.69),
           F("w-edges-5", pe5, "Revenue counts as more at 1.05x or above")], dpi=200)
    pw5 = pg("w-every20-5", "Losses vs revenue")
    sheet("defect-1b-every-20-5-percent", "w-every20-5", pw5, (0.06, 0.10, 0.93, 0.42),
          [F("w-every20-5", pw5, "600 to under 620 Broker", x2=0.69), F("w-every20-5", pw5, "Pockets per box:", x2=0.69)],
          dpi=200)
    rp5 = pgt("w-rev5", "49,152 and over Broker", 9)
    ob = F("w-rev5", rp5, "49,152 and over Broker", x2=0.69)
    sheet("defect-1c-default-bands-5-percent", "w-rev5", rp5, (0.06, max(ob[1] - 0.05, 0.02), 0.70, min(ob[3] + 0.015, 1.0)),
          [ob, F("w-rev5", rp5, "Pockets per box: About the same on both: 2.", x2=0.69)], dpi=200)
if want("defect-2"):
    r21 = F("run1", 2, "How far revenue must move before it", x2=0.99)
    sheet("defect-2-revenue-option-explained-wrong", "run1", 2, (0.06, r21[1] - 0.03, 0.99, r21[3] + 0.04),
          [(r21[0], r21[1], 0.99, r21[3] + 0.014)], dpi=200)
if want("defect-4"):  # the box text off its row
    fa = F("run1", 9, "FICO x ASSET_CLASS")
    sheet("defect-4-box-text-off-its-row", "run1", 9, (0.07, fa[1] - 0.005, 0.70, fa[1] + 0.12),
          [F("run1", 9, "654 to under 686 4", x2=0.69), F("run1", 9, "712 to under 746 4", x2=0.69)], dpi=240)
if want("defect-5"):  # RANR reading cut off
    pe5 = pg("w-edges-5", "Losses vs revenue")
    u = F("w-edges-5", pe5, "under 620 Broker", x2=0.69)
    sheet("defect-5-ranr-reading-cut-off", "w-edges-5", pe5, (0.30, u[1] - 0.03, 0.70, u[3] + 0.06),
          [(0.33, u[1] - 0.012, 0.47, u[3] + 0.004)], dpi=260)
if want("defect-3"):  # two tabs, two words
    lp = pgt("w-every20-luck", "6,559 to under 9,837 Broker", 11)
    lr = F("w-every20-luck", lp, "6,559 to under 9,837 Broker", x2=0.69)
    sheet("defect-3-every-20-earning-less", "w-every20-luck", lp, (0.06, max(lr[1] - 0.06, 0.02), 0.70, lr[3] + 0.06),
          [lr], dpi=200)
    wp_ = pgt("w-every20-luck", "RANR per booked dollar REV_DEBT 6,559 to under 9,837 CHANNEL Broker", 6)
    wr = F("w-every20-luck", wp_, "RANR per booked dollar REV_DEBT 6,559 to under 9,837 CHANNEL Broker", x2=0.95)
    sheet("defect-3b-every-20-where-it-bleeds-in-line", "w-every20-luck", wp_,
          (0.05, max(wr[1] - 0.04, 0.02), 0.95, wr[3] + 0.04), [wr], dpi=180)
    win("defect-3c-every-20-window", "wrong-every20-luck-1-after-run", [line_box(5)])
if want("defect-6"):
    mw = F("w-min-huge", 20, "Suggested values", x2=0.93)
    sheet("defect-6-check-fallback", "w-min-huge", 20, (0.05, mw[1] - 0.03, 0.95, mw[3] + 0.06),
          [(mw[0], mw[1], mw[2], mw[3] + 0.028)], dpi=200)
    lw = F("w-lowdef", 20, "Suggested values", x2=0.93)
    sheet("defect-6b-check-fallback-low-default", "w-lowdef", 20, (0.05, lw[1] - 0.03, 0.95, lw[3] + 0.06),
          [(lw[0], lw[1], lw[2], lw[3] + 0.028)], dpi=200)
    win("defect-6c-window-low-default", "wrong-lowdef-1-after-run", [line_box(2, 7), line_box(10, 11)])
if want("defect-7"):
    win("defect-7-blue-count-window", "wrong-min450-1-after-run", [line_box(6, 7)])
if want("defect-8"):
    npw_p = pgt("w-noplant-split", "Grids that don't hold FICO fixed.", 12)
    npw = F("w-noplant-split", npw_p, "Grids that don't hold FICO fixed.", x2=0.60)
    sheet("defect-8-no-effect-book-split", "w-noplant-split", npw_p, (0.05, npw[1] - 0.02, 0.95, npw[1] + 0.13),
          [npw, F("w-noplant-split", npw_p, "Outcome, share of loans 15 13 of 15", x2=0.56)], dpi=160)
    n1 = F("w-noplant-split", 15, "Outcome, share of loans ORIG_BAL 49,158 and over", x2=0.999)
    sheet("defect-8b-no-effect-book-three-way", "w-noplant-split", 15, (0.07, n1[1] - 0.02, 1.0, n1[3] + 0.02), [n1], dpi=240)
print("ok, defects")
