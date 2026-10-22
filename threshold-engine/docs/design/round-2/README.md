# Handoff: consumer credit workbook, design round 2 (with the Internal CRR check)

## Overview
This is a redesign of `consumer-credit.xlsx`, the workbook the threshold engine generates. It covers every visible tab: Decide, Summary, Peers, Thresholds, the new **Internal** tab and its **Internal data** slot, and the reference tabs. It answers the round 2 brief (`docs/design/BRIEF.md`, round 2): a change and its effect on one screen, a refusal that says what to do, Peers on one tab, and charts focused on recent quarters. It also adds the last step of the job: checking the bank's own CRR data against the outside series, to see how far each outside source can be trusted for setting lines.

## About the design files
`Consumer Credit Redesign.dc.html` is a **design reference built in HTML**. It is not code to ship. It draws each tab as Excel 16 does at 100% zoom on a 1920 × 1080 screen with the ribbon open, cell for cell, and runs live on the workbook's own Data and Peers data tabs (extracted to `data/*.json`). The task is to recreate it in the **existing generator**: Python, openpyxl, `keybank_style.py`, `decide_tab.py`, `summary_tab.py`, `peers/peers_workbook.py`, `slicers.py`, plus a new `internal_tab.py`. Everything here stays inside the brief's hard constraints: no macros, no images, no merged input cells, and decisions kept in a table.

To view it, serve the folder (for example `python -m http.server`) and open the `.dc.html` file. It needs `support.js` and `data/` beside it.

## Fidelity
**High fidelity.** Colours, fonts, row heights, column widths, number formats and chart styling are final. Pixel widths convert to Excel units as `(px − 5) / 7` (Calibri 11). Row heights convert to points as `px × 0.75`.

## Tab set and order
Work tabs, tab colour INK `0A0908`: **Decide, Summary, Peers, Thresholds, Internal**.
Reference tabs, STONE `B9B4AC`: Evidence, Backtest, Glossary, Sources, Run.
Data tabs, MIST `E4DFD5`: Data, Peers data, Peers delinquency data, **Internal data**.
Hidden: Assess, Chart, Peers pack.
Removed as tabs: Peers delinquency, Peers balances, Peers lagged, Peers normalisation and Peers mix (folded into the Peers dashboard); Peers glossary and Peers run (become second sections of Glossary and Run).

---

## Decide (`decide_tab.layout()`)
**Columns (px → units):** A 16 → 1.57 · B 120 → 16.43 Product · C 150 → 20.71 Measure · D 130 → 17.86 Source · E 130 → 17.86 Decision · F, G, H 84 → 11.29 (the three settings) · I 74 → 9.86 On a line · J, K 80 → 10.71 Leave out from, to · L 200 → 27.86 Why left out · M 220 → 30.71 Note · N 110 → 15.00 Check · O, P 100 → 13.57 · Q 106 → 14.43.

**Rows (pt):**
- Row 1, 25.5 pt: title, and "Decided: n of 105 · accepted a · rejected r" right-aligned from L.
- Row 2, 15 pt: subtitle, with a medium KEY_RED bottom border.
- Row 3: 6 pt.
- Rows 4–6, 19.5 pt each: slicers.
- Row 7: 6 pt.
- Row 8, 27 pt: table header.
- Rows 9–113, 34.5 pt each: the decision table, one row per series, in order product × measure × source. The slicers hide all but one row.
- Row 114: 7.5 pt.
- Row 115, 30 pt: headline.
- Row 116, 25.5 pt: Check band.
- Row 117: 7.5 pt.
- Row 118, 16.5 pt: section headings.
- Rows 119–136, 16.5 pt: chart (left) and panel (right).
- Below the fold: row 138 "What the history suggests" with rows 139–141; row 143 "What each setting does" with rows 144–147; rows 149–150, one-line notes on reading the chart.

**Slicers** (`slicers.py`, style `SlicerStyleOther2`, caption on, button height 0.25 in):
- Product over B4:D6, 3 columns.
- Measure over E4:L6, 4 columns.
- Source over M4:Q6, 3 columns.

**Table:**
- Header: Arial 9 bold PAPER on INK, wrapped. Turn off the filter buttons (`autoFilter` hidden / Table Design › Filter Button off); the slicers still filter.
- B–D: read-only, Calibri 11 SLATE.
- E–M: input cells with fill `FFF2CC` and a thin border `D6B656`, bold for numbers and picks. E is a list: Not decided / Accept these lines / Reject. I is a list: worse / better. J and K are lists of every quarter.
- N shows only `OK` (SLATE), or `Refused: see the fix below` (CRIMSON bold on CANVAS).

**Headline, row 115:**
- B:H holds the sentence "KeyBank, nonaccrual, credit card: 0.69% in 2026Q2" (Arial 14 bold).
- I:K holds the rating chip: the rating fill, or CANVAS + CRIMSON "No rating: see the Check".
- L:Q holds "KeyBank is 0.68 points higher than Peer group (15 banks)." (SLATE).

**Check band, row 116 (B:Q merged; it is not an input):**
- OK: CANVAS fill, "Check: OK, your settings fit this series." (Arial 12 bold INK).
- Refused: fill `F8E3E1`, top and bottom borders CRIMSON. "Refused: <reason>" in CRIMSON, then "To fix: <sentence>" in INK.

**Chart, B119:K136 (1016 × 396 px):** see the chart tokens below. Its title in B118 reads "The history over the five rating zones · last 48 quarters" (follows Chart shows).

**Right panel, L118:Q136:**
- Rows 119–124, "Where each rating begins": Rating (filled with its rating colour), Begins at, Quarters kept, Share, and a "◀ latest" marker.
- Rows 126–130, "Same product and measure, every source": the source name in its line colour, rating, latest value, decision, and On chart (an input list No/Yes; the picked source shows "Picked").
- Row 131: Chart shows (input list: Last 20 / 48 / 80 quarters / Every quarter).
- Rows 133–136: Median kept, Typical yearly move, and Worst quarter kept with its quarter.

## Summary (`summary_tab.py`)
Two side-by-side panels, each 9 columns:

| Column | Holds | px | Units |
|---|---|---|---|
| B | Product | 124 | 17.0 |
| C | Measure | 212 | 29.6 |
| D | KeyBank latest | 62 | 8.1 |
| E | KeyBank rating | 130 | 17.9 |
| F | Points vs Peer | 58 | 7.6 |
| G | Peer latest | 52 | 6.7 |
| H | Peer rating | 110 | 15.0 |
| I | Industry latest | 52 | 6.7 |
| J | Industry rating | 110 | 15.0 |

Then a 24 px gutter in K, and L–T repeat the same nine columns.
- Left panel: Credit card, Mortgage, Home equity (21 rows). Right panel: Other consumer, Auto (14 rows), then a blank row and the "Needs your attention · KeyBank" block (the 4s and 5s by rating, then the refused count).
- Rows 6–26 are 19.5 pt; body Calibri 13 (KeyBank bold), measure Calibri 11, peer and industry columns Calibri 11 SLATE. Row 4 holds the group headers: KeyBank on INK with a KEY_RED top border; Peer and Industry on SLATE. Row 5 holds the column labels, with a medium INK border below.
- The product name shows only on the first row of its block, which has a thin INK top border.
- The attention block uses `SORTBY` / `FILTER` over Thresholds. On a build without dynamic arrays, use 5 rows of `INDEX` / `SMALL`.

## Peers (`peers/peers_workbook.py`)
Two charts side by side: charge-offs on the left, delinquency on the right. Both follow the same cells.

**Columns:** A 16 · B–H 130 each (17.86) · I 24 (gutter) · J–P 130 each · Q 8. The left panel is B:H and the right panel is J:P.

**Rows:**
- 1 title (25.5 pt), 2 subtitle (15 pt), 3 spacer (6 pt).
- 4 labels (13.5 pt), 5 inputs (19.5 pt), 6 "Drawn: <bank>" under Peer A and Peer B (12 pt).
- 8 bank names (22.5 pt) and 9 "In the pack" (18 pt).
- 10 the best/worst rule (19.5 pt), 11 the best/worst note (13.5 pt).
- 13 panel titles (16.5 pt).
- 14–16 the four-number strip (13.5 / 19.5 / 12 pt).
- 17–32 charts (16 × 16.5 pt, 910 × 352 px each).
- 33 shading notes.
- 35 rank titles, 36–52 rank tables (15 pt).
- 54 small-chart titles, 55–62 small charts.
- 64 a note pointing to the lagged view.

**Inputs:**
- Row 5: B Product · C Charge-off rate (Net / Gross) · D Peer A · E Peer B · F Charts show (Last 20 / 48 quarters / Every quarter) · J Delinquency measure (30-89 / 90+ accruing / nonaccrual / 90+ incl. nonaccrual / 30+ incl. nonaccrual) · K Delinquency basis (quarter-end / four-quarter average).
- Peer A and Peer B offer **Worst in pack**, **Best in pack**, or any one of the 15 peers. Row 6 shows the bank actually drawn.
- Row 9: one Yes/No input per peer, 15 cells. This replaces the bank slicer, so no rows are ever hidden.
- Row 10: "Best and worst: ranked on the [net] rate's mean over the last [8] quarters, if kept in at least [6] · Banks a composite or band needs [5]".

**Calculations:**
- Best in pack is the lowest mean and Worst in pack the highest, among banks switched on that have at least the minimum number of kept quarters.
- **Pack composite** = Σ(rate × balance) ÷ Σ balance over the banks switched on that have a rate that quarter.
- **Bands:** p10–p90 in MIST `E4DFD5` and p25–p75 in `CFC8BC` (new token BAND_DARK). Both are blank where fewer banks than "needs" have a rate.
- KeyBank's rank counts 1 as the lowest rate.

**Four-number strip:** CANVAS fill, rows 14–16.
- Each pair of columns (B:C, D:E, F:G, H) holds a label (Arial 9 bold SLATE, uppercase), a value (Arial 16 bold INK) and a sub-line (Calibri 9 SLATE).
- Charge-offs: KeyBank · Pack composite · KeyBank's rank · Industry.
- Delinquency: KeyBank · Pack composite · KeyBank's rank · Banks with a rate.

**Charts** (legend at the top, Y gridlines MIST 0.5 pt):
- Two stacked-area bands.
- Pack composite: INK 2 pt.
- Industry: MEDIAN `8C877E` 1.5 pt, charge-offs chart only.
- Peer A: SLATE 1.5 pt dash. Peer B: SLATE 1.5 pt sysDot.
- KeyBank: KEY_RED 2.5 pt, with a 6 pt marker on its last point.

**Below the fold:**
- Two rank tables. Columns: Rank 60 · Bank 210 · Rate 110 · vs composite 120 · 4-quarter change 120 · Balance ($bn) 130 · In pack 80. KeyBank's row has a CANVAS fill and KEY_RED bold text; Peer A and Peer B are marked.
- Book size ($bn) over B:D.
- Charge-off rate ÷ composite over E:H, with a dashed reference line at 1.
- KeyBank's mix by product over J:P (100% stacked area, the selected product in KEY_RED).

## Thresholds
**Columns:** A 16 · B 120 Product · C 200 Measure · D 140 Source (KeyBank in KEY_RED) · E–K 84 each: Median kept, Typical yearly move, Worst kept, then where 2, 3, 4 and 5 begin · L 76 Quarter · M 76 Value · N 140 Rating · O 120 Decision · P 392 Check.
- Row 3: group headers with a medium border.
- Row 4: the INK header.
- Rows 5–109, 15 pt: the 105 series.
- Freeze panes at E5.
- A thin INK top border starts each product and a MIST border each measure. Repeated names are hidden with a white font through conditional formatting, so filters still work.
- Check shows `OK`, or "To fix: …" in CRIMSON bold.

## Internal (new, `internal_tab.py`) and Internal data (new)
**Purpose:** paste the bank's own CRR data and map its names once. Then see, for each product and measure, whether Industry, Peer group or KeyBank's Call Report series rates the same way the internal data does. That says whether each outside series is reliable enough to set lines from.

### Internal data (the slot)
- An Excel table named `InternalData`, header at A4.
- Title in row 1, purpose line in row 2 (KEY_RED rule).
- Columns, matched by header name, in any order:
  - `Quarter`: text such as 2024Q1, or a quarter-end date.
  - `Product`, `Measure`: the bank's own names.
  - `Value`: the rate.
  - `Units`: percent / decimal / bps.
  - `CRR grade`: optional.
  - `System`, `Note`: optional.
- Input fill on the data body.
- Helper columns to the right (formulas, SLATE): normalised quarter, mapped product, mapped measure, value in %, and the key `Product - Measure`.
- Units: decimal × 100, bps ÷ 100, blank → the default set on Internal.

### Internal tab layout
**Columns:** A 16 · B 150 · C 190 · D 20 · E 150 · F 250 · G 20 · H 110 · I 110 · J 110 · K 20 · L 170 · M–P 100 · Q 152.

**Rows:**
- 1: 25.5 pt.
- 2: 15 pt.
- 3: 6 pt.
- 4: 16.5 pt.
- 5: 15 pt.
- 6–12: 16.5 pt.
- 13: 7.5 pt.
- 14–31: 16.5 pt.
- 32: 7.5 pt.
- 33–34: 16.5 pt.
- 35–69: 15 pt.

1. **B4:C12 "Your products are".**
   - B lists each distinct product name in the file (`UNIQUE(InternalData[Product])`).
   - C is an input list of the five workbook products.
   - The default comes from a best guess: card → Credit card; mtg / mortgage → Mortgage; heloc / home eq → Home equity; auto → Auto; oth / other → Other consumer.
   - In Excel, write the guess as the starting value; the analyst can override it.
2. **E4:F12 "Your measures are"**: the same pattern for the seven measures.
   - Guess rules, applied in this order: "incl" + 30 → 30+ incl. nonaccrual; "incl" + 90 → 90+ incl. nonaccrual; 90 → 90+ and accruing; 30-89 → 30-89 days past due; non-acc → Nonaccrual; net / nco → Net charge-offs; gross / gco → Gross charge-offs.
3. **H4:J12 "What counts as reliable"**:
   - Inputs: quarters both have, at least (12); ratings that agree, at least (70%); change correlation, at least (0.60); default units (percent).
   - Read-only counts: rows on Internal data; rows not used. The unused count is CRIMSON on CANVAS when above 0.
4. **L4:Q12 "Quarters loaded, per series"**: measures down, products across, counting the non-blank quarters per series.
   - Fill `E1EAE6` when the count reaches the overlap minimum.
   - The picked series has fill INTERNAL `2F5D50` and white text.
   - In Excel, picking is done with the row 15 dropdowns; the grid is read-only.
5. **Row 15 (inputs):**
   - B Product, C Measure.
   - F "Shade with lines from", a list of the three sources. The zones come from that source's Decide settings.
6. **B16:J31: the chart (1110 × 352 px).**
   - Internal line in INTERNAL `2F5D50`, 2.5 pt solid.
   - KeyBank (Call Report) KEY_RED 1.5 pt dash; Peer group INK 1.5 pt sysDash; Industry SLATE 1.5 pt sysDot.
   - Rating zones and right-edge line labels as on Decide.
   - Last 48 quarters of the internal data.
   - When there is no data: a dashed STONE box on CANVAS reading "No internal data yet".
7. **L14:Q31 "How reliable is each outside source here?"**: one column per source.
   - Rows: Quarters both have; Level correlation; Change correlation (4 quarters); Average gap (internal − source); Ratings that agree; Within one rating; **Verdict**.
   - Below it, "If your file has CRR grades": five rating rows, each with an input for the lowest CRR grade (defaults 1, 3, 5, 7, 9). Then a sentence: "Your CRR grades agree with the rating from <source>'s lines in X% of N quarters."
8. **B33:Q69 "Every product and measure you loaded"**: Product, Measure, quarters, agreement % for each of the three sources, the best source, and its verdict chip.

### Calculations (formulas only)
- **Overlap:** quarters where the internal value and source *s* both have a value.
- **Level correlation:** `CORREL` of the values. **Change correlation:** `CORREL` of the 4-quarter changes over quarters where both have the current and the 4-back value.
- **Average gap:** the mean of internal − source, in points.
- **Ratings that agree:** rate both the internal value and the source value on **the source's own lines from Decide**, quarter by quarter. Count matches ÷ overlap. "Within one rating" counts |difference| ≤ 1. Use the same rating rule as Decide, including On a line.
- **Verdict**, checked in this order:
  1. Overlap < minimum → "Too few quarters".
  2. The source's lines are refused → "Its lines are refused".
  3. Agree ≥ minimum and change correlation ≥ minimum → "Reliable for setting lines".
  4. Agree ≥ 0.75 × minimum → "Use with care".
  5. Otherwise → "Not reliable".
- **Verdict fills:**
  - Reliable: `E1EAE6` with text `1E4637`.
  - Use with care: R3 cell colour with INK text.
  - Not reliable, and lines refused: CANVAS with CRIMSON text.
  - Too few quarters: PAPER with SLATE text.
- **CRR grade → rating:** the highest rating whose lowest grade ≤ the grade.

### Assumption to confirm with the analyst
"Internal CRR data" is read as **quarterly rates per consumer product and measure**, with an optional CRR grade per quarter. If the bank's extract is loan-level, keep the same slot and add a roll-up (pivot or `SUMIFS` by quarter, product and measure) feeding it.

### Glossary entries to add
Internal data, Mapped, Quarters both have, Level correlation, Change correlation, Average gap, Ratings that agree, Within one rating, Verdict (with each verdict's rule), CRR grade, Lowest grade in each rating.

---

## Reference tabs (one template)
- Row 1: title, Arial 14 bold INK, 25.5 pt.
- Row 2: purpose line, Calibri 11 SLATE, medium KEY_RED border below.
- Row 4: header, MIST fill, Arial 9 bold INK, STONE border below.
- Body: Calibri 11 on 15 pt rows with MIST hairlines; no fills, no banding.
- Numbers `0.00`, right-aligned. Wrap only in text columns. Freeze under the header and after the label column.
- Series blocks (Evidence, Backtest, Sources) each start with an Arial 11 bold heading over a thin INK rule, with a blank row between blocks.
- Per tab:
  - Evidence: the two tables side by side under one heading ("Spells worse than the median" | "Temporary departures from trend").
  - Backtest: Product, Measure and Source split into separate columns.
  - Sources: C at 120 units, wrapped.
  - Glossary: B 30.7, C and D 90.7, wrapped.
  - Data: freeze at B2, values `0.0000`, header row 45 pt.

## Design tokens
**Colours:**

| Token | Hex | Use |
|---|---|---|
| INK | `0A0908` | Titles, header fill, Peer group line, picked slicer button |
| INK_TEXT | `16130F` | Body text |
| SLATE | `57534B` | Secondary text, Industry line, Peer B |
| STONE | `B9B4AC` | Borders, left-out stretch on the chart |
| MIST | `E4DFD5` | Hairlines, reference headers, pack band |
| CANVAS | `F4F1EC` | Refused fill, OK band, KeyBank rank row |
| PAPER | `FFFFFF` | Sheet |
| KEY_RED | `CC0000` | KeyBank, title rule, KeyBank header rule |
| CRIMSON | `960019` | Refused text |
| INPUT | `FFF2CC` | Input cells, and only input cells |
| INPUT_EDGE (new) | `D6B656` | Input border |
| REFUSE_BAND (new) | `F8E3E1` | Refused Check band |
| MEDIAN (new) | `8C877E` | Industry line on Peers, ratio reference line |
| BAND_DARK (new) | `CFC8BC` | Middle-50% band on Peers |
| INTERNAL (new) | `2F5D50` | Internal line, picked coverage cell |
| INTERNAL_TINT (new) | `E1EAE6` | Coverage reached; Reliable verdict (text `1E4637`) |

**Rating cells:** 1 `E3EEDB` · 2 `EEF2D9` · 3 `FCEFC7` · 4 `F6C9A0` · 5 `E79A9A`.
**Chart zones** (one step lighter): `E9F1E3` `F2F5E3` `FCF3D6` `FAE0CA` `F4CBCB`.
Tonight's palette (`D9EAD3` `EBF1DE` `FCE8B2` `F8CBAD` `E6A0A0`) can be shown with the mock's palette switch for comparison.

**Type:**
- Title: Arial 16 bold.
- Section heading: Arial 11 bold, medium INK border below.
- Table header: Arial 9 bold PAPER on INK.
- Label: Arial 9 bold SLATE.
- Body: Calibri 11.
- Headline: Arial 14 bold.
- Check band: Arial 12 bold.
- Summary body: Calibri 13.
- Note: Calibri 10 SLATE.

**Number formats:**
- Rates `0.00`
- Difference `+0.00;-0.00;0.00`
- Settings `0.0#`
- Share and agreement `0%`
- Counts `0`
- Balance `#,##0.0`
- Ratio `0.00"×"`
- Correlation `0.00`
- Quarter: text

**Conditional formatting:**
- Rating cells: `=$X=1…5` → R1–R5 fill.
- Refused: fill CANVAS, font CRIMSON bold.
- Check band refused: fill REFUSE_BAND, CRIMSON borders.
- Decision: Accept → bold INK; Reject → bold SLATE.
- Repeated names: `=B7=B6` → PAPER font.
- Peers rank: KeyBank row → CANVAS fill, KEY_RED bold. Peers "In the pack": No → SLATE font.
- Internal: unmapped count > 0 → CRIMSON on CANVAS; coverage ≥ minimum → INTERNAL_TINT.

**Charts:**
- Decide zones: stacked area. A transparent base at the axis floor, then the 5 bands, no border.
- Lines: picked series 2.5 pt solid in its source colour; overlays 1.5 pt dash; left-out stretch 2.5 pt STONE (a separate series that has values only in the left-out period).
- Rating line labels: four hidden series, with the label on the last point, positioned right, Calibri 9 SLATE.
- Axes: Y `0.00` with automatic bounds over the `OFFSET` named range. X tick-label skip 2 / 4 / 8 / 12 for 20 / 48 / 80 / every quarter. Calibri 9 SLATE; axis line STONE 0.75 pt.
- Gridlines: none on Decide or Internal; major Y only at MIST 0.5 pt on Peers.
- Legend: at the top, with the zone and helper entries deleted.
- Peers bands: a base series at p10 with no fill, then p25 − p10 in MIST, p75 − p25 in BAND_DARK, and p90 − p75 in MIST.
- KeyBank's last point: a 6 pt circle marker.

## Interactions (all by formulas or slicers; no macros)
- Slicer picks → the table shows one row → every block below reads that row through the visible-row lookup (`AGGREGATE` / `SUBTOTAL`).
- Typing a setting moves the lines, counts, shading, Check, Summary, Thresholds and Internal verdicts.
- Leaving a period out greys it on the chart and drops it from the lines.
- The Internal mapping dropdowns re-key every pasted row.

## Files
- `Consumer Credit Redesign.dc.html`: the live mock (all tabs, the token sheet, the reasons and the cuts).
- `support.js`: the mock's runtime. Keep it beside the HTML.
- `data/series.json`, `data/peers.json`, `data/glossary.json`: extracted from `consumer-credit.xlsx` (Data, Peers data, Peers delinquency data, Glossary) so the mock is live.
- `reference/keybank_style.py`: the current style module, to extend with the new tokens above.

In the mock, the Internal tab is pre-filled with **sample rows made up from KeyBank's Call Report series**. They are labelled as samples and must never ship. "Mock only: load sample / clear" and the paste box exist only in the mock.
