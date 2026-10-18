"""Download every public file the macro proposal reads, into one folder.

    (from threshold-engine/)
    python docs/macro/analysis/fetch.py --sources work/macro-sources

No API key is used or needed: FRED's keyless CSV download, the Labor
Department's claims form, the Federal Reserve's own files, the FDIC API and
NBER's table. A file already in the folder is not fetched again. Every URL is
written to SOURCES/urls.txt beside what it produced.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (threshold-engine macro proposal; public data)"}
GET = {
    "UNRATE.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE",
    "fed-dsr-page.html": "https://www.federalreserve.gov/releases/housedebt/default.htm",
    "nber-cycles.html": "https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions",
    "2026_Final_Supervisory_Severely_Adverse_Domestic.csv":
        "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Severely_Adverse_Domestic.csv",
    "2026_Final_Historic_Domestic.csv": "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Historic_Domestic.csv",
    "public_results_DFAST_2026.csv": "https://www.federalreserve.gov/supervisionreg/files/public_results_DFAST_2026.csv",
}
for yr in (2008, 2015, 2025):
    GET["sod-17534-%d.json" % yr] = "https://api.fdic.gov/banks/sod?" + urllib.parse.urlencode({
        "filters": "CERT:17534 AND YEAR:%d" % yr,
        "fields": "YEAR,STALPBR,STNAMEBR,DEPSUMBR,STCNTYBR,CNTYNAMB", "limit": "10000", "format": "json"})
CLAIMS = ("dol-claims-us.xml", "https://oui.doleta.gov/unemploy/wkclaims/report.asp",
          {"level": "us", "final_yr": "2027", "strtdate": "1967", "enddate": "2026", "filetype": "xml"})


def fetch(url, data=None):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            return urllib.request.urlopen(req, timeout=180).read()
        except Exception as e:  # network trouble: wait and try again, then give up loudly
            if attempt == 3:
                raise SystemExit("could not fetch %s: %s" % (url, e))
            time.sleep(2 ** (attempt + 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", required=True)
    out = Path(ap.parse_args().sources)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "urls.txt", "a", encoding="utf-8") as log:
        for name, url in GET.items():
            p = out / name
            if not p.exists() or p.stat().st_size == 0:
                p.write_bytes(fetch(url))
            log.write("%s\t%s\n" % (name, url))
            print("have", name, flush=True)
        name, url, form = CLAIMS
        p = out / name
        if not p.exists() or p.stat().st_size == 0:
            p.write_bytes(fetch(url, urllib.parse.urlencode(form).encode()))
        log.write("%s\t%s (POST %s)\n" % (name, url, form))
        # the Fed's archived debt service table, 1980:1 to 2024:1, as rows
        t = (out / "fed-dsr-page.html").read_text("utf-8", "replace")
        rows = []
        for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
            tds = re.findall(r'<TD[^>]*headers="[^"]*"[^>]*>(.*?)</TD>', m.group(1), re.S | re.I)
            vals = [re.sub("<[^>]+>", "", v).strip() for v in tds]
            if vals and re.match(r"\d{4}:\d$", vals[0]):
                rows.append(vals)
        (out / "fed-dsr.json").write_text(json.dumps(rows), "utf-8")
        print("have", name, "and fed-dsr.json (%d quarters)" % len(rows))


if __name__ == "__main__":
    main()
