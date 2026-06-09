# EDGAR Industry Assumption-Set Tool

A reusable, fully-local command-line tool that derives **credit-relevant
industry benchmark RANGES** from SEC EDGAR public-company XBRL data, broken out
**by revenue tier**, for use as a *calibrated reference* when analyzing
**private middle-market borrowers** — not as a direct comp, and not as a
hurdle the borrower must clear.

> The output is the **distribution across size tiers**, never a bare average.
> Every output carries the standing caveats (size distortion, survivorship
> bias, accounting differences) attached to the numbers.

## Why tiers, not a single "industry number"

Public companies are systematically healthier than private middle-market
names. Rather than hide that, the tool reports each metric **by revenue tier**
so you can see how leverage tolerance, margins, and volatility shift as size
drops — and extrapolate the trend *below the smallest public tier* toward your
borrower. The cross-tier trend is itself a key output.

## Quickstart (one command)

Requires Python 3.9+. The launcher creates a virtualenv, installs the tool,
asks once for the contact email SEC requires, and runs it — re-runs are instant.

```bash
cd edgar-assumptions

# macOS / Linux
./run.sh --sic 5140 --years 7 --out food_dist

# Windows
run.bat --sic 5140 --years 7 --out food_dist

# or, with make:
make run ARGS="--sic 5140 --years 7 --out food_dist"
```

Run it with **no arguments** the first time to set everything up and execute the
self-test:

```bash
./run.sh          # sets up venv, installs, prompts for email, runs --self-test
```

The contact email is saved to `.edgar_contact` (git-ignored) and reused
automatically; you can also set `EDGAR_USER_AGENT` instead, or pass
`--user-agent` explicitly.

### Manual install (if you prefer)

No third-party runtime dependencies — pure Python standard library.

```bash
pip install -e .
python edgar_assumptions.py --sic 5140 --years 7 --out food_dist \
    --user-agent "Your Name, Your Firm, you@example.com"
```

SEC **requires** a descriptive `User-Agent` with a real contact email; the tool
refuses to run without one. It throttles to stay under SEC's ~10 req/sec limit.

### CLI arguments

| Arg | Default | Meaning |
|---|---|---|
| `--sic` | (required) | One or more SIC codes. |
| `--years` | 5 | Lookback window in fiscal years (e.g. 7 for cyclicality). |
| `--tiers` | `0-250M,250M-1B,1B-5B,5B+` | Revenue tier boundaries (USD; K/M/B/T suffixes). Companies are **assigned** to tiers — never screened out by size. |
| `--min-sample` | 10 | Per-tier minimum company count. Tiers below this are flagged **LOW CONFIDENCE** (reported anyway). |
| `--out` | (required) | Output base path; writes `<out>.csv` and `<out>.summary.md`. |
| `--user-agent` | — | SEC-required contact string (must contain an email). |
| `--cache-dir` | `.edgar_cache` | Local cache of raw EDGAR responses. |
| `--sleep` | 0.15 | Min seconds between requests (throttle). |
| `--offline` | off | Use only cached data; never hit the network. |
| `--self-test` | off | Run the end-to-end pipeline against known CIKs and exit. |

### Self-test first

```bash
python edgar_assumptions.py --self-test --user-agent "...you@example.com"
```

Runs the full fetch → extract → metric pipeline against a couple of known CIKs
(a large- and a mid-cap distributor) and verifies EBITDA reconstructs and
metrics compute before you commit to a slow full-industry scan.

## What it computes

Per company, per available fiscal year (from XBRL `us-gaap` concepts):

- **Leverage & coverage** — Total debt/EBITDA; Total debt/assets; EBITDA/interest; (EBITDA−capex)/interest.
- **Margins & profitability** — gross, EBITDA, operating, net margin; return on assets.
- **Working capital & liquidity** — current & quick ratio; DSO; DIO; DPO; cash conversion cycle.
- **Cyclicality** — through-cycle coefficient of variation per metric, aggregated; the 2020 shock surfaced explicitly when in-window.

**EBITDA is not an XBRL tag** and is reconstructed:
1. `OperatingIncomeLoss + D&A` (preferred), else
2. `NetIncomeLoss + Interest + IncomeTax + D&A`.

The method used is recorded per company-year (`ebitda_method` column). If D&A
is missing, EBITDA-based metrics for that company-year are recorded as missing
— **never imputed**.

## Output

- **`<out>.csv`** — one row per company / fiscal year with every raw line item,
  reconstructed EBITDA (+ method), assigned tier, and all computed metrics.
  This is the audit trail.
- **`<out>.summary.md`** — per SIC code: per-tier percentile tables
  (10/25/50/75/90), sample sizes (companies and company-years), through-cycle
  volatility, the 2020 shock, the cross-tier size trend, a data-quality report,
  and the standing caveats block — printed every time. A loud **LOW
  CONFIDENCE** banner appears for any thin tier.

## Determinism & reproducibility

- **Fully local and deterministic.** No LLM calls, no randomness. Same inputs +
  same cache ⇒ **byte-identical** outputs. All collections are sorted before
  output.
- Raw API responses are **cached** under `--cache-dir`; re-runs read from cache
  and don't re-hit EDGAR.
- The **EDGAR data vintage** (date first pulled) is recorded per cached
  resource and printed in the output, so a run is reproducible from cache
  regardless of when it is re-executed.
- Missing/malformed XBRL is **dropped and logged with a reason**, never
  silently imputed. Each run prints a data-quality report (attempted / usable
  per tier / dropped & why).

## EDGAR endpoints used

- Company universe: `https://www.sec.gov/files/company_tickers.json`
- SIC + names: `https://data.sec.gov/submissions/CIK{10-digit}.json`
  (`sic`, `sicDescription`)
- Financials: `https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit}.json`

There is no single SIC→company endpoint, so the universe is built by scanning
the tickers file and cross-referencing each company's `submissions` SIC. The
**first** scan for a given cache is slow (thousands of throttled requests);
subsequent runs are fast and offline-capable because everything is cached.

## Module layout

```
edgar_assumptions.py     # thin entry point
satc_edgar/
  cli.py        # argument parsing + orchestration
  fetch.py      # throttled, cached EDGAR REST client
  concepts.py   # priority-ordered us-gaap tag mappings
  metrics.py    # per-company-year extraction + metric computation + EBITDA
  aggregate.py  # revenue tiering, percentile distributions, cyclicality
  output.py     # auditable CSV + readable markdown summary + caveats
  selftest.py   # end-to-end pipeline check against known CIKs
tests/          # offline fixture-based tests (no network)
```

## Tests

```bash
pip install -e ".[test]"
pytest -q
```

Tests run entirely offline against synthetic EDGAR-shaped fixtures, including a
determinism check that two independent runs produce byte-identical files.

## Reading the numbers responsibly

These are public-company distributions. Even the smallest public tier skews
healthier than private middle-market borrowers (size, survivorship, and
accounting biases all push the same direction). Treat the ranges as a
**sanity-check band** and trust the **cross-tier trend** more than any single
tier's level.
