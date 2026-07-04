# SPEC ADDENDUM — Competitor Loan-Book Metric Pack (template #4 v1.1)

Extends `BUILD_SPEC_FDIC.md`; grounded in `RESEARCH_COMPETITOR_PACK.md`
(93/93 fields verified). Governed by `TEMPLATE_CONTRACT.md` (L1-L8).
**Design decision (user, binding): two-track competitor surveillance —
CONSUMER classes get the DQ/NCO track (retail classification is
DPD-formula-driven under the Uniform Retail Credit Classification policy,
so DQ IS the classification story); COMMERCIAL classes get Call-Report DQ
as the public floor here, with criticized/classified arriving via the
EDGAR template (#6).**

## 1. New metrics (all fields verified in RESEARCH_COMPETITOR_PACK.md)

### Dashboard_LoanBook — consumer track (per bank, quarterly)
Per class {card `CRCD`, auto `AUTO`, other consumer `CONOTH`, 1-4 family
`RERES` (+ HELOC `RELOC` column)}: PD30-89 rate (`P3{c}`/`LN{c}` or the
verified `P3{c}R` twin), PD90+ rate, nonaccrual rate, quarterly NCO rate
(`NT{c}Q` over balances — NEVER the YTD field, F1). Peer-median row per
column.

### Dashboard_LoanBook — commercial floor (same tab, second band)
Per class {construction `RECONS`, nonfarm-nonres CRE `RENRES`, multifamily
`REMULT`, C&I `CI`}: PD30-89 / PD90+ / nonaccrual / quarterly NCO rates.
Band subtitle carries the honest note: "Public Call-Report proxy —
commercial risk ratings lead delinquency; criticized/classified view via
the EDGAR tracker."

### SVB / funding-stress metrics (extend Dashboard_Funding_Concentration)
- Uninsured deposit share = `DEPUNINS`/`DEP` (null-tolerant: DEPUNINS is
  materially populated for larger reporters only — blank + note, never 0).
- Unrealized securities loss / capital cushion =
  ((`SCHA`-`SCHF`) + (`SCAA`-`SCAF`)) / (`EQ` + `LNATRES`) — both legs
  computed (no named unrealized field exists); label as the derived
  definition; note `EQCCOMPI` is a FLOW, not AOCI stock (do not use).
- FHLB reliance = `OTHBFHLB`/`ASSET`.

## 2. Thresholds (heuristic unless labeled; numeric-typed cells, L8)

Consumer: card PD90+ w1.5/a2.5; card NCOq w2.5/a4.0 (card runs
structurally high — QBP context in subtitle); auto PD30-89 w2.5/a4.0;
resi NA w1.0/a2.0. Commercial floor: CRE NA w1.0/a2.0; construction
PD30-89 w1.5/a3.0; C&I NCOq w0.5/a1.0. SVB pack: uninsured share w40/a60
(2023 failures: SVB ~94%); unrealized/capital w25/a50 (SVB >100%);
FHLB/assets w10/a20. All heuristic — labeled so in the help column.

## 3. Mechanics

- Fetch: extend the ONE bulk /financials request's `fields=` list (~30 ->
  ~75 fields; still one request, far under limits and the 250-field cap).
- Metric dictionary `[SERIES]` grows by the new metric rows (same
  slot-expansion; raw layout anchors recomputed — THIS IS A REBUILD of the
  workbook, not an in-place config edit; version the workbook v1.1).
- Field-vintage tolerance (F-traps): `*AUTO` fields exist only from 2011;
  construction splits from ~2007-08 — irrelevant at raw_slots=16 quarters
  but the parser stays null-tolerant.
- Derived-metric parity: every computed ratio defined identically in
  Python and Excel, parity-tested (existing harness pattern).
- Demo provider: extend seeded ranges per class (card NCO 1-5%, auto PD
  1-3%, uninsured share 20-70%, unrealized/capital 5-60%) so 1-2 demo
  banks trip the new bands.

## 4. Tests (additive)

`test_pack_fields_in_bulk_request` (all new fields in the fields= list,
under 250), `test_consumer_track_rates` + `test_svb_derived_metrics`
(hardcoded expectations incl. null DEPUNINS -> blank), `test_loanbook_tab`
(reload: both bands, medians, statuses), recalc parity extended to the
LoanBook tab, email-sim gains a per-class alert section.

## 5. Out of scope (unchanged)

Category loan yields + UBPR percentiles (FFIEC bulk-ZIP job only if ever
needed); AOCI stock; holding-company consolidation (CERT-level only —
EDGAR covers the HC view).
