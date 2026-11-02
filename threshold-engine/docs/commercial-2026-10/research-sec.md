# What the 16 peer holding companies tag about commercial credit quality in their 10-Q XBRL

Research note, 16 Oct 2026. Read-only. Nothing in the repository was edited.

**Sources.** SEC EDGAR, fetched live this session (User-Agent "SATC research (bank 10-Q credit quality study) research@example.com", about 0.2 s between requests). For each holding company I took the submissions record, the latest 10-Q's EDGAR-extracted instance (`*_htm.xml`), its label linkbase and its primary HTML. All 16 latest 10-Qs are for **2026 Q2 (period 30 Jun 2026)**. No Q3 10-Q was on file as of 16 Oct 2026.

- Working data: `(working file, not kept)`
  - `subs.json`
  - `survey.txt`, `detail.txt`, `survey.json`
  - per-bank folders holding the instance, labels, the primary .htm and `text.txt`
- Scripts: `research-scripts/sec/`
  - `subs.py`, `fetch.py`, `fetchdoc.py`
  - `survey.py`, `detail.py`, `labs.py`, `office.py`, `totext.py`
  - `run_tracker_parser.py`

**Method.** Every figure below comes from facts dated 30 Jun 2026 whose context carries a member on `us-gaap:InternalCreditAssessmentAxis`, or Citi's `ExternalCreditRatingByGroupingAxis`. Category names are the **filer's own labels** from its label linkbase, not the member names. In four banks the member name and the label disagree; see §3.

---

## 1. What the two existing tools do

### 1a. `edgar-crit-class-tracker/` (consulting line)

- **What it reads.**
  - Line items: `FinancingReceivableBeforeAllowanceForCreditLoss` and `FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss`. Only the `us-gaap` namespace is read; extension re-declarations are skipped.
  - Dimensions: `InternalCreditAssessmentAxis` together with either `FinancingReceivableRecordedInvestmentByClassOfFinancingReceivableAxis` or `FinancingReceivablePortfolioSegmentAxis`. A context carrying any other axis is dropped.
  - Vintage line items are ignored on purpose.
  - It also runs an 8-K item lane (1.03, 2.04, 2.06, 4.02).
  - Source: `runner.py` lines 117-126 and 1003-1097.
- **Banks.** Ten seeds in `member_seed.py`: Fifth Third, Regions, Zions, Comerica, Huntington, Truist, KeyCorp, M&T, U.S. Bancorp and BOK Financial.
  - 8 of the 10 are in our roster.
  - Comerica filed a **25-NSE on 2 Feb 2026**. Its last 10-Q is for Q3 2025, so that seed is stale.
- **Disclosure families it claimed:**
  - `grades_full`: FITB, ZION, RF, CMA, HBAN ("OLEM"), TFC ("Nonperforming" variant), BOKF
  - `criticized_only`: KEY, MTB
  - `ig_nig`: USB, JPM
- **What it found, and what it could not.**
  - `COVERAGE_RESEARCH_EDGAR.md` says SEC hosts were proxy-blocked from its sandbox. Its evidence came from mirrors, taxonomy linkbases and search snippets.
  - `BUILD_NOTES.md`: "Live path is fixture-tested only". The extension member names in its seeds are labelled "ILLUSTRATIVE placeholders". Its coverage estimates (60-75% of regionals give full grades; over 90% give at least pass versus criticized) are marked UNVERIFIED.
  - **It has never been run against a real filing.**

### 1b. threshold-engine consumer class mapping (`book/threshold-engine`)

- **`src/threshold_engine/peers/classes.py`**
  - `pull()` fetches, per holding company, the submissions JSON, the extracted instance and the label linkbase into a cache. The User-Agent is required, has no default and is never stored.
  - `read()` and `facts()` take one concept, `us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss`, at the quarter-end instant.
  - A fact is kept only when **every** axis on its context matches `CLASS_AXIS`, a regex for PortfolioSegment, ClassOf, ByClass, LoanType or ProductOrService. That deliberately excludes credit-quality, past-due and vintage cells.
  - Members are sorted into a key. Two different values for the same key are refused.
- **`config/peer-loan-classes.json`**
  - Covers 17 entries: the 16 roster holding companies plus SoFi. Each entry has CIK, holding company and filing URL.
  - `classes[]` gives either XBRL `members` (the amount is always looked up, never typed) or, for classes the filing prints but does not tag, `amount_musd` with `where`.
  - `findings` covers student, unsecured and secured non-auto lending. Each finding has `answer`, `short`, `quote` and `where`. "not stated" means the terms named in `where` were searched for and not found.
- **How quotes are checked: `docs/tie-out/peer-loan-classes-2026q2/`**
  - `record/make_config.py` fails the build if a quote is not in the reader agents' records.
  - `filed.py` re-fetches each 10-Q's primary .htm and parses its inline XBRL `ix:nonFraction` facts, a different file and parser from the build's. It also writes the document text with table cells separated by " | ".
  - `compare.py` matches each class amount. Tagged classes are matched to the inline fact with the same members. Printed classes are matched to a row with the class label and the printed figure, or to a quoted sentence (rules in the `PRINTED` dict). The verdict is TIED, DIFFERS or COULD NOT.
  - The exhibit reports 33 of 33 TIED. It says all 24 quotes were found word for word in the filed text, and that 27 "not stated" findings are listed as searches.
- **Gap.** The script that wrote `out/quotes.json` (the word-for-word check) is **not in the folder**. Only `build_exhibit.py`, which reads it, is present, so that check cannot be re-run from what is in the scratch tree.

---

## 2. Peer roster: bank charter to SEC filer

| Roster bank (FDIC cert) | SEC filer | CIK | Basis note (stated in the filing where quoted) |
|---|---|---|---|
| JPMorgan Chase Bank NA (628) | JPMorgan Chase & Co. | 19617 | "JPMorganChase's principal bank subsidiary is JPMorgan Chase Bank, National Association … principal non-bank subsidiary is J.P. Morgan Securities LLC". J.P. Morgan Securities plc and JPMSE "are subsidiaries of JPMorgan Chase Bank, N.A." |
| Wells Fargo Bank NA (3511) | Wells Fargo & Company | 72971 | The 10-Q's liquidity section defines "Wells Fargo Bank, N.A., and other bank entities (Bank)" |
| Bank of America NA (3510) | Bank of America Corp | 70858 | "We operate our banking activities primarily under the Bank of America, National Association … charter". Commercial is tagged domestic $456.6bn and foreign $159.9bn (by borrower, not by legal entity) |
| Citibank NA (7213) | Citigroup Inc. | 831001 | **Big basis gap, see §5.** Corporate loans of $183.9bn out of $377.1bn are booked in offices outside North America. The filer includes broker-dealer and non-bank subsidiaries |
| US Bank NA (6548) | U.S. Bancorp | 36104 | One principal bank (not examined further) |
| PNC Bank NA (6384) | PNC Financial Services Group | 713676 | One principal bank (not examined further) |
| Truist Bank (9846) | Truist Financial Corp | 92230 | One principal bank (not examined further) |
| Capital One NA (4297) | Capital One Financial Corp | 927628 | "On May 18, 2025 … Discover Financial Services merged into Capital One and Discover Bank merged into CONA." CONA is now the principal operating subsidiary, so the Discover card book sits inside cert 4297. Commercial is only $91.3bn (pass plus criticized, C&I and CRE) |
| KeyBank NA (17534), self | KeyCorp | 91576 | One principal bank |
| Fifth Third Bank NA (6672) | Fifth Third Bancorp | 35527 | Comerica merged in during Q1 2026 (Comerica filed its 25-NSE on 2 Feb 2026) |
| Huntington National Bank (6560) | Huntington Bancshares | 49196 | One principal bank |
| First-Citizens Bank & Trust (11063) | First Citizens BancShares | 798941 | One principal bank (not examined further) |
| Citizens Bank NA (57957) | Citizens Financial Group | 759944 | One principal bank |
| Manufacturers and Traders Trust (588) | M&T Bank Corp | 36270 | One principal bank |
| Regions Bank (12368) | Regions Financial Corp | 1281761 | One principal bank |
| Zions Bancorporation NA (2270) | Zions Bancorporation, N.A. | 109380 | **The filer is the bank itself.** There is no holding company, so no basis gap |

All 16 filers file with the SEC. None is missing.

---

## 3. Per-bank results, 2026 Q2 10-Q XBRL, verified now

Column definitions:

- **CQI categories**: the filer's labels on the credit-assessment axis for commercial loans.
- **SM/Sub split**: Y if special mention and substandard (classified) are tagged separately by class.
- **Vintage**: Y if the origination-year line items (`...YearOneOriginatedCurrentFiscalYear` through `...OriginatedMoreThanFiveYears`, plus `...Revolving`) are tagged with credit-quality dimensions at 30 Jun 2026.

| Holding co | CIK | Accession (10-Q, period 2026-06-30) | Commercial classes in the CQI table (filer labels) | CQI categories (filer labels) | Criticized in XBRL | SM/Sub split | Vintage | Verified now |
|---|---|---|---|---|---|---|---|---|
| JPMorgan Chase | 19617 | 0001628280-26-054343 | Wholesale by sector: C&I; Real estate (Multifamily and Commercial lessors tagged for criticized only); Other | Investment-grade; noninvestment-grade split into **Noncriticized / Criticized performing / Criticized nonaccrual** | Y | N | Y (IG/NIG only) | Y |
| Wells Fargo | 72971 | 0000072971-26-000302 | C&I; CRE; Lease financing (vintage cells only) | Pass / Criticized | Y | N | Y | Y |
| Bank of America | 70858 | 0000070858-26-000394 | U.S. commercial (domestic); Non-U.S. commercial (foreign); CRE; Commercial lease financing; U.S. small business commercial | Pass rated / Reservable criticized | Y | N | Y | Y |
| Citigroup | 831001 | 0000831001-26-000045 | Corporate: C&I; Financial institutions; Mortgage and real estate; Other | Investment grade / Non-investment grade accrual / Non-investment grade non-accrual (**external-rating axis**) | **N** | N | Y | Y |
| U.S. Bancorp | 36104 | 0000036104-26-000044 | Commercial (loans and leases); CRE | Pass / Special Mention / **Classified** (on `SubstandardMember`) / Total Criticized | Y | Y | Y | Y |
| PNC | 713676 | 0001628280-26-053170 | C&I; CRE | Pass Rated / Criticized | Y | N | Y | Y |
| Truist | 92230 | 0000092230-26-000099 | C&I; CRE; Commercial construction | Pass / Special mention / Substandard / Nonperforming | Y | Y | Y | Y |
| Capital One | 927628 | 0000927628-26-000089 | C&I; Commercial and multifamily RE (combined) | Noncriticized / Criticized, the criticized split performing / nonperforming | Y | N | Y | Y |
| KeyCorp (self) | 91576 | 0001628280-26-052671 | C&I; Commercial mortgage; Construction; Commercial lease financing | Pass / Criticized (Accruing) / Criticized (Nonaccruing) | Y | N | Y | Y |
| Fifth Third | 35527 | 0000035527-26-000202 | C&I; Commercial mortgage owner-occupied; Commercial mortgage nonowner-occupied; Commercial construction; Commercial leases | Pass / Special mention / Substandard / Doubtful | Y | Y | Y | Y |
| Huntington | 49196 | 0000049196-26-000066 | C&I; CRE; Lease financing | Pass / **OLEM** (on `SpecialMentionMember`) / Substandard | Y | Y | Y | Y |
| First Citizens | 798941 | 0000798941-26-000031 | C&I; CRE; Owner-occupied commercial mortgage; Investor dependent; Capital call lines (Pass only) | Pass / Special Mention / Substandard / Doubtful / Ungraded | Y | Y | Y | Y |
| Citizens | 759944 | 0000759944-26-000148 | C&I; CRE | Pass / Special Mention / **Substandard Accrual** / **Nonaccrual** (on `DoubtfulMember`) | Y | Y | Y | Y |
| M&T | 36270 | 0000036270-26-000050 | C&I (tagged on the segment member); CRE; Residential builder and developer; Other commercial construction | Pass / Criticized accrual / Criticized nonaccrual | Y | N | Y | Y |
| Regions | 1281761 | 0001281761-26-000055 | C&I; CRE mortgage owner-occupied; CRE construction owner-occupied; Investor RE mortgage; Investor RE construction | Pass / Special Mention / Substandard / Non-Accrual | Y | Y | Y | Y |
| Zions | 109380 | 0000109380-26-000111 | C&I; Owner-occupied; Municipal; Construction and land development; Term CRE | Pass / Special Mention / Accruing Substandard / Nonaccrual (one Doubtful fact, value 0) | Y | Y | Y | Y |

Sample values from the instances, 30 Jun 2026, $ millions:

| Bank | Class | Pass | Special mention | Substandard | Doubtful | Criticized |
|---|---|---|---|---|---|---|
| Fifth Third | C&I | 81,037 | 1,910 | 2,682 | 107 | |
| KeyCorp | C&I | 59,149 | | | | 3,227 accruing / 358 nonaccruing |
| Wells Fargo | C&I | 472,144 | | | | 15,486 |
| JPMorgan | C&I sector | 100,897 (noncriticized NIG) | | | | 14,195 performing / 2,120 nonaccrual |

**Total concept is not uniform.** Twelve filers use `us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss` for the CQI totals. The other four do not:

- M&T and Zions use `us-gaap:...BeforeAllowanceForCreditLossFeeAndLoanInProcess`.
- Regions uses `rf:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLossNetOfUnallocatedAmounts`, with a separate `rf:FinancingReceivableUnallocated`.
- Wells Fargo tags its commercial segment total on `wfc:FinancingReceivableAndNetInvestmentInLease...`.

---

## 4. Counts (denominator: 16 holding companies, all verified now)

| Question | Count | Banks |
|---|---|---|
| Tag commercial amortized cost by internal risk rating **with a criticized measure**, by class | **15 / 16** | All except Citi |
| …of which special mention and substandard (classified) tagged separately | **8 / 16** | USB, TFC, FITB, HBAN, FCNCA, CFG, RF, ZION |
| …of which only pass versus criticized, split accrual / nonaccrual (or performing / nonperforming) | **4 / 16** | KEY, MTB, COF, JPM |
| …of which only pass versus criticized, no further split | **3 / 16** | WFC, BAC, PNC |
| No criticized measure in XBRL (investment / non-investment grade on an external-rating axis) | **1 / 16** | Citi |
| A real "Doubtful" grade tagged (as opposed to a nonaccrual column) | **2 / 16** | FITB, FCNCA (ZION has a single zero-value Doubtful fact) |
| Nonaccrual or nonperforming tagged as its own column on the grade axis | **4 / 16** | CFG (labelled Nonaccrual on `DoubtfulMember`), RF, TFC, ZION |
| Criticized **C&I** by risk-rating category in XBRL | **15 / 16** | All except Citi (BAC as U.S. and non-U.S. commercial; JPM as the C&I sector) |
| …with special mention and substandard separate for C&I | **8 / 16** | Same eight as above |
| CRE split owner-occupied / non-owner-occupied in the CQI table | **4 / 16** | FITB, RF, ZION, FCNCA |
| Construction as its own CQI class | **6 / 16** | FITB, KEY, TFC, RF, ZION, MTB |
| Commercial leases as their own CQI class | **5 / 16** | FITB, HBAN, KEY, BAC, WFC (WFC in vintage cells only) |
| Multifamily as its own class | **1 / 16, partial** | JPM tags only criticized and nonaccrual amounts. COF combines it with CRE |
| **CRE office split in XBRL CQI** | **0 / 16** | None. Zions tags office members only in its individually-evaluated / LTV table |
| CRE office printed in text (property-type table or paragraph) | **12 / 16** | BAC, CFG, FCNCA, HBAN, JPM, KEY, MTB, PNC, RF, TFC, WFC, ZION. Not in C, COF, FITB or USB |
| Office **criticized** printed in text | **4 / 16** | MTB (criticized accrual / nonaccrual by property type), ZION (office criticized ratio 7.9%, classified 7.2%), BAC ("Reservable criticized exposure for the office property type was $2.8 billion"), PNC ("criticized loans totaled 29.4%") |
| Vintage disclosure with credit-quality dimensions | **16 / 16** | All. JPM's vintage is by investment / non-investment grade only, not by criticized |

---

## 5. Holding company versus bank basis, only where a filing states it

- **Citi.** Corporate loans in offices outside North America total $183,850m of $377,142m, about 49%. North America offices hold $193,292m. The 10-Q says:

  > "The classification of corporate loans between offices in North America and outside North America is based on the domicile of the booking unit."

  Mexico counts as outside North America. Citigroup consolidates "broker-dealer and other non-bank subsidiaries".

  The filing does not say what share of loans sits in Citibank NA, and booking-office location is not the same as legal entity: Citibank NA has foreign branches. Citi's MD&A also prints "Non-criticized / Criticized performing / Criticized non-performing" by industry. That is on total credit exposure (funded plus unfunded), **text only, not in XBRL**.
- **Capital One.** Discover Bank merged into CONA on 18 May 2025, so the holding company and cert 4297 now carry the same card book. The commercial book is small: $91.3bn tagged in the CQI.
- **JPMorgan.** The principal non-bank subsidiary is J.P. Morgan Securities LLC. JPMS plc and JPMSE are subsidiaries of the bank, so they sit inside the bank's consolidated basis.
- **Bank of America.** "Primarily under the BANA charter". Non-U.S. commercial is $159.9bn, by borrower domicile.
- **Wells Fargo.** The 10-Q's liquidity section names "Wells Fargo Bank, N.A., and other bank entities (Bank)". No loan split is given.
- **Zions.** The filer is the bank, so there is no gap.
- **The other ten.** Not examined for basis statements.

---

## 6. The edgar-crit-class-tracker against reality (re-verified now)

I ran its own `EdgarProvider.parse_instance` (imported read-only, no bytecode written) on the 16 real instances.

**Facts returned** by the 4-axis filter and the 2-concept filter:

| Facts | Banks |
|---|---|
| 0 | MTB, RF, ZION (concepts not in its list), Citi (external-rating axis) |
| Pass only | COF: the criticized cells carry a performing / nonperforming axis and are dropped |
| 6, of 95 credit-quality facts | JPM: its sector classes sit on `EquitySecuritiesByIndustryAxis` |

**Family claims, checked against the Q2 2026 XBRL:**

| Bank | Tracker claim | Verdict | What the XBRL shows |
|---|---|---|---|
| FITB | `grades_full` | Confirmed | |
| TFC | `grades_full`, Nonperforming variant | Confirmed | `us-gaap:NonperformingFinancingReceivableMember` is unseeded, so it would count in the denominator only |
| HBAN | `grades_full` with OLEM | Confirmed, member name wrong | Has no Doubtful. "OLEM" is the label on `us-gaap:SpecialMentionMember`; there is no `hban:OlemMember` |
| RF | `grades_full` | Partial | Pass / SM / Substandard / `rf:NonAccrualMember` |
| ZION | `grades_full` | Partial | `zions:AccruingSubstandardMember` and `zions:NonaccrualMember` are unseeded |
| KEY | `criticized_only` | Confirmed, one name wrong | Actual `key:CriticizedNonaccruingMember`; seed says `...NonaccrualMember` |
| MTB | `criticized_only` | Confirmed, one name wrong | Actual `mtb:CriticizedAccrualMember`; seed says `...AccruingMember` |
| USB | `ig_nig` | **Wrong** | Pass / SM / Classified / Total Criticized |
| JPM | `ig_nig` | **Wrong** | Criticized performing and nonaccrual are tagged |

**Class map.** The seed maps `us-gaap:CommercialPortfolioSegmentMember` to "ci". Most filers tag that segment as a *subtotal* above their classes, so the subtotal would be read as C&I. Most class members are extensions such as `fitb:`, `key:`, `tfc:` and `hban:`, which would bootstrap as unmapped and be left out. For CFG the seed maps `us-gaap:CommercialLoanMember` to "other_commercial" **and** the segment subtotal to "ci", which counts C&I twice.

**Axis order.** The segment and class axes both write to `dims["CLASS"]`. In all 15 relevant instances the class axis comes last, so the class wins. That is an ordering dependency, not a guarantee.

The threshold-engine `classes.py` has the same single-concept limitation, which is harmless for consumer classes. It would miss the commercial CQI totals for MTB, ZION and RF if it were reused.

---

## 7. COULD NOTs

1. **Re-run the threshold-engine quote check.** The producer of `out/quotes.json` is not in `docs/tie-out/peer-loan-classes-2026q2/`.
2. **Citibank NA's share of Citigroup commercial loans, and every bank-level versus holding-company commercial reconciliation.** No 10-Q states a legal-entity loan split. This would need the Call Report (FFIEC 031), which I did not pull.
3. **Basis statements for USB, PNC, TFC, KEY, FITB, HBAN, FCNCA, CFG, MTB and RF.** Not searched beyond confirming one principal bank each.
4. **Office split for USB and FITB in text.** Not found in the 10-Q text. USB may present property type in a graphic, which I cannot read from text extraction. FITB's non-owner-occupied CRE tables are by state only, and office appears only in the allowance narrative.
5. **Wells Fargo lease-class CQI totals.** Tagged only in vintage cells. No class-level total fact was found on the standard concept.
6. **Inline-XBRL cross-check.** Counts come from the EDGAR-extracted instances, not from the inline `ix:` facts in the .htm. For the threshold-engine consumer classes, the tie-out showed the two agree, 33 of 33 TIED.
