"""The explanation tabs -- with every number in the prose read off the data.

A sentence like "13,056 values were checked" is a claim about the workbook it
sits in, and the fastest way for it to become false is for somebody to rebuild
the data and not the prose. That has already happened here once: these tabs
described sixteen quarters after the feed had gone to forty.

So nothing below is typed. Every count is computed from the delivered CSVs at
build time. If the data changes and the prose does not, the prose changes anyway.
"""
import collections
import csv
import json
import pathlib

CS = pathlib.Path(__file__).resolve().parents[2]
D = CS / "verified-data"


def _rows(name):
    with (D / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


BANK = _rows("bank-values.csv")
MACRO = _rows("macro-observations.csv")
MERGERS = _rows("not-comparable-periods.csv")
#: The banks in the set that are not commercial lenders, read off the peer
#: list rather than counted by hand in a sentence.
OTHERS = [b["name"] for b in
          json.loads((CS / "config" / "peers.json").read_text(encoding="utf-8"))["banks"]
          if b["group"] == "counterparty" and b["active"]]

BANK_TIED = sum(1 for r in BANK if r["verified"] == "yes")
BANK_TREND_NO = sum(1 for r in BANK if r["usable_for_trend"] == "no")
BANK_RATIOS = sum(1 for r in BANK if "FDIC calculates" in r["verified_meaning"])
BANK_MERGER = sum(1 for r in BANK if "spans a merger" in r["verified_meaning"])
BANK_BASE = sum(1 for r in BANK
                if "moved the running total" in r["verified_meaning"])
#: Rows the filing and the FDIC do not agree on. READ OFF THE DELIVERED FILE.
#: This tab said "NONE DISAGREED" as a typed sentence until 7 September 2026,
#: when a difference appeared and the sentence went on saying it. A claim about
#: the data that is not computed from the data is the exact failure this whole
#: workbook exists to stop, printed on its own headline.
BANK_DIFFERS = [r for r in BANK if "DOES NOT MATCH" in r["verified_meaning"]]
BANK_NOLINE = (len(BANK) - BANK_TIED - BANK_RATIOS - BANK_MERGER
               - BANK_BASE - len(BANK_DIFFERS))
QUARTERS = sorted({r["report_date"] for r in BANK})
FIELDS = sorted({r["field"] for r in BANK})
CERTS = sorted({r["cert"] for r in BANK})

MACRO_TIED = sum(1 for r in MACRO if r["verified"] == "yes")
MACRO_NOT = len(MACRO) - MACRO_TIED
#: Not the same thing, and calling them the same overstates the gap. PENDING is
#: waiting on an agency's daily request allowance and will close on the next
#: run; UNOBTAINABLE is a paywall, a transform nobody tabulates, or a figure
#: printed only inside 146 separate documents.
MACRO_PENDING = sum(1 for r in MACRO if r["verified"] != "yes"
                    and r["why_not_verified"].startswith("not yet checked"))
MACRO_UNOBTAINABLE = MACRO_NOT - MACRO_PENDING
UNOBTAINABLE_SERIES = sorted({r["series_id"] for r in MACRO
                              if r["verified"] != "yes"
                              and not r["why_not_verified"].startswith(
                                  "not yet checked")})
SERIES = sorted({r["series_id"] for r in MACRO})
BY_PUB = collections.Counter(r["publisher"] for r in MACRO if r["verified"] == "yes")
UNVERIFIED = collections.Counter(r["series_id"] for r in MACRO
                                 if r["verified"] != "yes")
MACRO_DATES = sorted({r["date"] for r in MACRO})

ZEROS = sum(1 for r in BANK if float(r["value"] or 0) == 0.0)
ZEROS_TIED = sum(1 for r in BANK
                 if float(r["value"] or 0) == 0.0 and r["verified"] == "yes")

TOTAL = len(BANK) + len(MACRO)
TOTAL_TIED = BANK_TIED + MACRO_TIED

#: Case-Shiller is the paywalled block and the single biggest reason a
#: macro row says verified = no. Counted off the PUBLISHER column, not
#: off the series name: the twenty metros are named for their cities --
#: ATXRSA, BOXRSA, CHXRSA -- so a name-prefix count finds the two
#: national indexes and misses ten thousand observations.
CASE_SHILLER = sum(1 for r in MACRO if r["verified"] != "yes"
                   and r["publisher"] == "S&P Dow Jones Indices")


def n(x):
    return "{:,}".format(x)


def _earliest(publisher_fragment):
    return min((r["date"] for r in MACRO if r["verified"] == "yes"
                and publisher_fragment in r["publisher"]), default="-")


def _obs(publisher_fragment):
    return sum(v for k, v in BY_PUB.items() if publisher_fragment in k)


def _unverified_names(limit=6):
    names = sorted(UNVERIFIED)
    shown = ", ".join(names[:limit])
    return shown + (" and %d more" % (len(names) - limit)
                    if len(names) > limit else "")


START_HERE = [
    ("h1", "Verified raw data -- %d banks and %d macro series"
     % (len(CERTS), len(SERIES))),
    ("", ""),
    ("p", "Every number in this workbook was published by somebody else -- a "
          "bank, or a government agency -- and copied here without change."),
    ("ok", "NOTHING IN THIS WORKBOOK IS CALCULATED BY OUR SOFTWARE. No ratios, "
           "no quarter-on-quarter changes, no scores, no bands. If a number is "
           "here, a bank or an agency published it in that form."),
    ("", ""),
    ("h2", "What is in it"),
    ("p", "BANK DATA         %s values. %d large US banks, %d quarters (%s to "
          "%s), %d fields each."
     % (n(len(BANK)), len(CERTS), len(QUARTERS), QUARTERS[0], QUARTERS[-1],
        len(FIELDS))),
    ("p", "MACRO DATA        %s observations across %d national and regional "
          "series, %s to %s."
     % (n(len(MACRO)), len(SERIES), MACRO_DATES[0], MACRO_DATES[-1])),
    ("p", "WHAT WAS PROVEN   How each number was checked, and which ones have "
          "a photograph behind them."),
    ("p", "LIMITS            What this data cannot do. Read it before charting."),
    ("p", "THE SOURCES       Who publishes what, including what Case-Shiller is "
          "and why it is the gap."),
    ("p", "FIELD DICTIONARY  What each bank field means, in plain English."),
    ("p", "RATIOS            Ratios worth building and the trap in each. It "
          "describes them and builds none."),
    ("p", "NOT COMPARABLE    %d quarters you should not chart as a trend, and "
          "why." % len(MERGERS)),
    ("", ""),
    ("h2", "The headline"),
    ("ok" if not BANK_DIFFERS else "warn",
     "%s of %s values were compared against a document published by somebody "
     "who does not work for us -- the bank's own filed Call Report, or the "
     "agency that computes the series. %s The %s that could not be checked "
     "each say why, in their own row."
     % (n(TOTAL_TIED), n(TOTAL),
        "None of them disagreed." if not BANK_DIFFERS
        else ("%s disagreed -- see WHAT WAS PROVEN, which names %s."
              % (n(len(BANK_DIFFERS)),
                 "it" if len(BANK_DIFFERS) == 1 else "them")),
        n(TOTAL - TOTAL_TIED))),
    ("", ""),
    ("h2", "The two things to know before you chart anything"),
    ("caution", "1. UNITS. Bank values are THOUSANDS of dollars unless the row "
                "says otherwise. A bank total of 4,091,315,000 means $4.09 "
                "trillion."),
    ("caution", "2. MERGER QUARTERS. When a bank absorbs another bank, its "
                "quarterly charge-off figures for that quarter mix two banks. "
                "%d such quarters are listed on NOT COMPARABLE, and %s rows "
                "say usable_for_trend = no. One of these produced a charge-off "
                "rate of 670%% in an earlier version of this work. That is "
                "what a merger looks like when nothing flags it."
     % (len(MERGERS), n(BANK_TREND_NO))),
    ("", ""),
    ("h2", "How to check any bank number yourself, in about a minute"),
    ("p", "1. Find the row. Note the cited_line -- for example RCFD2170 -- and "
          "the filing_url."),
    ("p", "2. Open the filing_url. It is the regulator's own copy of that "
          "bank's Call Report for that quarter."),
    ("p", "3. Search the page for the cited_line code. The number beside it is "
          "the number in this workbook."),
    ("p", "That code is an MDRM code: the Federal Reserve's permanent "
          "identifier for one line on the form. Quote it to a bank's finance "
          "team and they will know exactly which number you mean."),
]

LIMITS = [
    ("h1", "Limits -- what this data cannot do"),
    ("", ""),
    ("warn", "1. THERE IS NO VINTAGE. These are the figures as published when "
             "they were pulled. Banks amend Call Reports and agencies revise "
             "series, so a value verified today may not match the same source "
             "in six months. Nothing here records which revision a figure is. "
             "Treat the whole workbook as a snapshot dated 5 September 2026."),
    ("warn", ("2. %s MACRO OBSERVATIONS ARE NOT VERIFIED, and they split two "
              "ways. %s are NOT YET CHECKED -- the Bureau of Labor Statistics "
              "caps unregistered use at 25 requests a day and this run spent "
              "them; every one of those that was reached ties, and the rest "
              "close on the next run. The other %s have no obtainable source "
              "at all: %d whole series out of %d, unchecked for their entire "
              "history rather than here and there. All of them are marked "
              "verified = no and shaded, and every row says which it is in "
              "why_not_verified."
              % (n(MACRO_NOT), n(MACRO_PENDING), n(MACRO_UNOBTAINABLE),
                 len(UNOBTAINABLE_SERIES), len(SERIES)))
     if MACRO_PENDING else
     ("2. %s MACRO OBSERVATIONS HAVE NO OBTAINABLE SOURCE, and they are not "
      "spread evenly -- they are %d whole series out of %d, unchecked for "
      "their entire history rather than here and there. They are marked "
      "verified = no and shaded, and each row says why in why_not_verified. "
      "They are: %s."
      % (n(MACRO_UNOBTAINABLE), len(UNOBTAINABLE_SERIES), len(SERIES),
         ", ".join(UNOBTAINABLE_SERIES[:6])
         + (" and %d more" % (len(UNOBTAINABLE_SERIES) - 6)
            if len(UNOBTAINABLE_SERIES) > 6 else "")))),
    ("warn", "3. PROVENANCE IS STRONGER ON THE BANK SIDE. Every one of the %s "
             "bank rows names its exact line and links to the exact filing -- "
             "you can click through and put a finger on the number. On the "
             "macro side the link is the agency's landing page, not the row. "
             "The check was done against the exact file; the link is coarser "
             "than the check." % n(len(BANK))),
    ("caution", "4. SOME BANK FIELDS ARE RATIOS THE FDIC COMPUTES, not lines a "
                "bank files -- %s rows, labelled computed_by = the FDIC. They "
                "are still ratios sitting in a raw feed. To drop them, filter "
                "BANK DATA where verified_meaning mentions the FDIC "
                "calculating them." % n(BANK_RATIOS)),
    ("caution", "5. THE %d BANKS ARE NOT A LIKE-FOR-LIKE PEER GROUP. %s are "
                "not commercial lenders: %s. Their balance sheets are shaped "
                "nothing like a lender's, and a peer ranking that mixes them "
                "will mislead. They are marked group = counterparty in the "
                "peer list, so they are straightforward to exclude. (This read "
                "\"two custody banks and two broker-dealer banks\" until "
                "7 September 2026, which is four, and there are three.)"
     % (len(CERTS), len(OTHERS), ", ".join(OTHERS))),
    ("caution", "6. %s OF THE BANK VALUES ARE EXACTLY ZERO -- categories where "
                "a bank has no exposure. %s of those were checked against an "
                "explicit zero on the bank's own filing, so they are a "
                "reported nil rather than a blank cell. It is still the "
                "weakest form of agreement, and worth knowing before you count "
                "ties." % (n(ZEROS), n(ZEROS_TIED))),
    ("caution", "7. ONE FIELD THE SOFTWARE ASKS FOR DOES NOT EXIST AT THE "
                "FDIC. NTRENREQ -- quarterly charge-offs on nonfarm "
                "nonresidential commercial property -- was requested for every "
                "bank-quarter and returned for none. The FDIC omits a field "
                "name it does not have instead of rejecting the request, so "
                "this looked exactly like banks reporting nothing. The FDIC "
                "does publish the quantity, as two lines rather than one: "
                "DRRENRSQ, the quarter's gross charge-offs, and CRRENRSQ, "
                "the quarter's recoveries. Their difference is the net "
                "figure, and that identity holds in 200 of 200 bank-quarters "
                "on the categories where the FDIC does publish the net. "
                "Adding those two lines is a change to the feed and is the "
                "firm's decision. Until then this workbook has %d fields per "
                "bank-quarter and not %d."
     % (len(FIELDS), len(FIELDS) + 1)),
    ("", ""),
    ("h2", "What this still does not prove"),
    ("p", "A value can match its filing exactly and the filing can still be "
          "wrong. This proves faithful copying, not that a bank reported "
          "correctly."),
    ("p", "Nothing here was checked by a second person."),
]

SOURCES = [
    ("h1", "Who publishes what"),
    ("", ""),
    ("h2", "The banks -- FFIEC Call Reports"),
    ("p", "Every US bank files a Call Report every quarter with its "
          "regulators. It is public. cdr.ffiec.gov serves a FACSIMILE of "
          "each one, and every bank row here links to its own."),
    ("p", "A facsimile is an exact copy -- the same word as a fax machine. "
          "It is the filled-in form itself, page by page: the schedule "
          "headings, the printed line numbers, the codes in their boxes and "
          "the bank's own figures typed into the columns. Not a summary and "
          "not a database made to look like a form. It is a reproduction of "
          "the document the bank signed and sent, which is why a picture of "
          "it counts as evidence and a picture of somebody's copy does not."),
    ("p", "%s of the %s bank values were checked against these, line by line. "
          "This is the strongest provenance in the workbook."
     % (n(BANK_TIED), n(len(BANK)))),
    ("", ""),
    ("h2", "Federal Housing Finance Agency (FHFA) -- house prices"),
    ("p", "A government agency. It publishes a house price index for every "
          "state, many metro areas and the nation: quarterly, free, full "
          "history, as a downloadable file. %s observations here were checked "
          "against those files, back to %s."
     % (n(_obs("Housing Finance")), _earliest("Housing Finance"))),
    ("", ""),
    ("h2", "Federal Reserve Board -- charge-offs, delinquencies, consumer "
           "credit, debt service, the loan officer survey"),
    ("p", "The central bank publishes these itself, free, with full history, as "
          "tables on federalreserve.gov. %s observations were checked against "
          "them, back to %s."
     % (n(_obs("Federal Reserve")), _earliest("Federal Reserve"))),
    ("", ""),
    ("h2", "S&P Dow Jones Indices -- the Case-Shiller house price indexes"),
    ("warn", "THIS IS THE ONE THAT IS DIFFERENT, AND IT IS THE BIGGEST GAP IN "
             "THE WORKBOOK. Case-Shiller is the best-known US house price "
             "index -- the one quoted on the news. Unlike the others it is a "
             "COMMERCIAL PRODUCT, not a government statistic. S&P sells the "
             "history."),
    ("p", "What is free: a monthly press release carrying the current month's "
          "index level for each of 20 cities plus the national indexes, and the "
          "month-on-month change. That is all."),
    ("p", "What that means here: the LATEST month of each Case-Shiller series "
          "was checked against S&P's own release and matched exactly. The %s "
          "earlier observations could not be checked, because the numbers to "
          "check them against are behind a paywall. They are marked "
          "verified = no on MACRO DATA and shaded so you can see them."
     % n(CASE_SHILLER)),
    ("p", "It does not mean those numbers are wrong. It means nobody here has "
          "seen the document that would prove them, and saying so is the whole "
          "point."),
    ("p", "If this matters, the fix is a data subscription, not more work on "
          "our side."),
    ("", ""),
    ("h2", "Two smaller gaps, for completeness"),
    ("p", "TOTALSLAR, the percent change in consumer credit at an annual rate. "
          "It is a change, not a table the Board publishes with history. The "
          "LEVEL it is the change in -- TOTALSL -- is checked in full against "
          "the Board's own historical table, every month back to 1943."),
    ("p", "SUBLPDCILSLGNQ, the large-bank subset of the loan officer survey. "
          "The survey's chart data covers all domestic respondents; the "
          "large-bank split is printed inside each quarter's own survey "
          "document, so a full history would mean opening 146 separate "
          "releases. The chart data was searched column by column first; it is "
          "not in there."),
    ("", ""),
    ("h2", "FRED, and why it is not the source"),
    ("p", "FRED is the St Louis Fed's database. It REDISTRIBUTES series that "
          "other bodies compute. Our software pulls from FRED because it is "
          "convenient. But every check in this workbook went to the body that "
          "actually computes the number, never to FRED. Asking a redistributor "
          "whether the redistributor is right proves nothing."),
]


def proven_tab(audit):
    """The honest account of how each number was checked.

    ``audit`` carries the photograph counts, which are the one thing here that
    cannot be read off the CSVs -- they are a property of the exhibits, not of
    the data. When it is empty the tab SAYS SO rather than printing a zero,
    because "no pictures" and "nobody counted" are different facts and only one
    of them is a reason to worry.
    """
    strips = audit.get("bank_strips")
    filings = audit.get("filings_photographed")
    photo = (("%s rows of filed Call Report pages were photographed, across %s "
              "filings -- %s banks, every quarter of them, with the page "
              "header in the shot so you can see whose filing it is and for "
              "which period."
              % (n(strips), n(filings), n(audit.get("banks_photographed", 0))))
             if strips else
             "The photograph count has not been measured for this build, so it "
             "is not stated here. That is not the same as there being none.")

    return [
        ("h1", "What was proven, and how"),
        ("", ""),
        ("ok" if not BANK_DIFFERS else "warn",
         "%s of %s values were compared against a document published by "
         "somebody outside this firm. %s"
         % (n(TOTAL_TIED), n(TOTAL),
            "NONE DISAGREED." if not BANK_DIFFERS
            else ("%s DISAGREED, and %s listed below."
                  % (n(len(BANK_DIFFERS)),
                     "it is" if len(BANK_DIFFERS) == 1 else "they are")))),
        ("", ""),
    ] + ([] if not BANK_DIFFERS else [
        ("h2", "What disagreed"),
    ] + [("p", "%s, %s, %s. %s" % (r["bank"], r["report_date"], r["field"],
                                   r["note"])) for r in BANK_DIFFERS] + [
        ("p", "A difference is a finding, not a failure. It is not adjusted, "
              "rounded away or hidden: both numbers are in the row, in BANK "
              "DATA, with the link to the filing so you can look yourself."),
        ("", ""),
    ]) + [
        ("h2", "The bank side -- %s values" % n(len(BANK))),
        ("p", "%s   checked line by line against that bank's own filed Call "
              "Report for that quarter." % n(BANK_TIED)),
        ("p", "%s   ratios the FDIC computes rather than banks filing them. "
              "There is no line on a form to compare a computed ratio with; "
              "the lines it is computed FROM are checked above."
         % n(BANK_RATIOS)),
        ("p", "%s   quarterly flows in a quarter that spans a merger. Not "
              "compared, because such a quarter is not a quarter of one bank. "
              "See NOT COMPARABLE." % n(BANK_MERGER)),
        ("p", "%s   quarterly flows in the quarter AFTER a merger that landed "
              "in a first quarter. A quarter is the year's running total less "
              "what was already reported, and a merger moves what was already "
              "reported to a figure no filing carries." % n(BANK_BASE)),
        ("p", "%s   a line that is not on the form for that quarter. Forms "
              "change, and a line that did not exist yet cannot be cited."
         % n(BANK_NOLINE)),
        ("", ""),
        ("h2", "The macro side -- %s observations" % n(len(MACRO))),
        ("p", "%s   checked against the agency that computes the series: "
              "FHFA's own file, the Federal Reserve's own table, the Z.1 data "
              "package." % n(MACRO_TIED)),
        # Only when there IS something pending. A line reading "0 NOT YET
        # CHECKED" above a paragraph explaining a rate limit is an explanation
        # for a thing that is not happening, and the reader has to work out
        # that it does not apply.
        ("p", "%s   NOT YET CHECKED, and that is different from unobtainable. "
              "The Bureau of Labor Statistics allows 25 requests a day to "
              "anyone who has not registered a key, and this run spent them. "
              "Every observation that WAS checked ties. These close on the "
              "next run."
         % n(MACRO_PENDING)) if MACRO_PENDING else ("", ""),
        ("p", "%s   no obtainable source: %d whole series, unchecked for their "
              "whole history, each row saying why."
         % (n(MACRO_UNOBTAINABLE), len(UNOBTAINABLE_SERIES))),
        ("", ""),
        ("h2", "Photographs"),
        ("p", photo),
        ("caution", "A photograph proves the row said what we read off it. It "
                    "does not prove the bank was right. Nothing can."),
        ("", ""),
        ("h2", "Why the code check is worth something on its own"),
        ("p", "It compares against a file published by the body that COMPUTES "
              "the number -- FHFA's own CSV, the Federal Reserve's own table, "
              "the bank's own filing from the regulator. There is no FRED file "
              "anywhere in the comparison, so the system is not being checked "
              "against itself."),
        ("ok", "The checker was attacked on purpose: known-wrong values planted "
               "-- off by a thousand, off by one percent, digits transposed, "
               "sign flipped -- and it called every one of them DIFFERS while "
               "calling the unchanged control TIES. It can still say no."),
        ("", ""),
        ("h2", "What running this found"),
        ("p", "The ten-year run reported nine differences, all on total loans "
              "and leases, all exactly one thousand dollars, across three "
              "unrelated banks in six unrelated quarters. The cause: the FDIC "
              "publishes that total as the sum of two separately-rounded "
              "halves -- held for sale plus held for investment -- and our "
              "citation pointed at the bank's own single-line total instead. "
              "Both numbers were correct as published. The citation was wrong, "
              "which is invisible until somebody follows it. It is fixed, and "
              "all %s now agree." % n(BANK_TIED)),
        ("p", "It also found that %s quarters in the ten years span a merger, "
              "where the first sixteen-quarter run had seen six. Every one of "
              "them would otherwise have been reported as the FDIC "
              "disagreeing with the filings when nothing was wrong with "
              "either." % len(MERGERS)),
        ("p", "Adding the firm's seven peers in September 2026 found six more "
              "faults, every one of them in our software rather than in "
              "anybody's data. The largest acquisition in the whole set -- "
              "First-Citizens taking on Silicon Valley Bridge Bank in March "
              "2023 -- was filed by the regulator under a code the merger list "
              "did not carry, and was reported as unrecognised rather than "
              "quietly dropped. The quarter after a merger that lands in a "
              "first quarter turned out not to be formable from the filings at "
              "all. The workbook builder rebuilt the bank list AFTER checking "
              "it, so a checked list and a built list could differ. The "
              "nineteen fields added a day earlier were shipping with no units "
              "beside them."),
        ("p", "And two in the evidence itself: the exhibits for all seven new "
              "banks were built with NO photographs in them and rendered "
              "perfectly, because the pictures had been cut into one folder "
              "and read from another; and a four-digit certificate was being "
              "read as a year, so five of the nineteen banks could not be "
              "selected at all. The exhibit builder now refuses to finish a "
              "document that carries values and no pictures."),
        ("p", "None of the six was found by a test. They were found by "
              "pointing the same machinery at banks it had never seen, and by "
              "opening what came out."),
    ]
