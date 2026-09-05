"""The two Z.1 commercial-property price indexes, from the Board's own data.

This one nearly went down as COULD NOT, and the obstacle was real but wrong.

The Z.1 release ships a public CSV bundle. I read every one of its members and
built the set of series codes it carries -- 6,107 of them -- and neither of
ours was there. The Board's Financial Accounts Guide has a page for each code,
but it prints the definition and no data, and its "add to clipboard" flow
returned an empty clipboard. Two dead ends, both accurately described.

The third route works: the Board's Data Download Program publishes the ENTIRE
Z.1 as one package, and that package carries both series. The CSV bundle on the
release page is a subset. "It is not in the file I looked in" was never the
same statement as "the Board does not publish it".

The package is SDMX XML, streamed rather than loaded, because it is far larger
uncompressed than it looks zipped.
"""
import io
import json
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
C = SB / "sources"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

WANT = {"FL075035403.Q": "BOGZ1FL075035403Q",
        "FL075035503.Q": "BOGZ1FL075035503Q"}
SOURCE = ("Federal Reserve Board, Z.1 Financial Accounts of the United States, "
          "complete Data Download Program package (Z1_data.xml)")

z = zipfile.ZipFile(C / "z1_pkg_zip.bin")
info = z.getinfo("Z1_data.xml")
print("Z1_data.xml: %d bytes compressed, %d uncompressed"
      % (info.compress_size, info.file_size))

found = {code: {} for code in WANT}
current = None
with z.open("Z1_data.xml") as handle:
    for event, elem in ET.iterparse(handle, events=("start", "end")):
        tag = elem.tag.rsplit("}", 1)[-1]
        if event == "start" and tag == "Series":
            name = (elem.get("SERIES_NAME") or elem.get("SERIES")
                    or elem.get("series_name"))
            current = name if name in WANT else None
        elif event == "end":
            if tag == "Obs" and current:
                period = (elem.get("TIME_PERIOD") or elem.get("time_period"))
                value = (elem.get("OBS_VALUE") or elem.get("obs_value"))
                if period and value not in (None, "", "ND"):
                    found[current][period] = value
            elif tag == "Series":
                current = None
                elem.clear()

for code, obs in found.items():
    print("%s: %d observations, latest %s"
          % (code, len(obs), max(obs) if obs else "-"))

ours = json.loads((SB / "fred_ours.json").read_text())
official = json.loads((SB / "fred_titles.json").read_text())
results = []
for code, sid in sorted(WANT.items()):
    block = ours.get(sid)
    entry = {"series": sid, "z1_code": code, "source": SOURCE,
             "units": "index",
             "official_title": official.get(sid, {}).get("title"),
             "workbook_title": block["title"] if block else None}
    if block is None or block.get("latest") is None:
        entry.update(verdict="COULD NOT", why="the workbook landed no observations")
        results.append(entry)
        continue
    latest = block["latest"]
    entry.update(tab=block["tab"], cell="B%d" % latest["row"],
                 ours=latest["value"], date=latest["date"])
    y, m = int(latest["date"][:4]), int(latest["date"][5:7])
    obs = found[code]
    # FRED stamps a quarter at its FIRST day; the Board stamps it at its LAST.
    # Same quarter, two conventions -- and matching on the literal date would
    # have reported "no observation" for a series that is plainly published.
    quarter = (m - 1) // 3 + 1
    end_month, end_day = ((3, 31), (6, 30), (9, 30), (12, 31))[quarter - 1]
    key = None
    for candidate in ("%04d-%02d-%02d" % (y, end_month, end_day),
                      "%04d-%02d-01" % (y, m),
                      "%d:Q%d" % (y, quarter), "%04d-Q%d" % (y, quarter)):
        if candidate in obs:
            key = candidate
            break
    entry["source_where"] = ("series %s, observation %s"
                             % (code, key or "%04d-%02d" % (y, m)))
    if key is None:
        entry.update(verdict="COULD NOT",
                     why="the package has no observation at that period; it "
                         "carries %s" % (sorted(obs)[-3:] if obs else "nothing"))
    else:
        theirs = float(obs[key])
        entry["theirs"] = theirs
        entry["diff"] = round(entry["ours"] - theirs, 6)
        entry["verdict"] = "TIED" if abs(entry["diff"]) < 0.5 else "DIFFERS"
    results.append(entry)

(SB / "fred_z1_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
from collections import Counter
print("\nZ.1 series compared: %d  %s"
      % (len(results), Counter(r["verdict"] for r in results).most_common()))
for r in results:
    mark = " " if r["verdict"] == "TIED" else "*"
    print("%s %-19s ours %12s  Board %12s  %s"
          % (mark, r["series"], r.get("ours"), r.get("theirs"),
             r.get("why") or r.get("source_where", "")))
    print("      workbook calls it: %s" % (r.get("workbook_title") or "-"))
    print("      the Board calls it: %s" % (r.get("official_title") or "-"))
