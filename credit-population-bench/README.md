# Consumer Credit Population Analysis Bench

A deterministic **pandas engine behind an `.xlsm` surface** for loan-level
consumer-loan population analysis. A bank credit reviewer loads a flat file,
maps its headers to a canonical-field contract, validates/cleans the population
(with an audit trail), stratifies it (mapped group-bys **and** user-defined
derived cohorts), computes **balance- and count-weighted** portfolio metrics +
URCCP classification + vintage, and draws a documentable **judgmental sample**
for linesheet review.

Spec: [`docs/prd-credit-population-bench.md`](docs/prd-credit-population-bench.md).
Sibling to `credit-review-os` — it **shares** the URCCP thresholds, safe
evaluator, and PII byte-scan rather than forking them.

## Status

Built in vertical slices (GitHub issues #79–#87). In: the full one-button path —
mapping → cleaning gate → weighted metrics (both bases) → delinquency + **URCCP**
(shared floors) → group-by + band schemes → **derived cohorts** (overlap matrix +
residual) → vintage + gross charge-off + conditional roll matrix → **judgmental
sampling + OCC doc** → the emailable **pure-ASCII bundle**.

## Verify

```bash
cd credit-population-bench
python -m pip install pandas openpyxl pytest
PYTHONPATH=src pytest -q                                # full suite
python -m popbench.cli --demo -o /tmp/bench_demo.xlsx   # build the demo workbook

# Emailable transmission (TEMPLATE_CONTRACT §11): one pure-ASCII builder that
# rebuilds the workbook in an empty folder with only pandas + openpyxl.
python make_bundle.py                 # writes build_population_bench.py
# ...email that one file; on the target machine, in an empty folder:
#   python build_population_bench.py  # -> population_bench_demo.xlsx (+ sidecars)
```

The shared URCCP/PII core lives in `../satc_credit_core` (imported at source,
vendored into the bundle). Tests find it via `conftest.py`; the CLI finds it via a
guarded runtime bootstrap.

## Design invariants

- Math is pandas, behind one button; Excel is the load + output (values) surface.
- **Every rate ships on both a dollar basis and a count basis, always labeled.**
- Weighted averages are **balance-weighted by current UPB** (default).
- URCCP thresholds are **imported** from the shared credit-core — never forked.
- **Nothing is computed on a dirty population**: hard errors refuse with a
  per-issue report; only safe, declared normalizations run automatically, each
  recorded on `_cleaning`.
- **Column mapping is confirm-not-silent**: headers are auto-proposed but every
  mapping is reviewer-confirmed and persisted, with units, on `_map`.

## PII boundary

This tool runs only on bank equipment; the **runtime populated workbook may hold
real borrower PII** (no gates — loan number is the file-pull key). The **shipped
tool, repository, and demo fixtures carry zero real PII** (100% synthetic), and a
byte-scan enforces that. See PRD §7.
