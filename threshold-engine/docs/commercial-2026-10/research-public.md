# Public data sources for commercial-loan risk-rating thresholds — checked against source

Research date: 16 Oct 2026. Every row below was fetched from the source on that date with curl (through the agent proxy) unless it is marked otherwise.
Labels: **VERIFIED** means it was read on the source page or file. **SECONDARY** means it came only from a search-engine summary or third-party page. **NOT CHECKED** means it was not looked at. **COULD NOT** means a fetch was tried and failed, with the reason given.
Downloaded working files are in `(working file, not kept)`.

---

## 1. Federal Reserve: Charge-Off and Delinquency Rates on Loans and Leases at Commercial Banks

URLs: https://www.federalreserve.gov/releases/chargeoff/ (index), `about.htm`, and the tables `chgallsa.htm`, `chgallnsa.htm`, `delallsa.htm`, `delallnsa.htm`, `chgtop100{sa,nsa}.htm`, `deltop100{sa,nsa}.htm`, `chgother{sa,nsa}.htm`, `delother{sa,nsa}.htm`. The index page shows "Last update: August 25, 2026", and its latest quarter is 2026:2.

| Item | Finding (VERIFIED unless noted) |
|---|---|
| Table columns | Real estate loans: **All**; then "Booked in domestic offices": **Residential**, **Commercial**, **Farmland**. Consumer loans: All, Credit cards, Other. **Leases**. **C&I loans**. **Agricultural loans**. Total loans and leases. |
| CRE definition (footnote 2) | "Commercial real estate loans include construction and land development loans, loans secured by multifamily residences, and loans secured by nonfarm, nonresidential real estate." **No split by property type, and no separate construction series.** Construction, multifamily and nonfarm nonresidential are all inside one "Commercial" line. NDFI is not shown separately. |
| Size cuts | All banks; the 100 largest ("measured by consolidated foreign and domestic assets", adjusted for mergers); Other ("smaller than the 100 largest"). Each comes SA and NSA. |
| Basis | "Banks are insured U.S.-chartered commercial banks." The data are **bank level, from the Call Report** (FFIEC 031–034 for 1985–2000, FFIEC 031 and 041 from 2001). They are **not holding-company level**. |
| Charge-off rate | Net charge-offs (gross minus recoveries) during the quarter, a **flow**, divided by the **average** loans for the quarter. "Multiplied by 400" means it is **annualized**. RI-B is the numerator; RC-K gives the average, allocated with RC-C. |
| Delinquency rate | 30+ days past due and still accruing, **plus nonaccrual**. It is a % of **end-of-period** loans (a quarter-end stock). RC-N is the numerator and RC-C the denominator. |
| History, charge-offs | Total, C&I, agricultural, leases, consumer and RE-All begin **1985:1**. RE Residential, **Commercial** and **Farmland** (domestic offices) begin **1991:1**; they are "n.a." for 1985–1990. |
| History, delinquency | Total loans begins **1985:1**. C&I, agricultural, leases, RE-All and consumer-All begin **1987:1**. RE Residential, **Commercial**, **Farmland**, credit cards and other consumer begin **1991:1**. |
| Breaks / definition notes | (a) Before Mar 2001, small banks filing the 033/034 forms could report charge-offs and delinquencies using internal loan classifications. The Fed imputed C&I versus other loans from 032-bank ratios and handled agricultural loans by assumption, so **pre-2001 C&I and agricultural figures are partly estimated** (about.htm). (b) Series revised on 13 Jun 2001 under the new method. (c) **2008:1 is affected by FAS 159** fair-value-option adoption, an effect described as "presumably small". (d) **1999:Q3 residential and commercial mortgage delinquency is "partially estimated"** because of a reporting problem. (e) The data are adjusted for mergers. |
| Free or paid | Free. |
| Scripted pull | Whole-release XML zip: `https://www.federalreserve.gov/releases/chargeoff/data/FRB_CHGDEL_xml.zip`, which 301-redirects to `/releases/chgdel/data/FRB_CHGDEL_xml.zip` and contains `CHGDEL_data.xml` and `CHGDEL_struct.xml` (downloaded, 280 KB). **Announcement on the page:** "During the week of November 9, the 'Build Your Package' feature in the Data Download Program (DDP) will be removed in preparation for the eventual retirement of the DDP", and users are pointed to FRED. A key-free FRED CSV works: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>`. The FRED JSON API needs an `api_key` (confirmed: it returns error 400 without one). |

**FRED series IDs.** All belong to FRED release rid=231. Each was fetched as CSV on 16 Oct 2026. Suffixes: ACBS = all banks SA; ACBN = all banks NSA; T100S/T100N = 100 largest; OBS/OBN = other banks.

| Category | Charge-off SA / NSA | First obs | Latest (2026-04-01 = 2026:Q2) | Delinquency SA / NSA | First obs | Latest 2026:Q2 |
|---|---|---|---|---|---|---|
| C&I ("Business Loans" in the FRED title) | CORBLACBS / CORBLACBN | 1985-01-01 | 0.58 / 0.58 | DRBLACBS / DRBLACBN | 1987-01-01 | 1.27 / 1.24 |
| CRE excl. farmland, domestic offices | CORCREXFACBS / CORCREXFACBN | 1991-01-01 | 0.14 / 0.15 | DRCRELEXFACBS / DRCRELEXFACBN | 1991-01-01 | 1.53 / 1.50 |
| Farmland, domestic offices | CORFLACBS / CORFLACBN | 1991-01-01 | 0.02 / 0.01 | DRFLACBS / DRFLACBN | 1991-01-01 | 1.33 / 1.34 |
| Agricultural production loans | CORLAGACBS / CORLAGACBN | 1985-01-01 | 0.15 / 0.17 | DRFAPGACBS / DRFAPGACBN | 1987-01-01 | 1.10 / 1.10 |
| Lease financing receivables | CORLFRACBS / CORLFRACBN | 1985-01-01 | 0.41 / 0.36 | DRLFRACBS / DRLFRACBN | 1987-01-01 | 1.19 / 1.10 |
| Total loans and leases | CORALACBS | 1985-01-01 | 0.55 | DRALACBS | 1985-01-01 | 1.42 |
| C&I, 100 largest / other (SA) | CORBLT100S / CORBLOBS | 1985-01-01 | 0.60 / 0.47 | DRBLT100S / DRBLOBS | 1987-01-01 | 1.17 / 1.85 |
| CRE, 100 largest / other (SA) | CORCREXFT100S / CORCREXFOBS | 1991-01-01 | 0.16 / 0.10 | DRCRELEXFT100S / DRCRELEXFOBS | 1991-01-01 | 1.70 / 1.27 |

The FRED release tables also list these IDs (fetched, not each pulled): CORFLT100S/N, CORLFRT100S/N, CORLAGT100S/N, CORCREXFT100N, CORBLT100N, CORFLOBS/N, CORLFROBS/N, CORLAGOBS/N, CORCREXFOBN, CORBLOBN, DRFLT100S/N, DRLFRT100S/N, DRFAPGT100S/N, DRCRELEXFT100N, DRBLT100N, DRFLOBS/N, DRLFROBS/N, DRFAPGOBS/N, DRCRELEXFOBN, DRBLOBN. They follow the same pattern.
The NSA values match the Fed's own NSA table for 2026:2 (C&I delinquency 1.24, CRE delinquency 1.50).
**Guessed IDs that do NOT exist** (FRED returned 404): CORBLNACBS, DRBLNACBS, CORCREXFNACBS, DRCRELEXFNACBS, CORAGACBS, DRAGACBS, CORCRET100S, DRCRET100S.

---

## 2. Senior Loan Officer Opinion Survey (SLOOS)

URLs: https://www.federalreserve.gov/data/sloos.htm, https://www.federalreserve.gov/data/sloos/about.htm, https://www.federalreserve.gov/data/sloos/sloos-202607.htm, https://www.federalreserve.gov/data/sloos/sloos-202607-chart-data.htm

| Item | Finding |
|---|---|
| What it holds for commercial lending | Net % of domestic banks tightening standards, and reporting stronger demand, for C&I loans to **large and middle-market firms** and to **small firms**. Spreads and terms series. CRE standards and demand: **"All"** through 2013:Q3, then separately **"Construction and land development"**, **"Nonfarm nonresidential"** and **"Multifamily"** (chart data). |
| CRE split start | Chart-data footnote: "For data starting in **2013:Q4**, changes in standards and demand for construction and land development, nonfarm nonresidential, and multifamily are reported separately." VERIFIED. The aggregate CRE series (FRED DRTSCREL) runs **1990-07-01 to 2013-07-01**, then stops. |
| Period labels | The Fed labels the July 2026 survey **2026:3**, and FRED dates it 2026-07-01. That survey covers activity in Q2. 2013:Q4 is therefore the October 2013 survey; this last step is inferred from the labelling convention. |
| Frequency | Quarterly in practice. about.htm: "conducted only four times a year since 1992", with authority for up to six. |
| Panel | about.htm: "up to 80 large domestically chartered commercial banks and up to 24 large U.S. branches and agencies of foreign banks". Panel of 60 from 1981 to 2012, expanded to 80 in May 2012. 73 domestic panel banks as of 31 Mar 2023. **Actual July 2026 respondents: 56 domestic banks and 18 U.S. branches and agencies** (footnote 1, sloos-202607.htm). "~80" is the target, not the response count. |
| Basis | Diffusion index (net percentage), NSA, qualitative. It is not a loss rate. |
| Breaks | CRE split at 2013:Q4. Panel expanded in May 2012. In other loan types (not commercial), mortgage categories split 2007:Q2 and 2014:Q4, and consumer categories split 2011:Q2. |
| Free or paid | Free. |
| Scripted pull | `https://www.federalreserve.gov/releases/sloos/data/FRB_SLOOS_xml.zip` (downloaded, 244 KB). The chart-data HTML is published with each survey. FRED CSV, as below. |

**FRED IDs** (release rid=191; all verified by CSV pull, latest obs 2026-07-01):

| ID | Title (FRED) | First obs | Latest |
|---|---|---|---|
| DRTSCILM | Net % tightening standards, C&I loans to large and middle-market firms | 1990-04-01 | 0.0 |
| DRTSCIS | Net % tightening standards, C&I loans to small firms | 1990-04-01 | 1.8 |
| DRSDCILM | Net % stronger demand, C&I, large and middle-market | 1991-10-01 | 16.1 |
| DRSDCIS | Net % stronger demand, C&I, small firms | 1991-10-01 | 3.6 |
| DRISCFLM / DRISCFS | Net % increasing spreads over cost of funds, large and middle-market / small | 1990-04-01 | -26.8 / -14.5 |
| DRTSCREL | Net % tightening standards, CRE (aggregate; discontinued) | 1990-07-01 | last 2013-07-01 = -19.2 |
| SUBLPDRCSC | Tightening standards, CRE construction and land development | 2013-10-01 | -3.7 |
| SUBLPDRCSN | Tightening standards, CRE nonfarm nonresidential | 2013-10-01 | -11.3 |
| SUBLPDRCSM | Tightening standards, CRE multifamily | 2013-10-01 | -5.7 |
| SUBLPDRCDC / SUBLPDRCDN / SUBLPDRCDM | Stronger demand, CRE construction / nonfarm nonresidential / multifamily | 2013-10-01 | -11.1 / 1.9 / -3.8 |

The FRED release page also lists large-bank variants such as SUBLPDRCSCLGNQ, SUBLPDRCSNLGNQ and SUBLPDRCDCLGNQ. These were NOT CHECKED individually.

---

## 3. Shared National Credit (SNC) Program

URLs: https://www.federalreserve.gov/supervisionreg/snc.htm, https://www.federalreserve.gov/supervisionreg/snc-archive.htm, the latest press release https://www.federalreserve.gov/newsevents/pressreleases/bcreg20260112a.htm (12 Jan 2026, "Agencies issue 2025 Shared National Credit Program report"), and its attachment https://www.federalreserve.gov/newsevents/pressreleases/files/bcreg20260112a1.pdf

| Item | Finding |
|---|---|
| Review cadence | snc.htm: "These agencies initiated a **semiannual** SNC examination schedule in **2016**. SNC reviews are now planned for the first and third calendar quarters". **Publication is annual**: one report each year, combining the Q1 and Q3 reviews, issued around January to March. |
| Threshold | Appendix A: $**100 million** or more, shared by three or more unaffiliated federally supervised institutions. Exhibit 1 note: the drop in facilities between 2017 and 2018 "mainly reflects the minimum commitment increase from **$20 million to $100 million**." **The change took effect with the 2018 review.** |
| What it publishes | Total commitments and outstandings; borrowers and facilities; **Special Mention, Substandard, Doubtful, Loss, Classified, and SM+Classified commitments**; nonaccrual commitments; leveraged-lending commitments and non-pass; split by lender type (U.S. banks / FBOs / other investors) with non-pass % by owner. 2025 figures: SM+Classified $592.9bn of $6,911.4bn = 8.6%; U.S. banks 4.2%. |
| By industry | Appendix C has a 5-year window (2021–2025) by industry, giving commitment, SM, Classified, %SM and %Classified. The 2025 report moved to "**twenty-one sub-sectors** from the prior seven sector grouping" (a break in the industry series). |
| History | Appendix B gives an annual table of SM, Substandard, Doubtful, Loss, Classified, SM+Classified, Total committed and Total outstanding from **1989 to 2025**. Press releases are archived back to 1999 (snc-archive.htm). |
| Breaks | Threshold $20mm to $100mm (2018). Semiannual reviews from 2016. Industry grouping changed in the 2025 report. The report format was also streamlined in 2025, with qualitative text dropped from the attachment. |
| Format | **PDF only.** The press release links only the PDF attachment; no CSV or XLSX link was found on that page. Script approach: download the PDF and parse the Appendix B and C tables (pdftotext -layout works cleanly on the 2025 file). |
| Basis | Shared syndicated credits only, at the **commitment** level, as rated by examiners. It is not a bank's whole book, and it is annual. |
| Free or paid | Free. |

---

## 4. FR Y-9C (holding-company consolidated financial statements)

| Item | Finding |
|---|---|
| Form description | https://www.federalreserve.gov/apps/reportingforms/Report/Index/FR_Y-9C (VERIFIED). Quarterly, "as of the last calendar day of the quarter". It became FR Y-9C in **June 1986**. Filing threshold: $150mm, raised to $500mm (Mar 2006), $1bn (Mar 2015), and **$3bn (Sep 2018)**. These are **sample-composition breaks**: the 2021Q1 Chicago file has 416 filers against 1,573 in 1986Q3. |
| Basis | **Holding company, consolidated** (BHCs, SLHCs, IHCs, SHCs). It is not the bank-level Call Report. SLHCs were phased in from Mar 2012, and IHCs from Jul 2016. |
| HC-C categories (current form, VERIFIED) | 1.a construction, land development and other land loans (1-4 family construction / other); 1.b farmland; 1.d multifamily; 1.e(1) **owner-occupied nonfarm nonresidential (BHCKF160)**; 1.e(2) other nonfarm nonresidential (F161); 3 agricultural production (1590); 4 **C&I (1766)**; 9.a **loans to nondepository financial institutions (J454)**, with Memo 10 split into mortgage credit intermediaries, business credit intermediaries, PE funds, consumer credit intermediaries and other (PV05–PV09); 10 lease financing receivables (2165). BHDM-prefixed codes are domestic offices. |
| HI-B (charge-offs, VERIFIED) | Charge-offs and recoveries for CLD (C891–C894), farmland (3584/3585), multifamily (3588/3589), OO-NFNR (C895/C896), other NFNR (C897/C898), agricultural (4655/4665), C&I (4645/4646, or KX48 for holding companies under $5bn), leases (C880/F188, or KX50/KX51), and Memo 1 "loans to finance CRE … not secured by real estate" (5409/5410). **There is no separate NDFI charge-off line.** Amounts are **calendar year-to-date**, per the instructions, so quarterly flows have to be differenced. |
| HC-N (past due and nonaccrual, VERIFIED) | 30–89 days / 90+ days / nonaccrual for the same RE property types (F172–F183, 3493–3501), agricultural (1594/1597/1583), C&I (1606/1607/1608), leases, and **NDFI as Memo 9 (PV23/PV24/PV25)**. |
| Same as the Call Report? | The category structure parallels Call Report RC-C, RI-B and RC-N: the form text says it was revised in 1985 "to parallel" the Call Report, and the item codes match. NOT CHECKED line-by-line against the current FFIEC 031/041. |
| When the items first appear | Checked by reading the column headers of every Chicago Fed file from 1986Q3 to 2021Q1. BHCK1766 C&I, 2165 leases, 1590 agricultural and 1608 C&I nonaccrual: **1986Q3**. Real-estate property types (BHCK/BHDM1460 multifamily, BHDM1420 farmland, 1415 construction), 3499 multifamily past due and 1606 C&I past due: **1990Q3**. **OO / non-OO NFNR split (F160/F161), CLD split (C891/C893) and F178–F183: 2007Q1** (absent in 2006Q4). **NDFI J454: 2010Q1**. NDFI memo PV-codes were absent in the 2021Q1 file, so the start date is NOT CHECKED. |
| Bulk download, 1986–2021Q1 | **VERIFIED.** The Chicago Fed page https://www.chicagofed.org/banking/financial-institution-reports/bhc-data links 139 quarterly CSVs, `.../bhc-data/bhcfYYMM.csv`, from **bhcf8609 to bhcf2103**. Two were downloaded and parsed: 8609 has 551 columns and 1,573 rows; 2103 has 2,367 columns and 416 rows. The page says quarters inside the "five years plus current" revision window moved to the NIC from 1 Aug 2021. |
| Bulk download, current (NIC) | `https://www.ffiec.gov/npw/FinancialReport/FinancialDataDownload`. **COULD NOT:** the FFIEC returned a 403 "CAPTCHA Error … Enable JavaScript and cookies" page to curl and to WebFetch. A search-engine summary (SECONDARY only) says the page offers Y-9C, Y-9LP and Y-9SP in one quarterly zipped TXT file, "back to year 2000", refreshed daily, with a "Financial Download Dictionary". **Not verified.** A scripted pull will probably need a browser session. |
| API | No public API was found. CDR PDD web services (https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx, fetched) cover **Call Reports and UBPR for "All Commercial Banks"**, not the Y-9C. The CDR page offers Call Reports single period, Call Report four periods and UBPR, in tab-delimited or XBRL format. |
| Free or paid | Free. |

---

## 5. Macro and market context series

| Series | Source / ID | Basis | First obs | Latest | Full history downloadable? |
|---|---|---|---|---|---|
| CRE prices, IMF FSI | FRED COMREPUSQ159N (source IMF, Financial Soundness Indicators) | **Percent change from year ago**, NSA, quarterly | 2005-01-01 | 2026-01-01 = 6.58 | Yes, via fredgraph CSV. It is a growth rate only, not a level. |
| CRE price index, Fed Z.1 | FRED BOGZ1FL075035503Q, "Commercial Real Estate Price Index, Level" (Z.1) | Quarterly, end of period. FRED labels the units "Percent", but the values are index levels such as 315332, so treat the units label as suspect. | 1945-10-01 | 2026-04-01 = 315332 | Yes. |
| CRE price index, BIS | BIS WS_CPP, key Q.US (API `https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CPP/1.0/Q.US?format=csv`) | "United States - Commercial property price index, all properties". BIS method note: "Starting in Q1 1996, the level index comes from the **Costar Commercial Repeat Sales Index** … Prior to Q1 1996 … weighted-average of three appraisal-based … series … from **NREI**". **This is a methodology break at 1996Q1.** All properties only; no split by property type in this key. | 1945-Q4 | 2026-Q2 = 187.28 | Yes, CSV via the API, free. |
| HY OAS | FRED BAMLH0A0HYM2 (ICE Data Indices) | Daily close, percent | **2023-10-16** (truncated) | 2026-10-14 = 3.25 | **No.** The FRED notes say: "Starting in April 2026, this series will only include 3 years of observations. For more data, go to the source." The ICE licence terms on FRED also restrict redistribution ("internal use only"). Full history needs ICE, which is paid; its price was not checked. |
| Industrial production | FRED INDPRO (G.17) | Index 2017=100, SA, monthly | 1919-01-01 | 2026-08-01 = 103.0682 | Yes. |
| Business bankruptcy filings | U.S. Courts, Table F-2 (12-month), F-2 Three Months, F-2 One Month, F-5A county. Hub: https://www.uscourts.gov/data-news/reports/statistical-reports/bankruptcy-filings-statistics | Business vs nonbusiness, by chapter (7, 11, 13, other) and by district. Example: June 2026 quarter, 6,965 business filings out of 162,772 total. | Quarterly pages on the hub run from **December 2007 to June 2026**. The hub says the dashboard dates "back to data from 2007". | June 2026 | **PDF tables** (e.g. `/sites/default/files/document/bf_f2.3_0630.2026.pdf`), one file per period, so it has to be scraped. Data before 2007 is NOT CHECKED. **FRED:** a FRED site search for "business bankruptcy filings" returned no U.S. Courts filing-count series in its first results. This was not exhaustive, so no FRED series is known. |

---

## 6. Paid sources (brief)

| Source | What it holds | Verified? | Price |
|---|---|---|---|
| Trepp (CMBS delinquency) | Monthly CMBS delinquency rate, overall and by property type (office, multifamily, retail, lodging, industrial). Trade press citing Trepp: June 2026 overall 7.35%, office 11.57%, multifamily 7.23%. | **COULD NOT** reach trepp.com: curl got 404s on guessed paths, and WebFetch said it was "unable to fetch from www.trepp.com". Figures are SECONDARY (credaily.com, multihousingnews.com, multifamilydive.com). | Price not published (not seen). |
| KBRA / KBRA Analytics | The kbra.com homepage (fetched) lists ratings for "ABS, CMBS, RMBS, Structured Credit", plus KBRA Analytics ("The standard in CMBS surveillance") and KBRA Direct Lending Deals (DLD, private credit). | Homepage VERIFIED. Any free monthly CMBS delinquency report is NOT CHECKED. | Price not published. |
| Green Street CPPI | **Monthly** Commercial Property Price Index built from REIT-owned asset valuations, value-weighted, institutional-quality assets; a Canadian CPPI started June 2026. September 2026: -0.1% m/m, +4.7% y/y. | VERIFIED (greenstreet.com/insights/CPPI). The page offers "Register For Free Monthly Updates" / "free CPPI® reports". Full history and sector series are subscription; the sector coverage was not confirmed on the page. | Price not published. |
| CoStar | Repeat-sales CRE price indices, vacancy and rents. CoStar's repeat-sales index is the post-1996 source for the BIS / Fed CRE index (BIS note, VERIFIED). | costar.com returned 403. Product detail is NOT CHECKED. | Price not published. |
| MSCI RCA CPPI | Transaction-based CRE price indices. | **COULD NOT:** msci.com returned a ~2 KB JavaScript shell. NOT CHECKED. | Price not published. |
| Moody's default studies | The annual "Corporate Default and Recovery Rates" study. The 1920–2006 edition (Feb 2007) is a free PDF at moodys.com/sites/products/DefaultResearch/2006400000429618.pdf (VERIFIED downloadable). The licensed **Default & Recovery Database** covers "550,000 debts and 60,000 … entities", with US coverage back to 1920 (HBS Baker Library page, VERIFIED). Whether current editions are free with registration is NOT CHECKED. | Partly | Price not published. |
| S&P default studies | "Default, Transition, and Recovery: Annual Global Corporate Default And Rating Transition Study", the 2024 edition published 27 Mar 2025 (per search). It has default rates and transition matrices by rating. | **COULD NOT:** spglobal.com returned 403 to curl and to WebFetch. Content is SECONDARY. Free versus registration is NOT CHECKED. | Price not published. |

---

## COULD NOT / NOT CHECKED (consolidated)

1. **FFIEC NIC Financial Data Download** (Y-9C bulk for 2000 or 2016 onward): COULD NOT. The page returned a 403 CAPTCHA ("Enable JavaScript and cookies") to curl and WebFetch. Its coverage start ("back to 2000"), file format and dictionary are SECONDARY only.
2. Y-9C to Call Report line-by-line equivalence: NOT CHECKED. Only the structure and shared MDRM codes were seen.
3. Start date of the Y-9C NDFI memo (PV05–PV09, PV23–PV25): NOT CHECKED. The codes are absent in 2021Q1 and present on the current form.
4. SLOOS large-bank variant IDs (…LGNQ): NOT CHECKED individually.
5. U.S. Courts business bankruptcy data before Dec 2007: NOT CHECKED. **No FRED series was found**, but the search was not exhaustive.
6. Trepp: COULD NOT reach the site. Monthly figures are trade-press only.
7. S&P Global Ratings default study: COULD NOT (403). Moody's current-edition access terms: NOT CHECKED.
8. MSCI RCA CPPI (JavaScript-only page) and CoStar product pages (403): COULD NOT.
9. ICE BofA full HY OAS history: not on FRED since April 2026 (verified). ICE direct pricing was NOT CHECKED.
10. Whether SNC has any machine-readable (non-PDF) release: none found on the Fed press-release page. OCC and FDIC copies were NOT CHECKED; the FDIC URL tried returned 404.
11. FRED BOGZ1FL075035503Q: the units label ("Percent") is inconsistent with its values, and the vendor behind the Z.1 series was not confirmed. The BIS key for the US states CoStar from 1996Q1.
