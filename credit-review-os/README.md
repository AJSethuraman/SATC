# Credit Review OS

Config-driven loan-review workpaper builder: a portable per-LOB **program**
config plus a thin per-client **engagement overlay** in, a bank-committee-grade
KeyBank-styled Excel workbook out. PRD: [`docs/prd-credit-review-os.md`](docs/prd-credit-review-os.md)
(landed with SATC PR #59); domain research: `docs/research/credit-review-methodology.md`
at the repo root.

**Status: slice 1 (tracer bullet, issue #60).** The engine builds a `Cover`,
one `LS_<loan_id>` linesheet per loan (the *Identification & exposure* section,
house-styled input cells + live formulas), and the `_config` knob panel from a
C&I program + a synthetic demo engagement. Later slices add rating validation
(#61), the exception engine (#62), the master roll-up (#63), the de-identified
mart + re-ingest (#64), the `_methodology` crosswalk (#65), the no-PII-leak
guard (#66), and encryption-at-rest + CLI (#67).

## Two-layer config

- **Program** (`src/credit_review/programs/<lob>.yaml`) — portable and
  client-agnostic: rating framework (the interagency Pass → Loss spine),
  linesheet sections/rows, `review_mode` (`loan_level` in v1;
  `product_conformance` is schema-reserved for consumer/residential).
  The loader rejects client-specific keys outright.
- **Engagement overlay** (`src/credit_review/engagements/<name>.yaml`) — thin
  and per-bank: client identity, `rating_scale_map` (internal grade →
  regulatory bucket), policy `thresholds` (the `[POL key]` formula targets on
  `_config`), scope, reviewer independence, and the loan list.

## Build the demo

```bash
pip install -e .[test]
python -c "
from credit_review import build_demo_workbook, workbook_bytes
wb, *_ = build_demo_workbook()
open('demo_engagement.xlsx', 'wb').write(workbook_bytes(wb))
"
pytest -q
```

## Principles (binding)

- **Deterministic core.** No network, no clock: same inputs → byte-identical
  workbook (`workbook_bytes` pins zip + docProps timestamps). No LLM anywhere
  in the data path, at any phase.
- **PII.** TINs are stored and shown as **last-4 only** — loaders reject
  full-TIN fields and full-TIN-shaped values. Every fixture in this repo is
  100% synthetic. Real engagements get encryption-at-rest (#67).
- **Live formulas.** Computed cells ship Excel formulas resolved from the
  token grammar (`{row_id}`, `[POL key]`), never precomputed results — the
  workbook, not Python, is the source of truth once the reviewer has it.
