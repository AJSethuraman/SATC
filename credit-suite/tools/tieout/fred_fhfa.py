"""FHFA: the agency that computes the house price indexes FRED redistributes.

70 of the 142 series are FHFA All-Transactions house price indexes -- 51
states, 15 metros, 4 national/census. FRED republishes them; FHFA computes and
publishes them. So the comparison is workbook cell against FHFA's own quarterly
dataset, downloaded from fhfa.gov.
"""
import csv
import io
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

FILES = {
    "state": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv",
    "metro": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv",
    "us": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_us_and_census.csv",
}


def fetch(name, url):
    path = CACHE / ("fhfa_%s.csv" % name)
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "credit-suite tie-out (public data)"})
        path.write_bytes(urllib.request.urlopen(req, timeout=180).read())
    return path.read_text(encoding="utf-8", errors="replace")


ours = json.loads((SB / "fred_ours.json").read_text())
series = json.loads((SB / "fred_series.json").read_text())
cat = {r["series_id"]: r["category"] for r in series}

state_rows, metro_rows, us_rows = {}, {}, {}
for line in csv.reader(io.StringIO(fetch("state", FILES["state"]))):
    if len(line) >= 4:
        state_rows.setdefault(line[0].strip(), {})[(line[1], line[2])] = line[3]
for line in csv.reader(io.StringIO(fetch("metro", FILES["metro"]))):
    if len(line) >= 5 and line[1].strip().isdigit():
        metro_rows.setdefault(line[1].strip(), {})[(line[2], line[3])] = line[4]
for line in csv.reader(io.StringIO(fetch("us", FILES["us"]))):
    if len(line) >= 4:
        us_rows.setdefault(line[0].strip(), {})[(line[1], line[2])] = line[3]
print("FHFA files: %d states, %d metros, %d national/census codes"
      % (len(state_rows), len(metro_rows), len(us_rows)))
print("national/census codes:", sorted(us_rows)[:12])


def quarter_of(iso):
    y, m = int(iso[:4]), int(iso[5:7])
    return str(y), str((m - 1) // 3 + 1)


results = []
for sid, block in sorted(ours.items()):
    category = cat.get(sid, "")
    if not category.startswith("hpi_") or category == "hpi_caseshiller":
        continue
    latest = block.get("latest")
    entry = {"series": sid, "title": block["title"], "category": category,
             "tab": block["tab"], "cell": "B%d" % latest["row"] if latest else None,
             "ours": latest["value"] if latest else None,
             "date": latest["date"] if latest else None}
    if latest is None:
        entry.update(verdict="COULD NOT", why="the workbook landed no observations for this series")
        results.append(entry)
        continue
    y, q = quarter_of(latest["date"])
    if category == "hpi_state":
        key = sid[:2]
        table, where = state_rows.get(key), "hpi_at_state.csv row %s %sQ%s" % (key, y, q)
    elif category == "hpi_metro":
        code = re.search(r"(\d{5})", sid)
        key = code.group(1) if code else None
        table, where = metro_rows.get(key), "hpi_at_metro.csv CBSA %s %sQ%s" % (key, y, q)
    else:
        key = {"USSTHPI": "USA"}.get(sid)
        table, where = (us_rows.get(key) if key else None), "hpi_at_us_and_census.csv %s %sQ%s" % (key, y, q)
    entry["source_where"] = where
    if table is None:
        entry.update(verdict="COULD NOT", why="no matching row in FHFA's file for key %r" % key)
    else:
        raw = table.get((y, q))
        if raw in (None, "-", ""):
            entry.update(verdict="COULD NOT", why="FHFA publishes no value for %sQ%s" % (y, q))
        else:
            theirs = float(raw)
            entry["theirs"] = theirs
            entry["diff"] = round(entry["ours"] - theirs, 6) if entry["ours"] is not None else None
            entry["verdict"] = "TIED" if abs(entry["diff"]) < 0.005 else "DIFFERS"
    results.append(entry)

(SB / "fred_fhfa_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
from collections import Counter
print("\nFHFA-sourced series compared: %d" % len(results))
print(Counter(r["verdict"] for r in results).most_common())
for r in results:
    if r["verdict"] != "TIED":
        print("   %-14s %-9s %s" % (r["series"], r["verdict"], r.get("why") or
                                    ("ours %s vs FHFA %s" % (r.get("ours"), r.get("theirs")))))
print("\nsample ties:")
for r in [r for r in results if r["verdict"] == "TIED"][:4]:
    print("   %-14s ours %10s  FHFA %10s  (%s)" % (r["series"], r["ours"], r["theirs"], r["source_where"]))
