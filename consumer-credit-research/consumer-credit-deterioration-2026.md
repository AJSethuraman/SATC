# Consumer Credit Deterioration — Signals for a Credit-Risk-Review Assessment

**Purpose.** A primary-source reference for adjusting a consumer credit-risk-review
process: which public indicators to weight, what they lead or lag, where
deterioration concentrates, and — critically — what aggregate public data can and
cannot tell you about *your* portfolio's segments.

**As of:** 2026-08-10. Every figure is stamped with its source release/quarter.
**Scope:** US consumer credit — credit card, auto, first-lien mortgage, HELOC,
personal/other, student. Bank credit-risk-review (second-line) perspective.

> ### ⚠ Sourcing integrity note — READ BEFORE QUOTING
> This session's environment **blocked direct WebFetch to every primary domain**
> (`fred.stlouisfed.org`, `federalreserve.gov`, `fdic.gov`, `newyorkfed.org`) under
> an egress policy. Figures below were therefore reconstructed from **web-search
> snippets that quote those primary releases**, cross-checked across multiple
> results — **not** from a direct read of the primary PDF/FRED table. They are
> high-confidence-directional but **must be confirmed to the basis point against
> the cited primary URL before use in any formal credit deliverable.** Figures I
> could not pin down are marked **⚑ CONFIRM**. This is exactly the seam a review
> process should enforce: cite the primary, don't trust the secondary.
>
> **Freshness:** NY Fed HHDC **Q2 2026 releases 2026-08-11 (tomorrow)** and will
> supersede the Q1 2026 stock figures here. Fed charge-off Q2 2026 posts ~late
> Aug. Re-pull then.

---

## 1. The definitions you must pin down first

Different releases count "delinquency" differently. Reconciling them is the whole
game — a process that mixes them will double-count or miss a turn.

| Term | Who defines it | What it counts |
|---|---|---|
| **Delinquency rate (Fed Charge-Off & Delinquency release)** | Federal Reserve Board | Loans **30+ days past due and still accruing** interest, **plus nonaccrual**, ÷ end-of-period balances; SA; **commercial-bank book only**. Source: FFIEC Call Reports. [about.htm](https://www.federalreserve.gov/releases/chargeoff/about.htm) |
| **Serious delinquency (NY Fed HHDC)** | NY Fed / Equifax | Balances **90+ days past due** ÷ balances; **whole consumer-credit-report universe** (banks + finance cos + credit unions). [HHDC](https://www.newyorkfed.org/microeconomics/hhdc) |
| **Transition into delinquency (NY Fed HHDC)** | NY Fed / Equifax | **Flow** — share of *current* balances that moved to 30+ (or to 90+) this quarter. The leading-edge measure. |
| **Net charge-off rate (Fed / FDIC)** | Fed Board / FDIC | Gross charge-offs **minus recoveries**, annualized, ÷ average balances. A *lagging*, realized-loss measure. |
| **Noncurrent / PDNA rate (FDIC QBP)** | FDIC | Loans **90+ days past due plus nonaccrual**. FDIC's headline asset-quality gauge. [QBP](https://www.fdic.gov/analysis/quarterly-banking-profile) |

**Why the seams matter for a review process:**
- The **bank** series (Fed release / FDIC) cover only the commercial-bank book; the
  **NY Fed** series cover the whole consumer-credit-report universe. A divergence
  between them is **signal, not noise** — and right now they *are* diverging (§4).
- Bank delinquency (30+, accruing) turns **before** noncurrent (90+/nonaccrual),
  which turns **before** charge-offs. Watching only charge-offs is watching the past.

---

## 2. The delinquency → charge-off lag (the spine of early warning)

```
transition-into-30+  →  30-89 DPD  →  90+ DPD / nonaccrual  →  charge-off
   (flow, earliest)      (early)        (mid; "serious")        (realized loss)
```

- **Credit cards:** charge-off is generally mandated at **180 days past due**
  (FFIEC Uniform Retail Credit Classification policy). So today's card NCO rate
  largely reflects delinquency **~2 quarters ago**; today's **flow-into-90+** leads
  the card NCO rate by ~1–2 quarters. ⚑ CONFIRM exact FFIEC URCC thresholds at
  [ffiec.gov](https://www.ffiec.gov/) before quoting policy.
- **Closed-end consumer (auto, personal):** classification/charge-off generally at
  **120 days**.
- **Mortgage:** loss realization lags far longer (foreclosure timelines), so
  mortgage NCOs are a poor early-warning tool — watch mortgage **transition-into-
  serious-delinquency** instead.

**Practical read** — rank indicators by lead time; weight leading ones for
*adjustment* decisions, lagging ones for *confirmation*:

| Lead | Indicator | Use |
|---|---|---|
| Earliest | NY Fed **transition into delinquency** (flow to 30+, to 90+) | Detect the turn |
| Early | Bank **30-89 DPD** by product | Size the early bucket |
| Forward | SLOOS **lending-standard** net tightening | Credit-box / supply signal |
| Mid | **90+ / noncurrent** (FDIC, NY Fed serious) | Confirm migration |
| Lagging | **Net charge-off** rate | Confirm realized loss; calibrate LGD |

---

## 3. Current readings by product

> All figures **snippet-sourced (see integrity note), confirm against primary
> before formal use.** Bank series = commercial-bank book (Fed/FDIC); NY Fed =
> whole consumer-report universe.

### 3.1 Credit card
| Measure | Latest | Trend | Baseline / context | Source |
|---|---|---|---|---|
| Serious delinquency, 90+ (**whole market**) | **13.1%** of balances | **Rising — ~15-year high** | far above pre-2020 | NY Fed HHDC **Q1 2026** (3/31/26) |
| Delinquency, 30+ accruing+nonaccrual (**bank book**, DRCCLACBS) | **2.92%** | **Falling** 4 qtrs (Q4'24 3.08→Q1'26 2.92) | 2019 ~2.6%; peak ~3.2% (2024) ⚑ | [DRCCLACBS](https://fred.stlouisfed.org/series/DRCCLACBS) **Q1 2026** |
| — large issuers only (DRCCLT100S, top-100 banks) | **2.84%** | Falling (Q4'25) | small-bank tail (DRCCLOBS) runs much higher | [DRCCLT100S](https://fred.stlouisfed.org/series/DRCCLT100S) **Q4 2025** ⚑ Q1'26 |
| Net charge-off (bank, CORCCACBS) | **4.11%** | Off the peak, ~flat/easing | peak **4.58%** Q4'24; 2019 ~3.6% ⚑; 2009 peak 10.54% | [CORCCACBS](https://fred.stlouisfed.org/series/CORCCACBS) **Q4 2025** ⚑ Q1'26 |
| Flow into 30+ (whole market) | **8.6%** | Down from 8.7% | — | NY Fed HHDC Q1 2026 |
| Flow into 90+ (whole market) | "mostly unchanged" ⚑ | Flat | — | NY Fed HHDC Q1 2026 |

**Note:** one search returned CORCCACBS "8.10% Q1 2026" — **rejected as a search
artifact** (inconsistent with the ~4% run); anchor on 4.11% (Q4'25) until FRED
confirms Q1'26.

### 3.2 Auto
| Measure | Latest | Trend | Source |
|---|---|---|---|
| Serious delinquency, 90+ (whole market) | **5.6%** of balances | **Rising — highest since 2003** (~+12% YoY) | NY Fed HHDC Q1 2026 |
| Flow into 90+ (4-qtr basis) | **2.97%** | vs 2.94% a yr ago — ~flat/marginally up (NY Fed flags this as the key auto signal) | NY Fed HHDC Q1 2026 |
| Flow into 30+ | held **steady** | Flat | NY Fed HHDC Q1 2026 |

Auto stress skews **subprime / younger borrowers**; captured only partly by the
bank book (much auto credit is finance-company/captive — outside Fed/FDIC series).

### 3.3 First-lien mortgage
| Measure | Latest | Trend | Source |
|---|---|---|---|
| Delinquency (bank book, DRSFRMACBS) | **1.78%** | Flat/stable ~1.7–1.8% since 2022 | [DRSFRMACBS](https://fred.stlouisfed.org/series/DRSFRMACBS) **Q4 2025** ⚑ Q1'26 |
| Flow into serious delinquency (whole market) | **1.5%** | **Rising** — up from 1.4% (the one clear flow deterioration) | NY Fed HHDC Q1 2026 |
| Foreclosures | — | Up **slightly** QoQ | NY Fed HHDC Q1 2026 |
| Stock 90+ level | **not reported** in accessible sources ⚑ | described "still solid" | NY Fed HHDC Q1 2026 |

Mortgage is the **one product where the leading flow is deteriorating** while the
level is still low — worth flagging even though the level looks benign.

### 3.4 HELOC
Balance **$446B**, 16th straight quarterly rise (+$129B off the 2022 low) — HELOC
utilization is climbing as a cash-out substitute in a high-mortgage-rate world.
Delinquency level **not reported** in accessible sources ⚑. Source: NY Fed HHDC Q1 2026.

### 3.5 Personal / other consumer
Bank-book consumer-loan delinquency (**DRCLACBS**) **2.64%**, falling (Q1'25 2.77 →
Q1'26 2.64). Consumer-loan NCO (**CORCACBS**) **2.81%** (Q4'25 ⚑ Q1'26). "Other"
balance $562B. Sources: [DRCLACBS](https://fred.stlouisfed.org/series/DRCLACBS),
[CORCACBS](https://fred.stlouisfed.org/series/CORCACBS), NY Fed HHDC Q1 2026.

### 3.6 Student — **treat as a reporting artifact, not real-time stress**
90+ delinquency **10.3%** (up from 9.6% in Q4'25). The jump "**largely tracks the
return of payment reporting after the pandemic-era pause**," pulling previously-
invisible missed payments back onto credit files. ~**2.6M** borrowers 120+ DPD
transferred to the Dept. of Education Default Resolution Group in Q1'26; average
defaulting borrower ~40 yrs old. The **flow** into student serious delinquency
actually **fell** (10.9% 4-qtr sum, down from 16.2% in Q4'25) — the *pace of new*
delinquency is easing even as the *stock* reappears. Source: NY Fed HHDC Q1 2026 +
Liberty Street Economics (May 2026). **Do not read the student spike as fresh
consumer deterioration.**

### 3.7 Industry confirmation (FDIC QBP Q1 2026, as-of 3/31/26)
| Metric | Q1 2026 | Trend | Source |
|---|---|---|---|
| Industry net charge-off rate (all loans) | **0.59%** | −4 bp QoQ, −8 bp YoY | FDIC QBP Q1 2026 |
| Noncurrent / PDNA rate (90+ + nonaccrual) | **1.53%** | −3 bp QoQ | FDIC QBP Q1 2026 |
| Credit-card / auto PDNA | ⚑ not confirmed to digit | Declined **seasonally** in Q1, **remain elevated** vs pre-pandemic | FDIC QBP Q1 2026 |
| CRE (context) | — | Non-owner-occupied CRE PDNA **eased**, esp. larger banks; multifamily elevated but no longer rising | FDIC QBP Q1 2026 |

FDIC headline: asset quality "generally favorable." [QBP Q1 2026](https://www.fdic.gov/quarterly-banking-profile/quarterly-banking-profile-q1-2026), [press release](https://www.fdic.gov/news/press-releases/2026/fdic-insured-institutions-reported-return-assets-126-percent-and-net).

### 3.8 Lending standards (Fed SLOOS, July 2026 survey → Q2 2026)
| Category | Reading | Direction | Source |
|---|---|---|---|
| Credit-card standards | ~**7% net tightened** | Mild net **tightening** (the only consumer category tightening) | SLOOS Jul 2026 |
| Auto standards | ~flat (slight easing) | ≈ unchanged | SLOOS Jul 2026 |
| Other consumer standards | ≈ unchanged | Flat | SLOOS Jul 2026 |
| Auto demand | net **weaker** | Soft | SLOOS Jul 2026 |
| Card demand | ≈ unchanged | Flat | SLOOS Jul 2026 |

Consumer standards are **flat-to-modestly-tightening — a de-escalation** from the
sharper 2024–25 tightening. FRED codes to pull exact series: **DRTSCLCC** (card
standards), **STDSAUTO** (auto standards). ⚑ Exact net percents (except card ~7%)
are qualitative in snippets — read SLOOS Table 1 directly.
[SLOOS Jul 2026](https://www.federalreserve.gov/data/sloos/sloos-202607.htm).

---

## 4. Leading vs lagging — the current signal, and the key divergence

**The synthesis (as of Q1 2026 data + Jul 2026 SLOOS):**

1. **The bank book is stabilizing / cresting.** Bank card delinquency (2.92%) and
   all-loan delinquency (1.48%) are **falling** off 2024 highs; card NCO (4.11%) is
   off its 4.58% peak; consumer-loan delinquency falling; card lending standards
   only mildly tightening after a sharp 2024–25 tightening. On the **flow** side
   (earliest signal), card 30+ flow ticked **down** and auto 30+ held **steady**.
   *The leading indicators are pointing to a peak passed, not a fresh wave.*

2. **But the whole-market stock of serious delinquency is still elevated/rising** —
   NY Fed card 90+ at a **~15-yr high (13.1%)** and auto 90+ at the **highest since
   2003 (5.6%)**. Stock lags flow, so an elevated-but-no-longer-accelerating stock
   is consistent with a cresting flow.

3. **The one genuine leading deterioration: mortgage flow-into-serious (1.4→1.5%)**
   plus a slight foreclosure uptick — off a very low base, but it's the only
   *leading* series moving the wrong way. Watch it.

4. **The bank-vs-market divergence is the headline insight.** The bank book (large
   issuers, DRCCLT100S 2.84%) looks materially better than the whole consumer-
   report universe (card 90+ 13.1%). That gap says **stress is concentrated outside
   the large-bank prime book** — in nonbank/finance-company auto, smaller-bank card
   tails (DRCCLOBS), and **younger (18–39) / lower-income** borrowers (NY Fed's
   explicit concentration finding). A prime large-bank portfolio will look calmer
   than the headlines; a subprime/thin-file or auto-heavy book will not.

5. **Student is noise** for real-time purposes (§3.6) — a reporting-resumption
   artifact, not new stress. Strip it out of trend reads.

---

## 5. Metrics a consumer credit-risk-review process should weight

Recommended standing dashboard (all public, all re-runnable via the suite):

1. **NY Fed transition-into-serious-delinquency**, card & auto — earliest turn.
2. **Bank 30-89 DPD / delinquency** by product (Fed DRCCLACBS, DRCLACBS, DRSFRMACBS).
3. **Net charge-off** card/consumer (CORCCACBS, CORCACBS; FDIC) — realized-loss confirm + LGD calibration.
4. **FDIC noncurrent/PDNA** (QBP) — industry asset-quality backstop.
5. **SLOOS consumer standards** (DRTSCLCC, STDSAUTO) — credit-box direction.
6. **Divergence pair: DRCCLT100S vs DRCCLOBS** (large-bank vs small-bank card), and
   **bank book vs NY Fed whole-market** — the concentration tell.

For each, track **level vs 2019 baseline** *and* **rate-of-change** — a series still
below its long-run mean but *rising* is the actionable early state; a series high
but *falling* (today's card stock) is a receding wave.

---

## 6. What public aggregate data CAN and CANNOT show

**Can:** national/system direction and turning points; product-level dispersion;
**bank-book vs whole-market divergence**; large-bank (top-100) vs small-bank splits;
some region/state cuts.

**Cannot** (the segment blind spots — where your internal data is irreplaceable):
- **FICO/score-band × vintage** loss curves — public releases don't cut NCO by
  origination cohort × score band; deterioration concentrates here first.
- **Your** underwriting mix, LTV/DTI distribution, geography, channel, line
  utilization, and payment-rate dynamics (the earliest card-stress tells).
- Account-level **roll-rate / forward-flow matrices**.

**Implication for the process:** use public data to set the **macro overlay and
direction** (and to sanity-check whether your book is tracking, leading, or lagging
the system), then require **internal vintage/segment cuts** to locate and size the
deterioration. Public data tells you *whether the tide is moving*; only internal
data tells you *which cohorts are underwater*. The bank-vs-market divergence in §4
is precisely why: if your book is prime large-bank, the system NCO understates the
tail risk in any subprime/auto/thin-file segment you hold.

---

## 7. Sources & refresh cadence

| Source | Release | Cadence | URL |
|---|---|---|---|
| Fed Charge-Off & Delinquency Rates | Board release + FRED | Quarterly, ~60 days after q-end | [releases/chargeoff](https://www.federalreserve.gov/releases/chargeoff/) |
| NY Fed Household Debt & Credit | Quarterly Report | Quarterly (**Q2'26 → 2026-08-11**) | [microeconomics/hhdc](https://www.newyorkfed.org/microeconomics/hhdc) |
| FDIC Quarterly Banking Profile | QBP | Quarterly (~8 wks after q-end) | [fdic.gov QBP](https://www.fdic.gov/analysis/quarterly-banking-profile) |
| Fed SLOOS | Senior Loan Officer survey | Quarterly | [data/sloos](https://www.federalreserve.gov/data/sloos.htm) |
| Fed G.19 Consumer Credit | G.19 | Monthly | [releases/g19](https://www.federalreserve.gov/releases/g19/) |
| CFPB | Consumer Credit Trends / research | Periodic | [consumerfinance.gov](https://www.consumerfinance.gov/) |

Exact FRED series pull the numeric history by appending `/data/` to a series URL
(e.g. `https://fred.stlouisfed.org/data/CORCCACBS`).

---

## 8. Confidence / open questions

- **Confidence: MEDIUM, directional HIGH.** The *shape* of the story — bank book
  cresting, whole-market serious-delinquency stock still elevated, mortgage flow
  the lone leading deterioration, student a reporting artifact, stress concentrated
  outside the large-bank prime book — is corroborated across multiple independent
  snippets and is internally consistent. **Individual basis-point figures are
  snippet-sourced and not yet confirmed against the primary PDF/FRED table** (§
  integrity note) — treat the ⚑-marked ones as provisional.
- **Hardest-confirmed numbers:** FDIC total NCO **0.59%** and PDNA **1.53%** (Q1'26);
  DRCCLACBS **2.92%** and DRALACBS **1.48%** (Q1'26); NY Fed card 90+ **13.1%** and
  auto 90+ **5.6%**; SLOOS card **~7%** net tightening.
- **Must confirm directly (⚑):** Q1'26 vs Q4'25 for CORCCACBS / CORCACBS / CORALACBS
  / DRSFRMACBS (whether Q1'26 has posted); the rejected CORCCACBS "8.10%"; all 2019
  baselines (pull Q4 2019 from each FRED `/data/` page); the FDIC card-specific NCO
  to the digit; SLOOS per-question net percents beyond card; FFIEC URCC 120/180-day
  thresholds.
- **Known data break:** the **2025 student-loan credit-reporting resumption**
  distorts student delinquency — exclude from trend reads.
- **Imminent supersession:** NY Fed **Q2 2026 drops 2026-08-11** and Fed charge-off
  Q2'26 ~late Aug — re-pull both and update §3–4.
- **Environment caveat:** produced under an egress policy that blocked direct
  primary-source fetches; a re-run from an unblocked machine (e.g. the work desk,
  where the suite already reaches these hosts) should verify every ⚑ figure.
