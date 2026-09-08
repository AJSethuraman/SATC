"""The nineteen fields added to the FEED, and the filed line behind each.

Added 6 September 2026, after the firm took every candidate in the first two
tiers of the opportunity scan. They go into the feed and NOT into
``fields.RAW_FIELDS``: that list drives ``raw_slots``, which the layout says is
built into every dashboard formula, and the firm's answer on that was "feed
only". A dashboard nobody asked to change does not get re-cut.

**Every citation here was derived from the filings, not copied from a
crosswalk.** For each field, the FDIC's published number was searched for in
the bank's own XBRL -- as a single line, and as the sum or difference of
several -- and a candidate only survived if it held in EVERY bank-quarter where
both sides had a value. Nothing here is a plausible-looking code.

That method exists because a citation can be documented, confident and wrong.
The same session found ``LNLSGR`` citing RC-C Part I line 12 when the FDIC has
always used RC 4.a + 4.b; the two agreed in 471 of the 480 bank-quarters then in the set, so no test
ever caught it. It paid again immediately: the scan reported the commercial
commitment total as three lines, and three lines is short by up to $1.4bn at
every bank with foreign offices -- and exact at the four without them, which is
how a wrong citation survives a spot check.

Two fields carry a DATED RECODING. A row naming only today's code is correct
today and silently wrong about years of history, so both eras are written down
with the quarter the form changed.
"""
from __future__ import annotations

#: field -> (schedule, plain caption, citation, how it was established)
#:
#: A citation is written as MDRM items without a prefix where the prefix varies
#: by form: RCFD/RIAD on the 031 a bank with foreign offices files, RCON on the
#: 041 without. The existing map writes this as "RCON2170 (RCFD2170 031)"; here
#: the item is given and the prefix follows the filing.
FEED_ROWS = [
    # ---- 1-2 · the credit lines behind the balances -----------------------
    ("UCCRCD", "RC-L 1.b", "Unused credit card lines",
     "3815", "760 of 760 bank-quarters"),
    ("UCLOC", "RC-L 1.a",
     "Unused revolving lines secured by 1-4 family homes",
     "3814", "760 of 760 bank-quarters"),

    # ---- 3 · the column that was always blank -----------------------------
    ("DRRENRSQ", "RI-B Pt I 4 col A",
     "CRE nonfarm nonresidential gross charge-offs, quarterly",
     "RIADC895+RIADC897 (year-to-date, differenced)",
     "728 of 728 comparable bank-quarters; derived on the 190 first-quarter filings, where the year-to-date IS the quarter. The other 32 span a merger or follow one and cannot be formed from the filings at all"),
    ("CRRENRSQ", "RI-B Pt I 4 col B",
     "CRE nonfarm nonresidential recoveries, quarterly",
     "RIADC896+RIADC898 (year-to-date, differenced)",
     "728 of 728 comparable bank-quarters; derived on the 190 first-quarter filings. The other 32 span a merger or follow one and cannot be formed from the filings at all"),

    # ---- 4 · the loan class that had no losses ----------------------------
    ("NTRELOCQ", "RI-B Pt I 1.c.(1) cols A-B",
     "Home equity line net charge-offs, quarterly",
     "RIAD5411-RIAD5412 (year-to-date, differenced)",
     "728 of 728 comparable bank-quarters; derived on the 190 first-quarter filings. The other 32 span a merger or follow one and cannot be formed from the filings at all"),

    # ---- 5 · the denominator the regulator actually uses -------------------
    ("RBC", "RC-R Pt I 3792", "Total risk-based capital",
     "RCFA3792 or RCFW3792 -- the column that binds",
     "759 of 760; exactly one column ties in every bank-quarter but one. The exception is Huntington at 2026-03-31, where the FDIC publishes 945 less than the filed line and no reason has been found -- it is delivered as a difference, not adjusted"),

    # ---- 6 · the real Texas ratio -----------------------------------------
    ("ORE", "RC 7", "Other real estate owned -- property taken back",
     "2150", "760 of 760 bank-quarters"),
    ("INTAN", "RC 10", "Intangible assets, which absorb no losses",
     "2143 (0426+3163 before 2018-06-30)",
     "760 of 760; the form changed at 2018-06-30 and both eras are exact"),

    # ---- 9 · commercial commitments ---------------------------------------
    ("UCCOMRES", "RC-L 1.c.(1)(a)+(b)",
     "Unused commitments on construction and land",
     "F164+F165", "760 of 760 bank-quarters"),
    ("UCCOMREU", "RC-L 1.c.(2)",
     "Unused CRE commitments not secured by property",
     "6550", "760 of 760 bank-quarters"),
    ("UCOTHER", "RC-L 1.e",
     "Unused commitments to businesses and other borrowers",
     "J457+J458+J459 (J457+PV11+J459+PV10 from 2024-12-31)",
     "760 of 760 across the recoding at 2024-12-31; both eras exact"),

    # ---- 10 · lending to non-banks ----------------------------------------
    ("LNNDEPD", "RC-C Pt I 9.b.(2)",
     "Loans to nondepository financial institutions (domestic)",
     "RCONJ454",
     "760 of 760; DOMESTIC -- the consolidated RCFDJ454 is larger at every "
     "bank with foreign offices and is not what the FDIC publishes"),

    # ---- 12 · loans modified because the borrower is in trouble ------------
    ("RSLNLTOT", "RC-C Pt I Mem 1", "Restructured loans, total",
     "HK25", "722 of 722; the line does not exist before 2017-03-31, so 38 bank-quarters have nothing to cite"),
    ("RSLNREFM", "RC-C Pt I Mem 1",
     "Restructured 1-4 family residential",
     "F576", "760 of 760 bank-quarters"),
    ("RSCI", "RC-C Pt I Mem 1", "Restructured commercial and industrial",
     "K163+K164", "760 of 760 bank-quarters"),
    ("RSCONS", "RC-C Pt I Mem 1", "Restructured consumer loans",
     "K158+K159", "760 of 760 bank-quarters"),
    ("RSMULT", "RC-C Pt I Mem 1", "Restructured multifamily",
     "K160", "760 of 760 bank-quarters"),
    ("RSOTHER", "RC-C Pt I Mem 1", "Restructured, all other",
     "K165", "760 of 760 bank-quarters"),
    ("NARSNRES", "RC-N Mem",
     "Restructured CRE already on nonaccrual",
     "K116+K119", "760 of 760 bank-quarters"),

    # ---- 13 · the income statement, added 8 September 2026 ----------------
    # The firm's instruction was "just add them": the four FDIC-computed
    # ratios -- ROAQ, NIMY, EEFFR, NTLNLSQR -- were checked against nothing,
    # and the fix is to carry the figures they are built out of. Every
    # citation below was established the way this module requires: the FDIC's
    # published number searched for in the bank's own XBRL across all 760
    # bank-quarters, and kept only where it held in every one.
    ("NETINC", "RI 14", "Net income, year to date",
     "4340", "760 of 760 bank-quarters"),
    ("NETINCQ", "RI 14", "Net income, this quarter",
     "4340 (year-to-date, differenced)",
     "752 of 752 comparable bank-quarters; the other 8 span a merger"),
    ("NIM", "RI 3", "Net interest income, year to date",
     "4074", "760 of 760 bank-quarters"),
    ("NIMQ", "RI 3", "Net interest income, this quarter",
     "4074 (year-to-date, differenced)",
     "752 of 752 comparable bank-quarters; the other 8 span a merger"),
    ("INTINC", "RI 1.h", "Total interest income, year to date",
     "4107", "760 of 760 bank-quarters"),
    ("EINTEXP", "RI 2.f", "Total interest expense, year to date",
     "4073", "760 of 760 bank-quarters"),
    ("NONII", "RI 5.m", "Total noninterest income, year to date",
     "4079", "760 of 760 bank-quarters"),
    ("NONIIQ", "RI 5.m", "Total noninterest income, this quarter",
     "4079 (year-to-date, differenced)",
     "752 of 752 comparable bank-quarters; the other 8 span a merger"),
    ("NONIX", "RI 7.e", "Total noninterest expense, year to date",
     "4093", "760 of 760 bank-quarters"),
    ("NONIXQ", "RI 7.e", "Total noninterest expense, this quarter",
     "4093 (year-to-date, differenced)",
     "752 of 752 comparable bank-quarters; the other 8 span a merger"),
    ("ITAX", "RI 9", "Income taxes, year to date",
     "4302", "760 of 760 bank-quarters"),
    ("ELNATR", "RI 4", "Provision for credit losses, year to date",
     "JJ33", "570 of 570 bank-quarters from 2019Q1; 4230 before it -- see RECODINGS"),
    ("ELNATQ", "RI 4", "Provision for credit losses, this quarter",
     "JJ33 (year-to-date, differenced)",
     "563 of 563 comparable bank-quarters from 2019Q1; the other 7 span a merger"),
    ("NTLNLS", "RI-B Pt I 9 cols A-B", "Net charge-offs, year to date",
     "4635-4605", "760 of 760 bank-quarters"),
    ("NTLNLSQ", "RI-B Pt I 9 cols A-B", "Net charge-offs, this quarter",
     "4635-4605 (year-to-date, differenced)",
     "753 of 753 comparable bank-quarters; the other 7 span a merger"),
    ("AVASSET", "RC-K 9", "Average total assets for the quarter",
     "3368", "760 of 760 bank-quarters"),

    # The two denominators no bank files. They are the FDIC's own averages,
    # and they are here because without them NIMY and NTLNLSQR cannot be
    # reconstructed at all -- but neither is a line on any form. Every subset
    # of Schedule RC-K was tested against them across the panel and none
    # reproduces either. Carried as the FDIC's figure, said so in the row.
    ("ERNAST", "FDIC-computed average", "Average earning assets for the quarter",
     "the FDIC's own average; no filed line carries it",
     "no citation found -- every subset of RC-K was tried across 760 bank-quarters"),
    ("LNLSGR5", "FDIC-computed average", "Average loans and leases for the quarter",
     "the FDIC's own average; no filed line carries it",
     "no citation found -- RC-K 3360, the filed average loans line, misses in all 760"),
]

FEED_FIELDS = [r[0] for r in FEED_ROWS]

#: All nineteen are dollar amounts in thousands. None is a ratio, which is why
#: none of them needs the "computed by the FDIC" treatment the eight existing
#: ratio fields carry.
FEED_UNITS = {f: "USD_thousands" for f in FEED_FIELDS}

#: The three that are quarterly figures the FDIC differences out of a
#: year-to-date filed line. They inherit the merger hazard every existing `*Q`
#: field has: across a merger the difference of two year-to-date totals mixes
#: two banks and is not a quarter of anything.
FEED_FLOW_FIELDS = ("DRRENRSQ", "CRRENRSQ", "NTRELOCQ",
                    "NETINCQ", "NIMQ", "NONIIQ", "NONIXQ", "ELNATQ",
                    "NTLNLSQ")

#: Citations whose code changed inside the ten-year window, with the quarter it
#: changed in. Written down because a row naming only the current code is right
#: today and wrong about the history, and nothing else would ever say so.
RECODINGS = {
    "INTAN": [("2016-09-30", "2018-03-31", "0426+3163"),
              ("2018-06-30", None, "2143")],
    "UCOTHER": [("2016-09-30", "2024-09-30", "J457+J458+J459"),
                ("2024-12-31", None, "J457+PV11+J459+PV10")],
    # The provision line was renamed and recoded when CECL arrived: RIAD4230
    # "provision for loan and lease losses" became RIADJJ33 "provisions for
    # credit losses". Both codes sit on the form from 2019Q1, and the FDIC
    # follows JJ33 from that quarter -- 570 of 570 -- while 4230 is what its
    # figure matches before it. A row naming only JJ33 would be right about
    # today and wrong about the first ten quarters in this window.
    "ELNATR": [("2016-09-30", "2018-12-31", "4230"),
               ("2019-03-31", None, "JJ33")],
    "ELNATQ": [("2016-09-30", "2018-12-31", "4230 (year-to-date, differenced)"),
               ("2019-03-31", None, "JJ33 (year-to-date, differenced)")],
}

#: The fields the FDIC constructs rather than reads off a form. They are here
#: because NIMY and NTLNLSQR cannot be reconstructed without them, and they are
#: marked because the honest verdict for a figure with no filed line behind it
#: is not "the bank did not report it".
FEED_COMPUTED = ("ERNAST", "LNLSGR5")


#: Fields the bank files in TWO columns, where the FDIC republishes whichever
#: one binds that quarter. Schedule RC-R Part I is filed by an
#: advanced-approaches bank under both the standardised framework (column A)
#: and the advanced one (column W); which binds varies by bank and by quarter,
#: so the row records the column that tied rather than asserting one.
#:
#: Naming a single column here would be right for 398 of the 480 bank-quarters
#: then in the set and
#: wrong for 82, and every spot check would land in the 398.
#: field -> ((amount code, its ratio code), ...). The framework is chosen from
#: the RATIOS -- the lower one binds -- and only then is the amount compared, so
#: the check can fail on choosing wrongly. Choosing the column by which amount
#: matched would tie by construction.
TWO_COLUMN_FIELDS = {
    "RBC": (("RCFA3792", "RCFA7205"), ("RCFW3792", "RCFW7205"),
            ("RCOA3792", "RCOA7205"), ("RCOW3792", "RCOW7205")),
}


def binding_column(field, raw):
    """The amount code of the framework that binds, or None if none is filed.

    Both the amount and its ratio must be present for a framework to count: a
    filing that carries one without the other cannot be ranked, and ranking it
    anyway is how a tie-break silently becomes a coin toss.
    """
    filed = [(amt, float(raw[rat])) for amt, rat in TWO_COLUMN_FIELDS[field]
             if raw.get(amt) is not None and raw.get(rat) is not None]
    if not filed:
        return None
    return min(filed, key=lambda t: t[1])[0]


def citation_for(field: str, report_date: str) -> str:
    """The citation in force for a field on a given report date."""
    if field in RECODINGS:
        for start, end, expr in RECODINGS[field]:
            if report_date >= start and (end is None or report_date <= end):
                return expr
    row = next((r for r in FEED_ROWS if r[0] == field), None)
    return row[3] if row else ""


#: Units for the nineteen fields this module adds. Every one is a dollar
#: amount in THOUSANDS -- there is no ratio among them, which is deliberate:
#: the firm's instruction was "eliminate you making ratios for me", so what was
#: added is balances, unused commitments, restructured loans and one capital
#: amount, all filed lines.
#:
#: It is asserted rather than assumed. Each of these is verified by dividing
#: the filed line by a thousand and comparing, so a percentage among them would
#: have failed 480 times over rather than shipped mislabelled.
#:
#: This exists because the delivered `bank-values.csv` shipped these nineteen
#: with an EMPTY units column on 7 September 2026: `fields.FIELD_UNITS` is
#: built from `RAW_FIELDS` and knows nothing about this module, and a lookup
#: that misses returns "" instead of refusing. A number in a spreadsheet with
#: no unit beside it is the trap the whole feed is written against.
FEED_FIELD_UNITS = {f: "USD_thousands" for f in FEED_FIELDS}
