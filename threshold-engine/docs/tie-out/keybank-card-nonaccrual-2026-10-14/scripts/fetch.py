"""Fetch every independent source this tie-out reads, into one folder.

    (from threshold-engine/)
    python docs/tie-out/keybank-card-nonaccrual-2026-10-14/scripts/fetch.py --sources work/nac-sources

Public data only, no login anywhere:

  FFIEC CDR      KeyBank, N.A.'s filed Call Report (FFIEC 031) for 30 June 2026,
                 the PDF pages and the XBRL, by pressing the 'Download PDF' and
                 'Download XBRL' buttons on the facsimile page
  FDIC BankFind  the financials call for cert 17534, report date 20260630,
                 and the FDIC's own field definitions (All Financial Reports.xlsx)

Unlike the comparability tie-out's fetcher, a file already in DIR IS fetched
again: the point of this run is a fresh copy of the filing, not an old one.
Every URL, size and SHA-256 goes to DIR/urls.txt.
"""
import argparse
import hashlib
import http.cookiejar
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "threshold-engine tie-out (public data)"
CERT, DATE = "17534", "06302026"
CDR_PAGE = ("https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call"
            "&idType=fdiccert&id=%s&date=%s" % (CERT, DATE))
API_CALL = ("https://api.fdic.gov/banks/financials?filters=CERT:17534%20AND%20REPDTE:20260630"
            "&fields=CERT,REPDTE,NAMEFULL,LNCRCD,NACRCD,P3CRCD,P9CRCD&format=json")
DEFS = "https://api.fdic.gov/banks/docs/All%20Financial%20Reports.xlsx"


def note(log, path, url, extra=""):
    body = path.read_bytes()
    log.write("%s\t%s\t%d bytes\tsha256 %s\t%s%s\n" % (
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"), path.name, len(body),
        hashlib.sha256(body).hexdigest(), url, extra))


def get(url, path, log):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    path.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    note(log, path, url)


def cdr(out, log):
    """Press the CDR page's own buttons: an ASP.NET postback. GET the page for
    its cookie and __VIEWSTATE, then POST the button to the form's action."""
    for label, check, ext in (("Download XBRL", b"<xbrl", "xbrl"), ("Download PDF", b"%pdf", "pdf")):
        path = out / ("call-%s-%s.%s" % (CERT, DATE, ext))
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        op.addheaders = [("User-Agent", UA), ("Referer", CDR_PAGE)]
        html = op.open(CDR_PAGE, timeout=180).read().decode("utf-8", "replace")
        hid = lambda n: (re.search(r'name="%s"[^>]*value="([^"]*)"' % re.escape(n), html) or [None, ""])[1]
        action = re.search(r'<form[^>]*action="([^"]+)"', html)
        button = re.search(r'name="([^"]+)"[^>]*value="%s"' % re.escape(label), html)
        if not (action and button):
            raise SystemExit("no %r button on %s" % (label, CDR_PAGE))
        form = {"__EVENTTARGET": "", "__EVENTARGUMENT": "", "__VIEWSTATE": hid("__VIEWSTATE"),
                "__VIEWSTATEGENERATOR": hid("__VIEWSTATEGENERATOR"),
                "__EVENTVALIDATION": hid("__EVENTVALIDATION"), button.group(1): label}
        req = urllib.request.Request("https://cdr.ffiec.gov/Public/" + action.group(1).replace("&amp;", "&"),
                                     data=urllib.parse.urlencode(form).encode(), method="POST")
        body = op.open(req, timeout=300).read()
        if check not in body[:5000].lower():
            raise SystemExit("%s for cert %s %s did not come back as the file" % (label, CERT, DATE))
        path.write_bytes(body)
        note(log, path, CDR_PAGE, " (button: %s)" % label)
        time.sleep(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", required=True, help="folder to download into")
    a = ap.parse_args()
    out = Path(a.sources)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "urls.txt", "a", encoding="utf-8") as log:
        cdr(out, log)
        get(API_CALL, out / "fdic-17534-20260630.json", log)
        get(DEFS, out / "fdic-all-financial-reports.xlsx", log)
    print((out / "urls.txt").read_text("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
