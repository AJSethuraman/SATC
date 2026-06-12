# UCPA — Unsecured Consumer Portfolio Asset-Quality Analytics Engine

A reusable credit-review analytics engine for unsecured consumer loan
portfolios (credit cards, personal/installment loans, student loans), built
for independent loan-review / asset-quality consulting work.

**Phase 1 (this delivery): a complete vertical slice on credit cards** —
calibrated synthetic tape generator, data-tier detector, deterministic
metric engine with configurable threshold flagging, formatted Excel
workbook output, and a findings-template stub. The card product module is
the template the other two products implement in Phase 2.

## Determinism mandate

All metric computation is plain, deterministic, unit-tested Python
(pandas/numpy). There are **no LLM/AI calls anywhere** in the computation
or data-generation path, no network access, and no randomness outside a
single fixed, configurable seed in the synthetic generator. The same input
produces byte-identical output on every run; golden-number tests in
`tests/test_metrics_golden.py` enforce this. Non-determinism in a metric is
treated as a defect.

## Quick start

```bash
cd consumer-portfolio-analytics
pip install -e .[dev]          # or: pip install pandas numpy openpyxl pytest

# Full Tier 2 demo: generate -> detect tier -> compute -> export
python -m ucpa.cli --outdir outputs

# Simulate a low-maturity client (Tier 0 snapshot extract)
python -m ucpa.cli --degrade-to 0 --outdir outputs

# Client-specific thresholds
python -m ucpa.cli --config client_thresholds.json --outdir outputs

pytest                          # 56 tests, ~4s
```

Outputs: `outputs/card_review_<tier>_<seed>.xlsx` (primary deliverable) and
`outputs/findings_template_<tier>_<seed>.md` (analyst template).

## Architecture — six layers

| # | Layer | Module | Role |
|---|-------|--------|------|
| 1 | Synthetic generator | `ucpa.generator.card_generator` | Seeded longitudinal monthly panel with correlated deterioration; `ucpa.generator.degrade` strips it to Tier 1/0 |
| 2 | Tier detector | `ucpa.tier_detector` | Classifies a tape as Tier 0/1/2 and lists what is missing for the next tier |
| 3 | Metric engine | `ucpa.engine` + `ucpa.metrics.*` | Computes the full card battery; logs a structured data-gap finding for everything the tier cannot support |
| 4 | Config/test layer | `ucpa.thresholds` + `configs/default_thresholds.json` | Standard-methodology limits per metric, deep-merge overridable per client; flags EXCEPTION/WATCH |
| 5 | Excel output | `ucpa.excel_report` | Formatted workbook: dashboard, card detail (full monthly time-series panel with trend charts), migration matrix, vintage curves, concentration, utilization — with embedded charts |
| 6 | Findings doc (stub) | `ucpa.findings_template` | Structured Markdown template with computed numbers laid out and `[ANALYST TO COMPLETE]` placeholders — interpretive opinions are human-supplied, never generated |

Layers are decoupled: a real client tape (any DataFrame conforming to the
data model below) drops in for the synthetic generator without touching the
engine — `run_review(tape, CreditCardModule(), thresholds)` is the whole
contract.

## Tiered data model

One row per account per month (panel) or per account (snapshot). Money in
dollars; `utilization` is a fraction. Charge-off convention: in the month
an account charges off, `charge_off_flag` flips to 1 and `balance` holds
the amount written off; later rows carry balance 0 and (Tier 2)
`recovery_amount`.

| Tier | Meaning | Fields |
|------|---------|--------|
| 0 | Required minimum | `account_id`, `product_type`, `origination_date`, `as_of_date`, `balance`, `delinquency_bucket` (`CURRENT/DPD30/DPD60/DPD90/DPD120/CO`), `charge_off_flag` |
| 1 | Standard monitoring | + `credit_limit`, `score_band` (`SUPER_PRIME/PRIME/NEAR_PRIME/SUBPRIME`), `payment_status`, **and structurally a monthly longitudinal panel** |
| 2 | Advanced analytics | + `orig_score`, `current_score`, `utilization`, `orig_credit_limit` (line-change history), `recovery_amount`, `original_term_months`/`remaining_term_months` (installment products; N/A for cards) |

A field counts as present when the column exists with at least one
non-null value. Tier detection is product-aware: fields not applicable to
a product (e.g. term for revolving cards) never gate detection. The list
of metrics that could **not** be computed, with the fields that blocked
them, is itself a client deliverable — the data-maturity gap assessment —
and appears on the workbook dashboard and in the findings template.

## Card metric battery (definitions)

| Metric | Min tier | Definition |
|--------|----------|------------|
| Delinquency distribution | 0 | Account/balance mix across buckets at latest month; 30+/90+ DPD balance rates (FRED `DRCCLACBS` convention); monthly trend on panel tapes |
| Portfolio time series | 1 | Consolidated monthly panel: open accounts/balance, originations, balance by bucket, 30+/90+ rates, gross COs, recoveries, annualized CO rate, utilization — with YoY-deterioration headlines (30+ rate YoY change, T12 CO rate YoY change, 12-month balance growth) |
| Migration / roll-rate matrix | 1 | For every consecutive month pair, transitions between buckets, account- and dollar-weighted, row-normalized; charge-off is absorbing; headline current→30 and 30→60 rolls plus 30DPD cure rate |
| Vintage cumulative-loss curves | 1 | Cohort = origination quarter; cumulative gross charge-off $ through each month-on-book / cohort total credit line at origination; recent-vs-seasoned comparison at MOB 12 |
| Concentration | 0 (partial) | Balance shares + HHI by score band (T1), vintage year (T0), line size (T1); blocked dimensions logged as gaps |
| Gross/net charge-off rate | 1 / 2 | Trailing-12-month write-offs (net of recoveries for the net rate) over average open balance, annualized (FRED `CORCCACBS` convention); net requires Tier 2 recovery detail |
| Recovery trends | 2 | Monthly recovery $; cumulative and T12 recovery rates vs gross charge-offs |
| Utilization distribution | 1 | Distribution across utilization buckets; portfolio (dollar-weighted) utilization; balance share >90% utilized; total open-to-buy |
| Line management | 2 | Line-increase events and exposure added; share of increase $ to below-prime; share of increases hitting 30+ DPD within 6 months |

Every metric returns headline scalars (threshold-checkable), detail tables
(exported to Excel), and any data-gap findings.

## Automated observations (deterministic)

After metrics and threshold checks, a rule-based observation layer
(`ucpa.observations`) turns the numbers into templated, auditable
statements of fact — e.g. *"Cohort 2023Q3 shows the highest MOB-12
cumulative loss at 1.71%, versus a median of 0.32% across 22 measurable
cohorts."* Each observation carries a stable rule ID and a severity
(`INFO`/`NOTABLE`/`ELEVATED`); where an observation covers a value that
also has a configured threshold, its severity is escalated to match the
threshold outcome, so the two layers never contradict. Observations are
pure code over computed results (no LLM, no raw-tape access), golden-tested
like every other number, and are explicitly **statements of what the
numbers show** — analytical conclusions remain the human reviewer's, and
the findings template labels them as such. Rules skip silently when their
metrics were blocked by data gaps.

## Threshold layer

`configs/default_thresholds.json` is the firm-standard methodology. A
client JSON file deep-merges over it (only restate the limits you change).
Breach ⇒ `EXCEPTION`; within 10% of the limit on the compliant side ⇒
`WATCH`. Both appear color-coded on the dashboard and in the findings
template.

## Synthetic generator and calibration

`CardGeneratorConfig(n_accounts=4000, panel_start="2019-01", n_months=78,
seed=42)` simulates a monthly delinquency state machine per account over a
6.5-year window, deep enough that every vintage is observed from
month-on-book zero and all year-over-year trend headlines are measurable.
Deterioration is **correlated**, not random: the current→30DPD hazard is
the product of score-band base rates, origination-vintage quality factors
(weak 2022–2023 cohorts, per NY Fed Household Debt & Credit commentary),
a months-on-book seasoning curve, and an idiosyncratic multiplier — so
migration matrices, score-band orderings, and vintage curves look like a
real card book.

Calibration targets (documented in `ucpa/generator/card_generator.py` and
asserted as ranges in `tests/test_generator.py`):

| Aggregate | Target | Source |
|-----------|--------|--------|
| 30+ DPD delinquency rate (balances) | ~3.0% (default config produces ~3.1–3.3%) | FRED `DRCCLACBS`, ~3.05% Q1 2025 / ~3.2% 2024 avg |
| Annualized gross charge-off rate | ~4.0–4.5% (produces ~3.7–4.1%) | FRED `CORCCACBS`, ~3.6–4.2% 2023 → ~4.4–4.7% 2024–Q1 2025 |
| Recoveries / gross charge-offs | ~15–20% | Industry card-recovery rule of thumb |
| Vintage pattern | 2022–2023 cohorts materially weaker | NY Fed Household Debt & Credit report |

The tape is fully synthetic and seeded; the targets are realism goals, not
data lookups — nothing downloads anything at runtime.

## Testing

- `test_generator.py` — seed determinism (same seed ⇒ identical frame),
  correlation structure (band ordering, weak vintages), FRED calibration
  ranges, charge-off conventions.
- `test_tier_detector.py` — tier classification, degrade function,
  missing-field reporting, all-null columns.
- `test_metrics_correctness.py` — hand-computed expected values on a tiny
  toy panel (proves the definitions, not just stability).
- `test_metrics_golden.py` — golden numbers on a seeded fixture (proves
  run-to-run stability to 1e-12).
- `test_thresholds.py` — config merge/override, EXCEPTION/WATCH bands.
- `test_end_to_end.py` — generate → degrade → detect → compute → export at
  all three tiers; Phase 2 stubs raise `NotImplementedError`.

## Phase 2 (not in scope here)

`PersonalLoanModule` and `StudentLoanModule` define only the
`ProductModule` interface (`ucpa/products/base.py`). Implementing them
means: an installment generator, term-aware tier fields (already modeled),
and a metric battery following `CreditCardModule` as the template.
