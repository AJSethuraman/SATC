# Research — Competitor Loan-Book Metric Pack (template #4 v1.1)

Decision research: for competitor loan-book analysis, does the FDIC API
suffice or is direct FFIEC CDR access needed? **Verdict: (A) metric pack on
the existing FDIC template.** 93/93 candidate fields verified present in the
FDIC RISVIEW schema (two independent mirrors of the FDIC's own field
dictionary — 2,377 definitions — plus a captured live response). Verification
sources: `risview_properties.yaml` (clafollett/fdic-bank-find-mcp-server),
`FieldDefs_financials` dump (troystaylor/SharingIsCaring), captured response
(gdickison/dainamic-charts), FDIC SDI dictionary (RSchwinn/fdic).

## What the FDIC API already carries (CONFIRMED)

**Loan-category credit quality — the full matrix.** Per category: 30-89 PD
(`P3*`), 90+ PD (`P9*`), nonaccrual (`NA*`), each with an `R` ratio twin:
construction `*RECONS` (+ splits `*RECNFM`/`*RECNOT`), nonfarm-nonres CRE
`*RENRES` (+ owner-occ splits), multifamily `*REMULT`, C&I `*CI`, 1-4 family
`*RERES` (+ lien/HELOC splits), credit card `*CRCD`, auto `*AUTO`, other
consumer `*CONOTH`, totals `*LNLS`. Balance denominators: `LNRECONS`,
`LNRENRES`, `LNREMULT`, `LNRERES`, `LNCI`, `LNCRCD`, `LNAUTO`, `LNCONOTH`.

**Category net charge-offs** with YTD AND quarterly variants: `NT{cat}` /
`NT{cat}Q` (+ gross `DR*`/`CR*`). NOTE the 8-char truncation quirk:
`NTRECONQ`, not NTRECONSQ.

**The SVB pack (previously deferred as unverified — now CONFIRMED):**
- HTM fair value `SCHF` vs amortized `SCHA` (+ `SCHTMRES` ACL netting) —
  HTM unrealized loss = SCHF - SCHA (computed; no named field).
- AFS fair `SCAF` vs amortized `SCAA` — AFS unrealized = SCAF - SCAA.
- Estimated insured/uninsured deposits: `DEPINS`, `DEPUNINS`, `ESTINS`.
- FHLB advances `OTHBFHLB` (+ maturity ladder, `EFHLBADV` expense).
- AOCI caveat: `EQCCOMPI` is the YTD OCI FLOW (per SDI dictionary), NOT
  the accumulated AOCI stock (folded into `EQUPTOT`) — label correctly.

**Yield/cost (portfolio-level):** `ILNLS(Q)`, `INTINC(Q)`, `EINTEXP`,
`EDEP`, `EDEPDOMQ`, pre-computed `INTINCY(Q)`/`INTEXPY(Q)`, averages
`AVASSET`/`ERNAST5`.

## Verified-ABSENT from the FDIC API (the only true gaps)

Interest income BY loan category and category average balances (so
category-level loan YIELDS cannot be built); UBPR peer PERCENTILES (not
machine-accessible even from FFIEC — internal CDR tables; the distribution
reports are rendered pages only); AOCI as a stock.

## FFIEC CDR mechanics (recorded for the hybrid trigger)

REST replaced SOAP (retired Feb 28, 2026): free account -> Entra ID,
90-day self-service JWT (manual regen), base `ffieccdr.azure-api.us/public`,
7 endpoints incl. `RetrieveFacsimile` (PDF/XBRL/SDF) and
`RetrieveUBPRXBRLFacsimile` (XBRL only), ~2,500 req/hr. **Bulk quarterly
ZIPs need NO login**: tab-delimited per schedule, ~500 MB/quarter, back to
2001Q1, appear ~45 days after quarter-end, regenerated monthly for
amendments. Public domain. If peer-percentile benchmarking ever becomes a
requirement: compute distributions from the bulk ZIPs (no login) rather
than the JWT API.

## The v1.1 pack (build when scheduled)

Add to template #4: a **Dashboard_LoanBook** lane (or extend dashboards)
with per-category credit-quality ratios (use the verified `R`/`QR` twins
where they exist, compute otherwise) + quarterly category NCOs; and the
**SVB metrics**: uninsured-deposit share (DEPUNINS/DEP), HTM+AFS unrealized
loss / (EQ + LNATRES) with the tangible-capital caveat. Thresholds: category
NC rates heuristic vs QBP category norms; unrealized-loss/capital WATCH >25%
/ ALERT >50% (heuristic; SVB >100%).

## Caveats (binding on the pack build)

1. Bank-level (CERT), not holding-company (Y-9C out of scope) — key on lead
   bank subsidiaries.
2. YTD vs quarterly: always the `Q` variants for flows (8-char truncated
   names).
3. Field vintages: `*AUTO` from 2011; construction/owner-occ splits from
   ~2007-08; `DEPUNINS` materially populated for larger reporters only —
   nulls, not zeros, in backfills.
4. AOCI/unrealized are DERIVED (SCHF-SCHA, SCAF-SCAA), and `EQCCOMPI` is a
   flow.
5. Category loan yields + UBPR percentiles are the FFIEC-only residue —
   bulk-ZIP ingest job if ever needed, not the JWT API.
