# Commercial loan categories, 2006–2026: reporting breaks and acquisitions for the 15-peer + KeyBank roster

Research done 16 Oct 2026, read-only. Nothing in the repository was changed.
Roster used: `book/threshold-engine/config/peers.json`, which has 16 certificates: 15 peers plus KeyBank (17534, "self").

**Verified** means I read the date or fact in the primary source named in that row.
**NOT CHECKED** means I did not see it in a primary source. Such items are leads, not facts.
"Data" means I read it from FDIC BankFind Call Report figures I pulled myself: `api.fdic.gov/banks/financials`, pulled 16 Oct 2026.

Working files (Federal Register texts, FDIC history and loan data, SEC search results) were not kept:

- `fr/txt/`: 192 Federal Register notices, from govinfo.gov
- `fdic/history.json`: FDIC structure history for the 16 certificates
- `fdic/sizes_table.txt`: each target's commercial book against its acquirer's
- `fdic/panel.json` and `fdic/jumps.tsv`: commercial balances 2005Q4–2026Q2, and every quarter-on-quarter move over 25%
- `sec/`: EDGAR results
- `docs/`: the FDIC, Federal Reserve and FFIEC documents used

---

## 0. How the repository's merger record works (what "already recorded" means)

- **Where it comes from.** `src/threshold_engine/peers/fdic.py` pulls the FDIC history API, `api.fdic.gov/banks/history`, for every filer. It starts from `--mergers 2005-01-01`.
- **Which rows count.** Only rows whose change code is on the allowlist `ACQUISITIONS` count: codes 211, 215, 216, 217, 221, 222, 223 and 224.
  - Code **712 (branch purchase)** is explicitly *not* an acquisition (`NOT_AN_ACQUISITION`).
  - A row that names no acquirer certificate (`ACQ_CERT`) is never seen.
- **What is written.** `absorptions()` writes `absorptions.json`: who absorbed whom, and the quarter-end of the effective date.
- **Pro forma combination.** `books.combination()` walks the absorption chain and adds each absorbed bank's own filings up to its merger quarter.
  - Example: SVB → DINB of Santa Clara → Silicon Valley Bridge Bank → First Citizens. Codes 211, 221 and 216 are all allowlisted, so SVB's filings through 2022Q4 are added to First Citizens.
- **The 25% jump rule.** `books.bank_book(jump=...)` leaves out any four-quarter window in which a quarter-end balance moved more than the jump, measured from i-4 to i. With 0.25 that is 25%. LOG, 7 Oct 2026, says it stands for "merger, sale, reclassification".
- **The 5% acquisition-share rule.** `acquired_quarters(share=0.05)` (LOG, 14 Oct 2026) adds up the recorded absorptions in a quarter, measures them against the acquirer's book of that product, and leaves out the four windows that hold that quarter.
- **The fixture matches the live record.** I re-pulled the history on 16 Oct 2026. It matches `tests/data/peers/mergers_roster.json` exactly for all 16 certificates, from 2006. So every allowlisted deal in table B is "in the repo's merger record".
- **What the record cannot see:** 712 transfers, failures with no acquirer row, and non-bank asset purchases. All three are listed in section C.

---

## A. Reporting and definition changes affecting commercial categories

"Effective" is the first Call Report date the change applies to. Federal Register (FR) notices are cited by volume and page, with the govinfo copy in the source list. In the "Categories" column, RC-C, RC-N, RI-B and RC-L are Call Report schedules, and "1.a", "9.a" and so on are their line numbers.

| Effective quarter | Event | Categories affected | What it does to the series | Source | Verified? | Handling (firm) |
|---|---|---|---|---|---|---|
| **2007Q1** (31 Mar 2007) | RC-C 1.a construction split into 1.a(1) "1-4 family residential construction" and 1.a(2) "other construction and all land development and other land". RC-C 1.e nonfarm nonresidential (NFNR) split into owner-occupied 1.e(1) and other 1.e(2). The same splits apply in **RC-N and RI-B**. RC-L 1.c(1) commitments are split the same way. Lease addressee detail (U.S./non-U.S.) is replaced by **retail (consumer) vs commercial leases** in RC-C 10, RC-N and RI-B. | Construction, NFNR, leases, RC-L | Totals are continuous. **The sub-series start in 2007Q1:** 1-4 family vs other construction (FDIC fields LNRECNFM/LNRECNOT), owner-occupied vs other NFNR (LNRENROW/LNRENROT), and commercial leases. For existing loans, banks could classify owner-occupied "when the loan was acquired or based on the most recent available information". | 71 FR 8649 (17 Feb 2006), "Call Report Revisions To Be Implemented March 31, 2007 (and 2008)". The 31 Mar 2007 date applies to banks with $300m or more in assets or with foreign offices, which covers all 16. | **Verified** | |
| **2008Q1** (March 2008) | Instructional guidance on when loans may be classified as **trading**. Loans so classified are excluded from RC-C and reported in RC-D. | All RC-C loan categories; syndicated C&I most likely | Loans a bank designates as trading leave RC-C. This could drop a bank's C&I or other categories with no credit event. | 76 FR 5253 (28 Jan 2011), §G.1: "In March 2008, the banking agencies provided instructional guidance … loans classified as trading assets should be excluded from Schedule RC-C". The original March 2008 guidance was not read. | **Verified** (as described in the 2011 notice) | |
| **2009Q1** (31 Mar 2009) | **"Loan secured by real estate" clarified.** The real estate collateral must be worth more than 50% of principal at origination. Applied **prospectively**: no reclassification of loans already reported. | Real estate categories (construction, multifamily, NFNR, farmland) vs C&I, agricultural, other | A slow drift, not a step: new loans with 50% or less real estate collateral go to C&I or other. | Proposed 73 FR 54807 (23 Sep 2008) §C. Final 74 FR 5028 (28 Jan 2009) §II.B, "will implement … as proposed" among the "March 31, 2009" revisions. | **Verified** | |
| **2009Q1** | FAS 141(R) business combinations: acquired loans are carried at fair value with no carried-over allowance. The agencies **declined** to add Call Report items for these loans. | All categories at acquirers | After 2009, charge-offs on acquired books in the first quarters after a deal understate what the target would have reported. `books.combined_flows` already says this. | 74 FR 5028 §II.A | **Verified** (accounting change and the agencies' decision). The effect on charge-offs is inference. | |
| **2010Q1** (1 Jan 2010) | **FAS 166/167**: securitization trusts and variable interest entities consolidated. | Mostly consumer | FDIC QBP 2010Q1: more than $300bn of securitized card receivables consolidated; other consumer +$28.0bn. "**Most non-consumer loan categories were not affected by the new accounting rules.**" Industry C&I fell $33.1bn that quarter, construction fell $33.1bn and NFNR fell $891m: declines, not consolidation steps. Bank-level asset-backed commercial paper conduit consolidations were not checked. | FDIC QBP Q1 2010 (fdic.gov …/qbp/2010mar/qbp.pdf). Background in 74 FR 41973 §III.A. | **Verified** (industry level). Bank level NOT CHECKED. | |
| **2010Q1** (31 Mar 2010) | **Loans to nondepository financial institutions (NDFIs) become a separate RC-C item, 9.a**, broken out of item 9 "Other loans", which keeps 9.b. RC-L 1.e "other unused commitments" split into 1.e(1) C&I, 1.e(2) loans to financial institutions (depository and nondepository together) and 1.e(3) all other. RC-L 1.b card lines split consumer/other. The definition of unused commitments was clarified, including "commitments to issue a commitment" and how to measure asset-based lending lines. | NDFI, all other loans, RC-L | NDFI exists **only from 2010Q1**. Before that it sits inside "other loans" (item 9); the FDIC field LNOTHER is the 9.a + 9.b sum and runs across the split. RC-L commercial detail starts in 2010Q1, and the commitments definition steps in 2010Q1. The 2008 proposal for that clarification was deferred in 74 FR 5028 and implemented now. | 74 FR 68314 (23 Dec 2009) §II.A–B ("as proposed, the Call Report changes would take effect as of March 31, 2010"). 88 FR 89489 confirms "Since this item was added in 2010… In March 2010, loans to NDFIs … approximately $56 billion". FDIC Banking Issues in Focus Feb 2026: "added to the Call Report in first quarter 2010". | **Verified** | |
| **2011Q1** (31 Mar 2011) | **Construction loan instruction clarified.** A construction loan not written as a combination construction-permanent loan stays in 1.a after construction is complete, as long as repayment still depends on sale of the property. Also: troubled debt restructuring (TDR) memoranda broken out by category, including C&I and owner-occupied/other NFNR, and auto split from consumer. | Construction vs NFNR/multifamily; RC-C/RC-N TDR memoranda | Possible migration between construction and permanent real estate categories at 2011Q1 for banks that had been moving such loans out. | Proposed 75 FR 60497 (30 Sep 2010) §L.1. Final 76 FR 5253 (28 Jan 2011): "Instructional revisions that address the reporting of construction loans following the completion of construction"; overview gives March 31, 2011. | **Verified** | |
| **2013Q2** (30 Jun 2013) | FFIEC 031: "large and highly complex institutions" (a deposit-insurance category for the biggest banks) begin reporting the **nine-category real estate breakdown for the consolidated bank** (column A) in RC-C 1. Before this, form 031 filers gave the breakdown for domestic offices only. | Construction, multifamily, NFNR, farmland at the largest 031 filers | Possible definitional step in the real estate sub-categories, domestic → consolidated, at the largest peers. **Whether the FDIC fields LNRECONS, LNREMULT and LNRENRES are domestic or consolidated was NOT CHECKED.** The FDIC API also carries LNREDOM and LNREFOR. | 78 FR 30922 (23 May 2013): "the reporting changes for large and highly complex institutions … effective date … June 30, 2013". The RC-O foreign-office items were optional at 30 Jun and required from 30 Sep 2013. | **Verified** (form change). Effect on FDIC fields NOT CHECKED. | |
| **2018Q2** (30 Jun 2018) | Scope: every institution with $100bn or more in consolidated assets files **FFIEC 031** whether or not it has foreign offices. | Field availability | A bank switching from form 041 to 031 gains a domestic/consolidated split. Domestic-only FDIC fields could change meaning for it. Which roster banks switched: NOT CHECKED. | 83 FR 939 (8 Jan 2018): "the agencies will delay the effective date of these reporting revisions and scope revision until the June 30, 2018, report date". | **Verified** (rule). Bank list NOT CHECKED. | |
| **2019Q1** (1 Jan 2019, public business entities) | **ASC 842, leases.** The notice describes the change as "most significant … to lessee accounting". The Call Report changes concern lessee liabilities: other borrowings vs other liabilities. | Leases (lessor) | No RC-C lease-item change found in the notices. Any lessor effect: NOT CHECKED. | 84 FR 53227 (4 Oct 2019) §H | **Verified** (scope as described). Lessor effect NOT CHECKED. | |
| **2020Q1** (1 Jan 2020, SEC filers) | **CECL, ASC 326.** Purchased credit-impaired (PCI) loans become purchased credit-deteriorated (PCD) loans, carried at purchase price plus allowance. **The PCI nonaccrual exception was not extended to PCD loans.** A later revision let banks elect to keep accruing PCD loans that meet set criteria, with past-due status judged by contractual terms loan by loan. | Nonaccrual and past due, all categories; balances of acquired PCD books | Possible step-up in nonaccrual and past-due for banks with big PCI books at adoption, unless they elected to keep accruing. PCD balances are grossed up by the allowance. | 84 FR 4131 (14 Feb 2019) (effective dates, PCD description, nonaccrual policies unchanged). 85 FR 44361 (22 Jul 2020) §C.3, citing the March 2020 Supplemental Instructions. | **Verified** (rules). Bank-level effect NOT CHECKED. | |
| **2020Q1** | Revolving-credit drawdowns. Not a definition change. | C&I | FDIC QBP Q1 2020: "C&I loan portfolio increased by $339.4 billion (15.4 percent) … Unfunded C&I loan commitments declined by $269 billion". In the data: JPMorgan C&I +31%, U.S. Bank C&I +27%. **This trips the 25% jump.** | FDIC QBP Q1 2020 | **Verified** (industry). Bank moves are data. | |
| **2020Q2** onward | **CARES Act §4013 and the April 2020 interagency statement.** Deferrals granted because of COVID are not reported as past due during the deferral. Eligible modifications are not TDRs. RC-C memoranda 17.a/b (number and balance of §4013 loans) are confidential. | Past due, TDR memoranda, all categories | Past-due rates understated during deferrals, 2020Q1/Q2 onward. | Interagency statement, 7 Apr 2020 (FDIC PR-49-2020): "these loans are not considered past due during the period of the deferral". 85 FR 44361 §B (items from 30 Jun 2020). | **Verified**. End date of §4013 relief NOT CHECKED. | |
| **2020Q2** | **Paycheck Protection Program (PPP) loans.** | C&I | FDIC QBP Q2 2020: C&I rose $146.5bn, "attributable to … PPP, with $482.2 billion in PPP loans". In the data: First Citizens C&I +80%, Zions +37%. **This trips the 25% jump.** The FFIEC instruction placing PPP in C&I was not read (ffiec.gov returned 403). | FDIC QBP Q2 2020 | **Verified** (QBP). Instruction NOT CHECKED. | |
| **2023Q1** accounting; **2024Q2** forms | **ASU 2022-02 ends TDR accounting.** TDR captions replaced by "loan modifications to borrowers experiencing financial difficulty" in the forms and instructions. | RC-C Memo 1, RC-N Memo 1 (memoranda only) | Main loan categories are unaffected. The TDR memoranda are not comparable across the change. | 89 FR 45046 (22 May 2024) §II.B.1: "effective as of the June 30, 2024, report date". The 2023 accounting date is from the ASU and was not separately verified. | **Verified** (forms date) | |
| proposed **2025Q4** | Report only modifications made in the previous 12 months. | Memoranda only | Memo counts fall. | 90 FR 31111 (11 Jul 2025), proposed for 31 Dec 2025. **Final notice not found.** | Proposal verified. Final **NOT CHECKED** | |
| **2024Q4–2025Q2** (31 Dec 2024, best efforts until 30 Jun 2025) | **NDFI and margin-loan revisions.** (1) NDFI definition widened, explicitly including special purpose entities and securitization vehicles. (2) Loans to broker-dealers and to investment companies and mutual funds move from 9.b(1) to **9.a NDFI**. (3) **All purpose and non-purpose securities-based margin loans, any borrower, more than 50% secured by securities with readily determinable fair values, go to 9.b(1)** ("loans for purchasing or carrying securities, including margin loans"). These come **out of C&I (item 4)** and **out of other consumer loans (6.d)**. (4) New RC-C Memo 10 splits NDFI five ways for banks over $10bn. New RC-N Memo 9 gives NDFI past due and nonaccrual. (5) **RC-L 1.e(2) becomes depository institutions only; new 1.e(3) is NDFI (with five sub-items); "all other" becomes 1.e(4).** (6) Loans to foreign banks that act as broker-dealers, made to purchase or carry securities, now go in 9.b(1). | **C&I, NDFI, all other loans, loans to depository institutions, other consumer**, RC-L | **A large step down in C&I and up in NDFI and other loans**, and for some banks a step down in other consumer. It is **spread over three quarters** (2024Q4, 2025Q1, 2025Q2) because banks could report on a best-efforts basis. Industry (FDIC): C&I −$128bn and "All other" −$60bn from 2024Q3 to 2024Q4. Federal Reserve H.8 estimate for domestic banks, week of 1 Jan 2025: **$115.0bn C&I, $41.2bn "credit cards and other revolving plans" and $76.2bn "all other consumer"** reclassified to NDFI ($113.5bn) and to all loans not elsewhere classified ($123.7bn). More followed in the weeks of 2 Apr 2025 ($27.7bn C&I) and 2 Jul 2025 ($50.5bn C&I). See the bank-level moves below. | Proposed 88 FR 89489 (27 Dec 2023) §II.A. Final 89 FR 45046 (22 May 2024) §II.C.1: "the effective date for these new items will be as of the December 31, 2024, report date". FDIC *Banking Issues in Focus* No. 1, Feb 2026 (mechanism, best efforts through 30 Jun 2025 citing FIL-84-2024, industry amounts). Federal Reserve H.8, 26 Sep 2025, Notes on Data. | **Verified**. FIL-84-2024 itself not opened (404); the best-efforts dates are from the FDIC article. | |

**About the "~$56bn out of other revolving credit plans" claim.**

- In the agencies' own notice, **$56bn** is the *level of NDFI loans in March 2010*, when the item was created (88 FR 89491).
- The 2024 reclassification amounts that are published are the H.8 figures above: $41.2bn out of "credit cards and other revolving plans", and more out of "all other consumer" and C&I.
- The FDIC says the **non-purpose margin loans to individuals came out of RC-C 6.d "Other consumer loans"**. It does not mention 6.b.
- Neither source gives a $56bn move out of 6.b. I found no source for that figure.

**Bank-level moves 2024Q3 → 2025Q2 (data, $bn; "OC" = 6.b + 6.d, the repo's Other consumer balance):**

| Bank | Field | 2024Q3 | 2024Q4 | 2025Q1 | 2025Q2 |
|---|---|---|---|---|---|
| Bank of America | OC | 44.4 | **10.2** | 10.2 | 10.0 |
| Bank of America | C&I | 337.1 | 295.4 | 296.7 | 307.1 |
| Bank of America | Other loans (LNOTHER) | 173.9 | 264.3 | 272.6 | 293.2 |
| JPMorgan | OC | 22.7 | 22.6 | **12.5** | 13.0 |
| PNC | OC | 5.7 | **3.7** | 3.6 | 3.6 |
| PNC | C&I | 129.0 | 127.3 | 126.3 | **101.1** |
| PNC | LNOTHER | 28.7 | 29.7 | 36.1 | **69.6** |
| Wells Fargo | OC | 8.3 | 8.9 | 9.2 | **6.7** |
| U.S. Bank | C&I | 98.0 | 94.4 | **83.6** | 84.3 |
| U.S. Bank | LNOTHER | 24.6 | 37.3 | 52.6 | 56.6 |
| **KeyBank** | C&I | 41.9 | **29.9** (−29%) | 31.5 | 33.7 |
| KeyBank | LNOTHER | 7.2 | 19.5 | 19.7 | 19.1 |
| Citizens | C&I | 37.8 | **25.8** (−32%) | 26.1 | 25.9 |
| Citizens | LNOTHER | 2.9 | 13.5 | 14.5 | 16.8 |
| Capital One | C&I | 45.4 | **34.3** | 35.2 | 35.2 |
| Regions | C&I | 30.9 | 27.0 | 26.8 | 27.5 |

**Side effect on the existing consumer build.** The consumer build's Other consumer balance is `LNCONOTH+LNCONRP`. That balance steps down at Bank of America (2024Q4), PNC (2024Q4), JPMorgan (2025Q1) and Wells Fargo (2025Q2). The cause matches the margin-loan move described by the FDIC. That this is the cause at each bank is inference: the timing and mechanism fit, but no bank disclosure was checked.

**Items asked about with nothing found:**

- **Agricultural production loans, farmland, loans to depository institutions (2006–2023).** No definition change found in the 192 FFIEC 031 information-collection notices searched. The only item-2 change found is the Dec 2024 one above. Not proof of absence; marked NOT CHECKED beyond those notices.
- **"Secured by real estate" after 2009, or another C&I/"all other" boundary change.** None found beyond 2010 (the NDFI split, which came out of item 9, not C&I) and Dec 2024.
- **RC-L categories.** Changes found in 2007Q1, 2010Q1 and 2024Q4, all in the table. Nothing else found.

---

## B. Acquisitions putting commercial books into the roster banks (bank-level)

**What the columns mean:**

- **Charter merger** is the FDIC history effective date. That date and its quarter are what the repo uses. All dates come from `api.fdic.gov/banks/history`, pulled 16 Oct 2026; that index was created 9 Oct 2026.
- **Holding-company close** is from the acquirer's SEC 8-K (Item 2.01 unless noted). Between the holding-company close and the charter merger, the target files its own Call Report under the new parent. The repo's `restarted()` handles a year to date that restarts under push-down accounting.
- **Target book** is the target's last Call Report before the merger quarter ($bn): C&I / CRE (construction + multifamily + NFNR), then the share of the acquirer's book the quarter before.
- **In record?** is whether the deal is in `absorptions.json` / `mergers_roster.json`.

| Acquirer (cert) | Target (cert) | Holding-company close (SEC) | Charter merger (FDIC; code) | Quarter | Target book: C&I / CRE ($bn); share of acquirer C&I / CRE | In record? | What it does to the series | Handling (firm) |
|---|---|---|---|---|---|---|---|---|
| Wells Fargo (3511) | Wachovia Bank NA (33869), plus Wachovia Bank of Delaware (33931) | HC close 31 Dec 2008: NOT CHECKED (no 8-K Item 2.01 found) | **2010-03-20** (223) | 2010Q1 | 61.4 / 63.6; **88% / 93%** | Yes | Wachovia filed under the Wells parent through 2009Q4; combining pro forma doubles the book. 2010Q1 also coincides with the FAS 166/167 and NDFI changes. | |
| Wells Fargo | Wachovia Card Services (58496); Wells Fargo HSBC Trade Bank (34075) | — | 2010-04-10; 2010-05-10 (223) | 2010Q2 | 0 / 0; 1.0 / 0.1 | Yes | Small | |
| Wells Fargo | Greater Bay Bank (27068) | NOT CHECKED | 2008-03-15 (223) | 2008Q1 | 1.9 / 2.4; 3% / 5% | Yes | Small | |
| Wells Fargo | **GE Capital commercial lending and leasing (asset purchase, no bank charter)** | Wells 1Q16 release (8-K): "$26.7 billion from commercial and industrial loans and leases (3/1/16 close)"; rail cars $4.1bn (1/1/16) | — (not in FDIC history) | 2016Q1 | Data: Wells leases 11.8 → 18.4 (+56%), C&I 163.2 → 185.4 (+14%) | **No** | Leases trip 25%. **C&I +14% passes the 25% jump, and the 5% acquisition-share rule cannot see it** (no record). | |
| PNC (6384) | National City Bank (6557) | HC close 31 Dec 2008: NOT CHECKED | **2009-11-06** (223) | 2009Q4 | 21.1 / 20.0; **98% / 130%** | Yes | National City filed under the PNC parent in 2009. The repo already handles the 2008Q4 restart of its year to date. | |
| PNC | Mercantile Bankshares' banks (11 charters incl. Mercantile-Safe Deposit 20347) | 8-K: 2 Mar 2007 | 2007-09-14 (223) | 2007Q3 | Mercantile-Safe Deposit alone: 1.5 / 3.2; 9% / 52% | Yes | CRE doubles. | |
| PNC | Yardville National (6515) | — | 2008-03-07 (223) | 2008Q1 | 0.3 / 1.2; 2% / 9% | Yes | | |
| PNC | RBC Bank (USA) (33184) | 8-K: 2 Mar 2012 | **2012-03-02** (223) | 2012Q1 | 2.5 / 6.8; 5% / 25% | Yes | | |
| PNC | BBVA USA (19048) | 8-K period 1 Jun 2021 | **2021-10-08** (223) | 2021Q4 | 13.3 / 14.3; 14% / 41% | Yes | BBVA USA filed under the PNC parent in 2021Q2–Q3. | |
| PNC | FirstBank (18714) | 8-K/press release: completed 5 Jan 2026 | **2026-06-18** (223) | 2026Q2 | 0.4 / 6.6; 0.4% / 17% | Yes | | |
| Truist (9846) | SunTrust Bank (867) | 8-K: effective 6 Dec 2019 | **2019-12-07** (223) | 2019Q4 | 42.7 / 22.1; **132% / 63%** | Yes | | |
| Truist | Colonial Bank (9609), failure | 8-K period 14 Aug 2009 | 2009-08-14 (211) | 2009Q3 | 0.7 / 9.2; 4% / 26% | Yes | | |
| Truist | BB&T Virginia (22584), BB&T South Carolina (21098) (affiliates) | — | 2006-12-31 (223) | 2006Q4 | 1.2 / 5.0 and 0.7 / 2.3; 17% / 22% and 10% / 10% | Yes | Same parent: the repeated year-to-date fix applies. | |
| Truist | Susquehanna (7579); National Penn (7414) | 8-K: 31 Jul 2015; 1 Apr 2016 | 2015-08-01; 2016-04-01 (223) | 2015Q3; 2016Q2 | 1.9 / 4.7 (10% / 15%); 0.9 / 2.2 (4% / 6%) | Yes | Susquehanna brought leases of 1.4: Truist leases +135%. | |
| U.S. Bank (6548) | MUFG Union Bank (22826) | 8-K period 1 Dec 2022 | **2023-05-26** (223) | 2023Q2 | 7.6 / 14.7; 8% / 39% | Yes | | |
| U.S. Bank | FBOP failures (California National 34659, Park National 11677, San Diego National 23594, Pacific National 30006 and others) | — | 2009-10-30 (211) | 2009Q4 | CRE 4.1 + 2.8 + 2.0 + 1.4 ...; together about 30% of CRE | Yes | | |
| U.S. Bank | Downey S&L (30968), PFF (28344), failures | — | 2008-11-21 (211) | 2008Q4 | Mostly residential | Yes | | |
| **KeyBank (17534)** | **First Niagara Bank NA (16004)** | 8-K: First Niagara merged into KeyCorp 1 Aug 2016 | **2016-10-08** (223) | 2016Q4 | 4.3 / 8.1; **16% / 80%** | Yes | KeyBank CRE +80% in 2016Q4. First Niagara filed under the KeyCorp parent in 2016Q3. | |
| KeyBank | Union State Bank (20119) | — | 2008-01-17 (223) | 2008Q1 | 0.2 / 0.9; 1% / 5% | Yes | | |
| KeyBank | HSBC branches (712) | — | 2012-07-13 (712) | 2012Q3 | Data: C&I +5%, CRE flat | **No** (712) | Negligible in commercial. | |
| Fifth Third (6672) | MB Financial Bank NA (3628) | 8-K: completion announced 22 Mar 2019 | **2019-05-04** (223) | 2019Q2 | 6.4 / 3.8; 16% / 34% | Yes | MB had absorbed Corus (2009) and Broadway (2010); the chain is walked. | |
| Fifth Third | **Comerica Bank (983)** and Comerica Bank & Trust NA (1596) | 8-K Item 2.01, period 1 Feb 2026: the bank mergers took effect and both Comerica charters "ceased" | **2026-02-01** (223) | 2026Q1 | 24.5 / 17.7; **59% / 107%** | Yes | Fifth Third C&I +64%, CRE +108% in 2026Q1. | |
| Fifth Third | Fifth Third Bank (993) and Fifth Third Bank NA (32712), affiliate consolidation | — | 2009-09-30 (223) | 2009Q3 | 11.3 / 11.7; 92% / 195% | Yes | Same parent. | |
| Fifth Third | Pathward (712); Mechanics Bank (712) | Not checked | 2025-11-05; 2026-05-01 (712) | 2025Q4; 2026Q2 | Data: no commercial move over 3% | **No** (712) | Negligible | |
| Huntington (6560) | Sky Bank (5982) | 8-K: 1 Jul 2007 | 2007-09-21 (223) | 2007Q3 | 4.3 / 4.4; 97% / 66% | Yes | | |
| Huntington | FirstMerit Bank (13675) | 8-K: effective 16 Aug 2016 | **2016-08-16** (223) | 2016Q3 | 5.1 / 3.5; 34% / 47% | Yes | | |
| Huntington | TCF National Bank (28330) | 8-K: effective 9 Jun 2021 | **2021-06-09** (223) | 2021Q2 | 11.8 / 10.0; 47% / 97% | Yes | Leases +122%. | |
| Huntington | Veritex Community Bank (57665) | 8-K (Item 8.01): effective 20 Oct 2025, the merger and the bank merger | **2025-10-20** (223) | 2025Q4 | 1.2 / 5.1; 3% / 28% | Yes | | |
| Huntington | **Cadence Bank (11813). It happened.** | 8-K Item 2.01: effective 1 Feb 2026 | **2026-02-01** (223) | 2026Q1 | 7.9 / 15.4; 19% / 66% | Yes | CRE +66% in 2026Q1. | |
| Huntington | Macquarie Equipment Finance (asset purchase) | Announced 24 Feb 2015 (8-K, about $900m of assets, "nearly $1 billion of commercial leases"). Close date NOT CHECKED. | — | 2015Q1 (data) | Leases 1.4 → 2.1 (+53%) | **No** | Trips the jump. | |
| M&T (588) | People's United Bank NA (27334) | 8-K: effective 1 Apr 2022 | **2022-04-02** (223) | 2022Q2 | 9.7 / 13.2; 54% / 39% | Yes | | |
| M&T | Hudson City (13074) | 8-K: 1 Nov 2015 | 2015-11-01 (223) | 2015Q4 | Almost all residential | Yes | | |
| M&T | Provident Bank of Maryland (15951) | — | 2009-05-23 (223) | 2009Q2 | 0.4 / 1.8; 3% / 10% | Yes | | |
| M&T | **Wilmington Trust Company (680) and Wilmington Trust FSB (33911)** | 8-K: effective 16 May 2011 | **2011-05-16 (712, branch purchase)** | 2011Q2 | Data, M&T 2011Q1 → Q2: construction +19%, NFNR +16%, C&I +10%, total +13% | **No** (712 is not an acquisition in `fdic.py`) | **Under 25% and invisible to the 5% rule. The windows would be kept, mixing two books.** | |
| Citizens (57957) | Investors Bank (28892) | Press release (8-K): closing announced 7 Apr 2022 | **2022-04-07** (223) | 2022Q2 | 1.6 / 15.6; 4% / 90% | Yes | Multifamily +994%. | |
| Citizens | HSBC East Coast branches (712) | Press release (8-K), 22 Feb 2022 | 2022-02-18 (712) | 2022Q1 | Data: C&I +1%, CRE flat | **No** (712) | Negligible in commercial | |
| Citizens | Citizens Bank of Pennsylvania (57282) (affiliate); 2007 consolidation of Charter One and others | — | 2019-01-02; 2007-09-01 (223) | 2019Q1; 2007Q3 | 5.7 / 3.7 (19% / 28%); 2007 several times Citizens NA's own book | Yes | Same parent: repeated year-to-date fix. | |
| First Citizens (11063) | **SVB, via Silicon Valley Bridge Bank (59334)** | 8-K Item 2.01: P&A agreement 27 Mar 2023; "approximately $72.1 billion in loans" | **2023-03-26** (216); chain SVB 24735 → 59331 (211, 2023-03-10) → 59334 (221, 2023-03-13) | 2023Q1 | SVB at 2022Q4: total 74.2, C&I 19.1, other loans (incl. NDFI / capital-call lines) 41.0 | Yes. The chain is all allowlisted, so SVB's 2022Q4 and earlier filings combine. | Pro forma adds SVB's whole book ($74.2bn). FCB bought about $72.1bn of loans. First Citizens' other loans +983% in 2023Q1. | |
| First Citizens | CIT Bank NA (58978) | 8-K: 3 Jan 2022 | **2022-01-04** (223) | 2022Q1 | 11.0 / 9.0; **221% / 55%** | Yes | Leases +723%. | |
| First Citizens | First Citizens Bank & Trust (SC) (15504) | 8-K period 1 Oct 2014 | 2015-01-01 (223) | 2015Q1 | 0.3 / 1.2; 24% / 16% | Yes | | |
| First Citizens | 2009–2017 failed-bank purchases (Temecula Valley, Venture, First Regional, United Western, Colorado Capital and others) | — | various (211) | 2009Q3–2017Q2 | First Regional: 0.2 / 1.6, 16% / 36% | Yes | | |
| JPMorgan (628) | **Washington Mutual Bank (32633), failure** | 8-K (Item 8.01), 25 Sep 2008 | **No acquirer row in FDIC history.** FDIC failures API: failed 9/25/2008, resolution type "PA". | 2008Q3 | WaMu Bank at 2008Q2: total 241.6, C&I 1.9, multifamily 32.1, NFNR 9.2, construction 4.4 | **No** (only WaMu Bank FSB 33891, $20.6bn, is recorded, 2008-09-25, code 223) | JPMorgan 2008Q3: multifamily 0.7 → 32.3, NFNR +73%, construction +64% (jump catches these). The 5% share is measured from the FSB only (4.3% of loans), so pro forma **cannot** combine the main bank. | |
| JPMorgan | First Republic Bank (59017), failure | 8-K (Item 8.01), 1 May 2023 | **2023-05-01** (211) | 2023Q2 | 4.5 / 38.8; 2% / 29% | Yes | | |
| JPMorgan | Chase Bank USA (23702) (affiliate, cards) | — | 2019-05-18 (223) | 2019Q2 | C&I 8.0 (5%) | Yes | | |
| Capital One (4297) | Discover Bank (5649) | 8-K Item 2.01: effective 18 May 2025 | **2025-05-18** (223) | 2025Q2 | C&I 0.1, CRE 0 | Yes | Consumer only | |
| Capital One | ING Bank fsb (35489) (ING Direct) | 8-K Item 2.01: 17 Feb 2012 | **2012-11-01** (223) | 2012Q4 | C&I 0, CRE 0 | Yes | ING Bank filed separately under the Capital One parent until 2012Q3. | |
| Capital One | HSBC US card business (712, HSBC Bank Nevada) | 8-K Item 2.01: 1 May 2012 | 2012-05-01 (712) | 2012Q2 | Consumer cards (total loans +28%) | **No** (712) | Consumer, not commercial | |
| Capital One | Capital One Bank (USA) (33954) (affiliate) | — | 2022-10-03 (223) | 2022Q4 | C&I 10.8 (29%) | Yes | Same parent | |
| Capital One | North Fork Bank (15985); Capital One FSB (34191); Chevy Chase (32324) | — | 2007-08-01; 2007-07-01; 2009-07-30 (223) | 2007Q3; 2009Q3 | North Fork: 5.7 / 14.3, several times Capital One NA's book | Yes | | |
| Capital One | **GE Capital Healthcare Financial Services (asset purchase)** | 4Q15 earnings release (8-K): "On December 1, 2015, we completed the acquisition" | — | 2015Q4 | Data: NFNR 10.9 → 16.2 (+49%), C&I +21%, other loans +27% | **No** | NFNR trips the jump. C&I and other loans do not, and no record exists. | |
| Bank of America (3510) | LaSalle Bank NA (15407) and LaSalle Midwest (22488) | HC close (ABN AMRO North America) NOT CHECKED | **2008-10-17** (223) | 2008Q4 | 17.4 / 13.8 and 3.7 / 3.6; 11% / 17% and 2% / 5% | Yes | Construction +52%. | |
| Bank of America | Merrill Lynch Bank USA (27374); Merrill Lynch Bank & Trust FSB (34571) | 8-K: 1 Jan 2009 | 2009-07-01; 2009-11-02 (223) | 2009Q3; 2009Q4 | 9.2 / 1.6 (6% / 2%); 1.5 / 5.7 (1% / 6%) | Yes | | |
| Bank of America | Countrywide Bank FSB (33143); FIA Card Services (33318) | — | 2009-04-27; 2014-10-01 (223) | 2009Q2; 2014Q4 | Mostly consumer | Yes | | |
| Citi (7213) | 2006 affiliate consolidation (CFSB, Citibank West, Citibank Texas and others); Citibank South Dakota (2011); Citicorp Trust Bank (2012) | — | 2006-10-01; 2011-07-01; 2012-01-01 (223) | 2006Q4; 2011Q3; 2012Q1 | Citibank West: CRE 9.2, 222% of Citibank NA's domestic CRE | Yes | Same parent. Multifamily +877% in 2006Q4. | |
| Regions (12368) | AmSouth Bank (26800) | 8-K Item 2.01: 4 Nov 2006 | **2006-11-04** (223) | 2006Q4 | 4.9 / 11.8; 50% / 57% | Yes | | |
| Zions (2270) | Seven affiliate banks consolidated (Amegy, CB&T, NB Arizona, Nevada State, Vectra, Commerce Bank of Washington, Zions Trust) | — | **2015-12-31** (223) | 2015Q4 | Amegy C&I 4.5 (135%), CB&T CRE 4.6 (78%) ... | Yes | Zions NA's own book triples. Same parent: repeated year-to-date fix. | |

**Not on the roster, or not found:**

- **Fifth Third / Comerica: closed** (see table).
- **PNC / FirstBank: closed** (see table).
- "Huntington / Cadence" refers to Cadence Bank (cert 11813), merged 2026-02-01 (see table).

---

## C. What the repository's merger record cannot see (commercial books that enter without a record)

1. **WaMu Bank (cert 32633) into JPMorgan, 2008Q3.**
   - The failure has no history row naming JPMorgan.
   - Only the FSB is recorded. Pro forma cannot be built, and the 5% share undercounts.
   - Every other large failure since 2006 into a roster bank does carry an acquirer row. I checked all 83 failures over $1bn.
2. **Code 712 branch/asset purchases.**
   - **M&T / Wilmington Trust (2011Q2): material.** Construction +19%, NFNR +16%, under the 25% jump.
   - Others with negligible commercial effect, from the data: Citizens/HSBC (2022Q1), KeyBank/HSBC (2012Q3), Huntington/BofA (2014Q3), Fifth Third/Pathward (2025Q4) and Mechanics (2026Q2), Zions/FirstBank branches (2025Q2).
   - Capital One/HSBC cards (2012Q2) is consumer.
3. **Non-bank asset purchases** (verified in SEC filings, none in FDIC history):
   - Wells / GE Capital (2016Q1)
   - Capital One / GE Healthcare Financial Services (2015Q4)
   - Huntington / Macquarie Equipment Finance (2015Q1, close date NOT CHECKED)

## D. Large moves and sales (25% rule)

**No commercial loan sale or held-for-sale transfer found with a primary source.**

- **Truist / Sheffield** (powersports) is consumer. Not checked against a primary source.
- **KeyBank and PNC**: no commercial sale found.

**Data scan.** `breaks-jumps.tsv` lists every quarter-on-quarter move over 25% in a commercial category where the bank's book was at least $1bn on one side. There are 302 bank-category-quarters; 87 are not explained by a recorded merger or a definition-change quarter. The unexplained ones worth a look, with causes NOT CHECKED:

| Bank | Quarter | Move |
|---|---|---|
| Truist | 2022Q1 | Leases −49% |
| Regions | 2015Q4 | Leases −48% |
| Capital One | 2013Q3 | Leases −77% |
| First Citizens | 2012Q4 | C&I −40% |
| Bank of America | 2013Q1 | Other loans +66% |
| Huntington | 2022Q2 | Other loans +161% |
| Fifth Third | 2022Q2–Q3 | Other loans −41% then +78% |
| Fifth Third | 2006Q1 | CRE +62% |
| Wells Fargo | 2021Q4 | Multifamily +25% |
| Citi | 2010Q3 | Multifamily −39% |

The deals behind three moves were confirmed in SEC filings (section C), but the deals are missing from the record: Wells 2016Q1 leases +56%, Capital One 2015Q4 NFNR +49%, Huntington 2015Q1 leases +53%.

**Loans to depository institutions (LNDEP) is volatile at every money-center bank:** dozens of moves over 25% with no event. Banks with large books in it, such as Citi and Capital One in 2010–2011, show swings of +200% to +4,000%.

---

## Sources

**Federal Register** (govinfo copies; HTML at `https://www.govinfo.gov/content/pkg/FR-<date>/html/<doc>.htm`):

- 71 FR 8649, 17 Feb 2006 (06-1495) — https://www.govinfo.gov/content/pkg/FR-2006-02-17/html/06-1495.htm
- 73 FR 54807, 23 Sep 2008 (E8-22258) — https://www.govinfo.gov/content/pkg/FR-2008-09-23/html/E8-22258.htm
- 74 FR 5028, 28 Jan 2009 (E9-1734) — https://www.govinfo.gov/content/pkg/FR-2009-01-28/html/E9-1734.htm
- 74 FR 41973, 19 Aug 2009 (E9-19911) — https://www.govinfo.gov/content/pkg/FR-2009-08-19/html/E9-19911.htm
- 74 FR 68314, 23 Dec 2009 (E9-30489) — https://www.govinfo.gov/content/pkg/FR-2009-12-23/html/E9-30489.htm
- 75 FR 60497, 30 Sep 2010 (2010-24476) — https://www.govinfo.gov/content/pkg/FR-2010-09-30/html/2010-24476.htm
- 76 FR 5253, 28 Jan 2011 (2011-1815) — https://www.govinfo.gov/content/pkg/FR-2011-01-28/html/2011-1815.htm
- 78 FR 30922, 23 May 2013 (2013-12220) — https://www.govinfo.gov/content/pkg/FR-2013-05-23/html/2013-12220.htm
- 83 FR 939, 8 Jan 2018 (2018-00122) — https://www.govinfo.gov/content/pkg/FR-2018-01-08/html/2018-00122.htm
- 84 FR 4131, 14 Feb 2019 (2019-02330) — https://www.govinfo.gov/content/pkg/FR-2019-02-14/html/2019-02330.htm
- 84 FR 53227, 4 Oct 2019 (2019-21659) — https://www.govinfo.gov/content/pkg/FR-2019-10-04/html/2019-21659.htm
- 85 FR 44361, 22 Jul 2020 (2020-15788) — https://www.govinfo.gov/content/pkg/FR-2020-07-22/html/2020-15788.htm
- 88 FR 89489, 27 Dec 2023 (2023-28473) — https://www.govinfo.gov/content/pkg/FR-2023-12-27/html/2023-28473.htm
- 89 FR 45046, 22 May 2024 (2024-11221) — https://www.govinfo.gov/content/pkg/FR-2024-05-22/html/2024-11221.htm
- 90 FR 31111, 11 Jul 2025 (2025-12935) — https://www.govinfo.gov/content/pkg/FR-2025-07-11/html/2025-12935.htm

**FDIC:**

- QBP Q1 2010 — https://www.fdic.gov/analysis/quarterly-banking-profile/qbp/2010mar/qbp.pdf
- QBP Q1 2020 — https://www.fdic.gov/analysis/quarterly-banking-profile/qbp/2020mar/qbp.pdf
- QBP Q2 2020 — https://www.fdic.gov/analysis/quarterly-banking-profile/qbp/2020jun/qbp.pdf
- Banking Issues in Focus No. 1, Feb 2026, "Bank Lending to Nondepository Financial Institutions" — https://www.fdic.gov/analysis/bank-lending-nondepository-financial-institutions.pdf
- Interagency statement, 7 Apr 2020 — https://www.fdic.gov/sites/default/files/2024-03/pr20049a.pdf
- Dec 2024 Supplemental Instructions — https://www.fdic.gov/system/files/2024-12/1224supplemental-instructions-final.pdf
- BankFind history, financials and failures APIs: https://api.fdic.gov/banks/history, …/financials, …/failures

**Federal Reserve:**

- H.8, 26 Sep 2025, Notes on Data — https://www.federalreserve.gov/releases/h8/20250926/

**SEC 8-Ks** (`https://www.sec.gov/Archives/edgar/data/<CIK>/<accession>/<file>`):

- KeyCorp — 000119312516665717/d231639d8k.htm
- Truist — 000119312519308844/d841243d8k.htm
- Fifth Third / Comerica — 000119312526032625/d642888d8k.htm
- Fifth Third / MB — 000119312519082657/d724824d8k.htm
- Huntington / Cadence — 000114036126003083/ef20064500_8k.htm
- Huntington / Veritex — 000114036125038574/ef20057398_8k.htm
- Huntington / TCF — 000114036121020258/nt10025590x4_8k.htm
- Huntington / FirstMerit — 000119312516685218/d234297d8k.htm
- Huntington / Sky — 000129993307003961/htm_21224.htm
- Huntington / Macquarie — 000129993315000283/exhibit1.htm
- PNC / FirstBank — 000071367626000003/exhibit991.htm
- PNC / BBVA — 000071367621000071/pnc-20210601.htm
- PNC / RBC — 000119312512095471/d310430d8k.htm
- PNC / Mercantile — 000089882207000372/pnc8kmarch8.htm
- U.S. Bancorp / MUFG — 000119312522296642/d766593d8k.htm
- M&T / People's United — 000119312522094296/d349120d8k.htm
- M&T / Hudson City — 000119312515362613/d92880d8k.htm
- M&T / Wilmington — 000095012311052112/l42734e8vk.htm
- Citizens / Investors — 000075994422000058/cfg_isbcclosingpressreleas.htm
- Citizens / HSBC — 000075994422000022/hsbcclosingpressrelease.htm
- First Citizens / SVB — 000119312523079743/d488575d8k.htm
- First Citizens / CIT — 000114036122000357/brhc10032347_8k.htm
- JPMorgan / WaMu — 000119312508201638/d8k.htm
- JPMorgan / First Republic — 000001961723000304/jpm-20230501.htm
- Capital One / Discover — 000119312525122059/d934475d8k.htm
- Capital One / ING — 000089882212000071/cof8k0217121.htm
- Capital One / HSBC — 000089882212000195/closing8-k.htm
- Capital One / GE Healthcare — 000092762816000126/q42015earningsrelease-ex992.htm
- Wells / GE Capital — 000007297116001077/wfc1qer4-14x2016exx991.htm
- Regions / AmSouth — 000089882206001166/reg8k.htm
- BofA / Merrill — 000095012309000010/y73597e8vk.htm

**NOT CHECKED (blocked or not found):**

- FFIEC supplemental instructions on ffiec.gov (returned 403), including where PPP loans are reported.
- FIL-84-2024 (returned 404).
- The final notice for the 2025 modification-reporting change.
- Holding-company closes for Wells/Wachovia, PNC/National City and BofA/LaSalle.
- Whether the FDIC real estate sub-fields are domestic or consolidated.
- Which roster banks moved from form 041 to 031 in 2018.
