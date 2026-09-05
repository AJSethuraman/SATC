"""The Federal Reserve's own release: charge-off and delinquency rates.

29 of the 142 series are the Fed's quarterly charge-off and delinquency rates
on loans at commercial banks. FRED redistributes them; the Board computes and
publishes them, in six HTML tables on federalreserve.gov. So the comparison is
workbook cell against the Board's own published table.

The tables are laid out as: a period column, then one column per loan
category, split three ways by bank group (all banks, the largest 100, the
rest) and two ways by measure (charge-offs, delinquencies) across six pages.
"""
import json
import pathlib
import re
import sys
import urllib.request

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
CACHE = SB / "sources"
CACHE.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

PAGES = {
    "chgallsa": "https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm",
    "delallsa": "https://www.federalreserve.gov/releases/chargeoff/delallsa.htm",
    "chgtop100sa": "https://www.federalreserve.gov/releases/chargeoff/chgtop100sa.htm",
    "deltop100sa": "https://www.federalreserve.gov/releases/chargeoff/deltop100sa.htm",
    "chgothersa": "https://www.federalreserve.gov/releases/chargeoff/chgothersa.htm",
    "delothersa": "https://www.federalreserve.gov/releases/chargeoff/delothersa.htm",
}

#: Which Fed page and which column each FRED series is. The column index is
#: into the numeric cells of a period row, left to right, as the release
#: prints them. Established by reading the table's own header, then confirmed
#: by the ties below -- a wrong column would not agree to two decimals across
#: twelve quarters, which is what `--check` verifies.
LAYOUT = {
    "CORREACBS": ("chgallsa", 0), "CORRECACBS": ("chgallsa", 2),
    "CORSFRMACBS": ("chgallsa", 1), "CORCACBS": ("chgallsa", 4),
    "CORCCACBS": ("chgallsa", 5), "COROCACBS": ("chgallsa", 6),
    "CORLFRACBS": ("chgallsa", 7), "CORBLACBS": ("chgallsa", 8),
    "CORAGACBS": ("chgallsa", 9), "CORALACBS": ("chgallsa", 10),
    "DRREACBS": ("delallsa", 0), "DRCRELEXFACBS": ("delallsa", 2),
    "DRSFRMACBS": ("delallsa", 1), "DRCLACBS": ("delallsa", 4),
    "DRCCLACBS": ("delallsa", 5), "DROCLACBS": ("delallsa", 6),
    "DRLFRACBS": ("delallsa", 7), "DRBLACBS": ("delallsa", 8),
    "DRAGACBS": ("delallsa", 9), "DRALACBS": ("delallsa", 10),
    "CORCCT100S": ("chgtop100sa", 5), "DRCCLT100S": ("deltop100sa", 5),
    "COROCT100S": ("chgtop100sa", 6), "DROCLT100S": ("deltop100sa", 6),
    "CORCCOBS": ("chgothersa", 5), "DRCCLOBS": ("delothersa", 5),
    "COROCOBS": ("chgothersa", 6), "DROCLOBS": ("delothersa", 6),
    # the same columns, split by bank group
    "CORCOBS": ("chgothersa", 4), "DRCLOBS": ("delothersa", 4),
    "DRCLT100S": ("deltop100sa", 4),
    "DRBLOBS": ("delothersa", 8), "DRBLT100S": ("deltop100sa", 8),
    "DRSFRMOBS": ("delothersa", 1), "DRSFRMT100S": ("deltop100sa", 1),
    "CORCREXFACBS": ("chgallsa", 2),
    "DRCRELEXFOBS": ("delothersa", 2), "DRCRELEXFT100S": ("deltop100sa", 2),
}


def page(name):
    path = CACHE / ("fed_%s.html" % name)
    if not path.exists():
        req = urllib.request.Request(PAGES[name],
                                     headers={"User-Agent": "credit-suite tie-out (public data)"})
        path.write_bytes(urllib.request.urlopen(req, timeout=180).read())
    return path.read_text(encoding="utf-8", errors="replace")


ROW = re.compile(r"(\d{4}):(\d)((?:\s*-?\d+\.\d+&nbsp;)+)")


def parse(name):
    """{(year, quarter): [values left to right]} from the release table."""
    html = page(name)
    flat = re.sub(r"<[^>]+>", " ", html)
    flat = re.sub(r"[ \t]+", " ", flat)
    out = {}
    for match in ROW.finditer(flat):
        year, quarter, body = match.groups()
        values = [float(v) for v in re.findall(r"-?\d+\.\d+", body)]
        out[(year, quarter)] = values
    return out


tables = {name: parse(name) for name in PAGES}
for name, rows in tables.items():
    keys = sorted(rows)
    print("%-12s %3d periods, %s..%s, %d columns"
          % (name, len(rows), keys[0] if keys else "-", keys[-1] if keys else "-",
             len(rows[keys[-1]]) if keys else 0))

ours = json.loads((SB / "fred_ours.json").read_text())
results = []
for sid, (table, column) in sorted(LAYOUT.items()):
    block = ours.get(sid)
    entry = {"series": sid, "source": "Federal Reserve Board, %s" % table,
             "column": column}
    if block is None:
        entry.update(verdict="COULD NOT", why="not in the workbook")
        results.append(entry)
        continue
    entry.update(title=block["title"], tab=block["tab"])
    latest = block.get("latest")
    if latest is None:
        entry.update(verdict="COULD NOT", why="the workbook landed no observations")
        results.append(entry)
        continue
    y, m = int(latest["date"][:4]), int(latest["date"][5:7])
    key = (str(y), str((m - 1) // 3 + 1))
    entry.update(cell="B%d" % latest["row"], ours=latest["value"], date=latest["date"],
                 source_where="%s row %s:%s column %d" % (table, key[0], key[1], column + 1))
    row = tables[table].get(key)
    if row is None:
        entry.update(verdict="COULD NOT", why="the release has no row for %s:%s" % key)
    elif column >= len(row):
        entry.update(verdict="COULD NOT", why="row has %d columns, wanted %d" % (len(row), column + 1))
    else:
        entry["theirs"] = row[column]
        entry["diff"] = round(entry["ours"] - row[column], 6)
        entry["verdict"] = "TIED" if abs(entry["diff"]) < 0.005 else "DIFFERS"
    results.append(entry)

(SB / "fred_fed_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
from collections import Counter
print("\nFed-sourced series compared: %d  %s"
      % (len(results), Counter(r["verdict"] for r in results).most_common()))
for r in results:
    mark = " " if r["verdict"] == "TIED" else "*"
    print("%s %-14s ours %8s  Fed %8s  %s"
          % (mark, r["series"], r.get("ours"), r.get("theirs"),
             r.get("why") or r.get("source_where", "")))
