# Example outputs

One finished credit file review (`CR-2026Q3-07`) and a quarter's sample of twelve, all synthetic. Methods and limits are fictional; wording is example text.

| File in `out/` | What it is |
|---|---|
| `CR-2026Q3-07-workpaper.pdf` / `.html` | The signed workpaper: conclusion, findings, every question, supporting analysis, review log, sign-offs |
| `CR-2026Q3-07.xlsx` | The same record with live formulas (cash flow, collateral, debt-to-income, counts) |
| `feed-2026-Q3.csv` | One row per credit, one column per question: what a database loads |
| `CR-2026Q3-07.record.json` | One credit as a full record, every value's state spelled out |
| `rollup-2026-Q3.pdf` / `.html` | The quarter roll-up: results by question, every finding listed |

Rebuild, then check:

```bash
python3 workpaper-studio/examples/build_examples.py
node workpaper-studio/examples/print_pdfs.js
python3 workpaper-studio/examples/check_workbook.py
python3 workpaper-studio/examples/build_showcase.py
```

`check_workbook.py` opens the workbook in LibreOffice, which recalculates every formula, and compares 12 results with independent arithmetic. It was seen to fail when a formula was broken on purpose.

**Honest limit:** these files come from a demonstration script, not from the product's engine. A real build must produce them from the engine, so the screen and the outputs can never disagree.
