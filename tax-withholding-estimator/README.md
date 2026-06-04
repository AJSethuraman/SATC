# Tax Withholding Estimator (twe)

A local-first, dependency-free tool that projects your **full-year federal tax
liability** from paystub figures plus extra income, adjustments, deductions, and
credits — then tells you **how much to withhold from each remaining paycheck**.

It answers the everyday question: *"Given my paystub and everything else going
on this year, am I withholding too much or too little, and what should I put on
my W-4?"*

> ⚠️ This is an estimate for planning purposes only. It is **not** tax advice and
> does not replace IRS Form W-4, IRS Publication 505, or a tax professional.

## What it models

- Progressive federal income tax brackets (all four filing statuses)
- Standard vs. itemized deduction (whichever is larger), plus age-65/blind
  additional standard deductions
- Preferential **0% / 15% / 20%** rates for qualified dividends and long-term
  capital gains, correctly *stacked* on top of ordinary income
- **Self-employment tax** (with the one-half-SE above-the-line deduction)
- **Additional Medicare Tax** (0.9%) and **Net Investment Income Tax** (3.8%)
- Above-the-line adjustments (traditional IRA, HSA, student-loan interest, …)
- Nonrefundable and refundable credits (e.g. Child Tax Credit)
- Mid-year projection from year-to-date wages/withholding and remaining pay
  periods
- A per-paycheck recommendation, including a **Form W-4 line 4(c)** extra
  withholding amount, with a configurable **target refund**
- An optional **safe-harbor** calculation (90% of current-year / 100%–110% of
  prior-year tax) to avoid an underpayment penalty

## Accuracy & tax-year data

Tax constants live as JSON under `src/twe/data/<year>.json` (currently **2025**,
from IRS Rev. Proc. 2024-40 and the SSA wage base). To add a year, drop in a new
file — no code changes needed. If you request a year that isn't bundled, the
estimator falls back to the latest available table and says so in its notes.

## Installation

From `tax-withholding-estimator/`:

```bash
python -m pip install -e .[dev]
```

The estimator core has **no runtime dependencies** — only the standard library.
The optional paystub-import feature (see below) needs one extra:

```bash
python -m pip install -e ".[paystub]"
```

## Paystub import (deterministic, learns your layout)

The web UI can read values straight off your paystub — no AI, no network. It is
fully deterministic: the same file and the same saved profile always produce the
same numbers.

How it works:

1. Drop a paystub **PDF** (best) or **image** into the *Import from Paystub* card.
2. The first time it sees a layout, you **map it once**: a window shows the
   paystub with every word boxed; you click a field (e.g. *Federal tax
   withheld*), then click that number on the page.
3. Save it as a named **profile** (per employer / payroll provider). The mapping
   is stored as a label-anchored rule (it finds the row by its label and the
   column by where you clicked), so it keeps working even when amounts change
   week to week.
4. Next time you drop a paystub with the same layout, it's **recognized
   automatically** and the form fills in — review and calculate.

Profiles are plain JSON files under `~/.twe/profiles/` (override with the
`TWE_PROFILE_DIR` environment variable) — portable and inspectable. Use
**Manage saved profiles** in the import card to review, rename, or delete them.

- **PDF paystubs** (downloaded from a payroll portal) have a real text layer, so
  extraction needs only **PyMuPDF** (`pip install ".[paystub]"`; Windows wheels
  included).
- **Image / scanned / photo paystubs** have no text layer, so they additionally
  require the **Tesseract OCR** engine installed and on your `PATH`. If it isn't
  present, the app says so and you can upload a PDF instead.

## Quick start

Estimate straight from a paystub:

```bash
twe estimate \
  --filing-status single \
  --pay-frequency biweekly \
  --gross 3200 --withheld 410 \
  --ytd-wages 35100 --ytd-withheld 4920 \
  --periods-remaining 14 \
  --ira-distributions 5000 --ltcg 2000
```

List bundled tax years:

```bash
twe years
```

## Scenarios with everything (recommended)

For anything beyond a basic paycheck, describe the full scenario in JSON. Write a
template and edit it:

```bash
twe sample --output scenario.json
twe estimate --input scenario.json
```

Add `--json` for machine-readable output, or `--output report.txt` to also save
to a file.

A scenario file looks like this (see `examples/sample_input.json`):

```json
{
  "filing_status": "single",
  "tax_year": 2025,
  "paystub": {
    "pay_frequency": "biweekly",
    "gross_pay_per_period": 3200,
    "federal_tax_withheld_per_period": 410,
    "retirement_pretax_per_period": 160,
    "other_pretax_per_period": 90,
    "ytd_taxable_wages": 35100,
    "ytd_federal_tax_withheld": 4920,
    "pay_periods_remaining": 14
  },
  "other_income": {
    "interest": 350,
    "ordinary_dividends": 800,
    "qualified_dividends": 600,
    "taxable_retirement_distributions": 5000,
    "long_term_capital_gains": 2000
  },
  "adjustments": { "hsa_deduction": 2000, "student_loan_interest": 1200 },
  "deductions": { "itemized_total": null },
  "credits": { "child_tax_credit": 0 },
  "other_payments": { "estimated_tax_payments": 0 },
  "target_refund": 0,
  "prior_year_tax": 8200,
  "prior_year_agi": 71000
}
```

### Input field reference

| Section | Field | Meaning |
| --- | --- | --- |
| (top) | `filing_status` | `single`, `married_jointly`, `married_separately`, `head_of_household` |
| (top) | `tax_year` | Tax year for the tables (defaults to latest bundled) |
| (top) | `target_refund` | Desired refund; `0` = break even |
| (top) | `prior_year_tax` / `prior_year_agi` | Enable the safe-harbor calculation |
| `paystub` | `pay_frequency` | `weekly`, `biweekly`, `semimonthly`, `monthly`, `annual` |
| `paystub` | `gross_pay_per_period` | Gross pay shown on the stub |
| `paystub` | `federal_tax_withheld_per_period` | Federal income tax withheld per check |
| `paystub` | `retirement_pretax_per_period` | Pre-tax 401(k)/403(b) per check (reduces taxable wages) |
| `paystub` | `other_pretax_per_period` | Other pre-tax (health, HSA, FSA) per check |
| `paystub` | `ytd_taxable_wages` | Year-to-date federal taxable (Box 1-style) wages |
| `paystub` | `ytd_federal_tax_withheld` | Year-to-date federal tax withheld |
| `paystub` | `pay_periods_remaining` | Pay periods left this year |
| `other_income` | interest, dividends, `qualified_dividends`, `taxable_retirement_distributions`, capital gains, `self_employment_net`, `spouse_taxable_wages`, `spouse_federal_tax_withheld`, … | Annual amounts |
| `adjustments` | IRA, HSA, student-loan interest, other | Above-the-line, annual |
| `deductions` | `itemized_total` (null = standard), `extra_standard_deductions` | |
| `credits` | `child_tax_credit`, `other_nonrefundable_credits`, `refundable_credits` | |
| `other_payments` | `estimated_tax_payments`, `other_withholding` | Already paid this year |

If you omit year-to-date figures and `pay_periods_remaining`, the estimator
assumes a full year at the current per-paycheck rate.

## Multiple jobs / W-2s

Multiple jobs are the most common cause of under-withholding: each employer
withholds as if its paycheck is your only income, so each applies its own
standard deduction and low brackets. Combined, your income lands in higher
brackets and no single job withholds enough — a surprise bill in April.

In the web UI, click **➕ Add another job / W-2** to add as many jobs as you
have. Each job has its own pay frequency, per-period amounts, year-to-date
figures, and last pay date. The estimator sums them all, computes one combined
liability, and recommends the extra per-paycheck withholding — applied to the
**one job you choose** (the *"Apply the recommendation to this job"* radio).
The paystub importer fills whichever job you pick in the *Fill into* dropdown.

In JSON, use either a `jobs` list or `paystub` + `additional_jobs`. Mark the job
to adjust with `"adjust_withholding": true`:

```json
{
  "filing_status": "single",
  "jobs": [
    {"name": "Main job", "pay_frequency": "biweekly", "gross_pay_per_period": 3000,
     "federal_tax_withheld_per_period": 350, "pay_periods_remaining": 26,
     "adjust_withholding": true},
    {"name": "Side job", "pay_frequency": "biweekly", "gross_pay_per_period": 2000,
     "federal_tax_withheld_per_period": 150, "pay_periods_remaining": 26}
  ]
}
```

Each job also carries an optional `name`. A job you already left this year fits
naturally too — enter its final YTD wages/withholding with `pay_periods_remaining`
set to `0`.

## Use as a library

```python
from twe import estimate, EstimatorInput

result = estimate(EstimatorInput.from_dict({
    "filing_status": "married_jointly",
    "paystub": {"pay_frequency": "monthly", "gross_pay_per_period": 8000,
                "federal_tax_withheld_per_period": 1100, "pay_periods_remaining": 12},
}))
print(result.breakdown.total_tax_liability)
print(result.recommendation.additional_withholding_per_period)
```

## Run tests

```bash
PYTHONPATH=src pytest -q
```

## Limitations

- Federal only — no state or local tax.
- Assumes the primary job's wages are subject to Social Security/Medicare when
  reducing the self-employment SS base; edge cases (multiple W-2s near the wage
  base) are approximations.
- Credit phase-outs (CTC, education, EITC) are **not** modeled — enter the
  credit amount you expect to qualify for.
- Taxable Social Security benefits should be entered already-computed; the
  provisional-income worksheet is not applied.
- Always confirm against the official
  [IRS Tax Withholding Estimator](https://www.irs.gov/individuals/tax-withholding-estimator).
```
