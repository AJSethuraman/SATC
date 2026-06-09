# Benchmark review memo -- Meridian Fabrication LLC (sample)

**Segment:** Middle-Market C&I | **Size band:** Core middle market ($25-100M EBITDA) | **Latest FY:** FY2024 | **View used for flags:** private-MM adjusted | **Prepared:** 2026-06-09

**Benchmark data:** ccbw 0.1.0, snapshot v1 (generated 2026-06-09T23:46:33+00:00), source: SYNTHETIC_DEMO.

> **DATA CAVEAT:** SYNTHETIC DEMONSTRATION DATA: this snapshot was generated from a deterministic synthetic corpus shaped like EDGAR CompanyFacts, because the build environment had no network access to data.sec.gov. All distributions are illustrative of the machinery, NOT sourced market statistics. Refresh against live EDGAR before any production use (see meta.refresh).

## Position vs. peer distributions

| Metric | Borrower | Peer median (adj.) | Percentile (adj.) | Flag | Basis |
|---|---|---|---|---|---|
| Total Debt / EBITDA | 5.06x | 3.92x | p76 | WATCH | Fiscal-year basis. |
| Net Debt / EBITDA | 4.88x | 3.04x | p77 | WATCH | Fiscal-year basis. |
| EBITDA / Interest | 2.19x | 3.27x | p33 | IN RANGE | Fiscal-year basis. |
| EBITDA Margin | 13.3% | 10.2% | p71 | IN RANGE | Fiscal-year basis. |
| Cash Conversion Cycle | 103d | 62d | p84 | WATCH | DSO + DIO - DPO, all on year-end-balance / full-year-flow basis. |
| Current Ratio | 1.96x | 1.85x | p66 | IN RANGE | Fiscal-year-end current assets / current liabilities (point-in-time). |
| (EBITDA - Capex) / Interest | 1.71x | 2.27x | p33 | IN RANGE | Fiscal-year basis. |
| Gross Margin | 30.0% | 27.2% | p58 | IN RANGE | Fiscal-year basis. |
| Days Sales Outstanding | 58d | 47d | p83 | WATCH | Year-end receivables / full-year revenue x 365. |
| Days Inventory Outstanding | 91d | 57d | p84 | WATCH | Year-end inventory / full-year COGS x 365. |
| Days Payables Outstanding | 46d | 42d | p69 | IN RANGE | Year-end payables / full-year COGS x 365. |
| Total Debt / Total Assets | 77.1% | 33.7% | p98 | SEVERE | Fiscal-year-end basis, book values. |
| Revenue Growth YoY | -2.4% | -0.5% | p39 | IN RANGE | Fiscal-year over prior fiscal-year revenue growth. |

All borrower figures are lender-provided, fiscal-year basis, USD. Peer distributions are fiscal-year company observations; every cell's full basis and per-datapoint provenance route is recorded in the benchmark snapshot and pipeline panel.

## Findings (departure vs. normalization)

### Total Debt / EBITDA: 5.06x -- WATCH

Path: FY2022 3.50x, FY2023 4.23x, FY2024 5.06x. Adjusted peer band (p25-p75): 2.39x-4.78x; raw public band: 2.70x-4.61x.

**Trajectory:** Structural departure (widening). Moving away from the peer baseline (gap widening ~0.36/yr since FY2022) -- a structural departure in motion, the pattern that precedes migration to criticized status; mechanism review warranted now.

**Mechanism:** Leverage rises through two channels: the numerator (acquisitions, shareholder distributions, capex funded with debt, revolver creep funding working capital) or the denominator (EBITDA compression). Denominator-driven leverage is the more dangerous read because it compounds -- verify which channel moved before accepting a 'we'll grow into it' rationale.

**Basis:** Fiscal-year basis. Total debt (incl. current portions & short-term borrowings, USD raw units) / EBITDA (operating income + D&A, no addbacks).
**Historical anchor:** pre-2020 peer median 3.76x (raw, pooled FY2015-2019) vs. current 3.92x.
**Adjustment applied:** Raw public distribution -> private-MM adjusted: dispersion widened x1.25 around the median; survivorship: risky tail (p90) extended by 12% of IQR. Parameters are judgment calibration (tunable); see methodology memo §adjustment-engine.
**Coverage gaps on this metric:** winsorized at analytic bounds [0, 15]: 1 current / 0 baseline observation(s) clamped (distressed outliers kept, not dropped)

### Net Debt / EBITDA: 4.88x -- WATCH

Path: FY2022 3.27x, FY2023 4.03x, FY2024 4.88x. Adjusted peer band (p25-p75): 1.75x-4.03x; raw public band: 2.01x-3.83x.

**Trajectory:** Structural departure (widening). Moving away from the peer baseline (gap widening ~0.80/yr since FY2022) -- a structural departure in motion, the pattern that precedes migration to criticized status; mechanism review warranted now.

**Mechanism:** A wide gap between gross and net leverage means a cash buffer -- but verify the cash is unrestricted and not trapped (foreign subs, regulatory deposits, borrowing-base collateral). Private MM borrowers typically sweep cash against the revolver, so a large idle balance alongside revolver usage deserves a question.

**Basis:** Fiscal-year basis. (Total debt - cash & equivalents) / EBITDA. Cash at fiscal year end (point-in-time).
**Historical anchor:** pre-2020 peer median 2.83x (raw, pooled FY2015-2019) vs. current 3.04x.
**Adjustment applied:** Raw public distribution -> private-MM adjusted: dispersion widened x1.25 around the median; survivorship: risky tail (p90) extended by 12% of IQR. Parameters are judgment calibration (tunable); see methodology memo §adjustment-engine.
**Coverage gaps on this metric:** winsorized at analytic bounds [-5, 15]: 1 current / 0 baseline observation(s) clamped (distressed outliers kept, not dropped)

### Cash Conversion Cycle: 103d -- WATCH

Path: FY2022 80d, FY2023 94d, FY2024 103d. Adjusted peer band (p25-p75): 54d-92d; raw public band: 56d-86d.

**Trajectory:** Structural departure (widening). Moving away from the peer baseline (gap widening ~12/yr since FY2022) -- a structural departure in motion, the pattern that precedes migration to criticized status; mechanism review warranted now.

**Mechanism:** The cash conversion cycle is the financing the business model demands: each day of CCC is a day of revenue that must be funded by the revolver or equity. A lengthening CCC during growth is the classic mechanism of 'profitable companies that run out of cash' -- size the revolver against peak, not average, CCC.

**Basis:** DSO + DIO - DPO, all on year-end-balance / full-year-flow basis.
**Historical anchor:** pre-2020 peer median 62d (raw, pooled FY2015-2019) vs. current 62d.
**Adjustment applied:** Raw public distribution -> private-MM adjusted: dispersion widened x1.25 around the median; survivorship: risky tail (p90) extended by 12% of IQR. Parameters are judgment calibration (tunable); see methodology memo §adjustment-engine.

### Days Sales Outstanding: 58d -- WATCH

Path: FY2022 48d, FY2023 53d, FY2024 58d. Adjusted peer band (p25-p75): 43d-53d; raw public band: 44d-52d.

**Trajectory:** Structural departure (widening). Moving away from the peer baseline (gap widening ~5.0/yr since FY2022) -- a structural departure in motion, the pattern that precedes migration to criticized status; mechanism review warranted now.

**Mechanism:** Rising DSO mechanisms: customer-mix shift toward slower payers, extended terms granted to hold volume (disguised price cut), billing/collections breakdown, or disputed receivables aging on the book. Verify aging schedule and concentration -- one large slow-paying customer moves the whole ratio.

**Basis:** Year-end receivables / full-year revenue x 365. Point-in-time numerator over duration denominator -- seasonal balances distort; basis note applies.
**Historical anchor:** pre-2020 peer median 47d (raw, pooled FY2015-2019) vs. current 47d.
**Adjustment applied:** Raw public distribution -> private-MM adjusted: dispersion widened x1.25 around the median; survivorship: risky tail (p90) extended by 12% of IQR. Parameters are judgment calibration (tunable); see methodology memo §adjustment-engine.

### Days Inventory Outstanding: 91d -- WATCH

Path: FY2022 81d, FY2023 88d, FY2024 91d. Adjusted peer band (p25-p75): 55d-74d; raw public band: 56d-70d.

**Trajectory:** Structural departure (widening). Moving away from the peer baseline (gap widening ~5.3/yr since FY2022) -- a structural departure in motion, the pattern that precedes migration to criticized status; mechanism review warranted now.

**Mechanism:** Inventory build mechanisms: demand miss (involuntary build -- the bad one), strategic pre-buy ahead of input cost increases, new product/location stocking, or obsolescence accumulating unwritten. Involuntary build shows alongside falling revenue growth; check which direction revenue moved.

**Basis:** Year-end inventory / full-year COGS x 365. Point-in-time over duration; harvest/seasonal effects noted per segment.
**Historical anchor:** pre-2020 peer median 57d (raw, pooled FY2015-2019) vs. current 57d.
**Adjustment applied:** Raw public distribution -> private-MM adjusted: dispersion widened x1.25 around the median; survivorship: risky tail (p90) extended by 12% of IQR. Parameters are judgment calibration (tunable); see methodology memo §adjustment-engine.

### Total Debt / Total Assets: 77.1% -- SEVERE

Path: FY2022 68.0%, FY2023 72.1%, FY2024 77.1%. Adjusted peer band (p25-p75): 22.2%-38.0%; raw public band: 24.5%-37.1%.

**Trajectory:** Structural departure (widening). Moving away from the peer baseline (gap widening ~4.6/yr since FY2022) -- a structural departure in motion, the pattern that precedes migration to criticized status; mechanism review warranted now.

**Mechanism:** Debt against the asset base is the balance-sheet read on the same leverage question: it rises through borrowing, asset write-downs, or buybacks/distributions shrinking equity. For cash-flow credits it is secondary to debt/EBITDA but catches the case where asset sales fund debt service -- leverage stable on EBITDA while the collateral base shrinks.

**Basis:** Fiscal-year-end basis, book values. Book-LTV proxy for CRE; book != market value of property (basis note).
**Historical anchor:** pre-2020 peer median 32.2% (raw, pooled FY2015-2019) vs. current 33.7%.
**Adjustment applied:** Raw public distribution -> private-MM adjusted: dispersion widened x1.25 around the median; survivorship: risky tail (p90) extended by 12% of IQR. Parameters are judgment calibration (tunable); see methodology memo §adjustment-engine.

## Coverage gaps

- Total Debt / EBITDA: winsorized at analytic bounds [0, 15]: 1 current / 0 baseline observation(s) clamped (distressed outliers kept, not dropped)
- Net Debt / EBITDA: winsorized at analytic bounds [-5, 15]: 1 current / 0 baseline observation(s) clamped (distressed outliers kept, not dropped)
- EBITDA / Interest: FY2024: thin coverage (n=6 company-years < 8); percentiles unstable
- (EBITDA - Capex) / Interest: FY2024: thin coverage (n=6 company-years < 8); percentiles unstable

## Methodology appendix

**Peer set:** Public manufacturers, distributors and business-services companies (SIC 2000-3999 ex pharma/devices/food, 5000-5199, 7300-7399). Generic commercial & industrial credit: diversified end markets, cash-flow lending basis.

**Normalization rules applied to the peer set:**
- EBITDA = operating income + D&A (no addbacks for non-recurring items; public data does not support consistent addback identification -- noted as a basis difference vs. sponsor-adjusted private EBITDA).
- Total debt includes current portions and short-term borrowings.
- Working-capital cycle on a trade basis: DSO/DIO/DPO from year-end balances (point-in-time, not average -- basis-labeled).

**Cyclicality treatment:** Moderate cyclicality: 3-year revenue/EBITDA growth volatility is reported alongside levels; current-year readings are anchored against the pre-2020 baseline to avoid judging a peak as normal.

**Size-distortion / survivorship adjustment (this band):** dispersion widened x1.25; margin medians haircut 1pp; coverage medians shifted -0.25x; risky tail extended 12% of IQR. Rationale: Core band: moderate size gap; private credit's main market. Public small-caps in this band are usable comps but still survivors with better capital access than private peers. These parameters are judgment calibration and are tunable; raw and adjusted views are shown side by side in the workbench and above.

**Flag-rule validation (public-proxy backtest):** hit rate 30%, capture rate 40%, median lead time 2 yr over FY2017-FY2021 (vs. base deterioration rate 15%; Altman Z' reference hit rate 15%). Caveats: Public-proxy validation only: deterioration events are public-financials proxies for migration to non-accrual, not observed private-loan defaults. Directional check, not calibration.

**Refresh:** To refresh against live EDGAR: ccbw build-live --user-agent 'Name email' --out snapshot.json, then ccbw bake. Requires network access to data.sec.gov (10 req/s fair-access limit).

*Every quantitative figure above carries its basis label; peer figures trace to the versioned snapshot and per-datapoint provenance (CIK, accession, tag, form, filed date) in the pipeline panel. Prepared with the Commercial Credit Benchmark Workbench.*