# Unemployment anchors a free macro-risk scorecard

Banks, supervisors and analysts build their macro story for lending on a small, stable core. That core is **the unemployment rate and how fast it is rising, real GDP, house prices, commercial real estate (CRE) prices and corporate credit spreads**, with interest rates and inflation in support. All nine large regional banks whose FY2025 10-Ks were read name unemployment and real GDP as drivers of their loan-loss allowance. The Federal Reserve builds its 2026 severe stress scenario from the same variables. Around that core sit the series regulators use to describe risk building up: bank lending standards, household debt service, flows into delinquency, jobless claims, financial-conditions indexes, the yield curve and the excess bond premium. Nearly all are free, most are public domain, most download without a key through FRED, and most go back 30 years or more. Home insurance, one of the two examples named in the question, is the important exception. **No free series measures what homeowners actually pay.** The consumer price index (CPI) line people reach for prices renters' policies only: it rose 5% from 2019 to 2024, while mortgage-escrow data show homeowners' premiums up 62%. The best free proxy is the BLS producer price index (PPI) for homeowner's insurance premiums, available from June 1998. The causal evidence that higher premiums cause delinquency rests on licensed data: a one-standard-deviation rise adds 0.6 points to the chance of falling 30 days behind, 16% of the average. On the commercial side, the binding constraint is licensing, not availability. FRED now keeps only three years of ICE BofA corporate spreads. Moody's bars storing its Baa yields. CRE vacancy and CMBS delinquency are all vendor data. Two free federal substitutes cover the gap: the Fed's own corporate-spread file (from 1973) and its Z.1 CRE price index, the one the stress test uses. Published ways to flag an unusual reading fall into four families:

1. **Position in a stated history**, as a percentile.
2. **Change from a recent low** (the Sahm and Michaillat–Saez rules).
3. **Fixed cut-offs on composite indexes** (CFNAI −0.70, the yield-curve recession model).
4. **Gaps from trend.**

The three best-known recession triggers all signalled in 2022–25 with no recession behind them: the Sahm rule, the yield-curve model and the Conference Board's leading index. A 1-to-5 rating therefore has to show what drives it, which window of history it compares against, and which release of the data it used.

## Nine of nine bank filings name unemployment and GDP, and no regulator sets thresholds

The most direct public record of which outside conditions drive US lending risk is what banks tell investors moves their reserves. CECL is the accounting standard that requires a bank to reserve today for losses it expects over a loan's whole life, using forecasts that are "reasonable and supportable". Under it, every large bank discloses its macroeconomic drivers. In the FY2025 10-Ks of nine large regional banks, filed in February 2026, **all nine name the unemployment rate and real GDP**, and most call them the two most significant. PNC says "two of the most significant drivers being real GDP and the U.S. unemployment rate" ([PNC 10-K](https://www.sec.gov/Archives/edgar/data/713676/000071367626000020/pnc-20251231.htm)). Regions says "the unemployment rate is the most significant macroeconomic factor among the allowance models" ([Regions 10-K](https://www.sec.gov/Archives/edgar/data/1281761/000128176126000019/rf-20251231.htm)). The largest banks say the same:

- Citigroup's key variables are "the U.S. unemployment rate and U.S. real GDP growth rate" ([Citigroup 10-K](https://www.sec.gov/Archives/edgar/data/831001/000083100126000011/c-20251231.htm)).
- JPMorgan's consumer drivers are "regional U.S. unemployment rates and U.S. HPI" ([JPMorgan 10-K](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm)).
- Bank of America lists unemployment, GDP, corporate bond spreads, "real estate and other asset prices and equity market returns" ([Bank of America 10-K](https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/bac-20251231.htm)).

| Variable named in the allowance discussion | Regional banks naming it | Count of 9 |
|---|---|---|
| Unemployment rate | KeyCorp, PNC, Truist, Fifth Third, Huntington, Regions, M&T, Citizens, U.S. Bancorp | 9 |
| Real GDP | All nine (Truist for commercial only) | 9 |
| House prices | Truist, Regions, M&T by name; KeyCorp, U.S. Bancorp, Citizens as "real estate values" or "collateral values" | 3 by name, 6 counting general terms |
| CRE or commercial property prices | M&T, U.S. Bancorp, Truist by name; KeyCorp, Citizens in general terms | 3 by name, 5 counting general terms |
| Interest rates (fed funds, 10-year, SOFR, curve) | KeyCorp, Fifth Third, Citizens, U.S. Bancorp; Huntington in its scenario text | 4–5 |
| Inflation (CPI or PPI) | Regions, Fifth Third, U.S. Bancorp, KeyCorp; Huntington in its scenario text | 4–5 |
| Corporate credit spreads | Truist, Fifth Third, U.S. Bancorp, all for commercial loans | 3 |
| Equity prices; used-car prices; real disposable income; household debt | Fifth Third; Truist; U.S. Bancorp; U.S. Bancorp | 1 each |

These counts come from targeted searches of each bank's allowance sections, not full reads, so a bank may name other variables elsewhere ([KeyCorp](https://www.sec.gov/Archives/edgar/data/91576/000162828026010546/key-20251231.htm), [Truist](https://www.sec.gov/Archives/edgar/data/92230/000009223026000030/tfc-20251231.htm), [Fifth Third](https://www.sec.gov/Archives/edgar/data/35527/000003552726000124/fitb-20251231.htm), [Huntington](https://www.sec.gov/Archives/edgar/data/49196/000004919626000015/hban-20251231.htm), [M&T](https://www.sec.gov/Archives/edgar/data/36270/000003627026000010/mtb-20251231.htm), [Citizens](https://www.sec.gov/Archives/edgar/data/759944/000075994426000028/cfg-20251231.htm), [U.S. Bancorp](https://www.sec.gov/Archives/edgar/data/36104/000003610426000011/usb-20251231_d2.htm)).

Truist gives the cleanest split between consumer and commercial lending, and it maps directly onto the two teams who will read this tool. Its commercial books are driven by "unemployment trends, U.S. real GDP, corporate credit spreads, and property values". Its consumer books are driven by "unemployment trends, home price indices, and used car prices" ([Truist 10-K](https://www.sec.gov/Archives/edgar/data/92230/000009223026000030/tfc-20251231.htm)). U.S. Bancorp adds, for consumers, "household debt levels, real disposable income, the effect of higher interest rates on variable rate or adjustable rate loans" ([U.S. Bancorp 10-K](https://www.sec.gov/Archives/edgar/data/36104/000003610426000011/usb-20251231_d2.htm)).

The effects are large. KeyCorp's downside case assumes about 4 points more unemployment and about 6 points less GDP growth. That would raise its modelled allowance about **1.7 times for commercial and 1.6 times for consumer loans** ([KeyCorp 10-K](https://www.sec.gov/Archives/edgar/data/91576/000162828026010546/key-20251231.htm)). The banks' downside unemployment peaks run from 6.7% (Citizens' pessimistic case) to 9.4% (Citizens' scenario for CRE office loans, and the top of U.S. Bancorp's range). Most sit below the Fed's 10% floor for a severe recession.

The forecasts come from vendors; KeyCorp names Moody's Consensus, a licensed product. They cover two years (three at PNC), after which the banks revert to long-run history; KeyCorp uses a 20-year lookback. The filings therefore say *which* series matter. They do not say *when* a series is stressed. That judgement has to come from the methods in the sixth section.

### The Fed's stress test is the official list

The Fed's supervisory stress test is the nearest thing to an official list. Its 2026 scenarios carry 28 variables, 16 of them domestic ([Fed 2026 scenarios](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf)):

- **Six for activity and prices:** real and nominal GDP, real and nominal disposable income, the unemployment rate, and CPI inflation.
- **Four asset prices or financial conditions:** house prices, CRE prices, equities, and stock-market volatility (the VIX).
- **Six interest rates:** 3-month, 5-year and 10-year Treasury yields, the 10-year BBB corporate yield, the 30-year mortgage rate, and the prime rate.

The Fed's notes on the variables tie 13 of the 16 to free public series. The other three are licensed even in the Fed's own build: the BBB yield (ICE), equities (Dow Jones via Bloomberg) and the VIX (CBOE via Bloomberg).

The 2026 severely adverse path:

- takes unemployment from 4.5% to **10%** by 2027:Q3;
- cuts house prices **30%** and CRE prices **39%**;
- drops equities about 58%;
- lifts the VIX to 72 and the BBB spread to 5.7 points.

The Fed sizes that severity against current conditions. It cited house prices "about 37% above five years earlier" and a BBB spread "low relative to its historical series". It also states that "scenario severity generally will be higher during economic expansions or periods when asset values have increased". That is an official reason to rate how stretched valuations are, not only how stressed conditions are today.

### Each regulator states its benchmark in the chart title

The regulators' own narrative reports frame risk the way the planned tool would. The Fed's semiannual Financial Stability Report separates unpredictable shocks from vulnerabilities that "can be monitored as they build up or recede over time" ([FSR framework](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-purpose-and-framework.htm)). It tracks four categories of vulnerability: valuation pressures, borrowing by businesses and households, leverage in the financial sector, and funding risk. Almost every reading is placed in its own history. Price-to-earnings ratios sit "in the upper range of its historical distribution"; auto delinquency is "at the 90th percentile of its historical distribution" ([FSR overview](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-overview.htm); [FSR borrowing](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-borrowing.htm)).

The OCC's Spring 2026 Semiannual Risk Perspective opens with real GDP, payrolls, unemployment, wage growth, inflation, house prices, multifamily rents and CRE vacancy by property type, against the Blue Chip consensus forecast ([OCC SARP](https://www.occ.gov/publications-and-resources/publications/semiannual-risk-perspective/files/pub-semiannual-risk-perspective-spring-2026.pdf)).

The FDIC's 2026 Risk Review charts:

- GDP;
- the ratio of unemployed people to job openings;
- the yield curve;
- CRE vacancy and values;
- the Senior Loan Officer Opinion Survey (SLOOS, the Fed's quarterly survey of bank lending standards);
- corporate and leveraged-loan defaults;
- real income;
- household debt service and debt-to-GDP.

It judges each against a fixed **"pre-pandemic average" of 2015:Q1–2019:Q4** ([FDIC Risk Review](https://www.fdic.gov/analysis/2026-risk-review)). The shared device is a chart title that is itself the verdict against a stated benchmark. The choice of benchmark matters. Against a calm 2015–19 window, almost any post-2020 reading looks elevated.

### Guidance requires judgement but prescribes no indicators

No US regulator prescribes indicators or cut-offs. The interagency CECL policy statement asks banks to weigh "changes in international, national, regional, and local economic and business conditions". It notes that a local unemployment rate "may be more relevant" than a strong national one when a major local employer is lost. The agencies explicitly declined to supply "an economic forecast or a simple model" ([CECL policy statement](https://www.govinfo.gov/content/pkg/FR-2020-06-01/html/2020-10291.htm)).

The 2012 interagency stress-testing guidance says a geographically concentrated bank "may be more adversely affected by shocks to economic activity at the state or local level than by a severe national recession". It also says stress testing is "particularly valuable during benign periods when other measures may not indicate emerging risks" ([2012 stress-testing guidance](https://www.govinfo.gov/content/pkg/FR-2012-05-17/html/2012-11989.htm)). The OCC's heightened standards require the risk framework to be updated for "emerging risks ... and other internal and external factors" ([12 CFR Part 30, Appendix D](https://www.ecfr.gov/current/title-12/chapter-I/part-30)).

A macro-conditions tool therefore fits as evidence for these qualitative factors and for emerging-risk reporting, not as a replacement for the CECL forecast. Its choices of series, window and cut-off are the bank's to document and defend. The Fed's scenario guides and the published triggers in the sixth section are the strongest citations available for them.

## Labour data carries the only official link to loan losses

Among labour and income series, only the unemployment rate has an official, published link to loan performance.

**The Fed's own models use it.** The 2026 supervisory credit-card default model uses each state's unemployment rate in the previous quarter plus its change over the year. The lag reflects that borrowers "may be able to rely on savings or temporary budget cuts before eventually defaulting". For other retail lending, "quarterly changes in the unemployment rate" are "the key macroeconomic specification". Auto loss-given-default (the share of a defaulted loan that is lost) uses the national rate ([Fed credit risk models](https://www.federalreserve.gov/supervisionreg/files/credit-risk-models.pdf)).

**A 2025 Fed note measured the effect.** "a 100 basis point increase in the unemployment rate is associated with about a 45 basis point increase in the [card] delinquency rate". The same note found the 2020 spike made the model "far over-predict" delinquency, and that the post-2022 rise came from credit extended to riskier borrowers, not from unemployment ([FEDS Note, Feb 2025](https://www.federalreserve.gov/econres/notes/feds-notes/predicting-credit-card-delinquency-rates-20250228.html)).

**Other studies agree.** A Chicago Fed study of auto loans found that a 1% rise in county unemployment raised default risk "by as much as 9 percent" ([Agarwal, Ambrose and Chomsisengphet, Chicago Fed](https://www.chicagofed.org/~/media/publications/economic-perspectives/2008/ep-3qtr2008-part2-agarwal-etal-pdf.pdf)). This repository's own public-data test is not peer-reviewed. It found:

- card net charge-offs rose 0.68, 1.03 and 1.25 points per point of unemployment in the 1990, 2001 and 2007–09 recessions, and fell in 2020;
- over 1985–2019, the yearly change in unemployment matched card losses best four quarters later (correlation 0.83);
- at 6.5–7.5% unemployment, card losses a year later ranged from 2.4% to 9.4% ([PROPOSAL.md](../PROPOSAL.md)).

That last finding matters most for the tool's design. **A level of unemployment does not map to a level of losses. A change in unemployment does.**

### Unemployment confirms a recession; claims warn earlier

Unemployment is coincident with recessions, not leading. Sahm's rule fires "within three months of the start of the past six recessions" on average and, in her words, "gives little advance warning" ([Sahm, Hamilton Project 2019](https://www.hamiltonproject.org/wp-content/uploads/2023/01/Sahm_web_20190506.pdf)). Michaillat and Saez combine unemployment with job vacancies. Their rule detects recessions after 1.2 months on average (3 at most), against 2.7 months (7 at most) for Sahm's, and caught all 15 recessions since 1929 without a false positive ([Michaillat and Saez, Oxford Bulletin 2025](https://eml.berkeley.edu/~saez/michaillat-saezOBES25.pdf)). That record is in-sample: the threshold was chosen as the lowest that gave no false alarms. Its 2024–26 reading was not available in this research.

Because losses trail unemployment by one to four quarters, a lending team gets roughly a year of warning on card losses from the point unemployment turns, and little or none on the recession itself. **Weekly initial jobless claims are the timeliest labour signal.** They come from the Labor Department's ETA 539 report, run from 1967 and are published five days after the week ends: 197,000 for the week to 3 October 2026 ([FRED ICSA](https://fred.stlouisfed.org/series/ICSA)). Claims are one of the ten components of the Conference Board's leading index. Their old 400,000 rule of thumb is out of date. The St. Louis Fed finds the best-fitting threshold averaged about 306,000 before 1984 and 434,000 after, and was "more informative ... during expansionary rather than recessionary periods". In 2020, claims crossed it only in February 2021 ([St. Louis Fed, Jan 2025](https://www.stlouisfed.org/on-the-economy/2025/jan/are-initial-jobless-claims-useful-gauge-labor-market-conditions)).

The only threshold on these series written into law is the Extended Benefits trigger on insured unemployment. The Labor Department publishes it weekly by state; on 11 October 2026 zero states were "on" ([DOL Trigger Notice 2026-39](https://oui.doleta.gov/unemploy/trigger/2026/trig_101126.html)). Its numbers, a 13-week insured rate of at least 5% and at least 120% of the prior two years, were confirmed only from a 2009 Federal Register notice ([FR, Apr 2009](https://www.govinfo.gov/content/pkg/FR-2009-04-29/pdf/E9-9747.pdf)).

Three other labour signals have published leading records for jobs, but none for loan losses:

- **Layoff notices.** Notices filed under the WARN Act lead state claims and unemployment changes ([Cleveland Fed WP 20-03R](https://www.clevelandfed.org/publications/working-paper/2022/wp-2003r-advance-layoff-notices-and-aggregate-job-loss)). There is no federal total; the Cleveland Fed's research panel is the only aggregate, and whether it is still updated in 2026 was not confirmed.
- **Temporary help employment.** Its peaks and troughs "generally have led those of total nonfarm employment" since 1990 ([BLS Monthly Labor Review, 2011](https://www.bls.gov/opub/mlr/2011/04/art6full.pdf)).
- **Average weekly hours in manufacturing.** This is a component of the Conference Board's leading index.

Challenger, Gray & Christmas's job-cut counts measure *announced* cuts, carry no stated reuse terms and have no API ([Challenger report, Aug 2026](https://www.challengergray.com/wp-content/uploads/2026/09/Challenger-Report-August-2026.pdf)).

### Income series revise too much to rate on their level

Income is the weakest-evidenced series in this group and the most prone to revision. Real disposable personal income, real personal income excluding transfers and the personal saving rate all run monthly from 1959 and are public domain. BEA's 30 September 2026 annual update revised personal income back to January 2021 ([BEA, Aug 2026 release](https://www.bea.gov/news/2026/personal-income-and-outlays-august-2026)). It moved October 2025's saving rate from a first print of 3.7% to 4.9% ([BEA Oct–Nov 2025 release](https://www.bea.gov/news/2026/personal-income-and-outlays-october-and-november-2025); [FRED PSAVERT](https://fred.stlouisfed.org/series/PSAVERT)). A "normal level" estimated in August can shift by more than a point a month later.

Gross and Souleles found state income not significant for card default ([NBER w8409](https://www.nber.org/papers/w8409)), and the 2025 Fed note found debt-to-income versions of its model "tend to work less well". KeyCorp nonetheless uses "U.S. household income" for mortgage, card and other consumer loans. NBER lists real personal income excluding transfers first among its recession-dating inputs ([NBER](https://www.nber.org/research/business-cycle-dating)). That transfers-excluded series is the cleaner cyclical signal: the gap between it and total disposable income shows when government support is propping households up, as it did in 2020, when the link from unemployment to losses broke.

### Three data hazards affect every labour series

1. **October 2025 is permanently missing.** "There are no CPS estimates for October 2025", and they "were not collected retroactively" ([BLS CPS shutdown Q&A](https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm)). The CPS is the household survey behind the unemployment rate, so the hole runs through the national, state, metro and county rates, U-6, participation, the Sahm series and the Atlanta Fed wage tracker. FRED leaves the cell blank and the BLS API returns a dash. A parser that turns either into zero would produce a false 0% unemployment outlier.
2. **The payroll benchmark was large.** The March 2025 payroll benchmark cut employment by **898,000 (0.6%)**, against a 10-year average revision of 0.2% ([BLS benchmark article](https://www.bls.gov/web/empsit/cesbmart.htm)). Payroll "outliers" scored on first releases can vanish after benchmarking.
3. **Several products have changed or stopped.** The Philadelphia Fed has stopped its state leading indexes for good ([Philadelphia Fed](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/state-leading-indexes)). State job-openings (JOLTS) data are now released only once a year. County rates can jump: Cuyahoga County, Ohio, read 3.3% in July 2026 and 1.9% in August, during a BLS revision notice whose text could not be read ([FRED OHCUYA5URN](https://fred.stlouisfed.org/series/OHCUYA5URN)).

**Licensing.** BLS material is public domain ([BLS copyright](https://www.bls.gov/opub/copyright-information.htm)). FRED's Sahm real-time page carries both a public-domain tag and a "copyrighted" banner, which needs resolving before the series is redistributed ([FRED SAHMREALTIME](https://fred.stlouisfed.org/series/SAHMREALTIME)).

| Indicator (id) — what it measures | Publisher | Frequency · from | Access · licence | Breaks and cautions | Who uses it this way | Evidence of stress |
|---|---|---|---|---|---|---|
| Unemployment rate, U-3 ([UNRATE](https://fred.stlouisfed.org/series/UNRATE)); 4.2% Sep 2026 | BLS (CPS) | Monthly, SA · Jan 1948; ~2-day lag | Public domain; FRED CSV keyless; BLS API | Oct 2025 missing; annual population controls | All 9 regional 10-Ks, JPMorgan, Citi, BofA; Fed stress test; OCC SARP | Fed card and retail models; +45 bp card delinquency per point |
| State unemployment ([CAUR](https://fred.stlouisfed.org/series/CAUR), pattern {ST}UR) | BLS LAUS | Monthly, SA · Jan 1976; ~18 days | Public domain | Oct 2025 cancelled; spring benchmark | Fed card model (prior quarter + year change); JPMorgan; CECL policy statement | As above, by state |
| County and metro unemployment ([OHCUYA5URN](https://fred.stlouisfed.org/series/OHCUYA5URN) example) | BLS LAUS | Monthly, county NSA · Jan 1990; ~30 days | Public domain; FRED ids must be looked up | Oct 2025 cancelled; odd moves (Cuyahoga, Aug 2026) | CECL policy statement's local example | County auto default risk up to 9% per point |
| U-6 broad underemployment ([U6RATE](https://fred.stlouisfed.org/series/U6RATE)); 7.6% | BLS | Monthly, SA · Jan 1994 | Public domain | Oct 2025 missing; only three recessions | — | None specific |
| Sahm rule ([SAHMREALTIME](https://fred.stlouisfed.org/series/SAHMREALTIME)); 0.00 Sep 2026 | Claudia Sahm via FRED | Monthly · Dec 1959 (current vintage Mar 1949) | Mixed public-domain and copyright tags | Oct 2025 blank | Hamilton Project trigger | Fires ~3 months after a recession starts; false alarms 1976, 2024 |
| Initial claims ([ICSA](https://fred.stlouisfed.org/series/ICSA)); state {ST}ICLAIMS | DOL ETA 539 | Weekly, SA · Jan 1967 (states NSA, Feb 1986); 5-day lag | Public domain; DOL downloads, no key | Weekly release paused in the 2025 shutdown (press report) | Conference Board leading index | Repository test: matches card losses six quarters later (0.66, to 2019); broke in 2020 |
| Continuing claims, insured unemployment rate ([CCSA](https://fred.stlouisfed.org/series/CCSA), [IURSA](https://fred.stlouisfed.org/series/IURSA)) | DOL | Weekly · 1967 / 1971 | Public domain | — | Statutory Extended Benefits trigger | 0 states triggered, Oct 2026 |
| Payroll employment ([PAYEMS](https://fred.stlouisfed.org/series/PAYEMS)) | BLS CES | Monthly, SA · Jan 1939 | Public domain | −898k benchmark (Mar 2025) | OCC SARP; NBER dating | Coincident by construction |
| Job openings, layoffs, quits ([JTSJOL](https://fred.stlouisfed.org/series/JTSJOL), [JTSLDR](https://fred.stlouisfed.org/series/JTSLDR), [JTSQUR](https://fred.stlouisfed.org/series/JTSQUR)) | BLS JOLTS | Monthly, SA · Dec 2000 | Public domain | Sep 2025 folded into Oct; state data now annual | FDIC unemployed-per-opening chart | Vacancies feed Michaillat–Saez |
| Temporary help employment ([TEMPHELPS](https://fred.stlouisfed.org/series/TEMPHELPS)) | BLS CES | Monthly, SA · Jan 1990 | Public domain | Three recessions in sample | — | Leads total employment (BLS) |
| Manufacturing weekly hours ([AWHMAN](https://fred.stlouisfed.org/series/AWHMAN)) | BLS CES | Monthly · Jan 1939 | Public domain | All-employee hours only from 2006 | Conference Board leading index | Through the leading index only |
| KC Fed labour conditions, level and momentum ([FRBKCLMCILA](https://fred.stlouisfed.org/series/FRBKCLMCILA), [FRBKCLMCIM](https://fred.stlouisfed.org/series/FRBKCLMCIM)) | Kansas City Fed | Monthly · Jan 1992 | Copyrighted: citation required | Composite of 24 series | — | None found |
| WARN layoff notices | State agencies; Cleveland Fed research panel | Semi-monthly panel | Research dataset; 2026 updates unverified | No federal total | — | Leads state claims and unemployment |
| Real disposable income ([DSPIC96](https://fred.stlouisfed.org/series/DSPIC96)); excluding transfers ([W875RX1](https://fred.stlouisfed.org/series/W875RX1)) | BEA | Monthly · Jan 1959 | Public domain; BEA API with free key | Annual revision back to Jan 2021; Oct 2025 deflator interpolated | Fed stress test; U.S. Bancorp; KeyCorp; NBER | Weak: not significant in Gross–Souleles |
| Personal saving rate ([PSAVERT](https://fred.stlouisfed.org/series/PSAVERT)); 4.1% Aug 2026 | BEA | Monthly · Jan 1959 | Public domain | Oct 2025 revised from 3.7% to 4.9% | — | None found |
| Wage growth: Atlanta Fed tracker; ECI ([ECIWAG](https://fred.stlouisfed.org/series/ECIWAG)); average hourly earnings | Atlanta Fed; BLS | Monthly from 1997; quarterly (FRED from 2001); monthly from 2006 | Free Excel; public domain | Tracker missing Oct 2025; earnings rise when low-paid workers lose jobs | — | None found |
| State coincident indexes ({ST}PHCI) | Philadelphia Fed | Monthly · Jan 1979 | Copyrighted: citation required | Whole history re-estimated each spring; leading indexes stopped after Feb 2020 | — | Context only |

## Home insurance has no free series for what owners actually pay

The question names home insurance prices, and this is where public data falls shortest. The CPI item for "tenants' and household insurance" (CUUR0000SEHD) is published only as a US average, not seasonally adjusted, from December 1997. BLS states that "only renters' insurance policies are sampled and priced" and that structure and liability coverage in homeowners' policies are excluded ([BLS factsheet](https://www.bls.gov/cpi/factsheets/tenants-household-insurance.htm); [BLS data](https://data.bls.gov/timeseries/CUUR0000SEHD)). The Dallas Fed measured the gap. From 2019 to 2024 that CPI item rose **5%**. Homeowners' premiums in ICE McDash mortgage-escrow data rose **62%**. The national accounts' "net household insurance" rose 35% ([Dallas Fed, Apr 2026](https://www.dallasfed.org/research/economics/2026/0409)). Calling the CPI line a home-insurance index understates the shock by an order of magnitude.

The Fed has named the same gap. It stopped publishing its Financial Obligations Ratio after 2023:Q3 "due to a lack of high-quality data on property tax and homeowners' insurance payments" ([Fed archived DSR/FOR](https://www.federalreserve.gov/releases/housedebt/default.htm)).

**The best free monthly proxy is the BLS producer price index for homeowner's insurance premiums** (PCU9241269241262, with a direct-insurers variant, PCU5241265241262). It runs from June 1998, is not seasonally adjusted, and is on FRED and the BLS API ([BLS data](https://data.bls.gov/timeseries/PCU9241269241262); [FRED](https://fred.stlouisfed.org/series/PCU9241269241262)). It measures what insurers charge, not what households pay. Most of each year's rise arrives as a single September step: from 265.926 to 277.777 between August and September 2025, then roughly flat to 279.164 (preliminary) by August 2026. Values stay preliminary for up to four months. The tool should rate its change over the year, not its month-to-month moves.

No study ties this PPI itself to delinquency. Regulators and the regional Feds measure premiums from licensed escrow data instead.

### Licensed escrow data supply the causal evidence

The strongest evidence that insurance costs cause household stress is causal. Dallas Fed Working Paper 2505 followed 6.7 million borrowers whose policies renewed between July 2022 and June 2023. It found that "when premiums increase by one standard deviation, the probability of delinquency rises by 0.6 percentage points, representing a 16% increase relative to the mean". The effect is larger for borrowers with high debt-to-income or high loan-to-value ratios, and "three times larger for non-jumbo compared to jumbo" loans. Higher premiums also "significantly raise the probability of credit card delinquency" ([Dallas Fed WP 2505](https://www.dallasfed.org/research/papers/2025/wp2505)).

Two more studies trace other channels:

- **New lending.** Premium increases reduce mortgage originations, most of all refinancing and cash-out refinancing; the denials cite debt-to-income and collateral ([Chicago Fed WP 2026-01](https://www.chicagofed.org/-/media/publications/working-papers/2026/wp2026-01.pdf)).
- **Collateral values.** The pass-through of disaster risk into premiums has doubled, and premium rises are priced into homes, "reducing home price growth by over $40,000 in the most exposed zipcodes" ([Keys and Mulder, NBER w32579](https://www.nber.org/papers/w32579)).

The Philadelphia Fed found real premiums up 25–29% from December 2021 to June 2025 in Pennsylvania, New Jersey and Delaware. It linked the rise to delinquency, but says the correlation "does not necessarily represent a causal relationship" ([Philadelphia Fed brief](https://www.philadelphiafed.org/-/media/FRBP/Assets/Community-Development/Briefs/homeowners_insurance_brief.pdf)). The New York Fed warns that premium per $1,000 of coverage "may not be informative about the effective price of insurance", because coverage limits rarely bind ([Liberty Street, Apr 2026](https://libertystreeteconomics.newyorkfed.org/2026/04/what-millions-of-homeowners-insurance-contracts-reveal-about-risk-sharing/)). A much-repeated figure — "every $500" of extra premium makes a borrower "20 percent more likely" to become delinquent — comes from advocacy summaries and could not be found in the working paper ([Public Citizen](https://www.citizen.org/article/rising-property-insurance-premiums-the-uneven-risks-to-household-and-systemic-financial-stability/)).

All of this rests on ICE McDash or Cotality escrow data, which are licensed. ICE McDash puts the average insured mortgagor at about $2,300 a year in 2024, 2.7% of median household income against about 2% before the pandemic. State rises were 73% in Texas, 78% in Florida, 84% in Idaho and 90% in Utah. The Dallas Fed expects premium growth to "ease through year-end 2026" as reinsurance rates fall ([Dallas Fed, Apr 2026](https://www.dallasfed.org/research/economics/2026/0409)). A public-data tool can therefore show the price signal and quote the published elasticity, but it cannot estimate the elasticity itself.

### The only free geographic premium data stops in 2022

The only free premium data below national level is the Treasury Federal Insurance Office's ZIP-level file for 2018–2022, built from a state-regulator data call. Real premiums per policy rose 8.7% to $1,737. Homes in the highest climate-risk fifth of ZIP codes paid $2,321, 82% more than the lowest-risk fifth, and faced about 80% higher non-renewal rates. The Consumer Federation of America says the report was deleted from the Treasury site in fall 2025, and now hosts the report and data itself ([FIO report via CFA](https://consumerfed.org/news/blogs/download-analyses-of-us-homeowners-insurance-markets-2018-2022-climate-related-risks-and-other-factors-report-and-data-from-federal-insurance-office-fio/)). It suits a static exposure map, not a time-series rating.

For commercial borrowers, the PPI for commercial multiple-peril insurance (PCU5241265241265) rose about 7% in 2025, from 185.675 to 198.651 ([BLS data](https://data.bls.gov/timeseries/PCU5241265241265)). The Dallas Fed puts the rise in commercial insurance at about 75% from 2019 to 2024. No delinquency study covers either.

### Vehicle, energy and shelter costs are free and long, but rarely linked to defaults

Car costs are well covered by free BLS series:

- **Motor vehicle insurance CPI** (SETE): monthly, not seasonally adjusted from 1947 and adjusted from 1985, with four regions from December 2017. It rose about 13% from January 2024 to December 2025, then fell about 5% from April to September 2026. October and November 2025 are both missing. BLS updates each sampled car's model year "usually in October or November", which "often results in premium changes" ([BLS data](https://data.bls.gov/timeseries/CUSR0000SETE); [BLS factsheet](https://www.bls.gov/cpi/factsheets/motor-vehicle-insurance.htm)).
- **Repair CPI** (SETD, from 1967): rose from 396.004 in January 2024 to 468.491 in September 2026 ([BLS data](https://data.bls.gov/timeseries/CUSR0000SETD)).
- **Used and new vehicle CPIs** (from 1953): both have an October 2025 value; the used-car sample is built from J.D. Power data ([BLS factsheet](https://www.bls.gov/cpi/factsheets/used-cars-and-trucks.htm)).

The Manheim used-vehicle index from Cox Automotive runs from January 1997 and can be downloaded free. It was rebased in January 2023 and carries no published redistribution licence, so treat it as licensed ([Cox Automotive](https://www.coxautoinc.com/insights/manheim-insights/)). The documented route from car prices to auto credit is loan size: "larger auto loan amount at origination, rather than the increases in interest rates, explain most of the increase in delinquencies", with the average required payment rising from $470 to about $600 ([FEDS Note, Sep 2024](https://www.federalreserve.gov/econres/notes/feds-notes/rising-auto-loan-delinquencies-and-high-monthly-payments-20240926.html)). Of the nine regional banks, only Truist names used-car prices as a consumer driver.

**Gasoline is the 2026 cost shock.** Its CPI rose **34.2% in the year to September 2026**, almost all of it from March to May. Headline CPI rose 3.7% and core 2.6% ([BLS gasoline CPI](https://data.bls.gov/timeseries/CUSR0000SETB01); [BLS all-items CPI](https://data.bls.gov/timeseries/CUSR0000SA0)). The EIA's weekly retail price runs from August 1990, is published two days after the survey, and has detail by region, nine states and ten cities: $4.331 a gallon for the week of 12 October 2026 ([EIA](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=EMM_EPMR_PTE_NUS_DPG&f=W)). The only link to loan performance is a banking trade group's commentary on 2005 and 2014 card delinquency ([American Banker](https://americanbanker.com/news/falling-gas-prices-help-consumers-pay-their-debts-aba-says)).

Other household costs, in the year to September 2026:

- **Electricity (+4.4%) and piped gas (+5.0%).** These outpaced inflation; EIA publishes residential prices by state about two months after the month.
- **Rent (+2.8%) and food at home (+1.8%).** These lagged it.
- **The BLS index of rents for new tenants.** It leads CPI rent, according to the Cleveland Fed paper behind it ([Cleveland Fed WP 22-38R](https://www.clevelandfed.org/publications/working-paper/2023/wp-2238r-disentangling-rent-index-differences)). But it is a quarterly prototype, re-estimated in full each release, and still ended at 2025q3 on 14 October 2026, with a 95% confidence interval of −4.0% to +6.5% ([BLS](https://www.bls.gov/cpi/research-series/r-cpi-ntr.htm)).

Property taxes and HOA dues have no monthly index. The Census Bureau's quarterly local property-tax collections run from 1962, with a gap from 1992Q3 to 1993Q2 ([Census QTax](https://www.census.gov/programs-surveys/qtax/about.html)). The American Community Survey gives annual median taxes paid by county ([ACS B25103](https://api.census.gov/data/2024/acs/acs1/groups/B25103.json)) and, new in 2024, HOA fees: 21.6 million of 86.6 million owner households paid them, at a median of $135 a month ([Census, Sep 2025](https://www.census.gov/library/stories/2025/09/condo-hoa-fees.html)). Evidence linking rising escrow payments (tax plus insurance) to delinquency comes from Cotality, a vendor, and is correlational ([MortgagePoint, Mar 2026](https://themortgagepoint.com/2026/03/04/cotality-fast-rising-escrows-leading-to-delinquency-spikes/)).

Disaster exposure changed source in 2025. NOAA stopped updating its Billion-Dollar Disasters database after 2024 ([CNN, May 2025](https://cnn.com/2025/05/08/climate/noaa-ends-disaster-database)). Climate Central continues it "with the same methodology and lead scientist": 447 events and over $3.3 trillion as of September 2026. Its terms of use were not found ([Climate Central](https://www.climatecentral.org/climate-services/billion-dollar-disasters)). FEMA's OpenFEMA API needs no key and serves disaster declarations from 1953 and flood-insurance (NFIP) policies and claims ([OpenFEMA](https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries)). Declarations fell from 100 in 2024 to 45 in 2025. They are administrative decisions as well as hazard events, so NFIP claims are the cleaner damage signal. Studies of Hurricane Harvey, read only in summary, tie uninsured flood damage to later mortgage default ([Fannie Mae](https://www.fanniemae.com/research-and-insights/publications/flood-damage-mortgage-credit-risk-hurricane-harvey); [OCC working paper](https://occ.gov/publications-and-resources/publications/economics/working-papers-banking-perf-reg/pub-econ-working-paper-hurricanes-residential-mort-loan-perf.pdf)).

| Indicator (id) — what it measures | Publisher | Frequency · from | Access · licence | Breaks and cautions | Who uses it this way | Evidence of stress |
|---|---|---|---|---|---|---|
| PPI, homeowner's insurance premiums ([PCU9241269241262](https://fred.stlouisfed.org/series/PCU9241269241262); direct insurers PCU5241265241262) | BLS | Monthly, NSA · Jun 1998 | Public domain; FRED, BLS API | September annual step; preliminary for 4 months | No named user; best free proxy | Proxy for the premiums in WP 2505 (causal, +0.6 pt) |
| CPI, tenants' and household insurance ([CUUR0000SEHD](https://data.bls.gov/timeseries/CUUR0000SEHD)) | BLS | Monthly, NSA, US only · Dec 1997 | Public domain | Renters only; Oct 2025 missing; weight method changed Jan 2025 | Dallas Fed critique | Mismeasures homeowners (5% vs 62%) |
| Homeowners' premiums by ZIP code, 2018–22 | Treasury FIO / NAIC | One-off annual cross-section | Re-hosted by CFA after removal | Not maintained | FIO | Exposure map; non-renewal ~80% higher in riskiest ZIPs |
| Escrowed premiums (ICE McDash) | ICE | Monthly, loan-level | **Licensed** | — | Dallas, Philadelphia, NY Feds | Causal (WP 2505) |
| PPI, commercial multiple-peril insurance ([PCU5241265241265](https://data.bls.gov/timeseries/PCU5241265241265)) | BLS | Monthly · Jun 1998 | Public domain | Step changes | — | None (business cost) |
| CPI, motor vehicle insurance ([CUSR0000SETE](https://data.bls.gov/timeseries/CUSR0000SETE)) | BLS | Monthly · SA 1985, NSA 1947; regions Dec 2017 | Public domain | Oct and Nov 2025 missing; model-year update each autumn | — | None found |
| CPI, used cars ([CUSR0000SETA02](https://data.bls.gov/timeseries/CUSR0000SETA02)) and new vehicles | BLS | Monthly, SA · 1953 | Public domain | New vehicles moved to J.D. Power transaction data from Apr 2022 | Truist (used-car prices) | Via loan size (FEDS 2024) |
| Manheim used-vehicle index | Cox Automotive | Monthly · Jan 1997 | Free download; no reuse licence | Rebased Jan 2023 | — | Collateral value |
| Weekly retail gasoline (EMM_EPMR_PTE_NUS_DPG) | EIA | Weekly · Aug 1990; 2-day lag | Free; EIA API needs a key; reuse policy | — | — | Trade-group commentary only |
| CPI all items and core ([CUSR0000SA0](https://data.bls.gov/timeseries/CUSR0000SA0)) | BLS | Monthly · 1947 / 1957 | Public domain | Oct 2025 missing | Fed stress test; Regions, Fifth Third, U.S. Bancorp | Stress-test variable |
| Electricity and piped-gas CPI; EIA residential prices by state | BLS; EIA | Monthly · 1952; EIA ~2-month lag | Public domain; EIA key | Oct 2025 missing; gas strongly seasonal | — | None found |
| Rent and owners' equivalent rent CPI; new-tenant rent index | BLS | Monthly · 1981 / 1983; new-tenant quarterly · 2005 | Public domain | New-tenant index a stale prototype (ends 2025q3) | OCC SARP (multifamily rents) | None found |
| Food at home CPI | BLS | Monthly · 1952 | Public domain | Oct 2025 missing | — | None found |
| Property tax collections; taxes paid; HOA fees | Census QTax; ACS | Quarterly · 1962; annual; HOA only 2024 | Public domain | 1992Q3–93Q2 not released | — | None found |
| Billion-dollar disasters | NOAA archive 1980–2024 → Climate Central | Event-based | NOAA stopped; Climate Central terms unverified | Source change 2025 | — | Damage leads to default where uninsured (Harvey) |
| Disaster declarations; NFIP policies and claims | FEMA OpenFEMA | Events · 1953 (county 1964) | API, no key | Declarations are administrative | — | NFIP claims as damage proxy |

## Household balance sheets: flows into delinquency beat balance stocks

Several household balance-sheet series changed definition in the last two years, and the change matters for any "normal level". **The Fed's household debt service ratio (DSR) was rebuilt in 2024 on credit-bureau data and now starts only in 2005.** The DSR is required debt payments as a share of disposable income. The new version includes mortgage escrow, so its level "is also consistently higher" than the old one ([Ringo, FEDS Note, Sep 2024](https://www.federalreserve.gov/econres/notes/feds-notes/introducing-a-credit-bureau-based-measure-of-u-s-household-debt-service-20240904.html)). FRED's TDSP now carries the new series: 11.11% in 2026:Q2, against 11.73% in 2019:Q4 and a 15.85% peak in 2007:Q4. The old series ran from 1980 and is archived but no longer updated ([Fed DSR](https://www.federalreserve.gov/releases/dsr/default.htm); [archive](https://www.federalreserve.gov/releases/housedebt/default.htm)). With only 21 years, the new series contains one housing bust and one pandemic, so percentiles of it will be dominated by those two episodes.

The evidence behind the DSR is strong but indirect. In BIS cross-country work, it "dominates at shorter horizons" as an early warning of banking crises ([Drehmann and Juselius, BIS WP 421](https://www.bis.org/publ/work421.htm)). That work measures the private non-financial sector's debt service, so it applies to the household DSR only by analogy.

### Use the flow into delinquency, not the share already late

The NY Fed's Household Debt and Credit report is the free, market-wide view across all lenders and products. It is an Excel workbook with quarterly flows into 30- and 90-day delinquency by product from 2003 ([NY Fed HHDC](https://www.newyorkfed.org/microeconomics/hhdc); [Q2 2026 workbook](https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/HHD_C_Report_2026Q2.xlsx)). **For cards, the NY Fed itself now says to watch the flow, not the share of balances already 90 days late.**

That share rose from 7.6% in 2022:Q3 to 12.8% in 2026:Q1, while the flow into it "has remained relatively stable for almost two years". The cause is reporting practice: about 40% of charged-off debts were still on credit reports a year later in 2004–2012; by 2024 the figure was 80% ([Liberty Street, Aug 2026](https://libertystreeteconomics.newyorkfed.org/2026/08/how-distressed-are-consumers-reconciling-diverging-credit-card-delinquency-measures/)). An outlier engine reading the stock would flag reporting drift as stress.

Q2 2026 annualised flows into 90 days late were 6.97% for cards, 3.00% for auto, 1.52% for mortgages and 7.83% for student loans. Student loans need their own regime marker. The payment pause and the "on-ramp" kept delinquencies off credit reports from 2020:Q2 to 2024:Q4. The 90-day share then jumped from under 1% to nearly 8% in 2025:Q1 ([Liberty Street, May 2025](https://libertystreeteconomics.newyorkfed.org/2025/05/student-loan-delinquencies-are-back-and-credit-scores-take-a-tumble/)), and 2026 readings carry distortions from defaulted loans being reported again. State tables cover only 11 states. Redistribution terms for these Equifax-derived figures were not found.

### Bankruptcies, consumer credit and card terms

Bankruptcy filings confirm the direction from two independent sources. Non-business filings in the 12 months to June 2026 were 581,570, up about 12% from 519,486 ([US Courts F-2, 2026](https://www.uscourts.gov/sites/default/files/document/bf_f2_0630.2026.pdf); [2025](https://www.uscourts.gov/sites/default/files/document/bf_f2_0630.2025.pdf)). Epiq data, reported second-hand, show individual Chapter 7 filings up 13% year to date ([ABF Journal](https://www.abfjournal.com/?p=173384)). US Courts publishes PDF tables, with no API.

The Fed's G.19 consumer-credit release runs monthly from 1943 (revolving credit from 1968). Its levels contain breaks, so the Fed says percent changes "are adjusted to exclude the effect of such breaks"; the tool should use those growth rates ([G.19](https://www.federalreserve.gov/releases/g19/current/default.htm)). G.19 also gives card interest rates from 1994: 21.19% across all accounts in August 2026. These are sampled once a quarter even though FRED stores them monthly.

The Philadelphia Fed's large-bank card data on FRED add a direct "running out of room" measure. The share of accounts making only the minimum payment was 10.15% in 2026:Q2, against 8.76% when the series began in 2012:Q3 ([FRED RCCCBSHRMIN](https://fred.stlouisfed.org/series/RCCCBSHRMIN)).

### Lending standards: long for cards, short for everything else

SLOOS card standards run from 1996, and banks' willingness to make consumer instalment loans from 1982. Auto and other consumer standards start only in 2011. Mortgage standards must be spliced across three category regimes: 1990–2007, 2007–2014 and from 2015. The July 2026 survey reported tighter card standards. It also found standards "at the tighter end of the range for all loan categories except C&I loans" relative to the range since 2005 ([July 2026 SLOOS](https://www.federalreserve.gov/data/sloos/sloos-202607.htm)). A tightening shock to a demand-adjusted SLOOS supply measure leads to "a substantial decline in output and the capacity of businesses and households to borrow from banks" ([Bassett et al., FEDS 2012-24](https://www.federalreserve.gov/econres/feds/changes-in-bank-lending-standards-and-the-macroeconomy.htm)). No test of consumer standards against consumer charge-offs was found.

### Sentiment: one survey is openly licensed; the others are not

The sentiment surveys differ most in licensing.

- **NY Fed Survey of Consumer Expectations: openly licensed.** It is monthly from June 2013 and asks the most lending-relevant question: the mean probability of missing a minimum debt payment in the next three months. That stood at 12.2% in September 2026, against a 12.3% full-sample mean and 15.3% in December 2025. Its licence grants "a worldwide, royalty-free, nonexclusive right to reproduce, use, and distribute" with attribution ([SCE data](https://www.newyorkfed.org/medialibrary/interactives/sce/sce/downloads/data/frbny-sce-data.xlsx)). No study tests it against realised delinquency.
- **University of Michigan: internal use only.** Its data may not be reproduced or redistributed "without the express written consent of the University of Michigan" ([UMich terms](https://data.sca.isr.umich.edu/agreement.php)), and it reaches FRED a month late. Its mid-2024 switch to web interviews is a break. Its May 2026 reading was a record low even on a consistent method ([Hsu, Jul 2026](https://data.sca.isr.umich.edu/fetchdoc.php?docid=81444)).
- **Conference Board: licensed.** Its detailed data are sold by subscription ([Conference Board](https://www.conference-board.org/press/consumer-confidence-premium-launch)).

The evidence that sentiment predicts anything is "modest" and depends on the period. Sentiment improved consumption forecasts "at some times", but not once macro variables were included ([Wilcox, FRBSF 2008](https://www.frbsf.org/research-and-insights/publications/economic-letter/2008/06/consumer-sentiment-spending/)).

### Leverage growth and negative equity carry the strongest evidence

The strongest published household evidence concerns leverage. "An increase in the household debt to GDP ratio in the medium run predicts lower subsequent GDP growth, higher unemployment" across 30 countries from 1960 to 2012 ([Mian, Sufi and Verner, NBER w21581](https://www.nber.org/papers/w21581)). Household leverage in 2006 was "a powerful statistical predictor" of how severe the 2007–09 recession was in each US county ([Mian and Sufi, NBER w15896](https://www.nber.org/papers/w15896)). The tool should therefore rate growth in debt-to-income over several years, not monthly credit growth.

For mortgages, "about 80 percent of defaults" in a sample of 2006 borrowers came from "income shocks combined with negative equity". The median borrower did not walk away strategically until equity fell to −62% ([Bhutta, Dokko and Shan, FEDS 2010-35](https://www.federalreserve.gov/pubs/feds/2010/201035/index.html)). House prices matter through collateral, but default needs an income shock too, which ties housing back to the labour series.

### Housing: rate valuation against income, and watch government-backed loans

Housing has free, long cores for every sub-topic.

- **Mortgage rates.** Freddie Mac's weekly survey runs from April 1971: 7.40% on 8 October 2026. It changed method on 17 November 2022, when it began using Loan Product Advisor data instead of surveying lenders. Its terms allow use "with proper attribution" but prohibit alteration ([Freddie Mac PMMS](https://www.freddiemac.com/pmms)).
- **House prices.** The FHFA index runs quarterly from 1975 and monthly from 1991, down to state, metro, county and ZIP code. FHFA also publishes volatility parameters that could set a normal band ([FHFA HPI](https://www.fhfa.gov/data/hpi)). Case-Shiller is S&P Dow Jones Indices' licensed product ([FRED CSUSHPINSA](https://fred.stlouisfed.org/series/CSUSHPINSA)).
- **Construction.** Census starts, permits and new-home months' supply run from 1959–63. Months' supply was 8.5 in August 2026, with a ±17.2% confidence interval on the monthly change, so it needs smoothing ([Census new home sales](https://www.census.gov/construction/nrs/pdf/newressales.pdf)).
- **Affordability.** The Atlanta Fed affordability monitor is free monthly from 2005, by metro and county: 68.4 in July 2026, where below 100 means unaffordable. Its price and insurance inputs are licensed ([Atlanta Fed HOAM](https://www.atlantafed.org/research-and-data/data/home-ownership-affordability-monitor)).
- **Not usable for history.** NAR's series appear on FRED for only 13 months ([FRED FIXHAI](https://fred.stlouisfed.org/series/FIXHAI)). Negative equity, 1.9% of mortgaged homes against 26% in Q4 2009, is free only as a Cotality press headline ([Cotality](https://www.cotality.com/press-releases/us-homeowner-equity-plateau-q2-2026)).

The Fed judges house prices by valuation, not raw growth. Its severe-scenario guide uses the ratio of house prices to per-capita disposable income. The FSR charts price-to-rent and a model-based valuation it calls "near historically high levels" ([FSR asset valuations](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-asset-valuations.htm)). The tool should rate house prices twice: the level relative to income or rent as a vulnerability, and the recent change as stress.

For delinquency, FHFA's National Mortgage Database is free, quarterly from 2002, covers all states and splits out "Government / Non-Conventional" loans. National 90-day delinquency was 1.0% in 2026:Q2 against a 4.6% peak ([FHFA NMDB](https://www.fhfa.gov/data/national-mortgage-database-aggregate-statistics)). The CFPB's monthly county series is the only free county-level mortgage delinquency data, but it lags about eight months ([CFPB](https://www.consumerfinance.gov/data-research/mortgage-performance-trends/download-the-data/)). Today's mortgage risk is concentrated in loan type rather than leverage. The FSR flags "borrowers with FHA and VA loans" ([FSR borrowing](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-borrowing.htm)), and ICE reported foreclosure starts up 22.8% year on year in July 2026 ([ICE First Look](https://s2.q4cdn.com/154085107/files/doc_news/ICE-First-Look-at-Mortgage-Performance-Mortgage-Delinquencies-Ease-in-July-as-Both-New-Defaults-and-Cure-Activity-Improve-2026.pdf)). A single national rate would miss that.

| Indicator (id) — what it measures | Publisher | Frequency · from | Access · licence | Breaks and cautions | Who uses it this way | Evidence of stress |
|---|---|---|---|---|---|---|
| Household debt service ratio ([TDSP](https://fred.stlouisfed.org/series/TDSP), MDSP, CDSP) | Fed Board | Quarterly · 2005 (new); 1980–2024 archived | Public; FRED; Fed's old download service being retired | Rebuilt 2024, includes escrow; do not splice the two | FDIC Risk Review; FSR | BIS: best short-horizon crisis warning (cross-country) |
| Financial obligations ratio ([FODSP](https://fred.stlouisfed.org/series/FODSP)) | Fed Board | **Stopped after 2023:Q3** | — | No insurance or property-tax data | — | — |
| Flow into 30+ and 90+ delinquency by product | NY Fed (CCP/Equifax) | Quarterly · 2003Q1; ~6-week lag | Free Excel, no key; reuse terms not found | Card stock drifts with reporting; student loans 2020–24; 11 states | FSR | Short mechanical lead on charge-offs |
| Consumer bankruptcies (Table F-2, F-5A by county) | US Courts | Quarterly, rolling 12 months | Free PDF, no API | 2005 bankruptcy reform | FDIC Risk Review | Realised stress |
| Consumer credit ([TOTALSL](https://fred.stlouisfed.org/series/TOTALSL), [REVOLSL](https://fred.stlouisfed.org/series/REVOLSL)) | Fed G.19 | Monthly · 1943 / 1968 | Public domain | Level breaks (2010, 2020, 2025): use growth | Old DSR input | Multi-year growth predicts weakness (Mian–Sufi–Verner) |
| Card and personal-loan interest rates ([TERMCBCCALLNS](https://fred.stlouisfed.org/series/TERMCBCCALLNS), TERMCBPER24NS) | Fed G.19 | Quarterly samples · 1994 / 1972 | Public domain | Stored monthly with gaps | — | None tested |
| Large-bank card data: minimum-payment share, 30+ days late ([RCCCBSHRMIN](https://fred.stlouisfed.org/series/RCCCBSHRMIN)) | Philadelphia Fed (FR Y-14M) | Quarterly · 2012Q3 | FRED | Large banks only; short | — | None tested |
| SLOOS consumer: cards ([DRTSCLCC](https://fred.stlouisfed.org/series/DRTSCLCC)), willingness to lend (DRIWCIL), auto, mortgage | Fed | Quarterly · 1996; 1982; auto 2011; mortgage in three regimes | Public domain | Category splits 2007, 2011, 2015 | FSR, OCC, FDIC; Fed card model | Bassett et al. (credit and output) |
| Probability of missing a debt payment | NY Fed SCE | Monthly · Jun 2013 | **Open licence**, Excel | Short history | — | No test found |
| Consumer sentiment ([UMCSENT](https://fred.stlouisfed.org/series/UMCSENT)) | University of Michigan | Monthly · 1978 (quarterly 1966) | **No redistribution**; FRED 1 month late | Web mode from mid-2024; partisan shift | In OECD leading index (per publisher) | Modest, period-dependent |
| Consumer Confidence Index | Conference Board | Monthly · 1967 | **Licensed** | — | — | — |
| 30-year mortgage rate ([MORTGAGE30US](https://fred.stlouisfed.org/series/MORTGAGE30US)) | Freddie Mac | Weekly · Apr 1971 | Attribution; no alteration | Method change Nov 2022 | Fed stress test (rate and spread) | Payment shock |
| FHFA house price index ([USSTHPI](https://fred.stlouisfed.org/series/USSTHPI); monthly HPIPONM226S) | FHFA | Quarterly · 1975; monthly · 1991; down to ZIP | Free | Conforming-loan sample | Truist, Regions, M&T, JPMorgan | Negative equity plus income shock (Bhutta et al.) |
| Case-Shiller | S&P DJI | Monthly · 1987 | **Licensed** | — | — | — |
| Home ownership affordability | Atlanta Fed | Monthly · 2005; metro, county | Free download; inputs licensed | — | — | None tested |
| Starts, permits, new-home months' supply ([HOUST](https://fred.stlouisfed.org/series/HOUST), [PERMIT](https://fred.stlouisfed.org/series/PERMIT), [MSACSR](https://fred.stlouisfed.org/series/MSACSR)) | Census / HUD | Monthly · 1959 / 1960 / 1963 | Public domain | Permits imputation change Feb 2025; wide sampling error | FDIC home-sales chart; permits in leading index | Business-cycle lead |
| Active listings ([ACTLISCOUUS](https://fred.stlouisfed.org/series/ACTLISCOUUS)) | Realtor.com | Monthly · Jul 2016 | FRED | Method change 2022 | — | — |
| Owners' equity share ([HOEREPHRE](https://fred.stlouisfed.org/series/HOEREPHRE)); negative equity | Fed Z.1; Cotality | Quarterly · 1945; Cotality licensed | Free aggregate; licensed tail | Aggregate hides the underwater tail | FSR (licensed McDash) | Double trigger |
| Mortgage delinquency by state and loan type | FHFA NMDB | Quarterly · 2002Q1 | Free CSV, no key | Stale-account rule from 2012; 2020–21 forbearance | — | Realised stress |
| Mortgage delinquency by county | CFPB | Monthly · 2008; ~8-month lag | Free CSV | Connecticut county change | — | Realised stress |
| MBA delinquency survey; ICE First Look | MBA; ICE | Quarterly · 1979; monthly | **Licensed** (free headlines) | — | Practitioners | Realised stress |

## Commercial risk reads off spreads, standards and CRE prices, but under licence

### Activity series are free and long, except the purchasing-manager indexes

The activity backbone for a commercial narrative is free, public domain and long:

- industrial production from 1919 and capacity utilisation from 1967 ([FRED INDPRO](https://fred.stlouisfed.org/series/INDPRO); [FRED TCU](https://fred.stlouisfed.org/series/TCU));
- real GDP and BEA corporate profits from 1947 ([FRED GDPC1](https://fred.stlouisfed.org/series/GDPC1); [FRED CPROFIT](https://fred.stlouisfed.org/series/CPROFIT));
- orders for business equipment excluding aircraft, a measure of investment plans, from 1992 ([FRED NEWORDER](https://fred.stlouisfed.org/series/NEWORDER)).

The orders series is in nominal dollars, so a "normal level" over 1992–2026 must be deflated, or the 2021–23 inflation reads as strength.

**The best-known purchasing-manager indexes cannot go in a shared tool.** ISM's 22 series were removed from FRED in 2016 ([FRED, 2016](https://news.research.stlouisfed.org/2016/06/institute-for-supply-management-data-to-be-removed-from-fred/)). ISM's terms forbid redistributing "any portion" without written authorisation ([ISM](https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/pmi/august/)). S&P Global's PMI is a paid product. The free substitutes are the regional Fed manufacturing surveys, released within the month they cover: Philadelphia from 1968, New York from 2001 and Dallas from 2004 ([FRED Philadelphia Fed survey](https://fred.stlouisfed.org/series/GACDFSA066MSFRBPHI)).

### Corporate spreads: FRED now holds three years of ICE data

The largest data change of 2026 is in corporate spreads. **Since April 2026 FRED serves only a rolling three years of every ICE BofA option-adjusted spread series.** On 14 October 2026 the high-yield and BBB series both started on 16 October 2023. ICE's terms make the data "for your internal use only" and bar furnishing it "to any third-party without prior written approval" ([FRED BAMLC0A0CM](https://fred.stlouisfed.org/series/BAMLC0A0CM); [FRED BAMLH0A0HYM2](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)). Moody's Baa yields go back to 1919, and the Baa-minus-Treasury spread to 1986. But Moody's text on FRED bars them being "STORED FOR SUBSEQUENT USE" or "REDISTRIBUTED" without consent ([FRED BAA10Y](https://fred.stlouisfed.org/series/BAA10Y)).

**The free full-cycle substitute is the Fed's own file of the GZ spread and the excess bond premium**, monthly from January 1973 at a permanent URL. The excess bond premium is "a component of corporate bond credit spreads that is not directly attributable to expected default risk". The same file gives a 12-month recession probability. In September 2026 the spread was 0.93, the premium −0.39 and the probability 0.091. The premium peaked at 3.41 in October 2008 ([EBP CSV](https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv)). It is a staff research product, and "the entire history of the EBP may revise each month", so the tool must keep every download it rates against ([FEDS Note](https://www.federalreserve.gov/econres/notes/feds-notes/updating-the-recession-risk-and-the-excess-bond-premium-20161006.htm)). Gilchrist and Zakrajšek found the premium "a considerably more powerful predictor of economic activity" than standard default-risk measures ([NBER w17021](https://www.nber.org/papers/w17021)).

### Financial-conditions indexes are already standardised

Three Fed financial-conditions indexes are built so that zero means average:

- **Chicago Fed NFCI.** Weekly from 1971, from 105 measures, with an adjusted version that removes the effect of the economic cycle ([Chicago Fed NFCI](https://www.chicagofed.org/research/data/nfci/about)).
- **St. Louis Fed STLFSI4.** Weekly from 1993; now in its fourth version ([FRED STLFSI4](https://fred.stlouisfed.org/series/STLFSI4)).
- **Kansas City Fed KCFSI.** Monthly from 1990; its bank-stock input changed in 2021 ([FRED KCFSI](https://fred.stlouisfed.org/series/KCFSI)).

On FRED, the VIX is a daily close from 1990, "reprinted with permission" from CBOE ([FRED VIXCLS](https://fred.stlouisfed.org/series/VIXCLS)). The 10-year minus 3-month Treasury spread runs from 1982 and is public domain ([FRED T10Y3M](https://fred.stlouisfed.org/series/T10Y3M)). The TED spread stopped in 2022 when LIBOR was retired ([FRED TEDRATE](https://fred.stlouisfed.org/series/TEDRATE)).

### Lending standards and loan volumes: long for C&I, short for CRE

SLOOS standards and demand for commercial and industrial (C&I) loans run quarterly from 1990–91 ([FRED DRTSCILM](https://fred.stlouisfed.org/series/DRTSCILM)). **SLOOS questions for CRE by property type start only in 2013:Q4**, 52 observations with no CRE bust in them ([FRED SUBLPDRCSN](https://fred.stlouisfed.org/series/SUBLPDRCSN)).

The H.8 weekly bank balance sheet gives C&I loans from 1947 (monthly) and CRE loans from 2004. Loan growth is an ambiguous stress signal: firms draw credit lines in a crisis. The Call Report reclassification of loans to non-depository financial institutions also moved **$193.2 billion of C&I loans** out of that line through September 2025 ([FDIC Risk Review PDF](https://www.fdic.gov/analysis/2026-risk-review-full.pdf)).

The Fed's survey of business-loan rates ended in 2017 ([Fed E.2](https://www.federalreserve.gov/releases/e2/current/)). The prime rate, from 1949, is the free benchmark that remains ([FRED MPRIME](https://fred.stlouisfed.org/series/MPRIME)).

The outcome series the narrative explains are free from the Fed:

- business-loan charge-off rate, from 1985: 0.58% in 2026:Q2 ([FRED CORBLACBS](https://fred.stlouisfed.org/series/CORBLACBS));
- CRE charge-off rate excluding farmland, from 1991: 0.14% ([FRED CORCREXFACBS](https://fred.stlouisfed.org/series/CORCREXFACBS)).

### Business failures and small firms: rising filings, short or restricted data

Business bankruptcy filings rose **16.9% to 26,941** in the year to June 2026 ([US Courts, Jul 2026](https://www.uscourts.gov/data-news/judiciary-news/2026/07/28/bankruptcies-rise-122-percent)). Epiq counts commercial Chapter 11 filings up 11% year to date ([ABF Journal](https://www.abfjournal.com/?p=173384)). A pending bill to restore the $7.5 million limit for the small-business form of Chapter 11 would shift those counts for legal rather than economic reasons.

The Census business-applications series runs from 2004. The January 2026 release redefined the "high-propensity" series (applications most likely to become employers) for its whole history, so any copy stored before then must be re-pulled ([Census BFS](https://www.census.gov/econ/bfs/index.html)). The biweekly Census Business Trends and Outlook Survey is consistent only from September 2023 ([Census BTOS](https://www.census.gov/data/experimental-data-products/business-trends-and-outlook-survey.html)). NFIB's small-business index, which the FDIC cites, is copyrighted, carries no redistribution licence and is not on FRED ([NFIB](https://www.nfib.com/page/sbet)).

### CRE prices are free; vacancy and CMBS delinquency are not

**The CRE price index in the Fed's stress test is free.** It is the Z.1 series FL075035503 ([FRED BOGZ1FL075035503Q](https://fred.stlouisfed.org/series/BOGZ1FL075035503Q)), quarterly from 1945. From 1996:Q1 it chains the CoStar value-weighted composite excluding multifamily. Before 1996 it blends three appraisal-based series, which smooth and lag ([Fed series analyzer](https://www.federalreserve.gov/apps/fof/SeriesAnalyzer.aspx?s=FL075035503&t=)). CoStar revisions back to 1996 enter every year, so this series needs its versions kept too.

Every other CRE input is licensed:

- **Vacancy.** The FDIC's office vacancy figure (14.0% at end-2025) comes from CoStar.
- **Price indexes.** Both the FSR and the FDIC chart prices from MSCI Real Capital Analytics ([FDIC Risk Review PDF](https://www.fdic.gov/analysis/2026-risk-review-full.pdf)).
- **CMBS delinquency.** This is the timeliest CRE stress signal, but every series is a vendor's. Trepp's August 2026 rate was 7.85% overall and 12.00% for office; non-performing matured balloon loans were 81% of newly delinquent balances, so the stress is about refinancing at maturity ([CRE Daily](https://www.credaily.com/?p=222275)). KBRA put September at 7.7%, with office distress at 17.6% ([KBRA](https://www.kbra.com/publications/jXhmdtGY/kbra-releases-research-cmbs-loan-performance-trends-september-2026?format=web)).

The vendors' definitions differ, so a narrative must name its vendor and never mix vendors in one series.

### Business costs and tariffs

Cost series are free and public domain:

- PPI for all commodities, from 1913 ([FRED PPIACO](https://fred.stlouisfed.org/series/PPIACO));
- import prices, from 1982;
- WTI crude, $96.24 a barrel on 6 October 2026, and Henry Hub gas ([FRED DCOILWTICO](https://fred.stlouisfed.org/series/DCOILWTICO));
- BEA customs-duty receipts, from 1959 ([FRED B235RC1Q027SBEA](https://fred.stlouisfed.org/series/B235RC1Q027SBEA)).

Duties at a $306.4 billion annual rate in 2026:Q2 are an outlier by construction. They measure policy, not borrower stress. The Yale Budget Lab puts the average statutory tariff rate at 11.0% after the 2026 switches between legal authorities ([Yale Budget Lab](https://budgetlab.yale.edu/research/state-us-tariffs)). Whether high oil prices are stress depends on the book: they hurt energy users and help energy producers.

### The evidence stops at recessions, not commercial charge-offs

The commercial evidence is strong for recessions and output and missing for losses.

- **The term spread.** It "significantly outperforms other financial and macroeconomic indicators in predicting recessions two to six quarters ahead". Estrella and Mishkin's model implies a four-quarters-ahead recession probability of 10% at a spread of 0.76 points and 50% at −0.82 ([Estrella and Mishkin, 1996](https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci2-7.pdf)).
- **Lending standards.** SLOOS tightening "strongly dominate[s] loan rates in explaining variation in business loans and output" ([Lown and Morgan](https://ideas.repec.org/p/hhs/sifrwp/0027.html)). But an Atlanta Fed paper finds the survey's power "only marginally" extends to banking-sector performance ([Atlanta Fed WP 2006-24](https://ideas.repec.org/p/fip/fedawp/2006-24.html)).

**No study read here measures how many quarters any of these lead C&I or CRE charge-offs.** Any claim of a lead on losses needs the firm's own backtest against the Fed's charge-off series.

| Indicator (id) — what it measures | Publisher | Frequency · from | Access · licence | Breaks and cautions | Who uses it this way | Evidence of stress |
|---|---|---|---|---|---|---|
| Industrial production; capacity utilisation ([INDPRO](https://fred.stlouisfed.org/series/INDPRO), [TCU](https://fred.stlouisfed.org/series/TCU)) | Fed G.17 | Monthly · 1919 / 1967 | Public domain | Re-weighted at annual revisions | NBER dating input (production) | Coincident |
| Real GDP ([GDPC1](https://fred.stlouisfed.org/series/GDPC1)) | BEA | Quarterly · 1947 | Public domain | Revisions | All 9 regional 10-Ks; stress test; OCC; FDIC | Core loss-model driver |
| Corporate profits ([CPROFIT](https://fred.stlouisfed.org/series/CPROFIT)) | BEA | Quarterly · 1947 | Public domain | Revisions | — | None tested |
| Business equipment orders ([NEWORDER](https://fred.stlouisfed.org/series/NEWORDER)) | Census M3 | Monthly · 1992 | Public domain | Nominal; industry classification changed 2001 | Conference Board leading index | Plausible only |
| Regional Fed manufacturing surveys ([Philadelphia](https://fred.stlouisfed.org/series/GACDFSA066MSFRBPHI), [New York](https://fred.stlouisfed.org/series/GACDISA066MSFRBNY), [Dallas](https://fred.stlouisfed.org/series/BACTSAMFRBDAL)) | Philadelphia, NY, Dallas Feds | Monthly · 1968 / 2001 / 2004 | Copyrighted: citation required | — | — | Plausible only |
| ISM PMI; S&P Global PMI | ISM; S&P Global | Monthly | **Licensed**; no redistribution | Removed from FRED 2016 | Widely quoted | — |
| ICE BofA spreads, IG, BBB, HY ([BAMLC0A4CBBB](https://fred.stlouisfed.org/series/BAMLC0A4CBBB)) | ICE via FRED | Daily · **only 3 years on FRED** | **Pre-approval required; internal use only** | Truncated from Apr 2026 | Fed stress test (BBB yield); FSR; Truist, Fifth Third, U.S. Bancorp | Stress-test driver |
| Moody's Baa yield and spread ([BAA](https://fred.stlouisfed.org/series/BAA), [BAA10Y](https://fred.stlouisfed.org/series/BAA10Y)) | Moody's via FRED | Monthly · 1919; daily · 1986 | **No storing or redistribution** without consent | — | Fifth Third's credit spread | — |
| GZ spread, excess bond premium, recession probability ([EBP CSV](https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv)) | Fed Board staff | Monthly · 1973 | Public Fed data; permanent URL, no key | Whole history revises monthly | FSR | Strong for activity (Gilchrist–Zakrajšek) |
| Chicago Fed financial conditions ([NFCI](https://fred.stlouisfed.org/series/NFCI), ANFCI, credit subindex) | Chicago Fed | Weekly · 1971 | Copyrighted: citation required | Standardised on full sample | — | Publisher's claim only |
| St. Louis and KC Fed stress indexes ([STLFSI4](https://fred.stlouisfed.org/series/STLFSI4), [KCFSI](https://fred.stlouisfed.org/series/KCFSI)) | St. Louis, KC Feds | Weekly · 1993; monthly · 1990 | Copyrighted: citation required | Fourth version; 2021 input change | — | None tested |
| VIX ([VIXCLS](https://fred.stlouisfed.org/series/VIXCLS)) | CBOE via FRED | Daily · 1990 | CBOE copyright ("reprinted with permission") | — | Fed stress test (quarterly maximum) | Stress-test driver |
| Term spread ([T10Y3M](https://fred.stlouisfed.org/series/T10Y3M)); NY Fed recession probability | Treasury via FRED; NY Fed | Daily · 1982; monthly | Public domain; NY Fed PDF and spreadsheet | Model fitted to 1959–2009 | NY Fed; leading index (10y minus fed funds) | Strong for recessions; false alarm 2023–25 |
| Policy uncertainty ([USEPUINDXM](https://fred.stlouisfed.org/series/USEPUINDXM), EPUTRADE) | Baker, Bloom, Davis | Monthly · 1985 | Public domain per FRED | — | — | None tested |
| SLOOS C&I standards and demand ([DRTSCILM](https://fred.stlouisfed.org/series/DRTSCILM), DRTSCIS, DRSDCILM) | Fed | Quarterly · 1990 / 1991 | Public domain | — | FSR, OCC, FDIC | Lown–Morgan; Bassett et al.; weak for bank outcomes |
| SLOOS CRE standards by type ([SUBLPDRCSN](https://fred.stlouisfed.org/series/SUBLPDRCSN) etc.) | Fed | Quarterly · 2013Q4 | Public domain | 52 observations, no bust | FSR | None tested |
| C&I and CRE loan volumes ([BUSLOANS](https://fred.stlouisfed.org/series/BUSLOANS), TOTCI, CREACBM027SBOG) | Fed H.8 | Monthly · 1947; weekly · 1973; CRE · 2004 | Public domain | $193.2bn C&I moved to loans to non-depository financial firms | — | Ambiguous (credit-line draws) |
| Prime rate ([MPRIME](https://fred.stlouisfed.org/series/MPRIME)); SOFR | Fed H.15; NY Fed | Monthly · 1949; daily · 2018 | Public domain; SOFR citation required | Business-loan rate survey (E.2) ended 2017 | Fed stress test (prime); KeyCorp (SOFR) | — |
| Bank C&I and CRE charge-off and delinquency rates ([CORBLACBS](https://fred.stlouisfed.org/series/CORBLACBS), [CORCREXFACBS](https://fred.stlouisfed.org/series/CORCREXFACBS)) | Fed | Quarterly · 1985 / 1991 | Public domain | — | Outcomes to explain | Backtest targets |
| Business bankruptcies (Table F-2) | US Courts | Quarterly, rolling 12 months | Free PDF/XLSX, no API | Small-business Chapter 11 limit in flux | FDIC Risk Review | Realised stress |
| Business applications ([BABATOTALSAUS](https://fred.stlouisfed.org/series/BABATOTALSAUS), BAHBATOTALSAUS) | Census BFS | Monthly · 2004 | Public domain | High-propensity series redefined Jan 2026; IRS outage Dec 2025 | — | Measures entry, not distress |
| Business Trends and Outlook Survey | Census | Biweekly · Sep 2023 | Public; experimental | Scope break 2023 | — | — |
| NFIB small business optimism | NFIB | Monthly · 1986 (quarterly 1974) | **Copyrighted**; no licence found | — | FDIC Risk Review | — |
| Z.1 CRE price index ([BOGZ1FL075035503Q](https://fred.stlouisfed.org/series/BOGZ1FL075035503Q)) | Fed Z.1 (CoStar chain) | Quarterly · 1945 (CoStar-based from 1996) | Public domain | Appraisal-based before 1996; no multifamily; annual revisions | Fed stress test; M&T, U.S. Bancorp, Truist | Stress-test driver |
| Office vacancy; MSCI-RCA and Green Street price indexes | CoStar; MSCI; Green Street | Monthly or quarterly | **Licensed** (free headlines) | — | FDIC, FSR, OCC | — |
| CMBS delinquency | Trepp; KBRA | Monthly | **Licensed** (free headlines) | Vendor definitions differ | FDIC Risk Review | Realised stress, timeliest |
| PPI ([PPIACO](https://fred.stlouisfed.org/series/PPIACO), PPIFIS); import prices ([IR](https://fred.stlouisfed.org/series/IR)) | BLS | Monthly · 1913; 2009; 1982 | Public domain | Final-demand PPI only from 2009 | KeyCorp (PPI) | Plausible only |
| WTI, Henry Hub ([DCOILWTICO](https://fred.stlouisfed.org/series/DCOILWTICO), DHHNGSP) | EIA | Daily · 1986 / 1997 | Public domain; EIA API needs a key | — | — | Sign depends on the book |
| Customs duties ([B235RC1Q027SBEA](https://fred.stlouisfed.org/series/B235RC1Q027SBEA)); tariff rate | BEA; Yale Budget Lab | Quarterly · 1959 | Public domain; Yale terms unchecked | 2026 policy breaks | — | Policy context only |

## Published flags rate position or change, and the best-known triggers misfired in 2022–25

Published "is this reading unusual?" methods fall into four families, and the planned tool can reproduce each.

1. **Position against the series' own history.** The FSR's percentile language is the clearest example: "upper quartile", "90th percentile", "near its median since 2005". Its formal ancestor is a 2015 Fed staff heat map. That map standardised 44 indicators against 1990Q1–2014Q4. It compared four ways of mapping a reading to a 0–1 scale (kernel density, normal distribution, min–max and rank), and set illustrative thresholds at the **65th and 85th percentiles**, with an **80th-percentile "red zone"** when three categories cross it ([Aikman et al., FEDS 2015-059](https://www.federalreserve.gov/econresdata/feds/2015/files/2015059pap.pdf)). The OFR's Financial System Vulnerabilities Monitor coloured 58 indicators "based on their positions within a long-term range" but was discontinued after Q4 2019 ([OFR](https://www.financialresearch.gov/financial-vulnerabilities/)).
2. **Change from a recent extreme**, such as the Sahm and Michaillat–Saez rules.
3. **Composite indexes with fixed cut-offs.**
4. **Deviation from trend**, such as the BIS credit-to-GDP gap.

| Method | Publisher | Rule | Published record | Use in a 1-to-5 tool |
|---|---|---|---|---|
| Percentile against own history | Fed FSR ([borrowing](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-borrowing.htm)) | Verdicts such as "upper quartile", "90th percentile" | Descriptive | The template for every series |
| Fixed calm benchmark | FDIC Risk Review and QBP ([Risk Review](https://www.fdic.gov/analysis/2026-risk-review)) | Compare with the 2015:Q1–2019:Q4 average | Descriptive | Shows how much the window choice matters |
| Z-score and percentile heat map | Aikman et al. 2015 | 65th/85th thresholds; 80th "red zone" | Caught the mid-2000s build-up; in real time also flagged the late 1990s | Closest precedent |
| Sahm rule | Sahm, Hamilton Project 2019 ([PDF](https://www.hamiltonproject.org/wp-content/uploads/2023/01/Sahm_web_20190506.pdf)) | 3-month average unemployment ≥0.50 points above its low in the prior 12 months | ~3 months after recession start; real-time false alarms in 1976 and 2024 | Change flag for labour series |
| Michaillat–Saez | Oxford Bulletin 2025 ([PDF](https://eml.berkeley.edu/~saez/michaillat-saezOBES25.pdf)) | Minimum of unemployment and vacancy indicators: 0.29 = probable, 0.81 = certain | All 15 recessions since 1929, no false positives (threshold set in-sample) | Faster labour flag |
| Jobless-claims threshold | St. Louis Fed 2025 ([blog](https://www.stlouisfed.org/on-the-economy/2025/jan/are-initial-jobless-claims-useful-gauge-labor-market-conditions)) | 400k rule of thumb; best-fit level drifts | Mostly informative in expansions | Use change from a recent low, not a fixed level |
| Extended Benefits trigger | Statute; DOL weekly ([notice](https://oui.doleta.gov/unemploy/trigger/2026/trig_101126.html)) | 13-week insured rate ≥5% and ≥120% of prior two years | 0 states on, Oct 2026 | Statutory red line by state |
| CFNAI 3-month average | Chicago Fed ([about](https://www.chicagofed.org/research/data/cfnai/about)) | Below −0.70 after an expansion means recession risk; above +0.70 means inflation risk | Publisher's historical association | Published cut-off |
| Leading index "3Ds" | Conference Board ([LEI](https://www.conference-board.org/topics/us-leading-indicators)) | Diffusion ≤50 and 6-month annualised growth below −4.3% (−4.4% in 2024) | Signalled in 2022–23; stood down Feb 2024 | Cite only (licensed data) |
| Yield-curve probit | NY Fed ([Prob_Rec](https://www.newyorkfed.org/medialibrary/media/research/capital_markets/Prob_Rec.pdf)) | 12-month-ahead probability; 30% reading convention | 2006 paper: above 30% before each recession in its sample. Current file: 7 of 9 recessions since 1960, plus Nov 2023–Nov 2025 with no recession | Published probability |
| Excess bond premium probability | Fed staff ([CSV](https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv)) | Monthly 12-month recession probability | Peaked 0.9997, Oct 2008 | Published probability |
| Zero-line stress indexes | OFR, St. Louis, Chicago, KC Feds ([OFR FSI](https://www.financialresearch.gov/financial-stress-index/)) | 0 = average, standard-deviation units | No published stress threshold | Rate by percentile |
| Credit-to-GDP gap | Basel Committee 2010 ([PDF](https://www.bis.org/publications/201012-guidelines-guidance-national-authorities-operating-countercyclical-capital-buffer.pdf)) | One-sided HP trend; buffer begins at a 2-point gap, maximum at 10 | 2 points chosen to flag crises 2–3 years ahead | Trend-gap variant; Fed recorded commenters' view of "no academic consensus" |
| Significance floor | BLS ([CPS Q&A](https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm)) | A monthly unemployment change needs ~0.21 points (0.26 after the shutdown) | Statistical | Ignore smaller monthly moves |

### Ready-made composites

Several composite indexes publish their own reading. The CFNAI averages 85 indicators, with zero as trend growth. The KC Fed labour index publishes separate "level" and "momentum" measures. The OECD leading indicator treats 100 as trend: 101.00 for the US in September 2026, via a free API ([OECD SDMX](https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.STES/DSD_STES@DF_CLI/latest?references=none&detail=full)). The Dallas Fed's Weekly Economic Index is scaled to GDP growth: 2.71% for the week to 3 October ([Dallas Fed WEI](https://www.dallasfed.org/research/wei)). These can be rated against their own published thresholds or by percentile.

### What "severe" looks like, in the Fed's words

The Fed's scenario-design guides, finalised on 2 October 2026 and effective 2 November, are the only regulator-published sizes of a severe move. They are the natural anchor for a rating of 5. They are not thresholds for "abnormal today".

| Variable | Severe move under the Fed's guide |
|---|---|
| Unemployment | Rises 3–5 points, peaking in quarters 6–8, and in most cases to at least 10% |
| House prices to per-capita disposable income | Fall at least 25%, or to the 2012:Q1 trough |
| BBB spread over the 10-year Treasury | Higher of 500–600 bp or about +100 bp |
| Mortgage spread over the 10-year Treasury | Higher of +70–160 bp or a level of at least 300 bp |
| VIX | Higher of 65–75 or +10 points |
| Equities | Fall 50% (±10%) |
| CRE prices | Fall 30–45% |

Sources: [final rule, FR Doc. 2026-20247](https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20247.htm) and [2019 policy statement](https://www.govinfo.gov/content/pkg/FR-2019-02-28/html/2019-03504.htm).

### The 2022–25 false alarms

The recent record is a warning. FRED's real-time Sahm series crossed 0.50 in July 2024 (0.53), peaked at 0.57 in August and then reversed with no recession. Sahm herself, as reported in the press, attributed the crossing to growth in labour supply rather than weaker demand ([FRED SAHMREALTIME](https://fred.stlouisfed.org/series/SAHMREALTIME); [Fortune, Aug 2024](https://fortune.com/2024/08/02/recession-indicator-claudia-sahm-rule-trigger-unemployment-rate-jobs-report)).

The NY Fed's own data file shows its model at or above 30% for every target month from November 2023 to November 2025, peaking at 70.9%, with no NBER recession. That is by far the longest such spell on record. The only earlier one, in 1967, peaked at 41.1% ([NY Fed allmonth.xls](https://www.newyorkfed.org/medialibrary/media/research/capital_markets/allmonth.xls)). The Conference Board withdrew its 2022–23 recession signal in February 2024 ([Conference Board, Feb 2024](https://www.conference-board.org/topics/us-leading-indicators/press/us-lei-feb-2024)).

These are calculations from the publishers' data, not the publishers' own verdicts. Even so, all three of the best-known recession warnings fired with nothing behind them.

### What this means for a 1-to-5 design

The following is a synthesis of the published methods; no regulator publishes a 1-to-5 mapping.

**Rating scale.** The simplest defensible scale rates each series by its percentile within a stated window. One option is equal fifths, signed so that 5 always means more stress or more vulnerability. The alternative concentrates the upper ratings in the tail, using the 65th, 80th and 85th percentiles from Aikman et al. and the FSR's "upper quartile" and "90th percentile" language.

**Published anchors.** Where a published threshold exists, it should override or annotate the percentile: Sahm 0.50, Michaillat–Saez 0.29, CFNAI −0.70, the NY Fed's 30% convention, the Extended Benefits trigger, and the Fed's severe-move sizes.

**Rules by type of series:**

1. **Unemployment and claims need a level and a change.** Unemployment is lowest just before recessions, so its level alone would read 1 Low at the turn. The Fed's models and this repository's test both find the change carries the signal.
2. **Asset prices need a valuation and a momentum reading.** Overvaluation is the vulnerability, and a fall is the stress. The Fed's house-price guide and its "severity higher when asset values have risen" rule both point this way.
3. **Short series need a flag.** Series with two or fewer stress episodes in sample (the new DSR, the CRE SLOOS, the SCE survey) should carry a warning that their range is thin.

**Window.** The window should be stated on every rating, as the regulators do. Aikman et al. show that the real-time view "would have also signaled elevated risks during the late 1990s".

**Explaining each rating.** Given 2022–25, each rating needs a short note on what drove it and how long it has held. A shallow one-month crossing like the 1976 and 2024 Sahm readings would then be visible as such. That persistence check is an inference from the record, not a published rule.

## Roughly three dozen series are ready; licences and breaks put the rest in context only

Four tests decide which series suit a separate tool that finds each one's normal level and outliers:

1. free and redistributable;
2. long enough to contain three or more stress episodes;
3. monthly or quarterly, with documented breaks;
4. a clear direction of stress backed by published use or evidence.

Applying them gives three groups.

| Group | Series |
|---|---|
| **Core: ready to rate** | Unemployment rate, national and state (1948 / 1976); Sahm-style change in unemployment; initial and continuing claims (1967); payrolls (1939, scored on the latest benchmark); real GDP (1947); industrial production and capacity utilisation; CFNAI (1967); CPI headline and core (1947 / 1957); gasoline (EIA weekly, 1990); CPI motor vehicle insurance (1985 adjusted), used cars (1953); PPI homeowner's insurance (1998, change over the year); FHFA house prices (1975) and their ratio to disposable income; 30-year mortgage rate and its spread over the 10-year Treasury (1971); Z.1 CRE price index (1996 on for volatility); GZ spread and excess bond premium (1973); NFCI and adjusted NFCI (1971), STLFSI4 (1993), KCFSI (1990); 10-year minus 3-month spread (1982) and the NY Fed probability; SLOOS C&I standards and demand (1990) and card standards (1996); G.19 revolving credit growth (1968); FHFA NMDB mortgage delinquency by state and loan type (2002); NY Fed flows into delinquency by product (2003; reuse terms to confirm) |
| **Usable with care: short, broken or revised** | New debt service ratio (2005); SLOOS auto and other consumer (2011) and CRE (2013Q4); SCE missed-payment probability (2013, open licence); large-bank minimum-payment share (2012); JOLTS (2000); U-6 (1994); temporary help (1990); county unemployment (1990, not seasonally adjusted); real income, income excluding transfers, saving rate (heavily revised); wage measures; regional Fed surveys; business equipment orders (deflate); business applications (re-pull after the 2026 redefinition); Business Trends and Outlook Survey (2023); Atlanta Fed affordability (2005); new-home months' supply (smooth); CFPB county mortgage delinquency (8-month lag); student loans (regime-flag 2020–24); University of Michigan sentiment (internal display only; 2024 mode change); bankruptcy filings (PDF only); customs duties and tariffs (policy context); policy uncertainty; VIX (CBOE copyright) |
| **Context only: licensed, discontinued or stale** | ICE BofA spreads (3 years, internal use); Moody's Baa (no storing); Case-Shiller; NAR; ISM and S&P PMIs; Conference Board leading index and confidence; NFIB; CoStar, MSCI-RCA and Green Street CRE data; Trepp and KBRA CMBS; ICE McDash and Cotality escrow, negative equity and delinquency; MBA delinquency survey; Epiq; Manheim; Challenger; Climate Central disasters (terms unverified); NOAA disaster archive (ends 2024); financial obligations ratio (stopped 2023:Q3); Philadelphia Fed state leading indexes (stopped); OFR vulnerabilities monitor (stopped 2019); Fed business-loan rate survey (stopped 2017); TED spread (stopped 2022); BLS new-tenant rent index (stale); FIO ZIP premiums (one-off); CPI tenants' insurance (wrong measure for homeowners); FEMA declaration counts (administrative) |

### Getting the data: most routes need no key

| Route | Key needed? | Limits and notes |
|---|---|---|
| FRED CSV (`fred.stlouisfed.org/graph/fredgraph.csv?id=…`) | No | Used to verify every FRED id in this report; the FRED API itself needs a free key |
| BLS Public Data API ([FAQ](https://www.bls.gov/developers/api_faq.htm)) | Version 2 needs free registration | Registered: 500 queries a day, 50 series and 20 years per query. Unregistered: 25 series, 10 years |
| BEA API ([guide](https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf)) | Free UserID | 100 requests a minute |
| EIA API ([open data](https://www.eia.gov/opendata/index.php)) | Free key | Subject to EIA's reuse policy |
| OpenFEMA | No | Declarations and NFIP datasets |
| DOL claims downloads ([ETA](https://oui.doleta.gov/unemploy/DataDownloads.asp)) | No | National and state history |
| Fed excess bond premium CSV; FHFA NMDB CSV; CFPB county CSV; NY Fed HHDC and SCE Excel; Atlanta Fed affordability and wage Excel | No | Direct files |
| US Courts bankruptcy tables | No | PDF or XLSX only; no API |
| Fed Data Download Program | — | "Build Your Package" is being removed during the week of November 9 before the program is retired; use FRED ([Fed G.19 page](https://www.federalreserve.gov/releases/g19/current/default.htm)) |

### Hazards that apply across the shortlist

Four hazards apply across the shortlist and belong in the tool's design, not in a footnote.

1. **The October 2025 gap.** It runs through every household-survey (CPS) series and most CPI items. It must be stored as missing, and three-month averages across it computed the way their publishers do, from the two available months.
2. **Revisions.** Annual and monthly revisions reach the payroll benchmark, BEA income, Z.1 CRE prices, the excess bond premium and the Philadelphia Fed indexes. The tool should keep each release it rated against; FRED's companion archive, ALFRED, holds past releases.
3. **Rebuilt series.** The debt service ratio, business applications, the mortgage-rate survey, Realtor.com and University of Michigan sentiment each changed method recently, and each needs a break marker.
4. **Licence tiers on FRED.** "Public Domain: Citation Requested", "Copyrighted: Citation Required" and "Copyrighted: Pre-Approval Required" decide what a shared tool may store and show.

## Conclusion

The research changes the shape of the tool more than its list of series. A single "where does it stand" percentile works for valuations, spreads and stress indexes, the vulnerabilities the Fed tracks. It fails for the series with the best evidence, because unemployment is lowest just as it turns. The tool therefore needs two kinds of rating: how stretched a series is against its history, for valuations, leverage and spreads, and how fast it is deteriorating, for labour, claims and flows into delinquency. Each needs its own published anchor. The 2022–25 false alarms make one more point. A rating that cannot say which inputs drove it, against which window and on which release of the data, will not survive its first wrong call in front of a consumer or commercial team.

Two gaps in the public record cannot be closed by choosing better series. The first is home insurance. The Fed dropped a whole ratio for lack of insurance and property-tax data, and the only causal estimate sits on licensed escrow data. The honest public treatment is the PPI premium index as a cost-pressure signal, with the Dallas Fed's elasticity quoted rather than re-estimated. The second is commercial losses. No published study measures how far the term spread, the excess bond premium, lending standards or CRE prices lead C&I or CRE charge-offs. The literature stops at recessions and output. The Fed's free charge-off series run from 1985 and 1991, so the firm can run that test itself. Until it has, any commercial rating should say that it reads conditions, not losses.
