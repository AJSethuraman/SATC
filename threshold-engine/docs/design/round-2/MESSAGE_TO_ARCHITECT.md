# To the workbook's architect

This is the round 2 design for `consumer-credit.xlsx`, answering `docs/design/BRIEF.md` (round 2). **README.md is the spec**: layouts cell by cell, tokens, formats, conditional formatting, chart styling and calculations. The `.dc.html` file shows the same design running live on the workbook's own data.

## What to build, in order
1. **`keybank_style.py`**: add the new tokens: INPUT_EDGE `D6B656`, REFUSE_BAND `F8E3E1`, MEDIAN `8C877E`, BAND_DARK `CFC8BC`, INTERNAL `2F5D50`, INTERNAL_TINT `E1EAE6`, and the revised rating cell and chart zone colours.
2. **Decide** (`decide_tab.layout()`):
   - Slicers become button rows over B4:Q6. Turn off the table's filter buttons.
   - The Check cell shows OK or Refused. The full reason and "To fix" go in the band at row 116.
   - The chart sits at B119:K136, with its panel beside it in L:Q.
3. **Summary**: two side-by-side panels, KeyBank first, and a "Needs your attention" block.
4. **Peers**:
   - One tab replaces Peers delinquency, balances, lagged, normalisation and mix. Peers pack stays hidden.
   - Charge-offs and delinquency charts side by side, each with a strip of four numbers.
   - Peer A and Peer B can be "Worst in pack" or "Best in pack".
   - "In the pack" is a row of Yes/No cells, so no slicer is needed.
5. **Thresholds**: split Product, Measure and Source into their own columns, and add a Decision column.
6. **Internal and Internal data (new)**:
   - A paste slot (the `InternalData` table) and a one-time name mapping.
   - A coverage grid and a reliability table for each outside source, plus a CRR grade mapping.
   - Add a Glossary entry for every new heading.
7. **Reference tabs**: one quiet template. Fold Peers glossary into Glossary and Peers run into Run.
8. **Tab order and colours**:
   - Work tabs, INK: Decide, Summary, Peers, Thresholds, Internal.
   - Reference tabs, STONE: Evidence, Backtest, Glossary, Sources, Run.
   - Data tabs, MIST: Data, Peers data, Peers delinquency data, Internal data.

## Unchanged
Every formula's meaning, the refusal wording (plus the new "To fix" sentences), decisions kept as one table row per series, no macros, and no images.

## Please confirm with the analyst
- **What the internal CRR extract is.** The design assumes quarterly rates per product and measure, with an optional CRR grade per quarter. If it is loan by loan, add a roll-up feeding `InternalData`.
- **Whether to keep the lagged peer view.** It is below the fold for now and is the next thing to cut.
- **The "Needs your attention" block on Summary uses dynamic-array formulas.** On a build of Excel without them, use the INDEX/SMALL fallback in the README.

## Not to ship
- **Sample internal rows.** The mock's Internal tab is pre-filled with rows made up from KeyBank's Call Report series. They exist only so the view has something to show.
- **Mock-only controls.** The "load sample" and "clear" buttons and the paste box are not part of the workbook.
- **Two placeholder lines on Decide.** "Suggested" and "Unusual stretches" in the mock are placeholders. Keep today's Evidence formulas there unchanged.

## To open the mock
From this folder, run `python -m http.server`, then open `http://localhost:8000/Consumer%20Credit%20Redesign.dc.html`. It needs `support.js` and `data/` beside it. Click the buttons and type in the yellow cells; every view follows.
