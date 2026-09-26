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

### The four ratios that were checked against nothing — 8 September 2026

The firm: *"Their ratios are fine. I mean we are not shipping calculations we
derive. Them deriving is basically source data and you would expect it to be
right."* Then, on whether to carry the figures behind the four unchecked ones:
**"Just add them then."**

That settled a confusion worth writing down. **Who derived a number and whether
we can show it are separate axes**, and the second pass had run them together.
The FDIC publishing `ROAQ` is no different in kind from Huntington publishing
`RCFD2170`: somebody else's number, copied without touching. All 6,080 satisfy
the no-derived-calculations rule. What did not hold was a *sentence*.

### The sentence

Every one of the 6,080 rows said:

> not a filed line — the FDIC calculates this from filed lines **that are
> verified here**

True for 2,964. False for 3,040. `ROAQ` is net income over *average* assets;
neither was among the 87 fields, so there were no verified lines behind it. The
clause was written about the four ratios where it holds and then applied to all
eight — the same failure as every other finding in this pass.

### Eighteen fields, and how each citation was established

The method this module already requires: take the FDIC's published number, look
for it in the bank's own XBRL as a single line or as a sum, and keep the
candidate only if it holds in **every** bank-quarter. Not a plausible-looking
code, and not a crosswalk.

| field | what it is | citation | held in |
|---|---|---|---|
| `NETINC` / `NETINCQ` | net income, year to date / this quarter | `4340` | 760 of 760 / 752 of 752 comparable |
| `NIM` / `NIMQ` | net interest income | `4074` | 760 / 752 |
| `NONII` / `NONIIQ` | noninterest income | `4079` | 760 / 752 |
| `NONIX` / `NONIXQ` | noninterest expense | `4093` | 760 / 752 |
| `NTLNLS` / `NTLNLSQ` | net charge-offs | `4635-4605` | 760 / 753 |
| `INTINC` | total interest income | `4107` | 760 of 760 |
| `EINTEXP` | total interest expense | `4073` | 760 of 760 |
| `ITAX` | income taxes | `4302` | 760 of 760 |
| `ELNATR` / `ELNATQ` | provision for credit losses | `JJ33`, and `4230` before 2019Q1 | 570 / 563 comparable |
| `AVASSET` | average total assets | `3368` (RC-K 9) | 760 of 760 |
| `ERNAST` | average earning assets | **no filed line** | — |
| `LNLSGR5` | average loans and leases | **no filed line** | — |

`ELNATR` is a **dated recoding**, found rather than assumed: `RIAD4230`
"provision for loan and lease losses" became `RIADJJ33` "provisions for credit
losses" under CECL. Both codes sit on the form from 2019Q1 and the FDIC's figure
follows `JJ33` from that quarter — 570 of 570 — while `4230` is what it matches
before. A row naming only `JJ33` would be right about today and wrong about the
first ten quarters in the window. Checked across all nineteen banks: the
boundary is a date, not a per-bank adoption.

`ERNAST` and `LNLSGR5` are the FDIC's own averages. **Every subset of Schedule
RC-K was tested against both across the panel and none reproduces either** —
including RC-K 3360, the filed average-loans line, which misses `LNLSGR5` in all
760. They are carried because without them two of the four ratios cannot be
reconstructed at all, and they carry a verdict that says what they are.

### What it moved

| | before | after |
|---|---|---|
| bank fields | 87 | **105** |
| bank values | 66,120 | **79,800** |
| verified against a filing | 59,606 | **71,580** |
| values delivered | 143,201 | **156,881** |
| checked against an outside document | 125,450 | **137,424** |
| FDIC-computed with no filed components | (unlabelled) | **1,520, and now labelled** |

26,279 of the 28,120 new values tie. The rest are the merger quarters every
`*Q` field has, the 2016 form-change rows, and the 1,520 FDIC averages. **No new
disagreement.** The two verdicts are now split, so half of the FDIC-computed
rows no longer promise a verification the feed cannot perform.

### What is still not proved, said plainly

The four ratios still do not reproduce. Tried on all 760: net income annualised
over average assets; net interest income annualised over average earning assets;
noninterest expense over net interest income plus noninterest income; quarterly
net charge-offs annualised over average loans — under both annualisation
conventions, four quarters and 365-over-days. **None holds across the panel.**
The FDIC's definitions carry adjustments that are not in what it publishes, and
fitting a formula until it matches is how a wrong citation gets written.

So the obstacle moved rather than vanished, which is the honest outcome:

- **`ROAQ` and `EEFFR`** — every figure they are built from is now in the feed
  and ties to a filing. Only the FDIC's exact arithmetic is unresolved.
- **`NIMY` and `NTLNLSQR`** — the numerator ties in all 760; the denominator is
  an average no bank files.

The practical effect is the one that matters for the workbook: a return on
assets, a net interest margin or an efficiency ratio can now be built downstream
from numbers that were each checked against a filed page, instead of taken from
a ratio nobody could check.

### Proof

- `run_and_tie_out.py` — **5 of 5 stages**, controls 16 of 16 caught.
- **695 tests pass.** Two failed first and were right to: both pin a count that
  moves when the field list does. The zero count went 8,621 → 8,655, and the 34
  new zeros were checked one at a time rather than waved through — every one is
  a filed nil with a TIES verdict.
- The covering document was rebuilt and **opened**: 105 fields, 156,881 values,
  137,424 checked, 2 disagreements.

### Two independent verifiers — 9 September 2026

The firm: *"go through here to verify what was actually truly tied out so we can
tell the original agent."* Two agents, one per half, each forbidden to import,
call or copy `filing.py`, `tieout.py` or anything in `tools/tieout/`; each wrote
its own citation parser, resolver and evaluator, and the macro one downloaded
every publisher's file and built its own crosswalks. Full report:
`credit-suite/docs/tie-out/WHAT-IS-ACTUALLY-TIED-OUT-2026-09-09.md`.

**The claim holds and nothing is overstated.** Of the 137,424 values claimed as
checked against an outside document: **135,580 exactly equal**, **1,775 agree to
the publisher's own printed precision**, **69 no longer match** (G.19, inside the
Fed's revision window — a vintage effect, and the macro side carries no `as_of`).
Bank 71,580 of 71,580; macro 65,844 of 65,844 located in the publisher's own file
and compared observation by observation, no sampling. Not circular: 400 of 400
delivered values match the live FDIC API, and 1,171 of 1,171 cited codes agree
between the printed facsimile and the machine-readable copy.

**The feed understates itself by 5,028 rows.** Of 8,220 published as
unverifiable: the 114 form-change rows all check out (composition derived from
2017 where the total IS printed, control-tested 2,644 of 2,644); `EEFFR`
reproduces 760 of 760 — its published citation omits `RIADC216`, goodwill
impairment, which is why 15 quarters failed; `LNLSGR5` is a 2-to-5 point average
of quarter-end balances, not RC-K, and 704 of 760 reproduce; 410 of 496 merger
rows reproduce arithmetically.

**Both DIFFERS confirmed, and they are one event.** The FDIC also publishes
`RWAJ` 206,827,694 against the filing's 206,904,227, and 29,147,082 / 206,827,694
= 14.092446439982066 exactly. One coherent restatement of three figures, which
strengthens the amendment hypothesis. `RWAJ` is not among the 105 fields.

**Seven defects were introduced or left open by the 8 September pass** — the pass
whose whole subject was this failure mode. The worst is on `main`: the covering
document's roster prints **0** where **114** belongs and sums to 156,767 against
its own headline of 156,881, because the delivered wording changed and
`build_covering_document.py:76` still counts the old string. Also: "eight of the
87 fields" where the denominator is 105; a verdict split that made 1,520 rows
claim their denominators are verified while the same file says they are not; a
page-6 classifier that describes 1,520 citation-less rows as arithmetic; a note
recording a search of the wrong space; `EEFFR` reported as not reproducing when
it does; and the 114 reported as COULD NOT when they were closeable.

**Inherited:** 56 first-quarter rows whose note prescribes a subtraction in a
quarter where the year-to-date IS the quarter — 46 reproduce with no subtraction,
and following the note gives negative nonsense.

**The macro half's own:** the workbook's THE SOURCES tab ships an unfilled
template for FHFA (*"0 observations here were checked against those files, back
to -"* — 14,160 were); BLS, the largest publisher at 31,244 rows, is never
mentioned there at all; a macro tolerance of 0.005 exists and no delivered
document discloses it, while the production diagram says "difference 0"; 2,825
rows carry TIED with a non-zero difference and one sits at 99.2% of the
tolerance; the H.8 crosswalk picks the series that agrees most and then reports
the agreement, so it cannot fail by construction; Case-Shiller's national index
IS obtainable free one release at a time, so "S&P sells the history" and "behind
a paywall" are overstated; and the single S&P row has no retained copy of its
source document, the one link in the chain that cannot be reopened.

**Not fixed.** The firm has the report; nothing was changed on the strength of
it. The roster defect is live on `main`.

## 6c · Portfolio Analysis Pack (`portfolio-analysis-pack/` — grilled + PRD'd 2026-09-18, v1 built 2026-09-19)

A loan extract plus a YAML question file → one workbook: the fixed six-step
ladder (capture, prevalence, gradient, stratified, decomposition, model) and
a closing control observation. Python aggregates; the workbook holds a count
cube and derives every rate, interval and the survives/collapses word by
live formula. First instance: stated obligor income above reported business
sales on the small-business book; built domain-free so a consumer question
(stated vs bureau income, auto) is a config, not code. Spec:
`portfolio-analysis-pack/docs/prd-portfolio-analysis-pack.md`.

- [x] **Build v1 (M1–M4 in the PRD) — built, 18–19 Sep 2026.** Nine
      vertical slices, one PR each, merged by the session as each went green:
      #364 tracer bullet → #365 inspect/hygiene/dates/outcome forms, #366
      steps 1–2, #367 step 4 + suggest, #368 bundle + README → #369 step 5 +
      step 7 + consumer example, #370 step 6 model, #371 charts → #372
      mutation tool + this close-out. **What shipped, in measured facts:**
      - **Tests: 94 pass** (`cd portfolio-analysis-pack && pytest -q`,
        measured 19 Sep 2026: 78 from the build, 16 from the adversarial pass below). The suite builds three 40,000-loan synthetic
        books (a planted effect, a null, and an effect that is size in
        disguise), reads each workbook back through the `formulas` engine,
        and checks: the gradient reads as planted; the step-4 word is
        survives / no crude effect / collapses respectively; both regressions
        recover the plant and lose it under the confounders; every `_check`
        row agrees; two builds are byte-identical; the bundle rebuilds the
        same bytes in an empty directory with only openpyxl and PyYAML.
      - **Mutations: 9 of 9 caught** by their named tests
        (`python tools/mutation_check.py`; CI runs it on every pull request).
        Each breaks one behaviour: the z quantile, the Clopper-Pearson tail,
        the pooled odds ratio's direction, seasoning, the leakage refusal,
        the flag's side of the line, the `_xlfn.` prefix, the check tab's
        tolerance, the decomposition sort.
      - **Build time** (this container, 19 Sep 2026): 40,000 loans in 5.2 s
        (read 0.2 · population 2.0 · models 1.8 · workbook 0.8); 100,000
        loans in 12.7 s (read 0.6 · population 4.8 · models 4.8 · workbook
        2.1). The workbook is 164 KB at both sizes: it holds counts, not
        loans, which is what the firm asked for on 18 Sep ("I don't want a
        situation where excel is the limiting factor").
      - **Render harness** (LibreOffice → PDF → one PNG per page): every tab
        fits one page wide, 58 pages for the confounded book, zero error
        cells, and the gradient and stratified charts carry axis numbers and
        interval bars — looked at, not just scanned. The first two chart
        attempts rendered cleanly and had no axis numbers; a cell scan
        cannot see that, which is why the pages are opened.
      - **Docket answers honoured:** no threshold, list, mapping or transform
        in code; any binary outcome; step 7 asserts nothing of its own;
        refuse on dirt, report blanks, never repair; plain language in the
        README as a standing rule.
      **Not checked, and who checks it:**
      - **Excel itself.** Nothing here has met Excel. The engine and
        LibreOffice both recalculate the pack and agree with Python, and the
        `_xlfn.` prefix is guarded, but the cover's "N of N formula checks
        agree" line is the first thing to read on the first Excel open.
      - **The first real run at the desk.** Key's column names, the date
        format the extract actually carries, and the bundle crossing the
        DLP boundary are all untried. `pack inspect` first, then
        `pack validate`, before a build.
      - **The NAICS list is gone**, so nothing checks it; grouping by
        `prefix` or `map` is proved on synthetic codes only.
      **Adversarial pass, 19 Sep 2026** (canon skill `adversarial`; the firm
      asked for it on the docket: "you also have the adversarial skill").
      A second model, tests only, one file across. **35 hypotheses formed,
      35 tried, 16 went red, 19 clean.** Fifteen were bugs against the PRD or
      README and are fixed; one was arguable and its expectation restated.
      All sixteen now live in `tests/test_adversarial.py`. In plain words,
      the ones that changed a number a reader would act on:
      - An empty bucket in the middle of the gradient broke the chain: rates
        of 5%, 20%, 1%, 2% with a gap between read *monotonic increasing*,
        and the cover said the rate rises at every step. Each bucket is now
        compared with the nearest bucket below it that holds loans.
      - A book with no events at all read *monotonic increasing* too (every
        change was exactly zero). There is now a word for that: *flat*.
      - Loans with a blank grouping value vanished from steps 4 and 5 with no
        row and no count, which also made the "whole population" crude odds
        ratio differ from block to block on the same tab and made the pack
        fail its own formula check. A `(blank)` level, always last, holds
        them now (PRD §6.8 said so; the code did not).
      - A blank measure on a snapshot outcome was a silent non-event; the
        capture tab now counts it by quarter, naming the measure fields.
      - With several outcomes, steps 4 and 5 headed every block with the
        first outcome's event count; each block now states its own.
      - Step 7 printed "In 0.0% of the 0 seasoned loans" when there were
        none; it now says there is no share to read.
      - One bad value in a column used twice was refused twice; once now.
        The hygiene file's row order was set-dependent; sorted now.
      - `pack inspect` called an all-digit `20210315` column an integer and
        said nothing about dates; it now says the column also reads as
        `%Y%m%d`. It crashed on an extract with a header and no rows.
      - `pack list` was in the PRD and did not exist. `pack suggest --field`
        answered a green nothing for the rule's own fields and crashed on a
        text column; it reads any numeric column now and refuses the rest.
      - A confounder with no seasoned levels wrote a cell range backwards
        (`SUM(C106:C105)`), which LibreOffice tolerates and the `formulas`
        engine reads as `#NULL!`. The block now says there is nothing to
        stratify on and writes no formula. `#NULL!` joined the render
        harness's error list.
      - **Restated (finding 15):** moving the live interval-method knob made
        the cover read "529 of 620 formula checks agree". The Python column
        is a snapshot at the built settings and cannot follow a knob; the
        cover now says the knobs have moved and shows no count, and reads N
        of N again when they are set back.
      **Checked and found clean (19):** a value exactly on a bucket edge; a
      rule at exactly its cut; seasoning at exactly the window with the
      month-end clamp; byte-identical builds under a different row order and
      five hash seeds; the confidence knob at 0.5 and 0.999 under both
      methods; both interval methods at zero events and at every loan an
      event; a one-loan book and a book with no seasoned loans; no error
      cell in the degenerate packs under LibreOffice or the engine;
      Mantel-Haenszel and the crude ratio with a zero cell; a CSV with a
      byte-order mark, Windows line endings and a trailing blank line;
      column names with a space and with accents; labels `0012` and `12`
      kept distinct; `N/A` and `-` read as blank; the bundle's contents and
      its `--validate` / `--inspect` argument order.
      **Close-out docket published 19 Sep 2026 (form
      BEtT86sVUTSDJaEGYhrLqL, collection `decisions`).** Two decisions open,
      to be read back from the form and written here when answered: (1) how
      the column names of Key's extract reach a question file — recommended:
      the firm runs the bundle's `--inspect` at the desk and pastes the
      column lines; (2) whether the candidate tenet below enters the record as
      S36 — recommended: yes, via bassy. Next, unless the firm says otherwise:
      merge the adversarial pass (PR #383) when green, then stop; the tool is
      complete as specified and the real run is the firm's.
      **Docket answered 20 Sep 2026.** In the firm's words, and what each
      caused:
      - *Decision 1 (how Key's column names reach a question file):* "The
        column names will never reach you. I am becoming annoyed with this -
        we design a tool that we can put anything into and designate it to
        be something that the tool can work with. The point is it isn't key
        specific but we're designing it to work with key." → The docket had
        asked the wrong question, and the tool had the same fault: the
        bundle carries one fixed question file, so the only place a column
        could be designated was where the bundle was made. Designation now
        happens at the desk, on any extract, with nothing coming back: see
        the entry below this one. The firm's sentence is a candidate
        conviction, to be put to them through bassy on the next docket, not
        recorded by a session.
      - *Decision 2 (candidate tenet S36):* "No" → it stays a project lesson
        here and binds nothing else. Struck from the docket.
      - *Next:* no objection → the last pull request was merged and the
        session stopped, as the docket said it would.
      **Designation at the desk, built 20 Sep 2026** (the change the firm's
      answer caused). `pack init EXTRACT` writes a question-file skeleton from
      the extract's own columns: every column listed with what inspect found
      beside it, and a `[CONFIRM: ...]` marker on each value the person must
      choose (the loan number column, the origination date, the two rule
      columns, the outcome, `known` per column, `existing_control`). The
      loader refuses a file that still carries a marker and names every one;
      the tool fills nothing on anyone's behalf. The bundle gained `--init`
      and `--config`, so any extract is designated and built at the desk with
      nothing coming back. Proved: the skeleton lists every column in the
      extract's order with a marker on every slot; the loader names all of
      them; a skeleton filled in by hand validates and builds with no code
      change; two `init` runs are byte-identical; the bundle writes the
      skeleton, refuses it unfilled, and builds from the filled file beside
      it. The example question file under `configs/examples/` is now only
      an example. Not checked: the flow at a real desk, which is the firm's.
      **The exercise harness, built 20 Sep 2026.** The firm, on seeing the
      designation slice wait on a test suite: "you should be ensuring
      everything works by actually running the script using a good
      synthetically created population. It should be able to show how each
      scenario is covered." → `tools/exercise.py` makes eleven made-up books
      with known answers, drives the bundle script from an empty folder the
      way a desk would, reads every answer back out of the workbook the way
      Excel reads it, renders the pages, and writes `docs/exercise-report.md`
      (pages beside it) putting what was planted beside what the pack said,
      scenario by scenario, with the checks counted. First full run: **48 of
      48 checks agree across 11 scenarios** — a planted effect (every word
      right, the planted odds ratio inside the regression's interval); no
      effect (no block says survives, the interval contains 1); size in
      disguise (size band collapses, M2 loses the effect, the tree splits on
      size); the outcome as a bank-set flag (same counts and words as the
      event-date book); a measure in bands (three blocks, blank measure
      counted); designation of an unseen extract at the desk (skeleton
      written, refused unfilled naming 20 slots, filled file builds
      byte-identical to a build here); four refusals (dirt, two-way dates,
      a missing line, a leaking control); blanks counted with the pack's own
      check still N of N; the live knobs; same inputs same file; 100,000
      loans in 9.5 s to a 165 KB workbook. One harness mistake on the first
      run (a flag outcome's `basis` written as free text) was refused by the
      tool with the exact line to add, which is the behaviour wanted.
      The report, with the pages in it, is published for the firm as
      https://claude.ai/artifact/VDjgSETp3wh6ysXag4rf7e and regenerated whole
      by every run of the harness.
      **The bundle carries the made-up-book generator, 21 Sep 2026.** The
      firm: "you have the script I can email myself to create and test this".
      `build_pack.py --synth demo` now writes a book with a known answer
      beside the script, so a desk can test on it before any extract
      exists; the test helpers, the render harness and any data still stay
      home. The file handed to the firm was run end to end in an empty
      folder first: book made, pack built, question file written and
      refused unfilled.
      **Candidate tenet, declined by the firm 20 Sep 2026 — kept as a
      project lesson only:** *A rule that holds because there was nothing to
      compare must not print the same word as a rule that held. Give "nothing
      to compare" and "nothing moved" their own words.* Cited to findings 1,
      2 and 8 above: `all(d >= 0)` over zero differences read "rises at every
      step"; a skipped pair over an empty bucket read "monotonic"; `share or
      0.0` read "checked, and it never happens".
      **Looked at and not filed:** `_provenance` prints the date pattern as
      "N of N parsed" using the same number on both sides; the capture tab's
      range-check note lives on `_provenance` instead; §5.11's zero and
      out-of-range columns are absent because hygiene refuses those values
      before the tab exists.
- [ ] **Door two — threshold/boundary.** Deferred by ruling (C11 struck for
      this project, 2026-09-18). Reuses the bucket-with-interval block with
      finer edges around the cut, a bunching count, and a boundary-coincidence
      map for the multi-scheme case. Checked 2026-09-18: `credit-review-os`
      Mode B's FRINGE flag + fringe-vs-core rate is a binary compare, not a
      curve with intervals — not a rebuild, not free.
- [ ] **Door three — residual profiling.** Deferred by the same ruling. Fit
      the accepted drivers across all vintages, compare predicted vs actual by
      vintage, profile the worst residuals, feed the split back through the
      ladder across all vintages.
- [ ] **Sweep mode.** Deferred. Leads never findings; log every partition
      attempted; promote only on held-back data.
- [ ] **Vintage curves** as an alternative to the fixed window. Deferred.
- [ ] **Utilization as a second outcome** (line-assignment failure looks
      like drawing to the line). The firm, 18 Sep 2026: outstanding divided
      by commitment, a snapshot at as-of. The PRD's third outcome form
      carries it; what remains is Key's column names and the threshold, then
      it is a second config file.
- **Docket answered 18 Sep 2026 (form 6LgJGrLMitMi6CKe9BMaH6).** In the
      firm's words, and what each caused:
      - *Next:* "Build and keep building until you actually need me." → the
        nine slices run autonomously; a docket only when genuinely blocked.
      - *Who merges:* "You merge them" → each slice's PR is merged by the
        session once its checks are green and the workbook has been opened.
      - *First real run:* "After all nine … i expect synthetic testing and
        proofing. you also have the adversarial skill" → synthetic fixtures
        prove each slice; a `canon:adversarial` pass (another agent writes
        only tests to break it) runs before the desk; the desk run is last.
      - *existing_control:* "None … this is specific to an idea - it also
        has to be generalized" → the step-7 sentence asserts nothing the
        tool cannot know: the share where the two fields disagree, plus what
        the question file says reacts today. No word like "unverified" is
        the tool's.
      - *Utilization threshold:* "why would we define this in the script
        when the person running the test can do it? … utilization can be
        segmented into percentages itself … the directive has been clear
        about being adaptable" → no threshold anywhere in the tool or spec.
        A measure outcome takes a single cut or a set of percentage bands,
        chosen by whoever runs it, and the pack shows the bands. Built in
        slice 2 (#365). The docket should not have asked it.
- **Decided against (2026-09-18), permanently for this tool:** any
      domain-specific list, mapping or transform in the code. The firm: "i
      don't want to have a sector list - this is supposed to be generic...
      it should be adaptable." Grouping is a generic `prefix` or a `map`
      the config supplies (PRD §6.15); the NAICS list that was in the PRD
      for a day is gone, and with it the item to confirm it.
- **Decided against for now (2026-09-18):** a PII guard for this project
      (the firm: "stop worrying about PII. It is all on Key's desk"); Excel-
      side bucket edges via a fine-grained cube; two outcomes in one pack;
      any numpy/scipy/statsmodels/sklearn on the build path (the desk has
      none); charts beyond the gradient blocks.

- **Walked at a desk (22 Sep 2026, `canon:walk`).** The job "test the
      tool from the emailed file to a read workbook", done as a person would:
      the bundle saved into an empty folder, every command typed, every
      screen read, the workbook opened tab by tab, then a question file
      written for the extract and a pack built from it. Thirty screens, all
      kept. Two documents: `portfolio-analysis-pack/docs/PROCEDURE-desk-test.md`
      (delivered as one self-contained PDF under `docs/walkthrough/
      desk-test-2026-09-22/`, a screenshot per step, ringed and zoomed, and
      the route pictured first) and `docs/WALKTHROUGH-DEFECTS.md`, **eleven
      defects against 99 passing tests, 9 of 9 mutations caught and 48 of 48
      harness checks, none of which caught any of them**. The first: fill in
      the question file exactly as `--init` writes it and the cover says
      step 4 is "not built in this version" — the skeleton ships
      `confounders: []` unmarked, and `wording.yaml`'s `not_built` sentence
      is used for a step that was given nothing to do. Then the JSON dump on
      every screen, a next-command line naming `pack validate` on a desk that
      has `build_pack.py`, a folder appearing beside the emailed file with
      `keybank_style.py` in it, headings cut by column widths in the rows
      the cover points to, chart helper columns shown as results, EPP and
      "no engine" unexplained, the run date silently set to the as-of date,
      "do they event more often", a knob note reading "(not in this
      version)", and the skeleton quoting three real values of every column.
      Nothing was fixed mid-walk; all eleven are a later slice. The walk is
      a script (`tools/walk_desk_test.py` over `tools/walkshot.py`, headless
      Chromium + LibreOffice, no image library): run twice, 22 of 31 screens
      byte-identical and the rest differing only by timings or by the
      capture tool's own height fix; the second run's screens are the ones
      committed. Deviations stated in both documents: terminal screens are
      rendered from captured text, spreadsheet screens are LibreOffice, and
      the knob change was written by a script. Excel itself is still the one
      thing not checked; the procedure is the script a fresh agent on a
      Windows machine with Excel would follow.
- **The walk's defects patched before anything shipped (22 Sep 2026, later
      the same day).** The firm, on being offered the script to test live:
      *"Wait stop hold on back up we need to patch anything wrong prior to
      shipping. Especially math issues."* Held. On the math: the walk had
      found no arithmetic defect, and `WALKTHROUGH-DEFECTS.md` now ends with
      every number checked by hand from the screens (the crude odds ratio and
      its interval recomputed from the four cells, the gradient multiples,
      the capture shares, events per coefficient, the two known answers, the
      formula twins). Ten of the eleven screen defects fixed in one slice,
      each pinned in `tests/test_walk_defects.py` (9 tests): the confounders
      slot is marked in the skeleton and a file with none is told so at
      validate, build, cover and model tab; the bundle keeps its JSON off
      the screen unless `--json`; every command ends with a `then:` line in
      the running front door's spelling; the bundle unpacks to a temporary
      folder removed on exit and `keybank_style.py` is `workbook_style.py`;
      header rows wrap and grow, no heading is cut (a test walks every
      sheet); chart and pooling columns are headed `chart:` / `working:` in
      a quieter face; "events per coefficient" and "runs when Excel opens
      the file" replace EPP and "no engine"; without `--run-date` the pack
      says "run date not given" rather than print the as-of date; "is
      {outcome} more common among them" replaces "do they {outcome}"; the
      knob note and the outcome line say what is true. Defect 11 stands by
      the firm's ruling of 18 Sep. Verified: 108 tests (99 + 9), 48 of 48
      harness checks on the patched bundle, the mutation check, and the walk
      run again on the patched script — thirty screens re-captured, the
      procedure re-issued from them, and the skeleton now filled with three
      confounders so the designated pack's cover matches the demo's.
- **The picker (22 Sep 2026).** The firm, asked how a desk designates its
      own columns: *"I want it to be really easy like a picker … I want no
      editing at the desk of Python or script this is meant to be straight
      forward. Build it and identify other opportunities."* Built:
      `python build_pack.py --setup EXTRACT.csv` (installed: `pack setup`)
      lists the extract's columns with a number, what each reads as, how
      often it is blank and three sample values, then asks one question at
      a time — which column numbers the loans, the origination date, the
      two rule columns, ratio or difference, the flag line, the gradient
      edges, how the extract says a loan went bad (a date column, a yes/no
      flag, or a measure from two columns), the word for it, the window,
      the as-of date, the columns the effect might hide in (numbers banded,
      quartiles proposed from the data; text taken level by level), what
      reacts today, anything known only later, the run date — writes the
      question file from the answers, checks it with the same loader, and
      builds the pack. Answers are numbers; four are words or dates. A
      wrong answer is refused and asked again; a column known only later
      named in the rule is refused as a leak on the spot. The tool proposes
      only what the data shows (the one column distinct on every row, the
      one date column, quartiles) and fills nothing unanswered. A second
      run finds the question file and offers to reuse it. The bundle now
      checks for openpyxl and PyYAML before anything and prints the one
      `pip install` line if either is missing. `src/analysis_pack/picker.py`,
      `tests/test_picker.py` (6). `pack init` and the Notepad path stay for
      scripts and the harness. The walk's Part E is now three screens of
      the picker and the cover (25 steps, not 30).
      **Other opportunities seen at the desk, not built (the firm to pick):**
      (a) `--synth demo` could build the demo pack too, so the demo is one
      command; (b) after a build, offer to open the workbook in Excel;
      (c) the picker could ask for controls beyond the origination year
      (a numeric column as a log, a text column as categories); (d) a
      `.exe` so a desk without Python can run it — the single biggest
      hurdle left, and outside the "pure-ASCII script" design; (e) an
      `.xlsx` extract is already read (`--sheet NAME` picks the tab) but
      the procedure only shows `.csv`; (f) the as-of date could be
      proposed from the latest origination date in the file (a fact, shown
      and confirmed, never assumed).
- **The form (22 Sep 2026, later).** Asked whether there was an easier
      way to select than typing numbers, the firm was offered a pop-up
      window or a form in Excel and chose the form: *"Actually excel
      version is fine."* Built: `python build_pack.py --setup EXTRACT.csv`
      run once writes `question.xlsx` beside the extract — the Columns tab
      has one row per column (what it reads as, how often blank, three
      samples) with a dropdown beside each for its role (loan number,
      origination date, rule top, rule bottom, rule top + group, rule
      bottom + group, went bad: date / flag / measure top / measure bottom,
      group), a yes/no for known-only-later, a cell for band edges with the
      column's quartiles shown beside it from the data; the Answers tab
      holds the twelve answers that are not a column, two of them required
      (the event word, the as-of date) and the rest at a usual value. The
      person picks in Excel, saves, runs the same command again; the tool
      reads the form, refuses everything the loader would refuse at once,
      each with its cell (`Columns!F9: category_1 reads as text, and "rule
      top" needs a number column`; a leak on `G7`; edges that fall on
      `Answers!B6`), writes `question.yaml` from the form and builds. A
      form written for another extract is refused by name. Excel's own
      storage is read as Excel stores it (a typed date becomes a date cell,
      a number a number). The picker stays as `--setup … --ask`; the yaml
      the form writes is byte-for-byte the yaml the picker writes from the
      same answers, and a test proves it. `src/analysis_pack/form.py`,
      `tests/test_form.py` (7). The walk's Part E is now the form: 27
      steps, four screens of Excel. The bundle grew to 117 KB.
      **Seen while building, not built:** (g) the form could carry the
      column's quartiles into the edges cell as a starting value instead of
      beside it, at the cost of a value the person did not type; (h) a
      second sheet in the extract's own workbook could hold the form, so a
      `.xlsx` extract and its designation travel as one file; (i) the form
      could be re-read on a timer, so saving in Excel builds without a
      second command — a watcher, which is a process, which is a different
      kind of tool.
## 6d · Origination Cube (`origination-cube/` — started 2026-09-25)

A loan extract and a cube file go in. Every band is crossed with every
dimension, and each pocket's rate is compared with the topline to find where
the book bleeds. It replaces the firm's Excel macros
(M08_Modes/M09_Roles/M10_ConfigEvents/M11_Median), which were reviewed on 25
Sep. Each place the VBA broke its own rules is tracked one at a time in
`origination-cube/docs/vba-findings.md`, with the test that stops it coming
back.

- [x] **Slice 1, the engine: built 25 Sep 2026.**
  - 39 tests.
  - 6 of 6 mutations caught (`python tools/mutation_check.py`).
  - Every grid is tied out against separately accumulated totals, and the
    excess figures must add to zero.
  - The planted pocket (score under 620, broker channel) is first on the
    bleed list.
  - Speed, pure Python: 1,000,000 loans take 6.7 s to read plus 19.6 s for
    one grid.
  - Rulings OC-1 to OC-4 are recorded in `vba-findings.md`:
    - OC-1: count and show a value that won't read.
    - OC-2: missing-value codes are rules in the file.
    - OC-3: thresholds are required.
    - OC-4: pockets are compared with the topline.
- [ ] **Slice 2: the workbook.** Python writes a small table of per-cell sums.
      Rates, the vs-topline index and readings are Excel formulas over it, so
      the thresholds can be changed in Excel, as in the Portfolio Analysis
      Pack. It includes a check tab with Python's value beside every formula.
      Its layout is for the firm to decide.
- [ ] **Slice 3: `cube init`.** It profiles every column and writes a cube file
      with `[CONFIRM: ...]` on each band and dimension it proposes. This
      replaces the candidacy table (READY / REVIEW / BLOCKED).
- [x] **Answered 25 Sep, rulings OC-5 to OC-10 in `origination-cube/docs/design.md`:**
  - cross everything and rank it
  - compare each pocket with the book, its parent and the rest of its peers
  - raise odd values as questions without stopping the run
  - apply materiality when the cube is read, not when it's built
  - a control center with explained options
  - a proof stage on the loans themselves
  - Population size: 17,000 × 80 in the firm's example, so pure Python is
    enough (100 grids in 3.7 s).
- [x] **Control tab built** (`cube control`): 12 settings from
      `settings.yaml`, each with options, explanations and your own value;
      rendered through LibreOffice with no error cells.
- [x] **Built later on 25 Sep, rulings OC-11 to OC-16 in `origination-cube/docs/design.md`:**
  - **Required lines:** key, booked, yes/no outcome, GCO and RANR, from which
    four core rates are built.
  - **`cube init`:** suggests the required columns with reasons, and refuses
    until `columns_confirmed: yes`; sorts every column into band, dimension
    or neither; raises odd values as questions.
  - **Bands** are set by a count or by cut points.
  - **Each pocket is tested** against the rest of the book, its band and its
    dimension (the ratio-estimator test).
  - **Evidence printed with every run:** loans needed for a gap, the smallest
    gap each pocket could show, and what each materiality level keeps.
  - **Judgment settings** (materiality, enough loans, worse at, confidence)
    open blank on the Control tab and are never pre-chosen.
  - **The size floor is not a gate.** A version that used the suggested
    3,500 loans as a minimum hid the planted 6.6x pocket of 531 loans; each
    pocket's own test decides.
  - 86 tests; 11 of 11 re-inserted bugs caught.
- [x] **Every column gets a meaning, and the tool learns** (rulings OC-17
      to OC-20):
  - `cube init` suggests a meaning for every column from a catalog in
    `settings.yaml` (FICO, score, DTI, LTV, dates, servicing ...).
  - What is confirmed is remembered outside the repository (names and
    meanings only), and can be pruned with `cube memory --forget` or an Excel
    Keep / Forget review.
  - Data recorded after booking is called servicing.
  - The Control tab shades what needs an answer instead of labelling it.
  - 95 tests; 13 of 13 re-inserted bugs caught.
- [x] **No commands for users (ruling OC-22), plus the walkthrough's 15 defects fixed:**
  - `Origination Cube.pyw` opens a two-button window: Set up, then Run.
  - One workbook holds every decision: Start here, Control, Columns, Odd
    values, Learned. Results land in the same workbook: Where it bleeds,
    Grids, Check, Log.
  - Every Control answer is applied (loan age, fewest losses, materiality,
    judged-against, the allowance for many tests).
  - RANR is revenue, so less of it is the bleed.
  - 126 tests; 19 of 19 re-inserted bugs caught.
- [x] **A third layer, GCO against RANR, and the second walkthrough's 16 defects**
      (rulings OC-23 to OC-25):
  - One column can split every pocket. A number is split at each pocket's own
    median, and the Split tab compares high with low, pooled across pockets
    (Mantel-Haenszel odds, a steadiness check, and observed against expected
    for the dollar rates). A category repeats each grid once per value.
  - On a planted book (revolving debt above the usual for the score: 1.8x the
    bad rate) the split finds 1.84x, worse in 20 of 20 pockets.
  - **Losses vs revenue:** each pocket in one of four boxes, with both flags
    and a chart. Nothing is netted until the firm says whether RANR already
    has losses taken out.
  - **Show per pocket:** the median or average of any number column.
  - **Materiality tab:** what each level would keep.
  - The second walk's defects: 15 fixed, 1 in part (a long problem list can
    scroll out of sight in the window). The status table is in
    `docs/walkthrough/walk-2026-09-25-b/WALKTHROUGH-DEFECTS.md`.
  - 160 tests; 32 of 32 re-inserted bugs caught.
- [x] **The third walkthrough's 16 defects** (rulings OC-26, OC-27; the firm chose B, B, C):
  - Losses vs revenue has nine boxes, set by the lines on Control. Revenue has its
    own line, and the suggested option is worked out from the book: what luck
    alone can move revenue in a typical pocket.
  - Each split grid says what it holds fixed, with the correlation.
  - Three-way pockets are tested and ranked on their own tab.
  - 14 fixed, 2 in part (the window can still scroll; the charts don't name their boxes). Status table in
    `docs/walkthrough/walk-2026-09-25-c/WALKTHROUGH-DEFECTS.md`.
  - 170 tests; 39 of 39 re-inserted bugs caught.
- **Docket, 25 Sep 2026:** https://claude.ai/artifact/SCjJwU3YSBZskGLztNjBP7. It asks six decisions: the
  many-tests reach, suggestions for other calls, a real-Excel check at work, RANR
  netting, the pull request, and remembering band edges. The firm answered at 18:27 UTC:
  - **Many tests:** keep the allowance per grid. Check will say what it covers.
  - **Suggestions:** yes, "where there's a calculation". Suggested options come
    from the book, are labelled, and are never pre-chosen (OC-13 holds).
  - **Excel check:** *"you keep working and such on it and debugging, i will tell
    you when i think it's in a position to be used at work"*. No Excel check
    until the firm says so.
  - **RANR netting:** still asking. It stays out.
  - **Pull request:** keep it a draft until the Excel check.
  - **Band edges:** yes, remember them, and *"it must have more bands than this for
    sure - like i can tell you from experience 20 point bands look very different.
    i assume all banding is adjustable to a degree"*. So: a band width ("every
    20") as well as edges, remembered per column, and more bands on offer.
  - **Next:** go ahead (the fourth walk).
  - **RANR (asked at work):** *"ranr does include the credit loss as far as we can
    tell"*. So nothing is netted (OC-29).
  - Built the same evening: band widths ("every 20"), remembered edges, 20 bands
    on offer, and suggested values for fewest loans and worse/better. 174 tests;
    42 re-inserted bugs.
- [x] **The fourth walkthrough's 11 defects**: 8 fixed, 3 in part (the luck line
      is one number per run; chart box names; Control's question wrap). The
      booked amount can split, by design. Status table in
      `docs/walkthrough/walk-2026-09-25-d/WALKTHROUGH-DEFECTS.md`.
- [x] **The fifth walkthrough's 11 defects:** 7 fixed, 3 fixed in part, 1 open
      (the chart). The firm's calls (OC-30): the lines decide the boxes and luck
      is marked; the suggested fewest loans is 5 expected losses. Status table in
      `docs/walkthrough/walk-2026-09-25-e/WALKTHROUGH-DEFECTS.md`. 184 tests; 50
      re-inserted bugs.
- [x] **The sixth walkthrough's 11 defects:** 8 fixed, 2 fixed in part, 1 open (an
      exact test for small pockets, proposed). The firm's call (OC-31): the
      suggested revenue line is each pocket's own luck range. 187 tests; 53
      re-inserted bugs. The walk's read on convergence: the edges are getting
      smaller, but the top defect kept changing shape until OC-31.
- **Small pockets (25 Sep 2026):** asked whether a pocket too small for the usual
  test should get an exact test, the firm answered: *"not really sure, if they were
  large maybe. this is a materiality thing"*. So there's no exact test for now. A
  pocket that is material but too small to test is shaded blue on Where it bleeds
  and counted in the window, to be looked at by hand. Both floors (fewest loans,
  fewest losses) keep their suggested option and take an override.
- [x] **Bands read as ranges** ("496 - 619", "620 - 679"), not "under 620" and
      "620 to under 680". The firm asked for this because words make the page look
      cluttered. 189 tests; 56 re-inserted bugs.
- [x] **Losses vs revenue shows its numbers** (the firm: *"find a clean way to
      display the comparable metrics"*). For losses and for revenue: this pocket,
      the rest, the multiple, a reading and the dollars. Red and green are on the
      cells, and the "Which box" column is gone. Control's In use now agrees with
      the run on a number such as 0.95. 190 tests; 59 re-inserted bugs.
- [x] **The seventh walkthrough's 8 defects:** 5 fixed, 1 gone with the box column
      (the wrapped box text), and 2 are the firm's call: which line RANR uses on
      Where it bleeds, and red on Three-way rows that don't hold FICO fixed.
      Checking its blank *Last Run used* rows found that Control's category limits
      were never used. They now apply at Set up. The write-up for the firm's own
      tests found that a negative RANR comparison flipped a pocket's reading; the
      multiple now keeps its direction. 193 tests; 64 re-inserted bugs. Status
      table in `docs/walkthrough/walk-2026-09-25-g/WALKTHROUGH-DEFECTS.md`.
- [x] **Proof that the engine is generic** (the firm asked, worried by walk numbers
      that all came from one test book). The whole route now runs on a second book
      with other names, another product and a problem planted in a dealer and a
      region; the workbook finds it and carries nothing from the first book. That
      test found Control's explanations using the test book's pocket as their
      example; they're generic now. 194 tests.
- [x] **The firm's two calls from walk 7** (OC-32, OC-33): the revenue setting
      decides revenue on every tab, and Three-way rows whose grid doesn't hold the
      score fixed aren't red. 197 tests; 66 re-inserted bugs.
- [x] **Next (set by the firm, 25 Sep 2026):** *(Done 26 Sep 2026: all six steps. The
      cube has what the confirmatory test needs; the test itself is 4b, the new Next.)*
      *"RANR is profit after losses —
      interest income + fees − cost of funds − losses — and the cube's outputs, tests
      and synthetic book should treat it that way; and the cube should be ready to test
      a derived column (income ÷ sales) against a dated outcome, on a holdout, from a
      committed pre-spec."* Every item is listed, with a box to tick, in
      `origination-cube/docs/NEXT-GOAL.md`:
      - an audit (1a–k), reported before any source changes
      - 18 fixes (3.1–3.18)
      - 5 capabilities, scoped but not built (4a–e)
      - an adversarial pass on the statistics module
      - the questions handed back

      Two of its references were not in the repository when it was set:
      `docs/statistics.md`, and the other agent's tree-based scouting code (no
      branch of 131 has either). The eighth walk (stopped on the firm's word: *"there
      will be a large change to code incoming"*) and the Claude Design hand-off wait
      until this is done.
- **Audit reported, 25 Sep 2026** (`origination-cube/docs/audit-2026-09-25.md`). The
  firm's answers to the four questions it raised (rulings OC-34 to OC-37):
  - **The permutation test:** *"add numpy; this is the kind of script where it should
    outline what is missing and try to download it, right?"*
  - **The losses inside RANR:** GCO.
  - **CMH:** no continuity correction, matching the reference.
  - **Share of loans:** the pooled two-proportion test (A1).
- [x] **Wave 1 of the fixes (26 Sep 2026), four agents in parallel, each merged:**
  - **Statistical tests** (`stats.py`, new `perm.py`, `engine.py`):
    - share of loans on the pooled test (A1), and Fisher's exact test (B1) below
      fewest loans;
    - every dollar rate on a 10,000-shuffle permutation test (B2), within the band
      or the book;
    - CMH without the ½;
    - A3's power formula;
    - the many-tests family is inner pockets only.

    Every worked example in `docs/statistics.md` for a test the cube runs is reproduced by
    a test: 8 of the 12 (A1–A3, A5, A6, A8, B1, B2), plus A7's and B9's arithmetic. The
    other four (B3/B4, B5, B6, B7) belong to capabilities 4a–4e, scoped and not built.
    *(Corrected 26 Sep: this line first said every worked example; the final check
    found four untested.)*
  - **The Look tab** (`look.py`).
  - **The pre-spec reader** (`prespec.py`, data only).
  - **The launcher's add-on check and install** (`deps.py`, OC-34).

  CI went red once on the way: numpy wasn't listed in `pyproject.toml`, so the new
  add-on check refused to run in CI. It was fixed by listing it. 350 tests; 81
  re-inserted bugs.
- [x] **Wave 3 (26 Sep 2026): dates, the outcome window, new columns** (NEXT-GOAL 3.9,
  3.10, 3.11, 3.13, 3.14; merge 3dcb3da).
  - **Dates:** origination date and outcome date roles give months on book and
    months to bad.
  - **The window:** bad means bad within N months. Loans under N months are left
    out and counted. Check gives the origination range tested and how much of the
    loss seasoned loans show had landed by month N.
  - **New columns:** ratio columns defined on Control (e.g. INCOME ÷ SALES), cut or
    split like any column, each with a Look block.
  - **Columns tab:** a period (per year / per month / one-time), with a Check warning
    when a ratio's inputs disagree; and a definition in the analyst's words.
  - **A dated synthetic book** (`write_extract(dated=True)`) plants the income ÷
    sales cliffs from `docs/scout-vs-measure.py`.
  - **A bad date** in a cube file is now a plain refusal.

  385 tests; 119 re-inserted bugs. **Its calls, for the firm to confirm** (listed in
  the hand-back):
  - where the as-of date comes from;
  - only the yes/no outcome is windowed, while GCO and RANR dollars stay as
    extracted;
  - the age filter and the window can't both be on;
  - definitions sit on Columns, not Control.
- [x] **Wave 2 (26 Sep 2026): RANR is profit after losses** (NEXT-GOAL 3.1–3.6;
  merge 89e1798).
  - **Points, not multiples:** RANR and a new "Contribution before losses" (RANR +
    GCO, OC-35) are compared in points of booked dollars (pocket − rest) on every
    tab. The two-negatives flaw and the near-zero blow-up are gone.
  - **The profit line on Control:** each pocket's own test (suggested), ± points, or
    the materiality line. "The same lines as for losses" is refused.
  - **Words:**
    - "p-value" and "not significant" replace "Luck alone" and "could be luck";
    - profit reads "keeps more / about the same / keeps less";
    - Losses vs revenue reads what they paid us / what they cost us / what we kept,
      with a Together column ("priced for it", "net drain", "safe but idle");
    - the dollar rates' Test column reads "shuffled: N of 10,000".
  - **Synthetic book:** RANR = contribution − GCO, and a priced-for-it pocket is
    planted. The firm's Tests 2 and 4 are tests; Test 4 as written reads profit
    "about the same", and an 8% variant reads "priced for it".
  - **A merge bug, caught by the suite before the push:** both waves had defined the
    synthetic book's AS_OF, one as a date and one as text (01d70ff).

  410 tests; 133 re-inserted bugs.
- [x] **Wave 4 (26 Sep 2026): Check lines, prevalence and the pre-spec** (NEXT-GOAL
  3.12, 3.15–3.18; merge 60ba9bc, tests brought up to Wave 2 in 7d886de).
  - **The pre-spec, named on Control:**
    - Check echoes it, with its commit;
    - one warning for each place the run deviates, and the Log says "Deviates from
      pre-spec";
    - a run whose extract holds holdout loans is logged "Touched the holdout", and
      Check counts those runs.
  - **The pocket budget** (bad loans ÷ 5) against each grid's pockets, with
    coverage in loans and dollars.
  - **The family count**, with the line that a single red across many families is
    weak evidence.
  - **A product-mix warning**, using a new "Credit product" meaning.
  - **A Prevalence tab** ("a count, not a test").

  430 tests; 164 re-inserted bugs. Every fix, 3.1 to 3.18, is now on the branch.
- [x] **The adversarial pass (NEXT-GOAL 5, 26 Sep 2026).**
  - **The pass:** another model, given only the job of breaking the arithmetic
    with tests, formed 33 hypotheses, ran them, and delivered 8 failing tests (4
    findings) on branch `adversarial/origination-cube-stats`.
  - **The intake, done by hand** the way `canon`'s intake works: only its findings
    file crossed over, and the branch touched nothing else.
  - **The four findings, all fixed** and moved into
    `tests/test_adversarial_2026_09_26.py`:
    - a p-value exactly at the bar;
    - Cochran's Q off A8's centre;
    - an absent rate read as zero;
    - an unanswered shuffle named as a test.

    Each has a planted bug, all caught; 169 in total.
  - **Proposed tenet for canon** (the firm's yes needed): *compare against a bar
    computed once and rounded, never against `1 − confidence` inline*.
- [x] **The mutation checker could run a stale planted bug** (found 26 Sep 2026: a
  clean checkout read one test red).
  - **Cause:** Python validates cached bytecode against the source's size and its
    mtime in whole seconds. A same-size mutation restored within one second left
    the mutant's bytecode in `__pycache__`, and the next run executed it.
  - **Effect:** one test read red on a clean checkout, and inside a mutation run a
    same-size mutant of the same file could run the previous one's bytecode.
  - **Fix:** the checker writes no bytecode from a mutant, drops the file's cache
    before and after each mutation, and its loop sits behind a main guard.
    `tests/test_mutation_tool.py` rebuilds the trap and proves it cleared.
- [x] **CI's mutation run died partway through** (26 Sep 2026, on `da0271a`).
  - **Cause:** the adversarial fix rewrote one line in `book.py` that the "split
    luck shaded" mutation planted into. Its text was no longer there, so the
    runner stopped on its own assert after about sixty mutations. The other
    hundred never ran.
  - **What I got wrong:** I checked only the four new mutations against the
    source, not all 169.
  - **Fix:** the entry now points at the current line and is caught. A new test
    in `tests/test_mutation_tool.py` checks that every planted bug still finds
    its line, so the next stranded entry fails the ordinary suite instead.
    That test failed on the old list and passes on the new one. The suite now has
    442 tests.
- [x] **The final check (NEXT-GOAL 6, 26 Sep 2026):**
  `origination-cube/docs/final-check-2026-09-26.md`.
  - **Who:** an agent that had not seen the work, on a clean copy of `a0f5bd1d`.
    It checked facts against sources, reran the arithmetic and opened the workbook.
  - **Result:** 206 claims checked. 181 held, 25 were wrong (14 findings), and 13
    could not be checked. **No error in the cube's arithmetic:** every worked
    example it runs matches `statistics.md`, scipy or statsmodels, and one pocket
    recomputed by hand from the CSV equals the workbook to the dollar.
  - **Every finding was fixed.**
    - 11 were in what the docs say about the work (`84440bc`). Examples: the README
      said the result tabs weren't built; "every worked example is tested" was 8
      of 12.
    - 3 were on the tabs, fixed by two agents with tests and planted bugs (merges
      `c7a6e92`, `924fd7f`):
      - F5: Check called the run's loan range "the holdout";
      - F9: jargon, ruling numbers, and a stale ask on Columns;
      - F13: one pre-spec group had two names, and a future date passed silently.
    - **One more on the way:** Split answered "yes" to "Same size in every pocket?"
      whenever Cochran's Q wasn't significant. `statistics.md` A8 says that is "never
      proof they agree", so it now reads "no sign they differ".
  - **New:** OC-38 records the switch to profit in points.
  - **Counts:** 454 tests; 177 planted bugs.
  - **For 4b:** the holdout line compares the run's first and last loan with the
    pre-spec's range. Once a run can hold itself to the holdout, it must compare the
    range it filtered to.
  - **For the next walk:** the wording seen but not fixed is listed at the end of
    the final check's file.
- [x] **The hand-back (NEXT-GOAL 6, 26 Sep 2026).** Docket:
  https://claude.ai/artifact/Dm54ZNHGJWaT9jooucgW4R. It is a separate page from the
  25 Sep docket, whose seven answers are logged above and are not asked again.
  - **Next, which silence approves:** build 4e, then 4b, so a pre-spec'd test of a
    new column runs from start to finish on held-back loans.
  - **The 12 decisions, each with both outcomes and a recommendation:**
    1. correct `statistics.md`'s three slips;
    2. window the dollars, or not;
    3. keep "latest" as the as-of date;
    4. keep refusing the age filter with a window;
    5. definitions on Columns;
    6. Test 4's "about the same";
    7. the pre-spec's "deviates" until 4b;
    8. a pocket alone in its band;
    9. scikit-learn for 4a;
    10. 4c's lines;
    11. 4d's bands and "survives";
    12. the tenet "compare against a bar computed once".
  - **What ran, for the whole goal:**
    - the audit;
    - 18 fixes in four waves of agents;
    - the scope for 4a–4e;
    - the adversarial pass: 33 ideas, 4 bugs;
    - the final check: 206 claims, 25 wrong, all fixed.

    The goal started at 197 tests and 66 planted bugs, and ends at 454 and 177.
- [x] **The firm's answers to the 26 Sep docket** (read back 26 Sep 2026, 10:15 UTC; their
  words verbatim):
  1. **statistics.md's three slips:** "Correct them, marked", with *"Confused about why they
     seemed wrong in the first place. Ensure you are correct too."* All three were recomputed
     before editing, and each correction is marked in the file:
     - B1: 1.0189 is 12 × 18 / 212, the rate the test assumes both share. 0.84 used the
       rest's rate alone.
     - B3/B4: the example reproduces only with groups of 100/400/500/400/100 loans, and
       66.4714 rounds to 66.5.
     - B7: the script prints 7.64% at 0.10.
  2. **Window the dollars:** *"I need this issue simplified when explained to me."* Asked
     again in plain words.
  3. **"Latest" as the as-of date:** *"The as of date is not of concern generally. And we would
     never use the as of date in place of a date. Either the gross charge off or original date
     is there or it isn't."*
  4. **Age filter and window together:** *"The person running it is in charge of whether
     something has been in the books long enough. This should not be a concern of the engine.
     If we have the age and can run that particular analysis great. Until this point we didn't
     include the date and it turns them into additional factors such as charged off in x
     months."*

     Answers 3 and 4 read together as: the engine stops policing seasoning, and dates only
     make factors. That reading was put back to the firm to confirm before anything changes.
  5. **Definitions:** "Keep on Columns". No change.
  6. **Test 4:** *"Not sure what is being said here. Is this configurable?"* Explained again.
  7. **Pre-spec "deviates" until 4b:** *"This is not a problem if we are fixing it."* Kept
     until 4b, which is Next.
  8. **A pocket alone in its band:** "Compare with the book", with *"It's hard to believe this
     will even happen unless a specific circumstance."* Being built: compared with the book, and
     the row says so.
  9. **scikit-learn for 4a:** "Optional add-on".
  10. **4c's lines:** *"This is not something the engine is meant to catch. This is non
      generic. This is meant to be something we may do on a specific study or something."*
      4c is out of the cube (`docs/capabilities-scope.md`).
  11. **4d:** "As proposed": 5 equal-loan bands; "survives" means the interval still excludes 1.
  12. **The tenet:** "Yes, add it". Being added to canon as S36.
  - **Next:** the box was left blank, so build 4e, then 4b.
- [ ] **First: take the date work out of the bleed analysis (OC-39, the firm, 26 Sep 2026).**
      Remove the loan-age filter, the outcome window, the as-of date, the outcome date role and
      the pre-spec's `window_months`. Keep the origination date for the dev/holdout split, and
      add one Check line giving its range. The firm answered decision 2 (windowing), 3 (as-of)
      and 4 (age filter) with this.
- [ ] **Next (proposed on the 26 Sep docket; silence approves it):** build 4e, then 4b
      (`origination-cube/docs/capabilities-scope.md`). It ends when the planted income ÷
      sales cliffs are found on development loans and confirmed on the holdout from a
      committed pre-spec, and Check no longer says "deviates" on the reference group.
- [ ] **After that:** the eighth walk on the new layout; the Claude Design hand-off;
      `cube drill` and `cube prove` (and put their settings back on the tab).
- **Not checked:** real Excel, a real extract, and the bank machine
  (Python and the add-ons installed, and .pyw files opening with Python).

## 7 · Standing rules for new items

New idea -> add a line here (one sentence, why it matters). New lesson
found in any build -> `TEMPLATE_CONTRACT.md` carried lessons (L-series),
not here. Anything touching the watchlist boundary or licensing -> gets a
research pass before a spec, no exceptions.

---

## Done log

- 2026-09-25 -- **Origination Cube slice 1: the engine** (`origination-cube/`). It replaces the firm's origination-analysis VBA. 39 tests, 6 of 6 mutations caught, and every place the macros broke their own rules is tracked in `docs/vba-findings.md`. The workbook is slice 2. Open questions are in §6d.
- 2026-09-19 -- **Portfolio Analysis Pack v1 built** (`portfolio-analysis-pack/`, nine slices #364–#372, one PR each). The ladder plus door one, the bundle, the render harness and the mutation tool. 94 tests, 9 of 9 mutations caught, 100,000 loans in 12.7 s to a 164 KB workbook. Then the adversarial pass: 35 hypotheses, 16 red, 15 fixed and 1 restated, all in the suite. Not checked: Excel itself and the desk run — §6c has the list.
- 2026-09-18 -- **Portfolio Analysis Pack grilled and PRD'd** (`portfolio-analysis-pack/docs/prd-portfolio-analysis-pack.md`). Fourteen decisions put to the firm as questions; two touched the record and are ruled in `canon/CONVICTIONS.md` (C11 struck for the project, C9 upheld on placement). Open items above in §6c.
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
