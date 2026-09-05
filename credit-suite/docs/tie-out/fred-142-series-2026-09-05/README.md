# Tie-out: the latest observation of all 142 macro series — 5 September 2026

*(This heading said "every number" until an audit pointed out that the document covers 142 figures out of 13,841 observations — the newest of each series. The body always said "142 of 142 series"; the title did not, and the title is the line a reader sees first.)*

**142 of 142 series tied. 0 differ. 0 could not.**

`TIE-OUT-fred-142-series-2026-09-05.pdf` is the deliverable and it is
self-contained: 35 pages, every screenshot embedded in the file, nothing that
resolves only on the machine that built it. Open that, not this.

## What was actually compared

The left of every comparison is a cell read out of the shipped workbook,
`example-output/FRED_Credit_Risk_Dashboard.xlsm`. Not re-fetched, not
recomputed — the value a person sees when they open the file. The right is a
figure published by **the agency that computes the series**, never by FRED,
which only redistributes them. Asking FRED whether FRED is right is a mirror.

| Set | Publisher | Tied |
|---|---|---|
| All-Transactions house price indexes | Federal Housing Finance Agency | 67 of 67 |
| Charge-off and delinquency rates at commercial banks | Federal Reserve Board | 29 of 29 |
| G.19 consumer credit, debt service ratios, FHFA monthly index | Board and FHFA | 9 of 9 |
| Senior Loan Officer Opinion Survey | Federal Reserve Board | 13 of 13 |
| Case-Shiller house price indexes | S&P Dow Jones Indices | 22 of 22 |
| Z.1 commercial property price indexes | Federal Reserve Board | 2 of 2 |

`roster.json` is the machine-readable version: one record per series with the
workbook tab and cell, both values, the difference, the verdict, and the
document and row the publisher's figure came off.

## What it found

Five defects, every one of which left the numbers correct — which is why the
test suite had been passing over all five.

1. **A shipped workbook with a state missing.** One `Internal Server Error` from
   FRED blanked Nebraska's house price index and the build passed. Fixed in
   `1b03896`.
2. **Two series wearing each other's description** — the commercial real estate
   construction and nonfarm-nonresidential labels were swapped.
3. **A tightening indicator with its alert switched off**, because it was filed
   as a demand series. Fixing it turns an alert on.
4. **Two more labels naming a different series** than the number beside them.
   2–4 fixed in `a9411a1`.
5. **Four G.19 series declaring "billions" beside a figure in millions** — a
   factor of a thousand on the line a person reads. Fixed in `94d431f`.

One thing was deliberately **not** changed: the unit on the two Z.1
commercial-property series, where our config, FRED and the Board give three
different answers and I could not establish which is right. It is written up in
the exhibit as unresolved.

## Reproducing it

The scripts are in `../../../tools/tieout/`, one per publisher, and they run in
this order:

```
python tools/tieout/fred_ours.py            # read the workbook -- the "ours" side
python tools/tieout/fred_fhfa.py            # FHFA's own quarterly files
python tools/tieout/fred_fed.py             # the Board's six charge-off tables
python tools/tieout/fred_other.py           # G.19, the DSR release, FHFA monthly
python tools/tieout/fred_sloos.py           # the survey's chart data and Table 1
python tools/tieout/fred_caseshiller.py     # S&P's monthly release
python tools/tieout/fred_z1.py              # the Z.1 complete package
python tools/tieout/fred_roster.py          # merge, and refuse if it does not add up
```

Then the evidence and the document:

```
python tools/tieout/fred_excel_shots.py     # photograph all 142 workbook cells
python tools/tieout/fred_source_shots.py    # photograph each publisher's page
python tools/tieout/build_fred_exhibit.py   # one self-contained PDF
```

`cs_second_month.py` and `cs_rounding_cause.py` are the two that turned five
Case-Shiller near-misses into an explanation instead of a wider tolerance.

The scripts carry absolute paths from the session that wrote them; they are
kept as the record of what was run, not as a polished tool.

## What this does not prove

- It proves the **latest** observation of each series, not the 13,905
  observations behind them. Case-Shiller was additionally checked a second
  month.
- The twenty adjusted Case-Shiller metros are tied through a **ratio of two
  cells**, because S&P does not publish adjusted levels free. That pins the
  month-on-month move, not the absolute level.
- It proves the **numbers, not the formulas**. Nothing here checks z-scores,
  bands or alert logic. That was the instruction.
- Nothing here was checked by a second person.
