"""The Senior Loan Officer Opinion Survey, against the Board's own chart data.

Thirteen of the 142 series are SLOOS net percentages. FRED redistributes them;
the Board runs the survey and publishes the numbers, as five tables on the
release's chart-data page. So the comparison is workbook cell against the
Board's own table.

The column map below was built from each series' *official* definition, not
from the title our own config prints beside it -- because several of those
titles turned out to describe a different series than the number they sit
next to, which is the whole reason to do this by hand.
"""
import json
import pathlib
import re
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
C = SB / "sources"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

PAGE = "sloos_chartdata.htm"
SOURCE = ("Federal Reserve Board, Senior Loan Officer Opinion Survey on Bank "
          "Lending Practices, chart data")

#: series -> (table index on the page, data cell index in a period row,
#:            the column's printed name, the table's printed panel)
LAYOUT = {
    "DRTSCILM":    (0, 1, "Large and medium",
                    "Panel 1: tightening standards for C&I loans"),
    "DRTSCIS":     (0, 2, "Small",
                    "Panel 1: tightening standards for C&I loans"),
    "DRSDCILM":    (0, 5, "Large and medium",
                    "Panel 3: stronger demand for C&I loans"),
    "DRSDCIS":     (0, 6, "Small",
                    "Panel 3: stronger demand for C&I loans"),
    "SUBLPDRCSC":  (1, 2, "Construction and land development",
                    "Panel 1: tightening standards for CRE loans"),
    "SUBLPDRCSN":  (1, 3, "Nonfarm nonresidential",
                    "Panel 1: tightening standards for CRE loans"),
    "SUBLPDRCSM":  (1, 4, "Multifamily",
                    "Panel 1: tightening standards for CRE loans"),
    "DRTSSP":      (2, 4, "Subprime",
                    "Panel 1: tightening standards for mortgage loans"),
    "SUBLPDHMSENQ": (2, 5, "GSE-eligible",
                    "Panel 1: tightening standards for mortgage loans"),
    "DRTSCLCC":    (3, 1, "Credit cards",
                    "Panel 1: tightening standards on consumer loans"),
    "STDSAUTO":    (3, 3, "New and used autos",
                    "Panel 1: tightening standards on consumer loans"),
    "STDSOTHCONS": (3, 4, "Consumer loans excluding credit cards and autos",
                    "Panel 1: tightening standards on consumer loans"),
    # SUBLPDCILSLGNQ is the LARGE-BANKS-ONLY split of C&I tightening, which the
    # chart-data page does not carry. It is taken from the survey's Table 1
    # instead -- see net_from_table_one below.
}

#: Question 1 of the survey is standards on C&I loans to large and
#: middle-market firms, and it is the first response table on the page.
QUESTION_ONE = 0
#: Within a response row: [label, all banks, all %, large banks, large %,
#: other banks, other %]. The percentage columns are the ones the net is
#: computed from, because that is what the Board's own net percentage means.
COL_PCT = {"all": 2, "large": 4, "other": 6}


def net_from_table_one(which):
    """The Board's net percentage, from its own published response counts."""
    html = (C / "sloos_t1.htm").read_text(encoding="utf-8", errors="replace")
    table = re.findall(r"<table.*?</table>", html, re.S)[QUESTION_ONE]
    pct = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
        cells = [txt(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cells) > COL_PCT[which] and cells[0]:
            value = cells[COL_PCT[which]]
            if re.fullmatch(r"-?\d+(\.\d+)?", value):
                pct[cells[0].lower()] = float(value)
    tighten = sum(v for k, v in pct.items() if k.startswith("tightened"))
    eased = sum(v for k, v in pct.items() if k.startswith("eased"))
    return round(tighten - eased, 4), pct


def txt(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).replace("\xa0", " ") \
             .replace("&nbsp;", " ").strip()


def tables():
    html = (C / PAGE).read_text(encoding="utf-8", errors="replace")
    out = []
    for tb in re.findall(r"<table.*?</table>", tb_src := html, re.S):
        rows = {}
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
            cells = [txt(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
            if cells and re.fullmatch(r"\d{4}:\d", cells[0]):
                rows[tuple(cells[0].split(":"))] = cells
        out.append(rows)
    return out


TB = tables()
print("chart-data tables parsed: %s period-row counts"
      % [len(t) for t in TB])

ours = json.loads((SB / "fred_ours.json").read_text())
official = json.loads((SB / "fred_titles.json").read_text())
results = []

for sid in sorted(set(LAYOUT) | {"SUBLPDCILSLGNQ"}):
    block = ours.get(sid)
    entry = {"series": sid, "source": SOURCE,
             "official_title": official.get(sid, {}).get("title"),
             "workbook_title": block["title"] if block else None,
             "units": "net percent of respondents"}
    if block is None:
        entry.update(verdict="COULD NOT", why="not in the workbook")
        results.append(entry)
        continue
    latest = block["latest"]
    entry.update(tab=block["tab"], cell="B%d" % latest["row"],
                 ours=latest["value"], date=latest["date"])
    y, m = int(latest["date"][:4]), int(latest["date"][5:7])
    key = (str(y), str((m - 1) // 3 + 1))
    if sid not in LAYOUT:
        # Prove the arithmetic on a series that already tied, then apply it.
        control, _ = net_from_table_one("all")
        control_ok = abs(control - ours["DRTSCILM"]["latest"]["value"]) < 0.05
        theirs, cells = net_from_table_one("large")
        entry["source_where"] = (
            "survey Table 1, question 1 (standards on C&I loans to large and "
            "middle-market firms), 'Large Banks' percent column: "
            + " ".join("%s %s" % (k, v) for k, v in sorted(cells.items())))
        entry["derivation"] = ("(tightened considerably + tightened somewhat) "
                               "- (eased somewhat + eased considerably)")
        entry["control"] = ("the same arithmetic on the 'All Respondents' "
                            "column gives %.1f against DRTSCILM's %.1f -- %s"
                            % (control, ours["DRTSCILM"]["latest"]["value"],
                               "agrees" if control_ok else "DOES NOT AGREE"))
        if not control_ok:
            entry.update(verdict="COULD NOT",
                         why="the derivation failed its own control: " + entry["control"])
        else:
            entry["theirs"] = theirs
            entry["diff"] = round(entry["ours"] - theirs, 6)
            entry["verdict"] = "TIED" if abs(entry["diff"]) < 0.05 else "DIFFERS"
        results.append(entry)
        continue
    ti, ci, colname, panel = LAYOUT[sid]
    entry["source_where"] = ("table %d, %s, column %r, row %s:%s"
                             % (ti + 1, panel, colname, key[0], key[1]))
    row = TB[ti].get(key)
    if row is None:
        entry.update(verdict="COULD NOT",
                     why="the Board's table has no row for %s:%s" % key)
    elif ci >= len(row) or not re.fullmatch(r"-?\d+(\.\d+)?", row[ci]):
        entry.update(verdict="COULD NOT",
                     why="the Board prints %r in that cell"
                         % (row[ci] if ci < len(row) else "nothing"))
    else:
        theirs = float(row[ci])
        entry["theirs"] = theirs
        entry["diff"] = round(entry["ours"] - theirs, 6)
        entry["verdict"] = "TIED" if abs(entry["diff"]) < 0.05 else "DIFFERS"
    results.append(entry)

(SB / "fred_sloos_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
from collections import Counter
print("\nSLOOS series compared: %d  %s"
      % (len(results), Counter(r["verdict"] for r in results).most_common()))
for r in results:
    mark = " " if r["verdict"] == "TIED" else "*"
    print("%s %-15s ours %7s  Board %7s  %s"
          % (mark, r["series"], r.get("ours"), r.get("theirs"),
             (r.get("why") or r.get("source_where", ""))[:74]))

print("\nWhere the workbook's own title disagrees with the series definition:")
bad = 0
for r in results:
    wt, ot = (r.get("workbook_title") or ""), (r.get("official_title") or "")
    keys = [k for k in ("Subprime", "GSE", "Construction", "Nonfarm",
                        "Multifamily", "Spreads", "Large Domestic")
            if (k.lower() in ot.lower()) != (k.lower() in wt.lower())]
    if keys:
        bad += 1
        print("  %-15s workbook: %s" % (r["series"], wt[:78]))
        print("  %-15s official: %s" % ("", ot[:78]))
print("  %d of %d series carry a title that misdescribes them" % (bad, len(results)))
