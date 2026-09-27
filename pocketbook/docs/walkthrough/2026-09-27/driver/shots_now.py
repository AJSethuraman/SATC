"""Every picture the procedure uses, retaken from one walk of the current build (walk_now.py), marked to its step.
Writes into pocketbook/docs/walkthrough/2026-09-27/. The defect-*, fixed-* and design-* pictures are history and are
not touched here.

    xvfb-run -a -s "-screen 0 1000x760x24" venv/bin/python walk_now.py pocketbook/src OUT "/home/analyst/Loan files"
    DPI=160: python3 render.py OUT/books/STAGE.xlsx OUT/r/STAGE 160          (every stage in OUT/books)
    python3 shots_now.py OUT

A ring on a workbook page is found by the words it goes round (pdftotext's word boxes), so it follows the layout;
crops are fractions of the page, as in shots.py."""
import html as entities
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1])
SH, R = OUT / "shots", OUT / "r"
RED = (204, 0, 0)
L = lambda x1, y1, x2, y2: (x1 / 720, y1 / 560, x2 / 720, y2 / 560)   # noqa: E731  launcher pixels


def page(stage: str, n: int) -> Path:
    """pdftoppm names pages p-4 or p-04, by how many there are."""
    folder = R / stage
    return next(p for p in (folder / f"p-{n}.png", folder / f"p-{n:02d}.png") if p.exists())


@lru_cache(None)
def _words(stage: str, n: int):
    html = subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), "-bbox", str(R / stage / "book.pdf"), "-"],
                          capture_output=True, text=True).stdout
    pw, ph = (float(x) for x in re.search(r'<page width="([\d.]+)" height="([\d.]+)"', html).groups())
    ws = [(float(a) / pw, float(b) / ph, float(c) / pw, float(d) / ph, entities.unescape(t)) for a, b, c, d, t in
          re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', html)]
    return ws


def find(stage: str, n: int, text: str, nth: int = 0, pad=(0.004, 0.003), below: float = 0.0) -> tuple:
    """The box round the words `text` (in order, on one line) on page n of a stage, as fractions of the page: the
    nth such run of words that starts below `below`."""
    want = text.split()
    ws = _words(stage, n)
    hits = []
    for i in range(len(ws) - len(want) + 1):
        run = ws[i:i + len(want)]
        if [w[4] for w in run] == want and run[0][1] >= below:
            hits.append(run)
    if len(hits) <= nth:
        raise SystemExit(f"not found on {stage} p{n}: {text!r}")
    run = hits[nth]
    return (min(w[0] for w in run) - pad[0], min(w[1] for w in run) - pad[1],
            max(w[2] for w in run) + pad[0], max(w[3] for w in run) + pad[1])


def span(a: tuple, b: tuple) -> tuple:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def across(box: tuple, x1: float, x2: float) -> tuple:
    """The same lines, from x1 to x2: a whole row of a table."""
    return (x1, box[1], x2, box[3])


def make(name, src, crop=None, rings=(), zoom=None, maxw=1100, rp=4):
    """rp: how far a ring stands off what it goes round, in pixels (0 in a close-set table, with a thinner line)."""
    im = Image.open(src).convert("RGB")
    w0, h0 = im.size
    d = ImageDraw.Draw(im)
    for x1, y1, x2, y2 in rings:
        d.rounded_rectangle((x1 * w0 - rp, y1 * h0 - rp, x2 * w0 + rp, y2 * h0 + rp), radius=8 if rp else 5, outline=RED,
                            width=3 if rp else 2)
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
    out.save(HERE / f"{name}.png", optimize=True)
    print(name, out.size)


if __name__ == "__main__":
    # ---- the window, first time
    make("step-01-add-ons-missing", SH / "s01-opened-addon-missing.png", rings=[L(606, 9, 706, 42)])
    make("step-02-browse", SH / "s02b-browse-typed.png", rings=[L(250, 345, 468, 372), L(470, 343, 566, 374)])
    make("step-03-installed", SH / "s04-installed.png", rings=[L(217, 277, 650, 295), L(526, 511, 701, 543)])
    # ---- where the book bleeds: the window
    make("step-04-set-up-read-the-columns", SH / "s06-choose-tests-bleed.png",
         rings=[L(441, 16, 702, 45), L(217, 438, 700, 495)])
    make("step-05-split-by-rev-debt", SH / "s07-split-rev-debt.png", rings=[L(630, 120, 690, 144), L(217, 395, 700, 495)])
    make("step-06-answer-in-the-workbook", SH / "s08-answer-in-workbook.png",
         rings=[L(217, 97, 700, 172), L(217, 180, 700, 215)])
    make("step-07-run-before-answering", SH / "s09-run-before-answering.png",
         rings=[L(217, 91, 700, 393), L(12, 216, 190, 254)])
    CONTROL = (0.06, 0.1, 0.81, 0.43)
    make("step-08-control-blank", page("01-written", 2), crop=CONTROL, maxw=1300)
    make("step-08b-worked-out", page("01-written", 2), crop=(0.45, 0.1, 0.94, 0.37),
         rings=[span(find("01-written", 2, "Worked out from the loans"), find("01-written", 2, "suggested: 65,"))])
    cols = find("01-written", 3, "Checked every column?", pad=(0.004, 0.006))
    make("step-09-columns", page("01-written", 3), crop=(0.065, 0.1, 0.62, 0.42),
         rings=[(cols[0], cols[1], find("01-written", 3, "Run won't start")[0], cols[3]),
                span(span(find("01-written", 3, "Odd values", nth=1), find("01-written", 3, "Treat as ↻")),
                     find("01-written", 3, "Negative on 595 loans"))])
    make("step-10-control-answered", page("02-answered", 2), crop=CONTROL,
         rings=[span(find("02-answered", 2, "1.34×"), find("02-answered", 2, "0.75×"))], maxw=1300)
    make("step-11-workbook-open", SH / "s11-workbook-open.png", rings=[L(217, 91, 700, 140), L(646, 511, 701, 543)])
    make("step-12-run-finished", SH / "s19-run-finished.png", rings=[L(215, 53, 530, 153), L(215, 160, 690, 210)])
    # ---- where the book bleeds: the workbook
    START = (0.07, 0.1, 0.93, 0.76)
    BLOCK = 0.697                     # the right edge of Start here's blocks
    make("step-13-start-here", page("03-run1", 1), crop=START,
         rings=[across(span(find("03-run1", 1, "Answers needed before Run"), find("03-run1", 1, "Control · Status")),
                       0.078, BLOCK),
                across(span(find("03-run1", 1, "Pockets worse and material, charge-offs"), find("03-run1", 1, "$427,896")),
                       0.078, BLOCK)])
    make("step-14-pockets", page("03-run1", 7), crop=(0.07, 0.1, 0.93, 0.66),
         rings=[span(find("03-run1", 7, "LINES IN USE NOW"), find("03-run1", 7, "Rest of its band"))])
    make("step-15-paid-cost-kept", page("03-run1", 9), crop=(0.07, 0.355, 0.93, 0.66),
         rings=[across(span(find("03-run1", 9, "Net drain", pad=(0, 0)),
                            find("03-run1", 9, "Losing more, profit holding", pad=(0, 0))), 0.072, 0.62)])
    make("step-16-grids", page("06-run2", 10), crop=(0.07, 0.1, 0.93, 0.53))
    bad = find("03-run1", 11, "Bad loans", below=0.47)
    make("step-17-split", page("03-run1", 11), crop=(0.07, 0.1, 0.93, 0.78),
         rings=[across(bad, 0.074, 0.745), find("03-run1", 11, "Holds FICO fixed", pad=(0.03, 0.006))])
    make("step-18-record", page("03-run1", 12), crop=(0.06, 0.1, 0.94, 0.62),
         zoom=(0.065, find("03-run1", 12, "Does it add up")[1] - 0.005, 0.5,
               find("03-run1", 12, "Loans needed for a 1.34x gap: Charge-offs")[3] + 0.004))
    make("step-19-live-change-start-here", page("04-live", 1), crop=START,
         rings=[across(span(find("04-live", 1, "Pockets worse and material, charge-offs"), find("04-live", 1, "$427,896")),
                       0.078, BLOCK)])
    top = find("04-live", 7, "LINES IN USE NOW")[1] - 0.012
    worse = find("04-live", 7, "Worse?", below=0.4)
    make("step-19b-live-change-pockets", page("04-live", 7), crop=(0.07, top, 0.93, 0.66),
         rings=[find("04-live", 7, "2.00×", pad=(0.03, 0.02)), (worse[0] - 0.02, worse[1], worse[2] + 0.02, 0.66)])
    make("step-20-waiting-for-a-run", page("05-pending", 1), crop=(0.07, 0.1, 0.93, 0.62),
         rings=[span(find("05-pending", 1, "Changes waiting for a Run"), find("05-pending", 1, "Control · Status")),
                across(span(find("05-pending", 1, "1 change is waiting"), find("05-pending", 1, "Save, close, and press Run")),
                       0.075, 0.924)])
    need = find("05-pending", 2, "Needs a Run · takes effect when you press Run again")
    make("step-20b-control-status", page("05-pending", 2), crop=(0.06, need[1] - 0.004, 0.795, 0.435),
         rings=[find("05-pending", 2, "Waiting for a Run", pad=(0.008, 0.001)),
                span(find("05-pending", 2, "Same as last Run", nth=5), find("05-pending", 2, "Same as last Run", nth=10))],
         maxw=1300)
    make("step-21-run-again", SH / "s20-run-again.png", rings=[L(215, 53, 530, 153)])
    # ---- test new variables
    make("step-22-test-new-variables", SH / "s22-test-new-variables.png",
         rings=[L(582, 16, 702, 45), L(561, 365, 701, 396), L(217, 405, 700, 502)])
    make("step-23-scikit-learn-installed", SH / "s23b-sklearn-installed.png", rings=[L(217, 405, 700, 500)])
    make("step-24-candidates", SH / "s24-candidates-ticked.png", rings=[L(540, 75, 702, 195), L(217, 378, 700, 500)])
    make("step-25-answer-new", SH / "s25-answer-new.png", rings=[L(217, 93, 700, 110)])
    make("step-25b-start-here-waits", page("07-new-written", 1), crop=(0.07, 0.1, 0.93, 0.45),
         rings=[span(find("07-new-written", 1, "Changes waiting for a Run"), find("07-new-written", 1, "Control · Status")),
                across(span(find("07-new-written", 1, "1 change is waiting"), find("07-new-written", 1, "Save, close, and press Run")),
                       0.075, 0.924)])
    what = find("07-new-written", 2, "What are you running?", pad=(0, 0.0015))
    make("step-26-control-new-variable", page("07-new-written", 2), crop=(0.06, 0.1, 0.785, 0.5),
         rings=[across(what, 0.064, 0.78)], maxw=1300, rp=0)
    make("step-27-scouting-finished", SH / "s26-scout-finished.png", rings=[L(215, 53, 690, 178), L(215, 183, 690, 232)])
    make("step-28-start-here-new", page("08-scout", 1), crop=(0.07, 0.1, 0.93, 0.63),
         rings=[across(find("08-scout", 1, "15,000 - 48,522"), 0.076, 0.92)])
    make("step-29-scouting", page("08-scout", 6), crop=(0.06, 0.1, 0.94, 0.85),
         rings=[span(find("08-scout", 6, "Candidate", below=0.6), find("08-scout", 6, "below the noise floor"))
                [:2] + (0.94 - 0.003, find("08-scout", 6, "below the noise floor")[3])])
    make("step-29b-the-pre-spec", page("08-scout", 7), crop=(0.06, 0.1, 0.94, 0.77))
    tested = find("08-scout", 8, "WHAT WAS TESTED")
    make("step-30-new-variables", page("08-scout", 8), crop=(0.06, tested[1] - 0.012, 0.94, 0.83),
         rings=[across(find("08-scout", 8, "15,000 - 48,522 vs 11,000 - 14,999"), 0.065, 0.905)])
    make("step-31-record-new", page("08-scout", 10), crop=(0.06, 0.1, 0.5, 0.66),
         rings=[across(find("08-scout", 10, "Pre-spec fingerprint", pad=(0, 0.0015)), 0.066, 0.5),
                across(find("08-scout", 10, "Runs that touched the holdout", pad=(0, 0.0015)), 0.066, 0.5)], rp=0)
    make("step-32-run-after-edit", SH / "s27-edited-prespec-run.png", rings=[L(535, 53, 690, 178), L(215, 185, 690, 250)])
    make("step-33-record-changed", page("09-edited", 10), crop=(0.06, 0.1, 0.5, 0.72),
         rings=[(0.066, find("09-edited", 10, "Warning", nth=1)[1] - 0.0015, 0.5,
                 find("09-edited", 10, "fingerprint b98435f2c897 then,")[3] + 0.002)], rp=0)
    make("step-34-run-stopped", SH / "d-tieout-fails.png", rings=[L(215, 18, 702, 196)])
