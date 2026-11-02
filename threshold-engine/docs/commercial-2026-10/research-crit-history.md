# How far back each peer's commercial loans by internal grade are tagged in XBRL

Research note, 16 Oct 2026. Read-only: nothing in the repository was edited, nothing pushed.
This extends `threshold-engine/docs/commercial-2026-10/research-sec.md`. That note checked only each filer's 2026 Q2 10-Q. This one goes back through every 10-Q and 10-K XBRL instance from 2009 Q1 to 2026 Q2.

**Source.** SEC EDGAR only, fetched live this session:

- the submissions API, including the older-filings pages;
- each filing's `index.json`;
- the XBRL instance:
  - before inline XBRL, the instance file itself (`xxx-YYYYMMDD.xml`);
  - for inline filings, EDGAR's extracted `*_htm.xml`;
- the label linkbase (`*_lab.xml`) at the quarters noted below.

User-Agent: `SATC research research@example.com`. No other source and no internal data was used.

---

## 1. The answer

**Denominator: 16 SEC filers, the CIKs in research-sec.md §2.**

| Question | Count | Banks |
|---|---|---|
| Commercial loans tagged by class with an internal-grade measure, in any form, before 2013 | **15 / 16** | All except CFG. CFG was not an SEC filer until its first 10-Q, for 2014 Q3. |
| …with pass / special mention / substandard / doubtful / criticized-type categories (not rating buckets), before 2013 | **13 / 16** | All except KEY (2016 Q1), C (never) and CFG (2014 Q3) |
| …with those categories **and** the class on a dimension (axis member), before 2013 | **12 / 16** | All except COF (2014 Q3; the class was in the line item before that), KEY, C and CFG |
| Tagged by class at **2010 Q4**, the earliest quarter any filer tags it | **11 / 16** | 5 on a dimension with grade categories: JPM, WFC, FITB, MTB, RF. 3 with grade categories but the class in the line item: BAC, USB, COF. 3 with rating buckets only: C, TFC, KEY. |
| Tagged in **2009 Q1 – 2010 Q3** in the filer's own-period instance | **0 / 16** | Confirmed (see §4) |
| …but with earlier values carried as tagged prior-period comparatives in a later instance | **3 / 16** | JPM: 2009-12-31. RF: 2009-12-31 and 2010 Q1–Q3. KEY: 2009-12-31 and 2010 Q1–Q3, rating buckets only. |
| Any quarter missing between a bank's first tagged quarter and 2026 Q2 | **0 / 16** | No hole in any series. There are format breaks; see the "breaks" column in §3. |
| Category set changed at least once (not only a member rename) | **6 / 16** | KEY, TFC, PNC, ZION, CFG, C (see §3). BAC also relabelled its two categories to "Pass rated" / "Reservable criticized" in 2014 Q3; whether that is a definition change is not stated in XBRL, so it is not counted here. |
| Never tags internal pass / criticized for commercial loans, 2010 Q4 – 2026 Q2 | **1 / 16** | C. Corporate loans are tagged by investment grade / non-investment grade in all 63 quarters. |

**Quarter counts.** The full window, 2010 Q4 to 2026 Q2, is 63 quarters.

| Banks | Quarters tagged by class | Through 2026 Q2 |
|---|---|---|
| HBAN, FCNCA, ZION | 61 / 61 | first tagged 2011 Q2 |
| PNC | 60 / 60 | first tagged 2011 Q3 |
| CFG | 48 / 48 | first tagged 2014 Q3 |
| The other 11 filers | 63 / 63 | first tagged 2010 Q4 |

**Coverage of the scan.**

- 1,098 filer-quarters were in scope: 16 filers × 2009 Q1–2026 Q2, with CFG from 2014 Q3.
- 1,071 had an XBRL instance and were parsed. The 27 without one are listed in §4.
- Every parsed instance was read in full, not sampled.

---

## 2. Method and definitions

**Method.**

1. List every 10-K, 10-K/A, 10-Q and 10-Q/A from the submissions API.
2. For each report period, take the original filing. Take an amendment only when the original's filing index carries no instance. That applied to six quarters:
   - TFC 2009 Q2 and 2010 Q2 (10-Q/A)
   - MTB 2009 Q2 and 2010 Q2 (10-Q/A)
   - COF 2010 Q4 (10-K/A, accession 0001140361-11-014724)
   - RF 2010 Q4 (10-K/A, 0001193125-11-070898)
   - KEY 2021 Q1 (10-Q/A, 0000091576-21-000078). The original 10-Q, 0000091576-21-000070, has no XBRL.
3. Parse every fact on a context carrying a member on a credit-quality axis.

The brief asked for one instance a year, then bisection. I scanned **every** quarter instead, because only a full scan can show the gaps the brief asked about. The full scan answers the same question and does not depend on bisection.

A fact counts as **commercial** when its class members or its line-item name say commercial, C&I, CRE, construction, lease, corporate, wholesale or similar, and are not consumer-only. Each quarter is then classed by how the class is carried:

| Code | Meaning |
|---|---|
| **DIM** | Amounts by grade category with the loan class on a **dimension**, with at least 2 commercial class rows. Commercial-segment plus CRE-segment counts as 2 rows; that is how USB and HBAN carry them. |
| **CONCEPT** | Grade category on an axis, but the class carried by the **line item**, e.g. `us-gaap:LoansReceivableCommercialRealEstate`. It is machine-readable by class, but not dimensionally. |
| **RATING** | Class on a dimension, but the categories are rating buckets (investment grade / non-investment grade, or AAA-AA … CCC-C), with no pass / criticized. |
| **NONE** | No commercial grade facts at the period end. |

**Period.** The period is the instance's own period-end date. Prior-period columns are recorded separately as comparatives.

**Labels.** Labels were read from the filer's label linkbase. Both the standard label and the terse / verbose labels were kept, because the filer's own wording often sits in the terse label only. Example: HBAN's "OLEM" is the terse label on `us-gaap:SpecialMentionMember`, and its standard label is "Special Mention".

**Tie-outs done**, each against a different file from the XBRL instance:

- **FITB 2026 Q2, C&I.** Pass 81,037; special mention 1,910; substandard 2,682; doubtful 107 ($m). These equal the research-sec.md sample values.
- **FITB 2010 10-K, C&I.** Pass $23,147m, special mention 1,406, substandard 2,541. All three were found in the filed 10-K HTML table (`d10k.htm`).
- **JPM 2010 10-K, C&I.** Noncriticized 30,874; criticized performing 2,371; criticized nonaccrual 1,634. All three were found in `y86143e10vk.htm`.
- **KEY 2010 10-K, commercial, financial and agricultural.** BBB-BB 12,386; B 1,282; CCC-C 1,970. All were found in `l40752e10vk.htm`, in a table headed "AAA — AA / A / BBB — BB / B / CCC — C".

**Result: 4 of 4 tie-outs tied.**

---

## 3. Per bank

### Summary table

"Quarters" counts the quarters tagged by class, out of the quarters from the first tagged quarter to 2026 Q2.

| Bank (CIK) | First quarter tagged by class | First quarter with grade categories on a dimension | Quarters | Gaps | Earliest instant tagged (as a comparative) | Breaks in form |
|---|---|---|---|---|---|---|
| JPM (19617) | 2010 Q4, DIM | 2010 Q4 | 63/63 | none | 2009-12-31 (10-K 2010, 6 class rows) | none |
| WFC (72971) | 2010 Q4, DIM | 2010 Q4 | 63/63 | none | none earlier | none |
| BAC (70858) | 2010 Q4, CONCEPT | 2011 Q3 | 63/63 | none | none earlier | CONCEPT 2010 Q4–2011 Q2 |
| C (831001) | 2010 Q4, RATING | never | 63/63 RATING | none | none earlier | n/a |
| USB (36104) | 2010 Q4, CONCEPT | 2011 Q3 | 63/63 | none | none earlier | CONCEPT 2010 Q4–2011 Q2 |
| PNC (713676) | 2011 Q3, DIM | 2011 Q3 | 60/60 | none | 2010-12-31 (10-Q 2011 Q3, 5 rows) | none |
| TFC (92230) | 2010 Q4, RATING | 2011 Q3 | 63/63 (60 with grade categories) | none | none earlier | RATING 2010 Q4–2011 Q2 |
| COF (927628) | 2010 Q4 (10-K/A), CONCEPT | 2014 Q3 | 63/63 | none | none earlier | CONCEPT 2010 Q4–2014 Q2 (15 quarters) |
| KEY (91576) | 2010 Q4, RATING | 2016 Q1 | 63/63 (42 with grade categories) | none | 2009-12-31 and 2010 Q1–Q3, RATING | RATING 2010 Q4–2015 Q4 (21 quarters) |
| FITB (35527) | 2010 Q4, DIM | 2010 Q4 | 63/63 | none | 2010-09-30, but only 3 special-mention facts, not a table | none |
| HBAN (49196) | 2011 Q2, DIM | 2011 Q2 | 61/61 (49 DIM) | none | 2010-12-31 (9 rows), 2011-03-31 | CONCEPT 2016 Q3–2019 Q2 (12 quarters) |
| FCNCA (798941) | 2011 Q2, DIM | 2011 Q2 | 61/61 | none | 2010-12-31 (12 rows), 2011-03-31 | none |
| CFG (759944) | 2014 Q3, DIM | 2014 Q3 | 48/48 | none | 2013-12-31 (4 rows) | none |
| MTB (36270) | 2010 Q4, DIM | 2010 Q4 | 63/63 | none | none earlier | none |
| RF (1281761) | 2010 Q4 (10-K/A), DIM | 2010 Q4 | 63/63 | none | 2009-12-31 and 2010 Q1–Q3 (7 rows each) | none |
| ZION (109380) | 2011 Q2, CONCEPT | 2011 Q4 | 61/61 (59 DIM) | none | 2010-12-31 (8 rows) | CONCEPT 2011 Q2–Q3 |

### First tagged instance, and the 2026 Q2 instance

| Bank | First tagged | 2026 Q2 |
|---|---|---|
| JPM | https://www.sec.gov/Archives/edgar/data/19617/000095012311019773/jpm-20101231.xml | https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/jpm-20260630_htm.xml |
| WFC | https://www.sec.gov/Archives/edgar/data/72971/000095012311018541/wfc-20101231.xml | https://www.sec.gov/Archives/edgar/data/72971/000007297126000302/wfc-20260630_htm.xml |
| BAC | https://www.sec.gov/Archives/edgar/data/70858/000095012311018743/bac-20101231.xml | https://www.sec.gov/Archives/edgar/data/70858/000007085826000394/bac-20260630_htm.xml |
| C | https://www.sec.gov/Archives/edgar/data/831001/000120677411000316/c-20101231.xml | https://www.sec.gov/Archives/edgar/data/831001/000083100126000045/c-20260630_htm.xml |
| USB | https://www.sec.gov/Archives/edgar/data/36104/000095012311019888/usb-20101231.xml | https://www.sec.gov/Archives/edgar/data/36104/000003610426000044/usb-20260630_htm.xml |
| PNC | https://www.sec.gov/Archives/edgar/data/713676/000119312511301292/pnc-20110930.xml | https://www.sec.gov/Archives/edgar/data/713676/000162828026053170/pnc-20260630_htm.xml |
| TFC | https://www.sec.gov/Archives/edgar/data/92230/000119312511047405/bbt-20101231.xml | https://www.sec.gov/Archives/edgar/data/92230/000009223026000099/tfc-20260630_htm.xml |
| COF | https://www.sec.gov/Archives/edgar/data/927628/000114036111014724/cof-20101231.xml | https://www.sec.gov/Archives/edgar/data/927628/000092762826000089/cof-20260630_htm.xml |
| KEY | https://www.sec.gov/Archives/edgar/data/91576/000095012311017655/key-20101231.xml | https://www.sec.gov/Archives/edgar/data/91576/000162828026052671/key-20260630_htm.xml |
| FITB | https://www.sec.gov/Archives/edgar/data/35527/000119312511049817/fitb-20101231.xml | https://www.sec.gov/Archives/edgar/data/35527/000003552726000202/fitb-20260630_htm.xml |
| HBAN | https://www.sec.gov/Archives/edgar/data/49196/000095012311074333/hban-20110630.xml | https://www.sec.gov/Archives/edgar/data/49196/000004919626000066/hban-20260630_htm.xml |
| FCNCA | https://www.sec.gov/Archives/edgar/data/798941/000119312511215686/fcnca-20110630.xml | https://www.sec.gov/Archives/edgar/data/798941/000079894126000031/fcnca-20260630_htm.xml |
| CFG | https://www.sec.gov/Archives/edgar/data/759944/000075994414000009/cfg-20140930.xml | https://www.sec.gov/Archives/edgar/data/759944/000075994426000148/cfg-20260630_htm.xml |
| MTB | https://www.sec.gov/Archives/edgar/data/36270/000095012311016289/mtb-20101231.xml | https://www.sec.gov/Archives/edgar/data/36270/000003627026000050/mtb-20260630_htm.xml |
| RF | https://www.sec.gov/Archives/edgar/data/1281761/000119312511070898/rf-20101231.xml | https://www.sec.gov/Archives/edgar/data/1281761/000128176126000055/rf-20260630_htm.xml |
| ZION | https://www.sec.gov/Archives/edgar/data/109380/000119312511216704/zion-20110630.xml | https://www.sec.gov/Archives/edgar/data/109380/000010938026000111/zions-20260630_htm.xml |

### Categories, member names and labels over time

In this section:

- Labels are quoted from the filer's label linkbase.
- "Member" names are given as `prefix:LocalName`.
- "Quarters" are counts within the bank's own window.

Label linkbases were read at three kinds of quarter:

1. every quarter where the set of category members changed;
2. every 10-K;
3. the first and last quarters, plus CFG 2023 Q1–Q3.

Label-only changes inside a run of 10-Qs between those points would not be seen (§5).

#### JPM

**Categories.** Investment-grade / Noninvestment-grade, the latter split into:

- Noncriticized
- Criticized performing
- Criticized nonaccrual

Those three were present in all 63 quarters.

**Member renames.**

- Noncriticized:
  - 2010 Q4–2016 Q2: `jpm:NoncriticizedMember`
  - from 2016 Q3: `us-gaap:PassMember`, labelled "Noncriticized"
- Criticized nonaccrual: `jpm:CriticizedTotalNonaccrualMember` (2010 Q4–2011 Q1), then `jpm:CriticizedNonaccrualMember`.
- Investment grade was tagged as sub-buckets ("Investment Grade AAA to AAA-" … "BBB to BBB-") 2011 Q2–2016 Q2, 19 quarters.

**Axis.**

| Quarters | Axis |
|---|---|
| 2010 Q4–2011 Q1 | `us-gaap:GuaranteeObligationsByPaymentAndPerformanceRiskCreditRatingAxis` |
| 2011 Q2–2013 Q2 | `PaymentAndPerformanceRiskCreditRatingAxis` |
| from 2013 Q3 | `InternalCreditAssessmentAxis` |

**Classes.**

- 2010 Q4: C&I, Real estate, Financial institutions, Government agencies, Other.
- From 2012 Q3, real estate is split into Multifamily, Commercial lessors, Commercial construction and development, and Other.
- From 2016 Q3 the classes are sector members.

#### WFC

**Categories.** Pass / Criticized, 63 of 63 quarters, with no member rename.

**Classes.**

- C&I, CRE mortgage, CRE construction and Lease financing throughout.
- Foreign loans as a class 2010 Q4–2014 Q3.
- A purchased-credit-impaired split axis until 2019 Q1.

#### BAC

**Categories.**

| Quarters | Categories |
|---|---|
| 2010 Q4–2011 Q2 | `bac:RiskRatingsPassMember` / `bac:RiskRatingsCriticizedMember` |
| 2011 Q3–2014 Q2 | `us-gaap:PassMember` / `bac:RiskRatingsCriticizedMember` |
| 2014 Q3–2019 Q4 | `bac:RiskRatingsPassRatedMember` "Pass rated" / `bac:RiskRatingsReservableCriticizedMember` "Reservable criticized" |
| from 2020 Q1 | `us-gaap:PassMember` / `us-gaap:CriticizedMember`, labelled "Pass rated" / "Reservable criticized" |

The word "reservable" first appears in the labels at 2014 Q3. Whether the definition changed then is **not stated in XBRL** and was not checked in the text.

U.S. small business commercial is graded by refreshed FICO, not pass / criticized.

**Classes.** U.S. commercial, non-U.S. commercial, CRE, commercial lease financing, U.S. small business commercial.

- 2010 Q4–2011 Q2: in line items.
- From 2011 Q3: on dimensions.

**Change instances.**

- CONCEPT to DIM: https://www.sec.gov/Archives/edgar/data/70858/000007085811000140/bac-20110930.xml
- "Reservable criticized": https://www.sec.gov/Archives/edgar/data/70858/000007085814000139/bac-20140930.xml

#### C

**Categories.**

| Quarters | Categories |
|---|---|
| 2010 Q4–2013 Q3 | Investment grade / Non-investment grade, on `c:` and then `us-gaap:FinancingReceivableInformationByCreditQualityIndicatorAxis` |
| 2013 Q4–2019 Q4 | `us-gaap:ExternalCreditRatingByGroupingAxis` |
| from 2020 Q1 | Non-investment grade split "accrual" / "non-accrual" (`c:ExternalCreditRatingNonInvestmentGradeAccrualMember` / `…NonaccrualMember`) |

No pass, special mention, substandard or criticized member is on Citi's commercial loan facts in any of the 63 quarters.

**Change instance (2020 Q1):** https://www.sec.gov/Archives/edgar/data/831001/000083100120000044/c-3312020x10q_htm.xml

#### USB

**Categories.** Pass / Special mention / Classified / Total criticized throughout.

**Members.**

| Quarters | Members |
|---|---|
| 2010 Q4–2011 Q2 | `usb:PassInternalCreditRatingMember`, `usb:SpecialMentionCriticizedInternalCreditRatingMember`, `usb:ClassifiedCriticizedInternalCreditRatingMember`, `usb:TotalCriticizedInternalCreditRatingMember`, on a `usb:` axis |
| 2011 Q3–2014 Q2 | `usb:ClassifiedCriticizedMember` |
| from 2014 Q3 | `us-gaap:SubstandardMember`, labelled "Classified Criticized" and, in 2026, "Classified". This is the label research-sec.md §4 reported. |

**Classes.** The Commercial and CRE segments.

- 2010 Q4–2011 Q2: as line items.
- From 2011 Q3: on dimensions.
- From 2023 Q4: class members (`usb:CommercialLoanAndLeaseFinancingLoanMember`, `us-gaap:CommercialRealEstateMember`).
- An energy-sector "special mention or classified" line was tagged in some quarters between 2015 Q1 and 2017 Q2.

#### PNC

**Categories.**

| Quarters | Categories |
|---|---|
| 2011 Q3–2018 Q3 (29 quarters) | Pass / Special Mention / Substandard / Doubtful. A second axis also carried `pnc:CriticizedCommercialLoansMember` (17 quarters). |
| from 2018 Q4 (31 quarters) | Pass (label "Pass Rated") / Criticized |

**Classes.** Commercial (C&I from 2020 Q2), CRE, Equipment lease financing, and purchased impaired early on. 2026 Q1 and Q2 show C&I and CRE only.

The 2011 Q3 class rows sit on `ServicingAssetsAtFairValueByTypeOfFinancialInstrumentAxis`, as recorded.

**Change instance:** https://www.sec.gov/Archives/edgar/data/713676/000071367619000015/pnc-20181231.xml

#### TFC

**Categories.**

| Quarters | Categories |
|---|---|
| 2010 Q4 | Investment Grade / Near Investment Grade / Noninvestment Grade |
| 2011 Q1–Q2 | Noninvestment grade split Performing / NonPerforming |
| 2011 Q3 onward | Pass / Special Mention / Substandard (performing) / Nonperforming |

**Members.**

- 2011 Q3–2015 Q2: `bbt:` members.
- From 2015 Q3: us-gaap members, labels unchanged in meaning.

**Classes.**

- 2011–2014: C&I, CRE-other, CRE residential ADC, other lending subsidiaries, later CRE construction / income-producing and dealer floor plan.
- From 2017 Q4: C&I, CRE, lease financing, then construction.

**Change instance:** https://www.sec.gov/Archives/edgar/data/92230/000119312511304459/bbt-20110930.xml

#### COF

**Categories.**

| Quarters | Members | Class carried by |
|---|---|---|
| 2010 Q4–2014 Q2 | `cof:NoncriticizedMember`, `cof:CriticizedPerformingMember`, `cof:CriticizedNonperformingMember` | line items: middle market, CRE, small-ticket CRE, specialty lending, later C&I |
| from 2014 Q3 | `us-gaap:PassMember` (label "Noncriticized") / `us-gaap:CriticizedMember`, the criticized amount split on `FinancialInstrumentPerformanceStatusAxis` | dimensions |

**Classes from 2014 Q3.** C&I, Commercial and multifamily real estate, and small-ticket CRE until 2019.

**Change instance:** https://www.sec.gov/Archives/edgar/data/927628/000092762814000020/cof-20140930.xml

#### KEY

**2010 Q4–2015 Q4 (21 quarters).** Commercial classes by rating bucket:

- Labels: "AAA-AA", "A", "BBB-BB", "B", "CCC-C".
- Member names: `key:ExternalCreditRating…Member`.
- Axis, as recorded:
  - a `key:` axis, then
  - `us-gaap:FinancingReceivableInformationByCreditQualityIndicatorAxis`, then
  - 2014 Q2 – 2015 Q1, `us-gaap:FairValueEstimateNotPracticableDisclosureItemsAxis`, then
  - 2015 Q2–Q4, `us-gaap:ExternalCreditRatingByGroupingAxis`.

**From 2016 Q1 (42 quarters).** Pass / Criticized (Accruing) / Criticized (Nonaccruing).

**Classes.** Commercial, financial and agricultural; CRE commercial mortgage; construction; commercial lease financing. A PCI / non-PCI split ran 2016 Q3–2019.

**Change instance:** https://www.sec.gov/Archives/edgar/data/91576/000119312516579436/key-20160331.xml

#### FITB

**Categories.** Pass / Special Mention / Substandard / Doubtful throughout.

- Labels carry the prefix "Risk Level, …" from 2011 Q1.
- `us-gaap:DoubtfulMember` is absent in 3 of 63 quarters: 2015 Q1, 2015 Q4, 2016 Q2.

**Classes, stable throughout.** C&I, commercial mortgage owner-occupied, commercial mortgage nonowner-occupied, commercial construction, commercial leases.

#### HBAN

**Categories.** Pass / Special Mention (terse label "OLEM" from the first quarter) / Substandard / Doubtful. Doubtful is absent in 6 of 61 quarters.

**Classes.**

| Quarters | How the class is carried |
|---|---|
| 2011 Q2–2016 Q2 (21 quarters) | C&I owner-occupied and other; **CRE by property type: retail, multifamily, office, industrial and warehouse, other**; plus purchased-impaired. This is the only office split on the grade axis in any of the 16 filers in any quarter; research-sec.md found 0/16 for 2026 Q2. Example, 2015 Q4 office ($m): pass 822.8, special mention 35.4, substandard 36.0, doubtful 0.4. |
| 2016 Q3–2019 Q2 (12 quarters) | Class only in line items (`LoansReceivableCommercialAndIndustrial`, `LoansReceivableCommercialRealEstate`): CONCEPT |
| 2019 Q3–2021 Q1 | Commercial and CRE segments on a dimension |
| from 2021 Q2 | Adds lease financing, then C&I loan members |

**Change instances.**

- https://www.sec.gov/Archives/edgar/data/49196/000004919616000085/hban-20160930.xml
- https://www.sec.gov/Archives/edgar/data/49196/000004919619000071/hban2019093010q_htm.xml

#### FCNCA

**Categories.** Pass / Special Mention / Substandard / Doubtful / Ungraded throughout. Doubtful is absent in 1 of 61 quarters (2020 Q4).

**Classes.**

- 2011–2013: covered (FDIC loss-share) and non-covered splits.
- From 2020 Q1: owner-occupied and non-owner-occupied commercial mortgage.
- From 2023 Q1: Silicon Valley Bridge Bank segment classes (Investor dependent early / growth stage, Innovation C&I and cash-flow dependent, CRE).

#### CFG

**2014 Q3–2023 Q3.** Pass / Special Mention / Substandard / Doubtful. The 2023 Q1–Q3 labels were still "Substandard" and "Doubtful".

**From 2023 Q4.** The categories are Pass / Special Mention / Substandard Accrual / Nonaccrual, but the 10-Ks and 10-Qs carry them on different members:

| Filing | Members carrying the categories |
|---|---|
| 10-Ks (2023, 2024, 2025) | `cfg:SubstandardAccrualMember`, `cfg:NonaccrualMember` |
| 10-Qs from 2024 Q1 | `us-gaap:SubstandardMember` labelled "Substandard Accrual", and `us-gaap:DoubtfulMember` labelled "Nonaccrual" |

So `us-gaap:DoubtfulMember` means "Doubtful" up to 2023 Q3 and "Nonaccrual" from 2024 Q1. Reading CFG by member name across 2023 would join two different measures.

**Change instances.**

- https://www.sec.gov/Archives/edgar/data/759944/000075994424000039/cfg-20231231_htm.xml
- https://www.sec.gov/Archives/edgar/data/759944/000075994424000090/cfg-20240331_htm.xml

#### MTB

**Categories.** Pass / Criticized Accrual / Criticized Nonaccrual, all 63 quarters.

**Axis.** `mtb:LoansAndLeasesReceivableByLoanGradesAxis` until 2013 Q3, then `InternalCreditAssessmentAxis`.

**Labels.** The 2023 10-K's filing index has no `_lab.xml`, so its labels were not read.

#### RF

**Categories.** Pass / Special Mention / Substandard Accrual / Non-accrual throughout.

**Members.**

- 2010 Q4–2011 Q1: `rf:OlemMember` (label "OLEM") and `rf:SubstandardAccrualMember`.
- From 2011 Q2: `us-gaap:SpecialMentionMember` and `us-gaap:SubstandardMember`.

**Classes, throughout.** C&I, CRE mortgage owner-occupied, CRE construction owner-occupied, investor RE mortgage, investor RE construction.

**Change instance:** https://www.sec.gov/Archives/edgar/data/1281761/000119312511209965/rf-20110630.xml

#### ZION

**Categories.**

| Quarters | Categories |
|---|---|
| 2011 Q2–2019 Q4 | Pass / Special Mention / Substandard (2011 label "Sub-Standard") / Doubtful |
| from 2020 Q1 | Pass / Special Mention / Accruing Substandard / Nonaccrual (`zions:AccruingSubstandardMember`, `zions:NonaccrualMember`) |

**Classes.**

- 2011 Q2–Q3: in line items (C&I, owner-occupied, CRE term, construction and land development, and others).
- 2011 Q4: segments on a dimension.

**Change instance:** https://www.sec.gov/Archives/edgar/data/109380/000010938020000174/zions-20200331_htm.xml

### Axis migration

Every filer except C moved its grade axis to `us-gaap:InternalCreditAssessmentAxis` and never left it. C never used it.

| First quarter on `us-gaap:InternalCreditAssessmentAxis` | Banks |
|---|---|
| 2013 Q2 | BAC, USB, COF, ZION |
| 2013 Q3 | JPM, FITB, FCNCA |
| 2013 Q4 | WFC, PNC, MTB |
| 2014 Q3 | CFG (from its first filing) |
| 2014 Q4 | RF |
| 2015 Q1 | KEY (the axis appears on commercial facts from 2015 Q1, but the rating buckets stay on other axes until 2015 Q4; Pass / Criticized sit on it from 2016 Q1) |
| 2015 Q3 | TFC |
| 2015 Q4 | HBAN |

**Before the switch**, filers used `us-gaap:FinancingReceivableInformationByCreditQualityIndicatorAxis` or their own axes:

- `bac:CreditQualityPortfolioAxis`
- `cof:CommercialRiskProfileByInternalRiskRatingAxis`
- `hban:CreditQualityIndicatorAxis`
- `mtb:LoansAndLeasesReceivableByLoanGradesAxis`
- `bbt:FinancingReceivableRecordedInvestmentByCreditQualityIndicatorAxis`
- `pnc:FinancingReceivableInformationByCommercialLoansQualityAxis`
- `rf:` axes
- `usb:AccountsNotesLoansAndFinancingReceivableByInternalCreditQualityRatingsAxis`

**Consequence for the reader.** A parser that looks only at `InternalCreditAssessmentAxis` sees nothing before 2013 Q2 for any bank, and nothing before 2015 Q4 for HBAN. The same applies to `research-sec.md` §1a's tracker and to `classes.py`.

---

## 4. 2009 Q1 – 2010 Q4

**2009 Q1.** None of the 15 filers then filing has an instance in its 2009 Q1 10-Q filing index. HBAN, FCNCA and ZION have no instance in any filing index until 2010 Q2.

So the **27 filer-quarters without any instance** are:

- 2009 Q1 for JPM, WFC, BAC, C, USB, PNC, TFC, COF, KEY, FITB, MTB, RF: 12
- 2009 Q1 – 2010 Q1 for HBAN, FCNCA, ZION: 15

CFG has no filing at all before 2014.

**2009 Q2 – 2010 Q3.** Instances exist for 12 of 16 filers from 2009 Q2 (all but HBAN, FCNCA, ZION and CFG) and for 15 of 16 from 2010 Q2. **None** carries commercial loan amounts by grade category at its own period end: 0 of 16 in every quarter. This is confirmed by full parse, not by sampling.

**2010 Q4.**

| Status | Banks | Count |
|---|---|---|
| DIM | JPM, WFC, FITB, MTB, RF | 5 |
| CONCEPT | BAC, USB, COF | 3 |
| RATING | C, TFC, KEY | 3 |
| Not tagged | PNC (from 2011 Q3); HBAN, FCNCA, ZION (from 2011 Q2) | 4 |
| Not a filer | CFG | 1 |

PNC, HBAN, FCNCA and ZION have 2010 Q4 instances with no grade facts.

**Pre-2010 Q4 values that exist only as comparatives in later instances:**

| Bank | Date | Rows | Where |
|---|---|---|---|
| JPM | 2009-12-31 | 6 class rows, DIM | in the 2010 10-K |
| RF | 2009-12-31 | 7 rows | 10-K/A 2010 |
| RF | 2010-03-31, 06-30, 09-30 | 7 rows each | prior-year columns of the 2011 Q1–Q3 10-Qs |
| KEY | 2009-12-31 and 2010 Q1–Q3 | 4 rows each, RATING buckets only | same pattern |
| FITB | 2010-09-30 | 3 special-mention facts only | 2011 Q3 10-Q; not a table |

All of these were checked to be instant contexts.

So the answer to "is 2009 Q1 – 2010 Q4 covered?" is:

- **2009 Q1 – 2010 Q3: no** for 13 of 16 banks, and only via later-filed comparatives for JPM (2009 Q4), RF (2009 Q4 – 2010 Q3) and KEY (2009 Q4 – 2010 Q3, rating buckets).
- **2010 Q4: yes** for 8 of 16 with grade categories (5 dimensional), plus 3 with rating buckets.

I did **not** verify this session the accounting-standard effective date that would explain the 2010 Q4 start.

---

## 5. COULD NOTs and limits

1. **Labels between checkpoints.** Labels were read at category-change quarters, at every 10-K, and at CFG 2023 Q1–Q3. That is 400 label files. A relabel that leaves member names unchanged, and that happens in a 10-Q between two of those points, would not be detected. The CFG case shows this happens; it was caught only because the change coincided with a 10-K.
   - **MTB 2023 10-K:** its filing index has no `_lab.xml`, so its labels were not read.
2. **The classifier is a pattern match on member and line-item names**, and the "commercial" and "category" tests are regexes. It was checked in two ways:
   - 4 of 4 value tie-outs (§2);
   - manual inspection of every quarter where a bank's verdict or category set changes.

   It was **not** checked by reading every one of the 1,071 instances by eye. Two false positives were found and removed during the work:
   - Citi guarantee rows "Classified based on internal and external ratings";
   - FITB's disposal-group "Classified as held for sale".
3. **Inline-XBRL cross-check not done.** For 2019 onward I read EDGAR's extracted `_htm.xml`, not the `ix:` facts in the primary .htm.
4. **Amendments.** Amendments were not compared with originals. A 10-K/A or 10-Q/A was used only when the original had no instance (six quarters, §2).
5. **Meaning of relabels.** Whether a relabel reflects a definition change was not checked in the filing text. Examples: BAC's "Reservable criticized" from 2014 Q3, and CFG's Doubtful to Nonaccrual from 2023 Q4.
6. **Rate limit.**
   - Each process spaced its requests at least 0.15 s apart.
   - Each instance pass ran as **two concurrent processes** of 3 threads each, so the enforced ceiling was about 13 requests per second, above the 10 per second asked.
   - Measured from output timestamps: the second pass averaged 3.1 instances per second; its busiest second completed 11 files.
   - The fetch helper retries silently on any non-404 HTTP error. So "no errors logged" (0 ERR lines in the four scan logs) does not prove SEC never throttled a request.
7. **Bank versus holding-company basis.** Not examined here; see research-sec.md §5. Everything above is the SEC filer's consolidated XBRL.

---

## 6. Files (the scripts are kept; the data is not)

Scripts, in `research-scripts/crit-history/` (they read the SEC contact from `SEC_USER_AGENT`):

| Script | What it does |
|---|---|
| `sec.py` | User-Agent, rate spacing, CIK list |
| `subs.py` | Filing lists |
| `idx.py` | Filing indexes |
| `pick.py` | Instance and label choice |
| `analyze2.py` / `scan2.py` | Fact-level parse of every instance |
| `verdict2.py` | Classification |
| `summary.py` | First quarter, counts, gaps, comparatives |
| `labels.py` / `labtl.py` | Labels |
| `checkcomp.py` | Comparative check |
| `samples.py` | Sample rows |

Data (working files, not kept):

| File | Contents |
|---|---|
| `subs_all.json` | Filing lists |
| `plan.json` | Which filing was read for each quarter |
| `sum2/*.json` | 1,071 fact dumps |
| `verdicts2.json` | Per-quarter verdicts with rows and categories |
| `summary.json` | Per-bank summary |
| `labs/*.json` | Label maps |
| `labtl.txt` | Label timeline |
| `samples.json` | Sample rows |
