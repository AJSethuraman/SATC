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
    return [
        ("h1", "What was proven, and how"),
        ("", ""),
        ("warn", "THE HONEST ANSWER FIRST. 22,819 values were checked against the "
                 "document that published them and none disagreed -- but they "
                 "were NOT all checked the same way, and only a small minority "
                 "were checked by eye. These counts come from an independent "
                 "audit of the scripts and images, not from me."),
        ("", ""),
        ("h2", "How the 26,897 values break down"),
        ("p", "773   PHOTOGRAPHED, BOTH SIDES. An image of the source document "
              "AND an image of the workbook cell, both embedded in a PDF "
              "exhibit, with the row ringed in red. A person can look at the "
              "two pictures and see the same number."),
        ("p", "82    PHOTOGRAPHED, ONE SIDE. The workbook cell was photographed "
              "but that period does not appear in any source image."),
        ("p", "21,964  CHECKED IN CODE ONLY. The agency's own file was "
              "downloaded, parsed, and every number compared with the workbook "
              "in software. No picture of that individual value exists."),
        ("p", "4,078  NOT CHECKED. 1,536 ratios the FDIC computes rather than "
              "banks filing them, 2,500 with no free historical source, and 42 "
              "merger-quarter flows."),
        ("", ""),
        ("warn", "So: about 3 percent of the data has a picture. The photographic "
                 "layer is ONE PERIOD DEEP -- the newest quarter for banks and "
                 "the newest observation for the macro series. Fifteen of the "
                 "sixteen bank quarters and 13,699 of the 13,841 macro "
                 "observations have never been photographed on either side."),
        ("", ""),
        ("h2", "Why the code check is still worth something"),
        ("p", "It compares against a file published by the body that COMPUTES "
              "the number -- FHFA's own CSV, the Federal Reserve's own table, "
              "the bank's own filing from the regulator. The audit confirmed "
              "there is no FRED file anywhere in the comparison, so the system "
              "is not being checked against itself."),
        ("ok", "The audit then tried to make the comparison produce a FALSE tie, "
               "four ways. Matching a series against a different series on the "
               "same date: 0 false ties out of 11,341. Matching against the "
               "wrong period: 1.4%. No series has a constant source-side value. "
               "Spot checks mid-history matched exactly. It could not fool it."),
        ("ok", "The bank checker was then mutation-tested directly: ten known-"
               "wrong values planted -- off by a thousand, off by one percent, "
               "digits transposed, sign flipped -- and it called all ten "
               "DIFFERS, and the unchanged control TIES. It can still say no."),
        ("", ""),
        ("h2", "Two weaknesses in the tie count, stated plainly"),
        ("caution", "2,178 of the 11,478 bank ties (19%) are ZERO MATCHED "
                    "AGAINST ZERO -- categories where a bank has no exposure. "
                    "True, and the weakest possible form of agreement."),
        ("caution", "The macro source pictures ring a ROW, and a row holds "
                    "eleven columns. The picture shows you where the number "
                    "lives; it does not circle the individual figure."),
        ("", ""),
        ("h2", "The pictures"),
        ("p", "docs/tie-out/macro-sources/ -- ten images of the agencies' own "
              "tables with the proved rows ringed, including the Federal "
              "Reserve charge-off and delinquency tables. 55 series map to one."),
        ("p", "docs/tie-out/banks-12-2026-06-30/ -- twelve PDFs, one per bank, "
              "824 pages, every line with its workbook cell and its filing row "
              "as images."),
        ("p", "docs/tie-out/fred-142-series-2026-09-05/ -- the macro exhibit, "
              "142 workbook cells photographed."),
        ("", ""),
        ("h2", "The one sentence to keep"),
        ("warn", "Every one of these was compared against the agency's own file "
                 "by software, and the software was attacked and could not be "
                 "fooled. But eyes-on-the-page proof covers the most recent "
                 "period only -- 862 figures. The other 21,957 are a code "
                 "comparison you have to trust the code for."),
    ]
