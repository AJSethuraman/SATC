# The stress table under the tool's own rules (16 Oct 2026)

The proposal's section 3 Q1 table (`COMMERCIAL-PROPOSAL.md`, on main) was
computed **as filed**: none of the tool's merger, jump or repeated
year-to-date rules. This recomputes it from what `peers pull` and `peers
build` wrote for the six commercial products added on branch
`commercial-build`, and sets it beside the as-filed table
(`stats-output.txt`, on main). Public data only: the FDIC BankFind API and
the Federal Reserve's series on FRED. Nothing decided here: the rule
settings are **the consumer book's** (`books/consumer-public.json`), used
because no commercial setting has been chosen, not as a commercial choice.

## What was run

Python 3.13 with `openpyxl`; from `threshold-engine/`, `CACHE` a folder
outside the repository (here the session's scratchpad, `cache-commercial`).

```
python -m threshold_engine peers pull --cache $CACHE --first 2006Q1 --last 2026Q2 --products "C&I" Construction Multifamily "Nonfarm nonresidential" "Owner-occupied nonfarm nonresidential" "Other nonfarm nonresidential" --delinquency yes --mergers 2005-01-01
cp $CACHE/mergers.json $CACHE/mergers-since-2005.json; cp $CACHE/absorptions.json $CACHE/absorptions-since-2005.json
python -m threshold_engine peers pull --cache $CACHE --first 1991Q1 --last 2005Q4 --products "C&I" Construction Multifamily "Nonfarm nonresidential" "Owner-occupied nonfarm nonresidential" "Other nonfarm nonresidential" --delinquency yes --mergers 1990-01-01
cp $CACHE/mergers.json $CACHE/mergers-since-1990.json; cp $CACHE/absorptions.json $CACHE/absorptions-since-1990.json
python -m threshold_engine peers build $OUT/peers.xlsx --cache $CACHE --roster config/peers.json --series-dir $OUT/series --first FIRST --last 2026Q2 --products "C&I" Construction Multifamily "Nonfarm nonresidential" "Owner-occupied nonfarm nonresidential" "Other nonfarm nonresidential" --mergers $CACHE/mergers-since-2005.json --absorptions $CACHE/absorptions-since-2005.json --extra-acquisitions 6672=2022Q2 --delinquency yes --reporting-changes config/reporting-changes.json --industry-combined "Construction+Multifamily+Nonfarm nonresidential" --jump 0.25 --acquisition-share 0.05 --min-book 0 --exempt-self yes --pro-forma yes --pack all --min-banks 5 --rank-by net --last-n 8 --min-obs 6 --base-quarter 2019Q4 --index-min-book 1000000 --lagged-years 2019 2025 --lag-years 2 --normalisation-years 2019 2025 --mix-base-year 2019
python docs/commercial-2026-10/stress_tool_rules.py $OUT/series $OUT/peers.xlsx PATH/TO/stats-output.txt
python docs/commercial-2026-10/fred_ttm.py PATH/TO/fred/CORBLACBN.csv $FED/CORBLACBN-ttm.csv
python docs/commercial-2026-10/fred_ttm.py PATH/TO/fred/CORCREXFACBN.csv $FED/CORCREXFACBN-ttm.csv
python -m threshold_engine compare $OUT/series/c-i_industry_net.csv $FED/CORBLACBN-ttm.csv
python -m threshold_engine compare $OUT/series/construction-multifamily-nonfarm-nonresidential_industry_net.csv $FED/CORCREXFACBN-ttm.csv
```

Each `pull --mergers` writes `mergers.json` and `absorptions.json` over the
last pull's, so each record is copied under the date it starts from. A
build from `FIRST` = **1991Q1** must read the `-since-1990` files. Since 18
Oct 2026 (question 22) each record states the date it starts from and the
build refuses one that starts after its first quarter begins, naming both;
a record written before then (no date) is refused with the pull to run
again, so the copies above must be re-pulled once. The builds tabled here ran before
`--stated-acquisitions FILE|none` existed; it has been required since 17
Oct 2026 (question 14), so the command above is refused today without it.

`build` was run twice, `FIRST` = **2006Q1** (the consumer book's first
quarter) and **2005Q1**. Only the second gives KeyBank a 2006Q4 window: a
bank's first TTM quarter is the fifth in the data, so a 2006Q1 build starts
KeyBank at 2007Q1. Every industry figure in 2006Q4 on is the same in both;
the 2005Q1 build is the one tabled. Each build took about 23 minutes.

Settings that are not rules: `--industry-combined` writes construction +
multifamily + nonfarm as one industry series, for the comparison with the
Fed's CRE line. `--extra-acquisitions 6672=2022Q2` is the consumer book's
(Fifth Third, a consumer acquisition), kept so the settings are the book's.

**The pull, by the numbers.** 2006Q1–2026Q2: 82 quarters fetched, 4,313
filers in 2026Q2; the merger record since 2005-01-01: 2,649 acquirers, 6,379
absorptions. **1991Q1–2005Q4: the existing pull fetched all 60 quarters with
no new machinery** (a field not yet filed comes back as null, checked
against the API), **but the merger record since 1990-01-01 was refused**:
four FDIC history rows carry change codes on neither of `fdic.py`'s lists
(code 213 "Merger - Assisted", three rows in May 1990; code 225 "Partial
Purchase & Assumption - Without Assistance", one row, 9 Oct 1991). What a
code means is the firm's decision, so **no build before 2005 was made under
the tool's rules: COULD NOT**, until those two codes are placed. The 60
quarters are in the cache.

## The table, under the tool's rules

TTM net charge-off rate and quarter-end nonaccrual rate, 2005Q1 build. "As
filed" is `stats-output.txt`. "Every kept quarter" is every quarter the
build kept for KeyBank (the peer workbook's Data and DelinquencyData tabs),
gaps left as gaps; "series written" is the file `peers build` wrote for the
workbook, which is the latest unbroken run, because the workbook refuses a
gap. Largest z = (worst − median) ÷ spread of levels, `scale.level_spread`.

| Segment | Measure | Industry worst since 2006Q4 (quarter) | Industry largest z, 2006Q4 on / 2014Q1 on | KeyBank median, 2014Q1 on | KeyBank largest z, 2006Q4 on / 2014Q1 on, every kept quarter | KeyBank series written: quarters from 2006Q4, largest z 2006Q4 on / 2014Q1 on |
|---|---|---|---|---|---|---|
| C&I | Net charge-off | 2.520% (2010Q1); as filed 2.492% (2010Q1) | 10.8 / 1.5; as filed 10.9 / 1.5 | 0.296%; as filed 0.296% | **16.4 / 3.0**; as filed 13.0 / 4.1 | **2**, 0.7 / 0.7 |
| C&I | Nonaccrual | 3.200% (2009Q3); as filed 3.166% (2009Q3) | 8.1 / 2.3; as filed 8.1 / 2.4 | 0.604%; as filed 0.604% | 10.9 / 2.7; as filed the same | 79, 10.9 / 2.7 |
| Nonfarm nonres | Net charge-off | 1.251% (2010Q4); as filed 1.250% (2010Q4) | 7.8 / 3.9; as filed the same | 0.135%; as filed 0.113% | 12.3 / 2.5; as filed 14.8 / 2.4 | 79, 12.3 / 2.5 |
| Nonfarm nonres | Nonaccrual | 3.899% (2010Q3); as filed 3.893% (2010Q3) | 4.8 / 2.2; as filed the same | 0.574%; as filed 0.574% | 7.8 / 2.2; as filed the same | 79, 7.8 / 2.2 |
| Multifamily | Net charge-off | 1.332% (2010Q2); as filed 1.332% (2010Q2) | 16.8 / 9.7; as filed 16.7 / 9.8 | 0.001%; as filed −0.000% | 359.2 / 135.7; as filed 457.7 / 214.9 | 65, 337.1 / 135.7 |
| Multifamily | Nonaccrual | 4.267% (2010Q3); as filed 4.264% (2010Q3) | 7.5 / 7.0; as filed 7.5 / 6.9 | 0.065%; as filed 0.065% | 41.7 / 51.0; as filed the same | 79, 41.7 / 51.0 |
| Construction | Net charge-off | 6.485% (2010Q1); as filed 6.477% (2010Q1) | 60.8 / 9.9; as filed 61.1 / 9.9 | 0.009%; as filed 0.004% | 94.7 / 7.1; as filed 76.4 / 14.8 | **44**, 7.2 / 7.2 |
| Construction | Nonaccrual | 15.062% (2010Q1); as filed 15.046% (2010Q1) | 20.9 / 9.3; as filed 21.2 / 9.3 | 0.052%; as filed 0.052% | 79.7 / 36.0; as filed the same | 79, 79.7 / 36.0 |

What differs, and what was checked as the cause:

1. **Industry, every segment: within 0.034 points of as filed** (0.03 or
   less on every figure but the C&I nonaccrual worst quarter, 3.1998% against
   3.166%, which item 1's own check explains). The tool
   leaves out a filer whose charge-off or nonaccrual field is blank (not
   filed), with its balance; as filed, the API's sums kept 17 or 18 such
   filers' balances in the denominator. **Checked** for C&I: 2009Q3
   nonaccrual is 3.1998% without them and 3.1664% with every filer's LNCI,
   the as-filed 3.166%; the 2010Q1 TTM average balance without them is
   0.98905 of the one with them, and 2.5201% × 0.98905 = 2.4925%, the
   as-filed 2.492%. Not checked segment by segment.
2. **KeyBank nonaccrual: the same as filed, every segment.** A quarter-end
   rate is one filing; the jump, acquisition and pro forma rules do not
   touch it (delinquency is each bank as filed).
3. **KeyBank C&I charge-offs: the series written holds two quarters.** The
   December 2024 NDFI revision moved $12.0bn of KeyBank's C&I out (LNCI
   41,865,646 to 29,882,121, research-fdic.md), a 28.6% fall, so the 25%
   jump leaves out the five windows 2024Q4 to 2025Q4, and the workbook's
   series starts at 2026Q1. Over every kept quarter (74 of 79 from 2006Q4)
   the largest z is 16.4 and 3.0 since 2014, against 13.0 and 4.1 as filed:
   the as-filed worst since 2014 (0.901%, 2025Q2) is one of the windows the
   jump leaves out. **This is a decision for the firm**: the jump rule
   reading a reporting change as a book move. Nothing was changed.
   *Update, 17 Oct 2026:* answered (question 16). The series continues
   across those windows: 2024Q4 to 2025Q4 are declared left out and the
   history before them is kept (LOG.md, 17 Oct 2026, question 16).
4. **KeyBank construction and multifamily charge-offs, pro forma.** Each
   includes the banks KeyBank absorbed (First Niagara Bank, certificate 16004 by the FDIC's
   institutions record, absorbed 2016Q4, and the others the Data tab names), so the 2010 peaks
   are lower: construction 12.161% against 13.894% as filed, multifamily
   4.636% against 6.837%. The jump leaves out construction 2014Q2–2015Q2
   and multifamily 2009Q1–2010Q1, so the series written start 2015Q3 and
   2010Q2. Multifamily's z stays in the hundreds (median 0.001% since 2014):
   the proposal's finding stands under the tool's rules.
5. **KeyBank nonfarm charge-offs since 2014**: median 0.135% against 0.113%
   as filed; the as-filed used the FDIC's quarterly fields (DRRENRSQ) and
   no pro forma. Which of the two moves the median was not separated.
6. **The splits** (owner-occupied and other nonfarm) are not in the
   proposal's table. For KeyBank pro forma, every window to 2011Q2 is "not
   filed": two banks it adds pro forma left the split blank, First Niagara
   (16004) through 2010Q1 and Willow Financial Bank (30089) through 2008Q3,
   both on CALLFORM 100 (the TFR) at 2008Q1 by the API. A window reads the
   quarters i-5 to i, so its split series run from 2011Q3.

## The Federal Reserve cross-check (`compare`)

FDIC industry TTM net charge-offs (2006Q1 build) against the mean of the
Fed's four quarterly NSA rates (`fred_ttm.py`; the FRED CSVs in
`fred/`, on main, pulled 16 Oct 2026), matched by calendar quarter:

| FDIC industry | Fed | Quarters | Mean difference (FDIC − Fed) | Mean absolute | Largest |
|---|---|---|---|---|---|
| C&I | CORBLACBN | 79, 2006Q4–2026Q2 | +0.030 | 0.031 | 0.178 (2010Q1) |
| Construction + multifamily + nonfarm | CORCREXFACBN | 79, 2006Q4–2026Q2 | −0.013 | 0.017 | 0.094 (2009Q4) |

The two are built differently, so no tolerance is set and none is judged:
the Fed's is insured U.S.-chartered commercial banks only, the quarter's
average loans, adjusted for mergers, and here a mean of four quarterly
rates; the FDIC's is every filer (savings institutions too), four quarters'
flows over four quarter-end balances. As filed (`more-output.txt`, quarterly
against quarterly, 82 quarters since 2006): C&I mean 0.021, largest 0.114;
CRE mean −0.016, largest 0.169. Not the same basis, so not comparable
number for number.

## Not done, or not checked

- **No build from 1991**: COULD NOT, the merger record since 1990 refused
  on codes 213 and 225 (above). The industry's early-1990s CRE losses, which
  the proposal leans on, are therefore not under the tool's rules yet.
  *Update, 17 Oct 2026:* the firm placed both codes (question 17: 213 an
  acquisition, 225 not), so the merger record since 1990 is no longer
  refused on them (LOG.md, 17 Oct 2026, question 17). A build from 1991Q1
  then ran (question 6), first on an interrupted run's code (LOG.md, the
  partial entry), then on the reviewed code, with the merger record since
  1990: LOG.md, "17 Oct 2026, question 6: a peers build from 1991Q1". The
  early-1990s figures were not tied out to the QBP.
- The registry's reporting-change notes on the commercial series were read
  in the series files; the workbook built from them was not opened in Excel.
- The peer workbook from these builds was not opened. Its dashboard text
  still says "consumer book" in two places (the book-by-product panel and
  its Glossary entry).
- The as-filed KeyBank charge-offs used the FDIC's quarterly fields; the
  tool uses year-to-date differences. How much of each KeyBank difference
  is that, and how much is pro forma, was not separated.
- Delinquency for industry splits in 2007 counts the 2,925–3,044 filers who
  filed the split as 0 and 0 (labelled in every split series' notes), and
  that label's size in delinquency terms was not measured.

## The whole output

`stress_tool_rules.py` on the 2005Q1 build, as printed. Industry rows and
KeyBank nonaccrual rows are the same on the 2006Q1 build; KeyBank's
charge-off rows there start at 2007Q1.

| Segment | Measure | Who | Window | n | Median | Spread | Worst (quarter) | Largest z | As filed: n | median | spread | worst (quarter) | largest z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C&I | TTM net charge-off | Industry | 2006Q4 on | 79 | 0.414 | 0.195 | 2.520 (2010Q1) | 10.8 | 79 | 0.407 | 0.192 | 2.492 (2010Q1) | 10.9 |
| C&I | TTM net charge-off | Industry | 2014Q1 on | 50 | 0.358 | 0.142 | 0.577 (2026Q2) | 1.5 | 50 | 0.352 | 0.140 | 0.561 (2026Q2) | 1.5 |
| C&I | TTM net charge-off | KeyBank, series written | 2006Q4 on | 2 | 0.530 | 0.048 | 0.562 (2026Q1) | 0.7 | 79 | 0.330 | 0.283 | 3.998 (2010Q2) | 13.0 |
| C&I | TTM net charge-off | KeyBank, series written | 2014Q1 on | 2 | 0.530 | 0.048 | 0.562 (2026Q1) | 0.7 | 50 | 0.296 | 0.148 | 0.901 (2025Q2) | 4.1 |
| C&I | TTM net charge-off | KeyBank, every kept quarter | 2006Q4 on | 74 | 0.335 | 0.203 | 3.673 (2010Q2) | 16.4 | | | | | |
| C&I | TTM net charge-off | KeyBank, every kept quarter | 2014Q1 on | 45 | 0.296 | 0.125 | 0.675 (2021Q1) | 3.0 | | | | | |
| C&I | Quarter-end nonaccrual | Industry | 2006Q4 on | 79 | 0.767 | 0.302 | 3.200 (2009Q3) | 8.1 | 79 | 0.755 | 0.297 | 3.166 (2009Q3) | 8.1 |
| C&I | Quarter-end nonaccrual | Industry | 2014Q1 on | 50 | 0.734 | 0.242 | 1.288 (2016Q2) | 2.3 | 50 | 0.722 | 0.231 | 1.270 (2016Q2) | 2.4 |
| C&I | Quarter-end nonaccrual | KeyBank, series written | 2006Q4 on | 79 | 0.680 | 0.356 | 4.569 (2009Q3) | 10.9 | 79 | 0.680 | 0.356 | 4.569 (2009Q3) | 10.9 |
| C&I | Quarter-end nonaccrual | KeyBank, series written | 2014Q1 on | 50 | 0.604 | 0.303 | 1.435 (2016Q1) | 2.7 | 50 | 0.604 | 0.303 | 1.435 (2016Q1) | 2.7 |
| C&I | Quarter-end nonaccrual | KeyBank, every kept quarter | 2006Q4 on | 79 | 0.680 | 0.356 | 4.569 (2009Q3) | 10.9 | | | | | |
| C&I | Quarter-end nonaccrual | KeyBank, every kept quarter | 2014Q1 on | 50 | 0.604 | 0.303 | 1.435 (2016Q1) | 2.7 | | | | | |
| Nonfarm nonresidential | TTM net charge-off | Industry | 2006Q4 on | 79 | 0.131 | 0.144 | 1.251 (2010Q4) | 7.8 | 79 | 0.131 | 0.144 | 1.250 (2010Q4) | 7.8 |
| Nonfarm nonresidential | TTM net charge-off | Industry | 2014Q1 on | 50 | 0.073 | 0.064 | 0.324 (2024Q3) | 3.9 | 50 | 0.073 | 0.064 | 0.322 (2024Q3) | 3.9 |
| Nonfarm nonresidential | TTM net charge-off | KeyBank, series written | 2006Q4 on | 79 | 0.193 | 0.229 | 3.002 (2010Q3) | 12.3 | 79 | 0.198 | 0.265 | 4.123 (2010Q3) | 14.8 |
| Nonfarm nonresidential | TTM net charge-off | KeyBank, series written | 2014Q1 on | 50 | 0.135 | 0.146 | 0.500 (2021Q1) | 2.5 | 50 | 0.113 | 0.161 | 0.500 (2021Q1) | 2.4 |
| Nonfarm nonresidential | TTM net charge-off | KeyBank, every kept quarter | 2006Q4 on | 79 | 0.193 | 0.229 | 3.002 (2010Q3) | 12.3 | | | | | |
| Nonfarm nonresidential | TTM net charge-off | KeyBank, every kept quarter | 2014Q1 on | 50 | 0.135 | 0.146 | 0.500 (2021Q1) | 2.5 | | | | | |
| Nonfarm nonresidential | Quarter-end nonaccrual | Industry | 2006Q4 on | 79 | 1.019 | 0.604 | 3.899 (2010Q3) | 4.8 | 79 | 1.014 | 0.605 | 3.893 (2010Q3) | 4.8 |
| Nonfarm nonresidential | Quarter-end nonaccrual | Industry | 2014Q1 on | 50 | 0.767 | 0.338 | 1.502 (2014Q1) | 2.2 | 50 | 0.763 | 0.335 | 1.494 (2014Q1) | 2.2 |
| Nonfarm nonresidential | Quarter-end nonaccrual | KeyBank, series written | 2006Q4 on | 79 | 0.792 | 0.615 | 5.588 (2009Q3) | 7.8 | 79 | 0.792 | 0.615 | 5.588 (2009Q3) | 7.8 |
| Nonfarm nonresidential | Quarter-end nonaccrual | KeyBank, series written | 2014Q1 on | 50 | 0.574 | 0.366 | 1.372 (2024Q4) | 2.2 | 50 | 0.574 | 0.366 | 1.372 (2024Q4) | 2.2 |
| Nonfarm nonresidential | Quarter-end nonaccrual | KeyBank, every kept quarter | 2006Q4 on | 79 | 0.792 | 0.615 | 5.588 (2009Q3) | 7.8 | | | | | |
| Nonfarm nonresidential | Quarter-end nonaccrual | KeyBank, every kept quarter | 2014Q1 on | 50 | 0.574 | 0.366 | 1.372 (2024Q4) | 2.2 | | | | | |
| Multifamily | TTM net charge-off | Industry | 2006Q4 on | 79 | 0.050 | 0.076 | 1.332 (2010Q2) | 16.8 | 79 | 0.050 | 0.077 | 1.332 (2010Q2) | 16.7 |
| Multifamily | TTM net charge-off | Industry | 2014Q1 on | 50 | 0.009 | 0.015 | 0.151 (2025Q3) | 9.7 | 50 | 0.009 | 0.014 | 0.150 (2025Q3) | 9.8 |
| Multifamily | TTM net charge-off | KeyBank, series written | 2006Q4 on | 65 | 0.005 | 0.014 | 4.636 (2010Q2) | 337.1 | 79 | 0.005 | 0.015 | 6.837 (2010Q2) | 457.7 |
| Multifamily | TTM net charge-off | KeyBank, series written | 2014Q1 on | 50 | 0.001 | 0.008 | 1.071 (2025Q4) | 135.7 | 50 | -0.000 | 0.005 | 1.071 (2025Q4) | 214.9 |
| Multifamily | TTM net charge-off | KeyBank, every kept quarter | 2006Q4 on | 74 | 0.006 | 0.013 | 4.636 (2010Q2) | 359.2 | | | | | |
| Multifamily | TTM net charge-off | KeyBank, every kept quarter | 2014Q1 on | 50 | 0.001 | 0.008 | 1.071 (2025Q4) | 135.7 | | | | | |
| Multifamily | Quarter-end nonaccrual | Industry | 2006Q4 on | 79 | 0.472 | 0.504 | 4.267 (2010Q3) | 7.5 | 79 | 0.472 | 0.504 | 4.264 (2010Q3) | 7.5 |
| Multifamily | Quarter-end nonaccrual | Industry | 2014Q1 on | 50 | 0.212 | 0.121 | 1.051 (2026Q2) | 7.0 | 50 | 0.211 | 0.120 | 1.047 (2026Q2) | 6.9 |
| Multifamily | Quarter-end nonaccrual | KeyBank, series written | 2006Q4 on | 79 | 0.130 | 0.185 | 7.841 (2010Q1) | 41.7 | 79 | 0.130 | 0.185 | 7.841 (2010Q1) | 41.7 |
| Multifamily | Quarter-end nonaccrual | KeyBank, series written | 2014Q1 on | 50 | 0.065 | 0.076 | 3.937 (2026Q2) | 51.0 | 50 | 0.065 | 0.076 | 3.937 (2026Q2) | 51.0 |
| Multifamily | Quarter-end nonaccrual | KeyBank, every kept quarter | 2006Q4 on | 79 | 0.130 | 0.185 | 7.841 (2010Q1) | 41.7 | | | | | |
| Multifamily | Quarter-end nonaccrual | KeyBank, every kept quarter | 2014Q1 on | 50 | 0.065 | 0.076 | 3.937 (2026Q2) | 51.0 | | | | | |
| Construction | TTM net charge-off | Industry | 2006Q4 on | 79 | 0.053 | 0.106 | 6.485 (2010Q1) | 60.8 | 79 | 0.053 | 0.105 | 6.477 (2010Q1) | 61.1 |
| Construction | TTM net charge-off | Industry | 2014Q1 on | 50 | -0.001 | 0.031 | 0.301 (2014Q1) | 9.9 | 50 | -0.001 | 0.030 | 0.301 (2014Q1) | 9.9 |
| Construction | TTM net charge-off | KeyBank, series written | 2006Q4 on | 44 | 0.009 | 0.042 | 0.311 (2017Q2) | 7.2 | 79 | 0.037 | 0.181 | 13.894 (2010Q2) | 76.4 |
| Construction | TTM net charge-off | KeyBank, series written | 2014Q1 on | 44 | 0.009 | 0.042 | 0.311 (2017Q2) | 7.2 | 50 | 0.004 | 0.049 | 0.726 (2016Q3) | 14.8 |
| Construction | TTM net charge-off | KeyBank, every kept quarter | 2006Q4 on | 74 | 0.037 | 0.128 | 12.161 (2010Q2) | 94.7 | | | | | |
| Construction | TTM net charge-off | KeyBank, every kept quarter | 2014Q1 on | 45 | 0.009 | 0.042 | 0.311 (2017Q2) | 7.1 | | | | | |
| Construction | Quarter-end nonaccrual | Industry | 2006Q4 on | 79 | 0.858 | 0.680 | 15.062 (2010Q1) | 20.9 | 79 | 0.848 | 0.670 | 15.046 (2010Q1) | 21.2 |
| Construction | Quarter-end nonaccrual | Industry | 2014Q1 on | 50 | 0.560 | 0.233 | 2.720 (2014Q1) | 9.3 | 50 | 0.557 | 0.233 | 2.716 (2014Q1) | 9.3 |
| Construction | Quarter-end nonaccrual | KeyBank, series written | 2006Q4 on | 79 | 0.151 | 0.224 | 18.023 (2010Q1) | 79.7 | 79 | 0.151 | 0.224 | 18.023 (2010Q1) | 79.7 |
| Construction | Quarter-end nonaccrual | KeyBank, series written | 2014Q1 on | 50 | 0.052 | 0.077 | 2.817 (2016Q2) | 36.0 | 50 | 0.052 | 0.077 | 2.817 (2016Q2) | 36.0 |
| Construction | Quarter-end nonaccrual | KeyBank, every kept quarter | 2006Q4 on | 79 | 0.151 | 0.224 | 18.023 (2010Q1) | 79.7 | | | | | |
| Construction | Quarter-end nonaccrual | KeyBank, every kept quarter | 2014Q1 on | 50 | 0.052 | 0.077 | 2.817 (2016Q2) | 36.0 | | | | | |

Quarters held: C&I nco: industry 2005Q4 to 2026Q2, KeyBank written 2026Q1 to 2026Q2, KeyBank kept 77; C&I na: industry 2005Q1 to 2026Q2, KeyBank written 2005Q1 to 2026Q2, KeyBank kept 86; Nonfarm nonresidential nco: industry 2005Q4 to 2026Q2, KeyBank written 2006Q1 to 2026Q2, KeyBank kept 82; Nonfarm nonresidential na: industry 2005Q1 to 2026Q2, KeyBank written 2005Q1 to 2026Q2, KeyBank kept 86; Multifamily nco: industry 2005Q4 to 2026Q2, KeyBank written 2010Q2 to 2026Q2, KeyBank kept 77; Multifamily na: industry 2005Q1 to 2026Q2, KeyBank written 2005Q1 to 2026Q2, KeyBank kept 86; Construction nco: industry 2005Q4 to 2026Q2, KeyBank written 2015Q3 to 2026Q2, KeyBank kept 77; Construction na: industry 2005Q1 to 2026Q2, KeyBank written 2005Q1 to 2026Q2, KeyBank kept 86
