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
from credit_suite.sources.fdic import feed_fields as NEW         # noqa: E402
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
    # One file, not two. The nineteen bank fields and sixty macro series the
    # firm added on 6 September join the same CSVs -- every row already carries
    # its own citation, verdict and meaning, and a second file is a thing
    # somebody does not know exists.
    _bn = SB / "bank_new_rows.json"
    if _bn.exists():
        bank_rows = bank_rows + json.loads(_bn.read_text())
    _mn = SB / "macro_new_rows.json"
    if _mn.exists():
        _new = json.loads(_mn.read_text())
        _meta = json.loads((SB / "deep" / "macro_new_meta.json").read_text())
        for _r in _new:
            fred_rows.append({
                "series": _r["series"], "date": _r["date"], "ours": _r["ours"],
                "theirs": _r["theirs"], "verdict": _r["verdict"],
                "source": _r["source"], "tab": "macro-observations.csv",
                "row": None})
        NEW_MACRO_META = _meta
    else:
        NEW_MACRO_META = {}
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

def units_of(field):
    """The field's units, or a refusal. Never a blank.

    `fields.FIELD_UNITS` is built from RAW_FIELDS and knows nothing about the
    nineteen fields `feed_fields` adds, so `.get(field, "")` handed back an
    empty string for every one of them and 14,440 numbers shipped with no unit
    beside them. A lookup that answers "" when it does not know is the shape of
    that bug; this one stops.
    """
    unit = FF.FIELD_UNITS.get(field) or NEW.FEED_FIELD_UNITS.get(field)
    assert unit, ("no unit declared for %s -- a number with no unit beside it "
                  "is the trap this feed is written against" % field)
    return ("thousands of dollars" if unit == "USD_thousands"
            else "percent" if unit == "pct" else unit)


VERDICT_PLAIN = {
    "TIES": "verified against the bank's own filed Call Report",
    "COMPUTED BY THE FDIC": ("not a filed line -- the FDIC calculates this from "
                             "filed lines that are verified here"),
    "NOT COMPARABLE (SPANS A MERGER)":
        "this quarter spans a merger, so this flow mixes two banks",
    "NOT COMPARABLE (BASE ADJUSTED FOR A MERGER)":
        "a merger earlier this year moved the running total this quarter "
        "counts from, so it cannot be checked against the filings",
    "NOT ON THIS FILING":
        "the bank did not report this line in this quarter, so there is "
        "nothing on the filing to check it against",
    "DIFFERS": "DOES NOT MATCH the filing -- do not use without reading the note",
}

#: Verdicts that mean the figure should not be charted beside its neighbours.
#: DIFFERS is one of them: a row whose verified_meaning reads "DOES NOT MATCH
#: the filing" and whose next column says it is usable for a trend contradicts
#: itself, and the reader has no way to know which half to believe.
NOT_FOR_TREND = {"NOT COMPARABLE (SPANS A MERGER)",
                 "NOT COMPARABLE (BASE ADJUSTED FOR A MERGER)",
                 "DIFFERS"}

# --------------------------------------------------------------- bank data --
with (OUT / "bank-values.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cert", "bank", "report_date", "field", "value", "units",
                "call_report_schedule", "cited_line", "verified",
                "verified_meaning", "usable_for_trend", "note",
                "filing_url"])
    for r in bank_rows:
        merger = r["verdict"] in NOT_FOR_TREND
        note = r.get("how", "")
        if r["verdict"] == "DIFFERS" and r.get("theirs") is not None:
            # A difference that does not say what the other number was is a
            # flag the reader cannot act on. Give them both figures and the
            # gap, in the row itself.
            note = ("the filing reads %s and the FDIC publishes %s, a "
                    "difference of %s. The filing was read twice -- off the "
                    "printed page and off the machine-readable copy of the "
                    "same filing -- and both say the same thing. %s"
                    % (f"{float(r['theirs']):,.0f}", f"{float(r['ours']):,.0f}",
                       f"{float(r['ours']) - float(r['theirs']):,.0f}",
                       r.get("how", ""))).strip()
        w.writerow([
            r["cert"], r["bank"], r["repdte"], r["field"], r["ours"],
            units_of(r["field"]),
            r.get("schedule", ""), r.get("cited", ""),
            "yes" if r["verdict"] == "TIES" else "no",
            VERDICT_PLAIN.get(r["verdict"], r["verdict"]),
            "no" if merger else "yes",
            note,
            FACSIMILE % (r["cert"], r["repdte"][5:7] + r["repdte"][8:10] + r["repdte"][:4]),
        ])
print("bank-values.csv        : %d rows%s"
      % (len(bank_rows), "  (ten years)" if DEEP else "  (sixteen quarters)"))

# -------------------------------------------------------------- macro data --
#: Titles, units and frequency for the sixty series added on 6 September.
#: They are not in `series_seed`, which is the dashboard's list; letting them
#: fall through to `fred_meta` would give them whatever a snapshot happened to
#: hold, and for these it holds nothing at all.
NEW_META = {}
if DEEP:
    _STATE = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut",
        "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
        "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
        "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
        "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
        "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
        "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
        "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
        "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
        "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
        "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
        "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming"}
    _FIXED = {
        "PCU9241269241262": ("Producer price index: premiums for homeowner's "
                             "insurance", "index Jun 1998=100", "monthly"),
        "TERMCBCCALLNS": ("Interest rate on credit card plans, all accounts",
                          "percent", "quarterly"),
        "TERMCBCCINTNS": ("Interest rate on credit card plans, accounts "
                          "assessed interest", "percent", "quarterly"),
        "RIFLPBCIANM60NM": ("Finance rate on 60-month new car loans",
                            "percent", "quarterly"),
        "CCLACBW027SBOG": ("Credit cards and other revolving plans, all "
                           "commercial banks", "billions $", "weekly"),
        "RHEACBW027SBOG": ("Revolving home equity loans, all commercial banks",
                           "billions $", "weekly"),
        "TOTCI": ("Commercial and industrial loans, all commercial banks",
                  "billions $", "weekly"),
        "CREACBW027SBOG": ("Commercial real estate loans, all commercial "
                           "banks", "billions $", "weekly"),
        "CLSACBW027SBOG": ("Consumer loans, all commercial banks",
                           "billions $", "weekly"),
    }
    for _sid, (_t, _u, _f) in _FIXED.items():
        NEW_META[_sid] = {"title": _t, "units": _u, "frequency": _f,
                          "category": "added_2026_09"}
    for _st, _name in _STATE.items():
        NEW_META["%sUR" % _st] = {
            "title": "Unemployment rate, %s (seasonally adjusted)" % _name,
            "units": "percent", "frequency": "monthly",
            "category": "state_unemployment"}

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
    # The Bureau of Labor Statistics caps unregistered use at 25 requests a day
    # and the first run of this spent them. What is cached is checked against
    # BLS and ties; the rest is fetched when the allowance resets or when a
    # free key is registered, which is the firm's to do. This says so per row
    # rather than letting an unfinished fetch read as an unavailable source.
    "_BLS_PENDING": ("not yet checked: the Bureau of Labor Statistics limits "
                     "unregistered use to 25 requests a day and this run spent "
                     "them. The observations that WERE checked all tie; the "
                     "rest are waiting on the next allowance, not on a missing "
                     "source"),
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
#: The Case-Shiller check that ran and whose verdict never reached this file.
#: {series: the record fred_caseshiller.py wrote}. Absent is handled: if the
#: check has not been run for this build, the rows say the history is not
#: obtainable and claim nothing about a current month, rather than repeating a
#: sentence about a check nobody executed.
_CS = SB / "fred_caseshiller_results.json"
CASE_SHILLER = ({r["series"]: r for r in json.loads(_CS.read_text())}
                if _CS.exists() else {})
#: Only the series whose tie is against a PUBLISHED LEVEL. Selected on the
#: units, which say what the number is; the first version tested the `basis`
#: prose for the word "level" and matched all 22, because the change records
#: describe themselves as pinning the move "not the absolute level".
CS_LEVEL_TIES = {sid: r for sid, r in CASE_SHILLER.items()
                 if r.get("verdict") == "TIED"
                 and "percent change" not in r.get("units", "")}


def case_shiller_note(series):
    """What was checked for this series, in the reader's words. None if not ours."""
    r = CASE_SHILLER.get(series)
    if r is None:
        return None
    if r.get("verdict") != "TIED":
        return ("S&P Dow Jones Indices sells the history. The most recent "
                "month was checked against their free release and DID NOT "
                "agree -- see the tie-out record.")
    if series in CS_LEVEL_TIES:
        return None                      # that row is verified; no gap to explain
    return ("S&P Dow Jones Indices sells the history, so no month here is "
            "checked against a published level. What WAS checked, on %s: S&P "
            "publishes the month-on-month change in its free release, and the "
            "change implied by this series' last two values matches it exactly "
            "(%s vs %s). That pins the MOVE between the last two months. It "
            "does not verify any level, and no earlier month is checked at all."
            % (r.get("date_new", "the most recent month"),
               r.get("ours"), r.get("theirs")))


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
    MACRO_VERIFIED = 0
    for r in fred_rows:
        meta = SEED_ROWS.get(r["series"]) or NEW_META.get(r["series"]) \
            or fred_meta.get(r["series"], {})
        cat = meta.get("category", "")
        block = ours_fred.get(r["series"], {})
        pub = r["source"].replace(" charge-off / delinquency table", "") \
                         .replace(" G.19 historical table", "") \
                         .replace(" Household Debt Service Ratio release", "") \
                         .replace(" Senior Loan Officer Opinion Survey chart data", "") \
                         .replace(" Z.1 complete data package", "") \
                         .replace(" All-Transactions house price index", "")
        ok = r["verdict"] == "TIED"
        # The one Case-Shiller series that ties to a PUBLISHED LEVEL, on the
        # month it was checked. Same entity, same date, same basis, same
        # units -- a verification by every test that word has to pass, and it
        # was being reported as unverified because the check's result was
        # never carried back into this file.
        cs_level = CS_LEVEL_TIES.get(r["series"])
        cs_against = ""
        if cs_level and r["date"] == cs_level.get("date_new"):
            ok = True
            cs_against = ("S&P Dow Jones Indices press release, %s"
                          % cs_level.get("source_where", "published level"))
        MACRO_VERIFIED += bool(ok)
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
            (cs_against or r["source"]) if ok else "",
            # The Case-Shiller note comes FIRST, because for those series the
            # generic "S&P sells the history" line is true and useless: it
            # says nothing about the check that was actually run against S&P's
            # own release, which tied 22 of 22 and was invisible here.
            "" if ok else (case_shiller_note(r["series"])
                           or NO_SOURCE_SERIES.get(r["series"])
                           or (NO_SOURCE_SERIES["_BLS_PENDING"]
                               # Keyed off the GROUP, not a phrase in the
                               # source string. Matching on "Labor Statistics"
                               # caught the insurance index and missed all 51
                               # state rates, whose source reads "BLS Local
                               # Area Unemployment Statistics" -- so 18,786
                               # rows said "no full-history source published"
                               # about an agency that publishes the whole
                               # history and had simply not been asked yet.
                               if NEW_MACRO_META.get(r["series"], [""])[0]
                               in ("insurance", "state_unemployment")
                               else None)
                           or NO_SOURCE_WHY.get(cat)
                           or "no full-history source published"),
            SOURCE_URL.get(r["source"], ""),
        ])
print("macro-observations.csv : %d rows" % len(fred_rows))

# ------------------------------------------------------------ not comparable --
#: The row said: "Balances are point-in-time and are unaffected."
#:
#: True of each measurement and false of the series, which is what a reader
#: charts. Every balance is a correct figure for the institution as it stood
#: that day -- and the institution is a different size on either side of the
#: line. Measured across the whole set on 7 September 2026: FIFTEEN of the 31
#: measurable merger quarters carry a total-asset step of 10% or more. Truist
#: doubles (+100.6%); First-Citizens nearly doubles taking on Silicon Valley
#: Bridge Bank (+96.6%).
#:
#: "Unaffected" is the word that did the damage: it is the sentence somebody
#: relies on when deciding a balance series is safe to trend. So the row now
#: says what actually happens and carries the size of the step, per bank, per
#: quarter, computed from the delivered values rather than described.
def _asset_step(cert, quarter):
    """Total assets the quarter before and the quarter of the merger."""
    y, mth = int(quarter[:4]), int(quarter[5:7])
    before = {3: "%d-12-31" % (y - 1), 6: "%d-03-31" % y,
              9: "%d-06-30" % y, 12: "%d-09-30" % y}[mth]
    got = {}
    for r in bank_rows:
        if (r["cert"] == cert and r["field"] == "ASSET"
                and r["repdte"] in (before, quarter)):
            got[r["repdte"]] = float(r["ours"])
    if len(got) != 2 or not got.get(before):
        return None, None, None
    return got[before], got[quarter], (got[quarter] / got[before] - 1) * 100


with (OUT / "not-comparable-periods.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cert", "bank", "report_date", "acquired_cert", "effective",
                "fdic_change_code", "total_assets_quarter_before",
                "total_assets_this_quarter", "change_in_total_assets_pct",
                "what_this_means"])
    steps = 0
    for m in mergers:
        before, after, pct = _asset_step(m["survivor"], m["quarter"])
        if pct is not None and abs(pct) >= 10:
            steps += 1
        if pct is None:
            size = ("The size of the step could not be computed here because "
                    "total assets are not present for both quarters.")
        else:
            size = ("Total assets go from %s to %s, a change of %+.1f%%. That "
                    "is not growth; it is a different institution."
                    % (format(before, ",.0f"), format(after, ",.0f"), pct))
        w.writerow([
            m["survivor"], m["name"], m["quarter"], m["acquired"],
            m["effective"], m["code"],
            "" if before is None else format(before, ".0f"),
            "" if after is None else format(after, ".0f"),
            "" if pct is None else format(pct, ".1f"),
            "Quarterly charge-off flows for this bank in this quarter mix two "
            "banks and are not a quarter of anything. THE BALANCES EITHER SIDE "
            "OF THIS QUARTER ARE NOT THE SAME INSTITUTION EITHER: each figure "
            "is correct for the bank as it stood that day, but a balance "
            "charted across this line compares a bank with a bigger bank under "
            "one name. " + size])
print("not-comparable-periods.csv : %d merger events, %d with a total-asset "
      "step of 10%% or more" % (len(mergers), steps))

# ------------------------------------------------------------ field meanings --
with (OUT / "field-dictionary.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["field", "plain_english", "units", "computed_by"])
    seen = set()
    for r in bank_rows:
        if r["field"] in seen:
            continue
        seen.add(r["field"])
        w.writerow([r["field"], FPLAIN.describe(r["field"]) or "",
                    units_of(r["field"]),
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
    # Counted off the rows this run WROTE, not off the verdicts it was handed.
    # The two are not the same thing -- a row verified against a source the
    # verifier did not know about is verified in the file and not in the
    # verdict -- and a summary that disagrees with the file it summarises is
    # the failure this whole feed is written against.
    "macro_observations": len(fred_rows), "macro_verified": MACRO_VERIFIED,
    "macro_no_source": len(fred_rows) - MACRO_VERIFIED,
    "macro_differs": fc.get("DIFFERS", 0),
}
summary["total_values"] = summary["bank_values"] + summary["macro_observations"]
summary["total_verified"] = summary["bank_verified"] + summary["macro_verified"]
(OUT / "verification-summary.json").write_text(json.dumps(summary, indent=1),
                                               encoding="utf-8")
print("\n%s" % json.dumps(summary, indent=1))
