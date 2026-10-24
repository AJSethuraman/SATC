"""The pictures that changed with the firm's answers to the walk's design calls (A to K, 27 Sep 2026), and the
before-and-after pairs for B, D and H. Writes into pocketbook/docs/walkthrough/2026-09-27/.

    xvfb-run -a -s "-screen 0 1000x760x24" venv/bin/python walk_answers.py BEFORE/pocketbook/src wb_before bleed
    xvfb-run -a -s "-screen 0 1000x760x24" venv/bin/python walk_answers.py pocketbook/src wb_after all
    DPI=160 python3 render.py wb_after/books/STAGE.xlsx r_after/STAGE 160     (each stage the pictures use; the same
                                                                              for wb_before into r_before)
    python3 shots_answers.py wb_before r_before wb_after r_after

BEFORE is the build at 37135f61 (`git archive`), the head the firm answered on. 08-scout's Start here is written again
with the fixed build before rendering (restart), since the odds heading changed after that run. Boxes are fractions
of the source image, as in shots.py."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parents[1]
WB, RB, WA, RA = (Path(a) for a in sys.argv[1:5])
RED = (204, 0, 0)
L = lambda x1, y1, x2, y2: (x1 / 720, y1 / 560, x2 / 720, y2 / 560)   # noqa: E731  launcher pixels


def page(folder: Path, n: int) -> Path:
    """pdftoppm names pages p-4 or p-04, by how many there are."""
    return next(p for p in (folder / f"p-{n}.png", folder / f"p-{n:02d}.png") if p.exists())


def make(name, src, crop=None, rings=(), zoom=None, maxw=1100, below=None):
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
    for src2, crop2 in below or ():
        b = Image.open(src2).convert("RGB")
        w1, h1 = b.size
        parts.append(b.crop((int(crop2[0] * w1), int(crop2[1] * h1), int(crop2[2] * w1), int(crop2[3] * h1))))
    out = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts) + 14 * (len(parts) - 1)), "white")
    y = 0
    for i, p in enumerate(parts):
        out.paste(p, (0, y))
        if i and zoom and i == 1:
            ImageDraw.Draw(out).rectangle((0, y - 1, p.width - 1, y + p.height - 1), outline=RED, width=2)
        y += p.height + 14
    if out.width > maxw:
        out = out.resize((maxw, int(out.height * maxw / out.width)), Image.LANCZOS)
    out.save(HERE / f"{name}.png", optimize=True)
    print(name, out.size)


SA, SB = WA / "shots", WB / "shots"
START = (0.07, 0.1, 0.93, 0.76)
FOUND = (0.075, 0.4, 0.92, 0.605)

# ---- the window: F's plain words, E's one count, B's two tiles and J's lines
make("step-04-set-up-read-the-columns", SA / "s06-choose-tests-bleed.png",
     rings=[L(441, 16, 702, 45), L(217, 438, 700, 495)])
make("step-05-split-by-rev-debt", SA / "s07-split-rev-debt.png", rings=[L(630, 258, 690, 282), L(217, 395, 700, 495)])
make("step-06-answer-in-the-workbook", SA / "s08-answer-in-workbook.png", rings=[L(217, 97, 700, 172), L(217, 180, 700, 215)])
make("step-11-workbook-open", SA / "s11-workbook-open.png", rings=[L(217, 91, 700, 140), L(646, 511, 701, 543)])
make("step-12-run-finished", SA / "s19-run-finished.png", rings=[L(215, 53, 530, 153), L(215, 160, 690, 210)])
make("step-21-run-again", SA / "s20-run-again.png", rings=[L(215, 53, 530, 153)])
make("step-22-test-new-variables", SA / "s22-test-new-variables.png",
     rings=[L(582, 16, 702, 45), L(561, 363, 701, 395), L(217, 405, 700, 497)])
make("step-23-scikit-learn-installed", SA / "s23b-sklearn-installed.png", rings=[L(217, 405, 700, 500)])
make("step-24-candidates", SA / "s24-candidates-ticked.png", rings=[L(540, 97, 702, 282), L(217, 378, 700, 500)])
make("step-25-answer-new", SA / "s25-answer-new.png", rings=[L(217, 93, 700, 124)])
make("step-27-scouting-finished", SA / "s26-scout-finished.png", rings=[L(215, 53, 690, 178), L(215, 183, 690, 232)])
make("step-32-run-after-edit", SA / "s27-edited-prespec-run.png", rings=[L(535, 53, 690, 178), L(215, 185, 690, 250)])

# ---- the workbook
make("step-10-control-answered", page(RA / "02-answered", 2), crop=(0.06, 0.1, 0.81, 0.43),
     rings=[(0.465, 0.226, 0.53, 0.25)], maxw=1300)
make("step-13-start-here", page(RA / "03-run1", 1), crop=START, rings=[(0.075, 0.26, 0.7, 0.33), FOUND])
make("step-15-paid-cost-kept", page(RA / "03-run1", 9), crop=(0.07, 0.37, 0.65, 0.63),
     rings=[(0.074, 0.42, 0.63, 0.436)])
make("step-18-record", page(RA / "03-run1", 12), crop=(0.06, 0.1, 0.94, 0.62), zoom=(0.065, 0.45, 0.5, 0.6))
make("step-19-live-change-start-here", page(RA / "04-live", 1), crop=START, rings=[FOUND])
make("step-20-waiting-for-a-run", page(RA / "05-pending", 1), crop=(0.07, 0.1, 0.93, 0.62),
     rings=[(0.498, 0.265, 0.695, 0.33), (0.075, 0.34, 0.93, 0.385)])
make("step-20b-control-status", page(RA / "05-pending", 2), crop=(0.06, 0.25, 0.81, 0.45),
     rings=[(0.605, 0.3, 0.67, 0.36), (0.605, 0.372, 0.67, 0.425)], maxw=1300)
make("step-26-control-new-variable", page(RA / "07-new-written", 2), crop=(0.06, 0.25, 0.81, 0.5),
     rings=[(0.06, 0.345, 0.81, 0.48), (0.70, 0.352, 0.775, 0.37)], maxw=1300)
make("step-25b-start-here-waits", page(RA / "07-new-written", 1), crop=(0.07, 0.1, 0.93, 0.45),
     rings=[(0.498, 0.265, 0.695, 0.33), (0.075, 0.34, 0.93, 0.395)])
make("step-28-start-here-new", page(RA / "08-scout-restart", 1), crop=(0.07, 0.1, 0.93, 0.62),
     rings=[(0.075, 0.495, 0.92, 0.6)])
make("step-29b-the-pre-spec", page(RA / "08-scout", 7), crop=(0.06, 0.1, 0.72, 0.77), rings=[(0.065, 0.16, 0.6, 0.35)])

# ---- before and after: B (the tie-out tile), D (Start here's list after a live change), H (Look)
make("design-B-before", SB / "s19-run-finished.png", rings=[L(535, 53, 690, 153)],
     below=[(page(RB / "03-run1", 1), (0.07, 0.4, 0.93, 0.62))])
make("design-B-after", SA / "s19-run-finished.png", rings=[L(215, 53, 530, 153)],
     below=[(page(RA / "03-run1", 1), (0.07, 0.4, 0.93, 0.62))])
make("design-D-before", page(RB / "04-live", 1), crop=START, rings=[(0.075, 0.49, 0.92, 0.585)])
make("design-D-after", page(RA / "04-live", 1), crop=START, rings=[(0.075, 0.47, 0.92, 0.6)])
make("design-H-before", page(RB / "01-written", 5), crop=(0.06, 0.1, 0.7, 0.6))
make("design-H-after", page(RA / "01-written", 4), crop=(0.06, 0.1, 0.7, 0.68),
     below=[(page(RA / "01-written", 5), (0.06, 0.1, 0.7, 0.36))])
