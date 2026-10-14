# Macro risk indicators for lending: frameworks and methods

*Research in progress, started 14 Oct 2026. Sections fill in as findings are verified.*

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
- The Z.1 CRE price index used by the stress test "is based on quarterly change of the Value Weighted Costar U.S. Composite Index Excluding Multifamily". — [Fed final rule, 91 FR (2 Oct 2026), FR Doc. 2026-20247, fn. 118](https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20247.htm)
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
- The variable notes give free public series for 13 of 16 domestic variables. BBB yield (ICE), equities (Dow Jones via Bloomberg) and VIX (CBOE via Bloomberg) are licensed in the Fed's own build. Whether free FRED equivalents (e.g. ICE BofA BBB OAS, VIXCLS) are acceptable substitutes is a design choice for the tool, not something the Fed states.

### Gaps
- The 2027 proposed scenarios: the final rule says the Board finalised models for 2027, but I did not confirm whether the 2027 scenarios themselves have been proposed or published as of 14 Oct 2026.
- I did not read the separate "Review of Comments" document or the macro-model guide in full.

## 2. Bank CECL disclosures: macroeconomic variables named in 10-K allowance discussions

### Takeaway
(pending)

### Cited Findings
- (pending)

### Inferences
- (pending)

### Gaps
- (pending)

## 3. Regulator publications that build a macro narrative (Fed FSR, OCC SARP, FDIC Risk Review, FDIC QBP)

### Takeaway
(pending)

### Cited Findings
- (pending)

### Inferences
- (pending)

### Gaps
- (pending)

## 4. Published methods for flagging unusual macro readings

### Takeaway
(pending)

### Cited Findings
- (pending)

### Inferences
- (pending)

### Gaps
- (pending)

## 5. Composite indexes worth tracking

### Takeaway
(pending)

### Cited Findings
- (pending)

### Inferences
- (pending)

### Gaps
- (pending)

## 6. Regulator guidance on external macro factors (risk appetite, emerging risk, CECL reasonable and supportable forecasts)

### Takeaway
(pending)

### Cited Findings
- (pending)

### Inferences
- (pending)

### Gaps
- (pending)
