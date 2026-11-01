# Configured tools, delivered as Excel workbooks

A tool's configuration (the builder's "As data") goes in; a working `.xlsx` comes out. No macros.

```bash
python3 workpaper-studio/excel/build_tool_workbook.py     # configs/*.json -> out/*.xlsx (blank tool + filled example)
python3 workpaper-studio/excel/check_tool_workbooks.py    # LibreOffice recalculates; 28 checks against independent arithmetic
```

| Sheet | What it does |
|---|---|
| **Workpaper** | The tool. Yellow cells are inputs, grey cells are worked out. Each section shows its status (Complete, N missing, Not applicable, Optional) and “Ready for review” sits at the top |
| **Check** | The release check, one line per section and per limit, each saying what to do |
| **Settings** | Limits belong to the organization. Until one is confirmed, nothing is tested against it |
| **Framework** | The questions and how to test each. The Workpaper reads its question wording from here |
| **Lists** | Every dropdown reads from these named lists |
| **Record** | One row for the database, built by formulas from the Workpaper |

Behaviour, all by formula: dropdowns from the organization's lists; sections and single questions that grey out and read “Not applicable” when an answer says so, keeping what was typed; “Waiting on an answer” when the deciding answer is blank; comments required only for the ratings that need them; calculations that say “Not calculated” rather than showing a number from missing inputs; sheet protection without a password so formulas are not typed over by accident.

Configs: `credit-file-review.json`, `control-test.json`, `bank-reconciliation.json`. All synthetic; methods and limits are fictional; wording is example text.
