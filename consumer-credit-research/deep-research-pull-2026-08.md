# Consumer credit data pull — deep-research run, 2026-08-11

**Purpose.** A breadth-first *data grab* (not analysis) to build the range of
values — normal → stressed — behind consumer credit-risk-review thresholds:
gross/net charge-offs, recoveries, delinquency by bucket, non-accrual, and any
public PD/loss proxy, cut by Key's consumer segments, super-regional peers,
national system series, consumer ABS, and footprint states, quarterly back to
2019.

**Run.** `/deep-research` harness — 5 hardcoded provenance-tiered search angles →
27 sources fetched → 18 falsifiable claims extracted → 18 adversarially verified
(2/3-vote), 0 killed.

---

## ⚑ Read this first — what this run could and couldn't do

**The granular pull did not land, and the reason is environmental, not the
prompt.** This session's **network egress proxy blocks the primary numeric
sources**. Confirmed blocked by direct test:

| Domain | Status | What we lost |
|---|---|---|
| `federalreserve.gov` | **EGRESS_BLOCKED** | Fed Charge-Off & Delinquency release (the backbone series + top-100-vs-other-banks splits) |
| `fred.stlouisfed.org` | **EGRESS_BLOCKED** | Every FRED series (quarterly history back to the 1980s) |
| `sec.gov` (EDGAR) | **EGRESS_BLOCKED** | KeyCorp + all peer 10-Q/10-K segment asset-quality tables |
| `fdic.gov`, `kbra.com`, S&P | fetched as "unreliable", 0 claims | FDIC QBP; consumer-ABS delinquency/loss by score band |

The search engine returns *snippets*, so the harness could confirm a source
**exists** and read its abstract — but every attempt to fetch the actual data
page failed. Result: the 18 verified claims are **national-level context and
"where the data lives" metadata**, not the segment × peer × quarter values.
This matches the README's standing note that Fed/FRED figures are snippet-sourced
under a session egress block and need the **unblocked work desk** to pull.

**Second, smaller issue:** the harness's final *synthesize* step returned a
placeholder (`"test"`) — a known structured-output serialization drift on the
largest payload. The tables below are **recovered directly from the per-agent
extraction journal**, not from the broken synthesis, so no real data was lost to
that bug.

---

## 1. What the run *did* capture (verified, provenance-tagged)

### 1a. National residential mortgage delinquency — MBA National Delinquency Survey, Q1 2026
`[PROXY]` for Key's residential first-mortgage segment (national, not Key-specific).
Source: MBA press release, 2026-05-14. Seasonally adjusted, 1–4 unit residential.

| Metric | Q1 2026 | QoQ | YoY |
|---|---|---|---|
| Total delinquency rate | **4.44%** | +18 bps | +40 bps |
| 30-day (early-stage) | **2.24%** | +17 bps | — |
| Conventional | **2.75%** | −14 bps | — |
| FHA | **11.88%** | +36 bps | — |
| VA | **4.99%** | +39 bps | — |
| Foreclosure starts | **0.24%** | +4 bps | — |

*Read:* stress concentrated in government-guaranteed (FHA/VA), not conventional;
FHA foreclosure inventory highest since Q4 2018, VA highest since Q2 2017.

### 1b. Income-stratified serious (90+) mortgage delinquency — NY Fed Liberty Street Economics, 2026-02-10
`[PROXY / INFERRED]` — national, income-zip stratified; snippet-sourced (page egress-blocked, verify verbatim).

| Series | Value |
|---|---|
| 90+ DPD, lowest-income zips | ~0.5% (2021) → **~3.0% (late 2025)** |
| 90+ DPD, highest-income zips | historically low, ~flat |
| Share of balances → seriously delinquent in 2025 | **~1.3%** (≈ non-recession historical avg) |
| Local unemployment linkage | 2/3 of counties rising; worst clustered in FL, MN (**outside Key footprint**) |

*Read:* a usable normal-vs-stressed calibration point — national serious-delinquency
transition sits near ~1.3% "normal," with the tail concentrated by income and
local-unemployment/HPI conditions (supports HPI + unemployment as footprint covariates).

### 1c. Super-regional peer cross-section, Q2 2026 — `credaily` aggregator (secondary)
`[PROXY]` but **CRE-focused, tangential** to the consumer ask — captured for completeness only.

| Bank | Metric (Q2 2026) |
|---|---|
| Citizens | CRE charge-off rate **0.36%** |
| PNC | total nonperforming loans **−10%** QoQ |
| KeyCorp | nonperforming-asset ratio **+11 bps** (total book, CRE-driven) |
| Huntington | nonperforming-asset ratio **+13 bps** |

*Caveat:* these are **total-book / CRE** figures, not consumer-segment. Do not
use as consumer read-across.

### 1d. Reference-data availability (metadata, not values)
- **NY Fed HHDC Q2 2026** `[DIRECT, primary]` — release **confirmed 2026-08-11, 11:00 AM ET** (covers mortgage, student, credit card, auto). Data itself not yet fetchable at run time.
- **FHFA HPI** `[DIRECT, primary]` — state-level quarterly, back to mid-1970s; Purchase-Only vs All-Transactions methodologies (comparability caveat); available to ZIP/tract for sub-state footprint cuts. CSV/JSON master files.

---

## 2. Turnkey source map — for an unblocked pull

Everything the grab was *meant* to retrieve, with the exact reachable location and
provenance tier. Run this list from the **work desk (unblocked egress)** and the
pull is mechanical. FRED series IDs are the stable public identifiers.

### 2a. National system series — Fed Charge-Off & Delinquency (FRED) `[DIRECT]`
Quarterly, SA, All Commercial Banks unless noted. Base: `fred.stlouisfed.org/series/<ID>` or CSV `.../graph/fredgraph.csv?id=<ID>`.

| Metric | Series ID |
|---|---|
| Delinquency — single-family residential mortgage | `DRSFRMACBS` |
| Delinquency — credit cards | `DRCCLACBS` |
| Delinquency — consumer loans | `DRCLACBS` |
| Delinquency — credit cards, **top 100 banks** | `DRCCLT100S` |
| Delinquency — credit cards, **other (smaller) banks** | `DRCCLOBS` |
| Delinquency — all loans | `DRALACBS` |
| Net charge-off — single-family residential mortgage | `CORSFRMACBS` |
| Net charge-off — credit cards | `CORCCACBS` |
| Net charge-off — consumer loans | `CORCACBS` |
| Net charge-off — credit cards, top 100 / other | `CORCCT100S` / `CORCCOBS` |

*(Fed HTML equivalents at `federalreserve.gov/releases/chargeoff/` — `delallsa.htm`, `chgallsa.htm`.)*
**Comparability caveat:** Fed series are **net** charge-offs, annualized; gross charge-offs and recoveries separately require FFIEC Call Report Schedule RI-B, not this release.

### 2b. Key & peer segment tables — SEC EDGAR 10-Q/10-K `[DIRECT]`
Base: `sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<CIK>&type=10-Q`.
Consumer credit-quality Notes hold NCO by category, delinquency/accruing-past-due
buckets, nonaccrual, and CECL allowance by segment.

| Bank | CIK | Segment detail expected |
|---|---|---|
| KeyCorp | `0000091576` | resi mortgage, home equity, consumer direct, credit card, Laurel Road, consumer indirect (run-off) |
| Fifth Third | `0000035527` | resi, home equity, auto, card, other consumer |
| Regions, Huntington, Citizens, M&T, Comerica, Truist, PNC, US Bancorp | (look up per EDGAR) | segment NCO/delinquency/nonaccrual where broken out |

**Caveat:** GCO + recoveries are rarely split by consumer sub-segment in the 10-Q;
usually only **net** charge-offs and allowance. True gross split → Call Report RI-B.

### 2c. Consumer ABS by score band `[PROXY]`
- **KBRA** consumer-loan / auto ABS indices (`kbra.com/publications/...`) — 30/60/90-DPD, net loss, recovery by trust.
- **S&P Global Ratings** U.S. Auto Loan ABS Tracker — prime vs subprime delinquency/loss.
- **SoFi / Nelnet / Navient** ABS trust reports + issuer 10-Qs (EDGAR) — student-refi performance as the **Laurel Road** read-across.

### 2d. Footprint-state macro `[DIRECT]`
- **FHFA HPI** — state quarterly (`fhfa.gov/data/hpi/datasets`), Purchase-Only.
- **BLS LAUS** — state unemployment (`bls.gov/lau/`).
- **MBA NDS** / **CFPB Mortgage Performance Trends** — delinquency by state.

---

## 3. Gaps — internal data only (public pull cannot cover)

Confirmed *not* publicly available at the needed granularity; must come from Key's
internal systems:

- **Key's own segment GCO + recoveries split** (10-Q gives net only) → recovery rate by segment.
- **FICO × vintage PD / loss curves** and **true WAPD** — no public equivalent; ABS-by-score-band is only a coarse proxy.
- **Laurel Road cohort performance** (healthcare/professional borrower cuts) — no public benchmark; student-refi ABS is a distant proxy.
- **HELOC utilization / draw-to-repayment reset schedule** by vintage.
- **Footprint concentration vs. internal limits.**

## 4. Confidence & open questions

- **Confidence: low on coverage, high on provenance.** What was captured is
  correctly sourced and verified, but it is a small national-context slice of the
  requested grab — the segment × peer × quarter matrix is **not** in this run.
- **Root cause is fixable:** re-run the identical pull from an **unblocked-egress
  environment** (the work desk that already reaches Fed/FRED/SEC), using the §2
  source map. That converts this from "context + pointers" into the actual
  time-series tables.
- **Open:** NY Fed HHDC Q2 2026 data (released 2026-08-11) was not yet fetchable at
  run time — pull the report itself for the national mortgage/card/auto/student
  90+ transition series.

---

*Method note:* tables in §1 are recovered from the deep-research per-agent
extraction journal (`wf_7add90bc-515`), each claim adversarially verified 2/3-vote.
The harness's synthesize step failed to a placeholder and was bypassed. Snippet-
sourced items (pages egress-blocked) are flagged inline and should be verified
verbatim from an unblocked machine before use in threshold-setting.
