# A commercial version of the thresholds workbook: proposal (16 Oct 2026)

The answer to `COMMERCIAL-PROMPT.md`, which is on the `threshold-engine-book`
branch at 45d60b79. That branch is also where the consumer record this reads
from lives. **Nothing was built.** Every figure here was pulled live on 16 Oct
2026 from a public source. Where it was computed, the script that computed it
is in `docs/commercial-2026-10/`, and the research notes that hold every URL
are there too. A figure that was not checked is marked as not checked.

---

## 1. Recommendation

**Build a commercial book with the same command and the same method, on four
segments and two rated measures. Show the rest as context, and leave the
leading signals rated only on the bank's own data.**

- **Segments.** Start with four:
  - **C&I.**
  - **Nonfarm nonresidential CRE.** Split owner-occupied and other from 2007Q1;
    the industry split is only complete from 2008Q1.
  - **Multifamily.**
  - **Construction and land.**

  Together these are $54.5bn of KeyBank's $111.8bn book at 30 Jun 2026.
  **NDFI** ($21.4bn at KeyBank) has no loss or delinquency fields in the FDIC
  API. The Call Report form has carried NDFI past due and nonaccrual only since
  2024Q4. Show it as a balance and share, not a rated rate. Farmland and
  agricultural loans ($0.9bn at KeyBank) and leases ($2.0bn) can come later at
  no extra data cost: their fields exist and are confirmed.
- **Rated measures:**
  - **Nonaccrual rate, for every segment.** It is the measure the commercial
    data supports best:
    - industry history from 1991Q1;
    - the 1991 and 2009–10 stress periods are in it;
    - in all four segments the median is above zero, for the industry and for
      KeyBank, so the zero refusals do not fire.

    It is live now: **KeyBank's multifamily nonaccrual rate was 3.94% at
    2026Q2**, its highest since 2011Q4, against an industry median of 0.47%
    since 2006Q4.
  - **Net charge-off rate (TTM).** Rate it for C&I. For the three CRE segments,
    rate it **only on lines set from the industry's 1991–2026 history**:
    - since 2014, KeyBank's and most peers' CRE loss medians are at or below
      zero;
    - the method refuses a median at or below zero, and cannot put High
      anywhere meaningful when nearly every quarter is zero (§4, break 1).
- **Shown, not rated:**
  - **90+ past due.** For commercial loans it is a small fraction of
    nonaccrual (industry C&I median 0.10% against 0.76% nonaccrual, 2006Q4 on).
  - **30–89 past due.**
  - **Peers' criticized share** from their 10-Qs. 15 of 16 disclose it, but in
    three different shapes, and its public history has not been measured.
  - **CRE concentration.**
  - **SLOOS standards.**
- **Rated on internal data only, on site:**
  - **Criticized and classified share.**
  - **Rating migration.**
  - **Utilization.**

  These lead charge-offs, and the public data cannot rate them. The FDIC API
  has no C&I commitments field, and the peers' criticized definitions differ.
  Design the import now, as the consumer one was.
- **Sources:**
  - **The FDIC Call Report**, through the pull that already exists. Every field
    is confirmed in the FDIC's definitions and returns data, and `credit-suite`
    already tied four segments to filed Call Reports.
  - **The Fed's charge-off release**, as the cross-check, as for consumer.
  - **10-Q XBRL** for a Peer criticized tab, on the consumer `classes.py`
    pattern (a stated mapping per bank, with quotes checked by script). **Not**
    `edgar-crit-class-tracker` as it stands: it has never read a real filing.
    Run on the 16 real filings, it read nothing for 4 of them and would count
    C&I twice at Citizens.
  - **No paid data for v1.**
- **Peers.** The same 15 to start, with lines resting on the **median**, and
  the dollar composite beside it. The five large banks hold **63.8%** of the
  peer group's C&I and **68.4%** of its multifamily. Citi books 49% of its
  corporate loans outside North America, and Capital One's commercial book is
  small beside its card book. Both are weak commercial comparators; whether to
  keep them is the firm's call (§5, question 5).

**Found on the way, for the consumer book.** The same December 2024 revision
moved margin loans out of other consumer (RC-C 6.d). The consumer workbook's
other consumer balance (6.b + 6.d) steps down at:
- Bank of America in 2024Q4 ($44.4bn to $10.2bn);
- PNC in 2024Q4;
- JPMorgan in 2025Q1;
- Wells Fargo in 2025Q2.

Each fall is more than 25% (Bank of America −77%, JPMorgan −45%, PNC −35%,
Wells Fargo −27%), so the jump rule should leave out the windows holding
them. That was not checked in the built workbook. After the step, each rate
is over a different book. The bank disclosures were not checked either; the
timing fits the revision's best-efforts window. The consumer workbook should
label it.

---

## 2. The data table

"Checked" means fetched from the publisher on 16 Oct 2026 and read. Notes
with every URL are in `docs/commercial-2026-10/research-*.md`.

| Source | Holds for commercial | History | Frequency | Basis | Cost | Breaks | Checked? |
|---|---|---|---|---|---|---|---|
| **FDIC Call Report** (api.fdic.gov) | By segment: balance, charge-offs, recoveries, 30–89, 90+ and nonaccrual for construction (1-4 family vs other from 2007Q1), multifamily, nonfarm nonres (owner-occupied vs other from 2007Q1), farmland, C&I (non-U.S. addressees separately), agricultural, depository institutions, all other loans, leases. NDFI is a balance only. RC-L unused commitments: total, CRE, "all other". **On the form but not in the API:** leases retail vs commercial (2007Q1); C&I and financial-institution commitments (2010Q1); NDFI split five ways, NDFI past due and nonaccrual (2024Q4). Those would need the FFIEC's bulk Call Report files (not checked) | Balances 1984Q1; RE charge-offs 1990Q1 (KeyBank 1991Q1); 30–89 2001Q1 | Quarterly | Bank charter. Quarter-end stock; charge-offs year to date (quarterly fields also exist) | Free | 2007Q1 splits; NDFI 2010Q1; Dec 2024 NDFI reclassification; depository charge-offs end 2016Q4 (§3 Q4) | Yes. 197 fields probed, each against the FDIC's definitions file and a live query |
| **Fed charge-off and delinquency release** | C&I, CRE excluding farmland (one line: construction, multifamily and nonfarm nonres together), farmland, agricultural, leases. **No property-type split, no construction, no NDFI** | Charge-offs: C&I 1985Q1, CRE 1991Q1. Delinquency: C&I 1987Q1, CRE 1991Q1 | Quarterly | All insured commercial banks, from the Call Report. SA and NSA; all banks, 100 largest, others. Net charge-offs annualized over average loans; delinquency is 30+ plus nonaccrual | Free (XML zip; FRED CSV) | Small banks' C&I partly imputed before 2001; method revised June 2001; FAS 159 in 2008Q1 | Yes. 10 FRED IDs pulled; 4 guessed IDs do not exist |
| **SEC 10-Q / 10-K XBRL** (credit quality indicators) | Amortized cost by internal rating, by class and vintage | Not measured (§6) | Quarterly | Holding company; amortized cost | Free (User-Agent required) | Each bank names its own classes and members; the concept for totals differs at 4 of 16 | Yes, 16 of 16 latest 10-Qs (2026 Q2) |
| **SLOOS** | C&I standards and demand (large/middle vs small firms), spreads. CRE: one series 1990–2013, then construction, nonfarm nonres and multifamily from 2013Q4 | C&I from 1990Q2 | Quarterly | Net percentage of respondents; NSA; qualitative. July 2026 had 56 domestic respondents (target up to 80) | Free | CRE split at 2013Q4 | Yes |
| **Shared National Credit review** | Criticized and classified share of shared commitments of at least $100m, by lender type; nonaccrual; leveraged | Annual table 1989–2025 | Annual report (exams twice a year) | Commitments in shared credits only, not a whole book | Free (PDF only) | Threshold $20m before 2018; industry detail is five years only and went from 7 sectors to 21 in 2025 | Yes (2025 report: 8.6% of commitments criticized, 4.2% at U.S. banks) |
| **FR Y-9C** | Same categories as the Call Report at holding-company level; NDFI memo past dues | C&I 1986Q3; property types 1990Q3; splits 2007Q1; NDFI 2010Q1 | Quarterly | Consolidated holding company; filer threshold raised 2006, 2015 and 2018 | Free | Filer-set changes at each threshold | Partly. Chicago Fed bulk files 1986–2021Q1 downloaded. **COULD NOT** script the NIC download for 2021 onward (CAPTCHA, 403) |
| **Macro context** | CRE price index level (Fed Z.1, 1945 on; BIS has a method break at 1996); IMF CRE year-over-year % (2005 on); industrial production (1919 on); business bankruptcies (U.S. Courts F-2, PDF, Dec 2007 on) | as stated | Quarterly / monthly | Context, not loss rates | Free | **High-yield spread on FRED holds only three years** since April 2026 (ICE licensing) | Yes, except bankruptcies before 2007 |
| **Paid** | Trepp CMBS delinquency by property type; Green Street CPPI; CoStar prices and vacancy; MSCI RCA; KBRA; Moody's and S&P default studies | — | — | — | **No price published for any** | — | Partly: Trepp, S&P and CoStar could not be reached; Moody's 1920–2006 study is a free PDF |
| **The bank's own** | Rating by obligor and facility, criticized and classified, watch list, migration, commitments and utilization, NAICS, CRE property type, LTV, DSCR, nonaccrual and charge-offs by segment | Unknown until the bank says | — | On site only | — | Rating-scale changes, system migrations | Not seen, by rule. Import designed in §3 Q6 |

---

## 3. The six questions

### Q1. Which measures?

The test the brief sets: does the history hold a stress period, so the
method can set a High line? The number that answers it is the method's own.
High begins at median + z × spread of levels, and the method refuses when High
would begin beyond the worst quarter kept. So the **largest z a history
allows** is (worst − median) ÷ spread. It is the upper end of "What fits" on
Decide.

- A number near 1 or 2 means the worst quarter is barely unusual: High would
  sit almost on the ordinary range.
- A number in the hundreds means the spread is close to zero: most quarters
  are the same value, usually zero, so z has no meaning.

TTM net charge-off rate and quarter-end nonaccrual rate, as filed. These are
**not** built with the tool's merger, jump or repeated-year-to-date rules, so
they are indicative. The scripts are `commercial-2026-10/stress_stats.py` and
`stress_more.py`, and `stress_extra.py` for the past-due and zero-median
counts; their printed output is saved beside them.

| Segment | Measure | Industry worst since 2006Q4 (quarter) | Industry largest z, 2006Q4 on / 2014Q1 on | KeyBank median, 2014Q1 on | KeyBank largest z, 2006Q4 on / 2014Q1 on |
|---|---|---|---|---|---|
| C&I | Net charge-off | 2.49% (2010Q1) | 10.9 / **1.5** | 0.30% | 13.0 / 4.1 |
| C&I | Nonaccrual | 3.17% (2009Q3) | 8.1 / 2.4 | 0.60% | 10.9 / 2.7 |
| Nonfarm nonres | Net charge-off | 1.25% (2010Q4) | 7.8 / 3.9 | 0.11% | 14.8 / 2.4 |
| Nonfarm nonres | Nonaccrual | 3.89% (2010Q3) | 4.8 / 2.2 | 0.57% | 7.8 / 2.2 |
| Multifamily | Net charge-off | 1.33% (2010Q2) | 16.7 / 9.8 | **0.00%** | 458 / 215 |
| Multifamily | Nonaccrual | 4.26% (2010Q3) | 7.5 / 6.9 | 0.07% | 41.7 / 51.0 |
| Construction | Net charge-off | 6.48% (2010Q1) | 61.1 / 9.9 | **0.00%** | 76.4 / 14.8 |
| Construction | Nonaccrual | 15.05% (2010Q1) | 21.2 / 9.3 | 0.05% | 79.7 / 36.0 |

What it says, measure by measure:

1. **Net charge-off rate, C&I.**
   - **Enough history:** 2009–10 sits inside the FDIC window, and the median is
     above zero.
   - **2014 on, it cannot stand alone.** The industry's worst quarter since
     2014Q1 is the **latest**, 0.561% at 2026Q2, so a calm window allows a z of
     only 1.5.
   - **Where High comes from:** 2006 on (KeyBank, peers or industry), or the
     Fed's series back to 1985.
2. **Net charge-off rate, CRE (all three segments).**
   - **The method breaks.** Since 2014, KeyBank's TTM median is 0.004%
     (construction), −0.00001% (multifamily) and 0.11% (nonfarm). Of the 16
     banks, 12 have a multifamily median at or below zero (8 below) and 14 a
     construction median at or below zero (10 below); for nonfarm, 1 of 16.
   - **Refused or meaningless.** The method refuses a median at or below zero.
     Where it does not refuse, the spread is so small that the largest z runs
     into the hundreds.
   - **Proposal:** lines from the industry's history from 1991, which holds the
     early-1990s CRE losses and 2009–10. Rate KeyBank, peers and industry on
     those lines.
3. **Nonaccrual rate, every segment.**
   - **Works:** the median is above zero everywhere, the history runs from
     1991Q1, and 2009–10 is in every segment.
   - **Lumpy for KeyBank's smaller books.** Its multifamily nonaccrual median
     since 2014 is 0.07%, so one loan moves it.
   - **Recommend:** the lead measure for CRE.
4. **90+ past due accruing.** Commercial loans that stop paying mostly go to
   nonaccrual, not 90+ accruing. Industry medians since 2006Q4 are 0.10% (C&I),
   0.07% (nonfarm) and 0.05% (multifamily), against nonaccrual's 0.76%, 1.01%
   and 0.47%. **Show, do not rate.**
5. **30–89 past due.** It exists from 2001Q1, so the 1991 stress is not in it.
   For commercial loans it mixes in administrative past dues (matured loans
   awaiting renewal); that is a known feature of the measure, but its size was
   **not checked**. **Show, do not rate**, unless the firm wants it.
6. **Criticized and classified share.**
   - **Public view:** 15 of 16 holding companies tag it for commercial classes
     (not Citi), but in three shapes:
     - 8 tag special mention and substandard separately;
     - 4 tag criticized split accrual and nonaccrual;
     - 3 tag pass and criticized only.
   - **History not measured.** How many quarters each bank has tagged was not
     checked (§6). If it starts with the credit-quality disclosures banks began
     around 2011 (ASU 2010-20; its dates not checked), it holds no 2009
     stress.
   - **Recommend:** rate it on the bank's internal history. Show peers' latest
     quarters beside it as context, with each bank's own words.
7. **Migration.** Internal only; no public source. Rate it on internal history
   if the bank has it through 2009–10. Otherwise show it, unrated.
8. **Utilization.** The FDIC API has no C&I commitment field: it puts commercial
   lines in "all other" (KeyBank: $60.9bn of $78.3bn unused). The Call Report
   form has split C&I commitments out since 2010Q1 (74 FR 68314). A public
   utilization rate (C&I balance over balance plus unused C&I commitments) is
   therefore possible from the FFIEC's bulk files, which were not checked.
   Internal first; public as a later addition.
9. **Concentration.** Show only, from the Call Report:
   - CRE over capital, as `credit-suite` already computes it (`CRECONR`);
   - NDFI share;
   - each segment's share of the book.

   The agencies' 2006 CRE concentration guidance sets supervisory criteria. It
   was **not read** for this proposal, so no figure from it is quoted here; if
   the firm wants its criteria on the tab, they must be taken from the Federal
   Register text and cited.
10. **Growth.** The consumer book-size view, carried over, with acquisitions
    taken out. Show only.

### Q2. Which segments?

The public data sets the floor, and peers' 10-Qs cannot go finer than it:

| Split | Call Report (bank) | Peers' 10-Q XBRL (16) |
|---|---|---|
| C&I | Yes (non-U.S. addressees separately) | 15 of 16 by internal rating |
| CRE owner-occupied vs other | From 2007Q1 (industry complete 2008Q1) | 4 of 16 in the credit-quality table |
| Construction | Yes; 1-4 family vs other from 2007Q1 | 6 of 16 as its own class |
| Multifamily | Yes | 1 of 16, partly (JPMorgan) |
| Office | **No** | **0 of 16 in XBRL**; printed in text at 12, office criticized at 4 |
| NDFI | In the API, balance only, from 2010Q1 (the form adds a five-way split, past due and nonaccrual from 2024Q4) | Not checked as a class |
| Leases | In the API, **no commercial vs consumer split** (the form has one since 2007Q1) | 5 of 16 as their own class |

Recommendation: the four segments in §1, with nonfarm split into
owner-occupied and other wherever the source has it. **Office is the split
everyone wants and no public machine-readable source has.** It can come from
the bank's own data, and for peers only as printed text, read and quoted the
way the consumer Peer loan classes tab reads student loans.

### Q3. Which peers, and weighted how?

- **Who:** keep the 15 for v1. Every one files every commercial category,
  the pull and the merger record already exist, and one roster across both
  books keeps "the peer group" one thing.
- **Weak comparators.** Name them on the Peers tab, and let the firm decide
  whether to drop them:
  - **Citi:** 49% of corporate loans booked outside North America; the bank
    charter is a small part of the holding company.
  - **Capital One:** $91.3bn commercial beside a card book that now includes
    Discover.
  - **First Citizens:** SVB from 2023. Its commercial book changed character,
    and its largest z for C&I charge-offs since 2006 is 1.3.
- **Weighting:** offer both, and rest the lines on the **median** when the
  peers lead. At 30 Jun 2026 the five large banks hold 63.8% of the peer
  group's C&I, 49.1% of its nonfarm nonres, 68.4% of its multifamily and 47.2%
  of its construction. A dollar composite of C&I is mostly JPMorgan, Bank of
  America, Wells and Citi.
- **A commercial peer group chosen by book mix** (CRE share, NDFI share)
  would compare like with like, but it is a new roster to check and maintain.
  It is a decision for the firm (§5, question 5), not a v1 default.

### Q4. Which breaks?

Every item below was read in a primary source: a Federal Register notice, an
FDIC or Fed publication, an SEC 8-K, or the FDIC's structure history. The
exception is anything marked *not checked*. The full tables, with sources and
what each event does to each category, are in
`commercial-2026-10/research-breaks.md`. Its "Handling" column is blank for the
firm; what is written here is my proposal.

**Reporting and definition changes**

| Quarter | Event | Categories | Proposed handling |
|---|---|---|---|
| 2007Q1 | Construction split 1-4 family / other; nonfarm split owner-occupied / other (RC-C, RC-N, RI-B); real estate commitments split; leases split retail / commercial (71 FR 8649) | Construction, nonfarm, leases | Totals are continuous, so rate the totals throughout and the splits from 2007Q1. **The industry's splits are incomplete until 2008Q1**: about 2,400–3,000 small filers report 0/0 in 2007. Savings banks filing the TFR never report the owner-occupied split, until TFR filing ended in 2011. Label both |
| 2008Q1 | Loans a bank classifies as trading leave RC-C | All, syndicated C&I most | Label; its size was not measured |
| 2009Q1 | "Secured by real estate" means collateral worth more than 50% of principal at origination; new loans only (74 FR 5028) | Real estate vs C&I | Label; it is gradual by construction, and no single quarter breaks |
| 2010Q1 | NDFI becomes RC-C 9.a, split out of "other loans" (**not** out of C&I). RC-L "other" commitments split into C&I, financial institutions and all other (74 FR 68314). FAS 166/167: "most non-consumer loan categories were not affected" (FDIC) | All other loans, RC-L | Label. The industry's C&I still fell $34.3bn that quarter; the cause was not traced |
| 2011Q1 | Construction loans stay in construction after completion while repayment depends on a sale (76 FR 5253) | Construction | Label |
| 2013Q2 | The largest 031 filers report the real estate breakdown for the whole bank, not only domestic offices | Real estate, 031 filers | Whether the FDIC fields moved: not checked. Check for the roster banks before building |
| 2018Q2 | Every bank of $100bn or more files the 031 | Field availability | Which roster banks switched: not checked. The tie-out resolver must handle both forms |
| 2020Q1 | CECL: the purchased-credit-impaired nonaccrual exception is not carried over to PCD loans | Nonaccrual at acquirers | Label; a nonaccrual step is possible at banks holding acquired books |
| 2020Q1 | Revolving-line drawdowns: industry C&I +$339.4bn (15.4%) | C&I | Not a definition change, but it trips the 25% jump at several roster banks (JPMorgan C&I +31%). Let the rule leave those windows out |
| 2020Q2 | **PPP**: $482.2bn of PPP loans, reported in C&I | C&I | Trips the jump (First Citizens +80%, Zions +37%). PPP loans also sit in the C&I denominator through 2021 and lower its rates. Leave out where the rule fires; label 2020Q2–2021Q4 |
| 2020Q2 on | CARES Act deferrals not reported as past due | Past due | Label 2020–21 on past-due series |
| 2023Q1 / 2024Q2 | Troubled-debt-restructuring accounting ends | Memoranda only | None needed |
| **2024Q4–2025Q2** | **NDFI and margin-loan revision** (31 Dec 2024; best efforts until 30 Jun 2025, so the break is **spread over three quarters**). Broker-dealer and fund loans move into NDFI; every securities-based margin loan moves to "loans for purchasing or carrying securities", out of C&I and out of other consumer (6.d). New on the form: NDFI split five ways (banks over $10bn), **NDFI past due and nonaccrual (RC-N Memo 9)**, RC-L NDFI commitments | C&I, NDFI, all other loans, other consumer, RC-L | KeyBank C&I −29% (2024Q4) and Citizens −32% trip the jump; U.S. Bank's C&I steps down in 2025Q1 and PNC's in 2025Q2. Label all three quarters on every C&I series, and let the rule leave out what it catches. **None of the new NDFI items is in the FDIC API** (checked against both definitions files) |

On the brief's lesson 4:
- **The FDIC's data shows the $56bn.** Industry "other revolving credit plans"
  (RC-C 6.b) fell $55.7bn from 2024Q3 to 2024Q4.
- **No published source gives a figure for that move.** The $56bn in the
  agencies' notice is a different number: the level of NDFI loans in March
  2010, when the line was created (88 FR 89491). The Fed's H.8 estimates $41.2bn
  out of "credit cards and other revolving plans" in the week of 1 Jan 2025.
- **What touched consumer was the margin-loan part of the revision, not
  NDFI.** The FDIC's description says margin loans to individuals came out of
  other consumer (6.d). It does not mention 6.b, and no source found names the
  6.b move: it is seen in the data, not explained.

**Acquisitions into the roster since 2006**

- **Already in the record.** The repository's merger record, pulled live from
  FDIC history and re-pulled today, matches the test fixture for all 16
  certificates. Every bank-to-bank deal is in it, among them:
  - Wells/Wachovia 2010Q1;
  - PNC/National City 2009Q4, RBC 2012Q1, BBVA 2021Q4 and FirstBank 2026Q2;
  - Truist/SunTrust 2019Q4;
  - U.S. Bank/MUFG Union 2023Q2;
  - KeyBank/First Niagara 2016Q4 (**80% of KeyBank's CRE**);
  - Fifth Third/MB 2019Q2 and **Comerica 2026Q1** (107% of its CRE);
  - Huntington/FirstMerit 2016Q3, TCF 2021Q2, Veritex 2025Q4 and
    **Cadence 2026Q1**;
  - M&T/People's United 2022Q2;
  - Citizens/Investors 2022Q2 (multifamily +994%);
  - First Citizens/CIT 2022Q1 and SVB 2023Q1;
  - JPMorgan/First Republic 2023Q2.

  **Handling:** combine pro forma, as for consumer. Commercial books make the
  pro forma matter more than consumer did: several targets were as large as
  the acquirer's own commercial book (SunTrust 132% of Truist's C&I; National
  City 130% of PNC's CRE).
- **Not in the record:**

  | Deal | Quarter | Why the record misses it | What it does | Proposed handling |
  |---|---|---|---|---|
  | JPMorgan / Washington Mutual Bank | 2008Q3 | A failure with no FDIC history row naming JPMorgan; only WaMu's savings bank ($20.6bn) is recorded | The 5% rule sees 4.3%; pro forma cannot be built | Leave out JPMorgan's windows across 2008Q3, with the reason |
  | M&T / Wilmington Trust | 2011Q2 | Recorded as a branch purchase (code 712) | M&T construction +19%, nonfarm +16%: under both rules, so two books mix | Leave out, with the reason; add a stated-acquisitions list to the record for deals the FDIC codes as branch purchases |
  | Wells Fargo / GE Capital commercial lending and leasing | 2016Q1 | An asset purchase, with no bank charter | $26.7bn of C&I and leases; leases +56% trip the jump, C&I +14% slips past both rules | Leave out, with the reason |
  | Capital One / GE Healthcare Financial Services | 2015Q4 | Asset purchase | Nonfarm +49%, C&I +21% | Leave out, with the reason |
  | Huntington / Macquarie Equipment Finance | 2015Q1 (close date not checked) | Asset purchase | Leases +53% | Leave out, with the reason |

  So the 25% and 5% rules, built for consumer, **miss commercial asset
  purchases**. Propose a stated list of acquisitions by bank, quarter and
  source (an 8-K), read by the build like the FDIC record.
- **Unexplained moves.** A scan found 302 bank-quarters where a commercial
  category moved more than 25%. 87 of them are explained neither by a
  recorded merger nor by a reporting change: `breaks-jumps.tsv`, causes not
  checked (for example Truist leases −49% in 2022Q1, First Citizens C&I −40%
  in 2012Q4). Loans to depository institutions swing at every large bank,
  which is one more reason to leave that category out. No commercial loan sale
  was found with a primary source.

### Q5. How is each figure tied out?

The consumer standard is a figure read out of the built workbook in Excel and
set against the filed document, through a different fetch and a different
parser, with the denominator. One figure per source:

| Source | The figure | Traced to | Note |
|---|---|---|---|
| FDIC Call Report | KeyBank C&I nonaccrual rate, 2026Q2: `NACI` ÷ `LNCI` | RC-N C&I line, column C, over RC-C C&I, on KeyBank's filed Call Report (FFIEC CDR page and XBRL) | **Watch the form.** On the FFIEC 031, C&I is split into U.S. and non-U.S. addressees; on the 041 it is one line. `credit-suite` found 63 values wrongly reported as uncheckable because the 031 codes were cited for 041 filers (`credit-suite/docs/tie-out/SECOND-PASS-2026-09-08.md`, F1). `credit-suite` has already tied C&I, construction, nonfarm and multifamily; reuse its resolver |
| Fed release | Industry C&I net charge-off rate, one quarter | The Fed's own release table (the HTML page, photographed), as the consumer card tie-out did | FDIC quarterly flows over the average of two quarter-ends differ from the Fed by at most 0.114 points on C&I and 0.169 on CRE since 2006. That is consistent with the Fed's different average-loans denominator, but the cause was **not checked**. A cross-check, not a tie |
| 10-Q XBRL | KeyCorp criticized C&I, 2026 Q2 | The 10-Q table as filed (inline XBRL, fetched fresh, a second parser), photographed | Every quote checked against the filed text by script, and every "not stated" a search. **The consumer quote-check script is missing from its tie-out folder**, so it cannot be re-run from the record. Restore it first |
| SNC | 2025 criticized share of commitments, 8.6% | The page of the 2025 report PDF, photographed | Context only |
| SLOOS | One net percentage (C&I standards, large and middle firms) | The release table | Context only |
| FR Y-9C | KeyCorp HC-C C&I, one quarter | Chicago Fed file (to 2021Q1) against the NIC facsimile | **COULD NOT** reach NIC by script. Only if Y-9C is used at all; v1 does not need it |

### Q6. What would the workbook look like?

The same book command, a second book file (`books/commercial-public.json` and
its series CSV), and the same tabs: **Decide, Summary, Peers, Thresholds,
Lines by source, Internal**, and the reference tabs. On those:

- **Segments × measures:** 4 × 2 rated (net charge-off and nonaccrual) = 8 rows
  on Decide.
- **Shown measures:** 90+, 30–89, 90+ including nonaccrual and 30+ including
  nonaccrual on the Peers tab, as consumer shows delinquency.
- **Sources:** industry, peer group and KeyBank, as now. Construction,
  multifamily and nonfarm net charge-off rows start with **Lines set from:
  Industry** suggested and still blank, because the firm picks.

What commercial needs that consumer did not:

| Tab | What it holds | Source |
|---|---|---|
| **Peer criticized** | Each peer's latest criticized share by class, in that bank's own categories (8 SM/substandard, 4 accrual/nonaccrual, 3 pass/criticized), with the filing's words; no cross-bank composite where the shapes differ | 10-Q XBRL, the `classes.py` pattern |
| **Concentration** | CRE ÷ capital, NDFI share, segment shares, per bank and quarter | Call Report |
| **Criticized (internal)** | The bank's criticized and classified share by segment, rated on its own history | Internal import |
| **Migration (internal)** | Grade-to-grade matrix per quarter, dollars and count; ships empty | Internal import |

**The internal import**, on the `INTERNAL-IMPORT.md` pattern ($ thousands,
segments, every column stated, refused when not whole, no identifiers):

- **One file of segment aggregates.** Segments: C&I by NAICS sector as the
  bank chooses, CRE by property type, construction, NDFI, leases. Columns:
  - balance and commitments;
  - pass, special mention, substandard, doubtful and loss;
  - nonaccrual, 30–89 and 90+;
  - gross charge-offs and recoveries;
  - LTV and DSCR buckets for CRE.
- **A second file for migration:** quarter, from grade, to grade, dollars and
  count.
- **Obligor-level data never travels.** It is aggregated on site before the
  file is written, as account-level data is for consumer.
- **The reconciliation:** filed less named exclusions against internal, per
  segment. The import also has to ask which Call Report line each internal
  segment maps to, because a bank's commercial segments rarely match RC-C
  (KeyBank's C&I lost $12.0bn to NDFI in 2024Q4, and owner-occupied CRE may sit
  in C&I internally).

---

## 4. Where the method breaks, and what I propose

1. **Loss series that are mostly zero.**
   - **What happens:** CRE net charge-off medians since 2014 are at or below
     zero for KeyBank (construction, multifamily) and for most peers. The
     method refuses ("the median is at or below zero"). Where it does not
     refuse, the robust spread is near zero, so High's z stops meaning
     anything.
   - **Propose:** do not change the method in v1. Rate CRE charge-offs on lines
     set from the industry's 1991–2026 history, and lead CRE with nonaccrual.
     A different High rule for zero-heavy series (a percentile, or the
     industry's worst quarters) would be a second scale; the firm retired a
     second scale on 12 Oct 2026, so that is theirs to reopen.
2. **Calm windows.**
   - **What happens:** since 2014 the industry's worst C&I loss quarter is the
     latest one.
   - **Propose:** for any measure whose lines come from 2014 on (the bank's
     internal history, most likely), High comes from industry or peers through
     2009–10, as the consumer synthesis already does.
3. **Big banks drive the composite.** Covered in §3 Q3. Propose the median.
4. **Reclassifications that look like credit events.**
   - **What happens:**
     - KeyBank's C&I fell from $41.9bn to $29.9bn in 2024Q4 as $12.0bn moved
       to NDFI: a 28.6% drop.
     - The industry's C&I fell $128.5bn that quarter, and the revision was
       spread over 2024Q4–2025Q2.
     - 2020 added two non-definitional jumps to C&I: revolver drawdowns
       (+15.4% for the industry) and PPP ($482.2bn).
   - **What already copes:** the 25% jump rule leaves out KeyBank's four
     windows across 2024Q4. The industry's C&I moved −5.0%, well under 25%.
   - **Propose:**
     - label 2024Q4–2025Q2 and 2020Q1–2021Q4 on every C&I series;
     - leave the four windows out where the rule fires;
     - do not combine C&I and "all other loans" to bridge the break. In 2024Q4
       "all other loans" excluding NDFI also rose $161.9bn, in the same quarter
       that other consumer loans fell $81.5bn.
5. **Blended lines.**
   - **What happens:**
     - Nonfarm nonres mixes owner-occupied (repaid from the occupant's
       business) with investor CRE until 2007Q1.
     - No public source splits office.
     - In the FDIC API, leases mix consumer and commercial; the form splits
       them from 2007Q1.
   - **Propose:** rate owner-occupied and other separately from 2007Q1 (the
     industry from 2008Q1), and the total before that. Leave leases out of v1.
     Office comes from internal data, and for peers from quoted text.
6. **Agents miss sentences, and tools that were never run on real data.**
   - **What happens:** `edgar-crit-class-tracker` has only ever been tested on
     fixtures. Run on the 16 real 10-Qs:
     - it found nothing for M&T, Regions, Zions and Citi;
     - it dropped Capital One's criticized cells;
     - two of its labels are wrong, and its class map would count C&I twice at
       Citizens.
   - **Propose:** read peers' commercial classes in threshold-engine on the
     `classes.py` pattern, with a stated mapping per bank, every amount read
     from the tagged members, and every quote and "not stated" checked by
     script. Use the tracker's research as leads only. Its own repair is a
     separate decision for the consulting line, not this build.
7. **Holding company is not bank.**
   - **What happens:**
     - Criticized shares come from 10-Qs, which report the holding company;
       rates come from Call Reports, which report the bank.
     - The gap is largest at Citi (49% of corporate loans booked outside North
       America, plus broker-dealers).
   - **Propose:** never put a 10-Q numerator over a Call Report denominator.
     The Peer criticized tab states the holding company basis on every row.
8. **Small books are lumpy.**
   - **What happens:** KeyBank's farmland is $119m and its depository loans
     $1.6m, and one loan moves a rate.
   - **Propose:** the peers' minimum book is now 0, by the analyst's ruling of
     15 Oct. A commercial minimum per segment is the firm's to set (§5, question 12).
9. **The FDIC's quarterly fields are not always year-to-date differences.**
   - **What happens:** KeyBank 2004Q4 C&I gross charge-offs: 15,814 in the
     quarterly field, against 20,715 by differencing.
   - **Propose:** keep the consumer method (difference year to date, take off
     repeated year to date after absorptions, read push-down restarts as the
     quarter's flow), and do not use the FDIC's `…Q` fields.
10. **Rate fields that are not loss rates.** The FDIC's `NT*R` and `NT*QR`
    divide by average total assets, not the loan book (KeyBank C&I: 0.11
    against 0.58). Never read a rate from the API; compute it from the dollar
    fields, as consumer does.

---

## 5. The decisions that are the firm's

Each question can be answered in one line. Each recommendation is mine.

**Answered so far.** Question 13, by the firm on 16 Oct 2026: *"Definitely
mark reporting changes."* This came after a discussion of why banks' C&I
differs even on the Call Report: there is one definition, but loans are
classified by collateral and borrower, with judgement at the edges.

- **What it covers.** Every reporting change in §3 Q4 is labeled on every
  series it touches, not just the C&I ones, in the quarter it took effect.
  That includes changes spread over several quarters, such as the
  2024Q4–2025Q2 revision.
- **The consumer book.** Its other consumer step in 2024Q4–2025Q2 falls under
  the same answer.
- **What it does not cover.** The 2020 drawdowns and PPP are not reporting
  changes. They stay open as question 15, together with leaving out the
  windows the 25% rule catches.

| # | Question | If yes | If no | Recommend |
|---|---|---|---|---|
| 1 | Start with four segments (C&I, nonfarm nonres split owner-occupied and other, multifamily, construction)? | 8 rated rows; farmland, agricultural loans and leases later | Name the others to add; each is a field list away | **Yes** |
| 2 | Rate CRE net charge-offs on lines set from the industry's 1991–2026 history? | KeyBank and peers rated on industry lines; the pull goes back to 1991Q1 | Leave CRE charge-offs shown and unrated | **Yes** |
| 3 | Lead CRE with the nonaccrual rate rather than net charge-offs? | Nonaccrual is the first CRE row on Decide | Charge-offs first, nonaccrual second | **Yes** |
| 4 | Rest peer lines on the median, with the dollar composite beside it? | Each bank counted once | The big five set peer lines | **Yes** |
| 5 | Keep the same 15 peers for commercial? | One roster; Citi, Capital One and First Citizens labeled as weak comparators | A commercial roster by book mix, to be chosen and checked | **Yes, for v1** |
| 6 | Pull commercial history from 1991Q1, not 2006Q1 as for consumer? | The early-1990s CRE losses are in it; splits still start 2007Q1 | 2006 on, like consumer; CRE High rests on 2009–10 alone | **Yes** |
| 7 | Rate criticized and classified on internal history only, and show peers' figures as context? | No peer lines for criticized | Peer lines from mixed definitions (3 shapes across 15) | **Yes** |
| 8 | Read peers' commercial classes in threshold-engine on the `classes.py` pattern, instead of fixing `edgar-crit-class-tracker`? | One reader, tied out the consumer way | Repair the tracker first, then reuse it | **Yes** |
| 9 | Buy any paid data for v1? | Name the source; I report what it adds before purchase | Public data only | **No** |
| 10 | Rate SLOOS standards? | A leading measure on Decide | Shown as context only | **No (context only)** |
| 11 | Build commercial as its own book file, not more rows in the consumer book? | Two workbooks, one command | One larger workbook | **Own book** |
| 12 | What minimum book size, per segment, keeps a bank-quarter in? | Your figure | 0, as for consumer peers | **Your number; I have no basis to propose one** |
| 13 | Label every reporting change (§3 Q4: the definition and form changes, among them the NDFI and margin-loan revision of 2024Q4–2025Q2) on the series it touches? | Labeled in the quarter it took effect | Unlabeled | **Answered, 16 Oct 2026: yes** |
| 14 | Add a stated list of acquisitions the FDIC record cannot see (JPMorgan/WaMu, M&T/Wilmington Trust, and asset purchases such as Wells/GE Capital), each with its 8-K, read by the build like the FDIC record? | Those windows are left out with a reason | They stay in, with two books mixed | **Yes** |
| 15 | Also label 2020Q1–2021Q4 on C&I (revolver drawdowns and PPP: not definition changes, but they move the book), and leave out the windows the 25% rule catches across both periods? | Labeled; windows left out where the rule fires | Unlabeled; the rule alone decides what is left out | **Yes** |

---

## 6. What I did not check

1. **How far back peers' criticized tagging goes.** Only the latest 10-Q per
   bank was read. Until the history is counted, the claim that it cannot rate
   High is a reasoned expectation, not a finding.
2. **The FFIEC supplemental instructions:** ffiec.gov refused access, so where
   PPP loans are reported was read from the FDIC's profile, not the
   instructions. Also not checked:
   - FIL-84-2024 (page not found);
   - whether the 2025 proposal on modification reporting was finalized;
   - three holding-company close dates (Wells/Wachovia, PNC/National City,
     BofA/LaSalle);
   - the causes of the 87 unexplained moves;
   - what moved the industry's C&I in 2010Q1.
3. **NDFI in the FFIEC bulk files.** The form carries NDFI past due and nonaccrual
   from 2024Q4 (RC-N Memo 9), C&I commitments from 2010Q1 and the lease split
   from 2007Q1, none of them in the FDIC API. The FFIEC bulk download was not
   reached, and whether RI-B has an NDFI charge-off line was not checked.
4. **Where depository-institution charge-offs went after 2016Q4.**
5. **The stress table in §3 Q1 with the tool's own rules** (pro forma mergers,
   the jump rule, repeated year to date). It is computed as filed and is
   indicative.
6. **The Fed and FDIC difference** (up to 0.114 points, C&I, since 2006): the
   cause was not traced.
7. **Administrative past dues in commercial 30–89:** their size.
8. **The 2006 interagency CRE concentration guidance:** not read.
9. **FR Y-9C after 2021Q1:** **COULD NOT** script NIC (CAPTCHA). Y-9C against the
   Call Report, line by line: not checked.
10. **Paid sources:** no price published. Trepp, S&P and CoStar could not be
    reached; their descriptions are second-hand.
11. **Holding company against bank for the 10 regionals:** not searched beyond
    one principal bank each.
12. **Whether KeyBank files the FFIEC 031 or 041** for the C&I tie-out: not
    checked; the resolver handles both.
13. **Inline XBRL against the extracted instance** for the 10-Q counts: counted
    from instances only.
14. **The tool's industry merger corrections on commercial series.** The
    absorbed-bank repeat and push-down fixes were proven on card against the
    QBP. They have not been run on commercial categories.
