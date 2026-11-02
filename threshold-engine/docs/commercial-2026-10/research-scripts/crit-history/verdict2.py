import json, os, sys, re
sys.path.insert(0, os.path.dirname(__file__)); from analyze import local
COMM = re.compile(r"Commercial|Industrial|Wholesale|Construction|RealEstate|Realestate|Lease|Leasing|Corporate|Business|Municipal|OwnerOccupied|Investor|Builder|Multifamily|Agricultur|FinancialInstitution|Government|CandI|CAndI|CNI|CRE|Cre(?=[A-Z])|Middle|Dealer|Equipment|Energy|Healthcare|Sector|Specialty|Asset", re.I)
CONS = re.compile(r"Consumer|Residential|HomeEquity|CreditCard|Card|Auto(?!mat)|Student|Indirect|Installment|Marine|Personal|Retail|OneToFour|1To4", re.I)
STRONGCOMM = re.compile(r"Commercial|Wholesale|Industrial|Corporate", re.I)
CRIT = re.compile(r"SpecialMention|Substandard|Doubtful|Criticized|Criticised|Classified(?!AsHeld)|Olem|OLEM|EspeciallyMentioned|Watch")
RATING = re.compile(r"ExternalCreditRating|InvestmentGrade|Rating[A-Z]|Aaa|Bbb|BBB")
BADCON = re.compile(r"Modification|Guarantee|Derivative|Commitment|Percentage|Percent|Ratio|NumberOf|FairValue|ChargeOff|Recover|Provision|Impaired|Troubled|Unfunded|LineOfCredit|LetterOfCredit|HeldForSale|Deposits|InventoryLand|LandImprovements|BuildingsAndImprovements|MachineryAndEquipment|LeaseholdImprovements|OperatingBranch|ParcelsOf|EnergyLoans|EnergyRelated")
BADAX = re.compile(r"Guarantee|Derivative|Modification|Impaired|Troubled|PastDue|Delinquen|Disposal|AvailableForSaleSecurities|LongTermPurchaseCommitment|ScheduleOfAvailableForSale", re.I)
GENERIC_CON = re.compile(r"^(us-gaap:|[a-z]+:)(FinancingReceivable|LoansAndLeasesReceivable(NetOfDeferredIncome|GrossCarryingAmount|NetReportedAmount)?|LoansReceivable|NotesReceivable(Net|Gross)?|LoansAndLeasesReceivableGrossCarryingAmount.*|FinancingReceivableRecordedInvestment.*|FinancingReceivableExcludingAccruedInterest.*|FinancingReceivableAndNetInvestmentInLease.*|.*(Originated|Revolving).*)$")
def iscomm(s): return bool(COMM.search(s)) and (not CONS.search(s) or bool(STRONGCOMM.search(s)))
def keep(f):
    d, q, oth, cq, v, u = f
    if not re.search(r"usd", u, re.I) and not re.search(r"^u\d|^U\d|iso4217", u): pass
    if BADCON.search(local(q)): return False
    if "Allowance" in q and "BeforeAllowance" not in q: return False
    if any(BADAX.search(a) for a in oth): return False
    try: float(v)
    except: return False
    return True
def judge(facts, date):
    fs = [f for f in facts if f[0] == date and keep(f)]
    dimall = {}; conall = {}; totall = {}; cqaxes = set()
    GENSEG = re.compile(r"us-gaap:Commercial(Portfolio)?(Segment)?(Loan)?Member")
    for d, q, oth, cq, v, u in fs:
        dimkey = "|".join(sorted("%s=%s" % (local(a), m) for a, m in oth.items()))
        generic = bool(GENERIC_CON.match(q))
        label = dimkey + ("" if generic else "  [concept " + q + "]")
        if not iscomm(label): continue
        cms = set(cq.values()); cqaxes.update(cq.keys())
        lone_generic_seg = len(oth) == 1 and bool(GENSEG.fullmatch(list(oth.values())[0]))
        if dimkey and iscomm(dimkey) and not (lone_generic_seg and generic):
            dimall.setdefault(dimkey, set()).update(cms)
        if not generic:
            conall.setdefault(q + ("|" + dimkey if dimkey else ""), set()).update(cms)
        if dimkey == "" or lone_generic_seg:
            totall.setdefault(label, set()).update(cms)
    hascrit = lambda ms: any(CRIT.search(local(m)) for m in ms)
    hasrat = lambda ms: any(RATING.search(local(m)) for m in ms)
    dimrows = {k: sorted(v) for k, v in dimall.items() if hascrit(v)}
    conrows = {k: sorted(v) for k, v in conall.items() if hascrit(v)}
    ratrows = {k: sorted(v) for k, v in dimall.items() if not hascrit(v) and hasrat(v)}
    tot = {k: sorted(v) for k, v in totall.items() if hascrit(v)}
    GEN = re.compile(r"^[A-Za-z]*Axis=us-gaap:Commercial(Portfolio)?(Segment)?(Loan)?Member$")
    if len(dimrows) == 1 and re.fullmatch(r"[A-Za-z]*Axis=us-gaap:CommercialRealEstate(PortfolioSegment)?Member", list(dimrows)[0]):
        g = [k for k in tot if GEN.match(k)]
        if g: dimrows["(Commercial segment beside CRE segment) " + g[0]] = tot[g[0]]
    if len(dimrows) >= 2: verdict = "DIM"
    elif len(conrows) >= 2: verdict = "CONCEPT"
    elif dimrows or conrows or tot: verdict = "TOTAL"
    elif len(ratrows) >= 2: verdict = "RATING"
    else: verdict = "NONE"
    if verdict == "RATING":
        ccats = sorted({m for v in ratrows.values() for m in v})
    else:
        gradeax = set()
        for d, q, oth, cq, v_, u in fs:
            for a, m in cq.items():
                if CRIT.search(local(m)): gradeax.add(a)
        ccats = set()
        for d, q, oth, cq, v_, u in fs:
            dimkey = "|".join(sorted("%s=%s" % (local(a), m) for a, m in oth.items()))
            label = dimkey + ("" if GENERIC_CON.match(q) else "  [concept " + q + "]")
            if iscomm(label): ccats.update(m for a, m in cq.items() if a in gradeax)
        ccats = sorted(ccats) if verdict != "NONE" else []
    return {"verdict": verdict, "dimrows": dimrows, "conrows": conrows, "ratrows": ratrows, "totrows": tot,
            "ccats": ccats, "cqaxes": sorted(cqaxes)}
if __name__ == "__main__":
    D = sys.argv[1]
    plan = json.load(open(os.path.join(D, "plan.json")))
    res = {}
    for t, cik, per, forms, ch in plan:
        e = {"period": per, "forms": forms}
        if not ch: e["status"] = "NO_XBRL"
        else:
            acc, form, name = ch; p = os.path.join(D, "sum2", acc + ".json")
            e.update(acc=acc, form=form, url="https://www.sec.gov/Archives/edgar/data/%d/%s/%s" % (cik, acc.replace("-", ""), name))
            if not os.path.exists(p): e["status"] = "PENDING"
            else:
                r = json.load(open(p)); e["status"] = "OK"; e["dei_pe"] = r["dei"].get("DocumentPeriodEndDate")
                pe = per
                if e["dei_pe"] and e["dei_pe"] != per and not any(f[0] == per for f in r["facts"]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["dei_pe"]): pe = e["dei_pe"]; e["note"] = "EDGAR reportDate %s; instance DocumentPeriodEndDate %s used" % (per, pe)
                e.update(judge(r["facts"], pe))
                comp = {}
                for d in sorted({f[0] for f in r["facts"]}):
                    if d != pe and len(d) == 10:
                        jj = judge(r["facts"], d)
                        if jj["verdict"] != "NONE": comp[d] = jj["verdict"]
                e["comparatives"] = comp
        res.setdefault(t, []).append(e)
    json.dump(res, open(os.path.join(D, "verdicts2.json"), "w"), indent=1)
    ab = {"RATING": "R", "DIM": "D", "CONCEPT": "C", "TOTAL": "T", "NONE": "-", "NO_XBRL": "x", "PENDING": "?"}
    for t, es in res.items():
        print("%-6s" % t, "".join(ab[e.get("verdict") or e["status"]] + (" " if e["period"][5:7] == "12" else "") for e in es))
