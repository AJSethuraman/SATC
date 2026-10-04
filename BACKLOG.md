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
## 6d · PocketBook (`pocketbook/`, built as Origination Cube in `origination-cube/` — started 2026-09-25)

*2026-09-27: the folder moved from `origination-cube/` to `pocketbook/` (Goal 3 item 1, the rename sweep;
entry below). Entries dated before then keep the old paths as they were written: read `origination-cube/` as
`pocketbook/` and `src/origination_cube/` as `src/pocketbook/`.*

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
     After the walk-through (the 3% is a one-time $600-style lift; doubled losses cost about
     3.8 points; the net −0.8 points is 80 bps short of the band), the firm: *"Approve."* Test 4's
     "about the same" stands.
  7. **Pre-spec "deviates" until 4b:** *"This is not a problem if we are fixing it."* Kept
     until 4b, which is Next.
  8. **A pocket alone in its band:** "Compare with the book", with *"It's hard to believe this
     will even happen unless a specific circumstance."* Built (merges a7909d6 and after): a lone
     pocket is judged against the book; Where it bleeds says so in its Test column, Losses vs
     revenue in a "Compared with" column, and Check counts them. First try put the note in
     Together, which the full suite caught (3 tests). 448 tests, 168 planted bugs.
  9. **scikit-learn for 4a:** "Optional add-on".
  10. **4c's lines:** *"This is not something the engine is meant to catch. This is non
      generic. This is meant to be something we may do on a specific study or something."*
      4c is out of the cube (`docs/capabilities-scope.md`).
  11. **4d:** "As proposed": 5 equal-loan bands; "survives" means the interval still excludes 1.
  12. **The tenet:** "Yes, add it". Being added to canon as S36.
  - **Next:** the box was left blank, so build 4e, then 4b.
- [x] **First: take the date work out of the bleed analysis (OC-39, the firm, 26 Sep 2026).**
      *(Done 26 Sep, merge b386e87: every loan runs; Check prints the origination-date range;
      an old cube file, pre-spec or Control row naming a removed setting is refused by name,
      and has to be deleted once. 442 tests, 164 planted bugs.)*
      Remove the loan-age filter, the outcome window, the as-of date, the outcome date role and
      the pre-spec's `window_months`. Keep the origination date for the dev/holdout split, and
      add one Check line giving its range. The firm answered decision 2 (windowing), 3 (as-of)
      and 4 (age filter) with this.
- [x] **Then: Set up asks what the run is for** *(Done 26 Sep, merge 75723ee: "What are you
      running?" heads Control, with a follow-up asked only for a new variable; each answer
      refuses by name on its own minimum; scouting is refused as not built; a pre-spec under a
      bleed run is refused. 461 tests, 175 planted bugs.)* (the firm, 26 Sep 2026: *"because those are
      added to this suite it likely makes sense for the script to ask which we are doing so it
      does indeed have the minimum required"*).
      - *Where the book bleeds* needs only the five core columns and never asks about dates.
      - *Finding and testing a new variable* also needs the origination date and the tested
        column, then asks: scout first, or test from a pre-spec already written. The trees
        stay optional. *(Amended 26 Sep 2026: it needs only what it uses, the key, the outcome,
        the origination date, the tested column and the strata; "the new-variable run needs only what it uses", below.)*
      - Each choice checks and refuses only on its own minimum.
- [x] **Then: literal row wording** *(Done 26 Sep, merged with the next item: e.g. "short of its
      band by 23.90 points ($1,338,239)", "-0.49 points against its band, not significant",
      "within 0.25 points of its band (-0.12)".)* (the firm, 26 Sep 2026: *"yes I prefer it to be
      literal"*). The profit reading says the gap, e.g. "short of its band by 0.8 points
      ($16,000)" or "ahead of its band by 4 points", instead of "keeps less" or "keeps more".
- [x] **Then: one comparison decides the verdict, the dollars and materiality** *(Done 26 Sep:
      both dollar figures on Where it bleeds and Losses vs revenue; the judged-against setting
      picks the one that ranks, flags and meets materiality; Check says which. 481 tests, 189
      planted bugs after both merges.)* (the firm, 26
      Sep 2026: *"That works"*).
      - Show both dollar figures, "over the book" and "over its band".
      - The reading and materiality follow Control's judged-against setting, so they can't
        disagree. The other figure stays visible for reference.
      - Why: materiality applied to the book-relative dollars while the reading used the band.
        A pocket in a high-loss band could clear materiality against the book while being in
        line with its neighbours.
- [x] **Then: the judging settings live in the workbook (OC-40).** *(Done 26 Sep, merge of
      `live-settings`: the five settings drive formulas on every result tab, through two hidden
      sheets; one rounded significance bar (S36); a LibreOffice recalculation test proves every
      live reading equals the engine's after each setting is changed. Order, charts and some
      Check counts stay as of the Run and say so. CI now installs LibreOffice, and the helper
      fails rather than skips there. 503 tests, 198 planted bugs.)* The loss line, the profit
      line, materiality, confidence, and judged against, all adjustable after the run. Scope
      first: which cells become formulas on each tab, and the recalculation step the tests
      need (openpyxl doesn't calculate formulas). Open question for the firm: is the bank's
      Excel Microsoft 365? That decides whether ordering can follow live.
- [ ] **Then: apply tenet T1** (`origination-cube/TENETS.md`, the firm, 26 Sep 2026: method
      is said once, never beside every row). Move the lone-pocket note and the Test column into
      one method note per tab, and sweep the other tabs for per-row settings.
- [ ] **Then: live ordering and counts (Excel is Microsoft 365, the firm, 26 Sep 2026).** Use
      SORT/FILTER on Where it bleeds and for Check's counts. The container's LibreOffice is 24.2,
      which predates SORT/FILTER (24.8), so the tests need a newer LibreOffice or another check.
- [ ] **Then: "judged against the book" on one basis** (the firm, 26 Sep 2026: option A, *"i
      think this makes most seense"*): points and dollars both against the rest of the book,
      as the band already is; the tie-out stays on Check.
- [x] **Then: the new-variable run needs only what it uses** (the firm, 26 Sep 2026: *"what's
      the point in that if you are searching for possibly important variables to the
      outcome?"*): the loan key, the outcome, the origination date, the tested column(s) and the
      strata. Booked, GCO and RANR become optional; if present, 4e also shows dollars.
      *(Done 26 Sep 2026, Goal 2 item 2: design.md OC-14 amended in place. Such a run writes
      no Losses vs revenue tab and says nothing about profit or booked dollars; the bleed
      analysis still refuses by name. Eleven planted bugs, all caught.)*
- [ ] **Then: no "not built yet" option on Control** (the firm: *"don't note what it does not
      include just note what it does"*): "Scout first" appears only once scouting exists.
- [ ] **Then: "Worse?" and "Material?" as two columns** (the firm, 26 Sep 2026: *"do it"*).
      Statistical significance and materiality are judged separately, as in risk and audit
      practice. The list ranks by dollars among the pockets that are worse.
- [ ] **Then: the pre-spec asks only for what it needs** (the firm: *"just drop unnecessary
      pre-spec columns"*). The strata default to the workbook's own band and segment columns,
      and are listed only when different. Several columns can be confirmed in one pre-spec, with
      the allowance for many tests across them.
- [ ] **Then: the tests are picked from one easy place** (the firm, 26 Sep 2026: *"all of these
      sorts of tests should be available in some sort of easy to pick way. at this point i
      think i am expecting a GUI of some sort"*). Waits on the redesign.
- [x] **Screens for the redesign** (the firm, 26 Sep 2026): every tab and every launcher state,
      rendered from the synthetic book: https://claude.ai/artifact/8duWJxayMTBtMe1GCPrvAX
      (the builder is `make_shots.py`, kept in the session's scratchpad).
- [x] **The pre-spec design** (the firm, 26 Sep 2026; built 27 Sep, OC-49, below): an outcome and a shortlist of inputs (never
      one: *"one column makes no sense - it can't be used in a tree"*), each with its cut points
      and reference; optionally the columns to hold fixed. Each input is reported on its own and
      with them held fixed, which folds in 4d.
- [x] **Then: scouting (4a).** Wide, on development loans: rank every candidate column and
      suggest bins. It feeds the confirmation, which is narrow: a shortlist, on the holdout.
      *(Done 27 Sep 2026: Goal 2 item 9, below; `origination-cube/docs/design.md` OC-50.)*
- [ ] **Next (proposed on the 26 Sep docket; silence approves it):** build 4e, then 4b
      (`origination-cube/docs/capabilities-scope.md`). It ends when the planted income ÷
      sales cliffs are found on development loans and confirmed on the holdout from a
      committed pre-spec, and Check no longer says "deviates" on the reference group.
- [ ] **After that:** the eighth walk on the new layout; the Claude Design hand-off;
      `cube drill` and `cube prove` (and put their settings back on the tab).
- **Goal 2 agreed, Count Bassy's pass, and the firm's three answers (26 Sep 2026).** The firm:
  *"we are now on the same page - make sure you docket all of this so we know what the goal
  is"*. Goal 2 is in `origination-cube/docs/NEXT-GOAL.md`, ten items in order. Count Bassy read 50
  entries (12 held convictions, 36 tenets, T1) and raised nine points. The run's minimum and the lean
  pre-spec moved up behind 4b (C11), and each item now names its proof (S2, S3, S13, S14, S18, S32).
  Answered on the docket (https://claude.ai/artifact/U5pHCYek9H7hqehzUvqs8M):
  - **Redesign hold:** the launcher, the test picker and the layout only. What a tab says goes ahead.
  - **Strata:** suggested, left blank. OC-13 holds with no exception.
  - **Pre-spec proof without git:** lock first. The workbook will not work out held-back results until
    a pre-spec is locked, and the Log records the lock and then each run, in order; git is recorded
    where it exists. The firm: *"actually i don't really know what this means - explain but probably
    take recommendation"*, explained in the reply the same day.
  - **Lock first, reopened:** once explained, the firm: *"i don't think there's a reason to have some
    sort of over the top control in place to make sure we didn't mess with our own analysis. is that
    what this is for?"* Answered yes, the trap is an honest one (the held-back loans helping pick the
    test), and proposed the lighter form: record, don't block. Built that way unless the firm says
    otherwise.
- **The redesign arrived (26 Sep 2026).** Committed unchanged in
  `origination-cube/docs/redesign-2026-09-26/`. The firm, on why Control could not suggest values:
  *"just select the workbook first, configure what you can, and then do the workbook config items so
  that there are suggestions to be made"*. The design's launcher order does exactly that. It becomes
  the main build; items 4, 6 and 7 fold into it; item 8 (live ordering) is replaced by the design's
  "order as of the last Run, verdicts live"; slicers become dropdowns. `NEXT-GOAL.md` has the phases.
- [x] **Redesign phase (a): the launcher's five steps, and suggestions at Set up (26 Sep 2026).**
      Extract, Set up, Choose tests, Answer in workbook, Run, each state (L1 to L5) as the spec draws
      it; the rules in `launcher.Flow`, tested without a display (`tests/test_launcher.py`), and
      photographed by `tools/shoot_launcher.py`. The cuts, the split, what's running, the saved
      shortlist and the two column limits are picked in the launcher and shown read-only on Control.
      The suggested fewest loans, worse at and better at are on Control when the workbook is written.
      The product is PocketBook in everything the analyst reads (the firm, 26 Sep 2026); "luck" is not
      used. Colours in `house.py`, not a copy of credit-suite's style file.
- [x] **Redesign phase (b): the tabs the analyst fills in (26 Sep 2026).** Start here, Control, Columns
      and Look to the spec's global rules and sections 1 to 4, with the firm's two Look additions: the
      mean beside the median, and live bars and range (10 / 20 / 50 bars and a From / To, regrouped by
      SUMIFS from 200 counted slices; no SORT, FILTER or LET), plus red dashed edge lines fed by
      formula from Columns and the likely code on its own bar. Control in three blocks with Status and
      the materiality panel (the Materiality tab is gone); Columns carries Odd values and Learned (the
      two tabs are gone); a new-variable run isn't asked the profit line. A Run loads the workbook once
      and saves it once (it was eight loads, three saves) and draws Look again only when the split
      moves: Run 31.0 s to 22.2 s, Set up 11.8 s to 12.5 s, at 17,000 × 80 under a 4 GB limit. "Run the
      cube" is "Run"; the launcher's clipped header is "Split by"; no analyst-facing "luck" or "cube"
      (a test reads every cell of the finished workbook). `tests/test_answer_tabs.py`, the Look tests
      rewritten; 21 planted bugs added, all caught; 10 moved ones repointed. 607 tests, 279 planted
      bugs. Departures: the answer keeps its *Or your own* cell; each option's meaning is a note on the
      setting's name, not a column. Not checked: real Excel (the combined bar-and-line chart is drawn
      by LibreOffice on the bars' axis; Excel draws it on the lines' own).
- [x] **Redesign phase (c): the result tabs (26 Sep 2026; `origination-cube/docs/design.md` OC-43, OC-44).**
      Pockets (Where it bleeds and Three-way), Paid cost kept (Losses vs revenue), Grids (with Prevalence
      under its blocks) and Split, to the spec's sections 5 to 8, in `src/origination_cube/results.py`; the
      four old tabs are taken off an older workbook at Run. Each tab: the title band, one grouped method
      note (T1: the Test column and the lone-pocket note are off the rows), lines-in-use tiles read from
      Control with "↻ N Control changes wait for a Run", then dropdowns in place of the slicers (Pockets:
      Measure, Pockets, Show; Paid cost kept: Grid; Grids: Grid and Measure; Split: Grid and Measure), each
      picking rows by INDEX/MATCH over hidden `_list`/`_views`, no SORT/FILTER/LET. Pockets' caption "N
      worse and material · N worse · N shown" is live. **Worse?** and **Material?** are separate columns;
      worse pockets rank first by dollars; order is the last Run's and each tab says so. **Option A built:**
      judged against the book counts points and dollars against the rest of the book (`excess_rest`); the
      whole-book excess stays as the tie-out. Together reads five pairs (adds strong; earns less, not from
      losses). Heat in the spec's tokens by rules that follow the Measure dropdown; loans shaded by share.
      The scatter (log x) is drawn from the table's cells, so it is live. "p-value" everywhere, never
      "luck". `tests/test_result_tabs.py` (21) and `tests/tabs.py` (reads a tab as the analyst sees it);
      old tests moved to the new layout. 20 planted bugs repointed and 24 added (310 in all), plus
      a test that a pytest run printing nothing still gets its verdict. 45 of 45 caught, each run alone. Run at 17,000 × 80: 23.2 s before, 21.7 s after.
      Departures: the scatter is live (the spec said as of the Run); "Earned before losses" and "Earns
      less, not from losses" are allowed past the old no-"earns" test, as the spec's own words; Split adds
      a Measure dropdown and keeps As odds; the other comparison's dollars leave the rows (they stay on
      `_pockets` and the command line). Not checked: real Excel.
- [x] **Redesign phase (d): New variables and Record (27 Sep 2026; `origination-cube/docs/design.md` OC-45 to OC-48).**
      **New variables** (black tab, spec section 9) replaces the Confirmatory test tab, in `confirm_tab.py`: one row per
      group of the pre-spec's column against its reference, **Found** (development, nothing held fixed), **Confirmed**
      on the held-back loans with *Holds up?*, **Confirmed with the held-fixed columns** (the pre-spec's strata) with
      *Still holds?*, then Excess (charge-offs above the group's share on the held-back loans, scaled to the book; bad
      loans without GCO), *Material?* and *In words*; the tiles (Outcome, Candidates, Held fixed, Loans found and held
      back, Material at, live) and a bar chart (Confirmed INK, held fixed KEY_RED, Found STONE when shown) with a dashed
      red line at worse at. The firm's lean pre-spec ruling is built: each input reported with and without the columns
      held fixed (the same conditional logistic regression with every loan in one pocket); the pre-spec needs no `hold`
      list, as its strata are the held-fixed columns, and old pre-specs read unchanged. A saved shortlist hides the
      Found columns and Record names the file. Every statistic the old tab had (B3, B4, the block test, B5 with its
      live range, 4e) is kept under the chart, on both sets of loans, with and without the columns held fixed.
      **Record** (grey tab, section 10, `record.py`) merges Check and the Log: This Run | Settings, Does it add up |
      Tests used, Left out | Every Run, each with the ONYX band, a CANVAS row, one label width and rows one line high
      (a long line goes on in the rows under it and reads back whole); Settings has in use now beside the last Run's,
      shaded while they differ. The Log is kept on the hidden `_log`, so a refusal shows at once; an older workbook's
      Log carries over. **Record, don't block:** the Log records a pre-spec when first read (fingerprint, the date in
      the file, its commit), each held-back run after it in order, and labels a run on a pre-spec changed after a
      held-back run. **Control** asks a new variable only worse at, materiality, confidence and the bands (the bleed's
      floors, better at, judged against, the catch rate and the allowance are hidden); worse at is suggested from the
      confirmation's own groups. **Memory:** the 2.5 GB pre-spec Set up was the harness's Set up without the launcher's
      choices, which cut all 74 columns (1,248 grids) for a suggestion pass run as a bleed; a new variable's Set up now
      builds no grid: 92.7 s and 2.41 GB to 12.8 s and 0.27 GB. The launcher's route at 17,000 × 80, before and after:
      pre-spec Set up 11.0 s / 0.23 GB and 14.0 s / 0.29 GB to 9.8 s / 0.22 GB and 13.8 s / 0.29 GB, Run 4.0 s / 0.21 GB
      both; bleed Set up 12.7 s to 13.2 s (0.28 GB), Run 21.3 s to 21.1 s (0.27 GB). 664 tests (23 new; the tests that
      read Check, the Log and the Confirmatory test read Record and New variables). 18 planted bugs added and 8 repointed, 1 retired (it planted into a sentence no tab shows now): 327 in all. Every planted bug whose test was rewritten or read through a rewritten helper was put back, each alone: 110 of 110 caught, 3 after their tests were strengthened.
      Departures: Found is always hidden today (every new-variable run confirms a saved shortlist); Record's rows wrap
      where a formula or label needs it, and a pair shares row heights; the tab keeps a short folding note; "p-value",
      never "luck". Not checked: real Excel.
- [x] **Goal 2 item 3: the lean pre-spec, a shortlist of inputs (27 Sep 2026; `origination-cube/docs/design.md` OC-49).**
      The pre-spec takes `outcome:` and `inputs:` (each input's column, bins and reference), beside strata,
      confidence and the two ranges; every line required, each input refused by its place. The one-column form
      is still read, as a shortlist of one: written either way, the same input gives the same New variables tab,
      number for number. **The allowance for many tests across the shortlist:** every candidate's groups against
      their own references are one family per set of loans, adjusted by Control's *Allowing for testing many
      pockets at once* (Benjamini-Hochberg by default), now asked of a new variable too; the table shows the
      allowed p-value (*p, allowed*), Holds up? and Still holds? read it, the tests in full keep every raw one,
      and the method note names the method once. New variables: a block of rows and a chart per candidate, and
      *Candidates · live* counting those that hold up. Start here and the launcher's last step count groups
      across candidates. The launcher fills Test it, Hold fixed and the outcome from the file. The line offered
      for missing strata, and `docs/prespec-shortlist-example.yaml`, leave strata as `[CONFIRM: ...]` (OC-13).
      The first book gains UTIL (x2.5 odds above 0.9, planted as the ratio is) and TENURE (nothing planted),
      each on a stream of its own: with FICO and CHANNEL held fixed and without, income ÷ sales' two cliffs and
      UTIL's hold up after the allowance; TENURE doesn't. Phase 4's loose ends: on a new-variable run Control's
      panel of levels is hidden and its method note names only worse at.
      - **Departure:** a shortlist of one allows for its own groups, where phase 4 read each group raw (a grid of
        one column is allowed for across its bands; otherwise the allowance would jump from none to eleven tests
        when a second input is added). Every odds ratio, raw p-value, count and excess is unchanged; with *No
        allowance* the verdicts are phase 4's exactly. On the goal's book one Still holds? at 90% sure moved, so
        `test_confirm_test.py`'s 90% check now reads either verdict.
      - Tests: 701 (37 new in `tests/test_shortlist.py`; 4 rewritten for the allowed p-value and the allowance
        being asked). Planted bugs: 20 added and 6 repointed (their lines were rewritten), 347 in all. Put back
        each alone: the 20 new, the 6 repointed and the 5 whose selectors reach a rewritten test, 31 of 31 caught.
      - Rendered through LibreOffice (three inputs, 20,000 loans): the tab reads as above. Not checked: real Excel.
- [x] **Goal 2 item 9: scouting, find then confirm in one Run (27 Sep 2026; `origination-cube/docs/design.md` OC-50).**
      The firm: scouting is *"to try and guess importance ... it should be wider"*, *"dates are for the scouting
      pipeline"* (OC-39), and each input tested *"once with and once without"* the held-fixed columns. Today a
      new-variable Run without a saved shortlist was refused; now it finds first. `scout.py` and `scout_tab.py`.
      - **Find**, on the development loans only (the first *Find on* share by origination date; the held-back
        loans' dates are read, nothing else): scikit-learn's random forest (200 trees, leaves of 40, seed 7) ranks
        every column ticked Test it and every new column by permutation importance (drop in AUC, cross-fitted in 3
        runs by date, 5 shuffles), with the candidates alone and with the Hold fixed columns in the forest, against
        a noise floor (the largest importance over at least 20 tries with the outcomes shuffled). Proposed: a number
        column above the floor in either forest whose shape bends. Bins from partial dependence over the column's
        own percentiles (a step of 25% of the curve's average, groups of at least 2%, at most 6), each edge where
        the forest itself split most, two figures; reference the median's group. Pairs with rank correlation 0.7 or
        more flagged.
      - **Write the pre-spec** (`<extract> - pre-spec.yaml`, the shortlist format; strata the Hold fixed columns,
        or `[CONFIRM: ...]` with none, which stops the Run after scouting with the file's line as what it waits
        for) and log it (fingerprint, date) before any held-back loan is tested. A file already there is
        confirmed as it stands, never written over; the Scouting tab lists where it differs from the proposal, and
        an edit after a held-back run is labelled as OC-47 built it.
      - **Confirm**: the saved-shortlist path, unchanged, its Found columns shown. **Scouting** tab (house style:
        title band, one folding note, tiles, the candidates ranked with both importances, bins, reference,
        partners, Proposed? and why; the held-fixed columns' own importance; the file; a curve and chart per
        proposed candidate). Record: *Scouting*, *Scouting held back*, *Scouting's pre-spec*, *Tests: scouting*.
      - **scikit-learn optional:** `deps.OPTIONAL`, the `scout` extra; the launcher offers *Install scikit-learn*
        where finding needs it; without it finding is refused by its Control cell in words and a saved shortlist
        still confirms (tested with it simulated missing, as test_perm does numpy). CI installs `.[test,scout]`
        in both origination-cube jobs (S14).
      - **Repeatable:** same extract, same forests, shortlist and file: the 17,000 × 80 file's fingerprint was
        a32fe0713bff in two separate processes. scikit-learn's `predict_proba` sums the trees in thread order,
        which moved the partial dependence in its 17th figure between two Runs; the votes are summed in the trees'
        own order here.
      - **Of scout-vs-measure.py:** kept the forest, the AUC-drop permutation importance, partial dependence and the
        median reference; changed 400 trees / 10 shuffles / one row-position split to 200 / 5 / cross-fitted by date
        (time; lower noise), hand-typed edges to found ones, two arrays to one extract split by date; added the
        noise floor; dropped `make_book`, the straight-line regression (kept in the doc as B7's example) and the
        frozen forest's holdout AUC (B7: development only). The table is in OC-50.
      - **Found and fixed on the way:** a new-variable Run with nothing held fixed, or a number held and no
        category, was refused by the bleed's "Nothing is left to cut" (config.py, engine.py); over values from
        0.03, bins [0.1, 2] named the lowest group "0.0 - 0.0" (now "0.03 - 0.09", fractional edges only), and the
        pre-spec now recognises a group named from the run's range.
      - **On the first book with filler** (12,000 loans in the tests, 20,000 rendered): income ÷ sales and UTIL
        rank first and are proposed, TENURE and five filler columns (a correlated pair and a category among them)
        aren't; bins 0.9 for UTIL and 0.1 / 0.099 and 2 for income ÷ sales. At 20,000, confirmed on the 5,993
        held back: UTIL above 0.9 2.08x; income ÷ sales from 2.00 3.07x (2.86x FICO and CHANNEL held fixed); below
        0.099 1.68x, not holding up after the allowance.
      - **Speed** at 17,000 × 80 with 40 candidates, under a 4 GB limit: the Run 64.4 s, scouting 59.3 s of it,
        0.56 GB at its peak (a confirmation-only Run is 4.5 s). Rendered through LibreOffice: the Scouting and New
        variables tabs read as above. Not checked: real Excel.
      - Tests: 719 (18 new in `tests/test_scout.py`; 2 in `test_run_kind.py` rewritten: scouting is no longer
        refused as not built, and its option says what it does). Planted bugs: 20 added, 367 in all; each put back
        alone, 20 of 20 caught, and the 1 whose selector reaches a rewritten test (*scouting runs*) caught.
      - **Departures:** noise floor over at least 20 tries, not 30 (time); proposed on either forest, not both; a
        category ranked, never proposed; a file already beside the workbook is never written over (delete it to
        re-propose); the ranking cross-fitted in 3 runs by date where the scope planned one 70 / 30 split.
- [x] **Goal 3 item 1: the rename sweep (27 Sep 2026).** The firm, 26 Sep: *"let's call it the PocketBook"*.
      The folder moved `origination-cube/` → `pocketbook/` (git mv, history kept); the package
      `origination_cube` → `pocketbook`; the command `cube` → `pocketbook`; `Origination Cube.pyw` →
      `PocketBook.pyw` (its `__main__` guard and `freeze_support()` kept); `$CUBE_MEMORY` →
      `$POCKETBOOK_MEMORY`; `~/.origination-cube/` → `~/.pocketbook/` (new `places.py`). CI's pytest matrix
      entry and the four-part mutation job now name `pocketbook`.
      - **Still read under the old names:** `$CUBE_MEMORY` when the new variable is unset; memory and the
        launcher's last choices from `~/.origination-cube/` while `~/.pocketbook/` has none (the next save writes
        the new folder, the old file is left alone); an installed `origination-cube` package's declared minimums;
        a `- Origination Cube.xlsx` workbook (Set up carries its answers over, now tested; picked as the extract
        it is refused, as before).
      - **Left as written:** entries in this section dated before the move; the dated walk-throughs, audit,
        final check, for-test-design write-up and redesign folder; canon's citation of the cube's commit; and
        the shuffle test's seed text (`perm.BASE`), which names the old folder and would move every p-value.
      - Tests: 723 (4 new). Planted bugs: 4 added, 371 in all; those 4 and 6 older ones put back alone from the
        new folder, 10 of 10 caught.
- [x] **Goal 3 item 2: a walk-through as the analyst (27 Sep 2026).** canon's walk, on `970b3647` frozen in
      scratch: the real Tk window under xvfb (Python 3.12, a fresh venv, so **Install now** and **Install
      scikit-learn** ran pip for real), the workbook read through LibreOffice, both run kinds on the synthetic
      book (8,000 loans), and the refusals (Run before answering, workbook open, add-ons missing, no program to
      open a workbook, a tie-out forced to fail). Then walked a second time on the fixed build.
      Deliverables in `pocketbook/docs/walkthrough/2026-09-27/`: `PROCEDURE-pocketbook-analyst.pdf` (one file,
      30 pages, a route picture, 32 numbered steps and a refusals table, every picture embedded; `.html` beside
      it, `.md` the source), `WALKTHROUGH-DEFECTS.md`, the pictures, and `driver/` (the scripts).
      - **12 defects, none caught by the 723 tests or the 371 planted bugs.** Fixed 11: (1, high) a pre-spec
        edited after the held-back run read "Follows the pre-spec: Yes" in green on the window and Start here,
        and on a scout-first run "Yes" couldn't be anything else. Now "Changed, after a held-back run" in red,
        or "Written now". (12, high, found on the second run) installing scikit-learn after the add-ons in one
        window never finished: the pip loop set the gone black bar's line and died. (2) A failed Run, a failed
        tie-out included, read "1 answer needed before Run". (3) Open at… failed silently with no program for
        .xlsx. (4) Install success in refusal red. (5) Answers needed out of order. (6) Record named the measures
        differently from the result tabs. (7) The new-variable tile didn't name its column, and the tiles now
        grow to their words. (8) Scouting's curve to four decimals. (9) "while the add-on installs". (11) Start
        here's Loans tested ran into the next tile.
      - **Left for the firm (A to K in the defects file, each with a recommendation):** Changes waiting for a
        Run doesn't count launcher choices; the tie-out tile can't show a failure; no name for "more
        charge-offs, kept the same"; Start here's largest list after a live change; three counts for one job;
        window jargon; Control's Comes to before the first Run; Look's outcome columns; Start here's held-fixed
        odds unlabelled; the finished screen shows none of the Run's lines; a print-title repeat.
      - Tests: 735 (12 new in `tests/test_walk_2026_09_27.py`, 2 of them window tests that skip without a
        display; 5 updated). Planted bugs: 14 added, each put back alone and caught; 385 in all.
- [x] **Goal 3 item 3: the bank-machine checklist (27 Sep 2026).** `pocketbook/docs/BANK-MACHINE-CHECKLIST.md`,
      with `.html` and `.pdf` beside it (16 pages, pictures embedded; built by `docs/bank-machine/build.py`).
      Seven parts: before you go, install and first open, a dry run on the practice book with the numbers to
      compare, Excel's live parts cell by cell, speed and the cores, the first real extract (what it needs,
      what to look at first, what never leaves the bank), what to send back; then a symptom table.
      - **Made, not prescribed:** `tools/bank_kit.py` writes `PocketBook.zip` (the window, its code, both
        install files, the checklist, the procedure, and `VERSION.txt` naming the commit, since the bank has no
        git) and, with `--add-ons`, `PocketBook add-ons.zip`: the Windows wheels for Python 3.11 to 3.14
        (233 MB; about 60 MB for one version). pip fetched them through this container's proxy.
        `Install add-ons from this folder.bat` installs from them with `--user --no-index --find-links`.
        The zip, not a wheel: a wheel can't carry `PocketBook.pyw`.
      - **Verified here:** the practice and speed books made by the checklist's own commands on 3.11 and 3.12
        (same MD5s); the dry run with the checklist's answers gave every number in its table (4 of 81,
        $3,094,991, 702 of 702, the four largest; 8.1 s on 4 cores), also on a fresh Python 3.12 with the
        add-ons installed offline from the kit (numpy 2.5.3, newer than CI's). 40,000 loans: 30.6 s on 4
        cores, 84.5 s on 1, same answer. LibreOffice: no error value on any visible tab; the live change
        (2 of 81, $1,922,025), the waiting banner's four places, the dropdown captions, and Look's dashed
        lines (the picture in the checklist). The window opened from the unzipped kit, with and without add-ons.
      - **Marked "check this", never seen:** everything in Excel (repair prompt, Find in hidden tabs, the
        validation message, the lock the open-workbook bar looks for, Look's lines on Excel's second axis, the
        outline fold, the charts, Run on a workbook Excel saved); pip through the bank's proxy; the Windows-only
        commands (`tar -xf` on a zip, `certutil`, `ren`, the .bat files), checked by reading.
      - **Found on the way:** the practice book's answers are remembered (`~/.pocketbook/memory.yaml`) and
        would be suggested for a real extract with the same column names; the checklist moves the file aside
        before Part 6. Not changed in code.
      - Tests: `tests/test_bank_checklist.py`, 5: the checklist's commands make the books whose MD5 it prints,
        the kit holds what it lists and no data files, the add-ons agree everywhere, the HTML is current, and
        every cell Part 4 names holds what it says. Two edits to the checklist (an MD5, a cell) turned it red.
- **The firm's calls, 26 Sep 2026 (evening).**
  - **Name: PocketBook.** *"i want to change the name of this... let's call it the PocketBook"*. What
    the analyst sees is renamed with the redesign; folder and package names in one sweep after the
    running agents land; workbooks under the old name still recognised.
  - **"Luck" is out.** *"i don't like the luck term, unless that's truly standard terminology"*. It is
    not, and "chance it's luck" misstates a p-value. Recommended and adopted unless the firm objects:
    the header stays **p-value**, explained once in the tab's method note; Worse? carries the verdict.
  - **Look: live bars and range** (*"If truly cheap- yes"*), plus the **mean** beside the median.
    Run stores fine counts per column in a hidden sheet; a Bars dropdown and a from/to range regroup
    them by formula. Phase 2.
  - **Found: Run does not scale.** 17,000 loans × 80 columns (70 filler), FICO in 3 bands, split by
    REV_DEBT: Set up 155 s; Run still going at 10 min and 12 GB, stopped. 8,000 × 10 runs in about a
    minute. To be profiled and fixed before the redesign phases; then time the firm's two cases
    (the bleed with 3 bands on 4 dimensions, and a pre-spec test) on that extract.
- **Speed, diagnosed (26 Sep 2026).** The 12 GB run was the test's own doing: "Cut by it?" defaults
  to Yes (`book.py:390`), so all 48 number and 26 category filler columns were cut, 1,248 grids. The
  redesign's launcher step (choose what to cut) removes that default. Realistic cases at 17,000 × 80:
  - bleed, 4 number columns in 8–10 bands, 2 segments, a split: Set up 158 s, Run 84 s, 0.35 GB;
  - pre-spec, 5-input shortlist: 162 s + 161 s (two Set ups) + 58 s.
  Causes: Set up's date detection (84%: every pattern tried on every value, each column checked five
  times) and Run's shuffle test (53 s of 75 s; linear in loans × groupings × rates × shuffles).
  Fixing now: date detection and repeated parsing (measured 158 s → 16 s). With the phase 2 Look
  rewrite: one workbook load and save per Run, Look not redrawn at Run. Expected after both: bleed
  about 75 s, pre-spec about 1.4 min. Open with the firm: spread the shuffles over the machine's cores
  (about 3× faster, p-values move within the shuffle test's own error), and whether a new-variable
  run needs the bleed grids at all.
- [x] **Goal 2 item 1 finished: the cliffs in the second book (26 Sep 2026).** The auto book in
      `tests/test_generic.py`, dated with US-style contract dates, carries income ÷ sales cliffs of
      its own (x3 below 0.05, x2.5 from 1.50, planted on each loan's odds). A "Test from a pre-spec"
      run finds both on development and confirms both on the holdout; the same loans with no cliff
      are not confirmed, though the whole book reads a difference in the lowest group (the worst
      dealer crowds it). Two planted bugs, both caught: dates read only year-month-day (the first
      book's goal tests pass it) and the pockets forgotten. 544 tests, 213 planted bugs.
- **Set up's reading, fixed (26 Sep 2026).** A regex gate per date pattern before strptime (looser than
  strptime's own, held to it over 22,750 generated values), each column's facts worked out once and
  handed to classify, suggest, review and Look, and settings.yaml read once per Set up or Run. Bleed at
  17,000 × 80 under a 4 GB limit: Set up 159.5 s → 9.5 s; Run 78.6 s → 75.8 s (the shuffle test is
  untouched); the workbook the same cell for cell but the time and path. `tests/test_set_up_once.py`,
  12 planted bugs in `tools/mutation_check.py`.
- **A new-variable run skips the bleed grids** (the firm, 26 Sep 2026: *"Yes. Seems obvious I think.
  They have entirely different outputs generally"*). Queued behind redesign phase 2 (same Run code).
- **A new-variable run skips the bleed, built (26 Sep 2026; `origination-cube/docs/design.md` OC-42).**
  A "Test from a pre-spec" Run builds no grid, no three-way or split grid, and no shuffle test. It writes
  the Confirmatory test, Check and the Log. The bleed's six tabs are taken off if an earlier bleed Run left
  them, and Check's "Bleed tabs" line says so where the tie-outs were. Start here's *What the last Run
  found* and the launcher's last step show the confirmation: the groups worse than the reference on the
  holdout, their share of its bad loans, and whether the run followed the pre-spec. Start here's count
  follows the confidence on Control.
  - Pre-spec Run at 17,000 × 80 under a 4 GB limit: 23.4 s → 4.5 s (12 grids and 1 shuffle test → 0
    and 0).
  - The bleed Run is unchanged: 136,762 of 136,762 cell values match before and after on the synthetic
    book, except the extract's path.
  - `tests/test_new_variable_run.py` (7 tests). 9 planted bugs, each run alone, all caught. Two older
    planted bugs were retired because their lines are now reachable only by a bleed Run, which always
    has the dollar columns.
  - Two existing tests read Prevalence on a new-variable Run. They now read the Confirmatory test tab.
  - **Open:** Control still asks, and suggests, the fewest loans and the loss lines for a new variable.
    Those suggestions came from the bleed's grids, so on such a Run the loss lines fall back to the usual
    values.
- **Shuffle test across cores: approved** (the firm, 26 Sep 2026: *"I'm good with plan"*); built (below). Proposed: each shuffle seeded from its own
  number, so the result is the same on any number of cores and every run; the p-values move once,
  within the shuffle count's own error (about ±0.002 near 0.03 at 10,000 shuffles).
- **Shuffle test across cores, built (26 Sep 2026; `origination-cube/docs/design.md` OC-41).** Shuffle i
  draws from its own stream (the i-th child of the run's seed); the shuffles go to worker processes in
  runs of consecutive shuffles, started the Windows way ("spawn") everywhere, and the counts are added
  in order. Every count, answer and kept gap is bit for bit the same on 1, 2, 3 and 4 workers.
  `perm.run` on the 17,000-loan bleed run, 10,000 shuffles, 4 GB limit: 53.6 s before, 20.9 s on this
  container's 4 cores (20.5 s on 3); about 70 MB per worker. The p-values moved once: on the synthetic
  books the largest of 465 moved 0.0149 (6,145 → 5,996 of 10,000), about 2 standard errors, and no
  allowed-for p-value crossed 0.05. `Origination Cube.pyw` now opens its window only as the program,
  never in a worker. 7 planted bugs in `tools/mutation_check.py`, all caught; 586 tests, 258 planted bugs.
- **The firm's answers on the walk-through's design calls (27 Sep 2026, docket U5pHCYek9H7hqehzUvqs8M).**
  Yes to A (launcher changes count as waiting), C ("Losing more, profit holding"), E (one count), F (plain
  words on the launcher), G (Comes to shows the value), I (say FICO held fixed), J (the Run's first lines
  on the finished screen), K (print titles). "Earned before losses" wording: *"Fine for now"*.
  - **B, the tie-out tile:** *"I specifically have asked and keep asking for this kind for wording to be
    considered slop. It is the slowest way to communicate a check figure. If it didn't tie out what would
    happen now"*. A failed tie-out stops the Run and writes no results, so a tile saying it tied is empty:
    it comes off. The check stays on Record.
  - **D, Start here's top five:** *"I don't understand this like at all like meaning it's slop"*. Rebuilt
    live instead: the list is picked by formula from the current verdicts, like the result tabs.
  - **H, Look on outcome columns:** *"Not sure why we even have the info? Like obviously we didn't band
    them?"* Look shows only columns that can be cut into bands; outcome columns come off it.
- **The firm's answers on the walk-through's design calls, built (27 Sep 2026).** All eleven, A to K, and
  tenet T2 (a check figure is shown only where it can fail). `pocketbook/docs/walkthrough/2026-09-27/
  WALKTHROUGH-DEFECTS.md` marks each resolved with what changed.
  - **A:** each Run keeps what the launcher chose on `_used`; *Chosen in the launcher* has a Status, and Next
    changing a row makes it wait: Start here counts it and the pink line names it (*Cut into bands: FICO,
    ORIG_BAL → FICO (launcher)*). A new kind of run is one change: the first build counted 9 on the walk's
    switch to Test new variables, every row that changes with it.
  - **B and T2:** the tie-out tile is off the finished screen and Start here, with no sentence in its place.
    The sweep T2 asked for found three more that could only read fine: the Run's first line ("N tie-out
    checks agree", on the Log and in the launcher's lines), Record's "702 of 702 agree" (now "702: every grid
    adds up to the book", the one place the count stays), and, once D was live, Start here's Worse? and
    Material? columns on its largest pockets (every row shown is both). Left as it was: the command line's
    "Tie-out: N of N checks agree" (`cli.py`), which no analyst screen shows.
  - **C:** *Losing more, profit holding* (charge-offs worse and real, kept gap not significant). The firm's
    Test 4 at 3% uplift reads it now; its test said "nothing read together" and was updated.
  - **D:** Start here's list is picked live, as Pockets' Show dropdown picks: `_found` holds every pocket the
    Run found losing more than its share, largest dollars first, with live Worse? and Material? from
    `_pockets` and a running count; row k is the first whose count reaches k. After worse at goes to 2 times
    it lists 2 pockets, both worse (the walk's four rows, two reading No).
  - **E:** one count, the refusal's: Next says *9 answers needed before Run, on Control and Columns*; Start
    here's *Answers needed before Run* counts live the refusal's way; *Columns to confirm* and *7 columns to
    look at first* are gone.
  - **F:** a slate line under each term the window uses first (GCO dollars, RANR dollars, a grid, five
    measures, worse at and better at with the worked-out multiple, scouting), 15 words or fewer, no term of
    art in the explanation.
  - **G:** Comes to shows the worked-out multiple before the first Run (1.34×, 0.75× on the walk's book),
    never the option's words; materiality's dollar line is blank until a Run has the book's losses.
  - **H:** Look draws only columns that can be cut into bands: FICO, ORIG_BAL, REV_DEBT.
  - **I:** *× 11,000 - 14,999's odds, FICO held fixed*. **J:** the Run's first two lines under the finished
    tiles. **K:** no print titles on Scouting.
  - Tests: 12 added (11 in `tests/test_firm_answers_2026_09_27.py`, 1 in `test_scout.py`); 752 collected, from
    740. 1 of them needs a display: under xvfb with Python 3.12 it passes, with the other window tests (69 of
    69 in the four window-test files). 9 existing tests rewritten for the new wording or layout (test_answer_tabs 2, test_book 1, test_book_results 3, test_look 2, test_profit 1).
  - Planted bugs: 20 added to `tools/mutation_check.py`, each run alone, 20 caught; 405 in all. The 10
    existing planted bugs whose selectors match a rewritten test were run again: 10 of 10 caught.
  - The procedure's changed pictures (22 of them, and a new one for step 25) were taken again on the fixed build,
    scripted this time (`driver/walk_answers.py`, `driver/shots_answers.py`), and the PDF rebuilt. Before and
    after for B, D and H: `design-{B,D,H}-{before,after}.png`. The bank checklist's numbers that moved
    (the Run's tiles, Start here's list after worse at 2 times, Comes to, Look) are updated and its PDF rebuilt.
  - Full suite (Python 3.11, no display, LibreOffice present): `747 passed, 5 skipped in 1899.63s (0:31:39)`. The 5 skipped are the window tests.
    The one new window test was also planted by hand under xvfb (the Run's lines not packed): it went red.
- **Not checked:** real Excel, a real extract, and the bank machine
  (Python and the add-ons installed, and .pyw files opening with Python).
- **The public-data rehearsal (29 Sep 2026, branch `claude/pocketbook-public-rehearsal`; the firm: *"1 and 4
  are good. Use workflow and whatever you need honestly"*).** PocketBook run end to end, headlessly, through the
  workbook route on public loans: the SBA 7(a) FOIA file FY2000-09 (604,573 loans with an outcome), the JSE paper's
  SBAnational.csv (897,167) and LendingClub 36-month loans of 2008-11 (30,931). Report:
  `pocketbook/docs/rehearsal-public-data-2026-09.md` (corrected after two reviews the same day; its section 6 lists
  every change); data (outside git, can be purged): `C:\Users\ajish\SATC-evidence\public-loans-2026-09-29\`.
  - **Read first: on both SBA files the term depends on the outcome.** 86.6% of SBAnational's paid loans have a
    whole-year term (a multiple of 12 months) against 10.6% of its charged-off loans; FOIA 82.0% against 8.9%. So
    REAL_ESTATE (term 240+), RECESSION (disbursement + term), the Term bands, the confirmatory "term under 60" figure
    and scouting's TermInMonths (AUC 0.93/0.92) are circular: PocketBook reproduces the paper's arithmetic, which
    inherits the same dependence, and none of it is evidence of a known effect. The builder's narrower check (term
    equal to months to charge-off, 0.8%) missed it. The converter's manifest now counts it (`term_check`).
  - **Tools:** `tools/public_extract.py` (raw file to extract and a manifest of every filter and derived column,
    each labelled native / constructed / rehearsal approximation, and `after_booking` where the value is not known
    when the loan is booked; judgments refuse rather than default), `tools/rehearse.py` (Set up, answers from a
    file, Run, timings, peak memory, a workbook check that can fail), `tools/rehearsal_effects.py`,
    `tools/rehearsal_answer_key.py` (reads the extracts, so independent of PocketBook but not of the converter),
    `tools/rehearsal_timing.py`. 26 tests on made-up rows (`tests/test_public_extract.py`).
  - **Defects fixed, each with a regression test (`tests/test_rehearsal_2026_09_29.py`, 9 tests) and a planted bug,
    4 of 4 caught:** (1) a category limit off the launcher's list (many_values=60 for State) written where only a
    listed option is read: the Run refused on the launcher's own row and reading back gave 50; (2) the confirmatory
    test's conditional likelihood multiplied every coefficient out: 191 s for one evaluation of a 217,800-loan pocket,
    the pre-registered test stopped after 10.5 minutes in its first fit; now 0.25 s (log-likelihood equal to the old
    code to 1e-12, gradient 1e-10, Hessian 1e-9), and a structural test so the planted bug is caught without a
    stopwatch; (3) scikit-learn installed but blocked at first load by Smart App Control crashed a scouting Run; now
    refused in words. The block cleared later and was not tied to a version.
  - **Known effects:** on SBAnational every 2-digit NAICS rate rounds to the paper's Table 3 and recession-Y is 31.21%
    (paper 31.21); other rates differ by up to 0.35 points; Florida highest; smaller loans worse on the margins.
    Real estate and recession reproduce the paper's arithmetic only (the term). The "recession is term mix" finding
    is **withdrawn**: both columns come from the term, and the band that went the other way was not quoted.
    LendingClub: the bleed Run completed; figures derived from LendingClub data are not published in this
    repository (the firm, 4 Oct 2026). Pre-registered on the FOIA holdout, five directions: larger loans better (2 of 2) held;
    25,000-49,999 worse held on the workbook's rule at 1.09x, under the 1.25x line; the smallest loans worse and
    240 months and up better missed, for reasons not settled (EXEMPT loans left out; the term).
  - **Also fixed after review:** `tools/mutation_check.py` counted any pytest exit but 0 or 5 as a catch, so errors
    (a temp folder pytest could not write) read as caught; now only a failed test is, errors are settled by a run
    without the bug, and all-skipped reads NOT CHECKED (6 tests). `--files` runs only the named files' planted bugs.
    `rehearsal_effects.py` says when a pocket alone in its band was judged against the book.
  - **Waiting on the firm:** SBA's RANR stand-in (revenue set to zero: profit tabs not evidence); LendingClub-derived
    figures already on this public repository's branch (answered 4 Oct 2026: dropped); how to read the live cells (LibreOffice
    or Excel; Excel was not opened); the confirmatory "Excess $" measured against the share of loans (350,000-and-up
    reads +$6.06bn at odds 0.79); equal-loan bands leaving a sliver (TermInMonths 82-83, 6,351 loans); whether the
    bank's machine runs application control; rerun the SBA pre-spec and scouting without the term, or leave them as
    software exercises.
  - **The suite on Windows:** first read 2 failed, 703 passed, 115 skipped. Both failures were fixed in the tests
    and the checker: `tools/mutation_check.py` and its test read files in cp1252, so four planted bugs could not
    be found here; the checklist test's symlink is refused without Developer Mode, so it now copies `src`. On the
    final code (origin/main ab7ddde0 merged in, fresh venv, scikit-learn 1.9.1): **1 failed, 734 passed, 115 skipped
    (all LibreOffice) of 850**. The failure is main's #405 window test (the Choose tests table 215 px high, its rows
    needing 248 at 1180 x 628); it fails the same way on main's own code here, and is left to the launcher work.
  - **Planted bugs:** on the final code, the 76 in control, kgroups, scout and confirmatory (the 4 new ones
    included): 68 caught, each by a failed test; 8 NOT CHECKED (their only tests need LibreOffice). 459 in all; the
    other 383 not run here (CI ran all 459).
  - **CI on the draft pull request (#407, e149a169):** every job passed; `pytest (pocketbook)` 843 passed, 7
    skipped of 850 (LibreOffice present), and the four mutation shards 459 of 459 caught.
  - **Not checked here:** any recalculation of the workbooks on this machine (CI's LibreOffice did), the Tk
    launcher driven by hand, a real extract, the bank machine.
- **The public-data rehearsal revived (3-4 Oct 2026, same branch, draft #407; the firm: *"Revive"*).** origin/main
  at 6a9aaafa merged in (no conflicts) and the rehearsal rerun on the merged code in a Linux sandbox (4 cores, shared
  with other sessions' suites). Report: section 7 of `pocketbook/docs/rehearsal-public-data-2026-09.md`.
  - **The three fixes of 29 Sep:** none had been made on main another way (`write_choices` still wrote an off-list
    limit into the pick cell; `kgroups.py` unchanged since the merge base; `scout.run` still did not load
    scikit-learn first). All kept, with their 9 tests and 4 planted bugs. Fix 1 was met again (`many_values: 60`, the
    State grids ran); fix 2 carried a confirmatory fit over pockets of up to 459,927 loans in 3 min 34 s.
  - **Data:** the SBA FOIA file could not be downloaded (the sandbox's proxy refuses data.sba.gov), so the FOIA bleed,
    pre-spec and scouting Runs were not repeated. SBAnational (a GitHub copy of Kaggle's file) and LendingClub's own
    `LoanStats3a.csv` gave the same extracts as 29 Sep (897,167 and 30,931 loans), and on SBAnational the answer key
    matches to the hundredth. The converter now takes LendingClub's own file: a notes line above the header, every id blank
    (`--row-key`), no `fico_range_low` (`--absent`), and rates written with a % sign (the sign taken off and counted).
  - **Defects fixed (2), each with tests (`tests/test_rehearsal_2026_10_03.py`, 4) and a planted bug, 2 of 2
    caught:** (4) a band column with no value readable as a number (revol_util written with a % sign) was refused as a column
    the extract does not have, while naming it among the extract's columns, and said to press Set up again; now
    refused as unreadable, with counts by reason and the two fixes; (5) a held-back p-value of 2.5e-315 written into
    New variables' "What it found" formula as a literal calculated to #VALUE! in LibreOffice; `live.num` now writes
    a subnormal number as 0.0.
  - **Runs:** SBAnational bleed (897,167 loans, 14 grids): Set up 129-131 s, Run 1,425-1,895 s, 3.6 GB.
    LendingClub bleed (30,931, 30 grids): Set up 7 s, Run 72-85 s. Scouting on SBAnational in place of FOIA
    (NewExist held fixed, term left out; a software exercise): Run 5,141 s, 81 minutes of it scouting, 7.1 GB; all
    three candidates proposed and held up on 270,199 held-back loans. Every workbook calculated with LibreOffice: no
    error value on a visible tab except defect 5's line; Pockets' calculated Worse? equals the Python reading on
    both (204 worse on SBAnational). The 29 Sep SBAnational effects reproduce pocket for pocket on the loan-size grid.
  - **Recorded, not changed:** a pocket whose rest of band has no bad loans gets no multiple, so Worse?
    is blank while Material? reads Yes (one LendingClub row); two Pockets rows can carry the same label when a Y/N
    segment comes from two grids; scouting at 627,000 development loans spends most of 81 minutes on the noise
    floor; decision 4 (Excess $ against the share of loans) reproduces on SBAnational (+$4.06bn on a 0.50x group).
  - **Suite:** 1,081 passed, 14 skipped (tkinter absent), 0 failed, in 81 min, on c3d77726; after defect 5, the
    112 tests touching `live.num` and the confirmatory tab passed. 669 planted bugs, each original text found
    exactly once.
  - **Still open:** decisions 1 and 4 to 7 of the report; decision 3 is answered for SBAnational and LendingClub
    (LibreOffice). Not checked: the FOIA file, real Excel, the Tk launcher, the CLI on full files.
- **The firm, 4 Oct 2026, on publishing LendingClub-derived figures in this public repository: *"Drop LendingClub
  figures"*.** Decision 2 of the report answered. The code fixes and the SBA results are kept; LendingClub-derived
  rates and figures were taken out of the report, this section and the README, leaving only that the file ran
  (30,931 loans after extraction, Set up and Run times, completed) and the defects it surfaced and how they were
  fixed. The converter's LendingClub tests already used made-up rows; their two percent-text example values were
  changed to plainly synthetic ones. Earlier commits on the branch still carry the figures; history was not
  rewritten.

### Held for the firm's final decision (raised 29 Sep 2026)

**Items 2 to 6 built the same day.** The firm: *"In order to correctly test this I guess these things need to be
fixed now so go ahead fix the changes"*. Items 1 and 7 stay open: neither stops a test at the bank. What was built:
- **2:** the two limits read *Number columns: ... more is cut into bands* and *Text columns: ... (text is never cut
  into bands)*, in the launcher and on Control.
- **3:** a tick repaints its own boxes, the outcome line and the summary in place; the table keeps its scroll.
- **4:** *All · None* under Test it (new variable only; All leaves Hold fixed as it is; a saved shortlist locks it).
- **5:** the window opens at the screen's size (1180 x 628 on a 1366 x 768 laptop, up to 1180 x 860), the table
  takes the height left and scrolls only when it must, and the word columns take the spare width.
- **6:** nothing is picked as the outcome, in either run kind. An *Outcome* list above the table (and the Outcome
  column in Test new variables) offers every column of 0s and 1s, each described by what it holds (*Yes/no · 1 on
  10.1% of loans*), never as a guess. Picking one asks first: *"Use EVER GCO as the outcome? 1 means the loan went
  bad: 304 loans (10.1%). 0 means it didn't: 2,696. Nothing else."* Next stays off until one is confirmed. Set up
  marks the pick on Columns and any other column marked the outcome goes back to a category. Names are read as
  words (`meanings.words`): a two-letter hint must be a whole word, three to five must begin or end one; `gco` and
  `ever` added to the outcome's hints; a tie for the outcome, or an outcome only its values suggest, is left to
  the analyst. A saved shortlist's outcome is asked about too.
- Tests: `tests/test_firm_answers_2026_09_29.py` (10; 1 needs a display); 6 existing tests changed to pick and
  confirm the outcome. Planted bugs: 12 added to `tools/mutation_check.py`.
- Not redone: the procedure's and the checklist's pictures of Choose tests show the old screen.
- **Later the same day, at the bank** (the firm set up on the bank's file):
  - *All · None* under Cut into bands and Segment by too (the firm: "Yes"). The split is never ticked by All.
  - Columns shows only the columns the Run uses; the rest are hidden rows, not asked about and not counted in
    Start here's *Odd values to answer* (the firm: *"considering the reason we reorganized the entire set up to
    allow you to pick the workbook first ... Why would we ever want to make it appear?"*). Set up with nothing
    picked still shows every column.
  - Look's charts lose their "Loans" axis title, which Excel drew over the axis's numbers (*"The axis title is
    out of place"*; LibreOffice had placed it clear).
  - Tests: 3 more in `tests/test_firm_answers_2026_09_29.py`; 5 planted bugs, all caught.
  - **A category splits the pockets too.** The firm: *"I kind of figured I'd be able to see a view with system
    flag and origination FICO and asset segment somehow"* ... *"Like I know it can't break down too far but can we
    not make something work?"* Split by now offers a radio on category rows as well as number rows (still one
    column, or none); picking a category unticks it from Segment by, and ticking it as a segment again stops the
    split. A category with more than 6 values (blanks aside; `choices.SPLIT_MOST_VALUES`) is refused in the same
    words in the launcher (Next stays off) and at the Run: *"REGION has 7 values. A category can split the pockets
    by 6 values at most: with more, each pocket's parts are too thin to read. ..."*. The engine already built the
    per-value layers (Grids' "FICO x ASSET_CLASS / SYS_FLAG", columns "ASSET_CLASS 4 · Y"; Pockets' split list;
    the tie-outs); what was missing was every comparison. Now each value is set against the rest of its pocket
    (the other value, when there are two) by exactly the halves' machinery: per pocket, the z test for bad loans
    and the within-pocket shuffle for the dollar rates; pooled, actual against expected with its range, and for
    bad loans the Mantel-Haenszel odds, CMH and Cochran's Q. The allowance for many tests takes every value and
    pocket of a grid and measure as one family, and the pooled p-values across the values. New, for bad loans
    only: whether the values differ at all, B3's K-group Mantel-Haenszel test on K - 1 degrees of freedom
    (`kgroups.association`, docs/statistics.md), which with two values is CMH's chi-square (a test holds them
    equal). The Split tab's Grid dropdown picks a grid and a value ("FICO x ASSET_CLASS · SYS_FLAG Y vs rest").
    **Left out, and said on the tab:** the partner chip (how a category moves with a band column isn't worked
    out; the note says a gap may partly be a column the grid doesn't hold); and the differ-at-all test for the
    dollar measures (no test of more than two groups at once exists here for a dollar rate). Paid, cost, kept and
    Start here's five largest read the two-way grids only, for a number split too, so nothing changed there.
    Record: the Split row, the Tests row and the Families row say what a category split does.
    Tests: 5 more in `tests/test_firm_answers_2026_09_29.py`; 9 planted bugs (and one repointed).
  - **One cell of a grid read out in words.** The firm: *"It would be useful to be able to maybe select a
    particular line and say I want this as an example and it fills in the band saying what versus book means
    what versus band means and what loans means ... the measures should be constant from run to run the grid
    may change"*. Grids has a **Row** and a **Column** dropdown beside Grid and Measure; their lists are the
    picked grid's own labels (hidden cells, offered by `OFFSET` over as many as there are), and they open on
    the first pocket with a rate. **What one cell says**, under the blocks, reads that pocket from the same
    cells the blocks show: its name, the rate, vs the book, vs rest of band, the loans (and its band's All), and
    the colour each comparison takes on the heat scale. The sentences are fixed by measure (`results.SAY`),
    so only names and numbers change. A blank says why: *alone in its band* when nothing else in the row has
    loans, otherwise *fewer losses than the minimum (N losses)*; the note under the blocks now gives both.
    A Row or Column left from another grid asks to be picked again rather than read a wrong cell.
    **Said as it is, not as asked:** vs the book is the pocket over the *whole* book (these loans included),
    as the block has always shown it, so it reads "the whole book", not "every other loan in the book"; and
    the colour is the size of the gap only (the block's heat has no test in it), so it says that rather than
    "unlikely to be chance".
    Tests: 3 more in `tests/test_firm_answers_2026_09_29.py`; 4 planted bugs, all caught.

The firm, 29 Sep 2026: *"make sure you're noting all of these so that we can go over them later for final
decision."* Each item: what is true now, what would change it, and the recommendation. Nothing below has been
changed in the code.

1. **Columns that arrive already banded** (a `FICO_BAND` of "620 - 659", a score code 1 to 7). The firm:
   *"Do we have a solution for when the metrics already have banded units that we decided to just try and
   use?"* What happens depends on how the bands are written (checked on a made-up file, 29 Sep; corrected
   after Codex on #405 found the first version of this item wrong):
   - **Band text** ("620 - 659"): read as a category. In a bleed run that is Segment by only, never Cut into
     bands, and Choose tests needs one band column, so a book with FICO only as text bands can't have a FICO
     band x segment grid. In a new-variable run scouting skips it ("a category", never proposed); it can
     still be tested or held fixed, value by value, with no trend reading. Whether the values sort in band
     order ("<600" before "600 - 619") was not checked.
   - **Number codes with a score-like name** (FICO_BAND, GRADE, RISK_TIER): read as a score ("Other score")
     and offered under Cut into bands, where they are cut again into PocketBook's own bands, not the bank's,
     unless the edges are typed on Columns at each code.
   - **Number codes with any other name**: 12 values or fewer is a category, as for band text.
   Workaround now: if the raw number is in the extract, cut it on Columns at the bank's own edges.
   **Recommended:** a *Treat as: bands, in this order* answer on Columns, so such a column is used as the
   bank's bands, can be the band axis, and its order feeds the trend test.
2. **The two "how columns are recognised" settings read like one scale.** The firm: *"it seems odd to say
   anything above 12 is not something we would have as a category, but it takes a whole 50 to get to banding
   so is that middle section just free to do whatever"*. They apply to different columns: 12 is for number
   columns (12 values or fewer: category; 13 or more: cut into bands); 50 is for text columns (50 or fewer:
   category; more: raised as a question). No middle zone exists. **Recommended:** label them *Number columns:*
   and *Text columns:* so they don't read as one range.
3. **Choose tests jumps to the top on every click.** The firm: *"every time I click the button screen kind of
   blinks scroll all the way up and then I have to find where I was again"*. Cause: a click redraws the whole
   screen (`launcher.py`, the box's command calls `render()`), and the new table starts scrolled to the top.
   **Recommended:** a click changes only its box, and anything it affects updates in place.
4. **All / None for Test it** in Test new variables, instead of one box at a time. Open: should All skip
   columns already ticked under Hold fixed (a column can't be both)? **Recommended:** yes, so All never undoes
   a choice. Hold fixed stays one at a time.
5. **The screens don't use the window.** The firm: *"the column and stuff doesn't fit all the way on the screen
   ... there's a lot of white space to use, and it should really use it so that I can see everything"*. Cause:
   the Choose tests table has a fixed height before it scrolls (`ROOM = {"new": 250, "bleed": 280}` px in
   `launcher.py`) and a fixed width (480 px), whatever the window's size. **Recommended:** the table grows with
   the window and scrolls only when the window itself is full; the other screens checked the same way.
6. **The outcome (and the other required columns) are picked for the analyst, and picked wrong.** The firm:
   *"I have no idea why it automatically decided this random column was an outcome. I should be able to
   change that there's no reason for it to automatically assign something, especially when it's just wrong.
   If anything, it should be a pop-up to say explicitly this is going to be what our outcome is."* Then:
   *"Yeah, [it] picked the wrong on both things. I literally don't understand why it would be so finite in
   that when we both know it's not gonna be able to pick it every time correctly."* (Which two columns were
   wrong on the bank's file was not said.) Cause: `meanings.suggest` fills the five required meanings (key,
   booked, outcome, GCO, RANR) on its own: a column remembered from an earlier confirmation, else a name
   hint with fitting values, else *the only column that fits*. The outcome's hints include `co` and `flag`,
   so any yes/no column named like a co-signer or autopay flag qualifies. The launcher then ticks the first
   outcome-type column (`launcher.py`, `_defaults`), and Choose tests offers the Outcome choice only on
   columns already read as outcomes, so a wrong one can't be corrected there; only on Columns, after the
   workbook is made. **Recommended:** nothing pre-picked for the required columns. Offer every column that
   could be one, the likely one first with its reason, and ask for an explicit yes that names the column
   and what counts as bad (*"BAD_FLAG = 1 is a bad loan: use this as the outcome?"*). Drop `co` as a hint.
   **The bank's file, 29 Sep:** it picked *% orig commitments* over a column named *EVER GCO*. The firm: *"It
   picked like % orig commitments for some reason. There is literally a column called EVER GCO."* Why: names
   are matched as fragments after spaces and symbols are stripped, and `origcommitments` contains both `co` and
   `gco` (ori-gco-mmitments), so it matched as well as EVER GCO; a tie goes to the name that sorts first, and
   "%" sorts before "E"; a percent column holding 0 and 1 (0% and 100%) passes the outcome's 0-or-1 test. EVER
   GCO would also be ruled out if it holds Y/N rather than 0/1: the outcome test takes numbers only (not
   checked; the file stayed at the bank). So beyond the recommendation above: match whole words, not fragments;
   never break a tie silently. The firm on Y/N: *"yes no or 01 like it doesn't need to accept multiple
   things as outcomes that can be part of the hygiene process, but I need to know how it's accepting stuff"*.
   So no new formats; the ask is that the screen says the rule it used (0 is good, 1 is bad, anything else left
   out and counted; or a *Yes means* value typed on Columns) beside the column it proposes.
7. **A verdict on a shuffled p-value near 5%** can fall either way with another seed (the full tie-out, *What
   it found* item 1). Either flag those "could fall either way", or shuffle more. **Recommended:** flag them.
   **Built** (29 Sep 2026, branch `pocketbook-borderline-0929`). The firm, by pop-up: *"I don't like 'could fall
   either way' but flag it somehow"*, and chose **Borderline**: *"Net drain · borderline (p 0.048)"*. The rule
   (`docs/statistics.md` B2a): the p-value that decides a verdict, after the allowance, came from shuffling and sits
   within 2 of its own standard errors of the bar, either side; SE = √(p(1 − p) / shuffles), times what the
   allowance multiplied the p-value by (for Benjamini-Hochberg, the raw p that sets it, times m / j, as the tie-out
   found). Only a verdict whose word turns on the p-value is flagged; a z or exact test never is. Shown on Pockets'
   Worse?, Paid cost kept's Together, Split's p-values, Start here's five largest and tile, the launcher's tile,
   the Run's *Worst for* line and Record (the rule, and a count per dollar rate), each tab's method note saying *"The
   test's p-value is within the shuffle's own margin of the 5% bar, so another run could read it the other way."*
   Colours, order and counts are unchanged. Tests: the Borderline section of `tests/test_firm_answers_2026_09_29.py`;
   planted bugs in `tools/mutation_check.py`.

- **Still at the bank, 29 Sep 2026, evening** (built, on PR #409):
  - *Dropdowns gone after an Excel save.* Excel keeps a dropdown whose list sits on another sheet in its
    extension block, and openpyxl dropped that block, so the next Run saved the workbook without them
    (*"I have no drop downs in most places now"*). `excel_lists.py` puts them back on every load.
  - *Look ignored Treat as Missing* (*"This median call seems to ignore that I said the -99... values ... are
    treating as missing. Look into this and see if this leaks elsewhere"*). Look is now drawn from the Run's
    rules and drawn again when an answer changes. The leak was Look only: a scan of every calculated cell
    after a Run finds the code only in Columns' sample values.
  - *Segments sorted as text*: a loan amount bucket put $5k-<$10k after $40k+. Numbers in labels now sort as
    numbers.
  - *Decided:* **everything compares against the whole book.** The firm: *"we keep things compared to the
    whole book that's just kind of the point"*. So Grids' vs the book stays the whole book, and a filtered
    view (below) compares against the whole book too.
- **Later that evening, at the bank: Look** (built, branch `pocketbook-look-0929`):
  - **Look percentile lines.** The firm: *"Shouldn't we have SD markings on the look tab? Our FICO seems fairly
    distributed but other stuff is not"*. Offered standard deviations or percentiles by pop-up, they chose
    percentiles (29 Sep 2026, evening). Each block lists the 10th, 25th, 50th (the median), 75th and 90th
    percentile, and the chart draws them as thin grey solid lines labelled P10 to P90 at the top, under the red
    dashed edges. Worked out in Python at draw time over the values the median uses (blanks, not a number, the
    likely code and anything answered missing left out), as Excel's PERCENTILE.INC and numpy's default do
    (`statistics.quantiles`, method "inclusive"); stored on `_look` and placed by the red lines' own formula, so
    they follow Bars, From and To, and one outside From..To isn't drawn. On the synthetic book (3,000 loans)
    FICO reads 629 · 665 · 701 · 738 · 774, numpy on the CSV the same. The method note says how they are worked out.
    A block is now 20 rows (was 19); the first still starts at row 10, so Bars stays in C20 as the bank checklist
    says. The method note's "Red dashed lines" line is now "The lines", red and grey.
  - **x-axis labels.** The firm: Excel's labels wrapped, *"24,0/00 should read 24k"*. Labels under the bars are
    now short: 1,000 and over read 24k, a million and over 1.2M, with the decimals the step between labels needs
    (20.5k when they are 500 apart); under 1,000 the column's own format (FICO 620, a ratio 0.35). Built from
    `ROUND(...)&"k"`, not a conditional number format, so negatives (-24k) come out the same in both programs. The
    axis's text is set flat with "wrap text" off (`wrap="none"`). The scatters' axes get the same short numbers
    as a number format, only where every tick is a whole thousand.
  - Tests: 5 in `tests/test_look.py` (percentiles by hand from the CSV for FICO and ORIG_BAL; answered missing
    left out; grey lines' x as LibreOffice calculates them, gone outside a narrower From..To; labels as
    calculated: 550 ... 790, 0 / 12k / 24k ..., 20.5k, 600k / 1.2M, -24k; axis formats). 11 planted bugs, all
    caught. Full suite: `828 passed, 7 skipped in 2167.70s`.
  - **Not checked in real Excel:** that Excel honours `wrap="none"` on category labels (LibreOffice ignores
    it), and where Excel puts the P10 to P90 labels (LibreOffice: right of each line's top).
- **Answered by pop-up, 29 Sep 2026, evening** (the four Grids changes offered at the bank that day, all **yes**;
  a number column as a segment, **Later**). Built on branch `pocketbook-grids-0929`
  (`tests/test_firm_answers_2026_09_29.py`, the section that opens with the firm's words):
  1. *Grey out Grids cells under the fewest-loans setting* (yes). A pocket with fewer loans than Fewest loans
     in a pocket (the number the Run used; its suggestion worked out when that was picked) shows its number in
     grey with no colour, in vs the book and vs rest of band, and is left out of the largest gap that sets the
     scale. What one cell says: *"Grey: only 3 loans, fewer than the 30 set on Control, so not coloured."* The
     photo's case, 620-659 · $20k-<$25k, 3 loans, Kept after losses -50.38 pts, is planted in the test book.
  2. *The book's own rate in the vs the book heading* (yes): *"vs the book (book: 7.73%)"*, live as the
     Measure changes; for a gap in points, the book's rate the gap is taken from. vs rest of band has none: its
     rest differs by row.
  3. *"Only loans where" on Grids* (yes; *"it would be nice to be able to filter by that category which would
     probably solve a lot of ... having multiway views"*). By the Split by column when it is a category: the
     engine builds each grid again on each value's loans (`Grid.filtered`), and every block and the one-cell
     reading show it. vs the book stays the whole book, as decided; vs rest of band is the rest of the band
     among those loans; grey and the heat scale go by that view's cells. Split in halves or not at all, the
     dropdown offers only All loans and says filtering needs Split by a category. Any category, not only the
     split column: later.
  4. *A Loan size measure* (yes; *"we tend to give these loan amounts to these FICO scores within this
     category"*): booked dollars per loan by cell, the average in Rate and as a multiple of the book's and the
     rest of the band's, the median read out in words (*"These 207 loans averaged $32,626 booked, median
     $34,127."*). Descriptive: no test, not on Pockets or Split, no red or green (one neutral hue, darker the
     bigger). Offered only when a booked amount is set.
  - Tests: 6 new (a 3-loan Kiosk pocket at -62 points planted in the test book, every count, rate and gap in a
    filtered view and every loan size worked out again from the loan file); 16 planted bugs added and 4
    repointed, all 23 put back one at a time and caught. Full suite 828 passed, 7 skipped. The note on Grids
    keeps its rows, so the checklist's B13 and F13 still hold; F13 now lists 6 measures (the .md says so; the
    checklist PDF was not rebuilt).
  - *A number column as a segment* (FICO x asset bands in one Run): **Later**.
  - *Pre-banded columns, "Treat as bands"*: parked. The firm: *"I don't know because I feel like there could be
    a few different ways that they are formatted and I added the ad hoc"*.
- **Column widths, 29–30 Sep 2026** (branch `pocketbook-widths-0929`). The firm: *"take a look at column spacing.
  i prefer to have nice even layouts, or at least the column sizes should make sense for the data we see"*. The
  survey, with before pictures and after pictures beside them, is `pocketbook/docs/column-widths-survey-2026-09-29.md`.
  Every width is now worked out per Run from what that Run shows (`house.fit`, `house.two_line_width`), never
  set per bank. Grids: one data width for every column of the four blocks and the groups table (9 to 16), one
  label width for both label columns (12 to 28), headers that wrap with every block's the same height. Split,
  Pockets, Paid cost kept, Start here, Look, Control and Columns fitted the same way. `tests/test_widths.py` and
  ten planted bugs hold it.
  - **Waiting for the firm:** the survey proposed wrapping Columns' *Check first* (prose up to 147 characters,
    clipped at 60 wide). It was built, then taken back: `test_answer_tabs` holds the redesign's rule 5 on that
    table (*"Every row is one line and every row in a table is the same height"*), and wrapping breaks it. The
    call is the firm's: wrap it (and relax the test for that one column), or leave it clipped and readable in
    the cell.
  - **Decided for the firm, reversible** (each is one place in `results.py`):
    - *G4: a split grid's header is two rows*: the segment merged over its parts, the parts ("high", "low", or
      the category's values) beneath. So the merge is the same for every split grid the Grid dropdown picks,
      every segment gets every part in one order, and a part a segment has no loans in is an empty column.
      Reverse: `_split_layout` returning `[]` gives one row of "<segment> · <part>" labels again.
    - *G6: booked dollars in the groups table under Grids show in thousands* (`$1,234k`) when the book's total
      would not fit the widest data column; never `####`. Reverse: `THOUSANDS_FMT`.
    - Beyond the plan: a label too long to fit two lines even at the cap (the survey's made-up
      "Non-Customer/Online Direct") gets the header lines it needs rather than being clipped; Split's Grid
      dropdown spans B:D and the partner chip moved from C:D to E:F (no checklist cell moved; two tests read
      the chip by `results.SPLIT_CHIP`); Look's B is fitted at 0.9 a character to the labels as they are now
      (the percentile rows, "50th percentile (P50), the median" at 33 characters, made it 32, not the survey's 30).
  - Not changed: Record (it wraps by design), `live.py`, hidden columns, the checklist's named cells (Grids B13
    and F13, Split B15 and B26, Look C20, Pockets C18 to E18 all stay where they were).
- **Filter by, apart from Split by, 30 Sep 2026** (branch `pocketbook-filter-by-0930`). The firm found the Grids'
  *Only loans where* worked only off Split by: *"Wait only works on split by? Isn't that for like above and below
  median"*. Offered a separate Filter by, they answered *"Yes hoping to have this by morning"*; their use is 2022 to
  2024 originations, flipped year by year to show the pockets hold across vintages.
  - **Launcher:** a fourth column, **Filter by** (a radio), in the Choose tests table beside Split by: any category,
    or **ORIG_YEAR**, a row that sits with the categories whenever a column is marked Origination date (*"Origination
    year, from ORIG_DATE · 3 values · 27 with no date"*). One column or none; it never touches the split or the
    segments (a category may segment and filter at once). More than 6 values (blanks and no-date loans aside,
    `choices.FILTER_MOST_VALUES`) is refused in the launcher (Next stays off) and at the Run in the same words:
    *"REGION has 7 values. The Grids can be filtered by a column of 6 values at most: with more, each value's loans are
    too few to fill a grid. Filter by a column with fewer values, or by none."* Written to Control's *Chosen in the
    launcher* as **Filter the Grids by** (one row more in that block, under *Split every pocket by*; no checklist cell
    moves), read back by the next Set up, and passed to the Run as `filter_by:`.
  - **ORIG_YEAR** is one definition (`engine.origination_years`), used by Split by and Filter by alike and by the
    launcher's count: the year of the column marked Origination date, read as the Run reads that column (dates that
    read two ways are refused). **Decided:** a loan with no readable date goes to **(no date)**, a value of its own
    listed last, never put in a year and never dropped (every loan stays in view, as decided 26 Sep); it isn't
    counted against the 6. No column marked Origination date: the Run refuses ORIG_YEAR in words.
  - **Grids:** *Only loans where* reads the Filter by column, whatever Split by is doing (halves, a category, or
    none). Every earlier rule holds: vs the book against the whole book, vs rest of band within the filtered loans,
    grey and the heat scale by the view's own cells, Loan size filtered, and the one-cell reading ends *", only loans
    where ORIG_YEAR is 2023"*. The one data width fits the filtered views' values too. No Filter by: the dropdown
    offers All loans only, and the note under it reads *"Pick a Filter by in the launcher."* (it read *"Filtering needs
    Split by a category."*). A category split no longer filters on its own.
  - **Split by ORIG_YEAR:** each year against the rest of its pocket, and the Split tab's *Do the values of ORIG_YEAR
    differ at all?* line (K-group Mantel-Haenszel; 3 degrees of freedom for 2022, 2023, 2024 and (no date)) is the
    consistency test across vintages.
  - **Record** has a *Grids filter* row (the column, where a year comes from, each value's loans); the Run's lines say
    the same. Start here doesn't name the split, so it doesn't name the filter either.
  - Tests: 6 in `tests/test_firm_answers_2026_09_29.py` (Filter by), on a synthetic book with origination dates
    across 2022 to 2024 (every filtered block cell, for each year and (no date), worked out again from the CSV);
    6 existing tests changed (the Grids fixture now picks Filter by as well as Split by; the no-filter note; the
    launcher's four headings, twice; the Choose tests order, twice, now with ORIG_YEAR after the categories).
    Planted bugs: 13 added and 4 repointed, put back one at a time with the 6 others on the lines touched: 23 of 23
    caught. Full suite in shards (Python 3.11, LibreOffice, no tkinter here): 872 passed, 7 skipped (the window
    tests), 0 failed. **Not checked:** the Tk window itself (no tkinter on this machine), real Excel, the bank.
  - **Found, not fixed:** an equal-loans band edge that isn't a whole number is labelled one short: FICO cut at 654.2
    reads *"496 - 653"* but holds FICO 654 (`engine.band_labels`: the step is 1 for whole-number display, and the
    edge is not rounded). The test types whole edges to stay clear of it.
- **Band labels one short on a whole-number column** (found 30 Sep 2026 building Filter by): FICO cut at an
  equal-loan point of 654.2 read "496 - 653" and held 654. A column of whole numbers now labels each band from the
  first value it holds (655) to the last (654); a column with cents keeps the nearest-dollar reading. Test and
  planted bug in `tests/test_firm_answers_2026_09_29.py`.
- **The evening tie-out, 30 Sep 2026** (`pocketbook/docs/tie-out/2026-09-30-evening/`, on build 44734da4): 281,421
  cells TIED, 12,016 within sampling, 376 DIFFERS, 13 COULD NOT; every figure of the evening's changes ties.
  The DIFFERS: 104 are the one shuffle draw 29 Sep's million-shuffle run already settled; 254 are width
  measurements, of which four were real clips and are fixed (Split's borderline cells, Start here's segment
  with the flag, Look's P50 label, New variables' ranges) and the rest are headings that wrap or spill as
  designed; 18 are the one item below (decided and built the same day: the 18 now tie).
- **Decided and built, 30 Sep 2026: a dollar band's label when its edge has cents** (branch
  `pocketbook-whole-dollar-edges`). Was open: an equal-loan cut at $37,950.548 read "26,324 - 37,950" then
  "37,951 - 49,151", and a loan of $37,950.99 sat in the second. The firm: *"Cut at whole dollars is fine"*.
  - **The rule** (`engine.whole_cut`): an edge PocketBook *cuts* on a column whose labels read in whole units
    (`engine.reads_whole`, the test `band_labels` already used: every edge 100 or more either way) and whose values
    carry cents is **raised** to the next whole number. **Decided: a whole-unit label reads a value with its cents
    dropped** (floor: $37,950.99 reads 37,950), so a band [a, b) at whole a and b holds exactly the loans whose
    reading is a to b - 1, which is its label. Raised rather than rounded because on a whole-number column raising
    moves no loan. The top label now ends at the largest value's whole units (it rounded up). Edges that meet after
    raising are kept once, and one past the largest loan is dropped: the Run's "asked for N bands, got M" says so. A
    column whose loans all read the same dollar keeps its cut rather than losing every band.
  - **Left alone:** edges typed on Columns (the analyst's, exactly as typed), a whole-number column such as FICO
    (already labelled by the values it holds), and ratios (edges under 100).
  - **Everywhere edges are cut:** the Run (`cut_edges`), and so Grids, prevalence, Record's *Band edges used* and
    the CLI, which read `res.band_edges`; and scouting's suggested bins (`scout.bins_at`), which are the pre-spec's
    suggested bins. Look's red lines read only edges typed on Columns, so nothing there moves.
  - **Q3 book, ORIG_BAL:** edges 15,448.536 / 26,323.856 / 37,950.548 / 49,152.37 became 15,449 / 26,324 / 37,951 /
    49,153. Labels were *5,005 - 15,448 · 15,449 - 26,323 · 26,324 - 37,950 (1,599) · 37,951 - 49,151 (1,600) ·
    49,152 - 59,983*; they are now *... 26,324 - 37,950 (1,600) · 37,951 - 49,152 (1,599) · 49,153 - 59,983*. The
    one loan that moved is L0001306 ($37,950.99).
  - Tests: 9 in `tests/test_firm_answers_2026_09_29.py` (Cut at whole dollars). One existing test's expected label
    moved: `tests/test_shortlist.py`, TENURE's top group over values to 61.3 now reads "10 - 61" (was "10 - 62"),
    under the same cents-dropped reading. Planted bugs: 10 added to `tools/mutation_check.py`, 10 of 10 caught.
    Full suite in shards: 885 passed, 7 skipped (the window tests), 0 failed, `test_mutation_tool.py` and
    `test_bank_checklist.py` included.
  - The evening tie-out's band-label check, run again on this build (`recheck_whole_dollars.py`, addendum to
    the report): 60 of 60 labels tie on the six grid books, and the 18 band-label DIFFERS no longer differ.
- **Decided and built, 30 Sep 2026: a number column too few-valued to cut gets one band per value** (branch
  `pocketbook-few-values`). The firm, at the bank: *"So it refuses to run some stuff because it cannot band. Which
  makes sense for the examples so far - they are things like major derogs which do not include too many numbers."*
  To the fix below: *"Yes that's fine"*.
  - **Before:** a column like Major Derogatories (0 to 8, 85% of loans at 0) marked Amount or number and cut into 5
    equal-loan bands had all four cuts land on 0, and the Run stopped: *Couldn't run: the extract has no column
    "Major Derogatories" (a band: no readable numbers to cut). Its columns are: ... If a column was renamed or
    dropped, press Set up again.* (wrong on both counts: the column was there, and Set up wouldn't help).
  - **Now** (`engine._cut_or_each_value`): when the equal-loan (or round) cut gives fewer bands than asked for and
    the column has Control's *few values* (the launcher's "Number columns: this many values or fewer is a
    category", 12 by default; it now rides with each band as `few_values:`) or fewer, **each value is its own
    band**, labelled by the value (*0*, *1*, ... never *0.0*; blank and the other special rows as usual). The Run's
    lines and Record say *"Major Derogatories: too few values to cut into equal bands, so each value is its own
    band."* More values than that and still collapsing: cut as far as it can be, with the existing *asked for N
    bands, got M* (when no cut survives at all, the lowest value against the rest). A single value: refused, *"Major
    Derogatories" reads 0 on every loan, so there is nothing to cut into bands. On Columns, set What it is to
    Category, or type Band edges like 1; 2; 5.* Band edges typed on Columns always win.
  - **Columns:** *Why we think so* gains *Few values (0 to 8): Category may read better.* beside a column the last
    Run gave value bands, and loses it at the next Run that doesn't. What it is, and what is remembered, stay as
    answered.
  - **Everywhere the labels are named:** `Result.value_bands` carries each such column's values, and
    `engine.labels_for` names bands for the Run and for prevalence (Grids' groups, `_labels_by_band`, `_bands_of`),
    so a subset of loans keeps the same names. Grids, its filter, Summary and the three-way pockets take the
    Run's own labels. Look's red lines read only typed edges, so nothing there moves.
  - Tests: 13 in `tests/test_firm_answers_2026_09_29.py` (few_values), Grids and Summary cell for cell against the
    loan file, whole book and one year. Two existing tests moved with the rule: `test_engine.py`'s 600/700 score
    column asked for 5 bands now gets one band per value (and still warns "asked for 5, got 2" at few_values 1), and
    the whole-dollars test whose five dollar values meet sets few_values 4 so the cut is still what it tests.
    Planted bugs: 9 added to `tools/mutation_check.py` and 2 repointed (the band loop moved), 11 of 11 caught. Full
    suite in shards: 907 passed, 7 skipped, 0 failed (the two moved tests red on the first pass, green after),
    `test_mutation_tool.py` and `test_bank_checklist.py` included.
  - **For the firm:** a dollar column with 12 or fewer distinct amounts that can't be cut would also get one band
    per amount, labelled with its cents (*100.1*); none of the books seen so far has one.
- **Paid, cost, kept: gross booked, GCO and RANR, 30 Sep 2026** (branch `pocketbook-pck-gross`). The firm: *"On the
  paid cost kept tab I would like to work on gross GCO gross booked and gross RANR as well so we can also see if
  pockets are straight negative on returns"*.
  - **Gross · this pocket alone**, four columns right after Loans (before the gaps: what the pocket did on its own
    reads before how it compares): **Booked**, **GCO**, **RANR** and **RANR rate** (RANR ÷ booked), from the Run,
    compared with nothing. **Decided here:** Booked is the booked dollars under RANR (Kept's bottom), so RANR rate is
    Kept's own rate; a loan whose RANR doesn't read is out of both, and GCO is what the charge-off rate adds up (a
    `#N/A` charge-off is out of GCO but its balance stays in Booked).
  - A pocket whose RANR is below zero: its RANR and RANR rate in **red** (CRIMSON, the house alert text), and a line
    beside the Grid dropdown, worked out in Python per grid: *"6 pockets lost money outright, totalling $166,260:
    RANR below zero, in red."* (red when any), or *"No pocket listed lost money outright ..."*. The method note's
    Kept item says *"Negative RANR: the pocket lost money outright, before comparing it with anyone."*, on the
    same row, so no row of the tab moves.
  - Under the table: **Pockets listed**, **Not listed** (pockets with nothing to compare them with, only when any)
    and **Whole book**, the grid's own margin; the first two add up to the third.
  - **Nothing named moves:** B16 (the Grid dropdown) and M13 (the waiting note) stay where the bank checklist sends
    the analyst; the tiles keep C:K. Together moves from K to O and the chart from M to Q. Verdicts, colours, order,
    borderline flag and chart are unchanged. Dollars switch to $k only when the whole book's booked would not fit
    the widest data column (the Grids rule); widths fit every value the dropdown can show.
  - Tests: 6 in `tests/test_firm_answers_2026_09_29.py` (Paid, cost, kept: gross), every gross cell of both grids
    worked out again from the CSV; `tests/tabs.py` reads the four new columns and `test_book_results`' header
    list grew by four. Planted bugs: 7 added to `tools/mutation_check.py` (RANR rate over loans; negative not red;
    count line leaving out untested pockets; gross from the rest of the band; Not listed dropped; whole book from
    the listed pockets; never thousands), 7 of 7 caught; *Together too narrow for the borderline flag* repointed
    (the spacer after Together is now `C_TOG + 1`, not column 12) and caught. Full suite in four shards: 891
    passed, 7 skipped (the window tests), 0 failed, `test_mutation_tool.py` and `test_bank_checklist.py` included.
  - Tie-out `pocketbook/docs/tie-out/2026-09-30-pck-gross/`: a Kiosk book (8,090 loans), both grids, 481 figures,
    **481 TIED, 0 DIFFERS**, Road 2 importing nothing from PocketBook.
  - **For the firm:** the count includes a 1-loan pocket (the loan with a blank score that charged off); a pocket
    under Fewest loans is still counted and red, since a loss is a loss, not a test. Say if it should be left out.

- **Built, 30 Sep 2026: the Summary tab** (branch `pocketbook-summary-tab`). The firm: *"I want to add some easy
  high value views as well. Like a few matrices where it lists out a chosen band on the left and shows real
  calculated metrics... Maybe I want to see bands of FICO on the left and straight up unit counts, loan amounts, % of
  units, % of loan amounts, charged off dollars, ratio, percentage of units. Same with RANR. They'd be across the
  top."* The ratio: *"Charged off / booked"*. Bad loans columns: *"Yes do this"*.
  - **The tab** (`results.write_summary`, after Grids: both show one table at a time from dropdowns, as of the last
    Run). A **Band column** dropdown lists every column the Run cut into bands. When the launcher picked a Filter by,
    an **Only loans where** dropdown offers All loans and that column's values. Rows are the bands in order, then
    (blank), (not a number) and (marked missing) where present, then All. Columns: Loans · % of loans · Bad loans ·
    Bad loans % · Booked $ · % of booked · Charged off $ · Charge-off rate · × book · % of charge-offs · RANR $ ·
    RANR rate · % of RANR. A column whose source the Run hasn't got is left off, and the note says which.
  - **The numbers** (`engine.Summary`, `engine.summary_rows`): each band is accumulated from the loans as a grid
    cell is, then tied out to the book before anything is written (`_tie_summary` raises TieOutError). Bad loans %
    is the Bad loans rate. The charge-off and RANR rates are the Charge-offs and Kept after losses rates, so a loan
    missing an amount is out of that rate's top and bottom, as on Grids. × book is against the whole book, even
    under a filter. The shares are of the view's All row. The tab's formulas only pick a _views row. There is no
    test and no red or green; only the All row is shaded (CANVAS). Widths use Grids' rule: one data width, headings
    on two lines, and $k only when the largest dollar figure would not fit under 16.
  - Tests: 3 in `tests/test_firm_answers_2026_09_29.py` (Summary). They check every cell of FICO and REV_DEBT
    against the CSV, that the shares add to 100%, that All equals the book, the dropdown switch, each year's filtered
    numbers, and that a missing source drops its columns with the note. 3 existing tests now expect Summary in the
    tab order. Planted bugs: 7 added to `tools/mutation_check.py`, 7 of 7 caught.
  - Tie-out (`pocketbook/docs/tie-out/2026-09-30-summary/`): 14 views, 1,274 cells, 1,274 TIED, 0 DIFFERS.
  - **For the firm to confirm:** × book stays against the whole book under Only loans where, so a year's All row
    reads something like 1.12× rather than 1.00×; the shares are of that year's loans. The Charged off $ column only
    counts loans that also have a booked amount, so it matches the rate. Summary offers band columns only, not
    segments.
- **Built, 30 Sep 2026: errors on the window, not in Notepad** (branch `pocketbook-errors-on-screen`). At the bank,
  Run with the extract (`Test_Pop_DC.xlsx`, in OneDrive) open in Excel stopped. The window said "Something went
  wrong while running. The details are in …\last-error.txt", and that file, opened in Notepad, held a
  `PermissionError: [Errno 13]` traceback from Run's fingerprint check (`book.py:1804`,
  `hashlib.sha256(src.read_bytes())`). PocketBook checked whether the *workbook* was open, never the *extract*. The
  firm: *"It would be a lot easier if these kinds of errors just displayed on screen in the huge white space
  allotted"*.
  - **The extract** (`book.cant_read`): every place it is read (Run, Set up's column read `read_extract`, Next's
    `set_up`) turns an OSError into a refusal naming the file. The bank's case now reads: *"Test_Pop_DC.xlsx can't
    be read: it's open in Excel, or OneDrive is still syncing it. Close it in Excel (check for a hidden Excel
    window), or right-click it in File Explorer and choose Always keep on this device. Then press Run again."*
    Set up says "press Set up again". A missing extract says where it was looked for. Run now reads the extract
    once and takes the fingerprint from those same bytes (`Table.sha256`); it used to read it twice, and the first
    read is the one that raised. Set up's second read for the fingerprint is gone the same way. Scouting reads no
    extract of its own (it works on the Run's table), and the launcher's pick reads nothing.
  - **Anything unexpected** (`launcher.Crash`): it shows in the page's own space under a plain heading (*Run
    stopped*, *Set up stopped*, *Writing the workbook stopped*): "Something went wrong that PocketBook didn't
    expect.", then the error's type and message, then "Press Copy details and send what it copies, to get it
    fixed." **Copy details** puts the full traceback on the clipboard. A copy is still written to
    `.pocketbook/last-error.txt`, and the window no longer points at it. Nothing opens Notepad: no code ever did.
    The analyst opened the file because the window said to. A Run that stopped for a reason other than an answer
    now spans the page, not a 360 px list row. The window stays usable, so the analyst can fix the cause and press
    Run again. `Flow.set_up`, `Flow.next` and `Flow.run` never raise; the window's thread keeps a last net for
    anything a step didn't catch.
  - Tests: `tests/test_errors_on_screen.py` (10: the bank's case through Flow and `book.run`, Set up and Next, a
    gone extract, one read per Run with a changed extract still noticed, an unexpected error in Run and in Set
    up/Next, the tie-out's own words kept with Copy details added, and 3 on a display: the panel in the page,
    Copy details on the clipboard, the last net). 1 test each changed in `test_launcher.py` (the old sentence) and
    added in `test_bank_checklist.py` (the checklist quotes the window's own words, and Part 7 no longer says
    Notepad). Planted bugs: 8 added to `tools/mutation_check.py`, 8 of 8 caught; 4 display-only ones run by hand
    under xvfb (CI has no display), 4 of 4 caught.
  - The checklist (Part 7 and *If something goes wrong*) and its HTML/PDF rebuilt; README step 5.
  - **Not exercised on a real screen:** Windows, Excel's real lock on the extract, OneDrive's online-only files, and
    the Windows clipboard. The lock was simulated by making every read of the extract raise PermissionError; the
    window was drawn under xvfb on Linux and photographed.

- **Built, 30 Sep 2026: the Choose tests table tints the row you are in** (branch `pocketbook-row-highlight`). The
  firm: *"In setup screens it would be nice if it highlighted the row you're clicking in when the button is far away
  from the column names"*. Pointing at any part of a row (name, what it is, any box) tints the whole row CANVAS, the
  colour of the All/None band. A click keeps it tinted after the pointer leaves, until another row is clicked. A
  redraw keeps the clicked row. `launcher.relight` decides which row is tinted and which go back to white, and
  `row_light` binds Enter, Leave and Button-1 on every widget in a row.
  - Tests: 2 in `tests/test_row_highlight.py`. One checks `relight` with no window, so it runs in CI. The other builds
    the window, points and clicks, and checks every background in the row; it skips without a display. Planted bug:
    1 added (*row highlight never cleared*), caught with a display (2 failed) and without one (1 failed).
  - Picture: `pocketbook/docs/row-highlight-2026-09-30/choose-row-highlighted.png` (REV_DEBT clicked at Split by,
    the pointer off the table).
- **Built, 30 Sep 2026: the bureau's missing codes, in every column** (branch `pocketbook-odd-values-all`). The
  firm: *"still not seeming to identify that things that aren't recent delinquency have negative values ... it's
  useful to see the value because they are generally just missing items"*, and *"I can guarantee you that they are
  the bureau missing codes so I think it's just not working correctly."* The cause: a numeric column read as a
  category (installment delinquencies of 0, 1, 2 and -99,000,900) was never asked about, and the one cell that was
  asked read *-9.90009e+07 on 12,410 loans*.
  - **Columns** now asks about every column of numbers, a category's too (`profile.classify`), and a 0/1 flag's 0,
    one step from the 1s, is never asked. The Odd values cell names the values and their loans in plain numbers:
    *-99,000,900 on 460 loans*; up to five negatives each with its count, more than five as *Negative on N loans
    (e.g. ...)*. Never scientific notation (`config.plain_value`, also used by Look and the memory rows). A category
    answered Missing puts those loans in *(marked missing)*, as a band does.
  - **Control** asks one question more, in the firm's words: *"Treat values ≤ -99,000,000 as missing in every
    column?"* (Yes/No; blank changes nothing and the Run doesn't wait for it). Yes makes every value at or below
    -99,000,000 missing in every column, with no Treat as needed; a column answered Real on Columns keeps its
    values. The Run's lines and the Log say how many loans it made missing in each column the Run read, and Columns
    marks each code it covered *→ missing (Control: ≤ -99,000,000)*, which Start here no longer counts as open.
  - A value missing by either route is in no band edge, rate, percentile or Look chart (`engine._caught`, which
    Look reads too).
  - Tests: 10 in `tests/test_firm_answers_2026_09_30.py`, on a synthetic extract, with counts tied to the
    CSV; 3 existing tests now read -9,999 for -9999. Planted bugs: 9 added to `tools/mutation_check.py` and 2
    repointed (their lines had moved), 11 of 11 caught. The bank checklist's Step 10 row reads the new cell text.
  - **For the firm to confirm:** with the Control question unanswered or No, an unanswered code is still used as
    recorded (odd values are asked, never acted on, OC-7), so it shows in Look until answered one way or the other.
- **The firm's own terms, 30 Sep 2026** (branch `pocketbook-literal-names`). The firm: *"let's rename this list of
  stuff for a couple things and be more literal - Charge-offs = GCOs ($), kept after losses = RANR, earned before
  losses = RANR + GCOs"*, and then *"I want to use the terms I gave you out of the box so it can be understood by
  insiders"*. Charge-offs is **GCOs ($)**, Kept after losses **RANR**, Earned before losses **RANR + GCOs**, on
  every tab, the launcher, the README and the bank checklist (HTML and PDF rebuilt); the tab Paid, cost, kept is
  **RANR vs GCOs**, its sides headed RANR + GCOs, GCOs and RANR; the Rate block on Grids says what it divides,
  *Rate · GCOs ÷ Booked*, following the Measure dropdown. Only the words moved: the keys (`gco_rate`, `ranr_rate`,
  `contribution_rate`) a workbook, a pre-spec and memory hold are unchanged. A workbook written before reads: Set
  up links its Paid, cost, kept tab under that name, and the next Run takes it off and writes RANR vs GCOs (held on
  the evening tie-out's own workbook, `tests/test_literal_names_2026_09_30.py`, 5 tests). Planted bugs: 5 added to
  `tools/mutation_check.py`, 3 existing ones repointed at the new wording; the 8 run alone, 8 caught. Tests: the 6 files the change touches most, 136 passed; 10 more, 208 passed and 3 failed, each for scikit-learn not being installed in the test environment.
  - **For the firm to confirm:** the launcher's plain line now reads *"Five measures: bad loans, bad dollars, GCOs
    ($), RANR, and RANR + GCOs"*; GCO and RANR are explained on the two lines above it. The historical documents
    (walkthroughs, audits, the redesign) keep the words they were written in.
- **Built, 30 Sep 2026: two filters, and the Compare chart** (branch `pocketbook-compare-chart`). The firm: two
  Filter by columns, *"independently and in conjunction with each other"*; then *"can we make it so they can be
  visually compared in a graph? Like if we used origination date as a filter it would essentially be vintage
  years"*, and *"if we are proving things exist across categories it should not be vintage analysis only so let's
  make sure that is the case and how would we show that say vintage analysis mixed with like underwriter/system
  approved?"* A line chart, chosen over bars.
  - **Filter 2.** The launcher has Filter 1 and Filter 2 columns (a category of 6 values or fewer, or ORIG_YEAR).
    Control carries it as *And filter them by*; the cube file as `filter_by2`. The engine builds every grid and
    every Summary again on each value of either filter alone and on every pair (AND), skipping a pair no loan has.
    Grids and Summary get a second dropdown, *and (column) is*, beside *Only loans where*; vs the book and × book
    stay against the whole book. Refused in words: one column picked twice, and a pair making more than 49 views
    of each grid (choices.FILTER_MOST_VIEWS). Filter 2 picked alone becomes the one filter.
  - **Compare** (`compare.py`, after Summary, only with a Filter by). Dropdowns: *Across the bottom* (a band
    column's bands, or either filter's values, so Origination year across is the vintage view), *Measure* (a
    rate), *Lines by* (Filter 1 or 2), *Panels by* (the other, or None), *Whole book line*. Panels sit side by side
    on one y scale; a point on fewer loans than *Fewest loans in a pocket* is #N/A, left off its line, and grey in
    the table under the charts. The numbers are the Run's (the Summary cells) on _views; the formulas only pick
    them, so the charts are live. Built as scatters with lines, not line charts: LibreOffice draws a line chart's
    #N/A at zero. The labels across are one-point series named by their label cells; the key sits in cells.
  - Tests: 9 in `tests/test_compare_2026_09_30.py`. Three tie every chart point, table cell and the shared scale to
    the CSV with nothing imported from pocketbook: Origination year x SYS_FLAG, FICO x year in SYS_FLAG panels,
    and FICO x CHANNEL in SYS_FLAG panels (not vintage at all). Grids and Summary with both filters, the Run's
    line and Record, the launcher, and both refusals. Planted bugs: 12 added and 5 repointed (17 of 17 caught) in
    `tools/mutation_check.py`. Pictures: `pocketbook/docs/compare-chart-2026-09-30/` (LibreOffice renders of
    synthetic data). The bank checklist now counts 35 pasted files.
  - **For the firm to confirm:** Compare's panel slots are fixed at the Run (the larger filter's value count), so
    lines by the larger filter leave a slot empty, drawn blank on the same scale. With a filter across the bottom
    the lines are by the other filter and there is one chart. (no date) and (blank) are lines or panels but never
    a place across.
- **Built, 30 Sep 2026: RANR vs GCOs in band order, sortable, headed against the rest** (branch
  `pocketbook-pck-order`). The firm: *"it would be really nice if the bands could be sorted or at least make it
  easier to look at what's happening on this tab. Hard to see these in a sensical order."*
  - **Order.** Rows are by band, lowest first ("0 - 619" before "620 - 659"), (blank) and (marked missing) last,
    then by segment, each in the grid's own order; they were by GCO dollars. Excel's sort and filter arrows sit on
    the header row over the pockets only, never the totals. The hidden workings now sit just right of Together,
    inside the arrows' range, so a sort in Excel moves each row's workings with it (outside it, a sort would have
    left every row reading its old row's numbers). Every rule on the rows reads its own row. The chart numbers the
    first 8 pockets read together down the table, whatever the order, and lists them under it.
  - **Headings.** "gap vs book" and "× book" read as the whole book; the numbers are against the rest, the pocket
    left out. Checked by hand on the firm's row, 720-739 Non-Customer/VLA: GCOs 12.85% ÷ the rest's 4.48% = 2.86×
    (÷ the whole book's 4.61% would be 2.78×). Now *gap vs rest of book* / *× rest of book*, and *rest of band*
    when Control judges against the band.
  - **Rest.** Each side has a Rest column, the rate its gap is measured against (_pockets' rest that decides). On
    the firm's row: RANR + GCOs 9.02%, GCOs 4.48%, RANR 4.54%.
  - Tests: 10 in `tests/test_pck_order_2026_09_30.py`, on a synthetic book built to the firm's figures; every
    rest is worked out from the loans with nothing from pocketbook, in both comparisons, and a sort done as Excel
    does it (formulas moved row to row) keeps every row, its colours and the chart's numbers. 4 tests in
    `test_book_results.py` found the planted pocket by being first and now look it up by name; headings updated in
    5 files. Planted bugs: 4 added to `tools/mutation_check.py`, 4 caught. Runs: 9 files, 152 passed;
    `test_book_results.py` and `test_firm_answers_2026_09_29.py -k pck`, 53 passed. Pictures (LibreOffice renders
    of the synthetic book): `pocketbook/docs/pck-order-2026-09-30/`.
  - **For the firm to confirm:** Rest sits last in each side (gap, dollars, rest). After a sort, picking another grid
    fills the rows in the sorted positions, so its pockets are out of band order until sorted again (Data, Reapply).
- **Built, 30 Sep 2026: Columns shows every column, the wheel never errors, a progress line** (branch
  `pocketbook-columns-launcher`). The firm: *"for some reason in my testing it is hiding random rows from the
  columns tab which makes it hard to make sure it's right"*; a wheel scroll at the bank raised *"_tkinter.TclError:
  invalid command name ".!frame2.!frame3.!frame100.!frame3.!canvas""*; and *"it seemed pocketbook hanging and it
  didn't before"*.
  - **Columns** no longer hides the columns the launcher didn't pick (29 Sep's change). They are shown greyed
    (CANVAS, SLATE text) and Check first opens *Not used this Run.*; D3 says how many. Still nothing asked about
    them and nothing counted. Check first's shading leaves that note alone.
  - **The wheel** is bound once, to whichever table is on screen (Choose tests, or the answers list), and does
    nothing once that page has gone. It was bound to Choose tests' own canvas and outlived it. X11's Button-4/5 too.
  - **Progress line**: under a busy page, the stage and the time since the button was pressed, e.g. *Running the
    shuffle test… 1 min 40 s*, updated ten times a second. `book.set_up` and `book.run` take `progress(stage)`
    (a no-op by default) and call it at their stage boundaries; `engine.run` says *Cutting bands* and *Running the
    shuffle test*. The work already ran in a thread; the line is what shows it hasn't hung. Picture:
    `pocketbook/docs/columns-launcher-2026-09-30/run-progress-line.png` (synthetic, xvfb).
  - **openpyxl's warnings** about Excel's extension blocks (*Data Validation extension…*, *Conditional Formatting
    extension…*) are filtered on every read of a workbook or an .xlsx extract (`excel_lists.quiet`/`hushed`).
    Checked: the tabs a Run keeps (Control, Columns, Look, and Start here, which it redraws) have no shading rule
    that reads another sheet, so Excel has nothing of theirs to move into that block. Grids has four; every Run
    deletes and redraws Grids, so they come back. Until the next Run, a Set up or a refused Run on a workbook Excel
    saved leaves Grids without those four.
  - Tests: 7 in `tests/test_columns_launcher_2026_09_30.py` (one on a display); 1 in
    `test_firm_answers_2026_09_29.py` and 1 in `test_answer_tabs.py` updated. Planted bugs: 6 added, 3 repointed, 9 of 9 caught; the wheel's and the
    progress line's plant into `launcher.wheel_target` and `Flow.progress_line`, caught with no display (CI has
    none), and the window test holds the same two under xvfb. The nine files the change touches: 168 passed, 1 failed for
    scikit-learn not being installed here.
- **Built, 30 Sep 2026: Grids stacked, and Summary by a category** (branch `pocketbook-grids-summary`).
  - **Grids.** From the firm's photo of a 4-segment grid: the four blocks sat 2×2, and the right-hand pair started
    after the *widest* grid's columns, so a narrow grid left a blank middle. Now they are stacked, one under another
    from column B: Rate, vs the book, vs rest of band, Loans; the note, *What one cell says* and the Groups tables
    follow under them. The dropdowns stay where the bank checklist sends the analyst (B13 Grid, F13 Measure), so
    the checklist and its HTML/PDF are unchanged. Every formula that reads a block (the INDEX/MATCH views, the
    grey and heat rules, the example-cell panel, the hidden helper cells) follows the block's new place; the
    widths are one label width in B and one data width across.
  - **Summary.** The firm: *"the band column should also allow for categories because we can still view it that
    way, and the logic should still make sense"*. The left-column dropdown, now **Band or category column**,
    lists the band columns, then the segment/category columns. The Run keeps a Summary for each category column
    too, the whole book and every filter view (keys (column, filter 1 value, filter 2 value)), and ties each to its
    All as the band columns do. Rows: each value in natural order, then (blank) / (marked missing), then All. The
    header cell names the column picked. The arithmetic is unchanged (counts, shares of All, rates = dollars ÷
    booked, × book against the whole book).
  - Tests: 6 in `tests/test_grids_summary_2026_09_30.py` (Loans and Rate blocks of FICO x ASSET_CLASS, the
    example-cell panel, and Summary by CHANNEL and by ASSET_CLASS on one year, all tied to the CSV with plain
    arithmetic). `tests/test_widths.py`'s Grids tests rewritten for the stacked layout. Planted bugs: 4 added and 2
    repointed in `tools/mutation_check.py` (the old right-hand label column is gone). Pictures (LibreOffice renders
    of synthetic data): `pocketbook/docs/grids-summary-2026-09-30/`.
  - **For the firm:** the title band and the note on Grids now run as wide as the dropdown row (to the Column
    picker), not the width of two blocks.
- **Built, 30 Sep 2026: where a Run's time goes, and what the workbook costs Excel to open** (branch
  `pocketbook-speed`). The firm: a Run on about 17,000 loans x 70 columns took **578 s** on the bank's laptop
  (Ryzen 9 PRO 7940HS, 32 GB, Windows, the extract an .xlsx in a OneDrive folder), and *"in excel it seems to work
  quickly enough but it takes quite some time to open particularly in the last stretch of loading"*.
  - **Seconds per stage.** `timing.py`: every stage of `book.run` and `book.set_up` is timed by the wall clock and
    handed to a `progress(stage)` callback as it starts (default: nothing; for the launcher to wire). Record's This
    Run gains *Where the time went*: each stage in order, its seconds and share, what it worked on (the extract's
    kind and rows x columns, the grids, the shuffles and how many processes dealt them, or that the worker processes
    didn't start); the Run's lines gain *"Took 12 s: the shuffle test 3.8 s, writing Look 3.3 s, saving the
    workbook 1.3 s."* (above *Open ...: start with*, which stays last); the record file carries every stage.
  - **Measured here** (Linux, 4 cores, synthetic 17,000 x 70: FICO in bands, CHANNEL, split by REV_DEBT, filter
    SYS_FLAG, 10,000 shuffles; the .xlsx an Excel-style file with shared strings). Run, .csv / .xlsx: opening the
    workbook 1.0 / 1.0 s, reading the extract **0.3 / 5.4 s**, the loans' values 0.7 / 0.4, grids 0.7 / 0.7, the
    shuffle test 3.8 / 3.9 (4 processes), filter grids 0.3 / 0.3, result tabs 0.5 / 0.5, **Look 3.3 / 3.0**, saving
    1.3 / 1.4; in all **12.3 / 16.9 s** (before these changes 12.2 / 16.6). Set up: 14.1 to 12.1 s (.csv), 18.6 to
    17.3 s (.xlsx), from not reading back the workbook it had just saved. Nothing here explains 578 s: the table
    will say where the bank's time goes. The likeliest, in order: many more grids than here (the shuffle test and
    the grids grow with banded columns x segments; *Every number column* left chosen would do it); the worker
    processes failing to start (Record now says so); OneDrive and the virus scanner on every file read and write
    (each file is now read once: the extract's bytes and the workbook's bytes are opened from memory, and a sheet
    without Excel's dropdown block is no longer parsed twice).
  - **The workbook's open cost** (the same Run's workbook; LibreOffice headless as the stand-in for Excel: 6.3 s to
    open and calculate, 1.6 s for an empty workbook). 31,350 formulas, 74% of them on the hidden `_look`; 231
    conditional-format rules over 5,708 cells; 50 dropdowns; 1 volatile formula (OFFSET on Grids, plus 2 OFFSETs
    in dropdown lists); about 4,500 whole-column references to `_views` and `_pockets`; 46 charts. Taken apart:
    **Look is 4.0 s of the 4.7 s above an empty workbook** (without Look, `_look` and `_dots`: 2.3 s); its 44
    charts (29 series each, 24 of them the red edge lines) are 2.5 s, `_look`'s formulas about 1.1 s (the 120
    chart slots per column most of it), every result tab's formulas together about 0.6 s. Changed, every number
    the same (LibreOffice-calculated copies compared cell by cell: 186,920 cells, differing only in the time
    stamps, Record's timings and the new cells): no OFFSET (INDEX:INDEX); whole columns of `_views` and `_pockets`
    ended at their last row (`bounds.py`, before the save; Record left word for word); Look's 58 line ends per
    column read one *tallest bar* cell instead of each taking MAX over 120 slots. Measured: 6.3 s to 6.2 s, within
    LibreOffice's noise. Not checked: real Excel.
  - **For the firm to decide:** the open cost is Look's blocks, one per number column that can be cut (43 here).
    Drawing blocks only for the columns chosen to band and the split, or fewer edge lines per chart, would take
    most of it off; either changes what Look shows. Reading an .xlsx extract costs 5 s here against 0.3 s for the
    same file as .csv, twice (Set up and Run): saving the extract as CSV before picking it is the cheapest win at
    the bank.
  - Tests: `tests/test_speed_2026_09_30.py` (12: the table there, in order, adding up, the Took line, progress,
    a broken progress, the refused pool said, each file read once, no OFFSET or whole column, the calculated values
    unchanged, the tallest bar). Two tests follow the change: the Row/Column list parser in
    `test_firm_answers_2026_09_29.py`, and the load counter in `test_answer_tabs.py` (the workbook is opened from
    its bytes). The bank checklist's paste count is 37 (two new modules); its PDF not rebuilt. 4 planted bugs
    added in `tools/mutation_check.py`; with 8 existing ones near the change, 12 of 12 caught (1 after its test
    was strengthened). Already failing before this branch, at f2998527: `test_compare_...panels_by_system_approved`,
    `test_a_new_variable_run_is_asked_only_what_it_uses`, `test_l2_the_summary_says_what_will_run_in_both_modes`.
- **Built, 1 Oct 2026: months to charge-off** (branch `pocketbook-co-months`). The firm: *"We worked in calculating
  charge off months right? If the data is there"*. It hadn't been built. Chosen: the average months to charge-off,
  from a charge-off date column in the extract.
  - **Columns.** A new meaning, **Charge-off date** (`chargeoff_date` in `settings.yaml`: test *dates*, never cut
    by, hints chargeoff, chgoff, chrgoff, codate, gcodate, writeoff, wrtoff, codt, gcodt). Optional: nothing
    requires it. At most one column may carry it (`config.DATE_ROLES`). A bleed Run counts it as in use, so its row
    isn't greyed. A date column nothing names is now asked *Origination date ... Charge-off date ... otherwise Not
    used*.
  - **The rule.** With both an Origination date and a Charge-off date, each loan with a charge-off date gets
    whole calendar months, `(y2 - y1) x 12 + (m2 - m1)`, the day ignored (31 Jan to 1 Feb is 1; 1 Jan to 31 Jan
    is 0). `engine.chargeoff_months`. A blank charge-off date is a loan that didn't charge off and is not counted.
    Left out and counted in one warning on the Log and Check: a charge-off date that isn't a date, no readable
    origination date, a charge-off before origination. A charge-off date with no Origination date marked is a
    warning too. Dates that read two ways are said, not guessed. Only a bleed Run works it out.
  - **Shown.** Summary gains **Avg months to charge-off** and **Median months to charge-off** (among the row's
    charged-off loans; blank where none did), on every row, All and every filter view, with a note line stating
    the rule. Grids gains the Measure **Months to charge-off (avg)**: it rides the existing Show-per-pocket
    machinery (a median-mode measure, `show: average`), so every cell, margin and filter view has it, shown and
    never compared or coloured; the rule is said inside Grids' Rate note, so the note keeps its rows and the
    dropdowns stay where the bank checklist puts them (checklist unchanged). With no charge-off date column, no
    column, measure, note or warning is added.
  - Synthetic: `synth.write_extract(..., chargeoff=True)` adds CO_DATE on every BAD_FLAG 1 loan (1 to 36 months
    after origination, never after AS_OF), from its own random stream; nothing else changes.
  - Tests: 10 (11 with the answer below) in `tests/test_co_months_2026_10_01.py`: Summary by CHANNEL, on one origination year, and every
    Summary view on `_views`, tied to the CSV with plain arithmetic; Grids' measure tied to the CSV; the
    warning's counts; Columns' suggestion and no grey; nothing changes without the column; the engine's months on a
    six-loan book; the no-origination warning. Run with the seven neighbouring files: 106 passed; meanings,
    config, engine, tab wording, columns/launcher, book, launcher: 108 passed, 2 skipped, 1 failed (scikit-learn
    not installed). Planted bugs: 3 added in `tools/mutation_check.py` (a charge-off before origination counted,
    the day of the month counted, the charge-off date greyed as unused), 3 of 3 caught with no LibreOffice and no
    display. Pictures (LibreOffice renders of synthetic data): `pocketbook/docs/co-months-2026-10-01/`.
  - **For the firm to decide** (2 answered below): (1) GCO_DT or CO_DT (two short words) isn't recognised by name, since a hint
    under six letters must begin or end a word; it is offered as *dates, but which date?* and remembered once
    confirmed. (2) A bad loan with no charge-off date isn't counted or warned about; say if it should be. (3)
    Days-ignored means a loan made 31 Jan and charged off 1 Feb counts 1 month; whole elapsed months would count
    0. (4) Summary doesn't show how many charged-off loans each average is over.
  - **Answered, 1 Oct 2026 (decision 2):** a bad loan with no charge-off date. The firm: *"Leave out, count in a
    note"*. It stays out of the averages, and when the Charge-off date column is in use the Run's lines, the Log
    and Check say *"Months to charge-off: 37 bad loans have no charge-off date, so they are left out."*
    (`engine.no_chargeoff_date`; the Run's lines now carry every months-to-charge-off warning). Test: the count
    tied to the CSV (`test_bad_loans_with_no_charge_off_date_are_counted_in_a_note`); 1 planted bug added, 4 of 4
    of this feature's caught with no display; every entry's old string still occurs once (644 entries).
- **Built, 1 Oct 2026: Start here counts each loan once; Filter 1 starts on Origination year** (branch
  `pocketbook-distinct-total`). Two choices the firm made the same day, as relayed to this session (the firm's own
  words were not passed on beyond these): Start here's dollar total should count *"distinct loans"*, each loan
  once; and Origination year should be Filter 1 by default.
  - **The fault.** *Dollars above their share, in those* was `SUMIFS(pk_dollars, ...)` over every worse-and-material
    pocket on every grid. Every loan sits in every grid, so a loan was counted once per grid it was flagged in. On
    the bank's workbook, with 168 grids: **$2,904,231,129** above share on a book whose GCOs were **$37,767,925**.
    The RANR tile (*N short $X*) and the launcher's finished tile added up the same way.
  - **The rule chosen.** A pocket's dollars above share are its loans' own: each loan's GCO less its booked dollars
    at the rate the pocket is compared with (the rest of the book, or the rest of its band). A loan in several
    worse-and-material pockets counts once, in the one where its own dollars above share are largest. In a
    sentence on Start here: *"The dollars count each loan once, in the pocket where it is furthest above its share:
    every loan is in every grid, so a plain sum counts it once per grid."*
  - **Why not the simpler one** (the union of those loans against the rest of the book). It doesn't tie to anything
    the workbook already shows: on one grid it gives a different number from the pockets' own dollars, because each
    pocket is compared with *its* rest (of the book or of its band) and the union with one rest. The rule chosen
    does tie: a pocket's loans' own dollars add up to exactly its *Dollars that decide*, so on a one-grid book the
    total is the old sum to the cent, and on many it is that sum with the repeats taken out. It also keeps
    Control's *judged against*. For a loss compared at a rate of nought or more it can't exceed the GCOs of the
    loans counted, so never the book's. RANR's shortfall is the same rule turned round (rate x booked less RANR).
  - **Where.** Worked out in the engine at Run (`engine.Once`, `engine.once_over`), over the two-way grids only, as
    the tiles count; written to `_found` as values (a formula can't tell one loan from another). Start here's tiles:
    *Pockets worse and material, GCOs* keeps its live count and adds *· in N grids*; *Dollars above share, each loan
    once*; *Pockets short on RANR, each loan once* (*N short $X*). The launcher's finished tile says *in those N
    pockets, each loan once*. Materiality, judged against, worse at and confidence take effect live, and move the
    pockets with no Run: the total is then the Run's for other pockets, so each tile checks that the live count and
    the live sum of pocket dollars are still the Run's and otherwise reads **Run again to total** (also what a
    workbook whose last Run predates this reads). Bank checklist: Step 12 $2.29M, Step 13 *4 of 81 · in 3 grids ·
    $2,287,240 · 4 short $2,746,544*, Step 19 now reads *Run again to total*, 5.3 *14 of 81 · in 4 grids* and
    $11,609,786; HTML and PDF rebuilt. The practice book's old sum is $3,100,042 today against the checklist's
    $3,094,991 (and the speed book's $23,486,461 against $23,486,197): the pinned numbers had drifted before this
    change, unexplained here; the other rows of that table were not re-measured.
  - **Filter 1.** When the extract has a column marked Origination date (and its years are few enough to filter by),
    Choose tests starts with Filter 1 on Origination year. It clears or changes like any pick; Filter 2 stays the
    analyst's; a workbook beside the extract still shows what was picked before, a cleared Filter 1 too (so a
    workbook written before today keeps no filter until it is picked).
  - Tests: 10 in `tests/test_distinct_total_2026_10_01.py`. Each loan once on a four-grid book, tied to an
    independent count from the CSV (plain Python; only which pockets the Run flagged and against what is taken
    from it, and each pocket's loans are checked against its top and bottom): at most the GCOs of the loans
    counted, at most the book's, and less than the old sum; the same for RANR; a one-grid book equals the old sum;
    Start here's three tiles after LibreOffice; *Run again to total* after a live materiality change and on an
    older `_found`; Filter 1's default, cleared and changed, kept cleared by the next Set up, none with no
    origination date or too many years, and the window drawing it (display, guarded). Three existing tests follow
    the default (the L2 summary, Filter 2 alone, the Filter by offer). 3 planted bugs added in
    `tools/mutation_check.py` (a loan counted once per pocket again, Start here showing the Run's total beside moved
    pockets, Filter 1 starting empty), 3 of 3 caught with no display; every entry's old string occurs once (647).
    Run: the new file and the eight named neighbours, 161 passed, 1 failed (`test_l2_...`, scikit-learn not
    installed, after the line this change touches); the eight other files that drive the launcher or read
    `_pockets`, 165 passed, 2 failed (both scikit-learn).

- **Built, 1 Oct 2026: Set up's suggestions from a sample of the grids** (branch `pocketbook-sampled-suggest`). At
  the bank, 184,937 loans and 12 band columns x 14 segment columns (168 grids): *Working out the suggestions* took
  over 3.5 minutes. The firm: *"Will the quick estimates be as accurate? … Test it and let's see"*. Tested first;
  built only because it passed.
  - **What the suggestions read.** Fewest loans is `ceil(5 / the whole book's bad rate)`: no grid at all, so it
    can't change. Worse at is the median, over every pocket of every grid at or above fewest loans, of the smallest
    gap that pocket's test could call significant (`luck_gap`), and that gap depends only on how many loans the
    pocket holds. Better at is `round(1 / worse at, 2)`. So a sample only has to get the spread of pocket sizes
    right. The sample: every segment column equally often, every band column within one of equally often, the same
    on every Set up (fixed seed).
  - **The experiment.** Synthetic books shaped like the bank's (12 number columns of four shapes, 14 categories of
    3 to 7 values in an uneven mix, the last skewed to about 88% one value, a missing code on one column, an
    outcome leaning on some of each), Set up's own first pass (draft bands of 5, no shuffle test), every grid
    against 14, 24, 28, 40 and 42 grids. Sizes 14, 28 and 42 are multiples of 14 (each segment column equally
    often); 24 and 40 aren't. Worse at as Control shows it (better at follows it; fewest loans matched in every
    book, every size). Seconds are the suggestion pass alone, on this container.

    | Book | Fewest loans | Worse at, every grid | 14 | 24 | 28 | 40 | 42 | Secs, every grid | Secs at 14 / 24 / 28 / 40 / 42 |
    |---|---|---|---|---|---|---|---|---|---|
    | 17k, seed 1 | 69 | 1.32x | 1.32 | 1.32 | 1.32 | 1.32 | 1.32 | 27 | 5 / 6 / 8 / 9 / 9 |
    | 17k, seed 2 | 151 | 1.45x | 1.45 | **1.44** | 1.45 | 1.45 | 1.45 | 25 | 5 / 6 / 7 / 8 / 9 |
    | 17k, seed 3 | 245 | 1.58x | 1.58 | **1.59** | 1.58 | **1.59** | 1.58 | 26 | 5 / 6 / 7 / 8 / 9 |
    | 17k, seed 4 | 21 | 1.15x | 1.15 | 1.15 | 1.15 | 1.15 | 1.15 | 27 | 5 / 7 / 7 / 10 / 9 |
    | 17k, seed 5 | 113 | 1.41x | 1.41 | 1.41 | 1.41 | 1.41 | 1.41 | 27 | 5 / 7 / 7 / 9 / 9 |
    | 17k, seed 6 | 36 | 1.22x (0.82x) | **1.23 (0.81)** | **1.23 (0.81)** | 1.22 | 1.22 | 1.22 | 27 | 5 / 7 / 7 / 8 / 10 |
    | 185k, seed 11 | 124 | 1.13x | 1.13 | 1.13 | 1.13 | 1.13 | 1.13 | 264 | 56 / 73 / 82 / 91 / 98 |
    | 185k, seed 12 | 105 | 1.12x | 1.12 | 1.12 | 1.12 | 1.12 | — | 262 | 56 / 71 / 83 / 93 / — |
    | 185k, seed 13 | 167 | 1.15x | 1.15 | — | 1.15 | — | 1.15 | 279 | 63 / — / 80 / — / 90 |
    | 185k, seed 14 | 123 | 1.12x | 1.12 | — | 1.12 | — | — | 256 | 63 / — / 79 / — / — |

    Bold: one step (0.01x) off. Before rounding, 28 grids came within 0.0017 of every grid in every book (0.0003
    at 185k); 14 within 0.0030; 24 and 40, which favour some segment columns, up to 0.0089.
  - **The verdict.** 28 grids, the smallest size that matched every grid at Control's rounding in every book it
    was run on (10 books, 4 of them 185k). 14 matched to within one step, but was off in one book (17k seed 6:
    1.23x / 0.81x for 1.22x / 0.82x). A sample can still land one step off in some book: the median of the
    sampled pockets sits within about 0.002 of every grid's, so a book whose answer sits that close to a rounding
    line can round the other way. That is why Run checks it (below). At 185k: about 80 seconds against about 265,
    three times faster. Most of what is left is reading every loan, cutting the bands and the Summary tables
    (about 45 seconds), not the grids. For reference, counting every pocket of every grid exactly, without building
    the grids, took about 126 seconds: exact, but slower than the sample.
  - **Built.** `book.suggest_pairs` picks the grids: a multiple of the segment columns, at least twice the larger
    column count and at least 28 (the size tested), so a book of 28 grids or fewer reads every grid as before.
    `engine.run(..., pairs=)` builds only those grids; the whole book's rate and everything else is read as before.
    Control says it beside worse at and better at: *"suggested: 1.32x, from this extract: a quick estimate from 28
    of its 168 grids, checked on all at Run"*. Fewest loans is never called an estimate. What the sample said is
    kept in `_about` (A5). At Run, which works every suggestion out from every grid as it always has, a
    suggestion whose estimate rounded differently says so: *"… Set up's quick estimate, from 28 of 168 grids, was
    1.32x"*. Where the answer typed on Control is that estimate: *"The answer chosen, 1.32x, is Set up's quick
    estimate from 28 of 168 grids: every grid says 1.33x"*. Where they agree, the words are unchanged.
  - **Not tested.** Shapes other than 12 x 14 at the bank's size (8 x 10 and 6 x 6 are tested below); a book
    whose band columns are mostly one-band-per-value columns; a split or filter chosen at Set up (both are built
    only for the sampled grids too).
  - Tests: 7 in `tests/test_sampled_suggest_2026_10_01.py`. On 20,000 loans x 8 band columns x 10 segment
    columns, 30 grids of 80 suggest what every grid does at the rounding shown. The sample builds only its grids
    and reads every loan. Every segment column comes up equally often and every band column within one. A small
    book reads every grid. Set up builds 30 of 36 grids and says so on Control and in `_about`. Run's words are
    checked through `_suggestions`, and once through a real Run where the answer typed is the estimate. Run with
    test_firm_answers (3 files), test_answer_tabs, test_control, test_book and test_mutation_tool: 167 passed, 3
    skipped, 0 failed. Planted bugs: 3 added in `tools/mutation_check.py` (the sample balanced on band columns, Set
    up building every grid, Run never checking the estimate) and 1 repointed (*Run leaves the suggestion stale*,
    whose line this rewrote). 4 of 4 caught with no display; every entry's old string still occurs once (647
    entries).
- **Built, 2 Oct 2026: a Glossary tab** (branch `pocketbook-glossary`). The firm, after explaining the grids'
  figures to their boss: *"Maybe a nice glossary of terms in the workbook should be there"*. They keep "points" as
  the unit.
  - **What it is.** A grey tab right after Start here, written by every Set up and every Run
    (`src/pocketbook/glossary.py`). One term a row: the term, what it means in one or two short sentences, and an
    example. 25 terms, in the firm's order: Booked, GCOs ($), RANR, RANR + GCOs, Rate, Points, × book / × rest of
    book, Rest of book / rest of band, Bad loan, Band, Segment, Pocket, Grid, Filter / Only loans where,
    Origination year, Worse and material, Borderline, Shuffle test / p-value, Fewest loans in a pocket, Worse at /
    Better at, Dollars above their share (each loan once), Lifetime-to-date, Months to charge-off, Odd values,
    (marked missing) / (blank).
  - **The examples.** After a Run, in the whole book's own figures: *"This book's RANR came to $33,030,193. The
    book keeps $12.80 per $100 booked"* on the 8,000-loan practice book. Points and × book name a real pocket (the
    one furthest short on RANR, and the one furthest above its share on GCOs, against the rest of the book). Worse
    and material, and dollars above share, are Start here's figures at the Run (4 of 81, $2,287,240 on the
    practice book). The figures are kept on `_found` as JSON, so Set up again keeps them. Before the first Run
    the examples are made up (the firm's own "$4.45 per $100 booked") and the note says so. Not live: a line
    changed on Control moves the result tabs, not the examples, and the note says that too.
  - **Wording.** Where a tab already words a definition the Glossary reuses it (Pockets' rest of band and Worse?,
    Summary's × book, Columns' odd values, the Borderline note). Every sentence is 28 words or fewer and carries
    no contract-desk word (tested). Made-up examples use SCORE and SOURCE, never the synthetic book's columns,
    so test_generic's no-leak check holds. "Earn" is not used (test_profit). The Glossary joins `_meanings` as a
    sheet allowed to say "charge-off", since it is a definition (test_literal_names).
  - **Start here** lists it under The tabs, in the grey group with Record (*Glossary: every term, with an
    example*). Its note now reads "grey tabs are the glossary and the record".
  - **Checklist.** A new 4.10 (the Glossary is second, 25 terms, Start here opens it). 4.2 counts eleven visible tabs
    (it said nine, already stale since Summary). The paste now writes 38 files. HTML and PDF rebuilt.
  - Picture (LibreOffice, practice book): `pocketbook/docs/glossary-2026-10-02/glossary-page-1.png` and `-2.png`.
  - Tests: 8 in `tests/test_glossary_2026_10_02.py`. RANR, GCOs, booked and the rate tie to the CSV, worked out
    without PocketBook. Tab order pinned in test_book, test_answer_tabs and test_result_tabs; test_bank_checklist
    checks the count, the position, the terms and the link. Planted bugs: 2 added (the RANR example read from
    RANR + GCOs; Set up writing the made-up examples over the Run's figures), 2 of 2 caught with no display;
    every entry's old string still occurs once (652 entries).
- **Built, 2 Oct 2026: Avg line and × book** (branch `pocketbook-avg-line`). The firm: *"I want to start including
  and using booked dollar averages so more easily demonstrate how line assignments look in pockets and I think it
  adds to the story if our basis is commitments would be stronger elsewhere"*. Booked is the committed line (cards
  book their line), so booked dollars per loan is the average line. They chose where: Summary and RANR vs GCOs.
  - **Summary.** Two columns right after Booked $: **Avg line**, the row's booked dollars over its loans with a
    booked amount, and **× book**, that over the whole book's Avg line, filtered or not (as GCOs' × book is). Every
    row, All and every filter view: worked out in the engine (`engine.summary_rows`, `Summary.booked_loans`) and
    put on `_views` like every other Summary figure, so the dropdowns move them. Blank, never 0 or #DIV/0!, where a
    row has no loans. A note line says what both are. Unshaded, as the rest of Summary.
  - **RANR vs GCOs.** The gross block ends on **Avg line** and **× book** (after RANR ÷ Booked, so no existing
    column of the block moves and `_views` rows keep their positions: the two ride at the end of each pocket's and
    each total's row). The same figure as Grids' Loan size for the pocket (`engine.size_vs`); the totals under the
    table carry them too (Whole book 1.00×). Shaded as Loan size is, `SIZE_STEPS` on the row's own × book (1.10×
    and up, darker the bigger), never red or green; each cell and rule reads its own row, inside the sort arrows'
    range, so a sort keeps them right. The words ride on RANR's note item, so no row of the tab moves (B16 and M13,
    the checklist's cells, stay put).
  - **Glossary.** A 26th term, *Avg line / Line × book*, second after Booked, with an example in the book's own average
    line after a Run. Checklist 4.10 says 26 terms; HTML and PDF rebuilt.
  - **For the firm to confirm:** (1) Summary now has two columns headed *× book*: the new one after Avg line, and
    GCOs' after GCOs ÷ Booked; each sits beside what it multiplies, but say if the new one should read *Avg line ×
    book*. (2) Avg line divides by the loans with a booked amount, as Grids' Loan size does, so where a loan has no
    booked amount it is not exactly Booked $ ÷ Loans (Branch on the plain synthetic book: $31,963, against $31,483,638 ÷
    986 = $31,931). (3) On RANR vs GCOs, Booked is the booked dollars under RANR while Avg line is over every loan
    with a booked amount; they differ only where RANR is unreadable.
  - Pictures (LibreOffice renders of synthetic data, ORIG_BAL scaled by FICO and channel for the pictures only so
    the lines differ): `pocketbook/docs/avg-line-2026-10-02/` (Summary by CHANNEL; by FICO on 2022 alone, its
    empty (blank) row blank; RANR vs GCOs whole and its gross block close up).
  - Tests: 8 in `tests/test_avg_line_2026_10_02.py` (6 need no LibreOffice): every Summary view by CHANNEL and by
    FICO band, All loans and each origination year, and every pocket and total of FICO x CHANNEL on RANR vs GCOs,
    tied to the CSV with plain arithmetic; a Kiosk channel made only in the first year proves the empty rows blank;
    the formulas pick the right `_views` positions and the shading is Loan size's hue on the row's own × book; and
    both tabs calculated by LibreOffice. Headings updated in `test_co_months_2026_10_01.py` and
    `test_firm_answers_2026_09_29.py`; the term list in `test_glossary_2026_10_02.py`; `tests/tabs.py` reads the
    two columns. Planted bugs: 2 added (Summary's Avg line over every loan; RANR vs GCOs' × book against the rest
    of the band), 2 of 2 caught with no display and no LibreOffice; every entry's old string still occurs once (654
    entries). Full suite: 1,016 passed, 13 skipped, 2 failed; one was a heading list in `test_book_results.py`, updated
    and passing on its own rerun; the other,
    `test_co_months_2026_10_01.py::test_without_a_charge_off_date_nothing_changes`, was already failing at the
    Glossary merge 40abd906: the Glossary always defines *Months to charge-off*, and that test asserts the words
    appear nowhere in a book without a charge-off date column; left for the firm, not changed here).
- **Built, 3 Oct 2026: Summary's vintage chart and grey rows** (branch `pocketbook-summary-vintage`). Two firm
  requests for Summary. The chart: *"Could the summary tab have vintage graphs as well? Showing our primary targeted
  info, maybe an option for average booked, amount booked, basically whatever is there except graphed out"*; chosen:
  *"Pocket vs rest vs book"*. The grey: *"make the really low unit counts grayed out to a degree... so it's easier to
  spot quick trends and not look left at the unit count. However this count should be separately adjustable from all
  other config items - no dependencies just a simple number for this view specifically"*.
  - **Vintage chart.** Under the Summary table, a row clear of it, so nothing existing moves: a dark heading, one line
    of what it is, **Vintage measure** (every Summary column, Loans to Median months to charge-off where the Run has
    it) and **Vintage row** (one row of the column Summary's dropdown picked; its list follows that dropdown, via
    OFFSET as Grids' Row does). Three lines across the origination years: the row, the rest of the book (every other
    loan of the view), and the whole book, dashed grey. Summary's Only loans where applies to all three, and a live
    caption says what is drawn and on which loans. Every point is worked out in the Run (`summary_chart.vintage`,
    called from `engine.run` after the Summaries): one pass per Summary view groups its loans by (row, year), and each
    point goes through `engine.summary_rows` itself, so it is the same arithmetic as a Summary row on that year's
    loans. A share is of that year's loans; x book is still against the whole book. Put on `_views` as
    `V|<column><view>|<i>`, `|<i>|rest` and `|book`, one flat row each (measure after measure, year after year);
    the tab's hidden cells pick them, so both dropdowns redraw live. A point on fewer loans than the Run's Fewest
    loans in a pocket is #N/A (not drawn) and grey in the table of points under the chart. A scatter with lines, as
    Compare's (LibreOffice draws a line chart's #N/A at zero), its x the year itself. A loan with no readable date is
    on no line. No column marked Origination date: one sentence in the chart's place, and in the note.
  - **Grey rows under [50] loans.** C2, in the blank row between the title band and the note (no cell moves): a plain
    50, styled as an answer that changes the tab now. One more rule in Summary's one conditional-format range (so
    LibreOffice and Excel agree, as `results.cf` requires) greys the font of every row whose Loans is under it.
    Nothing else reads it: no formula, rule or name elsewhere (tested). The note's Shading line says so.
  - **Glossary.** A 27th term, *Vintage*, after Origination year. Checklist 4.10 says 27 terms, and 2.2 says the
    paste writes 39 files (`summary_chart.py` is one more); HTML and PDF rebuilt.
  - **Kept across Runs (3 Oct 2026, at the merge).** The firm asked for the number to be "separately adjustable", so
    a Run reads what was typed before it rewrites Summary and puts it back (`summary_chart.typed_grey`/`keep_grey`,
    called in `book._write_results`); 1 test, 1 planted bug.
  - **For the firm to confirm:** (2) The chart's axis has one plain
    number format for every measure (an axis can't take its format from a dropdown), so a rate or share is drawn in
    per cent (7.12, the caption says per cent), dollars and counts read 32,000.0 with one decimal; the table under
    the chart shows each in its own format. (3) The vintage helper roughly doubles `_views`: on 20,000 loans, three
    band columns, two segments and two filters, a Run went 11.8 s to 17.7 s and the workbook 1.2 MB to 2.2 MB.
  - Pictures (LibreOffice, synthetic book of 6,000 loans): `pocketbook/docs/summary-vintage-2026-10-03/` (GCOs ÷
    Booked by FICO band; Avg line by CHANNEL; Bad loans % on Broker loans only, its 2026 point under 30 loans left
    off; Grey rows under 1,100; the book with no origination date).
  - Tests: 5 in `tests/test_summary_vintage_2026_10_03.py` (2 need no LibreOffice): every FICO row, the rest and the
    book, every year, All loans and each CHANNEL, on Loans, Avg line and GCOs ÷ Booked, tied to the CSV with the csv
    module (over 500 points); the tab calculated by LibreOffice with the dropdowns set, its points tied to the CSV and
    the chart's three series reading #N/A exactly where a point is thin; the rows list following a category column;
    the no-date sentence; the grey rule's formula, its 50, and nothing else reading C2. The term list in
    `test_glossary_2026_10_02.py` gains Vintage. Planted bugs: 4 added (the rest counting the pocket; greying at the
    number, not under it; a default other than 50; each year's point read from the year before), 4 of 4 caught with
    DISPLAY unset; every entry's old string still occurs once (659 entries).

- **Built, 1 Oct 2026: a third filter, with a size limit** (branch `pocketbook-three-filters`). The firm: *"I thought
  we discussed two filters plus date"*. Chosen: Origination year plus two more filters, with a size limit.
  - **Filter 3.** Built exactly as Filter 2 is: a third launcher column (*Filter 3*), Control's *And then by*, the
    cube file's `filter_by3`, and a third dropdown, *and (column) is*, on Grids and Summary. The engine builds every
    view of the three: each value alone, each pair and each triple, all holding together (AND), skipping a view no
    loan has. Views are keyed (Filter 1, Filter 2, Filter 3) in `Grid.filtered` and `Result.summaries`, and
    `|and3 value` on `_views`. Filter 3 needs Filter 2, as Filter 2 needs Filter 1: a later filter with an earlier
    one empty moves up, in the launcher and in Set up alike. Filter 3 must be another column than Filters 1 and 2,
    refused in words (*"Filter 1 and Filter 3 are both REGION. The third filter narrows the other two, ..."*). Filter
    1 still starts on Origination year. Compare: Lines by and Panels by each offer all three filters (the one in
    neither is All loans), and any of them can go across the bottom.
  - **Where the dropdowns sit.** Grids: Filter 3 right of Filter 2, Row and Column move four columns further right.
    Summary: Filter 3 right of Filter 2. Grid (B13) and Measure (F13), which the bank checklist names, do not move;
    the checklist was not changed and test_bank_checklist passes.
  - **The size limit.** Each grid is built again for every view, so views = (n1 + 1) x (n2 + 1) x (n3 + 1), All
    loans counted for each and blanks and (no date) counted as values. Three filters may make 150
    (`choices.FILTER_MOST_VIEWS3`: 6 x 5 x 5 = 150 passes, three columns of six values, 7 x 7 x 7 = 343, do not);
    two keep their 49 (`FILTER_MOST_VIEWS`, pinned by test_compare). Past it, the launcher refuses before Next and
    the Run refuses, in the same words: *"FA (5 values), FB (4 values) and FC5 (5 values) together make 6 x 5 x 6 =
    180 views of every grid, counting All loans in each. Three filters can make 150 at most. Drop a filter, or pick
    a column with fewer values."* The launcher's *This will run* line now says the cost with any filter: *"Each grid
    is built for 6 × 5 × 5 = 150 views, All loans counted: 8 grids × 150 = 1,200 to build."*
  - Tests: 15 in `tests/test_three_filters_2026_10_01.py`. Grids (three picks, cell by cell, and one cell's words)
    and Summary (two picks) tie to the CSV with nothing imported from pocketbook in the arithmetic; Compare with
    Filter 3 as Panels by, as Lines by, and lines by it with Origination year across; the Run's line, Record and
    Control; the limit at every combination of 0 to 8 values each, and 150 taken and 180 refused by the launcher
    and by a real Run; the launcher's Filter 3 logic and refusals, and its column on screen (needs a display).
    Changed: the launcher's heading tuples and three *This will run* assertions, which now end with the cost. Run
    with test_compare, test_grids_summary, test_firm_answers_2026_09_29, test_launcher, test_bank_checklist,
    test_distinct_total, test_mutation_tool, test_widths and test_result_tabs, no display: 209 passed, 4 skipped
    (each a launcher check that needs a screen). The one failure seen first (`test_l2_the_summary_says_what_will_
    run_in_both_modes`) was scikit-learn missing from that machine, not this change: it passes with it installed.
    Planted bugs: 3 added in `tools/mutation_check.py` (Filter 3 ignored by the engine, three filters' views
    unlimited, Filter 3 without Filter 2 kept third by the launcher), 13 repointed whose lines this rewrote.
    All 16 (the 3 new and the 13 repointed) put back one at a time with no display: 16 of 16 caught; every entry's
    old string occurs once (653 entries).
  - **Merged with the Glossary and Avg line (3 Oct 2026).** Avg line and Line × book come from each view's own
    Summary, so they move with Filter 3 as with the other two; `test_three_filters_summary_is_the_loans_with_all_
    three` now ties both, on the All row and each band, to the CSV under three picks. The Glossary's *Filter / Only
    loans where* now says up to three filters can be picked. Conflicts were only in this file's logs and in
    `tools/mutation_check.py`'s list (both kept); every entry's old string occurs once (658 entries). Full suite
    after the merge, no display: 1,032 passed, 14 skipped (all tkinter missing), 0 failed.
  - **For the firm to decide:** (1) The two limits are separate, so a pair refused at 56 views (8 x 7) is taken
    once a small third filter is added (8 x 7 x 2 = 112): the cost is still under 150, but it reads oddly. Holding
    every pair to 49 as well would close it. (2) The refusal writes the product with `x`, as the two-filter one
    always has; the launcher's cost line writes `×`.

- **Built, 3 Oct 2026: the audit workbook** (branch `pocketbook-audit`). The firm: *"We will need to make this
  auditable... a demo output mode that would take a file and show the calculations it makes on one set of things
  and prove out each one so someone could take their current population run it and then independently understand
  the calculation and its steps"*, then *"we definitely want to be able to demonstrate and explain what the
  formulas are and how to do them by hand"*. Agreed: a separate workbook, one pocket, a live dropdown, recomputed
  by Excel from the raw loans.
  - **Where it's asked.** Control, Needs a Run, last row: *Also write the audit workbook?* (`audit_book`, optional
    like the bureau codes: blank is No, so a normal Run writes nothing more; asked only for the bleed). Yes makes
    the Run write `<book stem> - audit.xlsx` beside the workbook after it saves, and say so in its lines. An audit
    file open in Excel is said in words; the Run itself still succeeds.
  - **Sheets** (`src/pocketbook/audit.py`): Start here (what it is, the order to read it); Run stamp (file, SHA-256,
    rows, every setting and Control answer, version, time, the shuffle seed and where it comes from); Rows in and
    out (rows read, less each loan left out of each rate by column and reason, = the loans in it, each tied to the
    Run's count); Bands (edges as typed and as used, each band's From and Up to, loans per band by formula against
    the Run's, and how many loans' formula band differs from the Run's: 0); Loans (one row a loan, only the Run's
    columns, a value or the reason it has none in words; each band a formula from the raw value and Bands, beside
    the Run's band; *In this pocket* and *In this band* follow the picks); One pocket (Grid, Band and Segment
    dropdowns, OFFSET lists, on the top flagged pocket: worse and material on GCOs, largest dollars above share;
    37 figures, each Step | In words | Written out with the pocket's numbers (live TEXT) | Excel's COUNTIFS/SUMIFS
    on Loans | PocketBook's figure | Ties? to a billionth | By hand); Shuffle test; hidden `_pocketbook` (the Run's
    figures for every pocket, and Benjamini-Hochberg's ranks by shuffle count) and `_lists`.
  - **The shuffle test, as perm.py does it.** What is shuffled: which loans carry the pocket's label, the pocket
    keeping its size; against the book every loan in the GCO rate, against its band only the band's loans. The
    statistic: pocket's GCOs ÷ Booked less the rest's. Two-sided: |g*| ≥ |g| less perm.TIE's allowance (1e-9 of
    the rates' size); a shuffle with no dollars in the pocket counts. p = (count + 1) ÷ (B + 1). Then the
    allowance for many tests over the grid's tested pockets on the same comparison. A 10-loan example (20 shuffles
    from `perm.order_of`, each gap tied to `perm.pocket_vs_rest`'s own draw, count 5, p 6 ÷ 21). The default
    pocket's B shuffles are dealt again from the Run's seed with `perm.run` on that one grid and comparison
    (`RestGap(keep=True)`), all listed; COUNTIF at or past the line either way gives the count, tied to the Run's,
    and so the p-value. The engine now keeps each loan's rate values and labels on `Result` (`per_row`,
    `row_labels`) and names its seed (`engine.SHUFFLE_SEED_NAME`), so the audit proves the Run's own numbers. Other
    pockets' shuffles are not listed (said on the sheet: re-run with that pocket on top, or deal the seed again).
    Beside it, the two-proportion z-test on bad loans, live for the pocket picked, said to be a cross-check.
  - **Fast.** Loans' rows go straight into the sheet's XML (openpyxl took 34 s for 185,000 rows of cells). At
    185,000 synthetic loans, 10,000 shuffles, two band and two segment columns: 33 s added to the Run (reading
    2.4 s, dealing the default pocket's shuffles again 22.5 s on 4 cores, sheets 1.4 s, loans 6.9 s), 23.8 MB.
    LibreOffice calculates it in 45 s: One pocket 37 ✓, Rows in and out 13, Bands 14, Shuffle test 9, no ✗.
  - **Tests:** 13 in `tests/test_audit_2026_10_03.py`, calculated by LibreOffice: every figure ties for the default
    pocket and for three picked with the dropdowns (another grid, the smallest pocket, a (marked missing) band); the
    default pocket's loans, GCOs, booked and bad loans from the CSV's text; rows in and out; every loan's formula
    band is the engine's; the stamp's hash is the file's sha256; the COUNTIF reproduces the count exactly and the
    p-value; the example is perm's; the option off (blank or No) writes nothing. Changed: test_answer_tabs (Block
    B ends with `audit_book`) and test_control (two optional settings). Planted bugs: 4 in `tools/mutation_check.py`
    (shuffles dealt across the book for a band pocket; band edges shifted; rest of the book holding the pocket; an
    outcome of 2 read as bad), 4 of 4 caught with no display; every entry's old string occurs once (667 entries).
    Pictures: `pocketbook/docs/audit-2026-10-03/`. Bank kit: the paste now writes 40 files (checklist 2.2 says so,
    HTML and PDF rebuilt). Full suite, no display: 1,051 passed, 14 skipped, 0 failed (73 min).
  - **For the firm to decide:** (1) A loan marked missing shows *(marked missing)* on Loans, not its value
    (-9,999): the rule is on Run stamp. (2) openpyxl writes numbers to 16 significant digits, so a stored figure
    can differ from the Run's in the 17th; Ties? allows a billionth. (3) Other pockets' shuffles need a re-run.
- **Built, 3 Oct 2026: PocketBook's voice** (branch `pocketbook-voice`). The firm, on the audit workbook's *"Loans —
  Every loan whose band and segment are the ones picked."*: *"it just sounds weird. it does not sound like something
  a human would type ... I'd want this explained like: Loans — Records from the population in the applicable band
  and/or category."* And: *"there has to be a way to get you to be able to understand what i don't like about some
  of the writing."* Diagnosis, agreed: the repo's copy rules (root `CLAUDE.md`'s client-facing section,
  `website/TENETS.md`) were written for tax clients on the website; applied to a bank analyst's tool they strip out
  the profession's vocabulary and produce spec-like sentences.
  - **`pocketbook/VOICE.md`**: who reads PocketBook (analysts, managers, model validators, internal auditors); the
    register (a credit-risk workpaper: full sentences, industry terms expected); what does not apply (the
    client-facing rules, `website/TENETS.md`) and what still does (no filler, no self-protective sentences,
    `pocketbook/TENETS.md` T1 and T2, and a test's existing rule on its own surface); seven patterns with before
    and after pairs, the firm's own first; and a five-question check for a sentence. `pocketbook/README.md` points
    to it; root `CLAUDE.md`'s PocketBook mention says its copy follows it.
  - **Rewritten** (`src/pocketbook/audit.py`, `src/pocketbook/glossary.py`), wording only: no number, formula,
    figure, cell position or meaning moved. Audit workbook 203 strings (Start here 14, Run stamp 7, Rows in and out
    20, Bands 24, Loans 1, One pocket 89, Shuffle test 33, and 15 in branches the test book doesn't reach);
    Glossary 74. One pocket's column headings are now Step | Definition | Calculation | Excel's figure |
    PocketBook's figure | Ties? | By hand. The Glossary still meets its test's contract-word list and 28-word cap.
  - **For the firm:** `pocketbook/docs/voice-2026-10-03/REVIEW.html`, every changed string numbered (277), Where |
    Before | After, to mark by number.
  - **Tests:** `test_glossary_2026_10_02.py` follows four reworded examples (the note, Rate, Points, × book); the
    audit's tests look up labels that were kept. Audit and Glossary tests 21 passed. Every `tools/mutation_check.py` entry's old string still
    occurs once (667), none repointed; the six for audit.py and glossary.py run again with no display, 6 of 6 caught.
    Full suite, no display: 1,051 passed, 14 skipped, 0 failed (79 min).
  - **For the firm to decide:** (1) Loans reads *"Records from the population in the selected band and segment"*,
    not *"and/or category"*: a pocket is the loans in both. (2) Lifetime-to-date's example now reads *"Compare loans
    within the same vintage, because a 2021 loan has had more time on book than a 2024 loan"*; the old *"compare
    vintages within a year"* was read that way. (3) Spelling stays as the tabs have it (*grey*, *coloured*).

- **Built, 3 Oct 2026: the audit workbook's tie-out findings fixed, and a random pocket** (branch
  `pocketbook-audit-fixes`, on `pocketbook-voice` and `pocketbook-audit-tieout`). The tie-out
  (`pocketbook/docs/audit-tieout-2026-10-03/TIEOUT.html`) found no arithmetic error and seven findings on what the
  workbook says and shows. Then the firm: *"tying out one thing that should prove everything if you picked
  randomly"*, chosen *"Random, seed stamped"*. Words follow `pocketbook/VOICE.md`.
  - **The random pocket.** The audit opens on a pocket drawn uniformly from the tested pockets (every pocket of the
    Run's grids with a GCO p-value on the comparison that decides it), not the top flagged one. Seed:
    `perm.seed_of("the audit workbook's pocket, selected at random", <the file's SHA-256>)`; the pockets sorted by
    their key (grid|band|segment, as text), numbered from 0; the pick is seed mod their number. Run stamp has a
    section for it (the pocket, the population, the seed, how it was drawn), and One pocket's Selection note says
    it at the top (*"FICO x CHANNEL: (marked missing), Online, selected at random from the 18 tested pockets ...;
    seed 13751448919744042928"*). Shuffle test lists that pocket's shuffles. Dropdowns unchanged.
  - **Findings fixed.** (1) Every By hand step now names exactly the loans its formula takes (`by_hand()`: scope,
    the columns whose text entries are excluded, what the status bar shows); rest of its band, Loans' Count, Loans
    with a loss and Rows in and out's "Less:" lines were short of a filter. (2) Definitions say what the formula
    computes (*Avg line, whole book*: per loan with a booked amount). (3) New rows for every gap RANR vs GCOs shows:
    RANR + GCOs for the pocket and the book, and RANR and RANR + GCOs against the rest of the book and of the band,
    each rate, gap in points and dollars (the tab's sign), against the Run's. (4) Each booked total is named by its
    population (*every loan with a booked amount*, *loans with a GCO*, *loans with a RANR*, *loans with a GCO and a
    RANR*), with a reconciling row, *loans with no GCO amount*, tied to a billionth of the book. (5) Shuffle test
    part D: the picked pocket's family (its grid, same comparison), the Run's count and p-value, rank, p × tests ÷
    rank, the adjusted p-value in Excel beside the Run's, the rule written out; live with One pocket's pick through a
    rank-ordered list on `_lists`. (6) The random default makes the listed shuffle test a sensitive one when the pick
    is (this scenario's: p 0.52). (7) Every One pocket row is as tall as its longest wrapped cell, the step label
    included; Run stamp, Rows in and out, Bands and Shuffle test likewise; Start here's title no longer clipped.
    One pocket: 60 figure rows (was 37).
  - **Tie-out re-run** (section 13 of `TIEOUT.html`; `compare_rerun.py`, `build_rerun.py`; `tieout.py` draws the pick
    itself from the file's bytes): same 50,000-loan file (SHA-256 9b41…0681), 241 comparisons, 0 differ, 0 ✗ on
    any sheet. The pick drawn independently is the workbook's; all 60 rows of the random pocket three ways (57 to
    1E-9, 3 shuffle rows within Monte Carlo error); two more pockets on the dropdowns; part B's 10,000 listed
    shuffles counted at the independent line (5,227 = Excel = the Run); part D's 18 adjusted p-values against
    Benjamini-Hochberg worked out from the listed p-values (exact) and the independent shuffles (MC); RANR vs GCOs'
    row and Whole book against the audit and the independent figures. Following finding 1's By hand now gives
    Excel's $213,994,598.67 (the old words gave $214,034,283.10).
  - **Tests:** `tests/test_audit_2026_10_03.py`, 17 (was 13): the default is the random pick, worked out in the test
    from the file's SHA-256 and the hidden sheet; the pick is the same for the same file and moves with the seed;
    every By hand step's population matches its formula's criteria (both parsed, 26 rows; the parser itself shown a
    missing filter); part D ties to Benjamini-Hochberg worked out in the test; the new RANR / RANR + GCOs band gaps
    and dollars and the booked totals worked out from the CSV. Planted bugs: 5 new in `tools/mutation_check.py`
    (pick ignoring the seed; pick drawn from untested pockets; part D's rank one low; rest of band's By hand
    without its GCO filter; RANR dollars against the band with the Run's sign), and the old "rest of the book
    holding the pocket" repointed to the renamed test: 9 of 9 audit bugs caught with no display; every entry's old
    string occurs once (672). Pictures: `pocketbook/docs/audit-2026-10-03/` replaced. Full suite, no display:
    1,055 passed, 14 skipped (all tkinter missing, as before), 0 failed (78 min); the audit tests again on the final
    code, 17 passed.
  - **For the firm to decide:** (1) The pick is drawn from tested pockets only; an untested pocket (too few losses)
    is never the default, since it has no shuffle test to show. (2) Part D follows One pocket's pick through its
    grid and comparison; a pocket alone in its band is listed in the book-side family.

- **Built, 3 Oct 2026: the audit workbook's review fixes, and the advice sweep** (branch
  `pocketbook-audit-review-fixes`, on `claude/keen-franklin-4l01un`). Four bugs found by reading the code, each
  with a failing-first test in `tests/test_audit_review_2026_10_03.py` (6 tests) and a planted bug:
  (1) pockets were found by MATCH on their names, which reads `~ * ?` as wildcards: a segment `Br~anch` left One
  pocket's row blank (56 ✗), `<B*` and `On"line` sent part D to another pocket's row, and `=A` was written to the
  hidden sheets as a formula. Names are now found with EXACT (`audit.find`), part D and the allowance's COUNTIFS go
  by grid number and the pocket's row on `_pocketbook`, In this pocket / band compare with EXACT, every COUNTIF
  criterion built from text is literal (`audit.crit`: `=` first, `~ * ?` escaped), and every name is written as
  text. Tested on segments `Br~anch`, `On"line ` (quote, trailing space), `<B*`, `10`, `1?`, `=A`, `>500`: every
  figure ✓ in LibreOffice. (2) control characters are stripped from the Loans sheet's hand-written XML (a loan number
  `L\x015` made it unreadable). (3) any audit failure other than an open file is a Run line, *"Couldn't write the
  audit workbook: <type>: <message>"*, and the Run finishes (it used to end before "what ran.yaml"). (4) more loans
  than 1,048,575 skip the audit with a Run line saying why. Found on the way and left for its own task: Set up
  itself refuses a control character in a column's first sample values (openpyxl, Columns tab).
  - **Advice sweep** (the firm, 3 Oct 2026: *"literal facts, calculations, our rules around leaving comments are
    fine. stuff like this i don't ask for"*): 15 strings in the audit workbook and the Glossary rewritten or cut,
    each listed before and after in `pocketbook/docs/voice-2026-10-03/ADVICE-SWEEP.md` (e.g. *"If the two tests
    point in opposite directions, the pocket warrants a closer look"* removed; Borderline now states the 2-standard-
    error rule instead of *"the flag serves as a caution"*).
  - **Checks:** every `tools/mutation_check.py` entry's old string occurs once (678); the 6 new planted bugs and the
    11 earlier audit and Glossary ones, 17 of 17 caught with no display. Full suite, no display: 1,061 passed, 14 skipped (all tkinter missing, as before), 0 failed (82 min).

- **Docket answers, 3 Oct 2026** (the form at claude.ai/artifact/Sx6tUKKWYHHQhN9wN75jTV):
  1. Merge the audit workbook (#418): *Merge it*.
  2. While Codex is over its limit: *CI + independent review* counts as reviewed, noted on the PR.
  3. The 277 rewrites: *"what are you asking"* — the question was unclear; re-asked in plain terms.
  4. Lifetime-to-date: *"this is the kind of garbage i do not want at all ... literal facts, calculations, our rules
     around leaving comments are fine. stuff like this i don't ask for"*. Rewritten to a literal definition; the rule
     added to `pocketbook/VOICE.md` (facts, calculations and rules only; no advice or interpretation).
  5. Random pick: *Tested only*, *"how will this work"* — explained in the session.
  6. Look tab charts: *"show me the before and after of your rec"* — open; a before/after picture to follow.
  7. Public-data rehearsal (#407): *Revive*.
  8. Filter limits: *"hard to understand it just seems vague without context"* — open; to be re-asked with an example.
  - **Next (agreed by silence):** ship #418, then revive #407.

## 7 · Standing rules for new items

New idea -> add a line here (one sentence, why it matters). New lesson
found in any build -> `TEMPLATE_CONTRACT.md` carried lessons (L-series),
not here. Anything touching the watchlist boundary or licensing -> gets a
research pass before a spec, no exceptions.

---

## Done log

- 2026-10-04 -- **PocketBook: the public-data rehearsal revived on current code** (draft #407). The firm: *"Revive"*. Main merged in without conflicts; the three 29 Sep fixes were not on main another way and are kept. Rerun on SBAnational and LendingClub's own file (the SBA FOIA file could not be downloaded from the sandbox), every workbook calculated with LibreOffice: Set up and Run complete, the 29 Sep effects reproduce, and Pockets' Worse? matches the Python reading. Two defects fixed with 4 tests and 2 planted bugs, both caught: a percent-text band column refused as missing, and a p-value of 2.5e-315 breaking a New variables formula. Suite 1,081 passed, 14 skipped. §6d has the detail.
- 2026-10-03 -- **PocketBook: the audit workbook's review fixes, and no advice.** Pockets found by exact name, not by MATCH's wildcards (a segment `Br~anch` blanked every figure); control characters stripped from the Loans sheet; an audit failure no longer ends the Run; past Excel's row limit the audit is skipped with a reason. 15 strings of advice or interpretation cut from the audit workbook and the Glossary, under the firm's new rule. 6 tests, 6 planted bugs, all caught. §6d has the detail.
- 2026-10-03 -- **PocketBook: the audit workbook's tie-out findings fixed, and a random pocket.** The firm: *"tying out one thing that should prove everything if you picked randomly"* (*"Random, seed stamped"*). The audit opens on a pocket drawn from the tested pockets, seeded from the file's SHA-256 and stamped; every By hand step filters what its formula takes (a test parses both); every gap RANR vs GCOs shows is proved; booked totals named by population; Benjamini-Hochberg worked out on a visible table; no overlapping rows. Tie-out re-run: 241 comparisons, 0 differ. 17 tests, 9 of 9 audit planted bugs caught. §6d has the detail.
- 2026-10-03 -- **PocketBook: its voice.** The firm, on *"Every loan whose band and segment are the ones picked"*: *"it does not sound like something a human would type"*. `pocketbook/VOICE.md` sets the register (a credit-risk workpaper for analysts, managers, validators and auditors; the website's client-copy rules don't apply) with before and after patterns, the firm's own first. The audit workbook (203 strings) and the Glossary (74) are rewritten to it, wording only; `docs/voice-2026-10-03/REVIEW.html` numbers all 277 for the firm to mark. Full suite 1,051 passed, 14 skipped; 6 of 6 audit and Glossary planted bugs caught. §6d has the detail.
- 2026-10-03 -- **PocketBook: the audit workbook.** The firm: *"show the calculations it makes on one set of things and prove out each one"*, and *"how to do them by hand"*. Control's *Also write the audit workbook?* makes the Run write `<book> - audit.xlsx`: Run stamp (file, SHA-256, settings, seed), Rows in and out, Bands, Loans (each band a formula), One pocket (a live Grid / Band / Segment pick, 37 figures each written out, worked out by COUNTIFS/SUMIFS on the loans, tied to the Run's, and how to do it by hand) and Shuffle test (a 10-loan example, and every shuffle of the default pocket whose COUNTIF gives its p-value). 33 s and 23.8 MB at 185,000 loans. 13 tests, 4 planted bugs, 4 caught. §6d has the detail.
- 2026-10-03 -- **PocketBook: Summary's vintage chart and grey rows.** The firm: *"Could the summary tab have vintage graphs as well?"*, chosen *"Pocket vs rest vs book"*; and low unit counts *"grayed out to a degree"*, by a number of its own. Under the Summary table, one row against the rest of the book and the whole book by origination year, on any Summary measure, following Only loans where, thin points left off; at the top, Grey rows under [50] loans, read by nothing else. 5 tests, 4 planted bugs, 4 caught. §6d has the detail.
- 2026-10-02 -- **PocketBook: Avg line and × book.** The firm: *"I want to start including and using booked dollar averages so more easily demonstrate how line assignments look in pockets"*. Summary gains Avg line (booked dollars per loan, the average committed line) and × book (that over the whole book's) right after Booked $, in every filter view; RANR vs GCOs' gross block ends on the same two, shaded as Grids' Loan size, never red or green; the Glossary gains the term. 8 tests, 2 planted bugs, 2 caught. §6d has the detail.
- 2026-10-02 -- **PocketBook: a Glossary tab.** The firm: *"Maybe a nice glossary of terms in the workbook should be there"*. A grey tab right after Start here, written by every Set up and Run: 25 terms, each with what it means and an example in the book's own figures from the last Run (*"the book keeps $12.80 per $100 booked"*), made up before the first. Start here links to it; the bank checklist has a 4.10 for it. 8 tests; 2 planted bugs, 2 caught. §6d has the detail.
- 2026-10-01 -- **PocketBook: a third filter, with a size limit.** The firm: *"I thought we discussed two filters plus date"*; chosen, Origination year plus two more filters with a size limit. Filter 3 sits beside Filter 2 everywhere (launcher, Control, Grids, Summary, Compare's Lines by and Panels by, Record and the Run's line); every value alone, pair and triple holds together. Three filters may make 150 views of each grid (6 × 5 × 5), refused past it by the launcher and the Run; the launcher shows the cost. 15 tests, 3 planted bugs added and 13 repointed. §6d has the detail and two points for the firm.
- 2026-10-01 -- **PocketBook: Set up's suggestions from a sample of the grids.** The firm, on Set up taking over 3.5 minutes at 184,937 loans and 168 grids: *"Will the quick estimates be as accurate? … Test it and let's see"*. Tested on ten synthetic books of 17,000 and 185,000 loans: a sample of 28 grids matched every grid at Control's rounding in every book, at about 80 seconds against 265. Fewest loans is never sampled. Run still works each suggestion out from every grid, and says so beside it where the estimate was different. 7 tests, 3 planted bugs added and 1 repointed, 4 of 4 caught. §6d has the table.
- 2026-10-01 -- **PocketBook: the bank checklist says to save the extract as CSV first.** The firm, on reading an .xlsx being about 20 times slower than CSV (5.4 s against 0.3 s at 17,000 × 70, read at Set up and at every Run): *"Yes definitely csv first then"*. Step 6.1 says how (Excel, Save As, CSV UTF-8) and 6.2 marks .csv as best; .xlsx still works. Checklist HTML and PDF rebuilt; test_bank_checklist 10 passed.
- 2026-09-30 -- **PocketBook: errors on the window, not in Notepad.** At the bank, Run with the extract open in Excel became a PermissionError traceback read in Notepad. The firm: *"It would be a lot easier if these kinds of errors just displayed on screen in the huge white space allotted"*. An extract that can't be read (open in Excel, OneDrive syncing, gone) is now a plain refusal naming the file, and the extract is read once per Run. Anything unexpected shows on the page with its type, its message and **Copy details**. 10 tests added and 2 changed; 8 planted bugs added, 8 caught, and 4 display-only ones caught by hand. §6d has the detail.
- 2026-09-30 -- **PocketBook: a number column too few-valued to cut gets one band per value.** The firm, at the bank: *"So it refuses to run some stuff because it cannot band"*, then *"Yes that's fine"*. Major Derogatories (0 to 8, most loans at 0) no longer stops the Run: each value is its own band, labelled 0 to 8, and the Run says so; Columns suggests Category without changing the answer. More values that still collapse are cut as far as they go; a single value is refused, naming the two fixes; typed edges always win. §6d has the detail.
- 2026-09-30 -- **PocketBook: two filters and the Compare chart.** The firm: two filters *"independently and in conjunction with each other"*, and a graph that is *"not vintage analysis only"*, e.g. *"vintage analysis mixed with like underwriter/system approved"*. Grids and Summary take a second filter (both at once is AND); a Compare tab draws each filter value as a line across a band column or the years, with panels by the other filter on one scale and thin points left off. §6d has the detail.
- 2026-09-30 -- **PocketBook: Paid, cost, kept shows each pocket's gross booked, GCO and RANR.** The firm: *"so we can also see if pockets are straight negative on returns"*. Booked, GCO, RANR and RANR rate after Loans; a pocket losing money outright in red and counted beside the Grid dropdown; totals that add up to the whole book. 6 tests, 7 planted bugs caught, tie-out 481 of 481 TIED. §6d has the detail.

- 2026-09-30 -- **PocketBook: the Summary tab.** The firm: *"a few matrices where it lists out a chosen band on the left and shows real calculated metrics ... Same with RANR. They'd be across the top"*; the ratio *"Charged off / booked"*; bad loans *"Yes do this"*. One band column down the side, with loans, bad loans, booked, charge-offs, × book and RANR across, plus each one's share. It can be filtered by the Filter by column. The engine does the arithmetic and ties it out; nothing is tested. 3 tests, 7 planted bugs, 7 caught; tie-out 1,274 of 1,274 cells TIED. Full suite in shards: 888 passed, 7 skipped, 0 failed. §6d has the detail and three points for the firm to confirm.
- 2026-09-30 -- **PocketBook: Filter by, apart from Split by.** The firm: *"Wait only works on split by? Isn't that for like above and below median"*, then *"Yes hoping to have this by morning"*. Grids' *Only loans where* now reads its own launcher pick (any category of 6 values or fewer, or ORIG_YEAR, the year of the Origination date column), whatever the split does; ORIG_YEAR can also split, for the consistency test across vintages. 6 tests, 13 planted bugs added and 4 repointed, all caught. §6d has the detail.
- 2026-09-28 -- **PocketBook: every figure in both workbooks tied out to the loan file** (`pocketbook/docs/tie-out/2026-09-28-full/`, the PDF and `roster.csv`). The firm, on the first tie-out's 64 figures: *"That tie out covered 60 things? It's pretty small"*. 15,650 cells read out of the bleed workbook (all 40 dropdown views) and a Test-new-variables workbook (the test_scout book, two candidates shortlisted), each worked out again from the loan file with no PocketBook code: 13,403 tie, 1,030 tie within sampling error (shuffle and forest figures), 16 differ, 5 could not be checked, the rest names, echoed answers and words. Found: the Look chart counts a value exactly on a bar's edge in the bar below (`look.py:195`, `:209`: 12 x 0.1 = 1.2000000000000002; UTIL's bars off by 1 to 5 loans), and six verdicts rest on shuffled p-values either side of 5% within sampling error, one of them behind Start here's *4 short $3,248,654*. Not fixed here.
- 2026-09-28 -- **PocketBook Goal 4: the tree is the main path, checked on later loans, and the shortlist regressed together** (OC-51; `pocketbook/docs/NEXT-GOAL.md` Goal 4, all seven ticked). The firm, 27 Sep 2026: *"shouldn't it regress all of those identified variables if it actually deems them important? import --> tree runs --> tree guesses on 2024 data if 2022-2023 are used to build branches --> regress shortlist?"*, then *"yes build it out"*. A cutoff date on Control replaces *Find on 70%* (suggested, never chosen); after the pre-spec is written the tree scores the held-back loans (*"Built on …: AUC 0.63. On …, unseen: 0.60."*, logged as a touch of the holdout); every shortlisted candidate goes into one logistic regression on the held-back loans with the pockets as control dummies (`joint.py`, statistics.md B10: a likelihood ratio test per candidate, the allowance across the shortlist, separation refused in words, correlated pairs named); New variables leads with both. 771 tests (15 new: `tests/test_together.py` and 7 in `tests/test_scout.py`), 766 passed and 5 skipped; 24 planted bugs added and 6 repointed (431 in all), each put back alone with every earlier one whose test was rewritten: 71 of 73 caught on the first pass, the 2 missed caught after their tests were strengthened. The walk's Part C pictures retaken and the procedure and checklist PDFs rebuilt. A scouting Run at 17,000 × 80: about 73 s before, 75–77 s after.
- 2026-09-27 -- **PocketBook: Choose tests in the order you work down it.** The firm, on the "What are you running?" table: *"it just isn't necessary to have anything there, really. i would prefer that screens are ordered more sensibly- this one seems all over the place"*. The outcome rows' "· every measure" is gone (their cells are empty), and the rows no longer follow the extract: number columns (bands, split), then categories (segment), then the outcome and dollar columns, then the key and date in grey, each group in the extract's order, with a small blank gap between groups and no headings. Same order for Test new variables, so the toggle never reshuffles. Also fixed: in Test new variables a table 251-280 px tall lost its last rows with no scroll bar. The other steps were checked and already in task order (Answers needed sorts by cell; the open questions by row). 3 tests, 6 planted bugs caught; steps 4, 5, 22, 23 and 24 retaken and the procedure PDF rebuilt.
- 2026-09-27 -- **PocketBook: Test 4 settled.** Asked on the docket whether the firm's Test 4 (3% uplift) should keep answer C's label *Losing more, profit holding* or stay blank; the firm picked **keep the label** (recommended). No code change: `tests/test_profit.py` already expects it. Nothing is left open with the firm; the next goal waits on the bank-machine trip.
- 2026-09-27 -- **PocketBook: the firm's answers to the walk's design calls, built** (A to K, and tenet T2's sweep). 12 tests, 20 planted bugs caught; the procedure's changed pictures taken again and its PDF rebuilt. §6d has each answer.
- 2026-09-27 -- **PocketBook bank-machine checklist** (`pocketbook/docs/BANK-MACHINE-CHECKLIST.pdf`, and `tools/bank_kit.py` to make what to carry). Goal 3 item 3; §6d has what was verified and what is marked "check this".
- 2026-09-27 -- **Origination Cube renamed PocketBook** (`origination-cube/` → `pocketbook/`; package, command, launcher file, memory folder and variable). Everything a machine kept under the old names is still read. §6d has the list of what was left as written.
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
