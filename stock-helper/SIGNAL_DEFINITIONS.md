# Signal Definitions

Every signal is a transparent rule over canonical metrics. Each result always
reports: **metric used, value, direction, interpretation, source, confidence,
caveat**. Statuses: `OK`, `NOT_APPLICABLE` (industry rules), `INSUFFICIENT_DATA`
(fewer periods than the rule needs), `UNAVAILABLE` (metric not mapped from XBRL),
`PLACEHOLDER` (declared but not yet implemented).

Directions are descriptive (`improving` / `deteriorating` / `stable` / `mixed`),
not predictive. Scores are small integers in [-2, +2] used only for ordering and
badges — they are *not* expected returns.

Confidence reflects **data quality**, not conviction: `high` = standard XBRL tags,
several periods; `medium` = fallback tags or short history; `low` = proxy
formulas or known comparability issues.

## Industry buckets and applicability

Buckets (from SIC, see `src/stock_helper/industry/sic_buckets.py`): `banking`,
`insurance`, `other_financial`, `real_estate`, `utilities`, `technology`,
`healthcare`, `consumer`, `industrials`, `energy`, `materials`, `communications`,
`other`.

Key exclusions:
- `banking`/`insurance`/`other_financial`: no gross margin, no current ratio, no
  inventory-style working-capital reasoning, interest coverage n/a (interest is
  their business, not a fixed charge burden).
- Bank-specific signals apply **only** to `banking`.

## Implemented signals (v0.1)

| Key | Category | Formula (annual series) | Direction rule | Applies to | Main caveat |
|---|---|---|---|---|---|
| `revenue_growth_yoy` | Growth | `rev[t]/rev[t-1] - 1` | >2% improving, <-2% deteriorating | all except `banking`* | Revenue tag varies by filer; M&A distorts organic growth |
| `operating_margin_trend` | Profitability | `op_income/revenue`, 3y direction | slope of last 3 values | non-financials | Operating income tag inconsistencies; one-offs not stripped |
| `gross_margin_trend` | Profitability | `(rev - cogs)/rev`, 3y direction | slope | non-financials with COGS | Not meaningful for banks/insurers; some filers omit COGS tag |
| `fcf_trend` | Cash flow | `OCF - capex`, 3y direction | slope | non-financials | Capex tag only (excl. acquisitions); lumpy by nature |
| `ocf_vs_net_income` | Quality | `OCF / net_income` (latest) | ≥1 supportive, <0.8 flag | non-financials | Ratio unstable near zero NI; banks' OCF less meaningful |
| `accrual_proxy` | Quality | `(NI - OCF) / total_assets` (latest) | lower is better; >0.10 flag | non-financials | Proxy only (cash-flow approach); refine in Phase 3 v2 |
| `debt_to_assets` | Leverage | `total_debt / total_assets` (latest + trend) | rising = deteriorating | non-financials | Excludes operating leases if untagged; banks n/a by design |
| `interest_coverage` | Leverage | `op_income / interest_expense` (latest) | <2 flag, >8 comfortable | non-financials | Interest expense tag frequently missing → `UNAVAILABLE` |
| `current_ratio` | Liquidity | `current_assets / current_liabilities` (latest) | <1 flag | non-financials that file classified balance sheets | Many filers (and all banks) don't classify → n/a |
| `share_dilution` | Quality | YoY change in diluted share count | rising >2% = dilution flag | all | Splits handled by XBRL values as filed; buybacks offset |
| `buyback_activity` | Capital return | `PaymentsForRepurchaseOfCommonStock` recent years | present/rising | all | Gross repurchases; ignores issuance netting |
| `cash_trend` | Liquidity | cash & equivalents, 3y direction | falling fast = flag | all | Ignores revolver capacity and ST investments |
| `deposits_trend` | Banking | `Deposits`, 3y direction | falling = flag | `banking` only | Face XBRL tag; mix (interest-bearing vs not) invisible |
| `credit_loss_allowance` | Banking | allowance for credit losses level + trend | rising sharply = flag | `banking` only | Tag transitions (CECL, 2020) hurt comparability |

\* For `banking`, revenue growth is `NOT_APPLICABLE` in v0.1 because "revenue"
for banks (net interest income + fees) is not reliably captured by the generic
revenue tags; a bank-specific revenue signal is planned in Phase 4.

## Declared placeholders (not implemented — shown as `PLACEHOLDER`)

| Key | Category | Why deferred |
|---|---|---|
| `valuation_*` (P/E, EV/EBIT…) | Valuation | Needs trustworthy price × share alignment (Phase 5) |
| `momentum_12_1` | Market | Needs canonical price history (Phase 5) |
| `disclosure_risk_language` | Disclosure | Needs Phase 2 text features (risk-factor novelty, tone delta) |
| `nim` (net interest margin) | Banking | Needs interest income/expense + earning-assets averaging (Phase 4) |
| `net_charge_offs`, `npl_ratio` | Banking | Tags inconsistent; often table-only disclosure (Phase 4) |
| `cet1_ratio` | Banking | Regulatory capital often not in face XBRL; filing-table parsing (Phase 4) |
| `industry_relative_percentiles` | Context | Needs sector distributions over a wider universe (Phase 4) |

## Data confidence signal

`data_confidence` is itself reported per company: fraction of canonical metrics
successfully mapped, count of annual periods available, and days since last
filing ingested. Low coverage lowers confidence on *all* interpretations, and the
report says so explicitly.

## How to read a scorecard row

> **Operating margin trend** — `OK` · value `31.2% → 29.8% → 28.4%` · direction
> `deteriorating` · *Evidence suggests operating margin has compressed for two
> consecutive fiscal years.* · Source: us-gaap `OperatingIncomeLoss`,
> `RevenueFromContractWithCustomerExcludingAssessedTax` (accessions listed) ·
> Confidence: high · Caveat: one-time items are not stripped; check MD&A before
> concluding.

The interpretation sentence is the *most* the tool will ever claim.
