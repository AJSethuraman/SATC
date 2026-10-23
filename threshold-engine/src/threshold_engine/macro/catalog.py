"""The series the tool reads: the report's "ready to rate" group, and its
"usable with care" group.

Every entry is a fact about a public series, checked at the publisher or on
FRED on 15 Oct 2026: who publishes it, where it comes from, how often, from
when, under what terms, and the breaks a reader must know. Nothing is rated
(the firm, 22 Oct 2026: "We are not rating these. At most these are
directional"); every series is read the same way, on where its level sits in
its own history and on whether its change is inside its normal movement.
"stress" records which way the research says a series signals stress, where
it says so, and is shown to the reader as that and nothing more.

"report" names the section of docs/macro/reports/Macro risk indicators for
lending.md that put the series on the list.

How each is read follows the report's rules by type of series. "change_in"
says whether its change is counted in points (a rate, a spread, an index
around zero) or as a percent of the earlier reading (a level that grows).
"position" is empty when the series' place in its own history means
something, and otherwise says why not; those are read on their change only.
DERIVED holds the readings built from two series: house prices against
income and the mortgage rate over the 10-year Treasury (the report's), and
wages after inflation, worked out as BLS does (usable with care).

CARE holds the report's "usable with care" group: short, broken or heavily
revised series, added at the firm's request on 21 Oct 2026 ("expand what we
keep in this book after all - even if not super useful"); "care" says why
each is only usable with care. The firm chose to leave licensed series out:
CARE_NOT_READ lists those, and the rest of the group the tool cannot read
yet, with the reason for each.
"""
from dataclasses import dataclass, field

HIGHER = "higher is worse"
LOWER = "lower is worse"

FRED_PD = "FRED: Public Domain: Citation Requested"
FRED_CR = "FRED: Copyrighted: Citation Required"
OCT_2025 = ("2025-10", "no value: the 2025 lapse in appropriations (BLS footnote 9); kept as missing, never filled")


@dataclass(frozen=True)
class Series:
    key: str
    title: str
    group: str              # consumer, commercial or both
    publisher: str
    source: str             # fred, bls, fed_ebp, fhfa_nmdb
    source_id: str          # the id or column at the source
    frequency: str          # daily, weekly, monthly, quarterly
    unit: str
    starts: str             # first observation, as checked
    licence: str
    stress: object          # HIGHER, LOWER, or None: which way the research says it signals stress, if it says
    report: str
    breaks: tuple = field(default=())
    read_alone: bool = True  # False: an input to a derived reading, not read on its own
    note: str = ""
    change_in: str = ""     # points (a rate, spread or index around zero) or percent (a level that grows)
    position: str = ""      # "" its place in its own history is read; otherwise why it is not
    care: str = ""          # in the "usable with care" group: why, for the reader of the workbook
    credit: str = ""        # wording the publisher's licence requires wherever its data are shown


def _fred(key, sid, title, group, publisher, freq, unit, starts, licence, stress, report, breaks=(), read_alone=True,
          note="", *, change_in, position=""):
    return Series(key, title, group, publisher, "fred", sid, freq, unit, starts, licence, stress, report,
                  tuple(breaks), read_alone, note, change_in, position)


def _care(key, sid, title, group, publisher, freq, unit, starts, licence, report, care, breaks=(), note="", *,
          change_in, position="", source="fred", credit=""):
    """A series of the "usable with care" group, read as every other is, with why it needs care."""
    return Series(key, title, group, publisher, source, sid, freq, unit, starts, licence, None, report,
                  tuple(breaks), True, note, change_in, position, care, credit)


#: Why a series is read on its change only. A level that climbs with prices
#: and the economy sits near the top of its own history in almost every year,
#: so its place there says nothing; the report reads these on their change
#: ("PPI homeowner's insurance (1998, change over the year)", "G.19 revolving
#: credit growth").
TREND = "its level climbs over the decades with prices and the economy, so its place in its own history says nothing"
VALUED_ELSEWHERE = TREND + "; its valuation is read against income (house_price_to_income)"
TREND_NO_VALUATION = TREND + "; the tool reads no measure of what CRE is worth against rents or income yet"


#: The NY Fed's household debt report, read 22 Oct 2026: its terms of use (last updated 6/9/2023) license use,
#: copying and distribution "for your personal or business purposes", and name the attribution for its data.
HHDC_LICENCE = ("NY Fed terms of use: free to use, copy and distribute for personal or business purposes, with "
                "the attribution it sets out (read 22 Oct 2026)")
HHDC_CREDIT = ("Source: New York Fed Consumer Credit Panel / Equifax. From the Quarterly Report on Household Debt "
               "and Credit, available without charge at https://www.newyorkfed.org/microeconomics/hhdc. Changes, "
               "shares and directions are this workbook's arithmetic on the NY Fed's figures, not the NY Fed's.")
HHDC_REVISED = ("each quarter", "each report can revise earlier quarters: the 2026 Q2 report revised 2026 Q1 credit "
                "card balances")
#: (key, the column as the NY Fed heads it, the title here), in the report's order.
HOUSEHOLD_DEBT = [("household_mortgage", "Mortgage", "mortgage"),
                  ("household_he_revolving", "HE Revolving", "home equity revolving"),
                  ("household_auto", "Auto Loan", "auto loan"), ("household_credit_card", "Credit Card", "credit card"),
                  ("household_student", "Student Loan", "student loan"), ("household_other", "Other", "other"),
                  ("household_total", "Total", "total")]

#: The bank credit series: each product's net charge-offs and its loans 30+ days late incl. nonaccrual, every FDIC
#: filer summed and KeyBank on its own. The firm, 23 Oct 2026: "Yes, from FDIC each pull". Built by the threshold
#: engine's peers build under the consumer book's settings (fdic_credit.py); the FDIC's website policies page,
#: read 23 Oct 2026, states no terms of reuse for its own data.
FDIC_LICENCE = ("FDIC BankFind: Call Report data the FDIC publishes; its website policies page states no terms of "
                "reuse for its own data (read 23 Oct 2026)")
#: (the product as the threshold engine names it, its file slug, the key's start, the title's words, the tab's).
BANK_PRODUCTS = [("Credit card", "credit-card", "card", "Card", "Card"),
                 ("Other consumer", "other-consumer", "other_consumer", "Other consumer", "Other cons"),
                 ("Mortgage", "mortgage", "mortgage", "Mortgage", "Mortgage"),
                 ("Home equity", "home-equity", "home_equity", "Home equity", "Home equity")]
#: (who, as the threshold engine's files say it, the key's end, the title's words).
BANK_WHO = [("industry", "all_banks", "all banks"), ("keybank", "keybank", "KeyBank")]
#: (measure, the file name's tail, the key's middle, the title's words, the tab's, the unit). A loss rate is the
#: past four quarters' net charge-offs over the average balance of those quarters; each tab's notes say so.
BANK_MEASURES = [("net", "net", "losses", "net charge-offs", "losses",
                  "% of loans, past year"),
                 ("30+", "delinquency-30-plus-incl-nonaccrual_quarter-end", "late", "30+ days late incl. nonaccrual",
                  "30+ late", "% of loans, quarter-end")]
#: The first quarter each series holds, as the build of 23 Oct 2026 wrote it (2006Q1 to 2026Q2). KeyBank's card and
#: other consumer start late: the build writes from the first quarter after the last break and fills no gap.
BANK_STARTS = {("card", "net", "industry"): "2006Q4", ("card", "net", "keybank"): "2013Q4",
               ("card", "30+", "keybank"): "2012Q3", ("other_consumer", "net", "keybank"): "2015Q4",
               ("mortgage", "net", "keybank"): "2007Q1", ("home_equity", "net", "keybank"): "2007Q1"}
SECURITIZED = ("2010Q1", "securitized cards came back onto banks' books under FAS 166 and 167 from 1 Jan 2010; "
                         "before it a bank's securitized cards were off its books (the threshold engine's note)")


def bank_key(product, measure, who):
    """card_losses_all_banks, mortgage_late_keybank ..."""
    pk = next(k for p, _, k, _, _ in BANK_PRODUCTS if p == product)
    mk = next(k for m, _, k, *_ in BANK_MEASURES if m == measure)
    return "%s_%s_%s" % (pk, mk, next(k for w, k, _ in BANK_WHO if w == who))


def bank_source_id(product, measure, who):
    """The threshold engine's own series file stem, e.g. credit-card_keybank_net."""
    return "%s_%s_%s" % (next(s for p, s, *_ in BANK_PRODUCTS if p == product), who,
                         next(t for m, t, *_ in BANK_MEASURES if m == measure))


LABOUR = "Labour data carries the only official link to loan losses"
INSURE = "Home insurance has no free series for what owners actually pay"
HOUSE = "Household balance sheets: flows into delinquency beat balance stocks"
COMM = "Commercial risk reads off spreads, standards and CRE prices, but under licence"
FLAGS = "Published flags rate position or change, and the best-known triggers misfired in 2022-25"

STATES = ("AK AL AR AZ CA CO CT DC DE FL GA HI IA ID IL IN KS KY LA MA MD ME MI MN MO MS MT NC ND NE NH NJ NM "
          "NV NY OH OK OR PA RI SC SD TN TX UT VA VT WA WI WV WY").split()

SERIES = [
    # -- consumer: labour
    _fred("unemployment", "UNRATE", "Unemployment rate", "both", "BLS (household survey)", "monthly", "percent",
          "1948-01", FRED_PD, HIGHER, LABOUR, [OCT_2025, ("each January", "population controls")], change_in="points"),
    _fred("initial_claims", "ICSA", "Initial jobless claims", "both", "Labor Department (ETA 539)", "weekly",
          "claims", "1967-01-07", FRED_PD, HIGHER, LABOUR, change_in="percent"),
    _fred("continuing_claims", "CCSA", "Continuing jobless claims", "both", "Labor Department (ETA 539)", "weekly",
          "claims", "1967-01-07", FRED_PD, HIGHER, LABOUR, change_in="percent"),
    _fred("payrolls", "PAYEMS", "Payroll employment", "both", "BLS (establishment survey)", "monthly",
          "thousands of jobs", "1939-01", FRED_PD, LOWER, LABOUR,
          [("2025-03", "annual benchmark cut 898,000 jobs (0.6%); rate on the latest benchmark")], change_in="percent", position=TREND),
    # -- consumer: costs
    _fred("cpi", "CPIAUCSL", "Consumer prices, all items", "both", "BLS", "monthly", "index 1982-84=100",
          "1947-01", FRED_PD, None, INSURE, [OCT_2025],
          note="Stress runs both ways: inflation, or deflation in a deep recession.", change_in="percent", position=TREND),
    _fred("cpi_core", "CPILFESL", "Consumer prices excluding food and energy", "both", "BLS", "monthly",
          "index 1982-84=100", "1957-01", FRED_PD, None, INSURE, [OCT_2025],
          note="As for all-items prices, stress runs both ways.", change_in="percent", position=TREND),
    _fred("gasoline", "GASREGW", "Retail gasoline price, regular", "consumer", "EIA (weekly survey)", "weekly",
          "dollars a gallon", "1990-08-20", FRED_PD, HIGHER, INSURE, change_in="percent", position=TREND),
    Series("motor_insurance", "Consumer prices: motor vehicle insurance", "consumer", "BLS", "bls", "CUSR0000SETE",
           "monthly", "index 1982-84=100", "1985-01", "BLS: public domain", HIGHER, INSURE,
           (("2025-10", "no value (2025 lapse in appropriations)"), ("2025-11", "no value"),
            ("each Oct-Nov", "model-year update changes premiums")), change_in="percent", position=TREND),
    _fred("used_cars", "CUSR0000SETA02", "Consumer prices: used cars and trucks", "consumer", "BLS", "monthly",
          "index 1982-84=100", "1953-01", FRED_PD, None, INSURE,
          note="Higher prices raise loan sizes and payments; lower prices cut collateral values.", change_in="percent", position=TREND),
    _fred("home_insurance", "PCU9241269241262", "Producer prices: homeowner's insurance premiums", "consumer", "BLS",
          "monthly", "index Jun 1998=100", "1998-06", FRED_PD, HIGHER, INSURE,
          [("each September", "most of the year's rise lands in one step; rate the change over a year"),
           ("latest 4 months", "preliminary")],
          note="What insurers charge, not what households pay: no free series measures that.", change_in="percent", position=TREND),
    # Inputs to wages after inflation (usable with care), both not seasonally adjusted, as BLS deflates. FRED's
    # pages, read 22 Oct 2026: BLS, Public Domain: Citation Requested.
    _fred("wages_eci_nsa", "CIU2020000000000I", "Employment cost index: wages and salaries, private, not seasonally "
          "adjusted", "consumer", "BLS", "quarterly", "index Dec 2005=100", "2001-01", FRED_PD, None, LABOUR,
          read_alone=False, note="Input to wages after inflation.", change_in="percent"),
    _fred("cpi_nsa", "CPIAUCNS", "Consumer prices, all items, not seasonally adjusted", "consumer", "BLS", "monthly",
          "index 1982-84=100", "1913-01", FRED_PD, None, LABOUR, [OCT_2025], read_alone=False,
          note="Input to wages after inflation.", change_in="percent"),
    # -- consumer: housing and credit
    _fred("house_prices", "USSTHPI", "House prices (FHFA, all transactions)", "consumer", "FHFA", "quarterly",
          "index 1980Q1=100", "1975-01", FRED_PD, None, HOUSE,
          note="Stretched when high against income, stressed when falling.", change_in="percent", position=VALUED_ELSEWHERE),
    _fred("income_per_person", "A229RC0", "Disposable income per person", "consumer", "BEA", "monthly", "dollars",
          "1959-01", FRED_PD, None, HOUSE, [("each year", "annual revision; Sep 2026 revised back to Jan 2021")],
          read_alone=False, note="Input to house prices against income.", change_in="percent"),
    _fred("mortgage_rate", "MORTGAGE30US", "30-year fixed mortgage rate", "consumer", "Freddie Mac (PMMS)", "weekly",
          "percent", "1971-04-02", FRED_CR, None, HOUSE,
          [("2022-11-17", "method change: built from loan applications instead of a lender survey")],
          note="Also read through its spread over the 10-year Treasury.", change_in="points"),
    _fred("treasury_10y", "DGS10", "10-year Treasury yield", "both", "Federal Reserve (H.15)", "daily", "percent",
          "1962-01-02", FRED_PD, None, HOUSE, read_alone=False, note="Input to the mortgage spread.", change_in="points"),
    _fred("revolving_credit", "REVOLSL", "Revolving consumer credit", "consumer", "Federal Reserve (G.19)", "monthly",
          "millions of dollars", "1968-01", FRED_PD, None, HOUSE,
          note="Fast growth is a build-up, contraction is stress.", change_in="percent", position=TREND),
    _fred("card_standards", "DRTSCLCC", "Banks tightening credit card standards (net %)", "consumer",
          "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "1996-01", FRED_PD, HIGHER, HOUSE, change_in="points"),
    Series("mortgage_30_89", "Mortgages 30-89 days late, all", "consumer", "FHFA (National Mortgage Database)",
           "fhfa_nmdb", "USA|All Mortgages|P3089DL", "quarterly", "percent of mortgages", "2002Q1",
           "FHFA: public", HIGHER, HOUSE, change_in="points"),
    Series("mortgage_90", "Mortgages 90+ days late, all", "consumer", "FHFA (National Mortgage Database)",
           "fhfa_nmdb", "USA|All Mortgages|P90DL", "quarterly", "percent of mortgages", "2002Q1",
           "FHFA: public", HIGHER, HOUSE, change_in="points"),
    Series("mortgage_90_government", "Mortgages 90+ days late, government-backed", "consumer",
           "FHFA (National Mortgage Database)", "fhfa_nmdb", "USA|Government / Non-Conventional|P90DL", "quarterly",
           "percent of mortgages", "2002Q1", "FHFA: public", HIGHER, HOUSE, change_in="points"),
] + [
    # The NY Fed's household debt by type, as its report gives it ("Total Debt Balance and Its Composition"):
    # the firm, 22 Oct 2026, "household as a graph ... split between as it is literally reported".
    Series(key, "Household debt: " + title, "consumer", "NY Fed (Consumer Credit Panel / Equifax)", "nyfed_hhdc",
           column, "quarterly", "trillions of dollars", "2003Q1", HHDC_LICENCE, None, HOUSE, (HHDC_REVISED,),
           change_in="percent", position=TREND, credit=HHDC_CREDIT)
    for key, column, title in HOUSEHOLD_DEBT
] + [
    Series(bank_key(product, measure, who), "%s %s, %s" % (words, mwords, wwords), "consumer",
           "FDIC (Call Reports), built by the threshold engine", "fdic", bank_source_id(product, measure, who),
           "quarterly", unit, BANK_STARTS.get((pk, measure, who), "2006Q1"), FDIC_LICENCE, None,
           # The firm added these, not the research; the report reads card charge-offs against unemployment in its
           # labour section and delinquency in its household section, the two each cites.
           LABOUR if measure == "net" else HOUSE,
           (SECURITIZED,) if pk == "card" and who == "industry" else (), change_in="points")
    for product, _, pk, words, _ in BANK_PRODUCTS
    for measure, _, _, mwords, _, unit in BANK_MEASURES
    for who, _, wwords in BANK_WHO
] + [
    # -- commercial and the economy
    _fred("real_gdp", "GDPC1", "Real GDP", "both", "BEA", "quarterly", "billions of chained 2017 dollars", "1947-01",
          FRED_PD, LOWER, COMM, change_in="percent", position=TREND),
    _fred("industrial_production", "INDPRO", "Industrial production", "commercial", "Federal Reserve (G.17)",
          "monthly", "index 2017=100", "1919-01", FRED_PD, LOWER, COMM, change_in="percent", position=TREND),
    _fred("capacity_use", "TCU", "Capacity utilisation", "commercial", "Federal Reserve (G.17)", "monthly",
          "percent", "1967-01", FRED_PD, LOWER, COMM, change_in="points"),
    _fred("cfnai", "CFNAI", "Chicago Fed National Activity Index", "commercial", "Chicago Fed", "monthly",
          "index (0 = trend growth)", "1967-03", FRED_CR, LOWER, FLAGS, [("monthly", "revised each month")], change_in="points"),
    _fred("cre_prices", "BOGZ1FL075035503Q", "Commercial real estate prices", "commercial",
          "Federal Reserve (Financial Accounts, Z.1)", "quarterly", "index level", "1945-10", FRED_PD, None, COMM,
          [("1996Q1", "method break: chained to CoStar's composite from 1996; appraisal-based before"),
           ("each year", "revised")],
          note="The index the Fed's stress test uses. Stretched when high, stressed when falling.", change_in="percent", position=TREND_NO_VALUATION),
    Series("gz_spread", "Corporate bond spread (GZ)", "commercial", "Federal Reserve (Gilchrist-Zakrajsek)",
           "fed_ebp", "gz_spread", "monthly", "percentage points", "1973-01", "Federal Reserve: public", HIGHER, COMM,
           (("every month", "whole history can revise; keep each download"),), change_in="points"),
    Series("excess_bond_premium", "Excess bond premium", "commercial", "Federal Reserve (Gilchrist-Zakrajsek)",
           "fed_ebp", "ebp", "monthly", "percentage points", "1973-01", "Federal Reserve: public", HIGHER, COMM,
           (("every month", "whole history can revise; keep each download"),), change_in="points"),
    Series("bond_recession_probability", "Recession probability from bond spreads", "commercial",
           "Federal Reserve (Gilchrist-Zakrajsek)", "fed_ebp", "est_prob", "monthly", "probability (0-1)", "1973-01",
           "Federal Reserve: public", HIGHER, FLAGS, (("every month", "whole history can revise"),), change_in="points"),
    _fred("nfci", "NFCI", "Chicago Fed financial conditions", "commercial", "Chicago Fed", "weekly",
          "index (0 = average)", "1971-01-08", FRED_CR, HIGHER, COMM, change_in="points"),
    _fred("nfci_adjusted", "ANFCI", "Chicago Fed financial conditions, adjusted for the economy", "commercial",
          "Chicago Fed", "weekly", "index (0 = average)", "1971-01-08", FRED_CR, HIGHER, COMM, change_in="points"),
    _fred("stlfsi", "STLFSI4", "St. Louis Fed financial stress", "commercial", "St. Louis Fed", "weekly",
          "index (0 = average)", "1993-12-31", FRED_CR, HIGHER, COMM, [("2022", "fourth version of the index")], change_in="points"),
    _fred("kcfsi", "KCFSI", "Kansas City Fed financial stress", "commercial", "Kansas City Fed", "monthly",
          "index (0 = average)", "1990-02", FRED_CR, HIGHER, COMM, [("2021", "bank-stock input changed")], change_in="points"),
    # Asked for by the firm on 22 Oct 2026 ("how do we not have the prime interest rate"). The report names it
    # (Lending standards and loan volumes) but put it in none of its three groups. FRED page read 22 Oct 2026.
    _fred("prime_rate", "DPRIME", "Bank prime loan rate", "both", "Federal Reserve (H.15)", "daily", "percent",
          "1955-08-04", FRED_PD, None, COMM,
          note="The free benchmark for business-loan rates since the Fed's survey of them ended in 2017 (report). "
               "FRED's note: rate posted by a majority of top 25 insured U.S.-chartered commercial banks; one of "
               "several base rates used by banks to price short-term business loans.", change_in="points"),
    _fred("yield_curve", "T10Y3M", "10-year minus 3-month Treasury", "both", "Federal Reserve (H.15)", "daily",
          "percentage points", "1982-01-04", FRED_CR, LOWER, FLAGS, change_in="points"),
    _fred("ci_standards", "DRTSCILM", "Banks tightening business loan standards (net %)", "commercial",
          "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "1990-04", FRED_PD, HIGHER, COMM, change_in="points"),
    _fred("ci_demand", "DRSDCILM", "Banks reporting stronger business loan demand (net %)", "commercial",
          "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "1991-10", FRED_PD, None, COMM,
          note="The research does not state which way demand signals stress.", change_in="points"),
] + [
    _fred("unemployment_" + st.lower(), st + "UR", "Unemployment rate, " + st, "both", "BLS (LAUS)", "monthly",
          "percent", "1976-01", FRED_PD, HIGHER, LABOUR, [OCT_2025, ("each spring", "annual benchmark")], change_in="points")
    for st in STATES
]

READY = "Roughly three dozen series are ready; licences and breaks put the rest in context only"

SCE_CREDIT = ("Source: Survey of Consumer Expectations, \u00a9 2013-2026 Federal Reserve Bank of New York (FRBNY). "
              "The SCE data are available without charge at http://www.newyorkfed.org/microeconomics/sce and may "
              "be used subject to license terms posted there. FRBNY disclaims any responsibility for this analysis "
              "and interpretation of Survey of Consumer Expectations data.")
SCE_LICENCE = ("NY Fed SCE licence: free to reproduce, use and distribute, with the attribution it sets out "
               "(read 21 Oct 2026)")
SHORT_SINCE = "starts %s, so its history holds %s"
REVISED = "heavily revised: BEA's annual update of September 2026 revised it back to January 2021"

#: The report's "usable with care" group, as far as the tool can read it. Every FRED id,
#: title, frequency, unit, first reading and licence tag was checked on FRED's own series page and in a live
#: pull on 22 Oct 2026; the NY Fed survey against its workbook and licence on 21 Oct.
CARE = [
    # -- jobs and income
    _care("underemployment", "U6RATE", "Underemployment rate (U-6)", "both", "BLS (household survey)", "monthly",
           "percent", "1994-01", FRED_PD, LABOUR, SHORT_SINCE % ("in 1994", "three recessions"), [OCT_2025],
           change_in="points"),
    _care("job_openings", "JTSJOL", "Job openings", "both", "BLS (JOLTS)", "monthly", "thousands", "2000-12",
           FRED_PD, LABOUR, SHORT_SINCE % ("in December 2000", "two recessions"), change_in="percent",
           position=TREND),
    _care("layoffs_rate", "JTSLDR", "Layoffs and discharges rate", "both", "BLS (JOLTS)", "monthly",
           "percent of employment", "2000-12", FRED_PD, LABOUR, SHORT_SINCE % ("in December 2000", "two recessions"),
           change_in="points"),
    _care("quits_rate", "JTSQUR", "Quits rate", "both", "BLS (JOLTS)", "monthly", "percent of employment",
           "2000-12", FRED_PD, LABOUR, SHORT_SINCE % ("in December 2000", "two recessions"), change_in="points"),
    _care("temp_help", "TEMPHELPS", "Temporary help jobs", "both", "BLS (establishment survey)", "monthly",
           "thousands of jobs", "1990-01", FRED_PD, LABOUR, SHORT_SINCE % ("in 1990", "three recessions"),
           change_in="percent", position=TREND),
    _care("wages_eci", "ECIWAG", "Employment cost index: wages and salaries, private", "consumer", "BLS",
           "quarterly", "index Dec 2005=100", "2001-01", FRED_PD, LABOUR,
           SHORT_SINCE % ("in 2001 on FRED", "two recessions"), change_in="percent", position=TREND),
    _care("hourly_earnings", "CES0500000003", "Average hourly earnings, private", "consumer",
           "BLS (establishment survey)", "monthly", "dollars an hour", "2006-03", FRED_PD, LABOUR,
           SHORT_SINCE % ("in 2006", "two recessions") + "; the average rises when low-paid workers lose their "
           "jobs (report)", change_in="percent", position=TREND),
    # FRED's page, read 22 Oct 2026, tags it Public Domain: Citation Requested. The Atlanta Fed's own site terms
    # (read 21 Oct) allow its content to be reproduced only "not for commercial gain"; it is read from FRED, under
    # FRED's tag, as every other FRED series is. The 3-month average, of the two FRED carries, follows a turn
    # sooner than the 12-month.
    _care("wage_tracker", "FRBATLWGT3MMAUMHWGO", "Median wage growth, 3-month average (Atlanta Fed tracker)",
           "consumer", "Federal Reserve Bank of Atlanta", "monthly", "percent change from a year ago", "1997-01",
           FRED_PD, LABOUR, SHORT_SINCE % ("in 1997", "three recessions") + "; each person's own wage change, from "
           "the household survey, so October 2025 has none",
           [("2025-10", "no value: no household survey that month (the 2025 lapse in appropriations); kept as "
                        "missing, never filled")], change_in="points"),
    _care("real_income", "DSPIC96", "Real disposable income", "consumer", "BEA", "monthly",
           "billions of chained 2017 dollars", "1959-01", FRED_PD, LABOUR, REVISED + "; the October 2025 price "
           "index was interpolated", change_in="percent", position=TREND),
    _care("income_ex_transfers", "W875RX1", "Real personal income excluding transfers", "consumer", "BEA",
           "monthly", "billions of chained 2017 dollars", "1959-01", FRED_PD, LABOUR, REVISED,
           change_in="percent", position=TREND),
    _care("saving_rate", "PSAVERT", "Personal saving rate", "consumer", "BEA", "monthly",
           "percent of disposable income", "1959-01", FRED_PD, LABOUR,
           REVISED + "; October 2025 moved from 3.7% at first print to 4.9%", change_in="points"),
    # -- household debt and credit
    _care("debt_service", "TDSP", "Household debt service ratio", "consumer", "Federal Reserve Board",
           "quarterly", "percent of disposable income", "2005-01", FRED_PD, HOUSE,
           "rebuilt in 2024 on credit-bureau data and now starts in 2005; it includes mortgage escrow, so it runs "
           "higher than the old series, which is not joined on", change_in="points"),
    _care("debt_service_mortgage", "MDSP", "Mortgage debt service ratio", "consumer", "Federal Reserve Board",
           "quarterly", "percent of disposable income", "2005-01", FRED_PD, HOUSE,
           "rebuilt in 2024 and now starts in 2005, as the household ratio", change_in="points"),
    _care("debt_service_consumer", "CDSP", "Consumer debt service ratio", "consumer", "Federal Reserve Board",
           "quarterly", "percent of disposable income", "2005-01", FRED_PD, HOUSE,
           "rebuilt in 2024 and now starts in 2005, as the household ratio", change_in="points"),
    _care("card_minimum_payment", "RCCCBSHRMIN", "Large-bank card accounts paying only the minimum",
           "consumer", "Philadelphia Fed (FR Y-14M)", "quarterly", "percent of accounts", "2012-07", FRED_PD,
           HOUSE, "large banks only; " + SHORT_SINCE % ("in 2012 Q3", "one recession (2020)"),
           change_in="points"),
    _care("expected_missed_payment", "Delinquency expectations",
           "Expected chance of missing a minimum debt payment", "consumer",
           "New York Fed (Survey of Consumer Expectations)", "monthly", "percent (mean probability)", "2013-06",
           SCE_LICENCE, HOUSE, SHORT_SINCE % ("in June 2013", "one recession (2020)"),
           note="The survey asks each household the chance it will miss a minimum debt payment in the next three "
                "months; this is the mean answer.", change_in="points", source="nyfed_sce", credit=SCE_CREDIT),
    # The NY Fed's count from the workbook household debt by type comes from: Page 17 Data, "Number of Consumers
    # with New Foreclosures and Bankruptcies", in thousands, from 2003 Q1 (read 23 Oct 2026). The firm, 23 Oct
    # 2026: "build it", on reading the 2005 law change as a break rather than leaving quarters out. The law,
    # Public Law 109-8, was enacted 20 April 2005 and its section 1501(a) has it "take effect 180 days after the
    # date of enactment": 17 October 2005 (https://www.govinfo.gov/content/pkg/PLAW-109publ8/html/PLAW-109publ8.htm).
    # The panel is "constructed from a nationally representative random sample of Equifax credit report data" (the
    # NY Fed's background page, https://www.newyorkfed.org/microeconomics/hhdc/background.html, read 23 Oct 2026).
    # Unlike credit card balances, no count here was revised by the 2026 Q2 report: its 93 earlier quarters match
    # the 2026 Q1 file's, checked 23 Oct 2026.
    _care("new_bankruptcies", "Page 17 Data: bankruptcy", "People with a new bankruptcy on their credit report",
          "consumer", "NY Fed (Consumer Credit Panel / Equifax)", "quarterly", "thousands of people", "2003Q1",
          HHDC_LICENCE, HOUSE, "estimated from a random sample of credit reports; the October 2005 bankruptcy law "
          "broke its history",
          [("2005-10", "the bankruptcy law of April 2005 took effect on 17 October 2005 (Public Law 109-8, section "
                       "1501): people rushed to file before it, and filings fell away after")],
          note="Counts people whose credit report shows a new bankruptcy in the quarter, not cases filed in court.",
          change_in="percent", source="nyfed_hhdc", credit=HHDC_CREDIT),
    _care("auto_standards", "STDSAUTO", "Banks tightening auto loan standards (net %)", "consumer",
           "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "2011-04", FRED_PD, HOUSE,
           SHORT_SINCE % ("in 2011", "one recession (2020)"), change_in="points"),
    _care("other_consumer_standards", "STDSOTHCONS", "Banks tightening other consumer loan standards (net %)",
           "consumer", "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "2011-04",
           FRED_PD, HOUSE, SHORT_SINCE % ("in 2011", "one recession (2020)"), change_in="points"),
    _care("new_home_supply", "MSACSR", "New homes for sale: months' supply", "consumer", "Census and HUD",
           "monthly", "months", "1963-01", FRED_PD, HOUSE,
           "wide sampling error: the Census Bureau puts the August 2026 monthly change at plus or minus 17.2%; "
           "the report reads it smoothed, and it is shown here as published", change_in="points"),
    # -- business
    _care("equipment_orders", "NEWORDER", "Orders for business equipment excluding aircraft", "commercial",
           "Census Bureau (M3)", "monthly", "millions of dollars", "1992-02", FRED_PD, COMM,
           "in dollars, not adjusted for prices; the industry classification changed in 2001",
           change_in="percent", position=TREND),
    _care("business_applications", "BABATOTALSAUS", "Business applications", "commercial",
           "Census Bureau (Business Formation Statistics)", "monthly", "applications", "2004-07", FRED_PD, COMM,
           "counts new businesses, not distress (report); an IRS outage in December 2025", change_in="percent",
           position=TREND),
    _care("likely_employer_applications", "BAHBATOTALSAUS", "Business applications likely to hire",
           "commercial", "Census Bureau (Business Formation Statistics)", "monthly", "applications", "2004-07",
           FRED_PD, COMM, "redefined for its whole history in January 2026, so a copy from before then differs; "
           "an IRS outage in December 2025", change_in="percent", position=TREND),
    _care("philadelphia_survey", "GACDFSA066MSFRBPHI", "Philadelphia Fed manufacturing survey: current activity",
           "commercial", "Philadelphia Fed", "monthly", "diffusion index", "1968-05", FRED_CR, COMM,
           "a survey of one region's manufacturers", change_in="points"),
    _care("empire_survey", "GACDISA066MSFRBNY", "Empire State manufacturing survey: current activity",
           "commercial", "New York Fed", "monthly", "diffusion index", "2001-07", FRED_CR, COMM,
           "a survey of one state's manufacturers; " + SHORT_SINCE % ("in 2001", "two recessions"),
           change_in="points"),
    _care("dallas_survey", "BACTSAMFRBDAL", "Dallas Fed manufacturing survey: business activity", "commercial",
           "Dallas Fed", "monthly", "diffusion index", "2004-06", FRED_CR, COMM,
           "a survey of one state's manufacturers; " + SHORT_SINCE % ("in 2004", "two recessions"),
           change_in="points"),
    _care("cre_standards_construction", "SUBLPDRCSC",
           "Banks tightening construction and land loan standards (net %)", "commercial",
           "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "2013-10", FRED_PD, COMM,
           SHORT_SINCE % ("in 2013 Q4", "no fall in CRE prices but 2020"), change_in="points"),
    _care("cre_standards_nonresidential", "SUBLPDRCSN",
           "Banks tightening nonresidential property loan standards (net %)", "commercial",
           "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "2013-10", FRED_PD, COMM,
           SHORT_SINCE % ("in 2013 Q4", "no fall in CRE prices but 2020"), change_in="points"),
    _care("cre_standards_multifamily", "SUBLPDRCSM", "Banks tightening multifamily loan standards (net %)",
           "commercial", "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "2013-10",
           FRED_PD, COMM, SHORT_SINCE % ("in 2013 Q4", "no fall in CRE prices but 2020"), change_in="points"),
    _care("customs_duties", "B235RC1Q027SBEA", "Customs duties collected", "commercial", "BEA", "quarterly",
           "billions of dollars, annual rate", "1959-01", FRED_PD, COMM,
           "policy context, not a measure of stress (report); tariff policy changed in 2025 and 2026",
           change_in="percent", position=TREND),
    _care("policy_uncertainty", "USEPUINDXM", "Economic policy uncertainty (newspaper index)", "both",
           "Baker, Bloom and Davis", "monthly", "index", "1985-01", FRED_PD, COMM,
           "built from newspaper articles; no test found linking it to loan losses (report)", change_in="points"),
    _care("trade_policy_uncertainty", "EPUTRADE", "Trade policy uncertainty (newspaper index)", "commercial",
           "Baker, Bloom and Davis", "monthly", "index", "1985-01", FRED_PD, COMM,
           "built from newspaper articles; no test found linking it to loan losses (report)", change_in="points"),
    # Its FRED tag, read 22 Oct 2026, is "Copyrighted: Citation Required", as for the Freddie Mac rate and the
    # Chicago Fed indexes the tool rates: usable with the citation, so it is not among the licensed series left
    # out. FRED's note: "Copyright, 2016, Chicago Board Options Exchange, Inc. Reprinted with permission."
    _care("vix", "VIXCLS", "Stock market volatility (VIX)", "commercial", "Cboe (via FRED)", "daily", "index",
           "1990-01-02", FRED_CR, COMM, "a daily market price of expected volatility, which moves in hours; the "
           "Fed's stress test uses its quarterly peak (report)", change_in="points"),
]

#: In the "usable with care" group and not read, and why.
CARE_NOT_READ = [
    ("University of Michigan consumer sentiment", "licensed: no redistribution (report); the firm chose to leave "
     "licensed series out"),
    ("Atlanta Fed home ownership affordability", "licensed: the same terms of use, and its price and insurance "
     "inputs are licensed from others (report)"),
    ("Yale Budget Lab tariff rate", "its terms are not confirmed (report); customs duties collected are shown"),
    ("NY Fed student loan delinquency", "not read: on 22 Oct 2026 the firm chose the same report's debt by type, "
     "which holds student loan balances; its delinquency needs the 2020-24 payment pause marked (report)"),
    ("County unemployment rates", "about 3,200 series, not seasonally adjusted, too many for one workbook; a "
     "county monitor is specified in this repository (bls-laus-county-monitor) but not built"),
    ("CFPB mortgage delinquency by state, metro and county", "each file is named for the month it runs to (the "
     "newest ran to December 2025 on 21 Oct 2026), so the pull would first have to find it on the CFPB's "
     "download page; no reader yet"),
    ("Bankruptcy filings (US Courts)", "published as PDF and spreadsheet tables with no download service "
     "(report); no reader yet"),
    ("Census Business Trends and Outlook Survey", "an experimental survey every two weeks from September 2023, "
     "published as a spreadsheet per question, with no reader yet"),
]


@dataclass(frozen=True)
class Derived:
    """A reading made from two catalog series, both from the same pull."""
    key: str
    title: str
    group: str
    inputs: tuple
    how: str                # in plain words, for the reader of the workbook
    frequency: str
    unit: str
    stress: object
    report: str
    change_in: str
    position: str = ""
    note: str = ""
    read_alone: bool = True
    breaks: tuple = ()
    care: str = ""          # in the "usable with care" group: why


DERIVED = [
    Derived("house_price_to_income", "House prices against income per person", "consumer",
            ("house_prices", "income_per_person"),
            "the FHFA house price index divided by the quarter's average disposable income per person, "
            "in thousands of dollars; a quarter missing any month of income is left out",
            "quarterly", "index points per $1,000 of yearly income", None, READY, "percent",
            note="The valuation reading the report names for house prices: stretched when high, stressed when "
                 "falling."),
    Derived("mortgage_spread", "30-year mortgage rate over the 10-year Treasury", "consumer",
            ("mortgage_rate", "treasury_10y"),
            "the weekly mortgage rate minus the 10-year yield on the same day, or on the last day in the week "
            "before it that has one",
            "weekly", "percentage points", HIGHER, READY, "points",
            note="Wider is worse: the Fed's scenario guide sizes a severe move as a spread up 0.70 to 1.60 "
                 "points, or at 3 points or more, whichever is higher (report, What \"severe\" looks like).",
            breaks=(("2022-11-17", "mortgage rate method change: built from loan applications"),)),
    # BLS's own figures after inflation in its June 2026 release (Table A: private and civilian wages and
    # salaries, June 2025, March and June 2026) come out of this arithmetic to the published decimal in five of
    # six; the sixth, private for June 2025, is 0.851 against BLS's 0.8. Prices averaged over the quarter, or
    # taken at its middle month, miss by 0.2 to 0.8 points (22 Oct 2026; docs/macro/LOG.md).
    Derived("real_wages_eci", "Employment cost index: private wages, after inflation", "consumer",
            ("wages_eci_nsa", "cpi_nsa"),
            "the wages and salaries index for private industry divided by consumer prices in the quarter's last "
            "month, both before seasonal adjustment; a quarter with no price for that month is left out",
            "quarterly", "index: wages over prices, x 100", None, LABOUR, "percent",
            position="an index of one index over another has no meaning as a level, so its place in its own "
                     "history says nothing",
            note="Worked this way, BLS's own figures after inflation for June 2025, March 2026 and June 2026 come "
                 "out to the decimal for private and for all civilian workers in five of six; the sixth, private "
                 "for June 2025, is 0.851% against BLS's 0.8%.",
            care=SHORT_SINCE % ("in 2001 on FRED", "two recessions")),
]

#: In the ready-to-rate group but not read yet, and why.
NOT_YET = [
    ("NY Fed recession probability (yield curve)", "published only as an old-format Excel file (allmonth.xls) "
     "that needs a reader the tool does not have; the 10-year minus 3-month spread itself is read"),
    ("NY Fed flows into delinquency by product", "not read yet: on 22 Oct 2026 the firm chose the same report's "
     "debt by type; its terms of use, read that day, allow both"),
    ("FHFA mortgage delinquency by state", "the state file is not wired in yet; national and loan type are"),
]

SERIES = SERIES + CARE
BY_KEY = {s.key: s for s in SERIES}
DERIVED_BY_KEY = {d.key: d for d in DERIVED}
#: The ready-to-rate group as read: the catalog's own series read alone, then the derived readings.
CORE = [s for s in SERIES if s.read_alone and not s.care] + [d for d in DERIVED if d.read_alone and not d.care]
#: The usable-with-care group's derived readings, read after its own series.
CARE_DERIVED = [d for d in DERIVED if d.care]
#: Everything the tool reads: the core, then the usable-with-care group.
READ = CORE + CARE + CARE_DERIVED
