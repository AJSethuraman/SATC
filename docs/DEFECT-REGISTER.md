# SATC — Defect Register

**Every known defect in this software that is not yet fixed, and every fix in
flight.** Started 3 September 2026 at the firm's instruction: *"always record
active fixes and bugs so you remember them and we can go over them together."*

## Why this is a third file and not one of the two that exist

- `docs/ERROR-LEDGER.md` records what the **agent** got wrong. A different
  question, and its answer — "reading the code caught nothing" — is the point of
  keeping it.
- `docs/SOFTWARE-TENETS.md` records what the **software** got wrong *after it was
  fixed*, as a lesson cited to a real bug.
- **This file is the part in between:** what is wrong *now*, what state the
  decision is in, and what proves it. An entry leaves here when it is fixed —
  and if it taught something general, it leaves a tenet behind.

**A defect is only listed here once it has been reproduced.** An unproven claim
belongs in a question to the firm, not in a register that reads as fact.

---

## Open — and this is the work queue, in order

Everything here is recoverable. The `satc_system` work that did not survive the
port is tagged **`parked/satc-system-pre-schema-port`** (= `055dcf3`, the tip of
PR #162 before it was closed). A tag rather than a branch, because branches get
deleted and a tag is how you say *keep this*. Recover any file with:

```
git show parked/satc-system-pre-schema-port:satc_system/src/satc/intake/chasing.py
```

| # | What | Costs | Needs |
|---|---|---|---|
| **S2** | **The chase panel** — "who owes us a document, longest wait first" — needs the bundle mechanism (`parts`, `is_bundle`, `outstanding`). Main did not rename it, it **deleted** it. Parked: `chasing.py` (171 lines), `test_chasing.py`, `test_bundle_stays_open.py` | the firm loses its morning list | a **product decision** first: does a bundle request ("core income documents") stay open when one part arrives? Then a `parts` column and a migration |
| **S3** | **`engagement_ref`** — the join between what a client sees (`2026-0001`) and what the system keys on (`SATC-001000`). The firm asked for it on 31 Aug: *"ADD THE FIELD"*. Main's `Engagement` has no such field, and `collect.py` still prints an error naming it. Parked: `test_engagement_ref.py` | the collector cannot close the request a document satisfies | a field on `Engagement`, a store column, a migration. **No product question — the firm already decided** |
| **S4** | **Page provenance.** The page is read and reported; it is not carried into the record. `source_ref.page` is `None`. `test_intake_carries_the_page_all_the_way_into_the_workpaper` is `xfail(strict=True)` — it fails loudly the moment this is fixed | a field cannot be cited to the page it came from | carrying `page` through `MapExtractor` into provenance. Smallest of the three |
| **S5** | **The reader ladder disagreement.** A text-layer PDF our anchors miss: #162 says never summon a model, main says fall through but say *"our anchors, not the document"*. Both argued, both defensible. `test_the_ladder_reaches_no_model_while_a_deterministic_rung_can_still_read` is skipped pending a decision | — | **a decision, not code.** A question about client documents |
| **S6** | `test_changing_a_rate_takes_effect_without_a_restart` is order-dependent — passes alone, fails after `test_price_editor`. **Confirmed on untouched main**, so it predates all of this | a green suite that is green by ordering | find the shared state and isolate it |

**Suggested order: S3, then S4, then S2.** S3 is decided and blocking a feature
that half-exists — `collect.py` already prints an error about the missing field.
S4 is the smallest. S2 needs the firm before any code is worth writing, and S5
is only a decision.

**What is NOT at risk:** `client-documents/`, `canon/`, `docs/` and
`satc-handoff/` had zero conflicts and shipped separately in PR #172.

All fourteen from the 3 September interview triage are closed — thirteen raised
by the review and F14 split out of F1 when its first fix turned out to be
partial.

## Closed — the client interview, raised 3 September 2026

Reproduced against the live interview engine and a running form on a temp store.
No client data was opened. The firm's decision form, with a recommendation and a
reason on every item:
**https://claude.ai/code/artifact/c5acade0-7e07-4881-8554-003377493ff7**

| # | Defect | Costs | State |
|---|---|---|---|

**Not one of the thirteen was covered by an existing test.** That is the number
worth remembering: the suite was 1,362 green and knew about none of it. It is
1,377 green now, and knows about three.

### Checked and found clean

Recorded because a survey that lists only what it found is not a survey.
`showIf` forward references (zero, audited programmatically against schema
order); dead `showIf`s (52 examined, 27 conditional, 0 dead); required-field
coverage against `registry/fields.yaml` (zero gaps); the back button's pruning
of now-invisible answers; `[CONFIRM: ]` refusal at merge; the TIN boundary
(denylisted in tests *and* refused on every draft write); draft-id path
traversal; the hard-no short-circuit; `MaterialsDeadline` correctly never asked;
and the live C-corp path.

---

## Fixed

### 3 September 2026 — the interview stops accepting answers it cannot mean

| # | Defect | Closed by |
|---|---|---|
| **F2** | `Interview.answer` never checked a value against the question's `options`, though `coerce`'s docstring claimed it did. `federal_form="1041"` was stored, printed as the engagement letter's scope line, and classified as an *individual* engagement | `is_offered()` — one predicate now shared with `prefill_is_answerable`, which had the rule all along. The interview would refuse to *suggest* a value it would happily *store* |
| **F1** | A double-click wrote the answer onto the next question | Defanged: the stray post now hits F2's guard and is refused. The missing question id on the post is still worth carrying — reopened as **F14** rather than called done |
| **F3** | `tax_year` was free text. `99999`/`-5` made `deadlines.board()` raise and took the whole calendar down; `0` printed a return due `0001-04-17` at the top of the board with `unplaced` empty | `type: year` in the schema, `deadlines.plausible_year()` enforcing it, and `board()` degrading an impossible year to `unplaced` instead of raising |

**Two things this taught, both worth keeping:**

1. **A refusal must not repeat what was sent.** The first version of F2's error
   quoted the rejected value — helpful until somebody types their SSN into
   question one, at which point the error, the log and the JSON response all
   carry it. `test_an_unfinished_sitting_is_refused_before_it_reaches_disk`
   caught it. The message now names what *would* work.
2. **Order the refusals by which message helps most.** Once F2 landed, an SSN
   typed into question one got "that is not one of the options" instead of "the
   last four digits are enough". `tins.refuse` now runs first inside
   `Interview.answer`, which also gives the CLI door a check it never had.

### 3 September 2026 — a count is a number, and some counts cannot be zero

| # | Defect | Closed by |
|---|---|---|
| **F5** | `coerce` returned the raw string when `int()` failed and `pricing._count` read any unparseable string as absence — zero. `count_rentals` of `abc`, `2.7` or `-3` all billed identically to a correct `1`, because `form_when` bumps a sub-1 count to 1; `count_states` of `-5` produced no state line at all | `Interview.answer` refuses a non-integer answer to a `number` or `year` question. `_count`'s comment — "the interview coerces its own types, and a stray string means the count was never really asked" — was an assumption about the interview; it is now true |
| **F13** | `count_owners = 0` satisfied a required question and printed as `OwnerCount` on the business letter, because required-ness is `value in (None, "", [])` and 0 is none of those | An optional `min:` on the question, declared in the schema rather than special-cased, so the next count that cannot be zero says so itself |

**And the engine now coerces its own input.** `web.py` called `coerce` before
`answer` and `cli.py --set` did too, so every type rule held for the two callers
that remembered and for nobody else. `answer()` calls it itself now — `coerce`
is idempotent, so the doors may keep calling it. Same shape as F7, and the same
reason `intake.py`'s header gives: *"a control that lives in one front door is a
control the other silently skips."*

### 3 September 2026 — one answer, and one place that derives from it

| # | Defect | Closed by |
|---|---|---|
| **F4** | The letter's scope came from the `states` list, the fee from a separate `count_states`. Proven: one state named in the letter, $100 of extra state returns on the estimate beside it, reconciled only at close-out a season later | The counts are `derived: true` now — same mechanism `federal_schedules` already used — and `interview.counted()` reads them off the lists. A lone `"None"` counts as zero, because `localities`' help tells the preparer to type exactly that |
| **F7** | `intake.finish` did not derive `federal_schedules`; `Interview.answer` did it per keystroke and `missing_required` on a throwaway copy, so answers arriving any other way were priced without them | `iv.derive()` at the top of `intake.finish`. The workaround in `exercise.py:332` is deleted — it was the tell that this was known |

**Both fixes are the same seam.** F4 adds a second derived value, and it had to
land wherever the first one did — building that hole twice would have been
silly, so `derive()` is now the one place: `schedules.apply` plus the counts,
called by `Interview.answer`, by `missing_required`, and by `intake.finish`.

Note the direction, because `schedules.py` warns against the opposite:
deriving a *schedule* from a *count* is wrong, since a count can be blank while
the thing exists. Deriving a count from a *list* is safe — the list is the
enumeration, so its length is exact and cannot be blank-but-true.

### 3 September 2026 — a type nothing understood, a question nobody should see, and two shapes

| # | Defect | Closed by |
|---|---|---|
| **F6** | `type: integer` on two questions was a type no code in the repo handled — free-text box for a count, and invisible to the dead-condition sweep, which probes only `type: number` | Both changed to `number`, and `check_types()` now runs at every `load_schema()`. The whole class of typo is an error at load rather than a wrong input box nobody notices |
| **F8** | `extra_forms` had no `showIf`, so a 1120 was asked about home sales, HSAs, marketplace insurance and pre-59½ withdrawals | `showIf: federal_form == '1040'`. The sweep could never have found it — an unconditional question is filed under `always` and never examined |
| **F12** | `client_email` and `client_zip` were unvalidated, and a mistyped address fails silently: the signing invitation just never arrives | A `pattern` the question declares, with `pattern_says` carrying the human sentence — because a regex is not an error message |

**The test helpers had to learn the new shapes**, in two files, and that is worth
recording: `_plausible` returned `"x"` for anything textual, so every walk
stalled at the first question with a `pattern`. The fix tries stock values
against the pattern rather than mapping question ids, so the next question to
grow one does not silently stall every walk again.

### 3 September 2026 — the last four, and the register is empty

| # | Defect | Closed by |
|---|---|---|
| **F14** | `POST /interview/<sid>` carried no question id, so a resubmit applied to whatever question was current when it landed | A hidden `question` field, and a 409 when it names a question the sitting has moved past. Absent is still accepted — the JSON door predates it, and present-and-wrong is the case that matters |
| **F9** | The coverage test asserted `business-letter` for a 1120, which gets `ccorp-letter`, and passed only because it hand-wrote two answers a real 1120 sitting prunes | It drives a real sitting and takes the document from `OPENING_BY_RETURN`. A second test asserts every opening letter is covered, so `ccorp-letter` cannot go unchecked again |
| **F10** | Abandoned drafts kept a prospect's name, address and email in cleartext forever, in a folder that syncs to OneDrive | `purge_drafts()` at 90 days, the firm's number. Refusals and declines are kept deliberately; an undated draft is kept, because the failure mode of this rule is destroying a record |
| **F11** | The PRD described seven sections with red flags at six; the schema has ten with red flags second | The PRD is read back from the schema and says the schema wins, and `test_the_prd_names_the_sections_the_schema_actually_has` fails if a section is ever added silently |

**Two harnesses caught things the suite did not**, which is the whole argument
for keeping them:

- `capture.py` failed after F3. It walks to "the first `text` question with no
  claim", which used to be `tax_year` — giving that its own `type: year` moved
  the stop PAST `red_flags`, so the walk answered the hard-no question on its
  way by and photographed the review screen instead. 1,412 tests were green
  while this was broken. The hand-maintained walkthrough registry was the only
  thing that noticed (S9).
- `drive()` in `test_web.py` looped `while True` and spun forever on a missing
  answer instead of failing. It cost ten minutes of a run and looked like a
  hang. Bounded now, and it says which question it stuck on.

### The year window, and why it is not three

IRC 6511(a) caps a **refund** claim at three years from filing (or two from
payment, whichever is later) — so three is right for an amended return worth
filing. It is *not* the input rule: an **unfiled** return has no statute of
limitations, because 6501's assessment clock starts when a return is filed and
for a year nobody filed it never started. The firm does that work and the
interview asks "Any unfiled years?" because it does.

So `YEARS_BACK = 7` is a typo guard and `REFUND_YEARS = 3` sits beside it as the
separate fact, unenforced — past three the return may still be worth filing, it
just cannot produce a refund, which is the shape of a review flag rather than an
input refusal. Confirmed against irs.gov, 3 September 2026, at the firm's
instruction.
