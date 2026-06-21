#!/usr/bin/env python3
"""Generate branded raster images for the SATC site (og-image, apple-touch-icon).

Run from anywhere:  python3 website/assets/make-images.py
Outputs:  website/og-image.png (1200x630)  and  website/apple-touch-icon.png (180x180)

Pure Pillow + the system DejaVu fonts, so it re-runs anywhere with `pip install Pillow`.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent  # the website/ folder

NAVY        = (11, 31, 58)
GOLD        = (176, 141, 87)
GOLD_LIGHT  = (212, 185, 126)
CREAM       = (247, 245, 240)

SERIF      = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS       = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def blend(fg, bg, a):
    return tuple(round(b * (1 - a) + f * a) for f, b in zip(fg, bg))


def text_w(draw, s, fnt, tracking=0):
    w = draw.textlength(s, font=fnt)
    if tracking:
        w += tracking * max(len(s) - 1, 0)
    return w


def draw_tracked(draw, cx, y, s, fnt, fill, tracking):
    """Draw letter-spaced text horizontally centered on cx."""
    total = text_w(draw, s, fnt, tracking)
    x = cx - total / 2
    for ch in s:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def draw_centered(draw, cx, y, s, fnt, fill):
    draw.text((cx - draw.textlength(s, font=fnt) / 2, y), s, font=fnt, fill=fill)


def seal(draw, cx, cy, r):
    """The gold-ringed 'S' monogram."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NAVY,
                 outline=GOLD, width=max(2, r // 18))
    ir = int(r * 0.74)
    draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], outline=GOLD, width=1)
    f = font(SERIF, int(r * 1.5))
    b = draw.textbbox((0, 0), "S", font=f)
    draw.text((cx - (b[2] - b[0]) / 2 - b[0], cy - (b[3] - b[1]) / 2 - b[1]),
              "S", font=f, fill=GOLD_LIGHT)


def make_og():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # decorative concentric rings, upper-right (dim gold over navy)
    for rr, a in ((430, 0.14), (330, 0.10), (230, 0.07)):
        d.ellipse([W - 250 - rr, -250 - rr, W - 250 + rr, -250 + rr],
                  outline=blend(GOLD, NAVY, a), width=2)

    seal(d, W // 2, 188, 78)

    draw_centered(d, W // 2, 300, "Sethuraman", font(SERIF, 92), CREAM)
    draw_tracked(d, W // 2, 410, "ACCOUNTING  ·  TAX  ·  CONSULTING",
                 font(SANS, 26), GOLD_LIGHT, tracking=6)
    draw_centered(d, W // 2, 470, "Clarity in complexity.", font(SERIF, 34),
                  blend(CREAM, NAVY, 0.82))

    # gold hairline + url
    d.line([(W // 2 - 70, 540), (W // 2 + 70, 540)], fill=GOLD, width=2)
    draw_tracked(d, W // 2, 558, "SATCLLP.COM", font(SANS, 20), GOLD, tracking=5)

    img.save(OUT / "og-image.png")
    print("wrote", OUT / "og-image.png")


def make_icon():
    S = 180
    img = Image.new("RGB", (S, S), NAVY)
    d = ImageDraw.Draw(img)
    seal(d, S // 2, S // 2, 78)
    img.save(OUT / "apple-touch-icon.png")
    print("wrote", OUT / "apple-touch-icon.png")


if __name__ == "__main__":
    make_og()
    make_icon()
