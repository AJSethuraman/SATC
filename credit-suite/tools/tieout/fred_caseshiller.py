"""S&P Cotality Case-Shiller, against S&P Dow Jones Indices' own press release.

Twenty-two of the 142 series are Case-Shiller house price indexes. S&P Dow
Jones Indices computes and publishes them; FRED redistributes them. The index
levels themselves are a commercial product -- spglobal.com refuses scripted
requests outright (HTTP 403) -- so the obstacle was real. It was not the
verdict.

What S&P publishes free, every month, is the release. It prints:

  * Table 2 -- the June NOT-seasonally-adjusted index LEVEL for each metro
  * Table 3 -- the June/May SEASONALLY ADJUSTED percent CHANGE for each metro

Twenty of our twenty-two series are the seasonally adjusted levels, which the
release does not print. But two adjacent cells of our own workbook imply the
change, and the change is published. So the comparison is:

    (our June cell / our May cell - 1) x 100   vs   S&P's printed SA change

Both sides of that are honest: ours is read out of the workbook and nothing
else, and theirs is a number S&P published which can perfectly well disagree.
It is a weaker tie than a level-for-level match -- it pins the ratio of two
cells rather than their absolute level -- and that limitation is stated per
line rather than buried.

The one national NSA series ties directly to a printed level.

Table 3 was read off the rendered release; the numbers below are that reading.
A misread would show up as a failed tie, not a silent pass, because the check
is a comparison and not an assertion.
"""
import json
import pathlib
import sys

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

RELEASE = ("S&P Dow Jones Indices, 'S&P Cotality Case-Shiller Index Reports "
           "Annual Gain in June 2026', press release dated 25 August 2026, "
           "1484791_cshomeprice-release-0825.pdf")

#: metro -> (series id, the release's printed June/May SEASONALLY ADJUSTED
#: percent change, from Table 3 on page 6 of the release)
SA_CHANGE = {
    "Atlanta":       ("ATXRSA", -0.12),
    "Boston":        ("BOXRSA", 0.11),
    "Charlotte":     ("CRXRSA", -0.03),
    "Chicago":       ("CHXRSA", 0.35),
    "Cleveland":     ("CEXRSA", 0.48),
    "Dallas":        ("DAXRSA", -0.07),
    "Denver":        ("DNXRSA", 0.10),
    "Las Vegas":     ("LVXRSA", -0.50),
    "Los Angeles":   ("LXXRSA", 0.39),
    "Miami":         ("MIXRSA", -0.10),
    "Minneapolis":   ("MNXRSA", 0.15),
    "New York":      ("NYXRSA", 0.72),
    "Phoenix":       ("PHXRSA", -0.40),
    "Portland":      ("POXRSA", 0.11),
    "San Diego":     ("SDXRSA", -0.11),
    "San Francisco": ("SFXRSA", 0.31),
    "Seattle":       ("SEXRSA", -0.34),
    "Tampa":         ("TPXRSA", 0.26),
    "Washington":    ("WDXRSA", 0.41),
    "U.S. National": ("CSUSHPISA", 0.13),
}

#: Detroit has no June 2026 index at all. The release says so in its own words:
#: recording-office delays in Wayne County meant "no valid June 2026 update of
#: the Detroit S&P Cotality Case-Shiller Index will be provided". Our workbook's
#: latest Detroit observation is May 2026 -- which is the release agreeing with
#: us about an absence, and is why this line ties on May/April instead.
DETROIT = ("DEXRSA", 0.15, "May / April")

#: The one series the release prints as an outright level: Table 2, page 5.
NSA_LEVEL = ("CSUSHPINSA", 336.66, "Table 2, row 'U.S. National', column 'June 2026 Level'")

ours = json.loads((SB / "fred_ours.json").read_text())
results = []


def two_cells(sid, back=0):
    """The workbook's newest and next-newest observations, as they are stored."""
    obs = ours.get(sid, {}).get("observations") or []
    if len(obs) < back + 2:
        return None, None
    return obs[back], obs[back + 1]


def compare(sid, metro, published, window, back=0):
    entry = {"series": sid, "metro": metro, "source": RELEASE,
             "units": "percent change, month over month, seasonally adjusted",
             "workbook_title": ours.get(sid, {}).get("title"),
             "basis": ("a ratio of two workbook cells against S&P's published "
                       "change -- this pins the month-on-month move, not the "
                       "absolute level")}
    new, old = two_cells(sid, back)
    if new is None:
        entry.update(verdict="COULD NOT",
                     why="the workbook does not hold two consecutive observations")
        results.append(entry)
        return
    entry.update(tab=ours[sid]["tab"],
                 cell_new="B%d" % new["row"], cell_old="B%d" % old["row"],
                 ours_new=new["value"], ours_old=old["value"],
                 date_new=new["date"], date_old=old["date"],
                 source_where="Table 3, row %r, column 'SA' under '%s Change (%%)'"
                              % (metro, window))
    # S&P publishes its index levels to two decimals and computes the printed
    # change from those. Matching that is an equality, not a tolerance: the
    # two decimals are the source's own precision, and rounding our cells to
    # it is reading the source's arithmetic rather than relaxing ours.
    computed = round((round(new["value"], 2) / round(old["value"], 2) - 1.0)
                     * 100.0, 2)
    entry["ours"] = computed
    entry["ours_full_precision"] = round(
        (new["value"] / old["value"] - 1.0) * 100.0, 4)
    entry["theirs"] = published
    entry["diff"] = round(computed - published, 6)
    entry["derivation"] = (
        "round(%s, 2) / round(%s, 2) - 1, x100, rounded to 2dp -- both cells "
        "read from %s. The rounding is S&P's published precision, and the "
        "match is exact rather than within a band."
        % (entry["cell_new"], entry["cell_old"], entry["tab"]))
    entry["verdict"] = "TIED" if entry["diff"] == 0 else "DIFFERS"
    results.append(entry)


for metro, (sid, published) in sorted(SA_CHANGE.items()):
    compare(sid, metro, published, "June / May")

sid, published, window = DETROIT
compare(sid, "Detroit", published, window)

# The national NSA index, level for level.
sid, published, where = NSA_LEVEL
block = ours.get(sid)
latest = block["latest"] if block else None
entry = {"series": sid, "metro": "U.S. National", "source": RELEASE,
         "source_where": where, "units": "index, Jan 2000 = 100",
         "workbook_title": block["title"] if block else None,
         "basis": "a published level against the workbook cell, directly"}
if latest is None:
    entry.update(verdict="COULD NOT", why="the workbook landed no observations")
else:
    entry.update(tab=block["tab"], cell_new="B%d" % latest["row"],
                 ours=latest["value"], date_new=latest["date"], theirs=published)
    entry["ours_full_precision"] = latest["value"]
    entry["ours"] = round(latest["value"], 2)
    entry["diff"] = round(entry["ours"] - published, 6)
    entry["verdict"] = "TIED" if entry["diff"] == 0 else "DIFFERS"
results.append(entry)

(SB / "fred_caseshiller_results.json").write_text(json.dumps(results, indent=1),
                                                 encoding="utf-8")
from collections import Counter
print("Case-Shiller series compared: %d  %s"
      % (len(results), Counter(r["verdict"] for r in results).most_common()))
for r in sorted(results, key=lambda x: (x["verdict"] != "TIED", x["series"]), reverse=True):
    mark = " " if r["verdict"] == "TIED" else "*"
    print("%s %-11s %-14s ours %9s  S&P %8s  diff %8s  %s"
          % (mark, r["series"], r["metro"], r.get("ours"), r.get("theirs"),
             r.get("diff"), r.get("why") or ""))
