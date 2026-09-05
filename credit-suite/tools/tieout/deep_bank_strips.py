"""Photograph the cited row of every filed page, in every quarter of ten years.

The firm's reason for wanting this, in their words: "i want the screenshot
method used for those quarters ... it's the only way i feel like i have been
able to trust this sort of audit."

So: twelve banks, forty quarters, every field whose provenance names a line on
the form. Each one becomes two pictures --

    the PAGE HEADER   the bank's name, the form, and the period, so "same
                      entity, same date" is read off the photograph instead of
                      taken on trust
    the ROW           the line carrying the code, with its number in the shot

-- and the row's text is recorded beside them, so the document can say what the
row said as well as show it.

A code that is not on the filing is written down as not found. A missing strip
and a strip nobody looked for are indistinguishable in a finished document, and
only one of them is honest.

Each PDF is indexed ONCE. The sixteen-quarter version scanned every page for
every code, which is 68 passes over an eighty-page document; at 480 documents
that is most of a day. One pass builds the whole map.
"""
import json
import pathlib
import re
import sys
import time

import pymupdf

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
BANKS = SB / "banks"
OUT = SB / "deepstrips"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import provenance_seed as PS       # noqa: E402

CODE = re.compile(r"[A-Z]{4}[A-Z0-9]{4}|(?<![A-Z0-9])[A-Z][0-9]{3}(?![0-9])")
NUM = re.compile(r"-?[\d,]+(\.\d+)?")

only = [a for a in sys.argv[1:] if a.isdigit()]
index = json.loads((BANKS / "index.json").read_text())
quarters = json.loads((SB / "deep" / "deep_quarters.json").read_text())
rows = json.loads((SB / "bank_deep_rows.json").read_text())

#: Only the fields whose verdict says they were compared against a filed line.
#: A ratio the FDIC computes has no row to photograph, and a quarter that spans
#: a merger has two filings behind it rather than one line.
WANTED = {}
for r in rows:
    if r["verdict"] != "TIES":
        continue
    WANTED.setdefault((r["cert"], r["repdte"]), {})[r["field"]] = r["cited"]


def index_document(doc):
    """{code: (page number, the words on its row)} in one pass over the file."""
    found = {}
    for pno in range(doc.page_count):
        words = doc[pno].get_text("words")
        for w in words:
            token = w[4]
            if token in found or not CODE.fullmatch(token):
                continue
            band = sorted([x for x in words if abs(x[1] - w[1]) < 7],
                          key=lambda x: x[0])
            found[token] = (pno, band)
    return found


def save_header(doc, pno, tag):
    """The top of the page: whose filing this is, which form, which period."""
    png = OUT / ("hdr-%s-p%d.png" % (tag, pno + 1))
    if not png.exists():
        page = doc[pno]
        clip = pymupdf.Rect(page.rect.x0, page.rect.y0,
                            page.rect.x1, page.rect.y0 + 96)
        page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0), clip=clip).save(png)
    return png.name


started = time.time()
manifest = {}
cut = notfound = 0
for entry in index:
    cert, name = entry["cert"], entry["name"]
    if only and cert not in only:
        continue
    per_bank = {}
    for iso in quarters:
        want = WANTED.get((cert, iso))
        if not want:
            continue
        mmddyyyy = iso[5:7] + iso[8:10] + iso[:4]
        pdf = BANKS / ("filing-%s-%s.pdf" % (cert, mmddyyyy))
        if not pdf.exists():
            per_bank[iso] = {"_why": "no facsimile PDF for this quarter"}
            continue
        doc = pymupdf.open(pdf)
        codes = index_document(doc)
        shots = {}
        for field, expr in sorted(want.items()):
            comps = []
            for code in CODE.findall(expr or ""):
                hit = codes.get(code)
                if hit is None:
                    comps.append({"code": code, "why": "not on this filing"})
                    notfound += 1
                    continue
                pno, band = hit
                page = doc[pno]
                top = min(w[1] for w in band) - 5
                bottom = max(w[3] for w in band) + 5
                clip = pymupdf.Rect(page.rect.x0 + 2, max(page.rect.y0, top),
                                    page.rect.x1 - 2, min(page.rect.y1, bottom))
                png = OUT / ("%s-%s-%s.png" % (cert, mmddyyyy, code))
                if not png.exists():
                    page.get_pixmap(matrix=pymupdf.Matrix(2.6, 2.6),
                                    clip=clip).save(png)
                text = " ".join(w[4] for w in band)
                comps.append({
                    "code": code, "page": pno + 1, "png": png.name,
                    "header": save_header(doc, pno, "%s-%s" % (cert, mmddyyyy)),
                    "row": text[:300],
                    "numbers": [w[4] for w in band
                                if NUM.fullmatch(w[4].replace("%", ""))][-3:]})
                cut += 1
            shots[field] = comps
        per_bank[iso] = shots
        doc.close()
    manifest[cert] = per_bank
    done = sum(1 for q in per_bank.values() if "_why" not in q)
    print("  %-26s %2d quarters photographed, %5d strips so far, %.0fs"
          % (name[:26], done, cut, time.time() - started), flush=True)

path = SB / ("deep_strips%s.json" % ("-" + "-".join(only) if only else ""))
path.write_text(json.dumps(manifest), encoding="utf-8")
print("\nstrips cut          : %d" % cut)
print("codes not on filing : %d" % notfound)
print("wrote %s" % path.name)
