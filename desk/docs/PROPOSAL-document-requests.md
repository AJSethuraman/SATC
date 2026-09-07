# Requesting a document a desk asks for — what exists, and where the seam is

**The question this answers.** Eight of the 43 questions from a real close
(`CLOSE-QUESTIONS-TRIAGE.md`, kind **C**) resolve by asking the client for a
document nobody asked for. The firm, on Q26:

> *"yeah this connects to the vehicle expenses there should be something telling
> us to get like loan statements and stuff to make sure we understand the deal"*

And the closing agent, on Q38: *"The order history resolves every one of them and
nobody asks for it."*

So: can a desk outcome reading *request the loan statement* reach the thing that
actually requests documents?

**No. And the two projects are further apart than the triage assumed.** The
triage says *"`client-documents/` already runs the engagement's document list."*
That is true of a **tax return onboarding letter** and of nothing else. The close
that produced these 43 questions is **bookkeeping work**, which `client-documents`
cannot open an engagement for at all. Meanwhile a second, unrelated document
register — with outstanding/received state, chasing, and follow-up rounds —
already exists in `satc_system`, and the interview PRD explicitly declined to
wire the two together.

Everything below is checkable. Every path and line number was opened.

---

## 1 · What exists today

### 1a · `client-documents` — one list, composed once, never revisited

**Where the list lives.** `client-documents/registry/document-requests.yaml` —
**20 entries**, each `document:` + `detail:` + an optional `when:` gate. Its own
header states the contract:

> `# THE WORDING IS THE FIRM'S. Every `document` and `detail` below prints on a`
> `# client's letter, so it lives here rather than in Python`

**What builds it.** `client-documents/requests.py:52`, `for_answers(answers)` —
walks the registry in registry order and keeps every entry whose gate holds.

**What decides which entries fire.** `pricing._gate_holds`
(`client-documents/pricing.py:371`, public alias at `:426`). A **closed** set of
five operators: `schedules_any`, `schedules_none`, `schedules_none_of`,
`answer_is`, `answer_includes`, `any_of`. Every one of them reads the
**interview answers dict** and nothing else. There is no operator that can read a
fact discovered later, because there is no place a fact discovered later is
written.

**When it is built — once, at engagement creation.**
`client-documents/intake.py:101`, inside `compose_record`:

```python
record["RequestList"] = requests.for_answers(answers)
```

with the reason stated in the comment above it: *"A letter regenerated in a year
should ask for what we asked for then, not what today's registry would ask for."*
The only other caller is `client-documents/cli.py:2540`, which rebuilds the
sample package. `grep` for `RequestList` across the project finds no third writer.

**It is rebuilt on a re-quote, and silently.** `requote.py:295` calls
`intake.compose_record` again, so changed answers do move the request list. But
`requote.SCOPE` (`requote.py:84`) is `("FederalReturns", "StateReturns",
"LocalReturns", "AdditionalForms", "EntityType", "PeriodLabel")` — `RequestList`
is not in it, so a re-quote that changes what we are asking the client for
reports the price move and the scope move and says nothing about the documents.
Nothing re-sends the onboarding letter either.

**Nothing records what arrived.** There is no received/outstanding state anywhere
in `client-documents`. `grep -rn "received"` over its Python finds only prose. The
list is printed on a letter and then forgotten.

**The one place a human can type a new ask** is the extension notice's
`OutstandingItems` — declared at `registry/fields.yaml:610`, collected as a
free-typed table at `registry/lifecycle.yaml:128`. The field registry says what it
should be and admits it is not:

> `What is still missing: the onboarding letter's RequestList minus what arrived.`
> `Done by hand it drifts, and a client chased for something they already sent`
> `stops reading these letters.`

The organizer letter's `Requested` list (`registry/lifecycle.yaml:88`,
`registry/fields.yaml:572`) is the same shape — typed by the preparer at event
time, **not** derived from `document-requests.yaml`. So the registry drives
exactly one document: the onboarding letter.

### 1b · The bigger problem: this pipeline cannot open the engagement in question

`client-documents/registry/interview.yaml:1-27` states its own scope:

> `# Scope: TAX RETURN PREPARATION only`
> `# Bookkeeping fields exist in the registry and are still not asked here.`

Held open by a test that exists to stop it being forgotten —
`client-documents/tests/test_coverage.py:217`,
`test_bookkeeping_has_no_interview_and_that_is_recorded_not_forgotten`, with the
comment at `:53`: *"Bookkeeping is a separate engagement with no interview at
all."* `intake.RETURN_TYPE` (`intake.py:37`) maps only `1040/1120S/1065/1120`.

**All 20 registry entries are tax-return documents.** The closest thing to any of
the eight is the entity line, transcribed from the business engagement letter:

> `- document: "Your books for the period, closed and reconciled"`
> `  detail: "Including bank and card accounts, loans, and any activity outside the accounting system"`

That gates on `federal_form` being `1065`/`1120S`/`1120` — a tax return, not a
bookkeeping engagement — and it asks for *the books*, not for the statements
behind them.

### 1c · `satc_system` — the register that actually tracks asks, and nobody joined it up

This is the part the triage did not know about. `docs/prd-interview-and-field-registry.md:65`
put it out of scope in one line:

> **`satc_system` integration.** Its intake module is a post-engagement
> document-request engine, a different animal. No wiring in this build.

What is there:

| | |
|---|---|
| `satc_system/src/satc/models/evidence.py:55` | `RequestedItem` — `doc_type`, `request_text` ("the exact ask, in the words the client reads"), `blocking`, `status`, `requested_at`, `follow_up_round`, `parts` |
| `satc_system/src/satc/intake/fanout.py:600` | `_open_requests` — mints one `RequestedItem` per client-facing task; ids derived from `{client, year, job, template}` so re-running opens no duplicate |
| `satc_system/src/satc/intake/service.py:175` | writes them alongside the engagement |
| `satc_system/src/satc/intake/service.py:378` | `reconcile_received` — a document arriving flips the matching request to received |
| `satc_system/src/satc/intake/chasing.py:144` | `waiting()` — every outstanding request, longest wait first |

And the asks themselves live in workflow YAML, not in Python:
`satc_system/configs/workflows/`. Two of them are directly on point.

`business_monthly_bookkeeping.yaml` already carries, **unconditionally**:

> `- template_id: monthly-request-bank-statements`
> `  title: Request bank, credit card, and loan statements`

plus payroll reports (gated on `usesPayroll`), an inventory report, and a
"transaction question list to client" task.

`business_year_end_cleanup.yaml` already carries asset purchase/disposal
documents, annual payroll reports, W-9s, and a "suspense item question list".

**So a loan-statement request is already written down in this repository** — in
the project the close-questions triage does not mention, in a workflow the closing
agent evidently was not running.

### 1d · What none of it has

**There is no path anywhere by which something discovered DURING the work adds to
what is requested.** Not in `client-documents`, where the list is a pure function
of interview answers evaluated once. Not in `satc_system`, where `_open_requests`
walks `job.tasks`, and a task only exists because a workflow template's
`condition` matched an **intake answer**. The nearest affordance is
`satc_system/src/satc/intake/workflows.py:105` — `apply_overrides`'s
`added_questions`, which lets the practice add a question and a request to a
**workflow definition** (all future clients on that workflow), not to one live
engagement.

The only way a mid-work discovery reaches either register today is a human
re-running the intake with a changed answer, and only if the discovery happens to
correspond to a question the workflow already asks.

That is the finding. State it plainly: **a desk that concludes "request the loan
statement" has nothing to hand it to.**

---

## 2 · The eight documents

Named in the firm's terms where they gave them. "Could the pipeline already ask?"
is answered separately for each of the two registers.

| Q | The document that settles it | `client-documents` | `satc_system` workflows |
|---|---|---|---|
| **Q10** municipality: permit, tax or draw | **The town's bill.** The closing agent: *"The town's bill settles it in one look."* The firm: *"this is a good question I'm not really sure how did you deduce something like this"* | No entry; no gate could fire | No task requests it |
| **Q11** a convenience fee implies a missing payment | **The statement for whichever account paid the tax**, and the tax payment confirmation. The triage: *"Which account paid it is data nobody holds"* | No | Only via the standing "bank, credit card, and loan statements" ask — and only if that account is known to exist |
| **Q15** which policies the premium covers | **The policy schedule.** The firm: *"yeah insurance questions are just fair in general and the outcome to this may be even like hey this is what you need to know in order to proceed"* | No | No |
| **Q26** is a loan hiding in the deposits | **The loan statements.** The firm: *"there should be something telling us to get like loan statements and stuff to make sure we understand the deal"* | No — the entity "books... including bank and card accounts, loans" line names loans but asks for the books | **Yes** — `business_monthly_bookkeeping.yaml`, `monthly-request-bank-statements`, unconditional |
| **Q36** what settles an unidentifiable cheque | **The cheque image, or the client's own cheque register** | No | No — the closest is `year-end-send-suspense-questions`, a question list rather than a document |
| **Q38** marketplace order history | **The marketplace order history.** *"The order history resolves every one of them and nobody asks for it"* | No | No |
| **Q41** a statement cycle that does not end at year end | **The bracketing statement** — on this client, the February statement, which *"was requested"* by hand | No | Partly — the standing statements ask does not say *which cycles*, and the year-end opening needs the pair that brackets 31 December |
| **Q43** payroll sweep and the wage cost | **The payroll register.** Without it *"the split cannot be made"* | No | **Yes** — `monthly-request-payroll-reports` (gated `usesPayroll`) and `year-end-request-annual-payroll-reports` (gated `hasPayroll`) |

**Two of eight are already askable, in `satc_system`, on a workflow nobody
appears to have been running.** Six are askable by neither.

Q39 is not in the eight but belongs beside them: *"payments went to a card that
was not a registered source account ... and nothing in the close notices."* The
triage files it as **E** with **C** secondary, and its remedy is the same
statement request.

---

## 3 · The seam

### The honest answer first

**`desk` should not write to either register, and should not import either
project.** Three reasons, none of them stylistic:

1. `desk` is offline by construction (`desk/conftest.py` replaces the socket
   layer) and holds no client data. A dependency on a store holding real client
   records inverts that.
2. `DESIGN-PRINCIPLES.md` § 9, *Propose, never dispose*: *"the action queue writes
   nothing; a model-classified arrival cannot close a client request."* A desk
   minting a live client-facing ask is disposal.
3. `DESIGN-PRINCIPLES.md` § 13, *A queue that becomes noise is worse than no
   queue*. A desk that can open requests will open duplicates of things already
   asked, and the register has no way to know that a desk's "loan statement" is
   the standing "bank, credit card, and loan statements" row.

So the seam is not a call. **It is an outcome plus a proposal file, and a human
click.**

### The smallest change that is actually useful

**One new escalation reason in `desk/engine.py`, and nothing else in `desk`.**

`engine.REASONS` (`desk/engine.py:56`) is a closed nine-value set; `unsupported.QUESTION_REASONS`
(`desk/unsupported.py:60`) is the two-value subset a *question* can honestly be
in, `("authority_absent", "facts_not_established")`, and `test_unsupported`
proves the subset relation so the two cannot drift.

Today a Q26 lands in `authority_absent` — the queue whose resolution is *add the
authority, cited* — where no authority is missing. `facts_not_established` is
closer and still wrong: it means *ask the client*, and the firm's whole point is
that this one is settled by **a piece of paper**, not by a phone call.

Add **`document_not_requested`** to `REASONS` and to `QUESTION_REASONS`. The
working already says which document. That is:

- one tuple entry in `engine.py`,
- one tuple entry in `unsupported.py`,
- the subset test passes unchanged,
- **cost: under an hour, and it couples nothing to anything.**

What it buys: the eight stop being counted as a gap in the authority record, and
the queue file becomes a readable list of *documents nobody asked for*, in the
desk's own words, with the reasoning intact — which is exactly what
`unsupported/` is for.

### The seam beyond that, described and not built

If and when a request should actually be opened, **the join is `satc_system`, not
`client-documents`.** `client-documents` composes a list once for a letter;
`satc_system` holds asks with state, chasing, and a reconcile-on-arrival path.
The shape:

1. A desk's `document_not_requested` entry names a `doc_type` and a
   `request_text` **in the words the client reads** — the two fields
   `RequestedItem` already requires (`evidence.py:55-67`). The desk writes both
   into its own queue and stops.
2. A human, or a `satc_system`-side reader, turns a queue entry into a
   `RequestedItem` through the existing intake path. `RequestedItem` ids are
   derived from `{client, year, job, template}` (`fanout.py:600`), so this new
   source needs a template id of its own or it collides with the fan-out's.
3. **Nothing in `desk` imports `satc_system`.** The direction of the arrow is a
   person reading a proposal, which is the same shape `positions/` already has.

Three things that must be settled before anyone builds step 2, and none of them
is mine to settle:

- **Deduplication against a standing ask.** *"Request bank, credit card, and loan
  statements"* is already open on a monthly bookkeeping client. A desk asking for
  *the loan statement* must resolve to that row, not open a second. `RequestedItem.parts`
  (`evidence.py:82`) exists for exactly this shape of problem and would be the
  place to look.
- **Which register a bookkeeping close even has.** See §4.
- **Whether the six unaskable documents belong in a workflow YAML instead.**
  Q15's policy schedule and Q38's marketplace order history are not one-off
  discoveries — they are standing asks the firm has simply never written down.
  Adding six lines to `configs/workflows/business_year_end_cleanup.yaml` would
  settle six of the eight for every future client, permanently, with **no desk
  involvement at all** and no new code anywhere. That is very likely the higher-value
  change and it is a firm decision, not an engineering one.

### What NOT to do

Do not add a `discovered:` answer key to `client-documents`' interview and gate
new registry entries on it. It would work — `answer_includes` already exists for
exactly that shape (`pricing.py:407`, added 26 Aug 2026 for this registry) — and
it would put mid-engagement discoveries into a list that is printed on an
onboarding letter which has **already been sent**, with nothing that re-sends it
and nothing that records what came back. It would look like a fix.

---

## 4 · What I could not establish

- **Which pipeline the close was actually run through.** The 43 questions
  describe bookkeeping work — a chart of accounts, a bank feed, a card payable,
  a rules engine, a review queue. `client-documents` cannot open a bookkeeping
  engagement. `satc_system` has bookkeeping workflows. Neither
  `CLOSE-QUESTIONS-2026-09-05.md` nor the triage names the software the close
  ran on, and I found no engagement record for it. **Until that is answered, the
  seam has no far side** — nobody can say which register the desk's outcome
  should reach, because nobody has said which register that close used.
- **Whether the standing "bank, credit card, and loan statements" ask ever
  reached this client.** `business_monthly_bookkeeping.yaml` would have asked for
  the loan statements Q26 wants. Whether that workflow was used, or whether the
  client is on one at all, I could not determine from the repository.
- **`client-documents/docs/WHERE-THINGS-STAND.md` does not exist.** The only
  `WHERE-THINGS-STAND.md` in the repo is `/home/user/SATC/docs/WHERE-THINGS-STAND.md`
  (repo root, 133 lines, dated 3 September 2026), and it says nothing about
  document requests. `client-documents/docs/` holds one file,
  `prd-1040-fee-estimate.md`.
- **`client-documents/docs/OPERATING-PROCEDURES.md` does not exist either.** The
  generated procedures live at `/home/user/SATC/docs/OPERATING-PROCEDURES.md`.
  Not read, not touched.
- **The `satc_system` request register was not exercised.** I read the model, the
  fan-out, the service and the chasing sweep; I ran nothing. Whether
  `reconcile_received` behaves as its docstring says is asserted by its own tests,
  which I did not run.
- **Whether the firm wants any of this automated at all.** Their words on Q26 are
  *"there should be something telling us to get like loan statements"* — "telling
  us", not "asking the client". That may describe a prompt to the preparer rather
  than an ask to the client, and the two are different builds. I did not
  paraphrase it into a requirement; it is quoted here so the next session argues
  with the sentence and not with my reading of it.

---

*Written 5 September 2026. Nothing outside this file was changed. No test suite
was run.*
