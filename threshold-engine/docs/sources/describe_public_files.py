"""Give the five public files the description an internal template asks for.

Same keys as the templates (measure, numerator, denominator, as-of, basis,
source), plus population and call-report. Quoted from: the Federal Reserve's
Charge-Off and Delinquency Rates release (chgallsa.htm, last update 25 Aug
2026: its notes and footnote 1) and KeyBank's filed Call Report for 30 June
2026 (FFIEC 031, from cdr.ffiec.gov), which prints the form's wording on each
line. The FDIC field mapping was checked on 13 Oct 2026 against that filing
(LNCONOTH 4,200,208 = RC-C 6.d; DRCONOTH 30,566 / CRCONOTH 5,183 = RI-B 5.c;
LNRELOC 2,929,570 = RC-C 1.c.(1); DRRELOC 1,166 / CRRELOC 684 = RI-B 1.c.(1)).
"""
from pathlib import Path

FED = ("Board of Governors of the Federal Reserve System, Charge-Off and Delinquency Rates on Loans and Leases at "
       "Commercial Banks, Charge-Off Rates, All Banks, SA: https://www.federalreserve.gov/releases/chargeoff/"
       "chgallsa.htm (also FRED, series {sid}). Compiled from the FFIEC Consolidated Reports of Condition and Income "
       "(Call Reports)")
FED_POP = ("All banks: \"Banks are insured U.S.-chartered commercial banks\" (the release's notes)")
FED_RATE_NUM = ("Net charge-offs: \"gross charge-offs minus recoveries\" during the quarter (the release)")
FED_RATE_DEN = ("\"the average level of its loans outstanding over that quarter\"; each quarter's rate is "
                "multiplied by 400 to be an annual percentage rate (the release)")
FED_BASIS = ("Trailing twelve months: the mean of the four latest quarterly rates, saved to 3 decimals. Seasonally "
             "adjusted. Dated at the first day of the quarter")
FDIC = ("FDIC BankFind Suite financial data, https://api.fdic.gov/banks/financials, fields {f}; the FDIC takes them "
        "from each bank's Call Report")
FDIC_POP = "Every institution that filed a Call Report for the quarter, summed across all of them"
FDIC_BASIS = ("Trailing twelve months: the four quarters' charge-offs less recoveries, over the average of the four "
              "quarter-end balances; dated at the quarter's end. Built in an earlier session; the script was not "
              "kept, and this file has not been tied out to its source")
HELOC = ("RC-C Part I line 1.c.(1), \"Revolving, open-end loans secured by 1-4 family residential properties and "
         "extended under lines of credit\"")
OTHER_BAL = ("RC-C Part I line 6.d, \"Other consumer loans (includes single payment and installment loans other than "
             "automobile loans, and all student loans)\". It does not include line 6.b, \"Other revolving credit "
             "plans\"")
OTHER_CO = ("RI-B Part I line 5.c, \"Other (includes revolving credit plans other than credit cards and other consumer "
            "loans)\". This includes other revolving credit plans, which the balance (6.d) does not: the numerator "
            "covers more loans than the denominator. For KeyBank on 30 June 2026, other revolving credit was 268,825 "
            "($000) against 4,200,208 in 6.d")

FILES = {
    "cards_nco_ttm.csv": [
        ("measure", "Net charge-off rate on credit card loans, all banks (Federal Reserve series CORCCACBS)"),
        ("population", FED_POP),
        ("call-report", "Credit cards: balances RC-C Part I line 6.a \"Credit cards\"; charge-offs and recoveries RI-B "
                        "Part I line 5.a \"Credit cards\". The release does not name the lines it uses; these are the "
                        "Call Report's credit card lines"),
        ("numerator", FED_RATE_NUM), ("denominator", FED_RATE_DEN), ("basis", FED_BASIS),
        ("as-of", "Each quarter, 1985Q4 to 2026Q2"), ("source", FED.format(sid="CORCCACBS")),
        ("checked", "Tied out 13 Oct 2026 against the release: every quarter equals the mean of the four published "
                    "rates once rounded to 3 decimals (docs/tie-out/cards-moderate-line-2026-10-13)"),
    ],
    "mortgage_nco_ttm.csv": [
        ("measure", "Net charge-off rate on residential real estate loans booked in domestic offices, all banks "
                    "(Federal Reserve series CORSFRMACBS)"),
        ("population", FED_POP),
        ("call-report", "\"Residential real estate loans include loans secured by one- to four-family properties, "
                        "including home equity lines of credit\" (the release, footnote 1). In the Call Report: RC-C "
                        "Part I line 1.c, its 1.c.(1) revolving lines and 1.c.(2) closed-end first and junior liens. "
                        "Because it includes home equity lines, it overlaps the Home equity series"),
        ("numerator", FED_RATE_NUM), ("denominator", FED_RATE_DEN), ("basis", FED_BASIS),
        ("as-of", "Each quarter, 1991Q4 to 2026Q2"), ("source", FED.format(sid="CORSFRMACBS")),
    ],
    "home_equity_nco_ttm.csv": [
        ("measure", "Net charge-off rate on home equity lines of credit, every Call Report filer"),
        ("population", FDIC_POP),
        ("call-report", "Balance (LNRELOC): " + HELOC + ". Charge-offs and recoveries (DRRELOC, CRRELOC): RI-B "
                        "Part I line 1.c.(1), the same wording"),
        ("numerator", "Charge-offs less recoveries on home equity lines (DRRELOC - CRRELOC), four quarters"),
        ("denominator", "Home equity line balances (LNRELOC), the average of four quarter-ends"),
        ("basis", FDIC_BASIS), ("as-of", "Each quarter-end, 1992Q4 to 2026Q2"),
        ("source", FDIC.format(f="LNRELOC, DRRELOC, CRRELOC")),
    ],
    "other_consumer_as_filed_nco_ttm.csv": [
        ("measure", "Net charge-off rate on other consumer loans, as filed, every Call Report filer"),
        ("population", FDIC_POP),
        ("call-report", "Balance (LNCONOTH): " + OTHER_BAL + ". Charge-offs and recoveries (DRCONOTH, CRCONOTH): "
                        + OTHER_CO + ". Automobile loans have their own line (6.c) from 2011; before "
                        "2011 they were reported within other consumer loans, so this series breaks there"),
        ("numerator", "Other consumer charge-offs less recoveries (DRCONOTH - CRCONOTH), four quarters"),
        ("denominator", "Other consumer balances (LNCONOTH), the average of four quarter-ends"),
        ("basis", FDIC_BASIS), ("as-of", "Each quarter-end, 1992Q4 to 2026Q2"),
        ("source", FDIC.format(f="LNCONOTH, DRCONOTH, CRCONOTH")),
    ],
    "other_consumer_with_auto_nco_ttm.csv": [
        ("measure", "Net charge-off rate on other consumer loans with automobile loans added back from 2011, every "
                    "Call Report filer"),
        ("population", FDIC_POP),
        ("call-report", "Other consumer as in the as-filed series (" + OTHER_BAL + "; charge-offs " + OTHER_CO
                        + "), plus automobile loans, RC-C Part I line 6.c \"Automobile loans\" (LNAUTO) and RI-B "
                        "Part I line 5.b \"Automobile loans\" (DRAUTO, CRAUTO). Adding auto back keeps the series "
                        "on one definition across the 2011 split"),
        ("numerator", "Other consumer plus auto charge-offs less recoveries, four quarters"),
        ("denominator", "Other consumer plus auto balances, the average of four quarter-ends"),
        ("basis", FDIC_BASIS), ("as-of", "Each quarter-end, 1992Q4 to 2026Q2"),
        ("source", FDIC.format(f="LNCONOTH, DRCONOTH, CRCONOTH, LNAUTO, DRAUTO, CRAUTO")),
    ],
}

for name, notes in FILES.items():
    p = Path(__file__).resolve().parents[2] / "tests" / "data" / name
    data = [l for l in p.read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    head = ["# %s: %s" % (k, v) for k, v in notes]
    p.write_text("\n".join(head + data) + "\n", encoding="utf-8")
    print(name, len(data) - 1, "rows")
