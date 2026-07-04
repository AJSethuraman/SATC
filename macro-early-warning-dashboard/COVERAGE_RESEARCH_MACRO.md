# Coverage Research — Macro Early-Warning Monitor (FRED provider) (v1)

Research artifact feeding BUILD_SPEC_MACRO.md. Produced by a two-agent
verification pass (national lanes + geographic lane; every series ID verified
against its primary FRED URL, metadata corroborated via independent mirrors
where the proxy blocked direct fetches). Verdicts: **CONFIRMED** (primary URL +
metadata corroborated), **CONFIRMED (snippet)** (primary URL exists, some
metadata via snippets), **UNVERIFIED** (do not rely on). Re-verify flagged
items via the FRED API (`fred/series?series_id=...`) at build time.

## Bottom line

A macro early-warning template is fully buildable on FRED alone — the existing
FRED adapter is reused unchanged. **The watchlist lane is legitimately OPEN**:
three state-keyed families (unemployment rate, initial claims, Philly Fed
coincident index) are confirmed alive, timely, and joinable on a portfolio's
state footprint. Two licensing constraints (ICE BofA, UMichigan) and one
discontinued family (Philly Fed state *leading* indexes) shape the spec.

## National dashboard lanes (18 series, all CONFIRMED)

**Rates & Curve:** `T10Y3M` (daily, from 1982, H.15 — the headline inversion
signal), `T10Y2Y` (daily, from 1976), `T10Y3MM` (monthly counterpart, for
composite math). Public domain.

**Labor:** `SAHMREALTIME` (monthly, from 1959-12 — built from *real-time*
unemployment vintages; the canonical trigger: 3-month avg U-3 rising >= 0.50pp
above its 12-month low), `SAHMCURRENT` (from 1949-03 — revised-vintage
context; its whole history mutates with BLS revisions), `ICSA` / `IC4WSA` /
`CCSA` (weekly claims, from 1967; Thursday release; CCSA lags one extra week).

**Credit & Financial Conditions:** `BAMLH0A0HYM2` (HY OAS) and `BAMLC0A0CM`
(IG OAS) — **see licensing/truncation trap below**; `NFCI` / `ANFCI` (Chicago
Fed, weekly, mean-0/sd-1 back to 1971, released Wednesdays); `STLFSI4` (St.
Louis stress index — 4th vintage confirmed current; STLFSI/2/3 all carry
"(DISCONTINUED)"); `DRTSCILM` (SLOOS C&I tightening, quarterly — still
current); optional `KCFSI` (monthly complement, from 1990).

**Recession probability / shading:** `RECPROUSM156N` (Chauvet-Piger smoothed
probabilities — alive but publishes ~2-3 months behind; confirmatory lane,
never early-warning), `USREC` (NBER 1/0 dummy — chart shading only,
retroactive by ~a year).

**Housing:** `PERMIT` (permits, monthly SAAR from 1960 — the leading one),
`HOUST` (starts, from 1959). Census revision trap: latest 1-2 prints are
preliminary; use 3-month averages.

**Sentiment & Composite inputs:** `UMCSENT` (UMich sentiment — **see 1-month
delay trap**), `AWHMAN` (manufacturing weekly hours, from 1939), `NEWORDER`
(core capex orders, from 1992, nominal — LEI deflates it, FRED copy is not;
recency of sibling `ACOGNO` UNVERIFIED, check at build).

**Excluded (verified dead or absent):** `TEDRATE` (discontinued Jan 2022 with
LIBOR's removal; no drop-in FRED successor — use NFCI/STLFSI4 funding
components instead), Cleveland `CFSI` (discontinued 2016 after calculation
errors), Conference Board LEI / Consumer Confidence (**not on FRED**,
proprietary — the spec composes a free LEI-style proxy from ICSA, PERMIT,
T10Y3MM, UMCSENT, AWHMAN, NEWORDER instead).

## Geographic watchlist lane (state join key — the lane is OPEN)

**Admitted families (3):**

1. **State unemployment rate — `{ST}UR`** (SA) / `{ST}URN` (NSA). Monthly,
   percent, all 50 states + DC, from 1976, ~3-week lag. Spot-verified CA, TX,
   NY, OH, FL, DC both variants. FRED release `rid=112`; release dates via
   `fred/release/dates` — **2026 BLS dates float between Friday and Tuesday,
   never hardcode a weekday rule.**
2. **State initial claims — `{ST}ICLAIMS`** (+ `{ST}CCLAIMS`). Weekly, **NSA
   only**, from 1986-87, ~10-day lag — the timeliest tripwire. Spot-verified
   CA, TX, NY, OH, FL. MUST be consumed as 4-week MA and/or YoY of the 4-week
   MA — raw weekly deltas are holiday/backlog noise (California notoriously).
3. **Philly Fed State Coincident Index — `{ST}PHCI`** (+ `USPHCI` national).
   Monthly, SA index, 50 states (**no DC** — join-key gap), from 1979, ~4-5
   week lag. Spot-verified CA, TX, NY, OH, FL, PA, US. **Alive** (last updated
   May 2026) with 2025 disruptions: no October 2025 report (the BLS household
   survey for that month was never collected — appropriations lapse) and a
   methodology change effective the Nov 2025 release; all 50 models re-estimate
   each spring on the BLS benchmark, so the whole history revises annually.

**REFUTED-equivalent / excluded from the lane:**
- **Philly Fed State *Leading* Indexes (`{ST}SLIND`, `USSLIND`) are
  DISCONTINUED** — data frozen at Feb 2020 (COVID claims spike broke the
  model; Philly Fed formally decided in 2025 not to resume). The series still
  *return data without erroring* — the #1 silent-staleness trap. The leading
  signal is replicated with permits + claims + the national yield curve.

**Dashboard-context only (confirmed but not watchlist rows):**
- State building permits `{ST}BPPRIV` / `{ST}BPPRIVSA` / `{ST}BP1FH(SA)`
  (monthly from 1988; lag ~6-8 weeks UNVERIFIED precisely).
- **`EQFXSUBPRIME{6-digit FIPS}`** — % of county population with Equifax Risk
  Score < 660, quarterly, NY Fed CCP/Equifax, alive through Q4 2025, small
  counties suppressed. County-FIPS-keyed and tempting for the watchlist, BUT:
  quarterly + 1-2 quarter lag + suppression + **FRED licensing note
  UNVERIFIED** (FRBNY/Equifax data normally carries required-citation terms —
  read the series notes before shipping). Context lane in v1; candidate for
  promotion after license review.
- County unemployment `{ST}{mnemonic}{digit}URN` (monthly NSA from 1990,
  ~3,100 counties, ~2-month lag). **The disambiguator digit is NOT derivable
  from FIPS** (CALOSA7URN, ILCOOK1URN, TXHARR1URN, OHCUYA5URN, FLMIAM6URN) —
  seed lists must be enumerated via `fred/release/series?release_id=116`
  (26,010 series) or tags, never constructed. Practical under the rate limit
  (50-300 series = 1-3 min at 0.6s/req). On-demand footprint drill-down, not
  standing rows.
- State real GDP `CARQGSP` — convention across states UNVERIFIED (1 of 5 spot
  checks); context at best.

**HPI continuity check (complementary to the FRED template, not duplicated):**
FHFA `{ST}STHPI` and `ATNHPIUS{cbsa}Q` unchanged and live through Q1 2026;
Case-Shiller series live, IDs unchanged, but rebranded **"S&P Cotality
Case-Shiller"** (CoreLogic -> Cotality).

## Licensing flags (must be honored in spec + _readme)

1. **ICE BofA OAS series (`BAMLH0A0HYM2`, `BAMLC0A0CM`): third-party "Top
   Level Data".** FRED terms: ICE has exclusive proprietary rights, access can
   terminate, ICE is a third-party beneficiary entitled to enforce. AND — as
   of **April 2026 FRED serves only a rolling 3-year window** (pre-2023
   history gone; corroborated across 9+ ICE series pages; re-verify note text
   via API at build). Consequences: display-only with attribution ("© Ice Data
   Indices, LLC"), current-level/3-yr-percentile tiles only, long-run
   thresholds (e.g., "HY OAS > 800bp = crisis") documented as static
   references, never computed; embedding cached values in a shared workbook is
   a **flag-for-legal item**.
2. **`UMCSENT`: source-mandated 1-month delay** (verified verbatim: "At the
   request of the source, the data is delayed by 1 month") + © University of
   Michigan attribution. Label the tile "as of prior month"; never diff
   against same-month series.
3. **FRED API terms (June 2024 update):** no storing/caching/archiving for
   redistribution, no third-party proprietary content redistribution without
   owner permission, no AI/ML training use, API key mandatory. Fed/Treasury/
   BLS/Census-sourced series are unproblematic for an internal workbook; the
   ICE + UMich series are the gray zone — keep them display-lane only.

## Operational facts (CONFIRMED)

- FRED API limit **120 requests/minute** (HTTP 429 over; the existing
  adapter's 0.6s throttle + backoff is compliant — keep it).
- `fred/release/dates?release_id={112,116}` gives deterministic release
  calendars for the state data.
- ALFRED vintages exist for UNRATE (from 1960), ICSA, DRTSCILM, UMCSENT,
  BAMLH0A0HYM2 (2023+ only) — enough for the Sahm real-time distinction.
- Seed enumeration for county/state families:
  `fred/release/series?release_id=...` and `fred/tags/series?tag_names=...`.

## Top data-quality traps (bake into spec §traps + stale-check)

1. **Frozen-series trap** — `{ST}SLIND` returns data ending Feb 2020 without
   erroring. The runner MUST check last-observation recency against each
   series' cadence, not just fetch success, and surface staleness.
2. **ICE BofA 3-year window** — percentile/threshold logic must not assume
   full-cycle history.
3. **October 2025 hole** — state household-survey data never collected;
   `{ST}UR` has a gap and `{ST}PHCI` skipped the month + changed methodology.
   Transforms must tolerate interior missing months.
4. **Annual benchmark revisions (Jan-Mar)** — LAUS re-benchmarks and all 50
   PHCI models re-estimate; entire state histories revise every spring.
5. **NSA noise** — state claims (and county URN) are NSA-only; alert only on
   4-week-MA/YoY transforms, never raw deltas.
6. **Revision/lag asymmetries** — UMCSENT 1-month delay; RECPROUSM156N 2-3
   months behind (confirmatory); PERMIT/HOUST preliminary prints; CCSA one
   week behind ICSA; SAHMCURRENT history mutates.
7. **Series-ID churn** — STLFSI→…→STLFSI4, TEDRATE, CFSI show FRED retires
   IDs; surface the "(DISCONTINUED)" title flag rather than serving stale data.

## Open questions (UNKNOWN — flag, never assert)

1. Exact current text of the ICE BofA truncation note and whether cached
   values in an internally-shared workbook are permissible — legal review.
2. FRED licensing note on the `EQFXSUBPRIME*` family (promotion candidate for
   the watchlist if terms allow).
3. `ACOGNO` recency; `{ST}RQGSP` convention beyond CA; `{ST}BPPRIV` exact lag;
   `{ST}INSUREDUR` convention; PR coverage of `{ST}UR`.
4. Whether FRED tagged `{ST}SLIND` titles "(DISCONTINUED)" (frozen either way).
