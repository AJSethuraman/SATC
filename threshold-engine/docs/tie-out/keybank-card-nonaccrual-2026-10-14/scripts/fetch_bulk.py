"""Download the FFIEC's bulk Call Report file for one quarter: every filer's
filed lines, tab-delimited, the same data the CDR facsimile pages render.

    (from threshold-engine/)
    python docs/tie-out/keybank-card-nonaccrual-2026-10-14/scripts/fetch_bulk.py --sources work/nac-sources

It presses the buttons on https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx
as a person would: 'Call Reports -- Single Period', the date 06/30/2026,
'Tab Delimited', 'Download'. Each press is an ASP.NET postback, so each step
carries the page's __VIEWSTATE forward. No login.

Used for one question only: is the FDIC's NACRCD the filed line RC-N 5.a
column C, and LNCRCD the filed line RC-C Part I 6.a, for EVERY filer, not just
KeyBank? The FDIC's own definitions give a title and a sentence, not a line
number, so the answer is shown on the numbers.
"""
import argparse
import hashlib
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PAGE = "https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx"
UA = "threshold-engine tie-out (public data)"


def hidden(html):
    return {n: v for n, v in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', html)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", required=True)
    ap.add_argument("--date", default="06/30/2026")
    a = ap.parse_args()
    out = Path(a.sources)
    out.mkdir(parents=True, exist_ok=True)
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.addheaders = [("User-Agent", UA), ("Referer", PAGE)]

    def post(fields, html):
        form = hidden(html)
        form.update(fields)
        body = op.open(urllib.request.Request(PAGE, data=urllib.parse.urlencode(form).encode(), method="POST"),
                       timeout=600).read()
        return body

    html = op.open(PAGE, timeout=180).read().decode("utf-8", "replace")
    lb = "ctl00$MainContentHolder$ListBox1"
    dd = "ctl00$MainContentHolder$DatesDropDownList"
    fmt = "ctl00$MainContentHolder$FormatType"
    html = post({"__EVENTTARGET": lb, "__EVENTARGUMENT": "", lb: "ReportingSeriesSinglePeriod"}, html).decode("utf-8", "replace")
    dates = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>\s*%s' % re.escape(a.date), html)
    if not dates:
        raise SystemExit("the page offers no %s; it offers %s" % (a.date, re.findall(r"<option[^>]*>([\d/]+)", html)[:8]))
    html = post({"__EVENTTARGET": "ctl00$MainContentHolder$TSVRadioButton", "__EVENTARGUMENT": "", lb: "ReportingSeriesSinglePeriod",
                 dd: dates[0], fmt: "TSVRadioButton"}, html).decode("utf-8", "replace")
    body = post({"__EVENTTARGET": "", "__EVENTARGUMENT": "", lb: "ReportingSeriesSinglePeriod", dd: dates[0],
                 fmt: "TSVRadioButton", "ctl00$MainContentHolder$TabStrip1$Download_0": "Download"}, html)
    if body[:2] != b"PK":
        raise SystemExit("the Download button did not return a zip (%d bytes, starts %r)" % (len(body), body[:80]))
    path = out / ("ffiec-bulk-call-%s.zip" % a.date.replace("/", ""))
    path.write_bytes(body)
    with open(out / "urls.txt", "a", encoding="utf-8") as log:
        log.write("%s\t%d bytes\tsha256 %s\t%s (Call Reports -- Single Period, %s, Tab Delimited, Download)\n"
                  % (path.name, len(body), hashlib.sha256(body).hexdigest(), PAGE, a.date))
    print("wrote", path, len(body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
