# Credit-Risk Template Series — Project Index

One reusable pattern, many data sources. Each template is a self-contained
`.xlsm`: Python pulls a source, lands raw data in the workbook, formula-driven
dashboards render it, and a **watchlist lane admits only series with a genuine
portfolio-joinable key** (geographic or entity) — national aggregates are
structurally refused. Deterministic, no LLM in the data path, one provider per
template behind an adapter seam, extract-only VBA bootstrap.

**Process for every template:** coverage research (cited, adversarially
verified) → build spec → build → headless verification → email-sim acceptance.

Each template's directory is self-contained: its spec, research, README,
BUILD_NOTES, code, tests, and the built workbook all live together. This file
is just the map.

## Shipped

| # | Template | Directory | Source | Watchlist | Status |
|---|----------|-----------|--------|-----------|--------|
| 1 | FRED Credit-Risk Dashboard | `fred-credit-risk-dashboard/` | FRED (147 series: charge-offs, delinquencies, G.19, SLOOS, DSR, HPI) | **OPEN** — FHFA state/metro + Case-Shiller HPI (geo keys) | v1 done, PR #53 |
| 2 | Bureau Consumer Credit Monitor | `bureau-credit-risk-dashboard/` | NY Fed HHDC (anonymized 5% Equifax sample; 18 series) | **GATED** — no free bureau source has a joinable key; opens only via licensed Class C (Prama-class) | v1 done + review-hardened, PR #53 |
| 3 | Macro Early-Warning Monitor | `macro-early-warning-dashboard/` | FRED (21 national credit-cycle signals + 151 state-keyed labor/coincident series) | **OPEN** — {ST}UR / {ST}ICLAIMS / {ST}PHCI ranked by Sahm-style state stress gap ({ST}SLIND leading indexes DISCONTINUED, excluded + staleness-guarded) | v1 done, PR #53; live FRED pull awaits a key |
| 4 | Bank Counterparty & Peer Monitor | `fdic-peer-monitor/` | FDIC BankFind Suite API (keyless REST, public domain; 15 C-A-E-L+concentration metrics x flexible `[PEERS]` list, 40 slots) | **OPEN (entity)** — `^cert:[0-9]+$`; the peer/counterparty list IS the watchlist, ranked by ALERT flags + Texas ratio | v1 done, PR #53; first keyless live run at the user's desk is the remaining validation |
| 5 | County Mortgage Delinquency Monitor | `cfpb-mortgage-monitor/` | CFPB Mortgage Performance Trends (NMDB 5% sample; county/state/national 30-89 + 90+ DPD, monthly, ~6-7 mo lag) | **OPEN** — `^county:[0-9]{5}$` [FOOTPRINT] slots; suppression rendered explicitly; vintage + continuity guarded | v1 done, PR #53 |

## Candidate pipeline (researched, not yet picked)

| Candidate | Angle | Join key | Why | Notes |
|-----------|-------|----------|-----|-------|
| BLS LAUS unemployment monitor | geographic | county FIPS / MSA | Geo scout's #1 (18/20): monthly, ~3–5 wk lag — the only candidate matching a monitoring rhythm | Free API key required (500 queries/day); flat-file alternative exists |
| SEC EDGAR corporate counterparty tracker | entity (corporate) | CIK / ticker | Entity scout 18/20: keyless REST, 10 req/s, near-real-time 8-K event lane | Nightly bulk zips available |
| HMDA loan-level mortgage | geographic | census tract + county FIPS | Best free join key anywhere; loan-level originations/denials (17/20) | Annual, ~6-mo lag — research pull, not a monitor |
| SBA 7(a)/504 FOIA loan data | geographic + industry | state / county name + NAICS | Real loan-level charge-offs, commercial (17/20); plain CSV, no key | County is a name string — needs deterministic name→FIPS crosswalk |
| NCUA credit-union monitor | entity (credit union) | charter number | Bulk ZIP, no API; natural sibling of the FDIC template (15/20) | — |
| FHFA NMDB aggregates | geographic | state + top-100 CBSA | Quarterly mortgage delinquency by geo, no key | Runner-up in the "real delinquency with geo key" class |

**Ruled out by research:** MSRB EMMA (paid API, $45k/yr); FHLB member-level
advances (not disclosed — but each bank's own FHLB balance is in Call
Report/FDIC data); UCC filings (paid/fragmented, name-string keys); WARN
notices standalone (name-string keys — viable later as a fuzzy "distress
signals" lane on the EDGAR template); NY Fed Community Credit county data
(Equifax vendor restriction — no machine-readable download; FRED's EQFX county
series partially cover the itch); Fed Board county household-debt maps (CSVs
carry binned ranges, not values); GSE single-family loan-level files
(registration + non-redistribution license); Household Pulse/HTOPS (state + 15
largest MSAs only, redesign churn); CFPB complaints as a watchlist
(ZIP3-degraded — state-only, dashboard lane at best).

## The to-do log

Open work, validation debts, v1.1 items, and ranked next templates live in
**`BACKLOG.md`** — the shared list both of us update. This file stays the map
of what exists; the backlog is what's next.

## Working conventions

- **`TEMPLATE_CONTRACT.md` is binding on every new template** — identical tab
  taxonomy, `_config` schema, runner CLI, extract-only macro, seam contract,
  watchlist gate, and verification bar. It's what makes the templates
  interchangeable and launcher-compatible.
- **`control_center.py` is the one place to run everything.** A stdlib Tkinter
  GUI (with a headless CLI) that discovers any template workbook (`.xlsm` with
  a `_code_py` tab), extracts that workbook's OWN embedded runner, and drives
  it — demo or live — one template at a time. No per-template wiring; new
  contract-compliant templates appear automatically.
- **One directory per template; one chat per template build.** The repo is the
  source of truth — any new session picks up from this file + the template's
  own spec/BUILD_NOTES, not from chat history.
- Lessons carried across builds live in each spec's L-notes (currently L1–L6 in
  `BUILD_SPEC_BUREAU.md`); new lessons append there and propagate to the next
  spec.
- Shared modules (`keybank_style.py`, `vba_writer.py`, `assemble_xlsm.py`) are
  copied per-template on purpose — each workbook must stay self-contained and
  emailable. The Control Center lives OUTSIDE the workbooks and is optional
  convenience: every workbook still works standalone via its Extract button.
