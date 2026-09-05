"""The explanation tabs, appended to the workbook builder.

Kept in its own file because the prose is long and a heredoc mangles it.
"""
import json
import pathlib

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")

START_HERE = [
    ("h1", "Verified raw data -- twelve banks and 142 macro series"),
    ("", ""),
    ("p", "Every number in this workbook was published by somebody else -- a "
          "bank, or a government agency -- and copied here without change."),
    ("ok", "NOTHING IN THIS WORKBOOK IS CALCULATED BY OUR SOFTWARE. No ratios, "
           "no quarter-on-quarter changes, no scores, no bands. If a number is "
           "here, a bank or an agency published it in that form."),
    ("", ""),
    ("h2", "The tabs"),
    ("p", "BANK DATA         13,056 values. Twelve large US banks, sixteen quarters, every field they report."),
    ("p", "MACRO DATA        13,841 observations. 142 national and regional series."),
    ("p", "WHAT WAS PROVEN   How each number was checked -- and the difference between photographed and checked in code."),
    ("p", "LIMITS            What this data cannot do. Read this before charting."),
    ("p", "THE SOURCES       Who publishes what, including what Case-Shiller is and why it is the gap."),
    ("p", "FIELD DICTIONARY  What each bank field means, in plain English."),
    ("p", "RATIOS            Ratios worth building and the trap in each. Describes them; builds none."),
    ("p", "NOT COMPARABLE    Six quarters you should not chart as a trend, and why."),
    ("", ""),
    ("h2", "The two things to know before you chart anything"),
    ("caution", "1. UNITS. Bank values are THOUSANDS of dollars unless the row "
                "says otherwise. A bank total of 4,091,315,000 means $4.09 trillion."),
    ("caution", "2. MERGER QUARTERS. When a bank absorbs another bank, its "
                "quarterly charge-off figures for that quarter mix two banks. Six "
                "such quarters are on NOT COMPARABLE and those rows say "
                "usable_for_trend = no. One of these produced a charge-off rate of "
                "670% in an earlier version of this work. That is what a merger "
                "looks like when nobody flags it."),
    ("", ""),
    ("h2", "How to check any bank number yourself, in about a minute"),
    ("p", "1. Find the row. Note the cited_line -- for example RCFD2170 -- and the filing_url."),
    ("p", "2. Open the filing_url. It is the regulator's own copy of that bank's Call Report for that quarter."),
    ("p", "3. Search the page for the cited_line code. The number beside it is the number in this workbook."),
    ("p", "That code is an MDRM code: the Federal Reserve's permanent identifier "
          "for one line on the form. Quote it to a bank's finance team and they "
          "will know exactly which number you mean."),
]

LIMITS = [
    ("h1", "Limits -- what this data cannot do"),
    ("", ""),
    ("warn", "1. THIS IS A WINDOW, NOT A HISTORY. The macro series hold only the "
             "most recent 100 observations each. About 25 years for a quarterly "
             "series, but only about EIGHT YEARS for a monthly one -- monthly "
             "series start in early 2018. The publishers hold far more: house "
             "prices back to 1975, consumer credit to 1943, Case-Shiller to 1987. "
             "Bank data is 16 quarters, from 2022 Q3. If you want the long run it "
             "exists, and this workbook does not have it."),
    ("warn", "2. THERE IS NO VINTAGE. These are the figures as published when they "
             "were pulled. Banks amend Call Reports and agencies revise series, so "
             "a value verified today may not match the same source in six months. "
             "Nothing here records when a figure was fetched or which revision it "
             "is. Treat the whole workbook as a snapshot dated 5 September 2026."),
    ("warn", "3. PROVENANCE IS STRONGER ON THE BANK SIDE. Every one of the 13,056 "
             "bank rows names its exact line and links to the exact filing -- you "
             "can click through and put a finger on the number. On the macro side "
             "the link is the agency's landing page, not the row. The check was "
             "done against the exact file; the link is coarser than the check. The "
             "WHAT WAS PROVEN tab lists pictures of those tables with the rows "
             "ringed, which is the visual proof for the macro side."),
    ("caution", "4. EIGHT BANK FIELDS ARE RATIOS. They are the FDIC's, not ours, "
                "labelled computed_by = the FDIC. They are still ratios sitting in "
                "a raw feed. To drop them, filter BANK DATA where verified_meaning "
                "mentions the FDIC calculating them -- 1,536 rows."),
    ("caution", "5. THE TWELVE BANKS ARE NOT A LIKE-FOR-LIKE PEER GROUP. Two are "
                "custody banks and two are broker-dealer banks. Their balance "
                "sheets are shaped nothing like a commercial lender's, and a peer "
                "ranking that mixes them will mislead."),
    ("", ""),
    ("h2", "What this still does not prove"),
    ("p", "A value can match its filing exactly and the filing can still be wrong. "
          "This proves faithful copying, not that a bank reported correctly."),
    ("p", "Nothing here was checked by a second person."),
]

SOURCES = [
    ("h1", "Who publishes what"),
    ("", ""),
    ("h2", "The banks -- FFIEC Call Reports"),
    ("p", "Every US bank files a Call Report every quarter with its regulators. It "
          "is public. cdr.ffiec.gov serves an image of the exact form each bank "
          "filed, and every bank row here links to its own."),
    ("p", "All 13,056 bank values were checked against these. This is the "
          "strongest provenance in the workbook."),
    ("", ""),
    ("h2", "Federal Housing Finance Agency (FHFA) -- house prices"),
    ("p", "A government agency. It publishes a house price index for every state, "
          "many metro areas and the nation: quarterly, free, full history, as a "
          "downloadable file. 6,800 observations here were checked against those "
          "files."),
    ("", ""),
    ("h2", "Federal Reserve Board -- charge-offs, delinquencies, consumer credit, "
           "debt service, the loan officer survey"),
    ("p", "The central bank publishes these itself, free, with full history, as "
          "tables on federalreserve.gov. 4,441 observations were checked against "
          "them. These are the tables you can see with your own eyes -- the "
          "pictures are listed on WHAT WAS PROVEN."),
    ("", ""),
    ("h2", "S&P Dow Jones Indices -- the Case-Shiller house price indices"),
    ("warn", "THIS IS THE ONE THAT IS DIFFERENT, AND IT IS THE BIGGEST GAP IN THE "
             "WORKBOOK. Case-Shiller is the best-known US house price index -- the "
             "one quoted on the news. Unlike the others it is a COMMERCIAL "
             "PRODUCT, not a government statistic. S&P sells the history."),
    ("p", "What is free: a monthly press release carrying the current month's "
          "index level for each of 20 cities, and the month-on-month change. That "
          "is all."),
    ("p", "What that means here: the LATEST month of each Case-Shiller series was "
          "checked against S&P's own release and matched exactly. The 2,200 "
          "earlier observations could not be checked, because the numbers to check "
          "them against are behind a paywall. They are marked verified = no on "
          "MACRO DATA and shaded so you can see them."),
    ("p", "It does not mean those numbers are wrong. It means nobody here has seen "
          "the document that would prove them, and saying so is the whole point."),
    ("p", "If this matters, the fix is a data subscription, not more work on our "
          "side."),
    ("", ""),
    ("h2", "FRED, and why it is not the source"),
    ("p", "FRED is the St Louis Fed's database. It REDISTRIBUTES series that other "
          "bodies compute. Our software pulls from FRED because it is convenient. "
          "But every check in this workbook went to the body that actually "
          "computes the number, never to FRED. Asking a redistributor whether the "
          "redistributor is right proves nothing."),
]


def proven_tab(audit):
    """The honest account of how each number was checked."""
    a = audit
    return [
        ("h1", "What was proven, and how"),
        ("", ""),
        ("warn", "THE HONEST ANSWER FIRST. 22,819 values were checked against the "
                 "document that published them, and none disagreed. But they were "
                 "NOT all checked the same way, and only a minority were checked "
                 "by photograph. The difference matters and is set out below."),
        ("", ""),
        ("h2", "Two kinds of checking"),
        ("p", "PHOTOGRAPHED -- an image of the source document AND an image of the "
              "workbook cell, both embedded in a PDF exhibit, with the row ringed. "
              "A person can look at the two pictures and see the same number. "
              "Roughly %s values." % a.get("photographed", "see below")),
        ("p", "CHECKED IN CODE -- the agency's own file was downloaded, parsed, "
              "and every number compared with the workbook in software. Real, "
              "repeatable, and against a genuinely independent document -- but "
              "there is no picture of each individual value. Roughly %s values."
              % a.get("programmatic", "see below")),
        ("p", "NOT CHECKED -- %s values. Case-Shiller history behind a paywall, "
              "two consumer-credit series with no historical table, one survey "
              "split published one quarter at a time, plus the FDIC's own computed "
              "ratios which are not a line on any form."
              % a.get("unverified", "4,078")),
        ("", ""),
        ("h2", "Why the code check is still worth something"),
        ("p", "It compares against a file published by the body that computes the "
              "number -- FHFA's own CSV, the Federal Reserve's own HTML table, the "
              "bank's own XBRL filing. It is not the software checking itself. If "
              "a number had been wrong, the comparison would have said so, and on "
              "22,819 comparisons it never did."),
        ("p", "What it is not is a photograph of each one. If you want a picture "
              "of a specific value, the exhibits under docs/tie-out/ have them for "
              "the most recent period, and the pictures below show the tables "
              "every other comparison was made against."),
        ("", ""),
        ("h2", "Pictures of the macro source tables, with the proved rows ringed"),
        ("p", "These are in docs/tie-out/macro-sources/. They are the answer to "
              "'show me that it matched' for the macro side, where the row-level "
              "link is only a landing page."),
    ]
