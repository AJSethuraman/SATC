"""The comparison: every class amount on the workbook's Peer loan classes
tab (read out of Excel, ours.json) against the 10-Q as filed (out/filed.json
and out/text/), with a verdict each, TIED, DIFFERS or COULD NOT.

    python compare.py CLASSES.json out/ours.json out/filed.json OUT.json

A class read from the filing's XBRL is compared with the inline XBRL fact of
the same members in the filed document. A class taken as printed is looked
for on the filed page: a table row whose first cell is the class's label and
which carries the printed figure, or, for a figure printed in a sentence,
the sentence itself. The verdict is read off the two numbers, never written
ahead of them."""
import json
import re
import sys
from pathlib import Path

#: Where each printed class is on the page: (bank, class) -> (row label or
#: None for a sentence, the figure as printed, $ millions per printed unit).
PRINTED = {
    ("Fifth Third", "Unsecured (in Other consumer loans)"): ("Unsecured", "626", 1),
    ("Fifth Third", "Other secured (in Other consumer loans)"): ("Other secured", "1,299", 1),
    ("Fifth Third", "Point-of-sale home improvement (in Other consumer loans)"): ("Point-of-sale home improvement", "613", 1),
    ("Fifth Third", "Third-party point-of-sale (in Other consumer loans)"): ("Third-party point-of-sale", "285", 1),
    ("Fifth Third", "Indirect RV and marine, primarily (in Indirect secured consumer loans)"):
        (None, "$2.8 billion primarily comprised of indirect recreational vehicle and marine loans", 1000),
    ("M&T", "Recreational finance"): ("Recreational finance", "14,856", 1),
    ("M&T", "Other (consumer)"): ("Other", "2,458", 1),
    ("Zions", "Other (consumer)"): ("Other", "114", 1),
    ("Wells Fargo", "Securities-based (in Other consumer)"): ("Securities-based", "32,231", 1),
    ("Wells Fargo", "Other (in Other consumer)"): ("Other", "6,493", 1),
    ("Bank of America", "U.S. securities-based lending (in Direct/Indirect consumer)"):
        (None, "U.S. securities-based lending loans of $61.9 billion", 1000),
    ("Bank of America", "Non-U.S. consumer loans (in Direct/Indirect consumer)"):
        (None, "non-U.S. consumer loans of $3.2 billion", 1000),
    ("Bank of America", "Other consumer"): ("Other consumer", "182", 1),
    ("Citi", "Personal, small business and other (North America offices)"):
        ("Personal, small business and other", "34,068", 1),
    ("SoFi", "Personal loans (held for sale, at fair value)"): ("Personal loans", "27,505,290", 0.001),
    ("SoFi", "Personal loans (held for sale, at lower of cost or fair value)"): ("Personal loans", "55,841", 0.001),
    ("SoFi", "Student loans (held for investment, at fair value)"): ("Student loans", "16,920,564", 0.001),
}


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()


def find_printed(text, label, printed):
    """The filed evidence for a printed figure: the row or the sentence, or None."""
    if label is None:
        t = norm(text)
        return printed if norm(printed) in t else None
    fig = re.compile(r"(?<![\d,.])" + re.escape(printed) + r"(?![\d,])")
    lines, joined = text.split("\n"), []
    for line in lines:
        # A footnote mark can end a label's line before its cells ("Personal loans(1)" then " | 55,841 |").
        if joined and "|" not in joined[-1] and line.startswith(" |"):
            joined[-1] += line
        else:
            joined.append(line)
    hits = []
    for line in joined:
        cells = [c.strip() for c in line.split(" | ")]
        first = next((c for c in cells if c), "")
        head = re.sub(r"\s*\(\w\)|\(\d\)$", "", first).strip()
        if head.lower().startswith(label.lower()) and len(head) <= len(label) + 6 and fig.search(line):
            numbers = [c for c in cells if re.fullmatch(r"\$?\(?[\d,.]+\)?", c)]
            hits.append((numbers[-1:] != [printed], norm(line)[:240]))
    # A row whose last figure is the one printed (a table's Total column) before any other.
    return sorted(hits)[0][1] if hits else None


def main(classes_path, ours_path, filed_path, out_path):
    spec = json.loads(Path(classes_path).read_text(encoding="utf-8"))
    ours = json.loads(Path(ours_path).read_text(encoding="utf-8-sig"))
    filed = json.loads(Path(filed_path).read_text(encoding="utf-8"))
    texts = Path(filed_path).parent / "text"
    members = {}
    for b in spec["banks"]:
        for c in b["classes"]:
            if "members" in c:
                members[(b["short"], c.get("name"))] = tuple(sorted(c["members"]))
    rows = []
    for o in ours["classes"]:
        bank, name, val = o["bank"], o["name"], float(o["value"])
        r = dict(bank=bank, name=name, ours=val, ours_shown=o["shown"], excel_row=o["row"], how=o["how"])
        if (bank, name) in members:
            key = list(members[(bank, name)])
            hit = [f for f in filed[bank]["facts"] if f[0] == key]
            if not hit:
                r.update(verdict="COULD NOT", why="no inline XBRL fact with members %s in the filed document" % key)
            else:
                v = hit[0][1] / 1e6
                r.update(filed=v, filed_shown=hit[0][2], evidence="ix:nonFraction %s, members %s, shown as %r"
                         % ("us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss", key, hit[0][2]),
                         diff=round(val - v, 6), verdict="TIED" if abs(val - v) < 1e-9 else "DIFFERS")
        elif (bank, name) in PRINTED:
            label, printed, unit = PRINTED[(bank, name)]
            text = (texts / (bank + ".txt")).read_text(encoding="utf-8")
            ev = find_printed(text, label, printed)
            num = float(re.sub(r"[^\d.]", "", re.search(r"[\d,]+(\.\d+)?", printed).group(0))) * unit
            if ev is None:
                r.update(verdict="COULD NOT", why="the figure %r was not found on the filed page%s"
                         % (printed, " in a row labeled %r" % label if label else ""))
            else:
                r.update(filed=num, filed_shown=printed, evidence=ev, diff=round(val - num, 6),
                         verdict="TIED" if abs(val - num) < 1e-6 else "DIFFERS")
        else:
            r.update(verdict="COULD NOT", why="no rule says where this class is in the filing")
        rows.append(r)
    count = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("TIED", "DIFFERS", "COULD NOT")}
    Path(out_path).write_text(json.dumps({"count": count, "total": len(rows), "rows": rows,
                                          "workbook": ours["file"], "excel": ours["excel"],
                                          "error_cells": ours["errors"]}, indent=1), encoding="utf-8")
    print("Tied out: %d of %d   TIED %d  DIFFERS %d  COULD NOT %d"
          % (count["TIED"], len(rows), count["TIED"], count["DIFFERS"], count["COULD NOT"]))
    for r in rows:
        if r["verdict"] != "TIED":
            print("  %-9s %s / %s: %s" % (r["verdict"], r["bank"], r["name"], r.get("why", r.get("diff"))))


if __name__ == "__main__":
    main(*sys.argv[1:5])
