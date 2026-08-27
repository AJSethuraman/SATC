# Tenet mechanization — specification for the SATC tenet linter

**Written 27 August 2026.** Governs a new checker over client-facing documents.
Input tenets: `satc-handoff/00-START-HERE/DOCUMENT-TENETS.md` (T1–T28).
Governing software rules: `docs/SOFTWARE-TENETS.md` §0, Part 1.

The firm's rule for this tool:

> A tenet a machine can check EXACTLY becomes a hard failure that blocks a
> document from being sent. A tenet a machine can only guess at prints as an
> advisory note. A tenet is promoted from advisory to blocking only after a
> full cycle with no false positive.

**Standard applied here for EXACT:** for any document the firm may write, the
check's answer *is* the tenet's answer. No judgement call. No plausible false
positive. If the justification contains "usually" or "in most cases", the
verdict is APPROXIMATE.

Everything below was run against the twelve templates in
`satc-handoff/04-TEMPLATES/` and against the 29 real rendered packs (55
documents) in `client-documents/out/exercise/`. Hit counts are measured, not
estimated.

---

## 0 · Two live bugs this analysis found

Reported first because they are the argument for building the thing.

**0.1 — Every onboarding letter without a prior firm ships misnumbered.**
`[[IF PriorFirm]]` drops section 03 and nothing renumbers what follows. The
letter goes to the client as **01, 02, 04, 05**. This is not theoretical: it is
**26 of the 55 rendered documents** in `out/exercise` — every single onboarding
letter except `ind-prior-firm`. The template's own FIELDS spec asked for the
fix and it was never built:

> `[[IF PriorFirm]]` … Drops section 04 entirely for a client with no previous
> accountant. **Renumber the remaining sections in code** — 05 and 06 must not
> follow 03. — `SATC Onboarding Letter.html`, the `.ref` block

Caught by **L2** below, which reads the rendered page and nothing else.

**0.2 — A retired sentence is still live in the bookkeeping engagement letter.**
`SATC Engagement Letter - Bookkeeping.html:124` still reads *"If this letter
states your understanding, sign and return a copy. Sign through Encyro and it
comes straight back to us."* The firm replaced that whole construction with
*"If this letter states your understanding, sign below."* (T9's table, row 2).
T9 flags it as not-yet-swept and it is still not swept. Caught by **L5**.

---

## 1 · What already exists. Do not rebuild any of it.

The linter must not re-implement, re-check, or restate the following. Where a
tenet is already enforced, the row below says so and stops.

| Already enforced | Where | Covers |
|---|---|---|
| Unresolved `<<Field>>` is a hard failure | `merge.render`, `_UNRESOLVED_FIELD` | — |
| Unresolved `[[IF]]` / `[[EACH]]` block is a hard failure | `merge.render`, `_UNRESOLVED_BLOCK` | — |
| A surviving `[CONFIRM:` is a hard failure | `merge.render`, `_CONFIRM` | **T23** ("nothing invented") |
| A required `[[EACH]]` list that is empty is a hard failure | `merge.render(required_lists=…)` + `registry/fields.yaml` | **T26** (half-done cut leaves a blank list) |
| The `.ref` block never ships | `merge._REF_BLOCK` | — |
| One engagement ref / one letter date across a pack | `consistency.report` | — |
| Letter and estimate state one scope; nothing billed outside scope | `consistency.report` | **T13**, partially |
| Total is the sum of the lines | `consistency.report` | **T13**, partially |
| Nothing promised before the materials are due | `consistency.report` | **T13**, partially |
| A cap with no stated consequence refuses to price | `pricing._cap_beyond` | **T22** |
| A `supersedes:` string no lower rung says refuses | `pricing.py` + fee-schedule test | **T12**, **T13** (the standard/itemized bug) |
| Every `phrases:` entry renders and keeps its slots | `pricing._SLOTS` + its test | **T28**, **T4** |
| Template ↔ `registry/fields.yaml` reconciled both directions | `test_registry.py` | **T26** |
| Firm block reaches every document from settings alone | `test_the_firm_block_reaches_every_document_from_settings_alone` | **T26** |
| Inverse flag pairs each render exactly one branch **given a correct record** | `test_merge.INVERSE_PAIRS` | **T13**, partially — see L2 |

Three of the twenty-eight tenets are therefore **already done** and get no new
check: **T22**, **T12**, and the `[CONFIRM:` half of **T23**.

One thing the existing set gets wrong for our purposes and it must be
understood before writing L4: **`consistency.py` REQUIRES the letter and the
estimate to print the same four scope lines.** A naive T1 "no sentence appears
in two documents of one pack" check therefore fires on exactly what another
check demands. Measured: **10 of 29 real packs**, every hit the scope line, e.g.
`ind-standard` → *"Federal: Form 1040 with Schedules E, D and A"* on both the
engagement letter and the fee estimate. See T1 below.

---

## 2 · The proxy rule for this linter

`SOFTWARE-TENETS.md` §0: *"in every case the verifier looked at a proxy rather
than the thing."* Three consequences, binding on every check below.

1. **Read the rendered document, not the template and not the record.** A value
   that nothing prints can never violate a tenet about wording. Proof from this
   corpus: three British spellings (`authorisation`, `organised`, `recognise`)
   and two `[CONFIRM]` mentions exist in the template files. **All five are
   inside `.ref` blocks, which `merge` strips.** A source-reading linter fires
   five times and is wrong five times. A rendered-output linter fires zero.
2. **A word list is not a tenet.** T20's own banned list contains
   *accompanies*. A literal sweep condemns *"the amount shown on the estimate
   accompanying this letter"* — live, unobjected-to copy in **5 of 12
   templates**. The word is the proxy; the register is the tenet.
3. **Print the denominator (S2).** Every check reports how many things it
   examined, not only how many failed. `L1: 55 enclosure claims checked, 0
   unresolved` is a result. `L1: pass` is not.

---

## 3 · Inputs

| Name | What it is |
|---|---|
| `rendered` | `{doc-key: HTML}` after `merge.render`. The client's page. |
| `text(doc)` | `rendered[doc]` with tags stripped, block tags → newline, entities unescaped, whitespace collapsed. One paragraph or list item per line. |
| `manifest` | `packaging.manifest(...)` — `Documents[].key`, plus a new `Attachments[]` (§5, L1). |
| `templates` | The twelve template files. Read **only** for structural markup (`data-encl`, `<h2><span class="n">`), never for wording. |
| `retired.yaml` | New. The registry of sentences the firm has deleted (§5, L5). |
| `registry/*.yaml` | `fee-schedule.yaml`, `interview.yaml`, `document-requests.yaml`, `fields.yaml`. |

A check that needs `manifest` **does not run** on a single-document render and
says so. Measured consequence of getting this wrong: run against the 40-odd
one-document render directories in a scratch tree, the pointer test reports 9
failures, all of them "a fee estimate rendered alone does not contain the
engagement letter it says it accompanies." That is not a document defect. It is
a checker that did not know what it was looking at.

---

## 4 · The twenty-eight tenets

Each row: **statement · verdict · check · false-positive risk · what it fires on
today.** "Today" means the twelve templates and the 29 rendered packs.

---

### T1 · A fact lives in one document; a second document may name it only if the sentence carries a fact of its own.

**Verdict: NOT MECHANIZABLE.**

**Check considered.** Sentence-shingle every document in a pack; normalize
(lowercase, strip punctuation, drop ≥6-word boilerplate); report any normalized
sentence present in two documents.

**False-positive risk: fatal, and it is not hypothetical.** `consistency.py`
requires `FederalReturns`, `StateReturns`, `LocalReturns` and `AdditionalForms`
to print identically on the letter and the estimate — that is the check that
caught Schedule E billed outside a signed scope. Every hit this check produces
today is that mandated repetition.

**Fires today: 10 of 29 real packs, 10 hits, 10 false positives, 0 true
positives.** Sample: `[ind-rentals-3]` engagement letter and fee estimate both
print *"Federal: Form 1040 with Schedule E"*. There is no threshold, stop-list
or length filter that separates this from a genuine T1 violation, because the
genuine violations were never verbatim duplicates — *"The same list as the What
we will prepare section of your engagement letter"* is a **caption**, not a
copy. A machine cannot tell a caption from a fact without reading both.

**Drop.** The enforceable residue of T1 is the pointer test (L1) and the retired
sentence registry (L5), both below.

---

### T2 · Never restate the heading in the items under it.

**Verdict: APPROXIMATE.**

**Check.** On `text(doc)`: for each `^(\d\d)\s+(.+)$` heading line, collect
content words (lowercase, ≥3 chars, minus a stop list). For each following
sentence until the next heading, flag if `|heading_words ∩ sentence_words| ≥ 3`.

**False-positive risk.** A section headed *Filing the paper returns* whose first
sentence must say *"filing these returns is your responsibility"* — that
repetition is the sentence's job, and T14 names this exact line as one that has
survived every round untouched.

**Fires today: 1 hit, and it is that sentence.** 1 false positive, 0 true
positives. The tenet's real evidence (five estimate bullets each opening "this
estimate assumes") lives in `fee-schedule.yaml`'s `phrases.assumption`, which
has already been fixed and is already guarded by the `_SLOTS` test.

**Advisory.** Report it against `phrases:` values only, where a bullet echoing
its block heading is the failure mode that actually occurred. Never against
template prose.

---

### T3 · Two names for one list is a bug. Use the owning document's name.

**Verdict: EXACT** — for the one named list, which is the only one the tenet is
about.

**Check.** In a pack containing an engagement letter and a fee estimate: read
the letter's section-01 `<h2>` text and the estimate's `.scope > .h` text from
the rendered HTML. Fail unless they are string-equal after whitespace collapse.

**False-positive risk. None constructible.** Both strings are headings of the
same list built from the same four fields. Any difference between them is the
bug the tenet names. Note the estimate's scope block sits inside
`[[IF ReturnScope]]`: when it drops, there is no second name and the check has
nothing to compare, so it reports `skipped` rather than passing.

**Fires today: 0 of 29 packs.** All three pack types print *"What we will
prepare"* on both. The bookkeeping letter's section 01 reads *"What we will
do"*, which would collide — but there is no bookkeeping pack in
`packaging.PACKS`, and the estimate drops its scope block for a bookkeeping
engagement anyway. **This check is a trap set for a pack that does not exist
yet.** That is a good reason to ship it, not a reason to skip it.

---

### T4 · A reassurance is made once, at the point where it changes what happens next.

**Verdict: NOT MECHANIZABLE.** Already enforced where it can be.

The firm's own diff resolved this inside `fee-schedule.yaml`: the promise
survives once, on `beyond_priced`, and its slots are pinned by the `_SLOTS`
test. Deciding whether a *new* sentence is a reassurance or a fact requires
reading it. Nothing to build.

**Fires today: n/a.**

---

### T5 · Do not ask for the same thing twice inside one document.

**Verdict: EXACT**, narrowly — for a repeated *ask*, which in these documents is
always a list item.

**Check.** On the rendered HTML, for each `[[EACH]]`-driven list
(`RequestList`, `OutstandingItems`, `Requested`, `ActionList`,
`ReturnsDelivered`, `WorkStatus`, `OpenDeadlines`, `LineItems`): normalize each
item's first sub-field (lowercase, strip punctuation and leading articles) and
fail on any duplicate within one list.

**False-positive risk. None constructible.** Two identical asks in one
checklist is the failure by definition; a legitimately repeated *document*
(two W-2s) is one line reading "Every W-2 for the year", not two lines.

**Fires today: 0.** All 17 entries in `document-requests.yaml` are distinct;
the 26 rendered onboarding letters carry no duplicate ask. **This check has no
evidence behind it in the current corpus.** It is cheap and cannot lie, so it
ships blocking — but it earns its place on the mutation test (§8), not on a
hit.

The tenet's other half — *"we can correct by saying something does not apply,
not ask for even more info if we think we have it all"* — is a property of the
interview, not of a document. Out of scope here.

---

### T6 · A sentence whose only job is to intensify the one before it gets deleted.

**Verdict: NOT MECHANIZABLE.**

**Check considered.** The cutting test's step 5: flag sentences opening with
*That is / This means / This is / Which is / Not merely / One … as many … as*.

**False-positive risk.** *"This is that writing."* — disengagement letter §01.
Four words, opens with a demonstrative, and it is the sentence that makes the
letter legally what it claims to be. Likewise *"This is our decision, and we are
telling you in writing so the date is not in doubt."*

**Fires today: 2 hits, both those sentences. 2 false positives, 0 true
positives.** The tenet's own test — *"cover it and reread the one before; only
emphasis lost?"* — is a reading comprehension task. The demonstrative opener is
a **proxy for it and a bad one**: it catches the surface of the two deleted
examples and nothing about why they were deleted.

**Drop.** This is the clearest single tenet in the file and the least
mechanizable one in it. Say so out loud rather than shipping a check that
teaches people to ignore it.

---

### T7 · Delete the consequence a reader derives for free.

**Verdict: NOT MECHANIZABLE.**

"Self-evident from the words surrounding it" is the definition, and it is a
judgement about a reader. The three deleted instances (the reliance tail, the
lender/investor sentence, the attorney/banker sentence) share no surface form.

**Fires today: n/a.** The three deleted sentences are covered exactly by the
retired-phrase registry (L5), which is where the enforceable part of T7 lives.

**Drop as a pattern; keep as three rows in `retired.yaml`.**

---

### T8 · Do not narrate our own tone, our own reasoning, or our own inability.

**Verdict: APPROXIMATE.**

**Check.** On `text(doc)`, case-insensitive:
`we cannot tell | we are unable to | we have no way (of|to) | as a courtesy |
to be clear | for the avoidance of doubt | not a brush-off | please understand |
we appreciate | we want to be`.

**False-positive risk.** *"We cannot transmit anything until the signed
authorization is back with us"* (delivery letter §03) is a fact about the law,
not a narration of our inability, and a slightly looser pattern (`we cannot`)
catches it. The pattern above is tuned to miss it, which is a different way of
saying the pattern is tuned to this corpus.

**Fires today: 0 of 12.** The corpus has been swept. That is also the problem:
with zero live hits, the list is unfalsifiable until someone writes a new
sentence, and the phrase that produced the tenet (*"we cannot tell a missing
document from one that does not exist"*) is already in `retired.yaml`.

**Advisory.**

---

### T9 · Cut the "why we want it" tail. Keep the ask.

**Verdict: NOT MECHANIZABLE.**

**Check considered.** The cutting test's step 6: find the em-dash or
`because / so that / rather than` tail and delete it.

**False-positive risk.** The tenet **explicitly carves out** reason-tails whose
consequence belongs to the reader, and the positive model in §0 is four
sentences all of which carry one: *"…and a return sent to the wrong authority is
not late — it is unfiled."* A mechanical em-dash rule deletes the house voice.

**Fires today:** the em-dash form alone hits **19 sentences across 9 of 12
templates**, and reading them, every one is either the reader's own consequence
or a compliance sentence. That ratio is the answer.

**Drop.** T9's one live unswept instance is the bookkeeping Encyro tail, and
it is caught exactly by L5.

---

### T10 · Describe the process that actually happens. Ask before writing a step you have not been told.

**Verdict: NOT MECHANIZABLE** for the process claim; **EXACT** for the two
sub-rules with a mechanical surface.

**10a — `[CONFIRM:` reaches no client.** Already a hard failure in
`merge.render`. Do not re-implement.

**10b — American English.** Check `text(doc)` against a British-spelling list
(`-isation/-ise/-isable` for the affected stems, `licence`, `behaviour`,
`centre`, `cheque`, `whilst`, `amongst`, `programme`, `enrol`).
**False-positive risk:** a proper noun or a quoted authority name. None in this
corpus, and a quoted foreign body name would need a stop-list entry.
**Fires today: 0 in rendered output.** Three exist in template source
(`authorisation` ×2, `organised`, `recognise`) and **all are inside `.ref`
blocks**, which never ship. This single fact is the whole argument for §2.1.

The tenet's core — *"i question how well you understand the proceses"* — is a
claim about the world. No linter reaches it.

**10b ships blocking. The rest: drop.**

---

### T11 · Do not state as certain what is only possible.

**Verdict: APPROXIMATE.**

**Check.** On `text(doc)`:
`will likely | is likely to | typically | generally | in most cases | usually |
in all cases | always results in`.

**False-positive risk.** *"…that penalty is commonly charged per owner, per
month"* (business letter §05) is a hedge that IS the fact, which the tenet
allows ("unless the hedge is the fact"). Distinguishing the two requires
knowing whether the underlying claim is certain — a tax question, not a text
question.

**Fires today: 0 of 12.** The `2a41777` sweep did its job.

**Advisory.** Promote after one cycle if it stays at zero. It is a good
candidate for promotion precisely because the corpus is already clean: a hit
after promotion is almost certainly new prose, which is what the check is for.

---

### T12 · The default is implied. Say only what departs from it.

**Verdict: EXACT — and already built.** `supersedes:` in `fee-schedule.yaml`,
with a test refusing a `supersedes:` string that no lower rung actually says.
The general form ("is this behavior the default?") is a domain question.

**Fires today: 0.** Nothing to build.

---

### T13 · A document must never state two things that cannot both be true.

**Verdict: NOT MECHANIZABLE in general. EXACT for the two contradiction shapes
that actually occurred.**

General contradiction detection over English is out of scope and always will
be. Two concrete shapes are exact:

**13a — the standard/itemized case.** Already fixed by `supersedes:` and
guarded. Do not rebuild.

**13b — mutually exclusive branches both rendered, or neither.** Five inverse
pairs are declared in the FIELDS specs: `EFiled/PaperFiled`,
`ClientInitiated/FirmInitiated`, `BalanceOutstanding/AccountSettled`,
`PaymentEnclosed/NoPaymentRequired`,
`OwnerReturnsPrepared/OwnerReturnsElsewhere`. `test_merge.INVERSE_PAIRS` proves
each branch renders correctly **given a correct record**. Nothing checks a real
record at send time. A record with `EFiled` and `PaperFiled` both true renders
two section 03s telling the client two incompatible things about how their
return gets filed.

The check does not need to know about flags. **Read the section numbers off the
rendered page** — see L2. A both-true render produces a duplicate number; a
both-false render produces a gap. One check, no flag registry to drift.

**Fires today: covered under L2 — 26 of 55 rendered documents.**

---

### T14 · A request stays a request. Never convert an ask into a transfer of blame.

**Verdict: NOT MECHANIZABLE.**

**Check considered.** Flag responsibility language inside a sentence that also
contains a request verb.

**False-positive risk.** The tenet itself supplies it: *"Not a ban on assigning
responsibility. 'You chose to file on paper, so filing these returns is your
responsibility, not ours' has survived every round untouched."* The difference
between that and the deleted version is which of the two the sentence is
*for* — unavailable to a regex.

**Fires today: 1 hit** — *"Reviewing the return before you sign it. You are
responsible for its contents."* (tax letter §03) — **and it is a false
positive**: that is the responsibilities section doing its job. The sentence
T14 was written about is already gone; the delivery letter now opens section 02
with the firm's own *"Review your returns"*. The line reference in
`DOCUMENT-TENETS.md` ("still live at `SATC Tax Return Delivery Letter.html:67`")
is **stale** — line 67 is now an `[[END EACH]]` marker.

**Drop.**

---

### T15 · Their choice, our limit. State what we will and will not do; do not disapprove of them.

**Verdict: APPROXIMATE.**

**Check.** On `text(doc)`: `we (would|do) not (advise|recommend) | we recommend
against | not advisable | unwise | you should not | it may not be secure | we
strongly (advise|urge)`.

**False-positive risk.** *"We would not advise on a reasonable compensation
figure without a separate engagement"* — a statement of our limit that happens
to use the banned verb.

**Fires today: 0 of 12.** The firm's own replacement line — *"Emailing or
otherwise transmitting unprotected documents is done at your own risk"* — is
live in the onboarding letter, and the "at your own risk" form is carried
across four templates as T15 required.

**Advisory.**

---

### T16 · Do not advertise our own virtue. Say the price; behave well silently.

**Verdict: APPROXIMATE.**

**Check.** On `text(doc)`: `free of charge | at no cost | no (extra|additional)
charge | costs nothing | we never charge | we pride | at our own expense | we
absorb | happy to`.

**False-positive risk.** *"Reading one and telling you what it actually says
costs nothing."* — T9's own table lists this as the **kept** version. So the
word list flags a sentence the firm wrote and approved. The reason T16 killed
the $0 amendment line was that it read as a marketing claim on a **public
page**; the same words in a client's own letter, about a specific favour, were
fine.

**Fires today: 0 of 12.** The kept sentence above is not currently in any
template, so the collision is latent rather than live.

**Advisory, and scoped to the website and the published fee schedule**, which
is where "can't bite if not a secret" was aimed. Not a client-letter check.

---

### T17 · Lead with what the reader must do, inside the first six words.

**Verdict: NOT MECHANIZABLE.**

**Check considered.** The subject line's first six words must contain a
second-person pronoun or an imperative verb.

**Fires today: 6 of 12 subject lines fail, and all six are correct copy:**

| Document | Subject | Verdict |
|---|---|---|
| Disengagement | *Ending our engagement* | correct |
| Bookkeeping | *Bookkeeping and accounting services* | correct |
| Extension Notice | *We have filed an extension* | correct — the fact IS the news |
| Fee Estimate | *(no subject line — it is a ledger)* | correct |
| Invoice | *(no subject line — it is a ledger)* | correct |
| Records Release | *Authorization to release my records* | correct — written **from** the client |

**Drop.** T17 is an editing instruction for one document, extracted from three
edits to one document. It is not a property of the set.

---

### T18 · One ask per line.

**Verdict: NOT MECHANIZABLE as stated. One exact sub-check available.**

**Check considered.** Flag a list-item label containing a coordinating
conjunction.

**False-positive risk: three live ones.** *"Rental income and expenses for each
property"*, *"Your business income and expenses"*, *"Farm income and expenses"*
— each is one ask about one thing, and splitting them would be wrong.

**Exact sub-check that survives:** a `document:` label in
`document-requests.yaml`, or an `Item.Action` / `Item.Document` label in a
rendered list, must not contain a sentence-terminating period or a semicolon. A
label is a noun phrase; two clauses in a label is the shape that produced the
tenet (*"The ID only if we have not seen it before. We need the numbers, not the
cards"*). **Fires today: 0 of 17 request entries.**

**Sub-check ships advisory. The conjunction form: drop.**

---

### T19 · A section states the decision, not the reasoning, edge cases or mechanics.

**Verdict: APPROXIMATE.**

**Check.** On `text(doc)`, per paragraph: flag paragraphs of more than three
sentences.

**Fires today: 9 hits across 4 of 12 templates.** Every one of the nine is a
compliance paragraph protected by T23 — the assurance-negation block (×4), the
billing-and-suspension paragraph (×4), the bookkeeping invoicing paragraph. A
check whose entire yield is protected text is a check that will be muted within
a week.

**Advisory, with the T23-protected paragraphs excluded** by paragraph id. Note
honestly that after that exclusion it fires on nothing today.

---

### T20 · Client's vocabulary, not the spec's. No client-facing sentence past 28 words.

**Verdict: split. One EXACT half, one APPROXIMATE half, one to drop.**

**20a — the hard-banned words. EXACT.**
`governs | constitutes | pursuant | at our discretion | deemed | shall be |
herein`, on `text(doc)`, word-boundary, case-insensitive. These seven have no
legitimate use in a document this firm sends. **False-positive risk: none
constructible** — they are legalese with plain-English equivalents in every
context, and the tenet names them individually.
**Fires today: 0 of 12.**

**20b — `accompanies` / `accompanying`. DROP FROM THE LIST.** It is in T20's
written list and it is **live in 5 of 12 templates**, in a sentence the firm has
read four times without objecting: *"Our fee for this engagement is the amount
shown on the estimate accompanying this letter"* (×4) and the estimate's own
header *"Accompanies our engagement letter"*. Either the list is wrong or five
templates are, and four rounds of review say it is the list. **Report this to
the firm as a correction to `DOCUMENT-TENETS.md`, not as a lint hit.**

**20c — 28-word sentence cap. APPROXIMATE.**
**Fires today: 21 sentences across 8 of 12 templates.** Of those 21, at least
fourteen are compliance-floor or load-bearing sentences that T23 forbids
cutting — the unclear-law paragraph (×3, 35 words each), the
engagement-concludes sentence (×3, 30–32 words), the mail-separately
instruction (36 words), the retention pointer (40 words). The worst offender is
the **50-word** officer-compensation sentence in the business and C-corporation
letters, written on 26 August, after T20 was recorded. That one is a real hit.
One real hit in twenty-one is a 5% signal rate.

**Ships advisory, sorted longest-first, and only the top five printed.** Its job
is to put the 50-word sentence in front of a human, not to gate a send.

---

### T21 · A sentence stating a fact AND citing a clause is load-bearing. It stays.

**Verdict: EXACT** for the mechanizable half — that a cited clause name exists.
NOT MECHANIZABLE for "is a fact left standing?".

**Check (L3).** On the rendered HTML, match
`(?:<b>|<strong>)([^<]{4,60})</(?:b|strong)>\s*section of your engagement
letter`. Each captured name must equal, after whitespace collapse and
case-fold, an `<h2>` heading text in at least one engagement-letter template.

Reading the **markup**, not the sentence, is what makes this exact — every one
of the seven live citations wraps the clause name in `<b>` or `<strong>`, so
there is no sentence to parse and no greedy-match ambiguity. (A plain-text
regex over the same corpus mis-captures 2 of 7.)

**False-positive risk.** A clause cited from a letter this client will never
receive — the bookkeeping letter has no *Your deadline, and extensions* section.
Resolving against the **union** of the four engagement-letter templates removes
this at the cost of some strictness. Resolving against the specific letter in
the record is stricter and reintroduces the risk, so it stays advisory.

**Fires today: 7 citations, 7 resolve, 0 failures.** The four names in use:
*Ending this engagement* (×2), *Your records, our files, and delivery* (×2),
*Fees and billing* (×3). This check's value is regression: rename a section in
an engagement letter and four other documents break silently.

---

### T22 · Both halves of a boundary get said.

**Verdict: EXACT — and already built.** `pricing._cap_beyond` refuses to price
a capped line whose consequence is unstated. Nothing to add.

**Fires today: 0.**

---

### T23 · The compliance floor is not style and is never cut for length.

**Verdict: split into four.**

**23a — the required negations are present. EXACT. This is the strongest check
in the whole set.**
State the floor **positively**: every engagement letter must contain its
assurance-negation. Register the requirement in `retired.yaml`'s sibling,
`required.yaml`, as `{id, applies_to, must_contain_all: [keyword sets]}` —
keyword sets, not pinned sentences, so T28 is honored (the firm can reword
freely; he cannot delete the negation). Example entry:

```yaml
- id: no-assurance-engagement
  applies_to: [tax-letter, business-letter, ccorp-letter, bookkeeping-letter]
  must_contain_all:
    - ["not perform", "do not perform", "will not perform"]
    - ["audit", "audits"]
    - ["review", "reviews"]
    - ["assurance"]
```

**False-positive risk: none constructible.** A letter that satisfies the tenet
contains the words; a letter that does not, does not.
**Fires today: 0 of 12** — all four letters carry it.

**23b — banned assurance vocabulary outside a negation. APPROXIMATE.**
The tenet says the words are banned "except in an explicit negation." Detecting
"explicit negation" is the judgement. Measured: a loose detector (any of
`not|no|never|cannot|nor|neither|without|separate engagement|separately quoted`
anywhere in the sentence) fires **0 of 12**. A strict detector requiring the
negator to precede the banned word fires **2 of 12, both false positives**:
*"If a lender specifically requires audited or reviewed statements, that is a
separate engagement"* and *"Representing you in an examination, notice response,
or appeal is a separately quoted engagement."* The gap between 0 and 2 is
entirely in the negation vocabulary, which is tuned to this corpus. That is the
definition of APPROXIMATE. **Advisory.**

**23c — "led by a licensed CPA", never "CPA firm". EXACT but out of scope
here.** **Fires today: 0 — the string `CPA` appears in none of the twelve
templates.** The credential line lives on the website and in firm settings.
Build it there.

**23d — client PII. DROP FROM THE DOCUMENT LINTER.** A client's own engagement
letter is addressed to them by legal name; `<<ClientFullName>>` prints on all
twelve. A PII check over rendered client documents fires 12 of 12 and is wrong
12 of 12. T23's PII rule is about **artifacts, logs, samples and workbooks**,
which is a different pipeline and already has its own guards. Confusing the two
is the fastest way to a muted check.

**23e — `[CONFIRM:`.** `merge` already hard-fails. Do not rebuild.

---

### T24 · A sentence flagged twice gets deleted, not reworded a third time.

**Verdict: NOT MECHANIZABLE as a document check. Mechanizable as a review
signal.**

The tenet is about *history*, so the check is over git, not over a document:
`git log --follow -L` the paragraph; if the same span has been edited in three
or more commits, print it. That is a code-review aid, not a send gate, and a
send gate on edit count would block a document for being carefully edited.

**Fires today: not measured — history-dependent and outside the linter's
inputs.**

**Drop from the linter.** Recommend it as a `make review` report instead.

---

### T25 · Do not answer a decision by adding prose to a document that already honours it.

**Verdict: NOT MECHANIZABLE.** "Does another document already say this?" is T1's
judgement, wearing a different hat. The enforcement that worked was social — the
sign-off register's *"Do not rewrite it again."*

**Fires today: n/a. Drop.**

---

### T26 · Finish the cut. Nothing dangles, nothing still points at it.

**Verdict: EXACT — and mostly already built.**

Three of the four sub-checks exist: template↔`fields.yaml` reconciliation both
directions (`test_registry.py`), the required-lists guard (`merge.render`), and
the firm-block property test. The fourth does not exist and is the one this
linter adds: **L5, the retired-phrase registry** — a deleted phrase must be
absent from the *rendered* output of every template.

**False-positive risk.** A retired phrase that is a substring of a legitimate
heading. **This is not hypothetical: it is 1 of the 2 hits today.** The retired
bullet prefix *"this estimate assumes"* is a substring of the fee estimate's
legitimate block heading *"What this estimate assumes"*. Fixed by storing the
retired **whole phrase** (`"{label} — {assumes}, {where}."`) and by excluding
heading lines from the scan. Both are exact.

**Fires today: 2 hits across 12 templates — 1 true positive (§0.2, the
bookkeeping Encyro tail), 1 false positive (the heading above), which the fix
above removes.** After the fix: **1 hit, 1 true positive, 0 false positives.**
Best signal-to-noise of any check in this document.

---

### T27 · Apply a note to every template before he reads the next one.

**Verdict: NOT MECHANIZABLE as a sweep detector.**

**Check considered.** For a family of sibling templates, flag any sentence
present in some but not all.

**Fires today: 44 partial sentences across the four engagement letters.**
Eighteen of the 44 are "present in the three tax letters, absent from the
bookkeeping letter" — correct, because bookkeeping is a different service.
Twenty-three are "present in the two entity letters, absent from the individual
one" — correct, because they are about an entity. Zero true positives.

**Drop the sweep. Keep L5,** which is T27's enforceable core: once a phrase is
retired anywhere, it is retired everywhere, and the registry says so in one
place.

---

### T28 · Wording is data. Three places hold client-facing words and only three.

**Verdict: EXACT for the existing guard. NOT MECHANIZABLE as a prose-in-code
detector.**

**Already built:** `pricing._SLOTS` plus the test that renders every phrase and
fails by name if one loses or gains a slot. That is `SOFTWARE-TENETS` S10.

**Check considered and rejected.** Scan the Python for string literals of ≥8
words ending in a sentence period. **Fires today: 94 hits across 14 modules**,
and every one I read is an operator-facing error message or CLI help text —
*"a lead needs at least a name, an email or a phone number"*, *"an invoice
assembled by hand is the…"*. The only arguable client-adjacent hits are
`packaging.PURPOSE`, which prints into `MANIFEST.json`, an internal artifact. 94
hits, ~0 true positives.

**Drop the detector.** T28's other half — *no test may pin his prose* — is a
constraint on **this specification**, and it is why L4/L5 store keyword sets and
whole retired sentences in YAML the firm can edit, rather than string literals
in Python.

---

## 5 · The blocking set — version one

Six checks. Ordered by the evidence behind them.

> Six checks that never lie beats twenty that get muted. Every one below either
> catches a bug that has actually happened in this repo, or cannot produce a
> false positive by construction.

---

### L1 · The pointer test — a promised enclosure is in the pack
*(T1, T21, T26 · the check the firm asked for by name)*

**Why it blocks.** `packaging.py` carries the incident in its own comment:

> `package` never carried the records release, so a client with a predecessor
> got a pack whose onboarding letter says "We have included a short
> authorization for you to sign" and did not include one. … A pack that
> promises an enclosure it does not carry is the same failure as a pack with a
> hole in it, arriving by the back door.

**Reads.** `text(doc)` for every document in the pack; `manifest` for what the
pack contains; the template source for `data-encl` markers only.

**The algorithm, in two halves. Both are required — either alone is a proxy.**

**Half A — the cue sweep. Nothing claims an enclosure without declaring what.**

```
CUE = /\b(
    enclosed | enclosure | attached | accompanies | accompanying
  | (?:is|are) included with | included with (?:this|your)
  | we have included | returned with this letter | (?:sent|comes) with this letter
)\b/i
```

For every sentence of `text(doc)` matching `CUE`, the corresponding source span
must sit inside an element carrying `data-encl`. If it does not:

> **FAIL — unclassified enclosure claim.** `<doc>`: "<sentence>". Wrap it in
> `<span data-encl="…">` naming what it promises, or `data-encl="none"`.

This half is what stops the check degrading into "only finds what somebody
remembered to annotate," which is exactly the proxy trap in
`SOFTWARE-TENETS.md` §0.

**Half B — resolution. Every declared claim resolves.**

`data-encl` takes one of four value kinds:

| Value | Meaning | Resolved against |
|---|---|---|
| a document key (`fee-estimate`, `records-release`, `invoice`, `engagement-letter`) | **we** enclose a SATC-rendered document | `manifest.Documents[].key` |
| `attachment:<id>` (`attachment:payment-voucher`, `attachment:organizer`, `attachment:return-copies`, `attachment:client-records`) | **we** enclose something this software did not render | `manifest.Attachments[].id` |
| `client` | **the client** encloses it, or it is theirs already | not resolved — passes unconditionally |
| `none` | the sentence explicitly says it is NOT enclosed ("will follow separately") | not resolved — passes unconditionally |

`engagement-letter` is a **role**, satisfied by any of `tax-letter`,
`business-letter`, `ccorp-letter`, `bookkeeping-letter`. Resolve roles through
a small alias map, or the fee estimate's *"Accompanies our engagement letter"*
fails in every pack.

**How it treats an enclosure by the CLIENT rather than by us — the case you
asked about.** It does **not** guess from the sentence. Direction is a
declaration (`data-encl="client"`), and Half A forces the author to make it.
The reason this must be declared and not inferred: the two directions are not
distinguishable by grammar in this corpus. Compare, from the disengagement
letter — *"Your original records are returned with this letter"* — with a
plausible future organizer sentence — *"Return the completed organizer with the
documents you have gathered."* Both use a second-person possessive, both use an
enclosure cue, and one is our obligation while the other is the client's. A
regex that gets this right on today's thirteen sentences gets it wrong on the
fourteenth. **A `client` declaration is never resolved and can never fail** —
its only job is to satisfy Half A so the sentence is not reported as
unclassified.

**Scope guard.** `manifest` absent → the check reports
`L1: skipped — no manifest (single-document render)` and does **not** pass. See
§3 for what happens when this guard is missing.

**False-positive risk after Half B.** None constructible. A failure means the
manifest does not list a key the page names, which is either a missing document
or a mis-declared marker. Both need fixing.

**Fires today: 55 enclosure claims across 29 packs, 0 unresolved.** The pack
assembler is currently honest. The check exists so it stays that way.

**Migration cost — the 13 sentences to annotate:**

| Template | Sentence | `data-encl` |
|---|---|---|
| Engagement Letter — Bookkeeping §05 | "…the amount shown on the estimate accompanying this letter" | `fee-estimate` |
| Engagement Letter — Business Return §07 | same | `fee-estimate` |
| Engagement Letter — C Corporation §06 | same | `fee-estimate` |
| Engagement Letter — Tax Preparation §06 | same | `fee-estimate` |
| Fee Estimate, header | "Accompanies our engagement letter" | `engagement-letter` |
| Onboarding Letter §03 | "We have included a short authorization for you to sign." | `records-release` |
| Disengagement §04 | "Your original records are returned with this letter…" | `attachment:client-records` |
| Disengagement §04 | "Copies of everything we prepared for you are included." | `attachment:work-copies` |
| Disengagement §05 | "The invoices are enclosed…" | `invoice` |
| Extension Notice §02 | "…the instructions in the enclosed voucher or the link we sent with it" | `attachment:payment-voucher` |
| Organizer Cover, opening | "Your organizer for the \<\<TaxYear\>\> tax year is enclosed." | `attachment:organizer` |
| Organizer Cover, closing | "Your engagement letter and estimate for this year will follow separately." | `none` |
| Delivery Letter §04 | "Estimated payment vouchers are included with your copies." | `attachment:estimate-vouchers` |

**Five of the thirteen name artifacts this software does not render.** The real
work is not the check, it is adding `Attachments[]` to
`packaging.manifest(...)` and making whoever assembles a pack declare what went
in the envelope. Without that, the extension notice's voucher promise — the one
a client literally cannot pay without — stays unchecked. Say so to the firm
plainly.

**One thing this check will surface immediately.** The disengagement letter says
*"The invoices are enclosed"* and `disengagement-letter` appears in
`cli.DOCUMENTS` but in **no** `packaging.PACKS` entry. It is assembled by a
human. That is the exact configuration the records-release bug shipped from.

---

### L2 · Section numbers on the rendered page are 01…N, contiguous, no repeats
*(T13, T26 · catches 26 live defects)*

**Why it blocks.** It catches two different real failures with one rule that
needs no registry:
- a dropped `[[IF]]` section leaving a gap — **live in 26 of 55 rendered
  documents today** (§0.1);
- both halves of an inverse pair rendering, which is T13's contradiction shape
  reaching the page.

**Reads.** The rendered HTML only.

**Algorithm.**
```
nums = [m.group(1) for m in re.finditer(r'<h2><span class="n">(\d+)</span>', rendered)]
if not nums: report "skipped — unnumbered document"; return
expect = [f"{i:02d}" for i in range(1, len(nums)+1)]
if nums != expect: FAIL f"section numbers on the page read {nums}, expected {expect}"
```

**False-positive risk. None constructible.** A client-facing document either
numbers its sections consecutively or it does not, and there is no document in
this set for which 01, 02, 04, 05 is correct.

**It must read the rendered page, not the template.** Run against template
source with every `[[IF]]` branch kept, it reports the disengagement letter as
`01 02 03 04 05 05 06 07` and the delivery letter as `01 02 03 03 04 05 06 07`
— both correct-by-design mutual exclusions, both false positives. **2 false
positives on templates, 0 on rendered output.** Second proof of §2.1.

**Fires today: 26 of 55 rendered documents.** Nine of twelve would be a signal
the check is wrong. Twenty-six of fifty-five, all the same document type, all
the same missing number, all traceable to one unimplemented FIELDS instruction,
is a systemic bug found. **Fix the renumbering before turning this gate on**, or
it blocks every send on day one — which is the correct outcome but not a useful
launch.

---

### L3 · A cited clause name exists
*(T21)*

**Reads.** Rendered HTML of the citing document; `<h2>` texts of the four
engagement-letter templates.

**Algorithm.**
```
CITE = /(?:<b>|<strong>)([^<]{4,60})<\/(?:b|strong)>\s*section of your engagement letter/gi
heads = { normalize(h2 text) for h2 in all engagement-letter templates }
for name in CITE captures:
    if normalize(name) not in heads: FAIL f"no engagement letter has a section named {name!r}"
```
`normalize` = collapse whitespace, strip trailing comma, case-fold.

**False-positive risk.** A clause cited from a letter this client will not
receive. Resolving against the **union** of the four letters removes it.

**Fires today: 7 citations, 7 resolve, 0 failures.** Value is pure regression:
this is the only thing that would notice a section rename in an engagement
letter silently orphaning pointers in four other documents.

---

### L4 · The compliance floor is present
*(T23a)*

**Reads.** `text(doc)`; `registry/required.yaml`.

**Algorithm.** For each entry whose `applies_to` includes this document key:
every list in `must_contain_all` must have at least one member present in
`text(doc)` (case-insensitive, word-boundary). Otherwise:

> **FAIL — the compliance floor for `<id>` is not on the page.** Missing:
> `<the group with no member found>`.

**Why keyword groups and not sentences.** T28: no test may pin his prose. He
must be able to reword the negation; he must not be able to delete it. Groups
allow the first and forbid the second.

**False-positive risk. None constructible.** The check asserts presence, never
absence. A reworded negation that keeps its words passes; one that loses the
word "assurance" has lost the negation.

**Fires today: 0 of 12.** All four engagement letters carry the negation. Seed
`required.yaml` with these, which is the whole of what T23 protects today:
`no-assurance-engagement` (4 letters), `no-audit-verification` (4 letters),
`unprotected-at-your-own-risk` (4 letters + onboarding + organizer),
`extension-is-not-more-time-to-pay` (3 letters + extension notice),
`estimate-is-not-final-liability` (extension notice).

---

### L5 · A retired sentence is absent from every rendered document
*(T7, T9, T24, T26, T27 · catches 1 live defect)*

**Reads.** `text(doc)` for all twelve templates plus every rendered document;
`registry/retired.yaml`.

**Algorithm.**
```
for phrase in retired.yaml:
    for line in text(doc) that is NOT a heading line:
        if normalize(phrase) in normalize(line): FAIL
```
`normalize` = lowercase, collapse whitespace, strip punctuation.
**Heading lines are excluded** — matched by `^\d\d\s` or by the source element
being `<h2>`/`.h`. This is not a fudge; it is the fix for the one false positive
the check produces, and it is exact.

**`retired.yaml` shape** — one entry per sentence the firm has deleted:
```yaml
- phrase: "Sign through Encyro and it comes straight back to us."
  retired: 2026-08-26
  why: "T9 — the reason tail. Replaced by 'If this letter states your understanding, sign below.'"
```

**False-positive risk.** A retired phrase that is a substring of legitimate
copy. Measured: 1 of 2 hits today (the *"this estimate assumes"* / *"What this
estimate assumes"* collision). Removed by two rules, both enforceable in the
registry loader: (a) store the whole retired sentence, not a prefix; (b) refuse
to load a `phrase` shorter than five words, since a short phrase cannot be a
sentence and will collide.

**Fires today: 2 hits → 1 after the fixes above, and that one is a real
defect** (§0.2). Best signal-to-noise in this document.

**Seed `retired.yaml` with the 30 phrases named in `DOCUMENT-TENETS.md`.** Only
one of them is currently live; the other 29 cost nothing and are the regression
suite for four separate tenets.

---

### L6 · No hard-banned legalese, and no British spelling
*(T20a, T10b)*

**Reads.** `text(doc)` only.

**Algorithm.** Two word-boundary, case-insensitive sweeps:
- `governs | constitutes | pursuant | at our discretion | deemed | shall be | herein`
- `authorisation | organis(e|ed|ing|ation) | recognis(e|ed) | realis(e|ed) | licence | behaviour | centre | cheque | whilst | amongst | programme | enrol`

**`accompanies` / `accompanying` is NOT in the first list.** It is in T20's
written list and it is live in five templates in copy the firm has approved four
times. Ship the check without it and raise the discrepancy as an amendment to
`DOCUMENT-TENETS.md`.

**False-positive risk.** A proper noun containing a British spelling (a quoted
authority name). None in this corpus; add a stop-list entry if one arrives.

**Fires today: 0 of 12 rendered.** Three British spellings exist in template
`.ref` blocks and are correctly invisible to a check that reads rendered output.

---

## 6 · The advisory set

Prints as a note. Never blocks. Each carries the condition for promotion.

| # | Tenet | Check | Fires today | Promote when |
|---|---|---|---|---|
| A1 | T11 | certainty hedges (`will likely`, `typically`, `generally`, `in most cases`, `usually`) | 0 / 12 | one full cycle at zero. Best promotion candidate in the set — the corpus is already swept, so any future hit is new prose. |
| A2 | T23b | banned assurance word in a sentence with no negation marker | 0 / 12 loose · 2 false positives strict | never, on the strict form. On the loose form, one cycle at zero. |
| A3 | T20c | sentence over 28 words — **top five only, longest first** | 21 / 12 templates, ~1 true positive | never. Its job is to show a human the 50-word officer-compensation sentence, not to gate. |
| A4 | T19 | paragraph over three sentences, excluding T23-protected paragraph ids | 9 raw · 0 after exclusion | never — nothing left to fire on. |
| A5 | T8 | narrating our own tone or inability | 0 / 12 | one cycle at zero, and only after the pattern is stress-tested against a mutation (§8). |
| A6 | T15 | disapproving of the client's choice | 0 / 12 | one cycle at zero. |
| A7 | T16 | virtue claim — **scoped to the website and the published fee schedule** | 0 / 12 templates | never on client letters: T9's own kept sentence *"costs nothing"* trips it. |
| A8 | T18 | a list-item label containing a sentence period or semicolon | 0 / 17 request entries | one cycle at zero. |
| A9 | T2 | heading echo — **against `phrases:` values only, never template prose** | 0 in phrases · 1 false positive in prose | never against prose. |
| A10 | T21 | cited clause resolves against **this client's specific** letter, not the union | 7 / 7 resolve | never — the bookkeeping letter lacks three sections the others have. |

---

## 7 · The ones to drop

Building any of these does more harm than good. Dropping a tenet from the
linter does not weaken the tenet; it says a machine is the wrong instrument.

| Tenet | Why dropped | Measured |
|---|---|---|
| **T1** (verbatim cross-document duplication) | Directly contradicts `consistency.py`, which **requires** the repeated scope lines. No filter separates a mandated repeat from a caption. | 10 / 29 packs, **10 false positives, 0 true** |
| **T6** (demonstrative openers) | The opener is a proxy for "does this sentence add a fact", and the two live hits are load-bearing. The clearest tenet in the file is the least mechanizable. | 2 hits, **2 false positives, 0 true** |
| **T7** (self-evident consequence) | "Self-evident" is a claim about a reader. The three real instances share no surface form and are covered exactly by L5. | n/a |
| **T9** (reason tail) | The tenet carves out reader-owned consequences, and the entire positive model in §0 consists of them. | em-dash form: 19 hits across 9/12, ~0 true |
| **T13** (general contradiction) | Contradiction detection over English. The two shapes that occurred are covered by `supersedes:` and by L2. | n/a |
| **T14** (blame transfer) | The tenet explicitly permits assigning responsibility. The difference is what the sentence is *for*. | 1 hit, **1 false positive** |
| **T17** (first six words) | An editing note about one document, generalized into a rule the other eleven correctly break. | **6 / 12 fire, all six correct copy** |
| **T18** (conjunction = two asks) | Three live labels join one ask with "and". | 3 hits, **3 false positives** (sub-check survives as A8) |
| **T23d** (PII in client letters) | Client letters are addressed to clients by legal name. T23's PII rule is about artifacts and logs — a different pipeline with its own guards. | would fire **12 / 12**, all wrong |
| **T24** (flagged twice → delete) | A property of git history, not of a document. A send gate on edit count blocks careful editing. | not measurable from document inputs |
| **T25** (don't answer a ruling with prose) | T1's judgement in a different hat. Enforced socially by the sign-off register. | n/a |
| **T27** (sweep detector) | Sibling templates legitimately differ; bookkeeping is a different service and the entity letters are about entities. | 44 partials, **~0 true positives** |
| **T28** (prose-in-Python detector) | The heuristic finds operator-facing error text, which is where long English sentences legitimately live in this codebase. | **94 hits, ~0 true positives** |

Plus three that need no new code because they are already enforced: **T4**,
**T12**, **T22**.

---

## 8 · Check the checker

Each gate is proved the way the render gate was proved — break a document on
purpose, confirm the gate catches it, revert. **A gate that has not been seen to
fail has not been seen to work.** Add each of these as a test that asserts the
failure, in `client-documents/tests/test_tenet_lint.py`.

| Gate | Exact mutation | Expected |
|---|---|---|
| **L1** Half B | In `packaging.CONDITIONAL`, comment out `{"records-release": "PriorFirm"}`. Render the `ind-prior-firm` engagement. | `FAIL onboarding-letter promises records-release: "We have included a short authorization for you to sign."` — **verified: this mutation fires, run 27 Aug** |
| **L1** Half B, role alias | In `packaging.PACKS["individual"]`, remove `"fee-estimate"`. Render any individual pack. | 1 failure per engagement letter — `promises fee-estimate` |
| **L1** Half B, attachment | Render an extension notice with `PaymentEnclosed: true` and a manifest whose `Attachments[]` omits `payment-voucher`. | `FAIL extension-notice promises attachment:payment-voucher` |
| **L1** Half A | In the delivery letter template, replace `<span data-encl="attachment:estimate-vouchers">Estimated payment vouchers are included with your copies.</span>` with the bare sentence. | `FAIL unclassified enclosure claim` — proves the gate is not blind to a sentence nobody annotated |
| **L1** direction | Add `<p data-encl="client">Send the completed organizer with the documents you have gathered.</p>` to the organizer letter and render it in a pack containing nothing else. | **passes.** Proves a client-side enclosure is not treated as our promise. |
| **L1** scope guard | Render a fee estimate alone, no manifest. | `L1: skipped — no manifest`, **not** a pass and **not** a failure |
| **L2** gap | Delete `<h2><span class="n">03</span>Signing the e-file authorization</h2>` … through its `</div>` from a rendered delivery letter. | `section numbers read ['01','02','04','05','06','07'], expected ['01'…'06']` |
| **L2** repeat | Render a delivery letter from a record with `EFiled: true` **and** `PaperFiled: true`. | `section numbers read [… '03','03' …]` — proves L2 subsumes the T13 inverse-pair check on real records, which `test_merge.INVERSE_PAIRS` does not |
| **L2** live regression | Render any onboarding letter with `PriorFirm` false, **before** the renumbering fix. | fires — this is §0.1, and it must go red before it goes green |
| **L3** | In `SATC Engagement Letter - Tax Preparation.html`, rename section 07 from *Your records, our files, and delivery* to *Your records and our files*, and do the same in the other three letters. Render a delivery letter. | `no engagement letter has a section named 'Your records, our files, and delivery'` — the silent-orphan case |
| **L3** false-positive guard | Rename in **one** letter only. | still fires (union resolution) — confirm this is the intended strictness before shipping |
| **L4** | Delete *"We do not perform audits, reviews, or any assurance engagement"* from the tax letter. Render it. | `the compliance floor for no-assurance-engagement is not on the page. Missing: ["assurance"]` |
| **L4** reword-tolerance | Rewrite the same sentence as *"We perform no audit, no review and no assurance engagement of any kind."* | **passes.** Proves L4 does not pin his prose (T28) |
| **L5** | Add `"That is a boundary, not a brush-off."` to any template body. | `retired phrase live in <doc>` |
| **L5** heading guard | Leave the fee estimate's heading *"What this estimate assumes"* untouched with `"this estimate assumes"` seeded as a short phrase. | the registry **loader refuses the entry** (under five words), before the scan runs |
| **L5** live regression | Run against `SATC Engagement Letter - Bookkeeping.html` as it stands. | fires on the Encyro tail — §0.2, red before green |
| **L6** legalese | Change *"outlines what each of us is responsible for"* to *"governs what each of us is responsible for"* in any letter. | `banned word 'governs'` |
| **L6** British | Change *"the signed authorization"* to *"the signed authorisation"* in the delivery letter **body**. | fires |
| **L6** proxy guard | Leave the three existing British spellings in `.ref` blocks untouched. | **does not fire.** Proves the linter reads the rendered page, not the file |
| **all** denominator | Run the suite against an empty pack. | every check reports `skipped, 0 examined` — **never** `pass`. This is S2, and it is the failure mode that produced "0 disagreements" while comparing nothing. |

---

## 9 · Reporting contract

Non-negotiable, from `SOFTWARE-TENETS` S2 and S4.

1. **Every check prints its denominator.** `L1: 55 enclosure claims across 5
   documents, 0 unresolved.` Never a bare `pass`.
2. **Blocking and advisory print in separate sections, blocking first.** S4: a
   tool that overstates what is broken destroys belief in the part that is true.
3. **A skipped check prints as `skipped` with the reason**, and a skip is never
   counted toward a pass.
4. **The exit code reflects blocking failures only.** Advisories never change
   it, or they will be muted and take the six real gates with them.
5. **A blocking failure names the document, the sentence, and the fix** — not
   the tenet number alone. `T21 violation` is unactionable; `no engagement
   letter has a section named 'Your records, our files, and delivery' — rename
   the citation in the delivery letter or restore the heading` is a next step.
6. **Promotion is recorded.** When an advisory is promoted, note the cycle it
   cleared and the date in `docs/sign-off-register.md`. An undocumented
   promotion is a gate nobody agreed to.

---

## 10 · Order of work

1. Fix §0.1 — renumber sections after a dropped `[[IF]]`. **26 rendered
   documents are wrong right now.** Do this before L2 exists, or L2 blocks every
   individual send on the day it ships.
2. Fix §0.2 — delete the Encyro tail from the bookkeeping letter.
3. Build `registry/retired.yaml` (30 seed phrases) and `registry/required.yaml`
   (5 seed floors). These are the two files the firm can edit; nothing else in
   this spec holds his words.
4. Ship **L5, L6, L2, L4** — no template changes needed, and two of them are
   already red.
5. Ship **L3** — no template changes needed.
6. Add `Attachments[]` to `packaging.manifest`, annotate the thirteen sentences
   in §5 L1, then ship **L1**. This is the largest piece of work and the check
   the firm asked for by name.
7. Add the advisories A1–A10 behind a `--notes` flag, off by default until one
   clean cycle.

---

## 10a · What shipped, and what the first run measured

**All ten advisories shipped, 27 August 2026**, in `client-documents/notes.py`,
behind `package --notes`. `notes.note()` is the only constructor in the module
and it hard-codes `blocking=False`, so "nothing here can stop a pack" is a
property a test asserts rather than a claim in a docstring.

Measured over the 27 rendered packs in `out/exercise`:

| # | Fires | Examined | Against §6's estimate |
|---|---|---|---|
| A1 | 0 | 2,500 sentences | 0 — as specified |
| A2 | 0 | 2,500 sentences | 0 — as specified |
| A3 | 59 (6 distinct sentences) | 2,500 sentences | consistent; the 51-word officer-compensation sentence is the worst, as predicted |
| A4 | 0 | 919 paragraphs, 6 compliance paragraphs excluded per pack | 0 after exclusion — as specified |
| A5 | 0 | 2,500 sentences | 0 — as specified |
| A6 | 0 | 2,500 sentences | 0 — as specified |
| A7 | 0 | 837 published phrases | 0 — as specified |
| A8 | 0 | 540 request labels | 0 — as specified |
| A9 | 0 | 34 list items under a long-enough heading | 0 — as specified |
| A10 | 0 | **0 cited clauses** | correct and empty; see below |

**Three things the build found that the specification did not.**

1. **`cited_clauses` — the blocking L3 — was passing having examined nothing.**
   All seven live citations are in the delivery letter, the disengagement
   letter, the extension notice and the invoice. None of those is in an opening
   pack, so on all 27 packs the gate printed `ok every cited clause name is a
   real section` while resolving zero citations. §8's "all denominator" row
   predicted this failure mode for an *empty* pack; it was live on every real
   one. **Every check in `presend.gate` now reports its denominator**, and a
   check with nothing to look at prints `NONE`, never `ok`.

2. **A3 read the masthead as a sentence.** Flattening a document and splitting
   on full stops made the firm name, address, document title, client name and
   first heading into one 74-word "sentence" — none of it ends in a full stop.
   Measured that way A3 fired **162 times**; §6 counted 21 by hand. Fixed by
   reading paragraphs and bullets as blocks, headings excluded.

3. **A4's exclusion needed a floor rule that did not exist.** §6 names the
   billing-and-suspension paragraph as T23-protected, but `required.yaml` had
   no entry for it, so A4 fired 27 times and the only fix it offered was to
   delete protected text. Added as `unpaid-invoice-and-late-filing` — keyword
   groups, not pinned prose — which also gives the blocking floor a rule it was
   missing. All four engagement letters carry it; a mutation test proves the
   rule fires when it is removed.

**Promotion status: none.** Every advisory is on cycle one. `A1` remains the
best candidate, for the reason §6 gives.

---

## 11 · Corrections owed to `DOCUMENT-TENETS.md`

Found while measuring. None are lint hits; all are stale text in the tenets
file, and they should be fixed by a human because the tenets file is his.

- **T20's banned-word list contains `accompanies`**, which is live and approved
  in five templates. Remove it from the list, or strike the five sentences —
  four rounds of review say remove it from the list.
- **T8's line reference is stale.** The sentence it names is no longer at
  `SATC Extension Notice.html:95`; the extension notice now reads *"If something
  on this list does not apply to you, just tell us."* — the corrected form. T8's
  "still live" claim is **no longer true**.
- **T14's line reference is stale.** `SATC Tax Return Delivery Letter.html:67`
  is now an `[[END EACH]]` marker; section 02 opens with the firm's own *"Review
  your returns"*. T14's "still live" claim is **no longer true**.
- **T9's line reference is correct and the defect is real.**
  `SATC Engagement Letter - Bookkeeping.html:124` still carries the long
  signature line. This is §0.2.
- **T27's "unswept instances: T1, T8, T9, T14"** should now read **T9 only**.
