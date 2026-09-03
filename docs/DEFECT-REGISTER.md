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

## Open — the client interview, raised 3 September 2026

Reproduced against the live interview engine and a running form on a temp store.
No client data was opened. The firm's decision form, with a recommendation and a
reason on every item:
**https://claude.ai/code/artifact/c5acade0-7e07-4881-8554-003377493ff7**

| # | Defect | Costs | State |
|---|---|---|---|
| **F14** | `POST /interview/<sid>` still carries no question id, so a resubmit is applied to whatever question is current when it lands. No longer able to store a wrong *value* (F2 refuses it), but on a free-text question — a name, a note — there are no options to check against, so it can still overwrite the wrong field | wrong document | open, split from F1 |
| **F4** | The letter's scope comes from the `states` list, the fee from a separate `count_states`. Neither derives from the other. Proven: one state in the letter, $100 of extra state returns on the estimate. Reconciled only at close-out, a season later | wrong price | awaiting decision **B** (client-facing question changes) |
| **F6** | `type: integer` (`count_brokerages`, `count_extension_estimates`) is a type no code in the repo handles. Prices correctly only by luck; renders a text box for a count; blinds the dead-condition sweep, which probes only `type: number` | latent | queued |
| **F7** | `intake.finish` does not derive `federal_schedules`; every caller must remember to. Answers arriving the back way pass the required gate and are priced without them — proven: the Essentials package billed where Standard was due, and a rental line the letter omits. `exercise.py:332` works around it by hand | wrong price | queued |
| **F8** | `extra_forms` has no `showIf`, so a 1120 is asked whether it sold a home. The dead-condition sweep cannot catch it — an unconditional question is filed under `always` and never examined | annoyance | queued |
| **F9** | `test_coverage.py:86-99` asserts a `1120` produces `business-letter`; `cli.py:126-131` sends a C corp to `ccorp-letter`. Passes only because the test hand-writes two answers a real 1120 sitting prunes. **The live path is fine** — I drove a real 1120 end to end | test integrity | queued |
| **F10** | A draft is deleted only when an engagement is created. A decline or an abandoned call leaves name, address and email in cleartext JSON indefinitely — in a folder that now syncs to OneDrive. TINs are already refused on every write; names are not | PII retention | awaiting decision **C** (retention period) |
| **F11** | The PRD describes seven sections with red flags at six; the schema has nine with red flags second, plus three sections the PRD never mentions. PRD requirement 8 is that someone can build the Microsoft Form from it — today they would build the wrong one | doc drift | queued |
| **F12** | `client_email` and `client_zip` are unvalidated. The email question's own help says the signing invitation goes to that address | low | queued |

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
