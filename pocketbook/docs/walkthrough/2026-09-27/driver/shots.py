"""Mark each screenshot to its step: crop, ring what the step is about, add a zoomed crop under it.
Writes into pocketbook/docs/walkthrough/2026-09-27/. Boxes are fractions of the source image."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

W = Path(__file__).resolve().parents[1]
S, R, S2 = W / "shots", W / "r", W / "shots2"
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
RED = (204, 0, 0)


def make(name, src, crop=None, rings=(), zoom=None, maxw=1100):
    im = Image.open(src).convert("RGB")
    w0, h0 = im.size
    d = ImageDraw.Draw(im)
    for x1, y1, x2, y2 in rings:
        d.rounded_rectangle((x1 * w0 - 4, y1 * h0 - 4, x2 * w0 + 4, y2 * h0 + 4), radius=8, outline=RED, width=3)
    base = im.copy()
    if crop:
        im = im.crop((int(crop[0] * w0), int(crop[1] * h0), int(crop[2] * w0), int(crop[3] * h0)))
    parts = [im]
    if zoom:
        z = base.crop((int(zoom[0] * w0), int(zoom[1] * h0), int(zoom[2] * w0), int(zoom[3] * h0)))
        k = min(im.width / z.width, 2.2)
        parts.append(z.resize((int(z.width * k), int(z.height * k)), Image.LANCZOS))
    out = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts) + 14 * (len(parts) - 1)), "white")
    y = 0
    for i, p in enumerate(parts):
        out.paste(p, (0, y))
        if i:
            ImageDraw.Draw(out).rectangle((0, y - 1, p.width - 1, y + p.height - 1), outline=RED, width=2)
        y += p.height + 14
    if out.width > maxw:
        out = out.resize((maxw, int(out.height * maxw / out.width)), Image.LANCZOS)
    out.save(OUT / f"{name}.png", optimize=True)
    print(name, out.size)


L = lambda x1, y1, x2, y2: (x1 / 720, y1 / 560, x2 / 720, y2 / 560)   # noqa: E731  launcher pixels
Q = lambda x1, y1, x2, y2: (x1 / 1000, y1 / 760, x2 / 1000, y2 / 760)  # noqa: E731  the whole virtual screen

# ---- the window, first time
make("step-01-add-ons-missing", S2 / "s01-opened-addon-missing.png", rings=[L(606, 9, 706, 42)])
make("step-02-browse", S / "s02b-browse-typed.png", crop=Q(0, 0, 720, 560), rings=[Q(143, 346, 578, 372), Q(581, 343, 675, 374)])
make("step-03-installed", S2 / "s04-installed.png", rings=[L(217, 277, 650, 295), L(526, 511, 701, 543)])
# ---- where the book bleeds
make("step-04-set-up-read-the-columns", S / "s06-choose-tests-bleed.png", rings=[L(441, 16, 702, 45), L(440, 53, 702, 305)])
make("step-05-split-by-rev-debt", S / "s07-split-rev-debt.png", rings=[L(630, 258, 690, 282), L(217, 455, 700, 502)])
make("step-06-answer-in-the-workbook", S / "s08-answer-in-workbook.png", rings=[L(217, 97, 700, 145)])
make("step-07-run-before-answering", S2 / "s09-run-before-answering.png", rings=[L(217, 91, 700, 393), L(12, 216, 190, 254)])
make("step-08-control-blank", R / "01-written/control-top.png", maxw=1300)
make("step-08b-worked-out", R / "01-written/control-right.png", rings=[(0.69, 0.37, 0.95, 0.66)], maxw=1100)
make("step-09-columns", R / "01-written/columns-left.png", rings=[(0.16, 0.105, 0.305, 0.14), (0.71, 0.315, 0.89, 0.43)])
make("step-10-control-answered", R / "02-answered/control-answered.png", rings=[(0.255, 0.4, 0.485, 0.61), (0.255, 0.66, 0.485, 0.85)], maxw=1300)
make("step-11-workbook-open", S / "s11-workbook-open.png", rings=[L(217, 91, 700, 140), L(646, 511, 701, 543)])
make("step-12-run-finished", S / "s19-run-finished.png", rings=[L(215, 53, 690, 153)])
make("step-13-start-here", R / "03-run1/m-01.png", crop=(0.07, 0.1, 0.93, 0.75), rings=[(0.08, 0.41, 0.93, 0.6)])
make("step-14-pockets", R / "03-run1/m-08.png", crop=(0.07, 0.11, 0.93, 0.62), rings=[(0.09, 0.39, 0.3, 0.41)],
     zoom=(0.07, 0.42, 0.93, 0.52))
make("step-15-paid-cost-kept", R / "03-run1/pck-table.png", rings=[(0.005, 0.14, 0.62, 0.21)])
make("step-16-grids", R / "06-run2/p-11.png", crop=(0.07, 0.1, 0.93, 0.53), rings=[(0.07, 0.25, 0.39, 0.28)])
make("step-17-split", R / "03-run1/m-12.png", crop=(0.07, 0.1, 0.93, 0.78), rings=[(0.075, 0.47, 0.745, 0.575)])
make("step-18-record", R / "03-run1/m-13.png", crop=(0.06, 0.1, 0.94, 0.62), zoom=(0.065, 0.445, 0.5, 0.6))
make("step-19-live-change-start-here", R / "04-live/p-01.png", crop=(0.07, 0.1, 0.93, 0.6), rings=[(0.08, 0.41, 0.93, 0.585)])
make("step-19b-live-change-pockets", R / "04-live/p-08.png", crop=(0.07, 0.36, 0.93, 0.55), rings=[(0.07, 0.395, 0.52, 0.415)])
make("step-20-waiting-for-a-run", R / "05-pending/start-pending.png", rings=[(0.72, 0.36, 0.99, 0.48), (0.01, 0.51, 0.99, 0.58)])
make("step-20b-control-status", R / "05-pending/control-pending.png", rings=[(0.68, 0.38, 0.78, 0.47)], maxw=1300)
make("step-21-run-again", S / "s20-run-again.png", rings=[L(215, 53, 690, 153)])
# ---- test new variables
make("step-22-test-new-variables", S / "s22-test-new-variables.png", rings=[L(582, 16, 702, 45), L(561, 414, 701, 446), L(217, 455, 700, 502)])
make("step-23-scikit-learn-installed", S2 / "s23b-sklearn-installed.png", rings=[L(217, 482, 545, 502)])
make("step-24-candidates", S2 / "s24-candidates-ticked.png", rings=[L(540, 97, 702, 282), L(217, 380, 430, 402), L(217, 415, 700, 478)])
make("step-25-answer-new", S / "s25-answer-new.png", rings=[L(217, 93, 700, 124)])
make("step-26-control-new-variable", R / "07-new-written/m-02.png", crop=(0.06, 0.1, 0.62, 0.62), rings=[(0.06, 0.41, 0.6, 0.6)])
make("step-27-scouting-finished", S2 / "s26-scout-finished.png", rings=[L(215, 53, 690, 178)])
make("step-28-start-here-new", R / "11-b2scout/p-01.png", crop=(0.07, 0.1, 0.93, 0.6), rings=[(0.08, 0.41, 0.93, 0.47)])
make("step-29-scouting", R / "08-scout/m-07.png", crop=(0.06, 0.1, 0.94, 0.85), rings=[(0.065, 0.675, 0.94, 0.78)])
make("step-29b-the-pre-spec", R / "08-scout/m-08.png", crop=(0.06, 0.1, 0.72, 0.77), rings=[(0.065, 0.19, 0.6, 0.38)])
make("step-30-new-variables", R / "08-scout/m-09.png", crop=(0.06, 0.51, 0.94, 0.83), rings=[(0.065, 0.63, 0.94, 0.66)])
make("step-31-record-new", R / "08-scout/m-11.png", crop=(0.06, 0.1, 0.94, 0.72))
make("step-32-run-after-edit", S2 / "s27-edited-prespec-run.png", rings=[L(535, 53, 690, 178)])
make("step-33-record-changed", R / "09-edited/m-11.png", crop=(0.06, 0.55, 0.5, 0.72), rings=[(0.065, 0.58, 0.5, 0.61)])
make("step-34-run-stopped", S2 / "d-tieout-fails.png", rings=[L(215, 18, 702, 225)])

# ---- the defects: before and after
make("defect-1-changed-pre-spec-reads-yes", S / "s27-edited-prespec-run.png", rings=[L(535, 53, 690, 153)])
make("fixed-1-changed", S2 / "s27-edited-prespec-run.png", rings=[L(535, 53, 690, 178)])
make("defect-2-run-stopped-as-an-answer", S / "d-tieout-fails.png", rings=[L(215, 18, 702, 166), L(12, 216, 190, 254)])
make("fixed-2-run-stopped", S2 / "d-tieout-fails.png", rings=[L(215, 18, 702, 225), L(12, 216, 190, 254)])
make("fixed-3-cannot-open", S2 / "s10-open-at-cannot.png", rings=[L(215, 398, 702, 462)])
make("defect-4-good-news-in-red", S / "s04-installing.png", rings=[L(217, 277, 650, 295)])
make("defect-11-loans-tested-cut-off", R / "08-scout/m-01.png", crop=(0.07, 0.41, 0.93, 0.48), rings=[(0.5, 0.445, 0.72, 0.47)])
make("defect-12-install-never-finishes", S / "defect-12-still-installing.png")
