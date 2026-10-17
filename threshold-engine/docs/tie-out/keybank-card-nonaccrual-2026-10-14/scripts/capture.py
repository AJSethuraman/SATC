"""Photograph the filed Call Report: cut the identity header, the column
headings and the row out of the real page, enlarge them, and ring the figure
in red. Also a whole-page view with the row boxed, so the cut can be found.

    (from threshold-engine/)
    python docs/tie-out/keybank-card-nonaccrual-2026-10-14/scripts/capture.py \
        --pdf work/nac-sources/call-17534-06302026.pdf \
        --out docs/tie-out/keybank-card-nonaccrual-2026-10-14/images

The comparability tie-out's capture.py does this with pdftoppm and pdfplumber.
Neither is on this machine; PyMuPDF is, and does both jobs: it renders the
page and reports where each word sits, so a ring lands on the word the PDF
itself holds at that place, never on a guessed coordinate.
"""
import argparse
import io
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

DPI = 200
K = DPI / 72.0
RED = (214, 0, 0)


def words_of(page):
    return [dict(x0=w[0], top=w[1], x1=w[2], bottom=w[3], text=w[4]) for w in page.get_text("words")]


def find_page(doc, must):
    hits = [i for i, p in enumerate(doc) if all(m in p.get_text() for m in must)]
    if len(hits) != 1:
        raise SystemExit("expected one page holding all of %s, found %d" % (must, len(hits)))
    return hits[0]


def phrase_box(words, phrase, after=None):
    """Bounding box of a run of consecutive words equal to ``phrase``."""
    toks = phrase.split()

    def same(w, t):
        # The forms run dot leaders into the last word: "cards......." is "cards".
        return w == t or (w.startswith(t) and set(w[len(t):]) <= set(".:,;*"))
    for i in range(len(words) - len(toks) + 1):
        if all(same(words[i + k]["text"], toks[k]) for k in range(len(toks))):
            if after is not None and words[i]["top"] < after:
                continue
            ws = words[i:i + len(toks)]
            return dict(x0=min(w["x0"] for w in ws), x1=max(w["x1"] for w in ws),
                        top=min(w["top"] for w in ws), bottom=max(w["bottom"] for w in ws))
    raise SystemExit("phrase %r not found" % phrase)


def value_after(words, code):
    """The first number to the right of ``code`` on its own line."""
    cs = [w for w in words if w["text"] == code]
    if len(cs) != 1:
        raise SystemExit("code %s appears %d times on the page" % (code, len(cs)))
    c = cs[0]
    mid = (c["top"] + c["bottom"]) / 2
    cands = [w for w in words if w["x0"] > c["x1"] and abs((w["top"] + w["bottom"]) / 2 - mid) < 4
             and re.fullmatch(r"\(?-?[\d,]+\)?|NR", w["text"])]
    if not cands:
        raise SystemExit("no value after %s" % code)
    return c, min(cands, key=lambda w: w["x0"])


def cut(page, top, bottom, x0=None, x1=None):
    r = page.rect
    clip = pymupdf.Rect(r.x0 if x0 is None else x0, top, r.x1 if x1 is None else x1, bottom)
    pix = page.get_pixmap(dpi=DPI, clip=clip)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"), clip


def ring(img, clip, box, pad=3, width=5):
    d = ImageDraw.Draw(img)
    x0, y0 = (box["x0"] - clip.x0 - pad) * K, (box["top"] - clip.y0 - pad) * K
    x1, y1 = (box["x1"] - clip.x0 + pad) * K, (box["bottom"] - clip.y0 + pad) * K
    d.ellipse((x0 - 8, y0 - 3, x1 + 8, y1 + 3), outline=RED, width=width)


def stack(parts, gap=10):
    w = max(p.width for p in parts)
    out = Image.new("RGB", (w, sum(p.height for p in parts) + gap * (len(parts) - 1)), "white")
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height + gap
    return out


def shot(doc, must, out, name, column_band, row_band, ring_codes, ring_phrases=()):
    """Header, column headings and row, each cut from the page and stacked;
    the value after each of ``ring_codes`` ringed, and each of ``ring_phrases``
    (a column heading) ringed too. Returns the values read off the page."""
    i = find_page(doc, must)
    page = doc[i]
    ws = words_of(page)
    r = phrase_box(ws, "RSSD-ID")
    hdr, _ = cut(page, r["top"] - 14, r["bottom"] + 14)
    parts, read = [hdr], {}
    for a, b in (column_band, row_band):
        t = phrase_box(ws, a)
        btm = phrase_box(ws, b, after=t["top"])
        top, bottom = t["top"] - 4, btm["bottom"] + 4
        piece, clip = cut(page, top, bottom)
        for code in ring_codes:
            c, v = value_after(ws, code)
            if top <= v["top"] and v["bottom"] <= bottom:
                ring(piece, clip, v)
                read[code] = v["text"]
        for ph in ring_phrases:
            try:
                bx = phrase_box(ws, ph, after=top - 1)
            except SystemExit:
                continue
            if bx["bottom"] <= bottom:
                ring(piece, clip, bx, pad=2, width=4)
        parts.append(piece)
    im = stack(parts)
    im.save(Path(out) / (name + ".png"), optimize=True)

    # the whole page, small, with the row boxed in red, so the cut can be found on it
    t = phrase_box(ws, row_band[0])
    btm = phrase_box(ws, row_band[1], after=t["top"])
    full = Image.open(io.BytesIO(page.get_pixmap(dpi=72).tobytes("png"))).convert("RGB")
    d = ImageDraw.Draw(full)
    d.rectangle((20, t["top"] - 4, full.width - 20, btm["bottom"] + 4), outline=RED, width=3)
    full.save(Path(out) / (name + "-page.png"), optimize=True)
    missing = set(ring_codes) - set(read)
    if missing:
        raise SystemExit("%s: could not ring %s" % (name, sorted(missing)))
    print("wrote %s.png (pdf page %d of %d, %dx%d) read %s" % (name, i + 1, doc.page_count, im.width, im.height, read))
    return dict(pdf_page=i + 1, read=read)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="the filed Call Report PDF, call-17534-06302026.pdf")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(a.pdf)
    got = {}
    got["rcn"] = shot(doc, ["RCFDB577", "RCFDB576"], a.out, "source-rcn-5a",
                      ("(Column A) Past due 30", "Dollar amounts in thousands"),
                      ("5. Loans to individuals for household", "a. Credit cards"),
                      ["RCFDB577"], ["(Column C) Nonaccrual"])
    got["rcc"] = shot(doc, ["RCFDB538", "RCFDK207"], a.out, "source-rcc-6a",
                      ("(Column A) Consolidated Bank", "(Column B) Domestic Offices"),
                      ("6. Loans to individuals for household", "a. Credit cards"),
                      ["RCFDB538"], ["(Column A) Consolidated Bank"])
    # the cover: whose report, which form, which date, which FDIC certificate
    cover = doc[0]
    ws = words_of(cover)
    top = phrase_box(ws, "Consolidated Reports of Condition")["top"] - 6
    bottom = phrase_box(ws, "Last updated on")["bottom"] + 6
    im, clip = cut(cover, top, bottom)
    for ph, after in (("KEYBANK NATIONAL ASSOCIATION", None), ("6/30/2026", None), ("17534", None)):
        ring(im, clip, phrase_box(ws, ph, after=after), pad=2, width=4)
    im.save(Path(a.out) / "source-cover.png", optimize=True)
    print("read off the pages:", got)
    return 0


if __name__ == "__main__":
    sys.exit(main())
