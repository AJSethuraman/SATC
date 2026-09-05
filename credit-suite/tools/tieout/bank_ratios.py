"""Read the two filed capital ratios off each bank's facsimile.

They are absent from the parsed XBRL and printed on the form, so this reads the
form -- which is the document the regulator serves and the one a reviewer would
open. Run under the venv that has PyMuPDF; the roster builder reads the JSON.

The MDRM prefix is RCFA on form 031 (consolidated, foreign offices) and RCOA on
041, so the match is on the caption plus the code's last four digits. That makes
the rule work for a filer of either form rather than for the twelve banks that
happen to be in this workbook.

A blank is a real answer, not a zero: a bank electing the community-bank
leverage ratio files no total capital ratio at all.
"""
import json
import pathlib
import re
import sys

import pymupdf

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
BANKS = SB / "banks"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

WANTED = {
    "RBC1AAJ": (r"31\. Leverage ratio", "7204", "Tier 1 leverage ratio"),
    "RBCRWAJ": (r"5\d\. Total capital ratio", "7205", "Total capital ratio"),
}


def read_ratio(doc, caption_rx, tail):
    """Every column of a filed ratio row, plus the one that binds.

    An advanced-approaches institution that has exited parallel run files the
    ratio twice -- Column A on the standardized calculation, Column B on the
    advanced one -- and must meet the LOWER of the two. That lower figure is
    what the FDIC publishes. Banks not subject to it print "NR" in Column B,
    so for them there is one column and nothing changes.
    """
    rx = re.compile(caption_rx)
    for pno in range(doc.page_count):
        page = doc[pno]
        if not rx.search(page.get_text()):
            continue
        words = page.get_text("words")
        anchors = [w for w in words if re.fullmatch(r"RC[A-Z][AW]" + tail, w[4])]
        if not anchors:
            continue
        band = sorted([x for x in words if abs(x[1] - anchors[0][1]) < 6],
                      key=lambda x: x[0])
        row_text = " ".join(x[4] for x in band)
        columns = []
        for a in sorted(anchors, key=lambda x: x[0]):
            after = [x for x in band if x[0] > a[0]]
            value = None
            for x in after:
                if re.fullmatch(r"RC[A-Z][AW]" + tail, x[4]):
                    break
                m = re.fullmatch(r"(-?[\d,]+\.\d+)%?", x[4])
                if m:
                    value = float(m.group(1).replace(",", ""))
                    break
                if x[4] in ("NR", "N/R"):
                    break
            columns.append({"code": a[4], "value": value})
        reported = [c for c in columns if c["value"] is not None]
        if not reported:
            return {"value": None, "code": columns[0]["code"], "page": pno + 1,
                    "row": row_text[:300], "columns": columns,
                    "why": "the row is on the form with no percentage in any column"}
        binding = min(reported, key=lambda c: c["value"])
        return {"value": binding["value"], "code": binding["code"],
                "page": pno + 1, "row": row_text[:300], "columns": columns,
                "rule": ("one column filed" if len(reported) == 1 else
                         "two columns filed (standardized and advanced "
                         "approaches); the binding ratio is the lower")}
    return {"value": None, "code": None, "page": None, "row": "", "columns": [],
            "why": "no row matching the caption was found in the filing"}


index = json.loads((BANKS / "index.json").read_text())
out = {}
for entry in index:
    cert = entry["cert"]
    pdf = BANKS / entry["filings"]["2026-06-30"]["pdf"]
    doc = pymupdf.open(pdf)
    try:
        got = {f: read_ratio(doc, rx, tail)
               for f, (rx, tail, _what) in WANTED.items()}
    finally:
        doc.close()
    out[cert] = got
    print("%-8s %-24s %s" % (
        cert, entry["name"][:24],
        "  ".join("%s=%s@p%s(%s)" % (f, g["value"], g["page"], g["code"])
                  for f, g in got.items())))

(SB / "bank_ratios.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
found = sum(1 for g in out.values() for r in g.values() if r["value"] is not None)
print("\n%d banks, %d of %d ratios read off the filed page"
      % (len(out), found, 2 * len(out)))
