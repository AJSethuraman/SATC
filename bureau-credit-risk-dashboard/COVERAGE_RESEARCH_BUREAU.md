# Coverage Research — U.S. Consumer Credit-Bureau Data Feeds (v1)

Research artifact feeding the bureau-feed BUILD SPEC. Produced by a fan-out
deep-research pass (6 angles, 27 sources fetched, 66 claims extracted, 25
adversarially verified with 3-vote refute logic): **22 confirmed, 3 refuted, 0
unverified.** Every assertion below is tagged with its verification result and
sources. Claims marked **REFUTED** must not be relied on.

## Bottom line

There is a clean split between a **free/public tier** that can power the
*dashboard* lanes and a **licensed tier** required for the *watchlist* lane.
The decisive finding: **none of the no-contract sources carry a
portfolio-joinable account key or a usable fine-grained geographic key**, so a
buildable-today template is honestly **dashboard-only, with the watchlist lane
gated** until a licensed feed is contracted — the same "never plug a national
aggregate into the watchlist" rule the FRED template already enforces.

## Tier 1 — Free / no-contract (dashboard-lane stand-ins)

**NY Fed Consumer Credit Panel (CCP) / Quarterly Report on Household Debt and
Credit (HHDC)** — CONFIRMED (3-0).
- Anonymized, nationally representative **5% (one-in-20)** random sample of
  individuals with an SSN and a credit report (usually 19+), sourced from
  **Equifax** credit-report data. Data current through 2026Q1.
- Supports **national and regional (state-level)** aggregate balances and
  delinquencies **by product type** — but only at the aggregate level, **not as
  account-joinable records**.
- **State data is annual (Q4) only** for all 50 states + PR; **quarterly
  all-state granularity is withheld due to contractual restrictions with
  Equifax**. Microdata is restricted to Federal Reserve System researchers.
- Public, downloadable tables. Source: https://www.newyorkfed.org/microeconomics/faq

**Philadelphia Fed Consumer Credit Explorer (CCE)** — CONFIRMED (3-0), with one
sub-claim REFUTED.
- Built on the **same CCP/Equifax one-in-20 (5%) sample**. Provides credit use,
  average debt levels, and delinquency rates by product (auto, student,
  mortgage, credit cards), segmentable by **age, credit score, neighborhood
  income, and majority race/ethnicity**. Uses Equifax Risk Score 280–850 (prime
  >= 660).
- **REFUTED (0-3): the claim that CCE offers census-tract / ZIP / county / MSA
  geographic granularity usable as a watchlist join key.** Do NOT treat CCE as a
  geographic-key source.
- Source: https://www.philadelphiafed.org/surveys-and-data/community-development-data/consumer-credit-explorer

**TransUnion Credit Industry Insights Report (CIIR)** — CONFIRMED (3-0).
- Quarterly, market-level aggregated analytics over four segments (auto, card,
  consumer/personal lending, mortgage), built on depersonalized + aggregated
  data via TruIQ; covers new openings, scores, balances, payment behaviors and
  100+ variables. **Only the press-release trend summaries are free**; the full
  dataset requires a Prama license. **National, aggregate, no joinable key.**
- Q1 2026 figures (illustrate the metric shapes): total bankcard balances grew
  4.6% YoY to **$1.12 trillion**; bankcard 90+ DPD delinquency rose 10 bps YoY
  to **2.53%**; bankcard originations +13% YoY to **21.9M** (Q4 2025, a standard
  **one-quarter origination lag**); unsecured personal-loan originations a record
  **7.6M** (+21.7% YoY).
- Source: https://newsroom.transunion.com/q1-2026-ciir/

**Equifax Market Pulse** — CONFIRMED (3-0), with one sub-claim weakly refuted.
- Monthly U.S. national consumer-credit trend reports tracking originations,
  balances, and delinquencies across mortgages, auto loans/leases, student
  loans, bankcards, private-label cards, and personal loans.
- Full access to the standard charts is **gated behind contacting the Equifax
  Risk Advisory team (RiskAdvisors@Equifax.com)** — a free contact request, not
  an open download.
- **REFUTED (weak, 1-2): that Market Pulse is national-only with no state/MSA
  cut.** Do not assert granularity in either direction without confirmation.
- Source: https://www.equifax.com/business/trends-insights/marketpulse/

## Tier 2 — Licensed analytics (some watchlist-capable)

**TransUnion Prama Benchmarking** — CONFIRMED (3-0). On-demand access to a
depersonalized national credit file with **60 months of account history updated
monthly**, viewable **at MSA level**, across four segments (auto, credit card,
mortgage, personal loan), segmentable by **consumer risk band (subprime/prime),
geography, and vintage**. This is the one product confirmed to carry an **MSA
geographic key + segment key → genuinely watchlist-capable**.
Source: https://www.transunion.com/product/prama-benchmarking

**Experian Ascend Analytical Sandbox** — CONFIRMED (3-0). Licensed, hosted
hybrid-cloud analytics environment with ~18–20 years of monthly snapshots of
de-identified full-file credit data (~245M reach / 220M+ full-file consumers)
plus commercial/property/auto/alternative data; SAS, R/RStudio, Python, H2O,
Hue, Tableau; lenders can combine their own datasets. Not an open API.
Source: https://www.experian.com/business/products/ascend-analytical-sandbox

**TransUnion Prama Vintage Analysis** — CONFIRMED (3-0), with one sub-claim
REFUTED. 200M+ consumers, **seven years of cohort/vintage** performance.
**REFUTED (0-3): finer delinquency-by-tier/geography/LOB/product with nine
quarters.** Treat as vintage cohorts only.
Source: https://www.transunion.com/product/prama-vintage-analysis

## Tier 3 — Account-level (the real portfolio join; FCRA "account review")

**Experian Risk and Retention Triggers** — CONFIRMED (3-0). Account-level
monitoring delivering **daily alerts within minutes** of a triggering event:
new trades, increasing utilization / balances over limit, new collection
accounts, charge-offs, closed accounts, **new delinquency 30–180 DPD**,
short-term high-risk financing activity, and bankruptcy/deceased.
Source: https://www.experian.com/business/products/risk-and-retention-triggers

**TransUnion TruVision Credit Risk** — CONFIRMED (3-0). An "**account review**"
process plus **event-based monitoring** for managing an existing portfolio —
identify, segment, prioritize accounts and act on timely changes.
Source: https://www.transunion.com/solution/truvision/credit-risk/manage-customer-portfolio

**Equifax Developer Portal (auth model)** — CONFIRMED (3-0). Authenticated REST
APIs use **OAuth 2.0 client_credentials** (access token from client_id +
client_secret + scope; HTTP 401 without a valid token). This is the pattern a
licensed provider adapter's authentication would implement.
Source: https://developer.equifax.com/documentation

## Data-quality traps (bake into the adapter)

- **5% (one-in-20) anonymized sample**, not a census — sampling noise grows at
  finer cuts (NY Fed/CCP, Philly Fed CCE).
- **One-quarter origination lag** is standard (CIIR; originations generally lag).
- **Quarterly all-state granularity withheld** by Equifax contract (NY Fed);
  only annual Q4 state data is public.
- Vendor figures (Sandbox 245M/18–20yr, Prama 200M/60mo, CIIR Q1 2026 numbers)
  are **point-in-time** and change each release.
- **Score scales differ** and must be normalized: Equifax Risk Score 280–850
  (prime >= 660), VantageScore, FICO.

## Refuted claims — DO NOT USE

1. Philadelphia Fed CCE offers census-tract / ZIP / county / MSA geographic
   granularity (a watchlist join key). — **REFUTED 0-3.**
2. Prama Vintage Analysis provides delinquency by credit tier / geography / LOB
   / product over nine quarters. — **REFUTED 0-3.**
3. Equifax Market Pulse is national-only with no state/MSA cut. — **REFUTED
   1-2 (weak); do not assert either way.**

## Open questions (in scope, NOT confirmed — flag in the spec)

- Exact FCRA permissible-purpose **attestation mechanics**, data-use /
  **redistribution restrictions**, **retention** limits, and secure-transfer
  (SFTP/encryption) requirements for each licensed feed.
- The actual sub-national **geographic granularity and join-key field** for each
  licensed watchlist-capable feed (e.g., the precise Prama Benchmarking MSA
  field; whether Market Pulse has a state/MSA cut).
- Concrete **cost / licensing structure** (pricing tiers, minimums) for Sandbox,
  Prama, and the trigger/account-review services.
- The literal **field schemas / data dictionaries** for the NY Fed HHDC public
  tables and Philly Fed CCE that a template would bind to.

## Source quality note

Many vendor product pages (equifax.com, transunion.com, experian.com) returned
HTTP 403 to automated fetch; verification relied on search-indexed snippets of
the exact primary URLs plus independent mirrors. Content is corroborated but a
few literal live-page bodies were not read directly. Treat vendor capability
statements as marketing-sourced and re-confirm specifics at contract time.
