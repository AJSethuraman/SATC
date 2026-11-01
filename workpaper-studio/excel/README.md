# Configured tools, delivered as Excel workbooks

A tool's configuration (the builder's "As data") goes in; a working `.xlsx` comes out. No macros.

**Design language** (taken from the owner's own linesheet, 1 Nov 2026): a navy title band with buttons between screens (links, not macros), no gridlines and no row or column headers, a grey canvas, detail panels side by side with labels right-aligned against tinted input boxes, large navy section headings, each question in its own box with a rating box and a large comment box, and supporting analysis on its own screen. Excel is the engine; it should not look like a spreadsheet.

```bash
python3 workpaper-studio/excel/build_tool_workbook.py     # configs/*.json -> out/*.xlsx (blank tool + filled example)
python3 workpaper-studio/excel/check_tool_workbooks.py    # LibreOffice recalculates; 29 checks, read by defined name so the layout can change freely
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
