"""Download every independent source this tie-out reads, into one folder.

    python fetch_sources.py --sources DIR --user-agent "Firm name you@example.com"

Public data only. Nothing here touches KeyBank's internal books.

What it fetches, and from whom (no login anywhere):

  FFIEC CDR      filed Call Reports, the XBRL and the PDF pages, by pressing
                 the 'Download XBRL' and 'Download PDF' buttons on
                 https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx
  FDIC BankFind  https://api.fdic.gov/banks/financials, /history, /institutions
                 and the field dictionary risview_properties.yaml
  SEC EDGAR      KeyCorp (CIK 91576): 10-K for 2025, 10-Q for 30 June 2026
  FDIC           Call Report instructions (glossary, RC-C part I, RC-N, RI-B)
                 and the Quarterly Banking Profile for 2026 Q2
  Federal Reserve  H.8 release of 16 April 2010 (FAS 166/167 notes)

A file already in DIR is not fetched again. Every URL is written to
DIR/urls.txt beside what it produced, so the reader can open the same page.
"""
import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

#: Set from --user-agent. SEC EDGAR refuses an automated request that does not
#: name a contact (it answered 403 to one that did not), so the person running
#: this supplies their own; no address is written into the repository.
UA = None
ROSTER = ["628", "3511", "3510", "7213", "6548", "6384", "9846", "4297", "17534",
          "6672", "6560", "11063", "57957", "588", "12368", "2270"]

#: (cert, MMDDYYYY) of every filed Call Report read.
FILINGS = [(c, "06302026") for c in ROSTER] + [
    ("17534", d) for d in ("06302025", "09302025", "12312025", "03312026",
                           "06302021", "09302021")] + [
    ("57957", "12312015"), ("3511", "12312015"),
    ("7213", "06302011"), ("7213", "09302011"), ("23360", "06302011")]

API = "https://api.fdic.gov/banks/"
CERTS = " OR ".join(ROSTER)
FDIC_CALLS = {
    "fdic-2026q2-guaranteed.json": API + "financials?" + urllib.parse.urlencode({
        "filters": "REPDTE:20260630",
        "fields": "CERT,REPDTE,NAMEFULL,P3GTY,P9GTY,NAGTY,P3GTYPAR,P9GTYPAR,NAGTYPAR,"
                  "P3GTYGNM,P9GTYGNM,NAGTYGNM,P9RERSFM,P9CONOTH,P9AUTO,P9CRCD,NARERSFM,"
                  "P9LNLS,NACRCD,LNCRCD,DRCRCD,CRCRCD,LNAUTO,LNCONOTH,LNCONRP,LNCON,LS",
        "sort_by": "CERT", "sort_order": "ASC", "limit": "10000", "format": "json"}),
    "fdic-2026q2-asset.json": API + "financials?" + urllib.parse.urlencode({
        "filters": "REPDTE:20260630",
        "fields": "CERT,REPDTE,ASSET,LNLSGR,LNCRCD,LNCONRP,LNRERSF2",
        "sort_by": "CERT", "sort_order": "ASC", "limit": "10000", "format": "json"}),
    "fdic-2009q4-revolving.json": API + "financials?" + urllib.parse.urlencode({
        "filters": "REPDTE:20091231", "fields": "CERT,REPDTE,BKCLASS,LNCRCD,LNCONRP,LNCON",
        "sort_by": "CERT", "sort_order": "ASC", "limit": "10000", "format": "json"}),
    "fdic-2010q1-revolving.json": API + "financials?" + urllib.parse.urlencode({
        "filters": "REPDTE:20100331", "fields": "CERT,REPDTE,BKCLASS,LNCRCD,LNCONRP,LNCON",
        "sort_by": "CERT", "sort_order": "ASC", "limit": "10000", "format": "json"}),
    "fdic-keybank-consumer-2015-2026.json": API + "financials?" + urllib.parse.urlencode({
        "filters": "CERT:17534 AND REPDTE:[20150101 TO 20261231]",
        "fields": "CERT,REPDTE,LNAUTO,LNCONOTH,LNCONRP,LNCRCD,LNCON,LS,DRAUTO,DRCONOTH",
        "sort_by": "REPDTE", "sort_order": "ASC", "limit": "100", "format": "json"}),
    "fdic-history-roster.json": API + "history?" + urllib.parse.urlencode({
        "filters": "ACQ_CERT:(%s) AND EFFDATE:[2005-10-01 TO *]" % CERTS,
        "fields": "CERT,EFFDATE,CHANGECODE,CHANGECODE_DESC,ACQ_CERT,OUT_CERT,ID",
        "sort_by": "EFFDATE", "sort_order": "ASC", "limit": "10000", "format": "json"}),
    "fdic-institutions-card-charters.json": API + "institutions?" + urllib.parse.urlencode({
        "filters": "CERT:(23360 OR 33318 OR 23702 OR 33954 OR 58496 OR 27595 OR 26211)",
        "fields": "CERT,NAME,ACTIVE,ENDEFYMD,CHANGEC1,NAMEHCR", "limit": "20", "format": "json"}),
    "fdic-risview_properties.yaml": API + "docs/risview_properties.yaml",
}

SEC = "https://www.sec.gov/Archives/edgar/data/91576/"
OTHER = {
    "keycorp-10k-2025.htm": SEC + "000162828026010546/key-20251231.htm",
    "keycorp-10k-2025_htm.xml": SEC + "000162828026010546/key-20251231_htm.xml",
    "keycorp-10q-2026q2.htm": SEC + "000162828026052671/key-20260630.htm",
    "keycorp-10q-2026q2_htm.xml": SEC + "000162828026052671/key-20260630_htm.xml",
    "instr-glossary-2026-09.pdf": "https://www.fdic.gov/bank-financial-reports/031-041-926gloss-9-30-2026-final.pdf",
    "instr-rc-c-part1.pdf": "https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2024/031-041-624-rc-c1.pdf",
    "instr-rc-n.pdf": "https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2024/031-041-624-rc-n.pdf",
    "instr-ri-b.pdf": "https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2024/031-041-324-ri-b.pdf",
    "qbp-2026q2.pdf": "https://www.fdic.gov/quarterly-banking-profile/quarterly-banking-profile-second-quarter-2026.pdf",
    "qbp-2026q2-time-series.xlsx": "https://www.fdic.gov/quarterly-banking-profile/qbp-time-series-spreadsheets-second-quarter-2026.xlsx",
    "qbp-2026q2-notes.pdf": "https://www.fdic.gov/quarterly-banking-profile/qbp-notes-users-second-quarter-2026.pdf",
    "fed-h8-2010-04-16.html": "https://www.federalreserve.gov/releases/h8/20100416/",
}


def get(url, path, log):
    if path.exists() and path.stat().st_size > 0:
        log.write("%s\talready there\t%s\n" % (path.name, url))
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    body = urllib.request.urlopen(req, timeout=300).read()
    path.write_bytes(body)
    log.write("%s\t%d bytes\t%s\n" % (path.name, len(body), url))
    time.sleep(0.5)


def cdr(cert, mmddyyyy, out, log):
    """Press the CDR page's own buttons: an ASP.NET postback. GET the page for
    its cookie and __VIEWSTATE, then POST the button to the form's action."""
    page = ("https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call"
            "&idType=fdiccert&id=%s&date=%s" % (cert, mmddyyyy))
    for label, check, ext in (("Download XBRL", b"<xbrl", "xbrl"), ("Download PDF", b"%pdf", "pdf")):
        path = out / ("call-%s-%s.%s" % (cert, mmddyyyy, ext))
        if path.exists() and path.stat().st_size > 0:
            log.write("%s\talready there\t%s\n" % (path.name, page))
            continue
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        op.addheaders = [("User-Agent", UA), ("Referer", page)]
        html = op.open(page, timeout=180).read().decode("utf-8", "replace")
        hid = lambda n: (re.search(r'name="%s"[^>]*value="([^"]*)"' % re.escape(n), html) or [None, ""])[1]
        action = re.search(r'<form[^>]*action="([^"]+)"', html)
        button = re.search(r'name="([^"]+)"[^>]*value="%s"' % re.escape(label), html)
        if not (action and button):
            raise SystemExit("no %r button on %s" % (label, page))
        form = {"__EVENTTARGET": "", "__EVENTARGUMENT": "", "__VIEWSTATE": hid("__VIEWSTATE"),
                "__VIEWSTATEGENERATOR": hid("__VIEWSTATEGENERATOR"),
                "__EVENTVALIDATION": hid("__EVENTVALIDATION"), button.group(1): label}
        req = urllib.request.Request("https://cdr.ffiec.gov/Public/" + action.group(1).replace("&amp;", "&"),
                                     data=urllib.parse.urlencode(form).encode(), method="POST")
        body = op.open(req, timeout=300).read()
        if check not in body[:5000].lower():
            raise SystemExit("%s for cert %s %s did not come back as the file" % (label, cert, mmddyyyy))
        path.write_bytes(body)
        log.write("%s\t%d bytes\t%s (button: %s)\n" % (path.name, len(body), page, label))
        time.sleep(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", required=True, help="folder to download into")
    ap.add_argument("--user-agent", required=True,
                    help="who is asking, with a contact address, e.g. \"Firm name you@example.com\" (SEC requires one)")
    a = ap.parse_args()
    global UA
    UA = a.user_agent
    out = Path(a.sources)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "urls.txt", "a", encoding="utf-8") as log:
        for cert, d in FILINGS:
            cdr(cert, d, out, log)
            print("filing", cert, d, flush=True)
        for name, url in list(FDIC_CALLS.items()) + list(OTHER.items()):
            get(url, out / name, log)
            print("got", name, flush=True)
        # second stage: the names of every bank a roster bank acquired
        hist = json.loads((out / "fdic-history-roster.json").read_text("utf-8"))
        certs = sorted({str(x["data"]["OUT_CERT"]) for x in hist["data"] if x["data"].get("OUT_CERT")}, key=int)
        for i in range(0, len(certs), 40):
            url = API + "institutions?" + urllib.parse.urlencode({
                "filters": "CERT:(%s)" % " OR ".join(certs[i:i + 40]),
                "fields": "CERT,NAME,ENDEFYMD,NAMEHCR", "limit": "100", "format": "json"})
            get(url, out / ("fdic-institutions-acquired-%02d.json" % (i // 40)), log)
        print("got acquired banks' names", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
