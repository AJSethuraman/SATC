# Macro risk indicators for lending: frameworks and methods

*Compiled 14 Oct 2026. Every claim links to its source; anything not opened and read directly is marked as such. Working copies of the downloaded sources were kept in the session scratchpad only.*

## 1. Fed supervisory stress test: 2026 domestic scenario variables and the scenario design policy statement

### Takeaway
The 2026 supervisory scenarios use 28 variables, 16 of them domestic (6 activity/prices, 4 asset prices/financial conditions, 6 interest rates), unchanged from 2025. The unemployment guide (peak rise of 3 to 5 points, floor of 10 percent) and the house-price guide (house price to per-capita income ratio falls at least 25 percent, or to its Q1 2012 trough) have been in force since 2019. The Board finalised them on 2 Oct 2026 (effective 2 Nov 2026) and added guides for seven more domestic variables. This is the closest thing US supervisors publish to an official definition of "severe" for each macro series.

### Cited Findings
**The 16 domestic variables (2026 scenarios, released 4 Feb 2026)**
- "Each scenario includes 28 variables; the set of variables for the 2026 supervisory stress test is the same as the set provided in last year's supervisory stress test scenarios." Scenarios run 2026:Q1 to 2029:Q1. — [Fed, 2026 Final Supervisory Stress Test Scenarios (PDF, Feb 2026)](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf)
- Domestic: **six measures of economic activity and prices** (annualised quarterly % change in real GDP, nominal GDP, real disposable personal income, nominal disposable personal income, CPI-U; and the unemployment rate, 16+). **Four asset prices or financial conditions** (house price index, commercial real estate price index, equity prices, stock market volatility). **Six interest rates** (3-month Treasury, 5-year Treasury, 10-year Treasury, 10-year BBB corporate yield, 30-year conforming fixed mortgage rate, prime rate). International: real GDP growth, CPI inflation and the USD exchange rate for the euro area, UK, developing Asia and Japan (12 variables). — [same PDF](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf)
- Published data source for each domestic variable ("Notes Regarding Scenario Variables"). The table is useful because it ties each stress variable to a free public series. — [same PDF](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf)
  - Real GDP: BEA NIPA 1.1.6 line 1. Nominal GDP: NIPA 1.1.5 line 1.
  - Real disposable income: NIPA 2.1 line 27 deflated by the PCE price index (NIPA 1.1.4 line 2). Nominal disposable income: NIPA 2.1 line 27.
  - Unemployment: quarterly average of BLS LNS14000000.
  - CPI: annualised % change in the quarterly average of BLS CUSR0000SA0.
  - 3-month Treasury: H.15 series RIFSGFSM03_N.B.
  - 5-year and 10-year Treasury: Fed staff Svensson smoothed yields constructed for FRB/US.
  - BBB yield: ICE BofAML US Corporate 7-10yr, C4A4 (licensed, "used with permission").
  - Mortgage rate: Freddie Mac Primary Mortgage Market Survey (PMMS), 30-year.
  - Prime rate: H.15 series RIFSPBLP_N.M.
  - Equities: Dow Jones Total Stock Market (Float Cap) Index, end of quarter, via Bloomberg (licensed).
  - House prices: Z.1 Price Index for Owner-Occupied Real Estate, FL075035243.Q.
  - CRE prices: Z.1 Commercial Real Estate Price Index, FL075035503.Q.
  - VIX: the **maximum** daily close in the quarter, CBOE via Bloomberg.
- The Z.1 CRE price index used by the stress test "is based on quarterly change of the Value Weighted Costar U.S. Composite Index Excluding Multifamily". — [Fed final rule, FR Doc. 2026-20247 (2 Oct 2026), fn. 118](https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20247.htm)
- 2026 severely adverse paths:
  - Unemployment rises 5.5 points from a 4.5% jump-off to a 10% peak in 2027:Q3, the seventh quarter, the midpoint of the 6-to-8-quarter guide.
  - Nominal house prices fall 30% and CRE prices 39%, both troughing in 2027:Q4.
  - Equities fall about 58%. The VIX peaks at 72. The BBB spread peaks at 5.7 points (up 4.7). The mortgage spread peaks at 3.4 points (up 1.3).
  - Real GDP falls 4.6%. The GDP, income, inflation and 3-month rate paths come from the Board's small "macro model for Stress Testing" (Okun's law plus a Phillips curve) given the unemployment path.
  - Most discretionary settings were placed "near or in the upper one-third of their ranges of severity."

  — [2026 scenarios PDF](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf)
- The Fed sizes scenario severity against **current** conditions. For 2026 it cited:
  - unemployment near the Blue Chip consensus long-run natural rate;
  - equities up about 16% over one year and about 41% over two;
  - house prices flat for two years but about 37% above five years earlier;
  - CRE prices stable since early 2024;
  - a BBB spread "low relative to its historical series".

  This follows its expectation that "scenario severity generally will be higher during economic expansions or periods when asset values have increased". — [2026 scenarios PDF](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf)

**The unemployment and house-price guides (2019 Policy Statement)**
- The 2019 amendments did two things. They clarified that the Board may adopt an unemployment rise of less than 4 points under certain conditions. They also introduced "a guide that limits procyclicality in the stress test for the change in the house price index". Effective 1 Apr 2019. — [Federal Register, 84 FR 6651 (28 Feb 2019), Doc. 2019-03504](https://www.federalregister.gov/d/2019-03504)
- **Unemployment guide (2019 text, section 4.2.2).** The severely adverse scenario will feature an unemployment rate that rises 3 to 5 points over 6 to 8 quarters. If that does not lift it to at least 10% ("the average level to which it has increased in the most recent three severe recessions"), the path will in most cases be set to reach at least 10%.
  - "Historically, a 3 to 5 percentage point increase in unemployment rate is reflective of stressful conditions." In all four severe post-war recessions of the last half-century unemployment rose 3 to 5 points. In the three most recent it reached 9 to 11%.
  - The typical rise is about 4 points. It is smaller when unemployment starts elevated, the labour market is strengthening and losses are already being realised. The evidence named for that is "elevated charge-offs on loans and leases, loan-loss provisions in excess of gross charge-offs".
  - The 10% floor exists because "cyclical systemic risks build up at financial intermediaries during robust expansions" and "are also easily obscured by the buoyant environment".

  — [govinfo text of 84 FR 6651](https://www.govinfo.gov/content/pkg/FR-2019-02-28/html/2019-03504.htm)
- **House-price guide (2019).** The Board considers the ratio of the nominal house price index to nominal per-capita disposable income (HPI-DPI). The typical decline in that ratio "will be at a minimum 25 percent from its starting value, or enough to bring the ratio down to its Great Recession trough". Housing recessions (1980-85, 1989-96, 2006-11) "on average featured HPI-DPI ratio declines of about 25 percent". — [govinfo text of 84 FR 6651](https://www.govinfo.gov/content/pkg/FR-2019-02-28/html/2019-03504.htm)

**Status as of October 2026: guides finalised and extended**
- On 2 Oct 2026 the Board published a final rule, "Enhanced Transparency and Public Accountability of the Supervisory Stress Test Models and Scenarios" (effective 2 Nov 2026). It finalises amendments to the Scenario Design Policy Statement and announces final models for the 2027 test. — [Federal Register, Doc. 2026-20247](https://www.federalregister.gov/documents/2026/10/02/2026-20247/enhanced-transparency-and-public-accountability-of-the-supervisory-stress-test-models-and-scenarios) (abstract via the FR API; full text at [govinfo](https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20247.htm))
- The proposal behind it was 90 FR 51856 (18 Nov 2025), the "Proposed 2025 Scenario Design Policy Statement". The 2026 scenarios were already built to its guides. — [2026 scenarios PDF](https://www.federalreserve.gov/publications/files/2026-final-supervisory-stress-test-scenarios-20260204.pdf); [FR proposed rule 2025-20211](https://www.federalregister.gov/documents/2025/11/18/2025-20211/enhanced-transparency-and-public-accountability-of-the-supervisory-stress-test-models-and-scenarios)
- Final 2026 text of the two existing guides:
  - **Unemployment (4.2.2.1):** "peak value that increases between 3 to 5 percentage points from its jump-off value", with the 10% floor in most cases. The peak falls "between quarters 6 and 8"; the trajectory has "high initial changes with smaller subsequent changes".
  - **House prices (4.2.2.2):** HPI-DPI falls "(1) by at least 25 percent, or (2) by enough to bring the ratio down to the trough reached in the first quarter of 2012". The trough falls between quarters 8 and 10, with 20% of the decline in quarter 1 and 20% in quarter 2.
  - The Board "did not receive comment on this aspect of the proposal and has determined to finalize, as proposed, the guide for house prices".

  — [govinfo, 2026-20247](https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20247.htm)
- **New guides finalised in the same text.** These are useful as published "severe" magnitudes. — [govinfo, 2026-20247](https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20247.htm)

  | Variable | Severe peak or trough | Timing |
  |---|---|---|
  | BBB spread over 10-year Treasury | Higher of 500-600 bp, or +~100 bp from jump-off | Peak in quarter 3-4; 60-80% of the rise in quarter 1 |
  | Mortgage spread over 10-year Treasury | Higher of +70 to 160 bp, or a level of at least 300 bp | Peak in quarter 3-4 |
  | VIX | Higher of 65-75, or +10 points | Peak in quarter 2 |
  | Equities | Fall of 50% ± up to 10%, scaled to the prior 12-month change (trough 40-60% below jump-off) | Trough in quarter 3 or 4 |
  | CRE prices | Fall of 30-45% | Trough in quarters 8-10 |
  | 5-year Treasury | Falls 1.5-3.5 points, with a floor of 0.3% | Trough in quarters 1-4 |
  | 10-year Treasury | Falls 1-3 points, with a floor of 0.5% | Trough in quarters 1-4 |

  International: GDP down 7.5% (range 5-10%) for the euro area, UK and Japan, plus inflation and FX guides.
- The proposed move of the jump-off date from 31 Dec to 30 Sep was **not adopted**: "The Board will not adopt the proposed jump-off date of September 30, and will retain the December 31 date in the final rule." — [govinfo, 2026-20247](https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20247.htm)

### Inferences
- For a "1 Low to 5 High" macro rating, the Fed guides give regulator-published anchors for what "severe" looks like on several series. These are not thresholds for "abnormal today"; they are sizes of a hypothetical severe move.
  - Unemployment: +3 to 5 points, or 10%.
  - House price to income: -25%.
  - BBB spread: 500-600 bp.
  - Mortgage spread: 300 bp or more.
  - VIX: 65-75.
  - CRE prices: -30 to -45%.
- The Fed's choice of HPI-to-income (not HPI alone) and of "severity higher when asset values have risen" is a published endorsement of valuation-gap measures (a level relative to fundamentals or trend) as the right way to judge house prices, not raw growth.
- The variable notes give free public series for 13 of 16 domestic variables. BBB yield (ICE), equities (Dow Jones via Bloomberg) and VIX (CBOE via Bloomberg) are licensed in the Fed's own build.
  - The 5- and 10-year yields are Fed-staff Svensson constructions; the H.15 constant-maturity yields are the obvious public stand-ins, though the Fed does not say so.
  - The CRE index is a Z.1 series built on CoStar data. Whether free FRED equivalents (e.g. ICE BofA BBB OAS, VIXCLS) are acceptable substitutes is a design choice for the tool, not something the Fed states.

### Gaps
- The 2027 proposed scenarios: the final rule says the Board finalised models for 2027, but I did not confirm whether the 2027 scenarios themselves have been proposed or published as of 14 Oct 2026.
- I did not read the separate "Review of Comments" document or the macro-model guide in full.

## 2. Bank CECL disclosures: macroeconomic variables named in 10-K allowance discussions

### Takeaway
All nine banks' FY2025 10-Ks (filed Feb 2026) name the **unemployment rate and real GDP**, and most call them the two most significant drivers.
- **Real-estate prices** are next: house prices for consumer books, CRE or commercial property prices for commercial books, named explicitly or as "real estate values" or "collateral values" by six of nine.
- **Interest rates** and **inflation** come after that.
- **Corporate credit spreads** appear in three, all on the commercial side.
- **Used-car prices, equity prices, real disposable income and household debt** each appear once.

Every bank uses a vendor or consensus forecast with a 2-year (PNC: 3-year) reasonable and supportable period, then reverts to long-run history.

### Cited Findings
All quotations are from each bank's 10-K for the fiscal year ended 31 Dec 2025, on SEC EDGAR.

- **KeyCorp** — [10-K filed 23 Feb 2026](https://www.sec.gov/Archives/edgar/data/91576/000162828026010546/key-20251231.htm)
  - Risk factor: "the softening of certain macroeconomic variables that we are more susceptible to, such as GDP, unemployment, SOFR and other interest rates, the producer price index, and real estate values ... may require an increase in the ALLL."
  - "The ALLL is sensitive to various macroeconomic drivers such as GDP and unemployment as well as portfolio attributes such as ... FICO, LTV, and delinquency status."
  - "Moody's Consensus forecast is our source of macroeconomic projections" (licensed).
  - A two-year reasonable and supportable period, then "a four quarter reversion period ... the macroeconomic variables linearly revert to their long run average", using "a 20 year lookback period".
  - Downside comparison: about 6 points lower GDP growth and about 4 points higher unemployment would drive about **1.7x commercial and 1.6x consumer** modelled allowance.
- **PNC** — [10-K filed 20 Feb 2026](https://www.sec.gov/Archives/edgar/data/713676/000071367626000020/pnc-20251231.htm)
  - "We used a number of economic variables in our scenarios, with two of the most significant drivers being real GDP and the U.S. unemployment rate."
  - Four probability-weighted scenarios over a **three-year** forecast period. Weighted-average unemployment is 5.1% at end-2026.
  - Severe downside: unemployment peaks at 7.3% in 2027, adding about $2.0bn to modelled losses.
  - Qualitative framework cites "the fundamental change in office demand, tariff and trade driven pressures, interest rate movements and housing affordability".
  - The auditor's critical audit matter centres on the "economic forecast scenarios of Real GDP and the U.S. unemployment rate".
- **Truist** — [10-K filed 24 Feb 2026](https://www.sec.gov/Archives/edgar/data/92230/000009223026000030/tfc-20251231.htm)
  - "Common macroeconomic drivers for the commercial portfolios include unemployment trends, U.S. real GDP, corporate credit spreads, and property values."
  - "Common macroeconomic drivers for the consumer portfolios include unemployment trends, home price indices, and used car prices."
  - Third-party forecasts with a two-year reasonable and supportable period, reverting over one year. The data "include employment factors, estimated collateral values, and market indicators".
- **Fifth Third** — [10-K filed 24 Feb 2026](https://www.sec.gov/Archives/edgar/data/35527/000003552726000124/fitb-20251231.htm)
  - Table 51, "Key Macroeconomic Factors", lists:
    - inflation rate
    - real GDP growth
    - average unemployment rate
    - average federal funds rate
    - 10-year Treasury yield
    - credit spread ("Moody's Baa-rated corporate bond yields" minus Treasuries)
    - annualised change in the S&P 500
  - Three third-party scenarios at the 10th, 50th and 90th percentiles, weighted 80/10/10. Downside unemployment averages 7.4% (2026) and 8.1% (2027).
  - A 100% downside weight would add about $1.2bn to the quantitative ACL.
- **Huntington** — [10-K filed 13 Feb 2026](https://www.sec.gov/Archives/edgar/data/49196/000004919626000015/hban-20251231.htm)
  - Scenarios come from "an independent third party"; "the most significant being unemployment rates and GDP".
  - Baseline, adverse and favourable scenarios, probability-weighted. The adverse unemployment rate peaks "at 8.4% in the first quarter of 2027, approximately 360 basis points higher than the baseline scenario projection of 4.8%".
- **Regions** — [10-K filed 24 Feb 2026](https://www.sec.gov/Archives/edgar/data/1281761/000128176126000019/rf-20251231.htm)
  - Table 16, "Macroeconomic Factors in the Forecast": unemployment rate, real GDP annualised % change, HPI year-over-year % change, CPI year-over-year % change.
  - "The unemployment rate is the most significant macroeconomic factor among the allowance models."
- **M&T** — [10-K filed 18 Feb 2026](https://www.sec.gov/Archives/edgar/data/36270/000003627026000010/mtb-20251231.htm)
  - Models "consider historical correlations of credit losses with various macroeconomic assumptions including unemployment, GDP and real estate prices."
  - Table 26 sensitivity, downside scenario: national unemployment 7.1% (year 1) and 8.1% (year 2); real GDP -2.4%; CRE price index -20.2% cumulative; home price index -6.7% cumulative.
  - A two-year reasonable and supportable period, reverting "ratably over a one-year period".
- **Citizens** — [10-K filed 12 Feb 2026](https://www.sec.gov/Archives/edgar/data/759944/000075994426000028/cfg-20251231.htm)
  - "Forward-looking economic assumptions include real GDP, unemployment rate, interest rate curve, and changes in collateral values."
  - Base forecast peak unemployment about 5.3%. **A more severe scenario is applied to CRE (general office)**, with peak unemployment about 9.4%.
  - A pessimistic scenario (peak 6.7%) gives about 1.4x modelled ACL, about +$700m.
- **U.S. Bancorp** — [10-K Exhibit 13, filed 23 Feb 2026](https://www.sec.gov/Archives/edgar/data/36104/000003610426000011/usb-20251231_d2.htm)
  - Commercial segment: "macroeconomic factors such as unemployment rates, corporate bond spreads, commercial property prices and long-term interest rates".
  - Consumer segment: "unemployment rates, asset and property prices, household debt levels, real disposable income, the effect of higher interest rates on variable rate or adjustable rate loans".
  - Also lists "unemployment rates, real estate prices, gross domestic product levels, inflation, interest rates and corporate bonds spreads".
  - Projected unemployment ranged from 3.7% to 9.4% across scenarios, with a peak weighted average of 5.9%.

**Recurrence across the nine FY2025 10-Ks (as named in allowance discussions):**

| Variable | Banks naming it | Count |
|---|---|---|
| Unemployment rate | KEY, PNC, TFC, FITB, HBAN, RF, MTB, CFG, USB | 9/9 |
| Real GDP | KEY, PNC, TFC (commercial), FITB, HBAN, RF, MTB, CFG, USB | 9/9 |
| House or home prices (HPI) | TFC (consumer), RF, MTB explicitly; KEY "real estate values", USB "real estate / property prices", CFG "collateral values" | 3 explicit, 6 including generic |
| CRE or commercial property prices | MTB (CRE price index), USB (commercial property prices), TFC (property values, commercial); KEY, CFG generic | 3 explicit, 5 including generic |
| Interest rates (fed funds, 10-year, SOFR, curve) | KEY, FITB, CFG, USB; HBAN in scenario narrative | 4-5 |
| Inflation (CPI, PPI) | RF (CPI), FITB, USB, KEY (PPI); HBAN narrative | 4-5 |
| Corporate credit spread (BBB/Baa) | TFC, FITB, USB — all commercial | 3 |
| Equity prices (S&P 500) | FITB | 1 |
| Used-car prices | TFC (consumer) | 1 |
| Real disposable income; household debt | USB (consumer) | 1 |

Counts are from the passages quoted above (see the Gaps below).

**Common design facts:**
- Reasonable and supportable period: two years at KEY, TFC, RF, MTB and CFG; three years at PNC.
- Reversion: to long-run history over one year at TFC and MTB, or four quarters to a 20-year average at KEY.
- Scenarios: three or four, probability-weighted, from a third party, at FITB, HBAN, PNC and KEY.
- Sources: the KEY, PNC, TFC, FITB, HBAN, RF, MTB and CFG 10-Ks above.

### Inferences
- Measured by what large regional banks tell investors drives reserves, a consumer and commercial macro tool should centre on the following. All have free public series.
  - Unemployment rate.
  - Real GDP.
  - A house price index (consumer, mortgage, home equity).
  - A CRE price index (commercial real estate).
  - Corporate credit spreads (C&I).
  - Used-vehicle prices (auto, per Truist).
  - Interest rates and inflation, in a supporting role.
- Seven of the nine banks quantify a downside or sensitivity scenario (KEY, PNC, FITB, HBAN, MTB, CFG, USB).
  - Downside unemployment peaks run from 6.7% (CFG's pessimistic case) to 9.4% (CFG's CRE-office scenario; the top of USB's range).
  - Downside-over-base gaps are about +3.6 points (HBAN) to about +4 points (KEY).
  - This is a market-practice benchmark for "adverse" that mostly sits below the Fed's 10% severely adverse floor.
- CECL scenarios are forecasts with weights, not rules for whether today's reading is abnormal. The 10-Ks tell you **which** series matter, not **when** they are stressed. Thresholds have to come from the methods in section 4.

### Gaps
- I did not read each 10-K end to end. The variable lists come from targeted searches of the ACL sections (MD&A critical estimates, Note 1, the ACL note). A bank may name additional variables elsewhere, for example in its 10-Q tables.
- Fifth Third's and Huntington's third-party providers are not named in the passages found. Only KeyCorp names Moody's (Consensus). I did not verify Truist's vendor.
- Counts mix explicit names with generic phrases ("real estate values", "collateral values"), so the house-price and CRE counts are a judgment call.

## 3. Regulator publications that build a macro narrative (Fed FSR, OCC SARP, FDIC Risk Review, FDIC QBP)

### Takeaway
Each of the three main narrative publications has its own frame, and all three share one presentation device.
- The **Fed FSR** is organised around four vulnerability categories and judges nearly every chart against its own **historical distribution** (median, quartile, "upper range").
- The **OCC SARP** opens with an "Economic Environment" section built on real GDP, unemployment, payrolls, wages, inflation, house prices and CRE vacancy. It uses the Blue Chip consensus for the outlook.
- The **FDIC Risk Review** judges macro and credit series against a fixed **"pre-pandemic average" (2015:Q1 to 2019:Q4)**.

The shared device: each series is stated as a level relative to a defined historical benchmark, in a one-line chart title that is itself the verdict.

### Cited Findings
**Federal Reserve Financial Stability Report (latest: May 2026, released 8 May 2026; semiannual)**
- The framework "distinguishes between shocks to, and vulnerabilities of, the financial system. Shocks are inherently difficult to predict, while vulnerabilities ... can be monitored as they build up or recede over time". It focuses on four categories:
  1. **valuation pressures** ("when asset prices are high relative to economic fundamentals or historical norms");
  2. **excessive borrowing by businesses and households**;
  3. **excessive leverage within the financial sector**;
  4. **funding risks**.

  It also tracks "near-term risks", including a "Survey of Salient Risks to Financial Stability" of market contacts.

  — [Fed FSR May 2026, Purpose and Framework](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-purpose-and-framework.htm); [Near-Term Risks](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-near-term-risks.htm)
- Charts in **Section 1, Asset Valuations**:
  - Treasury yields; term premium ("just above its historical median"); interest-rate volatility ("near its median since 2005").
  - S&P 500 P/E ("close to the upper end of its historical range"); equity premium ("near a 20-year low"); equity volatility.
  - Corporate bond yields and spreads; the **excess bond premium**; leveraged-loan spreads ("low relative to their historical distribution").
  - Treasury and equity market depth and liquidity.
  - Inflation-adjusted CRE prices; CRE income-to-price (cap rate); SLOOS CRE lending standards.
  - House prices; **model-based house price valuation** ("near historically high levels"); **house price-to-rent** by region.
  - Farmland prices and price-to-rent.

  — [FSR May 2026, Asset Valuations](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-asset-valuations.htm)
- Charts in **Section 2, Borrowing by Businesses and Households**:
  - Total business and household debt relative to GDP; real business debt; net issuance of risky debt.
  - Gross leverage of public firms; interest coverage ratios; leverage of firms with C&I bank loans.
  - Leveraged loans with debt/EBITDA of 4 or more; leveraged-loan default rate.
  - Household debt; housing leverage (LTV); mortgage originations by credit score; mortgage delinquency ("close to the low end of their historical distribution"); negative equity.
  - Consumer debt by type; used-car loan maturity; auto delinquency ("well above the historical median"); credit card balances; credit card delinquency ("leveled off at their long-term median").

  — [FSR May 2026, Borrowing](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-borrowing.htm)
- **Section 3 (Leverage)** charts bank capital ratios, ROE, securities fair-value losses, TCE/TA, the SLOOS share of banks easing, bank loan delinquency, broker-dealer, insurer and hedge-fund leverage, and bank credit to NBFIs. **Section 4 (Funding)** charts runnable liabilities, HQLA to short-term debt, bank funding structure, MMF and stablecoin assets, and fund flows. — [FSR Leverage](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-leverage.htm); [FSR Funding Risks](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-funding-risks.htm)
- Overview wording shows the method. The P/E ratio "stayed in the upper range of its historical distribution". "The ratio of house prices to rents remained in the upper ranges of its historical distribution". Life-insurer leverage "stayed well into the upper quartile of its historical distribution". — [FSR May 2026, Overview](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-overview.htm)

**OCC Semiannual Risk Perspective (latest: Spring 2026; data as of 31 Dec 2025)**
- The SARP "identifies key issues facing banks" as assessed by the OCC's National Risk Committee, which "monitors the condition of the federal banking system and identifies key risks" and "emerging threats". — [OCC SARP Spring 2026 (PDF)](https://www.occ.gov/publications-and-resources/publications/semiannual-risk-perspective/files/pub-semiannual-risk-perspective-spring-2026.pdf); [OCC news release NR 2026-35](https://www.occ.gov/news-issuances/news-releases/2026/nr-occ-2026-35.html)
- Part II, "Economic Environment and Bank Performance", narrates:
  - real GDP (2.1% in 2025) and net payrolls;
  - the unemployment rate (4.3% in March 2026) and wage growth (3.4%);
  - core inflation (3.1%) and Fed rate cuts;
  - single-family house prices, with regional divergence (Northeast and Midwest against the Sun Belt);
  - multifamily rents;
  - CRE vacancy by property type (office highest, industrial normalising, retail low);
  - the Blue Chip consensus outlook.

  Figure 1 is "Real GDP, annual percent change" with recession shading and the Blue Chip forecast. Bank-performance figures are ROE, loan growth and net charge-off rates by loan type. The January 2026 SLOOS is cited for expected credit performance. — [OCC SARP Spring 2026 (PDF)](https://www.occ.gov/publications-and-resources/publications/semiannual-risk-perspective/files/pub-semiannual-risk-perspective-spring-2026.pdf)

**FDIC Risk Review (latest: 2026 Risk Review, released 22 Apr 2026; annual)**
- Covers "funding, interest rate, and credit risks". Macro and market charts include:
  - real GDP growth (Chart 2.1.1) and labour-market tightness, the ratio of unemployed to job openings (2.1.2);
  - the yield curve (3.1);
  - CRE vacancy rates by property type, "below the recent historical average" (4.1.1), and CRE values by sector (4.1.2);
  - the SLOOS (4.3.1); corporate bond and leveraged-loan default rates (4.3.3);
  - real income and spending growth (4.4.1); the household debt-service ratio and household debt to GDP (4.4.2);
  - new and existing home sales (4.5.1);
  - farm production costs (4.6.1).

  Credit charts compare past-due-and-nonaccrual (PDNA) rates by loan type with their pre-pandemic averages (2.2.3, 4.1.3, 4.4.3).

  — [FDIC 2026 Risk Review](https://www.fdic.gov/analysis/2026-risk-review)
- The FDIC's benchmark is explicit: "Pre-pandemic average is the average from first quarter 2015 through fourth quarter 2019", and "The pre-pandemic period is the period starting first quarter 2015 through fourth quarter 2019, unless otherwise noted." — [FDIC 2026 Risk Review (PDF via the page above)](https://www.fdic.gov/analysis/2026-risk-review)

**FDIC Quarterly Banking Profile (latest: Q2 2026, released 25 Aug 2026)**
- The QBP remarks are bank-performance commentary, not macro narrative. Charts 1-11 are:
  - net income and its quarterly drivers; NIM; yield on earning assets against cost of funds;
  - provisions; long-dated loans and securities as a share of assets; unrealised securities losses;
  - loan growth; PDNA rate and net charge-off rate; non-owner-occupied CRE PDNA by asset size;
  - reserve coverage.
- The macro benchmark device is the same as the Risk Review's. The non-owner-occupied CRE PDNA rate for banks over $250bn is 3.08%, "below the recent peak of 4.99 percent in third quarter 2024 but well above the pre-pandemic average rate of 0.59 percent". "The period used to calculate pre-pandemic averages is first quarter 2015 through fourth quarter 2019."
- A text search of the Q2 2026 remarks and QBP landing page for "economic", "uncertain", "inflation" and "unemployment" found no macro-risk statement.

— [FDIC QBP Q2 2026 remarks](https://www.fdic.gov/news/speeches/2026/fdic-quarterly-banking-profile-second-quarter-2026); [QBP Q2 2026](https://www.fdic.gov/quarterly-banking-profile/quarterly-banking-profile-2q-2026)

### Inferences
- **Presentation conventions worth copying.** Each regulator writes chart titles as verdicts against a stated benchmark:
  - Fed: "near its median since 2005", "upper quartile of its historical distribution", "well above the historical median".
  - FDIC: "above pre-pandemic average".
  - OCC: "historically low".

  A 1-to-5 tool that reports a **percentile against a stated history window** plus a one-line verdict would read like regulator output.
- **Benchmark choice differs and matters.** The Fed uses the full available history or a stated start ("since 2005", "20-year low"). The FDIC uses a fixed calm window (2015-2019), which makes almost any post-2020 reading look "elevated". A tool should state its window, as both regulators do.
- **Indicators common to two or more regulator narratives:**
  - real GDP, unemployment and labour tightness;
  - house prices and valuation (price-to-rent, model-based);
  - CRE prices and vacancy by property type;
  - corporate bond spreads and the excess bond premium; leveraged-loan default rates;
  - household debt to GDP and the debt-service ratio;
  - consumer delinquency by product;
  - SLOOS lending standards;
  - the yield curve and rates.
- The FSR's split of **shocks (unpredictable) versus vulnerabilities (monitorable)** is the cleanest published justification for a tool that rates slow-moving conditions rather than predicting events.

### Gaps
- I read the FSR section pages (figure titles and text), not each figure's underlying data source. The excess bond premium and the model-based house-price valuation measure are Fed staff constructs. I did not check which are downloadable.
- FDIC Risk Review chart titles are embedded as images in the PDF. The chart contents above are inferred from the sentences that cite each chart.
- I did not review the OCC Fall 2025 SARP or check whether an OCC Fall 2026 SARP has been released (it normally appears around December).
- I did not review the FDIC Quarterly journal or FDIC regional economic publications.

## 4. Published methods for flagging unusual macro readings

### Takeaway
Published "is this reading unusual?" methods fall into four families:
1. **Change-from-recent-low triggers** on one series: the Sahm rule, +0.50 point on the 3-month average unemployment rate.
2. **Composite indexes with fixed cut-offs**: CFNAI-MA3 at −0.70; LEI 3Ds at a diffusion of 50 or less and six-month growth below about −4.3%; the probit on the 10-year minus 3-month spread, with 30% used as a reading convention.
3. **Standardised "zero-line" indexes** (mean 0, SD 1): OFR FSI, STLFSI4, NFCI. Zero means average, not stressed.
4. **Distribution-position heat maps**: z-scores or percentiles against a stated history. These are the OFR FSVM (discontinued after Q4 2019), the Fed staff heat map (65th/85th/80th percentile thresholds) and the Fed FSR's "historical distribution" language. The BIS credit-to-GDP gap (2 and 10 points) is a trend-deviation variant.

Every single-series trigger with a long clean record broke in 2022-2025: the Sahm rule fired in 2024; the yield curve put recession probability above 30% from November 2023 to November 2025; the LEI 3Ds signalled through 2022-23. None was followed by a recession by the publishers' own data.

### Cited Findings
**Sahm rule (Claudia Sahm, 2019; Hamilton Project/Brookings "Recession Ready"; data series published by FRED)**
- **Rule:** a trigger "when the three-month average national unemployment rate rises by at least 0.50 percentage points relative to its low in the previous 12 months".
  - "The three-month average smooths out some of the monthly random variation in the rate and avoids false positives."
  - Calculated "using real-time estimates of the unemployment rate".
- **Original track record:** "Early in each recession since 1970, the unemployment rate rose at least a 0.50 percentage points ... On average, payments would have been triggered within three months of the start of the past six recessions." Footnote: "Earlier in the postwar period ... the only false positive by this rule was in 1959, and it was followed six months later by a recession."

  — [Sahm, "Direct Stimulus Payments to Individuals", Hamilton Project (May 2019), PDF](https://www.hamiltonproject.org/assets/files/Sahm_web_20190506.pdf)
- **Live series and 2024 episode.** FRED's real-time Sahm Rule Recession Indicator (SAHMREALTIME) crossed 0.50 in July 2024 (0.53), peaked at 0.57 in August 2024, was 0.50 in September 2024, then fell back. It read 0.43 in Nov 2025 and 0.00 in Sep 2026; the Oct 2025 value is blank. — [FRED, SAHMREALTIME (CSV pulled 14 Oct 2026)](https://fred.stlouisfed.org/series/SAHMREALTIME)
- **How the 2024 crossing is read.** These are secondary sources; I found no Fed publication on it.
  - Press reports quote Sahm saying the rule cannot separate a rise in labour supply from a fall in labour demand, and that pandemic and immigration-driven labour-force growth was likely overstating the weakening. — [Fortune, 2 Aug 2024](https://fortune.com/2024/08/02/recession-indicator-claudia-sahm-rule-trigger-unemployment-rate-jobs-report); [ClearBridge, 2024](https://www.clearbridge.com/perspectives/institutional/2024/rising-unemployment-closer-look-different-conclusion)
  - Fed Chair Powell called the rule a "statistical regularity" at his late-July 2024 press conference. — [Wikipedia, Sahm rule (API extract, 14 Oct 2026)](https://en.wikipedia.org/wiki/Sahm_rule)
  - Wikipedia counts two pre-1970 early alerts, in 1959 and 1969, each followed by recession.
  - The FRED series shows the signal reversed without the unemployment rate continuing up (0.13 by April 2026).

**Conference Board LEI "3Ds" rule (licensed index; free headline release)**
- **Rule:** "The 3Ds rule signals an impending recession when: 1) the six-month diffusion index lies at or below 50 ... and 2) the LEI's six-month growth rate (annualized) falls below the threshold of −4.3%." The 3Ds are "duration, depth, and diffusion"; duration and depth are measured by the six-month annualised change.
- **Latest:** the August 2026 LEI fell 0.1% to 99.5 (2016=100); six-month growth was –0.1%; "the diffusion index remained above 50 and no recession signal was triggered" (page updated 18 Sep 2026).
- **Ten components:**
  1. Average weekly manufacturing hours.
  2. Initial unemployment-insurance claims.
  3. Manufacturers' new orders for consumer goods and materials.
  4. ISM new orders.
  5. Nondefense capital goods orders excluding aircraft.
  6. Building permits.
  7. S&P 500.
  8. Leading Credit Index.
  9. 10-year Treasury minus fed funds spread.
  10. Average consumer expectations for business conditions.

  — [Conference Board, US Leading Indicators](https://www.conference-board.org/topics/us-leading-indicators)
- **Track record and calibration.**
  - The threshold is an empirical median that the Conference Board re-estimates. In 2024 the rule used "the threshold of -4.4 percent" ("measured by the median"); the September 2026 page uses −4.3%. — [Conference Board LEI release, Feb 2024](https://www.conference-board.org/topics/us-leading-indicators/press/us-lei-feb-2024); [current page](https://www.conference-board.org/topics/us-leading-indicators)
  - In February 2024 it stood down its 2022-23 recession call: "for the first time in the past two years, six out of its ten components were positive contributors ... As a result, the leading index currently does not signal recession ahead. While no longer forecasting a recession in 2024...". — [Conference Board, Feb 2024](https://www.conference-board.org/topics/us-leading-indicators/press/us-lei-feb-2024)
  - By May 2024: "the LEI's six-month and annual growth rates no longer signal a forthcoming recession". — [Conference Board, May 2024](https://www.conference-board.org/topics/us-leading-indicators/press/us-lei-may-2024)
  - Together with the NY Fed data file (no NBER recession after 2020), this makes 2022-23 a recession signal with no recession behind it.
- Licensing: the LEI is a registered trademark (LEI®), and two components (ISM®, S&P 500®) are licensed data. Historical data require membership (see section 5).

**Chicago Fed National Activity Index (CFNAI; free)**
- "A weighted average of 85 existing monthly indicators of growth in national economic activity" in four groups: production and income; employment, unemployment and hours; personal consumption and housing; sales, orders and inventories.
- "A zero value for the monthly index has been associated with the national economy expanding at its historical trend (average) rate of growth; negative values with below-average growth (in standard deviation units)".
- **Thresholds:** "Following a period of economic expansion, an increasing likelihood of a recession has historically been associated with a CFNAI-MA3 value below –0.70." Expansions are associated with CFNAI-MA3 above –0.70 and the CFNAI Diffusion Index above –0.35; contractions with values below both. A CFNAI-MA3 above +0.70 "more than two years into an economic expansion" has been associated with "an increasing likelihood of a period of sustained increasing inflation".

— [Chicago Fed, CFNAI About](https://www.chicagofed.org/research/data/cfnai/about); [CFNAI Current Data](https://www.chicagofed.org/research/data/cfnai/current-data)

**OFR Financial Stress Index (free, daily) and the discontinued OFR Financial System Vulnerabilities Monitor**
- **OFR FSI:**
  - "a daily market-based snapshot of stress in global financial markets ... constructed from 33 financial market variables".
  - Five categories: credit, equity valuation, funding, safe assets and volatility. Regional contributions are shown for the US, other advanced economies and emerging markets.
  - "The value of the OFR FSI on a given day is the weighted average level of each variable observed in the market on that day, relative to its history. The index is zero when this average is zero, suggesting that stress is at normal levels." Positive means above-average stress.

  — [OFR Financial Stress Index](https://www.financialresearch.gov/financial-stress-index/)
- **OFR FSVM: discontinued.**
  - "The Financial System Vulnerabilities Monitor was discontinued after Q4 2019."
  - It was "a heat map of 58 indicators of potential vulnerabilities ... organized in six categories: macroeconomic, market, credit, solvency and leverage, funding and liquidity, and contagion".
  - It "color-codes key indicators of vulnerability, based on their positions within a long-term range. Scores closer to red signal higher potential vulnerability", and was updated quarterly.
  - It was "designed to provide early warning signals ... that merit investigation. It does not provide conclusions about financial stability."

  — [OFR Financial System Vulnerabilities Monitor (archived page)](https://www.financialresearch.gov/financial-vulnerabilities/)

**Fed staff heat map: z-scores and percentile thresholds (Aikman, Kiley, Lee, Palumbo and Warusawitharana, FEDS 2015-059)**
- Builds 44 indicators into the categories later used by the FSR (valuation pressures, nonfinancial borrowing, financial-sector health). It uses "an algorithmic approach to monitoring vulnerabilities that can complement the more judgmental approach of most official-sector organizations."
- **Standardisation:** "For each indicator, we subtract the mean and divide by the standard deviation, where the latter statistics are computed using data from 1990Q1 to 2014Q4, or the full sample for indicators with shorter histories."
- The paper compares four ways to map readings to a 0-1 scale:
  - a kernel-density CDF;
  - a Normal CDF of z-scores;
  - min-max rescaling;
  - ordinal ranks.
- **Percentile thresholds used in its illustrative policy rules:**
  - a lower threshold "at the 65th percentile of the historical distribution and the upper threshold at the 85th percentile";
  - a rule that "switches on at 50 basis points when three of these vulnerability components cross their 80th percentile — this threshold corresponds to the 'red zone'".
- **Track record:** "Our approach picks up rising imbalances in the U.S. financial system through the mid-2000s." The summary measures "lead the credit-to-GDP gap ... by a year or more". **But** "taking a real-time perspective ... while our approach would have signaled heightened vulnerabilities in the mid-2000s, it would have also signaled elevated risks during the late 1990s."

— [FEDS 2015-059, "Mapping Heat in the U.S. Financial System" (DOI)](https://www.federalreserve.gov/econresdata/feds/2015/files/2015059pap.pdf)

**Financial stress and conditions indexes: the "zero line" convention (free)**
- **St. Louis Fed (STLFSI4):** weekly, built from "18 weekly data series: seven interest rate series, six yield spreads and five other indicators". "The average value of the index, which begins in late 1993, is designed to be zero. Thus, zero is viewed as representing normal financial market conditions. Values below zero suggest below-average financial market stress." Latest reading is -0.7206 (week of 9 Oct 2026). — [FRED, STLFSI4](https://fred.stlouisfed.org/series/STLFSI4)
- **Chicago Fed NFCI and ANFCI:**
  - A weighted average of "105 measures of financial activity each expressed relative to their sample averages and scaled by their sample standard deviations".
  - Both are "constructed to have an average value of zero and a standard deviation of one over a sample period extending back to 1971". "Positive values of the NFCI have been historically associated with tighter-than-average financial conditions".
  - The adjusted ANFCI "removes the variation in the individual indicators attributable to economic activity and inflation". It is the version that answers "tighter than the macro backdrop would suggest".

  — [Chicago Fed, NFCI About](https://www.chicagofed.org/research/data/nfci/about)
- **Kansas City Fed (KCFSI):** monthly. Its methodology was changed in September 2021, when the SNL bank index was replaced with the S&P U.S. BMI Banks Index, using regression-predicted values for 1989-2004. — [FRED, KCFSI](https://fred.stlouisfed.org/series/KCFSI)
- **OFR FSI:** zero means "stress is at normal levels" (see above).
- Note: these zero lines are sample-mean conventions (mean 0, SD 1). They define "average", not "stressed". None of the three publishers attaches a stress threshold in the passages read.

**NY Fed term-spread recession probability (free; monthly)**
- **Model:** a probit, Recess(t+12) = F(α + β·spread(t)). The spread is the monthly average of the 10-year Treasury yield minus the 3-month bill "expressed on a bond-equivalent basis". "It seems most appropriate to look at the spread as a recession indicator on at least a monthly average basis." — [Estrella and Trubin, "The Yield Curve as a Leading Indicator: Some Practical Issues", NY Fed Current Issues 12(5), 2006](https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci12-5.pdf)
- **Track record as originally published:** "the estimated probability of recession exceeded 30 percent in the case of each recession and ranged as high as 98 percent in the 1981-82 recession". "When inversion on a monthly average basis is used as an indicator, there have been no false signals over this period", though "inversions in daily or intraday data often prove to be false signals." — [same](https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci12-5.pdf)
- **Current published values:**
  - Parameters were estimated on January 1959 to December 2009 data (α = -0.5333, β = -0.6330).
  - The September 2026 spread is 0.955; the probability of recession in September 2027 is 12.76%.
  - Updated 4 Oct 2026.

  — [NY Fed, Probability of US Recession chart (PDF)](https://www.newyorkfed.org/medialibrary/media/research/capital_markets/Prob_Rec.pdf); [NY Fed Yield Curve FAQ page](https://www.newyorkfed.org/research/capital_markets/ycfaq.html)
- **2022-2025 episode, from the NY Fed's own data file (allmonth.xls, read 14 Oct 2026):**
  - The monthly-average spread was negative in 27 months between November 2022 and April 2025.
  - The model's 12-month-ahead probability was at or above 30% for every target month from November 2023 to November 2025, peaking at 70.9% for May 2024.
  - The file's NBER recession flag shows no recession after 2020 through September 2026.
  - By the model's 30% convention, this is the second spell in the file of 30%-plus probabilities with no recession in the target window. The first is 1967 (target months January 1967 and September 1967 to February 1968, peak 41.1%; no NBER recession until 1969-70). It is also by far the longest and highest such spell.
  - The highest probability the model assigned to the months that turned out to be recession months:
    - 30% or more in seven of nine NBER recessions since 1960: 1970 (41.8%), 1973-75 (68.1%), 1980 (47.3%), 1981-82 (95.4%), 1990-91 (31.5%), 2001 (44.8%), 2008-09 (41.7%).
    - Below 30% in 1960-61 (27.8%) and 2020 (27.5%; a pandemic shock).
  - These are my calculations from the published file, not NY Fed statements.

  — [NY Fed allmonth.xls](https://www.newyorkfed.org/medialibrary/media/research/capital_markets/allmonth.xls)

**BIS/Basel credit-to-GDP gap (Borio-Lowe lineage; used in the Basel III countercyclical buffer)**
- **Rule:**
  - The gap is "deviations from the credit to GDP ratio from its long term trend, calculated by a one-sided HP filter using a smoothing factor λ=400,000".
  - Buffer guide: 0% when the gap is "2 percentage points or less". Above that it varies "linearly between 0% and 2.5%" between 2 and 10 points, and reaches the maximum at 10 points or more.
  - The low threshold L=2 was set so that "the rule would have required the build up of capital for all major banking crises 2-3 years in advance".
  - Authorities should not "rely mechanistically on the credit/GDP guide" and "are expected to apply judgment".

  — [BCBS, "Guidance for national authorities operating the countercyclical capital buffer" (Dec 2010), PDF](https://www.bis.org/publications/201012-guidelines-guidance-national-authorities-operating-countercyclical-capital-buffer.pdf)
- **US practice:** the Fed's 2016 CCyB framework says the Board's assessments "are informed by a broad array of quantitative indicators of financial and economic performance and a set of empirical models". It "expects that the CCyB will be activated when systemic vulnerabilities are meaningfully above normal". It notes commenters' caution that "no academic consensus had been reached with regard to the usefulness of a credit-to-GDP ratio gap". — [Fed, Framework for Implementing the U.S. Basel III Countercyclical Capital Buffer, FR Doc. 2016-21970 (16 Sep 2016)](https://www.govinfo.gov/content/pkg/FR-2016-09-16/html/2016-21970.htm)
- The Fed staff heat map (FEDS 2015-059, above) reports that its vulnerability composites "lead the credit-to-GDP gap ... by a year or more". — [FEDS 2015-059](https://www.federalreserve.gov/econresdata/feds/2015/files/2015059pap.pdf)

### Inferences
- **For a 1-to-5 rating, the closest published precedents are the percentile and z-score heat maps.** The OFR FSVM coloured indicators "based on their positions within a long-term range". Aikman et al. used percentiles with 65th, 80th and 85th cut-points and showed four interchangeable rescalings (kernel CDF, Normal CDF of z, min-max, rank).
  - A quintile mapping (percentile rank 0-20 = 1 ... 80-100 = 5, signed so that "bad" is high) is a natural, published-adjacent design. No regulator publishes that exact 1-to-5 mapping.
- **Choose the window and say so.** Aikman et al. standardised on 1990Q1-2014Q4. The FDIC uses a calm 2015-2019 window. The NFCI uses 1971 onward; STLFSI4 uses late 1993 onward. Results differ materially by window. Real-time (expanding-window) scoring is more honest, but Aikman et al. show it changes the signal: "it would have also signaled elevated risks during the late 1990s".
- **Level against change.** The Sahm rule (change from a 12-month low) triggered early in each recession from 1970 to 2009 in real time, per Sahm (2019). FRED's real-time series also crossed in April 2020 (4.00). A level percentile of unemployment would not, because unemployment is lowest just before recessions. A tool should rate both the level and the recent change for labour series. This follows from the rule's construction; no publisher has said it.
- **Direction matters per series.** For financial-conditions indexes, positive means tighter or more stress. For CFNAI, negative means weaker. For spreads, wider is worse. For house-price valuation, higher (overvaluation) is the vulnerability. This mirrors the FSR's "valuation pressures" framing and the Fed scenario guides' "severity higher when asset values have risen".
- **The 2022-25 false alarms argue for multi-signal confirmation and a "why" field.** The 2024 Sahm reading was attributed to labour-supply growth, and the yield curve was distorted by monetary-policy normalisation. A narrative tool should show which inputs drive a high rating, not only the rating.

### Gaps
- The FSR's own internal heat-map methodology has not been published in full since FEDS 2015-059. The FSR presents percentiles chart by chart.
- I found no published, authoritative track record for the zero-line stress indexes (STLFSI4, KCFSI, NFCI) as recession or loss predictors at a specific threshold. Their publishers define only "average".
- The Sahm rule's 2024 episode: no Fed or NBER publication reviewing it was read. The attribution to labour supply rests on press reports of Sahm's own comments.
- I did not verify NBER's business-cycle page directly. "No recession after 2020" rests on the NBER_Rec column in the NY Fed's allmonth.xls file (data through September 2026).
- I did not examine the 2014 OFR FSVM working paper (methodology for the colour scores), so its exact percentile bands are unverified.

## 5. Composite indexes worth tracking

### Takeaway
Of the composites asked about, five are free and current:
- **CFNAI** (Chicago Fed, monthly; a −0.70 threshold on its 3-month average);
- **Dallas Fed WEI** (weekly; moved from the NY Fed in Dec 2023);
- **Atlanta Fed GDPNow** (a nowcast);
- **OECD CLI** (monthly; 100 = long-term trend; free through the OECD SDMX API);
- **KC Fed LMCI** (monthly; level and momentum, 0 = long-run average).

The **Conference Board LEI** is free as a headline release, but the data are a Conference Board product. **The Philadelphia Fed state leading indexes are discontinued.**

### Cited Findings
- **Conference Board LEI (licensed data; free headline).** Ten components and the 3Ds rule are listed in section 4. The August 2026 LEI is 99.5 (2016=100). The next release is scheduled for 22 Oct 2026. The companion Coincident (CEI) and Lagging (LAG) indexes are published in the same release. — [Conference Board, US Leading Indicators](https://www.conference-board.org/topics/us-leading-indicators)
- **OECD Composite Leading Indicator (free).**
  - The CLI is "designed to provide qualitative information on short-term economic movements, especially at the turning points, rather than quantitative measures. Therefore, the main message of CLI movements over time is the increase or decrease, rather than the amplitude."
  - "The OECD's headline indicator is the amplitude adjusted CLI ... turning points in the de-trended reference series have been found about 4 to 8 months (on average) after the signals of turning points had been detected." The reference series is GDP since March 2012. — [OECD SDMX dataflow DSD_STES@DF_CLI, description](https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.STES/DSD_STES@DF_CLI/latest?references=none&detail=full)
  - US CLI (amplitude adjusted, OECD harmonised): 100.87 (Jul 2026), 100.95 (Aug 2026), 101.00 (Sep 2026). — [OECD SDMX API, USA.M.LI...AA...H (queried 14 Oct 2026)](https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,/USA.M.LI...AA...H?lastNObservations=4&format=csvfilewithlabels)
  - The conventional reading of 100 as the long-term trend, with four phases (expansion: above 100 and rising; downturn: above 100 and falling; slowdown: below 100 and falling; recovery: below 100 and rising), is reported from OECD release tables via secondary search results: [OECD iLibrary CLI tables](https://www.oecd-ilibrary.org/economics/composite-leading-indicators-2013-6_cli-table-2013-6-en). The oecd.org page itself was behind a Cloudflare challenge and was not read directly.
- **Chicago Fed National Activity Index (CFNAI; free).** 85 indicators. Zero is trend growth; values are in standard-deviation units. A CFNAI-MA3 below −0.70 after an expansion means an increasing likelihood of recession; above +0.70 more than two years into an expansion means an inflation risk. — [Chicago Fed CFNAI](https://www.chicagofed.org/research/data/cfnai/current-data)
- **Philadelphia Fed state leading indexes: DISCONTINUED.** "The Philadelphia Fed Will No Longer Release the State Leading Indexes."
  - In 2020, "due to the sudden, extreme impact of the COVID-19 outbreak on initial unemployment claims", the method "was not well suited".
  - "The Philadelphia Fed has reevaluated the potential to resume accurate estimation in 2025 and ultimately made the decision to no longer release the state leading indexes."
  - The FRED leading-index series (e.g. PASLIND) end at February 2020.

  — [Philadelphia Fed, State Leading Indexes](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/state-leading-indexes); [St. Louis Fed news, May 2020](https://news.research.stlouisfed.org/2020/05/philadelphia-fed-suspends-release-of-state-leading-indexes); [FRED PASLIND](https://fred.stlouisfed.org/series/PASLIND)

  The separate **state coincident indexes** page is live ([Philadelphia Fed](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/state-coincident-indexes)). I did not confirm its update cadence (JS-rendered page).
- **Atlanta Fed GDPNow (free).**
  - Provides "a 'nowcast' of the official estimate prior to its release by estimating GDP growth using a methodology similar to the one used by the US Bureau of Economic Analysis".
  - "GDPNow is not an official forecast of the Atlanta Fed."
  - Back-tested RMSE just before the advance estimate "is 1.15 percentage points for the 2000:Q1–2013:Q4 period ... these accuracy metrics do not give compelling evidence that the model is more accurate than professional forecasters."
  - It currently tracks 2026:Q3.

  — [Atlanta Fed GDPNow](https://www.atlantafed.org/cqer/research/gdpnow)
- **Weekly Economic Index (WEI; free): now at the Dallas Fed.**
  - "As of December 2023, the Weekly Economic Index is published by the Federal Reserve Bank of Dallas." — [NY Fed WEI page](https://www.newyorkfed.org/research/policy/weekly-economic-index)
  - It "represents the common component of 10 different daily and weekly series covering consumer behavior, the labor market and production", "scaled to four-quarter GDP growth", and is updated Thursdays.
  - 8 Oct 2026: 2.71% for the week ended 3 Oct; 13-week average 2.88%; against 2.19% four-quarter GDP growth through 2026:Q2.

  — [Dallas Fed WEI](https://www.dallasfed.org/research/wei)
- **Kansas City Fed Labor Market Conditions Indicators (LMCI; free).** "Two monthly measures of labor market conditions based on 24 labor market variables. One indicator measures the level of activity in labor markets and the other indicator measures momentum." "A positive value indicates that labor market conditions are above their long-run average." A Census-division version (DIV-LMCI) exists. Reference: Hakkio and Willis (2014). — [KC Fed LMCI](https://www.kansascityfed.org/data-and-trends/labor-market-conditions-indicators/)

### Inferences
- **Split by sign convention for a rating tool:**
  - "Zero equals average, SD units": CFNAI, LMCI, NFCI, STLFSI4, OFR FSI. These can be rated directly from their own published thresholds (−0.70) or by percentile.
  - "100 equals trend": OECD CLI.
  - "Growth-rate scaled": WEI, GDPNow. These need their own percentile history to rate.
- **LMCI suits the Sahm-style logic.** Its "level" and "momentum" split matches the inference in section 4 that labour series need both a level and a change reading. The KC Fed publishes both.
- **Regional coverage gap.** With the state leading indexes gone, there is no free Fed-published *leading* state composite. The DIV-LMCI (Census division) and the Philadelphia Fed coincident indexes are what remain for a footprint view. That is an inference from what I found, not an exhaustive search.

### Gaps
- Conference Board licensing terms for historical LEI data were not confirmed from a Conference Board terms page. "Licensed" rests on the brief's premise and the trademarked, member-gated presentation.
- I could not read the current GDPNow estimate value (the page is JavaScript-rendered).
- I did not obtain the KC Fed LMCI's latest values or the CFNAI's latest monthly reading (JS-rendered pages). Both have data downloads on their pages.
- I found no published track-record study for the WEI or LMCI as recession or credit-loss signals.

## 6. Regulator guidance on external macro factors (risk appetite, emerging risk, CECL reasonable and supportable forecasts)

### Takeaway
US guidance requires banks to **consider** external economic conditions in four places: the allowance, stress testing, risk appetite, and the risk-governance framework. It **does not prescribe any indicator set or threshold**. In the interagency CECL policy statement the agencies explicitly declined to supply an economic forecast or define the reasonable and supportable period.

The texts that come closest to specifying content are:
- the qualitative-factor list in the interagency CECL policy statement ("changes in international, national, regional, and local economic and business conditions"), with its example that local unemployment may matter more than national;
- the 2012 stress-testing guidance (geographic concentration, local shocks; stress testing "valuable during benign periods when other measures may not indicate emerging risks").

### Cited Findings
**Interagency Policy Statement on Allowances for Credit Losses (Fed, FDIC, NCUA, OCC; final 1 Jun 2020)**
- "When estimating expected credit losses, FASB ASC Topic 326 requires management to consider forward-looking information that is both reasonable and supportable and relevant to assessing the collectibility of cash flows." "These forecasts may include data from internal sources, external sources, or a combination of both." "Management is not required to search for all possible information nor incur undue cost and effort to collect data for its forecasts."
- On reversion: "FASB ASC Topic 326 requires reverting to historical loss information, or an appropriate proxy, for those periods beyond the reasonable and supportable forecast period". It "does not require the application of a specific reversion technique or use of a specific reversion period". "Management should not adjust historical loss information for existing economic conditions or expectations of future economic conditions for periods beyond the reasonable and supportable period."
- "FASB ASC Topic 326 does not require the use of multiple economic scenarios; however, institutions are not precluded from considering multiple economic scenarios."
- Adjustments "should reflect changes to relevant data (such as changes in unemployment rates, delinquency, or other factors associated with the financial assets)".
- The qualitative factors include "Actual and expected changes in international, national, regional, and local economic and business conditions and developments in which the institution operates that affect the collectibility of financial assets". Example given: national or state unemployment may look strong, "but a local unemployment rate, which may be significantly higher, for example, because of the actual or forecasted loss of a major local employer may be more relevant".
- Commenters asked the agencies to define the reasonable and supportable period and provide "an economic forecast or a simple model that can be used by all institutions". The agencies "decided not to limit flexibility ... by narrowing options or defining terms that are not defined in GAAP."
- Peer comparisons need caution because of differences in "reasonable and supportable forecast period assumptions, reversion techniques".

— [Federal Register, Doc. 2020-10291 (1 Jun 2020), govinfo text](https://www.govinfo.gov/content/pkg/FR-2020-06-01/html/2020-10291.htm)

**OCC Heightened Standards (12 CFR Part 30, Appendix D; covered banks of $50bn or more)**
- "A covered bank should have a comprehensive written statement that articulates the covered bank's risk appetite ... The risk appetite statement should include both qualitative components and quantitative limits. ... Quantitative limits should incorporate sound stress testing processes, as appropriate, and address the covered bank's earnings, capital, and liquidity."
- "Independent risk management should review and update the risk governance framework at least annually, and as often as needed to address ... changes in the covered bank's risk profile caused by emerging risks, its strategic plans, or other internal and external factors."
- Internal audit should assess "the risks, including emerging risks, associated with each" material process and product line.

— [eCFR, 12 CFR Part 30 (versioner API, as of 1 Sep 2026)](https://www.ecfr.gov/current/title-12/chapter-I/part-30)

**Interagency supervisory guidance on stress testing (banks over $10bn; 17 May 2012)**
- "A banking organization should use its stress testing framework to determine whether exposures, activities, and risks under normal and stressed conditions are aligned with the banking organization's risk appetite." Results "should be used to inform the board about alignment of the banking organization's risk profile with the board's chosen risk appetite".
- "A banking organization that is geographically concentrated may determine that a certain segment of its business may be more adversely affected by shocks to economic activity at the state or local level than by a severe national recession."
- "Stress testing may be particularly valuable during benign periods when other measures may not indicate emerging risks." Banks should be able to run ad hoc tests "to address rapidly emerging risks". Scenarios should have "a coherent, logical narrative or 'story'".

— [Federal Register, Doc. 2012-11989 (govinfo text)](https://www.govinfo.gov/content/pkg/FR-2012-05-17/html/2012-11989.htm)

**OCC Comptroller's Handbook and the National Risk Committee**
- The OCC's "Lending and Loan Portfolio Risk Management" booklet is Version 1.0, issued by OCC Bulletin 2026-29 ("Credit Risk: 'Lending and Loan Portfolio Risk Management' Booklet of the Comptroller's Handbook and Rescissions"). It "provides information about lending, risks associated with lending, risk management practices applicable to all phases of a loan's life cycle, and loan portfolio risk management." — [OCC Handbook index page](https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/lending-loan-portfolio-risk-management/index-lending-loan-portfolio.html)
- The predecessor "Loan Portfolio Management" booklet argued that "traditional practices rely too much on trailing indicators of credit quality such as delinquency, nonaccrual, and risk rating trends. Banks have found that these indicators do not provide sufficient lead time for corrective action when there is a systemic increase in risk." **This quote comes from a search-engine extract of the OCC PDF, which I could not open.** — [OCC, Loan Portfolio Management booklet (previous edition, PDF)](https://occ.gov/publications-and-resources/publications/comptrollers-handbook/files/loan-portfolio-management/pub-ch-loan-portfolio-mgmt.pdf)
- A search summary reports that the OCC revised the "Allowances for Credit Losses" booklet in 2026 (OCC Bulletin 2026-33). I could not open the bulletin or booklet. — [OCC ACL booklet index](https://occ.gov/publications-and-resources/publications/comptrollers-handbook/files/allowances-for-credit-losses/index-allowance-credit-losses.html)
- The OCC's own narrative is produced by the National Risk Committee, which "monitors the condition of the federal banking system and identifies key risks" and "emerging threats". It is published semiannually as the SARP (section 3). — [OCC SARP Spring 2026](https://www.occ.gov/publications-and-resources/publications/semiannual-risk-perspective/files/pub-semiannual-risk-perspective-spring-2026.pdf)

**Fed macroprudential guidance (indirect)**
- The Fed's CCyB framework is "informed by a broad array of quantitative indicators of financial and economic performance and a set of empirical models". The buffer is expected to be activated "when systemic vulnerabilities are meaningfully above normal". — [FR Doc. 2016-21970](https://www.govinfo.gov/content/pkg/FR-2016-09-16/html/2016-21970.htm)
- The FSR's split between shocks and vulnerabilities is in section 3. — [FSR May 2026](https://www.federalreserve.gov/publications/2026-may-financial-stability-report-purpose-and-framework.htm)

### Inferences
- A macro-conditions tool sits comfortably inside this guidance as **evidence for qualitative factors and emerging-risk reporting**: the "changes in ... national, regional, and local economic and business conditions" factor and the Heightened Standards' "emerging risks ... internal and external factors". It is not a replacement for the CECL forecast. Because no regulator prescribes indicators or cut-offs, the tool's choices must be documented and defended by the bank. The stress-test guides (section 1) and the published thresholds (section 4) are the strongest available citations for those choices.
- The CECL policy statement's local-unemployment example and the stress-testing guidance's "state or local level" sentence are direct regulatory support for **footprint-level** (state or MSA) versions of the national series.
- "Stress testing may be particularly valuable during benign periods when other measures may not indicate emerging risks." This is regulatory support for rating **vulnerability build-up** (valuations, leverage) and not only current stress. It mirrors the FSR's vulnerabilities framing.

### Gaps
- OCC Comptroller's Handbook PDFs ("Lending and Loan Portfolio Risk Management", 2026; "Allowances for Credit Losses", revised 2026; "Corporate and Risk Governance") were behind an OCC security redirect from this environment and could not be read. Their exact text on economic indicators, risk appetite and emerging risk is unverified here.
- I did not verify whether the 2012 interagency stress-testing guidance or other cited guidance has been rescinded or amended in the 2025-2026 OCC guidance rescissions. The bulletin titles found mention "Rescissions" without detail.
- I did not review FDIC or Fed-specific risk-appetite guidance (e.g. Fed SR letters on risk management for large firms) or the OCC's Risk Assessment System definitions for credit risk ("quantity" and "direction").
- FASB ASC 326 text was not read directly (it requires FASB Codification access). Its requirements are quoted as restated by the agencies.
