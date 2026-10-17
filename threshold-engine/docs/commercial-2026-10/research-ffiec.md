# FFIEC Call Report: instructions, bulk data and form type (research, 16 Oct 2026)

This research closes two items in `threshold-engine/docs/COMMERCIAL-PROPOSAL.md` §6: item 2 (the FFIEC instructions) and item 3 (NDFI in the FFIEC bulk files). It also closes item 12 (031 or 041). It is read-only, and no repository file was edited. Amounts are **$ thousands**, as filed. Everything is public: FDIC, FFIEC CDR and Federal Reserve sites.

## Summary

| Question | Answer | Source |
|---|---|---|
| Instruction text reachable? | **Yes**, through the FDIC's hosted copy of the FFIEC 031/041 instruction book. ffiec.gov itself refused both curl and WebFetch (HTTP 403). | §1 |
| (a) C&I definition and exclusions | Quoted, RC-C-9 to RC-C-11 (12-24) | §1.2a |
| (b) Secured-by-real-estate rule | The ">50 percent of principal at origination" test, quoted from Glossary A-90a (6-24) | §1.3 |
| (c) RC-C 9.a NDFI after Dec 2024 | Quoted (RC-C-17/18, 12-24), with the June 2024 text for comparison. Before 2024Q4, the 031 reported NDFI **for domestic offices only** | §1.4 |
| (d) PPP | **No instruction names an RC-C line.** They say "the appropriate loan category in Schedule RC-C, Part I". The PPP balance is RC-M Memo 17.b (`RCONLG27`) | §1.5 |
| (e) RC-L 1.e.(1) | Quoted, RC-L-2c (12-24). `J457`, from 2010Q1 | §1.6, §2 |
| (f) RC-N Memo 9 | Quoted, RC-N-15 (12-24). `PV23` / `PV24` / `PV25`, from 2024Q4 | §1.7, §2 |
| (g) NDFI charge-off line in RI-B? | **No.** NDFI charge-offs fall in RI-B Part I item 7, "All other loans" (`RIAD4644`/`RIAD4628`), mixed with other loan types. Confirmed three ways: instruction text, bulk file columns and the MDRM | §1.8 |
| FFIEC bulk data reachable by script? | **Yes.** cdr.ffiec.gov Bulk Data Download, scripted ASP.NET postback, 7 quarters downloaded | §2 |
| KeyBank values at 2026-06-30 | **Obtained** for every item, from the bulk file and, separately, from KeyBank's filed Call Report (CDR facsimile PDF). The two agree to the dollar | §2.3 |
| 031 or 041 at 2026-06-30 | **15 of 16 file the FFIEC 031. Zions (cert 2270) files the 041.** Source: FDIC `CALLFORM` and the CDR bulk "Financial Institution Filing Type". The two agree on all 16 | §3 |

---

## 1. The instructions

### 1.1 Routes tried and what each returned

| Route | Result |
|---|---|
| `https://www.ffiec.gov/forms031.htm`, `/resources/reporting-forms/ffiec031-ffiec041`, `/pdf/FFIEC_forms/FFIEC031_FFIEC041_202506_i.pdf` (curl, browser User-Agent) | **403** on all three (244 KB block page) |
| WebFetch `https://www.ffiec.gov/sites/default/files/data/reporting-forms/supplemental-instruction-031/FFIEC031_FFIEC041_FFIEC051_suppinst_202006.pdf` | **403** |
| Wayback availability API `https://archive.org/wayback/available?url=ffiec.gov/pdf/FFIEC_forms/FFIEC031_FFIEC041_202412_i.pdf` | Answered: snapshot `20250309231016` exists |
| Wayback download `https://web.archive.org/web/20250309231016id_/https://www.ffiec.gov/pdf/FFIEC_forms/FFIEC031_FFIEC041_202412_i.pdf` | **COULD NOT.** 16 connections were reset ("ws_closed_mid_exchange" at the egress proxy). The CDX query to web.archive.org was also reset |
| **FDIC copy**: `https://www.fdic.gov/bank-financial-reports/current-quarter-call-report-forms-instructions-and-related-materials` | **200.** It links the current FFIEC 031/041 instruction book, schedule by schedule. **Used** |
| FDIC previous-quarter pages (`https://www.fdic.gov/bank-financial-reports/previous-quarters`) | **200.** Used for edition history |
| `https://archive.fdic.gov/view/fdic/10099/fdic_10099_DS2.pdf` and `_DS3.pdf` (curl) | 403 (Akamai "Access Denied"). **WebFetch fetched both PDFs**, which were saved and text-extracted locally. **Used** |
| Federal Reserve `https://www.federalreserve.gov/apps/reportingforms/Report/Index/FFIEC_031` | 200. Not needed after the FDIC route worked |
| govinfo | Not tried, because the FDIC route had already worked |

### 1.2 Edition in force, and the edition history

The FDIC's current page holds the book "Most Recent Update September 30, 2026":
`https://www.fdic.gov/bank-financial-reports/ffiec-reports-condition-and-income-instructions-ffiec-031-and-041-report-5`.
Each schedule PDF carries an edition in each page footer, such as `RC-C-9 (12-24)`.

**Update lists** (FDIC-hosted "Call Report Instructions Update" PDFs list every changed page):

| Update | Pages changed in RC-C / RC-L / RC-N / RI-B / Glossary / General | URL |
|---|---|---|
| Dec 2024 | RC-C-8a, 11, 14a, 17–20b, 28, 30–33; **RC-L-2c – RC-L-3**; RC-N-2, **RC-N-15**; **RI-B-7 – RI-B-10**; General 4–6a, 16; Glossary many. It says: *"Updates to Schedules RC-C, RC-L, and RC-N are mainly related to the reporting of loans to nondepository financial institutions"* | `https://www.fdic.gov/bank-financial-reports/ffiec-031-and-ffiec-041-call-report-instructions-update-december-2024` |
| Mar 2025 | RC-C-8, RC-C-19, RC-C-20 | `https://www.fdic.gov/bank-financial-reports/ffiec-031-and-ffiec-041-call-report-instructions-update-march-2025` |
| Jun 2025, Sep 2025 | No new update. Those quarters' pages link the March 2025 update | `https://www.fdic.gov/bank-financial-reports/june-2025-call-report-forms-instructions-and-related-materials`, `.../september-2025-...` |
| Dec 2025 | RC-C-21; RC-M-19–20; RC-N-11; Glossary A-11, A-20a | `https://www.fdic.gov/bank-financial-reports/ffiec-031-and-ffiec-041-call-report-instructions-update-december-2025.pdf` |
| Mar 2026 | No new update. The page links the December 2025 update | `https://www.fdic.gov/bank-financial-reports/march-2026-call-report-forms-instructions-and-related-materials` |
| Jun 2026 | RC-R Part I only | `https://www.fdic.gov/bank-financial-reports/ffeic-031-041-call-report-instruction-update-june-2026.pdf` |
| Sep 2026 | RC-E, RC-O, RC-R I, RC-S, General 10–10a, Glossary A-20a, A-78, A-102, A-118a–A-119 | `https://www.fdic.gov/bank-financial-reports/ffiec-031-041-3q-2026-updates-final.pdf` |

So at 2026-06-30 the RC-L, RC-N Memo 9, RI-B and RC-C item 4 and 9.a pages quoted below were the ones in force. **Not compiled:** update lists before June 2024. The FDIC previous-quarter pages back to 2020 exist but were not read for these schedules.

**Finding: the FDIC's current book links stale RC-L and RI-B files.** The current (Sept 2026) and June 2026 book pages link
`https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2020/2020-09-rc-l.pdf` (latest page edition 9-20; it lacks the 12-24 pages) and
`https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2024/031-041-324-ri-b.pdf` (latest 3-24; it lacks the 12-24 pages).
The Dec 2024 update says RC-L-2c–RC-L-3 and RI-B-7–RI-B-10 changed. The 12-24 files are linked from the December 2024 book (`https://www.fdic.gov/bank-financial-reports/ffiec-reports-condition-and-income-instructions-ffiec-031-and-041-report-1`):
RC-L `https://www.fdic.gov/media/177656` (it redirects to `.../ffiec-031-041-schedule-rc-l-derivatives-and-balance-sheet-items-december`; footers include RC-L-2c, 2d and 3 at **(12-24)**), and
RI-B `https://www.fdic.gov/media/177696`. **No update after Dec 2024 touches RC-L or RI-B**, so these are the current editions. The RC-L and RI-B quotes below are from them.

Files used (SHA-256 of what was downloaded):

| File | URL | SHA-256 |
|---|---|---|
| RC-C (current, has 3-25 and 12-25 pages) | `https://www.fdic.gov/bank-financial-reports/ffiec-031-and-041-schedule-rc-c-loans-and-lease-financing-receivables` | `3c4b2a8c59ad52e08c5b64d792e378a6e70579549aee995595a7d07fecb93c89` |
| RC-N (current, has 12-25 page) | `https://www.fdic.gov/bank-financial-reports/ffiec-031-and-041-schedule-rc-n-past-due-and-nonaccrual-loans-leases-and` | `849109560e8692dac607efdf6d134598960824320df6161ce1b7be2e33bad39d` |
| RC-L (12-24) | `https://www.fdic.gov/media/177656` | not hashed (text extracted; footers recorded above) |
| RI-B (12-24) | `https://www.fdic.gov/media/177696` | not hashed (text extracted) |
| Glossary (9-30-2026) | `https://www.fdic.gov/bank-financial-reports/031-041-926gloss-9-30-2026-final.pdf` | `c97459dccbeb4721fed2adfeb47769a869c34e102237177bcc0ef1e47840b68f` |
| General Instructions (Sept 2026) | `https://www.fdic.gov/bank-financial-reports/ffiec-031-and-041-general-instructions-september-2026.pdf` | `4ab41fc6055d52c0cc7aa795f16b3b3474c1c8fc4901856615e141e915456a05` |
| RC-M (Dec 2025) | `https://www.fdic.gov/bank-financial-reports/ffiec-031-and-041-schedule-rc-m-memoranda-december-2025.pdf` | not hashed |
| RC-C (June 2024, for comparison) | `https://www.fdic.gov/resources/bankers/call-reports/crinst-031-041/2024/031-041-624-rc-c1.pdf` | `b5b1fffbd6c97d66015debed02b3537d99b88061a78837228f40c4fb36ad19f9` |
| June 2020 COVID-19 Related Supplemental Instructions | `https://archive.fdic.gov/view/fdic/10099/fdic_10099_DS3.pdf` (via WebFetch) | `c4402d47bf347cc0590e01b7163f7500ba20e774845120919a36ee7840305c68` |
| June 2020 Supplemental Instructions | `https://archive.fdic.gov/view/fdic/10099/fdic_10099_DS2.pdf` (via WebFetch) | `c5abd7b4c43420e1b6d8c5c961743fb55ac0594ee1d95a231326034f9daeae6a` |

### 1.2a (a) Commercial and industrial loans: RC-C Part I, item 4 (pages RC-C-9 to RC-C-11, edition 12-24)

> **4 Commercial and industrial loans.** Report loans for commercial and industrial purposes to sole proprietorships, partnerships, corporations, and other business enterprises, whether secured (other than those that meet the definition of a "loan secured by real estate") or unsecured, single-payment or installment. On the FFIEC 041, all banks should report the total of these loans in column B, and banks with $300 million or more in total assets should also report in the appropriate subitems of column A a breakdown of these loans between those loans to U.S. and non-U.S. addressees. On the FFIEC 031, all banks should report a breakdown of these loans between those to U.S. and non-U.S. addressees for the fully consolidated bank in the appropriate subitems of column A and for domestic offices in the appropriate subitems of column B.
>
> Commercial and industrial loans may take the form of direct or purchased loans. Include loans to individuals for commercial, industrial, and professional purposes but not for investment or personal expenditure purposes. Also include the reporting bank's own acceptances that it holds in its portfolio when the account party is a commercial or industrial enterprise. Exclude all commercial and industrial loans held for trading.

The include list runs from (1) to (13). It includes "(3) Loans to business enterprises guaranteed by the Small Business Administration (SBA)", "(6) Loans made to finance construction that do not meet the definition of a 'loan secured by real estate'", "(9) Dealer flooring or floor-plan loans" and "(13) Overnight lending for commercial and industrial purposes".

**Exclusions** (RC-C-10 to RC-C-11, verbatim):

> Exclude from commercial and industrial loans:
> (1) Loans that meet the definition of a "loan secured by real estate," even if for commercial and industrial purposes (report in Schedule RC-C, Part I, item 1).
> (2) Loans to depository institutions (report in Schedule RC-C, Part I, item 2).
> (3) Loans to nondepository financial institutions such as real estate investment trusts, mortgage companies, and insurance companies (report in Schedule RC-C, Part I, item 9.a).
> (4) Loans for the purpose of purchasing or carrying securities, including margin loans (report in Schedule RC-C, Part I, item 9.b or 9.b.1, as appropriate).
> (5) Loans for the purpose of financing agricultural production, whether made to farmers or to nonagricultural businesses (report in Schedule RC-C, Part I, item 3).
> (6) Loans to nonprofit organizations, such as hospitals or educational institutions (report as all other loans in Schedule RC-C, Part I, item 9.b and item 9.b.2, as appropriate), except those for which oil or mining production payments serve as collateral which are to be reported in this item.
> (7) Holdings of acceptances accepted by other banks (report in Schedule RC-C, part I, item 2).
> (8) Holdings of the bank's own acceptances when the account party is another bank (report in Schedule RC-C, part I, item 2) or a foreign government or official institution (report in Schedule RC-C, part I, item 7, on the FFIEC 031; Schedule RC-C, part I, item 9.b, on the FFIEC 041).
> (9) Equipment trust certificates (report in Schedule RC-B, item 6, "Other debt securities").
> (10) Any commercial or industrial loans held by the reporting bank for trading purposes (report in Schedule RC, item 5, "Trading assets").
> (11) Commercial paper (report in Schedule RC-B, item 5.a, "Asset-backed securities," or item 6, "Other debt securities," or in Schedule RC, item 5, "Trading assets," as appropriate).
>
> NOTE: Items 4.a and 4.b are not applicable to banks filing the FFIEC 041 report forms that have less than $300 million in total assets.

### 1.3 (b) "Secured by real estate": Glossary, "Loan Secured by Real Estate" (page A-90a, edition 6-24; continues on A-90b)

> **Loan Secured by Real Estate:** For purposes of these reports, a loan secured by real estate is a loan that, at origination, is secured wholly or substantially by a lien or liens on real property for which the lien or liens are central to the extension of the credit – that is, the borrower would not have been extended credit in the same amount or on terms as favorable without the lien or liens on real property. To be considered wholly or substantially secured by a lien or liens on real property, the estimated value of the real estate collateral at origination (after deducting any more senior liens held by others) must be greater than 50 percent of the principal amount of the loan at origination.
>
> A loan satisfying the criteria above, except a loan to a state or political subdivision in the U.S., is to be reported as a loan secured by real estate in Schedule RC-C, Part I, item 1, and related items in the Consolidated Reports of Condition and Income, (1) regardless of whether the loan is secured by a first or a junior lien; (2) regardless of whether the loan was originated by the reporting bank or purchased from others and, if originated by the reporting bank, regardless of the department within the bank or bank subsidiary that made the loan; (3) regardless of how the loan is categorized in the bank's records; (4) and regardless of the purpose of the financing. Only in a transaction where a lien or liens on real property (with an estimated collateral value greater than 50 percent of the loan's principal amount at origination) have been taken as collateral solely through an abundance of caution and where the loan terms as a consequence have not been made more favorable than they would have been in the absence of the lien or liens, would the loan not be considered a loan secured by real estate for purposes of the Consolidated Reports of Condition and Income. In addition, when a loan is partially secured by a lien or liens on real property, but the estimated value of the real estate collateral at origination (after deducting any more senior liens held by others) is 50 percent or less of the principal amount of the loan at origination, the loan should not be categorized as a loan secured by real estate. Instead, the loan should be reported in one of the other loan categories used in these reports based on the purpose of the loan.

Example (1), same page:

> A bank loans $700,000 to a dental group to construct and equip a building that will be used as its dental office. … At origination, the estimated values of the building, upon completion, and the equipment are $400,000 and $350,000, respectively. The loan should be reported as a loan secured by real estate in Schedule RC-C, Part I, item 1.a.(2) … In contrast, if the estimated values of the building and equipment at origination were $340,000 and $410,000, respectively, the loan should not be reported as a loan secured by real estate. Instead, the loan should be reported in Schedule RC-C, Part I, item 4, "Commercial and industrial loans."

### 1.4 (c) Loans to nondepository financial institutions: RC-C Part I, items 9 and 9.a (pages RC-C-17 and RC-C-18, edition 12-24)

> **9 Loans to nondepository financial institutions and other loans.** Report loans to nondepository financial institutions and loans for purchasing or carrying securities, including margin loans, as described below. Also, include in this item all other loans that cannot properly be reported in one of the preceding items in this schedule.
>
> On the FFIEC 041, all institutions should report in the appropriate subitem of column B loans to nondepository financial institutions (item 9.a) and other loans (item 9.b); institutions with $300 million or more in total assets should also report in the appropriate subitem of column A loans for purchasing or carrying securities, including margin loans (item 9.b.(1)) and all other loans (item 9.b.(2)).
>
> On the FFIEC 031, all institutions should report a breakdown between loans to nondepository financial institutions (item 9.a), loans for purchasing or carrying securities, including margin loans (item 9.b.(1)), and all other loans (item 9.b.(2)) for the fully consolidated bank and for domestic offices in columns A and B, respectively.
>
> **9.a Loans to nondepository financial institutions.** Report loans to nondepository institutions on the FFIEC 031 (columns A and B) and FFIEC 041 (column B), as defined below. For institutions with $10 billion or more in total assets, the amounts reported in this item must equal the sum of Schedule RC-C, Part I, Memorandum items 10.a through 10.e, columns A and B, respectively.
>
> Nondepository financial institutions (NDFIs) encompass a wide range of financial entities that provide services similar to those of traditional banks but do not accept deposits from the general public and are not regulated by the Federal banking agencies. NDFIs include, but are not limited to, mortgage companies, insurance companies, investment funds (such as mutual funds, money market funds, hedge funds, and private capital funds), pension funds, broker-dealers, securitization vehicles, and other financial entities engaged in credit intermediation, asset management, market-making, and other financial services activities.
>
> Include the following loans in this item:
> (1) Loans to mortgage credit intermediaries. … Report in Schedule RC-C, Part I, Memorandum item 10.a, if applicable.
> (2) Loans to business credit intermediaries. Include loans to special purpose entities, finance companies, direct lenders, CDOs, CLOs, private debt funds, leasing companies, ABCP conduits, Business Development Companies (BDCs), Small Business Investment Companies (SBICs), or other financial intermediaries in which the underlying assets are predominately (greater than 50% of assets or lending activities) comprised of loans to businesses. Include CLO tranche holdings that are reported as "loans" in accordance with GAAP. Include loans to other non-bank business lenders, including internet-based lending platforms and other marketplace lenders. Report in Schedule RC-C, Part I, Memorandum item 10.b, if applicable.
> (3) Loans to private equity funds. Include all loans to private equity funds. Include capital call commitment and other subscription-based facilities to private equity and venture capital funds … Report in Schedule RC-C, Part I, Memorandum item 10.c, if applicable.
> (4) Loans to consumer credit intermediaries. … Report in Schedule RC-C, Part I, Memorandum item 10.d, if applicable.
> (5) Other loans to nondepository financial institutions. Other NDFI loans include, but are not limited to, the following (report in Schedule RC-C, Part I, Memorandum item 10.e, if applicable): • Loans to holding companies of other depository institutions. • Loans to insurance companies. • Loans to federally-sponsored lending agencies … • Loans to investment banks and brokers-dealers. Exclude loans that meet the definition of a "loan secured by real estate" (Report in Schedule RC-C, Part I, item 1) and loans that meet the definition of "loans for purchasing or carrying securities, including margin loans" (Report in Schedule RC-C, Part I, item 9.b and item 9.b.1, as appropriate). • Loans and advances made to the bank's own trust department. • Loans to publicly-listed investment funds … • Loans to private capital funds, including private equity and private debt funds. • Loans to hedge funds. • Loans to pension funds, endowments, family offices and sovereign wealth funds. • Loans to securitization vehicles. • Loans to other investment firms and financial vehicles.
>
> NOTE: Item 9.b is not applicable to institutions filing the FFIEC 031 report form.

**Before the revision** (June 2024 edition, RC-C-19, 9-20; item 9 on RC-C-17, 3-19), verbatim:

> **9.a Loans to nondepository financial institutions.** Report in column B all loans to nondepository financial institutions (on the FFIEC 031, in domestic offices) as described above.

and, from item 9:

> On the FFIEC 031, all banks should report the total amount of these loans for the fully consolidated bank in column A, but with a breakdown between loans to nondepository financial institutions (item 9.a), loans for purchasing or carrying securities (item 9.b.(1)), and all other loans (item 9.b.(2)) for domestic offices in column B.

The old include list had 9 entries: REITs and mortgage companies; holding companies of other depository institutions; insurance companies; finance companies, factors and other financial intermediaries; federally-sponsored lending agencies; investment banks; the bank's own trust department; other financial intermediaries lending for business purposes; SBICs.

**What the data show** (CDR bulk, §2): `RCFDJ454` (consolidated NDFI on the 031) is **absent at 2024-09-30 and present from 2024-12-31**. `RCONJ454` (domestic offices) is present from 2010-03-31. The MDRM agrees: `RCFDJ454` FFIEC 031 starts 12/31/2024, and `RCONJ454` starts 3/31/2010. For KeyBank, `RCONJ454` was 789,720 at 2010Q1, 5,393,235 at 2024Q3 and 17,505,184 at 2024Q4; `RCFDJ454` was 21,354,472 at 2026Q2.

### 1.5 (d) Where PPP loans are reported

**COULD NOT find an instruction that names the RC-C line for PPP loans.** Six documents were searched:

- Current RC-C, RC-N, RC-L, General Instructions and Glossary: no occurrence of "PPP" or "Paycheck".
- Current supplemental (Sept 2026, `https://www.fdic.gov/supplemental-instructions-clean.pdf-2`) and Dec 2024 supplemental (`https://www.fdic.gov/system/files/2024-12/1224supplemental-instructions-final.pdf`): no occurrence.
- **June 2020 COVID-19 Related Supplemental Instructions**, section "5. Interim Final Rule for Paycheck Protection Program Liquidity Facility (PPPLF) and Paycheck Protection Program (PPP) Loans", printed page 13 (`https://archive.fdic.gov/view/fdic/10099/fdic_10099_DS3.pdf`), verbatim:

> Consistent with U.S. GAAP, the agencies would expect banking organizations to report PPP covered loans on their balance sheets. Starting with the June 30, 2020, report date, institutions would include the outstanding balances of their PPP covered loans held for investment or held for sale in the appropriate loan category in Schedule RC-C, Part I, and, as applicable, in other Call Report schedules in which loan data are reported. PPP covered loans not held for trading that are pledged to the PPPLF would be reported in Schedule RC-C, Part I, Memorandum item 14, "Pledged loans and leases." Any PPP covered loans held for trading would be reported by all institutions on the Call Report balance sheet in Schedule RC, item 5 …

- **RC-M Memorandum item 17** (page RC-M-19, edition 12-25), verbatim:

> **17.b Outstanding balance of PPP loans.** Report the aggregate amount at which PPP loans held for investment and held for sale are included in Schedule RC-C, Part I, and PPP loans held for trading are included in Schedule RC, item 5, as of the report date.
>
> Items 17.a through 17.e should be completed on a fully consolidated basis.

So the instructions place PPP loans "in the appropriate loan category". The fact that this means C&I for a loan to a business is a **reading**, not a quotation. It rests on RC-C item 4's include list item "(3) Loans to business enterprises guaranteed by the Small Business Administration (SBA)" and on PPP loans being SBA-guaranteed ("PPP covered loans … are fully guaranteed as to principal and accrued interest by the U.S. Small Business Administration (SBA)", RC-M item 17). The instructions do not say "item 4" for PPP. **The PPP balance itself is separately reported:** `RCONLG27`, "Outstanding balance of PPP loans", FFIEC 031 and 041, from 6/30/2020 (MDRM). KeyBank reported 1,861 at 2026-06-30 (facsimile, RC-M 17.b).

### 1.6 (e) RC-L item 1.e.(1): C&I unused commitments (page RC-L-2c, edition 12-24)

> **1.e Other unused commitments.** Report in the appropriate subitem the unused portion of all commercial and industrial loan commitments, commitments for loans to financial institutions, and all other commitments not reportable in Schedule RC-L, items 1.a through 1.d., above. Include commitments to extend credit through overdraft facilities or commercial lines of credit, retail check credit and related plans, and those overdraft protection programs in which the bank advises account holders of the available amount of protection.
>
> **1.e.(1) Commercial and industrial loans.** Report the unused portions of commitments to extend credit for commercial and industrial purposes, i.e., commitments that, when funded, would be reportable as commercial and industrial loans in Schedule RC-C, part I, item 4, "Commercial and industrial loans." Exclude unused credit card lines to commercial and industrial enterprises (report in Schedule RC-L, item 1.b, and, if applicable, item 1.b.(2), above).
>
> **1.e.(2) Loans to depository financial institutions.** Report the unused portions of commitments to extend credit to depository financial institutions, i.e., commitments that, when funded, would be reportable as loans in Schedule RC-C, Part I, item 2, …
>
> **1.e.(3) Loans to nondepository financial institutions.** Report the unused portions of commitments to extend credit to nondepository financial institutions, i.e., commitments that, when funded, would be reportable as loans in Schedule RC-C, Part I, item 9.a, "Loans to nondepository financial institutions." For banks with $10 billion or more in total assets, this item must equal Schedule RC-L, sum of items 1.e.(3)(a) through 1.e.(3)(e), below.
>
> NOTE: Items 1.e.(3)(a) through 1.e.(3)(e) are to be completed by banks with $10 billion or more in total assets.

1.e.(3)(e) and 1.e.(4) "All other unused commitments" are on RC-L-2d (12-24).

### 1.7 (f) RC-N Memorandum item 9 (page RC-N-15, edition 12-24)

> **9 Loans to nondepository financial institutions included in Schedule RC-N, item 7.** Report in the appropriate column the amount of all loans to nondepository financial institutions included in Schedule RC-C, Part I, item 9.a, that are past due 30 days or more or are in nonaccrual status as of the report date. Such loans will have been included in Schedule RC-N, item 7.

And the item it sits inside, RC-N item 7 (page RC-N-8, edition 3-17):

> **7 All other loans.** Report in the appropriate column the amount of all:
> • obligations (other than securities and leases) of states and political subdivisions in the U.S. included in Schedule RC-C, part I, item 8;
> • loans to nondepository financial institutions and other loans included in Schedule RC-C, part I, item 9; and
> • on the FFIEC 041 only, all loans to finance agricultural production and other loans to farmers included in Schedule RC-C, part I, item 3,
> that are past due 30 days or more or are in nonaccrual status as of the report date.

Lease split in RC-N (same page), quoted because it limits the lease series to 031 filers:

> NOTE: Items 8.a and 8.b are not applicable to banks filing the FFIEC 041 report form.

### 1.8 (g) Does RI-B have an NDFI charge-off line? **No.**

RI-B Part I, item 7 (page RI-B-4, edition 3-19, unchanged in the 12-24 file):

> **7 All other loans.** On the FFIEC 041, report in columns A and B, as appropriate, loans to depository institutions and acceptances of other banks, loans to finance agricultural production and other loans to farmers, obligations (other than securities and leases) of states and political subdivisions in the U.S., and loans to nondepository financial institutions and other loans (as defined for Schedule RC-C, part I, items 2, 3, 8, and 9) charged-off and recovered. On the FFIEC 031, report in columns A and B, as appropriate, loans to depository institutions and acceptances of other banks, obligations (other than securities and leases) of states and political subdivisions in the U.S. and loans to nondepository financial institutions and other loans (as defined for Schedule RC-C, part I, items 2, 8, and 9) charged-off and recovered.

Three independent checks agree:

1. **Instruction text.** In the 12-24 RI-B file, "nondepository" appears only in item 7 (the grep of `media_177696` found no other hit).
2. **Bulk file.** The 2026-06-30 RI-B Part I file (`FFIEC CDR Call Schedule RIBI 06302026.txt`) has 52 columns. None is NDFI-specific. The "all other" columns are `RIAD4644` "CHG-OFFS ON ALL OTHER LOANS" and `RIAD4628` "RECOV ON ALL OTHER LOANS".
3. **MDRM.** No FFIEC 031 or 041 item named "nondepository" has an `RIAD` mnemonic. Every one is `RCFD`/`RCON` (RC-C, RC-L, RC-N).

KeyBank's filed report (facsimile): "7. All other loans … RIAD4644 38,469 RIAD4628 14,321 7." (YTD, 2026-06-30).

**Consequence for the proposal:** an NDFI charge-off rate cannot be computed from the Call Report. The proposal's statement that the API carries NDFI "balance only" stays true at the form level for charge-offs. Past due and nonaccrual (RC-N Memo 9) do exist on the form from 2024Q4.

### 1.9 Who files the 031: General Instructions (pages 1–2, editions 9-23)

> (1) BANKS WITH FOREIGN OFFICES: Banks of any size that have any "foreign" offices (as defined below) must file quarterly the Consolidated Reports of Condition and Income for a Bank with Domestic and Foreign Offices (FFIEC 031). …
> (2) BANKS WITHOUT FOREIGN OFFICES: Banks that have domestic offices only must file quarterly: (a) … (FFIEC 031) if the bank: (i) Is an advanced approaches institutions for regulatory capital purposes, regardless of asset size; or (ii) Has total consolidated assets of $100 billion or more, including a bank of this size that is subject to Category III capital standards; (b) … (FFIEC 041) if the bank has total consolidated assets less than $100 billion …
>
> ¹ The $100 billion asset-size test is based on the total assets reported as of June 30 each year to determine whether the institution must file the FFIEC 031 report form beginning in March of the following year.

---

## 2. The FFIEC bulk Call Report data

### 2.1 Reaching it

`https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx` answers 200 to a script, unlike www.ffiec.gov. The page is an ASP.NET form. The script GETs it, then POSTs `ListBox1=ReportingSeriesSinglePeriod`, then picks the date and `FormatType=TSVRadioButton`, then POSTs `TabStrip1$Download_0`. The date list offers **102 quarters, 03/31/2001 to 06/30/2026**. Script: `research-scripts/ffiec/cdr_bulk.py` (and `cdr_bulk_date.py`).

Downloaded (`FFIEC CDR Call Bulk All Schedules <MMDDYYYY>.zip`):

| Quarter | SHA-256 |
|---|---|
| 2026-06-30 | `1ca075adb6b197421ff333d4348e62f3175ab021898676cd63a786d3cf668c43` (48 files; Readme says "as of 2026-10-15T04:30:03") |
| 2024-12-31 | `8b48f584c7bfef543bd8144db815bc5a67b6f46604c9f84b24846801682f8844` |
| 2024-09-30 | `f55efee0eb34c6e288fbe585789926f2f4b7cc69d28accc8b7243ddffd1f54ee` |
| 2010-03-31 | `589f9c3df9e2ec5938a7360426fb6446d2fce134bdac80d0ac337b379a2bcc4a` |
| 2009-12-31 | `244954f93918211574a4b6ff9904a1e564c2ee571bea67cb610abe4a21df352f` |
| 2007-03-31 | `258a9474d0e45ba0ef3f0237c9cb6e3e37b48c955d796a04520ceef34e78ef27` |
| 2006-12-31 | `e583a7a3cc673aab39ddbe5d3bc329f7925e58afa3666c23e8b4292dd7428ffd` |

Format: one tab-separated file per schedule. Row 1 holds the MDRM codes (`IDRSSD`, then `RCFD…`/`RCON…`/`RIAD…`), and row 2 holds a 36-character caption. `RCFD` = consolidated (031 filers); `RCON` = domestic offices (041/051 filers report here).

**Denominator, 2026-06-30:** the POR file lists **4,297** filers: **80** FFIEC 031, **935** FFIEC 041 and **3,282** FFIEC 051. The schedule files together hold 4,312 distinct `IDRSSD` values. The 15-row difference was not investigated.

### 2.2 MDRM codes and start dates

Dictionary: Federal Reserve MDRM, `https://www.federalreserve.gov/apps/mdrm/pdf/MDRM.zip` (download page `https://www.federalreserve.gov/apps/mdrm/download_mdrm.htm`). It reached by script (200), with zip SHA-256 `f13df53364fba07f7d00e4b0d4167f8a943319ad446ff38c1444deec79f78e1d` and `MDRM_CSV.csv` stamped 2026-10-16. **Data check:** "Column first appears" was read from the downloaded bulk files. It brackets each start date between two downloaded quarters.

| Item | Form line | MDRM (031 / 041) | MDRM start – end | Column first appears in bulk (checked) |
|---|---|---|---|---|
| C&I unused commitments | RC-L 1.e.(1) | `RCFDJ457` / `RCONJ457` | 3/31/2010 – open (also FFIEC 051 from 3/31/2017) | absent 2009-12-31, present 2010-03-31 |
| (old) Financial institution commitments | RC-L 1.e.(2) before Dec 2024 | `RCFDJ458` / `RCONJ458` | 3/31/2010 – **9/30/2024** (RCFD on 031; RCON on 041/051). **MDRM inconsistency:** `RCONJ458` on FFIEC 031 shows end 12/31/9999, but neither J458 column is in the 2024-12-31 bulk file | present 2010-03-31 and 2024-09-30; absent 2024-12-31 |
| Depository FI commitments | RC-L 1.e.(2) | `RCFDPV10` / `RCONPV10` | 12/31/2024 – open | present 2024-12-31 (not tested) |
| NDFI commitments | RC-L 1.e.(3) | `RCFDPV11` / `RCONPV11` | 12/31/2024 – open | absent 2024-09-30, present 2024-12-31 |
| NDFI commitments, 5-way split | RC-L 1.e.(3)(a)–(e) | `PV12`–`PV16` | 12/31/2024 – open | present 2026-06-30 |
| NDFI past due 30–89 | RC-N Memo 9, col A | `RCFDPV23` / `RCONPV23` | 12/31/2024 – open (also 051) | absent 2024-09-30, present 2024-12-31 |
| NDFI past due 90+ | RC-N Memo 9, col B | `RCFDPV24` / `RCONPV24` | 12/31/2024 – open | same |
| NDFI nonaccrual | RC-N Memo 9, col C | `RCFDPV25` / `RCONPV25` | 12/31/2024 – open | same |
| Consumer leases (balance) | RC-C 10.a | `RCFDF162` / `RCONF162` | 3/31/2007 – open | absent 2006-12-31, present 2007-03-31 |
| All other leases (balance) | RC-C 10.b | `RCFDF163` / `RCONF163` | 3/31/2007 – open | absent 2006-12-31, present 2007-03-31 |
| Consumer leases past due/nonaccrual | RC-N 8.a (031 only) | `RCFDF166`/`F167`/`F168` | 3/31/2007 – open | not tested separately |
| Other leases past due/nonaccrual | RC-N 8.b (031 only) | `RCFDF169`/`F170`/`F171` | 3/31/2007 – open | not tested separately |
| Lease charge-offs / recoveries split | RI-B I 8.a / 8.b | `RIADF185`/`RIADF187`; `RIADC880`/`RIADF188` | 3/31/2007 – open. MDRM also lists `F185`/`F187`/`F188` on FFIEC 041 with Confidentiality **Y**, although the instructions say 8.a/8.b do not apply to the 041; not resolved | — |
| NDFI loans (consolidated) | RC-C 9.a, col A | `RCFDJ454` | 12/31/2024 – open | absent 2024-09-30, present 2024-12-31 |
| NDFI loans (domestic) | RC-C 9.a, col B | `RCONJ454` | 3/31/2010 – open | present 2010-03-31 |
| NDFI loans, 5-way split | RC-C Memo 10.a–e | `PV05`–`PV09` | 12/31/2024 – open | present 2024-12-31 |
| Charge-offs / recoveries, all other loans (contains NDFI) | RI-B I 7 | `RIAD4644` / `RIAD4628` | 3/31/1984 (031) – open | — |

**Who reports, 2026-06-30** (filers with a value, and with a nonzero value):

| Code | Filers reporting | Nonzero | Sum |
|---|---|---|---|
| `RCFDJ457` | 80 | 59 | 2,497,572,594 |
| `RCONJ457` | 4,217 | 3,796 | 346,808,828 |
| `RCFDPV11` | 80 | 53 | 993,666,289 |
| `RCONPV11` | 4,217 | 426 | 96,162,975 |
| `RCFDPV23` / `PV24` / `PV25` | 80 | 24 / 9 / 26 | 796,869 / 78,006 / 505,246 |
| `RCONPV23` / `PV24` / `PV25` | 4,217 | 13 / 1 / 35 | 29,561 / 265 / 378,086 |
| `RCFDF162` / `RCFDF163` | 80 | 8 / 34 | 13,763,755 / 79,132,374 |
| `RCONF162` / `RCONF163` | **719** | 10 / 194 | 71,694 / 24,903,599 |
| `RCFDJ454` | 80 | 57 | 1,530,447,484 |
| `RCFDPV05` | 50 | 43 | 318,422,784 |

`RCONF162`/`F163` are reported by 719 filers out of 4,217 041 and 051 filers. Which filers are required to report them was not checked.

### 2.3 KeyBank (RSSD **280110**, verified: FDIC institutions endpoint `FED_RSSD` = "280110" for cert 17534, and the facsimile header reads "RSSD-ID 280110 / FDIC Certificate Number 17534 / Report Type 031")

**Obtained.** These are 2026-06-30 values from the bulk file, each checked against KeyBank's filed report. The filed report is the CDR facsimile PDF: `https://cdr.ffiec.gov/public/ViewFacsimileDirect.aspx?ds=call&idType=fdiccert&id=17534&date=06302026`, then `https://cdr.ffiec.gov/public/FacsimileContainer.aspx` in the same session, SHA-256 `d4ca7af089bc70d3d2872e2c214fec08370455d59b747b2429b88bcf6f8c471a`. Its header reads "Report Type 031". **Every value below is identical in both sources.**

| Line | Code | Value |
|---|---|---|
| RC-L 1.e.(1) C&I unused commitments | `RCFDJ457` | 40,550,339 |
| RC-L 1.e.(2) depository FI commitments | `RCFDPV10` | 0 |
| RC-L 1.e.(3) NDFI commitments | `RCFDPV11` | 15,101,045 (= PV12 458,736 + PV13 3,481,029 + PV14 2,176,577 + PV15 203,863 + PV16 8,780,840) |
| RC-L 1.e.(4) all other | `RCFDJ459` | 5,218,378 (facsimile) |
| RC-N Memo 9: NDFI 30–89 / 90+ / nonaccrual | `RCFDPV23` / `PV24` / `PV25` | 3,961 / 20 / 1,830 |
| RC-C 10.a consumer leases | `RCFDF162` | 0 |
| RC-C 10.b all other leases | `RCFDF163` | 1,997,330 |
| RC-N 8.a consumer leases 30–89 / 90+ / nonaccrual | `RCFDF166`/`F167`/`F168` | 0 / 0 / 0 |
| RC-N 8.b other leases 30–89 / 90+ / nonaccrual | `RCFDF169`/`F170`/`F171` | 204 / 1,000 / 5,648 |
| RI-B 8.a consumer lease charge-offs / recoveries (YTD) | `RIADF185` / `RIADF187` | 0 / 0 |
| RI-B 8.b other lease charge-offs / recoveries (YTD) | `RIADC880` / `RIADF188` | 632 / 336 |
| RC-C 9.a NDFI loans | `RCFDJ454` | 21,354,472 (= PV05 680,278 + PV06 9,002,795 + PV07 1,375,681 + PV08 102,176 + PV09 10,193,542) |
| RI-B 7 all other loans, charge-offs / recoveries (YTD) | `RIAD4644` / `RIAD4628` | 38,469 / 14,321 |
| RC-M 17.b PPP balance | `RCONLG27` | 1,861 |

**Tie to the FDIC API** (`https://api.fdic.gov/banks/financials?filters=CERT:17534%20AND%20REPDTE:20260630&fields=CERT,REPDTE,LNCI,LNNDEPC,LS,UC,NACI,P3CI,DRCI,NTCI&limit=5&format=json`):
- `LNCI` 37,374,689 = `RCFD1763` 36,979,972 + `RCFD1764` 394,717.
- `LNNDEPC` 21,354,472 = `RCFDJ454`.
- `LS` 1,997,330 = `F162` + `F163`.
- `DRCI` 126,668 = `RIAD4645` 126,668 + `RIAD4646` 0 (facsimile).

**KeyBank history at the break quarters** (bulk):
- `RCFDJ457` was 17,947,063 at 2010Q1; 38,101,084 at 2024Q3; 37,155,122 at 2024Q4.
- `RCFDJ458` was 1,168,938 at 2010Q1 and 7,562,381 at 2024Q3; it was gone at 2024Q4.
- At 2024Q4: `RCFDPV11` 12,258,755; `PV23`/`PV24`/`PV25` 0 / 0 / 128.
- `RCFDF163` was 10,013,688 at 2007Q1.

Other quarters were not pulled, but all 102 are offered by the same script.

### 2.4 The roster at 2026-06-30 (bulk; `RCFD` for 031 filers, `RCON` for Zions)

| Cert | Bank | RSSD | J457 C&I unused | PV11 NDFI unused | PV23 | PV24 | PV25 | F162 | F163 | J454 NDFI loans |
|---|---|---|---|---|---|---|---|---|---|---|
| 628 | JPMorgan | 852218 | 378,560,000 | 112,936,000 | 343,000 | 5,000 | 10,000 | 0 | 105,000 | 248,070,000 |
| 3511 | Wells Fargo | 451965 | 247,494,000 | 126,874,000 | 9,000 | 1,000 | 136,000 | 0 | 15,681,000 | 229,843,000 |
| 3510 | Bank of America | 480228 | 419,643,000 | 122,267,000 | 2,000 | 0 | 18,000 | 7,315,000 | 16,148,000 | 206,412,000 |
| 7213 | Citi | 476810 | 232,781,000 | 88,135,000 | 58,000 | 8,000 | 43,000 | 0 | 72,000 | 134,962,000 |
| 6548 | U.S. Bank | 504713 | 129,291,158 | 45,111,771 | 12,662 | 267 | 217 | 4,087,388 | 4,495,283 | 52,128,423 |
| 6384 | PNC | 817824 | 160,777,825 | 59,514,020 | 108 | 20 | 895 | 0 | 7,115,484 | 75,189,627 |
| 9846 | Truist | 852320 | 113,418,000 | 37,319,000 | 11,000 | 0 | 4,000 | 0 | 1,132,000 | 41,490,000 |
| 4297 | Capital One | 112837 | 29,471,000 | 25,279,000 | 72,000 | 0 | 0 | 0 | 0 | 39,155,000 |
| 17534 | KeyBank | 280110 | 40,550,339 | 15,101,045 | 3,961 | 20 | 1,830 | 0 | 1,997,330 | 21,354,472 |
| 6672 | Fifth Third | 723112 | 60,659,000 | 13,388,000 | 10,000 | 0 | 19,000 | 0 | 3,419,000 | 13,197,000 |
| 6560 | Huntington | 12311 | 33,593,253 | 16,465,061 | 2,440 | 0 | 21,625 | 0 | 5,712,939 | 17,511,739 |
| 11063 | First Citizens | 491224 | 18,682,000 | 16,783,000 | 37,000 | 0 | 25,000 | 0 | 1,959,000 | 41,427,000 |
| 57957 | Citizens | 3303298 | 36,622,533 | 22,475,130 | 0 | 0 | 130 | 0 | 1,059,923 | 21,993,287 |
| 588 | M&T | 501105 | 21,333,000 | 11,899,000 | 52,000 | 0 | 7,000 | 0 | 2,785,000 | 13,681,000 |
| 12368 | Regions | 233031 | 29,146,000 | 14,834,000 | 5,000 | 0 | 23,000 | 0 | 1,329,000 | 12,488,000 |
| 2270 | Zions (041) | 276579 | 9,911,032 | 1,601,534 | 0 | 0 | 9,459 | 0 | 352,128 | 2,517,907 |

16 of 16 roster banks have every column. RSSD IDs come from the FDIC institutions endpoint `FED_RSSD`: `https://api.fdic.gov/banks/institutions?filters=CERT:(628 OR … OR 2270)&fields=CERT,NAME,FED_RSSD,RSSDHCR,ACTIVE&limit=100&format=json`. Each RSSD matched a POR row with the same FDIC certificate number.

---

## 3. Which form each roster bank files at 2026-06-30

**The FDIC field** is `CALLFORM`. In `risview_properties.yaml` its description is "TBD". The full definition is in `https://api.fdic.gov/banks/docs/All%20Financial%20Reports.xlsx`, sheet `Reference-Variables&Definitions`, verbatim:

> CALLFORM — Regulatory reporting form number (FFIEC Call report number or before 2012 100 indicates FHLB TFR reporter) — The type of financial report filed by an institution to the regulators. Thrift Financial Report Filers: 100 - Savings institution Thrift Financial Report or TFR filer (3/1984 - 12/2011) FFIEC Call Report Filers: 002 – International Banking Act Institution (6/1980-present) 031 – Banks with domestic and foreign offices (3/1984 - present) 032 - … (3/1984 - 12/2000) 033 - … 034 - … 041 - Banks with domestic offices only (3/2001 - present) 051 - Banks with domestic offices only and total assets less than $5 billion (9/2019 - present). …

The API returns it as a number (31, 41). Query:
`https://api.fdic.gov/banks/financials?filters=REPDTE:20260630%20AND%20CERT:(628%20OR%203511%20OR%203510%20OR%207213%20OR%206548%20OR%206384%20OR%209846%20OR%204297%20OR%2017534%20OR%206672%20OR%206560%20OR%2011063%20OR%2057957%20OR%20588%20OR%2012368%20OR%202270)&fields=CERT,REPDTE,CALLFORM,ASSET,NAMEFULL&limit=100&format=json` (16 rows returned of 16).

**Second source:** the CDR bulk POR file's "Financial Institution Filing Type" for 2026-06-30. **It agrees on all 16.**

| Cert | Bank | FDIC `CALLFORM` | CDR filing type | Assets ($000) | CALLFORM history 1984Q1–2026Q2 (FDIC, every quarter) |
|---|---|---|---|---|---|
| 628 | JPMorgan | 31 | 031 | 4,091,315,000 | 031 throughout |
| 3511 | Wells Fargo | 31 | 031 | 1,907,928,000 | 031 throughout |
| 3510 | Bank of America | 31 | 031 | 2,654,645,000 | 031 throughout |
| 7213 | Citi | 31 | 031 | 1,976,180,000 | 031 throughout |
| 6548 | U.S. Bank | 31 | 031 | 705,554,946 | 031; 032 from 1987Q1; 031 from 1994Q3 |
| 6384 | PNC | 31 | 031 | 609,771,726 | 031 throughout |
| 9846 | Truist | 31 | 031 | 548,346,000 | 032; 031 from 1988Q2 |
| 4297 | Capital One | 31 | 031 | 662,157,000 | 031 throughout |
| **17534** | **KeyBank** | **31** | **031** | 188,555,486 | **031 throughout** |
| 6672 | Fifth Third | 31 | 031 | 299,177,000 | 033; 032 from 1989Q4; 031 from 2000Q4 |
| 6560 | Huntington | 31 | 031 | 283,073,605 | 031; **041 for 2018Q1–2018Q2**; 031 from 2018Q3 |
| 11063 | First Citizens | 31 | 031 | 236,317,000 | 032; 041 from 2001Q1; **031 from 2022Q1** |
| 57957 | Citizens | 31 | 031 | 232,517,438 | 041 from 2005Q2 (first quarter on file); 031 from 2006Q1 |
| 588 | M&T | 31 | 031 | 218,788,000 | 031 throughout |
| 12368 | Regions | 31 | 031 | 159,787,000 | 032; 031 from 1994Q2 |
| **2270** | **Zions** | **41** | **041** | 89,041,284 | 031; 041 2015Q1–2015Q3; 031 2015Q4–2016Q4; **041 from 2017Q1** |

History query: `https://api.fdic.gov/banks/financials?filters=CERT:(…16 certs…)&fields=CERT,REPDTE,CALLFORM,ASSET&sort_by=REPDTE&sort_order=ASC&limit=10000&format=json`. It returned 2,635 rows: 170 quarters for each of 15 banks, and 85 for Citizens.

**What this settles in the proposal:**
- §6 item 12: **KeyBank files the FFIEC 031 at 2026Q2, and in every quarter since 1984Q1** (FDIC `CALLFORM`). The C&I tie-out uses the 031 lines: RC-C 4.a/4.b `RCFD1763`/`RCFD1764`, and RC-N `RCFD1251`–`1256`.
- The 2018Q2 note ("Which roster banks switched: not checked"): no roster bank moved to the 031 in 2018. Huntington filed the 041 for 2018Q1–Q2 only and the 031 otherwise. First Citizens moved to the 031 at 2022Q1. Zions is the only 041 filer. **The resolver must still handle the 041 for Zions**, which reports `RCON1766` for C&I with no U.S./non-U.S. split in column B.

---

## 4. Not checked / COULD NOT

1. **ffiec.gov directly: COULD NOT** (403 by curl with a browser User-Agent, and 403 by WebFetch). This was worked around through the FDIC's hosted copies of the same FFIEC instruction book.
2. **Wayback Machine download: COULD NOT** (16 resets at the egress proxy). Only the availability API answered. Not needed after the FDIC route.
3. **An instruction naming the RC-C line for PPP loans: COULD NOT find one** in six documents (§1.5). The C&I reading is marked as a reading.
4. Edition history **before June 2024** for these schedules was not compiled. The FDIC previous-quarter pages go back to at least 2020 and are reachable.
5. The text of the footnote marker "1" printed beside RC-L 1.e.(3) and 1.e.(3)(a) on KeyBank's facsimile was not read.
6. The MDRM end date for `RCONJ458` on the FFIEC 031 (12/31/9999) contradicts the bulk data (column gone at 2024-12-31). It is recorded, not resolved.
7. Why only 719 041/051 filers report `RCONF162`/`F163`, and why the MDRM lists `RIADF185`/`F187`/`F188` on the 041 (confidential) when the instructions say RI-B 8.a/8.b do not apply to the 041: not checked.
8. 4,312 distinct IDRSSD across the 2026-06-30 schedule files against 4,297 POR rows: the difference was not investigated.
9. RC-L and RI-B PDFs from `/media/177656` and `/media/177696` were not hashed. Their page-footer editions are recorded in §1.2.
10. Bulk quarters other than the seven listed were not downloaded. Series values between them, such as a KeyBank `J457` history, were not built.
