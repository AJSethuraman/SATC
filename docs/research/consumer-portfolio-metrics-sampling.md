<!--
Provenance: owner-supplied deep research, pasted into the build session on
2026-07-05. Kept verbatim below the divider. Tier-1 items from this document
shipped in credit-review-os (dual-basis delinquency rates, balance attribute,
bankruptcy/fraud charge-off timeliness attestations, dollar coverage on the
Products roll-up, upgraded sampling citations). Tier-2 (population-tape
stratification layer) and Tier-3 (portfolio metrics engine) are logged as
GATED items in BACKLOG.md section 5, pending owner grills.
-->

# Consumer Loan Portfolio Credit Review, Stratification, and Judgmental Sampling: A Technical Reference for a Bank-Examination-Grade Tool

## TL;DR

- **Balance (dollar) weighting is the standard convention for virtually every portfolio “level” metric** (WA rate/coupon, WA FICO, WA LTV, WA DTI, WA age, WA term), while **delinquency and loss can be reported on either a dollar basis or a count basis** — the Federal Reserve computes Call Report charge-off/delinquency ratios on a dollar basis, but credit-bureau and account-level reporting frequently use count-based rates; a well-built tool should compute and display both.
- **Judgmental (non-statistical) sampling is the accepted method for consumer credit / line-sheet review**; its central limitation is that results cannot be extrapolated to the population, so the tool’s job is to *stratify* the population by risk drivers (vintage, score band, DPD status, channel, product, geography, balance band) so a reviewer can deliberately over-weight high-risk segments and document coverage — exactly what the OCC “Sampling Methodologies” booklet and Fed SR 14-4 describe.
- The controlling US guidance set is concrete and traceable: **FFIEC’s URCCAMP** (charge-off at 120 days closed-end / 180 days open-end; Substandard at 90 days), the **2020 Interagency Guidance on Credit Risk Review Systems** (SR 20-13 / OCC Bulletin 2020-50), the **OCC Comptroller’s Handbook** retail booklets, the **Call Report** (Schedules RI-B, RC-K, RC-N, RC-C) definitions, and the **FR Y-14M/Q** stress-test collections — the last of which (importantly) segments consumer portfolios on a coarse ≤620/>620 score split and six DPD buckets, *not* the fine bands often assumed.

-----

## Key Findings

1. **Weighting convention.** For “level”/attribute metrics (rate, score, LTV, DTI, age, term), the industry, rating-agency, and regulatory-reporting standard is to weight by current outstanding principal balance. Count-weighting (equal per loan/account) is a secondary/diagnostic view and is the norm only in specific contexts — notably bureau-reported delinquency and some account-management reporting. Both should be produced.
1. **Delinquency and loss: dollar vs count.** The Federal Reserve computes Call-Report-based charge-off and delinquency rates on a dollar basis. Per the Federal Reserve Board’s published methodology, “Charge-off rates for any category of loan are defined as the flow of a bank’s net charge-offs (gross charge-offs minus recoveries) during a quarter divided by the average level of its loans outstanding over that quarter,” and “As published, these ratios are multiplied by 400 to express them as annual percentage rates.” Likewise, “The delinquency rate is the ratio of the dollar amount of a bank’s delinquent loans to the dollar amount of total loans,” where delinquent means “those past due thirty days or more and still accruing interest as well as those in nonaccrual status.” Count-based rates (number of delinquent accounts ÷ number of accounts) are also standard, especially in credit-card MIS and bureau data.
1. **Charge-off timing is prescribed by URCCAMP.** Per the Federal Register final policy (June 12, 2000, 65 FR 36903): “Open- and closed-end retail loans past due 90 cumulative days from the contractual due date should be classified Substandard. Closed-end retail loans that become past due 120 cumulative days and open-end retail loans that become past due 180 cumulative days from the contractual due date should be classified Loss and charged off.” Bankruptcy (65 FR 36905): “Loans in bankruptcy should be classified Loss and charged off within 60 days of receipt of notification of filing from the bankruptcy court or within the time frames specified in this classification policy, whichever is shorter.” These thresholds are deterministic and should be hard-coded.
1. **Consumer nonaccrual is elective.** Under Call Report Schedule RC-N instructions, a consumer loan or 1–4 family residential loan 90+ days past due “need not” be placed on nonaccrual (subject to alternative evaluation to ensure net income is not materially overstated), so consumer portfolios frequently carry “90+ days past due and still accruing” as the operative nonperforming bucket rather than nonaccrual.
1. **Stratification dimensions are well-established** and differ by product: vintage/origination period, internal risk grade, FICO band (origination and refreshed), DTI band, LTV/CLTV band (secured), channel, product, behavioral/custom score, geography, balance band, term, and delinquency status. Cards emphasize score/utilization/behavioral score/delinquency; installment emphasizes LTV/collateral/channel/term; student emphasizes repayment status (in-school/grace/deferment/forbearance/repayment/default), school type, and cosigner.
1. **Score-band cutoffs are not uniform.** There is no single regulatory FICO band standard. The CFPB’s six-tier scheme, from “The Consumer Credit Card Market” (Oct. 2023, p.12), is the most authoritative published banding: “superprime (800 or greater), prime plus (720 to 799), prime (660 to 719), near-prime (620 to 659), subprime (580 to 619), and deep subprime (579 or less).” VantageScore, FICO-marketing tiers, and the Fed’s stress-test schedules all differ. The tool should make band edges configurable.
1. **Vintage and roll-rate analytics are the two core portfolio-monitoring lenses** and both have deterministic formulas (below).

-----

## Details

### AREA 1 — Population-level metrics for consumer credit quality

All formulas below specify numerator and denominator explicitly. “Balance” means current outstanding principal (unpaid principal balance, UPB), unless a metric is defined on original balance (vintage) or on a specified average.

#### 1.1 Weighted-average attribute metrics (all balance-weighted by default)

For a set of loans i with current balance Bᵢ and attribute xᵢ:

**WA(x) = Σᵢ (Bᵢ · xᵢ) / Σᵢ Bᵢ**

- **WA interest rate / coupon (WAC):** xᵢ = note/APR. Weight = current UPB. (Structured-finance/ABS standard; in the weighted-average calculation the principal balance of each loan is the weighting factor — multiply each loan’s rate by its remaining balance, sum, and divide by total remaining balance.)
- **WA FICO:** xᵢ = borrower score (origination or refreshed — compute both separately). Weight = current UPB.
- **WA LTV / CLTV:** xᵢ = loan-to-value (or combined LTV). Weight = current UPB. Applies to secured consumer (auto, HELOC, home-improvement); not meaningful for unsecured cards/personal loans.
- **WA DTI:** xᵢ = back-end DTI at origination (front-end also possible). Weight = current UPB.
- **WA age / months-on-book (MOB):** xᵢ = months since origination. Weight = current UPB.
- **WA remaining term / maturity (WAM):** xᵢ = remaining months to maturity. Weight = current UPB. (For amortizing ABS, weighted-average life (WAL) weights each principal payment date by the principal returned on that date.)

**Count-weighted (equal) alternative:** WA(x) = Σᵢ xᵢ / N. Report this as a secondary column; it answers “typical account” rather than “typical dollar.”

#### 1.2 Delinquency rate definitions

Delinquency is measured in days past due (DPD) from the contractual due date, bucketed conventionally as **30–59, 60–89, 90–119, 120–149, 150–179, 180+**, or as cumulative **30+ / 60+ / 90+**. (Note: some regulatory collections top out at 120+; see Area 3.)

- **Dollar-based delinquency ratio (bucket k):**
  DQ$_k = (Σ balance of loans in bucket k) / (Σ balance of all loans in the population/segment)
- **Count-based delinquency ratio (bucket k):**
  DQcount_k = (number of loans in bucket k) / (number of loans in population/segment)
- **Cumulative “90+” dollar rate:** (Σ balance of loans 90+ DPD) / (Σ total balance).

Conventions:

- The Federal Reserve’s published bank delinquency rates use the **dollar basis** (delinquent $ ÷ total $), sourced from Call Report Schedule RC-N (delinquent) and RC-C (total).  The Fed’s definition of “delinquent” includes loans 30+ days past due and still accruing plus those in nonaccrual.
- Partial-payment handling per URCCAMP: a payment ≥90% of the contractual payment may be treated as a full payment; alternatively, aggregate shortfalls to determine months past due (e.g., six months of $150 shortfalls on a $300 payment = three full months past due). Deterministic — implement one method per loan, not both simultaneously on a single loan.
- Nonaccrual and charge-offs: loans already charged off leave the delinquency base (they are removed from receivables); nonaccrual loans that remain on the books are included in the appropriate 90+ bucket. Whether 90+ consumer loans are “nonaccrual” vs “90+ still accruing” is an institutional election (see 1.6).

#### 1.3 Default rate definitions

“Default” for consumer credit is defined by the institution but commonly = reaching a severe-delinquency/charge-off state. Two standard forms:

- **Ever-default (cohort/vintage) rate:** (number or balance of accounts in a cohort that ever reached the “bad” definition — e.g., 90+ DPD or charge-off — by a given MOB) ÷ (original number or balance in the cohort).
- **Basel-style default:** 90 days past due OR unlikely-to-pay; the “bad” definition (60 vs 90 vs 120 DPD) is itself often chosen empirically via roll-rate analysis.  Note the OCC installment/credit-card handbook language that a scorecard “bad” account “typically involves some level of delinquency, usually 60 or 90” DPD.

#### 1.4 Net charge-off (NCO) rate — deterministic definition

- **Gross charge-off (GCO):** principal deemed uncollectible and removed from the books during the period (Call Report Schedule RI-B, item RIAD4635 for the ALLL charge-off line).
- **Recoveries:** amounts collected on previously charged-off loans (RI-B, RIAD4605).
- **Net charge-off:** NCO = GCO − Recoveries.
- **NCO rate (annualized, dollar basis):**
  NCO rate = (NCO during period) / (average loans held for investment during period) × (annualization factor)
  - For a quarter, annualization factor = 4 (the Fed multiplies the quarterly ratio by 400 to state an annual %); for a month, ×12.
  - Denominator = average balance over the period (e.g., three-month average for a quarterly card metric; period-end balance is an accepted simplification in some allowance contexts — the NCUA Simplified CECL Tool, for instance, uses net charge-offs ÷ period-end balance for a weighted-average 3-year NCO rate).
- **Gross charge-off rate:** GCO / average loans, annualized (same structure, no netting of recoveries).
- Recoveries net against gross charge-offs in the numerator; a large recovery quarter can even produce negative NCO. Billed finance charges/fees are frequently included in the card receivable base for both numerator and denominator.

#### 1.5 Delinquency bucketing conventions

Standard buckets: Current; 1–29 DPD; 30–59; 60–89; 90–119; 120–149; 150–179; 180+ (closed-end charge-off point 120, open-end 180 per URCCAMP). Cumulative reporting (30+, 60+, 90+) is standard for external disclosure. Re-aging (open-end) and extensions/deferrals/renewals/rewrites (closed-end) reset delinquency status and must be tracked per URCCAMP. Open-end re-aging conditions: account existed ≥9 months; borrower made ≥3 consecutive minimum monthly payments (or equivalent cumulative amount); no more than once per 12 months and no more than twice per 5 years (workout re-aging adds one more, limited to once per 5 years).

#### 1.6 Nonperforming loan (NPL) definitions for consumer

- **Nonaccrual (Call Report RC-N):** an asset is nonaccrual if maintained on a cash basis due to borrower deterioration, if full payment of principal/interest is not expected, or if principal/interest is in default 90+ days — *unless* well secured and in the process of collection. But **consumer and 1–4 family loans “need not” be placed on nonaccrual** even at 90+; the bank must instead use alternative methods to ensure net income is not materially overstated. Many card issuers therefore keep interest accruing and report a “90+ days past due and still accruing” line as the NPL proxy.
- **Nonperforming** for consumer is thus commonly operationalized as **90+ DPD (accruing) + nonaccrual + charged-off-in-period**, or as the institution’s defined nonperforming line. Provide a configurable NPL definition.

#### 1.7 Vintage (cohort) analysis

- **Group** accounts by origination period (month/quarter/year) = a “vintage.”
- **Cumulative loss curve:** for vintage v at months-on-book m:
  CumLoss(v, m) = (cumulative net charge-offs of vintage v through MOB m) / (original balance of vintage v)
- Analogous cumulative delinquency/default curves use cumulative 90+ or “ever-bad” counts/balances ÷ original cohort count/balance.
- **Loss triangle / heatmap:** rows = vintage, columns = MOB; reveals seasoning (losses ramp then plateau as the vintage “matures,” typically after ~24 months on unsecured products) and underwriting drift across cohorts.
- Use trailing 3/6/12-month averages to smooth.  Vintage curves feed age-dependent PD term structures, LGD/charge-off timing, and stress overlays.

#### 1.8 Roll-rate / transition-matrix analysis

- **Roll rate (bucket j → bucket k, month t→t+1):**
  Roll(j→k) = (balance or count in bucket k at t+1 that was in bucket j at t) / (balance or count in bucket j at t) 
- Computed on either a **dollar** or **count** basis (state both).  Standard chains: Current → 30 → 60 → 90 → 120 → … → charge-off.
- **Transition matrix:** square matrix P where P[j,k] = roll rate from state j to state k over one period; rows sum to ~1 (including cure/back-roll and stay probabilities). Multiplying a delinquency-distribution vector by P projects next period’s distribution (Markov approximation); the roll-to-charge-off path underpins loss forecasting . Per OCC guidance, “Most institutions use historical net charge-off rates, based on migration analysis of the roll rates to charge-off, as the starting point for determining appropriate loss allowances.”

-----

### AREA 2 — Stratification dimensions and segment cuts

Stratification supports **judgmental sampling** by partitioning a large, homogeneous-looking retail population into risk-differentiated cells so the reviewer can (a) concentrate the sample in high-risk cells, (b) achieve documented “coverage”/penetration of material segments, and (c) make ad-hoc asset-quality comparisons across subgroups. This directly matches the 2020 Interagency Guidance’s instruction that scope be “risk-based” and cover “segments of loan portfolios, including retail, with similar risk characteristics.”

**Standard stratification dimensions (all products):**

- **Vintage / origination period** — detect underwriting drift; align with vintage curves.
- **Internal risk grade / rating** — where the bank maintains one; retail often uses score-based tiers rather than commercial-style grades. The 2020 guidance expects internal frameworks to reconcile to the agency classification categories.
- **FICO band (origination and refreshed)** — the primary risk axis for unsecured consumer. Standard bandings (make configurable):
  - **CFPB six-tier:** deep subprime ≤579; subprime 580–619; near-prime 620–659; prime 660–719; prime-plus 720–799; superprime 800+.
  - Common lender/marketing splits (e.g., subprime <620/<660; prime; superprime 720+/740+/800+) vary by institution.
- **DTI band** — conventional edges around 36% and 43% (≤36 / 37–43 / 44–49 / 50+), reflecting the 28/36 rule and the QM/ability-to-repay 43% reference;  auto/personal lenders may use ~20% payment-to-income cuts.
- **LTV / CLTV band (secured only)** — e.g., ≤60 / 61–80 / 81–90 / 91–100 / 100+; URCCAMP uses a 60% CLTV threshold for classifying delinquent residential/HELOC exposures. 
- **Origination channel** — direct / indirect (dealer/broker) / branch / digital; risk generally rises as the channel becomes more removed from a direct bank relationship (per the OCC installment booklet, the least risky acquisition is a full application to a bank loan officer).
- **Product type** — card (general-purpose vs private-label), personal/installment, auto, student, HELOC, etc.
- **Custom / behavioral score** — internal or bureau behavior score; refreshed periodically.
- **Geography** — state/MSA/region; for concentration and localized stress.
- **Loan size / balance band** — supports selecting largest exposures.
- **Term** — e.g., ≤36 / 37–60 / 61–72 / 72+ months for installment/auto.
- **Delinquency status** — current / 1–29 / 30–59 / 60–89 / 90+ / nonaccrual / charged-off.
- **Refreshed vs origination FICO** — migration between the two is itself a risk signal.

**Product-specific conventions:**

- **Credit cards:** score band (orig + refreshed), utilization (cycle-ending balance ÷ current credit limit), behavioral score, delinquency status, product sub-type (general-purpose vs private label), vintage, credit-limit band. Utilization and refreshed score are especially diagnostic; over-limit segments warrant separate treatment.
- **Installment / personal / auto:** LTV/collateral value (secured), channel (direct vs indirect/dealer),  term, loan size, score band, vintage, geography.
- **Student:** repayment status (in-school / grace / deferment / forbearance / repayment / default)  is the dominant cut; also school type/program, cosigner presence, fixed vs variable rate, and program type (private vs federal/guaranteed). Delinquency is only meaningful for loans in active repayment, so segment on status first.

**How stratification enables judgmental sampling (per OCC “Sampling Methodologies,” Version 1.0, issued via OCC Bulletin 2020-56, effective June 15, 2020):** to draw statistically valid conclusions “examiners must define or stratify (group) the selected population as much as possible by their characteristics”; and for judgmental samples, “examiners cannot statistically relate the results of this sample to the entire population of items.” Consumer assets are explicitly a “common, uniform underwriting standards”  category — the booklet lists “one-to-four-family residential real estate loans, consumer instalment loans, credit card loans, home improvement loans, home equity loans, and overdraft lines of credit” — suited to portfolio/segment treatment rather than loan-by-loan review. Judgmental selection typically takes “all of the loans in the categories with the highest risk”  plus a sample from lower-risk cells.

-----

### AREA 3 — Regulatory and industry guidance sources

**(a) FFIEC Uniform Retail Credit Classification and Account Management Policy (URCCAMP).** FFIEC, final revised policy published in the Federal Register **June 12, 2000 (65 FR 36903)**, revising the February 10, 1999 policy (64 FR 6655) and the original 1980 policy; adopted via OCC Bulletin 2000-20, Fed SR 00-8, FDIC FIL-40-2000. Key deterministic rules:

- Open- and closed-end retail loans **90 cumulative days** past due → classify **Substandard**.
- Closed-end **120 days** / open-end **180 days** → classify **Loss** and charge off (charge-off no later than end of month in which the period elapses).
- Residential/HELOC 90+ days with LTV >60% → Substandard; ≤60% generally not classified on delinquency alone.
- Bankruptcy → Loss/charge-off within **60 days** of notice; fraud → within 90 days of discovery; deceased-borrower loans → when loss is determined (whichever is shorter of these vs the standard timeframes).
- Partial payments: 90%-rule or aggregation method.
- Re-aging (open-end) and extension/deferral/renewal/rewrite (closed-end) standards, with the caution that permissive re-aging “can cloud the true performance and delinquency status of the portfolio.”
- Explicitly authorizes examiners to **classify retail portfolios or segments** “where underwriting standards are weak and present unreasonable credit risk” — the supervisory basis for segment-level asset-quality assessment.

**(b) 2020 Interagency Guidance on Credit Risk Review Systems.** Issued by OCC/Board/FDIC/NCUA; **Federal Register June 1, 2020**;  Board SR 20-13 (May 8, 2020);  OCC Bulletin 2020-50; FDIC FIL-55-2020. Replaces Attachment 1 (“Loan Review Systems”) of the 2006 ALLL policy statement. On **scope and sampling**: an effective scope is “risk-based” and covers “loans over a predetermined size”; “a sufficient sample of smaller loans, new loans, and new loan products”; “loans with higher risk indicators, such as low credit scores, high credit lines, or those credits approved as exceptions to policy”; and **“segments of loan portfolios, including retail, with similar risk characteristics such as those related to borrower risk (e.g., credit history), transaction risk (e.g., product and/or collateral type), or other risk factors.”** It states establishment of an appropriate review scope “helps ensure that the sample of loans selected for review, or portfolio segments selected for review, is representative of the portfolio as a whole,” and directs institutions to “consider industry standards for credit risk review coverage.”  Review depth for retail explicitly includes “the appropriateness of automated underwriting and credit scoring, including prudent use of overrides, as well as the effectiveness of account management strategies, collections, and portfolio management activities.” Reviews typically annual, on renewal, or more frequent; results reported to the board/committee quarterly.

**(c) OCC Comptroller’s Handbook booklets** (issued for OCC examiners; applied to national banks and FSAs):

- **“Retail Lending”** — core retail risk-management framework covering closed- and open-end consumer credit; defines retail lending and references product booklets.
- **“Credit Card Lending”** — portfolio MIS by product/segment/affinity group; roll-rate/migration analysis for loss allowance; override tracking by score band/channel/reason; scoring model governance (generic vs custom scorecards).
- **“Installment Lending”** — direct vs indirect channel risk; collateral/term/pricing; scorecard “bad” definitions (typically 60 or 90 DPD).
- **“Student Lending”** — product-specific.
- **“Rating Credit Risk”** and **“Loan Portfolio Management”** — risk-rating and portfolio-management frameworks; management should systematically verify account-officer risk ratings, with independent loan review in larger banks.
- **“Sampling Methodologies”** (Examination Process, Version 1.0, issued via OCC Bulletin 2020-56, effective June 15, 2020) — the definitive OCC statement distinguishing **judgmental (non-statistical)** from **statistical (numerical/proportional)** sampling. Judgmental results “cannot be extrapolated statistically to the population”; statistical sampling requires random selection and a population of roughly 100+ items and three inputs (confidence level, tolerance rate, expected exception rate set to 0%). The booklet gives worked judgmental examples (e.g., selecting all doubtful/classified-accruing loans plus samples of substandard-accruing and 90+-still-accruing loans when testing nonaccrual accuracy), and requires examiners to document population, areas of focus, sample size, selection rationale, and results.

**(d) FDIC — “Risk Management Examination Manual for Credit Card Activities,” Chapter X (Transaction Testing).** States transaction testing is account/loan-level testing (a.k.a. account testing/sampling); **“Results from judgmental sampling cannot be projected beyond the accounts sampled,”** but exceptions “may suggest a larger problem” and should inform the quality assessment of the population.

**(e) Federal Reserve — SR 14-4 (Examiner Loan Sampling Requirements).** Establishes annual loan-sampling objectives. Commercial segments: minimum **10% of committed dollar exposure** per segment; cover the four highest concentrations by risk-based capital; sample categories contributing **25%+ of annual revenue**.  For **retail: “there is no minimum coverage expectation for retail portfolios or segments,”**  classification uses URCCAMP (SR 00-8), and “the goal of sampling is to arrive at an informed assessment of all aspects of retail credit risk management.” Institutions’ internal loan review “should achieve substantial coverage beyond the examiners’ annual judgmental sample.” Confirms the qualitatively different (portfolio/segment) treatment of retail vs commercial.

**(f) Call Report (FFIEC 031/041/051) definitions** — the authoritative source for the ratio mechanics: Schedule **RI-B** (charge-offs RIAD4635 and recoveries RIAD4605), **RC-K** (average loan balances), **RC-N** (past due 30–89 and 90+, and nonaccrual), **RC-C** (period-end loans, RCFD2122 total). The consumer-loan nonaccrual election lives in the RC-N instructions.

**(g) FR Y-14M / FR Y-14Q (Capital Assessments and Stress Testing).** FR Y-14M collects **monthly loan/account-level** data (Schedule D Domestic Credit Card, plus first-lien and HEL schedules) for holding companies with ≥$100B total consolidated assets (reporting cards if portfolio balances exceed $5B or are material). At the account level, score and DPD are captured as **raw values** (original FICO and refreshed FICO as whole numbers; DPD as an actual day count), *not* pre-banded, and the **Schedule D portfolio-level table segments only by Credit Card Type (4 values: general-purpose, private-label, business, corporate) × Lending Type (4 values) = 16 rows per month** — it contains no score/DPD/utilization/months-on-book bands. The **FR Y-14Q** retail schedules are the banded companion: they segment portfolios via an 8-digit segment ID using **six delinquency buckets (01 Current; 02 1–29; 03 30–59; 04 60–89; 05 90–119; 06 120+ DPD)** and a coarse **original-score split (≤620 / >620 / N/A-missing)**, plus product type and four geography segments (e.g., US Auto uses 3×3×6×4 = 216 segments). This is an important corrective: the fine score/DPD bands often assumed (e.g., 760+, or 150–179/180+) are analyst constructs, not the regulatory collection’s own segmentation. Note the top Y-14Q delinquency bucket is 120+, not 180+. The Philadelphia Fed’s public FR Y-14M product further uses percentile-based cuts (10th/25th/50th score percentiles; 50th/75th/90th utilization and credit-limit percentiles) and a three-group score split (<660 / 660–719 / ≥720), with card DPD reported as cumulative 30+/60+/90+.

**(h) Industry / structured-finance / rating-agency conventions.** SEC Regulation AB / Reg AB II asset-level disclosure (17 CFR; ABS Disclosure and Registration, effective Nov 24, 2014); rating-agency (S&P, Moody’s, Fitch) credit-card and consumer-ABS methodologies; and standard ABS pool statistics (WAC, WAM, WAL, WA FICO) — all of which weight pool statistics by outstanding principal balance. ABS credit-card reporting also defines portfolio yield, excess spread, and treats recoveries as part of finance-charge collections. The NCUA Simplified CECL Tool uses a weighted-average 3-year NCO rate (net charge-offs ÷ period-end balance, weighted by category balance across three years).

-----

### AREA 4 — Weighted-average weighting conventions (metric by metric)

**General rule:** balance-weight (by current outstanding principal) unless there is a specific reason not to. Rationale: portfolio economics and loss exposure scale with dollars, not account count; a $50,000 loan contributes far more risk than a $500 loan, so equal-weighting understates the risk of large balances. This is the ABS/structured-finance standard (WAC weights each loan’s rate by principal balance), the rating-agency standard, and the regulatory-reporting standard (Fed charge-off/delinquency ratios are dollar-based).

|Metric                             |Standard weighting                                                                     |Numerator / denominator                                                              |Notes & alternatives                                                                                                                                                                                        |
|-----------------------------------|---------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**WA interest rate / coupon (WAC)**|Balance (current UPB)                                                                  |Σ(Bᵢ·rateᵢ) / ΣBᵢ                                                                    |ABS/MBS standard; use current, not original, balances (using original balances overstates the weight of loans that have paid down).                                                                         |
|**WA FICO**                        |Balance                                                                                |Σ(Bᵢ·FICOᵢ) / ΣBᵢ                                                                    |Compute origination and refreshed separately. Count-weighted (“per account”) is a common secondary view; note transactor cards carry low balances, so balance-weighting shifts the average toward revolvers.|
|**WA LTV / CLTV**                  |Balance                                                                                |Σ(Bᵢ·LTVᵢ) / ΣBᵢ                                                                     |Secured consumer only. Use current balance over current value for refreshed LTV.                                                                                                                            |
|**WA DTI**                         |Balance                                                                                |Σ(Bᵢ·DTIᵢ) / ΣBᵢ                                                                     |Back-end DTI standard; front-end optional.                                                                                                                                                                  |
|**WA delinquency / loss rate**     |**Dollar basis is standard for regulatory reporting; count basis common in bureau/MIS**|Dollar: Σ(delinquent or charged-off $)/Σ(total $). Count: (# delinquent)/(# accounts)|This is the key exception — always compute BOTH. Fed/Call Report = dollar; credit-bureau delinquency and some account-management reporting = count.                                                         |
|**WA term / maturity (WAM)**       |Balance                                                                                |Σ(Bᵢ·remaining_termᵢ)/ΣBᵢ                                                            |For amortizing pools, WAL weights each principal cash flow by principal returned.                                                                                                                           |
|**WA age / months-on-book**        |Balance                                                                                |Σ(Bᵢ·ageᵢ)/ΣBᵢ                                                                       |Count-weighting gives “typical account age.”                                                                                                                                                                |

**Why count-weighting appears for delinquency:** consumer-protection and bureau reporting often count borrowers/accounts (e.g., “% of accounts 30+ DPD”), because the policy question is “how many households are behind,” not “how many dollars.” Dollar-weighting answers the loss-exposure question. Because the two can diverge sharply (many small delinquent balances vs few large ones), a credit-review tool must expose both and clearly label which is shown.

-----

## Recommendations

**Stage 1 — Deterministic metric engine (build first).**

- Implement all Area-1 formulas with an explicit, configurable weighting basis (default: current UPB) and a parallel count-based output for every rate. Hard-code URCCAMP charge-off/classification thresholds (90/120/180 days; 60-day bankruptcy) and the 90%-partial-payment rule.
- Compute NCO rate as (GCO − recoveries) ÷ average balance × annualization factor, with selectable period (monthly ×12, quarterly ×4) and selectable denominator (average vs period-end). Show gross and net side by side.
- Represent delinquency in canonical buckets (Current, 1–29, 30–59, 60–89, 90–119, 120–149, 150–179, 180+) with roll-up to cumulative 30+/60+/90+.
- Make nonperforming/nonaccrual an explicit configurable definition (consumer nonaccrual is elective per RC-N).

**Stage 2 — Stratification & sampling layer.**

- Support all Area-2 dimensions with configurable band edges (ship CFPB six-tier FICO bands and 36/43 DTI edges as defaults, but never hard-code them). Allow origination-vs-refreshed score and LTV as distinct axes.
- Build vintage triangles (cumulative loss/delinquency by MOB) and both dollar- and count-based roll-rate/transition matrices.
- For judgmental sampling, let the user (a) select “all items” in high-risk cells and a fixed n or % in others, (b) record coverage/penetration per segment (both $ and count), and (c) auto-generate the documentation the OCC booklet requires: population, areas of focus, sample size, selection rationale, results. Explicitly label samples as non-extrapolable.

**Stage 3 — Comparison & governance.**

- Add ad-hoc subgroup A/B comparison (e.g., indirect vs direct channel, refreshed-score-migrated vs stable) reporting both weightings and flagging where they diverge materially.
- Map internal grades to regulatory classifications (Substandard/Doubtful/Loss) per the 2020 guidance’s expectation that internal frameworks reconcile to agency categories.

**Benchmarks that would change the approach:**

- If a population/segment is homogeneous and the objective is to *estimate an exception rate* (not just find issues), switch from judgmental to **statistical** sampling (OCC booklet: needs random selection, population ~100+,  chosen confidence/tolerance). Build this as an optional mode.
- If the institution is a CCAR/FR Y-14 filer, align segment definitions to FR Y-14Q’s six DPD buckets and ≤620/>620 score split for a clean cross-walk to regulatory submissions.
- If commercial exposures are ever added, apply SR 14-4’s 10%-of-committed-dollars  and 25%-of-revenue coverage rules (these do *not* apply to retail, which has no minimum coverage expectation).

-----

## Caveats

- **No single FICO band standard exists.** The CFPB six-tier scheme is the most authoritative published banding, but VantageScore, FICO-marketing tiers, lender-internal tiers, and the Fed stress-test schedules all differ. Treat band edges as configuration, not constants.
- **Regulatory collections use coarser segmentation than practitioners assume.** FR Y-14M Schedule D’s portfolio table is only a 4×4 type/lending-type grid (score and DPD are raw account-level fields); FR Y-14Q retail uses a ≤620/>620 score split and tops delinquency at 120+ (no 150–179/180+ split). Fine banding is an analyst construct.
- **Dollar vs count materially changes delinquency/loss figures.** Never present a single delinquency number without specifying the basis; the tool should default to showing both.
- **Consumer nonaccrual is optional under Call Report rules**, so “nonperforming” is institution-defined for consumer books; comparisons across institutions require normalizing the definition.
- **URCCAMP thresholds are minimums**; institutions may adopt more conservative charge-off/classification timing, and re-aging/extensions can mask true delinquency — the tool should track re-aged/modified accounts separately.
- Some secondary sources used to corroborate formula mechanics (data-science blogs, vendor pages, ABS explainers) reflect widely used market conventions but are not authoritative; the authoritative anchors are URCCAMP (65 FR 36903), the 2020 Interagency Guidance (SR 20-13 / OCC Bulletin 2020-50), the Call Report instructions, the OCC handbook booklets (including “Sampling Methodologies,” OCC Bulletin 2020-56), and the FR Y-14M/Q instructions.
- The NCO annualization factor and denominator (average vs period-end) vary by issuer disclosure; the Fed’s Call-Report method (quarterly ×4/×400, average balance) is the reference standard, but issuer 10-Qs and ABS reports may differ — make it configurable and disclose the choice.
