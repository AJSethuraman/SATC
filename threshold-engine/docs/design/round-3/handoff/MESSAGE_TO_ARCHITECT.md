# To the architect: design round 3, Consumer Industry Analysis (19 Oct 2026)

Start with `README.md` in this folder; it says, tab by tab, what the generator changes. Open `Consumer Industry Analysis Round 3.dc.html` beside it (serve the folder: `python -m http.server`, then open the file; it needs `support.js` and `data/`). Round 2's hand-off still holds for everything this round does not mention.

## What this round decides

1. **Tab set: 19 visible → 13 (15 on site).** Summary first. Backtest folds into Lines by source; Reporting changes folds into Sources; Peer loan classes becomes Peer books; Peers data and Peers delinquency data are hidden; Internal and Internal data are built only with an internal file.
2. **Signals has its first design pass.** Controls, pack line and a HYPERLINK jump row at the top (freeze at row 8); three chart sizes by job; the 15-bank panel replaced by a one-row pack line; fit tables beside the charts with the pick first; the rescale's inputs as a table, not a sentence; the gap on a fixed ±20-point axis, shaded and priced; Yes/No per product under the dollars table to thin the charts. Every pick-dependent cell stays a formula on Signals workings; only positions move.
3. **The peer group, one way everywhere:** the pack line (TEXTJOIN over Peers' roster) under every chart or table that draws on the pack, and three states on Peers' roster: in / out by rule / off.
4. **Summary and Thresholds lose the two new source columns** (From 1990 has Industry's latest quarter; Large banks is one series, now a strip on Summary). `—` once instead of *Pick a source* 150 times; a count in the title row.
5. **One number format per kind of number** (rates `0.00` everywhere), one header style per tab group, column widths that fit their longest label (listed in the README and the token sheet).

## Please confirm before building

- Hiding Peers data and Peers delinquency data: nothing on the visible tabs links into them except the pack line's "why out" lookup, which is a formula and works on a hidden sheet.
- Lines by source gains Backtest's three summary columns; the five per-rating averages go in a collapsed column group. Say if any test reads Backtest by sheet name.
- Thresholds: a refused row is 34.5 pt and its To fix wraps; the Product cell wraps on a combined product's first row.
- The gap chart's fixed axis (−20 to +20 points) is a static axis setting, not a cell-driven one.

## What is mock-only

30+ to charge-off, the two gaps, the three drawn signals and their fit numbers, the Backtest columns on Lines by source, and the Internal sample are drawn to shape; the extract in `data/` does not hold them. Four of the seven signal blocks are stated, not drawn; they repeat the drawn block.

## Files

- `Consumer Industry Analysis Round 3.dc.html` — the mock: tab set, every visible tab at 1920 with the fold, per-tab notes, token sheet, cuts, constraints.
- `README.md` — the build spec for this round.
- `support.js`, `data/` — the mock's runtime and the round-2 extract it runs on.
