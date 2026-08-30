# Visual review of every client document

**27 August 2026.** Every document `exercise.py` produces, plus the later-life documents
it renders in memory, opened in Chromium, screenshotted full-page, and read on the page —
not parsed. Screenshots are under `client-documents/out/shots*` (gitignored).

**This report changes nothing.** No template, code, test or registry file was edited. The
wording is the firm's. Where a fix is named, it is named and not made.

---

## Verdict

**No. If the firm picked this up tomorrow and sent a real client an opening pack, the pack
would be wrong in at least three ways a client would notice within a minute, and one way
that would look broken.** The three opening documents render correctly *only* if the
preparer runs `package`; the `render` command the CLI itself prints as the "Next:" step
writes HTML with no stylesheet beside it, which opens in Times New Roman with the masthead
mashed into one line — the exact plain-text bug the firm found, fixed in `package` and
still live in `render`. Every onboarding letter jumps from section **02 to 04**, and every
return delivery letter from **03 to 05**. If the client is an entity, the letter headed
"What we need from you to begin" asks a partnership for **every W-2 for the year, a photo
ID, and the Social Security number for everyone on the return** — there is not one
entity-specific request in the registry. Every fee estimate tells a W-2-only client that
"your foreign holdings are accounts rather than companies." Every fee estimate, invoice and
organizer letter prints a second physical page carrying nothing but the signature line.
And the four documents that come *after* the opening pack — delivery, extension,
disengagement, organizer — cannot be produced by any command a preparer can run, because
nothing in the software builds the lists they require. The engagement letter, fee estimate
and records release are, on the page, genuinely good documents. The pack around them is not
ready.

---

## What I actually did

| | |
|---|---|
| Scenarios run | 29 (27 created an engagement; 2 correctly did not) |
| Pack documents produced on disk | **82** |
| Later-life documents I rendered myself | 136 (135 via `merge`, following `LATER_FACTS`; 1 bookkeeping letter from a hand fixture) |
| Later-life documents re-rendered through the real front door (`cli.py render`) | 85 |
| **Documents opened in Chromium and screenshotted full-page** | **303** |
| Screenshotted pages I read with my own eyes | **29** |
| Documents printed to PDF and read page by page | 19 |
| Distinct templates covered | **12 of 12** |

**Baseline.** The run was made against the working tree between 01:20 and 02:00 on 27 August.
Another session was editing `client-documents/cli.py` in parallel (a `presend` gate landed at
02:01). I re-verified finding 1 against the file as it stands afterwards and it still
reproduces; the other findings are in templates and registries that were not touched.

Where two scenarios differ only in a count I read one screenshot and diffed the sources
rather than reading the second picture — and I diffed **every** pack document against a
baseline I had read, so nothing was skipped on faith. That diff is what established that
the three amendment packs and both flagged packs are byte-identical to `ind-simple`'s
(finding 8).

The rendered-page checks I wrote were proven by breaking documents on purpose — see
**Proving the checks** at the end.

---

## Findings, worst first

### 1 · `cli.py render` writes HTML that opens as unstyled plain text — CRITICAL

*Every document, every scenario, on the `render` path.*

`cmd_package` copies `satc-doc.css` and `doc-page.js` beside the documents (cli.py:483).
`cmd_render` does not. Its output is a bare HTML file whose two relative asset links resolve
to nothing.

What a client sees: Times New Roman, no masthead, no rules, no layout. `SAT`*`CLLP`*`Sethuraman
Accounting, Tax & Consulting` run together on one line. `Standard``Schedules, but nothing
that scales` with no gap. The `doc-page` element never upgrades, so `doc-page:not(:defined)
{visibility:hidden}` is the only thing standing between this and the page being invisible.

This is not hypothetical. `cli.py invoice` finishes by printing, verbatim:

```
Next:  python cli.py render --engagement 2026-0025 --docs invoice --out out
```

The tool tells the preparer to run the command that produces the broken file. `cmd_demo`
calls `cmd_render` and inherits it.

**Screenshot:** `/home/user/SATC/client-documents/out/shots-render/render-path-invoice.png`

**Fix (not made):** `cmd_render` needs the same four lines as `cmd_package` — after
`outdir.mkdir(parents=True, exist_ok=True)` at cli.py:1004, copy `satc-doc.css` and
`doc-page.js` from `TEMPLATE_DIR` into `outdir`. The PDF path is unaffected: `render_pdf`
already copies both into its scratch directory (cli.py:151).

**Why nothing caught it:** `exercise.py`'s `renders()` opens only `pack.glob("*.html")`. The
`render` front door is opened by nothing.

---

### 2 · An entity's onboarding letter is the individual checklist, verbatim — CRITICAL

*All four entity scenarios: `ent-1065`, `ent-1120S`, `ent-1120`, `ent-1065-many`.*

Section 01, "What to send us", on a letter addressed to **Northbank Tooling LLC**:

- **Every W-2 for the year** — "One for each employer, for you and anyone filing with you"
- **Photo ID** — "Only if we have not seen it before"
- **The Social Security number for everyone on the return** — "The numbers themselves. We do not need the cards"

That is the whole list. No trial balance, no bank or card statements, no general ledger, no
owner list, no prior-year entity return, no fixed-asset schedule.

What a client experiences: a partnership is asked for its owners' Social Security numbers
and a driving licence in order to file a Form 1065, and is asked for none of the records
the engagement letter's own section 04 says they are responsible for providing. A real
client either calls confused or sends the wrong things and the file stalls.

**Cause:** `registry/document-requests.yaml` has no entity-gated entry at all. The first
three requests carry no `when:`, and the file's own header says an entry with no `when:` is
"asked of everybody." The gate vocabulary already supports `answer_is: {federal_form: …}` —
it was simply never used here.

**Screenshot:** `/home/user/SATC/client-documents/out/shots/ent-1065__SAT-C_Onboarding_Letter_-_LLC_-_2026.png`

---

### 3 · The extension notice ships with no payment instruction, and points at the section that should have had it — CRITICAL

*All 27 scenarios.*

The opening paragraph reads: *"Your payment deadline does not move, **and section 02 tells
you what to do about that.**"* Section 02 is headed "An extension is more time to file, not
more time to pay" and contains one callout — *"Interest and penalties run from the original
due date on anything unpaid"* — and then stops. No amount, no deadline, no instruction.

The template's two payment branches are `[[IF PaymentEnclosed]]` and `[[IF
NoPaymentRequired]]`. `exercise.py:257` supplies `PaymentEstimated` and
`NoPaymentEstimated` — names that exist nowhere in `registry/fields.yaml` or the template.
Both branches drop. `EstimatedPaymentAmount: "$450.00"` never prints. The merge does not
refuse, because an `[[IF]]` on an absent flag is a legitimate drop.

`FIELDS - Extension Notice.md` names this failure in advance, twice:

> "A client who reads the 'interest runs from the original due date' callout and then finds
> no instruction underneath it concludes there is nothing to pay. That conclusion has to be
> a statement the firm made, not a gap it left."
>
> "Two independent booleans can both be false, which leaves section 02 with a warning and
> no instruction — **the worst possible version of this letter.**"

What a client experiences: a letter that warns them interest is running, does not tell them
how much or by when, and directs them to a section that says nothing. Then an
underpayment charge.

`doctor` does not catch it — it lists `<<ExtendedDeadline>>` and `<<PaymentDeadline>>` as
awaited fields and says nothing about the flags, because flags are not required fields.

**Screenshot:** `/home/user/SATC/client-documents/out/shots2/ind-standard__extension-notice__SAT-C_Extension_Notice_-_Ellwood_-_2026.png`

---

### 4 · A raw Python data structure prints in the body of the disengagement letter — CRITICAL

*All 27 disengagement letters `exercise.py` produced.*

Section 01, first paragraph:

> "As the **Ending this engagement** section of your engagement letter provides, either of us
> may end it in writing at any time. This is that writing. It covers **[{'Item': '2026
> federal and Ohio returns', 'Status': 'Complete'}]**, and it takes effect on June 30, 2027."

`<<ScopeEnded>>` is a scalar — the registry calls it "a phrase, not a code, that names
precisely what ends". `exercise.py:264` hands it a list of dicts. `merge._substitute_one`
(merge.py:138) does `html.escape(str(value))`, so a container becomes its Python `repr`.

What a client experiences: a Python literal, in the body of the most legally-exposed letter
in the set, in the sentence that defines what is being terminated.

**Screenshot:** `/home/user/SATC/client-documents/out/shots2/ind-standard__disengagement-letter__SAT-C_Disengagement_-_Ellwood_-_2026.png`

**Fix (not made):** `_substitute_one` should raise `MergeError` naming the field when
`value` is a `list`, `dict` or `tuple`. A scalar merge field handed a container is always a
wiring bug and never intended output — refusing is the same posture the engine already
takes on an unresolved field. Separately, `exercise.py`'s `LATER_FACTS` for this document
supplies `ScopeEnded` (a list) and `UpcomingDates`, where the registry wants a `ScopeEnded`
*phrase* plus the `WorkStatus` and `OpenDeadlines` lists; through the real front door the
same record is **refused** on `WorkStatus`, which is the correct behaviour and shows the
harness is not using the door the preparer uses.

---

### 5 · Four documents cannot be produced by any command a preparer can run — HIGH

`delivery-letter`, `extension-notice`, `disengagement-letter` and `organizer-letter` each
require a list (`ReturnsDelivered`, `ActionList`, `OutstandingItems`, `WorkStatus`,
`OpenDeadlines`, `Requested`) that **no Python in the project builds** — I grepped the whole
package. `render --engagement` reads the stored record only; the only other door is
`render <record.json>`, which means hand-authoring JSON.

`FIELDS - Tax Return Delivery Letter.md` says of `ActionList`: *"built from the returns,
not typed … Every amount is a pre-formatted string from the one money formatter — **a human
should never type a tax figure into this letter.**"* There is no other way to produce it.

Consequences visible on the page today:

- `doctor` reports **`organizer-letter` — "Blocked, and due now"** on *every* engagement,
  because `Requested` is never populated. A readiness tool that is red on every record for
  the same reason is the failure mode `fac6cea` was written about.
- The delivery letter's section 03 says *"the payment is a separate step and it has its own
  deadline — **see section 02**"*, and section 02's only guaranteed content is "Review your
  returns". The pay items that would make that pointer true live in `ActionList`, which
  nothing builds. On the harness's own facts the client with an **$88 Ohio balance due** is
  told to look at a section that never mentions paying.

**Screenshot:** `/home/user/SATC/client-documents/out/shots2/ind-standard__delivery-letter__SAT-C_Return_Delivery_-_Ellwood_-_2026.png`

---

### 6 · Section-number gaps on the two most-sent documents — HIGH

Confirmed on the rendered page, not the source:

| Document | Rendered numbering | Count |
|---|---|---|
| Onboarding letter | `01 · 02 · **04** · 05` | 26 of 27 packs (all but `ind-prior-firm`) |
| Return delivery letter | `01 · 02 · 03 · **05** · 06 · 07` | 27 of 27 |

Both are hard-coded literals wrapped around a conditional section — onboarding's `03 Your
previous accountant` under `[[IF PriorFirm]]`, delivery's `04 Next year's estimated
payments` under `[[IF EstimatedPayments]]`. When the condition is false the number goes
with it and the hole stays.

What a client experiences: a numbered document that skips a number. The obvious readings are
"a page is missing" or "something was removed from my letter." On the onboarding letter it
lands next to the sentence *"Use it to send us everything in section 01"*, which trains the
reader to trust the numbers.

`editor.renumber()` exists precisely for this — its docstring says *"Every FIELDS doc says
the same thing about a dropped section: **a client should never see 03 followed by 05**"* —
but it renumbers the **template source** at edit time, where there is no gap. The gap is
created at render, which `renumber` never sees.

The delivery letter's two sections both numbered `03` (`EFiled` / `PaperFiled`) are correct
— they are exclusive branches, and `renumber` protects that deliberately. But nothing
enforces the exclusivity: I set both flags true through the real `cli.py render` and it
cheerfully produced a letter with **two section 03s**, telling the client both to sign an
e-file authorization and that filing on paper is their responsibility.

**Screenshot:** `/home/user/SATC/client-documents/out/shots/ind-simple__SAT-C_Onboarding_Letter_-_Ellwood_-_2026.png`

---

### 7 · Every fee estimate asserts three things about the client that are usually untrue — HIGH

*All 27 estimates carry the identical three (four for entities) assumption bullets.*

On the estimate for `ind-simple` — a W-2-only Simple Filer, standard deduction, $100:

> — Brokerage — **your 1099-Bs** can be summarized rather than keyed line by line. …
> — Foreign entities — **your foreign holdings** are accounts rather than companies. If you hold an interest in a foreign corporation or partnership, …
> — Records cleanup — your records arrive complete and reconciled. …

This client has no brokerage account and no foreign holdings. The sentences do not say *if
you have*; they say *your*.

What a client experiences: on the second document they ever receive from the firm, a
statement that they hold foreign assets. FBAR and Form 5471 are frightening words to a
person who has neither. At best it reads as a form letter; at worst it makes them wonder
whether the firm has confused them with someone else.

This is the same bug the firm already found once. `pricing.py:1040` carries the rule in its
own words:

> "`when:` is for an assumption that CANNOT arise on this return … A person filing a 1040
> has no officers, so the officer-compensation boundary is not being stated to them — it is
> noise on their estimate."

`officer_compensation` got its `when:` gate (`0ac7f7a`). `brokerage_keying` and
`foreign_company` did not, and they fail the same test — a client with no brokerage
statements cannot break the brokerage assumption. That is T27: the note was applied to one
instance and not swept.

Same page, three times verbatim: *"the additional time is billed at $150 an hour as it is
worked."* Four times on an entity estimate.

**Screenshot:** `/home/user/SATC/client-documents/out/shots/ind-simple__SAT-C_Fee_Estimate_-_Ellwood_-_2026.png`

---

### 8 · Nothing in an amendment client's opening pack says "amendment" — HIGH

*`amend-our_error`, `amend-new_information`, `amend-other_preparer`.*

Their engagement letters and onboarding letters are **byte-identical** to `ind-simple`'s. I
diffed them; zero changed lines. The word "amend" appears nowhere in any of the three
letters. The subject line reads *"Preparation of your 2026 income tax returns"*; the body
reads *"Thank you for choosing SAT-C LLP to prepare your 2026 tax returns"*; section 01 reads
*"Federal: Form 1040 / State: Ohio / Local: Solon"*.

The only trace of the amendment anywhere in the pack is one priced line on the estimate.

What a client experiences: an engagement letter whose scope section describes preparing an
original return, signed for work that is an amendment. Scope is what the letter is for.

The onboarding letter compounds it: a client whose return **SATC filed last month** is asked
to send every W-2, a photo ID and the Social Security numbers again (T5 — "do not ask for
the same thing twice"; here, across years).

---

### 9 · An entity's K-1 delivery promise has no date in it — HIGH

*`ent-1065`, `ent-1120S`, `ent-1065-many`.*

> "The entity return produces a **Schedule K-1 for every owner**. Our target for delivering
> them is **each owner's personal return**, provided the entity's records reach us complete
> by February 22, 2027."

And on the 1120-S, two paragraphs later: *"Tell your owners the target date above now, not
in April."*

`ScheduleK1Target` is a `type: text` interview question with the help *"A real date. Every
owner's own preparer schedules around it, so it is a commitment rather than an intention."*
Nothing validates that the answer is a date. The registry says the same: *"if it can only be
produced as a guess, refuse rather than guess."* The FIELDS doc says *"**A real date**: every
owner's preparer schedules around it."*

What a client experiences: an ungrammatical sentence where the commitment should be, and a
follow-up instruction telling them to pass on "the target date above" — which is not a date.
Every owner's own preparer is scheduling around it.

**Screenshot:** `/home/user/SATC/client-documents/out/shots/ent-1065__SAT-C_Business_Engagement_Letter_-_LLC_-_2026.png`

---

### 10 · Every fee estimate, invoice and organizer letter prints an orphan second page — MEDIUM

Measured in the browser and confirmed in the PDF. `doc-page size="letter"` renders one
continuous sheet on screen, sized to its content; pagination happens only at print. For the
simplest estimate the sheet is **1108 px tall against a letter page's 1056** — half an inch
over — so the tail spills.

| Document | Physical pages | Last page |
|---|---|---|
| Fee estimate (×27) | 2 | signature line + footer only (259 chars) |
| Invoice (×27) | 2 | signature line + footer only (264 chars) |
| Onboarding letter (×27) | 2 | signature line + footer only (358 chars) |
| Organizer letter | 2 | signature line + footer only (306 chars) |
| Engagement letter (×23) | 3 | acceptance block — legitimate |
| Business engagement letter (×3) | 4 | acceptance block — legitimate |

What a client experiences: a two-page PDF invoice for one line of work, whose second page is
blank except "Arjun Sethuraman, CPA / Managing Partner" at the top. Printed, that is a
wasted sheet on every document in the pack.

Note the review hazard underneath it: **the browser view of a SATC document is not a page
preview.** It is one long paper-coloured strip with no page breaks, so a reviewer looking at
the HTML — including this review's own screenshots — cannot see where the pages fall. Only
the PDF shows it.

**Screenshots:** `/home/user/SATC/client-documents/out/shots/_pdf-invoice-p2.png` ·
`/home/user/SATC/client-documents/out/shots/_orphan_ind-simple__SAT-C_Fee_.png`

---

### 11 · A doubled bullet on every invoice — MEDIUM

The Notes list renders three `<li>`s where the middle one is empty, so an 8 px list item
draws its own dash immediately above the last note's dash. In IBM Plex at print size the two
dashes read as a stray `=` beside the final note.

Source: `SATC Invoice.html:103` wraps the whole conditional inside the `<li>`, so when
`EstimateReference` is false the content drops and the empty `<li>` survives. Confirmed on
all 27 invoices, on both the harness path and the real `cli.py render` path, and visible in
the printed PDF.

**Fix (not made):** the `[[IF]]` markers need to sit outside the `<li>` — the same shape the
organizer letter uses for `[[EACH Requested]]`, where the marker is its own `<li class="mark">`
and disappears cleanly.

Worth flagging separately: `EstimateReference` is false on every invoice the pipeline
produces, so the note *"Estimated at $325.00 on …"* never prints — even though `cli.py
invoice` printed `Estimated $325.00` to the terminal one command earlier. The invoice and the
estimate agree; the invoice just never says so.

**Screenshots:** `/home/user/SATC/client-documents/out/shots/_crop_invoice_zoom.png` ·
`/home/user/SATC/client-documents/out/shots/_pdf-invoice-p1.png`

---

### 12 · A client sitting exactly on a soft cap is never told the cap exists — MEDIUM

`exercise.py` runs both sides on purpose. The two estimates differ in exactly one line:

| Scenario | Line as rendered |
|---|---|
| 4 foreign accounts | "Foreign account reporting — **Per account — 4 × $50.00**" |
| 5 foreign accounts | "Foreign account reporting — **Per account, capped at 4 — beyond that the time is billed at $150 an hour** — 4 × $50.00" |

`_capped()` sets `capped=True` only when `count > cap`, so the boundary sentence prints only
once the client has already crossed it.

What a client experiences: at four accounts, an estimate that says nothing about a cap. They
open a fifth account in March and meet the $150 hourly rate on the invoice. T22 — "Half a
boundary is a promise the firm is not making" — and the firm's own line, *"4 is a soft cap.
Then we add dollars for time."*

Secondary: the five-account client's line reads **"4 × $50.00"**. Nothing on the page tells
them the fifth account is the one on the meter.

**Screenshot:** `/home/user/SATC/client-documents/out/shots/ind-foreign-5__SAT-C_Fee_Estimate_-_Ellwood_-_2026.png`

---

### 13 · Tenet sweep across the rendered set — MEDIUM

Run over the visible text of all 303 rendered pages.

**T20, banned vocabulary — 55 documents.** `accompanies` / `accompanying`, both on the
cutting test's grep list:

- Every fee estimate (27) carries **"ACCOMPANIES OUR ENGAGEMENT LETTER"** as its document-kind
  line, in caps under the title.
- Every engagement letter (28, all four variants) carries *"the amount shown on the estimate
  **accompanying** this letter"* in Fees and billing.

**AUTHORING-CONTRACT §5, cross-reference by number — 5 document types, ~170 instances.**
*"section 01"*, *"section 02"*, *"Section 03"*. The firm's ruling is recorded as confirmed:
*"delete Section 02 sets out how that works and who does what."* Two of these pointers are
also factually dangling today (findings 3 and 5).

**T20, sentences over 28 words — 12 distinct sentences.** Most are protected: the T21
load-bearing pointers in the delivery letter and extension notice, the unclear-law paragraph
and the assurance negations (T23), and the bookkeeping letter's management-responsibility
clause. The ones not obviously protected:

- Disengagement §01: *"We will not begin any new work, respond to any notice, or file anything on your behalf after that date, and no filing extension we have already obtained changes any date a taxing authority has set for you."* (38)
- Disengagement §06: *"It is not an opinion about your records, your returns, your business, or your circumstances, and **it should not be read as one or shown to anyone as one**."* — the tail is the same shape as the reliance tail the firm deleted under T7 (*"and should not be relied on for that purpose"* → "self-evident").
- Delivery §06: *"New work — an amended return, a notice, next year's returns — starts with a new engagement letter, so you know what it covers and what it costs before it begins."* (30) — the `so you know…` tail is a T9 reason tail.

**T9/T27, unswept instance — bookkeeping letter, acceptance line.** DOCUMENT-TENETS names
`SATC Engagement Letter - Bookkeeping.html:124` as not yet swept, and it is still live on the
page: *"If this letter states your understanding, **sign and return a copy. Sign through
Encyro and it comes straight back to us.**"* Every other engagement letter in the set now
carries the firm's own shorter line, *"If this letter states your understanding, sign
below."*

---

### 14 · The bookkeeping letter promises an estimate the software cannot produce — MEDIUM

Section 05: *"Our fee for this engagement is the amount shown on the estimate accompanying
this letter."* `registry/fee-schedule.yaml` is explicit: *"No bookkeeping pricing. Recurring
work is a different engagement with a different cadence, and the bookkeeping interview does
not exist yet."*

The letter also refuses through every front door: its six `source: bookkeeping` fields
(`AccountingSystem`, `Cadence`, `CatchUpPeriods`, `DeliveryTarget`, `FirstPeriod`,
`NoticePeriod`) are collected by no interview. It is the one template `exercise.py` never
touches. I rendered it from a hand-written fixture to look at it; on the page it is clean
and well-made.

One design snag visible once it renders: `<<Cadence>>` appears both in the subject line
(*"Bookkeeping and accounting services — Monthly"*, wants a capital) and mid-sentence
(*"Beginning with July 2026, on a Monthly basis"*, wants lowercase — the FIELDS doc says so
in terms). One field, two required cases, no casing control. Whatever the preparer types is
wrong in one of the two places.

**Screenshot:** `/home/user/SATC/client-documents/out/shots/_later___bookkeeping-handfixture__bookkeeping-letter.png`

---

### 15 · Smaller things, on the page — LOW

- **A $0.00 fee estimate.** `amend-our_error` produces a document headed "Fee estimate" whose
  ledger is one line — "Amendment / No charge / $0.00" — and whose total is **$0.00**. Below
  it sit three assumptions, all three of which are ways the client could be billed $150 an
  hour. `publish: "no"` in the schedule controls the public price page, not this document, and
  the schedule's comment says the line is meant to read "as an amendment with no charge."
  That is a firm judgment call, not a bug — but the rendered page is a bill for nothing
  followed by three hourly warnings, which is close to the argument T16 exists to avoid.
  Screenshot: `out/shots/amend-our_error__SAT-C_Fee_Estimate_-_Ellwood_-_2026.png`
- **"Dear Northbank Tooling LLC,"** — every entity letter salutes the company. `SignerName`
  ("R. Halloway") is on the record and used correctly in the signature block.
- **A joint return is addressed to one spouse.** `ind-joint` renders both signature lines and
  the joint-clients note correctly, but the address block and salutation name only Marcus.
- **Filename collision risk.** Entity documents are named from the last word of the client
  name: `SAT-C Fee Estimate - LLC - 2026.html`. Every LLC client produces identically-named
  files. The C corporation's letter is `SAT-C C Corporation Engagement Letter - LLC - 2026.html`.
- **A C corporation named "…LLC" is described as "an Ohio corporation."** The characterization
  comes from a dropdown and nothing checks it against the client's own legal name.
- **`ind-dependents` gets a pack identical to `ind-simple`'s** — nothing asks for dependents'
  dates of birth, childcare records, or a Form 8332. The generic "Social Security number for
  everyone on the return" is the only coverage.
- **`flagged-tight` and `flagged-foreign` get an entirely standard pack.** Correct — the flags
  are internal — and I confirmed **no internal flag string reaches any client-facing HTML**
  (`deadline_tight`, `foreign_exposure`, `assurance_needed`, `hard_no`, `red_flag` appear only
  in the engagement store's `interview.json`).
- **`cli.py check` renders both `business-letter` and `ccorp-letter` for a 1065** and reports
  "4 document(s) rendered" — one more than the pack contains. Its seven joins all pass.
- **`ind-gig`** is asked for "Your business income and expenses … *if you claim actual vehicle
  expenses rather than mileage, the vehicle costs as well*" immediately above "Your mileage
  log." The registry already flags that line as open.

---

## What is clean

Stated plainly rather than padded with per-file entries:

- **All 303 documents rendered.** Zero failed to load, zero failed to upgrade `doc-page`,
  zero fell back to browser serif, zero missing masthead, zero missing rules.
- **Zero merge markers or template chrome anywhere.** No surviving `<<Field>>`, `[[IF]]`,
  `[[EACH]]`, `.f` span or `.cond` marker in any rendered page. The `.ref` merge-field
  documentation block is stripped correctly from all twelve templates.
- **Zero horizontal overflow, zero text running off the page, zero overlap, zero page
  scrolling sideways** — at 1000 px and in the printed PDF, in both the fallback face and
  real IBM Plex.
- **Zero empty priced tables and zero empty section headings**, across all 303. The
  `183afc2` failure (a confident total over a table with no rows) does not recur; I
  reproduced it deliberately to prove the check works.
- **T13 is fixed.** No estimate prints "The standard deduction" and "Itemized deductions"
  together. I checked all 27.
- **The engagement letter, fee estimate and records release are good documents on the page.**
  The individual letter's nine sections, the entity letter's ten, the C corporation letter's
  nine — all complete, all correctly numbered, all typeset well. The records release reads in
  the client's own voice and needs nothing.
- **The PDF path is faithful.** Real IBM Plex embedded, correct colour, correct rules,
  correct margins. Its only defect is the orphan page (finding 10).
- **`consistency.report` passes all seven joins** on every scenario, and I spot-checked its
  work by eye: one ref, one date, one scope, materials deadline before first deliverable.
- **No PII leak.** Every person in the run is invented by the harness. `leads.xlsx` was never
  opened.

---

## Proving the checks (tenet S1)

A check that reports everything is fine is worth nothing until it has been seen red. I broke
four documents on purpose — in copies under `out/`, never in the repo — and re-ran the checks:

| Break | Caught by | Result |
|---|---|---|
| Deleted `satc-doc.css` and `doc-page.js` from a pack | `doc-page` upgrade wait | **red** — all 3 documents time out |
| Re-introduced an unresolved `<<TaxpayerName>>` | rendered-text marker scan | **red** — `['<<TaxpayerName>>']` |
| Set `EFiled` and `PaperFiled` both true | section-number scan | **red** — `duplicateNumbers: ['03']` |
| Stripped the priced rows from the estimate ledger, keeping the total (`183afc2`) | empty-table check | **red** — `led header rows=1 data rows=0` |

The fourth is the one that matters most: my **first** version of that check did not fire on
the break. It required `tbody tr` to be zero, and browsers auto-insert `tbody`, so it counted
the header and total rows and stayed green. It was decoration until the break exposed it.
The version above counts rows that are neither header nor total, and goes red. Everything
reported clean above was measured with the fixed check.

---

## What I could not check

- **The bookkeeping letter under real data.** No interview collects its six fields, so I
  rendered it from a hand-written fixture. The wording and layout are reviewed; the merge
  against real answers is not, because there are none.
- **The organizer, delivery, extension and disengagement letters under real data.** Same
  reason (finding 5). I reviewed them against registry-shaped lists I wrote myself; a
  preparer today has no way to produce them.
- **Email and Encyro delivery.** Every document says things about how it reaches the client
  ("we will email a secure upload link", "encrypted through Encyro"). Nothing in this project
  sends anything, so those sentences are unverified against the actual process. T10 applies.
- **On-screen appearance in the real typeface.** Google Fonts is reachable from this machine
  but slow through the proxy, so the 303 screenshots were taken with it blocked and show the
  Helvetica/Arial fallback. Every size in the stylesheet is in points, so the layout is
  unchanged; I confirmed real IBM Plex separately in the 19 PDFs, which is where the type
  actually matters. A client opening the HTML offline sees what the screenshots show.
- **Print behaviour outside Chromium.** All page geometry here is Chromium's.
- **Whether the firm agrees with any of the wording findings.** They are theirs. Section 13
  reports what the tenets say, not what should be written instead.
