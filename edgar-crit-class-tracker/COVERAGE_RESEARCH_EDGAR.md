# Coverage Research — SEC EDGAR Criticized/Classified Tracker (v1)

Two-agent verification pass (access mechanics + disclosure content) feeding
BUILD_SPEC_EDGAR.md. SEC hosts were proxy-blocked from this sandbox; evidence
comes from mirrors of SEC's own docs, the official us-gaap taxonomy linkbases
(grepped locally), a real bank XBRL instance, and search snippets of actual
10-Q filings — each claim marked CONFIRMED/PARTIAL/UNVERIFIED in the agent
reports (preserved in the session record; key findings below).

## Bottom line

**Feasible — GREEN — with a tiered design.** The mission (quarterly
commercial criticized/classified per publicly-traded competitor bank) works
if and only if the pipeline bypasses SEC's convenience JSON APIs for the
crit/class lane: those APIs are structurally NON-DIMENSIONAL (their fact
schema has no field for axis/member data), and the CQI tables are dimensional
(grade x loan class). The bypass is clean and keyless.

## Access architecture (mechanics agent)

- **Fair access:** 10 req/s max, declared User-Agent ("Org email") REQUIRED
  (absent/generic UA -> silent 403 + ~10-min IP block), no key. Public
  domain.
- **Discovery:** `data.sec.gov/submissions/CIK{10d}.json` — entity metadata
  (incl. `sic`) + `filings.recent` as COLUMNAR parallel arrays; older history
  via `filings.files[]`. The **`items` array carries 8-K item numbers** —
  credit-event lane (esp. **2.04 triggering events/acceleration**, 2.06
  impairments, 4.02 non-reliance, 1.03 receivership) filters with zero extra
  requests.
- **Dimensional CQI path (the decisive finding):** every iXBRL filing
  directory contains an EDGAR-generated **"extracted XBRL instance"**
  (`{primarydoc}_htm.xml`) — plain XML with `xbrldi:explicitMember`
  dimensions, parseable with stdlib (~300 LOC; no arelle, no iXBRL HTML
  parsing). Pre-2019 backfill: the EX-101.INS instance, same parser.
- **Bulk backfill:** SEC "Financial Statement AND NOTES Data Sets" (monthly/
  quarterly ZIPs; DIM/NUM tables carry dimensions via `dimh` hash) — use for
  the initial 8-12 quarter history; instances for quarterly increments.
  Plain FSDS lacks notes; frames/companyfacts are dead ends for CQI
  (companyfacts stays as the consolidated-fundamentals lane).
- **Timing:** 10-Q at 40/45 days; **no Q4 10-Q** — Q4 arrives in the 10-K at
  60/75/90 days. companyfacts updates minutes after acceptance.
- **Enumeration:** registrant is the HOLDING COMPANY; bank universe spans
  SIC 6020/6021/6022/6029/6035/6036 + 6712/6710 — but v1 uses a hand-curated
  peer CIK list (the [PEERS]-style mechanism).

## Disclosure content (content agent)

- **Accounting basis:** ASC 326-20-50-5 — amortized cost by CQI, BY CLASS,
  quarterly; PBEs add vintage disaggregation (326-20-50-6; revolvers exempt);
  ASU 2022-02 added gross write-offs by vintage (FY2023+). Commercial
  portfolios use regulatory-style grades as the CQI; consumer uses FICO/DQ —
  which independently validates the suite's two-track design.
- **Uniform definitions (quote in `_readme`):** interagency lineage
  1938/1949/1979/**2004 Uniform Agreement**; Special Mention adopted
  interagency 1993 (SR 93-30). Definitions per the OCC Rating Credit Risk
  handbook. **Classified = Substandard + Doubtful + Loss; Criticized = SM +
  Classified** (SNC usage).
- **Taxonomy facts (grepped from official linkbases):** line item =
  `FinancingReceivableBeforeAllowanceForCreditLoss` (and
  `...ExcludingAccruedInterest` twin); axis = `InternalCreditAssessmentAxis`;
  members = `PassMember`, **`CriticizedMember` (standard, and it PARENTS
  SpecialMentionMember/SubstandardMember/DoubtfulMember/
  UnlikelyToBeCollectedFinancingReceivableMember)**; there is NO standard
  ClassifiedMember. Class axis keeps its legacy name
  (`FinancingReceivableRecordedInvestmentByClassOfFinancingReceivableAxis`).
  **Vintage is line items, NOT an axis** — the grade total per class is a
  single fact; the tracker can ignore vintage entirely (and MUST not sum
  vintage rows on top of the total — double-count trap).
- **Real-world disclosure families** (verified against actual 10-Qs):
  - `grades_full`: Fifth Third (CIK 35527), Zions (109380 — explicitly
    "consistent with published regulatory classifications"), Regions
    (1281761), Comerica (28412), Huntington (49196, "OLEM" label), Truist
    (92230, "Nonperforming" variant), BOK (875357).
  - `criticized_only`: KeyCorp (91576 — Pass/Criticized-accruing/
    Criticized-nonaccruing), M&T (36270).
  - `ig_nig`: JPMorgan (19617 — investment/noninvestment grade; criticized
    only in MD&A text), USB (36104, compressed).
  - Estimated ~60-75% of $10B+ regionals disclose SM/Substandard separately;
    >90% support at least pass-vs-criticized (UNVERIFIED estimate — verify
    empirically at build).
- **Extension-member risk:** the non-canonical buckets (criticized-accruing,
  substandard-accrual, OLEM, nonperforming-as-grade) are likely filer
  extensions. **Design requirement: a per-bank member-mapping table
  (standard + known extensions) with drift detection — never a fixed member
  list.**
- **Text fallback:** MD&A is outside the XBRL tagging mandate — criticized
  ratios for IG/NIG banks live in text; EDGAR full-text search
  (efts.sec.gov) is the fallback/cross-check lane.

## Metric set (v1 proposal)

Per bank x quarter (commercial classes, coarse-mapped to C&I / CRE /
construction / other): Tier 1 **criticized ratio** (works for ~all banks —
sum of grade members or native criticized rows); Tier 2 **classified ratio +
SM ratio** (grade-disclosing banks only, flag-gated); QoQ/YoY deltas;
criticized-$ mix by class; per-bank coverage flags
(`grades_full|criticized_only|ig_nig`), accrued-interest variant, mapping
version. Q4 gap handled explicitly (10-K timing).

## Top traps (bake into spec)

1. Convenience APIs are non-dimensional — instances/notes-datasets only for
   CQI. 2. Accrued-interest twin tags — per-bank preference order. 3. Vintage
   line-item double-count. 4. Extension members/axes — per-bank map + drift
   alarm. 5. Class taxonomies differ per bank — coarse normalization map.
6. No Q4 10-Q; vintage columns re-label at fiscal roll. 7. Amendments
   (10-Q/A) — dedupe by (cik, period, tag, dims) keeping latest acceptance.
8. CIK padding split (10-digit for data.sec.gov, unpadded in /Archives).
9. Definitions uniform, application timing is bank judgment (exam-cycle
   artifacts in QoQ moves). 10. HC-level consolidation vs FDIC CERT-level —
   reconcile approximately, never silently. 11. Corporate proxies may block
   sec.gov — ship a connectivity self-test + allowlist note.

## Open questions

Instance-level tagging of the big banks (which exact members each seed bank
uses — resolved empirically by the build's per-bank mapping bootstrap);
exact share of grade-disclosing regionals; FSNDS current zip sizes.
