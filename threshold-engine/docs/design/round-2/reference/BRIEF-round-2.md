# Design brief, round 2: the consumer credit workbook

Paste this whole file into Claude Design, and attach:

- the workbook itself, built by the tool: `consumer-credit.xlsx` (open it in
  Excel and click **Enable Editing** first, or its buttons do nothing);
- the pictures Excel took of it: `docs/walkthrough-book/pictures/*.png` (Summary,
  Decide at three moments, a refused series) and the peer dashboard pictures
  when it lands;
- the walkthrough `docs/walkthrough-book/WALKTHROUGH-BOOK.pdf`, which shows what
  each tab is used for, step by step.

## The ask

Make this workbook look good and read easily, tab by tab. It works: every
number is right and live, and it has been walked through in Excel and tied
out to a bank's filed Call Report. What it does not do yet is look like
something a bank's credit-risk team would be glad to open in a meeting. The
analyst's words this week, in order:

- *"assess one thing at a time, save decisions, not a guide"*
- *"it cannot be a huge list"*
- *"the axis should adjust to fit"*, *"it really needs a way to be smaller and
  it can focus - like maybe the last 48 quarters"*
- *"how do we overlay - like i want to see peer and key and fdic or whatever
  sometimes"*
- *"it is annoying to flip between stuff for peer analysis - can't they all
  exist on one tab with filters like a dashboard at the top?"*
- *"these views look crazy bad formatting-wise, does this have to go to design
  again"* (yes: this brief)

**You may propose a better layout than the one built**, including a different
set of tabs, a different order, or moving something to another tab, if it
serves the analyst better. Say what you would change and why, and where an
idea runs into a constraint below, say so and give the nearest thing that
works inside it. Don't stop at restyling what is there.

Deliver:

1. **Mockups of every visible tab** as Excel draws it at 100% zoom on a
   1920-wide screen: what is above the fold and what is below, in order.
   The tabs, in order of importance: **Decide**, **Summary**, the **Peers**
   dashboard, **Thresholds**; then a light, consistent treatment for the
   reference tabs (Evidence, Backtest, Sources, Glossary, Run, Data, and the
   peer data tabs).
2. **A token sheet** a developer can implement directly: colours as hex,
   fonts (name, size, weight), fills, borders, row heights and column widths in
   Excel units, number formats, slicer style, and chart styling (series colours,
   line widths and dashes, marker sizes, gridlines, axis label formats, where
   the key goes).
3. **For each change, the reason:** what a reader could not do before and can
   now.
4. **Anything you would cut,** and why.

## Who uses it, and for what

A bank's credit-risk analysts set the lines where a risk measure (a net
charge-off rate, a delinquency rate) moves from rating 1 Low to 5 High, for
five consumer products (credit card, mortgage, home equity, other consumer,
auto), seven measures, from three sources (every bank in the industry, a
15-bank peer group, and the bank itself): 105 series. The workbook proposes
lines from each series' own history; the analyst decides, one series at a
time, and the decision is kept in the file. They also compare the bank with
its peers.

## The tabs as built (what each is for)

| Tab | Job | What it has today |
|---|---|---|
| **Summary** | The whole picture on one page: every product and measure, the latest quarter and its rating from each source, and the bank against its peers | A grid, products down, sources across, ratings coloured 1-5; notes underneath |
| **Decide** | Assess and decide one series at a time | Three slicers (product, measure, source) pick one series; under them **one yellow row**: its decision (Accept these lines / Reject), four settings, a period to leave out (from, to, why), a note, and its Check. Under that: a headline sentence; the same product and measure from every source with an **On chart** switch each; a **Chart shows** pick (all, last 80, 48, 20 quarters; 48 at the start); the chart (the series over its five rating zones, other sources as dashed lines); where each rating begins, in words; the Check (OK, or why not and the number that would fix it); what the history suggests (keep every period or leave one out). A count at the top: *Decided: 1 of 105* |
| **Thresholds** | Every series' lines, latest value and rating in one table | One row per series |
| **Peers** dashboard | The bank against its peers, on one tab, with filters at the top (product, measure, Peer A and B, which banks are in, the window) driving every view: rates against the pack, book size, lagged and normalised views, mix | Being built now; the old version spread this over seven tabs that did not follow each other |
| Reference tabs | Evidence, Backtest, Sources, Glossary, Run, Data, peer data | Read rarely; must stay clear |
| Hidden | Assess and Chart hold workings the visible tabs read | Hidden on purpose; can be unhidden |

## Hard constraints (the design has to live inside these)

- **It is generated by code.** Python with `openpyxl` writes the file
  (`src/threshold_engine/workbook.py`, `decide_tab.py`, `summary_tab.py`,
  `peers/peers_workbook.py`, styled through `keybank_style.py`). Anything
  designed must be something openpyxl can write: fills, fonts, borders, number
  formats, row heights, column widths, merged cells (never on input cells),
  conditional formatting (colour scales and formula rules), data-validation
  dropdowns, frozen panes, hidden rows and columns, Excel tables, and native
  Excel charts (line, area, bar/column; stacked or not; combined on one axis).
  **Slicers** are written by the tool's own code (`slicers.py`): single-column
  or multi-column buttons, any built-in slicer style, placed by cell. No images
  are needed and none should be required.
- **No macros.** Banks block them. No buttons that run code, no cell that
  writes another. A control is a cell (or a slicer) whose value formulas read.
- **Decisions live in a table, one row per series**, filtered by the slicers
  so only one shows. That is how a choice is kept per series without a macro:
  it can be restyled and moved, but not replaced by one set of input cells
  that switches with a picker (Excel cannot keep a separate value per series
  in one cell).
- **Rows hidden by the filter hide the whole sheet row.** Anything that must
  stay visible sits outside the table's rows (today: the slicers above it, the
  screen below it).
- **A chart's axis cannot follow a cell**, but its data can be a named range
  (`OFFSET`) that does: that is how Decide's chart fits the window. Line,
  area and column charts are fine; no custom label positions beyond Excel's.
- **Excel 16 on Windows**, fonts installed there: Arial, Calibri, Aptos, Segoe
  UI, Consolas.
- **Live formulas stay; words are facts.** Cells may move (positions are set in
  one place per tab, e.g. `decide_tab.layout()`), labels may be reworded, but
  a refusal still says exactly why, and every heading needs a Glossary entry.
- **Brand.** The KeyBank Excel design system in `keybank_style.py`: INK
  `0A0908`, KEY_RED `CC0000` (accent, sparingly), CRIMSON `960019` (alert
  text), PAPER `FFFFFF`, CANVAS `F4F1EC`, MIST `E4DFD5`, STONE `B9B4AC`, SLATE
  `57534B`, INK_TEXT `16130F`; input cells `FFF2CC`; Arial for display,
  Calibri for data. Tonight's rating colours on Summary and Decide (green
  `D9EAD3` to red `E6A0A0`) were chosen for legibility in a table and may be
  revised. A redesign may extend the tokens; it should not abandon them.
- **Refused is common** with one set of settings for every series (about 40
  of 105 today), so a refused row must look like "needs your attention", not
  like an error.

## What good looks like

- **Decide**: on opening, without scrolling, the three pickers, the yellow row,
  the headline, and the chart. A change and its effect on one screen. Inputs
  look like inputs and nothing else does. A refusal is impossible to miss and
  says what to do.
- **Summary**: readable in a meeting from across a table; the bank's column
  and the ratings that need attention stand out first.
- **Peers**: one tab, filters at the top, every view following them, nothing
  to flip to.
- Charts small enough to sit beside what they explain, focused on recent
  quarters by default.
- The reference tabs are quiet, scannable and consistent with the rest.

## What is in the code for reference

`src/threshold_engine/`: `book.py` (the build file and command),
`decide_tab.py`, `summary_tab.py`, `workbook.py`, `assess_tab.py`,
`peers/peers_workbook.py`, `slicers.py`, `keybank_style.py`, `glossary.py`.
`tests/` says what must stay true. The previous round's brief and hand-off are
`docs/design/BRIEF.md` and `HANDOFF.md`.
