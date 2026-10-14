# Household balance sheets, credit conditions, sentiment and housing: US public indicators for a consumer-lending macro risk narrative

_Status: IN PROGRESS (started 2026-10-14). Notes saved incrementally. Every FRED id below was checked on 2026-10-14 by downloading `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>` (no API key needed for that CSV route) and reading the first and last observation; "first obs" / "last obs" are what that download returned on that date._

_Scope: household debt, credit conditions, consumer sentiment, housing. Bank-level Call Report charge-off/delinquency rates (e.g. FRED DRCCLACBS, DRSFRMACBS) are deliberately excluded: the team already has them._

## Household debt burden and delinquency (DSR/FOR, NY Fed HHDC, bankruptcy, student loans)

### Takeaway
(being filled)

### Cited Findings

**A. Household Debt Service Ratio (DSR) — Federal Reserve Board. METHODOLOGY BREAK in 2024: the series a user downloads today is a different series from the one most published research used.**
- What it measures: required household debt payments (principal and interest; the new version also includes mortgage escrow) as a percent of disposable personal income; split into Mortgage DSR and Consumer DSR, which sum to the total; seasonally adjusted, quarterly — [Fed DSR release, 22 Sep 2026](https://www.federalreserve.gov/releases/dsr/default.htm)
- Current release: "Release date: September 22, 2026", data through 2026:Q2: total DSR 11.11, mortgage 5.83, consumer 5.28. Pre-pandemic 2019:Q4 was 11.73 / 5.92 / 5.81; the 2007:Q4 peak in the new series was 15.85 — [Fed DSR release](https://www.federalreserve.gov/releases/dsr/default.htm)
- Break: "Starting with the 2024:Q2 Debt Service Ratio (DSR) publication, the Board will transition to a new, credit bureau data-based methodology ... An archived version of the old DSR series will continue to be hosted at .../releases/housedebt/default.htm, but will no longer be updated." — [Fed archived DSR/FOR page](https://www.federalreserve.gov/releases/housedebt/default.htm)
- New method uses the FRBNY/Equifax Consumer Credit Panel (5% sample of adults with a credit record), summing reported monthly scheduled payments per tradeline; "Coverage of the full range of tradeline types in the CCP only begins in 2005, so the new method lacks the long history of the old version"; the new series includes escrow (taxes/insurance) in mortgage payments, so its level "is also consistently higher than that from the old DSR"; the old DSR did not account for pandemic student-loan forbearance — [Ringo, FEDS Notes, 4 Sep 2024](https://www.federalreserve.gov/econres/notes/feds-notes/introducing-a-credit-bureau-based-measure-of-u-s-household-debt-service-20240904.html)
- The old (archived) DSR ran quarterly from 1980:Q1 (10.61 in 1980:Q1; peak 13.29 in 2007:Q4) and assumed card minimum payments of 2.5% of balance per month — [Fed archived DSR/FOR page](https://www.federalreserve.gov/releases/housedebt/default.htm); [About the (old) release](https://www.federalreserve.gov/releases/housedebt/about.htm)
- FRED ids (release rid=89): `TDSP` (total), `MDSP` (mortgage), `CDSP` (consumer); on FRED these now carry the NEW series, first obs 2005-01-01, last obs 2026-04-01 (=2026:Q2) — [FRED TDSP](https://fred.stlouisfed.org/series/TDSP), [FRED release 89](https://fred.stlouisfed.org/release?rid=89). Anyone with a pre-2024 TDSP download starting in 1980 holds the old series; do not splice without a level adjustment (inference from the level gap documented by Ringo, above).
- Access: Fed page, XML zip (`/releases/dsr/data/FRB_dsr_xml.zip`), Data Download Program, FRED. The Fed announces that "During the week of November 9, the 'Build Your Package' feature in the Data Download Program (DDP) will be removed in preparation for the eventual retirement of the DDP"; users are pointed to FRED — [Fed DSR release](https://www.federalreserve.gov/releases/dsr/default.htm). Free; Fed data are public. Note the new DSR is derived from Equifax CCP microdata, but only the aggregate is published (licensing of the aggregate: no restriction stated on the release page — not verified further).
- Release lag: 2026:Q2 published 22 Sep 2026, i.e. roughly one quarter (~12 weeks) after quarter-end — [Fed DSR release](https://www.federalreserve.gov/releases/dsr/default.htm)

**B. Financial Obligations Ratio (FOR) — DISCONTINUED.**
- "The final data update for the Financial Obligations Ratios (FOR) statistical release is 2023:Q3. The Board decided to stop publishing the FOR due to a lack of high-quality data on property tax and homeowners' insurance payments." The Board suggests BEA rental-of-tenant-occupied-housing data for users who want to add rent — [Fed archived DSR/FOR page](https://www.federalreserve.gov/releases/housedebt/default.htm)
- FOR was broader than DSR: added rent on tenant-occupied property, auto lease payments, homeowners' insurance and property tax — [About the release](https://www.federalreserve.gov/releases/housedebt/about.htm)
- FRED `FODSP`: first obs 1980-01-01, last obs 2023-07-01 (=2023:Q3); it will not update — [FRED FODSP](https://fred.stlouisfed.org/series/FODSP)
