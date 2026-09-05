"""A strip of the filed page for every code the workbook's provenance cites.

The rule this serves: the source has to be photographed and the figure located
on it, precisely enough that a reader can put a finger on the same one. So each
strip is a horizontal slice of the bank's own Call Report facsimile, cut around
the row that carries the MDRM code, at the page and position where it actually
sits -- with the code and the number both in the picture.

Where a line is a quarterly flow, two strips are cut: the same code on the June
filing and on the March one, because the quarter is the difference between them
and a reader has to see both halves of that subtraction.

If a code cannot be found on the filing, that is recorded as not found. It is
never quietly dropped, because a missing strip and a strip nobody looked for are
indistinguishable in a finished document.
"""
import json
import pathlib
import re
import sys

import pymupdf

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
BANKS = SB / "banks"
OUT = SB / "bankstrips"
OUT.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

Q2, Q1 = "2026-06-30", "2026-03-31"
CODE = re.compile(r"[A-Z]{4}[A-Z0-9]{4}")


def codes_in(expr):
    """Every MDRM code an expression cites, in the order it cites them."""
    return [c for c in CODE.findall(expr or "")]


def cut(doc, code, tag):
    """One strip: the row carrying `code`, with its number, as filed."""
    for pno in range(doc.page_count):
        page = doc[pno]
        words = page.get_text("words")
        hit = next((w for w in words if w[4] == code), None)
        if hit is None:
            continue
        band = sorted([w for w in words if abs(w[1] - hit[1]) < 7],
                      key=lambda w: w[0])
        text = " ".join(w[4] for w in band)
        top = min(w[1] for w in band) - 5
        bottom = max(w[3] for w in band) + 5
        clip = pymupdf.Rect(page.rect.x0 + 2, max(page.rect.y0, top),
                            page.rect.x1 - 2, min(page.rect.y1, bottom))
        png = OUT / ("%s.png" % tag)
        page.get_pixmap(matrix=pymupdf.Matrix(2.6, 2.6), clip=clip).save(png)
        nums = [w[4] for w in band
                if re.fullmatch(r"-?[\d,]+(\.\d+)?", w[4].replace("%", ""))]
        return {"code": code, "page": pno + 1, "png": png.name,
                "row": text[:300], "numbers": nums[-3:]}
    return {"code": code, "page": None, "png": None,
            "row": "", "numbers": [], "why": "not found in this filing"}


rosters = json.loads((SB / "bank_rosters.json").read_text())
index = {e["cert"]: e for e in json.loads((BANKS / "index.json").read_text())}

manifest = {}
made = missing = 0
for bank in rosters:
    cert = bank["cert"]
    entry = index[cert]
    docs = {}
    for iso in (Q2, Q1):
        name = entry["filings"][iso]["pdf"]
        docs[iso] = pymupdf.open(BANKS / name) if name else None
    per_bank = {}
    for line in bank["lines"]:
        if line["note"]:
            continue
        field = line["field"]
        expr = line["used"] or ""
        is_flow = "minus the same at" in expr
        want = codes_in(expr)
        comps = []
        quarters = (Q2, Q1) if is_flow else (Q2,)
        for iso in quarters:
            doc = docs.get(iso)
            if doc is None:
                comps.append({"code": None, "quarter": iso, "png": None,
                              "why": "no facsimile for this quarter"})
                continue
            for code in want:
                tag = "%s-%s-%s-%s" % (cert, field, iso.replace("-", ""), code)
                got = cut(doc, code, tag)
                got["quarter"] = iso
                comps.append(got)
                if got["png"]:
                    made += 1
                else:
                    missing += 1
        per_bank[field] = comps
    for doc in docs.values():
        if doc is not None:
            doc.close()
    found = sum(1 for cs in per_bank.values() for c in cs if c.get("png"))
    absent = sum(1 for cs in per_bank.values() for c in cs if not c.get("png"))
    manifest[cert] = per_bank
    print("%-8s %-26s %4d strips, %d code(s) not found on the filing"
          % (cert, bank["name"][:26], found, absent))

(SB / "bank_strips.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print("\n%d strips cut, %d codes not found" % (made, missing))
