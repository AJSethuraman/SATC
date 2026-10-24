"""Cut the ringed row out of each capture and enlarge it, so a reader can read
the digits without leaning in.

    cd docs/tie-out/1099-nec-threshold-2026-09-07 && python make-crops.py

The crops are not new evidence -- each one is a rectangle out of the full-page
capture sitting beside it in the exhibit, at 2.2x. The full page is what proves
the row is where it is said to be; the crop only makes it legible.
"""
import pathlib

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
SCALE = 2.2

# (source, output, box) -- box is (left, top, right, bottom) in the capture's
# own pixels, read off the ringed region of each screenshot.
CROPS = [
    ("01-ours-satcllp-business-records.jpg", "01-crop-ours.png", (24, 540, 648, 660)),
    ("02-irs-i1099mec-whats-new.jpg",        "02-crop-whats-new.png", (4, 978, 700, 1064)),
    ("03-irs-i1099mec-specific-instructions.jpg", "03-crop-who-must-file.png", (4, 540, 726, 672)),
    ("04-usc-6041a-cornell.jpg",             "04-crop-6041a.png", (64, 496, 690, 536)),
    ("05-usc-6041-olrc-amendments.jpg",      "05-crop-amendments.png", (8, 604, 728, 672)),
    ("05-usc-6041-olrc-amendments.jpg",      "05b-crop-inflation.png", (8, 222, 728, 320)),
    ("06-irs-i1099gi-furnish-date.jpg",      "06-crop-furnish.png", (34, 556, 648, 592)),
    ("06-irs-i1099gi-furnish-date.jpg",      "06b-crop-weekend-rule.png", (14, 692, 712, 762)),
]

for src, out, box in CROPS:
    im = Image.open(HERE / src)
    box = (max(0, box[0]), max(0, box[1]), min(im.width, box[2]), min(im.height, box[3]))
    crop = im.crop(box)
    w, h = crop.size
    crop = crop.resize((int(w * SCALE), int(h * SCALE)), Image.LANCZOS)
    crop.save(HERE / out)
    print(f"{out:34} {box}  ->  {crop.width}x{crop.height}")
