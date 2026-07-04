# Coverage Research — CFPB Mortgage Performance Trends (v1)

Single-agent deep pass. Evidence quality is unusually strong: an ACTUAL
county CSV was downloaded and inspected (2019-03 vintage, verbatim mirror)
AND the CFPB's own open-source generator script that produces these files
was read — so the schema is confirmed by both the data and the code that
writes it. Live cfpb hosts were proxy-blocked; current-vintage facts rest on
search snippets of the exact primary URLs (marked). Verdicts: CONFIRMED /
LIVE-VERIFIED(snippet) / UNVERIFIED.

## Bottom line

The only free public source of **actual mortgage credit OUTCOMES at county
level, monthly, joinable on 5-digit county FIPS** — the county delinquency
lane the bureau template couldn't get without a license. Public domain, no
key, six tiny CSVs (46-442 KB). Watchlist verdict: **OPEN on a clean county
FIPS key** (after stripping the deliberate Excel-protective quote wrapping).

## The files (CONFIRMED pattern; vintage via snippet)

```
https://files.consumerfinance.gov/data/mortgage-performance/downloads/
  {State|MetroArea|County}MortgagesPercent-{30-89|90-plus}DaysLate-thru-{YYYY-MM}.csv
```
- **Filenames are DATED** (`-thru-2025-09.csv` current, published Apr 2026,
  data Jan 2008 - Sep 2025). Hardcoded URLs die every release; the CFPB's
  own ecosystem discovers filenames by scraping the download page — the
  live adapter must do the same.
- Sizes: state 46 KB, metro 302 KB, county 442 KB per measure.

## Schema (CONFIRMED from the actual file + generator source)

```
RegionType,State,Name,FIPSCode,2008-01,2008-02,...,2025-09
National,,United States,-----,3.5,...
County,AL,Baldwin County,'01003',2.8,...
```
- **WIDE**: one row per county, one column per month (~213 now). New
  columns appear each release — parse by YYYY-MM header pattern, never
  position.
- **FIPS is 5-digit zero-padded WRAPPED IN LITERAL SINGLE QUOTES**
  (`'01003'`) — deliberate, per the generator: "so Excel doesn't strip
  leading zeros." Strip before joining; keep as text.
- Values are **percent, 1 decimal** (3.5 = 3.5%). National row has
  `FIPSCode="-----"` — filter by RegionType. State file: 2-digit quoted
  FIPS. Metro file mixes CBSA codes + synthetic `XX-non` non-metro keys
  (no FIPS join — skip in a lean build). Puerto Rico excluded.

## Coverage / suppression (CONFIRMED)

Inclusion: county average >= **1,000 sample mortgages** in the threshold
year (fixture: threshold_year 2016) — in a 5% sample that's ~20,000 real
mortgages, i.e. a big-county filter. Result: **469 counties** (of ~3,100)
in the inspected vintage (~470 estimated now — UNVERIFIED exactly).
**Suppressed counties are ABSENT from the file** — absence is not zero.
Rural footprints: fall back to the state row.

## Cadence / revisions (CONFIRMED)

Monthly series, published **~semiannually with a ~6-7 month lag** (cadence
not formally promised). **Every vintage revises the FULL history** ("rates
may change between updates due to updated credit data") — full-replace on
refresh, never append, never diff stored vs new history as "movement";
record the vintage (`thru-YYYY-MM`) as provenance.

## Provenance / definition (CONFIRMED)

NMDB (joint CFPB/FHFA): nationally representative **5% (1-in-20) sample**
of outstanding closed-end first-lien 1-4-family mortgages, credit-repository
sourced. 30-89 DPD = one-two missed payments / all outstanding; 90+ = three
or more. Credit-record buckets, not MBA survey rates.

## Licensing (CONFIRMED)

U.S. government work — public domain (17 U.S.C. s105). No key, no terms, no
attribution requirement (credit "CFPB Mortgage Performance Trends (NMDB)"
as good practice).

## Continuity risk — MODERATE (CONFIRMED alive)

Fresh vintage published April 2026 (post-2025 CFPB turmoil), but the
dataset was community-archived to DataLumos during the 2025 data-rescue
wave (that archive = recovery mirror), and cadence is informal. Tripwire:
alert if no new vintage within 9 months. Partial fallback: FHFA NMDB
Aggregate Statistics (state/CBSA, quarterly — NOT county-monthly;
details UNVERIFIED, fhfa.gov blocked). The county lane has no like-for-like
substitute.

## Traps (bake into spec)

1. Quoted FIPS — strip `'` or every join silently fails; never let Excel
   coerce to number.
2. Dated filenames — discover via the download page each refresh.
3. Full-history revisions — full-replace; label the vintage.
4. Suppression by omission — absent county != zero; surface "SUPPRESSED,
   use state row".
5. Wide format — unpivot by header pattern.
6. ~6-7 month lag — confirming indicator, not a nowcast; label as-of.
7. National row mixed into every file — filter by RegionType.

## Open questions (UNKNOWN — flag)

Six literal current URLs (pattern solid; page blocked here) · exact county
count in thru-2025-09 · whether threshold_year ever moved off 2016 · FHFA
fallback exact geography/frequency.
