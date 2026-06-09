# Commercial Credit Benchmark Workbench — Methodology Memo

*Prepared for an independent credit-risk-review (challenge) function. Version
v1, pipeline `ccbw 0.1.0`. This memo documents how the benchmark library is
built, every judgment call embedded in it, its known weaknesses, and how to
refresh it. It is written to be handed to whoever challenges the challenge
function.*

---

## 1. Purpose and architecture

The workbench supports source-anchored review of line-of-business credit
rationale for **private middle-market borrowers**. Public (EDGAR) data is
used **only to build industry benchmarks and assumption sets — never as a
direct comp** for a private name.

Two cleanly separated components:

1. **Python pipeline (`pipeline/`)** — pulls and parses SEC EDGAR XBRL
   filings into a normalized annual financial panel with per-datapoint
   provenance, builds per-segment / per-size-bucket benchmark distributions,
   applies the size-distortion & survivorship adjustment layer, and runs the
   validation backtest. Output: a **versioned snapshot JSON**.
2. **React workbench (`workbench/`)** — a single-file artifact that consumes
   a baked-in snapshot. Borrower overlay, raw-vs-adjusted exploration, and
   memo export happen here; no analytics are computed that are not also in
   the pipeline (the borrower ratio code mirrors `overlay.py`).

The snapshot is the contract: refreshing benchmarks = re-run pipeline →
re-bake. No GUI changes.

## 2. Data source and acquisition

- **Endpoints** (free, keyless): `companyfacts`, `companyconcept`, `frames`
  under `https://data.sec.gov/api/xbrl/...`, plus the bulk ticker file and
  the `submissions` endpoint for SIC codes. A descriptive `User-Agent`
  with contact email is mandatory; the client enforces SEC's ~10 req/s
  fair-access limit, retries transient failures with exponential backoff,
  and caches responses on disk so large pulls are resumable.
- **Values are raw units** (a company reporting $1.2bn revenue reports
  `1200000000`); no thousands/millions scaling is ever inferred. Facts in
  units other than the expected one (USD) are **rejected with a note**, not
  converted.
- **Usable history starts ~2010**: XBRL was phased in 2009–2011. The
  pre-2020 baseline (FY2015–FY2019) sits comfortably inside reliable
  history.

### 2.1 Tag fragmentation

Filers tag the same concept differently (`Revenues` vs.
`RevenueFromContractWithCustomerExcludingAssessedTax` vs. `SalesRevenueNet`,
etc.). Every concept carries an **ordered fallback chain** (`tags.py`); the
parser walks the chain, records **which tag actually supplied each value**
in provenance, and notes when (a) a fallback was used or (b) different years
were filled from different tags (cross-tag basis caution).

### 2.2 Duplicates, amendments, restatements

CompanyFacts returns one row per filing that mentioned an amount — the
original 10-K, the comparative column of next year's 10-K, and any 10-K/A.
Dedupe key is the **period identity** `(tag, unit, start, end)`; the **most
recently filed value wins** (restatements supersede originals; same-day ties
prefer the amended form). Superseded values are retained on the record for
audit, and the supersession count appears in provenance.

### 2.3 Fiscal-year alignment

Facts are assigned a fiscal-year **label**: the calendar year the period
ends in, unless it ends January–May, in which case the prior year (a
Jan-2024 FYE is FY2023 — the same economic year as a Dec-2023 FYE). Raw
period dates remain in provenance. Annual values are duration facts of
330–400 days, preferring annual forms (10-K/10-K/A/20-F/40-F); balance-sheet
facts are taken at the company's inferred fiscal year ends.

### 2.4 Derivations with disclosed ambiguity

- **Total debt** = noncurrent LTD + current debt, assembled from available
  tags without double counting (`DebtCurrent` preferred over summing its
  components). Where only the combined `LongTermDebt` tag exists, it is used
  **with a flagged basis ambiguity** (filer practice varies on including the
  current portion). No debt tags at all → a **gap**, not a zero: debt-free
  and untagged are indistinguishable in XBRL.
- **EBITDA** = operating income + D&A, **no addbacks**. Public data cannot
  support consistent addback identification. This is a standing basis
  difference vs. sponsor-adjusted private EBITDA: the borrower's
  lender-normalized EBITDA will look *better* than the same company measured
  on the benchmark basis. Missing D&A → EBITDA approximated by operating
  income with an "understated" note.

## 3. Segment taxonomy (no generic ruleset)

| Segment | Peer set | Key normalization | Cyclicality treatment |
|---|---|---|---|
| Middle-market C&I | SIC 2000–3999 (ex pharma/devices/food), 5000–5199, 7300–7399 | Standard EBITDA; trade working-capital cycle | 3-yr volatility reported; pre-2020 anchor |
| CRE operating cos. | SIC 6500–6599, 6798 (REITs/operators) | **Debt/assets primary** (book-LTV logic); trade-cycle metrics suppressed; REIT FFO/EBITDAre vs. private NOI comparability note on every cell | Long occupancy/rate cycles; 5-yr trend; post-2020 office stress makes the pre-2020 baseline mandatory context |
| Healthcare (providers/services) | SIC 8000–8099 | **Rent-adjusted leverage (debt + 8× rent)/EBITDAR** where rent disclosed; DSO as reimbursement-stress channel | Policy/event risk over macro cycle; trend breaks weighted over levels |
| Agribusiness | SIC 0100–0999, 2000–2099, 5150–5159 | **Through-cycle leverage (3-yr avg EBITDA)** beside spot; inventory seasonality basis notes | High, 3–5 yr commodity cycle; spot ratios never judged alone |
| Leveraged / ABL-adjacent | Financial-profile screen: ≥4.0× leverage on positive EBITDA, or AR+inventory ≥35% of assets | Net leverage; FCC proxy (EBITDA−capex)/interest; CCC as borrowing-base proxy; revolver availability **not observable — standing gap** | Coverage thresholds tightened rather than leverage levels; volatility reported with every leverage stat |

A company can inform multiple peer sets (a levered distributor is both C&I
and leveraged/ABL) — intended, as it would be in a real reference universe.

## 4. Size buckets and the bucketing rule

EBITDA bands per private-credit convention: **LMM $5–25M, CMM $25–100M,
UMM $100–300M**, plus a `large` (> $300M) context-only band that is never a
private comp.

**Bucketing is by the company's *median* EBITDA across its panel years**,
not the single-year EBITDA. Rationale: with year-by-year bucketing, a large
company whose EBITDA collapses *migrates into* a smaller band and poisons
that band's distribution with distress — a $200M-EBITDA name fallen to $40M
is a distressed UMM credit, not a CMM peer. The deterioration stays visible
in the company's own band and in the backtest. (This was observed concretely
during build: year-bucketing produced a CMM C&I cell with 1.2× median
coverage and −11% median growth — a distressed cohort, not a peer set.)

**Expect the LMM band to be thin.** Public companies skew large; the
snapshot reports `n_companies` per cell and emits coverage-gap notes
(n < 8 thin; n < 3 percentiles suppressed entirely). Thin-band cells say so
on their face and in every exported memo.

## 5. Benchmark statistics

- Percentiles p10/p25/p50/p75/p90 (linear interpolation), per
  (segment × bucket × metric × fiscal year), with n on every cell.
- **Pre-2020 baseline**: pooled FY2015–FY2019 company-year observations —
  the historical anchor for judging whether a current reading is normal.
- **Trend**: last 3 fiscal years of medians + IQR.
- **Winsorization**: observations are clamped at documented analytic bounds
  per metric (e.g., leverage [0, 15×], coverage [−5, 30×]) so distressed
  names *stay in the distribution* without destroying the tails (a 30×
  multiple on near-zero EBITDA is real distress but meaningless as a tail
  value). Clamp counts are disclosed per cell.
- **Negative-EBITDA leverage is NaN**, graded max-severity downstream rather
  than entering distributions.
- Every cell carries: basis string (period basis, dollar-vs-unit,
  derivation), direction metadata, sources line (observation counts +
  pointer to per-datapoint provenance), and coverage gaps.

## 6. The adjustment engine (the contestable core)

**Problem:** the EDGAR universe is public companies — far larger than
private middle-market borrowers, and survivors (failed/acquired firms drop
out). Raw public benchmarks therefore overstate stability, overstate
achievable margins at MM scale, and understate how quickly small borrowers
deteriorate at a given leverage.

**Three transformations, per size bucket** (raw → adjusted; raw always
shown beside adjusted):

1. **Dispersion widening** — percentile distances from the median scaled by
   a bucket multiplier (LMM 1.40, CMM 1.25, UMM 1.10, large 1.00). Smaller
   borrowers carry more idiosyncratic risk (customer concentration, key
   person, geography); public dispersion is a lower bound.
2. **Median shift** — margins haircut (LMM −2.0pp, CMM −1.0pp, UMM −0.5pp);
   coverage medians shifted (LMM −0.50×, CMM −0.25×, UMM −0.10×) reflecting
   wider private-credit pricing at smaller scale.
3. **Survivorship tail extension** — the risky-side tail (p90 for
   higher-is-riskier metrics, p10 for lower-is-riskier) pushed out by a
   fraction of IQR (LMM 20%, CMM 12%, UMM 6%): the censored left-tail
   companies lived there.

**These parameters are judgment calibration, not estimates.** They are
deliberately exposed: published in the snapshot
(`adjustment_params`, with per-bucket rationale), repeated in the GUI's
detail drawer and in every exported memo, and tunable in one place
(`adjust.py:DEFAULT_PARAMS`). A reviewer who disagrees with 1.40× LMM
widening should change it and re-bake — the point is that the disagreement
happens about an explicit number, not a buried assumption. No private-side
dataset exists (publicly) to fit them against; see §8 limitations.

## 7. Borrower overlay

- Borrower figures (1–3 fiscal years, lender-provided, $M inputs) produce
  the same ratio set as the panel, with segment suppressions applied.
- **Grading** against the adjusted distribution (raw view selectable):
  beyond p75 risky-side = `watch`, beyond p90 = `departure`, beyond p90 +
  0.25×IQR (the survivorship-extended zone) = `severe`. Symmetric on
  p25/p10 for lower-is-riskier metrics.
- **Departure-vs-normalization framing** (requires ≥2 years): outside the
  band and the gap to peer median is widening → *structural departure*;
  narrowing → *normalization toward baseline*; static (<10% relative move)
  → *persistent structural departure*; single year → explicitly *unknown
  trajectory*, with an instruction to obtain history. The delta is never
  reported bare.
- **Mechanism notes** (metric × segment) explain the commercial-credit
  channels that usually move the number and what to verify — e.g., rising
  provider DSO → payor-mix/denials/recoupment; lengthening CCC in an ABL
  name → borrowing-base squeeze from both sides.
- Missing borrower inputs that block a segment-primary metric are surfaced
  as **unverified primary metrics**, in the GUI and the memo.

## 8. Validation (Stage 5)

### 8.1 Design

Private-middle-market default data is not publicly pullable, so validation
is **directional, against public proxies** — never claimed as calibration:

- **Deterioration event** (public proxy for migration to non-accrual):
  within 3 years of the flag, any of — interest coverage < 1.0×, EBITDA
  down ≥ 40% from flag year, Altman Z′ newly in distress zone (< 1.23), or
  negative book equity.
- **Established failure models as references**: Altman **Z′
  (private-firm variant, book equity)** — chosen over the original Z
  because the user's borrowers are private; **Ohlson O-score** (size term
  substituted with log total assets in $M — ordering preserved, levels not
  calibrated PDs, disclosed); **Beaver** CFO/total liabilities. The
  workbench flag is required to beat the Z′-distress reference on
  precision while leading it in time.
- **Rating-study expectation**: issuers typically migrate through CCC/C
  over 1–3 years before default — a useful flag must *lead* distress by
  ≥ 1 year, not coincide with it. Median lead time is judged against that
  bar.

### 8.2 Flag-rule refinement

Candidate rules are re-evaluated on **every** backtest run and published in
the validation report, so the refinement evidence regenerates with the
data. On the current snapshot (synthetic corpus, FY2017–FY2021 flag years,
3-year horizon, base deterioration rate 14.5%):

| Rule | Flagged | Hit rate | Capture |
|---|---|---|---|
| **Production: any severe \| core departure** | 159 | **30%** | **40%** |
| Core departure only | 13 | 77% | 9% |
| Loose: core departure \| ≥2 watch+ (rejected) | 354 | 20% | 61% |
| Core departure \| ≥2 watch+ incl. core | 108 | 31% | 28% |
| Altman Z′ distress (reference) | — | ~15% | — |

The loose rule was rejected: flagging ~44% of all company-years for a hit
rate barely above base is an operationally useless review queue. The
production rule (any `severe` reading, or `departure`+ on leverage or
coverage) roughly doubles the Z′ reference's precision at a **median lead
time of 2 years**, consistent with the rating-study bar. Precision/capture
is an operator tradeoff; the comparison table exists so the operator can
re-choose deliberately.

### 8.3 What the demo validation does and does not show

The shipped backtest runs on the **synthetic corpus** (see §9): it
validates the *machinery* — that flags graded against adjusted
distributions fire 1–3 years ahead of engineered multi-year deterioration
paths, and that thresholds are neither inert nor hair-trigger. It does
**not** validate calibration to real markets. After a live refresh the
identical harness reports real hit rates against real public
deteriorations. The BDC-based check (sector-average non-accrual rates from
public BDC filings as a private-MM stress anchor) requires live EDGAR plus
footnote parsing (non-accruals are not standard XBRL tags) and is left as a
documented refresh-path extension.

### 8.4 Standing limitations (also stamped into outputs)

1. **Public-proxy substitution**: deterioration events are
   public-financials proxies, not observed private defaults. Directional
   check, not calibration.
2. **Survivorship in the backtest itself**: companies that delist or are
   acquired truncate the horizon and bias hit rates downward.
3. **Accounting-only signal**: market-based measures are known to add
   default-predictive power beyond ratios; working from financials alone
   is a structural ceiling.
4. **Size distortion**: even adjusted distributions inherit public-company
   composition; the adjustment layer is judgment, not estimation.
5. **EBITDA basis**: benchmark EBITDA is addback-free; lender-normalized
   borrower EBITDA flatters the borrower relative to peers.
6. **Point-in-time balances**: DSO/DIO/DPO use year-end balances over
   full-year flows; seasonal businesses distort (noted per segment).

## 9. The synthetic-data condition (this snapshot)

This build environment had **no network access to `data.sec.gov`** (host
allowlist). Therefore:

- The pipeline is fully built and tested for live EDGAR (client, tag
  chains, dedupe, the lot — 110 tests including malformed-filing,
  restatement, unit and fiscal-alignment cases).
- The shipped snapshot was generated from a **deterministic synthetic
  corpus shaped exactly like CompanyFacts JSON** and ingested through the
  same parse → panel → benchmark path live data takes. The corpus
  deliberately reproduces EDGAR's messiness (tag variants, comparative-
  column duplicates, 10-K/A restatements, missing line items, off-calendar
  FYEs, a non-USD unit trap, survivor-skewed size mix, ~16% engineered
  deterioration cohort).
- **Every level in the snapshot is illustrative.** The snapshot metadata,
  the GUI banner, and every exported memo carry this caveat; the pipeline
  enforces the banner whenever `data_source != EDGAR_LIVE`.

## 10. Refresh runbook

On any machine that can reach `data.sec.gov`:

```bash
cd pipeline
pip install -e .[dev] && python -m pytest          # should be all green
python -m ccbw build-live \
    --user-agent "Your Name you@bank.com" \
    --out ../data/benchmark_snapshot_v2.json \
    --validation-out ../data/validation_report.md \
    --bake ../workbench/CreditBenchmarkWorkbench.jsx
# universe: omit --ciks to enumerate all registrants (long; cached &
# resumable), or pass --ciks for a curated list
python ../workbench/make_html.py                    # regenerate the .html
```

Then: bump the snapshot version, diff the validation report against the
prior run (hit rate, capture, lead time, rule comparison), revisit the
adjustment parameters against the new raw distributions, and re-run the
workbench smoke test (`workbench/tests/`). Quarterly refresh is adequate;
the pre-2020 baseline is fixed by construction.
