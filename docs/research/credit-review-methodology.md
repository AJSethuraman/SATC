# Credit / Loan Review Methodology — Cited Findings

**Purpose.** Ground a config-driven loan-review workpaper tool in authoritative
primary sources (federal banking regulators). Every substantive claim below is
followed by a primary-source citation (URL + section/booklet). A PRD author and a
YAML-schema author should be able to build directly from this.

**Retrieval note (read this).** The regulator PDFs (occ.gov, fdic.gov,
federalregister.gov, federalreserve.gov) are blocked to this environment's direct
fetch/`curl` path (egress policy + bot filtering returned HTTP 403 on every direct
GET). All primary-source text below was retrieved via the web-search tool reading
those same primary pages, then transcribed. The URLs cited are the canonical
primary documents the text comes from. Verbatim quotes are marked with quotation
marks; **exact page/paragraph pin-cites should be confirmed against the live PDFs
before quoting them in a filed workpaper** (see "Confidence / open questions").

---

## 1. Universal risk-classification spine (Pass → Loss)

The five-bucket classification spine is a **single interagency standard** shared by
the OCC, FDIC, and Federal Reserve. It originates in the interagency *Uniform
Agreement on the Classification of Assets and Appraisal of Securities* and is
carried verbatim into each agency's examination guidance. Use these as the
canonical definitions.

### The five regulatory categories (verbatim)

- **Pass.** A credit that is in good standing and is not criticized in any way;
  Pass exposures are neither "special mention" nor "classified." ([OCC,
  *Rating Credit Risk*, Comptroller's Handbook — classification section](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

- **Special Mention.** "A special mention asset has potential weaknesses that
  deserve management's close attention. If left uncorrected, these potential
  weaknesses may result in deterioration of the repayment prospects for the asset
  or in the institution's credit position at some future date. Special mention
  assets are not adversely classified and do not expose an institution to
  sufficient risk to warrant adverse classification." ([FDIC RMS Manual of
  Examination Policies, §3.2 Loans](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf);
  [FDIC, *Adverse Classifications*](https://www.fdic.gov/credit-card-activities-manual/chapter-xi-adverse-classifications))

- **Substandard.** "A substandard asset is inadequately protected by the current
  sound worth and paying capacity of the obligor or of the collateral pledged, if
  any. Assets so classified must have a well-defined weakness, or weaknesses, that
  jeopardize the liquidation of the debt. They are characterized by the distinct
  possibility that the institution will sustain some loss if the deficiencies are
  not corrected." ([FDIC RMS Manual §3.2](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf);
  [OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

- **Doubtful.** "An asset classified doubtful has all the weaknesses inherent in
  one classified substandard with the added characteristic that the weaknesses make
  collection or liquidation in full, on the basis of currently existing facts,
  conditions, and values, highly questionable and improbable." ([FDIC RMS Manual
  §3.2](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf);
  [OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

- **Loss.** "Assets classified loss are considered uncollectible and of such little
  value that their continuance as bankable assets is not warranted. This
  classification does not mean that the asset has absolutely no recovery or salvage
  value, but rather that it is not practical or desirable to defer writing off this
  basically worthless asset even though partial recovery may be effected in the
  future." ([FDIC RMS Manual §3.2](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf))

### "Criticized" vs. "classified" boundary

- **Classified (a.k.a. adversely classified) = Substandard + Doubtful + Loss.**
  "Classified assets are exposures rated substandard, doubtful, or loss. Classified
  assets do not include pass and special mention exposures." ([OCC, *Rating Credit
  Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))
- **Criticized = Special Mention + Classified.** "Criticized assets include
  adversely classified assets plus items listed for special mention." Special
  Mention "should not be combined with adversely classified assets," but its total
  is considered in asset-quality analysis. ([FDIC RMS Manual §3.1 Asset Quality](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-1.pdf))

So the boundary is: **Special Mention is criticized but NOT classified.** Loss is
classified and generally charged off. Build the schema so a rating can carry two
derived flags: `is_criticized` (SM + SS + D + L) and `is_classified` (SS + D + L).

### How internal bank rating scales map onto the five buckets

Regulators expect banks to run a granular internal scale (commonly 1–9 or 1–10)
and to **map/reconcile** it to the five regulatory buckets. A representative
mapping (Federal Reserve's *Community Banking Connections*):

- Grades **1–2**: highest quality (cash/marketable-securities secured, government
  claims, investment-grade). Pass.
- Grades **3–5**: "pass" credits, split low/medium/high risk.
- Grades **6–9** incorporate the four criticized categories — **special mention,
  substandard, doubtful, loss** (one internal grade per regulatory bucket at the
  criticized end). ([Federal Reserve, *The Importance of Loan Risk Rating Systems*,
  Community Banking Connections](https://www.communitybankingconnections.org/Articles/2025/R2/the-importance-of-loan-risk-rating-systems))

The exact numbering (whether SM is grade 6 or 7, how many pass grades) varies by
bank — treat the crosswalk as **bank-configurable**, with the constraint that every
internal grade maps to exactly one of {Pass, Special Mention, Substandard,
Doubtful, Loss}. This is why the OCC booklet stresses rating systems should "reflect
the complexity of a bank's lending activities and the overall level of risk," and
"address both the ability and willingness of the obligor to repay and the support
provided by structure and collateral." ([OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

### Credit risk review independently validates the ratings

The 2020 Interagency Guidance expects the credit risk review function to
**independently assess and, where needed, adjust** risk ratings — it does not merely
re-file management's grade. An effective system "appropriately validates and, if
necessary, adjusts risk ratings, especially for those loans with potential or
well-defined credit weaknesses that may jeopardize repayment," and gives the board
"an objective, independent, and timely assessment of the overall quality of the
loan portfolio." ([Interagency Guidance on Credit Risk Review Systems, 85 FR 33278
(June 1, 2020)](https://www.federalregister.gov/documents/2020/06/01/2020-10292/interagency-guidance-on-credit-risk-review-systems);
[OCC Bulletin 2020-50](https://www.occ.gov/news-issuances/bulletins/2020/bulletin-2020-50.html);
[FDIC FIL-55-2020](https://www.fdic.gov/news/financial-institution-letters/2020/fil20055.html))

For the tool: the reviewer's **assigned rating** and the **originator's rating** are
distinct fields; a mismatch (a "downgrade" or "rating exception") is a first-class
finding.

---

## 2. Line-of-business / loan-type taxonomy

Anchor the canonical segment list to **Call Report Schedule RC-C, Part I (Loans and
Leases)** — the regulator-defined loan taxonomy every U.S. bank reports against —
supplemented by the portfolio segmentation language in the interagency guidance
(banks segment "into groups of loans with similar risk characteristics"). ([FFIEC
031/041 Call Report Instructions, Schedule RC-C Part I](https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2023/2023-09-rc-c1.pdf);
[Interagency Guidance on Credit Risk Review Systems](https://www.federalregister.gov/documents/2020/06/01/2020-10292/interagency-guidance-on-credit-risk-review-systems))

### Canonical LOB list (build the roadmap from this)

**A. Loans secured by real estate (RC-C item 1)** — subcategories:
  1. **Construction, land development, and other land (ADC)** — split into
     (a) 1–4 family residential construction and (b) other construction/land
     development.
  2. **Farmland** (secured by farmland and improvements).
  3. **1–4 family residential** — revolving open-end (HELOC) and closed-end
     (first liens; junior/other-than-first liens).
  4. **Multifamily (5+ dwelling units)** residential.
  5. **Nonfarm nonresidential (commercial real estate, CRE)** — split into
     **owner-occupied** (primary repayment = cash flow from operations of the
     owner/affiliate occupying the property) and **non-owner-occupied /
     income-producing / investor** (primary repayment = third-party rental income,
     i.e., 50%+, or sale/refinance proceeds).
     ([FFIEC RC-C, item 1 subcategories and owner-occupied definition](https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2023/2023-09-rc-c1.pdf))

**B. Loans to depository institutions and acceptances of other banks (item 2).**

**C. Loans to finance agricultural production and other loans to farmers (item 3)**
  — the **agricultural / ag operating** segment (distinct from farmland RE in A.2).

**D. Commercial and industrial (C&I) loans (item 4)** — to businesses for
  commercial, industrial, and professional purposes (manufacturing, mining, oil &
  gas, services, etc.).

**E. Loans to individuals for household/family/personal expenditures — consumer /
  retail (item 6)** — subcategories: **credit cards**, **other revolving credit
  plans**, **automobile loans**, **other consumer**.

**F. Loans to nondepository financial institutions and other loans (item 9).**

**G. Obligations (other than securities and leases) of states and political
  subdivisions in the U.S. (item 8).**

**H. Loans to foreign governments and official institutions (item 7).**

**I. Lease financing receivables (item 10)** — direct financing and leveraged
  leases.

([FFIEC 031/041 Schedule RC-C Part I category structure](https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2023/2023-09-rc-c1.pdf))

### Practical review-program segmentation

Most review programs collapse RC-C into these **review LOBs** (defensible canonical
list for the LOB roadmap):

1. Commercial & Industrial (C&I)
2. Owner-occupied CRE
3. Income-producing / investor CRE (non-owner-occupied)
4. Construction & Land Development (ADC)
5. Multifamily
6. Agricultural (ag operating **and** farmland)
7. 1–4 family residential mortgage (incl. HELOC)
8. Consumer / retail (cards, auto, other)
9. Leases
10. (Specialty as applicable: municipal/public-sector, financial-institution, and
    foreign — items G/F/H above)

Each LOB gets its own linesheet template because the repayment analysis differs
(global cash flow / DSCR for C&I and CRE; NOI + DSCR + LTV for income-producing CRE;
cost-to-complete + absorption for ADC; borrowing base for asset-based C&I). ([OCC,
*Commercial Real Estate Lending*, Comptroller's Handbook](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/commercial-real-estate-lending/pub-ch-commercial-real-estate.pdf))

---

## 3. C&I linesheet / workpaper content

A commercial-credit / loan-review **linesheet** captures the reviewer's independent
credit analysis. The OCC's *Rating Credit Risk* booklet frames the required
analysis: a rating "should address both the ability and willingness of the obligor
to repay and the support provided by structure and collateral," reflecting the
borrower's repayment capacity, financial condition, collateral, and guarantor
support. ([OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))
Map that into the following linesheet field groups.

### 3.1 Identification & exposure
- Borrower legal name (**PII — vault/last-4 in artifacts**), relationship/obligor
  group, NAICS/industry, facility ID(s).
- Facility type, purpose, origination/maturity dates.
- **Total exposure**: committed vs. outstanding vs. available; direct + contingent.
- Assigned risk rating (reviewer) + originator's rating + **rating rationale**.

### 3.2 Repayment sources
- **Primary repayment source** (typically operating cash flow) and **secondary
  repayment source(s)** (collateral liquidation, guarantor support, refinance).
  The booklet's "ability to repay" turns on identified primary and secondary
  sources. ([OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

### 3.3 Cash flow & debt-service coverage
- Operating cash flow / EBITDA; **debt-service coverage (DSCR / DSC)** against
  total debt service. Underwriting cushions "may include debt service coverage or
  loan-to-value requirements that provide a cushion if a borrower's financial
  condition declines or market conditions deteriorate." ([OCC, *Rating Credit
  Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))
- **Global cash flow / global DSCR**: combine borrower + guarantor(s) + related
  entities. Guarantor financial statements "should be analyzed to ensure that the
  guarantor can perform as required." ([OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

### 3.4 Leverage & liquidity
- **Leverage**: debt/EBITDA, debt/worth (total liabilities/tangible net worth).
  "High debt levels increase the risk of default … [and] make it more difficult
  for the borrower to withstand adverse economic conditions." ([OCC, *Rating Credit
  Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))
- **Liquidity**: current ratio, working capital, availability under lines.

### 3.5 Collateral
- Collateral type; **advance rate / LTV**; for asset-based C&I, **borrowing base**
  (eligible A/R + inventory × advance rates) and borrowing-base certificate
  currency. ([OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf);
  borrowing-base mechanics per [FFIEC RC-C](https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2023/2023-09-rc-c1.pdf))

### 3.6 Guarantor support
- Guarantor identity (**PII**), guarantee type (full/limited/payment/collection),
  guarantor global cash flow and net worth/liquidity, and whether the financial
  statement "acknowledges the guarantee." ([OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

### 3.7 Covenant compliance
- Financial covenants (min DSCR, max leverage, min tangible net worth, min
  liquidity), covenant test results, and any waivers. Covenant compliance is
  evidenced by a borrower-officer **compliance certificate** delivered with periodic
  financials. ([Practical Law, *Compliance Certificate: Lending*](https://uk.practicallaw.thomsonreuters.com/6-611-7345);
  tie back to OCC repayment-capacity analysis in *Rating Credit Risk*.)

### 3.8 Financial-statement currency & quality
- Statement date/period, and **quality tier**: audited > reviewed > compiled > tax
  return > company-prepared. Currency drives staleness exceptions (see §5).
  ([OCC, *Rating Credit Risk* — financial analysis; FDIC RMS §3.2 documentation
  expectations](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf))

### 3.9 Narrative
- Underwriting/credit-analysis narrative: business overview, industry, management,
  strengths/weaknesses, rating rationale, trend/outlook, and the reviewer's
  concurrence or exception with management's grade. ([OCC, *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

---

## 4. Exception taxonomy & severity

The OCC's *Loan Portfolio Management* booklet is the anchor: "Lending exceptions
generally either relate to documentation or underwriting," and "banks should have
systems to analyze and control both types of exceptions." ([OCC, *Loan Portfolio
Management*, Comptroller's Handbook (Apr 1998)](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html);
[PDF copy](https://www.cdfifund.gov/system/files/documents/occ-loan-portfolio-management-comptrollers-handbook.pdf))
Practice extends this to a third bucket — **compliance** exceptions — reflected in
the 2020 guidance's expectation that review report on "compliance with laws and
regulations." ([Interagency Guidance on Credit Risk Review Systems](https://www.federalregister.gov/documents/2020/06/01/2020-10292/interagency-guidance-on-credit-risk-review-systems))

### 4.1 The three exception classes

- **(a) Documentation exceptions** — required document missing, unsigned, expired,
  or defective (missing title, lapsed insurance, stale financials, unfiled UCC,
  missing appraisal). "Loan administration is the control point for loan
  documentation. A bank should systematically identify document exceptions,
  initiate timely resolution, and ensure that documentation remains current."
  ([OCC, *Loan Portfolio Management*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html))

- **(b) Policy / underwriting exceptions** — the credit does not meet the bank's
  written underwriting standards (LTV over limit, DSCR below floor, leverage over
  ceiling, tenor/amortization outside policy, out-of-area, over house lending
  limit). Subdivide into:
  - **Approved (with mitigants)** — granted as a documented, approved exception
    with compensating factors/mitigants.
  - **Unapproved** — outside policy with no documented approval (higher severity).
  These map to the OCC's underwriting-exception category. ([OCC, *Loan Portfolio
  Management*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html))

- **(c) Compliance exceptions** — violations of laws/regulations (e.g., flood
  insurance, appraisal regulation, Reg B/Reg Z, HMDA). Review is expected to report
  "compliance with laws and regulations." ([Interagency Guidance on Credit Risk
  Review Systems](https://www.federalregister.gov/documents/2020/06/01/2020-10292/interagency-guidance-on-credit-risk-review-systems))

### 4.2 Severity tiering

Severity is tied to **materiality**: "the level of attention and reporting should
correspond with the materiality of the exception. A missing title can be handled
satisfactorily at the administrative level, but a breach of the house lending limit
should be brought to the attention of senior management and the board." ([OCC, *Loan
Portfolio Management*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html))
Build a configurable severity scale (e.g., Low/Administrative → Medium → High/Board)
keyed off exception type and materiality, with routing/escalation per tier.

### 4.3 Clearing / curing & tracking to resolution

- **Clearing (curing)** an exception = obtaining the missing document, correcting
  the defect, or documenting an approval so the item is resolved and closed.
- Each exception is tracked open→resolved with owner and due date: "A bank should
  systematically identify document exceptions, initiate timely resolution, and
  ensure that documentation remains current." ([OCC, *Loan Portfolio Management*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html))
- **Aggregate tracking / trends**: "track the aggregate level of exceptions to help
  detect shifts in the risk characteristics of loan portfolios," and "analyze
  document exception patterns to identify problems in the origination process as
  well as … officers, units, or geographic locations that need to strengthen …
  compliance." ([OCC, *Loan Portfolio Management*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html))
  The 2020 guidance similarly expects review to report "the adequacy of and
  adherence to internal policies and procedures" and management's response to
  criticisms. ([Interagency Guidance on Credit Risk Review Systems](https://www.federalregister.gov/documents/2020/06/01/2020-10292/interagency-guidance-on-credit-risk-review-systems))

Schema implication: an exception record needs `class` (doc/policy/compliance),
`policy_subtype` (approved-with-mitigant / unapproved), `severity`, `status`
(open/cleared/waived), `owner`, `due_date`, `cleared_date`, and roll-up fields for
aggregate/trend reporting.

---

## 5. Evidence / documentation currency

Reviewers test that the credit file holds **current** evidence for each analysis.
Regulators do not publish a single universal staleness table; the file must be
"current" per the bank's own policy, and review analyzes exceptions to it. ([OCC,
*Loan Portfolio Management* — "ensure that documentation remains current"](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html);
[FDIC RMS §3.2](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf))

### Evidence items and currency expectations

- **Financial statements / tax returns.** Current period statements present,
  **signed and dated**, and within the bank's recency policy (commonly annual;
  interim statements for higher-risk credits). Track the **quality tier** (audited /
  reviewed / compiled / tax return / company-prepared). ([OCC, *Rating Credit Risk*
  financial analysis](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf);
  [FDIC RMS §3.2](https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf))

- **Appraisals / evaluations.** Must comply with the **Interagency Appraisal and
  Evaluation Guidelines** (75 FR 77450, Dec 10, 2010): appraisals "must conform to
  … USPAP … and must contain an opinion of market value." An institution "must
  monitor collateral values" and **obtain a new appraisal or evaluation when the
  existing one no longer reflects current market conditions** (i.e., validity is
  not a fixed clock — it is driven by market/credit changes; a new appraisal is
  required when the prior valuation is no longer valid). An AVM "by itself … is not
  an appraisal." ([Interagency Appraisal and Evaluation Guidelines, 75 FR 77450](https://www.federalregister.gov/documents/2010/12/10/2010-30913/interagency-appraisal-and-evaluation-guidelines);
  [SR 10-16 / FDIC FIL-82-2010 PDF](https://www.federalreserve.gov/boarddocs/srletters/2010/sr1016a1.pdf))

- **Borrowing-base certificates.** For asset-based C&I: a current BBC detailing
  eligible A/R and inventory against advance rates. Test presence and recency
  (typically monthly). ([NCUA sample borrowing-base certificate](https://publishedguides.ncua.gov/examiner/Content/PDFs/SampleBorrowingBaseCert.pdf);
  collateral analysis per [OCC *Rating Credit Risk*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf))

- **Covenant compliance certificates.** Borrower-officer certificate delivered with
  periodic financials, certifying covenant compliance and no default; covenant
  testing should be performed and documented promptly on receipt of financials.
  ([Practical Law, *Compliance Certificate: Lending*](https://uk.practicallaw.thomsonreuters.com/6-611-7345))

- **Credit approval / authorization.** Evidence the facility was approved within
  authority (approval memo, committee minutes), and any policy exception was
  approved. Ties to §4's policy-exception "approved vs. unapproved" split. ([OCC,
  *Loan Portfolio Management*](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html))

Schema implication: model each evidence item as `{type, as_of_date, quality_tier,
required_frequency, policy_staleness_days, is_current(bool), source_ref}`, and let a
staleness rule generate a **documentation exception** (§4a) when `as_of_date` is
older than `policy_staleness_days`. Keep staleness thresholds **config-driven** —
they are bank-policy values, not fixed regulatory numbers (except that appraisal
re-ordering is condition-driven per the 2010 Guidelines).

---

## Confidence / open questions

**High confidence (verbatim, single interagency standard):**
- The five classification definitions (Pass/SM/SS/D/Loss) and the criticized-vs-
  classified boundary (§1). These are stable interagency text repeated across FDIC,
  OCC, and FRB manuals.
- The 2020 Interagency Guidance's independence + rating-validation expectation and
  its supersession of Attachment 1 of the 2006 ALLL policy statement (§1, §4).
- The RC-C loan taxonomy and owner-occupied vs. non-owner-occupied CRE definition
  (§2).
- The documentation-vs-underwriting exception split and materiality-based severity
  from OCC *Loan Portfolio Management* (§4).
- Appraisals must meet USPAP + market-value opinion; re-order when no longer valid
  (§5).

**Medium confidence / verify before quoting in a filed workpaper:**
- **Exact page/paragraph pin-cites** for the OCC booklet quotes were not confirmable
  because direct PDF fetch was blocked (see retrieval note). Confirm page numbers
  against the live PDFs before pasting quotes into a client-facing workpaper.
- The **internal 1–9 grade → regulatory bucket** mapping (§1) is *representative*,
  not mandated. Numbering differs by bank; treat the crosswalk as bank-configured.
- The **third exception class (compliance)** and the **approved-with-mitigant vs.
  unapproved** policy-exception split are industry-standard practice consistent with
  the guidance, but the guidance frames exceptions primarily as documentation vs.
  underwriting plus "compliance with laws" — the finer taxonomy is a practice
  convention, not a verbatim regulatory list.
- **Staleness day-counts** (annual statements, monthly BBCs, etc.) are *bank policy*
  values, not fixed regulatory thresholds. The tool must treat them as config.

**Open questions for the PRD author:**
1. Which agency's classification wording is canonical for SATC's clients (OCC vs.
   FDIC vs. FRB)? They are substantively identical — pick one and cite it.
2. Should the LOB roadmap follow the 10-segment review list (§2) or the raw RC-C
   items? Recommend the review list, with RC-C mapping retained for reconciliation.
3. Is the tool scoping to commercial/C&I + CRE first (deepest linesheets), deferring
   consumer/retail (which is more scorecard/tabular)?
4. Confirm whether SATC needs the CECL/allowance linkage (classifications feed the
   allowance) — the [OCC *Allowances for Credit Losses* booklet](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/allowances-for-credit-losses/pub-ch-allowances-credit-losses.pdf)
   is the source if so.

---

## Sources

1. OCC, *Rating Credit Risk*, Comptroller's Handbook — <https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/rating-credit-risk/pub-ch-rating-credit-risk.pdf>
2. OCC, *Loan Portfolio Management*, Comptroller's Handbook (Apr 1998) — index: <https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/index-loan-portfolio-management.html> ; PDF: <https://www.cdfifund.gov/system/files/documents/occ-loan-portfolio-management-comptrollers-handbook.pdf>
3. OCC, *Commercial Real Estate Lending*, Comptroller's Handbook — <https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/commercial-real-estate-lending/pub-ch-commercial-real-estate.pdf>
4. OCC, *Allowances for Credit Losses*, Comptroller's Handbook — <https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/allowances-for-credit-losses/pub-ch-allowances-credit-losses.pdf>
5. FDIC, RMS Manual of Examination Policies, §3.2 Loans — <https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-2.pdf>
6. FDIC, RMS Manual of Examination Policies, §3.1 Asset Quality — <https://www.fdic.gov/resources/supervision-and-examinations/examination-policies-manual/section3-1.pdf>
7. FDIC, *Adverse Classifications* (Credit Card Activities Manual, Ch. XI) — <https://www.fdic.gov/credit-card-activities-manual/chapter-xi-adverse-classifications>
8. Interagency Guidance on Credit Risk Review Systems, 85 FR 33278 (June 1, 2020) — <https://www.federalregister.gov/documents/2020/06/01/2020-10292/interagency-guidance-on-credit-risk-review-systems> ; OCC Bulletin 2020-50: <https://www.occ.gov/news-issuances/bulletins/2020/bulletin-2020-50.html> ; FDIC FIL-55-2020: <https://www.fdic.gov/news/financial-institution-letters/2020/fil20055.html> ; FRB SR 20-13: <https://www.federalreserve.gov/supervisionreg/srletters/SR2013.htm>
9. FFIEC 031/041 Call Report Instructions, Schedule RC-C Part I (Loans and Leases) — <https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2023/2023-09-rc-c1.pdf>
10. Interagency Appraisal and Evaluation Guidelines, 75 FR 77450 (Dec 10, 2010) — <https://www.federalregister.gov/documents/2010/12/10/2010-30913/interagency-appraisal-and-evaluation-guidelines> ; FRB SR 10-16 attachment PDF: <https://www.federalreserve.gov/boarddocs/srletters/2010/sr1016a1.pdf>
11. Federal Reserve, *The Importance of Loan Risk Rating Systems*, Community Banking Connections — <https://www.communitybankingconnections.org/Articles/2025/R2/the-importance-of-loan-risk-rating-systems>
12. NCUA, sample Borrowing Base Certificate — <https://publishedguides.ncua.gov/examiner/Content/PDFs/SampleBorrowingBaseCert.pdf>
13. Practical Law (Thomson Reuters), *Compliance Certificate: Lending* — <https://uk.practicallaw.thomsonreuters.com/6-611-7345>

*Note on retrieval:* regulator PDFs were read via the web-search tool (direct
fetch/`curl` to occ.gov / fdic.gov / federalregister.gov / federalreserve.gov
returned HTTP 403 in this environment). URLs above are the canonical primary
documents; confirm exact page pin-cites against the live PDFs before quoting in a
filed workpaper.
