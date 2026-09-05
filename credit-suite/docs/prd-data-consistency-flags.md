# Built-in data-consistency flags for the credit suite

**Status:** design, 5 September 2026. No code changed. `src/` and `tests/` were
read, never written.

> "think through flags that we build in to check for data consistency... it
> literally looked like such a giant number that it could not be normal and that
> could also mean data was wrong or changed so flags for reasons to check are
> good if we do this one time where we check everything and then build them
> checks to ensure that it stays correct we can feel a lot safer using it"
> — the firm, 5 September 2026

The tie-out was a one-time act: **857 of 862 data points** compared against the
banks' own filed Call Reports and against the agencies that compute each macro
series (`docs/tie-out/banks-12-2026-06-30/README.md`,
`docs/tie-out/fred-142-series-2026-09-05/README.md`). This document says what to
build so that the same assurance holds every run without repeating it.

---

## 0 · What I did, and what I did not do

Every threshold below is taken from the data this repository actually holds. I
read the two shipped workbooks directly (they are XLSX zips; `openpyxl` is not
installed in this environment, so the sheets were parsed from the XML) and
re-pulled the FDIC live where a second rendering was needed.

**What was measured.**

| Population | Denominator |
|---|---|
| Bank panel, `Raw_FDIC` | 12 banks × 16 quarters × 69 fields = **13,248** cells; **192** bank-quarters |
| Quarter-on-quarter transitions, bank panel | 180 per field (12 banks × 15) |
| FDIC quarterly-flow identity | 12 banks × 16 transitions × 8 flow fields = **1,536** |
| Class charge-off rates | **1,246** bank-quarter-class observations |
| FRED panel, three `Raw_*` tabs | **142** series, **13,905** observations |
| FRED index period-on-period moves | **8,910** |
| FRED percent-unit period-on-period moves | **3,123** |
| Workbook vs a fresh FDIC pull | **13,248** field-quarters |

**What I did not check.** The FRED side has no second rendering here — a
re-pull needs an API key I do not have, so every FRED continuity threshold below
is grounded on the *history inside the workbook*, not on a revision study. I did
not verify any FDIC field's MDRM citation against a filing; the tie-out did that
and I take it as given. I did not run the test suite. Nothing here was checked
by a second person.

---

## 1 · The finding that changes the design

**The five PNC lines the tie-out could not explain are fully explained, and the
explanation is a merger the tie-out did not see.**

The banks tie-out reports (`README.md`, "What does not tie"):

> **PNC Bank, five lines.** ... The same reconciliation across twelve banks and
> seven flow fields holds **79 times out of 84** ... No merger explains it —
> PNC's only 2026 acquisition events are branch transfers dated 6 July 2026,
> after the reporting date. **I believe the filing**, and nothing was adjusted.

That sentence is hardcoded prose in `tools/tieout/build_bank_exhibits.py:256`
and `tools/tieout/build_master_roster.py:139`. It is contradicted by this
repository's own merger record. The shipped workbook's `_mergers` tab, written
by `src/credit_suite/sources/fdic/mergers.py` from the FDIC's own history
endpoint, carries:

```
PNC Bank NA | 6384 | effective 2026-06-18 | quarter 2026-06-30 |
CERT 18714 | change code 223 -- Merger - Without Assistance
```

CERT 18714 is **FirstBank, Lakewood, Colorado**, `ENDEFYMD 06/18/2026` (FDIC
institutions endpoint, pulled 5 Sep 2026). PNC absorbed it twelve days before
the reporting date.

The FDIC's merger adjustment then accounts for every gap **to the dollar**.
FirstBank's own 2026-03-31 year-to-date net charge-offs, from the FDIC
financials endpoint:

| field | FirstBank YTD 2026-03-31 | the tie-out's unexplained gap |
|---|---:|---:|
| `NTCRCD` | 515 | 515 |
| `NTCI` | 652 | 652 |
| `NTCONOTH` | 102 | 102 |
| `NTRERES` | 6 | 6 |
| `NTRECONS` | 188 | 188 |
| `NTAUTO` | 0 | *(this field tied)* |
| `NTREMULT` | 0 | *(this field tied)* |

The rule the FDIC is applying is the one `mergers.py` already documents for
Capital One: a quarterly flow is the year-to-date less the previous quarter's,
and in a merger quarter it subtracts **both** banks' prior year-to-date. The
tie-out's "filed" leg subtracted only PNC's. **The FDIC is right; the tie-out's
comparison was wrong in exactly the quarters a merger falls in.**

I widened this to the whole panel. Over **1,536** checks (12 banks × 16
transitions × 8 flow fields):

```
naive identity   quarterly == YTD(t) - YTD(t-1)      holds 1,517   fails 19
```

Every one of the 19 falls inside one of the 6 known merger quarters, and every
one is explained exactly by the acquired bank's prior year-to-date:

```
Citibank    2022-09-30  2 fields   Department Stores NB (58180)
Capital One 2022-12-31  3 fields   Capital One Bank USA NA (33954)
US Bank     2023-06-30  8 fields   MUFG Union Bank NA (22826)
PNC         2026-06-30  6 fields   FirstBank (18714)
JPMorgan    2023-06-30  0 fields   First Republic (59017) -- code 211, no adjustment
Capital One 2025-06-30  0 fields   Discover Bank (5649)
```

With the adjustment applied the identity holds **1,536 of 1,536**.

**Three things follow, and they shape everything below.**

1. The reconciling identity is not `Q1 + Q2 = YTD`. It is
   `NTxxxQ(t) = NTxxx(t) − NTxxx(t−1) − Σ NTxxx_acquired(t−1)`.
2. **A failure of the naive identity has exactly one observed cause: a merger.**
   That makes it a superb detector — but only if its trip consults the merger
   record instead of concluding "the publisher disagrees with itself".
3. JPMorgan's 2023-06-30 quarter is a whole-bank acquisition (code **211**,
   failure resolution) and takes **no** adjustment. So *merger quarter → maybe
   an adjustment*; *adjustment needed → always a merger quarter*. The asymmetry
   is observed over 6 events, not asserted as FDIC policy, and the sample is
   small enough that a new code should be treated as **unknown**, not as "no
   adjustment".

**Action outside this design:** `docs/tie-out/banks-12-2026-06-30/README.md`,
the two `tools/tieout/` builders and the twelve exhibit PDFs assert something
false. They should be corrected to "715 of 720 tie; the five that differ are
explained by the FirstBank merger and the FDIC is correct" — or the tie-out
denominator restated as 720 of 720. This is a documentation defect, not a data
defect; the workbook was right the whole time.

---

## 2 · The taxonomy

Five families. Each name says what kind of *wrongness* it can catch, which is
the only useful way to group them — a check that cannot be traced to a class of
fault is decoration (`docs/SOFTWARE-TENETS.md` **S30**).

| Family | Catches | Cannot catch |
|---|---|---|
| **I · Identity / arithmetic** | a column read into the wrong field, a parser dropping values, a publisher's own derivation breaking | a whole record that is internally consistent and wrong |
| **P · Plausibility / range** | decimal shifts, unit slips, a denominator that collapsed (the 670%) | a wrong value inside the normal band |
| **C · Continuity** | a series that went blank, an observation count that fell, a vintage that went backwards, a stale entity | a value that was always wrong |
| **S · Structural / metadata** | declared units contradicting the figures, a label naming another series, a citation that does not parse or resolve | anything about the numbers themselves |
| **X · Cross-source** | our value drifting from the publisher's, and the publisher disagreeing with itself | a publisher that is uniformly wrong |

Two properties are non-negotiable across all five.

**Every check reports its denominator** (**S2**). "0 problems" from a check that
compared nothing is the failure mode this repository has hit repeatedly. A check
with nothing to look at prints `NONE`, never `ok`.

**Unknown is a third answer.** `PASS / FAIL / UNKNOWN`, never `PASS / FAIL`.
`mergers.read_mergers` already does this — it returns `None` for "nobody asked"
and `{}` for "asked, none found", and its docstring says a caller that collapses
them "is back to the 670". Every check inherits that discipline.

---

## 3 · The checks

Each carries: what it asserts, where it applies, the threshold and how it was
picked, what happens when it trips, and the false-positive risk. Thresholds are
labelled **[grounded]** when measured here and **[ungrounded]** when I could not
measure them, with the data that would ground them named.

### I1 — The merger-adjusted quarterly-flow identity

**Asserts.** For every bank, every quarter after the first, every FDIC quarterly
flow field:

```
NTxxxQ(t) == NTxxx(t) - NTxxx(t-1) - SUM over banks acquired in quarter t
                                      of NTxxx_acquired(t-1)
```

with the acquired set taken from `mergers.py` and restricted to codes it
classifies as acquisitions.

**Applies to.** The 7 published quarterly-flow fields (`NTCRCDQ`, `NTAUTOQ`,
`NTCONOTQ`, `NTRERESQ`, `NTRECONQ`, `NTREMULQ`, `NTCIQ`) plus `NTLNLSQ`. Not
`NTRENREQ` — the FDIC publishes no quarterly variant, so it is blank in all
**192** bank-quarters and there is nothing to check.

**Threshold. [grounded]** Exact equality, integer thousands. Over **1,536**
observations the naive form holds 1,517 times exactly and the adjusted form
holds 1,536 times exactly. There is no near-miss population, so a tolerance
would only be a place for a real fault to hide.

**On trip.** Three outcomes, and the third is the point.

| Merger record says | Verdict |
|---|---|
| an acquisition in this quarter, and the adjustment closes the gap | **PASS**, note the reconciling item and the acquired cert |
| an acquisition, and the adjustment does *not* close the gap | **FAIL** — refuse the build |
| no acquisition (asked, none found) | **FAIL** — refuse the build |
| could not be established (`read_mergers` → `None`) | **UNKNOWN** — ship, mark every affected cell, raise a watch-list flag naming the bank and quarter |

**False-positive risk: low, and measured.** Zero unexplained failures in 1,536.
The residual risk is a new FDIC change code the allowlist does not carry — which
lands in `UNKNOWN`, not in `FAIL`, by construction.

**This one check would have replaced the entire PNC investigation.** It is the
highest-value item in this document.

### I2 — Ratio recomputation against the publisher's own numerator and denominator

**Asserts.** Where the FDIC publishes a ratio *and* both its components, the
ratio recomputed from the components equals the published ratio.

**Applies to.** `NCLNLSR = NCLNLS/LNLSGR`, `LNATRESR = LNATRES/LNLSGR`,
`LNRESNCR = LNATRES/NCLNLS`, `EQV = EQ/ASSET`, all × 100. **768** comparisons
(4 × 192).

**Threshold. [grounded]** Relative gap ≤ **1e-12**. Measured maximum over 768
comparisons: **5.3e-16** — floating-point epsilon. The FDIC serves these at full
double precision (`NCLNLSR = 1.0141164018559314` for Goldman at 2022-12-31), so
there is no rounding population to accommodate.

**Is this a mirror?** Partly, and say so. It does **not** prove the FDIC agrees
with the filing. It **does** prove that our parse landed a numerator, a
denominator and a ratio that belong to each other — which is precisely the fault
class of defects 5, 6 and 8 (a label on the wrong series, a column shifted, a
unit off by 1,000). It is worth building for that and for nothing more.

**False-positive risk: very low.** No observed near-misses.

### I3 — Nesting: revolving 1-4 family is inside total 1-4 family

**Asserts.** `xxRELOC ≤ xxRERES` for `LN`, `P3`, `P9`, `NA`.

**Applies to.** **704** comparisons across the panel (192 + 188 + 134 + 190,
the differences being cells the FDIC leaves blank).

**Threshold. [grounded]** Exact inequality. **0 breaches in 704.** Maximum
observed ratio 1.0000 (`P3`, Capital One 2023-12-31); on balances the maximum is
0.3159.

**Why it matters more than it looks.** The nine loan-class fields in `Raw_FDIC`
are **not a partition** — `RERES` contains `RELOC`. Anyone who builds a
"components sum to the total" check without knowing that will ship a check that
fires on half the panel (see §5, N2). Encoding the nesting makes the structure
explicit where the next person will be standing.

### I4 — Noncurrent classes do not exceed the noncurrent total

**Asserts.** `Σ over 8 disjoint classes (P9 + NA) ≤ NCLNLS`, the eight being the
nine minus `RELOC`.

**Applies to.** **192** bank-quarters.

**Threshold. [grounded]** Ratio ≤ **1.0000**. Measured maximum: exactly 1.0000
(Capital One, 2026-06-30 — a bank whose whole noncurrent book is inside these
eight classes). Minimum 0.640. With `RELOC` wrongly included the maximum is
1.1563 and 97 of 192 breach.

**On trip.** Refuse the build. A bucket exceeding the total it is drawn from is
a mapping error, not an unusual quarter.

**False-positive risk: low but not zero.** The population is 12 banks in 16
quarters. A bank with a loan type outside these eight would sit *below* 1.0, not
above, so the risk is a future FDIC definitional change — which should refuse and
be looked at, which is the correct outcome.

### I5 — The netting identity

**Asserts.** `LNLSGR − LNATRES == LNLSNET`.

**Threshold. [grounded]** Exact. **192 of 192**, no exceptions.

Cheap, and it pins three separately-landed fields to each other.

### I6 — G.19 components sum to the total

**Asserts.** `REVOLSL + NONREVSL == TOTALSL` for every month.

**Applies to.** The seasonally-adjusted G.19 trio, **99** monthly observations.

**Threshold. [grounded]** Exact to the cent at the latest observation
(1,351,069.14 + 3,815,838.57 = 5,166,907.71). I checked the latest month only;
**[ungrounded]** across the other 98 — running it over the full history is part
of the build and will either hold or produce a tolerance.

### P1 — The class charge-off rate band (the 670% check)

**Asserts.** An annualised quarterly net charge-off rate for a loan class sits
in a defensible band.

**Applies to.** The seven `NT*Q / LN*` pairs. **1,246** bank-quarter-class
observations.

**Threshold. [grounded] |rate| > 25%, annualised.** The distribution:

```
p50   0.12%      p90   3.76%      p95   4.54%      p99   6.46%     p99.9  28.31%
```

Only **4 of 1,246** observations exceed 10%, and only **1 of 1,246** exceeds 30%:

| rate | bank | quarter | field | flow | book | merger qtr | book < $100M |
|---:|---|---|---|---:|---:|---|---|
| 670.41% | Capital One | 2022-12-31 | `NTCONOTQ` | 5,318 | 3,173 | **yes** | yes |
| 28.31% | Capital One | 2023-03-31 | `NTCONOTQ` | 281 | 3,970 | no | yes |
| 20.82% | Capital One | 2022-09-30 | `NTCONOTQ` | 280 | 5,380 | no | yes |
| 13.26% | Goldman Sachs | 2023-12-31 | `NTREMULQ` | 32,000 | 965,000 | no | no |

At 25% the band trips **twice** in 1,246 and both trips are on a book under
$4M — already blanked by `trend.py`'s `MATERIALITY_FLOOR_K = 100_000` (the
firm's own $100M number). At 10% it trips four times, and the fourth is
**Goldman charging off $32M of a $965M multifamily book** — real, unusual, and
exactly the legitimate quarter a build-refusing check must not block.

**On trip.** Never refuse the build. Blank the cell, write the reason with the
book size in it, and raise a watch-list flag. `trend.py` already has this shape
in `LAST_MATERIALITY_BLANKS` and `LAST_MERGER_BLANKS`.

**False-positive risk: real, and this is why it does not gate.** The Goldman row
is the false positive you get for lowering the band, and it is a finding a credit
reviewer wants to see — as a flag, not as a build failure.

### P2 — The whole-book charge-off rate band

**Asserts.** `NTLNLSQR` sits in a plausible band.

**Threshold. [grounded] outside [−2.0, +10.0] percent.** Observed range over
**192** observations: **−0.09 to 3.56** (the ceiling is Capital One, every one of
the top five). The band is roughly 3× the observed maximum and 20× the observed
minimum, so it cannot fire on a real credit cycle but catches a factor-of-10
error instantly.

**On trip.** Watch-list flag. Not a gate.

### P3 — Balances are never negative

**Asserts.** Every balance-sheet field is ≥ 0.

**Applies to.** All `LN*`, `P3*`, `P9*`, `NA*`, `ASSET`, `DEP`, `EQ`, `BRO`,
`LNATRES`, `DEPUNINS`, `SC*`, `OTHBFHLB` — 60 of the 69 fields.

**Threshold. [grounded]** Zero negatives observed in these fields across
**13,248** cells. The 8 fields that *do* go negative are all flows and ratios,
and the counts say so plainly: `NTRERESQ` is negative in **116 of 192** quarters
(net recoveries are ordinary on a residential book), `NTRECONQ` 48, `NTREMULQ`
28, `NTAUTOQ` 11, `NTCONOTQ` 11, `NTCIQ` 3, `NTLNLSQR` 7, `ROAQ` 5.

**This is why a blanket "no negatives" rule is wrong.** The allowed-negative set
must be declared per field from the observed record, not guessed from the name —
the same discipline `trend.py`'s `WORSE_WHEN` already applies to polarity.

### P4 — The FRED band, by unit family

**Asserts.** A period-on-period move sits inside a band set per unit family, not
globally.

**Thresholds. [grounded]**

| Unit family | n | p50 | p99 | max | proposed band |
|---|---:|---:|---:|---:|---|
| index (all HPI/Case-Shiller) | 8,910 | 1.02% | 6.78% | **12.98%** (Miami 2008Q3) | **> 15% QoQ** |
| percent (charge-off / delinquency rates) | 3,123 | 0.09pp | 1.39pp | **3.37pp** | **> 5pp** |
| net percent (SLOOS) | 973 | 6.1pp | 45.0pp | **58.5pp** | **> 75pp**, and range `[-100, +100]` |
| billions/millions $ levels | 594 | 0.4–2.1% | 3.6–8.0% | 17.15% | **> 25% MoM** |
| percent (annual rate) | 99 | 2.23pp | 13.76pp | 13.76pp | **> 30pp** |

Each band clears the observed maximum by a wide margin and would have fired
**zero** times over 13,905 observations, while still catching a decimal shift
(10×) or a unit slip (1,000×) on the first run.

**On trip.** Watch-list flag on the dashboard, plus a line in the run status.
The 2008 Miami print is the reminder that the real world produces 13% quarters.

### P5 — Percent-unit series stay in range

**Asserts.** `units=percent` ∈ [−100, 100]; `units=net percent` ∈ [−100, 100];
index levels > 0.

**Threshold. [grounded]** Observed ranges: percent [−0.04, 15.85]; net percent
[−70.2, **100.0**] — `DRTSSP` touches exactly 100.0 in 2008Q4, so the bound must
be inclusive. Index families all strictly positive.

**On trip.** Refuse the build. A diffusion index outside ±100 is not a market
event, it is a parse.

### C1 — Every pullable series must land

**Asserts.** `series_pulled == series_pullable`, and for the FDIC, every active
entity slot landed.

**This is the Nebraska defect, and it is structural.**
`src/credit_suite/sources/fred/runner.py:1008`:

```python
def run_succeeded(status: dict) -> bool:
    """False when there were series to pull but ZERO came back..."""
    return not (pullable > 0 and status.get("series_pulled", 0) == 0)
```

The gate is **at least one**, not **all**. One HTTP 500 on the Nebraska house
price index gave `pulled = 141`, `errors = ["NESTHPI: ..."]`, exit 0, a shipped
workbook with a state missing, and a passing test suite. The error was recorded
honestly and nothing read it.

**Threshold.** Exact equality. Nothing to tune — this is arithmetic on the
runner's own status dict, which already carries both numbers.

**On trip.** **Refuse the build.** This is the one plausibility-free,
judgement-free gate in the document, and it is the cheapest thing here.

**False-positive risk: the trade-off, stated.** A transient 500 on one of 142
series now fails the whole run. That is the correct trade — a monitor with a
silent hole is worse than a monitor that did not ship — but it must come with a
retry (the runner already paces requests) and with the refusal naming the series
and the HTTP status, so the operator can decide in ten seconds whether to rerun
or to mark the series dead in the seed.

### C2 — Coverage may not shrink between runs

**Asserts.** For each series/field, `observation_count(this run) ≥
observation_count(last run)`, and a cell that was populated last run is
populated now.

**Applies to.** All **142** FRED series and all **13,248** bank cells. Needs a
small per-run coverage manifest written beside the workbook — series id,
observation count, latest date, first date, blank count. That artifact does not
exist yet and is the only new storage this document proposes.

**Threshold. [grounded, structurally] Exact.** Interior blanks are the signature.
Measured across the 142 FRED series:

```
TDSP    n=100  missing=15  all at the OLDEST end   -- the series starts later. legitimate.
MDSP    n=100  missing=15  all at the OLDEST end   -- legitimate.
CDSP    n=100  missing=15  all at the OLDEST end   -- legitimate.
DRTSSP  n= 78  missing=19  ALL INTERIOR            -- see below.
```

**A finding nobody has recorded.** `DRTSSP` — the subprime consumer-tightening
series, the one whose alert rule was fixed in `a9411a1` — has **19 interior
holes**, at 2009Q2 through 2011Q4 continuously, plus 2012Q1–Q2, 2013Q4, 2016Q2,
2017Q3, 2018Q1, 2018Q4 and 2019Q1. Every other series in the panel has zero
interior gaps. The SLOOS does not ask every question every quarter, so this is
*probably* legitimate — but it is exactly the Nebraska shape, nothing in the
repository says it was looked at, and the tie-out proved only the latest
observation. **Verdict: UNKNOWN.** Confirm against the Board's own SLOOS release
history before the check ships, and record the answer as a per-series allowance
with a citation. If it is not legitimate, this is defect number six.

**On trip.** New interior blank, or coverage down: refuse the build. Coverage
flat or up: pass. First run (no manifest): **UNKNOWN**, ship and say so.

### C3 — Vintage moves forward, and moves together

**Asserts.** The run vintage is ≥ the last run's, and every series carries the
same vintage within a run.

**Threshold. [grounded]** All **142** series in the shipped FRED workbook carry
`vintage=2026-09-05`. Uniformity is the current state, so any skew is new and
means part of the workbook did not refresh.

**On trip.** Vintage backwards → refuse. Vintage skew within a run → refuse.

### C4 — Publication lag, per category

**Asserts.** The latest observation is no older than the category's own
publication lag.

**Threshold. [grounded, per category — never global].** The latest observation in
the shipped workbook ranges from **2026-01-01** (`BOGZ1FL075035403Q`, Z.1, which
is published with a two-quarter lag) to **2026-07-01** (`SUBLPDRCSN`). Monthly
series range from 2026-05-01 (`DEXRSA`) to 2026-06-01.

A single global rule would fire on Z.1 every single run. The existing
`engine/staleness.py` already gets this right and its docstring says why:

> The test is *relative to the peer set*, not absolute. An absolute age test
> would flag every entity at once whenever a regulator's release slipped, which
> trains the analyst to ignore the flag.

For FRED the peer set is the *category*, and `cfg.publication_lag_days(category)`
already exists. This check is a wiring job, not a new mechanism.

### C5 — The date grid is regular

**Asserts.** Dates are strictly ordered, unique, and step by the declared
frequency.

**Threshold. [grounded]** **142 of 142** series are regular today — zero
duplicates, zero out-of-order, zero irregular steps. A perfect baseline.

**On trip.** Refuse. A duplicated or skipped date is a merge fault, and every
transform downstream (`zscore_8q`, `yoy_pct`) silently gives a wrong answer on a
broken grid.

### S1 — Declared units versus the figures beside them

**Asserts.** A series declaring a dollar magnitude carries figures of that
magnitude.

**This check is not hypothetical — it fires on the shipped workbook right now.**

`src/credit_suite/sources/fred/series_seed.py:80` says, in a comment written the
day the defect was fixed:

```
# MILLIONS, not billions: the Board prints 5,166,907.71 for June 2026
```

and the four rows below it declare `"millions $"`. The **shipped**
`example-output/FRED_Credit_Risk_Dashboard.xlsm` `_config` tab declares
`billions $` for `TOTALSL`, `TOTALNS`, `REVOLSL` and `NONREVSL`, beside a
`TOTALSL` of 5,166,907.71. The FRED tie-out README lists this as "Fixed in
`94d431f`". The source is fixed. **The artifact a person opens is not**, and
`example-output/` is in `.gitignore`, so nothing in version control can tell you
that. The workbook sits between two fixes — it carries the `a9411a1` alert-rule
correction for `DRTSSP` and not the `94d431f` unit correction.

This is `SOFTWARE-TENETS.md` **S1** — *nothing is produced until it has been
opened by the thing that consumes it* — recurring.

**Threshold. [grounded]** For a series declaring `billions $`, the latest value
should be roughly 1e0–1e5; for `millions $`, 1e2–1e8. The four G.19 series sit
at 1.35e6–5.17e6 against a `billions $` label — three orders of magnitude out.
A single order-of-magnitude comparison against the publisher's own printed figure
is enough; there is no need for a tight band.

**On trip.** Refuse the build. And the real fix is the one that makes the fault
impossible: **derive the workbook's `_config` from `series_seed.py` and assert
they are equal** (**S6** — *two lists that must agree will not; derive one from
the other*). A check that reads the workbook's label and the workbook's number is
one edit away from being a mirror; a check that compares the shipped artifact to
the source of record is not.

### S2 — The label names the series beside it

**Asserts.** A series' declared title, category and `metric_type` are consistent
with each other and with the series id.

**The incidents:** two series wearing each other's descriptions (CRE construction
vs nonfarm nonresidential), two more naming a different series, and a tightening
indicator filed as a demand series so its alert could never fire.

**Threshold. [ungrounded, and honestly so].** I cannot measure this from the
data — the numbers were correct in all four cases, which is exactly why the test
suite passed over them. What can be checked mechanically:

- a `metric_type` of `sloos_diffusion` with `alert_rule = none` must carry the
  seed's explicit "demand series" note, and no other row may;
- a title containing a state or metro name must match the geo key;
- a series id appearing in a title must be its own.

**[ungrounded]** the general case. What would ground it: FRED's own
`series/observations` metadata carries a `title` per series id, and comparing our
title to FRED's would turn this from a heuristic into a cross-source check (X2).
That needs the API key.

### S3 — Every citation parses, and resolves on a real filing

**Asserts.** Every landed field carries a provenance citation; every citation
parses; every parsed code is found on a filed Call Report.

**Already built.** `tests/test_provenance_citations.py` exists and is the guard
the tie-out found missing. Three faults it now covers, all inside rows already
flagged `[V]`:

1. **Seven fields carried the literal text `(not in tie-out map)`** — the map
   documented nothing and the tie-out walked past them silently. *A check that
   examines what the map documents cannot discover what the map omits* — the
   denominator is the only thing that reveals it (**S2**).
2. **Parentheses did not parse.** `(C891+C893) - (C892+C894)` became nothing.
   Every quarterly-flow citation was affected.
3. **A bare code resolved against `RCFD` then `RCON` only** — useless for an
   income-statement line needing `RIAD`; and the two capital ratios cited
   `RCOA`, the form-041 prefix, on twelve banks that all file 031.

**What is still open.** The README says plainly: *"The provenance map passed; it
was not proved universal... A citation right for these filers and wrong for a
bank filing form 041 would not show up here."* The check should assert coverage
— **69 of 69** fields cited, none `(not in tie-out map)` — and report that
denominator on every run.

### S4 — The filing parser keeps non-integers

**Asserts.** Reading a filing yields ratios as well as dollar amounts.

**The incident:** the parser kept whole numbers only and **discarded every ratio
in every filing**. Dollar amounts are whole numbers, so nothing
dollar-denominated ever looked wrong, and 24 bank-ratio pairs went unchecked.

**Threshold.** A parsed filing must yield at least one fact with
`unitRef="PURE"`. **[grounded, structurally]** — the capital ratios are in the
XBRL for all 12 filers and now agree three ways.

**On trip.** Refuse. This is a `> 0` assertion, which is the weakest useful
form, but it is the exact shape of the fault: a filter that silently emptied a
whole category.

### X1 — Our value versus a fresh pull of the same source

**Asserts.** Every landed value equals what the publisher returns today for the
same entity, period and field.

**Measured. [grounded]** I re-pulled all 69 fields for all 12 banks across all
16 quarters and compared cell for cell against the shipped workbook:

```
identical 13,248   differ 0   one side blank 0   quarter missing 0
denominator 12 x 16 x 69 = 13,248
```

**Threshold.** Exact equality; any difference is reported, none suppressed.

**Honest limit:** this measures a **one-day** window. It is evidence the
comparison is buildable and currently silent — it is **not** a revision-rate
study. Over a quarter the FDIC amends filings, and a real revision rate would
justify a "revised, not wrong" verdict distinct from "differs". Grounding that
needs the same comparison run weekly for a quarter and the distribution written
down. Until then, every difference goes to a human.

**On trip.** Never refuse — a restatement is normal and is a *finding*. Write a
revision note naming the field, both values and both dates, and raise a
watch-list flag.

**Where it lives.** `tools/live_acceptance.py`, which is already opt-in, already
network-dependent, and already explicitly outside the CI bar.

### X2 — The publisher against itself

**Asserts.** Where a publisher publishes two renderings of the same fact, they
agree.

Three instances exist today: the FDIC's quarterly versus year-to-date (**I1**);
the FDIC's ratio versus its components (**I2**); and the bank's XBRL versus the
rendered facsimile versus the workbook, which the tie-out proved agree three
ways on all 24 bank-ratio pairs.

**The lesson from the PNC case belongs here in bold. When the publisher appears
to disagree with itself, the instrument is the likelier culprit.** The banks
README already says so about its own three defects — *"Each announced itself as
an implausibly uniform failure across every entity"* — and then, five paragraphs
earlier, concludes that the FDIC disagrees with itself on the one case where the
instrument was wrong. **A trip of X2 must not be reportable as a publisher fault
until the reconciling item has been searched for and named.**

---

## 4 · The merger problem

The 670% was not bad data. Capital One's other-consumer charge-off flow for
2022Q4 was arithmetically correct from its inputs and described nothing, because
the FDIC derives a quarterly flow by subtracting the previous quarter's
year-to-date, and across a merger that subtraction spans two banks. A size floor
would have hidden it by luck: *"had the survivor carried a $500M book the same
$5.3M would have drawn a plausible 4.3% that nobody questioned"*
(`mergers.py`).

**So a flag must distinguish three states, not two.**

| State | Meaning | Verdict |
|---|---|---|
| **Data is wrong** | the numbers do not reconcile, and no event explains it | FAIL |
| **Data is right, period is not comparable** | the numbers reconcile once a named event is folded in | PASS, with the flow blanked and the event named |
| **Merger status unknown** | the merger record could not be established | UNKNOWN — never silently "fine" |

### How a check consults the record

`mergers.py` already carries the pieces and the discipline. Three properties are
load-bearing and must not be lost:

**It is an allowlist, not a denylist.** `ACQUISITIONS` names six codes (211, 217,
221, 222, 223, 224) and `NOT_AN_ACQUISITION` separately names four (712 branch
purchase, 810/811/812 mirror entries). A code in neither map is *unrecognised*,
not "not a merger". A denylist here fails open; this fails closed.

**`None` is not `{}`.** `read_mergers` returns `None` for "nobody asked" and
`{}` for "asked, none found". Its own docstring: *"a caller that collapses them
is back to the 670"*.

**Never infer a merger from the shape of the numbers.** The record is the FDIC's
own institution history. A flag that guessed a merger from a large move would
have blessed the very number the firm caught.

### The protocol every flag follows

```
1. compute the check
2. if it passes                       -> PASS
3. ask the merger record for (cert, quarter)
     record unavailable               -> UNKNOWN.  ship, mark, flag, name the bank
     acquisition, adjustment closes   -> PASS.     name the acquired bank and its
                                                   prior YTD as the reconciling item
     acquisition, adjustment does not -> FAIL
     no acquisition                   -> FAIL
     code unrecognised                -> UNKNOWN
```

### Two corrections to how the merger flag is used today

**Fix the window.** `mergers.py` already carries `quarter_start` with the scar
attached: *"A merger on 1 July contaminates the quarter ending 30 September, so
asking from the quarter-END misses it by two months — which is exactly what
happened to Citibank's July 2022 merger on the first live run."* The tie-out
session then made the same mistake in a different tool and reported PNC's
6 July branch transfers while missing the 18 June merger. **Every caller must
query from `quarter_start`, and the fan (**S29**) is: find every place that asks
the history endpoint and check the window in all of them.**

**Prefer reconciling to blanking.** `apply_merger_flags` blanks the flow in a
merger quarter. That is right for a *rate*, because the numerator mixes two banks
and the denominator is the merged book. But the underlying figure is
reconcilable — the FDIC has already subtracted the acquired bank's prior
year-to-date — so the flow itself can be **explained** rather than deleted.
Blanking a rate and explaining a flow are different actions and the design should
do both:

- blank the derived **rate**, with the merger named (as today);
- keep the **flow**, annotated with the reconciling item and the acquired cert.

`trend.py`'s two independent guards — `apply_materiality` ($100M floor, the
firm's number) and `apply_merger_flags` — stay independent. The comment there
already explains why one is not the other, and the 670% row is the proof: the
merger flag alone leaves 28%, −7.8% and 21% standing on a $2–8M book.

---

## 5 · Where each check lives

Three homes, and the trade-off is the whole decision.

**Build-time (refuse to ship).** Stops a stale or holed monitor reaching the
desk. Also stops a legitimate unusual quarter. **Only for checks whose trip has
no innocent explanation**: an arithmetic identity, a missing series, a broken
date grid, a metadata contradiction. Exit 2, the way `tools/conformance.py` and
`tools/check_parity.py` already do — *"drift is a gate error, not a crash"*.

**Run-time (flag on the dashboard).** For anything a real market can produce.
Goldman's 13.26% multifamily quarter is the case: a band tight enough to catch a
denominator collapse is tight enough to catch a bad quarter, and the bad quarter
is a finding, not a build failure. These write to the watch-list and to the run
status, and they carry their reason with the number in it.

**Test-time (regression guard).** For a fault that was fixed and must not come
back: citation parsing, prefix resolution, the ratio-keeping parser, the
`None`-vs-`{}` distinction in `read_mergers`.

| Check | Home | Verdict on trip |
|---|---|---|
| I1 merger-adjusted flow identity | build + test | refuse / UNKNOWN |
| I2 ratio recomputation | build | refuse |
| I3 RELOC ⊆ RERES | build | refuse |
| I4 noncurrent classes ≤ total | build | refuse |
| I5 netting identity | build | refuse |
| I6 G.19 components | build | refuse |
| P1 class NCO band | run-time | blank the rate, flag, keep the reason |
| P2 whole-book NCO band | run-time | flag |
| P3 balance sign | build | refuse |
| P4 FRED move band | run-time | flag |
| P5 percent range | build | refuse |
| C1 every pullable series lands | build | refuse |
| C2 coverage may not shrink | build | refuse / UNKNOWN on first run |
| C3 vintage | build | refuse |
| C4 publication lag | run-time | flag (already `staleness.py`) |
| C5 date grid | build | refuse |
| S1 units vs figures | build | refuse — and derive `_config` from the seed |
| S2 label vs series | build (mechanical part) | refuse |
| S3 citations parse and resolve | test (exists) + build coverage | refuse |
| S4 parser keeps ratios | test (exists) | red |
| X1 fresh-pull comparison | `live_acceptance.py`, opt-in | revision note + flag |
| X2 publisher vs itself | build (I1, I2) | refuse, after searching for the reconciling item |

**Every new check must be proved by mutation.** `tools/mutation_check.py` is the
existing instrument and its opening line is the standard: *"A test that stays
green when the code it covers is broken is not a test, it is decoration."* Each
check ships with a mutation that must turn it red — break the merger lookup and
I1 must fail; delete a series block and C1 must fail; multiply a unit by 1,000
and S1 must fail. A check without a mutation is not finished.

---

## 6 · What NOT to build

**N1 — A single global percent-move band.** The measured p95 quarter-on-quarter
move ranges from **6.76%** (`RBCRWAJ`) to **5,150%** (`NTREMULQ`) across the 69
bank fields — and the p50 from **1.24%** (`LNRERES`) to **100%**. `NTREMULQ`'s *median* move is 100% and `P3REMULT`'s is 92.86%. Any
band that does not fire constantly on the small-denominator flow fields is
useless on the balance-sheet aggregates, and vice versa. Bands are per field
family or they are noise.

**N2 — "The nine loan classes sum to total loans."** It passes — maximum
**0.9192** of `LNLSGR` over 192 bank-quarters — and it passes **by slack, not by
construction**: the nine classes do not cover agricultural, foreign or other
loans, so the sum sits well below the total and the check has room to hide a
double-count. Worse, the same idea on the past-due side breaches in **97 of
192** because `RERES` contains `RELOC`. Build I3 and I4 instead: the nesting
identity, and the sum over the eight that *are* disjoint.

**N3 — Percent-change checks on diffusion indexes.** SLOOS net-percent series
have a median period-on-period *relative* move of **52.6%** and a maximum of
**3,636%**, because the denominator crosses zero. `TOTALSLAR` is worse: p99 of
**11,525%**. Measure these in points, never in percent. The same series in
points is well behaved: SLOOS p99 = 45.0pp, max 58.5pp.

**N4 — Recomputing a workbook formula and comparing it to the workbook.** The
`Raw_FDIC` tab has **zero** formulas; the dashboards have 369 and the watchlist
2,480. Recomputing those in Python and comparing to the cached Excel value is the
mirror problem in its purest form: a total that balances by construction proves
nothing. `tools/check_parity.py` already covers the real question — does this
build produce what the last one did — by diffing against a pinned golden.

**N5 — A blanket "no negative values" rule.** `NTRERESQ` is negative in **116 of
192** bank-quarters. Net recoveries are ordinary. Declare the allowed-negative
set per field, from the record.

**N6 — An absolute staleness rule across all series.** The latest observation
legitimately spans **2026-01-01 to 2026-07-01** because Z.1 publishes two
quarters behind. A global rule fires on Z.1 every run, and `staleness.py` already
explains what that costs: *"trains the analyst to ignore the flag"*.

**N7 — A test that the shipped workbook's units match the shipped workbook's
values.** That is one file agreeing with itself. Compare the artifact to
`series_seed.py`, which is the source of record — and better, generate one from
the other so the fault cannot occur (**S30**: *prevent, do not detect*).

**N8 — Inferring a merger from the numbers.** Named again because it is the most
tempting shortcut in this document and it would have blessed the 670%.

---

## 7 · Ranked implementation order

Ordered by value per unit of effort. Sizes are rough: **S** ≈ under a day,
**M** ≈ a few days, **L** ≈ more.

| # | Check | Size | Why here |
|---|---|---|---|
| 1 | **C1 — every pullable series must land** | **S** | One comparison on a status dict the runner already builds. Closes the Nebraska hole outright. Highest value per line in the document. |
| 2 | **I1 — merger-adjusted flow identity** | **M** | Would have replaced the whole PNC investigation and produced the right answer. Needs the acquired bank's prior YTD, which is one extra API call per merger quarter. 1,536 of 1,536 with the adjustment. |
| 3 | **S1 — derive `_config` from `series_seed.py` and assert equality** | **S** | Fires on the shipped workbook today. Makes the units defect structurally impossible rather than detected. |
| 4 | **C3 + C5 — vintage and date grid** | **S** | Pure arithmetic on data already in the workbook. Perfect baselines today (142/142), so any trip is real. |
| 5 | **I2, I3, I4, I5 — the FDIC identity set** | **S** | All four are a few lines each over data already landed. Measured: 768, 704, 192 and 192 observations, zero exceptions. Cheap insurance against a column shift. |
| 6 | **P5 + P3 — range and sign** | **S** | Trivial, and P3 forces the allowed-negative set to be written down, which is documentation the panel currently lacks. |
| 7 | **P1 + P2 — the charge-off bands** | **S** | Small, but they belong *after* I1: the 670% is a merger artefact, and a band that fires without consulting the merger record teaches the reader to ignore it. |
| 8 | **C2 — coverage manifest** | **M** | Needs a new per-run artifact. Catches the whole "was populated, now blank" family, which is where the Nebraska defect and the `DRTSSP` question both live. |
| 9 | **P4 — the FRED bands** | **S** | Bands are already measured. Trivial once the per-unit-family grouping exists. |
| 10 | **S3 coverage assertion** | **S** | `test_provenance_citations.py` exists; add the denominator — 69 of 69 fields cited, zero `(not in tie-out map)` — and report it. |
| 11 | **X1 — fresh-pull comparison** | **M** | Belongs in `live_acceptance.py`. 13,248 of 13,248 identical today, so it starts silent. Real value arrives after a quarter of running it. |
| 12 | **C4 — per-category publication lag** | **S** | Mostly wiring: `staleness.py` and `publication_lag_days` both exist. |
| 13 | **S2 — label consistency, mechanical part only** | **M** | The general case is ungrounded. Build the three mechanical rules; leave the rest until FRED's own titles can be compared (needs the key). |

**Before any of it, three things that are not checks.**

- **Correct the banks tie-out.** Its PNC conclusion is false and it is the
  document a skeptic reads first (§1).
- **Rebuild `example-output/`.** The shipped FRED workbook is between two fixes
  and carries a units label the source corrected. Nothing that is only true in
  `src/` is true for the person opening the file (**S1**).
- **Resolve `DRTSSP`'s 19 interior blanks** against the Board's own SLOOS release
  history, and record the answer either as a per-series allowance with a citation
  or as defect number six.

---

## 8 · What this design does not cover

- **The dashboard's own logic.** Both tie-outs say plainly that z-scores, bands
  and alert rules were never checked. Every threshold here is arithmetic on
  landed values; none of it proves a flag lights when it should.
- **FRED revisions.** No second rendering was available. C2 and P4 are grounded
  on the workbook's own history, which cannot tell you whether the publisher
  changed an old figure.
- **Banks outside the twelve, and quarters outside the sixteen.** Every threshold
  is measured on 12 large banks, all of which file form 031. A form-041 filer, a
  small bank, or a stress period outside 2022Q3–2026Q2 could sit outside these
  bands legitimately. Each band is set well clear of the observed maximum for
  that reason, and each should be re-measured when the panel changes.
- **The two Z.1 commercial-property series**, where our config, FRED and the
  Board give three different answers on units and the FRED tie-out could not
  establish which is right. It is written up there as unresolved and it stays
  unresolved here. S1 must therefore treat those two as **UNKNOWN** rather than
  asserting either answer.

---

## 9 · What was built, and where it departs from the above

Built 5 September 2026, test-first. Five items, in the order §7 ranks them.
Everything below was run; every number in it is from a run, not from a plan.

| Rank | Check | Built | Where it lives |
|---|---|---|---|
| 1 | **C1** every pullable series must land | yes | `engine/consistency.py`, wired into `engine/runtime.run_succeeded` and `sources/fred/runner.run_succeeded` |
| 2 | **I1** merger quarters | **reframed — see below** | `sources/fdic/consistency.flow_comparability` |
| 3 | **S1** `_config` against `series_seed.py` | yes | `sources/fred/consistency.config_matches_seed` + `tools/consistency_check.py` |
| 4 | **C3 + C5** vintage and date grid | yes | `sources/fred/consistency.vintage_check`, `engine/consistency.date_grid` |
| 5 | **I2 I3 I4 I5** the FDIC identity set | yes | `sources/fdic/consistency.identity_set` |

Each has a mutation in `tools/mutation_check.py` and each mutation was killed.

### The four departures, and why

**I1 does not reconstruct anything, and cannot.** §1 above works PNC through as
if the merger adjustment were well defined. **That finding was withdrawn.** Two
mergers in this same twelve-bank panel consolidate opposite ways — PNC's
year-to-date contains the acquired bank's prior year-to-date and Capital One's
does not — so there is no single arithmetic that turns two year-to-dates into a
quarter. `flow_comparability` therefore answers COMPARABLE / NOT COMPARABLE /
UNKNOWN and hands back no number. `Comparability` has no field to put one in,
and a test pins its field list so adding one starts a conversation.

**The arithmetic leg of I1 is not implementable here anyway.** It needs the
year-to-date figures `NTCRCD`, `NTCI` and their siblings. The panel lands the
*quarterly* variants only — 68 fields, of which the eight `NT*` are all `*Q`.
Nothing in `verified-data/bank-values.csv` or in the workbook carries a
year-to-date charge-off. The identity cannot be computed without new fields and
new API calls, and per the paragraph above it should not be repaired even then.

**C5 is reported, not gating.** Duplicates, reversals and irregular steps have
no innocent explanation and §5 says refuse. It does not, yet: no live FRED pull
has been run through it. The 142-of-142 baseline was measured on a workbook,
and an unverified rule that blocks the desk's only refresh path is the false
alarm this document spends a page warning about. `run()` writes
`status["date_grid"]` and the runner prints it; `tools/consistency_check.py`
exits 2 on it. Wire it to the runner's exit code after one live run confirms
it, and change this paragraph when you do.

**An interior HOLE in a date grid is UNKNOWN, not a failure.** §C2 records
`DRTSSP`'s 19 interior blanks as unresolved. A gap that is a whole number of
steps is named and reported; a gap that is *not* a multiple of the step is a
failure, because that is a merge fault rather than a survey that did not ask.

### Two things found while grounding the thresholds

**The audited deliverable cannot tell a blank from a zero.** Every one of the
68 fields is present in all 192 bank-quarters of
`verified-data/bank-values.csv`, with no empty cells. But the count of
**non-zero** `xxRERES` values is exactly 192 / 188 / 134 / 190 for `LN` / `P3` /
`P9` / `NA` — the same four numbers §I3 above measured as the count of cells the
FDIC leaves *blank*. The blanks became zeros somewhere between the FDIC's
response and the published CSV. So I3's denominator is 768, of which 64 are
`0 <= 0` and prove nothing, and that is how
`test_the_deliverable_cannot_tell_a_blank_from_a_zero` reports it. A reader of
that CSV cannot distinguish "the bank reported nothing here" from "the bank
reported zero".

**The demo provider does not satisfy the publisher's identities.** Pointed at
the workbook `monitorbuild` produces, I2 failed 630 of 636, I5 44 of 156 and I4
20 of 44. None of it is a defect in the monitor: the synthetic provider rounds
each published ratio to four decimal places independently of its components
(`NCLNLSR = 0.8706` against `NCLNLS/LNLSGR = 0.87063304`), rounds net loans
independently of gross less reserve, and draws each loan class independently of
the noncurrent total. These identities are assertions about the **FDIC's**
numbers and a demo build has no publisher, so `tools/consistency_check.py`
reports them as UNKNOWN over the full 192 bank-quarters rather than refusing.
The thresholds themselves are grounded on the real panel, where all four hold
768 / 768, 768 / 768, 192 / 192 and 192 / 192.

### What running it found

```
tools/consistency_check.py Bank_Peer_Monitor.xlsm        (demo build)
  I2/I3/I4/I5 UNKNOWN  0 of 192 bank-quarters  -- synthetic provider
  I1          PASS   192 of 192 bank-quarters
tools/consistency_check.py FRED_Credit_Risk_Dashboard.xlsm
  S1          PASS  2130 of 2130 cells
  C3          UNKNOWN  0 of 142 series  -- no previous run recorded
  C5          PASS   142 of 142 series
same file with the four G.19 units put back to "billions $":
  S1          FAIL  2126 of 2130 cells (4 failed)     exit 2
```

### Still not built, and why

- **C2 coverage manifest, C4 publication lag, P1–P5, S2, S3, X1.** Outside the
  five this session was asked for.
- **P4's FRED bands, P1's 25% and P2's [−2, +10].** Grounded in §3 above, but
  measured against the workbook rather than against `verified-data/*.csv`; the
  CSV holds levels, not the period-on-period moves those bands are set over.
  They are re-measurable, but they were not re-measured here, and nothing is
  implemented on a number this session did not check.
