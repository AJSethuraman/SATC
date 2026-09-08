# Verified raw data — 5 September 2026

Everything here is a number somebody else published, copied without change, with
a note saying where it came from and whether it was checked against that source.

**Nothing in this folder is calculated by this software.** No ratios, no
quarter-on-quarter changes, no scores, no bands. If a number is here, a bank or
a government agency published it in that form.

## The files

| File | What's in it | Rows |
|---|---|---|
| `bank-values.csv` | Twelve large US banks, sixteen quarters, every reported field | 13,056 |
| `macro-observations.csv` | 142 national and regional series, most recent 100 observations each | 13,841 |
| `field-dictionary.csv` | What each bank field means, in plain English | 68 |
| `not-comparable-periods.csv` | Quarters you should not chart as a trend, and why | 6 |
| `ratios-worth-building.csv` | Ratios that make sense, and the traps — **descriptions only, nothing computed** | 18 |
| `verification-summary.json` | The counts below, machine-readable | — |

## How much of it is verified

**22,819 of 26,897 values were checked against the document that published
them. None disagreed.**

| | Count | |
|---:|---|---|
| **11,478** | bank values | matched the bank's own filed Call Report, quarter by quarter |
| **11,341** | macro observations | matched the agency that computes the series |
| **1,536** | bank values | ratios the **FDIC** calculates from filed lines — not a line on any form, so there is nothing to check them against. The lines underneath them are checked |
| **2,500** | macro observations | no free historical source exists (see below) |
| **42** | bank values | quarterly flows in a quarter that spans a merger — see *not comparable* |
| **0** | anything | disagreed with its source |

### What "verified" means here

For a bank value: the number in this file was compared with the same line on
that bank's own Call Report for that quarter, downloaded from the federal
regulator, matched by its MDRM code — the permanent identifier for one line on
the form. The `filing_url` column opens the exact filing. You can check any row
yourself in about a minute.

For a macro series: the number was compared against the file published by the
body that *computes* it — FHFA for house prices, the Federal Reserve Board for
bank charge-off rates, consumer credit, debt-service ratios and the loan officer
survey. Not against FRED, which only redistributes them. Asking a redistributor
whether the redistributor is right proves nothing.

### The 2,500 that could not be verified

Three reasons, all about what the publisher gives away free:

- **2,200 — Case-Shiller house prices (22 series).** S&P publishes only the
  current month free. The most recent month is verified against their release;
  the history is not available without a subscription.
- **200 — two consumer credit series.** The Federal Reserve publishes no
  historical table for the unadjusted level or the percent change. The current
  month is verified against the current release.
- **100 — one loan-officer survey series.** The large-banks split appears only
  inside each quarter's own survey document, so a full history would mean about
  a hundred separate documents.

They are marked `verified = no` with the reason in the file. They are not
marked as fine.

## Two things to know before charting

**1. Merger quarters.** When a bank absorbs another bank, its quarterly
charge-off figures for that quarter mix two banks and are not a quarter of
anything. Six such quarters are listed in `not-comparable-periods.csv`, and the
affected rows carry `usable_for_trend = no`. Balances are point-in-time and are
unaffected — only the flows.

This is not a theoretical worry. One of these produced a charge-off rate of
**670%** in an earlier version of this work, which is what a merger looks like
when nobody flags it.

**2. Units.** Bank values are **thousands of dollars** unless the row says
otherwise. A bank total of `4,091,315,000` means $4.09 trillion. Macro series
carry their own units per row.

## Where the numbers come from

- **Banks** — the Federal Financial Institutions Examination Council, which
  publishes every bank's filed Call Report: `https://cdr.ffiec.gov`
- **House prices** — the Federal Housing Finance Agency: `https://www.fhfa.gov/hpi`
- **Bank charge-off and delinquency rates, consumer credit, debt-service ratios,
  the loan officer survey, and the financial accounts** — the Federal Reserve
  Board: `https://www.federalreserve.gov`
- **Case-Shiller house prices** — S&P Dow Jones Indices

## What is deliberately not here

- **Any ratio this software calculated.** Removed at the firm's instruction.
  `ratios-worth-building.csv` describes the ones worth building and the traps in
  each, and computes none of them.
- **Scores, bands, alerts, trends.** All of it was arithmetic on top of these
  numbers. The numbers are the deliverable.
- **The eight ratios the FDIC computes** are still here, because the FDIC
  published them — but they are labelled `computed_by = the FDIC` so you always
  know whose arithmetic you are looking at.

## Cautions — read these before you chart anything

**1. This is a window, not a history.** The macro series are capped at the most
recent **100 observations** each. That is about 25 years for a quarterly series
and only about **8 years for a monthly one** — monthly series start in early
2018. The publishers hold far more: FHFA back to 1975, consumer credit to 1943,
Case-Shiller to 1987. If you want the long run, it exists and this file does not
have it. Bank data is **16 quarters**, from 2022 Q3.

**2. There is no vintage.** These are the figures as published when they were
pulled. Banks amend Call Reports and agencies revise series, so a value verified
today may not match the same source in six months. Nothing here records when a
figure was fetched or which revision it is. Treat the whole folder as a snapshot
dated 5 September 2026.

**3. Provenance is much stronger on the bank side.** Every one of the 13,056
bank rows names its exact line (the MDRM code) and links to the exact filing —
you can click through and put a finger on the number. On the macro side the
link is the agency's **landing page**, not the row: 10,941 of 11,241 verified
rows point at a page you would then have to search. The check was done against
the exact file; the link in the CSV is coarser than the check.

**4. Eight of the bank fields are ratios.** They are the FDIC's ratios, not
ones this software built, and they are labelled `computed_by = the FDIC`. But
they are still ratios sitting in a raw-data feed. If you want the feed to be
purely filed lines, drop the 1,536 rows where `verified_meaning` mentions the
FDIC calculating them.

**5. The twelve banks are not a like-for-like peer group.** Two are custody
banks and two are broker-dealer banks. Their balance sheets are shaped nothing
like a commercial lender's, and a peer ranking that mixes them will mislead.

## What this still does not prove

- A value can match its filing exactly and the filing can still be wrong. This
  proves faithful copying, not that a bank reported correctly.
- The 2,500 unverified observations above.
- Nothing here was checked by a second person.
