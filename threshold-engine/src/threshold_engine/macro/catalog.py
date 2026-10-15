"""The series the tool reads: the report's "ready to rate" group.

Every entry is a fact about a public series, checked at the publisher or on
FRED on 15 Oct 2026: who publishes it, where it comes from, how often, from
when, under what terms, and the breaks a reader must know. The direction of
stress is filled in only where the research states it; where a series can be
stressed both ways, or the research does not say, it is None and the firm
sets it (the rating refuses until it does).

"report" names the section of docs/macro/reports/Macro risk indicators for
lending.md that put the series on the list.
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
    stress: object          # HIGHER, LOWER, or None: the firm sets it
    report: str
    breaks: tuple = field(default=())
    rated: bool = True      # False: an input to a derived reading, not rated alone
    note: str = ""


def _fred(key, sid, title, group, publisher, freq, unit, starts, licence, stress, report, breaks=(), rated=True, note=""):
    return Series(key, title, group, publisher, "fred", sid, freq, unit, starts, licence, stress, report,
                  tuple(breaks), rated, note)


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
          "1948-01", FRED_PD, HIGHER, LABOUR, [OCT_2025, ("each January", "population controls")]),
    _fred("initial_claims", "ICSA", "Initial jobless claims", "both", "Labor Department (ETA 539)", "weekly",
          "claims", "1967-01-07", FRED_PD, HIGHER, LABOUR),
    _fred("continuing_claims", "CCSA", "Continuing jobless claims", "both", "Labor Department (ETA 539)", "weekly",
          "claims", "1967-01-07", FRED_PD, HIGHER, LABOUR),
    _fred("payrolls", "PAYEMS", "Payroll employment", "both", "BLS (establishment survey)", "monthly",
          "thousands of jobs", "1939-01", FRED_PD, LOWER, LABOUR,
          [("2025-03", "annual benchmark cut 898,000 jobs (0.6%); rate on the latest benchmark")]),
    # -- consumer: costs
    _fred("cpi", "CPIAUCSL", "Consumer prices, all items", "both", "BLS", "monthly", "index 1982-84=100",
          "1947-01", FRED_PD, None, INSURE, [OCT_2025],
          note="Stress runs both ways (inflation, or deflation in a deep recession); the firm sets the direction."),
    _fred("cpi_core", "CPILFESL", "Consumer prices excluding food and energy", "both", "BLS", "monthly",
          "index 1982-84=100", "1957-01", FRED_PD, None, INSURE, [OCT_2025],
          note="As for all-items prices: the firm sets the direction."),
    _fred("gasoline", "GASREGW", "Retail gasoline price, regular", "consumer", "EIA (weekly survey)", "weekly",
          "dollars a gallon", "1990-08-20", FRED_PD, HIGHER, INSURE),
    Series("motor_insurance", "Consumer prices: motor vehicle insurance", "consumer", "BLS", "bls", "CUSR0000SETE",
           "monthly", "index 1982-84=100", "1985-01", "BLS: public domain", HIGHER, INSURE,
           (("2025-10", "no value (2025 lapse in appropriations)"), ("2025-11", "no value"),
            ("each Oct-Nov", "model-year update changes premiums"))),
    _fred("used_cars", "CUSR0000SETA02", "Consumer prices: used cars and trucks", "consumer", "BLS", "monthly",
          "index 1982-84=100", "1953-01", FRED_PD, None, INSURE,
          note="Higher prices raise loan sizes and payments; lower prices cut collateral values. The firm sets the direction."),
    _fred("home_insurance", "PCU9241269241262", "Producer prices: homeowner's insurance premiums", "consumer", "BLS",
          "monthly", "index Jun 1998=100", "1998-06", FRED_PD, HIGHER, INSURE,
          [("each September", "most of the year's rise lands in one step; rate the change over a year"),
           ("latest 4 months", "preliminary")],
          note="What insurers charge, not what households pay: no free series measures that."),
    # -- consumer: housing and credit
    _fred("house_prices", "USSTHPI", "House prices (FHFA, all transactions)", "consumer", "FHFA", "quarterly",
          "index 1980Q1=100", "1975-01", FRED_PD, None, HOUSE,
          note="Stretched when high against income, stressed when falling: the firm sets how it is read."),
    _fred("income_per_person", "A229RC0", "Disposable income per person", "consumer", "BEA", "monthly", "dollars",
          "1959-01", FRED_PD, None, HOUSE, [("each year", "annual revision; Sep 2026 revised back to Jan 2021")],
          rated=False, note="Input to house prices against income."),
    _fred("mortgage_rate", "MORTGAGE30US", "30-year fixed mortgage rate", "consumer", "Freddie Mac (PMMS)", "weekly",
          "percent", "1971-04-02", FRED_CR, None, HOUSE,
          [("2022-11-17", "method change: built from loan applications instead of a lender survey")],
          note="Read through its spread over the 10-year Treasury; the firm sets the direction of the rate itself."),
    _fred("treasury_10y", "DGS10", "10-year Treasury yield", "both", "Federal Reserve (H.15)", "daily", "percent",
          "1962-01-02", FRED_PD, None, HOUSE, rated=False, note="Input to the mortgage spread."),
    _fred("revolving_credit", "REVOLSL", "Revolving consumer credit", "consumer", "Federal Reserve (G.19)", "monthly",
          "millions of dollars", "1968-01", FRED_PD, None, HOUSE,
          note="Fast growth is a build-up, contraction is stress: the firm sets how it is read."),
    _fred("card_standards", "DRTSCLCC", "Banks tightening credit card standards (net %)", "consumer",
          "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "1996-01", FRED_PD, HIGHER, HOUSE),
    Series("mortgage_30_89", "Mortgages 30-89 days late, all", "consumer", "FHFA (National Mortgage Database)",
           "fhfa_nmdb", "USA|All Mortgages|P3089DL", "quarterly", "percent of mortgages", "2002Q1",
           "FHFA: public", HIGHER, HOUSE),
    Series("mortgage_90", "Mortgages 90+ days late, all", "consumer", "FHFA (National Mortgage Database)",
           "fhfa_nmdb", "USA|All Mortgages|P90DL", "quarterly", "percent of mortgages", "2002Q1",
           "FHFA: public", HIGHER, HOUSE),
    Series("mortgage_90_government", "Mortgages 90+ days late, government-backed", "consumer",
           "FHFA (National Mortgage Database)", "fhfa_nmdb", "USA|Government / Non-Conventional|P90DL", "quarterly",
           "percent of mortgages", "2002Q1", "FHFA: public", HIGHER, HOUSE),
    # -- commercial and the economy
    _fred("real_gdp", "GDPC1", "Real GDP", "both", "BEA", "quarterly", "billions of chained 2017 dollars", "1947-01",
          FRED_PD, LOWER, COMM),
    _fred("industrial_production", "INDPRO", "Industrial production", "commercial", "Federal Reserve (G.17)",
          "monthly", "index 2017=100", "1919-01", FRED_PD, LOWER, COMM),
    _fred("capacity_use", "TCU", "Capacity utilisation", "commercial", "Federal Reserve (G.17)", "monthly",
          "percent", "1967-01", FRED_PD, LOWER, COMM),
    _fred("cfnai", "CFNAI", "Chicago Fed National Activity Index", "commercial", "Chicago Fed", "monthly",
          "index (0 = trend growth)", "1967-03", FRED_CR, LOWER, FLAGS, [("monthly", "revised each month")]),
    _fred("cre_prices", "BOGZ1FL075035503Q", "Commercial real estate prices", "commercial",
          "Federal Reserve (Financial Accounts, Z.1)", "quarterly", "index level", "1945-10", FRED_PD, None, COMM,
          [("1996Q1", "method break: chained to CoStar's composite from 1996; appraisal-based before"),
           ("each year", "revised")],
          note="The index the Fed's stress test uses. Stretched when high, stressed when falling: the firm sets how it is read."),
    Series("gz_spread", "Corporate bond spread (GZ)", "commercial", "Federal Reserve (Gilchrist-Zakrajsek)",
           "fed_ebp", "gz_spread", "monthly", "percentage points", "1973-01", "Federal Reserve: public", HIGHER, COMM,
           (("every month", "whole history can revise; keep each download"),)),
    Series("excess_bond_premium", "Excess bond premium", "commercial", "Federal Reserve (Gilchrist-Zakrajsek)",
           "fed_ebp", "ebp", "monthly", "percentage points", "1973-01", "Federal Reserve: public", HIGHER, COMM,
           (("every month", "whole history can revise; keep each download"),)),
    Series("bond_recession_probability", "Recession probability from bond spreads", "commercial",
           "Federal Reserve (Gilchrist-Zakrajsek)", "fed_ebp", "est_prob", "monthly", "probability (0-1)", "1973-01",
           "Federal Reserve: public", HIGHER, FLAGS, (("every month", "whole history can revise"),)),
    _fred("nfci", "NFCI", "Chicago Fed financial conditions", "commercial", "Chicago Fed", "weekly",
          "index (0 = average)", "1971-01-08", FRED_CR, HIGHER, COMM),
    _fred("nfci_adjusted", "ANFCI", "Chicago Fed financial conditions, adjusted for the economy", "commercial",
          "Chicago Fed", "weekly", "index (0 = average)", "1971-01-08", FRED_CR, HIGHER, COMM),
    _fred("stlfsi", "STLFSI4", "St. Louis Fed financial stress", "commercial", "St. Louis Fed", "weekly",
          "index (0 = average)", "1993-12-31", FRED_CR, HIGHER, COMM, [("2022", "fourth version of the index")]),
    _fred("kcfsi", "KCFSI", "Kansas City Fed financial stress", "commercial", "Kansas City Fed", "monthly",
          "index (0 = average)", "1990-02", FRED_CR, HIGHER, COMM, [("2021", "bank-stock input changed")]),
    _fred("yield_curve", "T10Y3M", "10-year minus 3-month Treasury", "both", "Federal Reserve (H.15)", "daily",
          "percentage points", "1982-01-04", FRED_CR, LOWER, FLAGS),
    _fred("ci_standards", "DRTSCILM", "Banks tightening business loan standards (net %)", "commercial",
          "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "1990-04", FRED_PD, HIGHER, COMM),
    _fred("ci_demand", "DRSDCILM", "Banks reporting stronger business loan demand (net %)", "commercial",
          "Federal Reserve (Senior Loan Officer Survey)", "quarterly", "net percent", "1991-10", FRED_PD, None, COMM,
          note="The research does not state which way demand signals stress; the firm sets it."),
] + [
    _fred("unemployment_" + st.lower(), st + "UR", "Unemployment rate, " + st, "both", "BLS (LAUS)", "monthly",
          "percent", "1976-01", FRED_PD, HIGHER, LABOUR, [OCT_2025, ("each spring", "annual benchmark")])
    for st in STATES
]

#: In the ready-to-rate group but not read yet, and why.
NOT_YET = [
    ("NY Fed recession probability (yield curve)", "published only as an old-format Excel file (allmonth.xls) "
     "that needs a reader the tool does not have; the 10-year minus 3-month spread itself is read"),
    ("NY Fed flows into delinquency by product", "its reuse terms are not confirmed (report, gaps)"),
    ("FHFA mortgage delinquency by state", "the state file is not wired in yet; national and loan type are"),
]

BY_KEY = {s.key: s for s in SERIES}
