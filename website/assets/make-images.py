#!/usr/bin/env python3
"""Generate branded raster images for the SATC site (og-image, apple-touch-icon).

UPDATED for the restyle: the Notch mark, cool palette, sans wordmark.
Replaces website/assets/make-images.py.

Run from anywhere:  python3 website/assets/make-images.py
Outputs:  website/og-image.png (1200x630)  and  website/apple-touch-icon.png (180x180)

Pure Pillow. Tries IBM Plex Sans first (to match the site) and falls back to the
system DejaVu fonts, so it still re-runs anywhere with `pip install Pillow`.
To get exact Plex output, install the family or point PLEX_* at your .ttf files.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent  # the website/ folder

# ---- restyle palette (was: NAVY 11,31,58 / GOLD 176,141,87 / CREAM 247,245,240)
NAVY    = (19, 36, 55)     # #132437
OXBLOOD = (106, 40, 51)    # #6A2833
GOLD    = (192, 162, 101)  # #C0A265
WHITE   = (255, 255, 255)
SHELL   = (247, 247, 245)  # #F7F7F5

# ---- fonts: prefer IBM Plex Sans, fall back to DejaVu -----------------------
PLEX_SANS      = "/usr/share/fonts/truetype/plex/IBMPlexSans-Regular.ttf"
PLEX_SANS_BOLD = "/usr/share/fonts/truetype/plex/IBMPlexSans-SemiBold.ttf"
PLEX_MONO      = "/usr/share/fonts/truetype/plex/IBMPlexMono-Regular.ttf"
DEJA_SANS      = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJA_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SANS      = PLEX_SANS if Path(PLEX_SANS).exists() else DEJA_SANS
SANS_BOLD = PLEX_SANS_BOLD if Path(PLEX_SANS_BOLD).exists() else DEJA_SANS_BOLD
MONO      = PLEX_MONO if Path(PLEX_MONO).exists() else DEJA_SANS


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


def wordmark(draw, cx, y, size, ink, square):
    """SAT[square]C LLP, centered on cx, drawn from the top at y.

    The proportions come straight from the CSS in the mark spec, with the
    font-size standing in for the em: square 0.3em, 0.18em either side of it,
    LLP set 0.22em after the C at a lighter weight. The square sits 0.2em above
    the baseline so it reads at hyphen height rather than as a full stop.
    """
    bold = font(SANS_BOLD, size)
    med = font(SANS, size)
    sq, pad, llp_gap = 0.30 * size, 0.18 * size, 0.22 * size

    w_sat = draw.textlength("SAT", font=bold)
    w_c = draw.textlength("C", font=bold)
    w_llp = draw.textlength("LLP", font=med)
    total = w_sat + pad + sq + pad + w_c + llp_gap + w_llp

    # Cap bottom of the bold face, so the square lines up with real letterforms
    # rather than with the font's full em box.
    cap_bottom = draw.textbbox((0, 0), "SATC", font=bold)[3]

    x = cx - total / 2
    draw.text((x, y), "SAT", font=bold, fill=ink)
    x += w_sat + pad
    sq_bottom = y + cap_bottom - 0.20 * size
    draw.rectangle([x, sq_bottom - sq, x + sq, sq_bottom], fill=square)
    x += sq + pad
    draw.text((x, y), "C", font=bold, fill=ink)
    x += w_c + llp_gap
    draw.text((x, y), "LLP", font=med, fill=ink)


def mark(draw, x, y, size, outer=WHITE, inner=GOLD):
    """The Notch mark. (x, y) is the top-left of the whole footprint.

    Proportions are lifted from the SVG in index.html so raster and vector
    agree exactly:
        viewBox 32 · outline path M3 3 H19 V11 H11 V19 H3 Z · piece 22,22 8x8
    which normalises to a 27-unit footprint (3 → 30).

    The notch and the piece are both 8x8 — the piece fits the hole it came
    from. Do not change one without the other.
    """
    k = size / 27
    w = max(2, round(2.4 * k))
    # the notched outline, drawn as a closed polyline
    pts = [(3, 3), (19, 3), (19, 11), (11, 11), (11, 19), (3, 19)]
    poly = [(x + (a - 3) * k, y + (b - 3) * k) for a, b in pts]
    draw.line(poly + [poly[0]], fill=outer, width=w, joint="curve")
    # the removed piece, set beside it
    draw.rectangle([x + 19 * k, y + 19 * k, x + 27 * k, y + 27 * k], fill=inner)


def make_og():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # decorative OFFSET SQUARES, upper-right (was: concentric circles).
    # Echoes the mark and matches the .hero::before/::after squares in the CSS.
    for off, a in ((0, 0.15), (150, 0.09)):
        x0 = W - 470 + off
        y0 = -190 + off
        d.rectangle([x0, y0, x0 + 430, y0 + 430],
                    outline=blend(GOLD, NAVY, a), width=2)

    mark(d, W // 2 - 58, 116, 116, outer=WHITE, inner=GOLD)

    # The wordmark, not the firm name in full — the descriptor carries that.
    # On navy the hyphen square goes gold, matching .lockup.on-dark .wm .hy.
    wordmark(d, W // 2, 274, 88, ink=WHITE, square=GOLD)
    draw_tracked(d, W // 2, 392, "SETHURAMAN ACCOUNTING, TAX & CONSULTING",
                 font(MONO, 20), GOLD, tracking=3)
    draw_centered(d, W // 2, 452, "Everything you need, from one desk.",
                  font(SANS, 32), blend(SHELL, NAVY, 0.74))

    # gold hairline + url
    d.line([(W // 2 - 60, 534), (W // 2 + 60, 534)], fill=GOLD, width=1)
    draw_tracked(d, W // 2, 552, "SATCLLP.COM", font(MONO, 19), GOLD, tracking=4)

    img.save(OUT / "og-image.png")
    print("wrote", OUT / "og-image.png")


def make_icon():
    S = 180
    img = Image.new("RGB", (S, S), NAVY)
    d = ImageDraw.Draw(img)
    fp = 104                      # mark footprint, leaves even padding
    mark(d, (S - fp) // 2, (S - fp) // 2, fp, outer=WHITE, inner=GOLD)
    img.save(OUT / "apple-touch-icon.png")
    print("wrote", OUT / "apple-touch-icon.png")


if __name__ == "__main__":
    make_og()
    make_icon()
