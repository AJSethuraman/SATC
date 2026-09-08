# BACKLOG — Credit-Risk Template Suite

The shared to-do log. Statuses: `[ ]` open · `[~]` in progress · `[x]` done.
Anyone (human or agent) picking up work starts here; finished items move to
the bottom log with a date. Companion docs: `PROJECTS.md` (what exists),
`TEMPLATE_CONTRACT.md` (how everything must behave).

---

## 1 · Validation debts (needs YOUR desk — the build box can't do these)

- [ ] **Open each .xlsm in real Excel** and click ExtractFiles once
      (FRED, bureau, macro, FDIC). The embedded VBA container is
      olevba-verified but has never met desktop Excel. Fallback if any
      complain: `_code_vba` paste-in.
- [ ] **Macro template: first live FRED run** — needs your FRED_API_KEY
      (`$env:FRED_API_KEY`), then `runner.py -w <book>.xlsm` per RUN.txt.
- [ ] **FDIC template: first live run** — keyless, zero setup. Also run
      `runner.py --lookup` to verify/replace the 9 illustrative seed CERTs
      with your real peer list.
- [ ] **Bureau template: bind the live HHDC schema** — `_parse_table` is
      deliberately unbound (the NY Fed table layout was unverifiable);
      demo works fully; live needs the real column mapping (Open Q#5).

## 2 · v1.1 improvements (per shipped template)

- [ ] **FDIC:** blank stale banks' latest quarter + show STALE in the
      Watchlist status column (removes the documented median divergence);
      optional UBPR asset-band medians. (SVB metrics SHIPPED in pack v1.1.)
- [ ] **Macro:** county-level drill-down via FRED's LAUS county mirrors
      (ids must be enumerated via release 116, never constructed);
      consider `EQFXSUBPRIME*` county subprime share pending its FRED
      license note (Open Q).
- [ ] **FRED (template #1) contract-alignment pass:** it predates the
      contract — audit for the L7 clear-blocks bug class, grandfathered
      `--backend` flag, `Watchlist_Geo` tab name; align or explicitly
      re-grandfather each item.
- [ ] **Bureau:** licensed Class C adapter swap when/if a Prama-class
      feed is ever contracted (the gate opens only then).

## 3 · Next templates (researched, ranked; process per contract)

- [ ] **#7 BLS LAUS county unemployment monitor** — monthly county-FIPS
      early warning; free API key, 500 q/day. (Partially covered by the
      macro template's state lane; standalone only if county cadence
      proves valuable at your desk.)
- [ ] **Later bench:** HMDA loan-level (annual research pull), SBA 7(a)/504
      FOIA (commercial charge-offs by county+NAICS), NCUA credit-union
      sibling of FDIC, FHFA NMDB aggregates.

## 4 · Suite infrastructure ideas (unscheduled — promote when wanted)

- [x] **Provenance/tie-out (contract §12, user requirement) — SHIPPED
      for FDIC in pack v1.1** (_provenance tab + --tieout with facsimile/
      BankFind URLs); EDGAR gets accession provenance in its build;
      retrofit FRED/bureau/macro/CFPB opportunistically:** every value
      traceable to the official document — _provenance tab + `--tieout`
      mode. **Field→Call-Report mapping DONE** (fdic-peer-monitor/
      PROVENANCE_MAP_FDIC.md — MDRM codes verified against FFIEC's own
      bulk-data captions; direct facsimile URL keyed by CERT; RC-N
      column structure confirmed). Implementation lands with the
      competitor pack; EDGAR gets accession-based provenance; retrofit
      others opportunistically.
- [ ] Suite-level conformance check: one script asserting every template's
      shared modules are byte-identical, embedded code is ASCII, tabs match
      the contract, and all suites are green (CI-able).
- [x] Control Center v2 SHIPPED: status board (purpose + last run + alert
      counts read from each workbook, no opening needed), Refresh ALL
      (demo), Tie-out button, --doctor env/host check with allowlist
      guidance.
- [x] Single suite bundle SHIPPED: build_suite.py (one ASCII file = all
      template bundles + control_center; menu or --all; regenerate with
      make_suite_bundle.py — new templates join automatically).
- [x] SUITE_GUIDE.md SHIPPED: the two-page operator manual (setup, daily
      driving, which-workbook-answers-what, verification, troubleshooting).
- [ ] Regenerate the visual suite-overview page from live demo digests
      (currently hand-assembled).

- [ ] Idea (deferred): shared peer-list sync across FDIC/EDGAR workbooks —
      same banks, different keys (CERT vs CIK); needs a name-based
      crosswalk; revisit after both templates are in real use.

## 5 · Credit Review OS (`credit-review-os/` — consulting workpapers, not monitoring)

v1 (C&I loan-level engine) shipped 2026-07-05 — see Done log. Roadmap, in
order; each LOB = a new program YAML + crosswalk on the same engine:

- [x] **Second demo bank overlay** — SHIPPED 2026-07-05: `Sample State Bank`
      overlay (1-10 scale, tighter thresholds) builds on the unchanged C&I
      program; recalc tests prove threshold-flips (DSCR 1.22 vs 1.25 floor,
      leverage 3.95x vs 3.5x). 0 code changes (PRD success metric met).
- [~] **LOB build-out (cash-flow-out order):** SHIPPED 2026-07-05:
      **income-producing CRE** (NOI DSCR, occupancy, appraised-value LTV,
      rent-roll evidence), **owner-occ CRE** (occupant-business global cash
      flow per the RC-C owner-occupied definition), **construction/ADC**
      (loan-to-cost, interest-reserve depletion, as-completed LTV, draw
      inspections), **agricultural** (farm operating DSCR, carryover debt,
      farmland/chattel LTV, crop insurance) — all config + crosswalk, zero
      engine changes. Remaining (each GATED on its own grill/design pass):
      consumer+residential (**first Mode B / product_conformance build** —
      schema already carries the mode) → multifamily / leases / specialty.
      **Mode B SHIPPED 2026-07-05** (grilled with the owner same day; PRD:
      `credit-review-os/docs/prd-mode-b-product-conformance.md`; issues
      #73/#74) — per-product PS_ tabs (conformance sample grid + URCCP pool
      classification by live formula, cited to 65 FR 36903 / OCC 2000-20 /
      FDIC FIL-40-2000; overlay may tighten the clock, never loosen — loader
      enforced), rate-vs-tolerance findings (compliance per-occurrence),
      stratified random + judgmental segments with per-stratum analytics,
      computed buy-box FRINGE flag + fringe-vs-core norms block, shared test
      library with per-product knob overrides, loan-number-only identity
      (zero person names — stricter than Mode A), product-level de-identified
      mart + re-ingest. Three demo products span every URCCP branch
      (indirect auto / credit card / HELOC). Remaining LOBs (multifamily /
      leases / specialty) are config work on either mode as needed.
- [ ] **Mixed-mode workbooks** (one engagement covering commercial loan-level
      + retail conformance in one deliverable) — decided against for Mode B
      v1 (one mode per workbook); revisit if real engagements demand it.
- [ ] **Statistical sample-size calculator** (attribute sampling: confidence /
      tolerable rate → n) — decided against for Mode B v1; the documented
      stratified-random + judgmental basis is the method. Revisit on demand.
- [x] **ASCII-bundle build-on-target** — SHIPPED 2026-07-05: `credit-review
      bundle <engagement>` emits a single pure-ASCII script (contract §11
      pattern, gzip+base64) that rebuilds the workbook byte-identical in an
      empty folder on a machine with only openpyxl+PyYAML; tested for
      ASCII purity, byte-parity, and no crypto/formulas deps on target.
- [ ] **Doc parsing / OCR pre-fill** — proposal lane only; deterministic core
      stays authoritative (needs its own grill/design pass).
- [ ] **Optional local LLM extraction assist** — human-confirmed proposals
      only, never in the data path, never writes a rating (own design pass).
- [ ] **ACL/CECL export** — emit classifications for the bank's allowance
      system (OCC *Allowances for Credit Losses* is the source when scoped).
- [ ] **Pin-cite confirmation sprint (needs YOUR desk)** — verify crosswalk
      page cites against the live regulator PDFs before the first filed
      workpaper. Re-attempted 2026-07-05 from the build box: occ.gov /
      fdic.gov / federalregister.gov / cdfifund.gov all still 403 to
      automated egress — this requires a human browser.

## 6 · credit-suite — ground-up one-engine consolidation (grilled + PRD'd 2026-09-03)

The big rebuild: collapse the six copy-pasted `.xlsm` monitors into ONE shared
engine (`credit-suite/`), all ideas intact, growing to first-class Call Reports.
PRD: `credit-suite/docs/prd-credit-suite-consolidation.md`. Supersedes the
overlapping items in §2 (FRED contract-alignment — partly done 2026-09-03), §3
(#7 BLS as an adapter, not a copy), and §4 (suite conformance check → M2).

Cross-cutting principles (durable, outlive this PRD):
- Keep emailable/DLP-safe via a build-time **inliner** (shared lib at dev time,
  self-contained ASCII bundle out) — reversible to an installed package later.
- `credit-review-os` stays a SEPARATE product (borrower PII + encryption); never
  merged — it may consume engine patterns, not the reverse.
- Every value traceable to its official record (§12); entity sets are config not
  code (§13); carried lessons L1–L8 remain in force.
- Build/validate on the unlocked PC → **live** verification (live FRED+FDIC pull,
  real-Excel ExtractFiles) is part of "done", not deferred.

Phased (one effort, sequenced):
- [ ] **M1 spine:** `credit-suite` engine + inliner; migrate **FDIC + FRED**
      (the two most divergent shapes); full rigor + **cell-for-cell output parity**
      vs the current shipped `.xlsm`; live FRED/FDIC + real-Excel acceptance.
- [ ] **M2:** SCOPED 4 Sep 2026 into issues #208-#214 (7 slices, dependency-ordered).
      migrate bureau/macro/CFPB/EDGAR onto the engine; retrofit §12
      provenance to all six; suite-wide conformance CI (single-sourced modules,
      contract-shaped tabs, all green on push).
- [ ] **M3:** raw **FFIEC CDR** provider + **FR Y-9C** holding-company —
      **opens with a `research` pass** (CDR bulk Public Data Distribution vs SOAP
      webservice; RSSD vs CERT; Call Report FFIEC 031/041 vs FR Y-9C).
- [ ] **M4 bench:** NCUA, HMDA, SBA, FHFA NMDB adapters; cross-monitor peer sync
      (one entity list across FDIC CERT + EDGAR CIK via a name crosswalk).

## 6b · credit-suite — the ten-year tie-out (5 September 2026)

Everything the feed holds, checked against a document this firm does not
control. **67,970 values. 52,759 tied. Nothing disagreed.**

| | values | tied to an outside source | differed |
|---|---|---|---|
| Banks — 12 × 40 quarters × 68 fields | 32,640 | 28,667 | 0 |
| Macro — 142 series, 1943 to 2026 | 35,330 | 24,092 | 0 |

The 3,973 bank values not tied: 3,840 ratios the FDIC computes rather than banks
filing them, 77 flows in a quarter spanning a merger, 56 lines the form did not
carry that quarter. The 11,238 macro observations not tied are **24 whole
series**, not scattered gaps — Case-Shiller's paywalled history (10,091), a
percent change the Board never tabulates (1,001), and the loan officer survey's
large-bank split (146). Each row says which.

**Evidence.** 480 facsimile PDFs fetched, 0 failures. **49,066 rows
photographed** — every bank, every quarter, the filing's own page header in the
shot so *same entity, same period* is read off the picture rather than trusted.
**132 exhibits**, one per bank-year, 664 MB, in
`credit-suite/docs/tie-out/banks-10y-2026-09-05/`. The PDFs are gitignored with
one specimen kept and `manifest.csv` as the record; the builder regenerates all
of them in six minutes.

### What running it found

1. **`LNLSGR` cited a line the FDIC does not use.** Nine of 480 bank-quarters
   came back as differences, always exactly $1,000, on a $200bn balance, across
   three unrelated banks in six unrelated quarters. The bank files that total
   twice: RC-C Part I line 12 as one rounded figure, and RC 4.a + 4.b as two
   separately rounded halves. The FDIC publishes the sum of the halves in all
   480; line 12 agrees in 471. Right value, wrong citation — invisible until
   somebody follows it. Fixed, two guard tests, guard mutated and confirmed red.
2. **Five merger quarters** would have been reported as the FDIC disagreeing
   with the filings. Ten years hold **eleven** acquisitions; the sixteen-quarter
   window had seen six. Now gathered through the shipped `mergers` module rather
   than a hand-rolled history query on the wrong date field.
3. **The Fed charge-off parser could not read an `n.a.` cell.** It matched runs
   of digits, so a 1985 row gave one value instead of eleven and 304 real
   observations were reported as "no source for this period".
4. **Two obstacles fell when tested rather than described** — +1,306
   observations. The G.19 unadjusted total has no single Board table but is the
   sum of two the Board does publish, tying to the cent for all 1,002 months.
5. **One requested field does not exist.** `NTRENREQ` has been asked of the FDIC
   in every run this software has made and returned never; the FDIC omits a name
   it does not have rather than rejecting the request.

### What I got wrong, in the same session

- Wrote that the FDIC "publishes no quarterly version" of the CRE charge-off,
  committed it as a test comment, and it was wrong four hours later. The FIELD
  does not exist; the QUANTITY does, as `DRRENRSQ` − `CRRENRSQ`, an identity
  that held 200 of 200 on the categories where the FDIC publishes the net. Same
  finding as #1 above, which is a reason to have looked harder the first time.
- The deep macro pull reported **"50 of 50 series"** when the seed defines 142.
  A denominator that counts what it found rather than what there was.
- The export built its unit and title table from three attribute names, two of
  which exist; 92 generated geography series fell through to a stale snapshot.
  Third artifact in one session bitten by reading a copy of the source of truth.
  The explanation tabs now contain **no typed number at all** — every count in
  the prose is computed from the delivered CSVs at build time.

### Docket answers (form `0b2cae0b`, answered 5 Sep 2026)

| | Question | Answer | Their words |
|---|---|---|---|
| D1 | Resolve the merge conflict on `canon/LOG.md`? | Yes, resolve it | |
| D2 | Rebuild the shipped monitors now or at next release? | Rebuild now | |
| D3 | Keep the unverifiable Case-Shiller history, shaded? | Keep, shaded | |
| D4 | Keep the eight FDIC-computed ratios in a raw feed? | Keep them | *"keep them especially if they can be tied to. like we have done."* |
| D5 | How deep should the first scheduled run go? | Widen it | *"yeah why not, this is going to also help me with another project so that adds value / also... datapoints... things like home owner insurance premiums can be important. maybe you should poke around at things that don't sound important and throw suggestions out"* |
| D6 | Build the consistency flags? | Build the top five | |
| D7 | Swap the twelve banks for a real peer group? | Keep these twelve | *"I can get them but honestly i won't use the data until i have you swap stuff out and there is no reason to throw away data we've already verified"* |

D5 produced the ten years above **and** the opportunity scan D5's second half
asked for. D6 landed as five checks and 66 tests, merged here; its verdict type
refuses to hold "PASS over nothing", and its `Comparability` record has no field
a repaired number could go in.

### The opportunity scan (D5, second half)

23 candidates, ranked, each fetched live rather than assumed. 83 FDIC field
names requested, 82 returned; 115 FRED ids requested, 102 returned. **Seven of
the twelve bank candidates were tied to a bank's own filed XBRL**, not merely to
the FDIC. Report: `scratchpad/opportunities.md` (session-local).

- **Utilization exists and is not in the feed.** `UCCRCD` and `UCLOC`, 480 of
  480 bank-quarters, tied to the filed report to the dollar. Card utilization
  19.99% (2016Q4) → 16.79% (2020Q4) → 20.35% (2025Q4), now above
  pre-pandemic; Capital One 26.3% against JPMorgan 16.2%.
- **Homeowners insurance** is `PCU9241269241262`, the BLS producer price series,
  +9.1% in 2024 after two flat decades. **The CPI has no homeowners insurance
  item at all** — `SEHD` is tenants' and contents cover, and
  `PCU5241265241262` is the insurer's price net of expected losses. Both look
  right and are not.

### Docket `47179bd6` — answered 5 Sep 2026

| | Question | Answer | Their words |
|---|---|---|---|
| D8 | Add `UCCRCD` + `UCLOC` (utilization)? | **Add both** | |
| D9 | Close the `NTRENREQ` blank with `DRRENRSQ` + `CRRENRSQ`? | **Add both halves** | |
| D10 | Add the BLS homeowners-insurance series? | *not yet* | *"I need more info on this. Your explanation isn't good enough"* |
| D11 | How far down the ranked 23? | *not yet* | *"Give me the list and why we'd want them and which you recommend"* |
| D12 | Feed only, or rebuild the dashboard too? | **Feed only** | |
| D13 | What should the recurring schedule run? | **Manual, when I ask** | |
| D14 | Which evidence layers to store? | **Layers 1, 3 and 4** | *"But we can save them locally on the forge instead of taking space on git"* |
| D15 | Greyscale or colour evidence? | **Greyscale** | |

**D14 reversed a storage decision made an hour earlier.** The exhibits had been
committed and pushed (451 MB); they now live on the Forge at `C:\\Users\\ajish\\SATC-evidence\\banks-10y-2026-09-05\\`, outside any
git working tree. Outside rather than merely gitignored inside: an ignored file
is one `git clean -xfd` away from gone. `manifest.csv` and `README.md` stay
versioned, and the builder writes the manifest in the same run that writes the
PDFs, MERGING rather than overwriting — the first version truncated a 132-row
record to one row the moment a single bank-year was rebuilt, which is exactly
how the tool is meant to be used.

**D13 means there is no schedule.** Nothing runs on a timer; a re-verification
happens when the firm asks. The quarterly and annual shapes stay written down
for whenever that is.

**What the storage question turned up on the way.** Being told to store all of
it prompted the question nobody had asked: did the pictures have to be that big?
A Call Report page is black text and hairline rules on white, so the colour
channels were carrying nothing. Measured over a random 60 strips — colour
11.6 KB mean, greyscale 6.2 KB (54%), **16-level greyscale 4.2 KB (36%)**, 1-bit
1.9 KB (17%) — then rendered side by side and LOOKED AT rather than chosen on
the ratio. Greyscale is indistinguishable at reading size; 1-bit is legible but
the table rules go ragged. **664 MB → 451 MB**, nothing cropped, nothing
scaled down.

Also: *"facsimile"* had been used forty times across this work and never once
defined. It is an exact copy, the same word as a fax machine, and what
cdr.ffiec.gov serves is the filled-in form itself — schedule headings, printed
line numbers, codes in their boxes, the bank's own figures in the columns. Not a
summary and not a database made to look like a form. That distinction is the
whole reason a photograph of it counts as evidence, and it sat inside a word the
reader was expected to already know. Now explained in the exhibits README and on
the workbook's sources tab.

### Still open after the docket

Two answers were "not enough information", which is a finding about the docket
and not about the firm:

- **D10 homeowners insurance.** *"Your explanation isn't good enough."* Owed: a
  proper account of what the series measures, why an insurance premium bears on
  credit at all, and what the two look-alikes actually are.
- **D11 the ranked 23.** *"Give me the list and why we'd want them and which you
  recommend."* Owed: the list itself, not a summary of it. The scan produced it;
  the docket described it and never showed it.

Landed from the answers: `UCCRCD`, `UCLOC`, `DRRENRSQ` and `CRRENRSQ` go into
the FEED only (D12), which means the deep pull's field list rather than
`RAW_FIELDS` — changing `RAW_FIELDS` re-cuts `raw_slots`, which the layout
says is built into every dashboard formula.

Suite **611 passed, 0 failed** (545 + 66 merged).

### Docket `0adcad79` — answered 7 September 2026

| | Question | Answer | Their words |
|---|---|---|---|
| N1 | Competitors: add to the twelve, or replace? | **Add them** | |
| N2 | The bank list lives in a temp folder — move it into the repo? | **Move it** | |
| N3 | Rotate the FRED and BLS keys? | **Leave them** | |
| N4 | PR #257 — merge or keep draft? | **Keep it draft until I look** | *"send me the excel sheet"* |

The workbook was sent. Two of the four should not have been on that page: moving
a file into the repository was an engineering call to make rather than ask, and
it re-opened a question the record already answered on 5 September when the
exhibits moved to the Forge for exactly the same reason. Behaviour 19 — *do not
manufacture the next decision* — was in force and was not followed.

### Goal named, and met

**Swapping the peer group is a one-step change.** Ends when all six pipeline
stages run clean against a peer list that has changed.

Distance ran **0 of 6 → 6 of 6**. The first published distance was wrong and is
worth recording as such: it read "3 of 6 done", and the three were facts about
the code's existing shape rather than work completed — a fraction that started
part-way for free and could not shrink. The firm asked whether the goal had been
assessed as the behaviour requires. It had not.

Proven on **cert 6672, Fifth Third Bank**, a bank the project had never touched,
with no script edited:

| | Stage | Result |
|---|---|---|
| 1 | filings | 40 of 40 quarters |
| 2 | facsimiles | 40 of 40 |
| 3 | fields | 3,480 values over 40 quarters |
| 4 | verify | **638 tie, 0 differ** |
| 5 | photograph | 24 cited rows locatable, 0 missing |
| 6 | export | 3,480 rows would join the deliverable |

### What landed

- **`config/peers.json`** — the peer group in the repository, generated from
  `series_seed.PEERS`, with each certificate checked against the legal name on
  that bank's own filed front page. **12 of 12 verified.** That check existed
  nowhere before: everything else proves the FDIC agrees with a filing FOR A
  GIVEN CERTIFICATE and proves nothing about whether the certificate is the bank
  whose name we print. The seed's own comment had said nine of the twelve were
  "illustrative from public sources and must be re-verified before a live run".
- **`tools/tieout/resolve_banks.py`** — names to certificates, showing the
  match and stopping. It caught two of the FDIC's own quiet behaviours: the query
  must be `search=NAME:<terms>` (a bare search returns an empty list, which reads
  as "no such bank" rather than "wrong query" — the first version reported that
  Fifth Third Bank does not exist), and a name outlives an institution, so
  "Fifth Third Bank" matches a live cert 6672 and a dead cert 993.
- **`tools/tieout/prove_peer_swap.py`** — the six-stage proof above.

### Next

Waiting on the competitor names. Everything after that is mechanical: resolve,
confirm the matches, add to free slots (28 of 40 are free), run the chain.

### Peer expansion — 7 September 2026

The firm sent ten names. **Three were already in the set**: US Bancorp, PNC
Financial and Truist Financial are the holding companies of U.S. Bank NA (6548),
PNC Bank NA (6384) and Truist Bank (9846), all already verified over ten years.
Seven are new, now in slots 13-19 of `series_seed.PEERS`.

| Asked for | Bank that files the Call Report | Cert | Holding company on the FDIC record |
|---|---|---|---|
| Fifth Third Bancorp | Fifth Third Bank, National Association | 6672 | FIFTH THIRD BCORP |
| Huntington Banc | The Huntington National Bank | 6560 | HUNTINGTON BANCSHARES INC |
| First Citizens Banc | First-Citizens Bank & Trust Company | 11063 | FIRST CITIZENS BANCSHARES INC |
| Citizens Financial | Citizens Bank, National Association | 57957 | CITIZENS FINANCIAL GROUP INC |
| M&T Bank Corp | Manufacturers and Traders Trust Company | 588 | M&T BANK CORP |
| Regions Financial | Regions Bank | 12368 | REGIONS FINANCIAL CORP |
| Zions Bancorp | Zions Bancorporation, N.A. | 2270 | *(none — the bank IS the top-tier entity)* |

**A holding company files an FR Y-9C with the Federal Reserve. It has no FDIC
certificate and files no Call Report**, so the bank is what can enter the feed.
Searching the FDIC for a holding-company name does not fail cleanly — it
word-matches and returns a real, live, unrelated bank:

    "PNC Financial"     -> PlainsCapital Bank, University Park TX, $12.7bn
    "Truist Financial"  -> Parkside Financial Bank & Trust, Clayton MO, $1.1bn

Both matched on the word "Financial", and either would have tied perfectly under
the wrong label. Every certificate above was instead confirmed against the FDIC's
own `NAMEHCR` field on that bank's record. `tools/tieout/resolve_holdcos.py`
does this; `resolve_banks.py` does the simpler bank-name case.

### Goals in flight

**Next: all seven pulled and verified.** Ends when each has 40 quarters of all 87
fields tied to its own filed Call Reports with zero differences, photographed to
the same standard as the twelve. **Distance: 0 of 7.**

**Final: one output the firm can forward to their work email.** The workbook plus
a covering document that stands on its own to a reader who was not here.

The chain is proven to run on a bank it has never seen — 6 of 6 stages on cert
6672, no script edited — so this is volume, not new ground.

### The seven peers, verified — 7 September 2026

All seven are in and verified, to the same standard as the twelve: forty
quarters each, eighty-seven fields, every value checked against that bank's own
filed Call Report and every cited row photographed off the filed page.

| | |
|---|---|
| bank values | **66,120** (was 32,640 over twelve banks) |
| verified against a filed Call Report | **59,544** |
| macro observations verified | **65,843** |
| **total values / verified** | **143,201 / 125,387** |
| differences | **1** |
| certificates checked against the filing's own front page | **19 of 19** |
| merger quarters found | **33** (eleven, over the twelve banks) |
| suite | **613 passed, 0 failed, 0 skipped** |

**Distance: 7 of 7.**

### What adding them found

Seven banks the code had never seen found six defects. Not one was found by a
test, and every one was in our software rather than in anybody's data.

1. **Change code 216 was not on the merger allowlist.** First-Citizens absorbed
   Silicon Valley Bridge Bank on 26 March 2023 — the largest acquisition in
   the whole peer set — and the FDIC files it as *Bridge Bank Resolution*.
   The allowlist refused to guess and reported it unclassified, which is what
   an allowlist is for; a denylist would have swallowed it. Added with a test,
   plus a second test proving an unknown code is still refused. Mutation:
   removing 216 turns the first test red.

2. **The quarter after a first-quarter merger cannot be formed from the
   filings.** A quarterly flow is the year's running total less what was
   already reported, and *the first quarter's published figure IS that base* —
   there is no earlier quarter for it to be a difference of. Huntington's first
   quarter of 2026 was the filed year-to-date less 88, and their second was the
   year-to-date less THAT. Five values reported as differences were arithmetic
   that could not be done.

   The first version of that check asked whether the FDIC's quarters still
   summed to the year-to-date, and took twenty-one rows that tie perfectly and
   called them uncomparable. **Suppressing a row that ties is the same error as
   plugging one that does not, pointed the other way.**

3. **`write_config` rebuilt the rows the gates had already checked.** `build`
   computed the config, validated it, and then `write_config` called
   `config_rows` again from the seed — so a roster handed to `build` was
   honoured by every gate and by nothing that reached the workbook.

4. **Nineteen fields shipped with an empty units column.** `FIELD_UNITS` is
   built from `RAW_FIELDS` and knows nothing about the nineteen fields added on
   6 September; `.get(field, "")` answered `""` rather than refusing, so 14,440
   numbers in the delivered CSV had no unit beside them. One helper serves both
   sites now, and it refuses.

5. **The exhibits for all seven had no pictures in them.** Every one reported
   *0 images* and rendered perfectly. The builder reads the shrunk strips,
   `deepstrips-grey`; the seven had only been photographed into `deepstrips`.
   Seventy-seven documents would have shipped as prose about numbers the reader
   cannot see. **That is tenet one, in the project the tenet is written into.**
   The builder now refuses, loads every strip shard, and asserts no bank in the
   set is unphotographed.

6. **A four-digit certificate was read as a year.** `2270 2026` filtered for
   the year 2270, built nothing, and reported *0 of 0* as though there were
   nothing to do. Five of the nineteen banks have four-digit certs and none of
   them could be selected.

### The claim that was false

The record said **swapping the peer group is a one-step change, no script
edited**. Adding seven banks turned eleven tests red. What had been proved was
that the tie-out chain runs on a new bank — not that the product's own tests
survive a roster change, which is what the sentence says.

Fixed rather than reworded. Counts come from the seed, the free slot is
wherever the seed stops, and the parity golden builds on the roster it was
captured with (`tests/goldens/fdic-demo-peers.json`) so it goes on pinning the ENGINE rather than the firm's
peer list.

### The one difference, and it stays one

Huntington's total risk-based capital at 31 March 2026:

    the filing        29,148,027   (printed page and machine-readable copy agree)
    the FDIC          29,147,082
    difference              -945

The filing's own total capital ratio times its risk-weighted assets reproduces
29,148,047, so the filing is internally consistent. The second column on that
line, `RCFW3792`, reads `NR` — there is no other column it could have come
from. **No explanation found.** It is not adjusted, rounded away or hidden: the
row carries both figures, the gap, and the link to the filing.

### Provenance review and the standing tie-out — 7 September 2026

The firm asked Bassy to go through the provenance and name the real issues.
Five were found; four were claims the data contradicted, and the data itself
held up.

| | Finding | Where it stands |
|---|---|---|
| 1 | Every merger row said *"Balances are point-in-time and are unaffected."* True of each measurement, false of the series. **15 of the 31 measurable merger quarters move total assets by 10% or more**; Truist doubles. | Rows now carry the assets either side and the size of the step. Test locks it; putting the old sentence back turns it red. |
| 2 | Twenty-two Case-Shiller series reported as unverified **had been verified** — `fred_caseshiller.py` tied 22 of 22 against S&P's own release and its verdict never reached the file. | Carried through. The national index ties to a published LEVEL and is marked verified; the other 21 tie to a published CHANGE, which pins the move and not the level, so they stay unverified with a note saying exactly that. |
| 3 | The last hop had never been executed. Every verifier reads what the delivered file was built FROM; two of the four read the raw API response. | Written and run: **143,201 of 143,201 identical, 0 moved.** |
| 4 | Identity was checked at one end of the window, and the wrong end — `filing-<cert>-MMDDYYYY.pdf` sorted as a string, so "the latest filing" was whichever December sorted last. | Sorted by date, and read at both ends. **17 of 19 carry the same legal name in 2016 as today.** The two: ZB NA became Zions Bancorporation NA (a rename); everything before December 2019 labelled "Truist Bank" is Branch Banking and Trust. |
| 5 | Every derived citation's evidence read "480 of 480" — the twelve-bank panel. | Restated at 760 from the verifier's own output. |

### The three "not checked" items, measured rather than explained

- **"There is no vintage" was wrong.** Every one of the 760 filings prints
  `Last Updated on <date>` on its schedule pages — it is in the header of
  every photograph in every exhibit — and nothing captured it. **442 of 760
  filings were amended more than 90 days after the quarter they report, and
  289 more than a year after it.** Bank of America amended its third
  quarter of 2016 in December 2021. Every bank row now carries
  `filing_last_updated` and `days_after_quarter_end`.

  It also very likely explains the one difference in the feed. Huntington
  amended its first quarter of 2026 on 21 August, 143 days after the quarter;
  the FFIEC serves the amended filing at 29,148,027 and the FDIC's published
  figure was 29,147,082 when pulled and still is, re-fetched. A lag, not a
  disagreement — and not proven, because the pre-amendment filing is not
  obtainable.

- **The FDIC-computed ratios are half checked.** Four of the eight are plain
  ratios of two figures already tied to the filings. Recomputed from their own
  verified components: **2,964 of 2,964 agree, none differ.** The other four
  need average balances or income-statement items this feed does not hold.

- **The macro links were worse than the line suggested.** **53,415 of 77,081
  rows shipped with no link at all** and the FHFA link 404'd on 13,734 more.
  Fixed, every URL fetched; three refuse scripted requests and were opened in a
  browser instead. All verified rows now carry a link and the build refuses to
  write one without.

### A tie-out that runs with the build — 7 September 2026

The firm: *"when it's ran, it should be tied out."* `run_and_tie_out.py` builds,
checks, and only then writes the workbook. A failed stage stops the run, so
there is never a workbook standing on a feed that failed. Five stages, about a
minute.

**Sized by coverage, not by a count of observations.** What breaks is a
citation, a form version or a source, so the sample touches each: every bank x
every field on the newest quarter, plus two random older quarters per bank,
plus every macro series. About 4,500 comparisons — 3% of the feed, and 100% of
the banks, 100% of the series, and **69 of 87 fields**; the rest
are quarterly flows, which need two filings, and ratios the FDIC computes,
which have no filed line. A planted control fails the run if the checker
shrugs: **16 of 16 caught**.

**It was wrong first, and that is the useful half.** Written with its own copy
of the comparison, it reported 157 differences against a feed the full run
calls clean — every one the copy. It stripped the parenthetical off
`RCON2200 (+RCFN2200 031)`, which is not a note but the citation. Tenet S3.
There is now one comparison, `sources/fdic/tieout.py`, validated by running it
over the whole panel: it reproduces the full run's verdict on **143,201 of
143,201 values**, including the single difference.

### Descriptions — 87 of 87

Nineteen fields shipped as bare codes because `plain.FIELD` knew the
sixty-eight the monitor was built for and nothing about the ones added later.
Written from the caption on the filed page, read off the photographed row.
LNRELOC, an original field, was blank too. The build refuses to write a field
with no description.

### Docket `0b2cae0b` — answered 7 September 2026

| | Question | Answer | Their words |
|---|---|---|---|
| 1 | The 5.4 GB the tie-out stands on lives in a Windows temp folder | **Move it to the Forge** | *"move to the forge - we will purge at some point"* |
| 2 | PR #257 has been a draft since 4 September | **Retitle and merge** | |
| 3 | What the fresh session gets before it ties this out | **Form its own view first** | |

All three matched the recommendation.

### What they caused

**1 — the working folder is a setting now, and the data is on the Forge.**
`src/credit_suite/workdir.py` resolves it: `$CREDIT_SUITE_WORKDIR` first, then
the Forge, then the old temp folder so a checkout mid-move still runs, then a
refusal that names all three. Fifty-two tools had the path typed into them,
session id and all; none does now, and a test asserts it.

Copied what the tools actually REFERENCE — 2.7 GB, found by reading the
tools — rather than the 5.4 GB the scratch folder happens to hold, most of
which is unrelated test runs from other sessions. The old location is
untouched: `workdir()` prefers the Forge the moment it exists, so the switch
happened when the copy finished rather than when anything was deleted.

Because they said they will purge, the Forge folder carries a README saying
**which half cannot be rebuilt**: `banks/` and `filings/`, the 760 filed Call
Reports as the regulator served them. 442 of the 760 have been amended since
the quarter they report, so fetching them again returns a different document —
delete those and a tie-out already done cannot be reproduced, only replaced.
Everything else regenerates in under half an hour.

Proven rather than assumed: the whole chain re-run from the new location,
**5 of 5 stages, 0 differences**.

**2 — PR #257.** Checked before merging rather than assumed: credit-suite's
`main` publishes nothing. The only publishing workflow is `pages.yml` and that
is the website, so under C5 this is ordinary work rather than a publication.

**3 — the fresh session.** It gets the repository and the two delivered files,
picks its own targets and writes them down, and only then reads the provenance
section above. Re-finding something is cheap; missing what this session missed
is what the second pass is for. Of the five faults found on 7 September, three
were claims this session had written itself.

### The second pass — 8 September 2026

A fresh session read the delivered files cold, wrote down its targets before
opening this file, and then went at them. Full write-up:
`credit-suite/docs/tie-out/SECOND-PASS-2026-09-08.md`.

**Nine findings. Eight are sentences; one is 63 numbers.**

| | Finding | Where it stands |
|---|---|---|
| 1 | **63 values published as impossible to check are on the filing, and all 63 tie.** `NTCIQ` is cited with the FFIEC **031** split codes only; an **041** filer reports C&I charge-offs as one line (`RIAD4638`/`RIAD4608`). The check finds nothing and the row says *the bank did not report this line* — Zions in **38 of its 40 quarters**. The correct dual citation is already in `provenance_seed.py:232` and `filing.py` resolves it; the delivered file does not go through that resolver. `verify_bank_history.py:66` holds a **second citation table** (`FLOW_EXPR`) and a **second evaluator**, covering ten flow fields. *"There is now one comparison"* is true of balances, not of flows. | Open. The other nine flow fields have not been read. The standing tie-out cannot catch this: the rows sit in *not claimed as verified*. |
| 2 | **A second disagreement with a filing, published as verified.** Huntington 2026-03-31 `RBCRWAJ` ties only through the 0.005 tolerance, at 0.00475 — 95x the next largest gap in 1,520 rows, same bank-quarter as the one admitted DIFFERS. Backing out RWA: the FDIC implies **206,827,694** against a filed **206,904,227**, a **−76,533** move alongside the known −945, while the leverage ratio is unmoved. Total capital and risk-weighted assets moved; Tier 1 and average assets did not. | Open, and it **narrows** the amendment hypothesis rather than contradicting it. The feed carries no RWA field, so a reader cannot see any of it. |
| 3 | **0 of 1,520 capital-ratio rows are exactly equal to the filing.** All tie inside a half-basis-point tolerance no delivered page mentions; 1,519 are display rounding and one is finding 2. 3,080 macro rows are TIED with a non-zero difference (worst 0.087%, all publisher rounding). Balance checks are genuinely exact. | Open — the document says *"agree to the dollar"* and *"difference 0"*. |
| 4 | **Fault 4's own fix is one bank short.** `same_name_throughout` is `True` for Fifth Third (cert 6672) whose filed name changes at 2019-12-31 from `FIFTH THIRD BANK` to `FIFTH THIRD BANK, NATIONAL ASSOCIATION`. It is **16 of 19**, with three exceptions — two renames and one Truist. A comparison that normalises is not the check that was described. | Open. Nothing downstream is wrong; the published count is. |
| 5 | **"15 of the 33 merger quarters"** in the covering PDF. This file says 15 of the **31 measurable**, which is right — 2 of the 33 have no prior quarter in the window. The qualifier died on the way into the deliverable. | Open. |
| 6 | **All 177 "not on that filing" rows carry a `note` that contradicts their own verdict** — *"nothing on the filing to check it against"* beside *"read straight off the filing"*. 114 of them are `NCLNLS`/`P3LNLS`/`RSLNLTOT` for **all 19 banks in exactly 2016Q3–Q4**: RC-N had no total line before 2017Q1. A form change, not a bank omission. | Open. Whether those 114 could be tied from the components (which ARE on the 2016 filing, and which this feed already sums for 3,933 other rows) was attacked from the facsimile and **did not close** — reported as COULD NOT. |
| 7 | **The published "check any number yourself" recipe works as written on 24,568 of 66,120 rows (37%).** 26% are sums the page never tells you to add, 10% are subtractions, 9% are ratios with no filed line, and **5,679 need the previous quarter's filing — a different URL from the one in the row**. | Open. |
| 8 | **The schedule label points at the wrong item on 532 filings.** RC-R Part I was renumbered at 2020Q1: `7204` was item 44 and `7205` item 43 before it; both are labelled 31 and 51 for all forty quarters. Item 31 on a 2016 filing is *"Unrealized gains on available-for-sale preferred stock"*. Of 32 single-code fields checked across 2016 and 2026, none other moved. Also undisclosed: the capital check takes `min()` across framework columns, and 293 rows had more than one. | Open. The MDRM code is right in every case. |
| 9 | **"Nothing in this feed is calculated by our software"** — `not-comparable-periods.csv` ships `change_in_total_assets_pct`, and page 7 quotes a statistic from it. True of the 143,201 values, false as written. | Open. |

### What it checked and could not break

Reported because a check nobody ran is not a check that passed.

- **No missing merger.** Ran the converse of finding 1 from 7 September: every
  quarter-on-quarter step of 10% or more in `ASSET`, `DEP` and `LNLSGR` that is
  NOT a flagged merger quarter — 18, 26 and 18 of them, every one explicable
  (the 2020 deposit surge; the custody and dealer banks). The 33 are complete as
  far as an outside scan can show. **But** the largest unflagged step in the feed
  is Morgan Stanley Bank NA at **+54.5% total assets, 2026-03-31**, bigger than
  18 of the 33 flagged ones — and LIMITS frames discontinuity as a merger
  property.
- **Seven cross-field identities, 760 of 760 each, no breaks.** `LNLSNET`,
  `EQV`, `LNATRESR`, `NCLNLSR`, `LNRESNCR`, `NARERES ≥ NARELOC`,
  `ASSET ≥ LNLSGR`. The 87 fields are mutually consistent, not merely
  individually matched — the first horizontal check anyone has run here.
- **The macro half is deeper than it looks, and the reviewer's main suspicion
  was wrong.** The result files hold one comparison per series, which reads like
  a series-level verdict stamped onto 65,844 rows. It is not: 90,922
  per-observation records sit behind them, and **all 65,844 verified rows have
  their own**. Page 1's 125,388 is honest.
- **Delivered = checked, macro side, re-executed independently** of
  `prove_delivered_is_what_was_checked.py`: 77,184 records, 0 differences.
- **The build reproduces the delivery byte-for-byte** — all five CSVs and
  `verification-summary.json` unchanged after a full `run_and_tie_out.py`.
- **629 tests pass; 16 of 16 planted controls caught; the Huntington −945
  reproduced from the filing store.**

### What it did not do

The macro source selection (still one session's judgement, unreviewed); the four
unchecked ratios; the nine other fields in `FLOW_EXPR`; whether the 209 exhibits
photograph the row their manifest names. And **nothing here has been checked by a
second person** — a second model is not that.

### Docket `51f34a75` — answered 8 September 2026

| | Question | Answer |
|---|---|---|
| D1 | Huntington's capital ratio disagrees with its filing by 0.00475 and a 0.005 tolerance is hiding it | **Publish it as a second disagreement** |
| D2 | Has the workbook gone anywhere beyond the firm? | **Only me — nobody else has it** |
| D3 | `desk` is red on Windows and another session owns it | **File an issue and leave it** |
| D4 | How far does the second pass go? | **Read the other nine flow fields** |

All four matched the recommendation. No note was added to any of them, so the
recommendation's own reasoning is the whole of the answer and is recorded above
rather than restated.

**Goal named, and what silence approved:** close the nine findings of the second
pass and reissue the covering document so the workbook the firm holds matches
what the code does. Distance at the time of the docket: **0 of 9**.

### What the answers caused — 8 September 2026

Distance ran **0 of 9 → 9 of 9**, and the work turned up a tenth thing nobody
had asked about.

| | Finding | What was done |
|---|---|---|
| 1 | 63 values published as impossible to check | `verify_bank_history.py` carried its own citation table (`FLOW_EXPR`) and its own evaluator. Both deleted. The flow path now reads the expression from `provenance_seed` — the file's own comment already said the seed is the source of truth — and resolves it through `filing.filed_dollars`, which is now **the one resolver**. `filed_value` is a wrapper over it. **`bank_verified` 59,544 → 59,606**; every one of the 63 ties, and each row now cites the line actually read on that filing (`RIAD4638-RIAD4608` for a 041 filer, the split for an 031). |
| 2 | A second disagreement hidden by a tolerance | `CAPITAL_TOL` 0.005 → **0.0001**, named as a constant with the measurement behind it. Huntington 2026-03-31 `RBCRWAJ` is published as **DIFFERS**. The covering document gains the decomposition: FDIC implies RWA **206,827,694** against a filed **206,904,227**, −76,533 beside the known −945, with the leverage ratio unmoved — two capital figures moved and two did not, which is the shape of an amendment to the risk-weighting pages and the best evidence yet for an explanation still not proven. **DIFFERS 1 → 2.** |
| 3 | Every capital ratio tied on an undisclosed tolerance | Disclosed in the document, with the measurement: the filing prints six decimals and the FDIC four, so rounding never exceeds 0.00005; the room was a hundred times that and exactly one value used it. |
| 4 | `same_name_throughout` reported 17 of 19 | `matches()` — a nine-character prefix test, right for *is this our bank* — was being reused for *did the name change*. New `same_name()` compares the two printed strings. **16 of 19**, three exceptions: Zions and Fifth Third are renames (the latter a charter conversion at 2019-12-31), Truist is not. |
| 5 | "15 of the 33 merger quarters" | Now 15 of the **31 measurable**, with the denominator computed rather than typed. Two merger quarters sit at the window's edge with no prior quarter to measure from. |
| 6 | 177 rows whose note contradicted their verdict | Both verifiers now write a note that agrees with the verdict. The count is **114**, and the roster says what they are: the form did not carry the line, in the second half of 2016, across all nineteen banks — not one bank leaving something out. |
| 7 | The self-check recipe works on 37% of rows | The document now counts the four shapes off the delivered rows and says what each needs: 24,568 single-line, 17,227 arithmetic, 5,679 needing the **previous quarter's filing at a different address**, 6,080 with no filed line at all. |
| 8 | Schedule labels wrong on 532 rows | RC-R Part I was renumbered at 2020Q1. The labels now carry both: *"RC-R Part I 51 from 2020Q1, 43 before it"*. The capital check also records that it took the **lower** of the frameworks filed, which 293 rows needed and none said. |
| 9 | "Nothing in this feed is calculated by our software" | *"No value in this feed is calculated by our software"*, and the one figure we do work out — the size of each merger step — is named as a warning about the data rather than part of it. |

### The tenth, which nobody was looking for

**Nine tools could not be imported.** The move to the Forge on 7 September left
`NAME = SB / "..."` above `SB = workdir()` in nine of them, so each raised
`NameError` before running a line — including `verify_bank_history.py`, the tool
that decides every bank verdict in the delivered file. Found by trying to run
it. Nothing caught it because the standing run starts *downstream* of all nine,
on the rows they had written before the move: a green chain standing on output
from tools that could no longer produce it.

It had a second consequence. `deep_strips.json` was copied to the Forge but the
shard holding the seven banks added on 7 September was not, so
`build_covering_document.py` **refused to write a document with no photographs
in it** — the guard added on 5 September, doing exactly its job. The index was
rebuilt for those seven certs and the document carries its pictures again.

### Proof

- **695 tests pass**, up from 629. `tests/test_one_resolver_and_runnable_tools.py`
  is new: 66 cases covering the dual-form citation, the refusal to sum a partial
  expression, leniency staying on the form the bank filed, the absence of a
  second citation table, the tolerance, and every tool in `tools/tieout`
  parsing with nothing reading the working folder before it is resolved.
- **The checker was checked.** Restoring the two pre-fix tools turns four of
  those tests red and leaves 62 green; restoring the fix turns them back.
- **`run_and_tie_out.py`: 5 of 5 stages.** Controls 16 of 16 caught.
- **The covering document was opened, not assumed** — 8 pages, 4 images, and
  every one of the ten claims above read back out of the rendered PDF.
- `SATC-VERIFIED-CREDIT-DATA-how-it-was-proved-2026-09-07.pdf` is superseded by
  the 8 September build and removed; the firm confirmed nobody outside holds a
  copy, so this is a replacement rather than a recall.

### Still open, deliberately

The macro source selection, unreviewed by anybody. The four FDIC ratios checked
against nothing. Whether the 209 exhibits photograph the row their manifest
names. Whether the 114 could be tied from the components that ARE on the 2016
filing — attacked from the facsimile and not closed. And
`verify_new_bank_fields.py` still carries a third resolver of its own; its ten
flow fields were proven on both versions of the form, so it is a duplicate
rather than a defect, and it was left alone rather than refactored under a
mandate that did not cover it.

## 7 · Standing rules for new items

New idea -> add a line here (one sentence, why it matters). New lesson
found in any build -> `TEMPLATE_CONTRACT.md` carried lessons (L-series),
not here. Anything touching the watchlist boundary or licensing -> gets a
research pass before a spec, no exceptions.

---

## Done log

- 2026-09-05 -- **Tie-out of every data point in both credit monitors:
  862 of 862 tie.** Each figure on the ours side read out of the shipped
  workbook -- the cell a person opens, never re-fetched -- and each on the
  other side taken off a document published by somebody else: a bank's own
  filed Call Report, or the agency that computes a macro series (FHFA, the
  Federal Reserve Board, S&P Dow Jones Indices), never FRED, which only
  redistributes. Twelve bank exhibits (53 lines each, 685 pages, 1,116 strips
  cut from the filings), one macro exhibit (142 series, six publishers), and a
  master roster: `credit-suite/docs/tie-out/`. Scripts in
  `credit-suite/tools/tieout/`.
  **Found six defects, every one of which left the numbers correct** and so was
  invisible to 414 passing tests: a shipped workbook with Nebraska blank after
  one unretried 5xx (fixed, `1b03896`); two series wearing each other's
  description; a mortgage-tightening indicator filed as a demand series and so
  wired to never alert; two more labels naming a different series (fixed,
  `a9411a1`); four series declaring "billions" beside a figure in millions
  (fixed, `94d431f`); and the FDIC's own quarterly and annual charge-off
  figures for PNC failing to reconcile by 515 and 652 thousand dollars -- our
  side is faithful to what the FDIC published, so nothing was adjusted.
  **Three more defects were in the checking, not the data**, each announcing
  itself as an implausibly uniform failure across every entity: C&I charge-offs
  cited to U.S. addressees only; the wrong column of the total capital ratio
  for the one bank filing two; and six blank source photographs that reported
  "ok". New guard `tests/test_fred_labels.py` checks a label against its
  publisher's own definition -- 414 tests, 4 mutations killed. PR #257.
  **Second edition, same day.** The first said 776 of 778 and did not say
  what 778 was: only 53 of each bank's 69 raw fields were being compared.
  Seven fields carried the literal text "(not in tie-out map)" where their
  MDRM code belongs, and the tie-out only checks fields the map cites -- a
  check that examines what the map documents cannot discover what the map
  omits. Behind that: bracketed expressions parse as nothing, bare
  income-statement codes resolve against the balance-sheet prefixes and find
  nothing, the capital ratios cited the form-041 prefix on twelve 031
  filers, and `parse_facts` discarded every ratio in every filing by keeping
  whole numbers only. All fixed; new guard `test_provenance_citations.py`
  requires every citation to parse AND to find its line on a real filed Call
  Report. Suite 414 -> 541. PNC's disagreement grew from two lines to five
  once the unchecked fields were checked.
  Still owed: the eight FDIC-computed ratios per bank (now named, not
  omitted), the alert logic built on these figures, and every period except
  the latest.
  **Third edition: the PNC finding was withdrawn.** Two editions reported
  five PNC lines as differences and said the FDIC disagreed with itself.
  PNC absorbed FirstBank of Lakewood CO (cert 18714) on 18 June 2026, and a
  quarterly flow across a merger must also subtract the acquired bank's
  prior year-to-date. Every gap equalled FirstBank's figure to the dollar,
  and the two fields that tied are the two where it was zero. The
  workbook's own `_mergers` tab recorded the merger and explained the
  arithmetic; the tie-out queried an API, filtered on the wrong date field,
  and believed the empty answer. All 862 data points tie. The flow
  derivation now consults the merger record.

- 2026-09-03 -- FRED template (#1) hardening + contract-alignment pass (part of
  the §2 debt): adversarial re-verification (4 agents: test+mutation, hazard
  hunt, adversarial compute, cell-level workbook open) + fixes — engine-level
  `validate_thresholds` (L8: refuse blank/non-numeric/non-positive band an
  alert_rule reads, not silent 0.0), exit-nonzero on zero-pull, DemoProvider
  cadence-by-declared-frequency (fixed a mislabeled watchlist YoY), 3 decoration
  tests made load-bearing + `sloos_level` coverage, self-citation provenance
  (per-block vintage stamp + units + FRED HYPERLINK) + optional `fred_vintage`
  realtime pin, `VERIFICATION_REPORT.md`, and CI coverage (pytest-fred-dashboard
  job). 44→57 tests, all mutation-proven; live FRED + real-Excel still owed
  (needs the desk). These fold into the credit-suite M1 spine (§6).
- 2026-07-05 -- Credit Review OS v1 shipped (credit-review-os/, issues
  #60-#68 on PR #71): config-driven C&I loan-review engine — two-layer
  config (portable program + engagement overlay), per-loan linesheets with
  live-formula exceptions (doc/policy/compliance + rating disagreement),
  evidence staleness vs [ASOF], Master roll-up + criticized/classified
  totals, de-identified Data Mart + formulas-engine re-ingest,
  _methodology regulatory crosswalk (every element cited), Seam-3
  no-PII-leak guard (TIN last-4 everywhere), AES-256-GCM encryption-at-
  rest + credit-review CLI; 64 tests across the PRD's three seams,
  byte-identical deterministic builds. Roadmap lives in §5 above.
- 2026-07-03 -- Template #6 EDGAR Crit/Class Tracker shipped: commercial
  criticized/classified per competitor HC (extracted-XBRL-instance path,
  family-honest N/A gating, member-map bootstrap), 8-K credit-event lane
  with 2.04 auto-WATCH, accession provenance + --tieout/--selftest;
  16 tests, email-sim PASS, recalc parity, 94.6KB ASCII bundle verified.
  SUITE COMPLETE AT SIX -- new-build freeze; next step is the user's
  desk validation sprint (build_suite.py + --doctor + one tie-out).
- 2026-07-03 -- Template #4 v1.1 competitor pack shipped: Dashboard_LoanBook
  two-track (consumer DQ surveillance + commercial Call-Report floor),
  SVB metrics (uninsured share, unrealized/capital, FHLB), _provenance
  tab (69 field + 28 derived rows, honesty-flagged) + --tieout mode;
  20 tests, email-sim PASS, recalc parity 455 values/636 statuses,
  105KB ASCII bundle verified in empty folder.
- 2026-07-03 — Template #5 CFPB Mortgage Delinquency Monitor shipped:
  county-FIPS watchlist (the suite's finest key), [FOOTPRINT] slots,
  dev-12m + rise-streak transforms, SUPPRESSED/vintage/continuity
  handling; 16 tests, email-sim PASS, recalc parity, bundle verified.
- 2026-07-03 — Template #4 FDIC Bank Peer Monitor shipped (flexible
  [PEERS], authority-labeled thresholds, entity watchlist); L7 openpyxl
  None-write bug found + carried back to bureau/macro.
- 2026-07-02/03 — Template #3 Macro Early-Warning Monitor shipped (open
  state watchlist, staleness first-class); TEMPLATE_CONTRACT.md +
  control_center.py + ASCII-bundle standard (§11) landed.
- 2026-07-02 — Bureau review pass: 16 findings fixed (heat inversion,
  IFERROR empty-cell coercion, raw_slots guard, MS-OVBA protection keys).
- 2026-06-30..07-01 — Templates #1 (FRED) and #2 (bureau) shipped; PR #53.

## 6 - Hosted practice app (satc_system) - the "hodgepodge" build-out (AJ, 2026-07-30)

The hosted app (port 5050 on the Forge) should be the practice front door:
client adder + interviewer (SHIPPED), plus:

- [x] **Email template library** SHIPPED 2026-07-31 (feat/comms-templates):
      configs/comms/ grew from two seed files to a seven-template registry
      (templates.yaml + one .txt body each) - interview invite, engagement
      letter, document request, missing items, return delivery, cover letter,
      invoice cover. Pure logic in src/satc/comms/ (library / context /
      render), thin blueprint at /comms + nav entry, 43 tests across
      tests/test_comms.py + tests/test_comms_app.py. Prefills from real state
      (document register, return refund/balance, engagement fee, vault name);
      a merge field with no fact behind it renders as a visible
      "[[ Fee: fill in ]]" marker and is listed on the screen - never guessed.
      Slots only a human can answer (meeting times, scope, fee terms, invoice
      number) get a text box. No SMTP anywhere: an ast-parsing test asserts the
      area never imports smtplib or calls sendmail. The two seed files stay
      byte-identical, so satc.drake.comms still renders them.
- [ ] **Invoice generation folded in**: port the standalone invoice-generator
      Flask app in as a satc_system piece (drop Stripe for local-first v1;
      invoice numbering, line items, PDF/HTML render, per-client history).
      Bigger job - own session.
