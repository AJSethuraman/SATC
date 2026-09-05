"""Plain English for the tie-out, alongside the codes rather than instead of them.

The tie-out map is correct and was unreadable: `NTCONOTQ_BOOK 4.13 RI-B Pt I 3.d
(B514-B515)/K207 [V] comp.` is exactly right and tells a reader who does not
live in MDRM codes nothing at all. Stripping the codes out would be worse -- they
are how you search for the line, ask someone about it, or recognise it on the
FFIEC form. So both, always: the term, then what it means.

**The codes are not decoration.** MDRM is the Federal Reserve's identifier for a
single filed line; quoting `RCON1407` to a bank's finance team gets you the exact
number they filed. The plain sentence is what gets you to the point of knowing
which line to ask about.

Most of these are systematic rather than special. Forty of the fifty-three are
`<measure><loan class>` -- `P3CRCDR` is "30-89 days past due" x "credit cards" --
so their descriptions are BUILT from the two halves rather than written out one
by one. Fifty-three hand-written sentences drift; two tables and a rule cannot.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

#: Terms the tie-out uses that a reader may not have met. Printed once at the
#: top of a tie-out rather than repeated per row.
GLOSSARY = [
    ("Call Report",
     "the quarterly financial report every US bank must file with its "
     "regulators. FFIEC forms 031, 041 and 051 -- which one depends on the "
     "bank's size and whether it has foreign offices."),
    ("Schedule / line",
     "where on that form the number sits. 'RC-N line 9 column B' is a "
     "specific box on a specific page, the same for every bank."),
    ("MDRM code",
     "the Federal Reserve's permanent identifier for one filed line, like "
     "RCON1407. Quote it to a bank's finance team and they know exactly which "
     "number you mean. RCON = domestic offices, RCFD = consolidated including "
     "foreign, RCOA = the capital schedule."),
    ("Facsimile",
     "an image of the actual form the bank filed, on the regulator's own "
     "site. The link below opens this bank's, for this quarter."),
    ("Still accruing",
     "the loan is late, but the bank still expects to collect and is still "
     "booking the interest."),
    ("Nonaccrual",
     "the bank has stopped booking interest because it no longer expects to "
     "collect in full. Worse than 'late'."),
    ("Noncurrent",
     "90+ days past due AND still accruing, plus everything on nonaccrual. "
     "The standard regulatory measure of loans that have gone bad."),
]

#: The measurement half of a patterned metric id.
MEASURE: Dict[str, Tuple[str, str]] = {
    "P3": ("30-89 days past due",
           "an early-warning bucket -- late, but not yet seriously so"),
    "P9": ("90+ days past due, still accruing",
           "seriously late, though the bank still expects to collect"),
    "NA": ("on nonaccrual",
           "the bank has stopped booking interest -- it does not expect to "
           "collect in full"),
    "NT": ("net charge-offs, annualised",
           "loans actually written off during the quarter, less anything "
           "recovered, scaled to a yearly rate"),
}

#: The loan-class half.
LOAN_CLASS: Dict[str, str] = {
    "CRCD":   "credit cards",
    "AUTO":   "car loans",
    "CONOTH": "other consumer loans",
    "RERES":  "home loans (1-4 family)",
    "RELOC":  "home equity lines",
    "RECONS": "construction and land loans",
    "RENRES": "commercial property loans (offices, shops, warehouses)",
    "REMULT": "apartment-building loans (5+ units)",
    "CI":     "business loans",
    "LNLS":   "all loans",
}

#: FDIC truncates the loan-class name inside the charge-off ids to keep them
#: short, so `NTCONOTQ_BOOK` carries `CONOT` where every other metric spells
#: `CONOTH`. Mapped explicitly rather than by loosening the prefix match: a
#: looser rule would happily map `NTRECONQ_BOOK` onto `RERES` and produce a
#: confident, wrong sentence about the wrong loan book.
CLASS_ALIAS: Dict[str, str] = {
    "CONOT": "CONOTH",     # NTCONOTQ_BOOK -> other consumer
    "RECON": "RECONS",     # NTRECONQ_BOOK -> construction and land
    "RENRE": "RENRES",     # NTRENREQ_BOOK -> commercial property
    "REMUL": "REMULT",     # NTREMULQ_BOOK -> apartment buildings
}

#: The metrics that are not built from the pattern above.
SPECIAL: Dict[str, str] = {
    "NCLNLSR":
        "Noncurrent loans as a share of all loans. Money the bank is owed "
        "that has stopped being paid properly -- the headline asset-quality "
        "number.",
    "PD3089R":
        "Loans 30-89 days late as a share of all loans. The early-warning "
        "bucket: these have not gone bad yet, and a rise here tends to show "
        "up in the noncurrent number two or three quarters later.",
    "LNATRESR":
        "The money set aside for expected loan losses, as a share of all "
        "loans. Higher is not simply better -- it means either more caution "
        "or a worse book.",
    "LNRESNCR":
        "How far the money set aside stretches to cover the loans that have "
        "already gone bad. 150% means the reserve is one and a half times "
        "the bad loans; below 100% means it is not enough to cover them.",
    "TEXAS":
        "Bad loans measured against the money available to absorb them "
        "(equity plus reserves). A rough solvency stress gauge -- the higher, "
        "the less room. NOTE: a variant, not the canonical Texas ratio.",
    "RBC1AAJ":
        "Tier 1 leverage ratio -- core capital as a share of assets, with no "
        "adjustment for how risky those assets are. A regulatory minimum.",
    "RBCRWAJ":
        "Total capital as a share of assets weighted by how risky each one "
        "is. Blank for banks that elected the simplified regime.",
    "EQV":
        "Equity as a share of assets. The simplest measure of how much of "
        "the bank is funded by its owners rather than borrowed.",
    "ROAQ":
        "Profit as a share of assets, annualised. How much the bank earns on "
        "what it holds.",
    "NIMY":
        "Net interest margin -- the gap between what the bank earns on loans "
        "and pays on deposits, as a share of earning assets.",
    "EEFFR":
        "Efficiency ratio: running costs as a share of revenue. LOWER is "
        "better here, unlike most of this list.",
    "LNDEPR":
        "Loans as a share of deposits. How much of the deposit base is lent "
        "out; higher means less spare liquidity.",
    "BRODEPR":
        "Brokered deposits as a share of deposits. Deposits bought through "
        "intermediaries rather than gathered from the bank's own customers -- "
        "they tend to leave faster when rates move.",
    "CRECONR":
        "Commercial property lending as a share of capital. Regulators watch "
        "concentration here because these loans move together in a downturn. "
        "NOTE: uses a documented proxy denominator, not the guidance one.",
    "UNINSDEPR":
        "Estimated deposits above the FDIC insurance limit, as a share of "
        "deposits. Uninsured money is the money most likely to run.",
    "UNRLZCAPR":
        "Unrealised losses on securities, against capital. Paper losses the "
        "bank has not taken yet -- the 2023 regional-bank problem.",
    "FHLBASSR":
        "Federal Home Loan Bank borrowings as a share of assets. A wholesale "
        "funding source; a sharp rise can mean deposits are leaving.",
}


#: The landed dollar fields -- the raw Call Report lines the ratios are built
#: from. Added 5 September 2026 after the firm read a provenance row: "i dont
#: know what RCON2200 means without looking it up so lets start making things
#: have plain definitions in addition to the code." Thousands of dollars in the
#: workbook; the FDIC lands them in thousands.
FIELD = {
    "ASSET": "Total assets -- everything the bank owns, at book value.",
    "DEP": "Total deposits -- the money customers have placed with the bank "
           "(domestic and, for a bank with foreign offices, foreign).",
    "LNLSGR": "Gross loans and leases -- all lending before subtracting the "
              "money set aside for losses.",
    "LNLSNET": "Net loans and leases -- gross loans less the allowance for "
               "losses; what the balance sheet carries.",
    "BRO": "Brokered deposits -- deposits bought through intermediaries "
           "rather than gathered from the bank's own customers.",
    "EQ": "Total equity capital -- the owners' stake; assets minus "
          "liabilities.",
    "NCLNLS": "Noncurrent loans -- loans 90 or more days late plus loans on "
              "nonaccrual (interest no longer being booked).",
    "LNATRES": "Allowance for loan and lease losses -- the money set aside "
               "for loans expected to go bad.",
    "DEPUNINS": "Estimated uninsured deposits -- the part of deposits above "
                "the FDIC insurance limit.",
    "DEPINS": "Estimated insured deposits -- the part of deposits within the "
              "FDIC insurance limit.",
    "OTHBFHLB": "Federal Home Loan Bank advances -- borrowings from the "
                "FHLB, a wholesale funding source.",
    "LNRECONS": "Construction and land development loans.",
    "LNRENRES": "Loans on commercial property (offices, shops, warehouses) "
                "-- 'nonfarm nonresidential' on the form.",
    "LNREMULT": "Loans on apartment buildings of five or more units "
                "('multifamily').",
    "LNRERES": "Loans on one-to-four family homes -- mortgages and home "
               "equity lines.",
    "LNCI": "Commercial and industrial loans -- lending to businesses not "
            "secured by property.",
    "LNCRCD": "Credit card balances outstanding.",
    "LNAUTO": "Auto loans to individuals.",
    "LNCONOTH": "Other consumer loans -- personal loans and instalment "
                "credit that are not cards or autos.",
    "SCHA": "Held-to-maturity securities at amortised cost -- bonds the bank "
            "intends to keep, carried at what it paid.",
    "SCHF": "Held-to-maturity securities at fair value -- the same bonds at "
            "today's market price.",
    "SCAA": "Available-for-sale securities at amortised cost -- bonds the "
            "bank may sell, at what it paid.",
    "SCAF": "Available-for-sale securities at fair value -- the same bonds "
            "at today's market price.",
}

#: The two denominators, said in words. Which one a rate uses is the whole
#: difference between two numbers that otherwise look identical, so it is
#: never left implied.
#:
#: Established live on 5 September 2026 against the FDIC's published values
#: (Capital One, CERT 4297, 2025-12-31): FDIC `P3CRCDR` = 0.861, which is
#: card 30-89 over TOTAL ASSETS (0.861), not over the card book (2.215).
#: Every one of the FDIC's fifteen landed class rates behaves this way.
OVER_BOOK = ("as a share of that loan book -- this template's own "
             "calculation, which is the question a credit reviewer asks")
OVER_ASSETS = ("as a share of the bank's TOTAL ASSETS -- the FDIC's own "
               "denominator for this published field, not the size of the "
               "loan book, so it reads far smaller than a book rate and is "
               "not comparable with one")


def describe(metric_id: str) -> Optional[str]:
    """One plain sentence for a metric id, or None when we genuinely have none.

    Returning None rather than a guess matters: an invented description of a
    regulatory ratio is worse than a blank, because it reads as authority.

    A class rate always says which denominator it stands on. `<field>_BOOK` is
    ours, over the class; a bare FDIC id is the FDIC's, over total assets.
    """
    if metric_id in SPECIAL:
        return SPECIAL[metric_id]
    if metric_id in FIELD:
        return FIELD[metric_id]

    if metric_id.endswith("_BOOK"):
        body, denominator = metric_id[:-len("_BOOK")], OVER_BOOK
    else:
        body = metric_id[:-1] if metric_id.endswith("R") else metric_id
        denominator = OVER_ASSETS
    for prefix, (measure, gloss) in MEASURE.items():
        if not body.startswith(prefix):
            continue
        rest = body[len(prefix):]
        if prefix == "NT" and rest.endswith("Q"):        # NTCRCDQ_BOOK etc.
            rest = rest[:-1]
        klass = LOAN_CLASS.get(CLASS_ALIAS.get(rest, rest))
        if klass:
            return ("%s: %s, %s. %s."
                    % (klass.capitalize(), measure, denominator,
                       gloss.capitalize()))
    return None
