"""The deliverable: verified raw data, and plain English about it.

The firm's instruction: "I just need all of the raw data and I need it verified.
I need some plain English explaining it all ... The only thing I wanna do is
basically eliminate you making ratios for me however, you are free to have a tab
in there that explains what ratios seem to make sense and why."

So: every value as it landed, the document it came from, and whether it was
checked against that document. Nothing computed here. The ratios tab describes
and does not calculate.
"""
import csv
import json
import pathlib
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
OUT = CS / "verified-data"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import plain as FPLAIN            # noqa: E402
from credit_suite.sources.fdic import fields as FF               # noqa: E402
from credit_suite.sources.fred import series_seed as FSEED       # noqa: E402

#: Units and titles come from the SEED, which is the source of truth, not from
#: a JSON snapshot of it taken earlier in the session. A snapshot shipped
#: "billions $" against a figure in millions -- the same defect the tie-out
#: found, reintroduced by reading a stale copy.
SEED_ROWS = {}
for _row in (list(FSEED.CONSUMER) + list(FSEED.COMMERCIAL)
             + list(FSEED.PRICE_NATIONAL) + list(FSEED._geo_rows())):
    SEED_ROWS[_row["series_id"]] = _row
assert len(SEED_ROWS) == 142, (
    "the seed defines 142 series and this holds %d; the missing ones fall "
    "through to a stale snapshot and ship its old titles and units"
    % len(SEED_ROWS))

DEEP = "--deep" in sys.argv
if DEEP:
    bank_rows = json.loads((SB / "bank_deep_rows.json").read_text())
    fred_rows = json.loads((SB / "fred_deep_rows.json").read_text())
    mergers = json.loads((SB / "merger_records_deep.json").read_text())
else:
    bank_rows = json.loads((SB / "bank_history_rows.json").read_text())
    fred_rows = json.loads((SB / "fred_history_rows.json").read_text())
    mergers = json.loads((SB / "merger_records.json").read_text())
#: Titles and units come from SEED_ROWS above. This snapshot is the last
#: resort and should never be reached; it predates the label corrections.
fred_meta = {r["series_id"]: r for r in json.loads((SB / "fred_series.json").read_text())}
ours_fred = json.loads((SB / "fred_ours.json").read_text())

FACSIMILE = ("https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx"
             "?ds=call&idType=fdiccert&id=%s&date=%s")

VERDICT_PLAIN = {
    "TIES": "verified against the bank's own filed Call Report",
    "COMPUTED BY THE FDIC": ("not a filed line -- the FDIC calculates this from "
                             "filed lines that are verified here"),
    "NOT COMPARABLE (SPANS A MERGER)":
        "this quarter spans a merger, so this flow mixes two banks",
    "DIFFERS": "DOES NOT MATCH the filing -- do not use without reading the note",
}

# --------------------------------------------------------------- bank data --
with (OUT / "bank-values.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cert", "bank", "report_date", "field", "value", "units",
                "call_report_schedule", "cited_line", "verified",
                "verified_meaning", "usable_for_trend", "note",
                "filing_url"])
    for r in bank_rows:
        units = FF.FIELD_UNITS.get(r["field"], "")
        merger = r["verdict"] == "NOT COMPARABLE (SPANS A MERGER)"
        w.writerow([
            r["cert"], r["bank"], r["repdte"], r["field"], r["ours"],
            "thousands of dollars" if units == "USD_thousands" else
            ("percent" if units == "pct" else units),
            r.get("schedule", ""), r.get("cited", ""),
            "yes" if r["verdict"] == "TIES" else "no",
            VERDICT_PLAIN.get(r["verdict"], r["verdict"]),
            "no" if merger else "yes",
            r.get("how", ""),
            FACSIMILE % (r["cert"], r["repdte"][5:7] + r["repdte"][8:10] + r["repdte"][:4]),
        ])
print("bank-values.csv        : %d rows%s"
      % (len(bank_rows), "  (ten years)" if DEEP else "  (sixteen quarters)"))

# -------------------------------------------------------------- macro data --
SOURCE_URL = {
    "FHFA All-Transactions house price index":
        "https://www.fhfa.gov/hpi/download/quarterly_datasets/",
    "Federal Reserve Board charge-off / delinquency table":
        "https://www.federalreserve.gov/releases/chargeoff/",
    "Federal Reserve Board G.19 historical table":
        "https://www.federalreserve.gov/releases/g19/hist/cc_hist_sa_levels.html",
    "Federal Reserve Board Household Debt Service Ratio release":
        "https://www.federalreserve.gov/releases/dsr/",
    "Federal Reserve Board Senior Loan Officer Opinion Survey chart data":
        "https://www.federalreserve.gov/data/sloos.htm",
    "Federal Reserve Board Z.1 complete data package":
        "https://www.federalreserve.gov/releases/z1/",
    "no full-history source": "",
}
#: Why a period could not be checked, said per series rather than per
#: category -- because within a category some series tie in full and others
#: cannot be reached at all, and one sentence covering both is a sentence
#: that is wrong about one of them.
NO_SOURCE_SERIES = {
    "TOTALSLAR": ("a percent change, not a published table. The Board prints "
                  "it only for the most recent months. The LEVEL it is the "
                  "change in, TOTALSL, is checked in full -- 1,002 of 1,002 "
                  "months against the Board's own historical table"),
    "SUBLPDCILSLGNQ": ("the large-bank subset. The survey's chart data covers "
                       "all domestic respondents; the large-bank split is "
                       "printed inside each quarter's own survey document, so "
                       "a full history means opening 146 separate releases. "
                       "Searched the chart data column by column first; it is "
                       "not in there"),
}
NO_SOURCE_WHY = {
    "hpi_caseshiller": ("S&P Dow Jones Indices sells the history. Its free "
                        "monthly press release carries the current month, and "
                        "that month is checked against it; the months before "
                        "it are not obtainable without paying S&P"),
    "hpi_national": ("the two national Case-Shiller indexes. S&P sells the "
                     "history; the current month is checked against its free "
                     "release. The two FHFA national indexes in this group "
                     "are checked in full"),
    "g19": ("no historical table is published for this particular series"),
    "sloos_diffusion": ("printed only inside each quarter's own survey "
                        "document, not in the chart data"),
}
with (OUT / "macro-observations.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["series_id", "title", "date", "value", "units", "frequency",
                "publisher", "verified", "verified_against", "why_not_verified",
                "source_url"])
    for r in fred_rows:
        meta = SEED_ROWS.get(r["series"], fred_meta.get(r["series"], {}))
        cat = meta.get("category", "")
        block = ours_fred.get(r["series"], {})
        pub = r["source"].replace(" charge-off / delinquency table", "") \
                         .replace(" G.19 historical table", "") \
                         .replace(" Household Debt Service Ratio release", "") \
                         .replace(" Senior Loan Officer Opinion Survey chart data", "") \
                         .replace(" Z.1 complete data package", "") \
                         .replace(" All-Transactions house price index", "")
        ok = r["verdict"] == "TIED"
        w.writerow([
            r["series"], meta.get("title", block.get("title", "")), r["date"],
            r["ours"], meta.get("units", ""), meta.get("frequency", ""),
            # The two NATIONAL Case-Shiller indexes sit in hpi_national,
            # beside two FHFA ones. Routing on the category alone left
            # them with no publisher while their own note explained that
            # S&P sells the history.
            "S&P Dow Jones Indices"
            if (cat == "hpi_caseshiller"
                or r["series"] in ("CSUSHPINSA", "CSUSHPISA")) else pub,
            "yes" if ok else "no",
            r["source"] if ok else "",
            "" if ok else (NO_SOURCE_SERIES.get(r["series"])
                           or NO_SOURCE_WHY.get(cat)
                           or "no full-history source published"),
            SOURCE_URL.get(r["source"], ""),
        ])
print("macro-observations.csv : %d rows" % len(fred_rows))

# ------------------------------------------------------------ not comparable --
with (OUT / "not-comparable-periods.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cert", "bank", "report_date", "acquired_cert", "effective",
                "fdic_change_code", "what_this_means"])
    for m in mergers:
        w.writerow([m["survivor"], m["name"], m["quarter"], m["acquired"],
                    m["effective"], m["code"],
                    "Quarterly charge-off flows for this bank in this quarter "
                    "mix two banks and are not a quarter of anything. Balances "
                    "are point-in-time and are unaffected."])
print("not-comparable-periods.csv : %d merger events" % len(mergers))

# ------------------------------------------------------------ field meanings --
with (OUT / "field-dictionary.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["field", "plain_english", "units", "computed_by"])
    seen = set()
    for r in bank_rows:
        if r["field"] in seen:
            continue
        seen.add(r["field"])
        units = FF.FIELD_UNITS.get(r["field"], "")
        w.writerow([r["field"], FPLAIN.describe(r["field"]) or "",
                    "thousands of dollars" if units == "USD_thousands" else
                    ("percent" if units == "pct" else units),
                    "the FDIC" if r["verdict"] == "COMPUTED BY THE FDIC"
                    else "the bank, on its Call Report"])
print("field-dictionary.csv   : %d fields" % len(seen))

from collections import Counter
bc = Counter(r["verdict"] for r in bank_rows)
fc = Counter(r["verdict"] for r in fred_rows)
summary = {
    "bank_values": len(bank_rows), "bank_verified": bc.get("TIES", 0),
    "bank_fdic_computed": bc.get("COMPUTED BY THE FDIC", 0),
    "bank_not_comparable": bc.get("NOT COMPARABLE (SPANS A MERGER)", 0),
    "bank_differs": bc.get("DIFFERS", 0),
    "macro_observations": len(fred_rows), "macro_verified": fc.get("TIED", 0),
    "macro_no_source": fc.get("NO SOURCE FOR THIS PERIOD", 0),
    "macro_differs": fc.get("DIFFERS", 0),
}
summary["total_values"] = summary["bank_values"] + summary["macro_observations"]
summary["total_verified"] = summary["bank_verified"] + summary["macro_verified"]
(OUT / "verification-summary.json").write_text(json.dumps(summary, indent=1),
                                               encoding="utf-8")
print("\n%s" % json.dumps(summary, indent=1))
