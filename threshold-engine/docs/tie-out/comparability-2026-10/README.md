# Comparability tie-out, October 2026

Seven questions about whether the public bank data threshold-engine uses
compares like with like, each tied out against documents the firm does not
control. KeyBank, N.A. (cert 17534), its 15 peers and the industry. Public data
only: nothing from KeyBank's internal books.

**The deliverable is [`TIE-OUT-comparability-2026-10.pdf`](TIE-OUT-comparability-2026-10.pdf)**:
one document with every picture embedded, checked and rendered by canon's
`check_tie_out`.

147 figures were set beside an independent document: **13 DIFFERS, 3 COULD NOT, 131 TIED**.

| Gap | Verdict | How big | What to do |
|---|---|---|---|
| 1 · Government-guaranteed loans in 90+ | Real, large for mortgage. The lines are RC-N 11, 11.a, 11.b, not 10 and 10.a | Rebooked GNMA 90+ is 80–103% of first-lien 90+ at eight peers, 63% industry-wide; about $5m of KeyBank's $15.0m | Compare mortgage on nonaccrual and charge-offs; do not subtract rebooked GNMA from peers' 90+ (the line is not split by loan type); show the GNMA share beside it as an upper bound |
| 2 · Card nonaccrual is policy | Real | 10 of 16 banks file zero card nonaccrual; Citizens files zero 90+ accruing in all 76 quarters | Compare cards on 90+ incl. nonaccrual and 30+ incl. nonaccrual |
| 3 · 2010Q1 securitizations (FAS 166/167) | Real in the industry card series only | Industry card balances +69.1% in one quarter; about +0.9 pts on the rate from mix | Treat 2010Q1 as a break; use the industry card series from 2010Q4 or label the earlier part |
| 4 · Industry total against peer median | Real, product-dependent | Card and other consumer about 0.15 pts apart on average (1.3 in 2009–11); auto industry typically 2× the median | Show both; anchor auto on the median; add p50 to the band |
| 5 · Mergers | Real, two ways | 56 of 149 material acquisition cases slip the 25% rule; affiliate mergers double-count charge-offs in the industry series (card rate up to +0.71 pts) | Leave out windows around recorded acquisitions of 5%+; subtract the absorbed bank's year-to-date flows |
| 6 · KeyCorp against KeyBank | Small, fully explained | Ties within $1m once education loans in discontinued operations and residential held-for-sale are added; KeyCorp "home equity" is ~$2.5bn wider than the Call Report's | Name both items as exclusions in the internal import; split or combine home equity |
| 7 · Auto | 6.c ties at 62,212; the rest of direct auto COULD NOT be located publicly | KeyBank sold its indirect book in 2021Q3; leases matter only for U.S. Bank (56%) and Bank of America (16%) | Compare internal direct auto with 62,212 on site; if larger, map what the internal segment holds before assigning the difference to a filed line; set its thresholds on internal data |

No code was changed. The tool's side of every figure is its own cache
(`peers pull`) or series CSVs (`peers build`), run unchanged.

## Rebuilding it

`scripts/` holds everything that produced the document. Run every command from
`threshold-engine/`, with outputs under `work/`:

| Script | What it does |
|---|---|
| `fetch_sources.py --sources work/sources --user-agent "Firm name you@example.com"` | Downloads the 27 filed Call Reports (FFIEC CDR, PDF and XBRL), the FDIC API responses, KeyCorp's 10-K and 10-Q, the QBP, the Call Report instructions and the Fed's H.8; every URL to `DIR/urls.txt` |
| `collect.py` | Computes every figure and verdict into `figures.json` (and `qbp-card.json` for the chart) |
| `capture.py` | Cuts each source photograph out of the real page and rings the figure in red, into `images/` |
| `build_exhibit.py` | Assembles the document; canon checks and renders it |
| `sources.py` | Readers for the XBRL, the API responses, the QBP workbook and the SEC filings |

The exact commands, with real values, are in the document's "How to run it
yourself" section.
