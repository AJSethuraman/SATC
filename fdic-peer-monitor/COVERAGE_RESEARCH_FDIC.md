# Coverage Research — Bank Counterparty & Peer Monitor (FDIC BankFind) (v1)

Two-agent verification pass feeding BUILD_SPEC_FDIC.md: (A) API mechanics —
live calls were proxy-blocked from THIS environment, but verified against the
FDIC's OWN API specification files (swagger.yaml + per-endpoint
*_properties.yaml, mirrored byte-for-byte) plus a genuine captured raw API
response and dozens of production clients; (B) metric semantics + peer
methodology — cited to supervisory authorities. Verdicts: CONFIRMED
(FDIC spec file / captured response / regulation text), CORROBORATED
(multiple independent production clients), UNVERIFIED (do not rely on;
re-check on first live run).

## Bottom line

Cleanest source in the series: **keyless REST, public domain, zero licensing
flags**. One request fetches an entire peer list (30 banks x 30 fields x 12
quarters << the 10,000-row cap). The watchlist is entity-keyed (FDIC CERT)
and legitimately open — the peer/counterparty list IS the watchlist. The
threshold bands come from real supervisory authorities (PCA, 2006 CRE
guidance, Texas-ratio literature), each labeled with its authority or marked
"heuristic" honestly.

## API mechanics (CONFIRMED unless noted)

- **Base:** `https://api.fdic.gov/banks`; endpoints `/institutions`,
  `/financials`, `/summary`, `/history`, `/failures`, `/sod`,
  `/demographics`, `/locations`. Docs + per-endpoint dictionaries at
  `/banks/docs`. No API key (swagger marks `api_key` optional; every observed
  client is keyless). Rate limit UNDOCUMENTED — be polite (>=0.6s between
  calls, retry/backoff on 5xx).
- **Envelope (captured response):** `{meta:{total,parameters,index:{name,
  createTimestamp}}, data:[{data:{...}, score:N}], totals:{count}}` —
  records are DOUBLE-WRAPPED (`data[i].data`); `meta.index.createTimestamp`
  is a data-vintage check; financials `ID` = `"{CERT}_{REPDTE}"`.
- **Query syntax:** `filters` = Elasticsearch query-string, UPPERCASE field
  names: `CERT:(628 OR 3511)`, `REPDTE:[20230630 TO *]`, `ASSET:[1000 TO
  9999]`, `ACTIVE:1`. `fields=` comma list (omit -> ~2,269 fields).
  `sort_by`/`sort_order`, `limit` (default 10, max 10,000; **max 500 if >250
  fields requested**), `offset`, `format=json|csv`. `search=` fuzzy name
  lookup on `/institutions`. Aggregation params exist (`agg_by`,
  `agg_sum_fields`) but the agg response shape is UNVERIFIED — out of v1.
- **/financials:** one record per bank-quarter; `REPDTE`="YYYYMMDD"
  quarter-ends; history to 1984Q1. **Dollar fields in $ thousands; ratio
  fields in PERCENT** (captured: ASSET 380997000 = $381B; ROE 16.35).
- **/summary is ANNUAL only** (year x state aggregates, dollar levels, no
  ratio fields) — cannot supply quarterly QBP-style context. QBP time-series
  exists as XLSX downloads, not an API; FRED's QBP series are DISCONTINUED.
  v1 industry context = peer-set medians computed in-workbook.
- **Identity:** `/institutions` fields `NAME, CERT, FED_RSSD, ACTIVE,
  BKCLASS, CITY, STALP, SPECGRP, CB, DENOVO, ESTYMD, ENDEFYMD, DATEUPDT`;
  holding company via `RSSDHCR/NAMEHCR`. Mergers in `/history`
  (`CHANGECODE`, `ACQ_CERT`); failures in `/failures` (`FAILDATE`,
  `RESTYPE`, `QBFASSET`, `COST` = estimated DIF loss, back to 1934).
- **Cadence:** call reports due 30 days after quarter-end; API financials
  land ~35-60 days after quarter-end (QBP publishes ~55 days). Institutions
  data refreshes ~weekly. Exact day-counts UNVERIFIED.

### Verified field set (exact API names; risview_properties.yaml + captured response)

Identity/time: `CERT, NAME, REPDTE`. Size/funding ($000): `ASSET, DEP,
LNLSGR, LNLSNET, BRO, EQ, NETINCQ`. Capital (%): `RBC1AAJ` (Tier 1
leverage-PCA), `RBC1RWAJ`, `RBCRWAJ`, `RBCT1CER`, `EQV`; `CBLRIND` flag
(CORROBORATED). Asset quality: `NCLNLSR` (noncurrent %), `NTLNLSQR`
(quarterly NCO %), `LNATRESR` (ALLL/loans %), `LNRESNCR` (coverage %),
`NCLNLS`, `LNATRES`, `P3LNLS` ($; NO ratio field — compute /LNLSGR).
Earnings (%): `ROAQ, ROEQ, NIMY, EEFFR`. Concentrations ($000): `LNRECONS,
LNRENRES, LNREMULT, LNRE, LNCI`.
**UNVERIFIED fields (Open Questions; tolerate-missing on first live run):**
`ORE` (OREO), `INTAN`, tier-1 dollar level, estimated-insured/uninsured
deposits, AOCI, HTM fair value, `NTLNLSCOQR`.

## Metric framework (cited)

- **CAMELS/UFIRS** ratings are CONFIDENTIAL (never public); the template's
  quantitative lanes mirror C-A-E-L + concentration. M/S not computable
  (S partially proxied by unrealized-loss ratios — fields UNVERIFIED, v2).
- **UBPR peer groups CHANGED Feb 26, 2026**: commercial banks now 8 groups
  by ASSET SIZE ONLY (>$100B; 10-100B; 3-10B; 1-3B; 300M-1B; 100-300M;
  50-100M; <50M). Any "peer band" logic must record this vintage.
- **PCA (12 CFR 324.403):** well-capitalized = total RBC >=10%, Tier 1 RBC
  >=8%, CET1 >=6.5%, leverage >=5%. The capital lane's ALERT authority.
- **CBLR:** floor lowered 9% -> **8% effective July 1, 2026** (OCC NR
  2026-30 / FDIC FIL). CBLR electors report NO risk-based ratios — capital
  lane falls back to the leverage ratio; CRE screens need a denominator
  proxy.
- **Texas ratio** (Cassidy/RBC; St. Louis Fed 2025): (noncurrent + OREO) /
  (tangible equity + reserves); <25% healthy, 50-100% significant stress,
  >100% historic failure signal. v1 computes a documented VARIANT from
  verified fields only: `(NCLNLS + ORE?) / (EQ + LNATRES)` (ORE pending
  verification; intangibles excluded until INTAN verified).
- **2006 Interagency CRE guidance** (OCC 2006-46; 71 FR 74580):
  construction >=100% of total RBC, or total CRE >=300% AND >=50% growth
  over 36 months. CBLR-era proxy denominator: tier 1 + ACL (documented as
  proxy; v1 uses EQ + LNATRES until the tier-1 dollar field is verified).
- **Brokered deposits** (FDI Act s29 / 12 CFR 337.6): restricted below
  well-capitalized — regulatory salience for the funding lane; healthy-bank
  bands are heuristic.
- **QBP Q1 2026 reference points:** industry ROA 1.26%, NIM 3.31%, NCO
  0.59%, problem banks 54 (count public, names confidential).
- **2023 failure lessons:** SVB ~94% / Signature ~90% uninsured deposits;
  unrealized HTM/AFS losses invisible in headline capital ratios. Both
  metrics deferred to v2 pending field verification (uninsured share,
  AOCI/HTM fair value) — flagged, never silently approximated.

## Not-available (scope fence, verified)

CAMELS ratings (confidential) · problem-bank NAMES (count only) · UBPR peer
percentile pages (public but via FFIEC, not this API — UNVERIFIED
programmatic access) · FR Y-9C holding-company consolidated data (FFIEC/
Chicago Fed, not FDIC API; bank-level CERT data only) · intraquarter data
(none exists publicly) · uninsured-deposit precision for <$1B banks (FDIC
estimate, not reported).

## Top traps (bake into spec)

1. **YTD vs quarterly variants** — `ROA/ROE/NTLNLSR/NETINC` are YTD
   (annualized); use `ROAQ/ROEQ/NTLNLSQR/NETINCQ` for clean quarters. The
   #1 mechanical error.
2. **Merged-away banks return stale REPDTEs without error** — join against
   `/institutions` `ACTIVE`/`ENDEFYMD` every refresh; the staleness guard
   (macro-template lesson) applies verbatim.
3. **JSON nulls are real** (not zero): CBLR electors' risk-based ratios,
   pre-2020 CBLRIND, non-applicable items.
4. **Units mixed in one record** ($ thousands vs percent) — the metric
   dictionary carries units per field.
5. **Missing ratios computed client-side** (brokered %, PD30-89 %, CRE
   concentration, loans/deposits, Texas) — deterministic pure functions,
   defined identically in Python and Excel.
6. **Merger survivorship** — survivor balances jump; flag any bank with
   >25% single-quarter asset growth; 36-month CRE growth test is
   merger-distorted.
7. **NCO seasonality** (Q4 cleanup) — compare YoY, not just QoQ.
8. **Uppercase everything** in filters/fields; parse `data[i].data`.
9. **De novo banks** (`DENOVO`/`ESTYMD`) distort ratios and medians.
10. **Regulatory vintage** — CBLR 8% (7/2026) and UBPR 8-band (2/2026)
    definitions must be dated in `_readme`.

## Open Questions (UNKNOWN — flag, never assert)

1. Exact field IDs for: OREO (`ORE`?), intangibles (`INTAN`?), tier-1
   dollar amount, estimated insured/uninsured deposits, AOCI, HTM fair
   value, FHLB borrowings. Verify on first live run; runner tolerates
   missing fields (blank + note).
2. Documented rate limit (none found; observed clients throttle ~1-5 rps).
3. Aggregation-parameter response shape (`agg_by` etc.) — out of v1.
4. Exact publication day-count for new quarters (~35-60 days corroborated).
5. Whether this sandbox's proxy permits api.fdic.gov varies by session —
   the template's live path must be validated at the user's desk (keyless,
   zero setup).
