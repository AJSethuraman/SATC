"""Is NACRCD the filed line RC-N 5.a column C (B577), and LNCRCD the filed
line RC-C Part I 6.a (B538) -- for every bank that filed for 30 June 2026?

    (from threshold-engine/)
    python -I docs/tie-out/keybank-card-nonaccrual-2026-10-14/scripts/fields_vs_filing.py \
        --sources work/nac-sources --out docs/tie-out/keybank-card-nonaccrual-2026-10-14/fields-vs-filing.txt

Reads the FFIEC bulk file fetch_bulk.py downloaded (every filer's filed lines)
and asks the FDIC API, once, for NACRCD and LNCRCD of every filer at
20260630. Joins on the FDIC certificate number the bulk file's POR table
gives for each RSSD ID. A form-031 filer files the consolidated line (RCFD);
a 041 or 051 filer files the domestic one (RCON); the consolidated line is
taken when there is one. A line a bank did not file is never read as 0.
"""
import argparse
import csv
import io
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

API = "https://api.fdic.gov/banks/financials?" + urllib.parse.urlencode({
    "filters": "REPDTE:20260630", "fields": "CERT,REPDTE,NACRCD,LNCRCD",
    "sort_by": "CERT", "sort_order": "ASC", "limit": "10000", "format": "json"})


def table(z, name):
    """A bulk schedule: header row, then a row of descriptions, then data."""
    with z.open(name) as f:
        rows = list(csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"), delimiter="\t"))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return [dict(zip(hdr, [c.strip().strip('"') for c in r])) for r in rows[2:] if r and r[0].strip()]


def line(row, code):
    for p in ("RCFD", "RCON"):
        v = row.get(p + code, "")
        if v != "":
            return int(v), p + code
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src = Path(a.sources)
    z = zipfile.ZipFile(src / "ffiec-bulk-call-06302026.zip")
    por = {r["IDRSSD"]: r for r in table(z, "FFIEC CDR Call Bulk POR 06302026.txt")}
    rcn = {r["IDRSSD"]: r for r in table(z, "FFIEC CDR Call Schedule RCN 06302026.txt")}
    rcc = {r["IDRSSD"]: r for r in table(z, "FFIEC CDR Call Schedule RCCI 06302026.txt")}

    api_path = src / "fdic-20260630-all-NACRCD-LNCRCD.json"
    if not api_path.exists():
        api_path.write_bytes(urllib.request.urlopen(urllib.request.Request(API, headers={"User-Agent": "threshold-engine tie-out"}), timeout=300).read())
    d = json.loads(api_path.read_text("utf-8"))
    fdic = {str(x["data"]["CERT"]): x["data"] for x in d["data"]}

    cert_of = {rssd: r.get("FDIC Certificate Number", "").strip() for rssd, r in por.items()}
    out, tally = [], {"NACRCD": [0, 0, 0, 0], "LNCRCD": [0, 0, 0, 0]}   # same, differs, FDIC blank, not filed
    differ = []
    joined = 0
    for rssd, cert in sorted(cert_of.items(), key=lambda kv: int(kv[1] or 0)):
        if cert not in fdic:
            continue
        joined += 1
        for field, sched, code in (("NACRCD", rcn, "B577"), ("LNCRCD", rcc, "B538")):
            filed, full = line(sched.get(rssd, {}), code)
            api = fdic[cert].get(field)
            t = tally[field]
            if filed is None and api is None:
                t[3] += 1
            elif api is None:
                t[2] += 1
                differ.append("%s cert %s: FDIC blank, filed %s = %s" % (field, cert, full, filed))
            elif filed is None:
                t[3] += 1
                differ.append("%s cert %s: FDIC %s, filing has no %s line" % (field, cert, api, code))
            elif int(api) == filed:
                t[0] += 1
            else:
                t[1] += 1
                differ.append("%s cert %s: FDIC %s, filed %s = %s" % (field, cert, api, full, filed))
    out.append("FFIEC bulk Call Report 06/30/2026: %d filers (POR). FDIC API rows at 20260630: %d (meta total %s, index %s)."
               % (len(por), len(fdic), d["meta"].get("total"), d["meta"].get("index", {}).get("name")))
    out.append("Joined on FDIC certificate number: %d banks." % joined)
    for field, code, where in (("NACRCD", "B577", "RC-N 5.a column C"), ("LNCRCD", "B538", "RC-C Part I 6.a")):
        s, df, fb, nf = tally[field]
        out.append("%s against %s (%s): %d equal to the dollar-thousand, %d differ, %d FDIC blank where filed, %d neither has a value; total %d"
                   % (field, code, where, s, df, fb, nf, s + df + fb + nf))
    k = next(r for r, c in cert_of.items() if c == "17534")
    out.append("KeyBank (cert 17534, RSSD %s): NACRCD %s, %s; LNCRCD %s, %s"
               % (k, fdic["17534"]["NACRCD"], "%s = %s" % line(rcn[k], "B577")[::-1],
                  fdic["17534"]["LNCRCD"], "%s = %s" % line(rcc[k], "B538")[::-1]))
    out.append("Differences, every one:" if differ else "Differences: none.")
    out += ["  " + x for x in differ]
    Path(a.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
