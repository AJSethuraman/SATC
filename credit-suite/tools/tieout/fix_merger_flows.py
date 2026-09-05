"""The five PNC differences were mine. The FDIC was right.

A quarterly flow is the year-to-date total less the previous quarter's. Across a
merger that subtraction is wrong unless the acquired bank's prior year-to-date
is subtracted too -- the survivor's Q2 total already contains it. I subtracted
only PNC's own Q1, so every one of PNC's quarterly charge-off fields came out
short by exactly the bank it had absorbed.

    NTCRCDQ   91,974 - (43,842 + 515) = 47,617   the FDIC's figure, to the dollar
    NTCIQ    211,710 - (101,857 + 652) = 109,201
    NTCONOTQ  26,566 - (15,470 + 102) =  10,994
    NTRERESQ   2,999 - (1,113 +    6) =   1,880
    NTRECONQ    -431 - (  -48 +  188) =    -571
    NTAUTOQ   17,837 - (10,233 +    0) =   7,604    (tied before, because 0)
    NTREMULQ    -273 - ( -286 +    0) =      13     (tied before, because 0)

The two that already tied are the two where the acquired bank's figure was zero.
That is not a coincidence; it is the shape of the defect.

PNC Bank merged FirstBank of Lakewood, Colorado (cert 18714) into itself on
18 June 2026, twelve days before the reporting date. **The workbook's own
`_mergers` tab records it**, and says in its own words that the quarter ending
2026-06-30 "spans a merger ... A quarterly flow is the year-to-date total less
the previous quarter's, so across a merger it mixes two banks and is not a
quarter of anything."

I did not read that tab. I queried the FDIC's history API instead, filtered on
processing date, saw only branch transfers dated 6 July 2026, and wrote "no
merger explains it" into twelve exhibits and a roster. The software had already
worked this out and told me on a tab I never opened.

So the fix is not a plug on five lines. The flow derivation now consults the
merger record for every bank, which is what it should have done first.
"""
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
BANKS = SB / "banks"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

import openpyxl                                                  # noqa: E402
import urllib.request                                            # noqa: E402

Q2, Q1 = "2026-06-30", "2026-03-31"
FLOW_YTD = {"NTCRCDQ": "NTCRCD", "NTCIQ": "NTCI", "NTAUTOQ": "NTAUTO",
            "NTCONOTQ": "NTCONOTH", "NTRERESQ": "NTRERES",
            "NTRECONQ": "NTRECONS", "NTREMULQ": "NTREMULT"}


def mergers_for_quarter(iso):
    """Every acquisition the workbook's own merger record shows in this quarter."""
    wb = openpyxl.load_workbook(CS / "example-output" / "Bank_Peer_Monitor.xlsm",
                                data_only=True)
    out = {}
    for row in wb["_mergers"].iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        if len(cells) < 6:
            continue
        survivor_cert = str(cells[1]).strip()
        quarter_end = str(cells[3]).strip()[:10]
        acquired = str(cells[5]).strip()
        if quarter_end == iso and survivor_cert.isdigit() and acquired.isdigit():
            out.setdefault(survivor_cert, []).append(
                {"cert": acquired, "effective": str(cells[2])[:10],
                 "code": str(cells[6]) if len(cells) > 6 else ""})
    wb.close()
    return out


def ytd(cert, repdte):
    fields = ",".join(sorted(set(FLOW_YTD.values())))
    url = ("https://banks.data.fdic.gov/api/financials?filters=CERT%3A" + cert +
           "&fields=CERT,REPDTE," + fields +
           "&sort_by=REPDTE&sort_order=DESC&limit=6&format=json")
    data = json.loads(urllib.request.urlopen(url, timeout=120).read())
    for r in data.get("data", []):
        h = r.get("data", r)
        if str(h.get("REPDTE")) == repdte.replace("-", ""):
            return h
    return {}


acquisitions = mergers_for_quarter(Q2)
print("acquisitions recorded in the workbook for the quarter ending %s: %s"
      % (Q2, {k: [a["cert"] for a in v] for k, v in acquisitions.items()} or "none"))

banks = json.loads((SB / "bank_rosters.json").read_text())
changed = 0
for bank in banks:
    cert = bank["cert"]
    acq = acquisitions.get(cert, [])
    if not acq:
        continue
    prior = [ytd(a["cert"], Q1) for a in acq]
    names = ", ".join(a["cert"] for a in acq)
    for line in bank["lines"]:
        field = line["field"]
        if field not in FLOW_YTD or line.get("note"):
            continue
        y = FLOW_YTD[field]
        add = sum(float(p.get(y) or 0) for p in prior)
        if line.get("ytd_q1") is None or line.get("ytd_q2") is None:
            continue
        filed = line["ytd_q2"] - (line["ytd_q1"] + add)
        ours = line["ours"]
        line["filed"] = filed
        line["merger_adjustment"] = add
        line["verdict"] = ("TIES" if ours is not None
                           and abs(float(ours) - filed) < 0.51 else "DIFFERS")
        line["used"] = ("%s at %s minus the same at %s, minus the year-to-date "
                        "of the bank(s) merged in this quarter (cert %s)"
                        % (line["used"].split(" at ")[0], Q2, Q1, names))
        line["how"] = ("the filing reports this year-to-date, so the quarter is "
                       "one filing minus the previous one -- and across a merger "
                       "the acquired bank's prior year-to-date must come off too, "
                       "because the survivor's total already contains it")
        changed += 1
    counted = [l for l in bank["lines"]
               if not l["note"] and l["verdict"] != "NOT PUBLISHED"]
    bank["compared"] = len(counted)
    bank["tied"] = sum(1 for l in counted if l["verdict"] == "TIES")
    bank["merger_in_quarter"] = [a["cert"] for a in acq]
    print("  %s: %d flow lines re-derived -> %d of %d tie"
          % (bank["name"], changed, bank["tied"], bank["compared"]))

(SB / "bank_rosters.json").write_text(json.dumps(banks, indent=1), encoding="utf-8")
tot = sum(b["compared"] for b in banks)
tied = sum(b["tied"] for b in banks)
print("\n12 banks: %d lines compared, %d tie, %d differ" % (tot, tied, tot - tied))
