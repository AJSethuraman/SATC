"""Domain content: segment definitions, question sets, and ratio specs.

Segments are config-driven: adding a segment (agribusiness, healthcare,
small-business-via-consumer-KRIs) means adding an entry to SEGMENTS with its
sections/questions/ratios - no builder changes required. Question sections
map to the individual-review criteria in the 2020 Interagency Guidance on
Credit Risk Review Systems.

Ratio formula templates use [Input Label] placeholders that the form builder
resolves to cell addresses. Every template guards its denominator so a blank
form never produces #DIV/0!.

Each ratio: (rid, label, formula_template, number_format, threshold_metric,
direction) where threshold_metric names a Crosswalk metric whose in-force
value (for the bank's primary agency, as of the review date) drives the
pass/exception flag; direction 'max' = exception when ratio exceeds the
threshold, 'min' = exception when it falls below.
"""

# Standard sections from the 2020 CRR guidance review criteria.
S_GRADE = "Credit Quality & Risk-Grade Accuracy"
S_UW = "Underwriting Soundness"
S_REPAY = "Repayment Sources & Projections"
S_GUAR = "Guarantor / Sponsor Creditworthiness"
S_DOC = "Credit & Collateral Documentation / Lien Perfection"
S_APPR = "Approval Authority"
S_COV = "Covenant Adherence"
S_POL = "Policy Compliance"

HIGH, MED, LOW = "High", "Medium", "Low"

_CORE = [
    (S_GRADE, "LOB-assigned risk grade is supported by current financial analysis.", HIGH),
    (S_GRADE, "Grade reflects all material credit weaknesses identified in the file.", HIGH),
    (S_GRADE, "Grade was reviewed/affirmed within policy frequency requirements.", MED),
    (S_UW, "Underwriting at origination conformed to policy standards in effect.", HIGH),
    (S_UW, "Financial statements meet policy quality/recency requirements (audit level, age).", MED),
    (S_UW, "Analysis critically evaluates borrower-provided information rather than restating it.", HIGH),
    (S_REPAY, "Primary repayment source is clearly identified and quantitatively supported.", HIGH),
    (S_REPAY, "Secondary repayment source is identified and realizable.", MED),
    (S_REPAY, "Projection assumptions are reasonable versus historical performance and market data.", HIGH),
    (S_GUAR, "Guarantor/sponsor financial condition is current, analyzed, and supports reliance.", MED),
    (S_GUAR, "Guaranty enforceability documented (signed, unconditional unless approved otherwise).", MED),
    (S_DOC, "All required credit documents are present, current, and properly executed.", HIGH),
    (S_DOC, "Lien positions are perfected and verified (searches, filings, titles).", HIGH),
    (S_DOC, "Insurance requirements are met and the bank is loss payee where required.", LOW),
    (S_APPR, "Credit was approved within delegated authority of the approving officer(s).", HIGH),
    (S_APPR, "Policy exceptions at approval were identified, justified, and approved at proper level.", MED),
    (S_COV, "Covenant compliance is tested at required frequency with evidence retained.", MED),
    (S_COV, "Covenant breaches (if any) were identified, reported, and waived/cured per policy.", HIGH),
    (S_POL, "Credit complies with internal lending policy limits (hold limits, tenor, pricing floors).", MED),
    (S_POL, "Required periodic monitoring (annual review, site visits) is current.", MED),
]

SEGMENTS = {
    "CI": {
        "name": "C&I / Commercial",
        "sheet": "LS_CI",
        "sections_extra": [
            ("Five Cs of Credit", [
                ("Character: management track record, credit history, and integrity assessed.", MED),
                ("Capacity: cash-flow capacity analysis covers debt service under stress.", HIGH),
                ("Capital: borrower equity/tangible net worth is adequate for the risk.", MED),
                ("Collateral: valuation basis is current and discounts are appropriate.", MED),
                ("Conditions: industry, market, and macro conditions are evaluated.", LOW),
            ]),
            ("Global Cash Flow", [
                ("Global cash flow combines business and guarantor sources with consistent treatment of taxes/living expenses.", HIGH),
                ("Inter-company / related-entity flows are identified and not double-counted.", MED),
            ]),
        ],
        "inputs": [
            ("Revenue ($000)", "usd", ""),
            ("EBITDA ($000)", "usd", ""),
            ("Interest Expense ($000)", "usd", ""),
            ("CPLTD ($000)", "usd", "Current portion of long-term debt"),
            ("Cash Taxes ($000)", "usd", ""),
            ("Maintenance Capex ($000)", "usd", ""),
            ("Distributions ($000)", "usd", ""),
            ("Total Debt ($000)", "usd", ""),
            ("Senior Debt ($000)", "usd", ""),
            ("Current Assets ($000)", "usd", ""),
            ("Current Liabilities ($000)", "usd", ""),
            ("Accounts Receivable ($000)", "usd", ""),
            ("Inventory ($000)", "usd", ""),
            ("Accounts Payable ($000)", "usd", ""),
            ("COGS ($000)", "usd", ""),
            ("Tangible Net Worth ($000)", "usd", ""),
            ("Guarantor Cash Flow ($000)", "usd", "Personal CF available for debt service"),
            ("Guarantor Debt Service ($000)", "usd", ""),
        ],
        "ratios": [
            ("CI-R1", "Total Debt / EBITDA", "=IF([EBITDA ($000)]<=0,\"n/m\",[Total Debt ($000)]/[EBITDA ($000)])", "x", "Total Debt / EBITDA", "max"),
            ("CI-R2", "Senior Debt / EBITDA", "=IF([EBITDA ($000)]<=0,\"n/m\",[Senior Debt ($000)]/[EBITDA ($000)])", "x", "Senior Debt / EBITDA", "max"),
            ("CI-R3", "DSCR", "=IF(([Interest Expense ($000)]+[CPLTD ($000)])=0,\"n/m\",([EBITDA ($000)]-[Cash Taxes ($000)]-[Maintenance Capex ($000)]-[Distributions ($000)])/([Interest Expense ($000)]+[CPLTD ($000)]))", "x2", "Minimum DSCR", "min"),
            ("CI-R4", "Fixed-Charge Coverage", "=IF(([Interest Expense ($000)]+[CPLTD ($000)])=0,\"n/m\",([EBITDA ($000)]-[Cash Taxes ($000)]-[Distributions ($000)])/([Interest Expense ($000)]+[CPLTD ($000)]))", "x2", None, None),
            ("CI-R5", "Interest Coverage", "=IF([Interest Expense ($000)]=0,\"n/m\",[EBITDA ($000)]/[Interest Expense ($000)])", "x", None, None),
            ("CI-R6", "Current Ratio", "=IF([Current Liabilities ($000)]=0,\"n/m\",[Current Assets ($000)]/[Current Liabilities ($000)])", "x2", None, None),
            ("CI-R7", "Working Capital Cycle (days)", "=IF(OR([Revenue ($000)]=0,[COGS ($000)]=0),\"n/m\",365*[Accounts Receivable ($000)]/[Revenue ($000)]+365*[Inventory ($000)]/[COGS ($000)]-365*[Accounts Payable ($000)]/[COGS ($000)])", "num", None, None),
            ("CI-R8", "Debt / Tangible Net Worth", "=IF([Tangible Net Worth ($000)]<=0,\"n/m\",[Total Debt ($000)]/[Tangible Net Worth ($000)])", "x2", None, None),
            ("CI-R9", "Global DSCR (incl. guarantor)", "=IF(([Interest Expense ($000)]+[CPLTD ($000)]+[Guarantor Debt Service ($000)])=0,\"n/m\",([EBITDA ($000)]-[Cash Taxes ($000)]-[Maintenance Capex ($000)]-[Distributions ($000)]+[Guarantor Cash Flow ($000)])/([Interest Expense ($000)]+[CPLTD ($000)]+[Guarantor Debt Service ($000)]))", "x2", None, None),
        ],
    },
    "CRE": {
        "name": "Commercial Real Estate",
        "sheet": "LS_CRE",
        "sections_extra": [
            ("Property & Market (subform: Office / Multifamily / Retail)", [
                ("Property-type risk factors (office obsolescence, MF supply, retail anchor risk) addressed for the subject type.", MED),
                ("Occupancy and lease rollover within 24 months are analyzed against market.", HIGH),
                ("Cap-rate sensitivity / stressed-value analysis is documented.", MED),
            ]),
            ("Appraisal & Evaluation (FIRREA / USPAP)", [
                ("Valuation product type (appraisal vs. evaluation) meets the regulatory threshold for this transaction size.", HIGH),
                ("Appraiser was engaged independently of the credit function.", HIGH),
                ("Appraisal is valid/recent for this action or revalidation is documented.", MED),
                ("Appraisal review evidence is in file and issues were resolved.", MED),
            ]),
        ],
        "inputs": [
            ("Net Operating Income ($000)", "usd", "In-place, trailing 12 months"),
            ("Annual Debt Service ($000)", "usd", ""),
            ("Loan Commitment ($000)", "usd", ""),
            ("Appraised Value ($000)", "usd", ""),
            ("Current Occupancy (%)", "pct", ""),
            ("Leases Rolling 24 Mo (%)", "pct", ""),
            ("In-Place Cap Rate (%)", "pct", ""),
            ("Stressed Cap Rate (%)", "pct", "Key assumption"),
        ],
        "ratios": [
            ("CRE-R1", "DSCR", "=IF([Annual Debt Service ($000)]=0,\"n/m\",[Net Operating Income ($000)]/[Annual Debt Service ($000)])", "x2", "Minimum DSCR", "min"),
            ("CRE-R2", "LTV", "=IF([Appraised Value ($000)]=0,\"n/m\",[Loan Commitment ($000)]/[Appraised Value ($000)])", "pct", "Maximum LTV", "max"),
            ("CRE-R3", "Debt Yield", "=IF([Loan Commitment ($000)]=0,\"n/m\",[Net Operating Income ($000)]/[Loan Commitment ($000)])", "pct", None, None),
            ("CRE-R4", "Stressed Value ($000)", "=IF([Stressed Cap Rate (%)]=0,\"n/m\",[Net Operating Income ($000)]/[Stressed Cap Rate (%)])", "usd", None, None),
            ("CRE-R5", "Stressed LTV", "=IF(OR([Stressed Cap Rate (%)]=0,[Net Operating Income ($000)]=0),\"n/m\",[Loan Commitment ($000)]/([Net Operating Income ($000)]/[Stressed Cap Rate (%)]))", "pct", None, None),
        ],
    },
    "LL": {
        "name": "Leveraged Lending",
        "sheet": "LS_LL",
        "sections_extra": [
            ("Leveraged Lending Specifics", [
                ("Transaction meets the bank's leveraged-lending definition and is flagged in systems.", MED),
                ("Sponsor track record, support history, and equity contribution are analyzed.", MED),
                ("Covenant package adequacy assessed; cov-lite structure identified and justified.", HIGH),
                ("EBITDA adjustments/add-backs are scrutinized and supportable.", HIGH),
                ("Enterprise-value cushion is estimated on a supportable basis.", MED),
                ("Repayment-capacity test (de-lever >=50% of total debt over 5-7 years, base case) is evidenced.", HIGH),
            ]),
        ],
        "inputs": [
            ("Reported EBITDA ($000)", "usd", ""),
            ("EBITDA Add-Backs ($000)", "usd", "Key assumption - scrutinize"),
            ("Total Debt ($000)", "usd", ""),
            ("Senior Debt ($000)", "usd", ""),
            ("Base-Case Annual FCF ($000)", "usd", "Free cash flow available for debt repayment"),
            ("Enterprise Value ($000)", "usd", ""),
            ("Interest Expense ($000)", "usd", ""),
        ],
        "ratios": [
            ("LL-R1", "Adjusted EBITDA ($000)", "=[Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)]", "usd", None, None),
            ("LL-R2", "Add-Backs % of Adj. EBITDA", "=IF(([Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)])=0,\"n/m\",[EBITDA Add-Backs ($000)]/([Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)]))", "pct", None, None),
            ("LL-R3", "Total Debt / Adj. EBITDA", "=IF(([Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)])<=0,\"n/m\",[Total Debt ($000)]/([Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)]))", "x", "Total Debt / EBITDA", "max"),
            ("LL-R4", "Senior Debt / Adj. EBITDA", "=IF(([Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)])<=0,\"n/m\",[Senior Debt ($000)]/([Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)]))", "x", "Senior Debt / EBITDA", "max"),
            ("LL-R5", "Interest Coverage", "=IF([Interest Expense ($000)]=0,\"n/m\",([Reported EBITDA ($000)]+[EBITDA Add-Backs ($000)])/[Interest Expense ($000)])", "x", None, None),
            ("LL-R6", "Years to Repay 50% of Total Debt", "=IF([Base-Case Annual FCF ($000)]<=0,\"n/m\",0.5*[Total Debt ($000)]/[Base-Case Annual FCF ($000)])", "num1", None, None),
            ("LL-R7", "EV Cushion", "=IF([Enterprise Value ($000)]=0,\"n/m\",([Enterprise Value ($000)]-[Total Debt ($000)])/[Enterprise Value ($000)])", "pct", None, None),
        ],
    },
    "ABL": {
        "name": "Asset-Based Lending",
        "sheet": "LS_ABL",
        "sections_extra": [
            ("Borrowing Base Mechanics", [
                ("Eligibility criteria (AR aging, concentration, cross-age; inventory categories) applied per agreement.", HIGH),
                ("Ineligibles are identified, current, and correctly deducted.", HIGH),
                ("Dilution is tracked and advance rates remain appropriate to dilution experience.", MED),
                ("Field examination is current per policy frequency and findings were cleared.", HIGH),
                ("Inventory appraisal (NOLV) is current and supports the advance rate.", MED),
                ("Borrowing-base certificate frequency and verification meet monitoring requirements.", MED),
            ]),
        ],
        "inputs": [
            ("Gross Accounts Receivable ($000)", "usd", ""),
            ("Ineligible AR ($000)", "usd", ""),
            ("AR Advance Rate (%)", "pct", "Per credit agreement"),
            ("Gross Inventory ($000)", "usd", ""),
            ("Ineligible Inventory ($000)", "usd", ""),
            ("Inventory Advance Rate (%)", "pct", "Per credit agreement"),
            ("Reserves ($000)", "usd", "Availability reserves"),
            ("Outstanding Balance ($000)", "usd", ""),
            ("Dilution (%)", "pct", "Trailing 12-month"),
        ],
        "ratios": [
            ("ABL-R1", "Eligible AR ($000)", "=[Gross Accounts Receivable ($000)]-[Ineligible AR ($000)]", "usd", None, None),
            ("ABL-R2", "Eligible Inventory ($000)", "=[Gross Inventory ($000)]-[Ineligible Inventory ($000)]", "usd", None, None),
            ("ABL-R3", "Borrowing Base ($000)", "=([Gross Accounts Receivable ($000)]-[Ineligible AR ($000)])*[AR Advance Rate (%)]+([Gross Inventory ($000)]-[Ineligible Inventory ($000)])*[Inventory Advance Rate (%)]-[Reserves ($000)]", "usd", None, None),
            ("ABL-R4", "Availability ($000)", "=([Gross Accounts Receivable ($000)]-[Ineligible AR ($000)])*[AR Advance Rate (%)]+([Gross Inventory ($000)]-[Ineligible Inventory ($000)])*[Inventory Advance Rate (%)]-[Reserves ($000)]-[Outstanding Balance ($000)]", "usd", None, None),
            ("ABL-R5", "Collateral Coverage (BB / Outstandings)", "=IF([Outstanding Balance ($000)]=0,\"n/m\",(([Gross Accounts Receivable ($000)]-[Ineligible AR ($000)])*[AR Advance Rate (%)]+([Gross Inventory ($000)]-[Ineligible Inventory ($000)])*[Inventory Advance Rate (%)]-[Reserves ($000)])/[Outstanding Balance ($000)])", "x2", None, None),
            ("ABL-R6", "Ineligible % of Gross AR", "=IF([Gross Accounts Receivable ($000)]=0,\"n/m\",[Ineligible AR ($000)]/[Gross Accounts Receivable ($000)])", "pct", None, None),
        ],
    },
    "ARG": {
        "name": "ARG / Workout",
        "sheet": "LS_ARG",
        "sections_extra": [
            ("Impairment, Accrual & Workout (ASC 326)", [
                ("Impairment measurement method is appropriate (collateral-dependent practical expedient applied correctly).", HIGH),
                ("Nonaccrual status is correct and timely per regulatory definitions.", HIGH),
                ("Modification / TDR-successor disclosures and tracking are accurate.", MED),
                ("Charge-offs were taken timely when loss was confirmed; recoveries posted correctly.", HIGH),
                ("Liquidation values reflect current, supportable collateral data and costs to sell.", MED),
                ("Exit strategy is documented, realistic, and progressing against milestones.", MED),
                ("Criticized/classified migration history is captured accurately in systems.", LOW),
            ]),
        ],
        "inputs": [
            ("Loan Balance ($000)", "usd", ""),
            ("Specific Reserve ($000)", "usd", ""),
            ("Prior Charge-Offs ($000)", "usd", ""),
            ("Recoveries to Date ($000)", "usd", ""),
            ("Collateral Value - Gross ($000)", "usd", "Most recent valuation"),
            ("Liquidation Discount (%)", "pct", "Key assumption"),
            ("Estimated Costs to Sell (%)", "pct", ""),
        ],
        "ratios": [
            ("ARG-R1", "Net Liquidation Value ($000)", "=[Collateral Value - Gross ($000)]*(1-[Liquidation Discount (%)])*(1-[Estimated Costs to Sell (%)])", "usd", None, None),
            ("ARG-R2", "Collateral Coverage (NLV / Balance)", "=IF([Loan Balance ($000)]=0,\"n/m\",[Collateral Value - Gross ($000)]*(1-[Liquidation Discount (%)])*(1-[Estimated Costs to Sell (%)])/[Loan Balance ($000)])", "x2", None, None),
            ("ARG-R3", "Collateral Shortfall ($000)", "=MAX(0,[Loan Balance ($000)]-[Collateral Value - Gross ($000)]*(1-[Liquidation Discount (%)])*(1-[Estimated Costs to Sell (%)]))", "usd", None, None),
            ("ARG-R4", "Reserve Coverage of Shortfall", "=IF(MAX(0,[Loan Balance ($000)]-[Collateral Value - Gross ($000)]*(1-[Liquidation Discount (%)])*(1-[Estimated Costs to Sell (%)]))=0,\"n/a\",[Specific Reserve ($000)]/MAX(0.001,[Loan Balance ($000)]-[Collateral Value - Gross ($000)]*(1-[Liquidation Discount (%)])*(1-[Estimated Costs to Sell (%)])))", "pct", None, None),
            ("ARG-R5", "Net Charge-Off ($000)", "=[Prior Charge-Offs ($000)]-[Recoveries to Date ($000)]", "usd", None, None),
        ],
    },
    "COMP": {
        "name": "General Compliance Crosswalk",
        "sheet": "LS_COMP",
        "sections_extra": [
            ("Risk-Rating Framework", [
                ("Assigned rating maps correctly to the regulatory scale (Pass / Special Mention / Substandard / Doubtful / Loss).", HIGH),
                ("Rating definitions applied match the bank's approved rating policy.", MED),
            ]),
            ("ALLL / CECL Linkage", [
                ("Risk grade flows correctly into the CECL pool / individual evaluation status.", HIGH),
                ("Individually evaluated credits have current, supportable measurement inputs.", MED),
            ]),
            ("Consumer-Adjacent Touchpoints", [
                ("Flood determination obtained and insurance in place for improved collateral in SFHA.", HIGH),
                ("Fair-lending / HMDA data points captured where the credit is reportable.", MED),
            ]),
        ],
        "inputs": [],
        "ratios": [],
    },
}

# Core question sections appear on every segment's line sheet.
CORE_QUESTIONS = _CORE

# Extension point: copy this template into SEGMENTS to add a new segment.
SEGMENT_TEMPLATE = {
    "name": "<display name>",
    "sheet": "LS_<CODE>",
    "sections_extra": [("<segment-specific section>", [("<question>", MED)])],
    "inputs": [("<input label> ($000)", "usd", "<note>")],
    "ratios": [],
}

RATING_SCALE = [
    (1, "Pass", "Substantially risk-free; strongest financial condition."),
    (2, "Pass", "Strong financial condition; ample debt-service capacity."),
    (3, "Pass", "Satisfactory; adequate capacity with identifiable secondary support."),
    (4, "Pass", "Acceptable with attention; tighter margins or higher leverage."),
    (5, "Special Mention", "Potential weaknesses deserving close attention; if uncorrected may weaken prospects."),
    (6, "Substandard", "Well-defined weakness; distinct possibility of loss if not corrected."),
    (7, "Doubtful", "Collection in full highly questionable and improbable."),
    (8, "Loss", "Considered uncollectible; charge-off warranted."),
]


def question_rows(segment_code: str):
    """Yield (qid, section, question, severity) for a segment: core + extras."""
    seg = SEGMENTS[segment_code]
    n = 0
    for section, question, severity in CORE_QUESTIONS:
        n += 1
        yield (f"{segment_code}-Q{n:02d}", section, question, severity)
    for section, questions in seg["sections_extra"]:
        for question, severity in questions:
            n += 1
            yield (f"{segment_code}-Q{n:02d}", section, question, severity)
