"""Mark a screenshot to its step: ring what the step is about, add a zoomed crop underneath.

  python3 annot.py OUT IMG [--crop x1,y1,x2,y2] [--ring x1,y1,x2,y2]... [--zoom x1,y1,x2,y2] [--hi HI_IMG]

Boxes are fractions of the whole image; --crop trims the main picture last. --zoom takes its crop from HI_IMG (a higher-resolution
render of the same page) when given, else from IMG, and places it under the full picture.
"""
import argparse
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("img")
ap.add_argument("--crop"); ap.add_argument("--ring", action="append", default=[])
ap.add_argument("--zoom"); ap.add_argument("--hi")
a = ap.parse_args()
f = lambda s: [float(x) for x in s.split(",")]
im = Image.open(a.img).convert("RGB")
hi = Image.open(a.hi).convert("RGB") if a.hi else im.copy()
W, H = im.size
d = ImageDraw.Draw(im)
for r in a.ring:
    x1, y1, x2, y2 = f(r)
    d.rounded_rectangle((x1 * W - 4, y1 * H - 4, x2 * W + 4, y2 * H + 4), radius=8, outline=(204, 0, 0), width=3)
if a.crop:                      # all boxes are fractions of the whole picture; the crop comes last
    c = f(a.crop)
    im = im.crop((int(c[0] * W), int(c[1] * H), int(c[2] * W), int(c[3] * H)))
W, H = im.size
parts = [im]
if a.zoom:
    x1, y1, x2, y2 = f(a.zoom)
    Wh, Hh = hi.size
    z = hi.crop((int(x1 * Wh), int(y1 * Hh), int(x2 * Wh), int(y2 * Hh)))
    scale = min(W / z.width, 2.5)
    z = z.resize((int(z.width * scale), int(z.height * scale)), Image.LANCZOS)
    parts.append(z)
out = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts) + 12 * (len(parts) - 1)), "white")
y = 0
for i, p in enumerate(parts):
    out.paste(p, (0, y))
    if i:
        ImageDraw.Draw(out).rectangle((0, y - 1, p.width - 1, y + p.height - 1), outline=(204, 0, 0), width=2)
    y += p.height + 12
out.save(a.out)
