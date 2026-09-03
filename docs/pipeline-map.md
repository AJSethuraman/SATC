# How a client's answers become documents

A map of `client-documents/`, written for someone who has never opened it.
Every function and file named here is real; nothing is illustrative. Produced
26 August 2026 while building `tests/test_scenarios.py`, because scenario tests
are impossible to write without first knowing what owns what.

---

## 1 · The shape of it in one paragraph

A prospect fills in the website form, and the submission lands as a row in a
workbook. A preparer opens that row and runs a **consultation interview** — a
branching sitting driven by a YAML schema. Those answers
are turned into **merge fields**, **a price**, and **a list of documents to ask
the client for**; the three together are an **engagement**, written to disk as a
folder of JSON. The engagement is then merged into **HTML templates** to produce
the documents the client receives. Nothing is typed twice, and a document with a
hole in it is never written.

```
 leads.xlsx  ─┐
 (a row)      ├─ leads.normalise ─→ a lead ─┐
 by hand   ───┘                             │
                                            ▼
                        interview.Interview  (registry/interview.yaml)
                        asks · branches · offers the lead as a CLAIM
                                            │
                                     answers (a dict)
                                            │
             ┌──────────────────────────────┼──────────────────────────────┐
             ▼                              ▼                              ▼
   schedules.derive              pricing.price                   requests.for_answers
   facts → Schedules A…SE        LineItems · EstimateTotal        RequestList
   (interview.yaml `implies`)    Assumptions                      (document-requests.yaml)
             │                   (fee-schedule.yaml)                       │
             └──────────────────────────────┼──────────────────────────────┘
                                            ▼
                              intake.finish   ← THE GATES
                        hard-no · decision · price · create
                                            │
                                            ▼
                        engagements/<YYYY-NNNN>/record.json
                        engagements/<YYYY-NNNN>/interview.json
                                            │
                              cli.build_record  + firm-settings.yaml
                                            │
                                            ▼
                        packaging.documents_for → which documents
                                            │
                                            ▼
                          merge.render  (satc-handoff/04-TEMPLATES/*.html)
                        refuses rather than shipping a hole
                                            │
                                            ▼
                        out/…  ·  a signing pack folder + MANIFEST.json
                                            │
                                            ▼
                              consistency.report — do they agree?
```

---

## 2 · Stage by stage

### 2.1 The lead — `leads.py`

**Owns:** one shape for "somebody who might become a client", whichever door
they came in by.

* `leads.from_row(header, row)` reads one row of the leads workbook. The row's
  `Raw JSON` column is the website submission verbatim and **wins**; the flat
  columns (`Name`, `Email`, `Services`, …) are the fallback for a row somebody
  typed by hand.
* `leads.by_hand(name=…, email=…, phone=…)` builds the same shape for a phone
  call. It needs at least one of name/email/phone — "without one of the three
  there is nobody to come back to" — and everything the website would have
  asked is simply **absent**, which is not the same as answered "none".
* `leads.normalise(lead)` makes the list fields lists, so nothing downstream has
  to know whether the answer arrived as `["individual_tax"]` or
  `"individual_tax, bookkeeping"`.

**A lead is a claim, never a fact.** Nothing it says is ever an answer.

### 2.2 The interview — `interview.py` + `registry/interview.yaml`

**Owns:** the consultation call as a question flow, and the translation from
answers into merge fields.

`registry/interview.yaml` is the file to edit when the interview changes. Nine
sections, 49 questions — nowhere near all of them asked of any one client, because
`showIf` decides which half of the schema applies. Each question carries:

| key | meaning |
|---|---|
| `type` | `single` · `multi` · `list` · `text` · `textarea` · `number` · `integer` |
| `required` | cannot be left blank |
| `showIf` | when the question is asked at all |
| `supplies` | which merge field(s) the answer fills |
| `internal: true` | it never prints; `internal_reason` says why it is asked |
| `feeds` | it drives `LineItems` (a price) or `RequestList` |
| `derived: true` | never asked — software works it out |
| `prefill` / `prefill_map` / `prefill_index` | which lead value to OFFER |
| `options[].hard_no` | ticking it is work the firm does not take |

The engine:

* `Interview.next_question()` / `.answer(qid, value)` drive a sitting.
  `answer()` does two things beyond storing the value — it **derives** the
  federal schedules (`schedules.apply`) and it **retracts** any answer whose
  question is no longer visible. Change `joint_return` to "no" and the spouse
  name is deleted, because left behind it reaches a document with no signature
  block for it.
* `visible(question, answers)` parses `showIf` — it is **parsed, never
  `eval`-ed**, and a condition the grammar does not cover raises. The supported
  grammar is `id == 'x'`, `id != 'x'`, `'x' in id`, joined by `and`/`or`.
* `prefill_for(question, lead)` returns what the website said, translated
  through `prefill_map`. Three outcomes per value: absent from the map → dropped
  quietly; mapped → translated; **mapped to `~` (null) → the whole prefill is
  dropped**, because the lead said something that does not resolve to one
  answer. `prefill_is_answerable()` then says whether the claim could be
  accepted with one keystroke.
* `hard_no(answers)` returns the labels of any ticked option marked
  `hard_no: true`. `review_flags(answers)` returns things a human should look at
  — today, one: more rentals than local returns.
* `compose(answers)` → the merge fields the interview owns. It also **builds**
  several: `FederalReturns` ("Form 1040 with Schedules A, C, and SE"),
  `EntityType` ("an Ohio limited liability company taxed as an S corporation"),
  `StateReturns`, `LocalReturns`, `AdditionalForms`, and the exact-inverse pair
  `OwnerReturnsPrepared` / `OwnerReturnsElsewhere`.
* `billable_counts(answers)` keeps everything tagged `feeds:` with the
  engagement, so an estimate can be rebuilt later from what was counted then.

### 2.3 The schedules — `schedules.py`

**Owns:** turning facts into federal schedules. **It decides no tax treatment of
its own**; the mapping lives in the registry, on the `return_features`
question's own options:

```yaml
- { value: "rentals", implies: E1, label: "Property they rent out" }
- { value: "farm",    implies: [F, SE], label: "Farming" }
```

`schedules.derive(answers)` returns the schedules **and the fact behind each
one**, so both front doors can show the preparer why. `schedules.apply(answers)`
writes the result into `answers["federal_schedules"]` — unless
`federal_schedules_override` is set, in which case the preparer wins.

The interview asks the fact ("Property they rent out"), never the conclusion
("Schedule E"), on the firm's instruction: *"the interview needs to ask
questions that then mean we definitely need a schedule."*

### 2.4 The price — `pricing.py` + `registry/fee-schedule.yaml`

**Owns:** every number a client is quoted. `pricing.price(answers)` returns
`LineItems`, `EstimateTotal` and `Assumptions`, ready to merge.

The schedule has five parts:

| block | what it does |
|---|---|
| `base` | the fee per federal return. `1040` is a **ladder of four tiers**; `1065`/`1120S`/`1120` are single "from" prices |
| `amendment` | three cases keyed on `amendment_reason`; one of them **replaces** the whole estimate |
| `per_unit` | counted lines — states, localities, rentals, farms, K-1s, brokerages, foreign accounts, extensions, records sorting, owner K-1s, Schedule C |
| `per_form` | one flat price for a named situation the client ticked (home sale, HSA, 1095-A …) |
| `assumed` | work that carries **no price** — it states what the fee assumes and what happens when the assumption breaks (`beyond: hourly`) |

Rules worth knowing before touching any of it:

* **A gate keys on what is ON the return, never on how many.** A client can tick
  the rentals schedule and leave the count blank; a gate reading that as zero
  sends a landlord to the cheapest package. Gate operators: `schedules_none`,
  `schedules_any`, `schedules_none_of`, `answer_is`, `answer_includes`,
  `any_of`. An unknown operator raises rather than silently never matching.
* **The ladder is read most-specific-first, and the client gets the cheapest
  package they are eligible for.** `derive_tier` totals the whole estimate on
  each eligible rung and picks the lowest, because a rung with a bigger
  allowance can cost more up front and less overall.
* **`includes:` is followed, `covers:` is printed.** A rung inherits the
  allowances of the rung below. `supersedes:` **replaces** an inherited covers
  line — that is what stops a Standard estimate listing both "The standard
  deduction" and "Itemized deductions".
* **`form_when:` makes a counted line fire on the schedule rather than the
  count**, so a blank count reads as one rather than none.
* **An unset amount is `[CONFIRM: …]` and it poisons the total on purpose**, so
  the estimate refuses to render rather than quoting a client nothing.
* **Every client-facing sentence the estimate assembles lives in `phrases:`** in
  the same YAML — "Includes: {list}.", "capped at {n} — beyond that the time is
  billed at {rate} an hour". Editing a word is editing YAML, not Python.

### 2.5 What to ask the client for — `requests.py` + `registry/document-requests.yaml`

**Owns:** the `RequestList` printed under "What to send us" on the onboarding
letter. Each entry is a `document` + `detail` and an optional `when:` gate —
**evaluated by `pricing.gate_holds`, the same evaluator that decides the
package**, so the two can never drift into asking for documents nobody has.
Entries print in registry order, not answer order.

### 2.6 The gates, and creating the engagement — `intake.py`

**Owns:** everything that has to be true before an engagement exists. Both front
doors go through it; a control that lives in one front door is one the other
silently skips.

* `intake.compose_record(answers)` — the merge fields plus `LetterDate`,
  `_season`, `_return_type`, `_billable_counts` and `RequestList`. Creates
  nothing, so a UI can preview.
* `intake.finish(answers, store=…)` — the gates, **in this order**:
  1. a **HARD NO** refuses (`override_hard_no=True` takes it anyway and records
     that it was overridden);
  2. `decision != "yes"` declines;
  3. the record is composed;
  4. it is **priced before the store is touched**, so a malformed schedule
     cannot leave half an engagement behind;
  5. the engagement is written.

  It returns an `Outcome` — `created` / `refused` / `declined` / `error` — not a
  printed message. Refusing, declining and being unable to price are three
  different things to a reader, and only `created` writes anything.

### 2.7 The store — `engagements.py`

**Owns:** engagements on disk. Deliberately a directory of JSON rather than a
database: one engagement is one folder a human can open and repair.

`EngagementRef` is `YYYY-NNNN`, allocated by `next_ref()`, **never reused**, and
validated at the door — it is byte-compared across every document, so a
malformed one is refused rather than discovered on a client's letter.

### 2.8 The firm's own values — `settings.py` + `registry/firm-settings.yaml`

**Owns:** everything identical on every client's documents — the firm name and
address, the preparer, the billing contact, the payment sentence, and the
**materials deadline** (one per return type per season, set at three weeks
before each filing deadline).

`firm.firm_fields(season, return_type)` produces them. `cli.build_record` folds
them in **underneath** the record, so a per-engagement override is honoured.
`firm.open_decisions()` walks the file for surviving `[CONFIRM: …]` markers;
`firm.blocks_render(path)` says whether a given one would actually stop a
document, because `hard_no` is policy and no template merges it.

### 2.9 The merge — `merge.py` + `satc-handoff/04-TEMPLATES/*.html`

**Owns:** template + record → client-ready HTML. Three markers:

```
&lt;&lt;Field&gt;&gt;               substitute a value (HTML-escaped)
[[IF Flag]] … [[END IF]]           keep or drop the block
[[EACH List]] … [[END EACH]]       repeat once per item, fields as <<Item.X>>
```

`merge.render(html, record, required_lists=…)` **raises rather than returning a
document with a hole in it**. It refuses on:

* an unresolved `<<Field>>` — "the one bug that actually costs you a client";
* an unresolved `[[BLOCK]]`;
* a surviving `[CONFIRM:` — a decision nobody has made;
* an empty **required list** — because an `[[EACH]]` over an empty list leaves
  no token behind to catch, which is how a fee estimate once rendered a blank
  services table under "Total estimate $785". Which lists may be empty is
  declared in `registry/fields.yaml` and passed in by the caller.

**These guards read the RENDERED TEXT, not the record.** A value no template
merges can never fail them — worth remembering, because it is how a guard test
once went on passing while checking nothing.

The `<div class="ref">…</div>` block at the foot of each template is
screen-only reference material and is stripped before anything else happens.

### 2.10 Which documents, and the atomic pack — `packaging.py`

**Owns:** what a client actually receives. `packaging.documents_for(record)`
keys on `_return_type`:

| return type | engagement letter | always | plus |
|---|---|---|---|
| `individual` | `tax-letter` | `fee-estimate`, `onboarding-letter` | `records-release` **if `PriorFirm`** |
| `s_corp` / `partnership` / `c_corp` | `business-letter` | same | same |

It **raises** for a record with no `_return_type` rather than guessing, because
guessing sends an individual engagement letter to a corporation. The invoice is
never in the pack unless asked for: an invoice is not something a client signs.

`cli.cmd_package` writes the pack **atomically** — every document renders to a
temporary directory first, and the output folder is touched only once all of
them have succeeded. A pack with a hole in it is worse than no pack, because the
client signs what arrived. A folder holding a `MANIFEST.json` this command wrote
is replaced wholesale; a folder holding anything else is somebody's and is
refused.

### 2.11 Do the documents agree? — `consistency.py`

**Owns:** the question `doctor` does not ask. Everything resolved, everything
rendered — do the documents tell one story? `consistency.report(record,
rendered)` returns named `Check`s, and `cli.py check <record.json>` prints them.

The joins today:

1. one engagement reference across the package;
2. one letter date;
3. the letter and the estimate state one scope (all four scope lines);
4. **nothing is billed outside the scope** — the schedules named by the estimate's
   *line items* against the schedules named by the letter's `FederalReturns` and
   `AdditionalForms`. The reverse direction is deliberately not checked: a scope
   naming Schedule A with nothing on the estimate is correct, because it is
   inside the package price;
5. the total is the sum of the lines;
6. one materials deadline across every document that states one;
7. **the first deliverable / the K-1s are not promised before the materials are
   due** — two dates from two sources that nothing had ever compared.

### 2.12 The bill — `invoicing.py`

**Owns:** the estimate becoming an invoice. `invoicing.build(record, number=…,
billed=…)` reads the priced engagement's own `LineItems`, so the two documents
cannot disagree about the money. Three rules it enforces: the invoice carries
the estimate it came from; **billing over the estimate without a
`VarianceNote` refuses**; numbers are sequential and never reused.

`billed` is required and is **not** the engagement's period — `PeriodLabel`
means the tax year on the estimate and the period billed on the invoice, and one
shared value prints the wrong thing on one of them.

### 2.13 The front doors — `cli.py`, `web.py`, `editor.py`

Both front doors are thin. Neither decides anything: every gate lives in
`intake`, every price in `pricing`, every word in a registry.

`cli.py` (`python cli.py …`, or the `Makefile`):

| command | what it does |
|---|---|
| `interview` | run the sitting; creates the engagement |
| `from-lead` | a website payload → a record skeleton |
| `engagements` | list what exists |
| `doctor` | what is still blocking a real render, firm-wide or `--engagement REF` |
| `render` | a record or `--engagement REF` → HTML (+ PDF) |
| `package` | the signing pack, atomically, with a manifest |
| `invoice` | a priced engagement → an invoice |
| `check` | do the documents agree with each other |
| `price` · `hours` · `ladder` | set fees, see what each buys in hours, sanity-check the ladder |
| `sample` | regenerate `samples/tax-opening-package.json` from the demo answers |
| `demo` | the whole chain, from a fixture, in one command |

Two modes everywhere: **real** (default) writes nothing at all when a document
would be holed; **`--draft`** renders anyway, stamps every page, marks open
decisions in oxblood and puts `DRAFT` in the filename.

`web.py` is the same engine in a browser (`make web`, port 5051): the leads
list, an interview with prefills shown as claims, a review screen showing the
derived schedules **with the answer behind each one**, the outcome, and the
engagement. Every route answers both a human and a script (`?format=json`).

`editor.py` is the wording editor at `/templates` — it edits the prose sections
of the HTML templates in place and refuses to touch a merge field, a conditional
marker or an open decision.

---

## 3 · Where the state actually lives

Everything is files. There is no database.

```
client-documents/
├─ leads.xlsx                     REAL PROSPECT DATA. gitignored. Never read it
│                                 into a test or a fixture.
├─ engagements/                   gitignored — client data
│  ├─ _drafts/<sid>.json          a half-finished web interview
│  └─ 2026-0001/
│     ├─ record.json              the merge fields (what documents are built from)
│     ├─ interview.json           every answer, including the internal ones —
│     │                           red flags, the decision, the notes, the counts
│     └─ invoices/2026-0001.json  one file per invoice raised
├─ out/                           gitignored — rendered HTML and PDF
│  └─ <a pack folder>/MANIFEST.json   what is in the folder, and why
├─ registry/*.yaml                the five files below — the only place
│                                 decisions live
└─ samples/*.json                 fictional fixtures, in the repo on purpose

satc-handoff/04-TEMPLATES/
├─ SATC *.html                    the ten templates
├─ FIELDS - *.md                  one spec per template
├─ satc-doc.css · doc-page.js     shared brand assets
```

The record is **lossy on purpose**: it holds the merge fields, not the answers.
`interview.json` beside it holds why the engagement was taken on.

---

## 4 · What each registry file governs

| file | governs | change it to… |
|---|---|---|
| `registry/interview.yaml` | which questions are asked, when, what they supply, what each fact **implies** for the schedules, which options are a HARD NO | add or reword a question; change what a fact means |
| `registry/fee-schedule.yaml` | every price, every package gate, every allowance and cap, and **every client-facing sentence the estimate assembles** (`phrases:`) | set a fee; change what a package covers |
| `registry/document-requests.yaml` | the onboarding letter's "what to send us" list, and which client gets which line | change what the firm asks a client for |
| `registry/firm-settings.yaml` | the firm block, the preparer, billing, the payment sentence, the materials deadlines, the hard-no policy | move the office; set next season's deadlines |
| `registry/fields.yaml` | the merge-field registry: every field, its `source`, which templates use it, and **which lists may not be empty** | after a template gains or loses a token |

`registry/fields.yaml` is generated from the templates and reconciled by
`tests/test_registry.py`, in both directions: a template gaining a field fails
the build here rather than at a client, and so does a registry entry claiming a
template that no longer uses it.

---

## 5 · Invariants the pipeline depends on

These are the things that must stay true. They are also the list of ways an
editor — a person, or a future registry GUI — could break the pipeline without
producing an error:

1. **Every price is reachable.** A gate that can never hold is a package that
   can never be sold and a line that can never be billed. Every tier gate, every
   `per_form` entry and every `when:` must key on a question the interview
   actually asks, with an option value the question actually offers.
2. **Every question earns its place.** A question must either `supplies` a merge
   field, `feeds` a price or a request list, or be `internal: true` with a
   reason. A question nothing consumes is a question asked for nothing.
3. **Every merge field a template asks for can be produced.** By a question, by
   the firm settings, or by software. A field registered and unasked is a
   document that can never render — that was true of the whole entity half of
   the letter set once, and every business engagement refused while the tests
   passed against a hand-written sample.
4. **A gate keys on a fact, never on a count.** Counts go blank; ticked boxes do
   not.
5. **Anything a client is asked for is something they are charged for**, unless a
   package explicitly covers it. The two are derived from one set of answers by
   one gate evaluator, so a change to one has to move the other.
6. **A `supersedes:` string must match a line a lower rung actually says.**
   Reword the lower rung and the match silently stops, and the estimate starts
   offering two deduction methods again. `pricing.covers()` raises instead.
7. **Two documents in one package may not contradict each other.** That is what
   `consistency.py` is for, and it is the seam where every hand-found bug in
   this project has lived.
8. **A refusal writes nothing.** Not a partial pack, not a stamped draft, not a
   half-made engagement.
