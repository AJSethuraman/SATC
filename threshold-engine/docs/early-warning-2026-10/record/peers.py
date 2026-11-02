"""Each bank's refreshed-FICO book by product and quarter, from its 10-Q and
10-K XBRL (facts.json): scored balance, unscored balance, the share under
each band edge it publishes, and the share under 660, exact or a proven range.

Every mapping from a bank's own classes to the book's products is a stated
judgment (CONCESSIONS), as the Peer loan classes tab states its own."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bands as B  # noqa: E402

NAMES = {"91576": "KeyCorp", "70858": "Bank of America", "72971": "Wells Fargo", "713676": "PNC", "831001": "Citi",
         "19617": "JPMorgan", "1281761": "Regions", "759944": "Citizens", "49196": "Huntington", "1818874": "SoFi",
         "927628": "Capital One"}

#: bank -> product -> a test on the class string (the non-band members joined by " / ").
def last(*names):
    return lambda c: c.split(" / ")[-1] in names


def us_last(*names):
    """Citi: its U.S. classes, which before 2024 carry no geography member."""
    return lambda c: c.split(" / ")[0] in ("US", "ConsumerPortfolioSegment") and c.split(" / ")[-1] in names


MAP = {
    "KeyCorp": {"Card": last("CreditCardReceivables", "ConsumerCreditCard"),
                "Mortgage": last("RealEstateResidentialMortgage"),
                "Home equity": last("HomeEquityLoan"),
                "Other consumer": last("OtherConsumerLoans", "ConsumerDirectLoans", "ConsumerIndirectLoans")},
    "Bank of America": {"Card": last("CreditCardReceivables"), "Mortgage": last("ResidentialMortgage"),
                        "Home equity": lambda c: c.split(" / ")[-1] == "HomeEquityLoan" or c == "ResidentialPortfolioSegment",
                        "Other consumer": last("DirectandIndirectFinancingReceivable")},
    "Wells Fargo": {"Card": lambda c: "CreditCardReceivables" in c.split(" / "),
                    "Mortgage": lambda c: bool({"ResidentialMortgage", "FirstMortgage"} & set(c.split(" / "))),
                    "Home equity": lambda c: "SecondMortgage" in c.split(" / "),
                    "Other consumer": lambda c: bool({"ConsumerOther", "ConsumerLoan"} & set(c.split(" / "))),
                    "Auto": lambda c: "AutomobileLoan" in c.split(" / ")},
    "PNC": {"Card": lambda c: "CreditCardReceivables" in c.split(" / "),
            "Mortgage": last("ResidentialRealEstate"), "Home equity": last("HomeEquityLoan"),
            "Other consumer": lambda c: "OtherConsumerLoans" in c.split(" / "),
            "Auto": lambda c: "AutomobileLoan" in c.split(" / ")},
    "Citi": {"Card": us_last("CreditCardReceivables"), "Mortgage": us_last("ResidentialMortgage"),
             "Home equity": us_last("HomeEquity"), "Other consumer": us_last("PersonalSmallBusinessAndOther")},
    "JPMorgan": {"Mortgage": lambda c: len(c.split(" / ")) == 3 and c.split(" / ")[1] == "ResidentialRealEstate"},
    "Regions": {"Card": last("CreditCardReceivables"), "Mortgage": last("ResidentialFirstMortgage"),
                "Home equity": last("HomeEquity", "HomeEquityLoan"),
                "Other consumer": last("OtherConsumerFinancingReceivable")},
    "Citizens": {"Mortgage": last("ResidentialMortgage"), "Home equity": last("HomeEquityLoanAndLineOfCredit"),
                 "Other consumer": last("ConsumerOtherRetail", "StudentLoan"), "Auto": last("AutomobileLoan")},
    "Huntington": {"Mortgage": last("ResidentialLoan"), "Home equity": last("HomeEquityLoan"),
                   "Other consumer": last("RVandMarineFinanceLoan", "OtherConsumerLoan"),
                   "Auto": last("AutomobileLoan")},
    "SoFi": {"Card": lambda c: c.split(" / ")[-1] == "CreditCardReceivables"},
    "Capital One": {"Auto (at origination)": last("AutomobileLoan")},
}

CONCESSIONS = [
    ("Every bank", "Under 660 is exact where the bank publishes a 660 edge. Elsewhere it is a range between the "
                   "bank's nearest published edges below and above 660, which the filing proves. Balances with no "
                   "score are left out of every share, with their dollars stated."),
    ("Band edges", "Each band's top is read as the lower of its own stated top plus one and the next band's "
                   "bottom: KeyCorp's tag says 'greater than 750' where its table prints '750 and above'."),
    ("Bank of America", "Home equity is its total home equity class (lines, loans converted to term and reverse "
                        "mortgages are parts of it); before 2022Q4 that total is tagged with no class member, and "
                        "equals its parts ($30.5bn at 2021Q2). Other consumer is 'direct and indirect', which includes auto "
                        "loans; most of it, securities-based lending, has no score."),
    ("Wells Fargo", "Mortgage excludes government-insured loans. Until 2022 it split first and second mortgages "
                    "and cut every 40 points (600 to 800); home equity is its second mortgages until then, after "
                    "which they sit inside residential mortgage and home equity has no Wells figure. Other consumer "
                    "is mostly securities-based lending with no score; the share is of the scored part."),
    ("Citi", "U.S. classes only. Card is its 'credit card receivables' class; it also tags a slightly smaller "
             "'credit card' class, not used. Until 2024 it cut at 680 and 760 only, so its share under 660 there "
             "is known only to be at most its share under 680."),
    ("JPMorgan", "Residential real estate, which also holds home equity, summed across its loan-to-value "
                 "splits; it publishes only the 660 edge."),
    ("Regions", "Home equity is its lines and its loans added together. Edges 620, 680 and 720."),
    ("Citizens", "Other consumer is its other retail loans plus student loans, as the Call Report counts them. "
                 "Edges 620, 680, 740, 800."),
    ("Huntington", "Other consumer is RV and marine plus other consumer. Edges 650 and 750, so under 660 is a "
                   "wide range. Whether its scores are refreshed is not stated in the filing read."),
    ("PNC", "Edges 660, 720, 780. Card, auto and other consumer are its 'using FICO' rows."),
    ("SoFi", "Card only, held at fair value; fine bands every 20 points."),
    ("Capital One", "Auto only, and scored at origination, not refreshed: shown apart, never in a peer range."),
    ("KeyCorp", "Before 2020, purchased credit-impaired and other loans added together; its 'consumer direct' "
                "and 'consumer indirect' classes are other consumer until 2023, when they became one class."),
]


def build(facts_path):
    d = json.loads(Path(facts_path).read_text())
    out = {}
    for cik, by in d.items():
        bank = NAMES[cik]
        for date, facts in sorted(by.items()):
            if not facts:
                continue
            rows = B.balances(facts)
            for product, test in MAP.get(bank, {}).items():
                merged, edgesets = {}, set()
                for cls, row in rows.items():
                    if test(cls):
                        for b, v in row.items():
                            merged[b] = merged.get(b, 0.0) + v
                if not merged:
                    continue
                total, unscored, edges = B.cumulative(merged)
                if not total:
                    continue
                lo, hi = B.under(edges)
                out.setdefault(product, {}).setdefault(bank, {})[date] = {
                    "scored": total, "unscored": unscored, "edges": edges, "lo": lo, "hi": hi}
    return out


if __name__ == "__main__":
    res = build(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(res))
    for product, banks in res.items():
        print("==", product)
        for bank, by in banks.items():
            last_d = max(by)
            r = by[last_d]
            u = ("%.1f%%" % (100 * r["lo"])) if r["lo"] == r["hi"] else "%.1f%%-%.1f%%" % (100 * r["lo"], 100 * r["hi"])
            print("   %-16s %2d quarters %s..%s  scored $%6.1fbn  under 660 %s  edges %s" % (
                bank, len(by), min(by), last_d, r["scored"] / 1e9, u, [e for e, _ in r["edges"]]))
