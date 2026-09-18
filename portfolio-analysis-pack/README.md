# Portfolio Analysis Pack

**Status: specified, not yet built.** Grilled and PRD'd 18 September 2026.

A Python tool, run at the bank's desk, that takes a loan extract plus a short
YAML question file and emits one self-contained Excel workbook: a fixed
six-step analysis (capture → prevalence → gradient → stratified →
decomposition → model) and a closing control observation. Python does the
work over the loans; the workbook holds only a count cube and derives every
rate, interval and headline word by live formula from it.

- **Spec:** [`docs/prd-portfolio-analysis-pack.md`](docs/prd-portfolio-analysis-pack.md)
- **Running log:** `../BACKLOG.md` §6c (credit line; not `PLAN.md`)
- **Rulings on the record:** `../canon/CONVICTIONS.md`, *Rulings by project*

Belongs to the credit consulting line beside `credit-review-os/` and
`credit-suite/`. Imports nothing from either; copies `keybank_style.py`.
Desk dependencies: Python 3.10+, `openpyxl`, `PyYAML`. Verification here
additionally needs `formulas`, `pytest` and `libreoffice-calc` (the bare
`soffice` in the build container cannot load a workbook without it).
