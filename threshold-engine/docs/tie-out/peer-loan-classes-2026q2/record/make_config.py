"""Write config/peer-loan-classes.json from the three readers' checked records
(research_a/b/c.json: quotes verified verbatim against each filing) and the
judgements below. Quotes are copied, never retyped."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
R = {}
for f in ("research_a.json", "research_b.json", "research_c.json"):
    for b in json.loads((HERE / f).read_text(encoding="utf-8")):
        R[b["ticker"]] = b
F = json.loads((HERE / "filings.json").read_text())
CS = "us-gaap:ConsumerPortfolioSegmentMember"


def q(t, key, answer, short="Not stated", pick=None):
    """A finding: the answer, a short form for the summary, and the reader's
    quote and where (or one of its 'also' entries)."""
    x = R[t][key]
    if pick is not None:
        x = x["also"][pick]
    return {"answer": answer, "short": short, "quote": x["quote"], "where": x["where"]}


def said(t, key, answer, quote, where, short="Not stated"):
    """A finding whose quote sits elsewhere in the reader's record; checked present below."""
    blob = json.dumps(R[t], ensure_ascii=False)
    if quote not in blob:
        sys.exit("%s: quote not in the reader's record: %s" % (t, quote[:60]))
    return {"answer": answer, "short": short, "quote": quote, "where": where}


NOT = "None stated in the 10-Q"
banks = [
 dict(short="KeyBank", t="KEY", holding_company="KeyCorp",
      classes=[{"members": [CS, "key:OtherConsumerLoansMember"], "name": "Other consumer loans", "is": "Mixed other consumer"}],
      findings=dict(student=q("KEY", "student", "Education loans of $182 million sit in discontinued operations, outside loans; the 10-Q also lists student loan refinancing among the Consumer Bank's products, with no class or amount", "$182m discontinued"),
                    unsecured=q("KEY", "unsecured", NOT),
                    # Found by the tie-out's own search of the filed text (15 Oct 2026); the reader had "not stated".
                    secured_non_auto={"answer": "Boats and RVs are named as collateral for its consumer loans; no amount given",
                                      "short": "Boats, RVs named",
                                      "quote": "Our consumer loans have collateral that includes residential real estate, automobiles, boats, and RVs.",
                                      "where": "Credit quality note, the paragraph on collateral-dependent loans"}),
      comparison={"answer": "Mixed", "why": "Other consumer loans ($4.3bn) is not defined in the 10-Q; KeyCorp names student loan refinancing among its products and boats and RVs among its consumer collateral, with no split."}),
 dict(short="Citizens", t="CFG", holding_company="Citizens Financial Group, Inc.",
      classes=[{"members": [CS, "us-gaap:StudentLoanMember"], "name": "Education", "is": "Student"},
               {"members": [CS, "cfg:ConsumerOtherRetailMember"], "name": "Other retail", "is": "Mixed other consumer"}],
      findings=dict(student=q("CFG", "student", "Yes: Education is a class of its own", "Own class"),
                    unsecured=q("CFG", "unsecured", NOT), secured_non_auto=q("CFG", "secured_non_auto", NOT)),
      comparison={"answer": "Mixed", "why": "Education ($8.0bn) is twice Other retail ($4.0bn), and both sit in the Call Report's other consumer."}),
 dict(short="PNC", t="PNC", holding_company="The PNC Financial Services Group, Inc.",
      classes=[{"members": [CS, "pnc:OtherConsumerLoansMember"], "name": "Other consumer", "is": "Mixed other consumer"}],
      findings=dict(student=q("PNC", "student", "Yes: education loans were folded into Other consumer from 1 Jan 2026; no amount given", "In other consumer"),
                    unsecured=q("PNC", "unsecured", "Yes, named among Retail Banking's products; no amount given", "Named, no amount"),
                    secured_non_auto=q("PNC", "secured_non_auto", "Securities-based lending is named; no amount or class given", "Named, no amount")),
      comparison={"answer": "Mixed", "why": "Other consumer ($5.9bn) holds education loans and, on the segment averages, securities-based lending as well as personal loans and lines."}),
 dict(short="Truist", t="TFC", holding_company="Truist Financial Corporation",
      classes=[{"members": [CS, "tfc:OtherConsumerLendingMember"], "name": "Other consumer", "is": "Mixed other consumer"}],
      findings=dict(student=q("TFC", "student", NOT),
                    unsecured=q("TFC", "unsecured", "Yes, named among the segment's products; no amount given", "Named, no amount"),
                    secured_non_auto=q("TFC", "secured_non_auto", "Yes: marine and RV (originations stopped in 2026Q2) and point-of-sale power sports and home improvement; no amount given", "Named, no amount")),
      comparison={"answer": "Mixed", "why": "Other consumer ($33.2bn) holds unsecured personal loans beside point-of-sale home improvement, power sports, marine and RV lending, with no split."}),
 dict(short="Fifth Third", t="FITB", holding_company="Fifth Third Bancorp",
      classes=[{"name": "Unsecured (in Other consumer loans)", "amount_musd": 626, "is": "Unsecured or personal",
                "where": "MD&A, Credit Risk Management, Table 44: Other Consumer Portfolio Loans Outstanding by Product Type, June 30, 2026"},
               {"name": "Other secured (in Other consumer loans)", "amount_musd": 1299, "is": "Secured non-auto",
                "where": "MD&A, Table 44, June 30, 2026"},
               {"name": "Point-of-sale home improvement (in Other consumer loans)", "amount_musd": 613, "is": "Mixed other consumer",
                "where": "MD&A, Table 44, June 30, 2026"},
               {"name": "Third-party point-of-sale (in Other consumer loans)", "amount_musd": 285, "is": "Mixed other consumer",
                "where": "MD&A, Table 44, June 30, 2026"},
               {"name": "Indirect RV and marine, primarily (in Indirect secured consumer loans)", "amount_musd": 2800, "is": "Secured non-auto",
                "where": "MD&A, Consumer Portfolio, Indirect secured consumer portfolio: \"$2.8 billion primarily comprised of indirect recreational vehicle and marine loans\""},
               # The analyst's ruling, 15 Oct 2026: "solar might as well be considered unsecured" (the
               # panels are nominal collateral with little to recover). A judgment, not the filing's word.
               {"members": [CS, "fitb:SolarEnergyInstallationLoansMember"], "name": "Solar energy installation loans",
                "is": "Unsecured or personal"}],
      findings=dict(student=q("FITB", "student", NOT),
                    unsecured=q("FITB", "unsecured", "Yes: $626 million of unsecured loans, split out in Table 44; and solar energy installation loans, $4,314 million, counted as unsecured by the analyst's ruling of 15 Oct 2026 (\"solar might as well be considered unsecured\"), not by the filing", "Own lines"),
                    secured_non_auto=q("FITB", "secured_non_auto", "Yes: other secured $1,299 million, and about $2.8 billion of RV and marine", "Own lines")),
      # Corrected 15 Oct 2026: "Clean" held for the balance split, not for the rate. Its Call Report other
      # consumer averaged $10.2bn in 2026Q2 (Peers data), of which $626m is unsecured.
      comparison={"answer": "Mixed", "why": "Unsecured ($626m) and solar ($4.3bn, counted as unsecured) are about half its Call Report other consumer ($10.2bn average, 2026Q2); the rest is RV and marine ($2.8bn), other secured and point-of-sale, so its rate is not an unsecured rate."}),
 dict(short="Huntington", t="HBAN", holding_company="Huntington Bancshares Incorporated",
      classes=[{"members": [CS, "hban:RVandMarineFinanceLoanMember"], "name": "RV and marine", "is": "Secured non-auto"},
               {"members": [CS, "hban:OtherConsumerLoanMember"], "name": "Other consumer", "is": "Mixed other consumer"}],
      findings=dict(student=q("HBAN", "student", NOT), unsecured=q("HBAN", "unsecured", NOT),
                    secured_non_auto=q("HBAN", "secured_non_auto", "Yes: RV and marine is a class of its own", "Own class")),
      comparison={"answer": "Mixed", "why": "RV and marine ($5.7bn) is twice Other consumer ($2.6bn), which is not defined in the 10-Q; both sit in the Call Report's other consumer."}),
 dict(short="M&T", t="MTB", holding_company="M&T Bank Corporation",
      classes=[{"name": "Recreational finance", "amount_musd": 14856, "is": "Secured non-auto",
                "where": "Note 4, Loans and allowance for loan losses, table of current, past due and nonaccrual loans, June 30, 2026"},
               {"name": "Other (consumer)", "amount_musd": 2458, "is": "Mixed other consumer",
                "where": "Note 4, same table, under Consumer"}],
      findings=dict(student=q("MTB", "student", NOT), unsecured=q("MTB", "unsecured", NOT),
                    secured_non_auto=q("MTB", "secured_non_auto", "Yes: recreational finance, a class of its own", "Own class")),
      comparison={"answer": "Not comparable", "why": "Recreational finance ($14.9bn) is six times the undefined Other ($2.5bn): M&T's other consumer is mostly loans secured by RVs and boats."}),
 dict(short="Regions", t="RF", holding_company="Regions Financial Corporation",
      classes=[{"members": ["rf:OtherConsumerFinancingReceivableMember"], "name": "Other consumer", "is": "Mixed other consumer"}],
      findings=dict(student=q("RF", "student", NOT), unsecured=q("RF", "unsecured", NOT), secured_non_auto=q("RF", "secured_non_auto", NOT)),
      comparison={"answer": "Mixed", "why": "Other consumer ($5.5bn) is indirect and direct consumer loans, overdrafts and revolving loans, with home improvement lending named; no split."}),
 dict(short="Zions", t="ZION", holding_company="Zions Bancorporation, N.A.",
      classes=[{"name": "Other (consumer)", "amount_musd": 114, "is": "Mixed other consumer",
                "where": "Note 6, Loans, Leases, and Loans Held for Sale schedule, under Consumer"}],
      findings=dict(student=q("ZION", "student", NOT), unsecured=q("ZION", "unsecured", NOT), secured_non_auto=q("ZION", "secured_non_auto", NOT)),
      comparison={"answer": "Not comparable", "why": "Other consumer is $114m, too small to compare with."}),
 dict(short="First Citizens", t="FCNCA", holding_company="First Citizens BancShares, Inc.",
      classes=[{"members": [CS, "fcnca:ConsumerLoanOtherMember"], "name": "Other consumer", "is": "Mixed other consumer"}],
      findings=dict(student=q("FCNCA", "student", NOT),
                    unsecured=q("FCNCA", "unsecured", "Unsecured consumer lines of credit are named in its charge-off policy; no amount given", "Named, no amount"),
                    secured_non_auto=q("FCNCA", "secured_non_auto", NOT)),
      comparison={"answer": "Mixed", "why": "Other consumer ($0.8bn) is not defined in the 10-Q, and $388m of it is revolving."}),
 dict(short="U.S. Bank", t="USB", holding_company="U.S. Bancorp",
      classes=[{"members": [CS, "usb:ConsumerRevolvingCreditLoanMember"], "name": "Revolving credit", "is": "Mixed other consumer"},
               {"members": [CS, "usb:ConsumerInstallmentLoanMember"], "name": "Installment", "is": "Mixed other consumer"},
               {"members": [CS, "usb:ConsumerRetailLeasingLoanMember"], "name": "Retail leasing", "is": "Other"}],
      findings=dict(student=q("USB", "student", NOT), unsecured=q("USB", "unsecured", NOT), secured_non_auto=q("USB", "secured_non_auto", NOT)),
      comparison={"answer": "Mixed", "why": "Revolving credit ($5.4bn) and Installment ($15.0bn) are split, but the 10-Q does not say what Installment holds or whether either is unsecured."}),
 dict(short="JPMorgan", t="JPM", holding_company="JPMorgan Chase & Co.",
      classes=[{"members": ["jpm:ConsumerExcludingCreditCardLoanPortfolioSegmentMember", "us-gaap:AutomobileLoanMember"],
                "name": "Auto and other", "is": "Mixed other consumer"}],
      findings=dict(student=q("JPM", "student", NOT),
                    unsecured=q("JPM", "unsecured", "Yes, inside Auto and other with scored auto and business banking; no amount given", "In Auto and other"),
                    secured_non_auto=q("JPM", "secured_non_auto", "Securities-based lending sits in the wholesale portfolio, not a consumer class", "Wholesale, not consumer")),
      comparison={"answer": "Not comparable", "why": "Its consumer class Auto and other ($66.5bn) is mostly auto and business banking; consumer unsecured loans are inside it with no amount."}),
 dict(short="Wells Fargo", t="WFC", holding_company="Wells Fargo & Company",
      classes=[{"name": "Securities-based (in Other consumer)", "amount_musd": 32231, "is": "Secured non-auto",
                "where": "MD&A, Risk Management, Credit Risk Management, Table 16: Credit Card, Auto, and Other Consumer Loans"},
               {"name": "Other (in Other consumer)", "amount_musd": 6493, "is": "Mixed other consumer",
                "where": "MD&A, Table 16"}],
      findings=dict(student=q("WFC", "student", NOT),
                    unsecured=q("WFC", "unsecured", "Personal lending is named; the filing does not tie it to a class or call it unsecured", "Named, no class"),
                    secured_non_auto=q("WFC", "secured_non_auto", "Yes: $32.2 billion of securities-based loans in Other consumer", "Own line")),
      comparison={"answer": "Not comparable", "why": "Five sixths of Other consumer ($32.2bn of $38.7bn) is securities-based lending, secured by brokerage accounts."}),
 dict(short="Bank of America", t="BAC", holding_company="Bank of America Corporation",
      classes=[{"name": "U.S. securities-based lending (in Direct/Indirect consumer)", "amount_musd": 61900, "is": "Secured non-auto",
                "where": "Note 5, aging table, footnote (2) to Direct/Indirect consumer: \"U.S. securities-based lending loans of $61.9 billion\""},
               {"name": "Non-U.S. consumer loans (in Direct/Indirect consumer)", "amount_musd": 3200, "is": "Other",
                "where": "Note 5, aging table, footnote (2) to Direct/Indirect consumer: \"non-U.S. consumer loans of $3.2 billion\""},
               {"name": "Other consumer", "amount_musd": 182, "is": "Other",
                "where": "Note 5, aging table by class of financing receivables, June 30, 2026, Total Outstandings column"}],
      findings=dict(student=q("BAC", "student", NOT),
                    unsecured=q("BAC", "unsecured", "Unsecured consumer lending is named; no amount given", "Named, no amount"),
                    secured_non_auto=q("BAC", "secured_non_auto", "Yes: $65.0 billion of securities-based lending in Direct/Indirect consumer", "In a sentence")),
      comparison={"answer": "Not comparable", "why": "Its non-card, non-mortgage consumer book is securities-based lending ($61.9bn U.S.) and auto and specialty ($52.4bn); Other consumer ($182m) is mainly overdrafts."}),
 dict(short="Citi", t="C", holding_company="Citigroup Inc.",
      classes=[{"name": "Personal, small business and other (North America offices)", "amount_musd": 34068, "is": "Mixed other consumer",
                "where": "Note 12, Loans, Consumer Loans, Delinquencies and Non-Accrual Status at June 30, 2026, Total loans column"}],
      findings=dict(student=q("C", "student", NOT),
                    unsecured=q("C", "unsecured", "Yes: $3.8 billion of Installment Lending (personal installment loans); the filing does not say which class holds it", "$3.8bn, no class"),
                    secured_non_auto=q("C", "secured_non_auto", "Yes: $36.5 billion of securities-based lending in Wealth", "$36.5bn, no class")),
      comparison={"answer": "Mixed", "why": "Personal, small business and other ($34.1bn in North America) mixes Wealth's securities-based lending with personal installment loans ($3.8bn) and small business."}),
 dict(short="Capital One", t="COF", holding_company="Capital One Financial Corporation",
      classes=[{"members": ["cof:PersonalLoansPortfolioSegmentMember"], "name": "Personal loans", "is": "Unsecured or personal"},
               {"members": [CS, "cof:RetailBankingMember"], "name": "Retail banking", "is": "Other"}],
      # Found by the tie-out's own search of the filed text (15 Oct 2026); the reader had "not stated".
      findings=dict(student={"answer": "No: Discover sold its student loan portfolio before the merger closed",
                             "short": "Sold before merger",
                             "quote": "Although Discover sold its student loan portfolio and ceased servicing student loans prior to the closing of the Transaction",
                             "where": "Legal and regulatory matters, the paragraph on Discover's 2020 CFPB consent order"},
                    unsecured=q("COF", "unsecured", "Yes: Personal loans, $8.6 billion, a class of its own (the filing does not call them unsecured)", "Own class"),
                    secured_non_auto=q("COF", "secured_non_auto", NOT)),
      comparison={"answer": "Clean", "why": "Personal loans ($8.6bn, from Discover) are a class of their own, and Discover's student loans were sold before the merger; its Call Report other consumer is these loans."}),
 dict(short="SoFi", t="SOFI", holding_company="SoFi Technologies, Inc.",
      classes=[{"name": "Personal loans (held for sale, at fair value)", "amount_musd": 27505.29, "is": "Unsecured or personal",
                "where": "Note 4, Loans, disaggregated loan table, loans held for sale at fair value (printed in thousands: 27,505,290)"},
               {"name": "Personal loans (held for sale, at lower of cost or fair value)", "amount_musd": 55.841, "is": "Unsecured or personal",
                "where": "Note 4, same table (printed in thousands: 55,841)"},
               {"name": "Student loans (held for investment, at fair value)", "amount_musd": 16920.564, "is": "Student",
                "where": "Note 4, same table (printed in thousands: 16,920,564)"}],
      findings=dict(student=q("SOFI", "student", "Yes: $16.9 billion, at fair value", "Own class"),
                    unsecured=said("SOFI", "unsecured", "Personal loans of $27.6 billion, at fair value; the 10-Q does not call them unsecured",
                                   "not stated", "Note 4, Loans: personal loans are not described as unsecured anywhere in the 10-Q"),
                    secured_non_auto=q("SOFI", "secured_non_auto", NOT)),
      comparison={"answer": "Not comparable", "why": "Personal and student loans are carried at fair value, so its Call Report files no charge-offs on them; its 10-Q gives 2.62% (personal) and 0.61% (student) for 2026Q2."}),
]

out = {"_what": "What each peer's consumer book holds, from its own quarterly filing with the SEC, for the Peer "
                "loan classes tab (src/threshold_engine/peers/loan_classes_tab.py). Amounts are never typed "
                "here for a class the filing tags: 'members' names the XBRL members and the build reads the "
                "amount from the cached filing. A class the filing prints but does not tag by class gives "
                "'amount_musd' as printed and 'where'. 'is' is a judgement: what the class is counted as. Every "
                "finding quotes the filing verbatim (checked by script against the filing's text, 15 Oct 2026) "
                "and says where.",
       "_built": "15 Oct 2026, from the three readers' records (docs/tie-out/peer-loan-classes-2026q2/record/research_a/b/c.json) and the "
                 "judgements in make_config.py; 'not stated' quotes mean the terms named in 'where' were "
                 "searched for and not found.",
       "quarter": "2026Q2", "banks": []}
for b in banks:
    t = b.pop("t")
    f = F[t]
    b["cik"] = f["cik"]
    b["filing_url"] = f["dir"] + f["primary"]
    out["banks"].append({k: b[k] for k in ("short", "cik", "holding_company", "filing_url", "classes", "findings",
                                            "comparison")})
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(len(out["banks"]), "banks")
