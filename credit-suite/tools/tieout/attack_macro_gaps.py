"""Attack the four remaining macro obstacles once each, and record the verdict.

A COULD NOT is a hypothesis about the source, not a fact about it. The deep run
came back with 12,544 observations unmatched, in four groups. Each group gets
one pass: name the obstacle, ask what it would take to get past it, try that,
and write down the verdict actually reached.

    TOTALNS      1,002  the unadjusted total. The cached file called
                        `g19_hist_nsa.csv` is not the unadjusted level table at
                        all -- it is the student-loan and motor-vehicle
                        quarterly table, saved under a name that describes what
                        was wanted rather than what arrived.
    TOTALSLAR    1,001  percent change at an annual rate.
    SUBLPDCILSLGNQ 146  spreads on C&I loans to large firms -- a survey series
                        the SLOOS layout map simply does not name.
    Case-Shiller 9,143  S&P Dow Jones Indices. Expected to stay unreachable;
                        tried anyway, because "expected" is not "tested".

Nothing here loosens a tolerance or substitutes a second copy of our own data
for a source. If a group cannot be reached, it stays unreached and says why.
"""
import pathlib
import re
import sys
import urllib.request

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
C = SB / "sources"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

UA = {"User-Agent": "credit-suite tie-out (public data)"}


def grab(name, url):
    """Fetch once, cache, and report the shape of what actually arrived."""
    path = C / name
    if not path.exists() or path.stat().st_size == 0:
        try:
            req = urllib.request.Request(url, headers=UA)
            path.write_bytes(urllib.request.urlopen(req, timeout=180).read())
        except Exception as exc:                                 # noqa: BLE001
            print("  %-34s FAILED %s" % (name, str(exc)[:70]))
            return None
    body = path.read_text(encoding="utf-8", errors="replace")
    title = re.search(r"<title>([^<]*)", body)
    print("  %-34s %8d bytes  %s"
          % (name, len(body), (title.group(1).strip()[:52] if title else "(no title)")))
    return body


def first_rows(html, n=3):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if cells:
            out.append(cells[:7])
        if len(out) >= n:
            break
    return out


print("1 - G.19 unadjusted levels (TOTALNS)")
NSA = "https://www.federalreserve.gov/releases/g19/HIST/cc_hist_nsa_levels.html"
h = grab("g19_hist_nsa_levels.html", NSA)
if h:
    for r in first_rows(h, 4):
        print("      ", r)

print("\n2 - G.19 percent change at an annual rate (TOTALSLAR)")
for name, url in (
        ("g19_hist_sa_pct.html",
         "https://www.federalreserve.gov/releases/g19/HIST/cc_hist_sa.html"),
        ("g19_ddp_totalsl.csv",
         "https://www.federalreserve.gov/datadownload/Output.aspx?"
         "rel=G19&series=b1a1ec1d1a2a1a1a1a1a1a1a1a1a1a1a&lastobs=&from=&to="
         "&filetype=csv&label=include&layout=seriescolumn")):
    h2 = grab(name, url)
    if h2:
        for r in first_rows(h2, 3):
            print("      ", r)

print("\n3 - SLOOS spreads on C&I loans to large firms (SUBLPDCILSLGNQ)")
sl = (C / "sloos_chartdata.htm").read_text(encoding="utf-8", errors="replace")
flat = re.sub(r"<[^>]+>", " ", sl)
for phrase in ("spread", "Spread", "SPREAD"):
    hits = [m.start() for m in re.finditer(phrase, flat)]
    if hits:
        print("  chart data mentions %-8s %d times; first context:" % (phrase, len(hits)))
        print("      ...%s..." % re.sub(r"\s+", " ", flat[hits[0] - 90:hits[0] + 130]))
        break
else:
    print("  the chart-data page never uses the word 'spread' -- the series is "
          "not in it")

print("\n4 - S&P CoreLogic Case-Shiller history (9,143 observations)")
for name, url in (
        ("spdji_national_history.xls",
         "https://www.spglobal.com/spdji/en/idsexport/file.xls?"
         "hostIdentifier=48190c8c-42c4-46af-8d1a-0cd5db894797&selectedModule="
         "PerformanceGraphView&selectedSubModule=Graph&yearFlag=tenYearFlag"
         "&indexId=340180"),
        ("fred_alternative_note.txt",
         "https://www.spglobal.com/spdji/en/indices/indicators/"
         "sp-corelogic-case-shiller-us-national-home-price-nsa-index/")):
    grab(name, url)

print("\nWhat this pass established goes into the exhibit as a verdict, not as")
print("a plan. An obstacle described is not an obstacle tested.")
