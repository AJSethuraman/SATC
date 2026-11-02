# Configured tools, delivered as Excel workbooks

A tool's configuration (the builder's "As data") goes in; a working `.xlsx` comes out. No macros.

**Design: "Paper"** (2 Nov 2026), specified in `../design/paper/` (open `Paper System.html`; its Build sheet is the spec). It replaced a first pass in the owner's linesheet style, which the firm rejected as *"thick rows, thick fonts, super blocky"*. A soft stone ground, lighter paper cards, inset paper-white fields with a small gap between them, flat recessed computed cells, header bars in the tool's colour family (credit navy, reconciliation forest, control test teal; set by `family` in the config), and colour used only for a state: amber required and empty, green complete or within limit, red above limit, grey not applicable. A part-built figure reads *Not calculated*, never $0. Each logical column is a wide column plus a narrow spacer so fields never touch, and two ground gutters split the width into thirds so side-by-side cards float apart.

**Not yet checked:** the files have only been opened in LibreOffice, never Microsoft Excel. The design package says to build one screen in Excel first and check the field gaps and the bevel borders. Not built from the design: the *excluded* state (no configuration uses it yet) and the *Rate this* hint inside an empty rating (Excel cannot show text in an empty cell through formatting alone).

```bash
python3 workpaper-studio/excel/build_tool_workbook.py     # configs/*.json -> out/*.xlsx (blank tool + filled example)
python3 workpaper-studio/excel/check_tool_workbooks.py    # LibreOffice recalculates; 30 checks, read by defined name so the layout can change freely
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
